#!/usr/bin/env python3
"""
SQL Server Authentication Test - Test user authentication without database
"""

import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def test_server_connection():
    """Test connection to SQL Server without specifying database"""
    server = os.getenv("AZURE_SQL_SERVER")
    username = os.getenv("AZURE_SQL_USER")
    password = os.getenv("AZURE_SQL_PASSWORD")
    
    print("Testing SQL Server Authentication (no database specified)...")
    print(f"Server: {server}")
    print(f"Username: {username}")
    print()
    
    # Connect to master database first (default)
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
            
            print("✅ Successfully authenticated to SQL Server!")
            
            # Check what databases this user can see
            cursor.execute("""
                SELECT name 
                FROM sys.databases 
                WHERE HAS_DBACCESS(name) = 1
                ORDER BY name
            """)
            
            accessible_dbs = [row[0] for row in cursor.fetchall()]
            print(f"Databases accessible to user '{username}':")
            for db in accessible_dbs:
                print(f"  - {db}")
            
            # Check if TERADATA-FI is in the list
            target_db = os.getenv("AZURE_SQL_DB")
            if target_db in accessible_dbs:
                print(f"\n✅ Target database '{target_db}' is accessible!")
                return test_specific_database()
            else:
                print(f"\n❌ Target database '{target_db}' is NOT accessible to this user")
                print("This is the root cause of your connection issue.")
                print()
                print("Solutions:")
                print(f"1. Grant user '{username}' access to database '{target_db}'")
                print("2. Use a different user that has access to this database")
                print("3. Verify the database name is correct (case sensitive)")
                return False
                
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        error_str = str(e).lower()
        
        if "login failed" in error_str:
            print("\nThis indicates the username/password combination is invalid.")
            print("Possible issues:")
            print(f"1. Username '{username}' doesn't exist")
            print("2. Password is incorrect")
            print("3. User might be disabled")
            print("4. Try using full format: username@servername")
        
        return False

def test_specific_database():
    """Test connection to specific database"""
    server = os.getenv("AZURE_SQL_SERVER")
    database = os.getenv("AZURE_SQL_DB")
    username = os.getenv("AZURE_SQL_USER")
    password = os.getenv("AZURE_SQL_PASSWORD")
    
    print(f"\nTesting direct connection to database '{database}'...")
    
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
            cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES")
            table_count = cursor.fetchone()[0]
            print(f"✅ Successfully connected to '{database}'!")
            print(f"   Found {table_count} tables")
            return True
            
    except Exception as e:
        print(f"❌ Connection to '{database}' failed: {e}")
        return False

if __name__ == "__main__":
    test_server_connection()