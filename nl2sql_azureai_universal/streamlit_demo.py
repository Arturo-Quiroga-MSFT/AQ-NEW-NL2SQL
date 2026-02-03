"""Streamlit demo for the NL2SQL Azure AI Universal pipeline.

Run this with:
    streamlit run nl2sql_azureai_universal/streamlit_demo.py

This lightweight UI wires into the public functions in `nl2sql_main.py` and
`schema_reader.py` to showcase intent extraction, SQL generation, sanitization,
execution and token usage.
"""
from __future__ import annotations

import importlib
import streamlit as st
import sys
from pathlib import Path

# Ensure repository root is on sys.path so package imports work when Streamlit
# runs the script from a different working directory or with a different import context.
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from typing import Optional
import json

# Lazily import heavy modules to avoid side-effects at import time (nl2sql_main checks
# for environment variables when imported which would raise during a dry import).
_nl2sql_module = None
_schema_module = None


def _import_nl2sql_module():
    global _nl2sql_module
    if _nl2sql_module is None:
        try:
            _nl2sql_module = importlib.import_module("nl2sql_azureai_universal.nl2sql_main")
        except Exception as e:  # capture ValueError/ImportError etc and return the exception to surface later
            _nl2sql_module = e
    return _nl2sql_module


def _import_schema_module():
    global _schema_module
    if _schema_module is None:
        try:
            _schema_module = importlib.import_module("nl2sql_azureai_universal.schema_reader")
        except Exception as e:
            _schema_module = e
    return _schema_module


st.set_page_config(page_title="NL→SQL Demo", layout="wide")


def show_schema_sidebar():
    st.sidebar.header("Database Schema")
    try:
        schema_mod = _import_schema_module()
        if isinstance(schema_mod, Exception):
            raise schema_mod
        meta = schema_mod.get_schema_metadata_from_cache()
        db = meta.get("database_name")
        server = meta.get("server")
        ts = meta.get("timestamp")
        st.sidebar.write(f"DB: {db} on {server}")
        tables = sorted(list(meta.get("tables", {}).keys()))
        sel = st.sidebar.selectbox("Select table to preview", ["-- none --"] + tables)
        if sel and sel != "-- none --":
            cols = meta.get("tables", {}).get(sel, [])
            st.sidebar.write(f"Columns ({len(cols)}):")
            for c in cols:
                s = f"- {c['name']} ({c.get('type')})"
                if c.get("is_primary_key"):
                    s += " [PK]"
                st.sidebar.text(s)
    except Exception as e:
        st.sidebar.error(f"Failed to load schema: {e}")


def main():
    st.title("NL → SQL (Azure AI) — Interactive Demo")

    show_schema_sidebar()

    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Natural language query")
        query = st.text_area("Enter a question", height=140, value="Show me total sales by country for 2023")

        st.subheader("Options")
        execute = st.checkbox("Execute generated SQL", value=False)
        show_raw = st.checkbox("Show raw agent outputs (intent & raw SQL)", value=True)
        reset_tokens = st.button("Reset token usage")

        if reset_tokens:
            nl2sql_mod = _import_nl2sql_module()
            if isinstance(nl2sql_mod, Exception):
                st.error(f"Cannot reset token usage: {nl2sql_mod}")
            else:
                nl2sql_mod.reset_token_usage()
            st.success("Token usage reset")

        if st.button("Run"):
            with st.spinner("Running pipeline..."):
                try:
                    nl2sql_mod = _import_nl2sql_module()
                    if isinstance(nl2sql_mod, Exception):
                        raise nl2sql_mod
                    resp = nl2sql_mod.process_nl_query(query, execute=execute)
                except Exception as e:
                    st.error(f"Pipeline failed: {e}")
                    resp = None

            # Persist the last run response so other panels (results) can read it
            st.session_state["last_run_resp"] = resp

            if resp:
                st.success("Pipeline completed")
                if show_raw:
                    st.subheader("Intent / Entities (raw)")
                    st.code(resp.get("intent") or "{}", language="json")

                    st.subheader("Generated SQL (raw)")
                    st.code(resp.get("sql_raw") or "", language="sql")

                st.subheader("Sanitized SQL")
                st.code(resp.get("sql") or "", language="sql")

                # Execution results are also displayed in the right-hand panel below
                if execute:
                    results = resp.get("results") or {}
                    if not results.get("success"):
                        st.error(f"Execution error: {results.get('error')}")

                st.subheader("Token Usage")
                tu = resp.get("token_usage") or (nl2sql_mod.get_token_usage() if not isinstance(nl2sql_mod, Exception) else {})
                st.write(tu)

                st.subheader("Run Metadata")
                st.json({k: v for k, v in resp.items() if k not in ("results",)})

    with col2:
        st.subheader("Model / Schema Context Preview")
        try:
            schema_mod = _import_schema_module()
            if isinstance(schema_mod, Exception):
                raise schema_mod
            ctx = schema_mod.get_sql_database_schema_context()
            # show only first N chars but with expanders for full
            st.text(ctx[:2000])
            with st.expander("Show full schema context"):
                st.code(ctx)
        except Exception as e:
            st.error(f"Failed to render schema context: {e}")

        st.subheader("Developer / Logs")
        st.write("This panel shows helpful debug info generated during runs (if any).")

        # Dedicated SQL Results panel
        st.subheader("SQL Results")
        try:
            # Use resp from top-level run if present in session state; otherwise try to show nothing
            resp_obj = None
            # When the app runs, resp is in local scope; persist it into session_state for the results panel
            if "last_run_resp" in st.session_state:
                resp_obj = st.session_state["last_run_resp"]
            else:
                # attempt to capture resp variable from locals (only works in same run)
                resp_obj = None

            if resp_obj:
                results = resp_obj.get("results") or {}
                if results.get("success"):
                    rows = results.get("rows", [])
                    with st.expander("Show results table", expanded=True):
                        if rows:
                            st.dataframe(rows)
                        else:
                            st.info("Query executed successfully but returned no rows")
                    with st.expander("Show raw results JSON"):
                        st.json(results)
                else:
                    st.info("No execution results available for the last run.")
            else:
                st.info("No run results available yet. Run a query with 'Execute generated SQL' enabled to see results here.")
        except Exception as e:
            st.error(f"Failed to render SQL results: {e}")


if __name__ == "__main__":
    main()
