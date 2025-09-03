from __future__ import annotations
from ..state import GraphState
from ..llm import azure_chat_completions, accumulate_usage

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


def run(state: GraphState) -> GraphState:
    try:
        prompt = REASONING_PROMPT_TEXT.format(schema=state.schema_context, intent_entities=state.intent_entities)
        messages = [{"role": "user", "content": prompt.strip()}]
        content, usage = azure_chat_completions(messages, max_completion_tokens=512)
        updated = accumulate_usage(usage, state.token_usage.model_dump())
        state.token_usage.prompt = updated.get("prompt", 0)
        state.token_usage.completion = updated.get("completion", 0)
        state.token_usage.total = updated.get("total", 0)
        state.reasoning = content
    except Exception as e:
        state.reasoning = f"Reasoning unavailable: {e}"
        state.add_error(f"Reasoning node failed: {e}")
    return state
