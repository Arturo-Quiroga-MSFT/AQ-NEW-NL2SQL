"""
Quick script to execute TERADATA-FI DDL scripts using pyodbc
Handles GO batch separators properly
"""

import pyodbc
import os

# Connection string - update with your credentials from credentials.json
CONNECTION_STRING = """
    DRIVER={ODBC Driver 18 for SQL Server};
    SERVER=aqsqlserver001.database.windows.net;
    DATABASE=TERADATA-FI;
    Encrypt=yes;
    TrustServerCertificate=no;
    Connection Timeout=30;
"""

def execute_sql_file_with_go(cursor, filepath):
    """Execute SQL file splitting on GO statements"""
    with open(filepath, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Split on GO statements (case-insensitive, with optional whitespace)
    import re
    batches = re.split(r'^\s*GO\s*$', sql_content, flags=re.MULTILINE | re.IGNORECASE)
    
    executed = 0
    for i, batch in enumerate(batches, 1):
        batch = batch.strip()
        if not batch or batch.startswith('--'):
            continue
        
        try:
            cursor.execute(batch)
            executed += 1
            print(f"  ✓ Batch {i} executed")
        except Exception as e:
            if "already exists" in str(e) or "There is already" in str(e):
                print(f"  ⊙ Batch {i} skipped (already exists)")
            else:
                print(f"  ✗ Batch {i} failed: {e}")
                raise
    
    return executed

def main():
    print("\n" + "="*60)
    print("TERADATA-FI DDL Execution via pyodbc")
    print("="*60 + "\n")
    
    # Load credentials
    import json
    creds_path = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
    
    try:
        with open(creds_path, 'r') as f:
            creds = json.load(f)
        
        conn_str = CONNECTION_STRING.replace('Encrypt=yes;', f"""
            UID={creds['username']};
            PWD={creds['password']};
            Encrypt=yes;
        """)
        
        print("✓ Credentials loaded from credentials.json\n")
    except Exception as e:
        print(f"Warning: Could not load credentials.json: {e}")
        print("Using connection string as-is (may need manual authentication)\n")
        conn_str = CONNECTION_STRING
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print("✓ Connected to TERADATA-FI database\n")
        
        # Execute dimension tables DDL
        print("Creating dimension tables...")
        dim_file = os.path.join(os.path.dirname(__file__), 'teradata_fi_phase1_dimensions.sql')
        executed = execute_sql_file_with_go(cursor, dim_file)
        conn.commit()
        print(f"✓ Dimension tables script executed ({executed} batches)\n")
        
        # Execute fact tables DDL
        print("Creating fact tables...")
        fact_file = os.path.join(os.path.dirname(__file__), 'teradata_fi_phase1_facts.sql')
        executed = execute_sql_file_with_go(cursor, fact_file)
        conn.commit()
        print(f"✓ Fact tables script executed ({executed} batches)\n")
        
        # Verify tables created
        cursor.execute("""
            SELECT s.name AS SchemaName, COUNT(*) AS TableCount
            FROM sys.tables t
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE s.name IN ('dim', 'fact', 'bridge', 'ref')
            GROUP BY s.name
            ORDER BY s.name
        """)
        
        print("="*60)
        print("Table counts by schema:")
        print("="*60)
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} tables")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✅ Phase 1 DDL execution complete!")
        print("="*60)
        print("\nNext step: Run generate_teradata_fi_data.py to seed data\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
