from __future__ import annotations
from typing import Callable
from langgraph.graph import StateGraph, END

from .state import GraphState
from .nodes import schema_ctx, intent, sql_gen, sanitize, execute


def _wrap(fn: Callable[[GraphState], GraphState]) -> Callable[[GraphState], GraphState]:
    # LangGraph nodes accept/return the state object directly in our case
    def _inner(state: GraphState) -> GraphState:
        return fn(state)
    return _inner


def route_after_schema(state: GraphState) -> str:
    if state.flags.explain_only:
        return "sanitize"
    return "intent"


def build() -> StateGraph:
    g: StateGraph = StateGraph(GraphState)

    g.add_node("schema_ctx", _wrap(schema_ctx.run))
    g.add_node("intent", _wrap(intent.run))
    g.add_node("sql_gen", _wrap(sql_gen.run))
    g.add_node("sanitize", _wrap(sanitize.run))
    g.add_node("execute", _wrap(execute.run))

    g.set_entry_point("schema_ctx")
    g.add_conditional_edges("schema_ctx", route_after_schema, {"intent": "intent", "sanitize": "sanitize"})
    g.add_edge("intent", "sql_gen")
    g.add_edge("sql_gen", "sanitize")
    g.add_edge("sanitize", "execute")
    g.add_edge("execute", END)

    return g.compile()
