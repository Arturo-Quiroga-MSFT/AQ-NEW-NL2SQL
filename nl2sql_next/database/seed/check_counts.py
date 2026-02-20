"""Quick row count check for all tables."""
import struct, pyodbc, os
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
cred = AzureCliCredential()
t = cred.get_token("https://database.windows.net/.default")
tb = t.token.encode("utf-16-le")
ts = struct.pack(f"<I{len(tb)}s", len(tb), tb)
conn = pyodbc.connect(
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={os.getenv('AZURE_SQL_SERVER')};"
    f"DATABASE={os.getenv('AZURE_SQL_DB')};"
    f"Connection Timeout=30;",
    attrs_before={1256: ts},
)
cur = conn.cursor()
tables = [
    "dim.DimDate","dim.DimCustomer","dim.DimProduct","dim.DimStore",
    "dim.DimPromotion","dim.DimShippingMethod","dim.DimPaymentMethod",
    "ref.RefReturnReason",
    "fact.FactOrders","fact.FactReturns","fact.FactCustomerReview",
    "fact.FactWebTraffic","fact.FactInventory",
]
for t_name in tables:
    cur.execute(f"SELECT COUNT(*) FROM {t_name}")
    print(f"  {t_name:<35} {cur.fetchone()[0]:>10,}")
conn.close()
