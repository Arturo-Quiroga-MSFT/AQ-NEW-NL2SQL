from __future__ import annotations
import re, yaml
from pathlib import Path
from typing import Optional, Dict, Any
from .dsl import NLAction, Unknown, assign_risk
from .normalize import normalize

_CATALOG_PATH = Path(__file__).with_name('intents.yaml')
with _CATALOG_PATH.open('r', encoding='utf-8') as f:
    INTENTS = yaml.safe_load(f)

# Precompile regex
for entry in INTENTS:
    compiled = []
    for pat in entry.get('patterns', []) or []:
        compiled.append(re.compile(pat))
    entry['_compiled_patterns'] = compiled
    if entry.get('slot_pattern'):
        entry['_compiled_slot'] = re.compile(entry['slot_pattern'])


def rule_classify(raw: str) -> NLAction | Unknown:
    norm = normalize(raw)
    # First: direct patterns
    for ent in INTENTS:
        for cp in ent.get('_compiled_patterns', []):
            if cp.match(norm):
                intent = ent['id']
                return NLAction(intent=intent, raw=raw, risk=assign_risk(intent), confidence=0.95)
    # Second: slot patterns
    for ent in INTENTS:
        slot_re = ent.get('_compiled_slot')
        if not slot_re:
            continue
        m = slot_re.match(norm)
        if m:
            intent = ent['id']
            slots: Dict[str, Any] = m.groupdict()
            action = NLAction(intent=intent, raw=raw, risk=assign_risk(intent), confidence=0.90)
            # Map common slots
            if 'table' in slots:
                action.table = slots['table']
            if 'cols' in slots:
                action.options['raw_cols'] = slots['cols']
            if 'column' in slots:
                action.options['column'] = slots['column']
            if 'ctype' in slots:
                action.options['ctype'] = slots['ctype']
            return action
    return Unknown(raw=raw)
