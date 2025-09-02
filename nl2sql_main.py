"""
nl2sql_main.py - NL2SQL-Only Pipeline Entrypoint
=================================================

Purpose
-------
Focus exclusively on the NL2SQL flow following the same approach and sequence as
the combined pipeline in `main.py`, but without any DAX generation or execution.

What it does
------------
1) Extract intent and entities from a natural language question
2) Generate a T-SQL query using schema-aware prompting
3) Sanitize/extract the SQL code from the LLM output
4) Execute the SQL against Azure SQL Database
5) Print results in a formatted table and persist the full run output to a file

Requirements
------------
- Environment variables set for Azure OpenAI and Azure SQL (see README/your .env):
  AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME
  AZURE_SQL_SERVER, AZURE_SQL_DB, AZURE_SQL_USER, AZURE_SQL_PASSWORD
- Python packages: langchain-openai, langchain, python-dotenv, pyodbc
"""

import os
import re
import sys
import time
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

# Initialize LLM (chat completion)
llm = AzureChatOpenAI(
    openai_api_key=API_KEY,
    azure_endpoint=ENDPOINT,
    deployment_name=DEPLOYMENT_NAME,
    api_version="2024-12-01-preview",
)


# ---------- Prompt setup ----------

# Intent extraction (NL -> structured intent/entities)
intent_prompt = ChatPromptTemplate.from_template(
    """
    You are an expert in translating natural language to database queries. Extract the intent and entities from the following user input:
    {input}
    """
)


def parse_nl_query(user_input: str) -> str:
    """Run the intent extraction chain and return the structured intent/entities."""
    chain = intent_prompt | llm
    res = chain.invoke({"input": user_input})
    return res.content


# SQL prompt (schema-aware)
sql_prompt = ChatPromptTemplate.from_template(
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


# Reasoning prompt (high-level plan before SQL)
reasoning_prompt = ChatPromptTemplate.from_template(
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
    """Generate a SQL query from structured intent/entities with schema context."""
    get_schema_ctx = _safe_import_schema_reader()
    schema = get_schema_ctx()
    chain = sql_prompt | llm
    result = chain.invoke({"schema": schema, "intent_entities": intent_entities})
    return result.content


def generate_reasoning(intent_entities: str) -> str:
    """Generate a short, high-level reasoning summary for SQL construction."""
    try:
        get_schema_ctx = _safe_import_schema_reader()
        schema = get_schema_ctx()
        chain = reasoning_prompt | llm
        res = chain.invoke({"schema": schema, "intent_entities": intent_entities})
        return res.content
    except Exception as e:
        return f"Reasoning unavailable: {e}"


def extract_and_sanitize_sql(raw_sql: str) -> str:
    """Extract SQL code from LLM output and normalize quotes for execution."""
    sql_code = raw_sql
    code_block = re.search(r"```sql\s*([\s\S]+?)```", raw_sql, re.IGNORECASE)
    if not code_block:
        code_block = re.search(r"```([\s\S]+?)```", raw_sql)
    if code_block:
        sql_code = code_block.group(1).strip()
    else:
        select_match = re.search(r"(SELECT[\s\S]+)", raw_sql, re.IGNORECASE)
        if select_match:
            sql_code = select_match.group(1).strip()
    return (
        sql_code.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
    )


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

    # 1) Get user query
    if args.query:
        query = args.query
    else:
        query = input("Enter your natural language query: ")

    print(colored_banner("NATURAL LANGUAGE QUERY", Colors.BLUE))
    print(query + "\n")
    output_lines.append(plain_banner("NATURAL LANGUAGE QUERY"))
    output_lines.append(query + "\n")

    # 2) Extract intent/entities
    intent_entities = parse_nl_query(query)
    print(colored_banner("INTENT & ENTITIES", Colors.BLUE))
    print(intent_entities + "\n")
    output_lines.append(plain_banner("INTENT & ENTITIES"))
    output_lines.append(intent_entities + "\n")

    # Optional: refresh schema cache on demand
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

    # 2.5) Reasoning summary (before SQL)
    if not args.no_reasoning or args.explain_only:
        reasoning = generate_reasoning(intent_entities)
        print(colored_banner("SQL GENERATION REASONING", Colors.CYAN))
        print(reasoning + "\n")
        output_lines.append(plain_banner("SQL GENERATION REASONING"))
        output_lines.append(reasoning + "\n")

    # Explain-only mode: stop before SQL generation/execution
    if args.explain_only:
        note = "Explain-only mode: SQL generation and execution skipped"
        print(colored_banner("EXPLAIN-ONLY MODE", Colors.CYAN))
        print(note + "\n")
        output_lines.append(plain_banner("EXPLAIN-ONLY MODE"))
        output_lines.append(note + "\n")

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

    # 5) Execute + format results
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


if __name__ == "__main__":
    sys.exit(main())
