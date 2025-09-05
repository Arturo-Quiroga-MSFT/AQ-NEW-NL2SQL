# Agents NL2SQL Streamlit UI

A Streamlit-based UI for the agents-driven NL2SQL pipeline. This app is similar in spirit to the main NL2SQL UI, but is designed to orchestrate the agent-based workflow defined in `agents_nl2sql`.

## How to run
1. Install dependencies (see `requirements.txt`).
2. From the repo root, run:

   ```bash
   streamlit run agents_nl2sql/ui/app.py
   ```

## Features
- Enter natural language questions and get SQL + results
- Shows agent state transitions and reasoning
- Displays raw and sanitized SQL
- Table view of results
- Schema cache refresh button
- Token usage and cost display

## Requirements
- Python 3.9+
- Streamlit
- pandas, XlsxWriter, pyodbc, langchain, etc. (see requirements.txt)

## Notes
- Uses the agent pipeline in `agents_nl2sql` (not the root pipeline)
- Schema cache is shared with the main pipeline
- Requires ODBC Driver 18 for SQL Server and `pyodbc` installed
