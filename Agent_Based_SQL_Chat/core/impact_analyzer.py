from __future__ import annotations

"""Impact / risk analysis utilities for planned migration operations.

Classifies each Operation (ALTER_COLUMN, DROP_COLUMN, ADD_COLUMN) with a heuristic
risk level to help users review potentially destructive changes before applying.

Risk Levels:
  - low: additive changes, widening types (e.g., VARCHAR(40)->VARCHAR(60)), adding nullable column
  - medium: NULLABLE to NOT NULL (unknown data), type family change within similar width (e.g., INT->BIGINT)
  - high: narrowing length/precision/scale, dropping a column, changing numeric scale/precision to smaller
"""

from typing import List, Dict, Any
import re
from .migration_planner import Operation


_DEC_RE = re.compile(r"DECIMAL\((\d+),(\d+)\)")
_VARCHAR_RE = re.compile(r"VARCHAR\((\d+)\)")


def _parse_decimal(t: str) -> tuple[int,int] | None:
    m = _DEC_RE.fullmatch(t.upper())
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _parse_varchar(t: str) -> int | None:
    m = _VARCHAR_RE.fullmatch(t.upper())
    if m:
        return int(m.group(1))
    return None


def analyze_impact(ops: List[Operation]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for op in ops:
        if op.op not in {"ALTER_COLUMN", "DROP_COLUMN", "ADD_COLUMN"}:
            continue
        entry: Dict[str, Any] = {"op": op.op, "table": op.table}
        col = getattr(op.payload, "name", None)
        if col:
            entry["column"] = col
        risk = "low"
        reasons: list[str] = []
        if op.op == "DROP_COLUMN":
            risk = "high"
            reasons.append("column removed")
        elif op.op == "ADD_COLUMN":
            # Treat adding NOT NULL as medium (data backfill required); nullable low
            nullable = getattr(op.payload, "nullable", True)
            if nullable:
                risk = "low"
                reasons.append("new nullable column")
            else:
                risk = "medium"
                reasons.append("new NOT NULL column (requires backfill)")
        elif op.op == "ALTER_COLUMN":
            prev = (op.extra or {}).get("previous") if isinstance(op.extra, dict) else None
            new_col = op.payload
            if prev is None or new_col is None:
                risk = "medium"
                reasons.append("missing previous column metadata")
            else:
                prev_type = prev.type.upper()
                new_type = new_col.type.upper()
                # Nullability tightening
                if prev.nullable and not new_col.nullable:
                    risk = "medium"
                    reasons.append("NULLABLE -> NOT NULL")
                # VARCHAR changes
                prev_v = _parse_varchar(prev_type)
                new_v = _parse_varchar(new_type)
                if prev_v and new_v:
                    if new_v < prev_v:
                        risk = "high"; reasons.append(f"VARCHAR length narrowing {prev_v}->{new_v}")
                    elif new_v > prev_v:
                        reasons.append(f"VARCHAR length widening {prev_v}->{new_v}")
                # DECIMAL precision/scale changes
                prev_d = _parse_decimal(prev_type)
                new_d = _parse_decimal(new_type)
                if prev_d and new_d:
                    p1,s1 = prev_d; p2,s2 = new_d
                    if p2 < p1 or s2 < s1:
                        risk = "high"; reasons.append(f"DECIMAL precision/scale reduction {prev_d}->{new_d}")
                    elif p2 > p1 or s2 > s1:
                        reasons.append(f"DECIMAL precision/scale increase {prev_d}->{new_d}")
                # Type family changes
                family_prev = _family(prev_type)
                family_new = _family(new_type)
                if family_prev != family_new:
                    # Changing family can be risky if contracting numeric to string or vice versa
                    reasons.append(f"type family change {family_prev}->{family_new}")
                    if risk != "high":
                        risk = "medium"
        entry["risk"] = risk
        entry["reasons"] = reasons
        results.append(entry)
    return results


def _family(t: str) -> str:
    if t.startswith("VARCHAR"): return "string"
    if t.startswith("DECIMAL") or t in {"INT","BIGINT","SMALLINT","TINYINT","FLOAT","REAL"}: return "numeric"
    if t in {"DATE","DATETIME","DATETIME2"}: return "date"
    return "other"
