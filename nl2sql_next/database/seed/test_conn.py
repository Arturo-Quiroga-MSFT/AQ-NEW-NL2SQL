"""Test different connection methods to diagnose timeout."""
import struct, pyodbc, os, sys
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
server = os.getenv("AZURE_SQL_SERVER")
db = os.getenv("AZURE_SQL_DB")

print(f"Server: {server}")
print(f"Database: {db}")

# 1. Verify token acquisition
print("\n--- Step 1: Acquire token ---")
cred = AzureCliCredential()
tok = cred.get_token("https://database.windows.net/.default")
print(f"Token acquired, length={len(tok.token)}, expires={tok.expires_on}")

# 2. Try ActiveDirectoryDefault (uses DefaultAzureCredential under the hood)
print("\n--- Step 2: Try ActiveDirectoryDefault auth ---")
try:
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={db};"
        f"Authentication=ActiveDirectoryDefault;"
        f"Connection Timeout=30;"
    )
    print(f"Connecting...")
    conn = pyodbc.connect(conn_str)
    print("SUCCESS with ActiveDirectoryDefault!")
    cur = conn.cursor()
    cur.execute("SELECT 1 AS test")
    print(f"Query result: {cur.fetchone()[0]}")
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"FAILED: {e}")

# 3. Try raw token with longer timeout
print("\n--- Step 3: Try raw token with 60s timeout ---")
try:
    tb = tok.token.encode("utf-16-le")
    ts = struct.pack(f"<I{len(tb)}s", len(tb), tb)
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={db};"
        f"Connection Timeout=60;"
    )
    print(f"Connecting with raw token...")
    conn = pyodbc.connect(conn_str, attrs_before={1256: ts})
    print("SUCCESS with raw token!")
    cur = conn.cursor()
    cur.execute("SELECT 1 AS test")
    print(f"Query result: {cur.fetchone()[0]}")
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"FAILED: {e}")

print("\nAll methods failed.")
