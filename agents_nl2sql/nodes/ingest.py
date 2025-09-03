from __future__ import annotations
from ..state import GraphState, Flags


def run(user_query: str, flags: Flags | None = None) -> GraphState:
    state = GraphState(user_query=user_query, flags=flags or Flags())
    return state
