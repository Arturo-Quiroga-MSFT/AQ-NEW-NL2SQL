# Agents NL2SQL (LangChain + LangGraph) — underscore package

This is the properly named Python package (underscores, importable as `agents_nl2sql`). 

Quick start

1) Install deps:
   - `pip install -r agents_nl2sql/requirements.txt`
2) Run a demo:
   - `python -m agents_nl2sql.run_demo --query "Show the 10 most recent loans." --no-reasoning`

Notes

- The LLM-backed nodes are placeholders; current flow focuses on sanitize + execute. Use `--explain-only` with a raw SQL to test execution quickly.
- Safety: sanitizer enforces SELECT-only; executor honors `--no-exec`.
