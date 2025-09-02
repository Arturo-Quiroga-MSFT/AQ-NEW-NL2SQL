"""
Simple SQL migration runner for CONTOSO-FI.

Applies all .sql files in the migrations/ folder in lexical order.
Each migration should be idempotent (use IF NOT EXISTS guards) to allow re-runs.

Environment variables (loaded via python-dotenv if present):
  AZURE_SQL_SERVER   - e.g., myserver.database.windows.net
  AZURE_SQL_DATABASE - e.g., CONTOSO-FI
  AZURE_SQL_USERNAME - SQL username (or AAD user if using access token)
  AZURE_SQL_PASSWORD - password for SQL auth

Usage:
  python run_migrations.py               # apply all
  python run_migrations.py --one 001.sql # apply only one by basename match
  python run_migrations.py --dry-run     # list files but do not execute
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


def get_connection() -> pyodbc.Connection:
    load_dotenv()
    server = os.getenv("AZURE_SQL_SERVER")
    database = os.getenv("AZURE_SQL_DATABASE")
    username = os.getenv("AZURE_SQL_USERNAME")
    password = os.getenv("AZURE_SQL_PASSWORD")

    if not all([server, database, username, password]):
        missing = [k for k, v in {
            "AZURE_SQL_SERVER": server,
            "AZURE_SQL_DATABASE": database,
            "AZURE_SQL_USERNAME": username,
            "AZURE_SQL_PASSWORD": password,
        }.items() if not v]
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};DATABASE={database};UID={username};PWD={password};"
        "TrustServerCertificate=no;Encrypt=yes;Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)


def apply_sql(cursor: pyodbc.Cursor, sql_text: str) -> None:
    # Split on GO batch separators safely
    batches: list[str] = []
    current: list[str] = []
    for line in sql_text.splitlines():
        if line.strip().upper() == "GO":
            batches.append("\n".join(current))
            current = []
        else:
            current.append(line)
    if current:
        batches.append("\n".join(current))

    for batch in batches:
        if not batch.strip():
            continue
        cursor.execute(batch)


def main():
    here = Path(__file__).resolve().parent
    migrations_dir = here / "migrations"
    parser = argparse.ArgumentParser()
    parser.add_argument("--one", help="Apply a single migration by basename match (e.g., 001 or 001_extend_domain)")
    parser.add_argument("--dry-run", action="store_true", help="List migrations without applying")
    args = parser.parse_args()

    if not migrations_dir.exists():
        print(f"No migrations directory found at {migrations_dir}")
        sys.exit(1)

    files = sorted(p for p in migrations_dir.glob("*.sql"))
    if args.one:
        match = args.one.lower()
        files = [p for p in files if p.stem.lower().startswith(match)]
        if not files:
            print(f"No migration matching '{args.one}' found.")
            sys.exit(1)

    print("Planned migrations:")
    for p in files:
        print(f" - {p.name}")

    if args.dry_run:
        return

    with get_connection() as conn:
        conn.autocommit = False
        try:
            cur = conn.cursor()
            for p in files:
                print(f"\nApplying {p.name} ...")
                sql_text = p.read_text(encoding="utf-8")
                apply_sql(cur, sql_text)
                conn.commit()
                print(f"Applied {p.name}")
        except Exception as e:
            conn.rollback()
            print(f"Migration failed: {e}")
            raise


if __name__ == "__main__":
    main()
