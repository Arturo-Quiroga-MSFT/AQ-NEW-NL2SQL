from __future__ import annotations
from ..state import GraphState
from ..tools.schema_tools import get_schema_context, refresh_schema_cache


def run(state: GraphState) -> GraphState:
    try:
        if state.flags.refresh_schema:
            try:
                refresh_schema_cache()
            except Exception as e:
                state.add_error(f"Schema refresh failed: {e}")
            # Always reload after refresh
            state.schema_context = get_schema_context(0)  # force reload
        else:
            # Use a 24h TTL for cache freshness (default in schema_reader is 24h)
            state.schema_context = get_schema_context(86400)
    except Exception as e:
        state.add_error(f"Schema context error: {e}")
    return state
