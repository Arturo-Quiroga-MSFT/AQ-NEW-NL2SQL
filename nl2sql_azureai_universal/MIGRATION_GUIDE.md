# Migration Guide: From CONTOSO-FI Specific to Universal

## Overview

This document explains the changes made to convert `nl2sql_standalone_AzureAI` (CONTOSO-FI specific) to `nl2sql_azureai_universal` (works with any Azure SQL database).

## Key Changes

### 1. Schema Reader (`schema_reader.py`)

#### **Hardcoded References Removed:**

**Before:**
```python
"""
Dynamic schema context provider for CONTOSO-FI used by the NL2SQL-only pipeline
"""

lines.append("DATABASE: CONTOSO-FI (Azure SQL)\n")

# Hardcoded guidance about specific views
lines.append("IMPORTANT SQL GENERATION NOTES:\n")
lines.append("- If the question involves 'portfolio' or 'loan details', consider using dbo.vw_LoanPortfolio\n")
lines.append("VIEWS:\n")
lines.append("- dbo.vw_LoanPortfolio: Pre-joined loan, customer, product, officer details; includes LoanID, CustomerName, ProductName, OfficerName, LoanAmount, OutstandingBalance, Status, OriginationDate, MaturityDate\n")
```

**After:**
```python
"""
Universal dynamic schema context provider for Azure SQL databases.
"""

db_name = meta.get("database_name", "Unknown")
lines.append(f"DATABASE: {db_name} on {server}\n")

# Generic guidance
lines.append("SQL GENERATION GUIDELINES:\n")
lines.append("- Generate T-SQL compatible with Azure SQL Database\n")
lines.append("- Use schema-qualified table names (e.g., schema.TableName)\n")
lines.append("- Use appropriate JOINs based on foreign key relationships\n")
# ... more generic guidelines
```

#### **Dynamic Database Name:**

The database name is now read from `AZURE_SQL_DB` environment variable and injected into the schema context string, rather than being hardcoded.

#### **Generic View Discovery:**

Instead of documenting specific views like `dbo.vw_LoanPortfolio`, the code now:
1. Discovers ALL views dynamically from `INFORMATION_SCHEMA.TABLES`
2. Lists them with their columns
3. Provides generic guidance about using views

### 2. Main Pipeline (`nl2sql_main.py`)

**No changes needed!** 

The original `nl2sql_main.py` was already database-agnostic:
- ✅ No hardcoded database names
- ✅ Uses `schema_reader` module dynamically
- ✅ Environment variable based configuration
- ✅ Generic SQL generation logic

### 3. SQL Executor (`sql_executor.py`)

**No changes needed!**

Already uses environment variables:
```python
AZURE_SQL_SERVER = os.getenv("AZURE_SQL_SERVER")
AZURE_SQL_DB = os.getenv("AZURE_SQL_DB")
AZURE_SQL_USER = os.getenv("AZURE_SQL_USER")
AZURE_SQL_PASSWORD = os.getenv("AZURE_SQL_PASSWORD")
```

### 4. Configuration Files

#### **New: `.env.example`**

Provides template for environment variables with clear documentation:
```bash
PROJECT_ENDPOINT=https://your-project-name.cognitiveservices.azure.com/
MODEL_DEPLOYMENT_NAME=gpt-4o
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DB=your-database-name
AZURE_SQL_USER=your-username
AZURE_SQL_PASSWORD=your-password
```

#### **New: `.gitignore`**

Ensures sensitive files are not committed:
- `.env` (credentials)
- `schema_cache.json` (database-specific)
- `RESULTS/` (query outputs)

### 5. Documentation

#### **Enhanced README.md**

New sections:
- Database-agnostic architecture explanation
- Environment variable configuration
- Schema discovery process
- Multi-database support examples

#### **New: QUICKSTART.md**

Step-by-step guide for:
- Setting up for TERADATA-FI (or any database)
- Running test_setup.py
- Refreshing schema cache
- Running first queries
- Troubleshooting common issues

#### **New: test_setup.py**

Validation script that checks:
- Environment variables are set
- Azure SQL connection works
- Schema can be discovered
- Azure AI Foundry connection works

## Architectural Improvements

### Schema Discovery is Already Universal

The original implementation already had excellent schema discovery:

```python
# Queries INFORMATION_SCHEMA - works with ANY database
cur.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')
      AND TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA')
    ORDER BY TABLE_SCHEMA, TABLE_NAME
""")

# Discovers foreign keys dynamically
cur.execute("""
    SELECT 
      fk.name AS ConstraintName,
      tp_s.name AS ParentSchema,
      tp.name AS ParentTable,
      cp.name AS ParentColumn,
      tr_s.name AS RefSchema,
      tr.name AS RefTable,
      cr.name AS RefColumn
    FROM sys.foreign_keys fk
    INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
    -- ... (discovers ALL relationships)
""")
```

**This means:**
- Switching databases is as simple as changing `.env`
- No code changes needed
- Schema structure is discovered automatically
- Foreign key relationships are detected
- Views are found and documented

### What Makes it "Universal"

| Aspect | Original | Universal | Impact |
|--------|----------|-----------|---------|
| Database name in schema context | Hardcoded "CONTOSO-FI" | Dynamic from `AZURE_SQL_DB` | LLM knows actual database name |
| View guidance | Hardcoded `dbo.vw_LoanPortfolio` | Generic + dynamic discovery | Works with any view structure |
| Documentation | CONTOSO-FI specific | Generic examples | Clear for any database |
| Schema cache location | Same | Same | Portable |
| Connection logic | Environment based | Environment based | Already flexible |
| SQL generation | Generic T-SQL | Generic T-SQL | Already universal |

## Usage Examples

### Switching from CONTOSO-FI to TERADATA-FI

**Step 1: Update `.env`**
```bash
# Before (CONTOSO-FI)
AZURE_SQL_DB=CONTOSO-FI

# After (TERADATA-FI)
AZURE_SQL_DB=TERADATA-FI
```

**Step 2: Refresh schema**
```bash
python nl2sql_main.py --refresh-schema --query "How many loans?"
```

**That's it!** The app now understands TERADATA-FI structure and generates appropriate SQL.

### Supporting Multiple Databases

Create separate `.env` files:

```bash
# .env.contoso
AZURE_SQL_DB=CONTOSO-FI
# ... other vars

# .env.teradata
AZURE_SQL_DB=TERADATA-FI
# ... other vars

# Switch databases
cp .env.teradata .env
python nl2sql_main.py --refresh-schema
```

Or use environment variable override:
```bash
AZURE_SQL_DB=TERADATA-FI python nl2sql_main.py --query "your question"
```

## Testing Strategy

### 1. Validate Setup
```bash
python test_setup.py
```

### 2. Test Schema Discovery
```bash
# List all tables
python schema_reader.py --list-tables

# List all views
python schema_reader.py --list-views

# Check specific table
python schema_reader.py --table fact.LoanApplications

# View full schema context
python schema_reader.py --print
```

### 3. Test Simple Queries
```bash
# Count query
python nl2sql_main.py --query "How many tables are in the database?"

# Single table query
python nl2sql_main.py --query "Show me the first 10 records from dim.Customers"
```

### 4. Test Complex Queries
```bash
# Multi-table join
python nl2sql_main.py --query "Show customer names with their loan amounts"

# Aggregation
python nl2sql_main.py --query "What is the total loan balance by product type?"

# Filtering
python nl2sql_main.py --query "Which loans were originated in 2024?"
```

### 5. Test Edge Cases
```bash
# Non-existent table
python nl2sql_main.py --query "Show me data from TableThatDoesntExist"

# Ambiguous query
python nl2sql_main.py --query "Show me everything"

# Invalid filter
python nl2sql_main.py --query "Show loans where status is InvalidStatus"
```

## Benefits of Universal Approach

### 1. **Zero Code Changes for New Databases**
- Copy `.env.example` to `.env`
- Update connection details
- Run `--refresh-schema`
- Start querying

### 2. **Automatic Schema Understanding**
- Discovers tables, columns, types, nullability
- Detects foreign key relationships
- Finds views automatically
- Caches for performance (24h TTL)

### 3. **Consistent Behavior Across Databases**
- Same NL→SQL pipeline
- Same intent extraction
- Same SQL generation logic
- Same result formatting

### 4. **Easy Testing and Validation**
- `test_setup.py` validates entire stack
- Schema inspection tools (`schema_reader.py --list-tables`)
- Detailed logging in RESULTS/
- `--explain-only` and `--no-exec` for debugging

### 5. **Maintainability**
- Single codebase for all databases
- No database-specific branches
- Clear separation of concerns (schema discovery vs SQL generation)
- Self-documenting schema context

## Migration Checklist

If you want to migrate your own database:

- [ ] Copy `.env.example` to `.env`
- [ ] Fill in Azure AI Foundry credentials
- [ ] Fill in Azure SQL connection details
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run setup test: `python test_setup.py`
- [ ] Refresh schema: `python schema_reader.py --refresh`
- [ ] Test simple query: `python nl2sql_main.py --query "Count records"`
- [ ] Inspect schema cache: `cat DATABASE_SETUP/schema_cache.json`
- [ ] Verify table discovery: `python schema_reader.py --list-tables`
- [ ] Test complex query with joins
- [ ] Review generated SQL quality
- [ ] Adjust schema cache TTL if needed

## Limitations and Considerations

### What IS Supported
✅ Any Azure SQL Database
✅ Dynamic schema discovery
✅ Multiple schemas (dim, fact, dbo, etc.)
✅ Foreign key relationships
✅ Views and base tables
✅ Complex data types
✅ NULL handling

### What is NOT Supported
❌ Non-Azure SQL databases (MySQL, PostgreSQL) - would need connection string changes
❌ SQL Server instances (not Azure) - would need authentication changes
❌ Stored procedures - not included in schema context
❌ Computed columns - shown as regular columns
❌ Triggers - not visible to schema discovery
❌ Custom functions - not documented

### Performance Considerations

**Schema Cache:**
- Default TTL: 24 hours
- Adjust via: `get_sql_database_schema_context(ttl_seconds=3600)` (1 hour)
- Force refresh: `--refresh-schema` flag
- Cache location: `DATABASE_SETUP/schema_cache.json`

**Large Databases:**
- Schema discovery takes 10-60 seconds for 100+ tables
- Consider creating focused views for common queries
- Use schema cache to avoid repeated discovery
- Increase TTL for stable schemas

## Conclusion

The "universal" version maintains 100% of the NL2SQL functionality while removing all hardcoded database assumptions. The core discovery logic was already excellent - we simply removed output string hardcoding and made guidance generic.

**Key insight:** Good architecture makes databases pluggable. The original implementation had great schema discovery; we just made the presentation layer database-agnostic.

Now you can test your NL2SQL capabilities against:
- TERADATA-FI (commercial lending)
- CONTOSO-FI (original dataset)
- Any other Azure SQL database

All with zero code changes - just update `.env` and refresh schema!
