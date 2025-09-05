from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Set
from .schema_models import SchemaSpec, Dimension, Fact, Column, Index


@dataclass
class Operation:
    op: str  # e.g., CREATE_TABLE, ADD_COLUMN, CREATE_INDEX, ADD_FOREIGN_KEY
    table: str
    payload: object | None = None  # Column | Index | ForeignKey | Dimension/Fact
    extra: dict | None = None      # auxiliary data (e.g., FK parsed parts)


def _columns_map(obj: Dimension | Fact) -> Dict[str, Column]:
    cols: Dict[str, Column] = {c.name: c for c in obj.columns}
    if isinstance(obj, Fact):
        for m in obj.measures:
            cols[m.name] = m
    return cols


def plan_migration(current: SchemaSpec | None, target: SchemaSpec) -> List[Operation]:
    ops: List[Operation] = []
    current_tables = current.table_dict() if current else {}
    target_tables = target.table_dict()

    new_tables: List[Operation] = []
    add_columns: List[Operation] = []
    add_indexes: List[Operation] = []
    add_fks: List[Operation] = []

    # Pass 1: tables
    for tname, obj in target_tables.items():
        cur_obj = current_tables.get(tname)
        if cur_obj is None and isinstance(obj, (Dimension, Fact)):
            new_tables.append(Operation("CREATE_TABLE", tname, obj))
        elif cur_obj and isinstance(obj, (Dimension, Fact)) and isinstance(cur_obj, (Dimension, Fact)):
            # Columns diff
            cur_cols = _columns_map(cur_obj)
            tgt_cols = _columns_map(obj)
            for cname, col in tgt_cols.items():
                if cname not in cur_cols:
                    add_columns.append(Operation("ADD_COLUMN", tname, col))
            # Indexes diff (naive: by name)
            cur_indexes: Set[str] = set()
            if isinstance(cur_obj, Dimension):
                cur_indexes = {idx.name for idx in cur_obj.indexes}
            elif isinstance(cur_obj, Fact):
                cur_indexes = {idx.name for idx in cur_obj.indexes}
            tgt_indexes: List[Index] = []
            if isinstance(obj, Dimension):
                tgt_indexes = obj.indexes
            elif isinstance(obj, Fact):
                tgt_indexes = obj.indexes
            for idx in tgt_indexes:
                if idx.name not in cur_indexes:
                    add_indexes.append(Operation("CREATE_INDEX", tname, idx))
            # Foreign keys diff (present only on facts now)
            if isinstance(obj, Fact):
                cur_fk_cols: Set[str] = set()
                if isinstance(cur_obj, Fact):
                    cur_fk_cols = {fk.column for fk in cur_obj.foreign_keys}
                for fk in obj.foreign_keys:
                    if fk.column not in cur_fk_cols:
                        # parse references table(column)
                        ref = fk.references
                        if "(" in ref and ref.endswith(")"):
                            ref_table, ref_col = ref[:-1].split("(")
                        else:
                            ref_table, ref_col = ref, "id"
                        extra = {"ref_table": ref_table, "ref_column": ref_col}
                        add_fks.append(Operation("ADD_FOREIGN_KEY", tname, fk, extra=extra))

    # Ordering: create tables -> add columns -> indexes -> foreign keys
    ops.extend(new_tables)
    ops.extend(add_columns)
    ops.extend(add_indexes)
    ops.extend(add_fks)
    return ops

