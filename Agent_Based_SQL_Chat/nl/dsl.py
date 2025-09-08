from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Intermediate neutral representations

@dataclass
class NLAction:
    intent: str
    risk: str = "low"
    table: Optional[str] = None
    tables: List[str] = field(default_factory=list)
    columns: List[Dict[str, Any]] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""
    confidence: float = 1.0

@dataclass
class Clarification:
    raw: str
    candidates: List[str]
    message: str

@dataclass
class Unknown:
    raw: str
    reason: str = "no_intent_detected"
    confidence: float = 0.0

INTENT_RISK = {
    "drop_table": "high",
    "drop_column": "medium",
    "create_table": "medium",
    "add_column": "medium",
    "create_index": "medium",
    # Diagnostics & reads remain low
}

def assign_risk(intent: str) -> str:
    return INTENT_RISK.get(intent, "low")
