# File Inventory - Azure AI Agent Service Implementation

## Directory: `nl2sql_standalone_AzureAI/`

Complete listing of all files in the Azure AI Agent Service implementation.

---

## Core Implementation Files

### 1. `nl2sql_main.py` (20 KB)
**Purpose**: Main NL2SQL pipeline using Azure AI Agent Service

**Key Components**:
- Agent creation functions: `_create_intent_agent()`, `_create_sql_agent()`
- Intent extraction: `extract_intent(query)` using AI Agent
- SQL generation: `generate_sql(intent_entities)` using AI Agent
- SQL sanitization: `extract_and_sanitize_sql(raw_sql)`
- Token usage tracking: `_accumulate_usage()`, `_reset_token_usage()`
- Pricing calculation: `_get_pricing_for_deployment()`
- Output formatting: `colored_banner()`, `_format_table()`
- Main execution: `main(argv)`

**CLI Options**:
- `--query`: Provide query inline
- `--no-exec`: Skip SQL execution
- `--explain-only`: Show intent only
- `--whoami`: Show script info
- `--refresh-schema`: Refresh schema cache
- `--no-reasoning`: Skip reasoning output

**Dependencies**:
- `azure.ai.projects.AIProjectClient`
- `azure.identity.DefaultAzureCredential`
- `schema_reader.get_sql_database_schema_context`
- `sql_executor.execute_sql_query`

**Environment Variables Required**:
- `PROJECT_ENDPOINT`: Azure AI Foundry project endpoint
- `MODEL_DEPLOYMENT_NAME`: Model deployment name (e.g., gpt-4.1)
- `AZURE_SQL_SERVER`: SQL server hostname
- `AZURE_SQL_DB`: Database name
- `AZURE_SQL_USER`: Database username
- `AZURE_SQL_PASSWORD`: Database password

---

### 2. `schema_reader.py` (8.0 KB)
**Purpose**: Load database schema context for SQL generation

**Key Functions**:
- `get_sql_database_schema_context()`: Returns complete schema description

**Functionality**:
- Loads pre-defined schema from embedded string
- Provides table descriptions, column definitions, relationships
- Optimized schema context for CONTOSO-FI database
- No database connection required (uses static schema)

**Schema Includes**:
- Database guidelines and best practices
- Table definitions with columns and types
- Recommended views for queries
- Relationship descriptions
- Query patterns and examples

**Size**: 4,777 characters of schema context

---

### 3. `sql_executor.py` (899 bytes)
**Purpose**: Execute SQL queries against Azure SQL Database

**Key Functions**:
- `execute_sql_query(sql_query)`: Executes query and returns results

**Functionality**:
- Connects to Azure SQL using pyodbc
- Executes T-SQL queries
- Returns results as list of dictionaries
- Handles errors and connection issues

**Dependencies**:
- `pyodbc`: ODBC driver for SQL Server
- Environment variables: `AZURE_SQL_SERVER`, `AZURE_SQL_DB`, `AZURE_SQL_USER`, `AZURE_SQL_PASSWORD`

**Connection String**:
```
DRIVER={ODBC Driver 18 for SQL Server};
SERVER={server};
DATABASE={database};
UID={user};
PWD={password};
Encrypt=yes;
TrustServerCertificate=no;
Connection Timeout=30;
```

---

## Configuration Files

### 4. `.env` (1.4 KB)
**Purpose**: Environment configuration

**Sections**:
1. **Azure AI Foundry Project Configuration**:
   - `PROJECT_ENDPOINT`: Project endpoint URL
   - `MODEL_DEPLOYMENT_NAME`: Model deployment name

2. **Azure OpenAI Configuration** (backward compatibility):
   - `AZURE_OPENAI_API_KEY`: API key (not used by Azure AI Agent Service)
   - `AZURE_OPENAI_ENDPOINT`: Endpoint URL
   - `AZURE_OPENAI_DEPLOYMENT_NAME`: Deployment name
   - `AZURE_OPENAI_API_VERSION`: API version

3. **Azure SQL Database**:
   - `AZURE_SQL_SERVER`: Server hostname
   - `AZURE_SQL_DB`: Database name
   - `AZURE_SQL_USER`: Username
   - `AZURE_SQL_PASSWORD`: Password

4. **Power BI/XMLA** (optional, for NL2DAX):
   - Various Power BI credentials
   - XMLA endpoint configuration
   - Tenant/Client/Secret credentials

**Security Note**: Contains sensitive credentials - keep secure

---

### 5. `azure_openai_pricing.json` (313 bytes)
**Purpose**: Token pricing configuration for cost estimation

**Format**:
```json
{
  "gpt-4.1": {
    "input_per_1k": 0.00275,
    "output_per_1k": 0.01100
  }
}
```

**Usage**:
- Loaded by `_load_pricing_config()` in `nl2sql_main.py`
- Used to calculate estimated costs per query
- Supports multiple model deployments
- Prices in USD per 1,000 tokens

**Current Pricing**:
- GPT-4.1 input: $0.00275 per 1K tokens
- GPT-4.1 output: $0.01100 per 1K tokens

---

### 6. `requirements.txt` (238 bytes)
**Purpose**: Python package dependencies

**Packages**:
```
# Azure AI Agent Service dependencies
azure-ai-projects>=1.0.0
azure-identity>=1.19.0

# Database connectivity
pyodbc>=5.2.0

# Utilities
python-dotenv>=1.0.0
requests>=2.32.0

# Optional: for Streamlit UI
streamlit>=1.40.0
pandas>=2.2.0
```

**Installation**:
```bash
pip install -r requirements.txt
```

**Key Dependencies**:
- `azure-ai-projects`: Azure AI Agent Service SDK
- `azure-identity`: Azure authentication (DefaultAzureCredential)
- `pyodbc`: SQL Server database driver
- `python-dotenv`: Environment variable management

---

## Documentation Files

### 7. `README.md` (9.1 KB)
**Purpose**: Comprehensive implementation guide

**Sections**:
1. **Overview**: Architecture and key differences from LangChain
2. **Prerequisites**: Azure AI Foundry, Azure SQL, Python requirements
3. **Setup**: Installation and configuration steps
4. **Usage**: Command-line examples and options
5. **How It Works**: Agent lifecycle and implementation details
6. **Output**: Result format and file structure
7. **File Structure**: Directory listing
8. **Token Usage & Pricing**: Cost tracking explanation
9. **Troubleshooting**: Common issues and solutions
10. **Comparison**: When to use LangChain vs Azure AI
11. **Next Steps**: Enhancement ideas
12. **Resources**: Links to Microsoft documentation

**Target Audience**: Developers implementing or evaluating the Azure AI version

---

### 8. `COMPARISON.md` (11 KB)
**Purpose**: Side-by-side comparison with LangChain implementation

**Sections**:
1. **Code Architecture Comparison**: Intent extraction and SQL generation code examples
2. **Key Differences**: Authentication, execution model, dependencies, token tracking, error handling
3. **Performance Comparison**: Agent creation overhead, optimization strategies
4. **Feature Comparison**: Detailed feature matrix
5. **Cost Comparison**: Infrastructure and pricing analysis
6. **When to Use Each**: Decision matrix for choosing implementation
7. **Migration Path**: Steps to migrate between implementations
8. **Testing Both**: How to run and compare both versions
9. **Conclusion**: Summary of trade-offs

**Key Comparisons**:
- LangChain: Chain-based, API key auth, 3 packages
- Azure AI: Agent-based, DefaultAzureCredential, 2 packages

---

### 9. `test_setup.py` (3.5 KB)
**Purpose**: Validation script to test setup

**Tests**:
1. **Imports**: Verify all required modules can be imported
2. **Environment**: Check environment variables are set
3. **Azure Auth**: Test DefaultAzureCredential initialization
4. **Project Client**: Test AIProjectClient initialization
5. **Schema Reader**: Verify schema loads correctly

**Usage**:
```bash
python test_setup.py
```

**Output**: Pass/fail status for each test with detailed feedback

**Exit Code**:
- `0`: All tests passed
- `1`: One or more tests failed

---

## Output Directory

### 10. `RESULTS/`
**Purpose**: Store query execution results

**File Format**: `nl2sql_run_<query>_<timestamp>.txt`

**Example**: `nl2sql_run_How_many_customers_20250107_154532.txt`

**Contents**:
- Model information (project endpoint, deployment name)
- Natural language query
- Intent & entities (JSON)
- Generated SQL (raw and sanitized)
- Query results (formatted table)
- Token usage & cost breakdown
- Run duration

**Creation**: Automatically created by `nl2sql_main.py` after each run

---

## Summary Statistics

| Category | Count | Total Size |
|----------|-------|------------|
| **Core Implementation** | 3 files | 29 KB |
| **Configuration** | 3 files | 2 KB |
| **Documentation** | 3 files | 24 KB |
| **Testing** | 1 file | 3.5 KB |
| **Directories** | 1 (RESULTS) | - |
| **Total** | 10 files + 1 dir | ~58 KB |

---

## File Ownership & Modification

| File | Origin | Status |
|------|--------|--------|
| `nl2sql_main.py` | New (Azure AI) | Created |
| `schema_reader.py` | Copied from LangChain | Unchanged |
| `sql_executor.py` | Copied from LangChain | Unchanged |
| `.env` | Copied from LangChain | Modified (added PROJECT_ENDPOINT) |
| `azure_openai_pricing.json` | Copied from LangChain | Unchanged |
| `requirements.txt` | New (Azure AI) | Created |
| `README.md` | New (Azure AI) | Created |
| `COMPARISON.md` | New (Azure AI) | Created |
| `test_setup.py` | New (Azure AI) | Created |
| `RESULTS/` | New (empty) | Created |

---

## Dependencies Graph

```
nl2sql_main.py
├── azure.ai.projects (AIProjectClient)
├── azure.identity (DefaultAzureCredential)
├── schema_reader.py
│   └── (embedded schema string)
├── sql_executor.py
│   ├── pyodbc
│   └── .env (SQL credentials)
├── .env (project configuration)
└── azure_openai_pricing.json (token pricing)

test_setup.py
├── azure.ai.projects
├── azure.identity
├── schema_reader
└── .env

schema_reader.py
└── (standalone, no dependencies)

sql_executor.py
├── pyodbc
└── .env
```

---

## Execution Flow

```
1. User runs: python nl2sql_main.py --query "How many customers?"

2. nl2sql_main.py:
   ├── Load environment (.env)
   ├── Initialize AIProjectClient (DefaultAzureCredential)
   ├── Display model information
   │
   ├── INTENT EXTRACTION
   │   ├── Create intent agent (_create_intent_agent)
   │   ├── Create thread
   │   ├── Send query message
   │   ├── Run agent (create_and_process)
   │   ├── Get response from messages
   │   ├── Track token usage
   │   └── Delete agent
   │
   ├── SQL GENERATION
   │   ├── Load schema (schema_reader.get_sql_database_schema_context)
   │   ├── Create SQL agent (_create_sql_agent with schema)
   │   ├── Create thread
   │   ├── Send intent message
   │   ├── Run agent (create_and_process)
   │   ├── Get response from messages
   │   ├── Track token usage
   │   └── Delete agent
   │
   ├── SQL SANITIZATION
   │   └── Remove markdown, trim whitespace
   │
   ├── SQL EXECUTION (unless --no-exec)
   │   └── sql_executor.execute_sql_query
   │       ├── Connect to Azure SQL (pyodbc)
   │       ├── Execute query
   │       └── Return results as list of dicts
   │
   ├── OUTPUT FORMATTING
   │   ├── Print colored banners
   │   ├── Format results as table
   │   ├── Display token usage & cost
   │   └── Show run duration
   │
   └── PERSIST RESULTS
       └── Save to RESULTS/nl2sql_run_<query>_<timestamp>.txt
```

---

## Key Implementation Patterns

### 1. Agent Lifecycle
```python
agent_id = create_agent()
try:
    # Use agent
    result = process_with_agent(agent_id, query)
    return result
finally:
    # Always clean up
    delete_agent(agent_id)
```

### 2. Thread-Based Communication
```python
thread = client.agents.threads.create()
client.agents.messages.create(thread_id=thread.id, content=query)
run = client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent_id)
messages = client.agents.messages.list(thread_id=thread.id)
```

### 3. Token Usage Tracking
```python
if hasattr(run, 'usage') and run.usage:
    _accumulate_usage({
        "prompt_tokens": run.usage.prompt_tokens,
        "completion_tokens": run.usage.completion_tokens
    })
```

---

## Future Enhancements

### Planned
1. **Persistent Agents**: Create once, reuse multiple times
2. **Conversation Memory**: Multi-turn conversations using threads
3. **Function Tools**: Custom functions for complex operations
4. **Streaming**: Real-time response streaming
5. **Batch Processing**: Parallel query processing

### Optional
1. **Streamlit UI**: Web interface for queries
2. **FastAPI Endpoint**: REST API wrapper
3. **Container Apps Deployment**: Azure deployment
4. **Monitoring Dashboard**: Azure AI Foundry observability

---

## Maintenance Notes

### Regular Updates
- **requirements.txt**: Keep packages updated (monthly)
- **azure_openai_pricing.json**: Update pricing when models change
- **.env**: Rotate credentials periodically

### Monitoring
- **RESULTS/**: Archive old query results (monthly)
- **Token usage**: Monitor costs via output files
- **Error patterns**: Check failed queries in RESULTS/

### Testing
- **test_setup.py**: Run before major changes
- **Integration tests**: Test with sample queries
- **Performance tests**: Track latency trends

---

## Contact & Support

For issues or questions:
1. Check README.md troubleshooting section
2. Review COMPARISON.md for LangChain migration
3. Consult Azure AI documentation
4. Contact repository maintainer

---

**Last Updated**: 2025-01-07  
**Version**: 1.0.0  
**Status**: Production Ready ✓
