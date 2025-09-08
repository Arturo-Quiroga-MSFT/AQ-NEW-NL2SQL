from __future__ import annotations

from .schema_models import SchemaSpec, Dimension, Fact


def validate_spec(spec: SchemaSpec) -> list[str]:
    """Return list of validation error strings (empty if OK).

    Current semantic checks:
      - Duplicate table names
      - Dimension surrogate_key must be defined
      - Fact grain columns must exist in fact columns or measures
      - Foreign key references syntactic format table(column)
      - Foreign key referenced table exists in spec
      - Index columns exist in table
    """
    errors: list[str] = []
    tables = spec.table_dict()
    seen_tables = set()
    for name in tables:
        if name in seen_tables:
            errors.append(f"Duplicate table name: {name}")
        seen_tables.add(name)

    # Build column maps
    col_map: dict[str, set[str]] = {}
    for tname, obj in tables.items():
        cols: set[str] = set()
        if isinstance(obj, Dimension):
            cols.update(c.name for c in obj.columns)
        elif isinstance(obj, Fact):
            cols.update(c.name for c in obj.columns)
            cols.update(m.name for m in obj.measures)
        col_map[tname] = cols

    # Dimension checks
    for tname, obj in tables.items():
        if isinstance(obj, Dimension):
            if not obj.surrogate_key:
                errors.append(f"Dimension {tname} missing surrogate_key")
            elif obj.surrogate_key not in col_map[tname]:
                errors.append(f"Dimension {tname} surrogate_key '{obj.surrogate_key}' not a defined column")

    # Fact grain check
    for tname, obj in tables.items():
        if isinstance(obj, Fact) and obj.grain:
            for gcol in [g.strip() for g in obj.grain.split(',') if g.strip()]:
                if gcol not in col_map[tname]:
                    errors.append(f"Fact {tname} grain column '{gcol}' not present in columns/measures")

    # Foreign key checks
    for tname, obj in tables.items():
        if isinstance(obj, Fact):
            for fk in obj.foreign_keys:
                ref = fk.references
                if '(' not in ref or not ref.endswith(')'):
                    errors.append(f"Foreign key reference format invalid in {tname}: '{ref}'")
                    continue
                ref_table, ref_col = ref[:-1].split('(')
                if ref_table not in tables:
                    errors.append(f"Foreign key references unknown table '{ref_table}' in {tname}")
                else:
                    if ref_col not in col_map.get(ref_table, set()):
                        errors.append(f"Foreign key references unknown column '{ref_col}' on table '{ref_table}' in {tname}")

    # Index checks
    for tname, obj in tables.items():
        indices = []
        if isinstance(obj, Dimension):
            indices = obj.indexes
        elif isinstance(obj, Fact):
            indices = obj.indexes
        for idx in indices:
            for col in idx.columns:
                if col not in col_map[tname]:
                    errors.append(f"Index {idx.name} on {tname} references unknown column '{col}'")
    return errors

