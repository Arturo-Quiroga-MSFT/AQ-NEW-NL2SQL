# CONTOSO-FI Database Setup and Migrations

This folder contains SQL migrations and a small Python runner to evolve the CONTOSO-FI schema with richer entities and seed data for demos.

## What’s here
- `migrations/` — ordered, idempotent `.sql` files. Apply in lexical order.
- `run_migrations.py` — applies all or one migration using pyodbc.

## Prereqs
- Microsoft ODBC Driver 18 for SQL Server installed on your machine.
- Python dependencies installed (pyodbc, python-dotenv), e.g. from the repo `requirements.txt`.
- Environment variables (in shell or a `.env` file at repo root or this folder):
  - `AZURE_SQL_SERVER` (e.g., `myserver.database.windows.net`)
  - `AZURE_SQL_DATABASE` (e.g., `CONTOSO-FI`)
  - `AZURE_SQL_USERNAME`
  - `AZURE_SQL_PASSWORD`

## Apply migrations
- Dry run (list planned files):
  - python run_migrations.py --dry-run
- Apply all:
  - python run_migrations.py
- Apply a single migration by prefix:
  - python run_migrations.py --one 001

Migrations should be idempotent (use `IF NOT EXISTS` guards) so re-running is safe.

## After applying
- Refresh the NL2SQL schema cache so the pipeline sees new tables/columns:
  - python ../schema_reader.py --cache --print

## Notes
- If you hit login/driver errors, verify ODBC Driver 18 is installed and the four env vars are set.
- If using Azure AD, adjust `run_migrations.py` connection code accordingly or provide a SQL user for simplicity.