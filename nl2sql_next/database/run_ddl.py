"""Execute a .sql file against RetailDW using Entra ID (az login) authentication.

Usage:
    python database/run_ddl.py database/ddl/01_dimensions.sql
    python database/run_ddl.py database/ddl/02_facts.sql
    python database/run_ddl.py database/ddl/03_views.sql
    python database/run_ddl.py --all          # run all ddl/*.sql in order
"""
from __future__ import annotations

import glob
import os
import struct
import sys

import pyodbc
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

# Load .env from the nl2sql_next directory
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
load_dotenv(os.path.join(_ROOT, ".env"))

SERVER = os.getenv("AZURE_SQL_SERVER", "")
DATABASE = os.getenv("AZURE_SQL_DB", "")


def _get_connection() -> pyodbc.Connection:
    cred = AzureCliCredential()
    token = cred.get_token("https://database.windows.net/.default")
    token_bytes = token.token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};",
        attrs_before={1256: token_struct},
        autocommit=True,
    )


def run_sql_file(filepath: str) -> None:
    with open(filepath, "r", encoding="utf-8") as f:
        script = f.read()

    # Split on GO (batch separator) — case-insensitive, must be alone on a line
    import re
    batches = re.split(r"^\s*GO\s*$", script, flags=re.MULTILINE | re.IGNORECASE)

    conn = _get_connection()
    cursor = conn.cursor()
    executed = 0
    for batch in batches:
        batch = batch.strip()
        if not batch:
            continue
        try:
            cursor.execute(batch)
            executed += 1
        except pyodbc.Error as e:
            print(f"  [WARN] Batch error: {e}")
    cursor.close()
    conn.close()
    print(f"  Executed {executed} batches from {os.path.basename(filepath)}")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--all":
        ddl_dir = os.path.join(_HERE, "ddl")
        files = sorted(glob.glob(os.path.join(ddl_dir, "*.sql")))
        if not files:
            print("No .sql files found in database/ddl/")
            sys.exit(1)
        print(f"Running {len(files)} DDL file(s) against {DATABASE} on {SERVER} ...")
        for f in files:
            print(f"\n>>> {os.path.basename(f)}")
            run_sql_file(f)
    else:
        filepath = sys.argv[1]
        if not os.path.isfile(filepath):
            print(f"File not found: {filepath}")
            sys.exit(1)
        print(f"Running {filepath} against {DATABASE} on {SERVER} ...")
        run_sql_file(filepath)

    print("\nDone.")


if __name__ == "__main__":
    main()
