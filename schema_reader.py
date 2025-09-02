"""
Dynamic schema context provider for CONTOSO-FI used by the NL2SQL-only pipeline.
Keeps the LLM schema description in sync with the live database using a JSON cache
that can be refreshed on demand or by TTL.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any

import pyodbc
from dotenv import load_dotenv

# Load env for DB connectivity
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

# Cache location under DATABASE_SETUP to keep artifacts together
DB_SETUP_DIR = Path(__file__).parent / "DATABASE_SETUP"
DB_SETUP_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = DB_SETUP_DIR / "schema_cache.json"


def _fetch_live_schema() -> Dict[str, Any]:
	"""Query the database for tables, columns, and relationships."""
	data: Dict[str, Any] = {"tables": {}, "relationships": []}
	with pyodbc.connect(CONN_STR) as conn:
		cur = conn.cursor()
		# Tables (exclude system schemas)
		cur.execute(
			"""
			SELECT TABLE_SCHEMA, TABLE_NAME
			FROM INFORMATION_SCHEMA.TABLES
			WHERE TABLE_TYPE IN ('BASE TABLE')
			  AND TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA')
			ORDER BY TABLE_SCHEMA, TABLE_NAME
			"""
		)
		tables = [(r.TABLE_SCHEMA, r.TABLE_NAME) for r in cur.fetchall()]
		for sch, tbl in tables:
			cur.execute(
				"""
				SELECT COLUMN_NAME
				FROM INFORMATION_SCHEMA.COLUMNS
				WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
				ORDER BY ORDINAL_POSITION
				""",
				(sch, tbl),
			)
			cols = [r.COLUMN_NAME for r in cur.fetchall()]
			data["tables"][f"{sch}.{tbl}"] = cols

		# Foreign keys
		cur.execute(
			"""
			SELECT 
			  tp_s.name AS ParentSchema,
			  tp.name AS ParentTable,
			  cp.name AS ParentColumn,
			  tr_s.name AS RefSchema,
			  tr.name AS RefTable,
			  cr.name AS RefColumn
			FROM sys.foreign_keys fk
			INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
			INNER JOIN sys.tables tp ON fkc.parent_object_id = tp.object_id
			INNER JOIN sys.schemas tp_s ON tp.schema_id = tp_s.schema_id
			INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
			INNER JOIN sys.tables tr ON fkc.referenced_object_id = tr.object_id
			INNER JOIN sys.schemas tr_s ON tr.schema_id = tr_s.schema_id
			INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
			ORDER BY tp_s.name, tp.name, cp.name
			"""
		)
		for r in cur.fetchall():
			data["relationships"].append(
				{
					"from_table": f"{r.ParentSchema}.{r.ParentTable}",
					"from_column": r.ParentColumn,
					"to_table": f"{r.RefSchema}.{r.RefTable}",
					"to_column": r.RefColumn,
				}
			)
	return data


def _save_cache(data: Dict[str, Any]) -> None:
	with open(CACHE_FILE, "w") as f:
		json.dump(data, f, indent=2)


def _load_cache() -> Dict[str, Any]:
	if CACHE_FILE.exists():
		try:
			with open(CACHE_FILE, "r") as f:
				return json.load(f)
		except Exception:
			return {"tables": {}, "relationships": []}
	return {"tables": {}, "relationships": []}


def refresh_schema_cache() -> Path:
	data = _fetch_live_schema()
	_save_cache(data)
	return CACHE_FILE


def _build_context_from_metadata(meta: Dict[str, Any]) -> str:
	lines = []
	lines.append("DATABASE: CONTOSO-FI (Azure SQL)\n")
	# Key guidance
	lines.append("GUIDELINES\n")
	lines.append("- Prefer dbo.vw_LoanPortfolio for portfolio-style questions and join to Collateral or PaymentSchedule when required.\n")
	lines.append("- Use appropriate GROUP BY for aggregates; weight interest rate averages by PrincipalAmount if needed.\n")
	lines.append("- Do not emit USE or GO; return a single executable SELECT statement.\n\n")

	# View is stable and convenient; keep it documented
	lines.append("VIEW\n")
	lines.append("- dbo.vw_LoanPortfolio: Denormalized portfolio view with columns including LoanId, LoanNumber, CompanyName, Industry, CreditRating, CountryName, RegionName, OriginationDate, MaturityDate, PrincipalAmount, CurrencyCode, InterestRatePct, InterestRateType, ReferenceRate, SpreadBps, AmortizationType, PaymentFreqMonths, Status, Purpose\n\n")

	# Tables
	lines.append("TABLES\n")
	for tbl, cols in sorted(meta.get("tables", {}).items()):
		# show first ~12 columns for brevity
		preview = ", ".join(cols[:12]) + (" ..." if len(cols) > 12 else "")
		lines.append(f"- {tbl}({preview})\n")
	lines.append("\n")

	# Relationships
	lines.append("RELATIONSHIPS\n")
	for rel in meta.get("relationships", []):
		lines.append(
			f"- {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}\n"
		)
	lines.append("\n")
	return "".join(lines)


def get_sql_database_schema_context(ttl_seconds: int = None) -> str:
	"""Return schema context string, refreshing cache if TTL expired.

	ttl_seconds: if provided, refresh cache when older than this TTL.
				 If None, default to 24h (86400 seconds).
	"""
	ttl = 86400 if ttl_seconds is None else ttl_seconds
	try:
		# If cache missing or stale, refresh
		stale = True
		if CACHE_FILE.exists():
			age = time.time() - CACHE_FILE.stat().st_mtime
			stale = age > ttl
		if stale:
			refresh_schema_cache()
		meta = _load_cache()
		return _build_context_from_metadata(meta)
	except Exception as e:
		# Fallback to a minimal static context if live sync fails
		return (
			"DATABASE: CONTOSO-FI (Azure SQL)\n\n"
			"VIEW\n"
			"- dbo.vw_LoanPortfolio: Denormalized portfolio view (Loan, Company, Region, Principal, InterestRate, etc.)\n\n"
			"GUIDELINES\n"
			"- Prefer dbo.vw_LoanPortfolio and join to Collateral/PaymentSchedule if needed.\n"
			f"- Schema sync unavailable: {e}\n"
		)


def get_schema_metadata_from_cache() -> Dict[str, Any]:
		"""Return the raw schema metadata from the local cache as a dictionary.

		Structure:
			{
				"tables": {
					"schema.table": ["col1", "col2", ...]
				},
				"relationships": [
					{"from_table": "schema.table", "from_column": "col", "to_table": "schema.table", "to_column": "col"},
					...
				]
			}
		"""
		return _load_cache()


if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Schema cache utilities")
	parser.add_argument("--cache", action="store_true", help="Refresh schema cache from DB")
	parser.add_argument("--print", action="store_true", help="Print current schema context")
	parser.add_argument("--ttl", type=int, default=86400, help="TTL in seconds when building context (default 86400)")
	args = parser.parse_args()

	if args.cache:
		path = refresh_schema_cache()
		print(f"[INFO] Schema cache refreshed: {path}")

	if args.print:
		ctx = get_sql_database_schema_context(ttl_seconds=args.ttl)
		print(ctx)

