# CONTOSO-FI Example Solutions (Baseline SQL)

This file contains a subset of validated baseline SQL queries for the CONTOSO-FI database, aligned to the question bank.

Note: Results may vary over time as data changes. Queries prefer `dbo.vw_LoanPortfolio` when suitable for simpler joins.

## Easy

E1) 10 most recent loans by OriginationDate
```sql
SELECT TOP 10 LoanId, LoanNumber, OriginationDate
FROM dbo.vw_LoanPortfolio
ORDER BY OriginationDate DESC;
```

E2) Loans maturing this year (no rows currently returned in sample data)
```sql
SELECT LoanId, LoanNumber, MaturityDate, PrincipalAmount, Status
FROM dbo.vw_LoanPortfolio
WHERE YEAR(MaturityDate) = YEAR(GETDATE())
ORDER BY MaturityDate;
```

## Medium

M1) Total outstanding principal per company
```sql
SELECT CompanyName, SUM(PrincipalAmount) AS TotalPrincipal
FROM dbo.vw_LoanPortfolio
GROUP BY CompanyName
ORDER BY TotalPrincipal DESC;
```

M3) Loans by status per country
```sql
SELECT CountryName, Status, COUNT(*) AS LoanCount
FROM dbo.vw_LoanPortfolio
GROUP BY CountryName, Status
ORDER BY CountryName, Status;
```

M4) Total collateral value per loan and company
```sql
SELECT p.LoanId,
       p.LoanNumber,
       p.CompanyName,
       SUM(c.ValueAmount) AS TotalCollateral
FROM dbo.vw_LoanPortfolio p
JOIN dbo.Collateral c ON c.LoanId = p.LoanId
GROUP BY p.LoanId, p.LoanNumber, p.CompanyName
ORDER BY TotalCollateral DESC;
```

## Complicated

C3) Weighted average interest rate by region (weighted by principal)
```sql
SELECT RegionName,
       CASE WHEN SUM(PrincipalAmount) = 0 THEN NULL
            ELSE SUM(InterestRatePct * PrincipalAmount) / SUM(PrincipalAmount)
       END AS WeightedAvgRate
FROM dbo.vw_LoanPortfolio
GROUP BY RegionName
ORDER BY RegionName;
```

C7) Collateral coverage ratio < 1.2 with maturity in next 6 months (no rows currently returned in sample data)
```sql
WITH CollateralTotals AS (
  SELECT LoanId, SUM(ValueAmount) AS TotalCollateral
  FROM dbo.Collateral
  GROUP BY LoanId
)
SELECT p.LoanId,
       p.LoanNumber,
       p.CompanyName,
       p.PrincipalAmount,
       ct.TotalCollateral,
       CAST(ct.TotalCollateral / NULLIF(p.PrincipalAmount, 0) AS decimal(18,2)) AS CoverageRatio,
       p.MaturityDate
FROM dbo.vw_LoanPortfolio p
LEFT JOIN CollateralTotals ct ON ct.LoanId = p.LoanId
WHERE p.MaturityDate BETWEEN CAST(GETDATE() AS date) AND DATEADD(month, 6, CAST(GETDATE() AS date))
  AND (ct.TotalCollateral / NULLIF(p.PrincipalAmount, 0)) < 1.2
ORDER BY CoverageRatio ASC;
```

---

Suggestions:
- Add additional solutions incrementally and note if queries return zero rows to help curate demo flows.
- Consider complementing with representative inserts in a staging environment if you need guaranteed non-empty results.
