# Complex Query Examples for NL2SQL Demo

**Date:** October 8, 2025  
**Purpose:** Curated list of complex natural language questions designed to showcase advanced SQL generation capabilities in the Azure AI Agent Service NL2SQL pipeline.

---

## Overview

These questions are designed to test and demonstrate the sophisticated capabilities of the NL2SQL pipeline, including:
- Multi-table JOINs across 3+ tables
- Complex aggregations (weighted averages, ratios, percentages)
- Window functions (ROW_NUMBER, LAG/LEAD, SUM OVER)
- Date/time calculations and filtering
- Conditional logic (CASE statements for bucketing)
- Subqueries and Common Table Expressions (CTEs)
- Real-world financial metrics and business logic

---

## 🔥 Complex Query Examples

### 1. Multi-Table Joins with Aggregations

**Question:**
```
Show the top 10 companies by total principal amount, including their industry, region, and average interest rate across all their loans.
```

**SQL Complexity:**
- JOIN: Loan → Company → Country → Region
- Aggregations: SUM(PrincipalAmount), AVG(InterestRate)
- GROUP BY: Company
- ORDER BY with LIMIT/TOP

**Business Value:** Portfolio concentration analysis by borrower

---

### 2. Weighted Average Calculations

**Question:**
```
What is the weighted average interest rate by region and currency, weighted by principal amount?
```

**SQL Complexity:**
- Formula: SUM(InterestRate * PrincipalAmount) / SUM(PrincipalAmount)
- Multiple JOINs: Loan → Company → Country → Region, Loan → Currency
- GROUP BY: Region, Currency

**Business Value:** True portfolio yield analysis accounting for loan sizes

---

### 3. Collateral Coverage Ratio Analysis

**Question:**
```
Calculate the collateral coverage ratio for each loan (total collateral value divided by principal amount) and show the top 20 loans with coverage below 120%.
```

**SQL Complexity:**
- Subquery/CTE with GROUP BY on Collateral
- JOIN to Loan for principal
- Calculated field: SUM(CollateralValue) / PrincipalAmount
- HAVING or WHERE clause for filtering ratio < 1.2
- ORDER BY for ranking

**Business Value:** Risk assessment - identify under-collateralized loans

---

### 4. Time-Series Analysis with Window Functions

**Question:**
```
Show the month-over-month change in ending principal from the payment schedule for the top 20 loans with the largest principal decrease.
```

**SQL Complexity:**
- Window function: LAG() OVER (PARTITION BY LoanId ORDER BY DueDate)
- Date formatting: YEAR(), MONTH() or FORMAT()
- Calculated field: EndingPrincipal - LAG(EndingPrincipal)
- ORDER BY absolute change DESC

**Business Value:** Cash flow trend analysis, amortization tracking

---

### 5. Covenant Compliance Rate by Industry and Quarter

**Question:**
```
What is the covenant compliance rate by industry and quarter? Show the percentage of covenant tests that passed versus total tests.
```

**SQL Complexity:**
- JOIN: CovenantTestResult → Covenant → Loan → Company
- Date functions: YEAR(), QUARTER() or DATEPART()
- CASE statement: Status = 'Pass' → 1, else 0
- Aggregation: SUM(CASE...) / COUNT(*) * 100
- GROUP BY: Industry, Quarter

**Business Value:** Regulatory compliance monitoring, risk management

---

### 6. Delinquency Buckets with Distribution Analysis

**Question:**
```
Group payment events into delinquency buckets (0-29, 30-59, 60-89, 90+ days) by region and show the percentage distribution for the last 6 months.
```

**SQL Complexity:**
- CASE statement for bucketing DaysDelinquent
- Date filtering: EventDate >= DATEADD(MONTH, -6, GETDATE())
- JOIN: PaymentEvent → Loan → Company → Country → Region
- Percentage calculation per region
- GROUP BY: Region, DelinquencyBucket

**Business Value:** Portfolio health assessment, delinquency concentration

---

### 7. Payment Timing Performance Analysis

**Question:**
```
What is the average number of days between due date and paid date for payments, grouped by company and quarter?
```

**SQL Complexity:**
- DATEDIFF(day, DueDate, PaidDate)
- WHERE clause: PaidFlag = 1 or PaidDate IS NOT NULL
- Date grouping: YEAR(), QUARTER()
- JOIN: PaymentSchedule → Loan → Company
- GROUP BY: Company, Quarter
- AVG() aggregation

**Business Value:** Payment behavior analysis, client performance tracking

---

### 8. Regional Portfolio Distribution with Ranking

**Question:**
```
For each region, show the top 3 companies by outstanding balance using the latest ending principal from payment schedules, including each company's percentage share of the regional total.
```

**SQL Complexity:**
- Window function: ROW_NUMBER() OVER (PARTITION BY Region ORDER BY Balance DESC)
- Subquery to get latest EndingPrincipal per loan
- Window function: SUM() OVER (PARTITION BY Region) for regional totals
- Percentage calculation: (CompanyBalance / RegionalTotal) * 100
- WHERE: RowNum <= 3

**Business Value:** Concentration risk by geography, top borrower identification

---

### 9. Rate Type Mix by Region

**Question:**
```
Show the distribution of fixed versus variable rate loans by region, including counts, total principal, and percentages.
```

**SQL Complexity:**
- CASE statements: InterestRateType = 'Fixed' → category
- Multiple aggregations: COUNT(), SUM(PrincipalAmount)
- Percentage calculations: COUNT(Fixed) / COUNT(*) * 100
- JOIN: Loan → Company → Country → Region
- GROUP BY: Region, InterestRateType (or pivoted)

**Business Value:** Interest rate risk exposure analysis

---

### 10. Multi-Dimensional Loan Maturity Analysis

**Question:**
```
What is the average loan maturity period in days by industry and loan purpose, for loans originated in the last 2 years?
```

**SQL Complexity:**
- DATEDIFF(day, OriginationDate, MaturityDate)
- Date filtering: OriginationDate >= DATEADD(YEAR, -2, GETDATE())
- JOIN: Loan → Company
- GROUP BY: Industry, LoanPurpose
- AVG() aggregation

**Business Value:** Product mix analysis, term structure insights

---

## 🎯 Demo Strategy

### For Technical Audiences:
Focus on questions **3, 4, 6, 8** - these showcase:
- Advanced SQL features (window functions, CTEs)
- Complex calculations and logic
- Multi-step query construction

### For Business Audiences:
Focus on questions **1, 2, 5, 9** - these emphasize:
- Clear business metrics
- Financial KPIs
- Risk management insights
- Straightforward interpretations

### For Comprehensive Demos:
Use a progression:
1. Start with question **1** (warmup - still complex but intuitive)
2. Move to question **3** or **5** (demonstrate business logic)
3. Finish with question **8** (showcase advanced SQL capabilities)

---

## 📊 SQL Features Demonstrated

| Feature | Questions |
|---------|-----------|
| Multi-table JOINs (3+) | 1, 2, 5, 6, 7, 9, 10 |
| Window Functions | 4, 8 |
| Weighted Aggregations | 2, 5 |
| Date Calculations | 4, 6, 7, 10 |
| CASE Statements | 5, 6, 9 |
| Subqueries/CTEs | 3, 8 |
| Percentage Calculations | 5, 6, 8, 9 |
| Filtering with HAVING | 3 |
| Time-based Filtering | 4, 6, 7, 10 |
| Ranking/Top-N | 1, 3, 4, 8 |

---

## 💡 Tips for Demo Success

1. **Start Simple:** Begin with question 1 to establish baseline capability
2. **Build Complexity:** Progress to more sophisticated queries
3. **Explain the Why:** Connect each query to real business scenarios
4. **Show the SQL:** Display the generated SQL to highlight complexity
5. **Validate Results:** Run the queries and show actual data
6. **Compare Approaches:** If available, contrast with manual SQL writing time

---

## 🔗 Related Documentation

- [CONTOSO-FI Example Questions](./CONTOSO-FI_EXAMPLE_QUESTIONS.txt) - Full question catalog
- [CONTOSO-FI Schema Summary](./CONTOSO-FI_SCHEMA_SUMMARY.md) - Database structure
- [NL2SQL Pipeline Flow](./NL2SQL_PIPELINE_FLOW.md) - Technical architecture

---

**Last Updated:** October 8, 2025
