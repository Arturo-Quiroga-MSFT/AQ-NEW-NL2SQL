from __future__ import annotations

"""Design agent – integrates Azure OpenAI for NL → YAML star schema generation.

Falls back to heuristic scaffold if LLM is unavailable or output invalid.
"""

from typing import Optional
import os
import re
import yaml
from DB_Assistant.core.schema_models import SchemaSpec, Entities, Dimension, Fact, Column

try:  # Reuse existing azure_chat_completions helper if available
    from agents_nl2sql.llm import azure_chat_completions  # type: ignore
except Exception:  # noqa: BLE001
    azure_chat_completions = None  # type: ignore


_YAML_SPEC_INSTRUCTIONS = (
    "You output ONLY valid YAML for a star schema specification. Keys: version (int), warehouse (optional), "
    "entities: dimensions: list, facts: list. Dimension fields: name, surrogate_key, natural_key(optional), columns(list of name,type,nullable). "
    "Fact fields: name, grain, columns(list), measures(list of columns), foreign_keys(list of {column,references}). "
    "Lower snake_case table & column names. Types chosen from whitelist: INT, BIGINT, SMALLINT, TINYINT, DECIMAL(18,2), DECIMAL(19,4), DATE, DATETIME2, VARCHAR(20|40|50|60|100|200), BIT, FLOAT, REAL. "
    "Do NOT include explanatory prose or code fences."
)


def _heuristic_fallback(prompt: str) -> SchemaSpec:
    lp = prompt.lower()
    dims = []
    if "company" in lp:
        dims.append(
            Dimension(
                name="dim_company",
                surrogate_key="company_key",
                natural_key="company_id",
                columns=[
                    Column(name="company_id", type="VARCHAR(50)", nullable=False),
                    Column(name="region", type="VARCHAR(40)", nullable=False),
                    Column(name="industry", type="VARCHAR(60)"),
                ],
            )
        )
    dims.append(
        Dimension(
            name="dim_date",
            surrogate_key="date_key",
            columns=[
                Column(name="date_key", type="INT", nullable=False),
                Column(name="calendar_date", type="DATE", nullable=False),
            ],
        )
    )
    facts = [
        Fact(
            name="fact_generic",
            grain="id",
            columns=[Column(name="id", type="VARCHAR(50)", nullable=False)],
            measures=[Column(name="amount", type="DECIMAL(18,2)", nullable=False)],
        )
    ]
    return SchemaSpec(version=1, warehouse=None, entities=Entities(dimensions=dims, facts=facts))


def _extract_yaml(text: str) -> Optional[str]:
    # Remove code fences if present
    fenced = re.findall(r"```[a-zA-Z0-9_-]*\n(.*?)```", text, flags=re.DOTALL)
    if fenced:
        return fenced[0].strip()
    return text.strip()


def draft_schema_from_prompt(prompt: str, use_llm: bool = True, max_completion_tokens: int = 1500) -> SchemaSpec:
    if not use_llm or azure_chat_completions is None:
        return _heuristic_fallback(prompt)
    # Check env quickly
    if not (os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")):
        return _heuristic_fallback(prompt)
    messages = [
        {"role": "system", "content": _YAML_SPEC_INSTRUCTIONS},
        {"role": "user", "content": f"Prompt: {prompt}"},
    ]
    try:
        content, _usage = azure_chat_completions(messages, max_completion_tokens=max_completion_tokens)
        yaml_text = _extract_yaml(content)
        data = yaml.safe_load(yaml_text)
        return SchemaSpec.parse_obj(data)
    except Exception:
        return _heuristic_fallback(prompt)

