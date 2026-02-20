"""SQL connection helper with Entra ID token auth."""
from __future__ import annotations

import os
import struct

import pyodbc
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load .env from nl2sql_next root
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ROOT, ".env"))

SERVER = os.getenv("AZURE_SQL_SERVER", "")
DATABASE = os.getenv("AZURE_SQL_DB", "")
AUTH_MODE = os.getenv("AZURE_SQL_AUTH", "entra").lower()


def get_connection() -> pyodbc.Connection:
    """Return a pyodbc connection using Entra ID or SQL auth based on config."""
    if AUTH_MODE == "entra":
        cred = DefaultAzureCredential()
        tok = cred.get_token("https://database.windows.net/.default")
        tb = tok.token.encode("utf-16-le")
        ts = struct.pack(f"<I{len(tb)}s", len(tb), tb)
        return pyodbc.connect(
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={SERVER};DATABASE={DATABASE};"
            f"Connection Timeout=30;",
            attrs_before={1256: ts},
        )
    user = os.getenv("AZURE_SQL_USER", "")
    pwd = os.getenv("AZURE_SQL_PASSWORD", "")
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={SERVER};DATABASE={DATABASE};"
        f"UID={user};PWD={pwd};Encrypt=yes;TrustServerCertificate=yes;",
    )
