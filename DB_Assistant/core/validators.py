from __future__ import annotations

from .schema_models import SchemaSpec


def validate_spec(spec: SchemaSpec) -> list[str]:
    """Return list of validation error strings (empty if OK)."""
    errors: list[str] = []
    seen_tables = set()
    for name, _obj in spec.table_dict().items():
        if name in seen_tables:
            errors.append(f"Duplicate table name: {name}")
        seen_tables.add(name)
    # Additional semantic checks can be added here
    return errors
