"""Additive seeder: bulk-insert FactOrders + FactReturns rows.

Reads current max IDs so it picks up without conflicts.
Targets:
  - FactOrders:  ~16,000 new rows  → ~20K total
  - FactReturns: ~1,900 new rows   → ~2K total  (~10% return rate)

Usage:
    cd nl2sql_next
    source ../.venv/bin/activate
    python database/seed/seed_orders_returns_boost.py
"""
from __future__ import annotations

import os
import random
import struct
import sys

import numpy as np
import pyodbc
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

# ── paths & env ──────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
load_dotenv(os.path.join(_ROOT, ".env"))

SERVER = os.getenv("AZURE_SQL_SERVER", "")
DATABASE = os.getenv("AZURE_SQL_DB", "")
SEED = 9999  # different from original so we get new patterns
random.seed(SEED)
np.random.seed(SEED)

# ── config ───────────────────────────────────────────────
TARGET_NEW_ORDER_ROWS = 16_000  # line items
TARGET_ORDERS = 5_500           # distinct orders (~2.9 lines each)
N_CUSTOMERS = 3_000
N_PRODUCTS = 500
N_STORES = 25
N_PROMOS = 30
N_SHIP = 5
N_PAY = 8
N_RETURN_REASONS = 8


# ── connection ───────────────────────────────────────────
def get_connection() -> pyodbc.Connection:
    cred = AzureCliCredential()
    token = cred.get_token("https://database.windows.net/.default")
    tb = token.token.encode("utf-16-le")
    ts = struct.pack(f"<I{len(tb)}s", len(tb), tb)
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};",
        attrs_before={1256: ts},
        autocommit=True,
    )


def bulk_insert(conn: pyodbc.Connection, table: str, columns: list[str], rows: list[tuple]) -> int:
    if not rows:
        return 0
    placeholders = ",".join(["?"] * len(columns))
    col_list = ",".join(columns)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
    cursor = conn.cursor()
    cursor.fast_executemany = True
    BATCH = 500
    total = 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i : i + BATCH]
        cursor.executemany(sql, batch)
        total += len(batch)
        if total % 2000 == 0 or total == len(rows):
            print(f"    {table}: {total:,}/{len(rows):,} rows inserted", end="\r")
    cursor.close()
    print()
    return len(rows)


# ── helpers ──────────────────────────────────────────────
def get_date_keys(conn: pyodbc.Connection) -> list[int]:
    cur = conn.cursor()
    cur.execute("SELECT DateKey FROM dim.DimDate ORDER BY DateKey")
    keys = [row[0] for row in cur.fetchall()]
    cur.close()
    return keys


def get_max_order_num(conn: pyodbc.Connection) -> int:
    cur = conn.cursor()
    cur.execute("SELECT MAX(CAST(REPLACE(OrderId, 'ORD-', '') AS INT)) FROM fact.FactOrders")
    val = cur.fetchone()[0]
    cur.close()
    return val or 0


def get_max_return_num(conn: pyodbc.Connection) -> int:
    cur = conn.cursor()
    cur.execute("SELECT MAX(CAST(REPLACE(ReturnId, 'RET-', '') AS INT)) FROM fact.FactReturns")
    val = cur.fetchone()[0]
    cur.close()
    return val or 0


def get_count(conn: pyodbc.Connection, table: str) -> int:
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    val = cur.fetchone()[0]
    cur.close()
    return val


# ── generators ───────────────────────────────────────────
def gen_orders_and_returns(
    date_keys: list[int],
    start_order_num: int,
    start_return_num: int,
) -> tuple[list[tuple], list[tuple]]:
    order_rows: list[tuple] = []
    return_rows: list[tuple] = []
    order_counter = start_order_num
    return_counter = start_return_num

    statuses = ["Completed"] * 85 + ["Cancelled"] * 5 + ["Returned"] * 10

    # Weight dates toward later years – simulate business growth
    date_weights = np.array([(dk - 20220000) for dk in date_keys], dtype=float)
    date_weights = date_weights / date_weights.sum()
    dk_idx = {dk: i for i, dk in enumerate(date_keys)}

    for _ in range(TARGET_ORDERS):
        order_counter += 1
        oid = f"ORD-{order_counter:06d}"
        cust_key = random.randint(1, N_CUSTOMERS)
        store_key = random.randint(1, N_STORES)
        date_key = int(np.random.choice(date_keys, p=date_weights))
        idx = dk_idx[date_key]
        ship_idx = min(idx + random.randint(1, 10), len(date_keys) - 1)
        ship_dk = date_keys[ship_idx]
        pay_key = random.randint(1, N_PAY)
        promo_key = random.randint(1, N_PROMOS) if random.random() < 0.35 else None
        ship_key = random.randint(1, N_SHIP)
        status = random.choice(statuses)

        n_lines = random.choices([1, 2, 3, 4, 5], weights=[40, 30, 15, 10, 5])[0]
        for ln in range(1, n_lines + 1):
            prod_key = random.randint(1, N_PRODUCTS)
            qty = random.choices([1, 2, 3, 4], weights=[60, 25, 10, 5])[0]
            unit_price = round(random.uniform(5, 500), 2)
            unit_cost = round(unit_price / random.uniform(1.3, 3.0), 2)
            disc = round(unit_price * qty * random.uniform(0, 0.15), 2) if promo_key else 0
            ship_cost = round(random.uniform(0, 15), 2) if ship_key != 5 else 0
            tax = round((unit_price * qty - disc) * 0.08, 2)
            line_total = round(unit_price * qty - disc, 2)
            line_cost = round(unit_cost * qty, 2)
            line_profit = round(line_total - line_cost - ship_cost, 2)
            is_returned = 1 if status == "Returned" and random.random() < 0.6 else 0

            order_rows.append((
                oid, ln, cust_key, prod_key, date_key, ship_dk,
                store_key, promo_key, ship_key, pay_key,
                qty, unit_price, unit_cost, disc, ship_cost, tax,
                line_total, line_cost, line_profit,
                status, is_returned,
            ))

            if is_returned:
                return_counter += 1
                ret_idx = min(dk_idx[date_key] + random.randint(5, 30), len(date_keys) - 1)
                ret_date = date_keys[ret_idx]
                return_rows.append((
                    f"RET-{return_counter:06d}", oid, ln,
                    cust_key, prod_key, ret_date, store_key,
                    random.randint(1, N_RETURN_REASONS),
                    qty, round(line_total * 0.95, 2),
                    random.choice(["Approved", "Approved", "Pending"]),
                    1 if random.random() < 0.9 else 0,
                ))

    return order_rows, return_rows


# ── main ─────────────────────────────────────────────────
def main() -> None:
    print(f"Connecting to {DATABASE} on {SERVER} ...")
    conn = get_connection()

    # Current counts
    cur_orders = get_count(conn, "fact.FactOrders")
    cur_returns = get_count(conn, "fact.FactReturns")
    print(f"Current counts: FactOrders={cur_orders:,}  FactReturns={cur_returns:,}")

    # Get date keys and max IDs
    date_keys = get_date_keys(conn)
    max_ord = get_max_order_num(conn)
    max_ret = get_max_return_num(conn)
    print(f"Max OrderId num: {max_ord}  Max ReturnId num: {max_ret}")
    print(f"Generating ~{TARGET_ORDERS:,} new orders (~{TARGET_NEW_ORDER_ROWS:,} line items) ...")

    order_rows, return_rows = gen_orders_and_returns(date_keys, max_ord, max_ret)
    print(f"Generated {len(order_rows):,} order lines, {len(return_rows):,} return rows")

    print("\nInserting FactOrders ...")
    n = bulk_insert(conn, "fact.FactOrders",
        ["OrderId", "LineNumber", "CustomerKey", "ProductKey", "OrderDateKey",
         "ShipDateKey", "StoreKey", "PromotionKey", "ShippingMethodKey",
         "PaymentMethodKey", "Quantity", "UnitPrice", "UnitCost",
         "DiscountAmount", "ShippingCost", "TaxAmount", "LineTotal",
         "LineCost", "LineProfit", "OrderStatus", "IsReturned"],
        order_rows)
    print(f"  Inserted {n:,} rows")

    print("Inserting FactReturns ...")
    n = bulk_insert(conn, "fact.FactReturns",
        ["ReturnId", "OrderId", "LineNumber", "CustomerKey", "ProductKey",
         "ReturnDateKey", "StoreKey", "ReturnReasonKey", "Quantity",
         "RefundAmount", "ReturnStatus", "IsRefunded"],
        return_rows)
    print(f"  Inserted {n:,} rows")

    # Final counts
    new_orders = get_count(conn, "fact.FactOrders")
    new_returns = get_count(conn, "fact.FactReturns")
    print(f"\nFinal counts: FactOrders={new_orders:,}  FactReturns={new_returns:,}")
    print(f"Added: +{new_orders - cur_orders:,} order lines, +{new_returns - cur_returns:,} returns")

    conn.close()
    print("\n=== Done! ===")


if __name__ == "__main__":
    main()
