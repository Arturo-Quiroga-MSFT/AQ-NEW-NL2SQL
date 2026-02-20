"""Dynamic schema reader with JSON cache, sample rows, and LLM context builder.

Usage:
    from core.schema import get_schema_context, refresh_schema_cache

    context = get_schema_context()          # uses 24h cache
    context = get_schema_context(ttl=0)     # force refresh
    refresh_schema_cache()                  # explicit refresh
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .db import get_connection, DATABASE, SERVER

_HERE = Path(__file__).parent
CACHE_DIR = _HERE.parent / "database"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE_DIR / "schema_cache.json"

SAMPLE_ROWS = 3  # number of sample rows per table to include in cache


# ── live schema fetch ───────────────────────────────────

def _fetch_live_schema() -> Dict[str, Any]:
    """Query database for full schema metadata including sample rows."""
    data: Dict[str, Any] = {
        "database_name": DATABASE,
        "server": SERVER,
        "tables": {},
        "relationships": [],
        "views": {},
        "sample_rows": {},
        "row_counts": {},
        "timestamp": time.time(),
    }
    with get_connection() as conn:
        cur = conn.cursor()

        # 1) Tables and views
        cur.execute(
            "SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE "
            "FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE IN ('BASE TABLE','VIEW') "
            "  AND TABLE_SCHEMA NOT IN ('sys','INFORMATION_SCHEMA') "
            "ORDER BY TABLE_SCHEMA, TABLE_NAME"
        )
        table_list = [(r[0], r[1], r[2]) for r in cur.fetchall()]

        # 2) Columns per table/view
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

        # 3) Primary keys
        cur.execute(
            "SELECT s.name, t.name, c.name "
            "FROM sys.key_constraints kc "
            "JOIN sys.tables t ON kc.parent_object_id=t.object_id "
            "JOIN sys.schemas s ON t.schema_id=s.schema_id "
            "JOIN sys.index_columns ic ON kc.parent_object_id=ic.object_id "
            "  AND kc.unique_index_id=ic.index_id "
            "JOIN sys.columns c ON ic.object_id=c.object_id "
            "  AND ic.column_id=c.column_id "
            "WHERE kc.type='PK'"
        )
        for r in cur.fetchall():
            full = f"{r[0]}.{r[1]}"
            if full in data["tables"]:
                for col in data["tables"][full]:
                    if col["name"] == r[2]:
                        col["is_primary_key"] = True

        # 4) Foreign keys
        cur.execute(
            "SELECT tp_s.name, tp.name, cp.name, "
            "       tr_s.name, tr.name, cr.name, fk.name "
            "FROM sys.foreign_keys fk "
            "JOIN sys.foreign_key_columns fkc ON fk.object_id=fkc.constraint_object_id "
            "JOIN sys.tables tp ON fkc.parent_object_id=tp.object_id "
            "JOIN sys.schemas tp_s ON tp.schema_id=tp_s.schema_id "
            "JOIN sys.columns cp ON fkc.parent_object_id=cp.object_id "
            "  AND fkc.parent_column_id=cp.column_id "
            "JOIN sys.tables tr ON fkc.referenced_object_id=tr.object_id "
            "JOIN sys.schemas tr_s ON tr.schema_id=tr_s.schema_id "
            "JOIN sys.columns cr ON fkc.referenced_object_id=cr.object_id "
            "  AND fkc.referenced_column_id=cr.column_id"
        )
        for r in cur.fetchall():
            data["relationships"].append({
                "constraint": r[6],
                "from_table": f"{r[0]}.{r[1]}",
                "from_column": r[2],
                "to_table": f"{r[3]}.{r[4]}",
                "to_column": r[5],
            })

        # 5) Row counts and sample rows for each table
        all_tables = list(data["tables"].keys()) + list(data["views"].keys())
        for full_name in all_tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {full_name}")
                data["row_counts"][full_name] = cur.fetchone()[0]
            except Exception:
                data["row_counts"][full_name] = -1

            if SAMPLE_ROWS > 0:
                try:
                    cur.execute(f"SELECT TOP {SAMPLE_ROWS} * FROM {full_name}")
                    col_names = [desc[0] for desc in cur.description]
                    rows = []
                    for row in cur.fetchall():
                        rows.append({col_names[i]: _serialize(row[i]) for i in range(len(col_names))})
                    data["sample_rows"][full_name] = rows
                except Exception:
                    data["sample_rows"][full_name] = []

    return data


def _serialize(val: Any) -> Any:
    """Convert non-JSON-serializable types to strings."""
    if val is None:
        return None
    if isinstance(val, (int, float, bool, str)):
        return val
    return str(val)


# ── cache management ────────────────────────────────────

def _save_cache(data: Dict[str, Any]) -> None:
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _load_cache() -> Dict[str, Any]:
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {"tables": {}, "views": {}, "relationships": [], "sample_rows": {}, "row_counts": {}, "timestamp": 0}


def refresh_schema_cache() -> Path:
    """Fetch fresh schema from database and save to cache."""
    data = _fetch_live_schema()
    _save_cache(data)
    return CACHE_FILE


# ── context builder ─────────────────────────────────────

def _build_context(meta: Dict[str, Any]) -> str:
    """Build human-readable schema context string for LLM prompts."""
    lines: list[str] = []
    db = meta.get("database_name", "RetailDW")
    srv = meta.get("server", "")
    ts = meta.get("timestamp", 0)
    ts_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "unknown"
    counts = meta.get("row_counts", {})

    lines.append(f"DATABASE: {db} on {srv}")
    lines.append(f"Schema cached: {ts_str}\n")

    lines.append("SQL GENERATION GUIDELINES:")
    lines.append("- Generate T-SQL for Azure SQL Database")
    lines.append("- Use TWO-PART names: schema.TableName (e.g. dim.DimCustomer, fact.FactOrders)")
    lines.append("- Star schema: dimensions in 'dim', facts in 'fact', references in 'ref'")
    lines.append("- Return a single SELECT statement (CTEs OK)")
    lines.append("- No USE, GO, INSERT, UPDATE, DELETE, DROP, TRUNCATE")
    lines.append("- Handle NULLs with ISNULL/COALESCE as needed\n")

    # Views
    views = meta.get("views", {})
    if views:
        lines.append("VIEWS (pre-joined, convenient for common queries):")
        for vname, cols in sorted(views.items()):
            rc = counts.get(vname, "")
            rc_str = f"  [{rc:,} rows]" if isinstance(rc, int) and rc >= 0 else ""
            cnames = [c["name"] for c in cols[:12]]
            lines.append(f"  {vname}{rc_str}: {', '.join(cnames)}")
        lines.append("")

    # Tables
    tables = meta.get("tables", {})
    if tables:
        lines.append("TABLES:")
        for tname, cols in sorted(tables.items()):
            rc = counts.get(tname, "")
            rc_str = f" [{rc:,} rows]" if isinstance(rc, int) and rc >= 0 else ""
            lines.append(f"\n  {tname}{rc_str}:")
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

    # Sample rows
    samples = meta.get("sample_rows", {})
    if samples:
        lines.append("SAMPLE DATA (first rows per table):")
        for tname in sorted(samples.keys()):
            rows = samples[tname]
            if not rows:
                continue
            lines.append(f"\n  {tname}:")
            # Header
            headers = list(rows[0].keys())
            # Truncate wide tables to first 8 columns
            show = headers[:8]
            extra = len(headers) - len(show)
            lines.append(f"    {' | '.join(show)}")
            for row in rows:
                vals = [_fmt(row.get(h)) for h in show]
                lines.append(f"    {' | '.join(vals)}")
            if extra:
                lines.append(f"    ... +{extra} more columns")
        lines.append("")

    lines.append(f"SUMMARY: {len(tables)} tables, {len(views)} views, {len(rels)} relationships")
    return "\n".join(lines)


def _fmt(val: Any) -> str:
    """Format a value for display in sample rows."""
    if val is None:
        return "NULL"
    s = str(val)
    return s[:30] + "…" if len(s) > 30 else s


# ── public API ──────────────────────────────────────────

def get_schema_context(ttl: Optional[int] = None) -> str:
    """Return LLM-ready schema context string.

    Args:
        ttl: Cache freshness in seconds. None = 24h default.
             0 = force refresh from database.
    """
    ttl_sec = 86400 if ttl is None else ttl
    stale = True

    if CACHE_FILE.exists():
        age = time.time() - CACHE_FILE.stat().st_mtime
        stale = age > ttl_sec

    if stale:
        refresh_schema_cache()

    meta = _load_cache()
    if not meta.get("tables"):
        refresh_schema_cache()
        meta = _load_cache()

    return _build_context(meta)
