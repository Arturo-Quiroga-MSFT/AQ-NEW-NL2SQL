#!/usr/bin/env python3
"""
Standalone SQL Database Connection Test

This script tests ONLY the SQL database connection using the same credentials
as your Azure Container App. Use this to diagnose connection issues.

Usage:
    python test_sql_connection.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_sql_connection():
    """Test Azure SQL Database connection with detailed diagnostics."""
    print("=" * 60)
    print("SQL DATABASE CONNECTION TEST")
    print("=" * 60)
    
    # Get connection parameters
    server = os.getenv("AZURE_SQL_SERVER")
    database = os.getenv("AZURE_SQL_DB") 
    username = os.getenv("AZURE_SQL_USER")
    password = os.getenv("AZURE_SQL_PASSWORD")
    
    print(f"Server: {server}")
    print(f"Database: {database}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password) if password else 'NOT SET'}")
    print()
    
    # Check if all required vars are set
    missing = []
    if not server: missing.append("AZURE_SQL_SERVER")
    if not database: missing.append("AZURE_SQL_DB")
    if not username: missing.append("AZURE_SQL_USER") 
    if not password: missing.append("AZURE_SQL_PASSWORD")
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("Please set these in your .env file or environment")
        return False
    
    # Test pyodbc import
    try:
        import pyodbc
        print("✅ pyodbc imported successfully")
    except ImportError:
        print("❌ pyodbc not available. Run: pip install pyodbc")
        return False
    
    # List available ODBC drivers
    print(f"Available ODBC drivers: {', '.join(pyodbc.drivers())}")
    
    # Test connection with different configurations
    test_configs = [
        {
            "name": "Standard Connection",
            "conn_str": (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"UID={username};PWD={password};"
                "Encrypt=yes;TrustServerCertificate=yes;"
            )
        },
        {
            "name": "Connection without TrustServerCertificate",
            "conn_str": (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"UID={username};PWD={password};"
                "Encrypt=yes;"
            )
        },
        {
            "name": "Connection with Connection Timeout",
            "conn_str": (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"UID={username};PWD={password};"
                "Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=30;"
            )
        }
    ]
    
    for config in test_configs:
        print(f"\nTesting: {config['name']}")
        print("-" * 40)
        
        try:
            with pyodbc.connect(config['conn_str'], timeout=10) as conn:
                cursor = conn.cursor()
                
                # Test basic query
                cursor.execute("SELECT @@VERSION, GETDATE(), USER_NAME()")
                row = cursor.fetchone()
                
                print(f"✅ Connection successful!")
                print(f"   SQL Server: {row[0].split()[0]} {row[0].split()[3]}")
                print(f"   Current time: {row[1]}")
                print(f"   Connected as: {row[2]}")
                
                # Test database access
                cursor.execute("SELECT DB_NAME()")
                db_name = cursor.fetchone()[0]
                print(f"   Current database: {db_name}")
                
                # Test table access
                cursor.execute("""
                    SELECT COUNT(*) as table_count 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_TYPE = 'BASE TABLE'
                """)
                table_count = cursor.fetchone()[0]
                print(f"   Tables accessible: {table_count}")
                
                return True
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            
            # Provide specific error guidance
            error_str = str(e).lower()
            if "login failed" in error_str:
                print("   → Check username and password")
                print("   → Verify user exists and has access to the database")
            elif "cannot open database" in error_str:
                print("   → Check database name is correct")
                print("   → Verify user has access to this specific database")
            elif "timeout" in error_str:
                print("   → Check firewall rules")
                print("   → Verify server name and network connectivity")
            elif "ssl" in error_str or "certificate" in error_str:
                print("   → Try with TrustServerCertificate=yes")
            
            continue
    
    print(f"\n❌ All connection attempts failed")
    print("\nTroubleshooting steps:")
    print("1. Verify server name ends with .database.windows.net")
    print("2. Check database name is exactly correct (case sensitive)")
    print("3. Confirm username format (could be 'user' or 'user@server')")
    print("4. Verify password is correct")
    print("5. Check Azure SQL firewall rules allow your IP")
    print("6. Test connection from Azure portal Query Editor")
    
    return False


def test_container_app_env():
    """Test the same environment variables that Container App would use."""
    print("\n" + "=" * 60)
    print("CONTAINER APP ENVIRONMENT SIMULATION")
    print("=" * 60)
    
    # These are the environment variable names used in Container Apps
    container_vars = {
        "AZURE_SQL_SERVER": os.getenv("AZURE_SQL_SERVER"),
        "AZURE_SQL_DB": os.getenv("AZURE_SQL_DB"), 
        "AZURE_SQL_USER": os.getenv("AZURE_SQL_USER"),
        "AZURE_SQL_PASSWORD": os.getenv("AZURE_SQL_PASSWORD")
    }
    
    print("Environment variables as Container App would see them:")
    for var_name, var_value in container_vars.items():
        if var_value:
            display_value = var_value if "PASSWORD" not in var_name else "*" * 8
            print(f"  {var_name}={display_value}")
        else:
            print(f"  {var_name}=NOT SET")
    
    # Test using the exact same connection string format as the app
    print(f"\nUsing Container App connection format...")
    return test_sql_connection()


if __name__ == "__main__":
    print("SQL Database Connection Diagnostic Tool")
    print("This will test the same database connection used by your Container App\n")
    
    success = test_sql_connection()
    
    if success:
        print(f"\n🎉 SUCCESS: Database connection is working!")
        print("If your Container App still can't connect, the issue might be:")
        print("  - Environment variables not properly set in Container App")
        print("  - Container App using different credentials")
        print("  - Network/firewall differences between your machine and Container App")
    else:
        print(f"\n❌ FAILED: Database connection is not working")
        print("Fix these issues before your Container App will work")
    
    sys.exit(0 if success else 1)