# NL2SQL Azure AI Agents - Universal Edition

A database-agnostic Natural Language to SQL implementation using Azure AI Agent Service.

## Overview

This is a clean, universal implementation that works with any Azure SQL database without hardcoded schema references. It dynamically discovers database schema and generates SQL queries from natural language.

## Key Features

- ✅ **Schema-Agnostic**: Works with any database schema
- ✅ **Dynamic Schema Discovery**: Automatically reads tables, columns, and relationships
- ✅ **Azure AI Agents**: Uses Azure AI Foundry Agent Service for intelligent SQL generation
- ✅ **Cache Management**: Schema caching with configurable TTL
- ✅ **Intent Extraction**: Separates intent understanding from SQL generation
- ✅ **Safe Execution**: SQL sanitization and validation
- ✅ **Result Formatting**: Pretty-printed table output

## Architecture

```
Natural Language Query
    ↓
[Intent Extraction Agent]
    ↓
[Schema Context Builder]
    ↓
[SQL Generation Agent]
    ↓
[SQL Sanitizer]
    ↓
[SQL Executor]
    ↓
Formatted Results
```

## Setup

### 1. Environment Variables

Create a `.env` file with:

```bash
# Azure AI Foundry
PROJECT_ENDPOINT=https://your-project.api.azureml.ms
MODEL_DEPLOYMENT_NAME=gpt-4

# Azure SQL Database
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DB=your-database-name
AZURE_SQL_USER=your-username
AZURE_SQL_PASSWORD=your-password
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Azure Authentication

Ensure you're authenticated to Azure:
```bash
az login
```

## Usage

### Basic Query
```bash
python nl2sql_main.py --query "Show me total sales by region"
```

### Refresh Schema Cache
```bash
python nl2sql_main.py --refresh-schema --query "List all customers"
```

### Explain Only (No Execution)
```bash
python nl2sql_main.py --explain-only --query "What are the top products?"
```

### Generate SQL Without Execution
```bash
python nl2sql_main.py --no-exec --query "Calculate revenue trends"
```

### Interactive Mode
```bash
python nl2sql_main.py
# Enter your question when prompted
```

## Command Line Options

| Flag | Description |
|------|-------------|
| `--query` | Provide natural language query inline |
| `--refresh-schema` | Force refresh of schema cache |
| `--no-reasoning` | Skip reasoning/planning step |
| `--explain-only` | Show intent only, skip SQL generation |
| `--no-exec` | Generate SQL but don't execute |
| `--whoami` | Display script information |

## File Structure

```
nl2sql_azureai_universal/
├── nl2sql_main.py          # Main pipeline orchestrator
├── schema_reader.py         # Dynamic schema discovery
├── sql_executor.py          # Safe SQL execution
├── requirements.txt         # Python dependencies
├── .env                     # Configuration (create this)
├── DATABASE_SETUP/          # Schema cache location
│   └── schema_cache.json    # Auto-generated schema cache
└── RESULTS/                 # Query results output
    └── {timestamp}_results.txt
```

## How It Works

### 1. Intent Extraction
The system first understands what the user wants:
- Identifies the type of query (aggregation, filtering, joining, etc.)
- Extracts entities (table names, column names, conditions)
- Determines the analytical goal

### 2. Schema Context
Dynamically builds context from the database:
- Queries `INFORMATION_SCHEMA` for tables and columns
- Discovers foreign key relationships
- Caches schema for performance (configurable TTL)
- Provides relevant schema subset to the agent

### 3. SQL Generation
Azure AI Agent generates T-SQL:
- Schema-aware prompting
- Follows SQL best practices
- Includes comments and formatting
- Validates against schema

### 4. Execution & Results
Safe execution with formatting:
- Sanitizes SQL (removes markdown, comments)
- Executes against database
- Formats results as ASCII table
- Saves output to timestamped file

## Schema Cache Management

The schema cache (`DATABASE_SETUP/schema_cache.json`) contains:
- Table definitions with columns and types
- Primary keys and relationships
- Indexes and constraints
- Metadata (last updated, TTL)

**Refresh the cache when:**
- Database schema changes
- New tables/columns added
- After database migrations
- Cache file is older than TTL

## Examples

### Example 1: Simple Aggregation
```
Query: "How many customers do we have?"

Intent: Count total customers
SQL: SELECT COUNT(*) as TotalCustomers FROM dim.DimCustomer
Result: 1,120 customers
```

### Example 2: Complex Join
```
Query: "Show me loan amounts by customer segment"

Intent: Aggregate loans grouped by customer segment
SQL: 
SELECT 
    c.CustomerSegment,
    COUNT(l.LoanKey) as LoanCount,
    SUM(l.OriginalAmount) as TotalAmount
FROM dim.DimCustomer c
JOIN fact.FACT_LOAN_ORIGINATION l ON c.CustomerKey = l.CustomerKey
GROUP BY c.CustomerSegment
```

### Example 3: Time-Series Analysis
```
Query: "What were the payment trends in 2024?"

Intent: Analyze payment patterns over time
SQL:
SELECT 
    FORMAT(d.Date, 'yyyy-MM') as Month,
    COUNT(p.PaymentKey) as PaymentCount,
    SUM(p.TotalPaymentAmount) as TotalAmount
FROM fact.FACT_PAYMENT_TRANSACTION p
JOIN dim.DimDate d ON p.PaymentDateKey = d.DateKey
WHERE YEAR(d.Date) = 2024
GROUP BY FORMAT(d.Date, 'yyyy-MM')
ORDER BY Month
```

## Troubleshooting

### Schema Cache Issues
```bash
# Force refresh if schema is outdated
python nl2sql_main.py --refresh-schema
```

### Connection Errors
- Verify `.env` file has correct credentials
- Check firewall rules allow your IP
- Ensure ODBC Driver 18 is installed

### Agent Not Found
- Agents are created on first run
- Check Azure AI Foundry project endpoint
- Verify authentication with `az login`

### SQL Errors
- Check generated SQL in RESULTS folder
- Verify table/column names exist
- Review intent extraction for misunderstandings

## Best Practices

1. **Schema Exploration**: Start with simple queries to understand your schema
2. **Cache Management**: Refresh cache after schema changes
3. **Specific Queries**: More specific questions generate better SQL
4. **Result Review**: Always review generated SQL before trusting results
5. **Iterative Refinement**: Use feedback to improve subsequent queries

## Performance Considerations

- **Schema Cache**: Reduces latency by avoiding repeated schema queries
- **Selective Context**: Only relevant schema is provided to the agent
- **Batch Queries**: Multiple similar queries can reuse cached schema
- **Agent Reuse**: Agents persist across sessions for efficiency

## Security Notes

- SQL is sanitized before execution
- Read-only operations recommended
- Credentials stored in `.env` (add to `.gitignore`)
- Connection uses encryption by default
- No stored procedures or admin commands allowed

## Limitations

- Currently supports T-SQL (Azure SQL / SQL Server)
- Read queries work best (SELECT statements)
- Complex stored procedures not supported
- Very large schemas may need filtering

## Contributing

This is a universal template that can be adapted for:
- Different database types (PostgreSQL, MySQL, etc.)
- Additional agent capabilities
- Enhanced schema discovery
- Query optimization
- Result caching

## License

Part of the AQ-NEW-NL2SQL project.

## Support

For issues or questions:
1. Check RESULTS folder for detailed error messages
2. Review generated SQL for syntax errors
3. Verify schema cache is up-to-date
4. Check Azure AI Foundry agent logs
