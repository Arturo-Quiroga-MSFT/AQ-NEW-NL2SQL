"""NL2SQL chain — convert natural language to SQL and execute it,
or answer schema/admin questions directly.

Features:
- Intent routing: data queries vs. schema/admin questions
- Few-shot examples for common query patterns
- Error-correction loop (retries with error context on SQL failure)
- Conversation memory (multi-turn follow-ups)
- Azure OpenAI Responses API

Usage:
    from core.nl2sql import ask, Conversation

    # Single-shot
    result = ask("What are the top 5 products by revenue?")

    # Admin question
    result = ask("What tables are in the database?")

    # Multi-turn
    conv = Conversation()
    r1 = conv.ask("What are the top 5 products by revenue?")
    r2 = conv.ask("Now show only Clothing category")
"""
from __future__ import annotations

import json
import os
import re
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from openai import AzureOpenAI
from dotenv import load_dotenv

from .schema import get_schema_context
from .db import get_connection
from .few_shots import format_few_shots
from .router import classify
from .tools import TOOLS_READ_ONLY, execute_tool

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))

_client: Optional[AzureOpenAI] = None

MAX_RETRIES = 2  # number of error-correction retries

# ── Model configuration ─────────────────────────────────
# Maps user-facing model key → (deployment_name, reasoning_effort | None)
MODEL_CONFIG: Dict[str, Dict[str, Any]] = {
    "gpt-4.1":           {"deployment": "gpt-4.1",  "reasoning": None},
    "gpt-5.2-low":       {"deployment": "gpt-5.2",  "reasoning": "low"},
    "gpt-5.2-medium":    {"deployment": "gpt-5.2",  "reasoning": "medium"},
}
DEFAULT_MODEL = "gpt-4.1"


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
        )
    return _client


def _call_llm(instructions: str, user_input: str,
              model_key: str = DEFAULT_MODEL,
              max_output_tokens: int = 1024) -> Tuple[str, Dict[str, int]]:
    """Unified LLM call — handles both standard and reasoning models.

    Returns (output_text, {"input_tokens": ..., "output_tokens": ..., "total_tokens": ...})
    """
    client = _get_client()
    cfg = MODEL_CONFIG.get(model_key, MODEL_CONFIG[DEFAULT_MODEL])

    kwargs: Dict[str, Any] = {
        "model": cfg["deployment"],
        "instructions": instructions,
        "input": user_input,
        "max_output_tokens": max_output_tokens,
    }

    if cfg["reasoning"]:
        # Reasoning models: use reasoning param, no temperature
        kwargs["reasoning"] = {"effort": cfg["reasoning"]}
    else:
        kwargs["temperature"] = 0

    resp = client.responses.create(**kwargs)
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    if resp.usage:
        usage["input_tokens"] = getattr(resp.usage, "input_tokens", 0)
        usage["output_tokens"] = getattr(resp.usage, "output_tokens", 0)
        usage["total_tokens"] = getattr(resp.usage, "total_tokens", 0)
    return resp.output_text or "", usage


def _add_usage(totals: Dict[str, int], usage: Dict[str, int]) -> None:
    """Accumulate token usage."""
    for k in ("input_tokens", "output_tokens", "total_tokens"):
        totals[k] = totals.get(k, 0) + usage.get(k, 0)


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
                 history: Optional[List[Dict[str, str]]] = None,
                 model_key: str = DEFAULT_MODEL) -> Tuple[str, Dict[str, int]]:
    """Generate SQL from a natural language question (uses Responses API).

    Returns (sql, usage_dict).
    """
    if schema_context is None:
        schema_context = get_schema_context()

    # Build input with optional conversation history
    parts: list[str] = [f"SCHEMA:\n{schema_context}"]
    if history:
        parts.append("\nCONVERSATION HISTORY:")
        for h in history:
            parts.append(f"User: {h['question']}")
            if h.get("sql"):
                parts.append(f"SQL: {h['sql']}")
            elif h.get("answer"):
                parts.append(f"Answer: {h['answer'][:200]}")
    parts.append(f"\nQUESTION: {question}")
    user_input = "\n".join(parts)

    raw, usage = _call_llm(_build_system_prompt(), user_input,
                           model_key=model_key, max_output_tokens=1024)
    return _extract_sql(raw), usage


def _generate_sql_fix(question: str, bad_sql: str, error_msg: str,
                      schema_context: str,
                      model_key: str = DEFAULT_MODEL) -> Tuple[str, Dict[str, int]]:
    """Ask the LLM to fix a SQL query that failed execution.

    Returns (sql, usage_dict).
    """
    fix_input = (
        f"SCHEMA:\n{schema_context}\n\n"
        f"QUESTION: {question}\n\n"
        f"The following SQL was generated but failed:\n{bad_sql}\n\n"
        f"ERROR: {error_msg}\n\n"
        f"Generate a corrected SQL query. Return ONLY the SQL."
    )

    raw, usage = _call_llm(_build_system_prompt(), fix_input,
                           model_key=model_key, max_output_tokens=1024)
    return _extract_sql(raw), usage


# ── Admin assistant ─────────────────────────────────────

ADMIN_PROMPT = """\
You are a knowledgeable Azure SQL Database administrator and assistant.
Given the database schema below, answer the user's question about the
database structure, design, relationships, optimization, indexing,
best practices, or general database management.

Guidelines:
- Be concise but thorough.
- Use the actual table/column names from the schema.
- When suggesting indexes or optimizations, be specific.
- Format your answer with markdown (headers, bullet points, code blocks).
- For schema descriptions, list columns with their types.
- If asked about relationships, reference the foreign keys.
"""

ADMIN_TOOL_PROMPT = """\
You are a knowledgeable Azure SQL Database administrator and assistant
with access to live database tools.

You have tools to:
- list_tables: see all tables and views with row counts
- describe_table: inspect column definitions, keys, and foreign keys
- run_read_query: execute read-only SELECT queries for live data

Guidelines:
- Use your tools to inspect the live database when the user asks about
  tables, columns, row counts, relationships, or data samples.
- After calling tools, synthesise a clear answer using the results.
- Be concise but thorough. Use markdown formatting.
- Use the actual table/column names from the tool results.
- When suggesting indexes or optimizations, be specific.
- You may call multiple tools in sequence if needed.
- Only use run_read_query for SELECT statements — never write queries.
"""

MAX_TOOL_ROUNDS = 6  # safety cap on tool-use loop iterations


def answer_admin(question: str, schema_context: Optional[str] = None,
                 history: Optional[List[Dict[str, str]]] = None,
                 model_key: str = DEFAULT_MODEL) -> Tuple[str, Dict[str, int]]:
    """Answer a schema/admin question using live database tools.

    Uses the Responses API tool-use loop: the LLM can call tools (list_tables,
    describe_table, run_read_query), receive results, and compose a final answer.

    Returns (answer_text, usage_dict).
    """
    client = _get_client()
    cfg = MODEL_CONFIG.get(model_key, MODEL_CONFIG[DEFAULT_MODEL])
    usage_totals: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    if schema_context is None:
        schema_context = get_schema_context()

    # Build initial input
    parts: list[str] = [f"DATABASE SCHEMA:\n{schema_context}"]
    if history:
        parts.append("\nCONVERSATION HISTORY:")
        for h in history:
            parts.append(f"User: {h['question']}")
            if h.get("sql"):
                parts.append(f"SQL: {h['sql']}")
            elif h.get("answer"):
                parts.append(f"Answer: {h['answer'][:200]}")
    parts.append(f"\nQUESTION: {question}")

    # Responses API expects `input` as a list of input items
    input_items: List[Any] = [{"role": "user", "content": "\n".join(parts)}]

    for _round in range(MAX_TOOL_ROUNDS):
        kwargs: Dict[str, Any] = {
            "model": cfg["deployment"],
            "instructions": ADMIN_TOOL_PROMPT,
            "input": input_items,
            "tools": TOOLS_READ_ONLY,
            "max_output_tokens": 2048,
        }
        if cfg["reasoning"]:
            kwargs["reasoning"] = {"effort": cfg["reasoning"]}
        else:
            kwargs["temperature"] = 0

        resp = client.responses.create(**kwargs)

        # Accumulate usage
        if resp.usage:
            usage_totals["input_tokens"] += getattr(resp.usage, "input_tokens", 0)
            usage_totals["output_tokens"] += getattr(resp.usage, "output_tokens", 0)
            usage_totals["total_tokens"] += getattr(resp.usage, "total_tokens", 0)

        # Check for tool calls in the response output
        tool_calls = [item for item in resp.output
                      if getattr(item, "type", None) == "function_call"]

        if not tool_calls:
            # No tool calls → LLM produced a text response, we're done
            return resp.output_text or "", usage_totals

        # Execute each tool call and feed results back
        for tc in tool_calls:
            tool_result = execute_tool(tc.name, tc.arguments)
            input_items.append(tc)  # the function_call item
            input_items.append({
                "type": "function_call_output",
                "call_id": tc.call_id,
                "output": tool_result,
            })
        # Loop — LLM will see tool results on next iteration

    # Safety: exceeded max rounds — return whatever text we have
    return resp.output_text or "(Tool loop reached maximum iterations)", usage_totals


# ── SQL execution ───────────────────────────────────────

def execute_sql(sql: str) -> Dict[str, Any]:
    """Execute SQL and return columns + rows."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = [list(row) for row in cur.fetchall()] if columns else []
    return {"columns": columns, "rows": rows}


def _make_stats(t0: float, tokens: Dict[str, int]) -> Dict[str, Any]:
    """Build the stats dict from start time and accumulated tokens."""
    return {
        "elapsed_ms": round((time.perf_counter() - t0) * 1000),
        "tokens_in": tokens.get("input_tokens", 0),
        "tokens_out": tokens.get("output_tokens", 0),
        "tokens_total": tokens.get("total_tokens", 0),
    }


def _suggest_chart(question: str, columns: List[str],
                   rows: List[list]) -> Dict[str, str]:
    """Heuristic chart suggestion based on question, columns, and result shape."""
    result: Dict[str, str] = {"chart_type": "none", "x_col": "", "y_col": ""}

    if not columns or not rows or len(rows) <= 1 or len(columns) < 2:
        return result

    q = question.lower()

    # ── Check for explicit chart type request ───────────
    explicit_type: Optional[str] = None
    if re.search(r"\bbar\s*chart\b", q):
        explicit_type = "bar"
    elif re.search(r"\bline\s*chart\b", q):
        explicit_type = "line"
    elif re.search(r"\bpie\s*chart\b", q):
        explicit_type = "pie"

    # Detect time-series signals
    time_keywords = [
        "trend", "over time", "monthly", "daily", "weekly", "yearly",
        "by month", "by year", "by quarter", "by date", "growth",
        "progression", "history", "evolution",
    ]
    time_col_words = ["month", "year", "date", "quarter", "week", "day", "period"]
    time_cols = [c for c in columns
                 if any(w in c.lower() for w in time_col_words)]
    is_time = any(k in q for k in time_keywords) or bool(time_cols)

    # Detect comparison signals
    compare_keywords = [
        "compare", "top", "bottom", "most", "least", "highest", "lowest",
        "best", "worst", "per", "by", "rank", "each",
    ]
    is_compare = any(k in q for k in compare_keywords)

    # Detect proportion signals
    proportion_keywords = [
        "breakdown", "distribution", "proportion", "share", "percentage",
        "split", "composition", "ratio", "mix",
    ]
    is_proportion = any(k in q for k in proportion_keywords)

    # Classify columns as numeric vs label from first row
    numeric_cols: List[str] = []
    label_cols: List[str] = []
    for i, col in enumerate(columns):
        if i < len(rows[0]):
            val = rows[0][i]
            if isinstance(val, (int, float, Decimal)):
                numeric_cols.append(col)
            else:
                label_cols.append(col)

    if not numeric_cols or not label_cols:
        return result

    # ── Pick x_col ──────────────────────────────────────
    # Prefer a time column that exists as a label; fall back to first label
    x_col = label_cols[0]
    for tc in time_cols:
        if tc in label_cols:
            x_col = tc
            break

    # ── Pick y_col — skip time-like and id-like numeric columns ─────
    skip_words = time_col_words + ["id", "key", "code", "flag"]
    candidate_y = [c for c in numeric_cols
                   if not any(w in c.lower() for w in skip_words)]
    y_col = candidate_y[0] if candidate_y else numeric_cols[-1]

    result["x_col"] = x_col
    result["y_col"] = y_col

    # ── Decision logic ──────────────────────────────────
    if explicit_type:
        result["chart_type"] = explicit_type
    elif is_time:
        result["chart_type"] = "line"
    elif is_proportion and len(rows) <= 8:
        result["chart_type"] = "pie"
    elif is_compare or len(rows) <= 30:
        result["chart_type"] = "bar"
    elif len(rows) > 30:
        result["chart_type"] = "line"
    else:
        result["chart_type"] = "bar"

    # Override: too many slices for pie → bar
    if result["chart_type"] == "pie" and len(rows) > 8:
        result["chart_type"] = "bar"

    return result


# ── Public API ──────────────────────────────────────────

def ask(question: str, model_key: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """End-to-end: question → route → SQL pipeline or admin answer.

    Returns dict with keys: question, mode, model, sql, columns, rows, answer,
    error, retries, elapsed_ms, tokens_in, tokens_out, tokens_total
    """
    t0 = time.perf_counter()
    tokens: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    mode, router_usage = classify(question)
    _add_usage(tokens, router_usage)

    result: Dict[str, Any] = {
        "question": question, "mode": mode, "model": model_key, "sql": "",
        "columns": [], "rows": [], "answer": "", "error": None, "retries": 0,
        "chart_type": "none", "x_col": "", "y_col": "",
    }

    try:
        schema_ctx = get_schema_context()

        if mode == "admin_assist":
            answer_text, usage = answer_admin(question, schema_ctx,
                                             model_key=model_key)
            _add_usage(tokens, usage)
            result["answer"] = answer_text
            result.update(_make_stats(t0, tokens))
            return result

        # ── data_query path ──
        sql, usage = generate_sql(question, schema_ctx, model_key=model_key)
        _add_usage(tokens, usage)
        result["sql"] = sql

        if sql.startswith("-- CANNOT_ANSWER"):
            result["error"] = sql
            result.update(_make_stats(t0, tokens))
            return result

        if not _is_safe(sql):
            result["error"] = "Blocked: query contains disallowed statements"
            result.update(_make_stats(t0, tokens))
            return result

        last_error = None
        for attempt in range(1 + MAX_RETRIES):
            try:
                data = execute_sql(sql)
                result["sql"] = sql
                result["columns"] = data["columns"]
                result["rows"] = data["rows"]
                result["retries"] = attempt
                chart = _suggest_chart(question, data["columns"], data["rows"])
                result.update(chart)
                result.update(_make_stats(t0, tokens))
                return result
            except Exception as exec_err:
                last_error = str(exec_err)
                if attempt < MAX_RETRIES:
                    sql, fix_usage = _generate_sql_fix(question, sql, last_error, schema_ctx,
                                            model_key=model_key)
                    _add_usage(tokens, fix_usage)
                    if not _is_safe(sql):
                        result["error"] = "Blocked: corrected query contains disallowed statements"
                        result["sql"] = sql
                        result.update(_make_stats(t0, tokens))
                        return result

        result["sql"] = sql
        result["error"] = f"SQL execution failed after {MAX_RETRIES} retries: {last_error}"
        result["retries"] = MAX_RETRIES

    except Exception as e:
        result["error"] = str(e)

    result.update(_make_stats(t0, tokens))
    return result


class Conversation:
    """Multi-turn NL2SQL conversation with memory.

    Keeps track of previous question→SQL pairs and admin answers so the
    LLM can handle follow-up questions in either mode.
    """

    def __init__(self, max_history: int = 10) -> None:
        self._history: List[Dict[str, str]] = []
        self._max_history = max_history
        self._model_key: str = DEFAULT_MODEL

    @property
    def model_key(self) -> str:
        return self._model_key

    @model_key.setter
    def model_key(self, value: str) -> None:
        self._model_key = value if value in MODEL_CONFIG else DEFAULT_MODEL

    @property
    def history(self) -> List[Dict[str, str]]:
        return list(self._history)

    def ask(self, question: str, model_key: Optional[str] = None) -> Dict[str, Any]:
        """Ask a question with conversation context and intent routing."""
        t0 = time.perf_counter()
        tokens: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        mk = model_key or self._model_key
        if mk not in MODEL_CONFIG:
            mk = DEFAULT_MODEL
        mode, router_usage = classify(question)
        _add_usage(tokens, router_usage)

        result: Dict[str, Any] = {
            "question": question, "mode": mode, "model": mk, "sql": "",
            "columns": [], "rows": [], "answer": "", "error": None, "retries": 0,
            "chart_type": "none", "x_col": "", "y_col": "",
        }

        try:
            schema_ctx = get_schema_context()

            if mode == "admin_assist":
                answer_text, usage = answer_admin(question, schema_ctx,
                                                history=self._history,
                                                model_key=mk)
                _add_usage(tokens, usage)
                result["answer"] = answer_text
                self._history.append({"question": question,
                                      "answer": result["answer"][:300]})
                if len(self._history) > self._max_history:
                    self._history = self._history[-self._max_history:]
                result.update(_make_stats(t0, tokens))
                return result

            # ── data_query path ──
            sql, usage = generate_sql(question, schema_ctx, history=self._history,
                               model_key=mk)
            _add_usage(tokens, usage)
            result["sql"] = sql

            if sql.startswith("-- CANNOT_ANSWER"):
                result["error"] = sql
                result.update(_make_stats(t0, tokens))
                return result

            if not _is_safe(sql):
                result["error"] = "Blocked: query contains disallowed statements"
                result.update(_make_stats(t0, tokens))
                return result

            last_error = None
            for attempt in range(1 + MAX_RETRIES):
                try:
                    data = execute_sql(sql)
                    result["sql"] = sql
                    result["columns"] = data["columns"]
                    result["rows"] = data["rows"]
                    result["retries"] = attempt
                    chart = _suggest_chart(question, data["columns"], data["rows"])
                    result.update(chart)

                    self._history.append({"question": question, "sql": sql})
                    if len(self._history) > self._max_history:
                        self._history = self._history[-self._max_history:]
                    result.update(_make_stats(t0, tokens))
                    return result
                except Exception as exec_err:
                    last_error = str(exec_err)
                    if attempt < MAX_RETRIES:
                        sql, fix_usage = _generate_sql_fix(question, sql, last_error, schema_ctx,
                                                model_key=mk)
                        _add_usage(tokens, fix_usage)
                        if not _is_safe(sql):
                            result["error"] = "Blocked: corrected query contains disallowed statements"
                            result["sql"] = sql
                            result.update(_make_stats(t0, tokens))
                            return result

            result["sql"] = sql
            result["error"] = f"SQL execution failed after {MAX_RETRIES} retries: {last_error}"
            result["retries"] = MAX_RETRIES

        except Exception as e:
            result["error"] = str(e)

        result.update(_make_stats(t0, tokens))
        return result

    def clear(self) -> None:
        """Reset conversation history."""
        self._history.clear()
