from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime
import typer

from DB_Assistant.core.schema_parser import load_schema, dump_schema
from DB_Assistant.core.schema_models import SchemaSpec
from DB_Assistant.agents.design_agent import draft_schema_from_prompt
from DB_Assistant.core.validators import validate_spec
from DB_Assistant.core.migration_planner import plan_migration
from DB_Assistant.core.ddl_renderer import operations_to_sql
from DB_Assistant.core.inspector import inspect_database
from DB_Assistant.core.data_generator import generate_all

app = typer.Typer(help="DB Assistant CLI – Phase 0 scaffold")


def _echo(s: str):  # Wrapper for future richer logging
    typer.echo(s)


@app.command()
def design(
    prompt: str = typer.Argument(..., help="Natural language schema intent."),
    out: Path = typer.Option(Path("DB_Assistant/schema_specs/proposals/generated.yml"), help="Output YAML path"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Disable LLM and use heuristic fallback."),
):
    """Generate a schema spec from a natural language prompt using Azure OpenAI (fallback heuristic)."""
    spec = draft_schema_from_prompt(prompt, use_llm=(not no_llm))
    out.parent.mkdir(parents=True, exist_ok=True)
    dump_schema(spec, out)
    _echo(f"Wrote schema to {out}")


@app.command()
def validate(path: Path):
    """Validate a schema spec file."""
    spec = load_schema(path)
    errs = validate_spec(spec)
    if errs:
        for e in errs:
            _echo(f"ERROR: {e}")
        raise typer.Exit(code=1)
    _echo("Schema valid.")


@app.command()
def plan(target: Path, current: Optional[Path] = typer.Option(None, help="Current schema YAML"), out: Optional[Path] = typer.Option(None, help="Write SQL plan to file")):
    """Produce a simple migration plan (Phase 0: only CREATE TABLE)."""
    target_spec = load_schema(target)
    current_spec = load_schema(current) if current else None
    ops = plan_migration(current_spec, target_spec)
    sql = operations_to_sql(ops)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(sql, encoding="utf-8")
        _echo(f"Wrote plan SQL to {out}")
    else:
        _echo(sql)
    _echo(f"Operations: {json.dumps([o.op for o in ops])}")


def _connect():  # Lazy import so environments without pyodbc still work for design/plan
    """Connect to Azure SQL using DB_* env vars with fallback to AZURE_SQL_*.

    Expected primary variables:
      DB_SERVER, DB_DATABASE, DB_USER, DB_PASSWORD
    Fallback (legacy/global .env):
      AZURE_SQL_SERVER, AZURE_SQL_DB, AZURE_SQL_USER, AZURE_SQL_PASSWORD
    """
    import os
    try:
        import pyodbc  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("pyodbc not installed. Install dependencies or skip apply.") from e

    server = os.getenv("DB_SERVER") or os.getenv("AZURE_SQL_SERVER")
    database = os.getenv("DB_DATABASE") or os.getenv("AZURE_SQL_DB")
    user = os.getenv("DB_USER") or os.getenv("AZURE_SQL_USER")
    password = os.getenv("DB_PASSWORD") or os.getenv("AZURE_SQL_PASSWORD")

    missing = [name for name, val in [
        ("server", server), ("database", database), ("user", user), ("password", password)
    ] if not val]
    if missing:
        raise RuntimeError(
            "Missing required DB connection env vars (tried DB_* then AZURE_SQL_*). Missing: "
            + ", ".join(missing)
        )

    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)


@app.command()
def apply(
    sql_path: Path,
    dry_run: bool = typer.Option(False, help="Print only, do not execute."),
    force: bool = typer.Option(False, help="Apply even if hash already recorded in ledger."),
):
    """Execute generated SQL statements against target Azure SQL (sequential) with migration ledger.

    Ledger table: db_assistant_migrations(hash VARCHAR(64) PK, file_name, applied_utc)
    """
    sql = sql_path.read_text(encoding="utf-8")
    file_hash = hashlib.sha256(sql.encode("utf-8")).hexdigest()
    if dry_run:
        _echo(f"-- Hash: {file_hash}\n{sql}")
        _echo("(Dry run complete)")
        return
    conn = _connect()
    cur = conn.cursor()
    # Ensure ledger table
    cur.execute(
        "IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='db_assistant_migrations') BEGIN "
        "CREATE TABLE db_assistant_migrations (hash VARCHAR(64) PRIMARY KEY, file_name NVARCHAR(400), applied_utc DATETIME2 NOT NULL); END"
    )
    cur.execute("SELECT 1 FROM db_assistant_migrations WHERE hash=?", (file_hash,))
    if cur.fetchone() and not force:
        _echo(f"Hash already applied ({file_hash}); skipping. Use --force to override.")
        cur.close(); conn.close()
        return
    # Parse statements while keeping IF...BEGIN ... END blocks intact
    raw_lines = [l for l in sql.splitlines() if l.strip()]
    statements: list[str] = []
    buffer: list[str] = []
    in_block = False
    for line in raw_lines:
        upper = line.upper().strip()
        if upper.startswith("IF NOT EXISTS") and "BEGIN" in upper:
            # Start of guarded block
            if buffer:
                statements.append("\n".join(buffer))
                buffer = []
            in_block = True
            buffer.append(line)
            continue
        if in_block:
            buffer.append(line)
            if upper == "END" or upper.endswith(" END"):
                # block finished
                statements.append("\n".join(buffer))
                buffer = []
                in_block = False
            continue
        # Non-guarded line; split on semicolons carefully
        if ";" in line:
            parts = [p.strip() for p in line.split(";") if p.strip()]
            for p in parts:
                statements.append(p)
        else:
            buffer.append(line)
    if buffer:
        statements.append("\n".join(buffer))

    for stmt in statements:
        _echo(f"Executing: {stmt[:110]}...")
        cur.execute(stmt)
    cur.execute(
        "INSERT INTO db_assistant_migrations (hash, file_name, applied_utc) VALUES (?, ?, ?)",
        (file_hash, str(sql_path), datetime.utcnow()),
    )
    conn.commit()
    cur.close(); conn.close()
    _echo(f"Apply complete. Ledger hash={file_hash}")


@app.command()
def inspect(out: Path = typer.Option(Path("DB_Assistant/schema_specs/live_inspected.yml"), help="Output YAML path for inspected live schema")):
    """Reverse engineer current database (tables & columns) into a schema YAML (minimal)."""
    conn = _connect()
    cur = conn.cursor()
    spec = inspect_database(cur)
    out.parent.mkdir(parents=True, exist_ok=True)
    dump_schema(spec, out)
    cur.close(); conn.close()
    _echo(f"Wrote inspected schema to {out}")


@app.command()
def seed(
    schema: Path = typer.Argument(..., help="Schema spec YAML to base data generation on"),
    profile: Path = typer.Argument(..., help="Seeding profile YAML"),
    batch_size: int = typer.Option(500, help="Insert batch size"),
    dry_run: bool = typer.Option(False, help="Generate but do not insert"),
    truncate: bool = typer.Option(False, help="Truncate target tables before inserting"),
):
    """Generate synthetic data and insert into tables respecting dimension→fact order."""
    import yaml
    spec = load_schema(schema)
    profile_obj = yaml.safe_load(profile.read_text(encoding="utf-8"))
    data = generate_all(spec, profile_obj)
    if dry_run:
        summary = {k: len(v) for k, v in data.items()}
        _echo(json.dumps(summary, indent=2))
        return
    conn = _connect()
    cur = conn.cursor()
    # Optional truncate
    if truncate:
        # Facts first for FK safety
        for fact in spec.entities.facts:
            cur.execute(f"IF OBJECT_ID('{fact.name}','U') IS NOT NULL TRUNCATE TABLE {fact.name};")
        for dim in spec.entities.dimensions:
            cur.execute(f"IF OBJECT_ID('{dim.name}','U') IS NOT NULL TRUNCATE TABLE {dim.name};")
    # Insert dimensions then facts
    def _insert(table: str, rows: list[dict[str, object]]):
        if not rows:
            return
        # Derive column list from first row keys
        cols = sorted(rows[0].keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_csv = ", ".join(cols)
        sql = f"INSERT INTO {table} ({col_csv}) VALUES ({placeholders})"
        batch = []
        for r in rows:
            batch.append([r.get(c) for c in cols])
            if len(batch) >= batch_size:
                cur.executemany(sql, batch)
                batch.clear()
        if batch:
            cur.executemany(sql, batch)

    for dim in spec.entities.dimensions:
        _echo(f"Seeding {dim.name} ({len(data.get(dim.name, []))} rows)...")
        _insert(dim.name, data.get(dim.name, []))
    for fact in spec.entities.facts:
        _echo(f"Seeding {fact.name} ({len(data.get(fact.name, []))} rows)...")
        _insert(fact.name, data.get(fact.name, []))
    conn.commit(); cur.close(); conn.close()
    _echo("Seeding complete.")


if __name__ == "__main__":  # pragma: no cover
    app()
