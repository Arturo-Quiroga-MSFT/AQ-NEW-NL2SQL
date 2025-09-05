# Recommended SQL Views for NL2SQL Acceleration

This document proposes a set of helper views to simplify natural-language-to-SQL generation, reduce model reasoning complexity, and improve runtime performance for common analytical questions over the Contoso-FI demo schema.

---
## Goals

1. **Reduce join & GROUP BY complexity** in model-generated SQL.
2. **Standardize repeated calculations** (remaining balance, loan-to-value, rankings, currency diversity).
3. **Provide semantically obvious surfaces** whose names closely match user phrasing.
4. **Lower token footprint** in the schema context by offering curated “summary” surfaces.
5. **Enable safe optimization later** (indexed views or materialized snapshots) without changing the NL pipeline.

---
## Design Principles

| Principle | Rationale |
|-----------|-----------|
| Clear, descriptive view names | Improves LLM selection & reduces prompt verbosity |
| Pre-compute frequently repeated aggregates | Avoid repeated reasoning & execution cost |
| Include both business and key identifiers | Supports further joins if needed |
| Avoid ambiguous column names | Minimizes hallucination risk |
| Separate summary vs event vs ranking views | Keeps surfaces focused & small |
| Keep deterministic logic in views | Candidate for indexed view optimization |
| Minimize volatile expressions (`GETDATE()`) in indexed candidates | Required for schemabinding consistency |

---
## Proposed View Catalog (Prioritized)

| View | Type | Purpose | Key Benefit |
|------|------|---------|-------------|
| `vw_LoanRemainingBalance` | Fact Enhancement | Remaining principal, collateral value, LTV | Eliminates payment aggregation repetition |
| `vw_CompanyLoanSummary` | Company Aggregate | Loan counts & principal sums per company/region | Simplifies company exposure queries |
| `vw_UpcomingCovenantTests` | Event Window | Covenants due next 30 days | Encapsulates date filter logic |
| `vw_LoanCollateralSummary` | Fact Rollup | Per-loan collateral totals / category splits | Cuts join+sum boilerplate |
| `vw_RegionCompanyPrincipalRank` | Ranking | Region-level ranked principal totals | Replaces window logic in generated SQL |
| `vw_CompanyCurrencyDiversity` | Classification | Flags multi-currency companies | Avoid DISTINCT reasoning |
| (Optional) `vw_LoanPortfolioLean` | Curated Subset | Slim subset of highly asked columns | Reduces schema context size |
| (Future) `vw_CompanyRiskSnapshot` | Snapshot | Latest risk metrics row per company | Single-row dimension for risk queries |
| (Future) `vw_PaymentsDueSoon` | Scheduling | Next payment + days until due | Answer scheduling queries directly |

Start with the **first 3–6** for maximal immediate impact.

---
## Core DDL Templates
> Adjust table & column names to your actual schema. Provided types and names are illustrative.

### 1. Loan Remaining Balance
```sql
CREATE VIEW dbo.vw_LoanRemainingBalance AS
SELECT
    L.LoanId,
    L.CompanyId,
    C.CompanyName,
    L.OriginationDate,
    L.MaturityDate,
    L.PrincipalAmount,
    ISNULL(SUM(P.AmountPaid), 0) AS TotalPaid,
    L.PrincipalAmount - ISNULL(SUM(P.AmountPaid), 0) AS RemainingPrincipal,
    Coll.TotalCollateralValue,
    CASE 
        WHEN Coll.TotalCollateralValue > 0 
             THEN CAST((L.PrincipalAmount - ISNULL(SUM(P.AmountPaid), 0)) AS decimal(18,2)) / Coll.TotalCollateralValue
        ELSE NULL
    END AS LoanToValueRatio
FROM dbo.Loan L
LEFT JOIN dbo.Company C ON L.CompanyId = C.CompanyId
LEFT JOIN dbo.PaymentSchedule P ON L.LoanId = P.LoanId AND P.Status = 'POSTED'
LEFT JOIN (
    SELECT LoanId, SUM(EstimatedValue) AS TotalCollateralValue
    FROM dbo.Collateral
    GROUP BY LoanId
) Coll ON L.LoanId = Coll.LoanId
GROUP BY L.LoanId, L.CompanyId, C.CompanyName, L.OriginationDate, L.MaturityDate, 
         L.PrincipalAmount, Coll.TotalCollateralValue;
```

### 2. Company Loan Summary
```sql
CREATE VIEW dbo.vw_CompanyLoanSummary AS
SELECT
    C.CompanyId,
    C.CompanyName,
    R.RegionName,
    COUNT(DISTINCT L.LoanId) AS LoanCount,
    SUM(L.PrincipalAmount) AS TotalPrincipal,
    SUM(RB.RemainingPrincipal) AS TotalRemainingPrincipal,
    AVG(RB.LoanToValueRatio) AS AvgLTV,
    MAX(L.OriginationDate) AS MostRecentOrigination
FROM dbo.Company C
LEFT JOIN dbo.Region R ON C.RegionId = R.RegionId
LEFT JOIN dbo.Loan L ON C.CompanyId = L.CompanyId
LEFT JOIN dbo.vw_LoanRemainingBalance RB ON L.LoanId = RB.LoanId
GROUP BY C.CompanyId, C.CompanyName, R.RegionName;
```

### 3. Upcoming Covenant Tests
```sql
CREATE VIEW dbo.vw_UpcomingCovenantTests AS
SELECT
    Cov.CovenantId,
    Cov.LoanId,
    Cov.TestType,
    Cov.NextTestDate,
    DATEDIFF(DAY, GETDATE(), Cov.NextTestDate) AS DaysUntilTest
FROM dbo.Covenant Cov
WHERE Cov.NextTestDate BETWEEN GETDATE() AND DATEADD(DAY, 30, GETDATE());
```
> NOTE: For indexed view eligibility, remove `GETDATE()` and materialize with a scheduler process instead.

### 4. Loan Collateral Summary
```sql
CREATE VIEW dbo.vw_LoanCollateralSummary AS
SELECT
    L.LoanId,
    COUNT(CO.CollateralId) AS CollateralItemCount,
    SUM(CO.EstimatedValue) AS CollateralTotalValue,
    SUM(CASE WHEN CO.CollateralType = 'RealEstate' THEN CO.EstimatedValue ELSE 0 END) AS RealEstateValue,
    SUM(CASE WHEN CO.CollateralType = 'Equipment' THEN CO.EstimatedValue ELSE 0 END) AS EquipmentValue
FROM dbo.Loan L
LEFT JOIN dbo.Collateral CO ON L.LoanId = CO.LoanId
GROUP BY L.LoanId;
```

### 5. Region Company Principal Rank
```sql
CREATE VIEW dbo.vw_RegionCompanyPrincipalRank AS
WITH CompanyTotals AS (
    SELECT
        C.CompanyId,
        C.CompanyName,
        R.RegionName,
        SUM(L.PrincipalAmount) AS TotalPrincipal
    FROM dbo.Company C
    LEFT JOIN dbo.Region R ON C.RegionId = R.RegionId
    LEFT JOIN dbo.Loan L ON C.CompanyId = L.CompanyId
    GROUP BY C.CompanyId, C.CompanyName, R.RegionName
)
SELECT *,
       RANK() OVER (PARTITION BY RegionName ORDER BY TotalPrincipal DESC) AS PrincipalRank
FROM CompanyTotals;
```

### 6. Company Currency Diversity
```sql
CREATE VIEW dbo.vw_CompanyCurrencyDiversity AS
WITH DistinctCurrencies AS (
    SELECT L.CompanyId, L.CurrencyCode
    FROM dbo.Loan L
    GROUP BY L.CompanyId, L.CurrencyCode
)
SELECT
    C.CompanyId,
    C.CompanyName,
    COUNT(DISTINCT DC.CurrencyCode) AS DistinctCurrencyCount,
    CASE WHEN COUNT(DISTINCT DC.CurrencyCode) > 1 THEN 1 ELSE 0 END AS IsMultiCurrency
FROM dbo.Company C
LEFT JOIN DistinctCurrencies DC ON C.CompanyId = DC.CompanyId
GROUP BY C.CompanyId, C.CompanyName;
```

---
## Query Simplification Examples

| NL Question | Old Pattern | With View |
|-------------|-------------|----------|
| Top companies by principal | Multi-table join + GROUP BY | `SELECT TOP 20 * FROM dbo.vw_CompanyLoanSummary ORDER BY TotalPrincipal DESC;` |
| Region top 5 companies | Window function over aggregated subquery | `SELECT * FROM dbo.vw_RegionCompanyPrincipalRank WHERE PrincipalRank <= 5;` |
| Remaining balance per loan | Aggregate payments + join collateral each time | `SELECT LoanId, RemainingPrincipal FROM dbo.vw_LoanRemainingBalance ORDER BY RemainingPrincipal DESC;` |
| Upcoming covenant tests | Date math in every query | `SELECT * FROM dbo.vw_UpcomingCovenantTests;` |
| Multi-currency companies | DISTINCT currency count | `SELECT CompanyName FROM dbo.vw_CompanyCurrencyDiversity WHERE IsMultiCurrency=1;` |
| Collateral > threshold | Join + SUM collateral | `SELECT LoanId FROM dbo.vw_LoanCollateralSummary WHERE CollateralTotalValue > 1000000;` |

---
## Performance & Indexing Guidance

| View | Underlying Index Candidates | Notes |
|------|-----------------------------|-------|
| `vw_LoanRemainingBalance` | `PaymentSchedule(LoanId, Status)`, `Collateral(LoanId)` | Consider materializing for heavy usage |
| `vw_CompanyLoanSummary` | `Loan(CompanyId)`, `Company(RegionId)` | Aggregation stable if loans append-only |
| `vw_UpcomingCovenantTests` | `Covenant(NextTestDate)` | If very frequent, transform into table w/ rolling job |
| `vw_LoanCollateralSummary` | `Collateral(LoanId)` | Good candidate for indexed view if static post-insert |
| `vw_RegionCompanyPrincipalRank` | `Loan(CompanyId, PrincipalAmount)` + `Company(RegionId)` | Ranking still computed dynamically |
| `vw_CompanyCurrencyDiversity` | `Loan(CompanyId, CurrencyCode)` | Distinct cardinality benefits from covering index |

### Indexed View Considerations
If converting to an indexed view:
- Add `WITH SCHEMABINDING`.
- Use two-part names for tables (e.g., `dbo.Loan`).
- Replace `COUNT` with `COUNT_BIG` where aggregated.
- Avoid non-deterministic functions (`GETDATE()`).

---
## Integration Into NL2SQL Pipeline

1. **Create Views** in the target database.
2. **Grant SELECT** to the app user / login.
3. **Refresh schema cache** via the UI button (or CLI function).
4. **Augment schema context**: Add a short section "Recommended Views" enumerating view name + 1-line purpose.
5. **Prompt Hint (optional)**: _"Prefer summary views (vw_CompanyLoanSummary, vw_LoanRemainingBalance, vw_RegionCompanyPrincipalRank, vw_UpcomingCovenantTests) when they fully answer the question."_
6. **Monitor token usage** pre/post to quantify improvement.

---
## Rollout Strategy

| Phase | Action | Success Criterion |
|-------|--------|------------------|
| Phase 1 | Create first 3–4 high-impact views | Generated SQL sheds ≥2 joins in target queries |
| Phase 2 | Add ranking & currency diversity | Region & currency queries become single-view selects |
| Phase 3 | Evaluate need for indexed/materialized variants | Reduced average execution time / stable plans |
| Phase 4 | Optional lean portfolio + risk snapshot | Shorter schema context token count |

---
## Future Enhancements
- **Snapshot / Fact Table**: Daily loan balance table for time-series trends.
- **FX Normalization View**: Principal in base currency for cross-currency analytics.
- **CompanyHealth View**: Merge risk, covenant status, multi-currency flag.
- **Event Union View**: Unified recent events (payments + covenant breaches) for “recent activity” queries.

---
## Validation Checklist After Deployment
- [ ] Views created successfully (no missing table errors).
- [ ] App user can `SELECT` from each view.
- [ ] Schema cache refreshed; views appear in context snippet.
- [ ] Sample NL queries now map directly to view-based SQL.
- [ ] Execution plans show fewer scans/joins.
- [ ] Token usage per run decreased (record baseline vs after).

---
## Disclaimer
All templates must be reviewed and adapted to actual column names, datatypes, and constraints in your environment. Introduce indexing and (especially) indexed views only after validating workload frequency and update patterns.

---
**End of Document**
