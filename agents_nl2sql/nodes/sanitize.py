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
    return code


def run(state: GraphState) -> GraphState:
    state.sql_sanitized = _extract_and_sanitize(state.sql_raw)
    return state
