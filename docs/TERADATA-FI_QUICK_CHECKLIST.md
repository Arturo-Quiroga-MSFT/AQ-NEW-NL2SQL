# TERADATA-FI Quick Deployment Checklist
## ⏱️ Time Estimate: 2-4 Hours | Difficulty: ⭐⭐☆☆☆

---

## 📋 Pre-Flight Checklist
- [ ] Azure SQL Database access confirmed
- [ ] SQL Server Management Studio or Azure Data Studio installed
- [ ] Python 3.8+ installed
- [ ] ODBC Driver 18 for SQL Server installed (`brew install msodbcsql18` on macOS)
- [ ] Azure SQL credentials ready (server, username, password)

---

## 🚀 Phase 1 Deployment (2-4 hours)

### Step 1: Create Database & Dimensions (⏱️ 5 minutes)
```bash
# Open Azure Data Studio or SSMS
# Connect to: aqsqlserver001.database.windows.net
# Execute: DATABASE_SETUP/teradata_fi_phase1_dimensions.sql
```
**Validation**: 
- [ ] Database `TERADATA-FI` created
- [ ] Schemas created: `dim`, `fact`, `bridge`, `ref`
- [ ] 20+ dimension tables created
- [ ] No SQL errors

### Step 2: Create Fact Tables (⏱️ 3 minutes)
```bash
# In same session, execute: DATABASE_SETUP/teradata_fi_phase1_facts.sql
```
**Validation**:
- [ ] 7 fact tables created
- [ ] 3 bridge tables created
- [ ] All foreign key constraints applied
- [ ] No SQL errors

### Step 3: Setup Python Environment (⏱️ 10 minutes)
```bash
# Install dependencies
pip install pyodbc faker

# Test ODBC driver
python -c "import pyodbc; print('✓ pyodbc working')"
```
**Validation**:
- [ ] `pyodbc` imports successfully
- [ ] `faker` imports successfully
- [ ] No import errors

### Step 4: Configure Data Generation Script (⏱️ 5 minutes)
```bash
# Edit: DATABASE_SETUP/generate_teradata_fi_data.py
# Update lines 18-26 with your credentials:

CONNECTION_STRING = """
    DRIVER={ODBC Driver 18 for SQL Server};
    SERVER=aqsqlserver001.database.windows.net;
    DATABASE=TERADATA-FI;
    UID=your_username_here;
    PWD=your_password_here;
    Encrypt=yes;
"""
```
**Validation**:
- [ ] Server name correct
- [ ] Database name = `TERADATA-FI`
- [ ] Username correct
- [ ] Password correct

### Step 5: Generate Dimension Data (⏱️ 30-60 minutes)
```bash
cd DATABASE_SETUP
python generate_teradata_fi_data.py
```
**Expected Output**:
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
**Validation**:
- [ ] Script completes without errors
- [ ] All 5 dimension types generated
- [ ] Success message displayed

### Step 6: Validate Setup (⏱️ 10 minutes)
```bash
# Execute: DATABASE_SETUP/teradata_fi_sample_queries.sql
# Run Query Q17 (record counts):
```
```sql
SELECT 'DimDate' AS Dimension, COUNT(*) AS RecordCount FROM dim.DimDate
UNION ALL
SELECT 'DimCustomer', COUNT(*) FROM dim.DimCustomer WHERE IsCurrent = 1
UNION ALL
SELECT 'DimIndustry', COUNT(*) FROM dim.DimIndustry
UNION ALL
SELECT 'DimLoanProduct', COUNT(*) FROM dim.DimLoanProduct
UNION ALL
SELECT 'DimRiskRating', COUNT(*) FROM dim.DimRiskRating;
```
**Expected Results**:
- [ ] DimDate: ~1,461 records
- [ ] DimCustomer: 5,000 records
- [ ] DimIndustry: 10 records
- [ ] DimLoanProduct: 8 records
- [ ] DimRiskRating: 10 records

### Step 7: Test Sample Queries (⏱️ 10 minutes)
Run these queries from `teradata_fi_sample_queries.sql`:
- [ ] **Q1**: Customer segmentation (should return ~10 rows)
- [ ] **Q4**: Industry risk profiles (should return 10 rows)
- [ ] **Q6**: Product catalog (should return 8 rows)
- [ ] **Q10**: Fiscal calendar mapping (should return ~90 rows)
- [ ] **Q15**: Multi-dimensional joins (should return data)

**Validation**: All queries execute in <1 second with no errors

---

## ✅ Phase 1 Success Criteria

You've successfully deployed TERADATA-FI Phase 1 if:
1. ✅ Database `TERADATA-FI` exists with 4 schemas
2. ✅ 20+ dimension tables + 7 fact tables created
3. ✅ 1,461 date records spanning 2022-2025
4. ✅ 5,000 realistic customer records with segments/tiers/ratings
5. ✅ 10 industries with SIC/NAICS codes and risk metrics
6. ✅ 8 loan products covering all major types
7. ✅ 10 risk ratings (AAA to D) with PD/LGD probabilities
8. ✅ All 20 sample queries execute successfully
9. ✅ No SQL errors or foreign key violations
10. ✅ Query performance <1 second for dimension queries

---

## 🎯 What You Can Demo NOW (Phase 1 Only)

Even without fact data, you can demonstrate:
- ✅ **Customer Segmentation Analysis** (Q1-Q3)
- ✅ **Industry Risk Profiling** (Q4-Q5)
- ✅ **Product Catalog Queries** (Q6-Q7)
- ✅ **Risk Rating Framework** (Q8-Q9)
- ✅ **Fiscal Calendar Analysis** (Q10-Q11)
- ✅ **Multi-Dimensional Joins** (Q15-Q16)
- ✅ **Star Schema Design** (show ER diagram)

**Demo Script**: "Our database covers 5,000 commercial lending customers across 10 industries, with 8 loan products and a sophisticated risk rating framework. Watch how easily we can answer complex questions about customer segmentation, industry risk profiles, and product features..."

---

## 📊 Quick Stats (Phase 1)

| Metric | Count |
|--------|-------|
| **Database Size** | ~50 MB |
| **Tables** | 30+ |
| **Dimension Records** | ~6,500 |
| **Date Range** | 2022-2025 (4 years) |
| **Customers** | 5,000 |
| **Industries** | 10 |
| **Products** | 8 |
| **Risk Ratings** | 10 |
| **Sample Queries** | 20 |
| **Query Performance** | <1s |

---

## 🚀 Next: Phase 2 (Optional, +4-6 hours)

**Ready to add fact data?**
Phase 2 will generate:
- 50,000 loan applications
- 12,000 originated loans
- 4.4M daily balance snapshots
- 150,000 payment transactions
- 15,000 financial statements
- 100,000 customer interactions

**Decision Point**: 
- **Yes, continue to Phase 2**: Unlock 500+ demo questions, full lifecycle analytics
- **No, validate Phase 1 first**: Test NL2SQL app with dimension-only queries, get stakeholder buy-in

---

## 🔧 Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| **"Login failed"** | Check Azure SQL firewall settings, add your IP |
| **"Driver not found"** | Install ODBC Driver 18: `brew install msodbcsql18` |
| **"Database exists"** | Drop and recreate, or comment out CREATE DATABASE line |
| **"FK constraint error"** | Ensure dimensions loaded before facts |
| **"Script slow"** | Normal for Azure SQL, be patient (5-10 min for 5K customers) |
| **"Query timeout"** | Increase connection timeout in script |

---

## 📞 Support Resources

| Document | Purpose | Location |
|----------|---------|----------|
| **Implementation Guide** | Step-by-step instructions | `docs/TERADATA-FI_IMPLEMENTATION_GUIDE.md` |
| **Schema Proposal** | Complete table definitions | `docs/TERADATA-FI_PROPOSAL.md` |
| **Capability Comparison** | ROI analysis | `docs/TERADATA-FI_VS_CONTOSO-FI.md` |
| **ER Diagram** | Visual schema | `docs/diagrams/teradata_fi_star_schema.mmd` |
| **Sample Queries** | Test/demo queries | `DATABASE_SETUP/teradata_fi_sample_queries.sql` |

---

## ✨ Congratulations!

After completing this checklist, you'll have:
- 🎉 A production-ready star schema database
- 🎉 5,000 realistic customer records
- 🎉 Complete dimensional framework
- 🎉 20 working demo queries
- 🎉 Foundation for 500+ advanced queries (Phase 2)
- 🎉 10x improvement over CONTOSO-FI

**Time to celebrate and show your stakeholders!** 🚀

---

**Print this checklist** and check off items as you complete them!

**Stuck?** Review the Implementation Guide or Schema Proposal documents for detailed explanations.

**Ready to start?** Open Azure Data Studio and execute `teradata_fi_phase1_dimensions.sql` now! ⚡
