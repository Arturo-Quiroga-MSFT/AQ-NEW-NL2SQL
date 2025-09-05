from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import typer

from DB_Assistant.core.schema_parser import load_schema, dump_schema
from DB_Assistant.core.schema_models import SchemaSpec, Entities, Dimension, Fact, Column
from DB_Assistant.agents.design_agent import draft_schema_from_prompt
from DB_Assistant.core.validators import validate_spec
from DB_Assistant.core.migration_planner import plan_migration
from DB_Assistant.core.ddl_renderer import operations_to_sql

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
    import os
    try:
        import pyodbc  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("pyodbc not installed. Install dependencies or skip apply.") from e
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_DATABASE")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    if not all([server, database, user, password]):
        raise RuntimeError("Missing one of DB_SERVER, DB_DATABASE, DB_USER, DB_PASSWORD.")
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)


@app.command()
def apply(sql_path: Path, dry_run: bool = typer.Option(False, help="Print only, do not execute.")):
    """Execute generated SQL statements against target Azure SQL (sequential)."""
    sql = sql_path.read_text(encoding="utf-8")
    if dry_run:
        _echo(sql)
        _echo("(Dry run complete)")
        return
    conn = _connect()
    cur = conn.cursor()
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    for stmt in statements:
        _echo(f"Executing: {stmt[:80]}...")
        cur.execute(stmt)
    conn.commit()
    cur.close()
    conn.close()
    _echo("Apply complete.")


if __name__ == "__main__":  # pragma: no cover
    app()
