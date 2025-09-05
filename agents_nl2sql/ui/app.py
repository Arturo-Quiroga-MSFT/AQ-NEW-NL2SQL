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

# Ensure repo root is on sys.path BEFORE importing package modules
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv()

# Now safe to import internal modules
from agents_nl2sql.llm import get_pricing_for_deployment, DEPLOYMENT_NAME
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

# Placeholder badges (updated after first run). We'll store small flags in session_state.
azure_ok = st.session_state.get("azure_env_valid_last", True)
sql_ok = st.session_state.get("sql_env_valid_last", True)

def _badge(ok: bool, label: str) -> str:
    color = "#4caf50" if ok else "#e53935"
    return f"<span style='background:{color};color:white;padding:2px 8px;border-radius:12px;font-size:0.75rem;margin-right:6px;'>{label}:{'OK' if ok else 'FAIL'}</span>"

st.markdown(
    _badge(azure_ok, "Azure OpenAI") + _badge(sql_ok, "Azure SQL") +
    " <span style='font-size:0.9rem;color:#666;'>Natural Language → Agents → SQL → Results</span>",
    unsafe_allow_html=True,
)
st.caption("Environment health badges update after a run.")
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
    # Environment status (pre-run quick visibility) adapted from original demo UI
    with st.expander("Environment status", expanded=False):
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        dep = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        sql_server = os.getenv("AZURE_SQL_SERVER")
        sql_db = os.getenv("AZURE_SQL_DB")
        sql_user = os.getenv("AZURE_SQL_USER")
        sql_pwd = os.getenv("AZURE_SQL_PASSWORD")
        def _ok(v):
            return "✅" if v else "⚠️"
        st.write(f"Azure OpenAI Key {_ok(api_key)}")
        st.write(f"Azure OpenAI Endpoint {_ok(endpoint)}")
        st.write(f"Deployment {_ok(dep)}")
        st.write(f"SQL Server {_ok(sql_server)} | DB {_ok(sql_db)} | User {_ok(sql_user)} | Password {_ok(sql_pwd)}")
        st.caption("Values shown only as presence checks. Detailed validation appears in Diagnostics after a run.")
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
            st.session_state["input_category"] = cat


# Get current question and category
query = st.text_area(
    "Enter your question",
    value=st.session_state.get("input_query", "Show the 10 most recent loans"),
    height=80,
)
category = st.session_state.get("input_category", "Easy")

run_clicked = st.button("Run", type="primary")
no_exec = st.toggle("Skip exec", value=False, help="Generate SQL but do not run it", key="skip_exec_toggle")
explain_only = st.toggle("Explain-only", value=False, help="Show intent and reasoning only; skip SQL generation and execution", key="explain_only_toggle")
no_reasoning = st.toggle("No reasoning", value=False, help="Skip the reasoning/plan step", key="no_reasoning_toggle")

# --- Adjustable Token Caps ---
with st.expander("Model token caps (per stage)", expanded=False):
    st.caption("Set per-stage completion token ceilings. Leave at defaults for full 8192 global cap.")
    intent_cap = st.slider("Intent max completion tokens", 64, 8192, st.session_state.get("intent_cap", 1024), step=64, key="intent_cap_slider")
    reasoning_cap = st.slider("Reasoning max completion tokens", 128, 8192, st.session_state.get("reasoning_cap", 1024), step=64, key="reasoning_cap_slider")
    sql_cap = st.slider("SQL generation max completion tokens", 256, 8192, st.session_state.get("sql_cap", 2048), step=64, key="sql_cap_slider")
    # Persist selections
    st.session_state["intent_cap"] = intent_cap
    st.session_state["reasoning_cap"] = reasoning_cap
    st.session_state["sql_cap"] = sql_cap
    # Reset button
    if st.button("Reset to defaults", key="reset_token_caps"):
        defaults = {"intent_cap": 1024, "reasoning_cap": 1024, "sql_cap": 2048}
        for k, v in defaults.items():
            st.session_state[k] = v
        # Also reset slider keys to reflect immediately
        st.session_state["intent_cap_slider"] = defaults["intent_cap"]
        st.session_state["reasoning_cap_slider"] = defaults["reasoning_cap"]
        st.session_state["sql_cap_slider"] = defaults["sql_cap"]
        st.experimental_rerun()

from agents_nl2sql.nodes import intent, reasoning, sql_gen, sanitize, execute

if run_clicked:
    start_time = time.time()
    flags = Flags(
        no_exec=no_exec,
        no_reasoning=no_reasoning,
        explain_only=explain_only,
        refresh_schema=False,
    )
    state = GraphState(
        user_query=query,
        flags=flags,
        question_category=category,
        intent_max_tokens=intent_cap if intent_cap else None,
        reasoning_max_tokens=reasoning_cap if reasoning_cap else None,
        sql_max_tokens=sql_cap if sql_cap else None,
    )

    # --- Step 1: Schema context ---
    with st.spinner("Building schema context..."):
        state = schema_ctx.run(state)
    st.markdown("### Schema Context (truncated)")
    st.code(state.schema_context[:2000], language="text")
    # Show Azure OpenAI environment validation messages if available
    # Consolidated Diagnostics Section
    st.markdown("### Diagnostics")
    cols_diag = st.columns(2)
    with cols_diag[0]:
        st.markdown("**Azure OpenAI Environment**")
        if not state.azure_env_valid:
            for msg in state.azure_env_messages:
                (st.error if msg.startswith(("[MISSING]", "[INVALID]")) else st.write)(msg)
        else:
            for msg in state.azure_env_messages:
                st.write(msg)
    with cols_diag[1]:
        st.markdown("**Azure SQL Environment**")
        if not state.sql_env_valid:
            for msg in state.sql_env_messages:
                (st.error if msg.startswith("[MISSING]") else st.write)(msg)
        else:
            for msg in state.sql_env_messages:
                st.write(msg)

    # Update session state for badges
    st.session_state["azure_env_valid_last"] = state.azure_env_valid
    st.session_state["sql_env_valid_last"] = state.sql_env_valid


    # --- Step 2: Intent extraction (always run, even in explain-only) ---
    with st.spinner("Extracting intent and entities..."):
        state = intent.run(state)
    intent_value = state.intent_entities
    st.markdown("### Intent & Entities")
    if intent_value:
        if isinstance(intent_value, dict):
            st.json(intent_value)
            intent_for_file = intent_value
        else:
            st.write(intent_value)
            intent_for_file = intent_value
    else:
        st.warning("No intent/entities extracted. The agent may have failed to parse the question or the LLM did not return a result.")
        st.info(f"User query fallback: {query}")
        intent_for_file = "<none extracted>"

    # --- Step 2b: Reasoning (optional, still runs in explain-only unless toggled off) ---
    reasoning_text = ""
    if not no_reasoning:
        with st.spinner("Generating reasoning plan (with retry)..."):
            from agents_nl2sql.nodes import reasoning as reasoning_node
            state = reasoning_node.run(state)
        reasoning_text = state.reasoning or ""
        st.markdown("### Reasoning / Plan")
        if reasoning_text:
            st.write(reasoning_text)
        else:
            st.info("No reasoning returned.")

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
    st.markdown("#### Run Metrics")
    st.write(f"Intent parse attempts: {getattr(state, 'intent_parse_attempts', 'n/a')}")
    st.write(f"Reasoning attempts: {getattr(state, 'reasoning_attempts', 'n/a')}")
    # Effective caps display
    eff_intent = state.intent_max_tokens if state.intent_max_tokens else "global"
    eff_reasoning = state.reasoning_max_tokens if state.reasoning_max_tokens else "global"
    eff_sql = state.sql_max_tokens if state.sql_max_tokens else "global"
    st.write(f"Token caps (intent / reasoning / SQL): {eff_intent} / {eff_reasoning} / {eff_sql} (global default=8192)")

    # --- Token & Cost Panel (mirrors legacy UI style) ---
    tok_prompt = state.token_usage.prompt
    tok_completion = state.token_usage.completion
    tok_total = state.token_usage.total or (tok_prompt + tok_completion)
    in_price_1k, out_price_1k, price_source, currency = get_pricing_for_deployment(DEPLOYMENT_NAME)
    with st.expander("Token usage & estimated cost", expanded=False):
        st.write({
            "prompt_tokens": tok_prompt,
            "completion_tokens": tok_completion,
            "total_tokens": tok_total,
            "pricing_source": price_source,
            "currency": currency,
        })
        if in_price_1k is not None and out_price_1k is not None:
            input_cost = (tok_prompt / 1000.0) * in_price_1k
            output_cost = (tok_completion / 1000.0) * out_price_1k
            total_cost = input_cost + output_cost
            st.success(
                f"Estimated cost ({currency}): {total_cost:.6f}  "
                f"[input={input_cost:.6f}, output={output_cost:.6f}; per-1k: in={in_price_1k}, out={out_price_1k}; source={price_source}]"
            )
        else:
            st.info("Pricing not configured. Provide env vars AZURE_OPENAI_PRICE_INPUT_PER_1K / OUTPUT_PER_1K or per-deployment overrides, or azure_openai_pricing.json.")

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
            try:
                if isinstance(intent_for_file, dict):
                    import json as _json
                    f.write("Intent & Entities (JSON):\n")
                    f.write(_json.dumps(intent_for_file, indent=2))
                    f.write("\n\n")
                else:
                    f.write(f"Intent & Entities: {intent_for_file}\n\n")
            except Exception:
                f.write(f"Intent & Entities: {intent_for_file}\n\n")
            if reasoning_text:
                f.write("Reasoning / Plan:\n")
                f.write(reasoning_text)
                f.write("\n\n")
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
