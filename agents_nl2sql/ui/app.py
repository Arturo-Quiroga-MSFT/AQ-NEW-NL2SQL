"""
Streamlit UI for the Agents NL2SQL Demo.

This UI orchestrates the agent-based pipeline in agents_nl2sql, allowing users to:
- Enter natural language questions
- See agent state transitions and reasoning
- View generated SQL and results
- Refresh schema cache
- Download results
"""
import os
import sys
import streamlit as st
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Ensure repo root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv()

# Import agent pipeline helpers
from agents_nl2sql.run_demo import main as agent_main
from agents_nl2sql.nodes import schema_ctx
from agents_nl2sql.state import Flags, GraphState

st.set_page_config(
    page_title="Agents NL2SQL Demo",
    page_icon="🤖",
    layout="wide",
)

st.title("Agents NL2SQL Demo UI")
st.caption("Natural Language → Agents → SQL → Results")

# Sidebar: schema cache refresh
with st.sidebar:
    st.header("Schema Cache")
    if st.button("🔄 Refresh schema cache"):
        try:
            from agents_nl2sql.tools.schema_tools import refresh_schema_cache
            path = refresh_schema_cache()
            st.success(f"Schema cache refreshed: {path}")
        except Exception as e:
            st.error(f"Failed to refresh schema cache: {e}")
    with st.expander("Current schema context (preview)", expanded=False):
        from agents_nl2sql.tools.schema_tools import get_schema_context
        ctx = get_schema_context(0)
        st.code(ctx[:4000], language="text")

# Main UI
query = st.text_area(
    "Enter your question",
    value=st.session_state.get("input_query", "Show the 10 most recent loans"),
    height=80,
)

run_clicked = st.button("Run", type="primary")
no_exec = st.toggle("Skip exec", value=False, help="Generate SQL but do not run it", key="skip_exec_toggle")
explain_only = st.toggle("Explain-only", value=False, help="Show intent and reasoning only; skip SQL generation and execution", key="explain_only_toggle")
no_reasoning = st.toggle("No reasoning", value=False, help="Skip the reasoning/plan step", key="no_reasoning_toggle")

if run_clicked:
    # Prepare agent state and flags
    flags = Flags(
        no_exec=no_exec,
        no_reasoning=no_reasoning,
        explain_only=explain_only,
        refresh_schema=False,
    )
    state = GraphState(user_query=query, flags=flags)
    # Run schema context node (loads schema, may use cache)
    with st.spinner("Building schema context..."):
        state = schema_ctx.run(state)
    st.markdown("### Schema Context (truncated)")
    st.code(state.schema_context[:2000], language="text")
    # Show intent/entities, reasoning, SQL, results, etc. (simulate agent pipeline)
    # For demo: show state object as dict
    st.markdown("### Agent State (Debug)")
    st.json(state.dict())
    # TODO: Expand to run full agent pipeline and display each step, results, and allow downloads
