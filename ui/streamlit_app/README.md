# NL2SQL Streamlit UI Applications

This directory contains **two** Streamlit-based user interfaces for the Contoso-FI NL2SQL demo, each using a different backend implementation.

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

### 2. `app_azureai.py` - Azure AI Agent Service Implementation 🆕
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

| Feature | LangChain (`app.py`) | Azure AI Agents (`app_azureai.py`) |
|---------|---------------------|-----------------------------------|
| Backend | LangChain + Azure OpenAI | Azure AI Foundry Agent Service |
| Authentication | API Key | DefaultAzureCredential |
| Agent Persistence | No | Yes (reused across queries) |
| Reasoning Step | Optional, explicit | Built-in to agent |
| Best For | Development, testing | Production, Azure-native apps |

## 🚀 Quick Start

1. **Ensure your `.env` file** (in repo root) contains the required settings
2. **Install dependencies** from the repo root
3. **Start the UI** of your choice:

```bash
# LangChain version
streamlit run ui/streamlit_app/app.py

# Azure AI Agent version  
streamlit run ui/streamlit_app/app_azureai.py
```

Notes
- Requires ODBC Driver 18 for SQL Server and `pyodbc` installed.
- Uses the same core functions in `nl2sql_main.py`, `schema_reader.py`, and `sql_executor.py`.
