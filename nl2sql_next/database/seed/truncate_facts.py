"""Truncate all fact tables and reseed identity columns."""
import struct, pyodbc, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

cred = AzureCliCredential()
tok = cred.get_token("https://database.windows.net/.default")
tb = tok.token.encode("utf-16-le")
ts = struct.pack(f"<I{len(tb)}s", len(tb), tb)

srv = os.getenv("AZURE_SQL_SERVER")
db  = os.getenv("AZURE_SQL_DB")
conn = pyodbc.connect(
    f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={srv};DATABASE={db};",
    attrs_before={1256: ts}, autocommit=True
)
cur = conn.cursor()

tables = [
    "fact.FactOrders",
    "fact.FactReturns",
    "fact.FactCustomerReview",
    "fact.FactWebTraffic",
    "fact.FactInventory",
]

for tbl in tables:
    cur.execute(f"TRUNCATE TABLE {tbl}")
    print(f"  Truncated {tbl}")

for tbl in tables:
    cur.execute(f"DBCC CHECKIDENT ('{tbl}', RESEED, 0)")

conn.close()
print("Done – all fact tables cleared and identity columns reseeded.")
