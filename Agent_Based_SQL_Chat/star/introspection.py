"""Star schema introspection & diagnostics utilities.

Functions here provide lightweight classification of tables into
  - dimension
  - fact
  - reference
  - other
based on naming heuristics and relational characteristics.

Also provides diagnostic helpers (row counts, orphan checks, null density, FK map).

NOTE: These operate with a provided pyodbc connection object created externally.
"""
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import re

DIM_PREFIXES = ("dim_",)
FACT_PREFIXES = ("fact_",)
REF_PREFIXES = ("ref_",)


def list_tables(conn) -> List[Tuple[str, str]]:
    cur = conn.cursor()
    cur.execute("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
    return [(r[0], r[1]) for r in cur.fetchall()]


def classify_table(schema: str, name: str, fk_counts: Dict[str, int], row_counts: Dict[str, int]) -> str:
    lname = name.lower()
    key = f"{schema}.{name}"
    if any(lname.startswith(p) for p in FACT_PREFIXES):
        return "fact"
    if any(lname.startswith(p) for p in DIM_PREFIXES):
        return "dimension"
    if any(lname.startswith(p) for p in REF_PREFIXES) or schema.lower() == 'ref':
        return "reference"
    # heuristic: high number of FKs -> fact; low rows & few fks -> dimension-like
    fk_ct = fk_counts.get(key, 0)
    rows = row_counts.get(key, 0)
    if fk_ct >= 3 and rows > 1000:
        return "fact"
    if rows < 20000 and fk_ct <= 2:
        return "dimension"
    return "other"


def foreign_key_counts(conn) -> Dict[str, int]:
    sql = """
    SELECT s.name+'.'+t.name AS tbl, COUNT(*) AS fk_count
    FROM sys.foreign_keys fk
    JOIN sys.tables t ON fk.parent_object_id=t.object_id
    JOIN sys.schemas s ON s.schema_id=t.schema_id
    GROUP BY s.name, t.name
    """
    cur = conn.cursor(); cur.execute(sql)
    return {r[0]: r[1] for r in cur.fetchall()}


def row_counts(conn) -> Dict[str, int]:
    sql = """
    SELECT s.name+'.'+t.name AS tbl, SUM(p.rows) AS row_count
    FROM sys.tables t
    JOIN sys.schemas s ON s.schema_id=t.schema_id
    JOIN sys.partitions p ON p.object_id=t.object_id AND p.index_id IN (0,1)
    GROUP BY s.name, t.name
    """
    cur = conn.cursor(); cur.execute(sql)
    return {r[0]: r[1] for r in cur.fetchall()}


def build_star_overview(conn) -> List[Dict[str, Any]]:
    fks = foreign_key_counts(conn)
    rcs = row_counts(conn)
    overview: List[Dict[str, Any]] = []
    for schema, name in list_tables(conn):
        key = f"{schema}.{name}"
        classification = classify_table(schema, name, fks, rcs)
        overview.append({
            "table": key,
            "class": classification,
            "row_count": rcs.get(key, 0),
            "fk_count": fks.get(key, 0)
        })
    return sorted(overview, key=lambda x: (x['class'], x['table']))


def orphan_check(conn, fact_table: str) -> Dict[str, Any]:
    # Inspect foreign keys referencing dimensions & check for orphans
    schema, name = (fact_table.split('.', 1) + [None])[:2]
    if name is None:
        schema = 'dbo'; name = fact_table
    fk_sql = """
    SELECT fk.name, COL_NAME(fkc.parent_object_id,fkc.parent_column_id) AS fk_col,
           s_ref.name AS ref_schema, o_ref.name AS ref_table,
           COL_NAME(fkc.referenced_object_id,fkc.referenced_column_id) AS ref_col
    FROM sys.foreign_keys fk
    JOIN sys.foreign_key_columns fkc ON fk.object_id=fkc.constraint_object_id
    JOIN sys.objects o ON o.object_id=fk.parent_object_id
    JOIN sys.schemas s ON s.schema_id=o.schema_id
    JOIN sys.objects o_ref ON o_ref.object_id=fk.referenced_object_id
    JOIN sys.schemas s_ref ON s_ref.schema_id=o_ref.schema_id
    WHERE s.name=? AND o.name=?
    """
    cur = conn.cursor(); cur.execute(fk_sql, (schema, name))
    fks = cur.fetchall()
    results = []
    for row in fks:
        fk_name, fk_col, ref_schema, ref_table, ref_col = row
        q = f"SELECT COUNT(*) FROM {schema}.{name} f LEFT JOIN {ref_schema}.{ref_table} d ON f.{fk_col}=d.{ref_col} WHERE d.{ref_col} IS NULL"
        cur2 = conn.cursor(); cur2.execute(q)
        orphan_count = cur2.fetchone()[0]
        results.append({
            "fk": fk_name,
            "fk_column": fk_col,
            "ref_table": f"{ref_schema}.{ref_table}",
            "ref_column": ref_col,
            "orphans": orphan_count
        })
    return {"fact_table": fact_table, "checks": results}


def column_null_density(conn, table: str) -> List[Dict[str, Any]]:
    schema, name = (table.split('.', 1) + [None])[:2]
    if name is None:
        schema = 'dbo'; name = table
    cur = conn.cursor()
    # gather columns
    cur.execute("""SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=? AND TABLE_NAME=?""", (schema, name))
    cols = [r[0] for r in cur.fetchall()]
    densities: List[Dict[str, Any]] = []
    for c in cols:
        q = f"SELECT SUM(CASE WHEN [{c}] IS NULL THEN 1 ELSE 0 END) AS nulls, COUNT(*) AS total FROM {schema}.{name}"
        cur.execute(q)
        n, t = cur.fetchone()
        pct = (n / t) if t else 0
        densities.append({"column": c, "nulls": n, "total": t, "null_pct": round(pct, 4)})
    return densities


def top_value_distribution(conn, table: str, column: str, top: int = 20) -> List[Dict[str, Any]]:
    schema, name = (table.split('.', 1) + [None])[:2]
    if name is None:
        schema = 'dbo'; name = table
    sql = f"SELECT [{column}] AS value, COUNT(*) AS cnt FROM {schema}.{name} GROUP BY [{column}] ORDER BY cnt DESC OFFSET 0 ROWS FETCH NEXT {top} ROWS ONLY"
    cur = conn.cursor(); cur.execute(sql)
    rows = cur.fetchall()
    total = sum(r[1] for r in rows) or 1
    return [{"value": r[0], "count": r[1], "pct": round(r[1]/total,4)} for r in rows]


def compute_fact_health(conn, fact_table: str) -> Dict[str, Any]:
    oc = orphan_check(conn, fact_table)
    nulls_summary = []  # optional plug for future measure nullability
    return {"fact_table": fact_table, "orphans": oc["checks"], "nulls": nulls_summary}
