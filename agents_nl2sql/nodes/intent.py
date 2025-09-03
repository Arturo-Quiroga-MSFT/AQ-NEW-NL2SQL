from __future__ import annotations
from ..state import GraphState
from ..llm import azure_chat_completions, accumulate_usage

INTENT_PROMPT_TEXT = (
    """
    You are an expert in translating natural language to database queries. Extract the intent and entities from the following user input:
    {input}
    """
)


def run(state: GraphState) -> GraphState:
    try:
        prompt = INTENT_PROMPT_TEXT.format(input=state.user_query)
        messages = [{"role": "user", "content": prompt.strip()}]
        content, usage = azure_chat_completions(messages, max_completion_tokens=512)
        updated = accumulate_usage(usage, state.token_usage.model_dump())
        state.token_usage.prompt = updated.get("prompt", 0)
        state.token_usage.completion = updated.get("completion", 0)
        state.token_usage.total = updated.get("total", 0)
        state.intent_entities = content
    except Exception as e:
        state.intent_entities = state.user_query
        state.add_error(f"Intent node failed: {e}")
    return state
