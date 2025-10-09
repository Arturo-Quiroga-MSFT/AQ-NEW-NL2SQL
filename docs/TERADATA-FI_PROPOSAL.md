# TERADATA-FI Database Proposal
## Enhanced Commercial Loan Origination & Portfolio Management System

**Date:** October 9, 2025  
**Purpose:** Create a comprehensive, demo-ready database that showcases NL2SQL capabilities across the **complete commercial lending lifecycle**

---

## 🎯 Current CONTOSO-FI Gaps & Limitations

### What CONTOSO-FI Has:
✅ **Post-origination** loan portfolio tracking  
✅ Basic payment schedules and events  
✅ Covenant monitoring  
✅ Risk metrics  

### What CONTOSO-FI Lacks (Critical for Compelling Demos):
❌ **Loan Application/Origination Process** - No pipeline visibility  
❌ **Customer Relationship Management** - No contact history, interactions  
❌ **Credit Analysis Workflow** - No underwriting decisions, credit scores  
❌ **Document Management** - No audit trail of required documents  
❌ **Pricing & Fee Management** - No fee schedules, origination costs  
❌ **Officer & Team Assignment** - No ownership, workflow tracking  
❌ **Time-Series Analytics** - Limited temporal dimensions  
❌ **Financial Statements** - No borrower financials (balance sheet, P&L)  
❌ **Industry Benchmarks** - No comparative analysis capabilities  
❌ **Relationship Banking** - No cross-sell, multi-product tracking  

---

## 🌟 TERADATA-FI: Star Schema Design

### Architecture Philosophy
- **True Star Schema** with optimized dimensional modeling
- **Slowly Changing Dimensions (SCD Type 2)** for historical tracking
- **Role-Playing Dimensions** (e.g., multiple date references)
- **Junk Dimensions** for low-cardinality flags
- **Outrigger Dimensions** for hierarchical data
- **Bridge Tables** for many-to-many relationships

---

## 📊 Dimensional Model

### **FACT TABLES** (7 Core Facts)

#### 1. **FACT_LOAN_APPLICATION**
*One row per loan application submission*
```
ApplicationId (PK)
ApplicationDate (FK to DimDate)
DecisionDate (FK to DimDate)
CustomerId (FK to DimCustomer)
ProductId (FK to DimLoanProduct)
LoanOfficerId (FK to DimEmployee)
BranchId (FK to DimBranch)
IndustryId (FK to DimIndustry)
CreditScoreId (FK to DimCreditScore)
ApplicationStatusId (FK to DimApplicationStatus)
--
RequestedAmount (DECIMAL)
ApprovedAmount (DECIMAL)
RequestedTerm (INT)
ApprovedTerm (INT)
RequestedRate (DECIMAL)
ApprovedRate (DECIMAL)
--
CreditScore (INT)
DebtToIncomeRatio (DECIMAL)
DaysToDecision (INT)
ApplicationScore (INT) -- Automated underwriting score
RiskRating (VARCHAR) -- Internal risk grade
--
IsApproved (BIT)
IsDeclined (BIT)
IsPending (BIT)
IsWithdrawn (BIT)
--
CreatedDate (DATETIME)
ModifiedDate (DATETIME)
```

#### 2. **FACT_LOAN_ORIGINATION**
*One row per successfully originated loan*
```
LoanId (PK)
OriginationDate (FK to DimDate)
MaturityDate (FK to DimDate)
FirstPaymentDate (FK to DimDate)
CustomerId (FK to DimCustomer)
ProductId (FK to DimLoanProduct)
LoanOfficerId (FK to DimEmployee)
UnderwriterId (FK to DimEmployee)
BranchId (FK to DimBranch)
IndustryId (FK to DimIndustry)
CollateralTypeId (FK to DimCollateralType)
PurposeId (FK to DimLoanPurpose)
RiskRatingId (FK to DimRiskRating)
--
PrincipalAmount (DECIMAL)
InterestRate (DECIMAL)
TermMonths (INT)
PaymentFrequency (VARCHAR)
AmortizationType (VARCHAR)
--
OriginationFee (DECIMAL)
ProcessingFee (DECIMAL)
TotalFeesCharged (DECIMAL)
EstimatedRevenue (DECIMAL)
--
LoanToValue (DECIMAL)
DebtServiceCoverageRatio (DECIMAL)
--
IsSecured (BIT)
IsSubordinated (BIT)
IsSyndicated (BIT)
--
CreatedDate (DATETIME)
```

#### 3. **FACT_LOAN_BALANCE_DAILY**
*Daily snapshot of loan balances (massive table for trend analysis)*
```
BalanceSnapshotId (PK)
SnapshotDate (FK to DimDate)
LoanId (FK to FACT_LOAN_ORIGINATION)
CustomerId (FK to DimCustomer)
ProductId (FK to DimLoanProduct)
DelinquencyStatusId (FK to DimDelinquencyStatus)
RiskRatingId (FK to DimRiskRating)
--
OutstandingPrincipal (DECIMAL)
OutstandingInterest (DECIMAL)
TotalOutstanding (DECIMAL)
ScheduledPrincipal (DECIMAL)
PrincipalPaid (DECIMAL)
InterestPaid (DECIMAL)
FeesPaid (DECIMAL)
--
DaysDelinquent (INT)
DelinquentAmount (DECIMAL)
--
CurrentRiskRating (VARCHAR)
ProbabilityOfDefault (DECIMAL)
ExpectedLoss (DECIMAL)
--
AllowanceForLosses (DECIMAL) -- CECL/Provisioning
```

#### 4. **FACT_PAYMENT_TRANSACTION**
*Every payment transaction (principal, interest, fees)*
```
PaymentId (PK)
PaymentDate (FK to DimDate)
ScheduledDate (FK to DimDate)
LoanId (FK to FACT_LOAN_ORIGINATION)
CustomerId (FK to DimCustomer)
PaymentMethodId (FK to DimPaymentMethod)
PaymentTypeId (FK to DimPaymentType)
--
PrincipalAmount (DECIMAL)
InterestAmount (DECIMAL)
FeesAmount (DECIMAL)
PenaltyAmount (DECIMAL)
TotalPaidAmount (DECIMAL)
--
DaysLate (INT)
IsEarlyPayment (BIT)
IsLatePayment (BIT)
IsPartialPayment (BIT)
IsReversed (BIT)
```

#### 5. **FACT_CUSTOMER_FINANCIALS**
*Periodic financial statements from borrowers (quarterly/annually)*
```
FinancialStatementId (PK)
StatementDate (FK to DimDate)
CustomerId (FK to DimCustomer)
IndustryId (FK to DimIndustry)
StatementTypeId (FK to DimStatementType) -- Q1, Q2, Annual, Interim
--
TotalRevenue (DECIMAL)
GrossProfit (DECIMAL)
EBITDA (DECIMAL)
NetIncome (DECIMAL)
--
TotalAssets (DECIMAL)
CurrentAssets (DECIMAL)
TotalLiabilities (DECIMAL)
CurrentLiabilities (DECIMAL)
ShareholdersEquity (DECIMAL)
--
CashFlow_Operating (DECIMAL)
CashFlow_Investing (DECIMAL)
CashFlow_Financing (DECIMAL)
--
CurrentRatio (DECIMAL)
QuickRatio (DECIMAL)
DebtToEquityRatio (DECIMAL)
InterestCoverageRatio (DECIMAL)
ReturnOnAssets (DECIMAL)
ReturnOnEquity (DECIMAL)
```

#### 6. **FACT_COVENANT_TEST**
*Covenant compliance testing results*
```
CovenantTestId (PK)
TestDate (FK to DimDate)
DueDate (FK to DimDate)
LoanId (FK to FACT_LOAN_ORIGINATION)
CustomerId (FK to DimCustomer)
CovenantTypeId (FK to DimCovenantType)
--
ActualValue (DECIMAL)
RequiredValue (DECIMAL)
ThresholdValue (DECIMAL)
Variance (DECIMAL)
VariancePercent (DECIMAL)
--
IsPassed (BIT)
IsFailed (BIT)
IsWaiverGranted (BIT)
IsInCure (BIT)
--
DaysToNextTest (INT)
ConsecutiveFailures (INT)
```

#### 7. **FACT_CUSTOMER_INTERACTION**
*CRM interactions, meetings, calls, emails*
```
InteractionId (PK)
InteractionDate (FK to DimDate)
CustomerId (FK to DimCustomer)
EmployeeId (FK to DimEmployee)
InteractionTypeId (FK to DimInteractionType)
InteractionChannelId (FK to DimInteractionChannel)
--
DurationMinutes (INT)
NextFollowUpDays (INT)
--
IsSuccessful (BIT)
IsComplaint (BIT)
IsCrossSellOpportunity (BIT)
--
SentimentScore (INT) -- 1-10
SatisfactionRating (INT) -- 1-5
--
Notes (NVARCHAR(MAX))
```

---

### **DIMENSION TABLES** (25+ Dimensions)

#### **CUSTOMER DIMENSIONS**

##### **DimCustomer** (SCD Type 2)
```
CustomerKey (PK Surrogate)
CustomerId (Business Key)
CompanyName (NVARCHAR)
TaxId (VARCHAR)
LegalEntityType (VARCHAR) -- LLC, Corp, Partnership, Sole Prop
YearFounded (INT)
EmployeeCount (INT)
AnnualRevenue (DECIMAL)
--
PrimaryIndustryId (FK to DimIndustry)
PrimarySICCode (VARCHAR)
PrimaryNAICSCode (VARCHAR)
--
HeadquartersAddressId (FK to DimAddress)
CreditRating_SP (VARCHAR)
CreditRating_Moody (VARCHAR)
CreditRating_Fitch (VARCHAR)
InternalRiskRating (VARCHAR)
--
RelationshipManagerId (FK to DimEmployee)
CustomerSegment (VARCHAR) -- Small Business, Middle Market, Corporate
CustomerTier (VARCHAR) -- Platinum, Gold, Silver, Bronze
--
TotalLoansCount (INT)
TotalLoanVolume (DECIMAL)
LifetimeRevenue (DECIMAL)
DefaultCount (INT)
--
IsActive (BIT)
IsHighRisk (BIT)
IsVIP (BIT)
--
EffectiveDate (DATE)
EndDate (DATE)
IsCurrent (BIT)
```

##### **DimCustomerContact**
```
ContactKey (PK)
CustomerId (FK to DimCustomer)
ContactName (NVARCHAR)
Title (VARCHAR)
Email (VARCHAR)
Phone (VARCHAR)
IsPrimaryContact (BIT)
IsAuthorizedSigner (BIT)
IsFinancialContact (BIT)
```

##### **DimIndustry** (Hierarchy)
```
IndustryKey (PK)
IndustryId (Business Key)
IndustrySector (VARCHAR) -- Manufacturing, Services, Technology
IndustryGroup (VARCHAR)
IndustryName (VARCHAR)
SICCode (VARCHAR)
NAICSCode (VARCHAR)
--
RiskProfile (VARCHAR) -- Low, Medium, High
DefaultRate_Historical (DECIMAL)
RecoveryRate_Historical (DECIMAL)
--
IsRegulated (BIT)
IsVolatile (BIT)
```

#### **PRODUCT DIMENSIONS**

##### **DimLoanProduct**
```
ProductKey (PK)
ProductId (Business Key)
ProductName (VARCHAR) -- Term Loan, LOC, Equipment Finance
ProductCategory (VARCHAR) -- Commercial, Real Estate, SBA
ProductType (VARCHAR)
--
MinAmount (DECIMAL)
MaxAmount (DECIMAL)
MinTerm (INT)
MaxTerm (INT)
--
BaseRateType (VARCHAR) -- Fixed, Variable
ReferenceRateType (VARCHAR) -- SOFR, Prime, LIBOR
MarginBps (INT)
--
RequiresCollateral (BIT)
RequiresPersonalGuarantee (BIT)
AllowsPrepayment (BIT)
PrepaymentPenaltyPercent (DECIMAL)
--
IsActive (BIT)
```

##### **DimLoanPurpose**
```
PurposeKey (PK)
PurposeId (Business Key)
PurposeCategory (VARCHAR) -- Working Capital, Expansion, Acquisition
PurposeName (VARCHAR)
RiskWeight (DECIMAL)
```

##### **DimCollateralType**
```
CollateralTypeKey (PK)
CollateralTypeId (Business Key)
CollateralCategory (VARCHAR) -- Real Estate, Equipment, Inventory
CollateralType (VARCHAR)
TypicalLTV (DECIMAL)
RequiresAppraisal (BIT)
AppraisalFrequencyMonths (INT)
```

#### **ORGANIZATIONAL DIMENSIONS**

##### **DimEmployee** (SCD Type 2)
```
EmployeeKey (PK)
EmployeeId (Business Key)
EmployeeName (NVARCHAR)
Email (VARCHAR)
Title (VARCHAR)
Department (VARCHAR)
Role (VARCHAR) -- Loan Officer, Underwriter, Analyst
--
HireDate (DATE)
ManagerId (FK to DimEmployee)
BranchId (FK to DimBranch)
RegionId (FK to DimRegion)
--
ProductionTarget_Annual (DECIMAL)
ProductionActual_YTD (DECIMAL)
LoanCount_Active (INT)
PortfolioSize (DECIMAL)
--
IsActive (BIT)
EffectiveDate (DATE)
EndDate (DATE)
IsCurrent (BIT)
```

##### **DimBranch** (Hierarchy)
```
BranchKey (PK)
BranchId (Business Key)
BranchName (VARCHAR)
BranchCode (VARCHAR)
BranchType (VARCHAR) -- Retail, Commercial, Private Banking
--
AddressId (FK to DimAddress)
RegionId (FK to DimRegion)
MarketId (FK to DimMarket)
--
OpenDate (DATE)
EmployeeCount (INT)
LoanVolume_YTD (DECIMAL)
--
IsActive (BIT)
```

##### **DimRegion** (Hierarchy)
```
RegionKey (PK)
RegionId (Business Key)
RegionName (VARCHAR)
RegionCode (VARCHAR)
Division (VARCHAR) -- Northeast, Southeast, Midwest, etc.
--
HeadquartersBranchId (FK to DimBranch)
RegionalVP_EmployeeId (FK to DimEmployee)
```

#### **RISK & COMPLIANCE DIMENSIONS**

##### **DimRiskRating**
```
RiskRatingKey (PK)
RiskRatingCode (VARCHAR) -- AAA, AA, A, BBB, BB, B, CCC, CC, C, D
RiskRatingName (VARCHAR)
RiskCategory (VARCHAR) -- Investment Grade, Sub-Investment Grade
NumericScore (INT) -- 1-10
PD_Probability (DECIMAL) -- Probability of Default
LGD_Probability (DECIMAL) -- Loss Given Default
RequiredProvision_Percent (DECIMAL)
```

##### **DimCreditScore**
```
CreditScoreKey (PK)
ScoreRange (VARCHAR) -- 800+, 750-799, 700-749, etc.
ScoreMin (INT)
ScoreMax (INT)
RiskCategory (VARCHAR)
ApprovalLikelihood (VARCHAR)
```

##### **DimDelinquencyStatus**
```
DelinquencyStatusKey (PK)
StatusCode (VARCHAR) -- CURRENT, DPD30, DPD60, DPD90, NPL
StatusName (VARCHAR)
MinDaysDelinquent (INT)
MaxDaysDelinquent (INT)
IsPerforming (BIT)
IsNonPerforming (BIT)
RequiresRestructuring (BIT)
```

##### **DimCovenantType**
```
CovenantTypeKey (PK)
CovenantCategory (VARCHAR) -- Financial, Affirmative, Negative
CovenantName (VARCHAR)
CovenantDescription (NVARCHAR)
TestFrequency (VARCHAR) -- Monthly, Quarterly, Annual
ThresholdType (VARCHAR) -- Minimum, Maximum, Range
DefaultSeverity (VARCHAR) -- Material, Non-Material, Technical
```

#### **TEMPORAL DIMENSIONS**

##### **DimDate** (Rich Calendar Dimension)
```
DateKey (PK) -- YYYYMMDD as INT
Date (DATE)
Year (INT)
Quarter (INT)
Month (INT)
MonthName (VARCHAR)
Week (INT)
DayOfYear (INT)
DayOfMonth (INT)
DayOfWeek (INT)
DayName (VARCHAR)
--
IsWeekend (BIT)
IsHoliday (BIT)
HolidayName (VARCHAR)
--
IsQuarterEnd (BIT)
IsYearEnd (BIT)
IsMonthEnd (BIT)
--
FiscalYear (INT)
FiscalQuarter (INT)
FiscalMonth (INT)
--
PriorDay (DATE)
PriorWeek (DATE)
PriorMonth (DATE)
PriorQuarter (DATE)
PriorYear (DATE)
```

#### **TRANSACTIONAL DIMENSIONS**

##### **DimApplicationStatus**
```
StatusKey (PK)
StatusCode (VARCHAR)
StatusName (VARCHAR)
StatusCategory (VARCHAR) -- Pending, Approved, Declined, Withdrawn
IsActive (BIT)
IsTerminal (BIT)
SortOrder (INT)
```

##### **DimPaymentMethod**
```
PaymentMethodKey (PK)
MethodCode (VARCHAR)
MethodName (VARCHAR) -- ACH, Wire, Check, Card
ProcessingFee (DECIMAL)
ProcessingDays (INT)
IsElectronic (BIT)
```

##### **DimPaymentType**
```
PaymentTypeKey (PK)
TypeCode (VARCHAR)
TypeName (VARCHAR) -- Regular, Principal Only, Interest Only, Payoff
```

##### **DimStatementType**
```
StatementTypeKey (PK)
TypeCode (VARCHAR) -- Q1, Q2, Q3, Q4, Annual, Interim
TypeName (VARCHAR)
PeriodMonths (INT)
IsAudited (BIT)
```

##### **DimInteractionType**
```
InteractionTypeKey (PK)
TypeCode (VARCHAR)
TypeName (VARCHAR) -- Initial Meeting, Follow-up, Review, Collection
Category (VARCHAR) -- Sales, Service, Collections, Compliance
```

##### **DimInteractionChannel**
```
ChannelKey (PK)
ChannelCode (VARCHAR)
ChannelName (VARCHAR) -- In-Person, Phone, Email, Video, Portal
IsFaceToFace (BIT)
```

#### **REFERENCE DIMENSIONS**

##### **DimAddress** (Shared/Reusable)
```
AddressKey (PK)
AddressLine1 (VARCHAR)
AddressLine2 (VARCHAR)
City (VARCHAR)
StateProvince (VARCHAR)
PostalCode (VARCHAR)
CountryCode (VARCHAR)
--
Latitude (DECIMAL)
Longitude (DECIMAL)
--
MSA_Code (VARCHAR) -- Metropolitan Statistical Area
County (VARCHAR)
TimeZone (VARCHAR)
```

##### **DimCurrency**
```
CurrencyKey (PK)
CurrencyCode (VARCHAR) -- USD, EUR, GBP
CurrencyName (VARCHAR)
Symbol (VARCHAR)
```

---

### **BRIDGE TABLES** (Many-to-Many)

##### **Bridge_LoanOfficer_Customer**
```
LoanOfficerId (FK)
CustomerId (FK)
RelationshipType (VARCHAR) -- Primary, Secondary, Team
AssignmentDate (DATE)
IsPrimary (BIT)
```

##### **Bridge_Loan_Collateral**
```
LoanId (FK)
CollateralId (FK)
CollateralSequence (INT)
LTV_AtOrigination (DECIMAL)
LTV_Current (DECIMAL)
```

##### **Bridge_Loan_Covenant**
```
LoanId (FK)
CovenantId (FK)
EffectiveDate (DATE)
EndDate (DATE)
IsMaterial (BIT)
```

---

## 🎬 Demo Scenarios Enabled by TERADATA-FI

### **Scenario 1: Pipeline Analytics**
*Questions the current DB cannot answer:*
```
✨ "Show me the loan application funnel by stage for Q3 2025"
✨ "What's our average time-to-decision by loan officer?"
✨ "Which industries have the highest approval rates?"
✨ "Show me pending applications over $5M with credit scores below 700"
✨ "Compare requested vs approved amounts by product type"
```

### **Scenario 2: Relationship Banking**
```
✨ "Which customers have multiple loans across different products?"
✨ "Show me VIP customers who haven't had an interaction in 90 days"
✨ "Top 10 relationship managers by total portfolio size and customer satisfaction"
✨ "Cross-sell opportunities: customers with term loans but no LOC"
```

### **Scenario 3: Credit Risk Analytics**
```
✨ "Show me the credit migration matrix for the past 12 months"
✨ "Which loans deteriorated from investment grade to sub-investment grade?"
✨ "Calculate expected loss by industry and risk rating"
✨ "Show me early warning indicators: customers with declining EBITDA and increasing debt-to-equity"
```

### **Scenario 4: Financial Performance Tracking**
```
✨ "Compare customer financials YoY for customers with loans over $10M"
✨ "Show me customers whose interest coverage ratio fell below covenant threshold"
✨ "Top 10 customers by revenue growth rate in the Technology sector"
✨ "Which customers improved their current ratio by more than 20%?"
```

### **Scenario 5: Operational Efficiency**
```
✨ "Average processing time by loan product and branch"
✨ "Loan officer productivity: applications per week and approval rate"
✨ "Which branches have the highest loan-to-deposit ratio?"
✨ "Show me underwriters with the lowest default rates in their portfolio"
```

### **Scenario 6: Delinquency & Collections**
```
✨ "Roll rate analysis: how many loans rolled from 30-day to 60-day delinquency?"
✨ "Show me the vintage analysis for 2023 originations"
✨ "Early payment behavior: which customer segments prepay most frequently?"
✨ "Recovery rates by collateral type for charged-off loans"
```

### **Scenario 7: Pricing & Profitability**
```
✨ "Average interest rate spread by risk rating and loan size"
✨ "Fee income by product type and branch for YTD"
✨ "Show me loans originated below our target rate for their risk profile"
✨ "Calculate ROE by customer segment"
```

### **Scenario 8: Compliance & Covenant Monitoring**
```
✨ "Show me all active covenant breaches with cure periods expiring this quarter"
✨ "Covenant compliance trend: test pass rate by covenant type over 24 months"
✨ "Which customers have multiple covenant waivers in the past year?"
✨ "Alert me to customers approaching covenant thresholds (within 10%)"
```

### **Scenario 9: Temporal Trends**
```
✨ "Month-over-month change in portfolio outstanding balance by product"
✨ "Quarter-over-quarter origination volume by region and industry"
✨ "Show me the cohort analysis: 2024 Q1 originations performance over time"
✨ "Rolling 12-month charge-off rate by customer segment"
```

### **Scenario 10: Competitive Intelligence**
```
✨ "Compare our average loan size and rates to industry benchmarks by segment"
✨ "Show me customer win/loss analysis by competitor"
✨ "Market share analysis: our volume vs total market by MSA"
```

---

## 📈 Data Volume Recommendations

To make demos realistic and performant:

| Table | Rows | Rationale |
|-------|------|-----------|
| DimCustomer | 5,000 | Realistic mid-sized bank commercial portfolio |
| DimEmployee | 150 | 100 loan officers, 30 underwriters, 20 analysts |
| DimBranch | 25 | Multi-state presence |
| DimLoanProduct | 15 | Diversified product suite |
| FACT_LOAN_APPLICATION | 50,000 | 3+ years of applications (high volume) |
| FACT_LOAN_ORIGINATION | 12,000 | ~24% approval rate (realistic) |
| FACT_LOAN_BALANCE_DAILY | 4.4M | 12,000 loans × 365 days (1 year history) |
| FACT_PAYMENT_TRANSACTION | 150,000 | ~12 payments/loan/year average |
| FACT_CUSTOMER_FINANCIALS | 15,000 | 5,000 customers × 3 years (quarterly) |
| FACT_COVENANT_TEST | 48,000 | 4,000 active covenants × 12 tests/year |
| FACT_CUSTOMER_INTERACTION | 100,000 | ~20 interactions/customer/year |

**Total Database Size:** ~15-20 GB (highly queryable, still realistic for demos)

---

## 🔥 Why TERADATA-FI is Superior for Demos

### **1. Complete Business Process Coverage**
- **Before:** Only post-origination tracking
- **Now:** Application → Underwriting → Origination → Servicing → Collections → Closeout

### **2. Multi-Dimensional Analysis**
- **Before:** Limited to loan-centric queries
- **Now:** Customer-centric, product-centric, employee-centric, time-series, regional, industry-specific

### **3. Rich Temporal Analytics**
- **Before:** Basic date filtering
- **Now:** Cohort analysis, vintage curves, roll rates, period-over-period comparisons, leading indicators

### **4. Real-World Complexity**
- **Before:** Simple star schema (3-4 dimensions)
- **Now:** True enterprise data warehouse (25+ dimensions, 7 facts, multiple bridges)

### **5. Storytelling Power**
- **Before:** "Show me loans"
- **Now:** "Tell me a story about our Q3 performance, customer relationships, risk trends, and operational efficiency"

### **6. Competitive Differentiation**
Your NL2SQL solution will demonstrate:
- ✅ Complex JOIN navigation (5+ tables)
- ✅ Window functions (rankings, running totals, period comparisons)
- ✅ Date arithmetic and period calculations
- ✅ Aggregations at multiple grains
- ✅ Slowly changing dimension queries
- ✅ Many-to-many relationship handling
- ✅ Hierarchical data navigation

---

## 🚀 Implementation Roadmap

### **Phase 1: Core Schema (Week 1)**
- Create all dimension tables
- Create FACT_LOAN_ORIGINATION
- Create FACT_LOAN_BALANCE_DAILY
- Seed with 3 months of data for testing

### **Phase 2: Origination Process (Week 2)**
- Add FACT_LOAN_APPLICATION
- Add employee/branch dimensions
- Seed with application funnel data

### **Phase 3: Financial Analytics (Week 3)**
- Add FACT_CUSTOMER_FINANCIALS
- Add FACT_COVENANT_TEST
- Seed with quarterly statements

### **Phase 4: CRM & Interactions (Week 4)**
- Add FACT_CUSTOMER_INTERACTION
- Add FACT_PAYMENT_TRANSACTION
- Full data seeding (3 years historical)

### **Phase 5: Views & Optimization (Week 5)**
- Create materialized views for common queries
- Add indexes for performance
- Generate demo question bank (200+ questions)

---

## 📝 Next Steps

1. **Review & Approve** this schema design
2. **Generate DDL scripts** for all tables
3. **Create data generation scripts** (Python/SQL)
4. **Build seeding profiles** with realistic distributions
5. **Create migration scripts** from CONTOSO-FI (if needed)
6. **Generate comprehensive demo question bank**
7. **Update NL2SQL app** to point to TERADATA-FI
8. **Performance testing** with complex queries

---

## 💡 Bonus: Advanced Features

### **Slowly Changing Dimensions (SCD Type 2)**
Track historical changes to customer attributes:
```sql
SELECT 
    c.CompanyName,
    c.CreditRating_SP,
    c.EffectiveDate,
    c.EndDate,
    c.IsCurrent
FROM DimCustomer c
WHERE c.CustomerId = 'CUST-001'
ORDER BY c.EffectiveDate;
```

### **Time-Series Window Functions**
```sql
-- 3-month rolling average of originations
SELECT 
    d.MonthName,
    COUNT(l.LoanId) AS OriginationCount,
    AVG(COUNT(l.LoanId)) OVER (
        ORDER BY d.DateKey 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS RollingAvg_3Month
FROM FACT_LOAN_ORIGINATION l
JOIN DimDate d ON l.OriginationDate = d.DateKey
GROUP BY d.Year, d.Month, d.MonthName, d.DateKey
ORDER BY d.DateKey;
```

### **Cohort Analysis**
```sql
-- Vintage analysis by origination quarter
SELECT 
    dOrig.FiscalYear AS OriginationYear,
    dOrig.FiscalQuarter AS OriginationQuarter,
    dSnap.Year AS PerformanceYear,
    AVG(b.DaysDelinquent) AS AvgDelinquency,
    SUM(CASE WHEN ds.IsNonPerforming = 1 THEN 1 ELSE 0 END) AS NPL_Count
FROM FACT_LOAN_BALANCE_DAILY b
JOIN DimDate dOrig ON b.LoanId = l.LoanId
JOIN DimDate dSnap ON b.SnapshotDate = dSnap.DateKey
JOIN DimDelinquencyStatus ds ON b.DelinquencyStatusId = ds.DelinquencyStatusKey
GROUP BY dOrig.FiscalYear, dOrig.FiscalQuarter, dSnap.Year
ORDER BY 1, 2, 3;
```

---

**Ready to build the most comprehensive commercial lending demo database in the market?** 🎯

