from __future__ import annotations
from ..state import GraphState


def run(state: GraphState) -> GraphState:
    # Placeholder: set intent_entities to the raw query for now
    state.intent_entities = state.user_query
    return state
