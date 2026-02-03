# Streamlit demo for NL2SQL (Azure AI universal)

This file explains how to run the Streamlit front-end demo for the NL→SQL pipeline.

Requirements
 - Python packages listed in the repository `requirements.txt` (Streamlit is already included).
 - Environment variables required by the pipeline (see top-level README):
   - PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME (Azure AI Foundry)
   - AZURE_SQL_SERVER, AZURE_SQL_DB, AZURE_SQL_USER, AZURE_SQL_PASSWORD (for schema & execution)

Run

```bash
pip install -r requirements.txt
streamlit run nl2sql_azureai_universal/streamlit_demo.py
```

Notes
- The demo calls the same public API used by the CLI: `process_nl_query` in `nl2sql_main.py`.
- If you do not have a live database or credentials, uncheck "Execute generated SQL" to still see intent and SQL generation.
- Schema caching is used to avoid repeated live DB calls; refresh the cache via the `schema_reader.refresh_schema_cache()` helper if needed.
