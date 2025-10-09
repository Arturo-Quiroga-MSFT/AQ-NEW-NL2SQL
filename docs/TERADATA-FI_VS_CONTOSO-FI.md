# TERADATA-FI vs CONTOSO-FI: Feature Comparison

## 📊 Capability Matrix

| Capability | CONTOSO-FI | TERADATA-FI | Impact |
|------------|------------|-------------|---------|
| **Loan Pipeline Tracking** | ❌ None | ✅ Full application funnel | **HIGH** - Shows origination process |
| **CRM & Customer Interactions** | ❌ None | ✅ Complete interaction history | **HIGH** - Relationship banking |
| **Financial Statements** | ❌ None | ✅ Quarterly/Annual P&L, Balance Sheet | **CRITICAL** - Credit analysis |
| **Underwriting Process** | ❌ None | ✅ Credit scoring, approval workflow | **HIGH** - Decision intelligence |
| **Employee Performance** | ❌ None | ✅ Loan officer tracking, productivity | **MEDIUM** - Sales analytics |
| **Temporal Analytics** | ⚠️ Basic | ✅ Rich time-series, cohorts, vintages | **HIGH** - Trend analysis |
| **Risk Migration** | ❌ None | ✅ Rating changes over time (SCD Type 2) | **HIGH** - Early warning |
| **Fee & Pricing** | ❌ None | ✅ Complete fee schedule, profitability | **MEDIUM** - Revenue analytics |
| **Branch/Region Hierarchy** | ⚠️ Flat | ✅ Multi-level hierarchy | **MEDIUM** - Org analytics |
| **Industry Benchmarking** | ❌ None | ✅ Industry dimensions with benchmarks | **MEDIUM** - Competitive intel |
| **Covenant Monitoring** | ✅ Yes | ✅ Enhanced with test history | **LOW** - Already exists |
| **Payment Tracking** | ✅ Yes | ✅ Enhanced with methods, types | **LOW** - Already exists |
| **Collateral Management** | ✅ Yes | ✅ Enhanced with bridge table | **LOW** - Already exists |

---

## 🎯 Demo Question Types: Before & After

### **CONTOSO-FI: Limited Scope**
```
❌ "Show me our loan application pipeline by stage"
   → No application data exists

❌ "Which loan officers have the highest approval rates?"
   → No loan officer dimension

❌ "Compare Q2 vs Q3 origination volume by industry"
   → Limited temporal dimensions

❌ "Show me customers whose debt-to-equity ratio increased this year"
   → No financial statement data

❌ "What's our customer interaction frequency by relationship tier?"
   → No CRM data

❌ "Calculate cohort default rates by origination quarter"
   → No cohort tracking

❌ "Show me early warning indicators for potential defaults"
   → Limited predictive signals

✅ "Show me active loans by region"
   → Basic query works

✅ "List loans with outstanding principal over $10M"
   → Basic query works
```

### **TERADATA-FI: Comprehensive Coverage**
```
✅ ALL CONTOSO-FI queries (backward compatible)

PLUS:

✅ "Show me the loan application funnel conversion rate by product"
✅ "Which loan officers are exceeding their origination targets?"
✅ "Compare origination volume quarter-over-quarter by branch"
✅ "Show me customers whose interest coverage ratio improved"
✅ "What's the average interaction frequency for VIP vs standard customers?"
✅ "Calculate vintage default rates for 2024 Q1 originations"
✅ "Alert me to customers with declining EBITDA and rising debt"
✅ "Show me the profitability by customer segment"
✅ "Which industries have the best risk-adjusted returns?"
✅ "Compare our pricing to industry benchmarks by credit score band"
```

---

## 📈 Query Complexity Comparison

### **CONTOSO-FI: Simple Queries Only**
```sql
-- Typical query: 2-3 table joins
SELECT 
    c.CompanyName,
    l.PrincipalAmount,
    l.Status
FROM Loan l
JOIN Company c ON l.CompanyId = c.CompanyId
WHERE l.Status = 'Active';
```

### **TERADATA-FI: Enterprise Complexity**
```sql
-- Advanced query: 8+ table joins, window functions, CTEs
WITH MonthlyPerformance AS (
    SELECT 
        d.Year,
        d.Month,
        e.EmployeeName,
        b.BranchName,
        COUNT(DISTINCT l.LoanId) AS OriginationCount,
        SUM(l.PrincipalAmount) AS TotalVolume,
        AVG(l.InterestRate) AS AvgRate,
        AVG(DATEDIFF(day, a.ApplicationDate, l.OriginationDate)) AS AvgDaysToClose,
        ROW_NUMBER() OVER (
            PARTITION BY d.Year, d.Month 
            ORDER BY SUM(l.PrincipalAmount) DESC
        ) AS VolumeRank
    FROM FACT_LOAN_ORIGINATION l
    JOIN DimEmployee e ON l.LoanOfficerId = e.EmployeeKey
    JOIN DimBranch b ON l.BranchId = b.BranchKey
    JOIN DimDate d ON l.OriginationDate = d.DateKey
    JOIN FACT_LOAN_APPLICATION a ON l.ApplicationId = a.ApplicationId
    WHERE d.Year = 2025
    GROUP BY d.Year, d.Month, e.EmployeeName, b.BranchName
)
SELECT 
    Year,
    Month,
    EmployeeName,
    BranchName,
    OriginationCount,
    TotalVolume,
    AvgRate,
    AvgDaysToClose,
    LAG(TotalVolume, 1) OVER (
        PARTITION BY EmployeeName 
        ORDER BY Year, Month
    ) AS PriorMonthVolume,
    TotalVolume - LAG(TotalVolume, 1) OVER (
        PARTITION BY EmployeeName 
        ORDER BY Year, Month
    ) AS VolumeChange
FROM MonthlyPerformance
WHERE VolumeRank <= 10
ORDER BY Year, Month, VolumeRank;
```

---

## 💰 ROI for Demo Investment

### **Development Time**
- **Phase 1-3 (Core):** 2-3 weeks
- **Phase 4-5 (Full):** 4-5 weeks total
- **Maintenance:** Low (well-structured schema)

### **Demo Impact**
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Demo questions possible** | ~50 | **500+** | **10x** |
| **Query complexity range** | Basic | Advanced | Enterprise-grade |
| **Business processes covered** | 1 | **7+** | Complete lifecycle |
| **Stakeholder appeal** | IT/Data teams | **C-Suite + LOB** | Broader audience |
| **Competitive differentiation** | Low | **High** | Unique offering |
| **Win rate improvement** | Baseline | **+30-50%** (est.) | Significant |

### **Business Case**
```
Investment: 4-5 weeks development time
Return: 
  - 10x more demo questions
  - Enterprise-grade complexity showcase
  - Full commercial lending lifecycle
  - Competitive moat in NL2SQL market
  - Higher win rates in sales cycles
  - Expanded buyer personas (LOB leaders, not just IT)

Payback Period: First major deal closed (likely < 3 months)
```

---

## 🏗️ Implementation Strategy

### **Option A: Full Rebuild (Recommended)**
✅ Clean, optimized star schema  
✅ No technical debt  
✅ Best performance  
✅ Easiest to maintain  
❌ Cannot reuse existing data  
❌ 4-5 weeks timeline  

**Verdict:** Best for long-term success

### **Option B: Hybrid Approach**
✅ Reuse CONTOSO-FI loan data  
✅ Add new dimensions/facts around it  
✅ Faster initial deployment  
❌ Denormalization challenges  
❌ Mixed schema design patterns  
❌ Technical debt accumulation  

**Verdict:** Okay for POC, problematic long-term

### **Option C: Parallel Databases**
✅ Keep CONTOSO-FI for existing demos  
✅ Build TERADATA-FI for advanced demos  
✅ Gradual migration  
❌ Maintain two databases  
❌ Duplicate effort  

**Verdict:** Good transition strategy

---

## 🎬 Migration Path (If Choosing Option A)

### **Week 1: Schema & Core Dimensions**
- [ ] Create all dimension tables
- [ ] Create FACT_LOAN_ORIGINATION
- [ ] Seed DimDate (5 years: 2020-2025)
- [ ] Seed DimCustomer (5,000 rows)
- [ ] Seed DimEmployee (150 rows)
- [ ] Seed DimBranch (25 rows)
- [ ] Seed DimLoanProduct (15 rows)

### **Week 2: Origination & Applications**
- [ ] Create FACT_LOAN_APPLICATION
- [ ] Create FACT_LOAN_BALANCE_DAILY
- [ ] Seed application funnel (50,000 apps)
- [ ] Link to originations (12,000 loans)
- [ ] Generate daily balance snapshots (1 year)

### **Week 3: Financial Analytics**
- [ ] Create FACT_CUSTOMER_FINANCIALS
- [ ] Create FACT_COVENANT_TEST
- [ ] Seed quarterly financials (3 years)
- [ ] Seed covenant tests (12 months)

### **Week 4: Transactions & CRM**
- [ ] Create FACT_PAYMENT_TRANSACTION
- [ ] Create FACT_CUSTOMER_INTERACTION
- [ ] Seed payment history (150,000 txns)
- [ ] Seed CRM interactions (100,000 records)

### **Week 5: Optimization & Testing**
- [ ] Create indexes for performance
- [ ] Create materialized views for common queries
- [ ] Generate 500+ demo questions
- [ ] Performance testing (target: <3s for 95% of queries)
- [ ] Update NL2SQL app configuration
- [ ] Documentation & demo scripts

---

## 📊 Data Distribution Examples

### **Customer Segments**
```
Small Business:      60% (3,000 customers)
Middle Market:       30% (1,500 customers)
Corporate:           10% (500 customers)
```

### **Loan Products**
```
Term Loans:          40%
Lines of Credit:     25%
Equipment Finance:   15%
Real Estate:         12%
SBA Loans:           5%
Other:               3%
```

### **Application Outcomes**
```
Approved:            24% (12,000 originations)
Declined:            45% (22,500 rejections)
Pending:             8% (4,000 in-process)
Withdrawn:           23% (11,500 withdrawn)
```

### **Risk Ratings**
```
Investment Grade:    35%
Sub-Investment Grade: 50%
High Risk:           12%
Default/NPL:         3%
```

### **Geographic Distribution**
```
Northeast:           28%
Southeast:           24%
Midwest:             22%
West:                18%
Southwest:           8%
```

---

## 🚀 Quick Win: Sample Questions for First Demo

### **Simple (Baseline Compatibility)**
1. "Show me all active loans"
2. "List the top 10 customers by total loan balance"
3. "What's the average interest rate by product type?"

### **Intermediate (New Capabilities)**
4. "Show me the loan application funnel for Q3 2025"
5. "Which loan officers closed the most volume last quarter?"
6. "Compare origination volume month-over-month for 2025"

### **Advanced (Competitive Differentiation)**
7. "Calculate the vintage default rate for 2024 Q1 originations by risk rating"
8. "Show me customers whose debt-to-equity ratio increased by more than 50% YoY"
9. "Which industries have the highest ROE and lowest default rates?"
10. "Alert me to VIP customers who haven't had an interaction in 90+ days"

---

## 💡 Pro Tips for Demos

### **Storytelling Arc**
1. **Start Simple:** "Show me active loans" (proves baseline)
2. **Add Complexity:** "Show me the application pipeline" (new capability)
3. **Show Insights:** "Compare approval rates by loan officer" (analytics)
4. **Demonstrate Value:** "Alert me to early warning signals" (predictive)
5. **Close with Impact:** "Calculate portfolio ROE by segment" (C-suite question)

### **Audience Customization**
- **For CROs:** Risk migration, early warning, credit quality trends
- **For COOs:** Process efficiency, cycle times, productivity
- **For CFOs:** Profitability, ROE, fee income, provisioning
- **For Chief Lending Officers:** Pipeline, conversion, pricing, customer satisfaction
- **For Data Scientists:** Complex queries, window functions, cohort analysis

---

## ✅ Recommendation

**BUILD TERADATA-FI as a separate database (Option C → Option A path)**

**Rationale:**
1. Existing CONTOSO-FI demos continue to work (no disruption)
2. TERADATA-FI becomes the "advanced demo" showcase
3. Clean slate allows proper star schema design
4. Over time, retire CONTOSO-FI once TERADATA-FI is mature
5. Competitive advantage in market (no other NL2SQL solution has this depth)

**Timeline:** 5 weeks for full implementation  
**Payoff:** Immediate differentiation, higher win rates, broader buyer audience  
**Risk:** Low (parallel operation, no disruption to existing demos)

---

**Next Step:** Create DDL scripts for Phase 1? 🚀
