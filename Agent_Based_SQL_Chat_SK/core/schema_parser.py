from __future__ import annotations

import yaml
from pathlib import Path
from .schema_models import SchemaSpec


def load_schema(path: str | Path) -> SchemaSpec:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return SchemaSpec.parse_obj(data)


def dump_schema(spec: SchemaSpec, path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(spec.dict(by_alias=True), f, sort_keys=False)
