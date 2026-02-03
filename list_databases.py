#!/usr/bin/env python3
"""
List all databases on the SQL Server to verify TERADATA-FI exists
"""

import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def list_all_databases():
    """List all databases on the SQL Server"""
    server = os.getenv("AZURE_SQL_SERVER")
    username = os.getenv("AZURE_SQL_USER")
    password = os.getenv("AZURE_SQL_PASSWORD")
    
    print("Listing all databases on SQL Server...")
    print(f"Server: {server}")
    print()
    
    # Connect to master database to list all databases
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE=master;"
        f"UID={username};PWD={password};"
        "Encrypt=yes;TrustServerCertificate=yes;"
    )
    
    try:
        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.cursor()
            
            # List all databases (this user can see)
            cursor.execute("""
                SELECT name, database_id, create_date
                FROM sys.databases 
                ORDER BY name
            """)
            
            print("All databases on this server:")
            print("-" * 50)
            databases = []
            for row in cursor.fetchall():
                db_name, db_id, create_date = row
                databases.append(db_name)
                print(f"  {db_name} (ID: {db_id}, Created: {create_date.strftime('%Y-%m-%d')})")
            
            print()
            target_db = os.getenv("AZURE_SQL_DB")
            if target_db in databases:
                print(f"✅ Target database '{target_db}' EXISTS on the server")
                print("   The issue is user permissions, not database existence")
            else:
                print(f"❌ Target database '{target_db}' does NOT exist on the server")
                print("   Possible solutions:")
                print(f"   1. Create the '{target_db}' database")
                print("   2. Use one of the existing databases above")
                print("   3. Check if the database name has different casing")
                
                # Check for similar names
                similar = [db for db in databases if 'TERADATA' in db.upper() or 'FI' in db.upper()]
                if similar:
                    print(f"   Similar database names found: {', '.join(similar)}")
            
            return databases
                
    except Exception as e:
        print(f"❌ Failed to list databases: {e}")
        return []

if __name__ == "__main__":
    list_all_databases()