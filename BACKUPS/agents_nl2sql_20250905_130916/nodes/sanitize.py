from __future__ import annotations
import re
from ..state import GraphState


def _extract_and_sanitize(sql: str) -> str:
    if not sql:
        return ""
    code = sql
    m = re.search(r"```sql\s*([\s\S]+?)```", sql, re.IGNORECASE)
    if not m:
        m = re.search(r"```([\s\S]+?)```", sql)
    if m:
        code = m.group(1).strip()
    else:
        with_m = re.search(r"(?is)\bWITH\b\s+[A-Za-z0-9_\[\]]+\s+AS\s*\(", sql)
        if with_m:
            code = sql[with_m.start():].strip()
        else:
            m2 = re.search(r"(?is)\bSELECT\b[\s\S]+", sql)
            if m2:
                code = m2.group(0).strip()
            else:
                code = sql.strip()
    code = (code
            .replace('’', "'")
            .replace('‘', "'")
            .replace('“', '"')
            .replace('”', '"'))
    # Enforce SELECT-only
    forbidden = re.compile(r"(?is)\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|EXEC|GRANT|REVOKE|DENY)\b")
    if forbidden.search(code):
        return ""
    # Detect unsupported aggregate/subquery pattern for SQL Server
    # Example: SELECT SUM((SELECT ...)) or SELECT COUNT((SELECT ...))
    agg_subquery = re.compile(r"(?is)\b(SUM|COUNT|AVG|MIN|MAX)\s*\(\s*\(\s*SELECT[\s\S]+?\)\s*\)")
    if agg_subquery.search(code):
        code += "\n-- [WARNING] This query uses an aggregate function directly on a subquery in the SELECT clause, which is not supported in SQL Server. Consider rewriting using a CTE or JOIN."
    return code


def run(state: GraphState) -> GraphState:
    sanitized = _extract_and_sanitize(state.sql_raw)
    # If warning is present, add to errors for user visibility
    if '-- [WARNING]' in sanitized:
        state.add_error('SQL contains unsupported aggregate/subquery pattern. See warning in SQL output.')
    state.sql_sanitized = sanitized
    return state
