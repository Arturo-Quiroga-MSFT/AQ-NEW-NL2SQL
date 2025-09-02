# NL2SQL-only Entrypoint

This folder contains `nl2sql_main.py`, a focused version of the pipeline that implements only the NL→Intent→SQL flow. It mirrors the sequence and comments of `AQ-NEW-NL2SQL/main.py` but excludes any DAX functionality.

## What it does
- Extract intent/entities from a natural language question (Azure OpenAI via LangChain)
- Generate a T-SQL query using schema-aware prompting
- Sanitize/extract the T-SQL code
- Execute against Azure SQL Database via `pyodbc`
- Print results in a table and save the full run output to a timestamped file

## Prerequisites
- Install dependencies from the repo’s `requirements.txt`
- Provide a `.env` with:
  - AZURE_OPENAI_API_KEY
  - AZURE_OPENAI_ENDPOINT
  - AZURE_OPENAI_DEPLOYMENT_NAME
  - AZURE_SQL_SERVER
  - AZURE_SQL_DB
  - AZURE_SQL_USER
  - AZURE_SQL_PASSWORD
- Ensure Microsoft ODBC Driver 18 for SQL Server is installed on macOS:
  - brew tap microsoft/mssql-release
  - brew install msodbcsql18

## Quick start
```bash
# Show script purpose
python AQ-NEW-NL2SQL/nl2sql_main.py --whoami

# Interactive prompt for the question
python AQ-NEW-NL2SQL/nl2sql_main.py

# Provide the question inline
python AQ-NEW-NL2SQL/nl2sql_main.py --query "List the top 5 customers by total credit"

# Generate SQL but skip execution
python AQ-NEW-NL2SQL/nl2sql_main.py --query "Average balance per customer" --no-exec
```

Output logs will be written in this folder as `nl2sql_run_<query>_<timestamp>.txt`.

## Diagrams

- End-to-end flow: see `docs/NL2SQL_PIPELINE_FLOW.md` for Mermaid flowchart and sequence diagram of the NL2SQL pipeline.
