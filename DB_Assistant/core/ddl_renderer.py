from __future__ import annotations

from .schema_models import Dimension, Fact, Column, Index
from .migration_planner import Operation


def render_create_table(op: Operation) -> str:
    obj = op.payload
    assert isinstance(obj, (Dimension, Fact))
    cols: list[Column] = []
    # Surrogate / natural keys are just columns; we assume they are already in columns list if needed.
    if isinstance(obj, Dimension):
        cols.extend(obj.columns)
    else:  # Fact
        cols.extend(obj.columns)
        cols.extend(obj.measures)

    col_defs = []
    for c in cols:
        null_sql = "NULL" if c.nullable else "NOT NULL"
        col_defs.append(f"    {c.name} {c.type} {null_sql}")
    col_section = ",\n".join(col_defs)
    return f"CREATE TABLE {obj.name} (\n{col_section}\n);"


def _render_add_column(table: str, col: Column) -> str:
    null_sql = "NULL" if col.nullable else "NOT NULL"
    return f"ALTER TABLE {table} ADD {col.name} {col.type} {null_sql};"


def _render_create_index(table: str, idx: Index) -> str:
    cols = ", ".join(idx.columns)
    unique = "UNIQUE " if idx.unique else ""
    return f"CREATE {unique}INDEX {idx.name} ON {table} ({cols});"


def _render_add_foreign_key(table: str, fk_op: Operation) -> str:
    fk = fk_op.payload
    assert fk is not None
    ref_table = fk_op.extra["ref_table"] if fk_op.extra else "unknown_table"
    ref_col = fk_op.extra["ref_column"] if fk_op.extra else "id"
    constraint = f"fk_{table}_{fk.column}"
    return (
        f"ALTER TABLE {table} ADD CONSTRAINT {constraint} FOREIGN KEY ({fk.column}) "
        f"REFERENCES {ref_table} ({ref_col});"
    )


def operations_to_sql(ops: list[Operation]) -> str:
    statements: list[str] = []
    for op in ops:
        if op.op == "CREATE_TABLE":
            statements.append(render_create_table(op))
        elif op.op == "ADD_COLUMN":
            statements.append(_render_add_column(op.table, op.payload))
        elif op.op == "CREATE_INDEX":
            statements.append(_render_create_index(op.table, op.payload))
        elif op.op == "ADD_FOREIGN_KEY":
            statements.append(_render_add_foreign_key(op.table, op))
    return "\n\n".join(statements)

