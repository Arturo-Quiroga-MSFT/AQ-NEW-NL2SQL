# NL2SQL Multi-Model Run Log

**Timestamp:** 2025-10-08T14:27:45.741489

**Implementation:** Multi-Model Optimized (LangChain + Azure OpenAI)

**Total Elapsed Time:** 14.98s

## Model Configuration

- **Intent Model:** `gpt-4o-mini`
- **SQL Model:** `gpt-4.1`
- **Formatting Model:** `gpt-4.1-mini`

## Timing Breakdown

| Stage | Time (seconds) |
|-------|---------------:|
| Intent Extraction | 1.1802 |
| Reasoning | 6.1335 |
| SQL Generation | 1.2592 |
| SQL Execution | 1.0454 |
| Result Formatting | 4.7500 |
| **Total** | **14.3682** |

---

## User Question

```
Show the 10 upcoming loan maturities (soonest MaturityDate first) with principal amount and status.
```

---

## Intent & Entities

*Extracted with `gpt-4o-mini`*

```
{
  "intent": "list",
  "entities": {
    "table": "dbo.vw_LoanPortfolio",
    "columns": ["MaturityDate", "PrincipalAmount", "Status"]
  },
  "timeframe": "upcoming maturities",
  "aggregations": null,
  "filters": null
}
```

---

## Reasoning

*Generated with `gpt-4.1`*

```
Certainly! Here is my reasoning, step by step:

### 1. **Tables and Relationships**
- The user wants to list columns (`MaturityDate`, `PrincipalAmount`, `Status`) from `dbo.vw_LoanPortfolio`.
- Since the question asks for a simple list of loan attributes, the view `dbo.vw_LoanPortfolio` is optimal, as it is denormalized and contains all required columns directly—no need for complex joins between base tables like `Loan` or `Company`.

### 2. **Calculations or Aggregations**
- **None required.** The question only requests a list of columns, and there is no indication of needing sums, averages, counts, or grouped data.

### 3. **Filtering or Sorting Logic**
- **Filtering:** The timeframe “upcoming maturities” implies we want loans whose `MaturityDate` is in the future (greater than or equal to today’s date). Depending on business context, this might be further limited to a certain future window, but with information given, the basic filter is:
  ```
  WHERE MaturityDate >= CAST(GETDATE() AS DATE)
  ```
- **Sorting:** Although not explicitly requested, it is often useful to sort by `MaturityDate` ascending so that loans maturing soonest are listed at the top. This could be appended as:
  ```
  ORDER BY MaturityDate ASC
  ```

### 4. **Why This Approach Is Optimal**
- **Simplicity:** `dbo.vw_LoanPortfolio` was designed for simple portfolio listing queries, avoiding the complexity and overhead of joining multiple base tables.
- **Performance:** Querying a view versus joining across multiple tables will generally be faster for simple selects—especially when only a few columns are needed.
- **Maintainability:** Using the view reduces query complexity, making it easier to maintain and understand.

---

**Summary:**  
I will query `dbo.vw_LoanPortfolio` for the specified columns, filter for loans with future `MaturityDate` (upcoming), and (optionally) sort by `MaturityDate`. No joins or aggregates needed. This is efficient, simple, and follows the provided schema guidelines.
```

---

## Generated SQL

*Generated with `gpt-4.1`*

```sql
SELECT
    MaturityDate,
    PrincipalAmount,
    Status
FROM
    dbo.vw_LoanPortfolio
WHERE
    -- Filter for loans with upcoming maturities (MaturityDate in the future)
    MaturityDate > GETDATE()
ORDER BY
    MaturityDate ASC;
```

---

## Query Results

**Row count:** 16

```json
[
  {
    "MaturityDate": "2026-08-27",
    "PrincipalAmount": 12000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2026-08-27",
    "PrincipalAmount": 12000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2026-08-27",
    "PrincipalAmount": 12000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2026-08-27",
    "PrincipalAmount": 12000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2027-01-15",
    "PrincipalAmount": 10000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2027-08-27",
    "PrincipalAmount": 25000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2027-08-27",
    "PrincipalAmount": 25000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2028-08-27",
    "PrincipalAmount": 18000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2028-08-27",
    "PrincipalAmount": 18000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2028-08-27",
    "PrincipalAmount": 18000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2028-08-27",
    "PrincipalAmount": 18000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2029-08-27",
    "PrincipalAmount": 22000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2029-08-27",
    "PrincipalAmount": 22000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2029-08-27",
    "PrincipalAmount": 22000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2029-08-27",
    "PrincipalAmount": 22000000.0,
    "Status": "Active"
  },
  {
    "MaturityDate": "2030-09-09",
    "PrincipalAmount": 14000000.0,
    "Status": "Active"
  }
]
```

---

## AI Summary

*Generated with `gpt-4.1-mini`*

Summary:
The query retrieved upcoming loan maturities sorted by the nearest maturity date, showing the maturity date, principal amount, and status for each loan. The dataset contains multiple loans with maturity dates ranging from August 27, 2026, to September 9, 2030, all of which are currently marked as "Active."

Key Insights and Patterns:
- The earliest upcoming maturity dates are August 27, 2026, with four loans each having a principal amount of $12 million.
- The second soonest maturity is January 15, 2027, with a single loan valued at $10 million.
- Several loans share the same maturity dates with identical principal amounts, indicating possible grouped or syndicated loans.
- The largest principal amounts tend to appear in later maturities (e.g., $25 million in 2027 and $22 million in 2029).
- Every loan listed is currently "Active," showing no matured or defaulted loans in the immediate future batch.

Notable Statistics:
- Number of loans in the first 16 maturities shown: 16
- Range of maturity dates: August 27, 2026 – September 9, 2030
- Principal amounts range from $10 million to $25 million.
- Multiple loans share exact maturity dates and amounts (e.g., four loans of $12 million on 2026-08-27).
- The total principal for the top 10 loans (by maturity date) sums approximately:
   - 4 loans at $12M = $48M
   - 1 loan at $10M = $10M
   - 2 loans at $25M = $50M
   Total = $108 million for the first 7 loans listed. Including subsequent loans would increase this total.

Natural Language Answer:
The 10 upcoming loan maturities starting with the soonest all have "Active" status, with maturity dates beginning on August 27, 2026. These loans range in principal amounts from $10 million to $25 million. Notably, multiple loans mature on the same dates with identical principal amounts, indicating clusters of loans maturing simultaneously. The soonest maturities include four loans each valued at $12 million maturing on August 27, 2026, followed by loans maturing in early 2027 and beyond. Overall, the immediate future loan portfolio has significant principal amounts coming due, totaling over $100 million within the first seven maturities.

---

## Token Usage & Cost Breakdown

**Total tokens:** 5,996

**Total cost:** $0.015058 USD

| Stage | Input Tokens | Output Tokens | Total Tokens |
|-------|-------------:|--------------:|-------------:|
| Intent Extraction | 1,317 | 69 | 1,386 |
| SQL Generation | 2,719 | 515 | 3,234 |
| Result Formatting | 873 | 503 | 1,376 |

---

*End of run log*
