from __future__ import annotations
from typing import List, Dict
from .dsl import NLAction

_DEFAULT_TYPE = "VARCHAR(50)"
_SIMPLE_TYPES = {"int","bigint","smallint","tinyint","date","datetime2","decimal(18,2)","decimal(19,4)","varchar(20)","varchar(40)","varchar(50)","varchar(60)","varchar(100)","nvarchar(100)"}


def _parse_column_list(raw_cols: str) -> List[Dict]:
    cols: List[Dict] = []
    parts = [p.strip() for p in raw_cols.split(',') if p.strip()]
    for p in parts:
        bits = p.split()
        name = bits[0]
        ctype = _DEFAULT_TYPE
        if len(bits) > 1:
            cand = bits[1].lower()
            if cand in _SIMPLE_TYPES or cand.startswith('varchar('):
                ctype = cand.upper()
        cols.append({"name": name, "type": ctype})
    return cols


def render_sql(action: NLAction) -> str | None:
    intent = action.intent
    if intent == 'list_tables':
        return ("SELECT t.TABLE_SCHEMA + '.' + t.TABLE_NAME AS table_name, COUNT(c.COLUMN_NAME) AS column_count "
                "FROM INFORMATION_SCHEMA.TABLES t LEFT JOIN INFORMATION_SCHEMA.COLUMNS c ON c.TABLE_SCHEMA=t.TABLE_SCHEMA "
                "AND c.TABLE_NAME=t.TABLE_NAME WHERE t.TABLE_TYPE='BASE TABLE' GROUP BY t.TABLE_SCHEMA,t.TABLE_NAME ORDER BY 1;")
    if intent == 'describe_table' and action.table:
        tbl = action.table.split('.')[-1]
        return ("SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH "
                f"FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{tbl}' ORDER BY ORDINAL_POSITION;")
    if intent == 'row_count' and action.table:
        return f"SELECT COUNT(*) AS row_count FROM {action.table};"
    if intent == 'drop_table' and action.table:
        tbl = action.table.split('.')[-1]
        return f"IF OBJECT_ID('{tbl}','U') IS NOT NULL DROP TABLE {action.table};"
    if intent == 'create_table' and action.table:
        raw_cols = action.options.get('raw_cols','')
        cols = _parse_column_list(raw_cols) or [{"name":"id","type":"INT"}]
        col_sql = ', '.join(f"{c['name']} {c['type']}" for c in cols)
        tbl = action.table.split('.')[-1]
        return f"IF OBJECT_ID('{tbl}','U') IS NULL CREATE TABLE {action.table} ({col_sql});"
    if intent == 'add_column' and action.table:
        col = action.options.get('column'); ctype = action.options.get('ctype', _DEFAULT_TYPE)
        return f"IF COL_LENGTH('{action.table}', '{col}') IS NULL ALTER TABLE {action.table} ADD {col} {ctype};"
    if intent == 'drop_column' and action.table:
        col = action.options.get('column')
        return f"IF COL_LENGTH('{action.table}', '{col}') IS NOT NULL ALTER TABLE {action.table} DROP COLUMN {col};"
    if intent == 'create_index' and action.table:
        cols = action.options.get('cols','')
        first = cols.split(',')[0].strip()
        idx_name = f"ix_{action.table.split('.')[-1]}_{first}"
        return ("IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='"+idx_name+"' AND object_id=OBJECT_ID('"+action.table+"')) "
                f"CREATE INDEX {idx_name} ON {action.table} ({cols});")
    if intent == 'star_overview':
        # This is handled separately in existing code; returning None signals non-DDL diagnostic
        return None
    return None
