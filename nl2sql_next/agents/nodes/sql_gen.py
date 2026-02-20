"""SQL generation node — produces T-SQL from schema context + intent."""
from __future__ import annotations

from ..llm import azure_chat_completions, accumulate_usage
from ..state import GraphState


def _build_prompt(schema: str, intent: str | None, user_query: str) -> str:
    intent_text = intent.strip() if isinstance(intent, str) else "<none>"
    parts = [
        "You are an expert T-SQL developer for Azure SQL Database.",
        "Produce ONE executable SELECT statement (optionally preceded by CTEs). No comments, no markdown fences.",
        "Rules:",
        "- No USE, GO, INSERT, UPDATE, DELETE, DROP.",
        "- Use the exact schema-qualified table names from the schema context below.",
        "- Prefer JOINs to sub-selects for readability.",
        "- Handle NULLs with ISNULL / COALESCE where appropriate.",
        "- Use ORDER BY for deterministic results.",
        "",
        "Schema context (may be truncated):",
        schema[:6000],
        "",
        f"User question: {user_query}",
        f"Intent summary: {intent_text}",
        "",
        "Output ONLY the T-SQL SELECT (with optional CTEs).",
    ]
    return "\n".join(parts)


def run(state: GraphState) -> GraphState:
    try:
        intent_text = ""
        if isinstance(state.intent_entities, dict):
            intent_text = state.intent_entities.get("intent", "")
        elif isinstance(state.intent_entities, str):
            intent_text = state.intent_entities

        prompt = _build_prompt(state.schema_context, intent_text, state.user_query)
        content, usage = azure_chat_completions(
            [{"role": "user", "content": prompt.strip()}],
            max_completion_tokens=state.sql_max_tokens,
        )
        updated = accumulate_usage(usage, state.token_usage.model_dump())
        state.token_usage.prompt = updated.get("prompt", 0)
        state.token_usage.completion = updated.get("completion", 0)
        state.token_usage.total = updated.get("total", 0)
        state.sql_raw = content
    except Exception as e:
        state.add_error(f"SQL generation failed: {e}")
    return state
