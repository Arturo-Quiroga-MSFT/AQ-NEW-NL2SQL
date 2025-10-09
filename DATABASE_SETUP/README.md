# Database Setup - CONTOSO-FI & TERADATA-FI

This folder contains database setup scripts for both **CONTOSO-FI** (legacy) and **TERADATA-FI** (new comprehensive demo database).

---

## 🚀 Quick Start: TERADATA-FI (Recommended for New Demos)

### What is TERADATA-FI?
A comprehensive commercial lending database with **star schema design**, covering the complete loan lifecycle from application through servicing. Enables 500+ demo questions vs 50 with CONTOSO-FI.

### Files for TERADATA-FI Setup
1. **`teradata_fi_phase1_dimensions.sql`** - Creates database, schemas, and 20+ dimension tables
2. **`teradata_fi_phase1_facts.sql`** - Creates 7 fact tables and bridge tables with FK constraints
3. **`generate_teradata_fi_data.py`** - Python script to seed dimension data (5,000 customers, dates, products, industries)
4. **`teradata_fi_sample_queries.sql`** - 20 demo queries to validate the schema and explore data

### Complete Setup Guide
See **`../docs/TERADATA-FI_IMPLEMENTATION_GUIDE.md`** for full step-by-step instructions.

### Quick Setup (2-4 hours)
```bash
# 1. Run DDL scripts in Azure Data Studio or SSMS
# Execute: teradata_fi_phase1_dimensions.sql
# Execute: teradata_fi_phase1_facts.sql

# 2. Install Python dependencies
pip install pyodbc faker

# 3. Update connection string in generate_teradata_fi_data.py
# Edit lines 18-26 with your Azure SQL credentials

# 4. Run data generation
python generate_teradata_fi_data.py

# 5. Validate with sample queries
# Execute: teradata_fi_sample_queries.sql
```

### What You Get (Phase 1)
- ✅ **1,461 date records** (2022-2025 with fiscal calendar)
- ✅ **5,000 customers** (segments: Small Business, Middle Market, Corporate)
- ✅ **10 industries** (with SIC/NAICS codes, risk profiles)
- ✅ **8 loan products** (Term Loans, Revolvers, SBA, CRE, Equipment)
- ✅ **Complete star schema** (7 fact tables, 20+ dimensions, ready for Phase 2 data)

### Phase 2 (Coming Next)
- 50,000 loan applications
- 12,000 originated loans
- 4.4M daily balance snapshots
- 150,000 payment transactions
- 15,000 financial statements
- 100,000 CRM interactions

---

## 📚 Reference Documentation
- **`../docs/TERADATA-FI_PROPOSAL.md`** - Complete schema design with all table definitions
- **`../docs/TERADATA-FI_VS_CONTOSO-FI.md`** - Feature comparison and ROI analysis
- **`../docs/diagrams/teradata_fi_star_schema.mmd`** - Visual ER diagram
- **`../docs/TERADATA-FI_IMPLEMENTATION_GUIDE.md`** - Step-by-step setup instructions

---

## 🔧 Legacy: CONTOSO-FI Database Migrations

The original CONTOSO-FI database uses a migration-based approach for schema evolution.

### What's here
- `migrations/` — ordered, idempotent `.sql` files. Apply in lexical order.
- `run_migrations.py` — applies all or one migration using pyodbc.
- `contoso_fi_extensions.sql` - Additional schema enhancements
- `seed_new_companies_loans.sql` - Sample data seeding

### Prereqs
- Microsoft ODBC Driver 18 for SQL Server installed on your machine.
- Python dependencies installed (pyodbc, python-dotenv), e.g. from the repo `requirements.txt`.
- Environment variables (in shell or a `.env` file at repo root or this folder):
  - `AZURE_SQL_SERVER` (e.g., `myserver.database.windows.net`)
  - `AZURE_SQL_DATABASE` (e.g., `CONTOSO-FI`)
  - `AZURE_SQL_USERNAME`
  - `AZURE_SQL_PASSWORD`

### Apply migrations
```bash
# Dry run (list planned files):
python run_migrations.py --dry-run

# Apply all:
python run_migrations.py

# Apply a single migration by prefix:
python run_migrations.py --one 001
```

Migrations should be idempotent (use `IF NOT EXISTS` guards) so re-running is safe.

### After applying
Refresh the NL2SQL schema cache so the pipeline sees new tables/columns:
```bash
python ../schema_reader.py --cache --print
```

### Notes
- If you hit login/driver errors, verify ODBC Driver 18 is installed and the four env vars are set.
- If using Azure AD, adjust `run_migrations.py` connection code accordingly or provide a SQL user for simplicity.

---

## 🔄 Migration Strategy: CONTOSO-FI → TERADATA-FI

**Current Recommendation**: Build TERADATA-FI as a **parallel database** on the same Azure SQL Server.

### Option A: Parallel Deployment (Recommended)
1. Keep CONTOSO-FI running for existing demos
2. Deploy TERADATA-FI alongside it (different database, same server)
3. Gradually transition demo questions to TERADATA-FI
4. Retire CONTOSO-FI once TERADATA-FI proven stable

### Option B: Direct Replacement
1. Build TERADATA-FI on a dev/test server
2. Validate with full demo question bank
3. Replace CONTOSO-FI in production
4. Update NL2SQL app connection string

### Decision Factors
- **Demo Schedule**: Parallel deployment allows immediate use without disrupting existing demos
- **Data Migration**: TERADATA-FI is clean slate, no data migration needed from CONTOSO-FI
- **Risk Tolerance**: Parallel deployment = zero downtime, full rollback capability

---

## 📊 Database Comparison

| Feature | CONTOSO-FI | TERADATA-FI |
|---------|------------|-------------|
| **Schema Design** | Transactional (OLTP) | Star Schema (OLAP) |
| **Tables** | 22 tables | 30+ tables (7 facts, 20+ dims) |
| **Business Processes** | Post-origination only | Complete lifecycle |
| **Demo Questions** | ~50 questions | 500+ questions |
| **Query Complexity** | 2-3 table joins | 8+ table joins, window functions |
| **Temporal Analytics** | Limited | Full (SCD Type 2, vintage curves) |
| **CRM Tracking** | None | Full interaction history |
| **Financial Analytics** | None | P&L, Balance Sheet, Cash Flow |
| **Application Funnel** | None | Complete (50K applications) |
| **Daily Snapshots** | None | 4.4M balance snapshots |

**Recommendation**: Use TERADATA-FI for new demos, complex analytics, C-suite presentations.

---

## 🎯 Next Steps

### If Starting Fresh
1. Follow TERADATA-FI setup guide (2-4 hours)
2. Complete Phase 1 (dimensions + initial data)
3. Proceed to Phase 2 (fact table data generation)
4. Connect NL2SQL app to TERADATA-FI
5. Generate 500+ demo questions

### If Using CONTOSO-FI Today
1. Review `../docs/TERADATA-FI_VS_CONTOSO-FI.md` for ROI analysis
2. Build TERADATA-FI in parallel (Option A)
3. Test critical demo scenarios on TERADATA-FI
4. Plan transition timeline (recommend 2-4 weeks)
5. Update NL2SQL app to support both databases

### Support
- Technical questions: Review implementation guide
- Schema design questions: Review proposal document
- Data generation issues: Check Python script comments
- Query examples: Review sample queries SQL file

**Ready to build TERADATA-FI? Start with the Quick Setup above!** ✅