from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Set
from .schema_models import SchemaSpec, Dimension, Fact, Column, Index


@dataclass
class Operation:
    op: str  # e.g., CREATE_TABLE, ADD_COLUMN, ALTER_COLUMN, DROP_COLUMN, CREATE_INDEX, ADD_FOREIGN_KEY
    table: str
    payload: object | None = None  # Column | Index | ForeignKey | Dimension/Fact
    extra: dict | None = None      # auxiliary data (e.g., FK parsed parts, original column)


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
    alter_columns: List[Operation] = []
    drop_columns: List[Operation] = []
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
            # Add & alter
            for cname, tgt_col in tgt_cols.items():
                cur_col = cur_cols.get(cname)
                if cur_col is None:
                    add_columns.append(Operation("ADD_COLUMN", tname, tgt_col))
                else:
                    # Detect type or nullability change
                    if (cur_col.type.upper() != tgt_col.type.upper()) or (cur_col.nullable != tgt_col.nullable):
                        alter_columns.append(Operation("ALTER_COLUMN", tname, tgt_col, extra={"previous": cur_col}))
            # Drops (columns present in current but removed from target)
            for cname, cur_col in cur_cols.items():
                if cname not in tgt_cols:
                    # Do not drop surrogate key if accidentally omitted; heuristic: keep if name endswith '_key' and appears in any FK referencing this table
                    if cname.endswith('_key'):
                        continue
                    drop_columns.append(Operation("DROP_COLUMN", tname, cur_col))
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

    # Automatic index inference (simple heuristics):
    # - Add non-unique index on each foreign key column if not already declared
    # - Add composite index on fact grain (if multiple columns) if not declared
    for tname, obj in target_tables.items():
        existing_index_names = {i.payload.name for i in add_indexes if i.op == "CREATE_INDEX"}
        if isinstance(obj, Fact):
            declared_idx_cols = {tuple(sorted(idx.columns)): idx.name for idx in obj.indexes}
            # FK columns
            fk_cols = [fk.column for fk in obj.foreign_keys]
            for fk_col in fk_cols:
                # Skip if an index (single-col) already planned or declared
                if any(fk_col in cols for cols in declared_idx_cols.keys() if len(cols) == 1):
                    continue
                inferred_name = f"ix_{tname}_{fk_col}"[:120]
                if inferred_name not in existing_index_names:
                    add_indexes.append(Operation("CREATE_INDEX", tname, Index(name=inferred_name, columns=[fk_col], unique=False)))
            # Grain composite
            if obj.grain:
                grain_cols = [c.strip() for c in obj.grain.split(',') if c.strip()]
                if len(grain_cols) > 1:
                    sig = tuple(sorted(grain_cols))
                    if sig not in declared_idx_cols:
                        inferred_name = f"ix_{tname}_grain"[:120]
                        if inferred_name not in existing_index_names:
                            add_indexes.append(Operation("CREATE_INDEX", tname, Index(name=inferred_name, columns=grain_cols, unique=False)))

    # Ordering: create tables -> add columns -> alter columns -> drop columns -> indexes (declared + inferred) -> foreign keys
    ops.extend(new_tables)
    ops.extend(add_columns)
    ops.extend(alter_columns)
    ops.extend(drop_columns)
    ops.extend(add_indexes)
    ops.extend(add_fks)
    return ops

