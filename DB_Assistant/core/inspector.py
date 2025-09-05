from __future__ import annotations

"""Basic reverse inspection utilities (Phase 0).

Currently captures table names & columns only (no FKs, indexes yet).
"""
from typing import List, Dict
from .schema_models import SchemaSpec, Entities, Dimension, Fact, Column, ForeignKey, Index


def inspect_database(cursor) -> SchemaSpec:
    """Reverse engineer tables, columns, simplistic FK & index metadata.

    Notes:
      - Surrogate keys not derivable reliably; left None.
      - Index uniqueness & columns derived via sys.indexes/sys.index_columns.
      - Foreign keys parsed into ForeignKey objects referencing referenced table & column.
    """
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
    table_rows = [r[0] for r in cursor.fetchall()]

    # Preload columns
    columns_by_table: Dict[str, List[Column]] = {}
    for tname in table_rows:
        cursor.execute(
            "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, NUMERIC_PRECISION, NUMERIC_SCALE "
            "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
            (tname,),
        )
        cols: List[Column] = []
        for col_name, data_type, is_nullable, num_p, num_s in cursor.fetchall():
            # Reconstruct DECIMAL precision/scale if available
            dt_norm = data_type.upper()
            if dt_norm in ("DECIMAL", "NUMERIC"):
                if num_p is not None and num_s is not None:
                    dt_norm = f"DECIMAL({int(num_p)},{int(num_s)})"
            dtype = _normalize_type(dt_norm)
            nullable = (is_nullable == "YES")
            try:
                cols.append(Column(name=col_name.lower(), type=dtype, nullable=nullable))
            except Exception:
                # Extend: silently skip unsupported types
                pass
        columns_by_table[tname] = cols

    # Foreign keys (table -> list)
    fk_sql = (
        "SELECT fk.name, tp.name AS parent_table, cp.name AS parent_col, tr.name AS ref_table, cr.name AS ref_col "
        "FROM sys.foreign_keys fk "
        "JOIN sys.foreign_key_columns fkc ON fk.object_id=fkc.constraint_object_id "
        "JOIN sys.tables tp ON fkc.parent_object_id=tp.object_id "
        "JOIN sys.columns cp ON fkc.parent_object_id=cp.object_id AND fkc.parent_column_id=cp.column_id "
        "JOIN sys.tables tr ON fkc.referenced_object_id=tr.object_id "
        "JOIN sys.columns cr ON fkc.referenced_object_id=cr.object_id AND fkc.referenced_column_id=cr.column_id"
    )
    cursor.execute(fk_sql)
    fks_map: Dict[str, List[ForeignKey]] = {}
    for _, parent_table, parent_col, ref_table, ref_col in cursor.fetchall():
        fk_obj = ForeignKey(column=parent_col.lower(), references=f"{ref_table}({ref_col.lower()})")
        fks_map.setdefault(parent_table, []).append(fk_obj)

    # Indexes (excluding primary keys) – simplified
    idx_sql = (
        "SELECT i.name, t.name AS table_name, i.is_unique "
        "FROM sys.indexes i JOIN sys.tables t ON i.object_id=t.object_id "
        "WHERE i.index_id > 0 AND i.is_hypothetical = 0 AND i.name IS NOT NULL"
    )
    cursor.execute(idx_sql)
    idx_names = [(r[0], r[1], r[2]) for r in cursor.fetchall()]
    # Map index -> columns
    idx_cols_sql = (
        "SELECT i.name, t.name, c.name FROM sys.indexes i "
        "JOIN sys.index_columns ic ON i.object_id=ic.object_id AND i.index_id=ic.index_id "
        "JOIN sys.columns c ON ic.object_id=c.object_id AND ic.column_id=c.column_id "
        "JOIN sys.tables t ON i.object_id=t.object_id WHERE i.name IS NOT NULL"
    )
    cursor.execute(idx_cols_sql)
    idx_cols_map: Dict[tuple, List[str]] = {}
    for iname, tname, col in cursor.fetchall():
        idx_cols_map.setdefault((iname, tname), []).append(col.lower())
    indexes_by_table: Dict[str, List[Index]] = {}
    for iname, tname, is_unique in idx_names:
        cols = idx_cols_map.get((iname, tname), [])
        # skip PK-like indexes (heuristic) starting with pk_
        if iname.startswith("pk_"):
            continue
        try:
            indexes_by_table.setdefault(tname, []).append(Index(name=iname, columns=cols, unique=bool(is_unique)))
        except Exception:
            pass

    dims: List[Dimension] = []
    facts: List[Fact] = []
    for tname in table_rows:
        cols = columns_by_table.get(tname, [])
        if tname.startswith("dim_"):
            dims.append(Dimension(name=tname, surrogate_key=None, columns=cols, indexes=indexes_by_table.get(tname, [])))
        elif tname.startswith("fact_"):
            # Heuristic: classify DECIMAL(*) columns (not *_id, not *_key, not date) as measures
            fact_measures: List[Column] = []
            fact_cols: List[Column] = []
            for c in cols:
                if c.type.startswith("DECIMAL") and not (c.name.endswith("_id") or c.name.endswith("_key") or c.name.endswith("date")):
                    fact_measures.append(c)
                else:
                    fact_cols.append(c)
            facts.append(Fact(name=tname, grain=None, columns=fact_cols, measures=fact_measures, foreign_keys=fks_map.get(tname, []), indexes=indexes_by_table.get(tname, [])))
    return SchemaSpec(version=1, warehouse=None, entities=Entities(dimensions=dims, facts=facts))


def _normalize_type(db_type: str) -> str:
    dt = db_type.upper()
    if dt in ("INT", "BIGINT", "SMALLINT", "TINYINT", "DATE", "DATETIME", "DATETIME2"):
        return dt
    if dt.startswith("DECIMAL"):
        # retain precision/scale if matches common patterns
        return dt
    if dt.startswith("VARCHAR"):
        # Keep first parenthetical length if present else default 50
        return "VARCHAR(50)"
    if dt in ("BIT", "FLOAT", "REAL"):
        return dt
    # Fallback
    return "VARCHAR(50)"
