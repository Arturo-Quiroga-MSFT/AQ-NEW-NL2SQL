from __future__ import annotations

"""Synthetic data generation utilities (Phase A: minimal features).

Supports:
  - Dimension row generation with fixed row counts or calendar ranges.
  - Fact row generation with rows_per_parent distribution.
  - Simple numeric distributions (uniform, normal, lognormal) and categorical weighted values.

Profile YAML structure (example):
```
entities:
  dim_company:
    rows: 50
    distributions:
      region:
        values:
          - value: north
            weight: 0.4
          - value: south
            weight: 0.6
  dim_date:
    strategy: calendar_range
    start: 2025-01-01
    end: 2025-01-10
  fact_loan_payments:
    rows_per_parent:
      parent: dim_company
      min: 5
      max: 12
    measures:
      amount:
        distribution: lognormal
        mean: 9.0
        sigma: 0.8
```
"""

import random
import math
from datetime import date, timedelta
from typing import Dict, Any, Iterable
from .schema_models import SchemaSpec, Dimension, Fact


def _daterange(start: date, end: date) -> Iterable[date]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def generate_dimension_rows(dim: Dimension, cfg: Dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # Calendar strategy
    if cfg.get("strategy") == "calendar_range":
        # Support values already parsed by PyYAML into date objects OR raw ISO strings
        raw_start = cfg.get("start")
        raw_end = cfg.get("end")
        if isinstance(raw_start, date):
            start = raw_start
        else:
            start = date.fromisoformat(str(raw_start))
        if isinstance(raw_end, date):
            end = raw_end
        else:
            end = date.fromisoformat(str(raw_end))
        for d in _daterange(start, end):
            row = {}
            for col in dim.columns:
                if col.name.endswith("date"):
                    row[col.name] = d.isoformat()
                elif col.name.endswith("_key"):
                    row[col.name] = None
                else:
                    row[col.name] = None
            # Surrogate key auto
            if dim.surrogate_key and dim.surrogate_key not in row:
                row[dim.surrogate_key] = int(d.strftime("%Y%m%d"))  # date_key style
            rows.append(row)
        return rows

    count = int(cfg.get("rows", 10))
    dists = cfg.get("distributions", {})
    for i in range(count):
        row = {}
        for col in dim.columns:
            if col.name == dim.natural_key:
                row[col.name] = f"{dim.name}_{i+1}"
            elif col.name.endswith("region") and "region" in dists:
                row[col.name] = _weighted_choice(dists["region"].get("values", []))
            elif col.name.endswith("industry"):
                row[col.name] = random.choice(["finance", "energy", "tech", "manufacturing"])
            else:
                row[col.name] = None
        if dim.surrogate_key and dim.surrogate_key not in row:
            row[dim.surrogate_key] = i + 1
        rows.append(row)
    return rows


def _weighted_choice(items: list[dict[str, Any]]) -> Any:
    if not items:
        return None
    total = sum(it.get("weight", 1) for it in items)
    r = random.uniform(0, total)
    acc = 0.0
    for it in items:
        acc += it.get("weight", 1)
        if acc >= r:
            return it.get("value")
    return items[-1].get("value")


def _sample_numeric(spec: dict[str, Any]) -> float:
    dist = spec.get("distribution", "uniform")
    if dist == "uniform":
        lo = float(spec.get("min", 0))
        hi = float(spec.get("max", 1))
        return random.uniform(lo, hi)
    if dist == "normal":
        mean = float(spec.get("mean", 0))
        std = float(spec.get("std", 1))
        return random.gauss(mean, std)
    if dist == "lognormal":
        mean = float(spec.get("mean", 0))
        sigma = float(spec.get("sigma", 1))
        return random.lognormvariate(mean, sigma)
    return 0.0


def generate_fact_rows(fact: Fact, cfg: Dict[str, Any], dim_data: Dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rpp = cfg.get("rows_per_parent")
    measures_cfg = cfg.get("measures", {})
    parent_dim_name = rpp.get("parent") if rpp else None
    parents = dim_data.get(parent_dim_name, [{}]) if parent_dim_name else [{}]
    min_rows = int(rpp.get("min", 1)) if rpp else 5
    max_rows = int(rpp.get("max", 5)) if rpp else 15
    # Optional date dimension link
    date_dim = None
    for k in dim_data.keys():
        if k.startswith("dim_date"):
            date_dim = dim_data[k]
            break
    # Build quick lookup of surrogate keys for parent and date dimensions
    def _pick_date_row() -> dict[str, Any] | None:
        return random.choice(date_dim) if date_dim else None

    for parent in parents:
        n = random.randint(min_rows, max_rows)
        for _ in range(n):
            row = {}
            date_row = _pick_date_row()
            for col in fact.columns:
                # Foreign key surrogate columns (company_key, date_key, etc.)
                if col.name.endswith("_key"):
                    if col.name.startswith("date_") and date_row:
                        # map date_key from date dimension surrogate (if present) else from calendar_date
                        candidate = date_row.get("date_key") or date_row.get("calendar_date")
                        row[col.name] = candidate
                    elif parent_dim_name and parent:
                        # Attempt to map company_key or generic *_key from parent
                        if col.name in parent:
                            row[col.name] = parent[col.name]
                        else:
                            # fallback: first *_key in parent
                            sk = [k for k in parent.keys() if k.endswith("_key")]
                            row[col.name] = parent.get(sk[0]) if sk else None
                    else:
                        row[col.name] = None
                elif col.name.endswith("date") and date_row:
                    row[col.name] = date_row.get("calendar_date")
                elif col.name.endswith("id") and parent_dim_name:
                    # derive from parent natural key if present
                    nk = parent.get("company_id")
                    row[col.name] = f"{nk}_txn_{random.randint(1,9999)}" if nk else f"id_{random.randint(1,9999)}"
                else:
                    row[col.name] = None
            for m in fact.measures:
                m_cfg = measures_cfg.get(m.name, {})
                val = _sample_numeric(m_cfg)
                # round decimals that look like DECIMAL(18,2)
                row[m.name] = round(val, 2)
            rows.append(row)
    return rows


def generate_all(spec: SchemaSpec, profile: Dict[str, Any]) -> Dict[str, list[dict[str, Any]]]:
    result: Dict[str, list[dict[str, Any]]] = {}
    ent_cfg = profile.get("entities", {})
    # Dimensions first
    for dim in spec.entities.dimensions:
        cfg = ent_cfg.get(dim.name, {})
        result[dim.name] = generate_dimension_rows(dim, cfg)
    # Facts
    for fact in spec.entities.facts:
        cfg = ent_cfg.get(fact.name, {})
        result[fact.name] = generate_fact_rows(fact, cfg, result)
    return result
