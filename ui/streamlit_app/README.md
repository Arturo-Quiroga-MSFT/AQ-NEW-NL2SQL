# NL2SQL Streamlit UI

A simple, rich UI to demo the NL → Intent → Reasoning → SQL → Results pipeline.

Features
- Example questions to click and run
- Shows extracted intent/entities
- Shows compact reasoning plan
- Shows raw and sanitized SQL
- Displays query results in a table
- Button to refresh the schema cache (uses `schema_reader.refresh_schema_cache()`)
- Token usage and cost (if pricing configured via env or `azure_openai_pricing.json`)

How to run
1. Ensure your `.env` (or environment variables) contains Azure OpenAI and Azure SQL settings (see root `README.md`).
2. Install dependencies from the repo root.
3. Start the UI:

   ```bash
   streamlit run ui/streamlit_app/app.py
   ```

Notes
- Requires ODBC Driver 18 for SQL Server and `pyodbc` installed.
- Uses the same core functions in `nl2sql_main.py`, `schema_reader.py`, and `sql_executor.py`.
