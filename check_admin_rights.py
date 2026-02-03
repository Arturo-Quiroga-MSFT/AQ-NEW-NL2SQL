#!/usr/bin/env python3
"""
SQL Server Admin Rights Diagnostic Test
"""

import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def check_admin_rights():
    """Check if the user has admin rights and what's blocking database access"""
    server = os.getenv("AZURE_SQL_SERVER")
    username = os.getenv("AZURE_SQL_USER")
    password = os.getenv("AZURE_SQL_PASSWORD")
    
    print("=" * 60)
    print("SQL SERVER ADMIN RIGHTS DIAGNOSTIC")
    print("=" * 60)
    print(f"Server: {server}")
    print(f"Username: {username}")
    print()
    
    # Connect to master database to check admin status
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
            
            print("✅ Connected to master database")
            
            # Check if user is sysadmin
            cursor.execute("SELECT IS_SRVROLEMEMBER('sysadmin')")
            is_sysadmin = cursor.fetchone()[0]
            print(f"Is sysadmin: {'✅ YES' if is_sysadmin else '❌ NO'}")
            
            # Check server roles
            cursor.execute("""
                SELECT r.name as role_name
                FROM sys.server_role_members rm
                JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
                JOIN sys.server_principals m ON rm.member_principal_id = m.principal_id
                WHERE m.name = ?
            """, username)
            
            server_roles = [row[0] for row in cursor.fetchall()]
            print(f"Server roles: {', '.join(server_roles) if server_roles else 'None'}")
            
            # Check all databases (even if not accessible)
            cursor.execute("SELECT name, database_id FROM sys.databases ORDER BY name")
            all_databases = cursor.fetchall()
            
            print(f"\nAll databases on server:")
            for db_name, db_id in all_databases:
                print(f"  - {db_name} (ID: {db_id})")
            
            # Check database access specifically
            print(f"\nDatabase access check:")
            cursor.execute("""
                SELECT name, 
                       HAS_DBACCESS(name) as has_access,
                       CASE 
                           WHEN state = 0 THEN 'ONLINE'
                           WHEN state = 1 THEN 'RESTORING'
                           WHEN state = 2 THEN 'RECOVERING'
                           WHEN state = 3 THEN 'RECOVERY_PENDING'
                           WHEN state = 4 THEN 'SUSPECT'
                           WHEN state = 5 THEN 'EMERGENCY'
                           WHEN state = 6 THEN 'OFFLINE'
                           ELSE 'UNKNOWN'
                       END as state
                FROM sys.databases 
                ORDER BY name
            """)
            
            for row in cursor.fetchall():
                db_name, has_access, state = row
                access_status = "✅ YES" if has_access else "❌ NO"
                print(f"  {db_name}: Access={access_status}, State={state}")
            
            # Try to check why TERADATA-FI specifically is not accessible
            target_db = "TERADATA-FI"
            print(f"\nSpecific check for '{target_db}':")
            
            try:
                # Try to use the database
                cursor.execute(f"USE [{target_db}]")
                print(f"✅ Successfully switched to {target_db}")
                
                # Check user permissions in this database
                cursor.execute("SELECT USER_NAME(), ORIGINAL_LOGIN()")
                user_info = cursor.fetchone()
                print(f"  Database user: {user_info[0]}")
                print(f"  Original login: {user_info[1]}")
                
            except Exception as e:
                print(f"❌ Cannot access {target_db}: {e}")
                
                # Check if database exists but is in bad state
                cursor.execute("""
                    SELECT name, state_desc, user_access_desc 
                    FROM sys.databases 
                    WHERE name = ?
                """, target_db)
                
                db_info = cursor.fetchone()
                if db_info:
                    print(f"  Database state: {db_info[1]}")
                    print(f"  User access: {db_info[2]}")
                else:
                    print(f"  Database '{target_db}' not found!")
            
            return True
            
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False

def test_direct_connection():
    """Try direct connection to TERADATA-FI with more detailed error info"""
    server = os.getenv("AZURE_SQL_SERVER")
    database = "TERADATA-FI"
    username = os.getenv("AZURE_SQL_USER")
    password = os.getenv("AZURE_SQL_PASSWORD")
    
    print(f"\n" + "=" * 60)
    print(f"DIRECT CONNECTION TEST TO {database}")
    print("=" * 60)
    
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
            cursor.execute("SELECT DB_NAME(), USER_NAME(), GETDATE()")
            result = cursor.fetchone()
            print(f"✅ Successfully connected to {database}!")
            print(f"  Current database: {result[0]}")
            print(f"  Current user: {result[1]}")
            print(f"  Server time: {result[2]}")
            return True
            
    except Exception as e:
        print(f"❌ Direct connection failed: {e}")
        
        # Parse the error for more specific info
        error_msg = str(e)
        if "42000" in error_msg and "Cannot open database" in error_msg:
            print("\nThis suggests one of these issues:")
            print("1. Database is in RESTORING, OFFLINE, or SUSPECT state")
            print("2. Database was recently renamed and hasn't fully updated")
            print("3. There's a contained database user issue")
            print("4. Azure SQL logical server firewall issue")
        
        return False

if __name__ == "__main__":
    print("SQL Server Admin Rights Diagnostic Tool")
    print("This will check why an admin user cannot access databases\n")
    
    success1 = check_admin_rights()
    success2 = test_direct_connection()
    
    if not success1 or not success2:
        print(f"\n🔍 INVESTIGATION SUMMARY:")
        print("If you are truly the SQL Server admin but cannot access TERADATA-FI:")
        print("1. Check if database is ONLINE in Azure Portal")
        print("2. Verify database wasn't corrupted during rename")
        print("3. Check Azure SQL Server firewall rules")
        print("4. Try connecting via Azure Portal Query Editor")
        print("5. Check if there are contained database users configured")