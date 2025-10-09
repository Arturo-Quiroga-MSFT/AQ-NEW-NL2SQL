# TERADATA-FI Implementation Guide
## Phase 1: Core Schema & Initial Data

**Status**: Ready for Execution  
**Estimated Time**: 2-4 hours  
**Prerequisites**: Azure SQL Database access, Python 3.8+, ODBC Driver 18 for SQL Server

---

## 📋 Quick Start Checklist

### 1️⃣ **Database Creation** (5 minutes)
- [ ] Connect to Azure SQL Server via Azure Portal or SQL Server Management Studio (SSMS)
- [ ] Run: `DATABASE_SETUP/teradata_fi_phase1_dimensions.sql`
- [ ] Verify: Database `TERADATA-FI` created with 4 schemas (dim, fact, bridge, ref)
- [ ] Verify: 20+ dimension tables created successfully

### 2️⃣ **Fact Tables Creation** (3 minutes)
- [ ] Run: `DATABASE_SETUP/teradata_fi_phase1_facts.sql`
- [ ] Verify: 7 fact tables created in `fact` schema
- [ ] Verify: 3 bridge tables created in `bridge` schema
- [ ] Verify: All foreign key constraints applied successfully

### 3️⃣ **Data Generation Setup** (10 minutes)
- [ ] Install Python dependencies:
  ```bash
  pip install pyodbc faker
  ```
- [ ] Update connection string in `DATABASE_SETUP/generate_teradata_fi_data.py`:
  ```python
  CONNECTION_STRING = """
      DRIVER={ODBC Driver 18 for SQL Server};
      SERVER=aqsqlserver001.database.windows.net;
      DATABASE=TERADATA-FI;
      UID=your_actual_username;
      PWD=your_actual_password;
      Encrypt=yes;
  """
  ```
- [ ] Test connection:
  ```bash
  python -c "import pyodbc; print('✓ pyodbc working')"
  ```

### 4️⃣ **Run Data Generation** (30-60 minutes)
- [ ] Execute seeding script:
  ```bash
  python DATABASE_SETUP/generate_teradata_fi_data.py
  ```
- [ ] Monitor progress (script will print status for each dimension)
- [ ] Expected output:
  ```
  ✓ Connected to database
  Generating DimDate...
    ✓ Generated 1461 date records
  Generating DimIndustry...
    ✓ Generated 10 industry records
  Generating DimLoanProduct...
    ✓ Generated 8 product records
  Generating reference dimensions...
    ✓ Generated reference dimension records
  Generating DimCustomer (5000 records)...
    ✓ Generated 5000 customer records
  Phase 1 Data Generation Complete!
  ```

### 5️⃣ **Validation Queries** (10 minutes)
Run these queries in Azure Data Studio or SSMS to verify data:

```sql
USE [TERADATA-FI];
GO

-- Check dimension record counts
SELECT 'DimDate' AS TableName, COUNT(*) AS RecordCount FROM dim.DimDate
UNION ALL
SELECT 'DimCustomer', COUNT(*) FROM dim.DimCustomer
UNION ALL
SELECT 'DimIndustry', COUNT(*) FROM dim.DimIndustry
UNION ALL
SELECT 'DimLoanProduct', COUNT(*) FROM dim.DimLoanProduct
UNION ALL
SELECT 'DimRiskRating', COUNT(*) FROM dim.DimRiskRating
UNION ALL
SELECT 'DimDelinquencyStatus', COUNT(*) FROM dim.DimDelinquencyStatus
UNION ALL
SELECT 'DimApplicationStatus', COUNT(*) FROM dim.DimApplicationStatus
UNION ALL
SELECT 'DimPaymentMethod', COUNT(*) FROM dim.DimPaymentMethod
UNION ALL
SELECT 'DimPaymentType', COUNT(*) FROM dim.DimPaymentType;

-- Expected Results:
-- DimDate: ~1,461 records (2022-01-01 to 2025-12-31)
-- DimCustomer: 5,000 records
-- DimIndustry: 10 records
-- DimLoanProduct: 8 records
-- DimRiskRating: 10 records
-- DimDelinquencyStatus: 6 records
-- DimApplicationStatus: 6 records
-- DimPaymentMethod: 4 records
-- DimPaymentType: 4 records
```

```sql
-- Sample customer distribution by segment
SELECT CustomerSegment, CustomerTier, COUNT(*) AS CustomerCount
FROM dim.DimCustomer
WHERE IsCurrent = 1
GROUP BY CustomerSegment, CustomerTier
ORDER BY CustomerSegment, CustomerTier;

-- Expected: 60% Small Business, 30% Middle Market, 10% Corporate
-- Tier breakdown: 50% Bronze, 30% Silver, 15% Gold, 5% Platinum
```

```sql
-- Sample date dimension with fiscal calendar
SELECT TOP 10 DateKey, [Date], [Year], Quarter, FiscalYear, FiscalQuarter, DayName, IsWeekend
FROM dim.DimDate
ORDER BY [Date] DESC;

-- Verify: Fiscal year calculations correct (Oct 1 - Sep 30)
```

---

## 🚀 What You've Built (Phase 1)

### ✅ Complete Star Schema Foundation
- **20+ Dimension Tables** with proper indexing and SCD Type 2 support
- **7 Fact Tables** covering complete commercial lending lifecycle
- **3 Bridge Tables** for many-to-many relationships
- **Foreign Key Constraints** ensuring referential integrity

### ✅ Data Seeded
- **1,461 Date Records** (4 years: 2022-2025)
- **5,000 Customers** with realistic company profiles, segments, tiers
- **10 Industries** with SIC/NAICS codes, risk profiles
- **8 Loan Products** (Term Loans, Revolvers, SBA, CRE, Equipment, etc.)
- **10 Risk Ratings** (AAA to D) with PD/LGD probabilities
- **Reference Data** (Delinquency statuses, payment methods, application statuses)

### 📊 Schema Highlights

#### **Fact Tables (Ready for Data)**
1. **FACT_LOAN_ORIGINATION** - All originated loans with performance metrics
2. **FACT_LOAN_APPLICATION** - Application funnel tracking (conversion analysis)
3. **FACT_LOAN_BALANCE_DAILY** - Daily balance snapshots (trend analysis, cohort tracking)
4. **FACT_PAYMENT_TRANSACTION** - Every payment recorded (cash flow analysis)
5. **FACT_CUSTOMER_FINANCIALS** - Quarterly/annual financial statements (credit analysis)
6. **FACT_COVENANT_TEST** - Covenant compliance testing (risk monitoring)
7. **FACT_CUSTOMER_INTERACTION** - CRM interactions (relationship tracking)

#### **Key Dimensions (Partially Seeded)**
- ✅ **DimDate** - Complete temporal dimension with fiscal calendar
- ✅ **DimCustomer** - SCD Type 2 with customer segments, tiers, risk ratings
- ✅ **DimIndustry** - Industry classification with risk profiles
- ✅ **DimLoanProduct** - Product catalog with terms, rates, requirements
- ⏳ **DimEmployee** - *Next Phase* (loan officers, underwriters, managers)
- ⏳ **DimBranch** - *Next Phase* (25 branches across regions)
- ⏳ **DimRegion** - *Next Phase* (5 regions, divisional structure)

---

## 🎯 Phase 2 Preview: Fact Table Data Generation

**Coming Next** (Ready to implement after Phase 1 validation):

### Phase 2A: Loan Origination & Application Data
- Generate **50,000 applications** (2022-2025)
- Generate **12,000 originated loans** (24% approval rate)
- Application statuses: 24% approved, 45% declined, 20% withdrawn, 11% expired
- Loan distribution: 60% Term Loans, 20% Revolvers, 10% SBA, 10% Other
- Amount range: $50K - $25M (realistic distribution by product type)

### Phase 2B: Daily Balance Snapshots
- Generate **4.4M daily balance records** (12,000 loans × ~365 days)
- Track principal/interest balances over time
- Delinquency status changes (95% current, 3% DPD30, 1.5% DPD60, 0.5% NPL)
- CECL allowance calculations
- Performance metrics (NPV, IRR, Yield)

### Phase 2C: Payment Transactions
- Generate **150,000 payment transactions**
- Scheduled payments, prepayments, late payments
- Payment methods: 70% ACH, 20% Wire, 8% Check, 2% Debit
- Realistic payment patterns (quarterly, monthly, irregular)

### Phase 2D: Customer Financials & CRM
- **15,000 financial statements** (quarterly for 3 years)
- Income statement, balance sheet, cash flow
- Financial ratios (DSCR, Debt/Equity, Current Ratio, etc.)
- **100,000 customer interactions** (sales, service, collections)

**Estimated Time for Phase 2**: 4-6 hours (including testing)

---

## 🔧 Troubleshooting

### Common Issues

**Issue**: `pyodbc.Error: ('IM002', '[IM002] [Microsoft][ODBC Driver Manager] Data source name not found...')`  
**Solution**: Install ODBC Driver 18 for SQL Server:
- **macOS**: `brew install msodbcsql18`
- **Windows**: Download from Microsoft
- **Linux**: `sudo apt-get install msodbcsql18`

**Issue**: `pyodbc.Error: Login failed for user`  
**Solution**: Verify Azure SQL firewall allows your IP address. Check Azure Portal → SQL Server → Firewalls and virtual networks.

**Issue**: `Database 'TERADATA-FI' does not exist`  
**Solution**: The DDL script creates the database automatically. Ensure you have `CREATE DATABASE` permissions on the server.

**Issue**: Data generation script runs slowly  
**Solution**: Script uses batch inserts (500-1000 records per batch). For 5,000 customers, expect 2-5 minutes depending on network latency to Azure.

**Issue**: Foreign key constraint errors  
**Solution**: Dimension tables must be populated before fact tables. Always run dimension seeding first.

---

## 📈 Performance Benchmarks

### Expected Query Performance (Phase 1 Schema, 5K Customers)
- Simple dimension queries: < 100ms
- Customer segmentation analysis: < 500ms
- Date range queries: < 200ms
- SCD Type 2 historical queries: < 1s

### Expected Query Performance (After Phase 2, Full Dataset)
- 8-table joins (Customer→Loan→Payment→Product→Branch): < 3s
- Daily balance trend analysis (1 year, 12K loans): < 5s
- Cohort analysis (vintage curves, 3 years): < 8s
- Covenant compliance dashboard (all loans, current): < 2s

**Target**: 95% of queries under 3 seconds with proper indexing

---

## 📝 Next Steps Recommendation

After completing Phase 1:

1. **Validate Schema** - Run all validation queries above
2. **Test Sample Queries** - Try joining Customer → Product → Industry
3. **Review Performance** - Check query execution plans for dimension queries
4. **Proceed to Phase 2A** - Generate application and origination fact data
5. **Build Demo Question Bank** - Start drafting NL2SQL questions for completed dimensions

**Decision Point**: Once Phase 1 validated successfully, you have two options:
- **Option A**: Continue to Phase 2 (generate all fact data, 4-6 hours)
- **Option B**: Connect NL2SQL app to TERADATA-FI now, test dimension-only queries

**Recommended**: Validate Phase 1, then proceed to Phase 2A (applications + originations) for meaningful demo capability.

---

## 📞 Support

**Files Created**:
- `teradata_fi_phase1_dimensions.sql` - DDL for 20+ dimension tables
- `teradata_fi_phase1_facts.sql` - DDL for 7 fact tables, 3 bridge tables, FK constraints
- `generate_teradata_fi_data.py` - Python script for dimension data generation

**Documentation References**:
- `docs/TERADATA-FI_PROPOSAL.md` - Complete schema design and rationale
- `docs/TERADATA-FI_VS_CONTOSO-FI.md` - Capability comparison and ROI analysis
- `docs/diagrams/teradata_fi_star_schema.mmd` - Visual ER diagram

**Estimated Total Time**: 2-4 hours for Phase 1 (schema + initial data)

---

**Ready to begin? Start with the Quick Start Checklist above!** ✅
