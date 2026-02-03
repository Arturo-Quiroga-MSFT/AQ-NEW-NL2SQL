#!/usr/bin/env python3
"""
Check actual schema in TERADATA-FI database
"""

import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def check_teradata_schema():
    """Check what tables and views exist in TERADATA-FI"""
    server = os.getenv("AZURE_SQL_SERVER")
    database = "TERADATA-FI"
    username = os.getenv("AZURE_SQL_USER")
    password = os.getenv("AZURE_SQL_PASSWORD")
    
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};PWD={password};"
        "Encrypt=yes;TrustServerCertificate=yes;"
    )
    
    try:
        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.cursor()
            
            print("=" * 60)
            print(f"SCHEMA ANALYSIS: {database}")
            print("=" * 60)
            
            # Get all tables
            cursor.execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_SCHEMA, TABLE_NAME
            """)
            
            tables = cursor.fetchall()
            print(f"\n📊 TABLES ({len(tables)} found):")
            for schema, table, table_type in tables:
                print(f"  {schema}.{table}")
            
            # Get all views
            cursor.execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.VIEWS
                ORDER BY TABLE_SCHEMA, TABLE_NAME
            """)
            
            views = cursor.fetchall()
            print(f"\n👁️  VIEWS ({len(views)} found):")
            if views:
                for schema, view in views:
                    print(f"  {schema}.{view}")
            else:
                print("  ⚠️  No views found in database")
            
            # Check if the old view exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.VIEWS 
                WHERE TABLE_NAME = 'vw_LoanPortfolio'
            """)
            
            loan_view_exists = cursor.fetchone()[0]
            print(f"\n🔍 Checking for 'vw_LoanPortfolio': {'✅ EXISTS' if loan_view_exists else '❌ NOT FOUND'}")
            
            # Check for any loan-related tables
            cursor.execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME LIKE '%loan%' OR TABLE_NAME LIKE '%Loan%'
                ORDER BY TABLE_NAME
            """)
            
            loan_tables = cursor.fetchall()
            print(f"\n💰 LOAN-RELATED TABLES ({len(loan_tables)} found):")
            if loan_tables:
                for schema, table in loan_tables:
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM [{schema}].[{table}]")
                    count = cursor.fetchone()[0]
                    print(f"  {schema}.{table} ({count:,} rows)")
            else:
                print("  ⚠️  No loan-related tables found")
            
            # Get sample of all tables with row counts
            print(f"\n📈 ALL TABLES WITH ROW COUNTS:")
            for schema, table, _ in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM [{schema}].[{table}]")
                    count = cursor.fetchone()[0]
                    print(f"  {schema}.{table}: {count:,} rows")
                except Exception as e:
                    print(f"  {schema}.{table}: Error - {e}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    check_teradata_schema()