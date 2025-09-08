"""Star-aware Natural Language admin parser (Phase 1).

Extends basic admin parsing with star-schema specific intents:
  - list star overview (tables with classification)
  - diagnose fact <table>
  - orphan check <fact_table>
  - null density <table>
  - top distribution <table>.<column>

Returns structured action objects consumed by the Streamlit NL Admin page.
"""
from __future__ import annotations
from typing import List, Dict, Any
import re

# Basic risk categories
LOW = "low"
MED = "medium"
HIGH = "high"

STAR_PATTERNS = [
    (r"^list star (schema )?overview$", "star_overview"),
    (r"^diagnose fact ([a-z0-9_.]+)$", "fact_health"),
    (r"^orphan check ([a-z0-9_.]+)$", "orphan_check"),
    (r"^null density ([a-z0-9_.]+)$", "null_density"),
    (r"^top distribution ([a-z0-9_.]+)\.([a-z0-9_]+)$", "top_distribution"),
]


class StarParser:
    def parse(self, text: str) -> List[Dict[str, Any]]:
        t = text.strip().lower()
        actions: List[Dict[str, Any]] = []
        if not t:
            return actions
        for pat, intent in STAR_PATTERNS:
            m = re.match(pat, t)
            if m:
                if intent == "star_overview":
                    actions.append({"intent": intent, "risk": LOW, "note": "List star schema classification"})
                elif intent == "fact_health":
                    fact = m.group(1)
                    actions.append({"intent": intent, "table": fact, "risk": LOW, "note": f"Fact health diagnostics for {fact}"})
                elif intent == "orphan_check":
                    fact = m.group(1)
                    actions.append({"intent": intent, "table": fact, "risk": LOW, "note": f"FK orphan check for {fact}"})
                elif intent == "null_density":
                    tbl = m.group(1)
                    actions.append({"intent": intent, "table": tbl, "risk": LOW, "note": f"Null density for {tbl}"})
                elif intent == "top_distribution":
                    tbl, col = m.group(1), m.group(2)
                    actions.append({"intent": intent, "table": tbl, "column": col, "risk": LOW, "note": f"Top value distribution for {tbl}.{col}"})
                return actions
        return actions  # no star intent matched
