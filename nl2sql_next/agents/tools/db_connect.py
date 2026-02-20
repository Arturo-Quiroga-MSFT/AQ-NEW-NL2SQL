"""SQL connection helper with Entra ID token auth."""
from __future__ import annotations

import os
import struct

import pyodbc
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

_SERVER = os.getenv("AZURE_SQL_SERVER", "")
_DATABASE = os.getenv("AZURE_SQL_DB", "")
_AUTH_MODE = os.getenv("AZURE_SQL_AUTH", "entra").lower()


def _get_entra_connection() -> pyodbc.Connection:
    cred = AzureCliCredential()
    tok = cred.get_token("https://database.windows.net/.default")
    tb = tok.token.encode("utf-16-le")
    ts = struct.pack(f"<I{len(tb)}s", len(tb), tb)
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={_SERVER};DATABASE={_DATABASE};",
        attrs_before={1256: ts},
    )


def _get_sql_connection() -> pyodbc.Connection:
    user = os.getenv("AZURE_SQL_USER", "")
    pwd = os.getenv("AZURE_SQL_PASSWORD", "")
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={_SERVER};DATABASE={_DATABASE};"
        f"UID={user};PWD={pwd};Encrypt=yes;TrustServerCertificate=yes;",
    )


def get_connection() -> pyodbc.Connection:
    if _AUTH_MODE == "entra":
        return _get_entra_connection()
    return _get_sql_connection()
