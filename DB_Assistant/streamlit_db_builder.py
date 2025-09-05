import streamlit as st
from pathlib import Path
import sys, os, json, textwrap
from typing import List, Dict, Any

# Ensure repository root is on sys.path; this file lives in <repo>/DB_Assistant/ so root = parent of its directory.
_here = Path(__file__).resolve()
_root = _here.parent.parent  # repo root
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from DB_Assistant.core.schema_parser import load_schema, dump_schema  # noqa: E402
from DB_Assistant.core.validators import validate_spec  # noqa: E402
from DB_Assistant.core.migration_planner import plan_migration  # noqa: E402
from DB_Assistant.core.ddl_renderer import operations_to_sql  # noqa: E402
from DB_Assistant.agents.design_agent import draft_schema_from_prompt  # noqa: E402

try:
    from agents_nl2sql.graph import build as build_graph  # type: ignore
    from agents_nl2sql.state import GraphState, Flags  # type: ignore
    _HAS_ORCHESTRATE = True
except Exception:  # noqa: BLE001
    _HAS_ORCHESTRATE = False


def _connect(db: str | None = None, use_master: bool = False):
    """Create a pyodbc connection using env vars (same pattern as CLI). Return None if not configured."""
    import pyodbc  # type: ignore
    server = os.getenv("DB_SERVER")
    database = db or os.getenv("DB_DATABASE")
    if use_master:
        database = "master"
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    if not all([server, database, user, password]):
        return None
    cs = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};"\
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
        if cur.description:  # SELECT or returning rows
            cols = [c[0] for c in cur.description]
            rows = cur.fetchall()
            if limit:
                rows = rows[:limit]
            data = [dict(zip(cols, r)) for r in rows]
            return {"columns": cols, "rows": data, "row_count": len(data)}
        else:
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
        schema = 'dbo'
        name = table
    cur.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=? AND TABLE_NAME=?
        ORDER BY ORDINAL_POSITION
    """, (schema, name))
    cols = [
        {"column": r[0], "type": r[1], "nullable": r[2], "length": r[3]} for r in cur.fetchall()
    ]
    cur.close(); conn.close()
    return cols


def _orchestrate_nl(query: str, execute: bool) -> Dict[str, Any]:
    if not _HAS_ORCHESTRATE:
        return {"error": "LangGraph orchestration components not available."}
    try:
        graph = build_graph()
        flags = Flags(no_exec=not execute, explain_only=False, no_reasoning=False, refresh_schema=False)
        state = GraphState(user_query=query, flags=flags)
        res = graph.invoke(state)
        # Normalize dictionary shape
        if not isinstance(res, dict):
            res = res.__dict__  # type: ignore
        # Trim rows sample
        exec_res = res.get("execution_result") or {}
        rows = []
        if isinstance(exec_res, dict):
            rows = exec_res.get("rows") or []
        else:
            rows = getattr(exec_res, "rows", []) or []
        payload = {
            "intent": str(res.get("intent_entities")),
            "reasoning": res.get("reasoning"),
            "sql_raw": res.get("sql_raw"),
            "sql_sanitized": res.get("sql_sanitized"),
            "rows": rows[:200],
            "row_count": len(rows),
            "errors": res.get("errors", []),
            "token_usage": res.get("token_usage", {}),
        }
        return payload
    except Exception as e:  # noqa: BLE001
        return {"error": f"Orchestration failed: {e}"}

st.set_page_config(page_title="DB Assistant", layout="wide")
st.title("DB Assistant – Unified Admin & NL2SQL Console")

st.sidebar.header("Navigation")
pages = [
    "Prompt", "Plan", "Apply", "Explore", "Query Console", "Orchestrate", "Admin"
]
page = st.sidebar.radio("Go to", pages, index=0)
state = st.session_state

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
        # Pydantic v2: use model_dump for serialization
        state["draft_spec"] = spec.model_dump()
        st.success("Draft generated.")
    if "draft_spec" in state:
        st.code(json.dumps(state["draft_spec"], indent=2), language="json")
        if st.button("Persist Draft YAML"):
            from DB_Assistant.core.schema_models import SchemaSpec
            # Pydantic v2: use model_validate for reconstruction
            spec_obj = SchemaSpec.model_validate(state["draft_spec"])
            out_path = Path("DB_Assistant/schema_specs/proposals/streamlit_draft.yml")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            dump_schema(spec_obj, out_path)
            st.info(f"Saved to {out_path}")

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
                        for row in impact:
                            st.write(row)
                    else:
                        st.info("No column-level impacts detected.")
                except Exception as e:  # noqa: BLE001
                    st.warning(f"Impact analyzer unavailable: {e}")
    if "plan_sql" in state:
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

elif page == "Apply":
    st.subheader("3. Apply Plan (Sequential)")
    if "plan_sql" not in state:
        st.warning("Generate a plan first in the Plan step.")
    else:
        dry_run = st.checkbox("Dry Run", value=True)
        confirm = st.checkbox("I understand this will run DDL against the target database", value=False, disabled=dry_run)
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
                        import pyodbc  # type: ignore
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
                schema, name = (t.split('.', 1) + [None])[:2]
                if name is None:
                    name = t
                    schema = 'dbo'
                res = _run_sql(f"SELECT TOP 25 * FROM {t}")
                if res.get("error"):
                    st.error(res["error"])
                else:
                    st.dataframe(res["rows"])

elif page == "Query Console":
    st.subheader("5. SQL Query Console")
    default_sql = state.get("last_sql", "SELECT TOP 5 * FROM dbo.dim_company;")
    sql_input = st.text_area("SQL", height=180, value=default_sql)
    limit_rows = st.number_input("Client Row Limit (display)", min_value=10, max_value=1000, value=200)
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

elif page == "Orchestrate":
    st.subheader("6. NL → SQL Orchestration")
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
                    st.caption(f"Token usage: prompt={tu.get('prompt')} completion={tu.get('completion')} total={tu.get('total')}")

elif page == "Admin":
    st.subheader("7. Admin Utilities")
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
    ddl_cols = st.text_area("Columns (comma-separated col TYPE)", "id INT PRIMARY KEY, name VARCHAR(50), created_at DATETIME2")
    if st.button("Create Table"):
        if not ddl_table or not ddl_cols:
            st.error("Provide table name and columns definition.")
        else:
            res = _run_sql(f"IF OBJECT_ID('{ddl_table.split('.')[-1]}','U') IS NULL CREATE TABLE {ddl_table} ({ddl_cols});")
            if res.get("error"):
                st.error(res["error"])
            else:
                st.success("Table ensured.")
    st.divider()
    st.markdown("### Safety Notes")
    st.info("Admin operations are minimally validated. Use with caution in shared environments.")
