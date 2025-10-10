#!/usr/bin/env python3
"""
Quick setup test for nl2sql_azureai_universal

This script verifies:
1. All required environment variables are set
2. Azure SQL Database connection works
3. Schema can be read
4. Azure AI Foundry connection works

Run this before using nl2sql_main.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

def check_env_vars():
    """Check if all required environment variables are set."""
    print("Checking environment variables...")
    required_vars = [
        "PROJECT_ENDPOINT",
        "MODEL_DEPLOYMENT_NAME",
        "AZURE_SQL_SERVER",
        "AZURE_SQL_DB",
        "AZURE_SQL_USER",
        "AZURE_SQL_PASSWORD",
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
            print(f"  ❌ {var}: NOT SET")
        else:
            # Mask password
            if "PASSWORD" in var or "SECRET" in var:
                display_value = "*" * 8
            else:
                display_value = value[:50] + ("..." if len(value) > 50 else "")
            print(f"  ✅ {var}: {display_value}")
    
    if missing:
        print(f"\n❌ Missing required environment variables: {', '.join(missing)}")
        print("Please copy .env.example to .env and fill in your values.")
        return False
    
    print("✅ All required environment variables are set\n")
    return True


def check_azure_sql():
    """Test Azure SQL Database connection."""
    print("Testing Azure SQL Database connection...")
    try:
        import pyodbc
        
        server = os.getenv("AZURE_SQL_SERVER")
        database = os.getenv("AZURE_SQL_DB")
        username = os.getenv("AZURE_SQL_USER")
        password = os.getenv("AZURE_SQL_PASSWORD")
        
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};PWD={password};"
            "Encrypt=yes;TrustServerCertificate=yes;"
        )
        
        with pyodbc.connect(conn_str, timeout=5) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            print(f"  ✅ Connected to: {database} on {server}")
            print(f"  ✅ SQL Server version: {version.split()[0]} {version.split()[3]}")
        
        print("✅ Azure SQL Database connection successful\n")
        return True
        
    except ImportError:
        print("  ❌ pyodbc not installed. Run: pip install pyodbc")
        return False
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Check your server name (should end with .database.windows.net)")
        print("  2. Verify your username and password")
        print("  3. Ensure the database name is correct")
        print("  4. Check firewall rules allow your IP address")
        return False


def check_schema_reader():
    """Test schema reader."""
    print("Testing schema reader...")
    try:
        from schema_reader import refresh_schema_cache, get_table_list, get_view_list
        
        # Refresh schema
        print("  Refreshing schema cache...")
        cache_path = refresh_schema_cache()
        print(f"  ✅ Schema cached to: {cache_path}")
        
        # Get tables
        tables = get_table_list()
        views = get_view_list()
        print(f"  ✅ Found {len(tables)} tables and {len(views)} views")
        
        if tables:
            print(f"  Sample tables: {', '.join(tables[:5])}")
        if views:
            print(f"  Sample views: {', '.join(views[:5])}")
        
        print("✅ Schema reader working correctly\n")
        return True
        
    except Exception as e:
        print(f"  ❌ Schema reader failed: {e}")
        return False


def check_azure_ai():
    """Test Azure AI Foundry connection."""
    print("Testing Azure AI Foundry connection...")
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
        
        endpoint = os.getenv("PROJECT_ENDPOINT")
        model = os.getenv("MODEL_DEPLOYMENT_NAME")
        
        print(f"  Connecting to: {endpoint}")
        print(f"  Using model: {model}")
        
        # Try to create client
        credential = DefaultAzureCredential()
        client = AIProjectClient(endpoint=endpoint, credential=credential)
        
        print("  ✅ Azure AI Foundry client created successfully")
        print("\n⚠️  Note: Full validation requires creating an agent, which is done by nl2sql_main.py")
        print("✅ Azure AI Foundry basic connection successful\n")
        return True
        
    except ImportError as e:
        print(f"  ❌ Missing required packages: {e}")
        print("  Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"  ❌ Azure AI Foundry connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure you're authenticated: run 'az login'")
        print("  2. Check PROJECT_ENDPOINT is correct (from Azure AI Foundry)")
        print("  3. Verify MODEL_DEPLOYMENT_NAME matches your deployment")
        print("  4. Ensure you have access to the AI Foundry project")
        return False


def main():
    print("=" * 60)
    print("NL2SQL Azure AI Universal - Setup Test")
    print("=" * 60)
    print()
    
    # Run all checks
    checks = [
        ("Environment Variables", check_env_vars),
        ("Azure SQL Database", check_azure_sql),
        ("Schema Reader", check_schema_reader),
        ("Azure AI Foundry", check_azure_ai),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ {name} check failed with error: {e}\n")
            results[name] = False
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    print()
    if all(results.values()):
        print("🎉 All checks passed! You're ready to use nl2sql_main.py")
        print("\nTry running:")
        print('  python nl2sql_main.py --query "How many records are there?"')
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
