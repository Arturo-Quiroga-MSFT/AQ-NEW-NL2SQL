"""LangGraph pipeline: schema_ctx → intent → sql_gen → sanitize → execute."""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from .state import GraphState
from .nodes import schema_ctx, intent, sql_gen, sanitize, execute


def route_after_schema(state: GraphState) -> str:
    if state.flags.explain_only:
        return "sanitize"
    return "intent"


def build() -> StateGraph:
    g: StateGraph = StateGraph(GraphState)

    g.add_node("schema_ctx", schema_ctx.run)
    g.add_node("intent", intent.run)
    g.add_node("sql_gen", sql_gen.run)
    g.add_node("sanitize", sanitize.run)
    g.add_node("execute", execute.run)

    g.set_entry_point("schema_ctx")
    g.add_conditional_edges(
        "schema_ctx",
        route_after_schema,
        {"intent": "intent", "sanitize": "sanitize"},
    )
    g.add_edge("intent", "sql_gen")
    g.add_edge("sql_gen", "sanitize")
    g.add_edge("sanitize", "execute")
    g.add_edge("execute", END)

    return g.compile()
