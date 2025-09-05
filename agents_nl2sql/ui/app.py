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


# --- App purpose and DB summary ---
st.title("Agents NL2SQL Demo UI")
st.caption("Natural Language → Agents → SQL → Results")
st.markdown("""
**Welcome!** This app demonstrates an agent-based pipeline for translating natural language questions into SQL queries and running them live against the Contoso-FI demo database.

**What can you do?**
- Ask questions about loans, companies, collateral, covenants, payments, risk, and more.
- See how each agent (intent extraction, SQL generation, etc.) works step by step.
- View, download, and analyze results instantly.

**About the demo database:**
- **Tables:** Loans, Companies, Collateral, Covenants, Payments, Risk Metrics, Currencies, Regions, and more.
- **Example questions:** Portfolio analysis, top companies, regional breakdowns, risk metrics, overdue payments, and more.
- **Schema highlights:**
    - `dbo.vw_LoanPortfolio`: Denormalized view for portfolio-style queries
    - `dbo.Loan`, `dbo.Company`, `dbo.Collateral`, `dbo.PaymentSchedule`, `dbo.Covenant`, `ref.Currency`, `ref.Region`, etc.
    - Relationships between loans, companies, collateral, and reference data
""")

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


# Sample questions with categories
SAMPLE_QUESTIONS = [
    ("Show the 10 most recent loans by OriginationDate.", "Easy"),
    ("List all currencies and their symbols available in the database.", "Easy"),
    ("Show all companies with more than 3 active loans.", "Easy"),
    ("For each region, list the top 5 companies by total principal amount.", "Medium"),
    ("Identify loans with upcoming covenant tests in the next 30 days.", "Medium"),
    ("For each loan, compute the remaining balance and show the top 10 by balance.", "Medium"),
    ("Show the total number of loans and total principal by risk category.", "Medium"),
    ("List all collateral items valued above 1,000,000.", "Medium"),
    ("For each company with loans, compute total principal amount; show the top 20 companies by total principal.", "Hard"),
    ("For each region, show the average loan-to-value ratio.", "Hard"),
    ("List all companies with loans in multiple currencies.", "Hard"),
    ("Show all covenants that have failed in the last year.", "Hard"),
    ("List all risk metrics for companies in the Technology industry.", "Hard"),
]

# Color map for categories
CATEGORY_COLORS = {
    "Easy": "#e0f7fa",
    "Medium": "#fff9c4",
    "Hard": "#ffebee",
}


st.markdown("### Example Questions")
cols = st.columns(min(3, len(SAMPLE_QUESTIONS)))
import hashlib
for i, (q, cat) in enumerate(SAMPLE_QUESTIONS):
    with cols[i % len(cols)]:
        # Styled container for color and legend
        st.markdown(f"""
            <div style='background-color:{CATEGORY_COLORS[cat]}; border-radius:6px; border:1px solid #ccc; padding:0.5em 0.2em; margin-bottom:0.2em;'>
                <div style='font-size:1em; font-weight:500; color:#222; margin-bottom:0.3em;'>{q}</div>
                <div style='font-size:0.9em; color:#666;'><b>Category:</b> <span style='color:#333'>{cat}</span></div>
            </div>
        """, unsafe_allow_html=True)
        # Unique key: index + hash of question
        q_hash = hashlib.md5(q.encode()).hexdigest()[:8]
        if st.button("Select", key=f"ex_{i}_{q_hash}"):
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
    intent_value = None
    if not explain_only:
        with st.spinner("Extracting intent and entities..."):
            state = intent.run(state)
        intent_value = state.intent_entities
    else:
        intent_value = state.intent_entities
    st.markdown("### Intent & Entities")
    if intent_value:
        st.write(intent_value)
    else:
        st.warning("No intent/entities extracted. The agent may have failed to parse the question or the LLM did not return a result.")
        st.info(f"User query fallback: {query}")

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
