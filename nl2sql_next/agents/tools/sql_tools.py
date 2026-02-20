"""Execute read-only SQL against RetailDW."""
from __future__ import annotations

from typing import Any, Dict, List

from .db_connect import get_connection


def execute_sql_query(sql: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
