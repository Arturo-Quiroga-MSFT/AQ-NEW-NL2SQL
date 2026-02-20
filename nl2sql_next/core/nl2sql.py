"""NL2SQL chain — convert natural language to SQL and execute it.

Features:
- Few-shot examples for common query patterns
- Error-correction loop (retries with error context on SQL failure)
- Conversation memory (multi-turn follow-ups)
- Azure OpenAI Responses API

Usage:
    from core.nl2sql import ask, Conversation

    # Single-shot
    result = ask("What are the top 5 products by revenue?")

    # Multi-turn
    conv = Conversation()
    r1 = conv.ask("What are the top 5 products by revenue?")
    r2 = conv.ask("Now show only Clothing category")
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from openai import AzureOpenAI
from dotenv import load_dotenv

from .schema import get_schema_context
from .db import get_connection
from .few_shots import format_few_shots

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))

_client: Optional[AzureOpenAI] = None

MAX_RETRIES = 2  # number of error-correction retries


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
        )
    return _client


SYSTEM_PROMPT = """\
You are an expert SQL analyst. Given a database schema and a user question,
generate a single T-SQL SELECT query that answers the question.

Rules:
1. Return ONLY the SQL query — no explanation, no markdown fences, no commentary.
2. The query must be a single SELECT statement (CTEs are OK).
3. Use the exact table and column names from the schema.
4. Use appropriate JOINs based on the foreign key relationships.
5. Include ORDER BY for consistent results.
6. Limit results to 50 rows max unless the user asks for more.
7. Never generate INSERT, UPDATE, DELETE, DROP, TRUNCATE, or any DDL.
8. If the question cannot be answered from the schema, respond with: -- CANNOT_ANSWER: <reason>

{few_shots}
"""


def _build_system_prompt() -> str:
    return SYSTEM_PROMPT.format(few_shots=format_few_shots())


def _extract_sql(text: str) -> str:
    """Extract SQL from LLM response, stripping markdown fences if present."""
    # Strip ```sql ... ``` fences
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text.strip()


def _is_safe(sql: str) -> bool:
    """Basic safety check — block destructive statements."""
    blocked = re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|EXEC|EXECUTE|xp_|sp_)\b",
        re.IGNORECASE,
    )
    # Ignore anything after -- comments for the check
    code_lines = [l.split("--")[0] for l in sql.splitlines()]
    code = " ".join(code_lines)
    return not blocked.search(code)


def generate_sql(question: str, schema_context: Optional[str] = None,
                 history: Optional[List[Dict[str, str]]] = None) -> str:
    """Generate SQL from a natural language question (uses Responses API)."""
    if schema_context is None:
        schema_context = get_schema_context()

    client = _get_client()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")

    # Build input with optional conversation history
    parts: list[str] = [f"SCHEMA:\n{schema_context}"]
    if history:
        parts.append("\nCONVERSATION HISTORY:")
        for h in history:
            parts.append(f"User: {h['question']}")
            parts.append(f"SQL: {h['sql']}")
    parts.append(f"\nQUESTION: {question}")
    user_input = "\n".join(parts)

    resp = client.responses.create(
        model=deployment,
        instructions=_build_system_prompt(),
        input=user_input,
        temperature=0,
        max_output_tokens=1024,
    )
    raw = resp.output_text or ""
    return _extract_sql(raw)


def _generate_sql_fix(question: str, bad_sql: str, error_msg: str,
                      schema_context: str) -> str:
    """Ask the LLM to fix a SQL query that failed execution."""
    client = _get_client()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")

    fix_input = (
        f"SCHEMA:\n{schema_context}\n\n"
        f"QUESTION: {question}\n\n"
        f"The following SQL was generated but failed:\n{bad_sql}\n\n"
        f"ERROR: {error_msg}\n\n"
        f"Generate a corrected SQL query. Return ONLY the SQL."
    )

    resp = client.responses.create(
        model=deployment,
        instructions=_build_system_prompt(),
        input=fix_input,
        temperature=0,
        max_output_tokens=1024,
    )
    raw = resp.output_text or ""
    return _extract_sql(raw)


def execute_sql(sql: str) -> Dict[str, Any]:
    """Execute SQL and return columns + rows."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = [list(row) for row in cur.fetchall()] if columns else []
    return {"columns": columns, "rows": rows}


def ask(question: str) -> Dict[str, Any]:
    """End-to-end: question → SQL → execute → results (with error-correction).

    Returns dict with keys: question, sql, columns, rows, error, retries
    """
    result: Dict[str, Any] = {
        "question": question, "sql": "", "columns": [], "rows": [],
        "error": None, "retries": 0,
    }

    try:
        schema_ctx = get_schema_context()
        sql = generate_sql(question, schema_ctx)
        result["sql"] = sql

        if sql.startswith("-- CANNOT_ANSWER"):
            result["error"] = sql
            return result

        if not _is_safe(sql):
            result["error"] = "Blocked: query contains disallowed statements"
            return result

        # Try executing, with error-correction retries
        last_error = None
        for attempt in range(1 + MAX_RETRIES):
            try:
                data = execute_sql(sql)
                result["sql"] = sql
                result["columns"] = data["columns"]
                result["rows"] = data["rows"]
                result["retries"] = attempt
                return result
            except Exception as exec_err:
                last_error = str(exec_err)
                if attempt < MAX_RETRIES:
                    sql = _generate_sql_fix(question, sql, last_error, schema_ctx)
                    if not _is_safe(sql):
                        result["error"] = "Blocked: corrected query contains disallowed statements"
                        result["sql"] = sql
                        return result

        # All retries exhausted
        result["sql"] = sql
        result["error"] = f"SQL execution failed after {MAX_RETRIES} retries: {last_error}"
        result["retries"] = MAX_RETRIES

    except Exception as e:
        result["error"] = str(e)

    return result


class Conversation:
    """Multi-turn NL2SQL conversation with memory.

    Keeps track of previous question→SQL pairs so the LLM can handle
    follow-up questions like "now filter by Clothing" or "show that as a
    percentage".
    """

    def __init__(self, max_history: int = 10) -> None:
        self._history: List[Dict[str, str]] = []
        self._max_history = max_history

    @property
    def history(self) -> List[Dict[str, str]]:
        return list(self._history)

    def ask(self, question: str) -> Dict[str, Any]:
        """Ask a question with conversation context."""
        result: Dict[str, Any] = {
            "question": question, "sql": "", "columns": [], "rows": [],
            "error": None, "retries": 0,
        }

        try:
            schema_ctx = get_schema_context()
            sql = generate_sql(question, schema_ctx, history=self._history)
            result["sql"] = sql

            if sql.startswith("-- CANNOT_ANSWER"):
                result["error"] = sql
                return result

            if not _is_safe(sql):
                result["error"] = "Blocked: query contains disallowed statements"
                return result

            last_error = None
            for attempt in range(1 + MAX_RETRIES):
                try:
                    data = execute_sql(sql)
                    result["sql"] = sql
                    result["columns"] = data["columns"]
                    result["rows"] = data["rows"]
                    result["retries"] = attempt

                    # Only add to history on success
                    self._history.append({"question": question, "sql": sql})
                    if len(self._history) > self._max_history:
                        self._history = self._history[-self._max_history:]
                    return result
                except Exception as exec_err:
                    last_error = str(exec_err)
                    if attempt < MAX_RETRIES:
                        sql = _generate_sql_fix(question, sql, last_error, schema_ctx)
                        if not _is_safe(sql):
                            result["error"] = "Blocked: corrected query contains disallowed statements"
                            result["sql"] = sql
                            return result

            result["sql"] = sql
            result["error"] = f"SQL execution failed after {MAX_RETRIES} retries: {last_error}"
            result["retries"] = MAX_RETRIES

        except Exception as e:
            result["error"] = str(e)

        return result

    def clear(self) -> None:
        """Reset conversation history."""
        self._history.clear()
