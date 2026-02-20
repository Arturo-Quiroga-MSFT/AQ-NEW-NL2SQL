"""Dynamic schema reader with JSON cache and Entra ID auth support."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .db_connect import get_connection

_HERE = Path(__file__).parent
CACHE_DIR = _HERE.parent.parent / "database"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE_DIR / "schema_cache.json"

_DB = os.getenv("AZURE_SQL_DB", "RetailDW")
_SERVER = os.getenv("AZURE_SQL_SERVER", "")


def _fetch_live_schema() -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "database_name": _DB,
        "server": _SERVER,
        "tables": {},
        "relationships": [],
        "views": {},
        "timestamp": time.time(),
    }
    with get_connection() as conn:
        cur = conn.cursor()

        # Tables and views
        cur.execute(
            "SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE "
            "FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE IN ('BASE TABLE','VIEW') "
            "  AND TABLE_SCHEMA NOT IN ('sys','INFORMATION_SCHEMA') "
            "ORDER BY TABLE_SCHEMA, TABLE_NAME"
        )
        table_list = [(r[0], r[1], r[2]) for r in cur.fetchall()]

        for sch, tbl, ttype in table_list:
            cur.execute(
                "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE "
                "FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA=? AND TABLE_NAME=? ORDER BY ORDINAL_POSITION",
                (sch, tbl),
            )
            cols = []
            for r in cur.fetchall():
                c: Dict[str, Any] = {"name": r[0], "type": r[1], "nullable": r[3] == "YES"}
                if r[2]:
                    c["max_length"] = r[2]
                cols.append(c)
            full = f"{sch}.{tbl}"
            if ttype == "BASE TABLE":
                data["tables"][full] = cols
            else:
                data["views"][full] = cols

        # Primary keys
        cur.execute(
            "SELECT s.name, t.name, c.name "
            "FROM sys.key_constraints kc "
            "JOIN sys.tables t ON kc.parent_object_id=t.object_id "
            "JOIN sys.schemas s ON t.schema_id=s.schema_id "
            "JOIN sys.index_columns ic ON kc.parent_object_id=ic.object_id AND kc.unique_index_id=ic.index_id "
            "JOIN sys.columns c ON ic.object_id=c.object_id AND ic.column_id=c.column_id "
            "WHERE kc.type='PK'"
        )
        for r in cur.fetchall():
            full = f"{r[0]}.{r[1]}"
            if full in data["tables"]:
                for col in data["tables"][full]:
                    if col["name"] == r[2]:
                        col["is_primary_key"] = True

        # Foreign keys
        cur.execute(
            "SELECT tp_s.name, tp.name, cp.name, tr_s.name, tr.name, cr.name, fk.name "
            "FROM sys.foreign_keys fk "
            "JOIN sys.foreign_key_columns fkc ON fk.object_id=fkc.constraint_object_id "
            "JOIN sys.tables tp ON fkc.parent_object_id=tp.object_id "
            "JOIN sys.schemas tp_s ON tp.schema_id=tp_s.schema_id "
            "JOIN sys.columns cp ON fkc.parent_object_id=cp.object_id AND fkc.parent_column_id=cp.column_id "
            "JOIN sys.tables tr ON fkc.referenced_object_id=tr.object_id "
            "JOIN sys.schemas tr_s ON tr.schema_id=tr_s.schema_id "
            "JOIN sys.columns cr ON fkc.referenced_object_id=cr.object_id AND fkc.referenced_column_id=cr.column_id"
        )
        for r in cur.fetchall():
            data["relationships"].append({
                "constraint": r[6],
                "from_table": f"{r[0]}.{r[1]}",
                "from_column": r[2],
                "to_table": f"{r[3]}.{r[4]}",
                "to_column": r[5],
            })
    return data


def _save_cache(data: Dict[str, Any]) -> None:
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _load_cache() -> Dict[str, Any]:
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {"tables": {}, "views": {}, "relationships": [], "timestamp": 0}


def refresh_schema_cache() -> Path:
    data = _fetch_live_schema()
    _save_cache(data)
    return CACHE_FILE


def _build_context(meta: Dict[str, Any]) -> str:
    lines: list[str] = []
    db = meta.get("database_name", "RetailDW")
    srv = meta.get("server", "")
    ts = meta.get("timestamp", 0)
    ts_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "unknown"

    lines.append(f"DATABASE: {db} on {srv}")
    lines.append(f"Schema cached: {ts_str}\n")

    lines.append("SQL GENERATION GUIDELINES:")
    lines.append("- Generate T-SQL for Azure SQL Database")
    lines.append("- Use TWO-PART names: schema.TableName (e.g. dim.DimCustomer, fact.FactOrders)")
    lines.append("- Star schema: dimension tables in 'dim' schema, fact tables in 'fact' schema")
    lines.append("- Reference tables in 'ref' schema, views in 'dbo' schema")
    lines.append("- Return a single SELECT statement (optionally with CTEs)")
    lines.append("- No USE, GO, INSERT, UPDATE, DELETE, DROP")
    lines.append("- Handle NULLs appropriately\n")

    # Views
    views = meta.get("views", {})
    if views:
        lines.append("VIEWS (pre-joined for common queries):")
        for vname, cols in sorted(views.items()):
            cnames = [c["name"] for c in cols[:15]]
            lines.append(f"  {vname}: {', '.join(cnames)}")
        lines.append("")

    # Tables
    tables = meta.get("tables", {})
    if tables:
        lines.append("TABLES:")
        for tname, cols in sorted(tables.items()):
            lines.append(f"\n  {tname}:")
            for col in cols:
                pk = " [PK]" if col.get("is_primary_key") else ""
                lines.append(f"    {col['name']} ({col['type']}){pk}")
        lines.append("")

    # Relationships
    rels = meta.get("relationships", [])
    if rels:
        lines.append("FOREIGN KEY RELATIONSHIPS:")
        for r in rels:
            lines.append(f"  {r['from_table']}.{r['from_column']} -> {r['to_table']}.{r['to_column']}")
        lines.append("")

    lines.append(f"SUMMARY: {len(tables)} tables, {len(views)} views, {len(rels)} relationships")
    return "\n".join(lines)


def get_schema_context(ttl_seconds: Optional[int] = None) -> str:
    ttl = 86400 if ttl_seconds is None else ttl_seconds
    stale = True
    if CACHE_FILE.exists():
        age = time.time() - CACHE_FILE.stat().st_mtime
        stale = age > ttl

    if stale:
        refresh_schema_cache()

    meta = _load_cache()
    if not meta.get("tables"):
        refresh_schema_cache()
        meta = _load_cache()

    return _build_context(meta)
