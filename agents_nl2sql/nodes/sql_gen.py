from __future__ import annotations
from ..state import GraphState
from ..llm import azure_chat_completions, accumulate_usage

SQL_PROMPT_TEXT = (
    """
    You are an expert in SQL and Azure SQL Database. Given the following database schema and the intent/entities, generate a valid T-SQL query for querying the database.

    IMPORTANT:
    - Do NOT use USE statements (USE [database] is not supported in Azure SQL Database)
    - Generate only the SELECT query without USE or GO statements
    - Return only executable T-SQL code without markdown formatting
    - The database connection is already established to the correct database
    - Avoid using aggregate functions (SUM, COUNT, AVG, MIN, MAX) directly on subqueries or derived tables in the SELECT clause, as this is not supported in SQL Server. Instead, use CTEs or JOINs for such aggregations.
    - If you need to aggregate over a subquery, use a CTE (WITH ...) or join the subquery result to the main query.

    Schema:
    {schema}
    Intent and Entities:
    {intent_entities}

    Generate a T-SQL query that can be executed directly:
    """
)


def run(state: GraphState) -> GraphState:
    try:
        prompt = SQL_PROMPT_TEXT.format(schema=state.schema_context, intent_entities=state.intent_entities)
        messages = [{"role": "user", "content": prompt.strip()}]
        content, usage = azure_chat_completions(messages, max_completion_tokens=2048)
        # track usage
        updated = accumulate_usage(usage, state.token_usage.model_dump())
        state.token_usage.prompt = updated.get("prompt", 0)
        state.token_usage.completion = updated.get("completion", 0)
        state.token_usage.total = updated.get("total", 0)
        state.sql_raw = content
    except Exception as e:
        state.add_error(f"SQL generation failed: {e}")
    return state
