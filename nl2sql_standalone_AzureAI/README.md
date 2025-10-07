# NL2SQL Pipeline - Azure AI Agent Service Implementation

This is a standalone implementation of the NL2SQL pipeline using **Azure AI Agent Service** (Azure AI Foundry SDK) instead of LangChain.

## Overview

This implementation provides the same NL→Intent→SQL pipeline as the LangChain version but leverages Azure AI Foundry's Agent Service for:

- **Native Azure Integration**: Direct integration with Azure AI Foundry projects
- **Built-in Agent Management**: Automatic agent lifecycle management
- **Enterprise Authentication**: Uses DefaultAzureCredential for secure authentication
- **Enhanced Observability**: Native tracing and monitoring through Azure AI Foundry
- **No External Dependencies**: No need for LangChain or third-party orchestration libraries

## Architecture

The pipeline follows the same 5-step process:

```
Natural Language Query
         ↓
    Intent Extraction (Azure AI Agent)
         ↓
    SQL Generation (Azure AI Agent)
         ↓
    SQL Sanitization
         ↓
    SQL Execution (Azure SQL)
         ↓
    Formatted Results
```

### Key Differences from LangChain Version

| Aspect | LangChain Version | Azure AI Agent Version |
|--------|-------------------|------------------------|
| **Orchestration** | LangChain chains | Azure AI Agent Service |
| **Agent Creation** | N/A | Dynamic agent creation per request |
| **Thread Management** | N/A | Thread-based conversation |
| **Authentication** | API Key | DefaultAzureCredential |
| **Observability** | Manual tracking | Built-in Azure AI tracing |
| **Dependencies** | langchain, langchain-openai | azure-ai-projects, azure-identity |

## Prerequisites

### 1. Azure AI Foundry Project

You need an Azure AI Foundry project with:
- A deployed AI model (e.g., gpt-4.1, gpt-4o)
- Agent Service enabled
- Your Azure credentials configured

### 2. Azure SQL Database

- Azure SQL Database with the CONTOSO-FI schema (or your own database)
- Connection credentials

### 3. Python Environment

- Python 3.11 or higher
- Virtual environment (recommended)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the `.env` file and configure these required variables:

```bash
# Azure AI Foundry Project Configuration
PROJECT_ENDPOINT=https://<your-project>.openai.azure.com/
MODEL_DEPLOYMENT_NAME=gpt-4.1

# Azure SQL Database Configuration
AZURE_SQL_SERVER=<your-server>.database.windows.net
AZURE_SQL_DB=<your-database>
AZURE_SQL_USER=<your-username>
AZURE_SQL_PASSWORD=<your-password>
```

### 3. Configure Azure Authentication

The implementation uses `DefaultAzureCredential`, which supports multiple authentication methods:

**Option 1: Azure CLI (Recommended for local development)**
```bash
az login
```

**Option 2: Environment Variables**
```bash
export AZURE_TENANT_ID=<your-tenant-id>
export AZURE_CLIENT_ID=<your-client-id>
export AZURE_CLIENT_SECRET=<your-client-secret>
```

**Option 3: Managed Identity**
- Automatically works when running in Azure (App Service, Container Apps, VMs)

## Usage

### Basic Usage

```bash
python nl2sql_main.py --query "How many customers do we have?"
```

### Interactive Mode

```bash
python nl2sql_main.py
# Enter your natural language query when prompted
```

### Command-Line Options

```bash
--query "your question"   # Provide query inline
--no-exec                 # Generate SQL but don't execute
--explain-only            # Show intent extraction only
--whoami                  # Show script information
```

### Example Queries

```bash
# Count queries
python nl2sql_main.py --query "How many loans are active?"

# Aggregation queries
python nl2sql_main.py --query "What is the total collateral value per loan type?"

# Filtered queries
python nl2sql_main.py --query "List companies with more than 5 employees in California"

# Top-N queries
python nl2sql_main.py --query "Top 10 companies by revenue in 2024"
```

## How It Works

### 1. Intent Extraction Agent

The pipeline creates a temporary **intent extraction agent** that:
- Analyzes the natural language query
- Identifies intent (count, list, aggregate, filter)
- Extracts entities (tables, columns, metrics)
- Returns structured JSON with the analysis

**Agent Instructions:**
```python
"You are an AI assistant that extracts the intent and entities 
from natural language database queries. Return JSON format with 
keys: intent, entity, metrics, filters, group_by."
```

### 2. SQL Generation Agent

The pipeline creates a temporary **SQL generation agent** that:
- Receives the extracted intent
- Uses the database schema context
- Generates valid T-SQL for Azure SQL Database
- Returns clean SQL without markdown

**Agent Instructions:**
```python
"You are an expert SQL query generator for Azure SQL Database.
Given the user's intent and the database schema, generate a 
valid T-SQL query. Database Schema: {schema_context}"
```

### 3. Agent Lifecycle

Both agents are:
1. **Created** dynamically for each request
2. **Used** with thread-based communication
3. **Deleted** immediately after use

This ensures:
- No persistent agent storage
- Clean state for each query
- Minimal resource usage

## Output

The pipeline produces comprehensive output including:

1. **Model Information**: Project endpoint and deployment name
2. **Natural Language Query**: The original user question
3. **Intent & Entities**: Structured extraction result
4. **Generated SQL (Raw)**: Initial SQL from the agent
5. **Sanitized SQL**: Cleaned SQL ready for execution
6. **Query Results**: Formatted table with results
7. **Token Usage & Cost**: Detailed token tracking with pricing
8. **Run Duration**: Total execution time

Results are saved to `RESULTS/nl2sql_run_<query>_<timestamp>.txt`

## File Structure

```
nl2sql_standalone_AzureAI/
├── nl2sql_main.py              # Main pipeline using Azure AI Agent Service
├── schema_reader.py            # Database schema loader
├── sql_executor.py             # SQL query executor
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration
├── azure_openai_pricing.json  # Token pricing configuration
├── RESULTS/                    # Query execution results
└── README.md                   # This file
```

## Token Usage & Pricing

The implementation tracks token usage across all agent interactions:

- **Input Tokens**: Tokens sent to agents (queries + context)
- **Completion Tokens**: Tokens generated by agents (responses)
- **Total Tokens**: Sum of input + completion tokens

Pricing is calculated based on `azure_openai_pricing.json`:

```json
{
  "gpt-4.1": {
    "input_per_1k": 0.00275,
    "output_per_1k": 0.01100
  }
}
```

Example output:
```
Input tokens: 1,523
Completion tokens: 287
Total tokens: 1,810
Estimated cost (USD): 0.007327 [input=0.004188, output=0.003157]
```

## Troubleshooting

### Authentication Errors

```
DefaultAzureCredential failed to retrieve a token
```

**Solution**: Run `az login` or set environment variables:
```bash
export AZURE_TENANT_ID=<your-tenant-id>
export AZURE_CLIENT_ID=<your-client-id>
export AZURE_CLIENT_SECRET=<your-client-secret>
```

### Agent Creation Errors

```
Failed to create agent: Project not found
```

**Solution**: Verify `PROJECT_ENDPOINT` in `.env` is correct and you have access to the project.

### SQL Execution Errors

```
Login failed for user
```

**Solution**: Verify Azure SQL credentials in `.env` and check firewall rules.

### Import Errors

```
ImportError: cannot import name 'AIProjectClient'
```

**Solution**: Install required packages:
```bash
pip install azure-ai-projects azure-identity
```

## Comparison: LangChain vs Azure AI Agent Service

### When to Use LangChain Version

- You need LangChain ecosystem integrations
- You're already using LangChain in your application
- You want maximum framework flexibility

### When to Use Azure AI Agent Service Version

- You want native Azure integration
- You need built-in observability and tracing
- You prefer enterprise authentication (DefaultAzureCredential)
- You want minimal dependencies
- You're building on Azure AI Foundry platform

## Next Steps

### Enhancements

1. **Persistent Agents**: Store agents for reuse instead of creating per request
2. **Conversation Memory**: Use threads to maintain conversation history
3. **Function Tools**: Add custom function tools for complex operations
4. **File Search**: Enable document search for schema documentation
5. **Code Interpreter**: Add code execution capabilities

### Integration

1. **Streamlit UI**: Build a web interface for the pipeline
2. **API Endpoint**: Expose as REST API using FastAPI
3. **Container Apps**: Deploy to Azure Container Apps
4. **Batch Processing**: Process multiple queries in parallel

## Resources

- [Azure AI Agent Service Documentation](https://learn.microsoft.com/azure/ai-services/agents/)
- [Azure AI Foundry SDK](https://learn.microsoft.com/python/api/azure-ai-projects/)
- [DefaultAzureCredential Guide](https://learn.microsoft.com/python/api/azure-identity/azure.identity.defaultazurecredential)

## License

MIT License - See parent repository for details

## Support

For issues or questions, please refer to the main repository documentation or create an issue in the project repository.
