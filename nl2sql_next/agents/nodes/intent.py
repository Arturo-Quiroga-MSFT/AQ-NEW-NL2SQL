"""Intent extraction node — translates user question into a structured intent summary."""
from __future__ import annotations

from ..llm import azure_chat_completions, accumulate_usage
from ..state import GraphState
from ..tools.env_validation import validate_azure_openai_env, validate_sql_env

INTENT_PROMPT = """
You are an expert analyst for an E-Commerce / Retail data warehouse (RetailDW).
The database uses a star schema with:
  Dimension tables: dim.DimDate, dim.DimCustomer, dim.DimProduct, dim.DimStore,
                    dim.DimPromotion, dim.DimShippingMethod, dim.DimPaymentMethod
  Fact tables:      fact.FactOrders, fact.FactReturns, fact.FactInventory,
                    fact.FactWebTraffic, fact.FactCustomerReview
  Reference:        ref.RefReturnReason
  Views:            dbo.vw_OrderSummary, dbo.vw_MonthlySales,
                    dbo.vw_ProductPerformance, dbo.vw_CustomerLifetimeValue

Given the user question below, summarize in 2-4 sentences:
- The core analytical goal
- Key tables / entities involved
- Aggregation, filtering, or ranking hints

User Question:
{input}
"""


def run(state: GraphState) -> GraphState:
    try:
        env_ok, env_msgs = validate_azure_openai_env()
        state.azure_env_valid = env_ok
        state.azure_env_messages = env_msgs
        if not env_ok:
            state.intent_entities = {
                "intent": state.user_query,
                "error": "Azure OpenAI env invalid",
            }
            return state

        sql_ok, sql_msgs = validate_sql_env()
        state.sql_env_valid = sql_ok
        state.sql_env_messages = sql_msgs

        prompt = INTENT_PROMPT.format(input=state.user_query)
        content, usage = azure_chat_completions(
            [{"role": "user", "content": prompt.strip()}],
            max_completion_tokens=state.intent_max_tokens,
        )
        updated = accumulate_usage(usage, state.token_usage.model_dump())
        state.token_usage.prompt = updated.get("prompt", 0)
        state.token_usage.completion = updated.get("completion", 0)
        state.token_usage.total = updated.get("total", 0)

        text = content.strip() or state.user_query
        state.intent_raw_response = text
        state.intent_entities = {"intent": text}
    except Exception as e:
        state.intent_entities = {"intent": state.user_query, "error": str(e)}
        state.add_error(f"Intent node failed: {e}")
    return state
