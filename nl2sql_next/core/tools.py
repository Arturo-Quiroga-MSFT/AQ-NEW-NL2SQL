"""Admin assistant tool definitions and execution engine (Phase 1: read-only).

Tools give the LLM the ability to inspect the live database:
- list_tables: enumerate all tables with schema, row count, type
- describe_table: column definitions, types, constraints, FKs
- run_read_query: execute arbitrary SELECT queries

Security: Phase 1 is read-only.  run_read_query enforces SELECT-only.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from .db import get_connection

# ── Tool definitions (OpenAI function-calling schema) ───

TOOLS_READ_ONLY: List[Dict[str, Any]] = [
    {
        "type": "function",
        "name": "list_tables",
        "description": (
            "List all user tables and views in the database with their "
            "schema name, object type, and approximate row count."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "describe_table",
        "description": (
            "Show column names, data types, nullability, default values, "
            "primary key, and foreign key relationships for a table or view."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": (
                        "Schema-qualified table name, e.g. dim.DimCustomer or "
                        "dbo.vw_MonthlySales"
                    ),
                },
            },
            "required": ["table_name"],
        },
    },
    {
        "type": "function",
        "name": "run_read_query",
        "description": (
            "Execute a read-only SQL SELECT query against the database and "
            "return the columns and up to 50 rows of results."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "A SELECT query to execute.",
                },
            },
            "required": ["sql"],
        },
    },
]


# ── Tool implementations ────────────────────────────────

def _sanitize_table_name(name: str) -> str:
    """Allow only schema.table format — prevent injection."""
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$", name):
        raise ValueError(f"Invalid table name: {name}")
    return name


def _is_select_only(sql: str) -> bool:
    """Ensure SQL is a read-only SELECT (no writes, no DDL)."""
    blocked = re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|EXEC|EXECUTE|xp_|sp_)\b",
        re.IGNORECASE,
    )
    code_lines = [line.split("--")[0] for line in sql.splitlines()]
    code = " ".join(code_lines)
    return not blocked.search(code)


def tool_list_tables() -> str:
    """List all user tables and views with row counts."""
    sql = """
    SELECT
        s.name       AS [schema],
        t.name       AS [table],
        t.type_desc  AS [type],
        p.row_count  AS [approx_rows]
    FROM sys.tables t
    JOIN sys.schemas s ON t.schema_id = s.schema_id
    LEFT JOIN (
        SELECT object_id, SUM(rows) AS row_count
        FROM sys.partitions
        WHERE index_id IN (0, 1)
        GROUP BY object_id
    ) p ON t.object_id = p.object_id
    UNION ALL
    SELECT
        s.name, v.name, 'VIEW', NULL
    FROM sys.views v
    JOIN sys.schemas s ON v.schema_id = s.schema_id
    ORDER BY 1, 2
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    return json.dumps(rows, default=str)


def tool_describe_table(table_name: str) -> str:
    """Describe columns, types, keys, and FKs for a table."""
    table_name = _sanitize_table_name(table_name)
    schema, table = table_name.split(".")

    # Column info
    col_sql = """
    SELECT
        c.name           AS [column],
        tp.name          AS [type],
        c.max_length,
        c.precision,
        c.scale,
        c.is_nullable,
        c.is_identity,
        dc.definition    AS [default]
    FROM sys.columns c
    JOIN sys.types tp ON c.user_type_id = tp.user_type_id
    JOIN sys.objects o ON c.object_id = o.object_id
    JOIN sys.schemas s ON o.schema_id = s.schema_id
    LEFT JOIN sys.default_constraints dc ON c.default_object_id = dc.object_id
    WHERE s.name = ? AND o.name = ?
    ORDER BY c.column_id
    """
    # Primary key columns
    pk_sql = """
    SELECT col.name
    FROM sys.indexes i
    JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
    JOIN sys.columns col ON ic.object_id = col.object_id AND ic.column_id = col.column_id
    JOIN sys.objects o ON i.object_id = o.object_id
    JOIN sys.schemas s ON o.schema_id = s.schema_id
    WHERE i.is_primary_key = 1 AND s.name = ? AND o.name = ?
    """
    # Foreign keys
    fk_sql = """
    SELECT
        fk.name            AS fk_name,
        cp.name            AS [column],
        rs.name + '.' + rt.name AS references_table,
        rcp.name           AS references_column
    FROM sys.foreign_keys fk
    JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
    JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
    JOIN sys.objects rt ON fkc.referenced_object_id = rt.object_id
    JOIN sys.schemas rs ON rt.schema_id = rs.schema_id
    JOIN sys.columns rcp ON fkc.referenced_object_id = rcp.object_id AND fkc.referenced_column_id = rcp.column_id
    JOIN sys.objects po ON fk.parent_object_id = po.object_id
    JOIN sys.schemas ps ON po.schema_id = ps.schema_id
    WHERE ps.name = ? AND po.name = ?
    """

    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute(col_sql, schema, table)
        cols_desc = [d[0] for d in cur.description]
        columns = [dict(zip(cols_desc, row)) for row in cur.fetchall()]

        cur.execute(pk_sql, schema, table)
        pk_cols = [row[0] for row in cur.fetchall()]

        cur.execute(fk_sql, schema, table)
        fk_desc = [d[0] for d in cur.description]
        fks = [dict(zip(fk_desc, row)) for row in cur.fetchall()]

    result = {
        "table": table_name,
        "columns": columns,
        "primary_key": pk_cols,
        "foreign_keys": fks,
    }
    return json.dumps(result, default=str)


def tool_run_read_query(sql: str) -> str:
    """Execute a SELECT query and return results (max 50 rows)."""
    if not _is_select_only(sql):
        return json.dumps({"error": "Only SELECT queries are allowed."})

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = [list(row) for row in cur.fetchmany(50)] if cols else []

    return json.dumps({"columns": cols, "rows": rows, "row_count": len(rows)},
                      default=str)


# ── Dispatcher ──────────────────────────────────────────

_TOOL_MAP = {
    "list_tables": lambda _args: tool_list_tables(),
    "describe_table": lambda args: tool_describe_table(args["table_name"]),
    "run_read_query": lambda args: tool_run_read_query(args["sql"]),
}


def execute_tool(name: str, arguments: str) -> str:
    """Execute a tool by name with JSON arguments. Returns JSON string."""
    fn = _TOOL_MAP.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        args = json.loads(arguments) if arguments else {}
        return fn(args)
    except Exception as e:
        return json.dumps({"error": str(e)})
