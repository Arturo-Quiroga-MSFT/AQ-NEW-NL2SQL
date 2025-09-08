"""
Clean Streamlit UI for DB Assistant.
Rebuilt after corruption to provide:
 1. Prompt (LLM → draft schema)
 2. Plan (migration planning + optional impact)
 3. Apply (executes plan SQL)
 4. Explore (table/columns/sample)
 5. Query Console (ad-hoc SQL)
 6. Orchestrate (multi-agent NL→SQL)
 7. NL Admin (natural language administrative commands with risk gating)
 8. Admin (utility DDL helpers)
"""

from pathlib import Path
import sys, os, json
from typing import List, Dict, Any
import streamlit as st

# --- Path setup ---
_here = Path(__file__).resolve()
_root = _here.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from DB_Assistant.core.schema_parser import load_schema, dump_schema  # noqa: E402
from DB_Assistant.core.validators import validate_spec  # noqa: E402
from DB_Assistant.core.migration_planner import plan_migration  # noqa: E402
from DB_Assistant.core.ddl_renderer import operations_to_sql  # noqa: E402
from DB_Assistant.agents.design_agent import draft_schema_from_prompt  # noqa: E402

# Star schema diagnostics (Phase 1 integration)
try:  # optional star modules
    from DB_Assistant.star.nl_parser import StarParser  # type: ignore
    from DB_Assistant.star.introspection import (
        build_star_overview,
        compute_fact_health,
        orphan_check as star_orphan_check,
        column_null_density,
        top_value_distribution,
    )  # type: ignore
    _HAS_STAR = True
    _STAR_PARSER = StarParser()
except Exception:  # noqa: BLE001
    _HAS_STAR = False
    _STAR_PARSER = None  # type: ignore

try:  # optional orchestration
    from agents_nl2sql.graph import build as build_graph  # type: ignore
    from agents_nl2sql.state import GraphState, Flags  # type: ignore
    _HAS_ORCHESTRATE = True
except Exception:  # noqa: BLE001
    _HAS_ORCHESTRATE = False


# ---------------- DB Helpers ----------------
def _connect(db: str | None = None, use_master: bool = False):
    import pyodbc  # type: ignore
    # Prefer new DB_* vars; fallback to legacy AZURE_SQL_* if DB_* not provided
    server = os.getenv("DB_SERVER") or os.getenv("AZURE_SQL_SERVER")
    database = db or os.getenv("DB_DATABASE") or os.getenv("AZURE_SQL_DB")
    if use_master:
        database = "master"
    user = os.getenv("DB_USER") or os.getenv("AZURE_SQL_USER")
    password = os.getenv("DB_PASSWORD") or os.getenv("AZURE_SQL_PASSWORD")
    if not all([server, database, user, password]):
        return None
    cs = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )
    try:
        return pyodbc.connect(cs)
    except Exception as e:  # noqa: BLE001
        st.error(f"Connection failed: {e}")
        return None


def _run_sql(sql: str, limit: int | None = None) -> Dict[str, Any]:
    conn = _connect()
    if conn is None:
        return {"error": "Missing or invalid DB_* env vars."}
    cur = conn.cursor()
    try:
        sql_clean = sql.strip().rstrip(";")
        cur.execute(sql_clean)
        if cur.description:
            cols = [c[0] for c in cur.description]
            rows = cur.fetchall()
            if limit:
                rows = rows[:limit]
            data = [dict(zip(cols, r)) for r in rows]
            return {"columns": cols, "rows": data, "row_count": len(data)}
        conn.commit()
        return {"message": "Statement executed.", "row_count": cur.rowcount}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
    finally:
        cur.close(); conn.close()


def _list_tables() -> List[str]:
    conn = _connect()
    if conn is None:
        return []
    cur = conn.cursor()
    cur.execute("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' ORDER BY 1,2")
    rows = [f"{r[0]}.{r[1]}" for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def _table_schema(table: str) -> List[Dict[str, Any]]:
    conn = _connect()
    if conn is None:
        return []
    cur = conn.cursor()
    schema, name = (table.split('.', 1) + [None])[:2]
    if name is None:
        schema = 'dbo'; name = table
    cur.execute(
        """
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=? AND TABLE_NAME=?
        ORDER BY ORDINAL_POSITION
        """, (schema, name)
    )
    cols = [{"column": r[0], "type": r[1], "nullable": r[2], "length": r[3]} for r in cur.fetchall()]
    cur.close(); conn.close()
    return cols


def _generate_table_ddl(table: str) -> str:
    cols = _table_schema(table)
    if not cols:
        return f"-- Unable to introspect {table}"
    schema, name = (table.split('.', 1) + [None])[:2]
    if name is None:
        schema = 'dbo'; name = table
    parts = [f"CREATE TABLE {schema}.{name} ("]
    col_defs = []
    for c in cols:
        dtype = c['type']
        if c.get('length') and c['length'] and dtype.upper() in {"VARCHAR", "NVARCHAR", "CHAR", "NCHAR"}:
            dtype = f"{dtype}({c['length']})"
        nullable = "NOT NULL" if c['nullable'] == 'NO' else "NULL"
        col_defs.append(f"    {c['column']} {dtype} {nullable}")
    parts.append(",\n".join(col_defs))
    parts.append(");")
    return "\n".join(parts)


def _orchestrate_nl(query: str, execute: bool) -> Dict[str, Any]:
    if not _HAS_ORCHESTRATE:
        return {"error": "LangGraph orchestration components not available."}
    try:
        graph = build_graph()
        flags = Flags(no_exec=not execute, explain_only=False, no_reasoning=False, refresh_schema=False)
        state = GraphState(user_query=query, flags=flags)
        res = graph.invoke(state)
        if not isinstance(res, dict):
            res = res.__dict__  # type: ignore
        exec_res = res.get("execution_result") or {}
        rows = exec_res.get("rows") if isinstance(exec_res, dict) else getattr(exec_res, "rows", [])
        rows = rows or []
        return {
            "intent": str(res.get("intent_entities")),
            "reasoning": res.get("reasoning"),
            "sql_raw": res.get("sql_raw"),
            "sql_sanitized": res.get("sql_sanitized"),
            "rows": rows[:200],
            "row_count": len(rows),
            "errors": res.get("errors", []),
            "token_usage": res.get("token_usage", {}),
        }
    except Exception as e:  # noqa: BLE001
        return {"error": f"Orchestration failed: {e}"}


# -------------- NL Admin Heuristics --------------
_ADMIN_SIMPLE_TYPES = [
    "INT", "BIGINT", "SMALLINT", "TINYINT", "DECIMAL(18,2)", "DECIMAL(19,4)", "DATE", "DATETIME2",
    "VARCHAR(20)", "VARCHAR(40)", "VARCHAR(50)", "VARCHAR(60)", "VARCHAR(100)"
]


def _classify_risk(sql: str) -> str:
    up = sql.upper()
    if any(k in up for k in ["DROP TABLE", "DROP COLUMN", "TRUNCATE TABLE"]):
        return "high"
    if "ALTER TABLE" in up and ("DROP" in up or "ALTER COLUMN" in up):
        return "medium"
    return "low"


def _heuristic_admin_parse(nl: str) -> List[Dict[str, Any]]:
    import re
    text = nl.strip().lower()
    actions: List[Dict[str, Any]] = []
    if not text:
        return actions
    if re.search(r"^(list|show) tables", text):
        actions.append({"action": "list_tables", "sql": "SELECT TABLE_SCHEMA + '.' + TABLE_NAME AS full_name FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' ORDER BY 1;", "risk": "low", "note": "List all base tables"})
        return actions
    m = re.match(r"describe table ([a-z0-9_.]+)", text)
    if m:
        tbl = m.group(1)
        actions.append({"action": "describe_table", "sql": f"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{tbl.split('.')[-1]}' ORDER BY ORDINAL_POSITION;", "risk": "low", "note": f"Describe columns for {tbl}"})
        return actions
    m = re.match(r"row count for ([a-z0-9_.]+)", text)
    if m:
        tbl = m.group(1)
        actions.append({"action": "row_count", "sql": f"SELECT COUNT(*) AS row_count FROM {tbl};", "risk": "low", "note": f"Row count for {tbl}"})
        return actions
    m = re.match(r"drop table ([a-z0-9_.]+)", text)
    if m:
        tbl = m.group(1)
        sql = f"IF OBJECT_ID('{tbl.split('.')[-1]}','U') IS NOT NULL DROP TABLE {tbl};"
        actions.append({"action": "drop_table", "sql": sql, "risk": _classify_risk(sql), "note": f"Drop table {tbl} if exists"})
        return actions
    m = re.match(r"create table ([a-z0-9_.]+) with columns (.+)", text)
    if m:
        tbl = m.group(1)
        cols_raw = m.group(2)
        cols = []
        for part in cols_raw.split(','):
            part = part.strip()
            if not part:
                continue
            pieces = part.split()
            col = pieces[0]
            typ = "VARCHAR(50)"
            if len(pieces) > 1:
                candidate = pieces[1].upper()
                if candidate in [t.upper() for t in _ADMIN_SIMPLE_TYPES] or re.match(r"VARCHAR\(\d+\)", candidate):
                    typ = candidate
            cols.append(f"{col} {typ}")
        cols_sql = ", ".join(cols) if cols else "id INT"
        sql = f"IF OBJECT_ID('{tbl.split('.')[-1]}','U') IS NULL CREATE TABLE {tbl} ({cols_sql});"
        actions.append({"action": "create_table", "sql": sql, "risk": _classify_risk(sql), "note": f"Create table {tbl}"})
        return actions
    m = re.match(r"add column ([a-z0-9_]+) ([a-z0-9()]+) to ([a-z0-9_.]+)", text)
    if m:
        col, typ, tbl = m.groups()
        sql = f"IF COL_LENGTH('{tbl}', '{col}') IS NULL ALTER TABLE {tbl} ADD {col} {typ};"
        actions.append({"action": "add_column", "sql": sql, "risk": _classify_risk(sql), "note": f"Add column {col} to {tbl}"})
        return actions
    m = re.match(r"drop column ([a-z0-9_]+) from ([a-z0-9_.]+)", text)
    if m:
        col, tbl = m.groups()
        sql = f"IF COL_LENGTH('{tbl}', '{col}') IS NOT NULL ALTER TABLE {tbl} DROP COLUMN {col};"
        actions.append({"action": "drop_column", "sql": sql, "risk": _classify_risk(sql), "note": f"Drop column {col} from {tbl}"})
        return actions
    m = re.match(r"create index on ([a-z0-9_.]+)\(([^)]+)\)", text)
    if m:
        tbl, cols = m.groups()
        idx_cols = ''.join([c for c in cols if c.lower() in 'abcdefghijklmnopqrstuvwxyz0123456789_, '])
        idx_name = f"ix_{tbl.split('.')[-1]}_{idx_cols.split(',')[0].strip()}"
        sql = f"IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='{idx_name}' AND object_id=OBJECT_ID('{tbl}')) CREATE INDEX {idx_name} ON {tbl} ({idx_cols});"
        actions.append({"action": "create_index", "sql": sql, "risk": _classify_risk(sql), "note": f"Create index {idx_name}"})
        return actions
    if text.startswith("select "):
        actions.append({"action": "select", "sql": nl, "risk": "low", "note": "Ad-hoc query"})
    else:
        actions.append({"action": "unknown", "sql": nl, "risk": _classify_risk(nl), "note": "Unparsed; executing raw may be unsafe"})
    return actions


def _nl_admin_plan(nl: str) -> Dict[str, Any]:
    """Produce a unified plan from star-aware parser (if match) else heuristic parser.

    Star intents are converted to action objects with an 'action' key for uniform handling.
    """
    star_actions: List[Dict[str, Any]] = []
    if _HAS_STAR and _STAR_PARSER is not None:
        try:
            star_actions = _STAR_PARSER.parse(nl)
        except Exception:
            star_actions = []
    if star_actions:
        # Normalize field name to 'action'
        normalized = []
        for a in star_actions:
            na = {**a}
            if 'intent' in na:
                na['action'] = na.pop('intent')
            # introspection actions are read-only (risk already low)
            normalized.append(na)
        actions = normalized
    else:
        actions = _heuristic_admin_parse(nl)
    return {"input": nl, "actions": actions, "high_risk": any(a.get("risk") == "high" for a in actions)}


def _execute_star_action(act: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a star diagnostic action (no SQL) returning structured result.

    Returns dict with 'result' or 'error'.
    """
    if not _HAS_STAR:
        return {"error": "Star modules unavailable"}
    action = act.get('action')
    table = act.get('table')
    column = act.get('column')
    try:
        conn = _connect()
        if conn is None:
            return {"error": "No DB connection"}
        if action == 'star_overview':
            data = build_star_overview(conn)
            conn.close()
            return {"rows": data, "row_count": len(data)}
        if action == 'fact_health' and table:
            data = compute_fact_health(conn, table)
            conn.close()
            return {"json": data}
        if action == 'orphan_check' and table:
            data = star_orphan_check(conn, table)
            conn.close()
            return {"json": data}
        if action == 'null_density' and table:
            data = column_null_density(conn, table)
            conn.close()
            return {"rows": data, "row_count": len(data)}
        if action == 'top_distribution' and table and column:
            data = top_value_distribution(conn, table, column)
            conn.close()
            return {"rows": data, "row_count": len(data)}
        conn.close()
        return {"error": f"Unsupported star action {action}"}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def _audit_log(entries: List[Dict[str, Any]]):
    if not entries:
        return
    log_path = Path("DB_Assistant/admin_audit.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with log_path.open("a", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
    except Exception:
        pass  # silent


# -------------- UI --------------
st.set_page_config(page_title="DB Assistant", layout="wide")
st.title("DB Assistant – Unified Admin & NL2SQL Console")
st.sidebar.header("Navigation")
pages = [
    "Prompt", "Plan", "Apply", "Explore", "Star Model", "Query Console", "Orchestrate", "NL Admin", "Admin"
]
page = st.sidebar.radio("Go to", pages, index=0)
state = st.session_state


# ---- 1. Prompt ----
if page == "Prompt":
    st.subheader("1. Natural Language → Draft Schema")
    prompt = st.text_area(
        "Describe the analytical star schema you want",
        height=140,
        value=state.get("prompt", "Star schema for loan payments and companies"),
    )
    use_llm = st.checkbox("Use LLM (Azure OpenAI)", value=True)
    if st.button("Generate Draft", type="primary"):
        spec = draft_schema_from_prompt(prompt, use_llm=use_llm)
        state["prompt"] = prompt
        state["draft_spec"] = spec.model_dump()
        st.success("Draft generated.")
    if "draft_spec" in state:
        st.code(json.dumps(state["draft_spec"], indent=2), language="json")
        if st.button("Persist Draft YAML"):
            from DB_Assistant.core.schema_models import SchemaSpec
            spec_obj = SchemaSpec.model_validate(state["draft_spec"])
            out_path = Path("DB_Assistant/schema_specs/proposals/streamlit_draft.yml")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            dump_schema(spec_obj, out_path)
            st.info(f"Saved to {out_path}")

# ---- 2. Plan ----
elif page == "Plan":
    st.subheader("2. Plan Migration")
    target_file = st.text_input("Target schema YAML", "DB_Assistant/schema_specs/proposals/streamlit_draft.yml")
    current_file = st.text_input("Current schema YAML (optional)", "")
    include_impact = st.checkbox("Include impact analysis", value=True)
    if st.button("Compute Plan", type="primary"):
        target = load_schema(target_file)
        current = load_schema(current_file) if current_file.strip() else None
        errs = validate_spec(target)
        if errs:
            st.error("Validation errors: " + "; ".join(errs))
        else:
            ops = plan_migration(current, target)
            sql = operations_to_sql(ops)
            state["plan_sql"] = sql
            st.code(sql, language="sql")
            st.success(f"Operations: {[o.op for o in ops]}")
            if include_impact:
                try:
                    from DB_Assistant.core.impact_analyzer import analyze_impact
                    impact = analyze_impact(ops)
                    state["impact"] = impact
                    if impact:
                        st.markdown("### Impact Analysis")
                        st.code(json.dumps(impact, indent=2), language="json")
                    else:
                        st.info("No column-level impacts detected.")
                except Exception as e:  # noqa: BLE001
                    st.warning(f"Impact analyzer unavailable: {e}")
    if state.get("plan_sql"):
        st.download_button(
            "Download Plan SQL", data=state["plan_sql"], file_name="migration_plan.sql", mime="text/sql"
        )
    if state.get("impact"):
        st.download_button(
            "Download Impact JSON",
            data=json.dumps(state["impact"], indent=2),
            file_name="migration_plan.sql.impact.json",
            mime="application/json",
        )

# ---- 3. Apply ----
elif page == "Apply":
    st.subheader("3. Apply Plan (Sequential)")
    if "plan_sql" not in state:
        st.warning("Generate a plan first in the Plan step.")
    else:
        dry_run = st.checkbox("Dry Run", value=True)
        confirm = st.checkbox(
            "I understand this will run DDL against the target database", value=False, disabled=dry_run
        )
        if st.button("Execute Plan", type="primary"):
            sql = state["plan_sql"]
            if dry_run:
                st.info("Dry run – SQL not executed.")
                st.code(sql, language="sql")
            else:
                if not confirm:
                    st.error("Please confirm execution acknowledgment.")
                else:
                    try:
                        conn = _connect()
                        if conn is None:
                            raise RuntimeError("Missing DB env vars.")
                        cur = conn.cursor()
                        statements = [s.strip() for s in sql.split(";") if s.strip()]
                        for stmt in statements:
                            cur.execute(stmt)
                        conn.commit(); cur.close(); conn.close()
                        st.success("Apply complete.")
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Execution failed: {e}")

# ---- 4. Explore ----
elif page == "Explore":
    st.subheader("4. Explore Schema")
    tables = _list_tables()
    if not tables:
        st.info("No tables (or no connection). Set DB_* env vars and refresh.")
    else:
        t = st.selectbox("Select table", tables)
        if t:
            cols = _table_schema(t)
            st.write(cols)
            if st.button("Sample Rows"):
                res = _run_sql(f"SELECT TOP 25 * FROM {t}")
                if res.get("error"):
                    st.error(res["error"])
                else:
                    st.dataframe(res["rows"])
            if st.button("Show CREATE DDL"):
                st.code(_generate_table_ddl(t), language="sql")

# ---- 5. Star Model ----
elif page == "Star Model":
    st.subheader("5. Star Schema Model Dashboard")
    if not _HAS_STAR:
        st.warning("Star schema modules not available.")
    else:
        st.markdown("""This dashboard surfaces star schema classification & diagnostics.
        Use the controls below to inspect facts, dimensions, orphaned foreign keys, null density, and value distributions.""")

        # Caching layer for overview
        @st.cache_data(ttl=300, show_spinner=False)
        def _cached_star_overview() -> List[Dict[str, Any]]:  # type: ignore
            conn = _connect()
            if conn is None:
                return []
            try:
                data = build_star_overview(conn)
            finally:
                try:
                    conn.close()
                except Exception:  # noqa: BLE001
                    pass
            return data

        col_refresh, col_info = st.columns([1,4])
        with col_refresh:
            if st.button("Refresh Overview", help="Invalidate cache and re-run classification"):
                _cached_star_overview.clear()  # type: ignore
        with col_info:
            st.caption("Overview cached for 5 minutes – refresh to pick up new tables or FK changes.")

        overview = _cached_star_overview()
        if not overview:
            st.info("No overview data (check DB connection / tables).")
        else:
            st.markdown("### Classification Overview")
            st.dataframe(overview, use_container_width=True)
            # Derive lists
            fact_tables = [o['table'] for o in overview if o['class'] == 'fact']
            all_tables = [o['table'] for o in overview]

            st.markdown("### Diagnostics")
            diag_mode = st.radio("Select diagnostic", ["Fact Health", "Orphan Check", "Null Density", "Top Distribution"], horizontal=True)

            if diag_mode in ("Fact Health", "Orphan Check") and not fact_tables:
                st.warning("No fact tables detected.")
            else:
                if diag_mode == "Fact Health":
                    ft = st.selectbox("Fact table", fact_tables)
                    if ft and st.button("Run Fact Health"):
                        conn = _connect()
                        if conn is None:
                            st.error("No DB connection.")
                        else:
                            with st.spinner("Computing fact health..."):
                                try:
                                    res = compute_fact_health(conn, ft)
                                    st.code(json.dumps(res, indent=2), language='json')
                                finally:
                                    conn.close()
                elif diag_mode == "Orphan Check":
                    ft = st.selectbox("Fact table", fact_tables)
                    if ft and st.button("Run Orphan Check"):
                        conn = _connect()
                        if conn is None:
                            st.error("No DB connection.")
                        else:
                            with st.spinner("Checking foreign key orphans..."):
                                try:
                                    res = star_orphan_check(conn, ft)
                                    st.code(json.dumps(res, indent=2), language='json')
                                finally:
                                    conn.close()
                elif diag_mode == "Null Density":
                    tbl = st.selectbox("Table", all_tables)
                    if tbl and st.button("Compute Null Density"):
                        conn = _connect()
                        if conn is None:
                            st.error("No DB connection.")
                        else:
                            with st.spinner("Calculating null density..."):
                                try:
                                    res = column_null_density(conn, tbl)
                                    st.dataframe(res, use_container_width=True)
                                finally:
                                    conn.close()
                elif diag_mode == "Top Distribution":
                    tbl = st.selectbox("Table", all_tables)
                    if tbl:
                        # fetch columns
                        cols = _table_schema(tbl)
                        col_names = [c['column'] for c in cols]
                        col_sel = st.selectbox("Column", col_names)
                        top_n = st.slider("Top N", 5, 50, 20)
                        if col_sel and st.button("Compute Distribution"):
                            conn = _connect()
                            if conn is None:
                                st.error("No DB connection.")
                            else:
                                with st.spinner("Computing distribution..."):
                                    try:
                                        res = top_value_distribution(conn, tbl, col_sel, top=top_n)
                                        st.dataframe(res, use_container_width=True)
                                    finally:
                                        conn.close()

        st.caption("Planned additions: SCD change tracking, aggregate coverage matrix, index/partition advisor, drift detection.")

# ---- 6. Query Console ----
elif page == "Query Console":
    st.subheader("5. SQL Query Console")
    default_sql = state.get("last_sql", "SELECT TOP 5 * FROM sys.objects;")
    sql_input = st.text_area("SQL", height=180, value=default_sql)
    limit_rows = st.number_input("Client Row Limit (display)", min_value=10, max_value=2000, value=200)
    if st.button("Run Query", type="primary"):
        res = _run_sql(sql_input, limit=limit_rows)
        state["last_sql"] = sql_input
        if res.get("error"):
            st.error(res["error"])
        else:
            if res.get("rows"):
                st.success(f"Returned {res['row_count']} row(s) (showing up to {limit_rows}).")
                st.dataframe(res["rows"])
            else:
                st.info(res.get("message", "Statement executed."))

# ---- 7. Orchestrate ----
elif page == "Orchestrate":
    st.subheader("7. NL → SQL Orchestration")
    if not _HAS_ORCHESTRATE:
        st.warning("Orchestration modules not available.")
    else:
        nlq = st.text_input("Ask a question", "For each region list top 5 companies by total principal")
        execute = st.checkbox("Execute SQL", value=False)
        if st.button("Run Orchestration", type="primary"):
            res = _orchestrate_nl(nlq, execute)
            if res.get("error"):
                st.error(res["error"])
            else:
                st.markdown("**Intent**")
                st.code(res.get("intent"), language="text")
                if res.get("reasoning"):
                    st.markdown("**Reasoning**")
                    st.code(res.get("reasoning"), language="text")
                st.markdown("**SQL (Sanitized)**")
                st.code(res.get("sql_sanitized") or res.get("sql_raw") or "(none)", language="sql")
                if res.get("rows"):
                    st.success(f"Rows returned: {res['row_count']}")
                    st.dataframe(res["rows"])
                if res.get("errors"):
                    st.error("\n".join(res["errors"]))
                tu = res.get("token_usage", {})
                if tu:
                    st.caption(
                        f"Token usage: prompt={tu.get('prompt')} completion={tu.get('completion')} total={tu.get('total')}"
                    )

# ---- 8. NL Admin ----
elif page == "NL Admin":
    st.subheader("8. Natural Language DB Administration")
    st.markdown("Enter ONE plain English admin instruction. Multi-line batching coming soon.")
    examples = [
        "list star overview",
        "diagnose fact fact_loan_payments",
        "orphan check fact_loan_payments",
        "null density dbo.dim_company",
        "top distribution dbo.dim_company.country_key",
        "list tables",
        "describe table dbo.dim_company",
        "row count for fact_loan_payments",
        "create table dbo.demo_payments with columns id int, amount decimal(18,2)",
        "add column notes varchar(100) to dbo.demo_payments",
        "create index on dbo.demo_payments(id, created_at)",
        "drop table dbo.demo_payments",
        "select top 5 * from dbo.dim_company",
    ]
    st.code("\n".join(examples), language="text")
    nl_text = st.text_area("Instruction", height=140, value=state.get("last_nl_admin", "list tables"))
    if st.button("Parse Instruction", type="primary"):
        plan = _nl_admin_plan(nl_text)
        state["last_nl_admin"] = nl_text
        state["nl_admin_plan"] = plan
    plan = state.get("nl_admin_plan")
    if plan:
        st.markdown("### Planned Actions")
        for i, act in enumerate(plan["actions"], 1):
            risk_badge = {"high": "🔥 HIGH", "medium": "⚠️ MEDIUM", "low": "✅ LOW"}.get(act.get('risk',''), act.get('risk',''))
            st.write(f"{i}. [{risk_badge}] {act.get('action')} – {act.get('note','')}")
            if 'sql' in act:
                st.code(act['sql'], language="sql")
            else:
                st.caption("(diagnostic – no direct SQL shown)")
        high = any(a['risk'] == 'high' for a in plan['actions'])
        medium = any(a['risk'] == 'medium' for a in plan['actions']) and not high
        if high:
            st.error("High risk statements present (DROP/TRUNCATE). Type YES EXACTLY to enable execution.")
            ack = st.text_input("Type YES to allow execution", value="")
            exec_enabled = ack == "YES"
        elif medium:
            exec_enabled = st.checkbox("Acknowledge medium risk changes (ALTER/DROP column)", value=False)
        else:
            exec_enabled = st.checkbox("Ready to execute (low risk)", value=False)
        if st.button("Execute Actions", type="secondary"):
            if not exec_enabled:
                st.error("Risk acknowledgment not satisfied.")
            else:
                results = []
                audit_entries = []
                for act in plan['actions']:
                    if 'sql' in act:
                        res = _run_sql(act['sql'])
                        results.append({"action": act['action'], "result": res})
                        audit_entries.append({"action": act['action'], "sql": act['sql'], "risk": act['risk']})
                    else:  # star diagnostic
                        res = _execute_star_action(act)
                        results.append({"action": act['action'], "result": res})
                        audit_entries.append({"action": act['action'], "risk": act.get('risk','low'), "table": act.get('table'), "column": act.get('column')})
                _audit_log(audit_entries)
                st.markdown("### Execution Results")
                for r in results:
                    res = r['result']
                    if res.get('error'):
                        st.error(f"{r['action']}: {res['error']}")
                    elif res.get('rows'):
                        st.success(f"{r['action']} – {res.get('row_count', len(res['rows']))} row(s)")
                        st.dataframe(res['rows'])
                    elif res.get('json'):
                        st.success(f"{r['action']} – JSON result")
                        st.code(json.dumps(res['json'], indent=2), language='json')
                    else:
                        st.info(f"{r['action']}: {res.get('message','done')}")
                st.caption("Audit logged to DB_Assistant/admin_audit.log")
    st.caption(
        "Heuristic parser – upcoming: multi-statement batching, rename/alter type, FK & index introspection, rollback bundling, richer audit."
    )

# ---- 9. Admin ----
elif page == "Admin":
    st.subheader("9. Admin Utilities")
    st.markdown("### Create Database (requires server-level permissions)")
    new_db = st.text_input("New database name", "demo_db")
    if st.button("Create Database"):
        master_conn = _connect(use_master=True)
        if master_conn is None:
            st.error("Master connection failed (check credentials).")
        else:
            cur = master_conn.cursor()
            try:
                cur.execute(f"IF DB_ID('{new_db}') IS NULL CREATE DATABASE [{new_db}];")
                master_conn.commit()
                st.success(f"Database '{new_db}' ensured.")
            except Exception as e:  # noqa: BLE001
                st.error(f"Creation failed: {e}")
            finally:
                cur.close(); master_conn.close()
    st.divider()
    st.markdown("### Quick Table Create")
    ddl_table = st.text_input("Table name (schema.table)", "dbo.demo_table")
    ddl_cols = st.text_area(
        "Columns (comma-separated col TYPE)", "id INT PRIMARY KEY, name VARCHAR(50), created_at DATETIME2"
    )
    if st.button("Create Table"):
        if not ddl_table or not ddl_cols:
            st.error("Provide table name and columns definition.")
        else:
            res = _run_sql(
                f"IF OBJECT_ID('{ddl_table.split('.')[-1]}','U') IS NULL CREATE TABLE {ddl_table} ({ddl_cols});"
            )
            if res.get("error"):
                st.error(res["error"])
            else:
                st.success("Table ensured.")
    st.divider()
    st.markdown("### Safety Notes")
    st.info("Admin operations are minimally validated. Use caution in shared or production environments.")
