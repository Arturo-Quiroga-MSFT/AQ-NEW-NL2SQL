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
import time
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


# --- Sample questions for quick access ---
SAMPLE_QUESTIONS = [
    "Show the 10 most recent loans by OriginationDate.",
    "For each company with loans, compute total principal amount; show the top 20 companies by total principal.",
    "For each region, list the top 5 companies by total principal amount.",
    "List all currencies and their symbols available in the database.",
    "Identify loans with upcoming covenant tests in the next 30 days.",
    "For each loan, compute the remaining balance and show the top 10 by balance.",
    "By region, list the top 10 companies by total outstanding loan amount.",
    "Show all companies with more than 3 active loans.",
    "List all collateral items valued above 1,000,000.",
    "For each customer profile, show the average loan interest rate.",
    "Show the total number of loans and total principal by risk category.",
    "List the 5 most common loan purposes and their total amounts.",
    "For each region, show the average loan-to-value ratio.",
    "Find all loans with overdue payments and their associated companies.",
    "Show the distribution of loan amounts by currency.",
    "List all companies in the Americas region with loans above 5,000,000.",
    "For each company, list the most recent loan and its amount.",
    "Show all loans with fixed interest rates above 7%.",
    "List the top 10 customers by total collateral value.",
    "For each region, show the number of loans and the sum of principal amounts.",
    "Show all companies with ESGScore above 80.",
    "List all loans originated in the last 12 months.",
    "Show the average interest rate by industry.",
    "List all payment events for overdue loans.",
    "Show the top 5 regions by total loan value.",
    "List all companies with loans in multiple currencies.",
    "Show all covenants that have failed in the last year.",
    "List all companies with more than 1000 employees and active loans.",
    "Show the total collateral value per loan.",
    "List all risk metrics for companies in the Technology industry.",
]

st.markdown("### Example Questions")
cols = st.columns(min(3, len(SAMPLE_QUESTIONS)))
for i, q in enumerate(SAMPLE_QUESTIONS):
    with cols[i % len(cols)]:
        if st.button(q, key=f"ex_{i}"):
            st.session_state["input_query"] = q

query = st.text_area(
    "Enter your question",
    value=st.session_state.get("input_query", "Show the 10 most recent loans"),
    height=80,
)

run_clicked = st.button("Run", type="primary")
no_exec = st.toggle("Skip exec", value=False, help="Generate SQL but do not run it", key="skip_exec_toggle")
explain_only = st.toggle("Explain-only", value=False, help="Show intent and reasoning only; skip SQL generation and execution", key="explain_only_toggle")
no_reasoning = st.toggle("No reasoning", value=False, help="Skip the reasoning/plan step", key="no_reasoning_toggle")

from agents_nl2sql.nodes import intent, sql_gen, sanitize, execute

if run_clicked:
    start_time = time.time()
    flags = Flags(
        no_exec=no_exec,
        no_reasoning=no_reasoning,
        explain_only=explain_only,
        refresh_schema=False,
    )
    state = GraphState(user_query=query, flags=flags)

    # --- Step 1: Schema context ---
    with st.spinner("Building schema context..."):
        state = schema_ctx.run(state)
    st.markdown("### Schema Context (truncated)")
    st.code(state.schema_context[:2000], language="text")

    # --- Step 2: Intent extraction ---
    if not explain_only:
        with st.spinner("Extracting intent and entities..."):
            state = intent.run(state)
        st.markdown("### Intent & Entities")
        st.write(state.intent_entities)

    # --- Step 3: SQL generation ---
    if not explain_only:
        with st.spinner("Generating SQL..."):
            state = sql_gen.run(state)
        st.markdown("### Generated SQL (raw)")
        st.code(state.sql_raw or "", language="sql")

    # --- Step 4: SQL sanitization ---
    if not explain_only:
        with st.spinner("Sanitizing SQL..."):
            state = sanitize.run(state)
        st.markdown("### Sanitized SQL (for execution)")
        st.code(state.sql_sanitized or "", language="sql")

    # --- Step 5: SQL execution ---
    if not explain_only and not no_exec:
        with st.spinner("Executing SQL against database..."):
            state = execute.run(state)
        st.markdown("### Results Preview")
        st.code(state.execution_result.preview or "", language="text")
        if state.execution_result.rows:
            st.dataframe(state.execution_result.rows, width='stretch')
    elif explain_only:
        st.info("Explain-only mode: SQL generation and execution skipped.")
    else:
        st.info("Execution skipped.")

    # --- Show pipeline execution time ---
    elapsed = time.time() - start_time
    st.success(f"Total pipeline execution time: {elapsed:.2f} seconds")

    # --- Save results to a text file ---
    if not explain_only and state.execution_result.rows:
        results_dir = os.path.join(ROOT, "agents_nl2sql", "results")
        os.makedirs(results_dir, exist_ok=True)
        safe_query = query.strip().replace(" ", "_")[:40]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_filename = f"agents_ui_run_{safe_query}_{ts}.txt"
        txt_path = os.path.join(results_dir, out_filename)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Query: {query}\n\n")
            f.write(f"Generated SQL:\n{state.sql_raw or ''}\n\n")
            f.write(f"Sanitized SQL:\n{state.sql_sanitized or ''}\n\n")
            f.write("Results Preview:\n")
            f.write(state.execution_result.preview or "")
            f.write(f"\nTotal pipeline execution time: {elapsed:.2f} seconds\n")
        st.info(f"Results saved to {txt_path}")

    # --- Errors ---
    if state.errors:
        st.error("\n".join(state.errors))

    # --- Debug: Show full agent state ---
    with st.expander("Agent State (Debug)", expanded=False):
        st.json(state.model_dump())
