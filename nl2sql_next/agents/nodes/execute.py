"""Execute node — runs sanitized SQL against RetailDW."""
from __future__ import annotations

from typing import Dict, List

from ..state import GraphState
from ..tools.sql_tools import execute_sql_query


def _format_table(rows: List[Dict]) -> str:
    if not rows:
        return "No results returned.\n"
    cols = list(rows[0].keys())
    widths = {c: max(len(c), max(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    header = " | ".join(c.ljust(widths[c]) for c in cols)
    sep = "-+-".join("-" * widths[c] for c in cols)
    lines = [header, sep]
    for r in rows:
        lines.append(" | ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))
    return "\n".join(lines) + "\n"


def run(state: GraphState) -> GraphState:
    if state.flags.no_exec or state.flags.explain_only:
        state.execution_result.preview = "[NO_EXEC] Execution skipped."
        return state
    sql = state.sql_sanitized.strip() if state.sql_sanitized else ""
    if not sql:
        state.execution_result.preview = "[INFO] No SQL to execute."
        return state
    rows: list = []
    try:
        rows = execute_sql_query(sql)
    except Exception as e:
        state.add_error(f"SQL execution failed: {e}")
    state.execution_result.rows = rows
    state.execution_result.preview = _format_table(rows)
    return state
