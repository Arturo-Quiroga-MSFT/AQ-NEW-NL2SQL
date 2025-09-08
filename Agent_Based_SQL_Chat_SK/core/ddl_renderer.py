from __future__ import annotations

from .schema_models import Dimension, Fact, Column, Index
from .migration_planner import Operation


def render_create_table(op: Operation) -> str:
    obj = op.payload
    assert isinstance(obj, (Dimension, Fact))
    cols: list[Column] = []
    # Surrogate / natural keys are just columns; we assume they are already in columns list if needed.
    if isinstance(obj, Dimension):
        # Inject surrogate key column if declared but not explicitly listed
        sk = getattr(obj, "surrogate_key", None)
        existing = {c.name for c in obj.columns}
        if sk and sk not in existing:
            cols.append(Column(name=sk, type="INT", nullable=False))
        cols.extend(obj.columns)
    else:  # Fact
        cols.extend(obj.columns)
        cols.extend(obj.measures)

    col_defs = []
    for c in cols:
        null_sql = "NULL" if c.nullable else "NOT NULL"
        col_defs.append(f"    {c.name} {c.type} {null_sql}")
    col_section = ",\n".join(col_defs)
    # Primary key constraint if surrogate key present
    pk_line = ""
    if isinstance(obj, Dimension) and getattr(obj, "surrogate_key", None):
        pk_line = f",\n    CONSTRAINT pk_{obj.name} PRIMARY KEY CLUSTERED ({obj.surrogate_key})"

    # Wrap with IF NOT EXISTS guard for idempotent replay
    guard = (
        "IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = '"
        + obj.name
        + "') BEGIN\n"
    )
    end_guard = "END"  # separate for readability
    return f"{guard}CREATE TABLE {obj.name} (\n{col_section}{pk_line}\n);\n{end_guard}"


def _render_add_column(table: str, col: Column) -> str:
    null_sql = "NULL" if col.nullable else "NOT NULL"
    return f"ALTER TABLE {table} ADD {col.name} {col.type} {null_sql};"


def _render_alter_column(table: str, col: Column) -> str:
    null_sql = "NULL" if col.nullable else "NOT NULL"
    # Use ALTER COLUMN syntax (assumes no data loss constraints; caller handles sequencing)
    return f"ALTER TABLE {table} ALTER COLUMN {col.name} {col.type} {null_sql};"


def _render_drop_column(table: str, col: Column) -> str:
    return f"ALTER TABLE {table} DROP COLUMN {col.name};"


def _render_create_index(table: str, idx: Index) -> str:
    cols = ", ".join(idx.columns)
    unique = "UNIQUE " if idx.unique else ""
    return (
        "IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='"
        + idx.name
        + "' AND object_id = OBJECT_ID('"
        + table
        + "')) BEGIN\nCREATE "
        + unique
        + f"INDEX {idx.name} ON {table} ({cols});\nEND"
    )


def _render_add_foreign_key(table: str, fk_op: Operation) -> str:
    fk = fk_op.payload
    assert fk is not None
    ref_table = fk_op.extra["ref_table"] if fk_op.extra else "unknown_table"
    ref_col = fk_op.extra["ref_column"] if fk_op.extra else "id"
    constraint = f"fk_{table}_{fk.column}"
    # Guard: ensure not already present (by name)
    return (
        "IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='"
        + constraint
        + "') BEGIN\nALTER TABLE "
        + table
        + f" ADD CONSTRAINT {constraint} FOREIGN KEY ({fk.column}) REFERENCES {ref_table} ({ref_col});\nEND"
    )


def operations_to_sql(ops: list[Operation]) -> str:
    statements: list[str] = []
    for op in ops:
        if op.op == "CREATE_TABLE":
            statements.append(render_create_table(op))
        elif op.op == "ADD_COLUMN":
            statements.append(_render_add_column(op.table, op.payload))
        elif op.op == "ALTER_COLUMN":
            statements.append(_render_alter_column(op.table, op.payload))
        elif op.op == "DROP_COLUMN":
            statements.append(_render_drop_column(op.table, op.payload))
        elif op.op == "CREATE_INDEX":
            statements.append(_render_create_index(op.table, op.payload))
        elif op.op == "ADD_FOREIGN_KEY":
            statements.append(_render_add_foreign_key(op.table, op))
    return "\n\n".join(statements)

