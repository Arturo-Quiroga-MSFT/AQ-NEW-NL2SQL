"""
nl2sql_main.py — NL → Intent → SQL pipeline (diagram-aligned)
=============================================================

Overview
--------
This entrypoint implements the NL→SQL path shown in the NL2SQL flowchart. It mirrors
the sequence from the older prototype but excludes DAX. The commentary highlights each
decision node and step in the diagram.

What it does
------------
1) Extract intent and entities from a natural language question
2) Generate a T‑SQL query using schema‑aware prompting
3) Sanitize/extract the SQL code from the LLM output
4) Execute the SQL against Azure SQL Database
5) Print results in a formatted table and persist the full run output to a file

Relevant CLI flags (map to decision nodes)
------------------------------------------
--query            Provide the question inline, otherwise you’ll be prompted
--refresh-schema   Refresh schema cache before generation
--no-reasoning     Skip the reasoning/plan step
--explain-only     Show intent + reasoning only, skip SQL & execution
--no-exec          Generate SQL but don’t execute
--whoami           Print script purpose and exit

Requirements
------------
- Environment variables for Azure OpenAI and Azure SQL (see README/.env):
    AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_API_VERSION,
    AZURE_SQL_SERVER, AZURE_SQL_DB, AZURE_SQL_USER, AZURE_SQL_PASSWORD
- Python packages: langchain-openai, langchain, python-dotenv, pyodbc, requests
"""

import os
import re
import sys
import time
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate

# Load environment variables early
load_dotenv()

# Azure OpenAI configuration
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
# Allow overriding Azure OpenAI REST api-version via env; default to latest preview suited for GPT-5 Chat Completions
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")

# Note on o-series/GPT‑5 models:
# According to Azure documentation, reasoning models (o-series and gpt-5)
# do NOT support temperature/top_p/presence_penalty/frequency_penalty with Chat Completions.
# Ref: https://learn.microsoft.com/azure/ai-foundry/openai/how-to/reasoning#api-&-feature-support

# Helper: detect o-series and gpt‑5 deployments which do not support temperature/top_p
def _is_reasoning_like_model(deployment_name: str | None) -> bool:
    name = (deployment_name or "").lower()
    return name.startswith("o") or name.startswith("gpt-5")


_USING_REASONING_STYLE = _is_reasoning_like_model(DEPLOYMENT_NAME)


def _make_llm():
    """Create an LLM instance for non‑reasoning models; return None for o*/gpt‑5.

    For o-series/gpt‑5 deployments, we avoid LangChain defaults that may send unsupported
    parameters and instead use a direct HTTP call path. For non‑o-series, we use the
    AzureChatOpenAI LangChain wrapper with the configured api_version.
    """
    if _USING_REASONING_STYLE:
        return None  # We'll use direct Azure Chat Completions calls without temperature
    return AzureChatOpenAI(
        openai_api_key=API_KEY,
        azure_endpoint=ENDPOINT,
        deployment_name=DEPLOYMENT_NAME,
        api_version=API_VERSION,
        max_tokens=8192,
    )


llm = _make_llm()

# ---------- Token usage & pricing accumulation ----------

# Accumulator for token usage across all calls in a run
_TOKEN_USAGE = {"prompt": 0, "completion": 0, "total": 0}


def _accumulate_usage(usage: Optional[Dict[str, Any]]) -> None:
    """Accumulate token usage dicts of shape like {'prompt_tokens': int, 'completion_tokens': int, 'total_tokens': int}."""
    if not usage:
        return
    _TOKEN_USAGE["prompt"] += int(usage.get("prompt_tokens", 0) or 0)
    _TOKEN_USAGE["completion"] += int(usage.get("completion_tokens", 0) or 0)
    _TOKEN_USAGE["total"] += int(usage.get("total_tokens", 0) or (_TOKEN_USAGE["prompt"] + _TOKEN_USAGE["completion"]))


def _extract_usage_from_langchain_message(msg: Any) -> Optional[Dict[str, Any]]:
    """Best-effort extraction of token usage from LangChain AIMessage/Message results."""
    try:
        # Newer langchain puts token usage in response_metadata.token_usage
        meta = getattr(msg, "response_metadata", None) or {}
        token_usage = meta.get("token_usage")
        if token_usage and isinstance(token_usage, dict):
            return {
                "prompt_tokens": token_usage.get("prompt_tokens") or token_usage.get("input_tokens") or 0,
                "completion_tokens": token_usage.get("completion_tokens") or token_usage.get("output_tokens") or 0,
                "total_tokens": token_usage.get("total_tokens")
                or (token_usage.get("prompt_tokens", 0) or 0)
                + (token_usage.get("completion_tokens", 0) or 0),
            }
        # Some versions expose usage_metadata directly
        um = getattr(msg, "usage_metadata", None)
        if um and isinstance(um, dict):
            return {
                "prompt_tokens": um.get("input_tokens") or um.get("prompt_tokens") or 0,
                "completion_tokens": um.get("output_tokens") or um.get("completion_tokens") or 0,
                "total_tokens": um.get("total_tokens")
                or (um.get("input_tokens", 0) or 0) + (um.get("output_tokens", 0) or 0),
            }
    except Exception:
        pass
    return None


def _normalize_dep_to_env_key(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", (name or "")).upper().strip("_")


def _load_pricing_config() -> Dict[str, Dict[str, float]]:
    """Load optional pricing map from azure_openai_pricing.json at repo root.

    Expected JSON shape:
    {
      "<DEPLOYMENT_NAME_LOWER>": {"input_per_1k": 2.5, "output_per_1k": 10.0}
    }
    Returns empty dict if file not present or invalid.
    """
    try:
        repo_root = os.path.dirname(__file__)
        config_path = os.path.join(repo_root, "azure_openai_pricing.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def _get_target_currency() -> str:
    """Return desired currency code (USD or CAD). Defaults to USD."""
    cur = (os.getenv("AZURE_OPENAI_PRICE_CURRENCY", "USD") or "USD").upper()
    if cur not in ("USD", "CAD"):
        cur = "USD"
    return cur


def _convert_currency(amount: float, from_currency: str, to_currency: str) -> Optional[float]:
    """Convert between USD and CAD using env-provided rates when available.

    Supported env vars:
    - AZURE_OPENAI_PRICE_USD_TO_CAD
    - AZURE_OPENAI_PRICE_CAD_TO_USD
    Returns None if conversion isn't possible.
    """
    if from_currency == to_currency:
        return amount
    if from_currency == "USD" and to_currency == "CAD":
        rate = os.getenv("AZURE_OPENAI_PRICE_USD_TO_CAD")
        if rate:
            try:
                return amount * float(rate)
            except ValueError:
                return None
    if from_currency == "CAD" and to_currency == "USD":
        rate = os.getenv("AZURE_OPENAI_PRICE_CAD_TO_USD")
        if rate:
            try:
                return amount * float(rate)
            except ValueError:
                return None
    return None


def _get_pricing_for_deployment(dep_name: Optional[str]) -> Tuple[Optional[float], Optional[float], str, str]:
    """Resolve pricing (per 1K tokens) for input/output based on env or optional JSON with currency support.

    Priority order:
    1) AZURE_OPENAI_PRICE_<DEPLOYMENT>_INPUT_PER_1K and ..._OUTPUT_PER_1K
    2) AZURE_OPENAI_PRICE_INPUT_PER_1K and AZURE_OPENAI_PRICE_OUTPUT_PER_1K (global fallback)
    3) azure_openai_pricing.json mapping by deployment name (lowercased keys), supporting either flat prices or per-currency maps

    Returns (input_price_per_1k, output_price_per_1k, source_string, currency_code)
    """
    dep = dep_name or ""
    dep_key = _normalize_dep_to_env_key(dep)
    target_cur = _get_target_currency()
    # 1) Deployment-specific env vars
    in_env = os.getenv(f"AZURE_OPENAI_PRICE_{dep_key}_INPUT_PER_1K")
    out_env = os.getenv(f"AZURE_OPENAI_PRICE_{dep_key}_OUTPUT_PER_1K")
    if in_env and out_env:
        try:
            return float(in_env), float(out_env), f"env:{dep_key}", target_cur
        except ValueError:
            pass
    # 2) Global env fallback
    in_glob = os.getenv("AZURE_OPENAI_PRICE_INPUT_PER_1K")
    out_glob = os.getenv("AZURE_OPENAI_PRICE_OUTPUT_PER_1K")
    if in_glob and out_glob:
        try:
            return float(in_glob), float(out_glob), "env:global", target_cur
        except ValueError:
            pass
    # 3) Optional JSON file mapping
    pricing_map = _load_pricing_config()
    if pricing_map:
        entry = pricing_map.get(dep.lower()) or pricing_map.get(dep)
        if entry and isinstance(entry, dict):
            # If entry is flat (legacy): assume USD unless otherwise specified
            if "input_per_1k" in entry and "output_per_1k" in entry:
                try:
                    in_usd = float(entry.get("input_per_1k"))
                    out_usd = float(entry.get("output_per_1k"))
                    if target_cur == "USD":
                        return in_usd, out_usd, "file:azure_openai_pricing.json", "USD"
                    # Try convert to CAD
                    in_cad = _convert_currency(in_usd, "USD", target_cur)
                    out_cad = _convert_currency(out_usd, "USD", target_cur)
                    if in_cad is not None and out_cad is not None:
                        return in_cad, out_cad, "file:azure_openai_pricing.json (converted)", target_cur
                    # No conversion rate; fall back to USD values with note
                    return in_usd, out_usd, "file:azure_openai_pricing.json (USD; no conversion)", "USD"
                except Exception:
                    pass
            # New per-currency nested format { "USD": {...}, "CAD": {...} }
            cur_block = entry.get(target_cur)
            if isinstance(cur_block, dict) and "input_per_1k" in cur_block and "output_per_1k" in cur_block:
                try:
                    return float(cur_block["input_per_1k"]), float(cur_block["output_per_1k"]), "file:azure_openai_pricing.json", target_cur
                except Exception:
                    pass
            # If target currency missing, try USD and convert
            usd_block = entry.get("USD")
            if isinstance(usd_block, dict) and "input_per_1k" in usd_block and "output_per_1k" in usd_block:
                try:
                    in_usd = float(usd_block["input_per_1k"])
                    out_usd = float(usd_block["output_per_1k"])
                    if target_cur == "USD":
                        return in_usd, out_usd, "file:azure_openai_pricing.json", "USD"
                    in_conv = _convert_currency(in_usd, "USD", target_cur)
                    out_conv = _convert_currency(out_usd, "USD", target_cur)
                    if in_conv is not None and out_conv is not None:
                        return in_conv, out_conv, "file:azure_openai_pricing.json (converted)", target_cur
                    return in_usd, out_usd, "file:azure_openai_pricing.json (USD; no conversion)", "USD"
                except Exception:
                    pass
    return None, None, "unset", _get_target_currency()

# ---------- Prompt setup (diagram: Intent → Reasoning → SQL) ----------

# Shared prompt text constants (reused for direct API calls)
INTENT_PROMPT_TEXT = (
    """
    You are an expert in translating natural language to database queries. Extract the intent and entities from the following user input:
    {input}
    """
)
SQL_PROMPT_TEXT = (
    """
    You are an expert in SQL and Azure SQL Database. Given the following database schema and the intent/entities, generate a valid T-SQL query for querying the database.

    IMPORTANT:
    - Do NOT use USE statements (USE [database] is not supported in Azure SQL Database)
    - Generate only the SELECT query without USE or GO statements
    - Return only executable T-SQL code without markdown formatting
    - The database connection is already established to the correct database

    Schema:
    {schema}
    Intent and Entities:
    {intent_entities}

    Generate a T-SQL query that can be executed directly:
    """
)
REASONING_PROMPT_TEXT = (
    """
    You are assisting with SQL generation. Before writing SQL, produce a short, high-level reasoning summary
    for how you will construct the query, based on the schema and the intent/entities.

    Rules:
    - Do NOT include any SQL code.
    - Keep it concise (<= 150 words) and actionable.
    - Use simple bullets covering: Entities mapping, Tables/Joins, Aggregations (if any), Filters, Order/Limit, Assumptions.

    Schema:
    {schema}
    Intent and Entities:
    {intent_entities}

    Provide the reasoning summary now:
    """
)

# Templates for LangChain path
intent_prompt = ChatPromptTemplate.from_template(INTENT_PROMPT_TEXT)


def parse_nl_query(user_input: str) -> str:
    """Extract intent and entities (diagram: INTENT & ENTITIES)."""
    if _USING_REASONING_STYLE:
        prompt_text = INTENT_PROMPT_TEXT.format(input=user_input)
        messages = [
            {"role": "user", "content": prompt_text.strip()},
        ]
        content, usage = _azure_chat_completions(messages, max_completion_tokens=8192)
        _accumulate_usage(usage)
        return content
    # Non-reasoning path via LangChain
    chain = intent_prompt | llm  # type: ignore[arg-type]
    res = chain.invoke({"input": user_input})
    _accumulate_usage(_extract_usage_from_langchain_message(res))
    return res.content


# SQL prompt (schema-aware)
sql_prompt = ChatPromptTemplate.from_template(SQL_PROMPT_TEXT)


# Reasoning prompt (high-level plan before SQL)
reasoning_prompt = ChatPromptTemplate.from_template(REASONING_PROMPT_TEXT)


# ---------- Direct Azure Chat Completions for o-series / gpt-5 ----------

def _azure_chat_completions(messages: List[Dict[str, Any]], max_completion_tokens: int | None = None) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Direct Chat Completions call without temperature/top_p (reasoning-safe).

    Returns (content, usage_dict)
    """
    import requests  # lazy import

    url = f"{ENDPOINT.rstrip('/')}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={API_VERSION}"
    payload: Dict[str, Any] = {"messages": messages}
    if max_completion_tokens is not None:
        payload["max_completion_tokens"] = max_completion_tokens
    headers = {"api-key": API_KEY or "", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage")
    return content, usage


def _safe_import_schema_reader():
    """Try to import get_sql_database_schema_context from likely locations."""
    # Ensure local directory is on sys.path so we can import sibling modules
    this_dir = os.path.dirname(__file__)
    if this_dir and this_dir not in sys.path:
        sys.path.insert(0, this_dir)
    try:
        from schema_reader import get_sql_database_schema_context  # type: ignore
        return get_sql_database_schema_context
    except Exception:
        pass
    try:
        from CODE.NL2DAX_PIPELINE.schema_reader import (  # type: ignore
            get_sql_database_schema_context,
        )
        return get_sql_database_schema_context
    except Exception as e:
        raise ImportError(
            "Unable to import get_sql_database_schema_context from schema_reader."
        ) from e


def _safe_import_sql_executor():
    """Try to import execute_sql_query from likely locations."""
    # Ensure local directory is on sys.path so we can import sibling modules
    this_dir = os.path.dirname(__file__)
    if this_dir and this_dir not in sys.path:
        sys.path.insert(0, this_dir)
    try:
        from sql_executor import execute_sql_query  # type: ignore
        return execute_sql_query
    except Exception:
        pass
    try:
        from CODE.NL2DAX_PIPELINE.sql_executor import execute_sql_query  # type: ignore
        return execute_sql_query
    except Exception as e:
        raise ImportError("Unable to import execute_sql_query from sql_executor.") from e


def generate_sql(intent_entities: str) -> str:
    """Generate SQL from intent/entities with schema context (diagram: SQL GENERATION)."""
    get_schema_ctx = _safe_import_schema_reader()
    schema = get_schema_ctx()
    if _USING_REASONING_STYLE:
        prompt_text = SQL_PROMPT_TEXT.format(schema=schema, intent_entities=intent_entities)
        messages = [
            {"role": "user", "content": prompt_text.strip()},
        ]
        content, usage = _azure_chat_completions(messages, max_completion_tokens=8192)
        _accumulate_usage(usage)
        return content
    # Non-reasoning path via LangChain
    chain = sql_prompt | llm  # type: ignore[arg-type]
    result = chain.invoke({"schema": schema, "intent_entities": intent_entities})
    _accumulate_usage(_extract_usage_from_langchain_message(result))
    return result.content


def generate_reasoning(intent_entities: str) -> str:
    """Produce a short plan for SQL construction (optional diagram branch)."""
    try:
        get_schema_ctx = _safe_import_schema_reader()
        schema = get_schema_ctx()
        if _USING_REASONING_STYLE:
            prompt_text = REASONING_PROMPT_TEXT.format(schema=schema, intent_entities=intent_entities)
            messages = [
                {"role": "user", "content": prompt_text.strip()},
            ]
            content, usage = _azure_chat_completions(messages, max_completion_tokens=8192)
            _accumulate_usage(usage)
            return content
        chain = reasoning_prompt | llm  # type: ignore[arg-type]
        res = chain.invoke({"schema": schema, "intent_entities": intent_entities})
        _accumulate_usage(_extract_usage_from_langchain_message(res))
        return res.content
    except Exception as e:
        return f"Reasoning unavailable: {e}"


def extract_and_sanitize_sql(raw_sql: str) -> str:
    """Extract SQL from LLM output and normalize quotes (diagram: SANITIZATION)."""
    sql_code = raw_sql
    # 1) Prefer fenced code blocks if present (captures full content, e.g., WITH ...)
    code_block = re.search(r"```sql\s*([\s\S]+?)```", raw_sql, re.IGNORECASE)
    if not code_block:
        code_block = re.search(r"```([\s\S]+?)```", raw_sql)
    if code_block:
        sql_code = code_block.group(1).strip()
    else:
        # 2) If a CTE exists, start from WITH to capture the entire statement
        with_match = re.search(r"(?is)\bWITH\b\s+[A-Za-z0-9_\[\]]+\s+AS\s*\(", raw_sql)
        if with_match:
            sql_code = raw_sql[with_match.start():].strip()
        else:
            # 3) Fallback to first SELECT
            select_match = re.search(r"(?is)\bSELECT\b[\s\S]+", raw_sql)
            if select_match:
                sql_code = select_match.group(0).strip()
            else:
                sql_code = raw_sql.strip()

    # Normalize quotes and strip stray markdown remnants
    sql_code = (
        sql_code.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
    )
    return sql_code


# ---------- Output formatting ----------

class Colors:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


def colored_banner(title: str, color: str = Colors.RESET) -> str:
    return f"{color}\n========== {title} =========={Colors.RESET}\n"


def plain_banner(title: str) -> str:
    return f"\n========== {title} ==========\n"


def _format_table(rows):
    if not rows:
        return "No results returned.\n", []
    columns = list(rows[0].keys())
    col_widths = {c: max(len(c), max(len(str(r[c])) for r in rows)) for c in columns}
    header = " | ".join(c.ljust(col_widths[c]) for c in columns)
    sep = "-+-".join("-" * col_widths[c] for c in columns)
    lines = [header, sep]
    for r in rows:
        lines.append(" | ".join(str(r[c]).ljust(col_widths[c]) for c in columns))
    return "\n".join(lines) + "\n", [header, sep] + [
        " | ".join(str(r[c]).ljust(col_widths[c]) for c in columns) for r in rows
    ]


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="NL2SQL-only pipeline")
    parser.add_argument("--query", help="Natural language question", default=None)
    parser.add_argument("--no-exec", action="store_true", help="Skip SQL execution")
    parser.add_argument("--whoami", action="store_true", help="Print script purpose and exit")
    parser.add_argument("--no-reasoning", action="store_true", help="Skip printing the SQL generation reasoning section")
    parser.add_argument(
        "--explain-only",
        action="store_true",
        help="Only print intent and the reasoning summary; skip SQL generation and execution",
    )
    parser.add_argument(
        "--refresh-schema",
        action="store_true",
        help="Refresh the schema cache before generating SQL",
    )
    args = parser.parse_args(argv)

    if args.whoami:
        print(
            "This is the NL2SQL-only pipeline: it extracts intent, generates SQL, "
            "sanitizes it, executes it (unless --no-exec), and prints/saves results."
        )
        return 0

    start = time.time()
    output_lines = []

    # Display model information
    model_name = DEPLOYMENT_NAME or "Unknown"
    model_type = "Reasoning Model (o-series/GPT-5)" if _USING_REASONING_STYLE else "Standard Model"
    print(colored_banner("MODEL INFORMATION", Colors.CYAN))
    print(f"Deployment: {model_name}")
    print(f"Type: {model_type}")
    print(f"Endpoint: {ENDPOINT}")
    print(f"API Version: {API_VERSION}\n")
    output_lines.append(plain_banner("MODEL INFORMATION"))
    output_lines.append(f"Deployment: {model_name}\n")
    output_lines.append(f"Type: {model_type}\n")
    output_lines.append(f"Endpoint: {ENDPOINT}\n")
    output_lines.append(f"API Version: {API_VERSION}\n")

    # 1) Get user query (diagram: NATURAL LANGUAGE INPUT)
    if args.query:
        query = args.query
    else:
        query = input("Enter your natural language query: ")

    print(colored_banner("NATURAL LANGUAGE QUERY", Colors.BLUE))
    print(query + "\n")
    output_lines.append(plain_banner("NATURAL LANGUAGE QUERY"))
    output_lines.append(query + "\n")

    # 2) Extract intent/entities (diagram: INTENT & ENTITIES)
    intent_entities = parse_nl_query(query)
    print(colored_banner("INTENT & ENTITIES", Colors.BLUE))
    print(intent_entities + "\n")
    output_lines.append(plain_banner("INTENT & ENTITIES"))
    output_lines.append(intent_entities + "\n")

    # Optional: refresh schema cache on demand (diagram: REFRESH SCHEMA branch)
    if args.refresh_schema:
        print(colored_banner("REFRESHING SCHEMA CACHE", Colors.CYAN))
        output_lines.append(plain_banner("REFRESHING SCHEMA CACHE"))
        try:
            # Ensure local path is importable and refresh
            this_dir = os.path.dirname(__file__)
            if this_dir and this_dir not in sys.path:
                sys.path.insert(0, this_dir)
            import schema_reader  # local module
            path = schema_reader.refresh_schema_cache()
            msg = f"[INFO] Schema cache refreshed: {path}"
            print(msg + "\n")
            output_lines.append(msg + "\n")
        except Exception as e:
            msg = f"[WARN] Failed to refresh schema cache: {e}"
            print(msg + "\n")
            output_lines.append(msg + "\n")

    # 2.5) Reasoning summary (before SQL) — optional planning step
    if not args.no_reasoning or args.explain_only:
        reasoning = generate_reasoning(intent_entities)
        print(colored_banner("SQL GENERATION REASONING", Colors.CYAN))
        print(reasoning + "\n")
        output_lines.append(plain_banner("SQL GENERATION REASONING"))
        output_lines.append(reasoning + "\n")

    # Explain-only mode: stop before SQL generation/execution (diagram end)
    if args.explain_only:
        note = "Explain-only mode: SQL generation and execution skipped"
        print(colored_banner("EXPLAIN-ONLY MODE", Colors.CYAN))
        print(note + "\n")
        output_lines.append(plain_banner("EXPLAIN-ONLY MODE"))
        output_lines.append(note + "\n")

        # Token usage & cost
        in_price_1k, out_price_1k, price_src, currency_code = _get_pricing_for_deployment(DEPLOYMENT_NAME)
        prompt_tokens = _TOKEN_USAGE["prompt"]
        completion_tokens = _TOKEN_USAGE["completion"]
        total_tokens = _TOKEN_USAGE["total"] or (prompt_tokens + completion_tokens)
        if in_price_1k is not None and out_price_1k is not None:
            input_cost = (prompt_tokens / 1000.0) * in_price_1k
            output_cost = (completion_tokens / 1000.0) * out_price_1k
            total_cost = input_cost + output_cost
            print(colored_banner("TOKEN USAGE & COST", Colors.CYAN))
            print(f"Input tokens: {prompt_tokens}")
            print(f"Completion tokens: {completion_tokens}")
            print(f"Total tokens: {total_tokens}")
            print(
                f"Estimated cost ({currency_code}): {total_cost:.6f}  [input={input_cost:.6f}, output={output_cost:.6f}; per-1k: in={in_price_1k}, out={out_price_1k}; source={price_src}]"
            )
            output_lines.append(plain_banner("TOKEN USAGE & COST"))
            output_lines.append(f"Input tokens: {prompt_tokens}\n")
            output_lines.append(f"Completion tokens: {completion_tokens}\n")
            output_lines.append(f"Total tokens: {total_tokens}\n")
            output_lines.append(
                f"Estimated cost ({currency_code}): {total_cost:.6f}  [input={input_cost:.6f}, output={output_cost:.6f}; per-1k: in={in_price_1k}, out={out_price_1k}; source={price_src}]\n"
            )
        else:
            print(colored_banner("TOKEN USAGE", Colors.CYAN))
            print(f"Input tokens: {prompt_tokens}")
            print(f"Completion tokens: {completion_tokens}")
            print(f"Total tokens: {total_tokens}")
            print(
                "[INFO] Pricing not configured. Set per-1K token prices via env or azure_openai_pricing.json."
            )
            output_lines.append(plain_banner("TOKEN USAGE"))
            output_lines.append(f"Input tokens: {prompt_tokens}\n")
            output_lines.append(f"Completion tokens: {completion_tokens}\n")
            output_lines.append(f"Total tokens: {total_tokens}\n")
            output_lines.append("[INFO] Pricing not configured. See README for env vars or azure_openai_pricing.json.\n")

        # Duration
        dur = time.time() - start
        dur_line = f"Run duration: {dur:.2f} seconds"
        print(colored_banner("RUN DURATION", Colors.CYAN))
        print(dur_line)
        output_lines.append(plain_banner("RUN DURATION"))
        output_lines.append(dur_line + "\n")

        # Persist results (under RESULTS/)
        safe_query = query.strip().replace(" ", "_")[:40]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_filename = f"nl2sql_run_{safe_query}_{ts}.txt"
        results_dir = os.path.join(os.path.dirname(__file__), "RESULTS")
        os.makedirs(results_dir, exist_ok=True)
        out_path = os.path.join(results_dir, out_filename)
        with open(out_path, "w") as f:
            f.writelines([line if line.endswith("\n") else line + "\n" for line in output_lines])
        print(f"[INFO] Run results written to {out_path}")
        return 0

    # 3) Generate SQL (diagram: SQL GENERATION)
    raw_sql = generate_sql(intent_entities)
    print(colored_banner("GENERATED SQL (RAW)", Colors.GREEN))
    print(raw_sql + "\n")
    output_lines.append(plain_banner("GENERATED SQL (RAW)"))
    output_lines.append(raw_sql + "\n")

    # 4) Sanitize SQL (diagram: SQL SANITIZATION)
    sql_to_run = extract_and_sanitize_sql(raw_sql)
    if sql_to_run != raw_sql:
        print(colored_banner("SANITIZED SQL (FOR EXECUTION)", Colors.GREEN))
        print(sql_to_run + "\n")
        output_lines.append(plain_banner("SANITIZED SQL (FOR EXECUTION)"))
        output_lines.append(sql_to_run + "\n")

    # 5) Execute + format results (diagram: EXECUTION)
    if not args.no_exec:
        try:
            print(colored_banner("EXECUTING SQL QUERY", Colors.GREEN))
            execute_sql_query = _safe_import_sql_executor()
            rows = execute_sql_query(sql_to_run)
            print(colored_banner("SQL QUERY RESULTS (TABLE)", Colors.YELLOW))
            table_text, table_lines = _format_table(rows)
            print(table_text)
            output_lines.append(plain_banner("SQL QUERY RESULTS (TABLE)"))
            output_lines.extend(line + "\n" for line in table_lines)
        except Exception as e:
            msg = f"[ERROR] Failed to execute SQL query: {e}"
            print(colored_banner("SQL QUERY ERROR", Colors.RED))
            print(msg + "\n")
            output_lines.append(plain_banner("SQL QUERY ERROR"))
            output_lines.append(msg + "\n")
    else:
        print(colored_banner("EXECUTION SKIPPED (--no-exec)", Colors.CYAN))
        output_lines.append(plain_banner("EXECUTION SKIPPED (--no-exec)"))

    # Duration & persistence (diagram: DURATION & LOGGING)
    dur = time.time() - start
    dur_line = f"Run duration: {dur:.2f} seconds"
    # Token usage & cost calculation section
    in_price_1k, out_price_1k, price_src, currency_code = _get_pricing_for_deployment(DEPLOYMENT_NAME)
    prompt_tokens = _TOKEN_USAGE["prompt"]
    completion_tokens = _TOKEN_USAGE["completion"]
    total_tokens = _TOKEN_USAGE["total"] or (prompt_tokens + completion_tokens)
    cost_line = ""
    if in_price_1k is not None and out_price_1k is not None:
        input_cost = (prompt_tokens / 1000.0) * in_price_1k
        output_cost = (completion_tokens / 1000.0) * out_price_1k
        total_cost = input_cost + output_cost
        print(colored_banner("TOKEN USAGE & COST", Colors.CYAN))
        print(f"Input tokens: {prompt_tokens}")
        print(f"Completion tokens: {completion_tokens}")
        print(f"Total tokens: {total_tokens}")
        print(f"Estimated cost ({currency_code}): {total_cost:.6f}  [input={input_cost:.6f}, output={output_cost:.6f}; per-1k: in={in_price_1k}, out={out_price_1k}; source={price_src}]")
        output_lines.append(plain_banner("TOKEN USAGE & COST"))
        output_lines.append(f"Input tokens: {prompt_tokens}\n")
        output_lines.append(f"Completion tokens: {completion_tokens}\n")
        output_lines.append(f"Total tokens: {total_tokens}\n")
        output_lines.append(
            f"Estimated cost ({currency_code}): {total_cost:.6f}  [input={input_cost:.6f}, output={output_cost:.6f}; per-1k: in={in_price_1k}, out={out_price_1k}; source={price_src}]\n"
        )
    else:
        # Pricing not set; still print tokens and guidance
        print(colored_banner("TOKEN USAGE", Colors.CYAN))
        print(f"Input tokens: {prompt_tokens}")
        print(f"Completion tokens: {completion_tokens}")
        print(f"Total tokens: {total_tokens}")
        print(
            "[INFO] Pricing not configured. Set per-1K token prices via env: "
            f"AZURE_OPENAI_PRICE_{_normalize_dep_to_env_key(DEPLOYMENT_NAME or '')}_INPUT_PER_1K / ..._OUTPUT_PER_1K, "
            "or AZURE_OPENAI_PRICE_INPUT_PER_1K / AZURE_OPENAI_PRICE_OUTPUT_PER_1K, "
            "or add azure_openai_pricing.json."
        )
        output_lines.append(plain_banner("TOKEN USAGE"))
        output_lines.append(f"Input tokens: {prompt_tokens}\n")
        output_lines.append(f"Completion tokens: {completion_tokens}\n")
        output_lines.append(f"Total tokens: {total_tokens}\n")
        output_lines.append(
            "[INFO] Pricing not configured. See README for env vars or azure_openai_pricing.json.\n"
        )
    print(colored_banner("RUN DURATION", Colors.CYAN))
    print(dur_line)
    output_lines.append(plain_banner("RUN DURATION"))
    output_lines.append(dur_line + "\n")

    # Persist results (under RESULTS/)
    safe_query = query.strip().replace(" ", "_")[:40]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"nl2sql_run_{safe_query}_{ts}.txt"
    results_dir = os.path.join(os.path.dirname(__file__), "RESULTS")
    os.makedirs(results_dir, exist_ok=True)
    out_path = os.path.join(results_dir, out_filename)
    with open(out_path, "w") as f:
        f.writelines([line if line.endswith("\n") else line + "\n" for line in output_lines])
    print(f"[INFO] Run results written to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
