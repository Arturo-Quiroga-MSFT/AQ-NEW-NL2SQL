"""
Local SQL executor for NL2SQL-only runs, self-contained to avoid external imports.
Uses pyodbc and environment variables for Azure SQL connectivity.
"""

import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

AZURE_SQL_SERVER = os.getenv("AZURE_SQL_SERVER")
AZURE_SQL_DB = os.getenv("AZURE_SQL_DB")
AZURE_SQL_USER = os.getenv("AZURE_SQL_USER")
AZURE_SQL_PASSWORD = os.getenv("AZURE_SQL_PASSWORD")

CONN_STR = (
	f"DRIVER={{ODBC Driver 18 for SQL Server}};"
	f"SERVER={AZURE_SQL_SERVER};"
	f"DATABASE={AZURE_SQL_DB};"
	f"UID={AZURE_SQL_USER};PWD={AZURE_SQL_PASSWORD};"
	"Encrypt=yes;TrustServerCertificate=yes;"
)


def execute_sql_query(sql_query: str):
	with pyodbc.connect(CONN_STR) as conn:
		cursor = conn.cursor()
		cursor.execute(sql_query)
		columns = [desc[0] for desc in cursor.description]
		rows = cursor.fetchall()
		return [dict(zip(columns, row)) for row in rows]

