from __future__ import annotations
from .rules import rule_classify
from .dsl import NLAction, Unknown, Clarification
from .renderer import render_sql

# Phase 1: rule-only classifier orchestrator (semantic & LLM stubs for future)

def classify(raw: str):
    action = rule_classify(raw)
    return action


def to_sql(action: NLAction | Unknown | Clarification):
    if isinstance(action, NLAction):
        return render_sql(action)
    return None
