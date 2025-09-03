
import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any

# Azure Blob Storage
import tempfile
from urllib.parse import quote as urlquote
try:
    from azure.storage.blob import BlobServiceClient
    _HAS_BLOB = True
except ImportError:
    _HAS_BLOB = False

import streamlit as st
from dotenv import load_dotenv

# Ensure repo root on sys.path so we can import pipeline modules
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv()

# Import pipeline helpers from root modules
from nl2sql_main import (
    parse_nl_query,
    generate_reasoning,
    generate_sql,
    extract_and_sanitize_sql,
    _TOKEN_USAGE,
    _get_pricing_for_deployment,
    DEPLOYMENT_NAME,
    _format_table,
)
from schema_reader import refresh_schema_cache, get_sql_database_schema_context
from sql_executor import execute_sql_query

# ------------ UI Config ------------
st.set_page_config(
    page_title="NL2SQL Demo",
    page_icon="🧠",
    layout="wide",
)

def _load_examples() -> List[str]:
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
        ]
    # Limit to a reasonable number for buttons
    return examples[:12]

EXAMPLE_QUESTIONS: List[str] = _load_examples()

# Sidebar controls
with st.sidebar:
    st.title("NL2SQL Demo UI")
    st.caption("Natural Language → Intent → Reasoning → SQL → Results")
    # Environment status
    with st.expander("Environment status", expanded=False):
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        dep = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        sql_server = os.getenv("AZURE_SQL_SERVER")
        sql_db = os.getenv("AZURE_SQL_DB")
        sql_user = os.getenv("AZURE_SQL_USER")
        sql_pwd = os.getenv("AZURE_SQL_PASSWORD")
        def ok(v: Any) -> str:
            return "✅" if v else "⚠️"
        st.write(f"Azure OpenAI Key {ok(api_key)}")
        st.write(f"Azure OpenAI Endpoint {ok(endpoint)}")
        st.write(f"Deployment {ok(dep)}")
        st.write(f"SQL Server {ok(sql_server)} | DB {ok(sql_db)} | User {ok(sql_user)} | Password {ok(sql_pwd)}")
    if st.button("🔁 Refresh schema cache"):
        try:
            path = refresh_schema_cache()
            st.success(f"Schema cache refreshed: {path}")
        except Exception as e:
            st.error(f"Failed to refresh schema cache: {e}")
    with st.expander("Current schema context (preview)", expanded=False):
        ctx = get_sql_database_schema_context(ttl_seconds=0)
        st.code(ctx[:4000], language="text")


# Main layout
st.markdown("""
<h1 style='text-align: left;'>Contoso-FI Natural Language to SQL Analytics</h1>
<p style='font-size:1.1em;'>
<b>Ask questions in plain English and get instant, explainable SQL and results from the Contoso-FI financial dataset.</b><br>
This app lets you explore a realistic banking/loans database using natural language. It generates SQL, explains its reasoning, and runs the query live against Azure SQL.<br><br>
<b>About the data:</b> The <b>Contoso-FI</b> dataset models a mid-size financial institution, with tables for loans, companies, collateral, covenants, payments, risk, and more. You can ask about loan portfolios, top companies, regional breakdowns, risk metrics, and other financial insights.
</p>
""", unsafe_allow_html=True)

# Example questions pills
st.markdown("### Examples")
cols = st.columns(min(3, len(EXAMPLE_QUESTIONS)))
for i, q in enumerate(EXAMPLE_QUESTIONS):
    with cols[i % len(cols)]:
        if st.button(q, key=f"ex_{i}"):
            st.session_state["input_query"] = q

# Input area
query = st.text_area(
    "Enter your question",
    value=st.session_state.get("input_query", "Show the 10 most recent loans"),
    height=80,
)

# Right-aligned controls row: large spacer + controls
controls_cols = st.columns([6, 2, 2, 2, 2])
with controls_cols[1]:
    run_clicked = st.button("Run", type="primary")
with controls_cols[2]:
    no_exec = st.toggle("⏭️ Skip exec", value=False, help="Generate SQL but do not run it", key="skip_exec_toggle")
with controls_cols[3]:
    explain_only = st.toggle("📝 Explain-only", value=False, help="Show intent and reasoning only; skip SQL generation and execution", key="explain_only_toggle")
with controls_cols[4]:
    no_reasoning = st.toggle("🧠 No reasoning", value=False, help="Skip the reasoning/plan step", key="no_reasoning_toggle")

if run_clicked:
    # Reset token usage counters for a new run
    _TOKEN_USAGE["prompt"] = 0
    _TOKEN_USAGE["completion"] = 0
    _TOKEN_USAGE["total"] = 0
    result_rows: List[Dict[str, Any]] | None = None
    exec_error: str | None = None

    if not query.strip():
        st.warning("Please enter a question.")
        st.stop()

    # Orchestrate pipeline
    with st.spinner("Extracting intent and entities..."):
        intent_entities = parse_nl_query(query)

    st.markdown("### Intent & Entities")
    st.write(intent_entities)

    reasoning = None
    if not no_reasoning or explain_only:
        with st.spinner("Generating reasoning plan..."):
            reasoning = generate_reasoning(intent_entities)
        with st.expander("Reasoning (high-level plan)", expanded=True):
            st.write(reasoning)

    if not explain_only:
        with st.spinner("Generating SQL..."):
            raw_sql = generate_sql(intent_entities)

    if not explain_only:
        st.markdown("### Generated SQL (raw)")
        st.code(raw_sql, language="sql")

    if not explain_only:
        sanitized_sql = extract_and_sanitize_sql(raw_sql)
        if sanitized_sql != raw_sql:
            st.markdown("### Sanitized SQL (for execution)")
            st.code(sanitized_sql, language="sql")

    if not explain_only and not no_exec:
        with st.spinner("Executing SQL against Azure SQL Database..."):
            try:
                rows: List[Dict[str, Any]] = execute_sql_query(sanitized_sql)
                if rows:
                    st.markdown("### Results")
                    st.dataframe(rows, width='stretch')
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

    # Token usage and cost
    from nl2sql_main import _TOKEN_USAGE as TOK
    in_price_1k, out_price_1k, src, currency = _get_pricing_for_deployment(DEPLOYMENT_NAME)
    prompt_t = TOK["prompt"]
    completion_t = TOK["completion"]
    total_t = TOK["total"] or (prompt_t + completion_t)
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

    # Persist run artifact similar to CLI
    safe_query = query.strip().replace(" ", "_")[:40]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"nl2sql_run_{safe_query}_{ts}.txt"
    results_dir = os.path.join(ROOT, "RESULTS")
    os.makedirs(results_dir, exist_ok=True)
    run_summary = [
        "========== NATURAL LANGUAGE QUERY ==========\n",
        query + "\n\n",
        "========== INTENT & ENTITIES ==========\n",
        intent_entities + "\n\n",
    ]
    if reasoning is not None:
        run_summary += [
            "========== SQL GENERATION REASONING ==========\n",
            reasoning + "\n\n",
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
    in_price_1k_log, out_price_1k_log, src_log, currency_log = _get_pricing_for_deployment(DEPLOYMENT_NAME)
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
    blob_url = None
    blob_error = None
    try:
        txt_path = os.path.join(results_dir, out_filename)
        with open(txt_path, "w") as f:
            for line in run_summary:
                f.write(line)
        # If we have results, also write JSON sidecar for programmatic reuse
        sidecar_msg = ""
        if result_rows is not None:
            json_name = out_filename.replace(".txt", ".json")
            json_path = os.path.join(results_dir, json_name)
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(result_rows, jf, ensure_ascii=False, indent=2)
            sidecar_msg = f"; JSON rows written to RESULTS/{json_name}"
        # Upload to Azure Blob Storage if possible
        AZURE_BLOB_CONN = os.getenv("AZURE_BLOB_CONNECTION_STRING")
    BLOB_CONTAINER = "nl2sql"
    STORAGE_ACCOUNT = "r2d2nl2sql"
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
