"""
Universal dynamic schema context provider for Azure SQL databases.
Keeps the schema description in sync with the live database using a JSON cache
that can be refreshed on demand or by TTL. Works with any database schema without hardcoding.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

try:
	import pyodbc  # type: ignore
	_PYODBC_AVAILABLE = True
	_PYODBC_IMPORT_ERROR = None
except Exception as _e:  # pragma: no cover
	pyodbc = None  # type: ignore
	_PYODBC_AVAILABLE = False
	_PYODBC_IMPORT_ERROR = _e
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
	"""Query the database for tables, columns, data types, and relationships."""
	if not _PYODBC_AVAILABLE:
		raise RuntimeError(
			f"pyodbc is not available (import error: {_PYODBC_IMPORT_ERROR}). "
			"Install system ODBC Driver 18 and the 'pyodbc' package to enable live schema fetch."
		)
	
	data: Dict[str, Any] = {
		"database_name": AZURE_SQL_DB,
		"server": AZURE_SQL_SERVER,
		"tables": {},
		"relationships": [],
		"views": {},
		"timestamp": time.time()
	}
	
	with pyodbc.connect(CONN_STR) as conn:  # type: ignore
		cur = conn.cursor()
		
		# Get all tables (exclude system schemas)
		cur.execute(
			"""
			SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
			FROM INFORMATION_SCHEMA.TABLES
			WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')
			  AND TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA')
			ORDER BY TABLE_SCHEMA, TABLE_NAME
			"""
		)
		table_list = [(r.TABLE_SCHEMA, r.TABLE_NAME, r.TABLE_TYPE) for r in cur.fetchall()]
		
		# Get columns with data types for each table/view
		for sch, tbl, tbl_type in table_list:
			cur.execute(
				"""
				SELECT 
					COLUMN_NAME,
					DATA_TYPE,
					CHARACTER_MAXIMUM_LENGTH,
					IS_NULLABLE,
					COLUMN_DEFAULT
				FROM INFORMATION_SCHEMA.COLUMNS
				WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
				ORDER BY ORDINAL_POSITION
				""",
				(sch, tbl),
			)
			
			columns = []
			for r in cur.fetchall():
				col_info = {
					"name": r.COLUMN_NAME,
					"type": r.DATA_TYPE,
					"nullable": r.IS_NULLABLE == 'YES',
				}
				if r.CHARACTER_MAXIMUM_LENGTH:
					col_info["max_length"] = r.CHARACTER_MAXIMUM_LENGTH
				if r.COLUMN_DEFAULT:
					col_info["default"] = r.COLUMN_DEFAULT
				columns.append(col_info)
			
			full_name = f"{sch}.{tbl}"
			if tbl_type == 'BASE TABLE':
				data["tables"][full_name] = columns
			else:
				data["views"][full_name] = columns

		# Get primary keys
		cur.execute(
			"""
			SELECT 
				s.name AS SchemaName,
				t.name AS TableName,
				c.name AS ColumnName
			FROM sys.key_constraints kc
			INNER JOIN sys.tables t ON kc.parent_object_id = t.object_id
			INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
			INNER JOIN sys.index_columns ic ON kc.parent_object_id = ic.object_id AND kc.unique_index_id = ic.index_id
			INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
			WHERE kc.type = 'PK'
			ORDER BY s.name, t.name, ic.key_ordinal
			"""
		)
		pk_map = {}
		for r in cur.fetchall():
			full_name = f"{r.SchemaName}.{r.TableName}"
			if full_name not in pk_map:
				pk_map[full_name] = []
			pk_map[full_name].append(r.ColumnName)
		
		# Add PK info to tables
		for tbl_name, pk_cols in pk_map.items():
			if tbl_name in data["tables"]:
				for col in data["tables"][tbl_name]:
					if col["name"] in pk_cols:
						col["is_primary_key"] = True

		# Get foreign key relationships
		cur.execute(
			"""
			SELECT 
			  tp_s.name AS ParentSchema,
			  tp.name AS ParentTable,
			  cp.name AS ParentColumn,
			  tr_s.name AS RefSchema,
			  tr.name AS RefTable,
			  cr.name AS RefColumn,
			  fk.name AS ConstraintName
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
					"constraint": r.ConstraintName,
					"from_table": f"{r.ParentSchema}.{r.ParentTable}",
					"from_column": r.ParentColumn,
					"to_table": f"{r.RefSchema}.{r.RefTable}",
					"to_column": r.RefColumn,
				}
			)
	
	return data


def _save_cache(data: Dict[str, Any]) -> None:
	"""Save schema metadata to JSON cache file."""
	with open(CACHE_FILE, "w") as f:
		json.dump(data, f, indent=2)


def _load_cache() -> Dict[str, Any]:
	"""Load schema metadata from JSON cache file."""
	if CACHE_FILE.exists():
		try:
			with open(CACHE_FILE, "r") as f:
				return json.load(f)
		except Exception:
			return {
				"database_name": AZURE_SQL_DB,
				"server": AZURE_SQL_SERVER,
				"tables": {},
				"relationships": [],
				"views": {},
				"timestamp": 0
			}
	return {
		"database_name": AZURE_SQL_DB,
		"server": AZURE_SQL_SERVER,
		"tables": {},
		"relationships": [],
		"views": {},
		"timestamp": 0
	}


def refresh_schema_cache() -> Path:
	"""Fetch fresh schema from database and save to cache."""
	data = _fetch_live_schema()
	_save_cache(data)
	return CACHE_FILE


def _build_context_from_metadata(meta: Dict[str, Any]) -> str:
	"""Build human-readable schema context string from metadata."""
	lines = []
	
	# Database identification
	db_name = meta.get("database_name", "Unknown")
	server = meta.get("server", "Unknown")
	timestamp = meta.get("timestamp", 0)
	if timestamp:
		from datetime import datetime
		ts_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
		lines.append(f"DATABASE: {db_name} on {server}\n")
		lines.append(f"Schema cached: {ts_str}\n\n")
	else:
		lines.append(f"DATABASE: {db_name} on {server}\n\n")
	
	# General SQL guidelines
	lines.append("SQL GENERATION GUIDELINES:\n")
	lines.append("- Generate T-SQL compatible with Azure SQL Database\n")
	lines.append("- Use TWO-PART table names ONLY (e.g., schema.TableName)\n")
	lines.append("- DO NOT use three-part names with database prefix (already connected to database)\n")
	lines.append("- IMPORTANT: Use the EXACT table names from the TABLES section below\n")
	lines.append("- This database uses a star schema with 'dim' (dimension) and 'fact' schemas\n")
	lines.append("- Do NOT assume generic table names like 'dbo.customers' - check the actual schema\n")
	lines.append("- Use appropriate JOINs based on foreign key relationships\n")
	lines.append("- Use GROUP BY for aggregations\n")
	lines.append("- Include ORDER BY for result consistency\n")
	lines.append("- Return a single executable SELECT statement\n")
	lines.append("- Do not use USE, GO, or multiple statements\n")
	lines.append("- Handle NULL values appropriately\n\n")
	
	# Views (if any)
	views = meta.get("views", {})
	if views:
		lines.append("VIEWS (Pre-joined data for convenient queries):\n")
		for view_name, cols in sorted(views.items()):
			col_names = [c["name"] for c in cols[:15]]
			preview = ", ".join(col_names)
			if len(cols) > 15:
				preview += f" ... ({len(cols)} total columns)"
			lines.append(f"- {view_name}: {preview}\n")
		lines.append("\n")
	
	# Tables with detailed column info
	tables = meta.get("tables", {})
	if tables:
		lines.append("TABLES:\n")
		for tbl_name, cols in sorted(tables.items()):
			lines.append(f"\n{tbl_name}:\n")
			for col in cols[:20]:  # Show first 20 columns
				col_str = f"  - {col['name']} ({col['type']}"
				if col.get("max_length"):
					col_str += f"({col['max_length']})"
				col_str += ")"
				if col.get("is_primary_key"):
					col_str += " [PK]"
				if not col.get("nullable", True):
					col_str += " NOT NULL"
				lines.append(col_str + "\n")
			if len(cols) > 20:
				lines.append(f"  ... ({len(cols) - 20} more columns)\n")
		lines.append("\n")
	
	# Relationships
	relationships = meta.get("relationships", [])
	if relationships:
		lines.append("FOREIGN KEY RELATIONSHIPS:\n")
		for rel in relationships:
			lines.append(
				f"- {rel['from_table']}.{rel['from_column']} -> "
				f"{rel['to_table']}.{rel['to_column']}\n"
			)
		lines.append("\n")
	
	# Summary
	lines.append(f"SUMMARY: {len(tables)} tables, {len(views)} views, {len(relationships)} relationships\n")
	
	return "".join(lines)


def get_sql_database_schema_context(ttl_seconds: Optional[int] = None) -> str:
	"""Return schema context string, refreshing cache if TTL expired.

	Args:
		ttl_seconds: If provided, refresh cache when older than this TTL.
					 If None, default to 24h (86400 seconds).

	Returns:
		String containing formatted schema information for LLM context.
	"""
	ttl = 86400 if ttl_seconds is None else ttl_seconds
	
	try:
		# Check if cache needs refresh
		stale = True
		if CACHE_FILE.exists():
			age = time.time() - CACHE_FILE.stat().st_mtime
			stale = age > ttl
			if stale:
				print(f"[INFO] Schema cache is stale (age: {age:.0f}s > TTL: {ttl}s), refreshing...")
		else:
			print(f"[INFO] Schema cache not found at {CACHE_FILE}, fetching from database...")
		
		if stale:
			refresh_schema_cache()
		
		meta = _load_cache()
		
		# Validate we have table data
		if not meta.get("tables"):
			print(f"[WARNING] Schema cache has no tables, forcing refresh...")
			refresh_schema_cache()
			meta = _load_cache()
		
		return _build_context_from_metadata(meta)
	
	except Exception as e:
		# Fallback to minimal context if live sync fails
		return (
			f"DATABASE: {AZURE_SQL_DB} on {AZURE_SQL_SERVER}\n\n"
			f"WARNING: Schema sync unavailable: {e}\n\n"
			"SQL GENERATION GUIDELINES:\n"
			"- Generate T-SQL compatible with Azure SQL Database\n"
			"- Use schema-qualified table names\n"
			"- Return a single executable SELECT statement\n"
			"- Use appropriate JOINs and WHERE clauses\n"
			"\nPlease refresh the schema cache or check database connectivity.\n"
		)


def get_schema_metadata_from_cache() -> Dict[str, Any]:
	"""Return the raw schema metadata from the local cache as a dictionary.

	Returns:
		Dictionary with structure:
		{
			"database_name": str,
			"server": str,
			"tables": {
				"schema.table": [
					{"name": "col1", "type": "int", "nullable": bool, ...},
					...
				]
			},
			"views": {
				"schema.view": [columns...]
			},
			"relationships": [
				{
					"constraint": "FK_Name",
					"from_table": "schema.table",
					"from_column": "col",
					"to_table": "schema.table",
					"to_column": "col"
				},
				...
			],
			"timestamp": float
		}
	"""
	return _load_cache()


def get_table_list() -> list:
	"""Return a list of all table names (schema.table format)."""
	meta = _load_cache()
	return sorted(meta.get("tables", {}).keys())


def get_view_list() -> list:
	"""Return a list of all view names (schema.view format)."""
	meta = _load_cache()
	return sorted(meta.get("views", {}).keys())


def get_table_columns(table_name: str) -> list:
	"""Return columns for a specific table."""
	meta = _load_cache()
	return meta.get("tables", {}).get(table_name, [])


if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Universal schema cache utilities")
	parser.add_argument("--refresh", action="store_true", help="Refresh schema cache from database")
	parser.add_argument("--print", action="store_true", help="Print current schema context")
	parser.add_argument("--list-tables", action="store_true", help="List all tables")
	parser.add_argument("--list-views", action="store_true", help="List all views")
	parser.add_argument("--table", type=str, help="Show columns for specific table")
	parser.add_argument("--ttl", type=int, default=86400, help="TTL in seconds (default 86400)")
	parser.add_argument("--json", action="store_true", help="Output raw JSON metadata")
	args = parser.parse_args()

	if args.refresh:
		path = refresh_schema_cache()
		print(f"[INFO] Schema cache refreshed: {path}")

	if args.print:
		ctx = get_sql_database_schema_context(ttl_seconds=args.ttl)
		print(ctx)

	if args.list_tables:
		tables = get_table_list()
		print(f"Tables ({len(tables)}):")
		for tbl in tables:
			print(f"  - {tbl}")

	if args.list_views:
		views = get_view_list()
		print(f"Views ({len(views)}):")
		for view in views:
			print(f"  - {view}")

	if args.table:
		cols = get_table_columns(args.table)
		if cols:
			print(f"\nColumns in {args.table}:")
			for col in cols:
				print(f"  - {col['name']} ({col['type']})")
		else:
			print(f"Table '{args.table}' not found in cache")

	if args.json:
		meta = get_schema_metadata_from_cache()
		print(json.dumps(meta, indent=2))
