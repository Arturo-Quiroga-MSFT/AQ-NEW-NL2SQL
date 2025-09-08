"""Simple NL→DDL Admin Console

Purpose: Provide a minimal interface for a DB admin to:
  1. Enter natural language instructions (one or many lines)
  2. Parse into concrete DDL/DML admin actions (create table, add/drop column, drop table, create index, list/describe)
  3. Preview generated SQL statements
  4. (Optionally) execute with risk gating safeguards

Environment variables required:
  DB_SERVER, DB_DATABASE, DB_USER, DB_PASSWORD

Run:
  streamlit run DB_Assistant/streamlit_db_admin_simple.py
"""
from __future__ import annotations
from pathlib import Path
import os, sys, json, re
from typing import List, Dict, Any
import streamlit as st

# --- Path setup & env loading ---
_here = Path(__file__).resolve()
_root = _here.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Load environment variables (first localized DB_Assistant/.env, then fallback to root .env)
_LOADED_ENV_FILES = []
try:  # noqa: SIM105
    from dotenv import load_dotenv  # type: ignore
    local_env = _here.parent / ".env"
    if local_env.exists():
        load_dotenv(local_env)  # do not override existing process env
        _LOADED_ENV_FILES.append(str(local_env))
    # root fallback (won't override already set vars)
    root_env = _root / ".env"
    if root_env.exists():
        load_dotenv(root_env)
        _LOADED_ENV_FILES.append(str(root_env))
except Exception:  # noqa: BLE001
    pass

# Optional star parser (we'll treat star diagnostics as informational, not DDL)
try:  # noqa: SIM105
    from DB_Assistant.star.nl_parser import StarParser  # type: ignore
    _STAR = StarParser()
    _HAS_STAR = True
except Exception:  # noqa: BLE001
    _STAR = None
    _HAS_STAR = False


# ---------------- DB Helpers & NL Integration ----------------
_NL_LOAD_ERROR = None
try:  # New generic NL interpreter (rule-based phase 1)
    from DB_Assistant.nl.classifier import classify as nl_classify, to_sql as nl_to_sql  # type: ignore
    from DB_Assistant.nl.dsl import NLAction as _NLAction, Unknown as _NLUnknown  # type: ignore
    _HAS_NEW_NL = True
except Exception as _e:  # noqa: BLE001
    _HAS_NEW_NL = False
    _NL_LOAD_ERROR = str(_e)
def _connect():
    import pyodbc  # type: ignore
    # Prefer DB_*; fallback to legacy AZURE_SQL_* to remain compatible with root .env
    server = os.getenv("DB_SERVER") or os.getenv("AZURE_SQL_SERVER")
    database = os.getenv("DB_DATABASE") or os.getenv("AZURE_SQL_DB")
    user = os.getenv("DB_USER") or os.getenv("AZURE_SQL_USER")
    password = os.getenv("DB_PASSWORD") or os.getenv("AZURE_SQL_PASSWORD")
    if not all([server, database, user, password]):
        return None  # caller will infer missing vars
    cs = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )
    try:
        return pyodbc.connect(cs)
    except Exception:
        return None


def _connection_diagnostics() -> Dict[str, Any]:
    """Return structured diagnostics explaining why a connection might fail."""
    report: Dict[str, Any] = {"stage": "init"}
    missing = []
    server = os.getenv("DB_SERVER") or os.getenv("AZURE_SQL_SERVER")
    database = os.getenv("DB_DATABASE") or os.getenv("AZURE_SQL_DB")
    user = os.getenv("DB_USER") or os.getenv("AZURE_SQL_USER")
    password = os.getenv("DB_PASSWORD") or os.getenv("AZURE_SQL_PASSWORD")
    for name, val in [("server", server), ("database", database), ("user", user), ("password", password)]:
        if not val:
            missing.append(name)
    if missing:
        report["stage"] = "missing_env"
        report["missing"] = missing
        return report
    import pyodbc  # type: ignore
    # First try master to isolate DB existence errors
    master_cs = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE=master;"
        f"UID={user};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=15;"
    )
    try:
        master_conn = pyodbc.connect(master_cs)
        report["master_connect"] = "ok"
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        report["stage"] = "master_connect_failed"
        report["error"] = msg
        if "Login failed" in msg:
            report["hint"] = "Check username/password or ensure SQL Authentication is enabled."
        elif "cannot open server" in msg.lower():
            report["hint"] = "Verify server DNS / firewall (port 1433) and driver installation."
        elif "driver" in msg.lower():
            report["hint"] = "Install msodbcsql18 (macOS: brew install --cask msodbcsql18)."
        return report
    try:
        cur = master_conn.cursor()
        cur.execute("SELECT name FROM sys.databases WHERE name=?", database)
        exists = cur.fetchone() is not None
        report["database_exists"] = exists
        cur.close(); master_conn.close()
    except Exception as e:  # noqa: BLE001
        report["stage"] = "metadata_check_failed"
        report["error"] = str(e)
        return report
    if not report.get("database_exists"):
        report["stage"] = "db_missing"
        report["hint"] = f"Create database [{database}] or change DB_DATABASE."
        return report
    # Attempt final connect to target DB
    target_cs = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=15;"
    )
    try:
        t_conn = pyodbc.connect(target_cs)
        t_conn.close()
        report["stage"] = "success"
    except Exception as e:  # noqa: BLE001
        report["stage"] = "target_connect_failed"
        report["error"] = str(e)
    return report


def _run_sql(sql: str) -> Dict[str, Any]:
    conn = _connect()
    if conn is None:
        return {"error": "DB connection failed (check environment variables)."}
    cur = conn.cursor()
    try:
        cur.execute(sql)
        if cur.description:
            cols = [c[0] for c in cur.description]
            rows = cur.fetchall()
            data = [dict(zip(cols, r)) for r in rows]
            return {"rows": data, "row_count": len(data)}
        conn.commit()
        return {"message": "Statement executed", "row_count": cur.rowcount}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
    finally:
        cur.close(); conn.close()


# --------- Heuristic Parsing (single line) ---------
_SIMPLE_TYPES = [
    "INT", "BIGINT", "SMALLINT", "TINYINT", "DECIMAL(18,2)", "DECIMAL(19,4)", "DATE", "DATETIME2",
    "VARCHAR(20)", "VARCHAR(40)", "VARCHAR(50)", "VARCHAR(60)", "VARCHAR(100)", "NVARCHAR(100)"
]

def _risk(sql: str) -> str:
    u = sql.upper()
    if any(tok in u for tok in ["DROP TABLE", "TRUNCATE TABLE"]):
        return "high"
    if "DROP COLUMN" in u or ("ALTER TABLE" in u and ("ALTER COLUMN" in u or "DROP" in u)):
        return "medium"
    return "low"


def _legacy_parse_line(line: str) -> List[Dict[str, Any]]:  # retained for fallback
    text = line.strip().lower()
    if not text:
        return []
    return [{"action": "unknown", "sql": line, "risk": _risk(line), "note": "Legacy fallback"}]


def _parse_line(line: str) -> List[Dict[str, Any]]:
    raw = line.strip()
    if not raw:
        return []
    if not _HAS_NEW_NL:
        return _legacy_parse_line(raw)
    try:
        result = nl_classify(raw)
        from DB_Assistant.nl.dsl import NLAction as __A, Unknown as __U  # type: ignore
        if isinstance(result, __U):
            if raw.lower().startswith("select "):
                return [{"action": "select", "sql": raw, "risk": "low", "note": "Ad-hoc select"}]
            return [{"action": "unknown", "sql": raw, "risk": _risk(raw), "note": "Unparsed (new NL)"}]
        if isinstance(result, __A):
            sql = nl_to_sql(result)
            note_map = {
                "list_tables": "Schema overview",
                "describe_table": f"Describe {result.table}",
                "row_count": f"Row count {result.table}",
                "create_table": f"Create {result.table}",
                "drop_table": f"Drop {result.table}",
                "add_column": f"Add column to {result.table}",
                "drop_column": f"Drop column from {result.table}",
                "create_index": f"Create index on {result.table}",
                "star_overview": "Star classification (diagnostic)",
            }
            action_id = result.intent
            entry: Dict[str, Any] = {
                "action": action_id,
                "risk": result.risk,
                "note": note_map.get(action_id, action_id)
            }
            if sql:
                entry["sql"] = sql
            return [entry]
        return _legacy_parse_line(raw)
    except Exception:  # noqa: BLE001
        return _legacy_parse_line(raw)


def _parse_multi(text: str) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    # split by newlines or semicolons
    parts = [p.strip() for p in re.split(r"[\n;]", text) if p.strip()]
    for p in parts:
        actions.extend(_parse_line(p))
    return actions


def _star_execute(action: Dict[str, Any]) -> Dict[str, Any]:
    if action.get('action') != 'star_overview' or not _HAS_STAR:
        return {"error": "Unsupported star diagnostic"}
    try:
        from DB_Assistant.star.introspection import build_star_overview  # type: ignore
        conn = _connect()
        if conn is None:
            return {"error": "No DB connection"}
        data = build_star_overview(conn)
        conn.close()
        return {"rows": data, "row_count": len(data)}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


# ------------- UI -------------
st.set_page_config(page_title="DB_ASSISTANT", layout="wide")
st.title("DB_ASSISTANT")

# Connection status banner (supports DB_* or AZURE_SQL_* fallbacks)
_server_env = os.getenv("DB_SERVER") or os.getenv("AZURE_SQL_SERVER")
_db_env = os.getenv("DB_DATABASE") or os.getenv("AZURE_SQL_DB")
_user_env = os.getenv("DB_USER") or os.getenv("AZURE_SQL_USER")
_pwd_env = os.getenv("DB_PASSWORD") or os.getenv("AZURE_SQL_PASSWORD")
_env_ok = all([_server_env, _db_env, _user_env, _pwd_env])
if not _env_ok:
    st.warning("Database environment variables missing (need DB_* or AZURE_SQL_* quartet). Read-only parsing still works.")
    with st.expander("Environment diagnostics", expanded=False):
        # show both naming styles
        rows = []
        for label, val in [
            ("DB_SERVER|AZURE_SQL_SERVER", _server_env),
            ("DB_DATABASE|AZURE_SQL_DB", _db_env),
            ("DB_USER|AZURE_SQL_USER", _user_env),
            ("DB_PASSWORD|AZURE_SQL_PASSWORD", '***' if _pwd_env else None),
        ]:
            rows.append({
                "vars": label,
                "set": bool(val),
                "value_preview": (val[:40] + '…') if (val and len(val) > 40) else val
            })
        st.table(rows)
        st.caption("Export either naming style, e.g. DB_SERVER / DB_DATABASE / DB_USER / DB_PASSWORD")
        if _LOADED_ENV_FILES:
            st.caption("Loaded env file(s): " + ", ".join(_LOADED_ENV_FILES))
        else:
            st.caption("No .env files loaded automatically (install python-dotenv if needed).")
        st.code(
            """export DB_SERVER=yourserver.database.windows.net
export DB_DATABASE=Multi_Dimensional_modeling
export DB_USER=your_user
export DB_PASSWORD=your_password""",
            language="bash",
        )
else:
    try:
        _probe = _connect()
        if _probe is None:
            st.error("Connection attempt failed (credentials or driver issue).")
        else:
            st.success(f"Connected to DB '{_db_env}' on server '{_server_env}'.")
            _probe.close()
    except Exception as _e:  # noqa: BLE001
        st.error(f"Connection attempt failed: {_e}")

# Show NL interpreter load status
with st.expander("NL Interpreter Status", expanded=not _HAS_NEW_NL):
    if _HAS_NEW_NL:
        st.success("Rule-based NL intent classifier loaded.")
        st.caption("Source: DB_Assistant/nl/*. Uses intents.yaml patterns. Next phases: embeddings & LLM fallback.")
    else:
        st.error("NL interpreter failed to load – falling back to legacy unknown parser.")
        if _NL_LOAD_ERROR:
            st.code(_NL_LOAD_ERROR, language='text')
        st.caption("Install dependencies (pip install -r requirements.txt) and ensure intents.yaml is readable.")
        import sys as _sys
        from pathlib import Path as _P
        nl_dir = _P(__file__).parent / 'nl'
        st.markdown("**Diagnostics:**")
        st.write({
            "pythonpath_len": len(_sys.path),
            "nl_dir_exists": nl_dir.exists(),
            "nl_dir_contents": [p.name for p in nl_dir.glob('*')][:20]
        })

# Manual test connection on demand (even if vars missing to show failure reason)
col_tst, col_sp = st.columns([1,5])
if col_tst.button("Test Connection"):
    diag = _connection_diagnostics()
    stage = diag.get("stage")
    if stage == "success":
        st.success("Connection successful to target database.")
    elif stage == "missing_env":
        st.error(f"Missing environment variables: {', '.join(diag.get('missing', []))}")
    elif stage == "db_missing":
        st.error("Target database does not exist.")
        if diag.get("hint"):
            st.caption(diag["hint"])
        target_db = os.getenv('DB_DATABASE') or os.getenv('AZURE_SQL_DB') or 'YOUR_DB'
        create_sql = f"CREATE DATABASE [{target_db}]"
        st.code(create_sql, language='sql')
        if st.button(f"Attempt to create database {target_db}"):
            import pyodbc  # type: ignore
            # Reconnect to master and attempt creation
            server = os.getenv("DB_SERVER") or os.getenv("AZURE_SQL_SERVER")
            user = os.getenv("DB_USER") or os.getenv("AZURE_SQL_USER")
            password = os.getenv("DB_PASSWORD") or os.getenv("AZURE_SQL_PASSWORD")
            if not all([server, user, password]):
                st.error("Cannot create database: missing server/user/password env vars.")
            else:
                master_cs = (
                    f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE=master;"
                    f"UID={user};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=15;"
                )
                try:
                    conn = pyodbc.connect(master_cs)
                    cur = conn.cursor()
                    cur.execute(f"IF DB_ID(?) IS NULL EXEC('CREATE DATABASE [{target_db}]')", target_db)
                    cur.commit()
                    cur.close(); conn.close()
                    st.success(f"Database {target_db} created or already existed. Re-run Test Connection.")
                except Exception as ce:  # noqa: BLE001
                    st.error(f"Create database failed: {ce}")
    else:
        st.error(f"Connection stage: {stage}")
        if diag.get("error"):
            st.code(diag["error"], language='text')
        if diag.get("hint"):
            st.caption(diag["hint"])
    with st.expander("Raw diagnostics"):
        st.json(diag)

st.markdown("""Enter one or more natural language admin instructions. Each line (or semicolon separated) is parsed independently.""")

# --- Sample Queries Palette (interactive buttons) ---
sample_queries = [
    "create table dbo.demo_payments with columns id int, amount decimal(18,2), created_at datetime2",
    "add column notes varchar(100) to dbo.demo_payments",
    "drop column notes from dbo.demo_payments",
    "create index on dbo.demo_payments(id, created_at)",
    "drop table dbo.demo_payments",
    "list tables",
    "describe table dbo.dim_company",
    "row count for fact_loan_payments",
    "list star overview"
]

st.caption("Click to insert a sample (first click replaces, shift-click or ⌘/Ctrl-click appends).")
btn_cols = st.columns(3)
append_mode = st.checkbox("Append mode (always append instead of replace)", value=False)
for i, q in enumerate(sample_queries):
    col = btn_cols[i % 3]
    if col.button(q, key=f"sample_q_{i}"):
        existing = st.session_state.get('draft_instructions', '')
        # Detect modified click (cannot directly capture shift/meta; allow manual append toggle)
        if append_mode and existing.strip():
            new_val = existing.rstrip() + ('\n' if not existing.endswith('\n') else '') + q
        else:
            new_val = q
        st.session_state['draft_instructions'] = new_val

# Use session_state to persist text area edits when buttons modify it
default_placeholder = "create table dbo.demo_dim with columns id int, name varchar(50)\nadd column created_at datetime2 to dbo.demo_dim"
initial_text = st.session_state.get('draft_instructions', default_placeholder)
text_input = st.text_area("Instructions", value=initial_text, height=180, key="instructions_area")
st.session_state['draft_instructions'] = text_input

col_parse, col_clear = st.columns([1,1])
if col_parse.button("Parse"):
    st.session_state['parsed_actions'] = _parse_multi(text_input)
if col_clear.button("Clear"):
    st.session_state.pop('parsed_actions', None)
    st.experimental_rerun()

actions = st.session_state.get('parsed_actions', [])
if actions:
    st.markdown("### Parsed Actions")
    exec_keys = []
    # Ensure result cache exists
    if 'action_results' not in st.session_state:
        st.session_state['action_results'] = {}
    action_results = st.session_state['action_results']

    for idx, act in enumerate(actions):
        with st.container():
            cols = st.columns([2,1,2,5,1,1])
            cols[0].markdown(f"**Action:** {act.get('action')}")
            cols[1].markdown(f"Risk: `{act.get('risk')}`")
            cols[2].markdown(act.get('note',''))
            has_sql = bool(act.get('sql'))
            if has_sql:
                with cols[3]:
                    st.code(act['sql'], language='sql')
            else:
                with cols[3]:
                    st.caption("(No direct SQL – may be diagnostic or unknown)")
            # Selection checkbox only for executable SQL or star diagnostic
            selectable = has_sql or act.get('action') == 'star_overview'
            if selectable:
                exec_flag = cols[4].checkbox("Exec", value=False, key=f"act_exec_{idx}")
                if exec_flag:
                    exec_keys.append(idx)
            # Inline run button (non-high risk auto allowed; high risk requires confirmation checkbox)
            run_clicked = False
            if selectable:
                if act.get('risk') == 'high':
                    confirm = cols[5].checkbox("Confirm", value=False, key=f"inline_confirm_{idx}")
                    if cols[5].button("Run", key=f"inline_run_{idx}", help="Execute this high-risk action only after confirming"):
                        if confirm:
                            run_clicked = True
                        else:
                            st.warning("Confirm checkbox required for high risk action.")
                else:
                    if cols[5].button("Run", key=f"inline_run_{idx}"):
                        run_clicked = True

            if run_clicked:
                if act.get('action') == 'star_overview':
                    res = _star_execute(act)
                elif act.get('sql'):
                    res = _run_sql(act['sql'])
                else:
                    res = {"error": "No executable content"}
                action_results[idx] = res

            # Display inline result if present
            if idx in action_results:
                res = action_results[idx]
                with st.expander(f"Inline Result #{idx+1}", expanded=True):
                    if 'error' in res:
                        st.error(res['error'])
                    elif 'rows' in res:
                        st.dataframe(res['rows'])
                        st.caption(f"Row count: {res.get('row_count')}")
                        # CSV download for inline result
                        import pandas as _pd  # type: ignore
                        try:
                            df = _pd.DataFrame(res['rows'])
                            csv_bytes = df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="Download CSV",
                                data=csv_bytes,
                                file_name=f"action_{idx+1}_result.csv",
                                mime='text/csv',
                                key=f"dl_inline_{idx}"
                            )
                        except Exception as _csv_err:  # noqa: BLE001
                            st.caption(f"CSV generation error: {_csv_err}")
                    else:
                        st.success(res.get('message','Done'))
        with st.expander(f"Details #{idx+1}"):
            st.json(act)
        st.divider()
    # Continuation / execution panel
    st.markdown("### Next Step: Review & Execute")
    # Risk summary
    risk_counts = {"low":0, "medium":0, "high":0}
    exec_candidates = 0
    for a in actions:
        if a.get('risk') in risk_counts:
            risk_counts[a['risk']] += 1
        if a.get('sql') or a.get('action') == 'star_overview':
            exec_candidates += 1
    cols_summary = st.columns(4)
    cols_summary[0].write({"total_actions": len(actions)})
    cols_summary[1].write({"risk": risk_counts})
    cols_summary[2].write({"executable": exec_candidates})
    cols_summary[3].write({"selected": len(exec_keys)})

    if exec_candidates and not exec_keys:
        st.info("Select the actions you want to execute using the Exec checkboxes on the right.")

    # Aggregated SQL preview (only for selected with SQL)
    selected_sql = [actions[i]['sql'] for i in exec_keys if actions[i].get('sql')]
    if selected_sql:
        combined_sql = '\n'.join(selected_sql)
        with st.expander(f"Combined SQL for {len(selected_sql)} selected action(s)"):
            st.code(combined_sql, language='sql')
    else:
        st.caption("(No SQL selected yet)")

    # Execute button (always shown if any executable exists)
    if exec_candidates:
        if st.button("Execute Selected"):
            if not exec_keys:
                # Auto-select convenience if exactly one safe candidate
                candidate_indices = [i for i,a in enumerate(actions) if (a.get('sql') or a.get('action')=='star_overview')]
                if len(candidate_indices) == 1 and actions[candidate_indices[0]].get('risk') != 'high':
                    exec_keys = candidate_indices
                    st.info("Auto-selected the only executable safe action.")
                else:
                    st.warning("No actions selected for execution (tick the Exec checkbox).")
            if exec_keys:
                results = []
                debug_events = []
                for k in exec_keys:
                    act = actions[k]
                    dbg_entry = {"index": k+1, "action": act.get('action'), "risk": act.get('risk')}
                    if act.get('action') == 'star_overview':
                        res = _star_execute(act)
                        dbg_entry['mode'] = 'star_overview'
                    elif act.get('sql'):
                        if act.get('risk') == 'high':
                            confirm = st.checkbox(f"Confirm HIGH risk action #{k+1} ({act.get('action')})", key=f"confirm_high_{k}")
                            dbg_entry['confirm_needed'] = True
                            dbg_entry['confirm_value'] = confirm
                            if not confirm:
                                res = {"error": "High risk action not confirmed"}
                                results.append({"action_index": k+1, "action": act.get('action'), "result": res})
                                debug_events.append(dbg_entry)
                                continue
                        res = _run_sql(act['sql'])
                        dbg_entry['mode'] = 'sql'
                        dbg_entry['sql'] = act.get('sql')
                    else:
                        res = {"error": "No executable content"}
                        dbg_entry['mode'] = 'none'
                    dbg_entry['result_keys'] = list(res.keys())
                    results.append({"action_index": k+1, "action": act.get('action'), "result": res})
                    debug_events.append(dbg_entry)
                st.session_state['execution_results'] = results
                st.session_state['execution_debug'] = debug_events

    exec_results = st.session_state.get('execution_results')
    if exec_results:
        st.markdown("### Execution Results")
        for r in exec_results:
            st.markdown(f"**Action #{r['action_index']} – {r.get('action')}**")
            res = r.get('result', {})
            if 'error' in res:
                st.error(res['error'])
            elif 'rows' in res:
                st.dataframe(res['rows'])
                st.caption(f"Row count: {res.get('row_count')}")
                import pandas as _pd  # type: ignore
                try:
                    df = _pd.DataFrame(res['rows'])
                    csv_bytes = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label=f"Download CSV (Action {r['action_index']})",
                        data=csv_bytes,
                        file_name=f"action_{r['action_index']}_result.csv",
                        mime='text/csv',
                        key=f"dl_batch_{r['action_index']}"
                    )
                except Exception as _csv_err:  # noqa: BLE001
                    st.caption(f"CSV generation error: {_csv_err}")
            else:
                st.success(res.get('message', 'Done'))
            st.divider()
        with st.expander("Execution Debug Trace"):
            st.json(st.session_state.get('execution_debug', []))
else:
    st.info("No parsed actions yet – enter instructions and press Parse.")
