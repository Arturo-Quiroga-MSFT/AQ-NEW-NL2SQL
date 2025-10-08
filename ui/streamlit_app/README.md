# NL2SQL Streamlit UI Applications

This directory contains **three** Streamlit-based user interfaces for the Contoso-FI NL2SQL demo, each using a different backend implementation or optimization strategy.

## 📱 Applications

### 1. `app.py` - LangChain Implementation
Uses the LangChain-based pipeline from `nl2sql_standalone_Langchain/`

**Run command:**
```bash
streamlit run app.py
# or from repo root:
streamlit run ui/streamlit_app/app.py
```

**Backend:** LangChain + Azure OpenAI  
**Requires:** `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT_NAME`

---

### 2. `app_azureai.py` - Azure AI Agent Service Implementation
Uses the Azure AI Foundry Agent Service pipeline from `nl2sql_standalone_AzureAI/`

**Run command:**
```bash
streamlit run app_azureai.py
# or from repo root:
streamlit run ui/streamlit_app/app_azureai.py
```

**Backend:** Azure AI Foundry Agent Service  
**Requires:** `PROJECT_ENDPOINT`, `MODEL_DEPLOYMENT_NAME`, DefaultAzureCredential (az login)

---

### 3. `app_multimodel.py` - Multi-Model Optimized Implementation 🎯 🆕
Uses **different specialized models** for each pipeline stage to optimize cost and performance

**Run command:**
```bash
streamlit run app_multimodel.py --server.port 8503
# or from repo root:
streamlit run ui/streamlit_app/app_multimodel.py --server.port 8503
```

**Backend:** LangChain + Azure OpenAI (multi-model)  
**Model Strategy:**
- 🎯 **Intent Extraction**: `gpt-4o-mini` (fast, cheap parsing)
- 🧠 **SQL Generation**: `gpt-4.1` or `gpt-5-mini` (accurate SQL, user-selectable)
- 📝 **Result Formatting**: `gpt-4.1-mini` (balanced summaries)

**Requires:** `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`  
**Cost Savings:** Up to 80% compared to using gpt-4.1 for all stages!

---

## ✨ Common Features

Both applications provide:
- ✅ Example question buttons for quick exploration
- ✅ Intent and entity extraction display
- ✅ SQL generation with syntax highlighting
- ✅ Live SQL execution against Azure SQL Database
- ✅ Results in interactive tables (CSV/Excel export)
- ✅ Token usage tracking and cost estimation
- ✅ Elapsed time measurement
- ✅ Run configuration display
- ✅ Detailed run logs saved to `RESULTS/` directory
- ✅ Optional Azure Blob Storage upload for logs
- ✅ Schema cache refresh capability

## 🔑 Key Differences

| Feature | LangChain (`app.py`) | Azure AI Agents (`app_azureai.py`) | Multi-Model (`app_multimodel.py`) |
|---------|---------------------|-----------------------------------|-----------------------------------|
| Backend | LangChain + Azure OpenAI | Azure AI Foundry Agent Service | LangChain + Azure OpenAI |
| Authentication | API Key | DefaultAzureCredential | API Key |
| Model Strategy | Single model for all | Single agent model | **3 specialized models** |
| Intent Extraction | Uses configured model | Built into agent | **gpt-4o-mini** (cheapest) |
| SQL Generation | Uses configured model | Built into agent | **gpt-4.1 or gpt-5-mini** (user choice) |
| Result Formatting | Not included | Not included | **gpt-4.1-mini** (balanced) |
| Agent Persistence | No | Yes (reused across queries) | No |
| Reasoning Step | Optional, explicit | Built-in to agent | Optional, explicit |
| Cost Optimization | Standard | Standard | **Up to 80% savings** |
| Best For | Development, testing | Production, Azure-native apps | **Cost-sensitive production** |

## 💰 Cost Comparison Example

For a typical query with 2K input tokens and 1K output tokens:

| Implementation | Cost per Query | Notes |
|----------------|---------------|-------|
| `app.py` (gpt-4.1 only) | ~$0.017 | Single model for all stages |
| `app_azureai.py` | Varies | Depends on agent model |
| `app_multimodel.py` | ~$0.006 | **65% cheaper!** Uses cheap models where possible |

**Breakdown for multi-model:**
- Intent (gpt-4o-mini): ~$0.0006 (1K tokens @ $0.00015 in, $0.0006 out)
- SQL (gpt-4.1): ~$0.005 (2K tokens @ $0.00277 in, $0.01107 out)  
- Formatting (gpt-4.1-mini): ~$0.0008 (1K tokens @ $0.00055 in, $0.0022 out)

## 🚀 Quick Start

1. **Ensure your `.env` file** (in repo root) contains the required settings
2. **Install dependencies** from the repo root
3. **Start the UI** of your choice:

```bash
# LangChain version (single model)
streamlit run ui/streamlit_app/app.py

# Azure AI Agent version  
streamlit run ui/streamlit_app/app_azureai.py --server.port 8502

# Multi-Model optimized version (best cost efficiency)
streamlit run ui/streamlit_app/app_multimodel.py --server.port 8503
```

**💡 Tip:** Run all three simultaneously on different ports to compare performance and costs!

## 🎯 Which App Should I Use?

### Use `app.py` if:
- ✅ You're developing and testing
- ✅ You want simple, straightforward setup
- ✅ You're using a single powerful model for everything

### Use `app_azureai.py` if:
- ✅ You're deploying to production on Azure
- ✅ You want native Azure integration with managed identity
- ✅ You need persistent agents across queries
- ✅ You want built-in safety and monitoring

### Use `app_multimodel.py` if:
- ✅ **You want to minimize costs** (up to 80% savings)
- ✅ You want optimal model selection for each task
- ✅ You need detailed cost breakdowns by pipeline stage
- ✅ You want to experiment with different model combinations
- ✅ You have high query volume and want to optimize spend

## 🧪 Multi-Model Strategy Explained

The `app_multimodel.py` implementation uses the principle of **"right model for the right job"**:

### 🎯 Stage 1: Intent Extraction (gpt-4o-mini)
**Task:** Parse user question into structured format  
**Why:** Simple parsing doesn't need expensive reasoning models  
**Token Cost:** $0.00015 per 1K input tokens (cheapest available)  
**Typical Usage:** ~1K-2K tokens per query

### 🧠 Stage 2: SQL Generation (gpt-4.1 or gpt-5-mini)
**Task:** Generate accurate, complex T-SQL queries  
**Why:** Requires deep reasoning and schema understanding  
**Options:**
- `gpt-4.1`: Most accurate, best for complex multi-table joins (~$0.00277 per 1K input)
- `gpt-5-mini`: Faster reasoning, lower cost (~$0.0003 per 1K input)  
**Typical Usage:** ~3K-5K tokens per query (includes schema context)

### 📝 Stage 3: Result Formatting (gpt-4.1-mini)
**Task:** Summarize SQL results into natural language  
**Why:** Balanced capability for clear, professional explanations  
**Token Cost:** $0.00055 per 1K input tokens  
**Typical Usage:** ~2K-4K tokens per query (includes results preview)

### 💰 Cost Savings Example

**Scenario:** 1,000 queries per day, average 6K total tokens per query

| Implementation | Daily Cost | Monthly Cost | Annual Cost |
|----------------|------------|--------------|-------------|
| Single gpt-4.1 | $102 | $3,060 | $36,720 |
| Multi-model optimized | $36 | $1,080 | $12,960 |
| **Savings** | **$66/day** | **$1,980/month** | **$23,760/year** |

*Assumptions: 3K input, 3K output tokens per query; prices from October 2025*

## Notes

- All apps require ODBC Driver 18 for SQL Server and `pyodbc` installed
- The LangChain and Multi-Model apps use the same core functions from `nl2sql_standalone_Langchain/`
- The Multi-Model app automatically tracks token usage and costs separately for each stage
- **Environment Variables Required:**
  - For `app.py` and `app_multimodel.py`: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`
  - For `app_azureai.py`: `PROJECT_ENDPOINT`, `MODEL_DEPLOYMENT_NAME`
  - All apps: `AZURE_SQL_SERVER`, `AZURE_SQL_DB`, `AZURE_SQL_USER`, `AZURE_SQL_PASSWORD`

## 📊 Features Unique to Multi-Model App

- ✨ **Per-stage cost breakdown**: See exactly what each model costs
- ✨ **Model selection UI**: Choose between gpt-4.1 and gpt-5-mini for SQL generation
- ✨ **AI-powered result summaries**: Natural language explanations of query results
- ✨ **Visual cost comparison**: See savings vs single-model approach
- ✨ **Detailed multi-model logs**: Run logs show which model was used for each stage

## 🔧 Environment Setup

Create a `.env` file in the repository root with:

```bash
# Azure OpenAI (for app.py and app_multimodel.py)
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1  # For single-model app.py
AZURE_OPENAI_API_VERSION=2025-04-01-preview

# Azure AI Agent Service (for app_azureai.py)
PROJECT_ENDPOINT=https://your-project.cognitiveservices.azure.com/
MODEL_DEPLOYMENT_NAME=gpt-4.1

# Azure SQL Database (all apps)
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DB=CONTOSO-FI
AZURE_SQL_USER=your_username
AZURE_SQL_PASSWORD=your_password

# Optional: Azure Blob Storage for log uploads
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
AZURE_STORAGE_CONTAINER_NAME=nl2sql-logs
```

## 🎓 Learn More

- See `/PRICING_UPDATE_GUIDE.md` for detailed pricing information
- See `/azure_openai_pricing_updated_oct2025.json` for current model pricing
- See `/docs/` for schema documentation and example questions
