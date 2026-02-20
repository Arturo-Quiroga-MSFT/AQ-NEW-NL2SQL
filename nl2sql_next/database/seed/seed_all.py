"""Seed RetailDW with realistic synthetic data.

Generates and inserts:
  - DimDate          2022-01-01 → 2025-12-31  (1,461 rows)
  - DimCustomer      3,000 customers
  - DimProduct       500 products across 8 categories
  - DimStore         25 stores
  - DimPromotion     30 promotions
  - DimShippingMethod 5 methods
  - DimPaymentMethod  8 methods
  - RefReturnReason   8 reasons
  - FactOrders       ~120,000 order line items
  - FactReturns      ~6,000 returns  (~5% return rate)
  - FactCustomerReview ~15,000 reviews
  - FactWebTraffic   ~60,000 sessions
  - FactInventory    ~18,000 snapshots (monthly)

Usage:
    cd nl2sql_next
    python database/seed/seed_all.py
"""
from __future__ import annotations

import math
import os
import random
import struct
import sys
from datetime import date, datetime, timedelta
from typing import Any, List

import numpy as np
import pyodbc
from azure.identity import AzureCliCredential
from dotenv import load_dotenv
from faker import Faker

# ── paths & env ──────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
load_dotenv(os.path.join(_ROOT, ".env"))

SERVER = os.getenv("AZURE_SQL_SERVER", "")
DATABASE = os.getenv("AZURE_SQL_DB", "")
SEED = 42
fake = Faker("en_US")
Faker.seed(SEED)
random.seed(SEED)
np.random.seed(SEED)


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
    """Fast batch insert with executemany."""
    if not rows:
        return 0
    placeholders = ",".join(["?"] * len(columns))
    col_list = ",".join(columns)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
    cursor = conn.cursor()
    cursor.fast_executemany = True
    BATCH = 1000
    for i in range(0, len(rows), BATCH):
        cursor.executemany(sql, rows[i : i + BATCH])
    cursor.close()
    return len(rows)


# ── dimension generators ────────────────────────────────
US_REGIONS = {
    "Northeast": ["New York", "Massachusetts", "Pennsylvania", "Connecticut", "New Jersey"],
    "Southeast": ["Florida", "Georgia", "North Carolina", "Virginia", "Tennessee"],
    "Midwest": ["Illinois", "Ohio", "Michigan", "Minnesota", "Wisconsin"],
    "Southwest": ["Texas", "Arizona", "New Mexico", "Oklahoma", "Colorado"],
    "West": ["California", "Washington", "Oregon", "Nevada", "Utah"],
}
STATE_TO_REGION = {s: r for r, states in US_REGIONS.items() for s in states}

CATEGORIES = {
    "Electronics": ["Smartphones", "Laptops", "Tablets", "Headphones", "Cameras", "TVs"],
    "Clothing": ["Mens Shirts", "Womens Dresses", "Jeans", "Outerwear", "Activewear", "Accessories"],
    "Home & Kitchen": ["Cookware", "Small Appliances", "Bedding", "Furniture", "Decor"],
    "Sports & Outdoors": ["Fitness Equipment", "Camping", "Running", "Cycling", "Water Sports"],
    "Beauty": ["Skincare", "Haircare", "Makeup", "Fragrance"],
    "Books": ["Fiction", "Non-Fiction", "Children", "Textbooks"],
    "Toys & Games": ["Board Games", "Action Figures", "Puzzles", "Outdoor Toys", "Video Games"],
    "Grocery": ["Snacks", "Beverages", "Organic", "Pantry Staples"],
}

BRANDS_BY_CAT = {
    "Electronics": ["TechNova", "PixelCore", "SoundWave", "VoltEdge", "ClearView"],
    "Clothing": ["UrbanThread", "FitFlex", "NorthPeak", "ClassicStitch", "EcoWear"],
    "Home & Kitchen": ["NestCraft", "ChefLine", "ComfortPlus", "HavenHome", "PureSpace"],
    "Sports & Outdoors": ["TrailBoss", "Kinetic", "WaveRider", "SummitGear", "FlexForm"],
    "Beauty": ["GlowLab", "PureEssence", "VelvetSkin", "AuraBlend"],
    "Books": ["PageTurn Press", "Insight Books", "Rainbow Reads", "Scholar House"],
    "Toys & Games": ["FunWorld", "BrainSpark", "PlayZone", "StarToy"],
    "Grocery": ["FreshHarvest", "NaturesBest", "SnackBox", "GreenPantry"],
}

COLORS = ["Black", "White", "Red", "Blue", "Green", "Gray", "Pink", "Navy", "Tan", None]
SIZES = ["XS", "S", "M", "L", "XL", None]

PROMOTIONS = [
    ("Winter Clearance", "Percentage Off", 25, None, "2024-01-05", "2024-01-31", 50),
    ("Valentine's Day", "Percentage Off", 15, None, "2024-02-07", "2024-02-14", 30),
    ("Spring Sale", "Percentage Off", 20, None, "2024-03-15", "2024-03-31", 40),
    ("Easter Deals", "Bundle", None, 10, "2024-03-25", "2024-04-01", 60),
    ("Mother's Day", "Percentage Off", 15, None, "2024-05-01", "2024-05-12", 25),
    ("Memorial Day", "Percentage Off", 30, None, "2024-05-20", "2024-05-27", 75),
    ("Summer Kick-Off", "Free Shipping", None, None, "2024-06-01", "2024-06-15", 0),
    ("4th of July", "Percentage Off", 20, None, "2024-06-28", "2024-07-07", 50),
    ("Back to School", "Percentage Off", 15, None, "2024-08-01", "2024-08-31", 25),
    ("Labor Day", "Percentage Off", 25, None, "2024-08-30", "2024-09-03", 50),
    ("Fall Fashion", "BOGO", None, None, "2024-09-15", "2024-10-01", 75),
    ("Halloween Special", "Percentage Off", 10, None, "2024-10-20", "2024-10-31", 20),
    ("Singles Day", "Percentage Off", 35, None, "2024-11-11", "2024-11-11", 0),
    ("Black Friday", "Percentage Off", 40, None, "2024-11-29", "2024-12-01", 0),
    ("Cyber Monday", "Percentage Off", 35, None, "2024-12-02", "2024-12-02", 0),
    ("Holiday Season", "Percentage Off", 20, None, "2024-12-05", "2024-12-24", 50),
    ("New Year Sale", "Free Shipping", None, None, "2025-01-01", "2025-01-07", 0),
    ("President's Day", "Percentage Off", 15, None, "2025-02-15", "2025-02-17", 30),
    ("Spring Refresh", "Percentage Off", 20, None, "2025-03-15", "2025-04-01", 40),
    ("Easter 2025", "Bundle", None, 12, "2025-04-15", "2025-04-21", 60),
    ("Mother's Day 25", "Percentage Off", 15, None, "2025-05-01", "2025-05-11", 25),
    ("Summer Blowout", "Percentage Off", 30, None, "2025-06-01", "2025-06-30", 50),
    ("Prime Summer", "Free Shipping", None, None, "2025-07-15", "2025-07-17", 0),
    ("Back to School 25", "Percentage Off", 15, None, "2025-08-01", "2025-08-31", 25),
    ("Labor Day 25", "Percentage Off", 25, None, "2025-08-29", "2025-09-01", 50),
    ("Fall Flash", "Percentage Off", 20, None, "2025-10-01", "2025-10-07", 30),
    ("Halloween 25", "Percentage Off", 10, None, "2025-10-20", "2025-10-31", 20),
    ("Black Friday 25", "Percentage Off", 45, None, "2025-11-28", "2025-11-30", 0),
    ("Cyber Monday 25", "Percentage Off", 40, None, "2025-12-01", "2025-12-01", 0),
    ("Holiday 25", "Percentage Off", 25, None, "2025-12-05", "2025-12-24", 50),
]

SHIPPING_METHODS = [
    ("Standard Ground", "UPS", 7, 5.99),
    ("Express 2-Day", "FedEx", 2, 12.99),
    ("Next-Day Air", "FedEx", 1, 24.99),
    ("Same-Day Delivery", "Local Courier", 0, 34.99),
    ("In-Store Pickup", None, 0, 0.00),
]

PAYMENT_METHODS = [
    ("Credit Card", "Visa"),
    ("Credit Card", "Mastercard"),
    ("Credit Card", "Amex"),
    ("Debit Card", "Visa"),
    ("PayPal", "PayPal"),
    ("Apple Pay", "Apple"),
    ("Gift Card", None),
    ("Buy Now Pay Later", "Affirm"),
]

RETURN_REASONS = [
    ("DEFECTIVE", "Product Defective or Damaged"),
    ("WRONG_SIZE", "Wrong Size or Fit"),
    ("NOT_AS_DESC", "Not as Described"),
    ("CHANGED_MIND", "Changed Mind"),
    ("LATE_DELIVERY", "Arrived Too Late"),
    ("WRONG_ITEM", "Received Wrong Item"),
    ("BETTER_PRICE", "Found Better Price Elsewhere"),
    ("QUALITY", "Quality Below Expectations"),
]


# ── DimDate ────────────────────────────────────────────
def gen_dim_date() -> list[tuple]:
    rows = []
    start = date(2022, 1, 1)
    end = date(2025, 12, 31)
    d = start
    us_holidays = {
        (1, 1): "New Year's Day", (7, 4): "Independence Day",
        (12, 25): "Christmas Day", (11, 11): "Veterans Day",
    }
    while d <= end:
        dk = int(d.strftime("%Y%m%d"))
        is_wknd = 1 if d.weekday() >= 5 else 0
        hol_name = us_holidays.get((d.month, d.day))
        is_hol = 1 if hol_name else 0
        fy = d.year if d.month >= 7 else d.year - 1
        fq = ((d.month - 7) % 12) // 3 + 1
        rows.append((
            dk, d, d.year, (d.month - 1) // 3 + 1, d.month,
            d.strftime("%B"), d.isocalendar()[1], d.timetuple().tm_yday,
            d.day, d.weekday() + 1, d.strftime("%A"),
            is_wknd, is_hol, hol_name, fy, fq,
        ))
        d += timedelta(days=1)
    return rows


# ── DimCustomer ──────────────────────────────────────────
def gen_dim_customer(n: int = 3000) -> list[tuple]:
    tiers = ["Bronze"] * 50 + ["Silver"] * 30 + ["Gold"] * 15 + ["Platinum"] * 5
    rows = []
    for i in range(1, n + 1):
        state = random.choice([s for states in US_REGIONS.values() for s in states])
        region = STATE_TO_REGION[state]
        gender = random.choice(["Male", "Female"])
        first = fake.first_name_male() if gender == "Male" else fake.first_name_female()
        last = fake.last_name()
        birth = fake.date_of_birth(minimum_age=18, maximum_age=75)
        age = (date.today() - birth).days // 365
        age_group = (
            "18-24" if age < 25 else
            "25-34" if age < 35 else
            "35-44" if age < 45 else
            "45-54" if age < 55 else
            "55-64" if age < 65 else "65+"
        )
        signup = fake.date_between(start_date=date(2020, 1, 1), end_date=date(2025, 6, 30))
        rows.append((
            f"CUST-{i:05d}", first, last,
            f"{first.lower()}.{last.lower()}@{fake.free_email_domain()}",
            gender, birth, age_group,
            fake.city(), state, "United States", fake.zipcode(),
            region, random.choice(tiers), signup, 1,
        ))
    return rows


# ── DimProduct ───────────────────────────────────────────
def gen_dim_product(n: int = 500) -> list[tuple]:
    rows = []
    cats = list(CATEGORIES.keys())
    for i in range(1, n + 1):
        cat = random.choice(cats)
        subcat = random.choice(CATEGORIES[cat])
        brand = random.choice(BRANDS_BY_CAT[cat])
        cost = round(random.uniform(2, 400), 2)
        markup = random.uniform(1.3, 3.0)
        price = round(cost * markup, 2)
        color = random.choice(COLORS)
        size = random.choice(SIZES) if cat in ("Clothing", "Sports & Outdoors") else None
        weight = round(random.uniform(0.1, 25), 2)
        launch = fake.date_between(start_date=date(2021, 1, 1), end_date=date(2025, 6, 30))
        name = f"{brand} {subcat.rstrip('s')} {fake.bothify('??##').upper()}"
        rows.append((
            f"SKU-{i:05d}", name, cat, subcat, brand,
            cost, price, weight, color, size, 1, launch,
        ))
    return rows


# ── DimStore ─────────────────────────────────────────────
def gen_dim_store() -> list[tuple]:
    stores = []
    store_types = ["Flagship", "Outlet", "Warehouse"]
    all_states = [s for states in US_REGIONS.values() for s in states]
    # One online store
    stores.append((
        "STR-ONLINE", "RetailDW Online", "Online",
        None, None, "United States", None,
        date(2020, 1, 1), None, "Web Platform",
    ))
    for i in range(1, 25):
        state = all_states[i % len(all_states)]
        region = STATE_TO_REGION[state]
        stype = random.choice(store_types)
        stores.append((
            f"STR-{i:03d}", f"{fake.city()} {stype}", stype,
            fake.city(), state, "United States", region,
            fake.date_between(start_date=date(2015, 1, 1), end_date=date(2023, 12, 31)),
            random.randint(5000, 80000), fake.name(),
        ))
    return stores


# ── Fact generators ──────────────────────────────────────
def gen_fact_orders(
    n_customers: int, n_products: int, n_stores: int,
    n_promos: int, n_ship: int, n_pay: int,
    date_keys: list[int],
) -> tuple[list[tuple], list[tuple]]:
    """Returns (order_rows, return_rows)."""
    order_rows = []
    return_rows = []
    order_counter = 0
    return_counter = 0
    statuses = ["Completed"] * 90 + ["Cancelled"] * 5 + ["Returned"] * 5

    # Weight dates toward later years – simulate growth
    date_weights = np.array([(dk - 20220000) for dk in date_keys], dtype=float)
    date_weights = date_weights / date_weights.sum()
    date_key_set = set(date_keys)
    # Build index lookup for fast offset navigation
    dk_idx = {dk: i for i, dk in enumerate(date_keys)}

    for _ in range(5_000):  # ~5 K orders, avg 3 lines each
        order_counter += 1
        oid = f"ORD-{order_counter:06d}"
        cust_key = random.randint(1, n_customers)
        store_key = random.randint(1, n_stores)
        date_key = int(np.random.choice(date_keys, p=date_weights))
        # Pick a valid ship date key from the date dimension
        idx = dk_idx[date_key]
        ship_idx = min(idx + random.randint(1, 10), len(date_keys) - 1)
        ship_dk = date_keys[ship_idx]
        pay_key = random.randint(1, n_pay)
        promo_key = random.randint(1, n_promos) if random.random() < 0.35 else None
        ship_key = random.randint(1, n_ship)
        status = random.choice(statuses)

        n_lines = random.choices([1, 2, 3, 4, 5], weights=[40, 30, 15, 10, 5])[0]
        for ln in range(1, n_lines + 1):
            prod_key = random.randint(1, n_products)
            qty = random.choices([1, 2, 3, 4], weights=[60, 25, 10, 5])[0]
            unit_price = round(random.uniform(5, 500), 2)
            unit_cost = round(unit_price / random.uniform(1.3, 3.0), 2)
            disc = round(unit_price * qty * random.uniform(0, 0.15), 2) if promo_key else 0
            ship_cost = round(random.uniform(0, 15), 2) if ship_key != 5 else 0  # free for pickup
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

            # Generate return record
            if is_returned:
                return_counter += 1
                ret_idx = min(dk_idx[date_key] + random.randint(5, 30), len(date_keys) - 1)
                ret_date = date_keys[ret_idx]
                return_rows.append((
                    f"RET-{return_counter:06d}", oid, ln,
                    cust_key, prod_key, ret_date, store_key,
                    random.randint(1, 8),  # return reason
                    qty, round(line_total * 0.95, 2),  # ~95% refund
                    random.choice(["Approved", "Approved", "Pending"]),
                    1 if random.random() < 0.9 else 0,
                ))

    return order_rows, return_rows


def gen_fact_reviews(n_customers: int, n_products: int, date_keys: list[int], n: int = 2000) -> list[tuple]:
    rows = []
    for i in range(1, n + 1):
        rating = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 20, 35, 30])[0]
        sentiment = round(random.gauss((rating - 3) / 2.5, 0.2), 2)
        sentiment = max(-1.0, min(1.0, sentiment))
        rows.append((
            f"REV-{i:06d}",
            random.randint(1, n_customers),
            random.randint(1, n_products),
            random.choice(date_keys),
            rating,
            random.randint(5, 300),
            random.randint(0, 50),
            fake.sentence(nb_words=6) if random.random() < 0.7 else None,
            1 if random.random() < 0.85 else 0,
            sentiment,
        ))
    return rows


def gen_fact_web_traffic(n_customers: int, date_keys: list[int], n: int = 5000) -> list[tuple]:
    sources = ["Organic"] * 30 + ["Paid Search"] * 25 + ["Social"] * 20 + ["Email"] * 15 + ["Direct"] * 10
    devices = ["Desktop"] * 40 + ["Mobile"] * 45 + ["Tablet"] * 15
    browsers = ["Chrome"] * 55 + ["Safari"] * 25 + ["Firefox"] * 10 + ["Edge"] * 10
    pages = ["/", "/products", "/deals", "/category/electronics", "/category/clothing",
             "/cart", "/checkout", "/account", "/about", "/support"]
    rows = []
    for i in range(1, n + 1):
        cust_key = random.randint(1, n_customers) if random.random() < 0.6 else None
        pvs = max(1, int(np.random.lognormal(1.5, 0.8)))
        dur = max(5, int(np.random.lognormal(4.5, 1.0)))
        bounce = 1 if pvs == 1 else 0
        viewed = random.randint(0, min(pvs, 8))
        added = random.randint(0, max(1, viewed // 2))
        converted = 1 if added > 0 and random.random() < 0.25 else 0
        rows.append((
            f"SES-{i:07d}",
            cust_key,
            random.choice(date_keys),
            pvs, dur, bounce, viewed, added, converted,
            random.choice(sources),
            random.choice(devices),
            random.choice(browsers),
            random.choice(pages),
        ))
    return rows


def gen_fact_inventory(n_products: int, n_stores: int, date_keys: list[int]) -> list[tuple]:
    """Monthly snapshots — one row per product × store on the 1st of each month."""
    rows = []
    monthly_keys = [dk for dk in date_keys if dk % 100 == 1]  # 1st of each month
    for dk in monthly_keys:
        for store in range(1, n_stores + 1):
            # Sample ~30% of products per store per month to keep volume manageable
            for prod in random.sample(range(1, n_products + 1), k=min(30, n_products)):
                qty_hand = max(0, int(np.random.lognormal(3, 1)))
                qty_order = random.randint(0, 50) if qty_hand < 20 else 0
                reorder = random.randint(10, 50)
                ucost = round(random.uniform(2, 400), 2)
                rows.append((
                    prod, store, dk,
                    qty_hand, qty_order, reorder,
                    ucost, round(qty_hand * ucost, 2),
                ))
    return rows


# ── main ─────────────────────────────────────────────────
def main() -> None:
    facts_only = "--facts-only" in sys.argv
    print(f"Connecting to {DATABASE} on {SERVER} ...")
    conn = get_connection()

    # Always generate date_rows for date_keys list
    date_rows = gen_dim_date()
    date_keys = [r[0] for r in date_rows]

    if not facts_only:
        print("\n=== Generating dimension data ===")

        n = bulk_insert(conn, "dim.DimDate",
            ["DateKey", "[Date]", "[Year]", "Quarter", "[Month]", "MonthName",
             "[Week]", "DayOfYear", "DayOfMonth", "DayOfWeek", "DayName",
             "IsWeekend", "IsHoliday", "HolidayName", "FiscalYear", "FiscalQuarter"],
            date_rows)
        print(f"  DimDate: {n} rows")

        cust_rows = gen_dim_customer(3000)
        n = bulk_insert(conn, "dim.DimCustomer",
            ["CustomerId", "FirstName", "LastName", "Email", "Gender", "BirthDate",
             "AgeGroup", "City", "[State]", "Country", "PostalCode", "Region",
             "MembershipTier", "SignupDate", "IsActive"],
            cust_rows)
        print(f"  DimCustomer: {n} rows")

        prod_rows = gen_dim_product(500)
        n = bulk_insert(conn, "dim.DimProduct",
            ["ProductId", "ProductName", "Category", "Subcategory", "Brand",
             "UnitCost", "UnitPrice", "[Weight]", "Color", "Size", "IsActive", "LaunchDate"],
            prod_rows)
        print(f"  DimProduct: {n} rows")

        store_rows = gen_dim_store()
        n = bulk_insert(conn, "dim.DimStore",
            ["StoreId", "StoreName", "StoreType", "City", "[State]", "Country",
             "Region", "OpenDate", "SquareFootage", "ManagerName"],
            store_rows)
        n_stores = len(store_rows)
        print(f"  DimStore: {n} rows")

        promo_rows = [(f"PROMO-{i+1:03d}", *p) for i, p in enumerate(PROMOTIONS)]
        n = bulk_insert(conn, "dim.DimPromotion",
            ["PromotionId", "PromotionName", "PromotionType", "DiscountPercent",
             "DiscountAmount", "StartDate", "EndDate", "MinOrderAmount"],
            promo_rows)
        n_promos = len(promo_rows)
        print(f"  DimPromotion: {n} rows")

        ship_rows = SHIPPING_METHODS
        n = bulk_insert(conn, "dim.DimShippingMethod",
            ["MethodName", "CarrierName", "AvgDeliveryDays", "BaseCost"],
            ship_rows)
        n_ship = len(ship_rows)
        print(f"  DimShippingMethod: {n} rows")

        pay_rows = PAYMENT_METHODS
        n = bulk_insert(conn, "dim.DimPaymentMethod",
            ["MethodName", "Provider"],
            pay_rows)
        n_pay = len(pay_rows)
        print(f"  DimPaymentMethod: {n} rows")

        ret_rows = RETURN_REASONS
        n = bulk_insert(conn, "ref.RefReturnReason",
            ["ReasonCode", "ReasonName"],
            ret_rows)
        print(f"  RefReturnReason: {n} rows")
    else:
        print("\n=== Skipping dimensions (--facts-only) ===")
        n_stores = 25
        n_promos = 30
        n_ship = 5
        n_pay = 8

    # ── Facts ────────────────────────────────────────────
    print("\n=== Generating fact data (this may take a minute) ===")

    n_customers = 3000
    n_products = 500

    order_rows, return_rows = gen_fact_orders(
        n_customers, n_products, n_stores, n_promos, n_ship, n_pay, date_keys
    )
    n = bulk_insert(conn, "fact.FactOrders",
        ["OrderId", "LineNumber", "CustomerKey", "ProductKey", "OrderDateKey",
         "ShipDateKey", "StoreKey", "PromotionKey", "ShippingMethodKey",
         "PaymentMethodKey", "Quantity", "UnitPrice", "UnitCost",
         "DiscountAmount", "ShippingCost", "TaxAmount", "LineTotal",
         "LineCost", "LineProfit", "OrderStatus", "IsReturned"],
        order_rows)
    print(f"  FactOrders: {n} rows ({len(set(r[0] for r in order_rows))} distinct orders)")

    n = bulk_insert(conn, "fact.FactReturns",
        ["ReturnId", "OrderId", "LineNumber", "CustomerKey", "ProductKey",
         "ReturnDateKey", "StoreKey", "ReturnReasonKey", "Quantity",
         "RefundAmount", "ReturnStatus", "IsRefunded"],
        return_rows)
    print(f"  FactReturns: {n} rows")

    review_rows = gen_fact_reviews(n_customers, n_products, date_keys)
    n = bulk_insert(conn, "fact.FactCustomerReview",
        ["ReviewId", "CustomerKey", "ProductKey", "ReviewDateKey", "Rating",
         "ReviewLength", "HelpfulVotes", "ReviewTitle", "IsVerifiedPurchase",
         "SentimentScore"],
        review_rows)
    print(f"  FactCustomerReview: {n} rows")

    web_rows = gen_fact_web_traffic(n_customers, date_keys)
    n = bulk_insert(conn, "fact.FactWebTraffic",
        ["SessionId", "CustomerKey", "VisitDateKey", "PageViews",
         "SessionDurationSec", "BounceFlag", "ProductsViewed", "AddedToCart",
         "ConvertedFlag", "TrafficSource", "DeviceType", "Browser", "LandingPage"],
        web_rows)
    print(f"  FactWebTraffic: {n} rows")

    inv_rows = gen_fact_inventory(n_products, n_stores, date_keys)
    n = bulk_insert(conn, "fact.FactInventory",
        ["ProductKey", "StoreKey", "SnapshotDateKey", "QuantityOnHand",
         "QuantityOnOrder", "ReorderPoint", "UnitCost", "InventoryValue"],
        inv_rows)
    print(f"  FactInventory: {n} rows")

    conn.close()
    print("\n=== Seeding complete! ===")


if __name__ == "__main__":
    main()
