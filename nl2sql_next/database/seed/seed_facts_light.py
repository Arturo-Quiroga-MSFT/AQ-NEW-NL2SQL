"""Resilient fact seeder — small batches, retries, fresh connections.

Reduced volumes suitable for NL2SQL testing:
  FactOrders:         ~3,500 line items  (1,000 orders x ~3.5 avg lines)
  FactReturns:        ~100 returns
  FactCustomerReview: 500 reviews
  FactWebTraffic:     1,000 sessions
  FactInventory:      ~4,500 snapshots
"""
import os, sys, struct, random, time
import numpy as np
import pyodbc
from azure.identity import AzureCliCredential
from dotenv import load_dotenv
from faker import Faker

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
load_dotenv(os.path.join(_ROOT, ".env"))

SERVER = os.getenv("AZURE_SQL_SERVER", "")
DATABASE = os.getenv("AZURE_SQL_DB", "")
SEED = 42
fake = Faker("en_US"); Faker.seed(SEED); random.seed(SEED); np.random.seed(SEED)

BATCH = 200  # small batches to avoid TCP timeouts
MAX_RETRIES = 3


def get_connection() -> pyodbc.Connection:
    cred = AzureCliCredential()
    token = cred.get_token("https://database.windows.net/.default")
    tb = token.token.encode("utf-16-le")
    ts = struct.pack(f"<I{len(tb)}s", len(tb), tb)
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={SERVER};DATABASE={DATABASE};"
        f"Connection Timeout=30;",
        attrs_before={1256: ts},
        autocommit=True,
    )


def safe_insert(table: str, columns: list[str], rows: list[tuple]) -> int:
    """Insert with small batches, retry on failure, fresh connection per table."""
    if not rows:
        return 0
    placeholders = ",".join(["?"] * len(columns))
    col_list = ",".join(columns)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.fast_executemany = True
    inserted = 0

    for i in range(0, len(rows), BATCH):
        chunk = rows[i : i + BATCH]
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                cursor.executemany(sql, chunk)
                inserted += len(chunk)
                break
            except (pyodbc.OperationalError, pyodbc.Error) as e:
                print(f"    ⚠ batch {i//BATCH+1} attempt {attempt} failed: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(2 * attempt)
                    try:
                        cursor.close(); conn.close()
                    except Exception:
                        pass
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.fast_executemany = True
                else:
                    print(f"    ✗ batch {i//BATCH+1} SKIPPED after {MAX_RETRIES} retries")
        if (i // BATCH + 1) % 5 == 0:
            print(f"    ... {inserted}/{len(rows)} rows inserted")

    try:
        cursor.close(); conn.close()
    except Exception:
        pass
    return inserted


# ── date keys (must match DimDate) ──────────────────────
def get_date_keys():
    from datetime import date, timedelta
    start = date(2022, 1, 1)
    end = date(2025, 12, 31)
    keys = []
    d = start
    while d <= end:
        keys.append(d.year * 10000 + d.month * 100 + d.day)
        d += timedelta(days=1)
    return keys


# ── generators ──────────────────────────────────────────
def gen_orders(date_keys, dk_idx):
    order_rows, return_rows = [], []
    oc = rc = 0
    statuses = ["Completed"]*90 + ["Cancelled"]*5 + ["Returned"]*5
    weights = np.array([(dk - 20220000) for dk in date_keys], dtype=float)
    weights /= weights.sum()

    for _ in range(1_000):
        oc += 1
        oid = f"ORD-{oc:06d}"
        ck = random.randint(1, 3000)
        sk = random.randint(1, 25)
        dk = int(np.random.choice(date_keys, p=weights))
        idx = dk_idx[dk]
        ship_idx = min(idx + random.randint(1, 10), len(date_keys) - 1)
        ship_dk = date_keys[ship_idx]
        pay = random.randint(1, 8)
        promo = random.randint(1, 30) if random.random() < 0.35 else None
        ship = random.randint(1, 5)
        status = random.choice(statuses)

        for ln in range(1, random.choices([1,2,3,4,5], weights=[40,30,15,10,5])[0] + 1):
            pk = random.randint(1, 500)
            qty = random.choices([1,2,3,4], weights=[60,25,10,5])[0]
            up = round(random.uniform(5, 500), 2)
            uc = round(up / random.uniform(1.3, 3.0), 2)
            disc = round(up * qty * random.uniform(0, 0.15), 2) if promo else 0
            sc = round(random.uniform(0, 15), 2) if ship != 5 else 0
            tax = round((up * qty - disc) * 0.08, 2)
            lt = round(up * qty - disc, 2)
            lc = round(uc * qty, 2)
            lp = round(lt - lc - sc, 2)
            is_ret = 1 if status == "Returned" and random.random() < 0.6 else 0

            order_rows.append((
                oid, ln, ck, pk, dk, ship_dk, sk, promo, ship, pay,
                qty, up, uc, disc, sc, tax, lt, lc, lp, status, is_ret,
            ))
            if is_ret:
                rc += 1
                ri = min(dk_idx[dk] + random.randint(5, 30), len(date_keys) - 1)
                return_rows.append((
                    f"RET-{rc:06d}", oid, ln, ck, pk, date_keys[ri], sk,
                    random.randint(1, 8), qty, round(lt * 0.95, 2),
                    random.choice(["Approved","Approved","Pending"]),
                    1 if random.random() < 0.9 else 0,
                ))
    return order_rows, return_rows


def gen_reviews(date_keys):
    rows = []
    titles = ["Great product", "Not bad", "Terrible quality", "Love it!", "Meh",
              "Exceeded expectations", "Would not buy again", "Perfect gift",
              "Good value", "Disappointing"]
    for i in range(1, 501):
        r = random.randint(1, 5)
        rows.append((
            f"REV-{i:06d}", random.randint(1, 3000), random.randint(1, 500),
            random.choice(date_keys), r, random.randint(10, 2000),
            random.randint(0, 50), random.choice(titles),
            1 if random.random() < 0.7 else 0,
            round(min(1.0, max(-1.0, (r - 3) / 2 + random.gauss(0, 0.2))), 2),
        ))
    return rows


def gen_web(date_keys):
    sources = ["Google","Direct","Facebook","Email","Instagram","TikTok","Bing"]
    devices = ["Desktop","Mobile","Tablet"]
    browsers = ["Chrome","Safari","Firefox","Edge"]
    pages = ["/","category/electronics","category/clothing","deals","search"]
    rows = []
    for i in range(1, 1001):
        ck = random.randint(1, 3000) if random.random() < 0.6 else None
        pvs = max(1, int(np.random.lognormal(1.5, 0.8)))
        dur = max(5, int(np.random.lognormal(4, 1)))
        bounce = 1 if pvs == 1 else 0
        viewed = min(pvs, random.randint(0, 5))
        added = min(viewed, random.randint(0, 2))
        converted = 1 if added > 0 and random.random() < 0.3 else 0
        rows.append((
            f"SES-{i:07d}", ck, random.choice(date_keys), pvs, dur, bounce,
            viewed, added, converted, random.choice(sources),
            random.choice(devices), random.choice(browsers), random.choice(pages),
        ))
    return rows


def gen_inventory(date_keys):
    monthly = [dk for dk in date_keys if dk % 100 == 1]
    rows = []
    for dk in monthly:
        for store in range(1, 26):
            for prod in random.sample(range(1, 501), k=10):
                qh = max(0, int(np.random.lognormal(3, 1)))
                qo = random.randint(0, 50) if qh < 20 else 0
                rp = random.randint(10, 50)
                ucost = round(random.uniform(2, 400), 2)
                rows.append((prod, store, dk, qh, qo, rp, ucost, round(qh * ucost, 2)))
    return rows


# ── main ────────────────────────────────────────────────
def main():
    print(f"Connecting to {DATABASE} on {SERVER} ...")
    date_keys = get_date_keys()
    dk_idx = {dk: i for i, dk in enumerate(date_keys)}

    print("\n--- FactOrders ---")
    order_rows, return_rows = gen_orders(date_keys, dk_idx)
    n = safe_insert("fact.FactOrders",
        ["OrderId","LineNumber","CustomerKey","ProductKey","OrderDateKey",
         "ShipDateKey","StoreKey","PromotionKey","ShippingMethodKey",
         "PaymentMethodKey","Quantity","UnitPrice","UnitCost",
         "DiscountAmount","ShippingCost","TaxAmount","LineTotal",
         "LineCost","LineProfit","OrderStatus","IsReturned"],
        order_rows)
    print(f"  FactOrders: {n} rows")

    print("\n--- FactReturns ---")
    n = safe_insert("fact.FactReturns",
        ["ReturnId","OrderId","LineNumber","CustomerKey","ProductKey",
         "ReturnDateKey","StoreKey","ReturnReasonKey","Quantity",
         "RefundAmount","ReturnStatus","IsRefunded"],
        return_rows)
    print(f"  FactReturns: {n} rows")

    print("\n--- FactCustomerReview ---")
    review_rows = gen_reviews(date_keys)
    n = safe_insert("fact.FactCustomerReview",
        ["ReviewId","CustomerKey","ProductKey","ReviewDateKey","Rating",
         "ReviewLength","HelpfulVotes","ReviewTitle","IsVerifiedPurchase",
         "SentimentScore"],
        review_rows)
    print(f"  FactCustomerReview: {n} rows")

    print("\n--- FactWebTraffic ---")
    web_rows = gen_web(date_keys)
    n = safe_insert("fact.FactWebTraffic",
        ["SessionId","CustomerKey","VisitDateKey","PageViews",
         "SessionDurationSec","BounceFlag","ProductsViewed","AddedToCart",
         "ConvertedFlag","TrafficSource","DeviceType","Browser","LandingPage"],
        web_rows)
    print(f"  FactWebTraffic: {n} rows")

    print("\n--- FactInventory ---")
    inv_rows = gen_inventory(date_keys)
    n = safe_insert("fact.FactInventory",
        ["ProductKey","StoreKey","SnapshotDateKey","QuantityOnHand",
         "QuantityOnOrder","ReorderPoint","UnitCost","InventoryValue"],
        inv_rows)
    print(f"  FactInventory: {n} rows")

    print("\n=== Done! ===")


if __name__ == "__main__":
    main()
