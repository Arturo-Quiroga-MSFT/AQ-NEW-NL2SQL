from __future__ import annotations
from ..state import GraphState
from ..llm import azure_chat_completions, accumulate_usage


def build_sql_prompt(schema: str, intent_entities: str | None, category: str, user_query: str) -> str:
    intent_text = intent_entities.strip() if isinstance(intent_entities, str) else ""
    if not intent_text:
        intent_text = "<none provided>"
    base = [
        "You are an expert in T-SQL for Azure SQL. Produce ONE executable SELECT statement only (no comments, no markdown).",
        "Rules:",
        "- No USE or GO statements.",
        "- Prefer clarity with CTEs for multi-step logic.",
        "- If computing ratios requiring collateral: aggregate Collateral.ValueAmount by LoanId first.",
        "- If intent JSON missing, infer from the user question directly.",
    ]
    if category.lower() == "hard":
        base.extend([
            "HARD QUESTION DIRECTIVES:",
            "- Use star schema: JOIN fact tables (fact.FACT_LOAN_ORIGINATION, fact.FACT_LOAN_APPLICATION, fact.FACT_PAYMENT_TRANSACTION) with dimension tables (dim.DimCustomer, dim.DimLoanProduct, dim.DimIndustry, dim.DimDate).",
            "- Use CTEs for derived aggregations (e.g., loan totals, payment sums, ratio calculations).",
            "- Demonstrate advanced SQL patterns (star schema joins, conditional handling, NULL safety).",
        ])
    # Few-shot examples only for hard to steer complexity
    if category.lower() == "hard":
        base.append("EXAMPLE PATTERN (DO NOT REPEAT LITERALLY)\nWITH CollateralAgg AS (\n  SELECT LoanId, SUM(ValueAmount) AS TotalCollateralValue\n  FROM dbo.Collateral\n  GROUP BY LoanId\n), LoanRegion AS (\n  SELECT l.LoanId, l.PrincipalAmount, r.RegionName, ca.TotalCollateralValue,\n         CASE WHEN ca.TotalCollateralValue > 0 THEN CAST(l.PrincipalAmount AS decimal(38,6)) / ca.TotalCollateralValue END AS LoanToValueRatio\n  FROM dbo.Loan l\n  JOIN dbo.Company c ON l.CompanyId = c.CompanyId\n  JOIN ref.Country ct ON c.CountryCode = ct.CountryCode\n  JOIN ref.Region r ON ct.RegionId = r.RegionId\n  LEFT JOIN CollateralAgg ca ON l.LoanId = ca.LoanId\n)\nSELECT RegionName, AVG(LoanToValueRatio) AS AvgLoanToValueRatio\nFROM LoanRegion\nWHERE LoanToValueRatio IS NOT NULL\nGROUP BY RegionName\nORDER BY AvgLoanToValueRatio DESC")
    prompt_sections = [
        "\n".join(base),
        "Schema (truncated / advisory):\n" + schema[:4000],
        f"User Question:\n{user_query}",
        f"Intent JSON or Text:\n{intent_text}",
        "Output: ONLY the final T-SQL SELECT (with optional preceding CTEs).",
    ]
    return "\n\n".join(prompt_sections)


def run(state: GraphState) -> GraphState:
    try:
        prompt = build_sql_prompt(
            state.schema_context,
            state.intent_entities,
            getattr(state, "question_category", "Easy"),
            state.user_query,
        )
        messages = [{"role": "user", "content": prompt.strip()}]
        content, usage = azure_chat_completions(
            messages,
            max_completion_tokens=state.sql_max_tokens if state.sql_max_tokens else None,
        )
        # track usage
        updated = accumulate_usage(usage, state.token_usage.model_dump())
        state.token_usage.prompt = updated.get("prompt", 0)
        state.token_usage.completion = updated.get("completion", 0)
        state.token_usage.total = updated.get("total", 0)
        state.sql_raw = content
    except Exception as e:
        state.add_error(f"SQL generation failed: {e}")
    return state
