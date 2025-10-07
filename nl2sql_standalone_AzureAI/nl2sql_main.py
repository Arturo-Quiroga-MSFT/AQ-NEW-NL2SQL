"""
nl2sql_main.py — NL → Intent → SQL pipeline using Azure AI Agent Service
===========================================================================

Overview
--------
This implementation uses Azure AI Foundry Agent Service instead of LangChain.
It mirrors the same NL→SQL pipeline but leverages Azure AI Agents for:
- Better integration with Azure AI Foundry
- Built-in agent management and persistence
- Native Azure authentication
- Enhanced observability and tracing

What it does
------------
1) Extract intent and entities from a natural language question using AI Agent
2) Generate a T‑SQL query using schema‑aware prompting via AI Agent
3) Sanitize/extract the SQL code from the Agent output
4) Execute the SQL against Azure SQL Database
5) Print results in a formatted table and persist the full run output to a file

Relevant CLI flags
------------------
--query            Provide the question inline, otherwise you'll be prompted
--refresh-schema   Refresh schema cache before generation
--no-reasoning     Skip the reasoning/plan step
--explain-only     Show intent + reasoning only, skip SQL & execution
--no-exec          Generate SQL but don't execute
--whoami           Print script purpose and exit

Requirements
------------
- Environment variables for Azure AI Foundry and Azure SQL (see README/.env):
    PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME,
    AZURE_SQL_SERVER, AZURE_SQL_DB, AZURE_SQL_USER, AZURE_SQL_PASSWORD
- Python packages: azure-ai-projects, azure-identity, python-dotenv, pyodbc
"""

import os
import re
import sys
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Load environment variables early
load_dotenv()

# Azure AI Foundry configuration
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME")

# Validate required environment variables
if not PROJECT_ENDPOINT:
    raise ValueError("PROJECT_ENDPOINT environment variable is required")
if not MODEL_DEPLOYMENT_NAME:
    raise ValueError("MODEL_DEPLOYMENT_NAME environment variable is required")

# Initialize Azure AI Project Client
project_client = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

# ---------- Token usage & pricing accumulation ----------

# Accumulator for token usage across all calls in a run
_TOKEN_USAGE = {"prompt": 0, "completion": 0, "total": 0}


def _accumulate_usage(usage: Optional[Dict[str, Any]]) -> None:
    """Accumulate token usage from agent runs."""
    if not usage:
        return
    _TOKEN_USAGE["prompt"] += int(usage.get("prompt_tokens", 0) or 0)
    _TOKEN_USAGE["completion"] += int(usage.get("completion_tokens", 0) or 0)
    _TOKEN_USAGE["total"] += int(usage.get("total_tokens", 0) or (_TOKEN_USAGE["prompt"] + _TOKEN_USAGE["completion"]))


def _reset_token_usage():
    """Reset token usage counters."""
    _TOKEN_USAGE["prompt"] = 0
    _TOKEN_USAGE["completion"] = 0
    _TOKEN_USAGE["total"] = 0


def _load_pricing_config() -> Dict[str, Dict[str, float]]:
    """Load optional pricing map from azure_openai_pricing.json."""
    try:
        repo_root = os.path.dirname(__file__)
        price_file = os.path.join(repo_root, "azure_openai_pricing.json")
        if os.path.exists(price_file):
            with open(price_file, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _get_pricing_for_deployment(deployment_name: str) -> tuple:
    """Get pricing info for a deployment."""
    config = _load_pricing_config()
    dep_key = (deployment_name or "").lower()
    
    if dep_key in config:
        prices = config[dep_key]
        # Handle both flat and nested (currency) structure
        if "USD" in prices:
            # Nested structure with currency
            usd_prices = prices["USD"]
            return (
                usd_prices.get("input_per_1k"),
                usd_prices.get("output_per_1k"),
                f"file:azure_openai_pricing.json",
                "USD"
            )
        else:
            # Flat structure
            return (
                prices.get("input_per_1k"),
                prices.get("output_per_1k"),
                f"file:azure_openai_pricing.json",
                "USD"
            )
    return (None, None, "not configured", "USD")


# ---------- Agent helpers ----------

# Persistent agent IDs (created once, reused across queries)
_INTENT_AGENT_ID = None
_SQL_AGENT_ID = None
_SQL_AGENT_SCHEMA = None  # Track if schema has changed


def _get_or_create_intent_agent() -> str:
    """Get or create a persistent intent extraction agent."""
    global _INTENT_AGENT_ID
    
    if _INTENT_AGENT_ID is None:
        agent = project_client.agents.create_agent(
            model=MODEL_DEPLOYMENT_NAME,
            name="intent-extractor-persistent",
            instructions="""You are an AI assistant that extracts the intent and entities from natural language database queries.

Analyze the user's question and provide:
1. The main intent (e.g., count, list, aggregate, filter)
2. Key entities mentioned (tables, columns, metrics)
3. Any filters or conditions
4. Desired aggregations or groupings

Return your analysis in JSON format with keys: intent, entity, metrics, filters, group_by."""
        )
        _INTENT_AGENT_ID = agent.id
        print(f"[DEBUG] Created persistent intent agent: {_INTENT_AGENT_ID}")
    
    return _INTENT_AGENT_ID


def _get_or_create_sql_agent(schema_context: str) -> str:
    """Get or create a persistent SQL generation agent."""
    global _SQL_AGENT_ID, _SQL_AGENT_SCHEMA
    
    # Recreate agent if schema has changed
    if _SQL_AGENT_ID is None or _SQL_AGENT_SCHEMA != schema_context:
        # Delete old agent if it exists
        if _SQL_AGENT_ID is not None:
            try:
                project_client.agents.delete_agent(_SQL_AGENT_ID)
                print(f"[DEBUG] Deleted old SQL agent (schema changed)")
            except Exception:
                pass
        
        # Create new agent with updated schema
        agent = project_client.agents.create_agent(
            model=MODEL_DEPLOYMENT_NAME,
            name="sql-generator-persistent",
            instructions=f"""You are an expert SQL query generator for Azure SQL Database.

Given the user's intent and the database schema, generate a valid T-SQL query.

Database Schema:
{schema_context or 'Schema not provided - use generic table names'}

Requirements:
- Generate clean, efficient T-SQL
- Use proper JOINs when needed
- Include appropriate WHERE clauses for filters
- Use meaningful column aliases
- Return ONLY the SQL query, no explanations
- Do NOT include markdown code blocks"""
        )
        _SQL_AGENT_ID = agent.id
        _SQL_AGENT_SCHEMA = schema_context
        print(f"[DEBUG] Created persistent SQL agent: {_SQL_AGENT_ID}")
    
    return _SQL_AGENT_ID


def extract_intent(query: str) -> str:
    """Extract intent and entities from natural language query using Azure AI Agent."""
    
    # Get or create persistent agent
    agent_id = _get_or_create_intent_agent()
    
    # Create thread
    thread = project_client.agents.threads.create()
    
    # Send message
    project_client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content=query
    )
    
    # Run agent
    run = project_client.agents.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent_id
    )
    
    # Track usage
    if hasattr(run, 'usage') and run.usage:
        _accumulate_usage({
            "prompt_tokens": getattr(run.usage, 'prompt_tokens', 0),
            "completion_tokens": getattr(run.usage, 'completion_tokens', 0),
            "total_tokens": getattr(run.usage, 'total_tokens', 0)
        })
    
    # Get response
    messages = project_client.agents.messages.list(thread_id=thread.id)
    for message in messages:
        if message.role == "assistant":
            if hasattr(message, 'text_messages') and message.text_messages:
                return message.text_messages[0].text.value
            elif hasattr(message, 'content'):
                return str(message.content)
    
    return "{}"


def generate_sql(intent_entities: str) -> str:
    """Generate SQL query based on extracted intent using Azure AI Agent."""
    
    # Get schema context
    try:
        from schema_reader import get_sql_database_schema_context
        schema_context = get_sql_database_schema_context()
    except Exception:
        schema_context = ""
    
    # Get or create persistent SQL agent
    agent_id = _get_or_create_sql_agent(schema_context)
    
    # Create thread
    thread = project_client.agents.threads.create()
    
    # Send message with intent
    project_client.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content=f"Intent: {intent_entities}\n\nGenerate the SQL query:"
    )
    
    # Run agent
    run = project_client.agents.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent_id
    )
    
    # Track usage
    if hasattr(run, 'usage') and run.usage:
        _accumulate_usage({
            "prompt_tokens": getattr(run.usage, 'prompt_tokens', 0),
            "completion_tokens": getattr(run.usage, 'completion_tokens', 0),
            "total_tokens": getattr(run.usage, 'total_tokens', 0)
        })
    
    # Get response
    messages = project_client.agents.messages.list(thread_id=thread.id)
    for message in messages:
        if message.role == "assistant":
            if hasattr(message, 'text_messages') and message.text_messages:
                return message.text_messages[0].text.value
            elif hasattr(message, 'content'):
                return str(message.content)
    
    return "SELECT 1;"


def extract_and_sanitize_sql(raw_sql: str) -> str:
    """Extract and clean SQL from agent response."""
    # Remove markdown code blocks if present
    sql = re.sub(r'^```(?:sql)?\s*', '', raw_sql, flags=re.MULTILINE)
    sql = re.sub(r'```\s*$', '', sql, flags=re.MULTILINE)
    
    # Trim whitespace
    sql = sql.strip()
    
    return sql


def _safe_import_sql_executor():
    """Safely import sql_executor module."""
    try:
        from sql_executor import execute_sql_query
        return execute_sql_query
    except ImportError as e:
        raise ImportError("Unable to import execute_sql_query from sql_executor.") from e


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

    parser = argparse.ArgumentParser(description="NL2SQL pipeline using Azure AI Agent Service")
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
            "This is the NL2SQL pipeline using Azure AI Agent Service: it extracts intent, "
            "generates SQL using AI Agents, sanitizes it, executes it (unless --no-exec), "
            "and prints/saves results."
        )
        return 0

    start = time.time()
    output_lines = []
    
    # Reset token usage
    _reset_token_usage()

    # Display model information
    print(colored_banner("MODEL INFORMATION", Colors.CYAN))
    print(f"Azure AI Project: {PROJECT_ENDPOINT}")
    print(f"Model Deployment: {MODEL_DEPLOYMENT_NAME}")
    print(f"Agent Service: Azure AI Foundry\n")
    output_lines.append(plain_banner("MODEL INFORMATION"))
    output_lines.append(f"Azure AI Project: {PROJECT_ENDPOINT}\n")
    output_lines.append(f"Model Deployment: {MODEL_DEPLOYMENT_NAME}\n")
    output_lines.append(f"Agent Service: Azure AI Foundry\n")

    # 1) Get user query
    if args.query:
        query = args.query
    else:
        query = input("Enter your natural language query: ")

    print(colored_banner("NATURAL LANGUAGE QUERY", Colors.BLUE))
    print(query + "\n")
    output_lines.append(plain_banner("NATURAL LANGUAGE QUERY"))
    output_lines.append(query + "\n")

    # 2) Extract intent
    print(colored_banner("INTENT & ENTITIES", Colors.BLUE))
    intent_entities = extract_intent(query)
    print(intent_entities + "\n")
    output_lines.append(plain_banner("INTENT & ENTITIES"))
    output_lines.append(intent_entities + "\n")

    if args.explain_only:
        print(colored_banner("EXPLAIN-ONLY MODE", Colors.CYAN))
        print("Explain-only mode: SQL generation and execution skipped\n")
        output_lines.append(plain_banner("EXPLAIN-ONLY MODE"))
        output_lines.append("Explain-only mode: SQL generation and execution skipped\n")
        
        # Show usage and duration
        dur = time.time() - start
        in_price_1k, out_price_1k, price_src, currency_code = _get_pricing_for_deployment(MODEL_DEPLOYMENT_NAME)
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
            output_lines.append(plain_banner("TOKEN USAGE"))
            output_lines.append(f"Input tokens: {prompt_tokens}\n")
            output_lines.append(f"Completion tokens: {completion_tokens}\n")
            output_lines.append(f"Total tokens: {total_tokens}\n")

        dur_line = f"Run duration: {dur:.2f} seconds"
        print(colored_banner("RUN DURATION", Colors.CYAN))
        print(dur_line)
        output_lines.append(plain_banner("RUN DURATION"))
        output_lines.append(dur_line + "\n")

        # Persist results
        safe_query = re.sub(r'[^\w\s-]', '', query.strip()).replace(" ", "_")[:40]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_filename = f"nl2sql_run_{safe_query}_{ts}.txt"
        results_dir = os.path.join(os.path.dirname(__file__), "RESULTS")
        os.makedirs(results_dir, exist_ok=True)
        out_path = os.path.join(results_dir, out_filename)
        with open(out_path, "w") as f:
            f.writelines([line if line.endswith("\n") else line + "\n" for line in output_lines])
        print(f"[INFO] Run results written to {out_path}")
        return 0

    # 3) Generate SQL
    raw_sql = generate_sql(intent_entities)
    print(colored_banner("GENERATED SQL (RAW)", Colors.GREEN))
    print(raw_sql + "\n")
    output_lines.append(plain_banner("GENERATED SQL (RAW)"))
    output_lines.append(raw_sql + "\n")

    # 4) Sanitize SQL
    sql_to_run = extract_and_sanitize_sql(raw_sql)
    if sql_to_run != raw_sql:
        print(colored_banner("SANITIZED SQL (FOR EXECUTION)", Colors.GREEN))
        print(sql_to_run + "\n")
        output_lines.append(plain_banner("SANITIZED SQL (FOR EXECUTION)"))
        output_lines.append(sql_to_run + "\n")

    # 5) Execute
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

    # Duration & token usage
    dur = time.time() - start
    dur_line = f"Run duration: {dur:.2f} seconds"
    in_price_1k, out_price_1k, price_src, currency_code = _get_pricing_for_deployment(MODEL_DEPLOYMENT_NAME)
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
        print("[INFO] Pricing not configured. Set per-1K token prices via env or azure_openai_pricing.json.")
        output_lines.append(plain_banner("TOKEN USAGE"))
        output_lines.append(f"Input tokens: {prompt_tokens}\n")
        output_lines.append(f"Completion tokens: {completion_tokens}\n")
        output_lines.append(f"Total tokens: {total_tokens}\n")
        output_lines.append("[INFO] Pricing not configured.\n")

    print(colored_banner("RUN DURATION", Colors.CYAN))
    print(dur_line)
    output_lines.append(plain_banner("RUN DURATION"))
    output_lines.append(dur_line + "\n")

    # Persist results
    safe_query = re.sub(r'[^\w\s-]', '', query.strip()).replace(" ", "_")[:40]
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
