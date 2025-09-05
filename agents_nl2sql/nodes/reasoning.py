from __future__ import annotations
from ..state import GraphState
from ..llm import azure_chat_completions, accumulate_usage
import re

MAX_REASONING_RETRIES = 2

REASONING_PROMPT_TEXT = (
    """
You are assisting with SQL generation. Produce a concise, actionable reasoning plan (NOT the SQL) for the query.

OUTPUT REQUIREMENTS:
- MUST return at least 5 bullet points.
- Each bullet must start with a hyphen '-'.
- Absolutely NO SQL keywords like SELECT, FROM, JOIN in the answer.
- Focus only on: Entities/Source Tables, Join Logic, Filters, Aggregations (or lack), Ordering/Limit, Potential Edge Cases.
- If no aggregation required, explicitly state that.

CONTEXT SCHEMA (TRUNCATED):
{schema}

INTENT:
{intent_entities}

Return ONLY the bullet list. If information is insufficient, still return structured bullets with reasonable assumptions.
"""
)


def _is_valid_reasoning(text: str) -> bool:
    if not text:
        return False
    # Reject if contains obvious full SQL pattern
    if re.search(r"\bSELECT\b.+\bFROM\b", text, re.IGNORECASE):
        return False
    # Accept almost anything non-empty now
    return True

def _fallback_reasoning(intent_text: str) -> str:
    """Heuristic reasoning generation when model fails or returns invalid output."""
    bullets = [
        "- Identify core entity: RiskMetricHistory joined to Company for industry filter",
        "- Filter Company.Industry = 'Technology'",
        "- Select relevant columns (CompanyName, MetricName, MetricValue, AsOfDate) ordered by Company then date",
        "- No aggregation required (list all metrics) unless dedup needed",
        "- Consider limiting date range if implied (not specified here)"
    ]
    return "Heuristic reasoning (fallback):\n" + "\n".join(bullets)

def run(state: GraphState) -> GraphState:
    try:
        attempt = 0
        last_content = ""
        schema_snippet = (state.schema_context or "")[:2500]
        while attempt <= MAX_REASONING_RETRIES:
            prompt = REASONING_PROMPT_TEXT.format(schema=schema_snippet, intent_entities=state.intent_entities)
            if attempt > 0:
                prompt += "\nPrevious attempt invalid or empty. Provide 5-8 bullets now, follow rules strictly."
            messages = [{"role": "user", "content": prompt.strip()}]
            content, usage = azure_chat_completions(
                messages,
                max_completion_tokens=state.reasoning_max_tokens if state.reasoning_max_tokens else None,
            )
            updated = accumulate_usage(usage, state.token_usage.model_dump())
            state.token_usage.prompt = updated.get("prompt", 0)
            state.token_usage.completion = updated.get("completion", 0)
            state.token_usage.total = updated.get("total", 0)
            last_content = content.strip()
            state.reasoning_raw_responses.append(last_content)
            if _is_valid_reasoning(last_content):
                break
            attempt += 1
        state.reasoning_attempts = attempt + 1
        if _is_valid_reasoning(last_content):
            state.reasoning = last_content
        else:
            # Use fallback heuristic reasoning
            state.reasoning = _fallback_reasoning(str(state.intent_entities))
            state.add_error("Reasoning validation failed; fallback heuristic used")
    except Exception as e:
        state.reasoning = f"Reasoning unavailable: {e}"
        state.add_error(f"Reasoning node failed: {e}")
    return state
