from __future__ import annotations
from ..state import GraphState


def run(state: GraphState) -> GraphState:
    # Placeholder: no LLM yet; leave sql_raw empty to rely on sanitizer/no-exec path in demo
    state.sql_raw = ""
    return state
