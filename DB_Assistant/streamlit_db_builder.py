import streamlit as st
from pathlib import Path
from DB_Assistant.core.schema_parser import load_schema, dump_schema
from DB_Assistant.core.validators import validate_spec
from DB_Assistant.core.migration_planner import plan_migration
from DB_Assistant.core.ddl_renderer import operations_to_sql
from DB_Assistant.agents.design_agent import draft_schema_from_prompt

st.set_page_config(page_title="DB Builder", layout="wide")
st.title("DB Builder – Phase 0")

st.sidebar.header("Steps")
step = st.sidebar.radio("Navigate", ["Prompt", "Plan", "Apply"], index=0)

state = st.session_state

if step == "Prompt":
    st.subheader("1. Natural Language → Draft Schema")
    prompt = st.text_area("Describe the analytical star schema you want", height=140, value=state.get("prompt", "Star schema for loan payments and companies"))
    use_llm = st.checkbox("Use LLM (Azure OpenAI)", value=True)
    if st.button("Generate Draft"):
        spec = draft_schema_from_prompt(prompt, use_llm=use_llm)
        state["prompt"] = prompt
        state["draft_spec"] = spec.dict()
        st.success("Draft generated.")
    if "draft_spec" in state:
        st.code(state["draft_spec"], language="json")
        if st.button("Persist Draft YAML"):
            from DB_Assistant.core.schema_models import SchemaSpec
            spec_obj = SchemaSpec.parse_obj(state["draft_spec"])
            out_path = Path("DB_Assistant/schema_specs/proposals/streamlit_draft.yml")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            dump_schema(spec_obj, out_path)
            st.info(f"Saved to {out_path}")

elif step == "Plan":
    st.subheader("2. Plan Migration")
    target_file = st.text_input("Target schema YAML", "DB_Assistant/templates/star_loans_risk.yml")
    current_file = st.text_input("Current schema YAML (optional)", "")
    if st.button("Compute Plan"):
        from DB_Assistant.core.schema_models import SchemaSpec
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
    if "plan_sql" in state:
        st.download_button("Download Plan SQL", data=state["plan_sql"], file_name="migration_plan.sql", mime="text/sql")

elif step == "Apply":
    st.subheader("3. Apply Plan (Sequential)")
    if "plan_sql" not in state:
        st.warning("Generate a plan first in the Plan step.")
    else:
        dry_run = st.checkbox("Dry Run", value=True)
        if st.button("Execute Plan"):
            sql = state["plan_sql"]
            if dry_run:
                st.info("Dry run – SQL not executed.")
                st.code(sql, language="sql")
            else:
                # Attempt execution
                try:
                    import os, pyodbc  # type: ignore
                    server = os.getenv("DB_SERVER")
                    database = os.getenv("DB_DATABASE")
                    user = os.getenv("DB_USER")
                    password = os.getenv("DB_PASSWORD")
                    if not all([server, database, user, password]):
                        raise RuntimeError("Missing DB_SERVER/DB_DATABASE/DB_USER/DB_PASSWORD env vars.")
                    conn_str = (
                        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};"
                        f"UID={user};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
                    )
                    conn = pyodbc.connect(conn_str)
                    cur = conn.cursor()
                    for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
                        cur.execute(stmt)
                    conn.commit()
                    cur.close(); conn.close()
                    st.success("Apply complete.")
                except Exception as e:  # noqa: BLE001
                    st.error(f"Execution failed: {e}")
