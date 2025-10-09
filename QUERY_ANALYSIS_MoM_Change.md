# Query Analysis: Month-over-Month Principal Change

## Original Question
"For each loan, compute month-over-month change in EndingPrincipal from PaymentSchedule; show 20 loans with the largest absolute change (include positive/negative flags)."

## Why No Results Were Returned

### Primary Reason: **Query Was Not Executed**
Looking at the log file, there is **no "QUERY RESULTS" section**, which means:
- ✅ SQL was generated successfully
- ✅ No SQL execution errors
- ❌ Query was not executed (likely user clicked "Skip exec" toggle)

### If Query Were Executed: Would It Work?

**Answer: Maybe - depends on data availability**

## SQL Query Assessment

### ✅ Strengths:
1. **Well-structured CTEs** - Clean, readable approach
2. **Correct windowing logic** - Uses `ROW_NUMBER()` properly
3. **Proper month-over-month join** - Uses `DATEADD(month, -1, ...)` correctly
4. **Good ordering** - Sorts by absolute change descending

### ⚠️ Issue: Schema Assumption

**The query calculates:**
```sql
EndingPrincipal = (StartingPrincipal - PrincipalDue)
```

**But the actual table has:**
```sql
dbo.PaymentSchedule (
    LoanId,
    PaymentNumber,
    DueDate,
    StartingPrincipal,
    PrincipalDue,
    InterestDue,
    CurrencyCode,
    Status,
    PaidFlag,
    EndingPrincipal  -- ✅ This column EXISTS!
)
```

**Impact**: The calculation is **redundant but not wrong**. However, if `EndingPrincipal` is already calculated correctly in the table, using it directly is better.

## Improved Query

```sql
-- Calculate month-over-month absolute changes in EndingPrincipal per loan
-- Uses existing EndingPrincipal column from PaymentSchedule table
WITH MonthlySchedules AS
(
    -- Capture schedule rows with month bucket and row number per loan/month by latest DueDate
    SELECT
        ps.LoanId,
        DATEFROMPARTS(YEAR(ps.DueDate), MONTH(ps.DueDate), 1) AS MonthStart,
        ps.DueDate,
        ps.EndingPrincipal,  -- ✅ Use existing column
        ROW_NUMBER() OVER (
            PARTITION BY ps.LoanId, DATEFROMPARTS(YEAR(ps.DueDate), MONTH(ps.DueDate), 1)
            ORDER BY ps.DueDate DESC, COALESCE(ps.PaymentNumber, 0) DESC
        ) AS rn
    FROM dbo.PaymentSchedule AS ps
    WHERE ps.DueDate IS NOT NULL
      AND ps.EndingPrincipal IS NOT NULL  -- ✅ Filter out NULLs early
)
, MonthEndPerLoan AS
(
    -- Keep only the last schedule row (month-end) per loan/month
    SELECT
        LoanId,
        MonthStart,
        DueDate AS LastDueDate,
        EndingPrincipal
    FROM MonthlySchedules
    WHERE rn = 1
)
, MonthOverMonth AS
(
    -- Join each month to the prior calendar month for the same loan
    SELECT
        cur.LoanId,
        cur.MonthStart,
        cur.LastDueDate,
        cur.EndingPrincipal AS EndingPrincipal_Current,
        prev.EndingPrincipal AS EndingPrincipal_Previous,
        (cur.EndingPrincipal - prev.EndingPrincipal) AS ChangeAmount,
        ABS(cur.EndingPrincipal - prev.EndingPrincipal) AS AbsChangeAmount,
        CASE
            WHEN (cur.EndingPrincipal - prev.EndingPrincipal) > 0 THEN 'Increase'
            WHEN (cur.EndingPrincipal - prev.EndingPrincipal) < 0 THEN 'Decrease'
            ELSE 'NoChange'
        END AS ChangeDirection
    FROM MonthEndPerLoan AS cur
    INNER JOIN MonthEndPerLoan AS prev
        ON cur.LoanId = prev.LoanId
       AND prev.MonthStart = DATEADD(month, -1, cur.MonthStart)
)
-- Return top 20 loans/months with largest absolute month-over-month change
SELECT TOP (20)
    m.LoanId,
    CONVERT(varchar(7), m.MonthStart, 120) AS YearMonth,
    m.LastDueDate,
    m.EndingPrincipal_Current AS EndingPrincipal,
    m.EndingPrincipal_Previous AS EndingPrincipal_Prev,
    m.ChangeAmount AS MoM_SignedChange,
    m.AbsChangeAmount AS MoM_AbsoluteChange,
    m.ChangeDirection
FROM MonthOverMonth AS m
ORDER BY m.AbsChangeAmount DESC, m.LoanId;
```

## Why It Might Return 0 Rows (Even With Correct SQL)

### Data Requirements:
1. **Need consecutive months** - Query requires INNER JOIN between adjacent months
2. **Need non-NULL EndingPrincipal** - If values are NULL, no results
3. **Need multiple months per loan** - Single-month loans won't have MoM comparison
4. **Need variation in principal** - If all loans have same principal, changes might be zero

### To Diagnose:

#### Test 1: Check if PaymentSchedule has data
```sql
SELECT COUNT(*) AS TotalRows
FROM dbo.PaymentSchedule;
```

#### Test 2: Check date range and loan coverage
```sql
SELECT 
    MIN(DueDate) AS EarliestDate,
    MAX(DueDate) AS LatestDate,
    COUNT(DISTINCT LoanId) AS UniqueLoans,
    COUNT(DISTINCT DATEFROMPARTS(YEAR(DueDate), MONTH(DueDate), 1)) AS UniqueMonths
FROM dbo.PaymentSchedule
WHERE EndingPrincipal IS NOT NULL;
```

#### Test 3: Check for consecutive months
```sql
WITH MonthData AS (
    SELECT DISTINCT
        LoanId,
        DATEFROMPARTS(YEAR(DueDate), MONTH(DueDate), 1) AS MonthStart
    FROM dbo.PaymentSchedule
    WHERE EndingPrincipal IS NOT NULL
)
SELECT COUNT(*) AS LoansWithConsecutiveMonths
FROM MonthData cur
INNER JOIN MonthData prev
    ON cur.LoanId = prev.LoanId
   AND prev.MonthStart = DATEADD(month, -1, cur.MonthStart);
```

## Verdict

### Query Quality: ✅ **CORRECT**
- The SQL is well-written and should execute without errors
- Logic is sound for month-over-month calculation

### Why No Results:
1. **Primary**: Query was not executed (no "QUERY RESULTS" section in log)
2. **If executed**: Would depend on:
   - Data availability (consecutive months)
   - Non-NULL EndingPrincipal values
   - Actual variation in principal amounts

### Recommendation:
1. ✅ **Execute the query** (don't skip execution)
2. ✅ **Use existing EndingPrincipal column** (already in table)
3. ✅ **Run diagnostic queries** to verify data availability
4. ⚠️ **If still 0 rows**: Data likely doesn't have consecutive months or variations

---

**Classification**: 
- ❌ Not an erroneous query
- ⚠️ Likely insufficient data or query not executed
- ✅ SQL syntax and logic are correct
