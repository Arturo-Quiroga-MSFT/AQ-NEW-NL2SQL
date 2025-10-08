
"""Streamlit UI for the Contoso-FI NL2SQL Demo using Azure AI Agent Service.

High-level flow when the user presses Run:
 1. Reset token counters.
 2. Extract intent and entities from natural language using Azure AI Agent.
 3. (Optional) Generate a reasoning / high-level plan explanation (if needed).
 4. Generate raw SQL from the intent using Azure AI Agent.
 5. Sanitize / extract runnable SQL (adds warnings or modifications if needed).
 6. (Optional) Execute SQL against Azure SQL and display tabular results.
 7. Display token usage + estimated cost (based on pricing map).
 8. Persist a detailed run log (mirrors CLI log format) locally and optionally upload
    to Azure Blob Storage for durable retrieval / sharing.

This file uses the Azure AI Agent Service pipeline from nl2sql_standalone_AzureAI.
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import List, Dict, Any

###############################################################################
# Optional Azure Blob Storage integration (for uploading run logs)
# If azure-storage-blob isn't installed, uploads are simply skipped.
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

# Ensure repository root is on sys.path so we can import project modules directly
# Get the absolute path of this file first
CURRENT_FILE = os.path.abspath(__file__)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_FILE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Add nl2sql_standalone_AzureAI to path for module imports
AZUREAI_DIR = os.path.join(ROOT, "nl2sql_standalone_AzureAI")
if AZUREAI_DIR not in sys.path:
    sys.path.insert(0, AZUREAI_DIR)

load_dotenv()

# Import pipeline helpers from Azure AI implementation
from nl2sql_main import (
    extract_intent,              # Natural language → structured intent/entities using AI Agent
    generate_sql,                # Intent/entities → candidate SQL using AI Agent
    extract_and_sanitize_sql,    # Cleans / warns / final SQL to execute
    _TOKEN_USAGE,                # Shared mutable token usage accumulator
    _get_pricing_for_deployment, # Lookup per-1K token pricing for current model
    MODEL_DEPLOYMENT_NAME,       # Active Azure AI model deployment name
    PROJECT_ENDPOINT,            # Azure AI Foundry project endpoint
    _format_table,               # Utility for fixed-width text table formatting
)
from schema_reader import refresh_schema_cache, get_sql_database_schema_context
from sql_executor import execute_sql_query

# -----------------------------------------------------------------------------
# Streamlit Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="NL2SQL Demo (Azure AI Agents)",
    page_icon="🤖",
    layout="wide",
)

def _load_examples() -> List[str]:
    """Load example NL questions for quick-access buttons.

    Primary source: docs/CONTOSO-FI_EXAMPLE_QUESTIONS.txt (if present).
    Fallback: Hard-coded curated list for discoverability.
    Only the first 12 are returned to avoid overcrowding the UI.
    """
    path = os.path.join(ROOT, "docs", "CONTOSO-FI_EXAMPLE_QUESTIONS.txt")
    examples: List[str] = []
    # Debug: print resolved path and file existence
    print(f"[DEBUG] Looking for example questions at: {path}")
    print(f"[DEBUG] File exists: {os.path.exists(path)}")
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Lines beginning with a number and ')' are questions
                if line[0].isdigit() and ")" in line[:4]:
                    # Remove leading ordinal like '1) '
                    q = line.split(")", 1)[1].strip()
                    examples.append(q)
    except Exception as e:
        print(f"[DEBUG] Exception reading example questions: {e}")
    # Fallback defaults if file missing
    if not examples:
        examples = [
            "Show the 10 most recent loans by OriginationDate.",
            "For each company with loans, compute total principal amount; show the top 20 companies by total principal.",
            "For each region, list the top 5 companies by total principal amount.",
            "List all currencies and their symbols available in the database.",
            "Identify loans with upcoming covenant tests in the next 30 days.",
            "For each loan, compute the remaining balance and show the top 10 by balance.",
            "By region, list the top 10 companies by total outstanding loan amount.",
            "Show all companies with more than 3 active loans.",
            "Show all loans with fixed interest rates above 7%.",
            "List the top 10 customers by total collateral value.",
            "For each region, show the number of loans and the sum of principal amounts.",
        ]
    # Limit to a reasonable number for buttons
    return examples[:12]

EXAMPLE_QUESTIONS: List[str] = _load_examples()

# -----------------------------------------------------------------------------
# Sidebar: Environment status, schema refresh, schema preview
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("NL2SQL Demo UI")
    st.caption("**Azure AI Agent Service** Implementation")
    st.caption("Natural Language → Intent (AI Agent) → SQL (AI Agent) → Results")
    
    # Environment status
    with st.expander("Environment status", expanded=False):
        project_endpoint = os.getenv("PROJECT_ENDPOINT")
        model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")
        sql_server = os.getenv("AZURE_SQL_SERVER")
        sql_db = os.getenv("AZURE_SQL_DB")
        sql_user = os.getenv("AZURE_SQL_USER")
        sql_pwd = os.getenv("AZURE_SQL_PASSWORD")
        def ok(v: Any) -> str:
            return "✅" if v else "⚠️"
        st.write(f"Azure AI Project Endpoint {ok(project_endpoint)}")
        st.write(f"Model Deployment {ok(model_deployment)}")
        st.write(f"SQL Server {ok(sql_server)} | DB {ok(sql_db)} | User {ok(sql_user)} | Password {ok(sql_pwd)}")
    
    # Manual schema cache refresh (forces re-reading DB metadata / cached file)
    if st.button("🔁 Refresh schema cache"):
        try:
            path = refresh_schema_cache()
            st.success(f"Schema cache refreshed: {path}")
        except Exception as e:
            st.error(f"Failed to refresh schema cache: {e}")
    
    with st.expander("Current schema context (preview)", expanded=False):
        ctx = get_sql_database_schema_context(ttl_seconds=0)
        st.code(ctx[:4000], language="text")


# -----------------------------------------------------------------------------
# Main page header & descriptive blurb
# -----------------------------------------------------------------------------
st.markdown("""
<h1 style='text-align: left;'>🤖 Contoso-FI NL2SQL with Azure AI Agents</h1>
<p style='font-size:1.1em;'>
<b>Ask questions in plain English and get instant, explainable SQL and results powered by Azure AI Agent Service.</b><br>
This app lets you explore a realistic banking/loans database using natural language. It uses <b>Azure AI Agents</b> to generate SQL, explain its reasoning, and run queries live against Azure SQL.<br><br>
<b>About the data:</b> The <b>Contoso-FI</b> dataset models a mid-size financial institution, with tables for loans, companies, collateral, covenants, payments, risk, and more. You can ask about loan portfolios, top companies, regional breakdowns, risk metrics, and other financial insights.<br><br>
<b>🆚 Difference:</b> This version uses <b>Azure AI Foundry Agent Service</b> instead of LangChain for better Azure integration and agent management.
</p>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Example question buttons (quick inserts into the query box)
# -----------------------------------------------------------------------------
st.markdown("### Examples")
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
# Control toggles:
#  - Run: Execute full pipeline
#  - Skip exec: Stop after SQL generation
#  - No reasoning: Skip reasoning step (faster) - Note: Azure AI version doesn't have separate reasoning step
# -----------------------------------------------------------------------------
controls_cols = st.columns([6, 2, 2, 2])
with controls_cols[1]:
    run_clicked = st.button("Run", type="primary")
with controls_cols[2]:
    no_exec = st.toggle("⏭️ Skip exec", value=False, help="Generate SQL but do not run it", key="skip_exec_toggle")
with controls_cols[3]:
    explain_only = st.toggle("📝 Explain-only", value=False, help="Show intent only; skip SQL generation and execution", key="explain_only_toggle")

if run_clicked:
    # -------------------------------------------------------------------------
    # PIPELINE ORCHESTRATION
    # -------------------------------------------------------------------------
    # Start timer for elapsed time tracking
    start_time = time.time()
    
    # Display run configuration context
    st.markdown("---")
    with st.expander("⚙️ Run Configuration", expanded=False):
        config_cols = st.columns(2)
        with config_cols[0]:
            st.markdown("**Azure AI Agent Service Settings:**")
            st.write(f"🤖 **Model/Deployment:** `{MODEL_DEPLOYMENT_NAME or 'Not configured'}`")
            endpoint_display = PROJECT_ENDPOINT or "Not set"
            # Show just the hostname for cleaner display
            if endpoint_display.startswith("http"):
                from urllib.parse import urlparse
                endpoint_display = urlparse(endpoint_display).netloc
            st.write(f"🌐 **Project Endpoint:** `{endpoint_display}`")
            st.write(f"🏗️ **Service:** Azure AI Foundry Agent Service")
        
        with config_cols[1]:
            st.markdown("**Database Settings:**")
            sql_server = os.getenv("AZURE_SQL_SERVER", "Not set")
            sql_db = os.getenv("AZURE_SQL_DB", "Not set")
            st.write(f"🗄️ **SQL Server:** `{sql_server}`")
            st.write(f"📊 **Database:** `{sql_db}`")
            st.markdown("**Pipeline Options:**")
            st.write(f"{'✅' if not no_exec else '❌'} SQL execution enabled")
            st.write(f"{'✅' if explain_only else '❌'} Explain-only mode")
    
    st.markdown("---")
    
    # Reset token usage counters for a new run. (Shared dict mutated by
    # lower-level functions called during LLM interactions.)
    _TOKEN_USAGE["prompt"] = 0
    _TOKEN_USAGE["completion"] = 0
    _TOKEN_USAGE["total"] = 0
    result_rows: List[Dict[str, Any]] | None = None
    exec_error: str | None = None

    if not query.strip():
        st.warning("Please enter a question.")
        st.stop()

    # ---- Step 1: NL parsing / intent extraction using Azure AI Agent
    with st.spinner("Extracting intent and entities using Azure AI Agent..."):
        intent_entities = extract_intent(query)

    st.markdown("### Intent & Entities")
    st.write(intent_entities)

    # Note: Azure AI version doesn't have separate reasoning step in this implementation
    # The agent itself handles reasoning internally

    # ---- Step 2: Raw SQL generation using Azure AI Agent
    if not explain_only:
        with st.spinner("Generating SQL using Azure AI Agent..."):
            raw_sql = generate_sql(intent_entities)

    if not explain_only:
        st.markdown("### Generated SQL (raw)")
        st.code(raw_sql, language="sql")

    # ---- Step 3: SQL sanitization / extraction (adds warnings, ensures safety)
    if not explain_only:
        sanitized_sql = extract_and_sanitize_sql(raw_sql)
        if sanitized_sql != raw_sql:
            st.markdown("### Sanitized SQL (for execution)")
            st.code(sanitized_sql, language="sql")

    # ---- Step 4: Execute final SQL if not skipped
    if not explain_only and not no_exec:
        with st.spinner("Executing SQL against Azure SQL Database..."):
            try:
                rows: List[Dict[str, Any]] = execute_sql_query(sanitized_sql)
                if rows:
                    st.markdown("### Results")
                    st.dataframe(rows, use_container_width=True)
                    result_rows = rows
                    # Export buttons
                    exp_cols = st.columns([1,1,1,6])
                    with exp_cols[0]:
                        csv_data = None
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
                            xlsx_bytes = None
                            df = pd.DataFrame(rows)
                            from io import BytesIO
                            bio = BytesIO()
                            with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
                                df.to_excel(writer, index=False, sheet_name="Results")
                            xlsx_bytes = bio.getvalue()
                            st.download_button("⬇️ Download Excel", data=xlsx_bytes, file_name="results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                        except Exception:
                            pass
                    with exp_cols[2]:
                        # Copy SQL button (shows a copyable text area)
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

    # ---- Step 5: Token usage + estimated cost panel
    # Use the _TOKEN_USAGE already imported at the top
    TOK = _TOKEN_USAGE
    in_price_1k, out_price_1k, src, currency = _get_pricing_for_deployment(MODEL_DEPLOYMENT_NAME)
    prompt_t = TOK["prompt"]
    completion_t = TOK["completion"]
    total_t = TOK["total"] or (prompt_t + completion_t)
    
    # Calculate elapsed time
    end_time = time.time()
    elapsed_seconds = end_time - start_time
    elapsed_str = f"{elapsed_seconds:.2f}s"
    if elapsed_seconds >= 60:
        minutes = int(elapsed_seconds // 60)
        seconds = elapsed_seconds % 60
        elapsed_str = f"{minutes}m {seconds:.2f}s"
    
    # Display elapsed time prominently
    st.markdown(f"### ⏱️ Total Elapsed Time: **{elapsed_str}**")
    
    with st.expander("Token usage & estimated cost", expanded=False):
        st.write({
            "prompt_tokens": prompt_t,
            "completion_tokens": completion_t,
            "total_tokens": total_t,
            "pricing_source": src,
            "currency": currency,
        })
        if in_price_1k is not None and out_price_1k is not None:
            input_cost = (prompt_t / 1000.0) * in_price_1k
            output_cost = (completion_t / 1000.0) * out_price_1k
            total_cost = input_cost + output_cost
            st.success(
                f"Estimated cost ({currency}): {total_cost:.6f}  "
                f"[input={input_cost:.6f}, output={output_cost:.6f}; per-1k: in={in_price_1k}, out={out_price_1k}; source={src}]"
            )
        else:
            st.info("Pricing not configured. See repo README for configuration options.")

    # ---- Step 6: Persist run artifact (human-readable log + optional JSON rows)
    # Mirrors CLI logging format: sections separated by banners.
    safe_query = query.strip().replace(" ", "_")[:40]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"nl2sql_azureai_run_{safe_query}_{ts}.txt"
    results_dir = os.path.join(ROOT, "RESULTS")
    os.makedirs(results_dir, exist_ok=True)
    
    # Prepare run configuration section for log
    run_config_section = [
        "========== RUN CONFIGURATION ==========\n",
        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"Implementation: Azure AI Foundry Agent Service\n",
        f"Model/Deployment: {MODEL_DEPLOYMENT_NAME or 'Not configured'}\n",
        f"Project Endpoint: {PROJECT_ENDPOINT or 'Not set'}\n",
        f"SQL Server: {os.getenv('AZURE_SQL_SERVER', 'Not set')}\n",
        f"Database: {os.getenv('AZURE_SQL_DB', 'Not set')}\n",
        f"Pipeline Options:\n",
        f"  - SQL execution: {'enabled' if not no_exec else 'disabled'}\n",
        f"  - Explain-only mode: {'yes' if explain_only else 'no'}\n",
        "\n",
    ]
    
    run_summary = run_config_section + [
        "========== NATURAL LANGUAGE QUERY ==========\n",
        query + "\n\n",
        "========== INTENT & ENTITIES (AI AGENT) ==========\n",
        intent_entities + "\n\n",
    ]
    
    if not explain_only:
        run_summary += [
            "========== GENERATED SQL (RAW) ==========\n",
            raw_sql + "\n\n",
        ]
        if 'sanitized_sql' in locals():
            run_summary += [
                "========== SANITIZED SQL (FOR EXECUTION) ==========\n",
                sanitized_sql + "\n\n",
            ]
        if result_rows is not None:
            table_text, table_lines = _format_table(result_rows)
            run_summary += [
                "========== SQL QUERY RESULTS (TABLE) ==========\n",
            ] + [line + "\n" for line in table_lines] + ["\n"]
        if exec_error is not None:
            run_summary += [
                "========== SQL QUERY ERROR ==========\n",
                exec_error + "\n\n",
            ]
    
    # Token usage & cost (append to log similar to CLI)
    in_price_1k_log, out_price_1k_log, src_log, currency_log = _get_pricing_for_deployment(MODEL_DEPLOYMENT_NAME)
    prompt_t_log = TOK["prompt"]
    completion_t_log = TOK["completion"]
    total_t_log = TOK["total"] or (prompt_t_log + completion_t_log)
    if in_price_1k_log is not None and out_price_1k_log is not None:
        input_cost = (prompt_t_log / 1000.0) * in_price_1k_log
        output_cost = (completion_t_log / 1000.0) * out_price_1k_log
        total_cost = input_cost + output_cost
        run_summary += [
            "========== TOKEN USAGE & COST ==========\n",
            f"Input tokens: {prompt_t_log}\n",
            f"Completion tokens: {completion_t_log}\n",
            f"Total tokens: {total_t_log}\n",
            (
                f"Estimated cost ({currency_log}): {total_cost:.6f}  "
                f"[input={input_cost:.6f}, output={output_cost:.6f}; per-1k: in={in_price_1k_log}, out={out_price_1k_log}; source={src_log}]\n\n"
            ),
        ]
    else:
        run_summary += [
            "========== TOKEN USAGE ==========\n",
            f"Input tokens: {prompt_t_log}\n",
            f"Completion tokens: {completion_t_log}\n",
            f"Total tokens: {total_t_log}\n",
            "[INFO] Pricing not configured. See README for env vars or azure_openai_pricing.json.\n\n",
        ]
    
    # Add elapsed time to run summary
    run_summary += [
        "========== EXECUTION TIME ==========\n",
        f"Total elapsed time: {elapsed_str} ({elapsed_seconds:.3f} seconds)\n\n",
    ]
    
    blob_url = None          # Public URL (if uploaded successfully)
    blob_error = None        # Capture upload exception message for user feedback
    # NOTE: Adjust these defaults if deploying to a different storage account
    # or container. The connection string is sourced from env var
    # AZURE_BLOB_CONNECTION_STRING.
    BLOB_CONTAINER = "nl2sql"
    STORAGE_ACCOUNT = "r2d2nl2sql"
    try:
        txt_path = os.path.join(results_dir, out_filename)
        with open(txt_path, "w") as f:
            for line in run_summary:
                f.write(line)
        # If we have results, also write JSON sidecar for programmatic reuse
        sidecar_msg = ""
        if result_rows is not None:
            import datetime as _dt
            from decimal import Decimal
            def _json_safe(obj):
                if isinstance(obj, (list, tuple)):
                    return [_json_safe(x) for x in obj]
                if isinstance(obj, dict):
                    return {k: _json_safe(v) for k, v in obj.items()}
                if isinstance(obj, (_dt.date, _dt.datetime)):
                    return obj.isoformat()
                if isinstance(obj, Decimal):
                    return float(obj)
                return obj
            json_name = out_filename.replace(".txt", ".json")
            json_path = os.path.join(results_dir, json_name)
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(_json_safe(result_rows), jf, ensure_ascii=False, indent=2)
            sidecar_msg = f"; JSON rows written to RESULTS/{json_name}"
        # Upload to Azure Blob Storage if possible
        AZURE_BLOB_CONN = os.getenv("AZURE_BLOB_CONNECTION_STRING")
        if _HAS_BLOB and AZURE_BLOB_CONN:
            try:
                blob_service = BlobServiceClient.from_connection_string(AZURE_BLOB_CONN)
                container_client = blob_service.get_container_client(BLOB_CONTAINER)
                # Upload log file
                with open(txt_path, "rb") as data:
                    container_client.upload_blob(out_filename, data, overwrite=True)
                blob_url = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net/{BLOB_CONTAINER}/{urlquote(out_filename)}"
            except Exception as ex:
                blob_error = str(ex)
        # Show download link if uploaded
        if blob_url:
            st.success(f"Run log uploaded to Azure Blob Storage: [Download log]({blob_url}){sidecar_msg}")
        else:
            st.caption(f"Run log written to RESULTS/{out_filename}{sidecar_msg}")
            if blob_error:
                st.warning(f"Blob upload failed: {blob_error}")
        # Optionally, offer direct download from local file (for local runs)
        with open(txt_path, "rb") as f:
            st.download_button("⬇️ Download log file", data=f, file_name=out_filename, mime="text/plain")
    except Exception as ex:
        st.error(f"Failed to write or upload run log: {ex}")
