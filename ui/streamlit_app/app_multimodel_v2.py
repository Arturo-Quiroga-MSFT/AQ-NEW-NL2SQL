"""Streamlit UI for the Contoso-FI NL2SQL Demo - Multi-Model Optimized V2.

This version uses different optimized models for each stage of the pipeline:
- Intent Extraction: gpt-4o-mini (fast & cheap for parsing)
- SQL Generation: gpt-4.1 or gpt-5-mini (accurate for complex queries)
- Result Formatting: gpt-4.1-mini (balanced for natural language explanations)

V2 Changes:
- Hardcoded example questions (no longer reads from external file)
- Curated set of EASY, MEDIUM, COMPLICATED, and STRESS questions

High-level flow when the user presses Run:
 1. Reset token counters.
 2. Parse the natural language question into structured intent/entities (gpt-4o-mini).
 3. (Optional) Generate a reasoning / high-level plan explanation (user-selected model).
 4. Generate raw SQL from the intent (gpt-4.1 or gpt-5-mini).
 5. Sanitize / extract runnable SQL (adds warnings or modifications if needed).
 6. (Optional) Execute SQL against Azure SQL and display tabular results.
 7. Format results into natural language explanation (gpt-4.1-mini).
 8. Display token usage + estimated cost breakdown by model.
 9. Persist a detailed run log locally and optionally upload to Azure Blob Storage.

This multi-model approach optimizes for both cost and quality:
- Fast, cheap model (gpt-4o-mini) handles simple parsing
- Powerful model (gpt-4.1/gpt-5-mini) handles complex SQL generation
- Balanced model (gpt-4.1-mini) creates readable result summaries
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

###############################################################################
# Optional Azure Blob Storage integration
###############################################################################
import tempfile
from urllib.parse import quote as urlquote
try:
    from azure.storage.blob import BlobServiceClient
    _HAS_BLOB = True
except ImportError:
    _HAS_BLOB = False

import streamlit as st
from dotenv import load_dotenv

# Ensure repository root is on sys.path
CURRENT_FILE = os.path.abspath(__file__)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_FILE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Add nl2sql_standalone_Langchain to path for module imports
LANGCHAIN_DIR = os.path.join(ROOT, "nl2sql_standalone_Langchain")
if LANGCHAIN_DIR not in sys.path:
    sys.path.insert(0, LANGCHAIN_DIR)

load_dotenv()

# Import necessary components for multi-model setup
import importlib.util
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
import requests

# Import the original module to reuse helper functions
nl2sql_main_path = os.path.join(LANGCHAIN_DIR, "1_nl2sql_main.py")
if not os.path.exists(nl2sql_main_path):
    raise FileNotFoundError(f"Could not find nl2sql_main module at: {nl2sql_main_path}")
    
spec = importlib.util.spec_from_file_location("nl2sql_main", nl2sql_main_path)
nl2sql_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nl2sql_main)

# Extract helper functions and variables
extract_and_sanitize_sql = nl2sql_main.extract_and_sanitize_sql
_format_table = nl2sql_main._format_table
_load_pricing_config = nl2sql_main._load_pricing_config

from schema_reader import refresh_schema_cache, get_sql_database_schema_context
from sql_executor import execute_sql_query

# Azure OpenAI configuration
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")

# Model configuration for each stage
INTENT_MODEL = "gpt-4o-mini"  # Fast & cheap for intent extraction
SQL_MODEL_DEFAULT = "gpt-4.1"  # Default for SQL generation (can be changed to gpt-5-mini)
FORMATTING_MODEL = "gpt-4.1-mini"  # Balanced for result formatting

# Token usage tracking per model
_TOKEN_USAGE_BY_MODEL = {
    "intent": {"prompt": 0, "completion": 0, "total": 0},
    "sql": {"prompt": 0, "completion": 0, "total": 0},
    "formatting": {"prompt": 0, "completion": 0, "total": 0},
}

def _reset_token_usage():
    """Reset all token counters."""
    for model_stage in _TOKEN_USAGE_BY_MODEL.values():
        model_stage["prompt"] = 0
        model_stage["completion"] = 0
        model_stage["total"] = 0

def _accumulate_usage(stage: str, usage: Optional[Dict[str, Any]]) -> None:
    """Accumulate token usage for a specific model stage."""
    if not usage:
        return
    _TOKEN_USAGE_BY_MODEL[stage]["prompt"] += int(usage.get("prompt_tokens", 0) or 0)
    _TOKEN_USAGE_BY_MODEL[stage]["completion"] += int(usage.get("completion_tokens", 0) or 0)
    _TOKEN_USAGE_BY_MODEL[stage]["total"] += int(usage.get("total_tokens", 0) or 
        (_TOKEN_USAGE_BY_MODEL[stage]["prompt"] + _TOKEN_USAGE_BY_MODEL[stage]["completion"]))

def _extract_usage_from_message(msg: Any) -> Optional[Dict[str, Any]]:
    """Extract token usage from LangChain message."""
    try:
        meta = getattr(msg, "response_metadata", None) or {}
        token_usage = meta.get("token_usage")
        if token_usage and isinstance(token_usage, dict):
            return {
                "prompt_tokens": token_usage.get("prompt_tokens") or token_usage.get("input_tokens") or 0,
                "completion_tokens": token_usage.get("completion_tokens") or token_usage.get("output_tokens") or 0,
                "total_tokens": token_usage.get("total_tokens") or 
                    (token_usage.get("prompt_tokens", 0) or 0) + (token_usage.get("completion_tokens", 0) or 0),
            }
        um = getattr(msg, "usage_metadata", None)
        if um and isinstance(um, dict):
            return {
                "prompt_tokens": um.get("input_tokens") or um.get("prompt_tokens") or 0,
                "completion_tokens": um.get("output_tokens") or um.get("completion_tokens") or 0,
                "total_tokens": um.get("total_tokens") or 
                    (um.get("input_tokens", 0) or 0) + (um.get("output_tokens", 0) or 0),
            }
    except Exception:
        pass
    return None

def _make_llm(deployment_name: str, max_tokens: int = 8192) -> AzureChatOpenAI:
    """Create an Azure OpenAI LLM instance for a specific deployment.
    
    Note: Newer models (gpt-4o, gpt-5, o-series) use max_completion_tokens instead of max_tokens
    and don't support custom temperature values.
    """
    # Determine if this is a newer model that requires max_completion_tokens
    model_name = deployment_name.lower()
    uses_completion_tokens = (
        model_name.startswith('gpt-4o') or 
        model_name.startswith('gpt-5') or 
        model_name.startswith('gpt-4.1') or
        model_name.startswith('o1') or 
        model_name.startswith('o3') or 
        model_name.startswith('o4')
    )
    
    if uses_completion_tokens:
        # New models: use max_completion_tokens via model_kwargs, no custom temperature
        return AzureChatOpenAI(
            openai_api_key=API_KEY,
            azure_endpoint=ENDPOINT,
            deployment_name=deployment_name,
            api_version=API_VERSION,
            temperature=1,  # Must be 1 (default) for new models
            model_kwargs={"max_completion_tokens": max_tokens}
        )
    else:
        # Legacy models: use max_tokens, can customize temperature
        return AzureChatOpenAI(
            openai_api_key=API_KEY,
            azure_endpoint=ENDPOINT,
            deployment_name=deployment_name,
            api_version=API_VERSION,
            max_tokens=max_tokens,
        )

def _get_pricing_for_deployment(deployment_name: str) -> Tuple[Optional[float], Optional[float], str, str]:
    """Get pricing for a specific deployment."""
    pricing = _load_pricing_config()
    dep_lower = deployment_name.lower()
    
    if dep_lower in pricing:
        data = pricing[dep_lower]
        # Handle nested structure with USD/CAD
        if "USD" in data:
            usd_data = data["USD"]
            return (
                usd_data.get("input_per_1k"),
                usd_data.get("output_per_1k"),
                "pricing_config",
                "USD"
            )
        # Handle flat structure (legacy)
        elif "input_per_1k" in data:
            currency = data.get("currency", "USD")
            return (
                data.get("input_per_1k"),
                data.get("output_per_1k"),
                "pricing_config",
                currency
            )
    return (None, None, "not_configured", "USD")

# -----------------------------------------------------------------------------
# MULTI-MODEL PIPELINE FUNCTIONS
# -----------------------------------------------------------------------------

def parse_nl_query_with_gpt4o_mini(user_input: str) -> str:
    """Extract intent and entities using gpt-4o-mini (optimized for speed and cost)."""
    llm = _make_llm(INTENT_MODEL, max_tokens=2048)
    
    schema = get_sql_database_schema_context()
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at parsing natural language questions about financial data.
Your task is to extract the key intent and entities from the user's question.

Database Schema Context:
{schema}

Return a structured JSON with:
- intent: The main action (e.g., "list", "count", "calculate", "find")
- entities: Key entities mentioned (e.g., table names, columns, filters)
- timeframe: Any time-related constraints
- aggregations: Any grouping or aggregation requirements
- filters: Specific filtering conditions

Be concise but complete."""),
        ("human", "{user_input}")
    ])
    
    chain = prompt_template | llm
    result = chain.invoke({"schema": schema, "user_input": user_input})
    
    # Track token usage
    usage = _extract_usage_from_message(result)
    _accumulate_usage("intent", usage)
    
    return result.content

def generate_sql_with_selected_model(intent_entities: str, model_name: str) -> str:
    """Generate SQL using the selected model (gpt-4.1 or gpt-5-mini)."""
    llm = _make_llm(model_name, max_tokens=8192)
    
    schema = get_sql_database_schema_context()
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are an expert T-SQL developer for Azure SQL Database.
Given the user's intent and the database schema, generate a precise T-SQL query.

Database Schema:
{schema}

Requirements:
- Use proper T-SQL syntax for Azure SQL Database
- Include appropriate JOINs, WHERE clauses, and aggregations
- Use CTEs for complex queries
- Add comments for clarity
- Format the SQL nicely with proper indentation
- Wrap the final SQL in ```sql code blocks

User Intent:
{intent_entities}

Generate the T-SQL query now:"""),
        ("human", "Generate the SQL query based on the intent above.")
    ])
    
    chain = prompt_template | llm
    result = chain.invoke({"schema": schema, "intent_entities": intent_entities})
    
    # Track token usage
    usage = _extract_usage_from_message(result)
    _accumulate_usage("sql", usage)
    
    return result.content

def generate_reasoning_with_selected_model(intent_entities: str, model_name: str) -> str:
    """Generate reasoning/plan using the selected model."""
    llm = _make_llm(model_name, max_tokens=4096)
    
    schema = get_sql_database_schema_context()
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are an expert data analyst explaining your reasoning.
Given the user's intent and database schema, explain your high-level plan for answering the question.

Database Schema:
{schema}

User Intent:
{intent_entities}

Provide a clear, step-by-step explanation of:
1. What tables and relationships you'll use
2. What calculations or aggregations are needed
3. Any filtering or sorting logic
4. Why this approach is optimal

Be concise but thorough."""),
        ("human", "Explain your reasoning for this query.")
    ])
    
    chain = prompt_template | llm
    result = chain.invoke({"schema": schema, "intent_entities": intent_entities})
    
    # Track token usage (counted as part of SQL generation stage)
    usage = _extract_usage_from_message(result)
    _accumulate_usage("sql", usage)
    
    return result.content

def format_results_with_gpt41_mini(query: str, intent: str, sql: str, results: List[Dict[str, Any]]) -> str:
    """Format query results into natural language using gpt-4.1-mini."""
    if not results:
        return "The query returned no results."
    
    llm = _make_llm(FORMATTING_MODEL, max_tokens=4096)
    
    # Limit results to first 20 rows for formatting (to avoid token limits)
    sample_results = results[:20]
    results_preview = json.dumps(sample_results, indent=2, default=str)[:3000]  # Limit to 3000 chars
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are an expert data analyst providing clear, concise summaries of query results.

Given the user's original question, the SQL query executed, and the results, provide:
1. A brief summary of what was found
2. Key insights or patterns in the data
3. Any notable statistics (totals, averages, extremes)
4. A natural language answer to the user's original question

Be professional, clear, and concise. Focus on insights, not just restating the data."""),
        ("human", """Original Question: {query}

Intent: {intent}

SQL Query:
{sql}

Results (first {count} rows):
{results}

Provide a clear summary and insights:""")
    ])
    
    chain = prompt_template | llm
    result = chain.invoke({
        "query": query,
        "intent": intent,
        "sql": sql,
        "results": results_preview,
        "count": len(sample_results)
    })
    
    # Track token usage
    usage = _extract_usage_from_message(result)
    _accumulate_usage("formatting", usage)
    
    return result.content

# -----------------------------------------------------------------------------
# HARDCODED EXAMPLE QUESTIONS (V2)
# -----------------------------------------------------------------------------

EXAMPLE_QUESTIONS: List[str] = [
    # EASY
    "Show the 10 most recent loans by OriginationDate.",
    "Show the 10 upcoming loan maturities (soonest MaturityDate first) with principal amount and status.",
    "List 20 companies with their industry and credit rating.",
    
    # MEDIUM
    "For each company with loans, compute total principal amount; show the top 20 companies by total principal.",
    "Average interest rate by industry and region (join Loan → Company → Country → Region).",
    "Count of loans by status per country (join Loan → Company → Country).",
    "Total collateral value per loan with the associated company name; show the top 20 by total collateral value.",
    
    # COMPLICATED
    "For each loan, compute month-over-month change in EndingPrincipal from PaymentSchedule; show 20 loans with the largest absolute change (include positive/negative flags).",
    "Covenant compliance rate by industry: percentage of covenant tests with Status = 'Pass' (all-time), grouped by industry and calendar quarter.",
    "Weighted average interest rate by region and currency (weighted by PrincipalAmount).",
    
    # STRESS (ADVANCED SQL)
    "As-of-balance: for each region, using the latest available DueDate per loan from PaymentSchedule, sum EndingPrincipal by company and show the top 3 companies per region with each company's share of the region total.",
    "Delinquency buckets by month and region: using PaymentEvent, bucket DaysDelinquent into 0–29, 30–59, 60–89, and 90+ and show, for the 6 most recent months in the data, each bucket's percentage of total per region.",
]

# -----------------------------------------------------------------------------
# Streamlit Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="NL2SQL Demo (Multi-Model V2)",
    page_icon="🎯",
    layout="wide",
)

# -----------------------------------------------------------------------------
# Sidebar: Environment status, schema refresh, schema preview
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("NL2SQL Demo UI")
    st.caption("**Multi-Model Optimized V2** Implementation")
    st.caption("🎯 Intent (gpt-4o-mini) → 🧠 SQL (gpt-4.1/gpt-5-mini) → 📝 Format (gpt-4.1-mini)")
    st.caption("✨ **V2**: Hardcoded example questions")
    
    # Model selection
    st.markdown("### SQL Generation Model")
    sql_model_choice = st.radio(
        "Choose SQL generation model:",
        options=["gpt-4.1", "gpt-5-mini"],
        index=0,
        help="gpt-4.1: Most accurate, best for complex queries\ngpt-5-mini: Faster reasoning, lower cost"
    )
    
    # Environment status
    with st.expander("Environment status", expanded=False):
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        sql_server = os.getenv("AZURE_SQL_SERVER")
        sql_db = os.getenv("AZURE_SQL_DB")
        sql_user = os.getenv("AZURE_SQL_USER")
        sql_pwd = os.getenv("AZURE_SQL_PASSWORD")
        def ok(v: Any) -> str:
            return "✅" if v else "⚠️"
        st.write(f"Azure OpenAI Key {ok(api_key)}")
        st.write(f"Azure OpenAI Endpoint {ok(endpoint)}")
        st.write(f"SQL Server {ok(sql_server)} | DB {ok(sql_db)} | User {ok(sql_user)} | Password {ok(sql_pwd)}")
    
    # Manual schema cache refresh
    if st.button("🔁 Refresh schema cache"):
        try:
            path = refresh_schema_cache()
            st.success(f"Schema cache refreshed: {path}")
        except Exception as e:
            st.error(f"Failed to refresh schema cache: {e}")
    
    with st.expander("Current schema context (preview)", expanded=False):
        ctx = get_sql_database_schema_context(ttl_seconds=0)
        st.code(ctx[:4000], language="text")
    
    # Multi-model explanation
    with st.expander("💡 Multi-Model Strategy", expanded=False):
        st.markdown("""
**Why different models for each stage?**

🎯 **Intent Extraction (gpt-4o-mini)**
- Task: Parse user question into structured format
- Why: Simple parsing doesn't need expensive models
- Cost: ~$0.00015 per 1K tokens (cheapest)

🧠 **SQL Generation (gpt-4.1 or gpt-5-mini)**
- Task: Create accurate, complex T-SQL queries
- Why: Requires deep reasoning and schema understanding
- Cost: gpt-4.1 ~$0.00277, gpt-5-mini ~$0.0003 per 1K tokens

📝 **Result Formatting (gpt-4.1-mini)**
- Task: Summarize results in natural language
- Why: Balanced capability for clear explanations
- Cost: ~$0.00055 per 1K tokens

**Savings**: Up to 80% cost reduction vs using gpt-4.1 for all stages!
        """)

# -----------------------------------------------------------------------------
# Main page header
# -----------------------------------------------------------------------------
st.markdown("""
<h1 style='text-align: left;'>🎯 Contoso-FI NL2SQL - Multi-Model Optimized V2</h1>
<p style='font-size:1.1em;'>
<b>Ask questions in plain English and get instant, optimized SQL and results with AI-powered summaries.</b><br>
This app uses <b>multiple specialized models</b> for optimal cost and performance:<br>
&nbsp;&nbsp;🎯 <b>gpt-4o-mini</b> for fast intent extraction<br>
&nbsp;&nbsp;🧠 <b>gpt-4.1 or gpt-5-mini</b> for accurate SQL generation<br>
&nbsp;&nbsp;📝 <b>gpt-4.1-mini</b> for result formatting and summaries<br><br>
<b>About the data:</b> The <b>Contoso-FI</b> dataset models a mid-size financial institution, with tables for loans, companies, collateral, covenants, payments, risk, and more.<br><br>
<b>🆚 Implementation:</b> This version uses <b>multi-model optimization</b> to balance cost, speed, and quality.<br>
<b>✨ V2 Update:</b> Hardcoded example questions from curated question bank (EASY, MEDIUM, COMPLICATED, STRESS).
</p>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Example question buttons
# -----------------------------------------------------------------------------
st.markdown("### Examples")
st.caption("Curated questions: EASY → MEDIUM → COMPLICATED → STRESS (Advanced SQL)")
cols = st.columns(min(3, len(EXAMPLE_QUESTIONS)))
for i, q in enumerate(EXAMPLE_QUESTIONS):
    with cols[i % len(cols)]:
        if st.button(q, key=f"ex_{i}"):
            st.session_state["input_query"] = q

# -----------------------------------------------------------------------------
# User query input area
# -----------------------------------------------------------------------------
query = st.text_area(
    "Enter your question",
    value=st.session_state.get("input_query", "Show the 10 most recent loans"),
    height=80,
)

# -----------------------------------------------------------------------------
# Control toggles
# -----------------------------------------------------------------------------
controls_cols = st.columns([6, 2, 2, 2, 2])
with controls_cols[1]:
    run_clicked = st.button("Run", type="primary")
with controls_cols[2]:
    no_exec = st.toggle("⏭️ Skip exec", value=False, help="Generate SQL but do not run it", key="skip_exec_toggle")
with controls_cols[3]:
    explain_only = st.toggle("📝 Explain-only", value=False, help="Show intent and reasoning only; skip SQL", key="explain_only_toggle")
with controls_cols[4]:
    no_reasoning = st.toggle("🧠 No reasoning", value=False, help="Skip the reasoning/plan step", key="no_reasoning_toggle")

if run_clicked:
    # -------------------------------------------------------------------------
    # MULTI-MODEL PIPELINE ORCHESTRATION
    # -------------------------------------------------------------------------
    start_time = time.time()
    
    # Display run configuration
    st.markdown("---")
    with st.expander("⚙️ Run Configuration - Multi-Model Setup", expanded=True):
        config_cols = st.columns(3)
        with config_cols[0]:
            st.markdown("**🎯 Intent Extraction:**")
            st.write(f"Model: `{INTENT_MODEL}`")
            st.write(f"Purpose: Parse user question")
            intent_in, intent_out, _, _ = _get_pricing_for_deployment(INTENT_MODEL)
            if intent_in:
                st.write(f"Cost: ${intent_in:.5f} in / ${intent_out:.5f} out per 1K tokens")
        
        with config_cols[1]:
            st.markdown("**🧠 SQL Generation:**")
            st.write(f"Model: `{sql_model_choice}`")
            st.write(f"Purpose: Generate accurate T-SQL")
            sql_in, sql_out, _, _ = _get_pricing_for_deployment(sql_model_choice)
            if sql_in:
                st.write(f"Cost: ${sql_in:.5f} in / ${sql_out:.5f} out per 1K tokens")
        
        with config_cols[2]:
            st.markdown("**📝 Result Formatting:**")
            st.write(f"Model: `{FORMATTING_MODEL}`")
            st.write(f"Purpose: Summarize results")
            fmt_in, fmt_out, _, _ = _get_pricing_for_deployment(FORMATTING_MODEL)
            if fmt_in:
                st.write(f"Cost: ${fmt_in:.5f} in / ${fmt_out:.5f} out per 1K tokens")
    
    st.markdown("---")
    
    # Reset token usage counters
    _reset_token_usage()
    result_rows: List[Dict[str, Any]] | None = None
    exec_error: str | None = None
    formatted_results: str | None = None
    
    # Stage timing tracking
    stage_times = {}

    if not query.strip():
        st.warning("Please enter a question.")
        st.stop()

    # ---- Step 1: NL parsing with gpt-4o-mini
    stage_start = time.time()
    with st.spinner(f"🎯 Extracting intent with {INTENT_MODEL}..."):
        intent_entities = parse_nl_query_with_gpt4o_mini(query)
    stage_times["intent_extraction"] = time.time() - stage_start

    st.markdown("### 🎯 Intent & Entities")
    st.write(intent_entities)
    st.caption(f"⏱️ Time: {stage_times['intent_extraction']:.2f}s")

    reasoning = None
    # ---- Step 2: Optional reasoning
    if not no_reasoning and not explain_only:
        stage_start = time.time()
        with st.spinner(f"🧠 Generating reasoning with {sql_model_choice}..."):
            reasoning = generate_reasoning_with_selected_model(intent_entities, sql_model_choice)
        stage_times["reasoning"] = time.time() - stage_start
        with st.expander("Reasoning (high-level plan)", expanded=True):
            st.write(reasoning)
            st.caption(f"⏱️ Time: {stage_times['reasoning']:.2f}s")

    # ---- Step 3: SQL generation with selected model
    if not explain_only:
        stage_start = time.time()
        with st.spinner(f"🧠 Generating SQL with {sql_model_choice}..."):
            raw_sql = generate_sql_with_selected_model(intent_entities, sql_model_choice)
        stage_times["sql_generation"] = time.time() - stage_start

    if not explain_only:
        st.markdown("### Generated SQL (raw)")
        st.code(raw_sql, language="sql")
        st.caption(f"⏱️ Time: {stage_times['sql_generation']:.2f}s")

    # ---- Step 4: SQL sanitization
    if not explain_only:
        sanitized_sql = extract_and_sanitize_sql(raw_sql)
        if sanitized_sql != raw_sql:
            st.markdown("### Sanitized SQL (for execution)")
            st.code(sanitized_sql, language="sql")

    # ---- Step 5: Execute SQL
    if not explain_only and not no_exec:
        stage_start = time.time()
        with st.spinner("⚡ Executing SQL against Azure SQL Database..."):
            try:
                rows: List[Dict[str, Any]] = execute_sql_query(sanitized_sql)
                stage_times["sql_execution"] = time.time() - stage_start
                if rows:
                    st.markdown("### Results")
                    st.dataframe(rows, use_container_width=True)
                    st.caption(f"⏱️ Execution Time: {stage_times['sql_execution']:.2f}s")
                    result_rows = rows
                    
                    # ---- Step 6: Format results with gpt-4.1-mini
                    stage_start = time.time()
                    with st.spinner(f"📝 Formatting results with {FORMATTING_MODEL}..."):
                        formatted_results = format_results_with_gpt41_mini(
                            query, intent_entities, sanitized_sql, rows
                        )
                    stage_times["result_formatting"] = time.time() - stage_start
                    
                    st.markdown("### 📝 AI-Generated Summary")
                    st.info(formatted_results)
                    st.caption(f"⏱️ Time: {stage_times['result_formatting']:.2f}s")
                    
                    # Export buttons
                    exp_cols = st.columns([1,1,1,6])
                    with exp_cols[0]:
                        try:
                            import pandas as pd
                            df = pd.DataFrame(rows)
                            csv_data = df.to_csv(index=False).encode("utf-8")
                            st.download_button("⬇️ Download CSV", data=csv_data, file_name="results.csv", mime="text/csv")
                        except Exception:
                            pass
                    with exp_cols[1]:
                        try:
                            import pandas as pd
                            from io import BytesIO
                            df = pd.DataFrame(rows)
                            bio = BytesIO()
                            with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
                                df.to_excel(writer, index=False, sheet_name="Results")
                            xlsx_bytes = bio.getvalue()
                            st.download_button("⬇️ Download Excel", data=xlsx_bytes, file_name="results.xlsx", 
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                        except Exception:
                            pass
                    with exp_cols[2]:
                        if 'sanitized_sql' in locals():
                            st.button("📋 Copy SQL", on_click=lambda: st.session_state.update({"_copy_sql": sanitized_sql}))
                            if st.session_state.get("_copy_sql"):
                                st.code(st.session_state["_copy_sql"], language="sql")
                else:
                    st.info("No results returned.")
            except Exception as e:
                st.error(f"SQL execution failed: {e}")
                exec_error = str(e)
    elif explain_only:
        st.info("Explain-only mode: SQL generation and execution skipped")
    else:
        st.info("Execution skipped.")

    # ---- Step 7: Token usage & cost breakdown by model
    end_time = time.time()
    elapsed_seconds = end_time - start_time
    elapsed_str = f"{elapsed_seconds:.2f}s"
    if elapsed_seconds >= 60:
        minutes = int(elapsed_seconds // 60)
        seconds = elapsed_seconds % 60
        elapsed_str = f"{minutes}m {seconds:.2f}s"
    
    st.markdown(f"### ⏱️ Total Elapsed Time: **{elapsed_str}**")
    
    with st.expander("💰 Token usage & estimated cost by model", expanded=True):
        total_cost = 0.0
        total_tokens = 0
        
        st.markdown("#### Per-Model Breakdown")
        
        # Intent extraction cost
        intent_usage = _TOKEN_USAGE_BY_MODEL["intent"]
        intent_in_price, intent_out_price, _, currency = _get_pricing_for_deployment(INTENT_MODEL)
        if intent_in_price and intent_out_price and intent_usage["total"] > 0:
            intent_input_cost = (intent_usage["prompt"] / 1000.0) * intent_in_price
            intent_output_cost = (intent_usage["completion"] / 1000.0) * intent_out_price
            intent_total_cost = intent_input_cost + intent_output_cost
            total_cost += intent_total_cost
            total_tokens += intent_usage["total"]
            
            st.markdown(f"**🎯 Intent Extraction ({INTENT_MODEL})**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Input tokens", f"{intent_usage['prompt']:,}")
            with col2:
                st.metric("Output tokens", f"{intent_usage['completion']:,}")
            with col3:
                st.metric("Cost", f"${intent_total_cost:.6f}")
        
        # SQL generation cost
        sql_usage = _TOKEN_USAGE_BY_MODEL["sql"]
        sql_in_price, sql_out_price, _, _ = _get_pricing_for_deployment(sql_model_choice)
        if sql_in_price and sql_out_price and sql_usage["total"] > 0:
            sql_input_cost = (sql_usage["prompt"] / 1000.0) * sql_in_price
            sql_output_cost = (sql_usage["completion"] / 1000.0) * sql_out_price
            sql_total_cost = sql_input_cost + sql_output_cost
            total_cost += sql_total_cost
            total_tokens += sql_usage["total"]
            
            st.markdown(f"**🧠 SQL Generation ({sql_model_choice})**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Input tokens", f"{sql_usage['prompt']:,}")
            with col2:
                st.metric("Output tokens", f"{sql_usage['completion']:,}")
            with col3:
                st.metric("Cost", f"${sql_total_cost:.6f}")
        
        # Formatting cost
        fmt_usage = _TOKEN_USAGE_BY_MODEL["formatting"]
        fmt_in_price, fmt_out_price, _, _ = _get_pricing_for_deployment(FORMATTING_MODEL)
        if fmt_in_price and fmt_out_price and fmt_usage["total"] > 0:
            fmt_input_cost = (fmt_usage["prompt"] / 1000.0) * fmt_in_price
            fmt_output_cost = (fmt_usage["completion"] / 1000.0) * fmt_out_price
            fmt_total_cost = fmt_input_cost + fmt_output_cost
            total_cost += fmt_total_cost
            total_tokens += fmt_usage["total"]
            
            st.markdown(f"**📝 Result Formatting ({FORMATTING_MODEL})**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Input tokens", f"{fmt_usage['prompt']:,}")
            with col2:
                st.metric("Output tokens", f"{fmt_usage['completion']:,}")
            with col3:
                st.metric("Cost", f"${fmt_total_cost:.6f}")
        
        # Total
        st.markdown("---")
        st.markdown("#### Total")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total tokens", f"{total_tokens:,}")
        with col2:
            st.metric("Total cost", f"${total_cost:.6f} {currency}")
        
        if total_cost > 0:
            st.success(f"✨ Multi-model optimization active! Using specialized models for each stage.")

    # ---- Step 8: Persist run artifact
    def _json_safe(obj: Any) -> Any:
        """Convert non-JSON-serializable objects."""
        from decimal import Decimal
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, )):
            return obj.isoformat()
        return str(obj)
    
    def _format_results_as_table(rows: List[Dict[str, Any]], format_type: str = "text") -> str:
        """Format query results as a text or markdown table."""
        if not rows:
            return "No results."
        
        # Get column names
        columns = list(rows[0].keys())
        
        if format_type == "markdown":
            # Markdown table format
            lines = []
            # Header
            lines.append("| " + " | ".join(columns) + " |")
            # Separator
            lines.append("|" + "|".join(["-" * (len(col) + 2) for col in columns]) + "|")
            # Rows
            for row in rows:
                values = [str(_json_safe(row.get(col, ""))) for col in columns]
                lines.append("| " + " | ".join(values) + " |")
            return "\n".join(lines)
        else:
            # Text table format with proper alignment
            # Calculate column widths
            col_widths = {col: len(col) for col in columns}
            for row in rows:
                for col in columns:
                    val_len = len(str(_json_safe(row.get(col, ""))))
                    if val_len > col_widths[col]:
                        col_widths[col] = val_len
            
            # Build table
            lines = []
            # Header
            header = " | ".join([col.ljust(col_widths[col]) for col in columns])
            lines.append(header)
            # Separator
            separator = "-+-".join(["-" * col_widths[col] for col in columns])
            lines.append(separator)
            # Rows
            for row in rows:
                values = [str(_json_safe(row.get(col, ""))).ljust(col_widths[col]) for col in columns]
                lines.append(" | ".join(values))
            return "\n".join(lines)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"nl2sql_multimodel_v2_run_{timestamp}.txt"
    log_path = os.path.join(ROOT, "RESULTS", log_filename)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, "w", encoding="utf-8") as logf:
        logf.write("=" * 80 + "\n")
        logf.write("NL2SQL MULTI-MODEL V2 RUN LOG\n")
        logf.write("=" * 80 + "\n")
        logf.write(f"Timestamp: {datetime.now().isoformat()}\n")
        logf.write(f"Implementation: Multi-Model Optimized V2 (LangChain + Azure OpenAI)\n")
        logf.write(f"Intent Model: {INTENT_MODEL}\n")
        logf.write(f"SQL Model: {sql_model_choice}\n")
        logf.write(f"Formatting Model: {FORMATTING_MODEL}\n")
        logf.write(f"Elapsed Time: {elapsed_str}\n")
        logf.write("=" * 80 + "\n\n")
        
        logf.write("USER QUESTION:\n")
        logf.write(f"{query}\n\n")
        
        logf.write("=" * 80 + "\n")
        logf.write("INTENT & ENTITIES (extracted with gpt-4o-mini):\n")
        logf.write("=" * 80 + "\n")
        logf.write(f"{intent_entities}\n\n")
        
        if reasoning:
            logf.write("=" * 80 + "\n")
            logf.write(f"REASONING (generated with {sql_model_choice}):\n")
            logf.write("=" * 80 + "\n")
            logf.write(f"{reasoning}\n\n")
        
        if not explain_only:
            logf.write("=" * 80 + "\n")
            logf.write(f"GENERATED SQL (with {sql_model_choice}):\n")
            logf.write("=" * 80 + "\n")
            logf.write(f"{sanitized_sql}\n\n")
        
        if result_rows:
            logf.write("=" * 80 + "\n")
            logf.write("QUERY RESULTS:\n")
            logf.write("=" * 80 + "\n")
            logf.write(f"Row count: {len(result_rows)}\n\n")
            # Format as text table instead of JSON
            logf.write(_format_results_as_table(result_rows, format_type="text"))
            logf.write("\n\n")
        
        if formatted_results:
            logf.write("=" * 80 + "\n")
            logf.write(f"AI SUMMARY (generated with {FORMATTING_MODEL}):\n")
            logf.write("=" * 80 + "\n")
            logf.write(f"{formatted_results}\n\n")
        
        if exec_error:
            logf.write("=" * 80 + "\n")
            logf.write("EXECUTION ERROR:\n")
            logf.write("=" * 80 + "\n")
            logf.write(f"{exec_error}\n\n")
        
        logf.write("=" * 80 + "\n")
        logf.write("TOKEN USAGE & COST BREAKDOWN:\n")
        logf.write("=" * 80 + "\n")
        logf.write(f"Total tokens: {total_tokens:,}\n")
        logf.write(f"Total cost: ${total_cost:.6f} {currency}\n\n")
        
        for stage_name, stage_data in [
            ("Intent Extraction", _TOKEN_USAGE_BY_MODEL["intent"]),
            ("SQL Generation", _TOKEN_USAGE_BY_MODEL["sql"]),
            ("Result Formatting", _TOKEN_USAGE_BY_MODEL["formatting"])
        ]:
            if stage_data["total"] > 0:
                logf.write(f"{stage_name}:\n")
                logf.write(f"  Input tokens: {stage_data['prompt']:,}\n")
                logf.write(f"  Output tokens: {stage_data['completion']:,}\n")
                logf.write(f"  Total: {stage_data['total']:,}\n\n")
        
        logf.write("=" * 80 + "\n")
        logf.write("END OF RUN LOG\n")
        logf.write("=" * 80 + "\n")

    # ---- Also save as Markdown with timing breakdown
    log_filename_md = f"nl2sql_multimodel_v2_run_{timestamp}.md"
    log_path_md = os.path.join(ROOT, "RESULTS", log_filename_md)
    
    with open(log_path_md, "w", encoding="utf-8") as mdf:
        mdf.write("# NL2SQL Multi-Model V2 Run Log\n\n")
        mdf.write(f"**Timestamp:** {datetime.now().isoformat()}\n\n")
        mdf.write(f"**Implementation:** Multi-Model Optimized V2 (LangChain + Azure OpenAI)\n\n")
        mdf.write(f"**Total Elapsed Time:** {elapsed_str}\n\n")
        
        mdf.write("## Model Configuration\n\n")
        mdf.write(f"- **Intent Model:** `{INTENT_MODEL}`\n")
        mdf.write(f"- **SQL Model:** `{sql_model_choice}`\n")
        mdf.write(f"- **Formatting Model:** `{FORMATTING_MODEL}`\n\n")
        
        # Timing breakdown table
        mdf.write("## Timing Breakdown\n\n")
        mdf.write("| Stage | Time (seconds) |\n")
        mdf.write("|-------|---------------:|\n")
        
        total_stage_time = 0.0
        for stage_label, stage_key in [
            ("Intent Extraction", "intent_extraction"),
            ("Reasoning", "reasoning"),
            ("SQL Generation", "sql_generation"),
            ("SQL Execution", "sql_execution"),
            ("Result Formatting", "result_formatting")
        ]:
            if stage_key in stage_times:
                stage_time = stage_times[stage_key]
                mdf.write(f"| {stage_label} | {stage_time:.4f} |\n")
                total_stage_time += stage_time
        
        mdf.write(f"| **Total** | **{total_stage_time:.4f}** |\n\n")
        
        mdf.write("---\n\n")
        mdf.write("## User Question\n\n")
        mdf.write(f"```\n{query}\n```\n\n")
        
        mdf.write("---\n\n")
        mdf.write("## Intent & Entities\n\n")
        mdf.write(f"*Extracted with `{INTENT_MODEL}`*\n\n")
        mdf.write(f"```\n{intent_entities}\n```\n\n")
        
        if reasoning:
            mdf.write("---\n\n")
            mdf.write("## Reasoning\n\n")
            mdf.write(f"*Generated with `{sql_model_choice}`*\n\n")
            mdf.write(f"```\n{reasoning}\n```\n\n")
        
        if not explain_only and sanitized_sql:
            mdf.write("---\n\n")
            mdf.write("## Generated SQL\n\n")
            mdf.write(f"*Generated with `{sql_model_choice}`*\n\n")
            mdf.write(f"```sql\n{sanitized_sql}\n```\n\n")
        
        if result_rows:
            mdf.write("---\n\n")
            mdf.write("## Query Results\n\n")
            mdf.write(f"**Row count:** {len(result_rows)}\n\n")
            # Format as markdown table instead of JSON
            mdf.write(_format_results_as_table(result_rows, format_type="markdown"))
            mdf.write("\n\n")
        
        if formatted_results:
            mdf.write("---\n\n")
            mdf.write("## AI Summary\n\n")
            mdf.write(f"*Generated with `{FORMATTING_MODEL}`*\n\n")
            mdf.write(f"{formatted_results}\n\n")
        
        if exec_error:
            mdf.write("---\n\n")
            mdf.write("## Execution Error\n\n")
            mdf.write(f"```\n{exec_error}\n```\n\n")
        
        mdf.write("---\n\n")
        mdf.write("## Token Usage & Cost Breakdown\n\n")
        mdf.write(f"**Total tokens:** {total_tokens:,}\n\n")
        mdf.write(f"**Total cost:** ${total_cost:.6f} {currency}\n\n")
        
        mdf.write("| Stage | Input Tokens | Output Tokens | Total Tokens |\n")
        mdf.write("|-------|-------------:|--------------:|-------------:|\n")
        
        for stage_name, stage_key in [
            ("Intent Extraction", "intent"),
            ("SQL Generation", "sql"),
            ("Result Formatting", "formatting")
        ]:
            stage_data = _TOKEN_USAGE_BY_MODEL[stage_key]
            if stage_data["total"] > 0:
                mdf.write(f"| {stage_name} | {stage_data['prompt']:,} | {stage_data['completion']:,} | {stage_data['total']:,} |\n")
        
        mdf.write("\n---\n\n")
        mdf.write("*End of run log*\n")
    
    # ---- Download buttons for log files
    st.markdown("### 📥 Download Run Logs")
    log_cols = st.columns([1, 1, 1, 5])
    
    with log_cols[0]:
        # Download text log
        with open(log_path, "rb") as f:
            txt_data = f.read()
        st.download_button(
            label="📄 Download .txt",
            data=txt_data,
            file_name=log_filename,
            mime="text/plain",
            help="Download complete run log in text format"
        )
    
    with log_cols[1]:
        # Download markdown log
        with open(log_path_md, "rb") as f:
            md_data = f.read()
        st.download_button(
            label="📝 Download .md",
            data=md_data,
            file_name=log_filename_md,
            mime="text/markdown",
            help="Download run log in markdown format (better formatting)"
        )
    
    with log_cols[2]:
        # Download JSON summary
        json_summary = {
            "timestamp": datetime.now().isoformat(),
            "implementation": "Multi-Model Optimized V2",
            "models": {
                "intent": INTENT_MODEL,
                "sql": sql_model_choice,
                "formatting": FORMATTING_MODEL
            },
            "query": query,
            "elapsed_time_seconds": elapsed_seconds,
            "token_usage": {
                "intent": _TOKEN_USAGE_BY_MODEL["intent"],
                "sql": _TOKEN_USAGE_BY_MODEL["sql"],
                "formatting": _TOKEN_USAGE_BY_MODEL["formatting"],
                "total": total_tokens
            },
            "cost": {
                "total_usd": total_cost,
                "currency": currency
            },
            "result_count": len(result_rows) if result_rows else 0
        }
        json_data = json.dumps(json_summary, indent=2).encode("utf-8")
        st.download_button(
            label="📊 Download .json",
            data=json_data,
            file_name=f"nl2sql_multimodel_v2_run_{timestamp}.json",
            mime="application/json",
            help="Download run summary in JSON format (for analysis)"
        )
    
    st.caption(f"💾 Logs saved locally: `{log_filename}` and `{log_filename_md}`")
    
    # Optional blob upload
    if _HAS_BLOB:
        blob_conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "nl2sql-logs")
        if blob_conn_str:
            try:
                blob_service_client = BlobServiceClient.from_connection_string(blob_conn_str)
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=log_filename)
                with open(log_path, "rb") as data:
                    blob_client.upload_blob(data, overwrite=True)
                st.success(f"☁️ Uploaded to Azure Blob Storage: {log_filename}")
            except Exception as e:
                st.warning(f"Could not upload to blob storage: {e}")
