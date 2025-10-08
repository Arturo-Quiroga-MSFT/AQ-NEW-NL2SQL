# NL2SQL Multi-Model Run Log

**Timestamp:** 2025-10-08T14:29:58.317163

**Implementation:** Multi-Model Optimized (LangChain + Azure OpenAI)

**Total Elapsed Time:** 14.81s

## Model Configuration

- **Intent Model:** `gpt-4o-mini`
- **SQL Model:** `gpt-4.1`
- **Formatting Model:** `gpt-4.1-mini`

## Timing Breakdown

| Stage | Time (seconds) |
|-------|---------------:|
| Intent Extraction | 1.5939 |
| Reasoning | 6.5368 |
| SQL Generation | 1.7380 |
| SQL Execution | 1.1032 |
| Result Formatting | 3.8039 |
| **Total** | **14.7757** |

---

## User Question

```
Show the 10 upcoming loan maturities (soonest MaturityDate first) with principal amount and status. include customer names, region and total number of their loans for each
```

---

## Intent & Entities

*Extracted with `gpt-4o-mini`*

```
```json
{
  "intent": "list",
  "entities": {
    "table": "dbo.vw_LoanPortfolio",
    "columns": [
      "MaturityDate",
      "PrincipalAmount",
      "Status",
      "CompanyName",
      "RegionName"
    ],
    "aggregations": {
      "count": "number of loans"
    }
  },
  "timeframe": "upcoming (soonest MaturityDate first)",
  "filters": {}
}
```
```

---

## Reasoning

*Generated with `gpt-4.1`*

```
Certainly! Here’s my high-level reasoning for constructing the query, step by step:

---

### 1. **Tables and Relationships**
- **Primary Source**: I will use `dbo.vw_LoanPortfolio`, a denormalized view that already combines key information about loans, companies, and their regional details.
    - **Why?** For listing loan details by company and region, with maturity, principal, and basic aggregation, this view is recommended. All required columns (`MaturityDate`, `PrincipalAmount`, `Status`, `CompanyName`, `RegionName`) are present, so no multi-table joins are necessary.

### 2. **Calculations/Aggregations Needed**
- **Count Aggregation**: The user requests a count of loans (i.e., number of loans).
    - This is a `COUNT(*)` grouped by the chosen fields: `MaturityDate`, `PrincipalAmount`, `Status`, `CompanyName`, `RegionName`.
    - **Each row** in the result set will represent a unique combination of these fields, with a count of how many loans exist per that combination.

### 3. **Filtering and Sorting**
- **Filtering**: No specific filters were requested (e.g., by status, company, min/max principal, etc.).
- **Sorting**: The user wants loans ordered by the soonest upcoming maturity dates.
    - I will apply an `ORDER BY MaturityDate ASC` to prioritize loans that are maturing most imminently.
    - This aligns with the "upcoming (soonest MaturityDate first)" timeframe request.

### 4. **Why is this Approach Optimal?**
- **Simplicity and Performance**: Using the `vw_LoanPortfolio` view avoids unnecessary complexity and computation, as this view is purpose-built for portfolio summaries.
- **Accurate Aggregation**: Grouping by all specified fields ensures counts are accurate for each combination (e.g., loans for a specific company in a specific region, on a particular maturity date).
- **Direct Sorting**: Sorting at the SQL level quickly returns the most relevant (soonest) maturities at the top of the result.
- **No Data Redundancy**: No need for extra joins, subqueries, or complex logic, keeping the query clear and maintainable.

---

**Summary:**  
I’ll query `vw_LoanPortfolio`, group by the specified dimensions, count the number of loans, and order the results by the soonest `MaturityDate`. This efficiently delivers the requested portfolio overview, leveraging the database’s design as intended.
```

---

## Generated SQL

*Generated with `gpt-4.1`*

```sql
SELECT
    MaturityDate,
    PrincipalAmount,
    Status,
    CompanyName,
    RegionName,
    COUNT(*) OVER () AS [NumberOfLoans]
FROM
    dbo.vw_LoanPortfolio
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
    "Status": "Active",
    "CompanyName": "Cape Coast Minerals Ltd",
    "RegionName": "Africa",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2026-08-27",
    "PrincipalAmount": 12000000.0,
    "Status": "Active",
    "CompanyName": "Lagos Marine Services",
    "RegionName": "Africa",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2026-08-27",
    "PrincipalAmount": 12000000.0,
    "Status": "Active",
    "CompanyName": "Nairobi AgriFoods PLC",
    "RegionName": "Africa",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2026-08-27",
    "PrincipalAmount": 12000000.0,
    "Status": "Active",
    "CompanyName": "Alexandria Textiles Co",
    "RegionName": "Africa",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2027-01-15",
    "PrincipalAmount": 10000000.0,
    "Status": "Active",
    "CompanyName": "Acme Industrial Holdings",
    "RegionName": "Americas",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2027-08-27",
    "PrincipalAmount": 25000000.0,
    "Status": "Active",
    "CompanyName": "Blue Ridge Energy Corp",
    "RegionName": "Americas",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2027-08-27",
    "PrincipalAmount": 25000000.0,
    "Status": "Active",
    "CompanyName": "Toronto Health Devices",
    "RegionName": "Americas",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2028-08-27",
    "PrincipalAmount": 18000000.0,
    "Status": "Active",
    "CompanyName": "Nordwind Logistics GmbH",
    "RegionName": "Europe",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2028-08-27",
    "PrincipalAmount": 18000000.0,
    "Status": "Active",
    "CompanyName": "Gaulois Pharma SA",
    "RegionName": "Europe",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2028-08-27",
    "PrincipalAmount": 18000000.0,
    "Status": "Active",
    "CompanyName": "Thyme Retail Group",
    "RegionName": "Europe",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2028-08-27",
    "PrincipalAmount": 18000000.0,
    "Status": "Active",
    "CompanyName": "Amsterdam FinTech BV",
    "RegionName": "Europe",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2029-08-27",
    "PrincipalAmount": 22000000.0,
    "Status": "Active",
    "CompanyName": "Osaka Precision K.K.",
    "RegionName": "Asia",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2029-08-27",
    "PrincipalAmount": 22000000.0,
    "Status": "Active",
    "CompanyName": "Shanghai GreenChem Co",
    "RegionName": "Asia",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2029-08-27",
    "PrincipalAmount": 22000000.0,
    "Status": "Active",
    "CompanyName": "Mumbai InfraTech Ltd",
    "RegionName": "Asia",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2029-08-27",
    "PrincipalAmount": 22000000.0,
    "Status": "Active",
    "CompanyName": "Singapore Data Centers",
    "RegionName": "Asia",
    "NumberOfLoans": 16
  },
  {
    "MaturityDate": "2030-09-09",
    "PrincipalAmount": 14000000.0,
    "Status": "Active",
    "CompanyName": "Acme Industrial Holdings",
    "RegionName": "Americas",
    "NumberOfLoans": 16
  }
]
```

---

## AI Summary

*Generated with `gpt-4.1-mini`*

Summary:
The 10 upcoming loan maturities are all scheduled between August 2026 and August 2028, with principal amounts ranging from $10 million to $25 million. All listed loans are currently active. These loans belong to companies across four regions: Africa, Americas, Europe, and Asia. The total number of loans in the portfolio is 16.

Key Insights:
- The earliest maturities (August 27, 2026) are concentrated in African companies, each with a principal amount of $12 million.
- The Americas loans due in 2027 have higher principal amounts, notably $25 million for two companies.
- European loans maturing in 2028 each have a principal of $18 million.
- Every loan is currently active, indicating a consistent status among the upcoming maturities.
- Each company listed holds one of the 16 total portfolio loans, implying the total loan count covers the whole dataset.

Notable Statistics:
- Principal amounts range from $10 million (earliest Americas loan) to $25 million (peak Americas loans).
- There are 16 total loans in the dataset, all active.
- Maturity dates span roughly two years (2026-2028) for these top 10 maturities.

Natural Language Answer:
The 10 upcoming loan maturities are all active loans mostly clustered around specific dates in late August 2026, January 2027, August 2027, and August 2028. They involve companies from Africa, Americas, and Europe with principal amounts between $10 million and $25 million. All companies share a total portfolio size of 16 loans, indicating these loans represent the full loan dataset currently tracked.

---

## Token Usage & Cost Breakdown

**Total tokens:** 6,499

**Total cost:** $0.016522 USD

| Stage | Input Tokens | Output Tokens | Total Tokens |
|-------|-------------:|--------------:|-------------:|
| Intent Extraction | 1,330 | 103 | 1,433 |
| SQL Generation | 2,789 | 639 | 3,428 |
| Result Formatting | 1,298 | 340 | 1,638 |

---

*End of run log*
