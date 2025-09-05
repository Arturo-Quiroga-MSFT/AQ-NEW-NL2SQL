from __future__ import annotations
from ..state import GraphState
from ..llm import azure_chat_completions, accumulate_usage
from ..tools.env_validation import validate_azure_openai_env
from ..tools.sql_env_validation import validate_sql_env
import os
import json
import re

# Environment toggle: if set to "1" enables structured JSON attempt, otherwise simple plain extraction.
STRUCTURED_ON = os.getenv("ENABLE_STRUCTURED_INTENT", "0") == "1"

INTENT_PROMPT_TEXT = (
        """
You are an expert assistant that converts a user's natural language question about a financial loans database into a structured intent specification.

Return a SINGLE compact JSON object (no markdown, no commentary) with the following keys:
    intent: short description of the analytical goal
    measures: list of derived or raw metrics needed
    dimensions: list of grouping columns
    filters: list of semantic filter clauses (empty list if none)
    expected_joins: list of important table relationships implied
    aggregation: textual summary of required aggregation(s)
    complexity: one of [easy, medium, hard] (infer from wording; phrases like 'for each', 'top', 'trend', 'ratio', multiple conditions => higher complexity)
    question_type: one of [lookup, aggregation, ranking, ratio, time_series, correlation, segmentation]

Rules:
- Do NOT invent tables that don't exist.
- If the question implies a ratio involving collateral, note collateral aggregation by LoanId.
- If collateral values are needed, mention aggregation of Collateral.ValueAmount.
- If nothing is extractable, still return a JSON object with empty lists and an 'intent' paraphrase.

Example:
Input: For each region, show the average loan-to-value ratio.
Output:
{"intent":"Compute average loan-to-value ratio by region","measures":["loan_to_value_ratio = Loan.PrincipalAmount / SUM(Collateral.ValueAmount)"],"dimensions":["RegionName"],"filters":[],"expected_joins":["Loan -> Company -> Country -> Region","Collateral aggregated by LoanId"],"aggregation":"AVG(loan_to_value_ratio) GROUP BY RegionName","complexity":"hard","question_type":"ratio"}

Now extract intent JSON for:
{input}
"""
)

PLAIN_INTENT_PROMPT = (
    """
You are an expert in translating natural language questions into a concise description of intent and involved entities.
User Question:
{input}

Return 1-3 sentences summarizing:
- Core analytical goal
- Key entities / tables implied
- Any aggregation or filtering hints
Do NOT return JSON. Just natural language.
"""
)


def run(state: GraphState) -> GraphState:
    """Intent extraction with optional structured JSON.

    Default behavior (STRUCTURED_ON disabled): single prompt returning natural language summary (always usable),
    stored as a simple dict with just the 'intent' text for downstream display.
    When STRUCTURED_ON=1: attempt structured JSON; if that fails, fall back to plain summary without raising errors.
    """
    try:
        # Validate Azure OpenAI environment first
        env_ok, env_msgs = validate_azure_openai_env()
        state.azure_env_valid = env_ok
        state.azure_env_messages = env_msgs
        if not env_ok:
            state.intent_entities = {"intent": state.user_query, "error": "Azure OpenAI environment invalid", "env": env_msgs}
            # Do not attempt LLM calls; return early so UI can surface cause.
            return state

        # Validate SQL environment (does not block intent, but record status)
        sql_ok, sql_msgs = validate_sql_env()
        state.sql_env_valid = sql_ok
        state.sql_env_messages = sql_msgs

        # Always produce at least a plain summary first (guarantees non-null intent)
        plain_prompt = PLAIN_INTENT_PROMPT.format(input=state.user_query)
        messages_plain = [{"role": "user", "content": plain_prompt.strip()}]
        plain_content, usage_plain = azure_chat_completions(
            messages_plain,
            max_completion_tokens=state.intent_max_tokens if state.intent_max_tokens else None,
        )
        updated = accumulate_usage(usage_plain, state.token_usage.model_dump())
        state.token_usage.prompt = updated.get("prompt", 0)
        state.token_usage.completion = updated.get("completion", 0)
        state.token_usage.total = updated.get("total", 0)
        base_text = plain_content.strip() or state.user_query.strip()
        state.intent_raw_response = base_text
        state.intent_parse_attempts = 1
        # Base representation
        state.intent_entities = {"intent": base_text}

        if not STRUCTURED_ON:
            return state

        # Try structured JSON enrichment
        struct_prompt = INTENT_PROMPT_TEXT.format(input=state.user_query)
        messages_struct = [{"role": "user", "content": struct_prompt.strip()}]
        struct_content, usage_struct = azure_chat_completions(
            messages_struct,
            max_completion_tokens=state.intent_max_tokens if state.intent_max_tokens else None,
        )
        updated2 = accumulate_usage(usage_struct, state.token_usage.model_dump())
        state.token_usage.prompt = updated2.get("prompt", 0)
        state.token_usage.completion = updated2.get("completion", 0)
        state.token_usage.total = updated2.get("total", 0)
        raw_struct = struct_content.strip()
        json_candidate = raw_struct
        if not json_candidate.startswith('{'):
            lb = json_candidate.find('{'); rb = json_candidate.rfind('}')
            if lb != -1 and rb != -1 and rb > lb:
                json_candidate = json_candidate[lb:rb+1]
        try:
            parsed = json.loads(json_candidate)
            if isinstance(parsed, dict) and 'intent' in parsed:
                state.intent_entities = parsed
                state.intent_raw_response = raw_struct
                state.intent_parse_attempts = 2
        except Exception as je:
            state.add_error(f"Structured intent parse failed: {je}")
            # Keep plain summary (do not overwrite)
    except Exception as e:
        state.intent_entities = {"intent": state.user_query, "error": str(e)}
        state.add_error(f"Intent node failed: {e}")
    return state
