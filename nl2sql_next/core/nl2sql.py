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
from .tools import TOOLS_ALL, execute_tool, needs_approval

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
- run_write_query: execute INSERT/UPDATE/DELETE (requires user approval)

Guidelines:
- Use your tools to inspect the live database when the user asks about
  tables, columns, row counts, relationships, or data samples.
- After calling tools, synthesise a clear answer using the results.
- Be concise but thorough. Use markdown formatting.
- Use the actual table/column names from the tool results.
- When suggesting indexes or optimizations, be specific.
- You may call multiple tools in sequence if needed.

CRITICAL RULE FOR WRITE OPERATIONS:
- When the user asks to modify, insert, update, or delete data, you MUST
  ALWAYS call the run_write_query tool immediately with the SQL statement.
- NEVER describe the SQL and ask the user to confirm in text.
- NEVER say "would you like to proceed?" or "shall I execute this?".
- The system has a built-in approval UI that will show the SQL to the user
  and let them approve or reject before execution. Your job is to call the
  tool — the safety confirmation is handled by the system, not by you.
- This applies to ALL write operations: INSERT, UPDATE, and DELETE.
"""

MAX_TOOL_ROUNDS = 6  # safety cap on tool-use loop iterations


def _build_admin_input(question: str, schema_context: str,
                       history: Optional[List[Dict[str, str]]] = None) -> List[Any]:
    """Build the initial input items for the admin tool-use loop."""
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
    return [{"role": "user", "content": "\n".join(parts)}]


def _admin_llm_call(cfg: Dict[str, Any], input_items: List[Any],
                    usage_totals: Dict[str, int]) -> Any:
    """Single Responses API call for the admin tool-use loop."""
    client = _get_client()
    kwargs: Dict[str, Any] = {
        "model": cfg["deployment"],
        "instructions": ADMIN_TOOL_PROMPT,
        "input": input_items,
        "tools": TOOLS_ALL,
        "max_output_tokens": 2048,
    }
    if cfg["reasoning"]:
        kwargs["reasoning"] = {"effort": cfg["reasoning"]}
    else:
        kwargs["temperature"] = 0

    resp = client.responses.create(**kwargs)

    if resp.usage:
        usage_totals["input_tokens"] += getattr(resp.usage, "input_tokens", 0)
        usage_totals["output_tokens"] += getattr(resp.usage, "output_tokens", 0)
        usage_totals["total_tokens"] += getattr(resp.usage, "total_tokens", 0)

    return resp


def answer_admin(question: str, schema_context: Optional[str] = None,
                 history: Optional[List[Dict[str, str]]] = None,
                 model_key: str = DEFAULT_MODEL
                 ) -> Tuple[str, Dict[str, int], Optional[Dict[str, Any]]]:
    """Answer a schema/admin question using live database tools.

    Uses the Responses API tool-use loop.  When the LLM calls a tool that
    requires approval (e.g. run_write_query), the loop pauses and returns
    a pending-approval dict so the caller can present it to the user.

    Returns (answer_text, usage_dict, pending_approval_or_None).
    """
    cfg = MODEL_CONFIG.get(model_key, MODEL_CONFIG[DEFAULT_MODEL])
    usage_totals: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    if schema_context is None:
        schema_context = get_schema_context()

    input_items = _build_admin_input(question, schema_context, history)

    for _round in range(MAX_TOOL_ROUNDS):
        resp = _admin_llm_call(cfg, input_items, usage_totals)

        tool_calls = [item for item in resp.output
                      if getattr(item, "type", None) == "function_call"]

        if not tool_calls:
            return resp.output_text or "", usage_totals, None

        # Separate safe vs approval-requiring tool calls
        safe_calls = [tc for tc in tool_calls if not needs_approval(tc.name)]
        approval_calls = [tc for tc in tool_calls if needs_approval(tc.name)]

        if approval_calls:
            tc = approval_calls[0]  # handle one approval at a time

            # Collect any explanation text the LLM emitted alongside the call
            explanation_parts = [
                getattr(item, "text", "")
                for item in resp.output
                if getattr(item, "type", None) == "output_text"
                   and getattr(item, "text", "")
            ]

            # Append all output items to input_items for conversation continuity
            for item in resp.output:
                input_items.append(item)

            # Execute safe tool calls so their outputs are present
            for sc in safe_calls:
                tool_result = execute_tool(sc.name, sc.arguments)
                input_items.append({
                    "type": "function_call_output",
                    "call_id": sc.call_id,
                    "output": tool_result,
                })

            pending = {
                "tool_name": tc.name,
                "tool_arguments": tc.arguments,
                "tool_call_id": tc.call_id,
                "explanation": " ".join(explanation_parts),
                "input_items": input_items,
                "model_key": model_key,
            }
            return "", usage_totals, pending

        # All tool calls are safe — execute them
        for tc in tool_calls:
            tool_result = execute_tool(tc.name, tc.arguments)
            input_items.append(tc)
            input_items.append({
                "type": "function_call_output",
                "call_id": tc.call_id,
                "output": tool_result,
            })

    return resp.output_text or "(Tool loop reached maximum iterations)", usage_totals, None


def resume_after_approval(pending: Dict[str, Any], approved: bool
                          ) -> Tuple[str, Dict[str, int]]:
    """Resume the admin tool-use loop after a user approval decision.

    If approved, executes the tool and feeds the result to the LLM.
    If rejected, tells the LLM the user declined and gets a response.

    Returns (answer_text, usage_dict).
    """
    cfg = MODEL_CONFIG.get(pending["model_key"], MODEL_CONFIG[DEFAULT_MODEL])
    usage_totals: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    input_items: List[Any] = pending["input_items"]

    if approved:
        tool_result = execute_tool(pending["tool_name"], pending["tool_arguments"])
    else:
        tool_result = json.dumps({"status": "rejected", "message": "User declined this operation."})

    input_items.append({
        "type": "function_call_output",
        "call_id": pending["tool_call_id"],
        "output": tool_result,
    })

    # Continue the tool-use loop
    for _round in range(MAX_TOOL_ROUNDS):
        resp = _admin_llm_call(cfg, input_items, usage_totals)

        tool_calls = [item for item in resp.output
                      if getattr(item, "type", None) == "function_call"]

        if not tool_calls:
            return resp.output_text or "", usage_totals

        # Execute any subsequent tool calls (should be read-only at this point)
        for tc in tool_calls:
            if needs_approval(tc.name):
                # Nested approval not supported — reject
                input_items.append(tc)
                input_items.append({
                    "type": "function_call_output",
                    "call_id": tc.call_id,
                    "output": json.dumps({"error": "Only one write operation per request."}),
                })
            else:
                tool_result = execute_tool(tc.name, tc.arguments)
                input_items.append(tc)
                input_items.append({
                    "type": "function_call_output",
                    "call_id": tc.call_id,
                    "output": tool_result,
                })

    return resp.output_text or "(Tool loop reached maximum iterations)", usage_totals


# ── Streaming admin assistant ───────────────────────────

def _admin_llm_stream(cfg: Dict[str, Any], input_items: List[Any]):
    """Single streaming Responses API call — returns the raw stream iterator."""
    client = _get_client()
    kwargs: Dict[str, Any] = {
        "model": cfg["deployment"],
        "instructions": ADMIN_TOOL_PROMPT,
        "input": input_items,
        "tools": TOOLS_ALL,
        "max_output_tokens": 2048,
        "stream": True,
    }
    if cfg["reasoning"]:
        kwargs["reasoning"] = {"effort": cfg["reasoning"]}
    else:
        kwargs["temperature"] = 0

    return client.responses.create(**kwargs)


def answer_admin_stream(question: str, schema_context: Optional[str] = None,
                        history: Optional[List[Dict[str, str]]] = None,
                        model_key: str = DEFAULT_MODEL):
    """Streaming admin assistant — yields SSE-friendly dicts.

    Yields dicts with "type" key:
      {"type": "delta", "text": "..."}        — text token chunk
      {"type": "tool_start", "name": "..."}   — tool call beginning
      {"type": "tool_done", "name": "...", "result_preview": "..."}
      {"type": "approval", "pending": {...}}  — needs user approval
      {"type": "done", "usage": {...}}        — stream finished
      {"type": "error", "message": "..."}     — error
    """
    cfg = MODEL_CONFIG.get(model_key, MODEL_CONFIG[DEFAULT_MODEL])
    usage_totals: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    if schema_context is None:
        schema_context = get_schema_context()

    input_items = _build_admin_input(question, schema_context, history)

    for _round in range(MAX_TOOL_ROUNDS):
        stream = _admin_llm_stream(cfg, input_items)

        text_chunks: list[str] = []
        tool_calls_acc: list[Any] = []  # completed function_call items
        current_tool_name: Optional[str] = None
        completed_response = None

        for event in stream:
            etype = event.type

            # Text token
            if etype == "response.output_text.delta":
                delta = getattr(event, "delta", "")
                if delta:
                    text_chunks.append(delta)
                    yield {"type": "delta", "text": delta}

            # Tool call starting
            elif etype == "response.output_item.added":
                item = getattr(event, "item", None)
                if item and getattr(item, "type", None) == "function_call":
                    current_tool_name = getattr(item, "name", "unknown")
                    yield {"type": "tool_start", "name": current_tool_name}

            # Tool call completed
            elif etype == "response.output_item.done":
                item = getattr(event, "item", None)
                if item and getattr(item, "type", None) == "function_call":
                    tool_calls_acc.append(item)
                    current_tool_name = None

            # Full response done — extract usage
            elif etype == "response.completed":
                resp_obj = getattr(event, "response", None)
                if resp_obj and resp_obj.usage:
                    usage_totals["input_tokens"] += getattr(resp_obj.usage, "input_tokens", 0)
                    usage_totals["output_tokens"] += getattr(resp_obj.usage, "output_tokens", 0)
                    usage_totals["total_tokens"] += getattr(resp_obj.usage, "total_tokens", 0)
                completed_response = resp_obj

        # If no tool calls, we're done
        if not tool_calls_acc:
            yield {"type": "done", "usage": usage_totals}
            return

        # Process tool calls — separate safe vs approval-requiring
        safe_calls = [tc for tc in tool_calls_acc if not needs_approval(tc.name)]
        approval_calls = [tc for tc in tool_calls_acc if needs_approval(tc.name)]

        if approval_calls:
            tc = approval_calls[0]

            # Add all output items from completed response to input
            if completed_response:
                for item in completed_response.output:
                    input_items.append(item)

            # Execute safe calls
            for sc in safe_calls:
                tool_result = execute_tool(sc.name, sc.arguments)
                yield {"type": "tool_done", "name": sc.name,
                       "result_preview": tool_result[:200]}
                input_items.append({
                    "type": "function_call_output",
                    "call_id": sc.call_id,
                    "output": tool_result,
                })

            pending = {
                "tool_name": tc.name,
                "tool_arguments": tc.arguments,
                "tool_call_id": tc.call_id,
                "explanation": "",
                "input_items": input_items,
                "model_key": model_key,
            }
            yield {"type": "approval", "pending": pending}
            yield {"type": "done", "usage": usage_totals}
            return

        # All safe — execute and loop
        for tc in tool_calls_acc:
            tool_result = execute_tool(tc.name, tc.arguments)
            yield {"type": "tool_done", "name": tc.name,
                   "result_preview": tool_result[:200]}
            input_items.append(tc)
            input_items.append({
                "type": "function_call_output",
                "call_id": tc.call_id,
                "output": tool_result,
            })

    # Exhausted rounds
    yield {"type": "done", "usage": usage_totals}

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
        "approval": None,
    }

    try:
        schema_ctx = get_schema_context()

        if mode == "admin_assist":
            answer_text, usage, pending = answer_admin(question, schema_ctx,
                                                      model_key=model_key)
            _add_usage(tokens, usage)
            if pending:
                result["approval"] = pending
            else:
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
            "approval": None,
        }

        try:
            schema_ctx = get_schema_context()

            if mode == "admin_assist":
                answer_text, usage, pending = answer_admin(question, schema_ctx,
                                                          history=self._history,
                                                          model_key=mk)
                _add_usage(tokens, usage)
                if pending:
                    result["approval"] = pending
                else:
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
