# Quick Start Guide

## For TERADATA-FI Database

Follow these steps to test the universal NL2SQL app with your TERADATA-FI database:

### 1. Setup Environment

```bash
cd /Users/<YOUR_DB_USER>iroga/GITHUB/AQ-NEW-NL2SQL/nl2sql_azureai_universal

# Copy environment template
cp .env.example .env

# Edit .env with your values
nano .env
```

### 2. Configure for TERADATA-FI

Edit your `.env` file with these values:

```bash
# Azure AI Foundry (copy from your existing .env)
PROJECT_ENDPOINT=<your-project-endpoint>
MODEL_DEPLOYMENT_NAME=<your-model-deployment>

# Azure SQL Database - TERADATA-FI
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DB=TERADATA-FI
AZURE_SQL_USER=<your-username>
AZURE_SQL_PASSWORD=<your-password>
```

### 3. Install Dependencies

```bash
# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 4. Test Setup

```bash
# Verify everything is configured correctly
python test_setup.py
```

This will check:
- ✅ Environment variables are set
- ✅ Azure SQL Database connection works
- ✅ Schema can be discovered
- ✅ Azure AI Foundry connection works

### 5. Refresh Schema Cache

```bash
# Discover the TERADATA-FI schema
python schema_reader.py --refresh
```

This will:
- Connect to TERADATA-FI database
- Query all tables, columns, and relationships
- Cache the schema to `DATABASE_SETUP/schema_cache.json`
- Take 10-30 seconds depending on schema size

### 6. Run Your First Query

```bash
# Interactive mode
python nl2sql_main.py

# Or provide query directly
python nl2sql_main.py --query "How many loan applications do we have?"

# Or ask about customers
python nl2sql_main.py --query "Show me the top 10 customers by loan amount"

# Or explore payments
python nl2sql_main.py --query "What is the total payment volume this month?"
```

### Example Queries for TERADATA-FI

Based on your database structure, try these:

```bash
# Applications
python nl2sql_main.py --query "How many loan applications were submitted in 2024?"

# Loans
python nl2sql_main.py --query "What is the total outstanding balance across all loans?"

# Payments
python nl2sql_main.py --query "Show me payment statistics by loan status"

# Customers
python nl2sql_main.py --query "Which customers have the most active loans?"

# Cross-fact analysis
python nl2sql_main.py --query "Show me customers with high balance but low payment activity"

# Time-based queries
python nl2sql_main.py --query "What is the month-over-month trend in loan originations?"
```

### Troubleshooting

**Schema not found:**
```bash
# Force refresh the schema cache
python nl2sql_main.py --refresh-schema --query "your question"
```

**Connection errors:**
- Verify your IP is whitelisted in Azure SQL firewall
- Check username/password are correct
- Ensure AZURE_SQL_DB is set to "TERADATA-FI" (case-sensitive)

**Authentication errors:**
- Run `az login` for Azure CLI authentication
- Verify you have access to the AI Foundry project

**SQL generation issues:**
- Use `--explain-only` to see intent extraction without SQL generation
- Use `--no-exec` to generate SQL without executing

### Output Files

All query results are saved to `RESULTS/` directory with format:
- `nl2sql_run_<query>_<timestamp>.txt`

This includes:
- Natural language query
- Extracted intent
- Generated SQL
- Query results
- Token usage and cost

### Tips for Best Results

1. **Be specific**: "Show me the top 10 loans by balance" is better than "show loans"

2. **Use schema terminology**: The app understands your actual table/column names from the schema cache

3. **Try complex queries**: The app can handle multi-table joins, aggregations, and filters

4. **Check schema first**:
   ```bash
   python schema_reader.py --list-tables
   python schema_reader.py --list-views
   python schema_reader.py --table fact.LoanApplications
   ```

5. **Review generated SQL**: If results are unexpected, check the generated SQL to understand what was queried

### Next Steps

Once you've validated the app works with TERADATA-FI:

1. Try progressively more complex queries
2. Test edge cases (empty results, invalid filters, etc.)
3. Evaluate SQL quality and accuracy
4. Tune the schema cache TTL if needed (default 24 hours)
5. Add custom views for common queries

### Comparison to Original App

This universal version differs from `nl2sql_standalone_AzureAI` in:

| Feature | Original | Universal |
|---------|----------|-----------|
| Database references | Hardcoded "CONTOSO-FI" | Dynamic from env |
| View guidance | Specific to vw_LoanPortfolio | Generic |
| Schema discovery | Same | Same |
| Agent architecture | Same | Same |
| SQL generation | Same | Same |

**Result**: Simply change `.env` to switch databases with zero code changes!

### Getting Help

If you encounter issues:

1. Check `test_setup.py` output for diagnostics
2. Review schema cache: `python schema_reader.py --print`
3. Test with `--explain-only` to isolate issues
4. Check RESULTS/ for detailed output logs
5. Verify schema cache has correct tables: `python schema_reader.py --list-tables`
