# AQ-NEW-NL2SQL

Repository structure

```
AQ-NEW-NL2SQL/
├─ .env.example                 # Sample env vars with placeholders (copy to .env)
├─ .gitignore                   # Ignore caches, env files, IDE cruft
├─ DATABASE_SETUP/              # SQL migrations and helpers for Azure SQL
│  ├─ README.md
│  ├─ contoso_fi_extensions.sql
│  ├─ migrations/
│  │  └─ 001_extend_domain.sql
│  ├─ run_migrations.py         # Applies migrations; reads AZURE_SQL_* env vars
│  └─ schema_cache.json         # Cached DB schema (for prompt context)
├─ docs/                        # Documentation and diagrams
│  ├─ CONTOSO-FI_DATASET_GUIDE.md
│  ├─ CONTOSO-FI_EXAMPLE_QUESTIONS.txt
│  ├─ CONTOSO-FI_EXAMPLE_SOLUTIONS.md
│  ├─ NL2SQL_PIPELINE_FLOW.md
│  └─ diagrams/
│     ├─ .gitignore
│     ├─ nl2sql_data_lineage.mmd
│     ├─ nl2sql_flowchart.mmd
│     ├─ nl2sql_sequence.mmd
│     └─ nl2sql_flowchart.svg   # Auto-generated from the Mermaid flowchart
├─ ui/
│  └─ streamlit_app/
│     ├─ app.py                 # Streamlit UI for NL→Intent→Reasoning→SQL→Results
│     └─ README.md              # How to run the demo UI
├─ agents_nl2sql/               # Experimental multi-agent NL2SQL demo
│  ├─ graph.py
│  ├─ llm.py
│  ├─ run_demo.py               # Minimal runner for the agent graph
│  ├─ state.py
│  ├─ requirements.txt          # Extra deps for the agents demo (optional)
│  └─ README.md
├─ RESULTS/                     # Saved outputs from runs (logs, SQL, results)
│  ├─ nl2sql_run_*.txt          # Timestamped run artifacts (CLI & UI)
│  └─ nl2sql_run_*.json         # JSON sidecar with exact result rows (UI)
├─ nl2sql_main.py               # Main NL→SQL pipeline entrypoint (Azure OpenAI)
├─ old_main.py                  # Earlier prototype (kept for reference)
├─ schema_reader.py             # Reads/caches DB schema for prompting
├─ sql_executor.py              # Executes SQL against Azure SQL via pyodbc
└─ README.md
```

# NL2SQL-only Entrypoint (CLI)

This folder contains `nl2sql_main.py`, a focused version of the pipeline that implements only the NL→Intent→SQL flow. It mirrors the sequence and comments of `AQ-NEW-NL2SQL/main.py` but excludes any DAX functionality.

## What it does
- Extract intent/entities from a natural language question (Azure OpenAI via LangChain)
- Generate a T-SQL query using schema-aware prompting
- Sanitize/extract the T-SQL code
- Execute against Azure SQL Database via `pyodbc`
- Print results in a table and save the full run output to a timestamped file

## Prerequisites
- Install dependencies from the repo’s `requirements.txt`
- Provide a `.env` (use `.env.example` as a starting point) with:
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

## How to run with decision flags (matches the flowchart)

Use these flags to control the decision points shown in the NL→SQL flow:

- --refresh-schema: Refresh the cached DB schema before generation (ensures up-to-date context)
- --no-reasoning: Skip the optional “SQL Generation Reasoning” step
- --explain-only: Print only Intent & Entities and the Reasoning summary; skip SQL generation and execution
- --no-exec: Generate SQL but do not execute it against the database
- --query "...": Provide the natural language question inline (otherwise you’ll be prompted)

Examples

```bash
# Full run (default): Intent → Reasoning → SQL → Execute
python nl2sql_main.py --query "Show the 10 most recent loans"

# Refresh schema first, then run end-to-end
python nl2sql_main.py --query "Weighted average interest rate by region" --refresh-schema

# Reasoning only (no SQL produced, no execution)
python nl2sql_main.py --query "List collateral items valued above 1,000" --explain-only

# Generate SQL but skip execution
python nl2sql_main.py --query "For each company, compute the total outs" --no-exec

# Faster run without the reasoning summary
python nl2sql_main.py --query "For each region, list the top 5 companies by balance" --no-reasoning
```

## Components

- `nl2sql_main.py`: CLI entrypoint that:
  - Loads env vars, wires LangChain with Azure OpenAI
  - Pulls schema context from `schema_reader.py`
  - Prompts for SQL, sanitizes and optionally executes via `sql_executor.py`
  - Writes outputs into `RESULTS/`
- `schema_reader.py`: Builds a compact schema context from Azure SQL (with a TTL cache) used to steer SQL generation.
- `sql_executor.py`: Executes T-SQL using pyodbc with connection details from env vars.
- `DATABASE_SETUP/`: SQL artifacts and `run_migrations.py` to set up/extend the Contoso FI sample.
- `docs/`: Guides and Mermaid diagrams. The flowchart SVG is generated from Mermaid sources.
- `RESULTS/`: Timestamped logs from pipeline runs; consider ignoring in `.gitignore` if you don’t want to commit them.

## Streamlit UI (Demo)

An interactive UI for the same NL→Intent→Reasoning→SQL→Results pipeline lives under `ui/streamlit_app/app.py`.

Features
- Clickable example questions (auto-parsed from `docs/CONTOSO-FI_EXAMPLE_QUESTIONS.txt` when present)
- Sidebar controls:
  - Environment status (checks Azure OpenAI and Azure SQL env vars)
  - Refresh schema cache button (updates `DATABASE_SETUP/schema_cache.json`)
  - Schema context preview
- Main panel shows: Intent & Entities, optional Reasoning, Generated SQL (raw), Sanitized SQL, and Results table
- Toggles: “Skip execution”, “Explain-only”, “No reasoning”
- Exports: CSV and Excel for results, “Copy SQL” button to show copyable SQL
- Logging: Writes a `.txt` log and a `.json` sidecar containing the exact result rows

Run the UI
```bash
# Install repo requirements (includes Streamlit, pandas, etc.)
python -m pip install -r requirements.txt

# Start the Streamlit app
streamlit run ui/streamlit_app/app.py
```

Notes
- Ensure your `.env` (or shell env) contains the same variables listed under Prerequisites.
- On macOS, installing Microsoft ODBC Driver 18 is required for SQL execution via pyodbc.
- For faster file watching during development, the repo includes `watchdog`.

Results artifacts from the UI
- `RESULTS/nl2sql_run_<query>_<ts>.txt`: Includes the table-formatted SQL results and a token usage/cost section.
- `RESULTS/nl2sql_run_<query>_<ts>.json`: Exact result rows as a JSON array for programmatic reuse.

## Database setup (optional)

If you need to provision/extend the sample schema in Azure SQL, see `DATABASE_SETUP/README.md` and run `DATABASE_SETUP/run_migrations.py` after setting your AZURE_SQL_* environment variables.

## Diagrams

End-to-end NL→SQL flowchart (generated from `docs/diagrams/nl2sql_flowchart.mmd`):

<p align="center">
  <img src="docs/diagrams/nl2sql_flowchart.svg" alt="NL2SQL Flowchart" width="800" />
  <br />
  <em>High-level flow from NL question to SQL generation and execution.</em>
  
</p>

### Diagram legend (flags → decision boxes)

- Decision: Refresh schema? → Use `--refresh-schema`
- Decision: Show reasoning plan? → Omit `--no-reasoning` (add it to skip)
- Decision: Only explain (no SQL/no exec)? → Use `--explain-only`
- Decision: Execute SQL? → Omit `--no-exec` (add it to skip execution)
- Input source: Prompt vs inline → Use `--query "..."` to provide the question


## Azure SQL tips: USE and GO

When generating or executing T-SQL from applications/drivers (ODBC/pyodbc), keep these Azure SQL specifics in mind:

- GO isn’t T‑SQL. It’s a client tool batch separator (for SSMS/sqlcmd). Don’t include `GO` in SQL you send via drivers; split batches into separate commands instead. See: https://learn.microsoft.com/sql/t-sql/language-elements/sql-server-utilities-statements-go
- USE to change database context isn’t appropriate for Azure SQL Database app queries. Connect directly to the target database with the right connection string. For cross-database scenarios consider [Elastic query](https://learn.microsoft.com/azure/azure-sql/database/elastic-query-overview?view=azuresql) or use Azure SQL Managed Instance if you need wider cross-DB features. See T‑SQL differences: https://learn.microsoft.com/azure/azure-sql/database/transact-sql-tsql-differences-sql-server?view=azuresql
- This repo’s demo notebook and script already guard against empty or non‑SELECT SQL to avoid driver errors; keep prompts focused on single, executable queries.

## Token usage and cost reporting

At the end of each run, the CLI prints token counts and, when pricing is configured, an estimated cost for the run (USD by default; CAD supported). It includes:

- Input tokens (prompt)
- Completion tokens (output)
- Total tokens
- Estimated cost (input + output)

Configure the per‑1K token prices using one of the following methods:

1) Deployment‑specific environment variables

- `AZURE_OPENAI_PRICE_<DEPLOYMENT_NAME>_INPUT_PER_1K`
- `AZURE_OPENAI_PRICE_<DEPLOYMENT_NAME>_OUTPUT_PER_1K`

Example for `AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o`:

```bash
export AZURE_OPENAI_PRICE_GPT_4O_INPUT_PER_1K=<current_input_price_usd>
export AZURE_OPENAI_PRICE_GPT_4O_OUTPUT_PER_1K=<current_output_price_usd>
```

2) Global environment variables (fallback used if no deployment‑specific values are set)

- `AZURE_OPENAI_PRICE_INPUT_PER_1K`
- `AZURE_OPENAI_PRICE_OUTPUT_PER_1K`

3) Optional JSON file at repo root: `azure_openai_pricing.json`

```json
{
  "gpt-4o": { "input_per_1k": 2.50, "output_per_1k": 10.00 },
  "gpt-4o-mini": { "input_per_1k": 0.15, "output_per_1k": 0.60 }
}
```

Notes:

- Always source the latest numbers from the official Azure OpenAI pricing page. Prices vary by Global/Data Zone/Regional deployments and may change over time.
- If pricing isn’t configured, the script still prints token counts with a quick hint on how to enable cost calculation.

### Currency selection (USD/CAD) and conversion

You can choose the currency shown in cost estimates:

- `AZURE_OPENAI_PRICE_CURRENCY` = `USD` (default) or `CAD`

If your JSON is in USD but you want CAD output, optionally provide a conversion rate via env vars. If no rate is set, the script will fall back to USD values while labeling them clearly:

- `AZURE_OPENAI_PRICE_USD_TO_CAD` (e.g., `1.36`)
- `AZURE_OPENAI_PRICE_CAD_TO_USD` (e.g., `0.74`)

Both env-based pricing and JSON pricing work with the chosen target currency. The JSON file also supports a nested per-currency format if you prefer to store values for multiple currencies:

```json
{
  "gpt-5": {
    "USD": { "input_per_1k": 0.00, "output_per_1k": 0.00 },
    "CAD": { "input_per_1k": 0.00, "output_per_1k": 0.00 }
  },
  "gpt-4.1": {
    "USD": { "input_per_1k": 0.00, "output_per_1k": 0.00 },
    "CAD": { "input_per_1k": 0.00, "output_per_1k": 0.00 }
  }
}
```

In all cases, deployment-specific env vars take precedence over global env vars, which take precedence over JSON file entries.

Reference: Azure OpenAI pricing

- https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/

## Agents NL2SQL (experimental)

An experimental multi-agent approach is provided in `agents_nl2sql/`. This is optional and separate from the main CLI and UI paths.

Quick start
```bash
# Optional: install extra deps for the agents demo
python -m pip install -r agents_nl2sql/requirements.txt

# Run the demo
python agents_nl2sql/run_demo.py
```

As this is experimental, APIs and behaviors may change; see `agents_nl2sql/README.md` for details.

