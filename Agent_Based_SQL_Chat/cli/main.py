from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime
import typer
import statistics


from DB_Assistant.core.schema_parser import load_schema, dump_schema
from DB_Assistant.core.schema_models import SchemaSpec
from DB_Assistant.agents.design_agent import draft_schema_from_prompt
from DB_Assistant.core.validators import validate_spec
from DB_Assistant.core.migration_planner import plan_migration
from DB_Assistant.core.ddl_renderer import operations_to_sql
from DB_Assistant.core.inspector import inspect_database
from DB_Assistant.core.data_generator import generate_all
from DB_Assistant.core.impact_analyzer import analyze_impact
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

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
def plan(
    target: Path,
    current: Optional[Path] = typer.Option(None, help="Current schema YAML"),
    out: Optional[Path] = typer.Option(None, help="Write SQL plan to file"),
    impact_meta: bool = typer.Option(False, help="Also emit impact analysis JSON next to SQL (requires --out)"),
):
    """Produce a migration plan & optionally its impact metadata."""
    target_spec = load_schema(target)
    current_spec = load_schema(current) if current else None
    ops = plan_migration(current_spec, target_spec)
    sql = operations_to_sql(ops)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(sql, encoding="utf-8")
        _echo(f"Wrote plan SQL to {out}")
        if impact_meta:
            from DB_Assistant.core.impact_analyzer import analyze_impact
            impact = analyze_impact(ops)
            meta_path = Path(str(out) + ".impact.json")
            meta_path.write_text(json.dumps(impact, indent=2), encoding="utf-8")
            _echo(f"Wrote impact meta to {meta_path}")
    else:
        _echo(sql)
        if impact_meta:
            _echo("(impact_meta ignored without --out)")
    _echo(f"Operations: {json.dumps([o.op for o in ops])}")


@app.command()
def impact(
    target: Path,
    current: Optional[Path] = typer.Option(None, help="Current schema YAML for comparison"),
    json_output: bool = typer.Option(False, help="Emit JSON array of row-level analysis"),
    summary_only: bool = typer.Option(False, help="Show only aggregated risk counts"),
):
    """Analyze risk / impact of schema migration (ALTER/DROP/ADD columns).

    Provides per-column change rows plus an aggregated risk summary.
    """
    target_spec = load_schema(target)
    current_spec = load_schema(current) if current else None
    ops = plan_migration(current_spec, target_spec)
    analysis = analyze_impact(ops)
    # Build summary
    summary: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
    for a in analysis:
        summary[a.get("risk", "low")] = summary.get(a.get("risk", "low"), 0) + 1
    if json_output:
        _echo(json.dumps({"changes": analysis, "summary": summary}, indent=2))
        return
    if not analysis:
        _echo("No column-level changes requiring impact analysis.")
        return
    if not summary_only:
        widths = {"op": len("OP"), "table": len("TABLE"), "column": len("COLUMN"), "risk": len("RISK")}
        for a in analysis:
            for k in widths:
                widths[k] = max(widths[k], len(str(a.get(k, ""))))
        header = f"{ 'OP'.ljust(widths['op']) }  { 'TABLE'.ljust(widths['table']) }  { 'COLUMN'.ljust(widths['column']) }  { 'RISK'.ljust(widths['risk']) }  REASONS"
        _echo(header)
        _echo("-" * len(header))
        for a in analysis:
            reasons = "; ".join(a.get("reasons", []))
            _echo(f"{ a.get('op','').ljust(widths['op']) }  { a.get('table','').ljust(widths['table']) }  { a.get('column','').ljust(widths['column']) }  { a.get('risk','').ljust(widths['risk']) }  {reasons}")
    _echo("")
    _echo("Risk summary: " + ", ".join(f"{k}={v}" for k,v in summary.items()))


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
    allow_breaking: bool = typer.Option(False, help="Permit high-risk (destructive) operations in associated impact meta"),
):
    """Execute generated SQL statements against target Azure SQL (sequential) with migration ledger.

    Ledger table: db_assistant_migrations(hash VARCHAR(64) PK, file_name, applied_utc)
    """
    sql = sql_path.read_text(encoding="utf-8")
    # Safety gate: check for impact meta file
    meta_path = Path(str(sql_path) + ".impact.json")
    if meta_path.exists():
        try:
            impact = json.loads(meta_path.read_text(encoding="utf-8"))
            # Format may be list (older) or list under key changes
            if isinstance(impact, dict) and "changes" in impact:
                changes = impact.get("changes", [])
            else:
                changes = impact
            high = [c for c in changes if c.get("risk") == "high"]
            if high and not allow_breaking and not dry_run:
                _echo("Refusing to apply: high-risk operations detected (use --allow-breaking to override):")
                for c in high:
                    _echo(f"  - {c.get('table')}.{c.get('column')} ({c.get('op')}) reasons: {', '.join(c.get('reasons', []))}")
                raise typer.Exit(code=2)
        except Exception as e:  # noqa: BLE001
            _echo(f"Warning: failed to parse impact meta ({e}); proceeding.")
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
    # Drop blank and full-line SQL comments so we don't attempt to execute comment-only lines
    raw_lines = [
        l for l in sql.splitlines()
        if l.strip() and not l.lstrip().startswith("--")
    ]
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
    seed_value: Optional[int] = typer.Option(None, help="Deterministic random seed for reproducible data"),
):
    """Generate synthetic data and insert into tables respecting dimension→fact order."""
    import yaml, random
    if seed_value is not None:
        random.seed(seed_value)
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
        # Use DELETE (not TRUNCATE) to avoid FK restriction while preserving identity reseed simplicity if needed.
        # Order: facts then dimensions.
        for fact in spec.entities.facts:
            cur.execute(f"IF OBJECT_ID('{fact.name}','U') IS NOT NULL DELETE FROM {fact.name};")
        for dim in spec.entities.dimensions:
            cur.execute(f"IF OBJECT_ID('{dim.name}','U') IS NOT NULL DELETE FROM {dim.name};")
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
    # Before inserting facts, detect legacy required columns (e.g., payment_date) still present in DB but not in spec
    for fact in spec.entities.facts:
        fact_rows = data.get(fact.name, [])
        if not fact_rows:
            continue
        # Inspect live table columns & nullability
        cur.execute("SELECT COLUMN_NAME, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME=?", (fact.name,))
        live_cols = cur.fetchall()
        live_required = {r[0] for r in live_cols if r[1] == 'NO'}
        spec_cols = {c.name for c in fact.columns} | {m.name for m in fact.measures}
        missing_required = [c for c in live_required if c not in spec_cols]
        if missing_required:
            # Derive possible date columns from date_key
            for row in fact_rows:
                if 'date_key' in row:
                    dk = row['date_key']
                    # Convert int yyyymmdd to ISO date
                    iso_date = None
                    if isinstance(dk, int):
                        s = str(dk)
                        if len(s) == 8:
                            iso_date = f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
                    elif isinstance(dk, str) and dk.isdigit() and len(dk) == 8:
                        iso_date = f"{dk[0:4]}-{dk[4:6]}-{dk[6:8]}"
                    for miss in missing_required:
                        if miss not in row:
                            if iso_date and (miss.endswith('_date') or miss == 'payment_date'):
                                row[miss] = iso_date
                            else:
                                # Fallback nullable populate with None (will fail if truly required non-date, but surfaces clearly)
                                row[miss] = None
        _echo(f"Seeding {fact.name} ({len(fact_rows)} rows)...")
        _insert(fact.name, fact_rows)
    conn.commit(); cur.close(); conn.close()
    _echo("Seeding complete.")


@app.command()
def report(
    table: str = typer.Argument(..., help="Table name (fact) to summarize measures"),
    json_output: bool = typer.Option(False, help="Emit JSON instead of text lines"),
    percentiles: str = typer.Option("95", help="Comma-separated percentile list (e.g. 90,95,99)"),
):
    """Quick stats summary for DECIMAL / NUMERIC measure columns in a fact table.

    Adds variance, selected percentiles, and null counts.
    """
    conn = _connect(); cur = conn.cursor()
    cur.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME=?", (table,))
    dec_cols = [r[0] for r in cur.fetchall() if r[1].upper() in ("DECIMAL", "NUMERIC")]
    if not dec_cols:
        _echo("No DECIMAL measure columns detected."); cur.close(); conn.close(); return
    pct_list = []
    try:
        if percentiles.strip():
            pct_list = [int(p.strip()) for p in percentiles.split(',') if p.strip()]
    except ValueError:
        _echo("Invalid percentile list; must be integers.")
        cur.close(); conn.close(); return
    results = {}
    for col in dec_cols:
        cur.execute(f"SELECT CAST([{col}] AS FLOAT) FROM {table}")
        raw = [row[0] for row in cur.fetchall()]
        vals = [v for v in raw if v is not None]
        nulls = len(raw) - len(vals)
        if not vals:
            results[col] = {"count": 0, "nulls": nulls}
            continue
        sorted_vals = sorted(vals)
        def _pct(p: int) -> float:
            if not sorted_vals:
                return 0.0
            k = (len(sorted_vals)-1) * (p/100)
            f = int(k)
            c = min(f+1, len(sorted_vals)-1)
            if f == c:
                return sorted_vals[f]
            return sorted_vals[f] + (sorted_vals[c]-sorted_vals[f]) * (k - f)
        pct_stats = {f"p{p}": round(_pct(p), 2) for p in pct_list}
        stats_obj = {
            "count": len(vals),
            "nulls": nulls,
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
            "mean": round(sum(vals)/len(vals), 2),
            "median": round(statistics.median(vals), 2),
            "variance": round(statistics.pvariance(vals), 4) if len(vals) > 1 else 0.0,
            **pct_stats,
        }
        results[col] = stats_obj
    if json_output:
        _echo(json.dumps(results, indent=2))
    else:
        for col, stats_obj in results.items():
            _echo(f"{col}: {stats_obj}")
    cur.close(); conn.close()


@app.command()
def diagram(schema: Path = typer.Argument(..., help="Schema spec YAML"), out: Path = typer.Option(Path("schema.mmd"), help="Output Mermaid file")):
    """Generate a Mermaid ER-style diagram (simplified) for the schema."""
    spec = load_schema(schema)
    lines = ["%% Autogenerated Mermaid ER diagram", "erDiagram"]
    # Entities
    for dim in spec.entities.dimensions:
        lines.append(f"  {dim.name} {{")
        for c in dim.columns:
            lines.append(f"    {c.type} {c.name}")
        lines.append("  }")
    for fact in spec.entities.facts:
        lines.append(f"  {fact.name} {{")
        for c in fact.columns:
            lines.append(f"    {c.type} {c.name}")
        for m in fact.measures:
            lines.append(f"    {m.type} {m.name}")
        lines.append("  }")
    # Relationships (FKs)
    for fact in spec.entities.facts:
        for fk in fact.foreign_keys:
            ref = fk.references
            if "(" in ref and ref.endswith(")"):
                ref_table, _ = ref[:-1].split("(")
                lines.append(f"  {ref_table} ||--o{fact.name} : {fk.column}")
    out.write_text("\n".join(lines), encoding="utf-8")
    _echo(f"Wrote diagram to {out}")


@app.command()
def orchestrate(
    query: str = typer.Argument(..., help="Natural language question"),
    no_exec: bool = typer.Option(False, help="Skip SQL execution"),
    explain_only: bool = typer.Option(False, help="Only intent + reasoning, no SQL gen"),
    no_reasoning: bool = typer.Option(False, help="Skip reasoning step"),
    refresh_schema: bool = typer.Option(False, help="Force schema context refresh"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON (suppresses rich panels)"),
):
    """Run multi-agent (LangGraph) orchestration pipeline for NL → SQL."""
    try:
        from agents_nl2sql.graph import build as build_graph
        from agents_nl2sql.state import GraphState, Flags
    except Exception as e:  # noqa: BLE001
        _echo(f"LangGraph components unavailable: {e}")
        raise typer.Exit(code=1)
    console = Console()
    flags = Flags(no_exec=no_exec, explain_only=explain_only, no_reasoning=no_reasoning, refresh_schema=refresh_schema)
    graph = build_graph()
    state = GraphState(user_query=query, flags=flags)
    console.print(Panel.fit(f"[bold cyan]Starting orchestration[/bold cyan]\nQuery: [white]{query}[/white]"))
    result = graph.invoke(state)
    # LangGraph returns dict-like state; support both object & dict attribute styles.
    def _get(attr: str, default=None):
        if isinstance(result, dict):
            return result.get(attr, default)
        return getattr(result, attr, default)

    # If JSON output requested, build structured payload and print once.
    if json_output:
        exec_result = _get("execution_result") or {}
        rows = []
        if isinstance(exec_result, dict):
            rows = exec_result.get("rows") or []
        else:
            rows = getattr(exec_result, "rows", []) or []
        tu = _get("token_usage", {}) or {}
        payload = {
            "query": query,
            "intent": str(_get("intent_entities")),
            "reasoning": None if no_reasoning else _get("reasoning"),
            "sql_raw": None if explain_only else _get("sql_raw"),
            "sql_sanitized": None if explain_only else _get("sql_sanitized"),
            "rows_sample": rows[:25],
            "row_count": len(rows) if rows else 0,
            "errors": _get("errors", []),
            "token_usage": {
                "prompt": (tu.get("prompt") if isinstance(tu, dict) else getattr(tu, "prompt", 0)) or 0,
                "completion": (tu.get("completion") if isinstance(tu, dict) else getattr(tu, "completion", 0)) or 0,
                "total": (tu.get("total") if isinstance(tu, dict) else getattr(tu, "total", 0)) or 0,
            },
            "flags": {
                "no_exec": no_exec,
                "explain_only": explain_only,
                "no_reasoning": no_reasoning,
                "refresh_schema": refresh_schema,
            },
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        }
        typer.echo(json.dumps(payload, indent=2))
        return
    console.print(Panel.fit(str(_get("intent_entities")), title="Intent", border_style="green"))
    # Reasoning (if any)
    reasoning_val = _get("reasoning")
    if reasoning_val and not no_reasoning:
        console.print(Panel(reasoning_val, title="Reasoning", border_style="blue"))
    # SQL
    if not explain_only:
        console.print(Panel(_get("sql_raw") or "(no sql generated)", title="SQL Raw", border_style="magenta"))
        console.print(Panel(_get("sql_sanitized") or "(no sanitized sql)", title="SQL Sanitized", border_style="magenta"))
    # Execution
    exec_rows = _get("execution_result", {}).get("rows") if isinstance(_get("execution_result"), dict) else getattr(_get("execution_result"), "rows", [])
    if exec_rows:
        tbl = Table(show_header=True, header_style="bold yellow")
        first = exec_rows[0]
        for i, col in enumerate(first.keys()):
            if i >= 8:
                break
            tbl.add_column(col)
        for r in exec_rows[:25]:
            tbl.add_row(*[str(r[k]) for k in list(first.keys())[:8]])
        console.print(tbl)
    errs = _get("errors", [])
    if errs:
        console.print(Panel("\n".join(errs), title="Errors", border_style="red"))
    tu = _get("token_usage", {})
    prompt_t = tu.get("prompt") if isinstance(tu, dict) else getattr(tu, "prompt", 0)
    completion_t = tu.get("completion") if isinstance(tu, dict) else getattr(tu, "completion", 0)
    total_t = tu.get("total") if isinstance(tu, dict) else getattr(tu, "total", 0)
    console.print(Panel.fit(f"Run complete. Tokens: prompt={prompt_t} completion={completion_t} total={total_t}", border_style="cyan"))


if __name__ == "__main__":  # pragma: no cover
    app()
