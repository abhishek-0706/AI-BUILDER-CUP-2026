#!/usr/bin/env python3
"""Generate newline-delimited JSON seed files for the RetailIQ BigQuery dataset.

The dimension rows are transcribed from retail_data.js, which is the source of
truth for the demo. The transaction history is synthesised, because the fixture
holds only 7 daily totals and ARIMA_PLUS needs a real series to train on.

What the generator guarantees:
  - For the last 7 days, daily net revenue and basket count match revenueWeek
    exactly, so the revenue widget reproduces the demo chart.
  - The 10 named SKUs hit their unitsSoldLast30d velocities, so top movers and
    reorder alerts are about real products.
  - The remaining store revenue is carried by a generated long-tail catalogue,
    because 10 SKUs cannot add up to a 48,000 rupee day.

Everything it writes is synthetic. Nothing here is customer data.

Usage:
    python seed_data.py --out ./seed_out [--as-of 2026-09-27] [--days 180]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import random
from pathlib import Path

RNG_SEED = 20260927

STORE_ID = "BLR-KOR-014"
SECOND_STORE_ID = "BLR-JAY-007"

# Day label -> (net revenue, basket count) from RETAIL_DATA.revenueWeek.
WEEK_SHAPE = {
    "Mon": (48200, 312),
    "Tue": (41800, 278),
    "Wed": (52600, 349),
    "Thu": (44100, 291),
    "Fri": (67300, 447),
    "Sat": (89400, 598),
    "Sun": (94100, 627),
}
AVG_DAILY_REVENUE = sum(r for r, _ in WEEK_SHAPE.values()) / 7

CATEGORIES = [
    "Dairy & Eggs",
    "Snacks & Beverages",
    "Fresh Produce",
    "Packaged Foods",
    "Personal Care",
]

# Supplier lead time by category, used to turn a stock level into an urgency.
LEAD_TIME_DAYS = {
    "Fresh Produce": 1,
    "Dairy & Eggs": 1,
    "Snacks & Beverages": 3,
    "Packaged Foods": 4,
    "Personal Care": 5,
}

# id, name, category, brand, price, margin, reorder point, units sold in 30d, stock
FIXTURE_PRODUCTS = [
    ("P001", "Amul Gold Milk 1L",        "Dairy & Eggs",       "Amul",       68,  0.09, 40, 1240, 142),
    ("P002", "Lay's Classic Salted 90g", "Snacks & Beverages", "Lay's",      20,  0.22, 30,  890,  88),
    ("P003", "Tropicana Orange 1L",      "Snacks & Beverages", "Tropicana",  130, 0.18, 25,  410,  34),
    ("P004", "Britannia NutriChoice",    "Packaged Foods",     "Britannia",  45,  0.20, 20,  670,  12),
    ("P005", "Dove Soap 100g",           "Personal Care",      "Dove",       60,  0.28, 15,  320,  56),
    ("P006", "Farm Fresh Tomatoes 1kg",  "Fresh Produce",      "Farm Fresh", 40,  0.15, 30, 1100,  95),
    ("P007", "Haldiram Bhujia 400g",     "Snacks & Beverages", "Haldiram",   110, 0.21, 20,  540,  67),
    ("P008", "Nescafe Classic 200g",     "Packaged Foods",     "Nescafe",    395, 0.25, 15,  190,  28),
    ("P009", "Amul Butter 500g",         "Dairy & Eggs",       "Amul",       275, 0.11, 20,  380,  41),
    ("P010", "Sunfeast Marie Light",     "Packaged Foods",     "Sunfeast",   30,  0.19, 25,  820,   8),
]

# Long-tail catalogue building blocks: (brand, item name, price, margin).
LONG_TAIL = {
    "Dairy & Eggs": (
        ["Nandini", "Heritage", "Mother Dairy", "Milky Mist", "Akshayakalpa"],
        [("Toned Milk 500ml", 28, 0.08), ("Curd 400g", 45, 0.14),
         ("Paneer 200g", 95, 0.16), ("Eggs 6 pack", 54, 0.12),
         ("Cheese Slices 200g", 135, 0.19)],
    ),
    "Snacks & Beverages": (
        ["Bingo", "Kurkure", "Parle", "Frooti", "Bisleri"],
        [("Masala Chips 52g", 20, 0.24), ("Soda 750ml", 40, 0.20),
         ("Fruit Drink 1L", 99, 0.18), ("Namkeen Mixture 200g", 65, 0.22),
         ("Mineral Water 1L", 20, 0.15)],
    ),
    "Fresh Produce": (
        ["Farm Fresh", "Green Basket", "Local Grower", "Daily Harvest", "Nature Pick"],
        [("Onions 1kg", 35, 0.13), ("Potatoes 1kg", 32, 0.13),
         ("Bananas 1 dozen", 55, 0.17), ("Spinach 250g", 25, 0.20),
         ("Apples 1kg", 180, 0.16)],
    ),
    "Packaged Foods": (
        ["Aashirvaad", "Fortune", "MTR", "Maggi", "Tata"],
        [("Atta 5kg", 275, 0.10), ("Sunflower Oil 1L", 145, 0.09),
         ("Rava Idli Mix 500g", 85, 0.21), ("Noodles 4 pack", 56, 0.19),
         ("Iodised Salt 1kg", 28, 0.14)],
    ),
    "Personal Care": (
        ["Colgate", "Clinic Plus", "Santoor", "Nivea", "Himalaya"],
        [("Toothpaste 200g", 115, 0.26), ("Shampoo 340ml", 210, 0.29),
         ("Soap 3 pack", 99, 0.25), ("Body Lotion 200ml", 185, 0.27),
         ("Face Wash 100g", 145, 0.30)],
    ),
}

# Promotions are applied to the seeded lines at category level, which is a
# simplification of the SKU-level Health Week mechanic in the fixture.
PROMOTIONS = [
    {
        "promotion_id": "PROMO-01", "promotion_name": "Weekend Bonanza",
        "store_id": STORE_ID, "category": "Snacks & Beverages",
        "mechanic": "percentage_off", "discount_label": "15% off Snacks",
        "discount_pct": 0.15, "active_weekdays": "Fri,Sat,Sun",
        "observed_uplift_pct": 22.0,
    },
    {
        "promotion_id": "PROMO-02", "promotion_name": "Dairy Deal",
        "store_id": STORE_ID, "category": "Dairy & Eggs",
        "mechanic": "multibuy", "discount_label": "Buy 2 Amul, get Rs 20 off",
        "discount_pct": 0.07, "active_weekdays": "",
        "observed_uplift_pct": 11.0,
    },
    {
        "promotion_id": "PROMO-03", "promotion_name": "Health Week",
        "store_id": STORE_ID, "category": "Packaged Foods",
        "mechanic": "percentage_off", "discount_label": "10% off NutriChoice & Marie",
        "discount_pct": 0.10, "active_weekdays": "Mon,Tue,Wed,Thu",
        "observed_uplift_pct": 18.0,
    },
]

SEGMENTS = [
    ("Weekend Warriors", 34, 1240, 1.4, "Bulk-buy on weekends, high-value baskets"),
    ("Daily Top-Ups", 28, 310, 5.8, "Small daily purchases, highly loyal"),
    ("Deal Seekers", 22, 680, 2.1, "Price-sensitive, respond to promotions"),
    ("Convenience First", 16, 890, 2.9, "Time-pressed, value speed and availability"),
]

KB_DOCS = [
    ("KB-101", "[SYNTHETIC] Nielsen Retail Audit - South India Biscuits Q3 2026",
     "Health-positioned biscuits grew 18.4% YoY in South India modern trade, versus 3.1% for the total biscuit category.",
     "syndicated_audit", "Packaged Foods", "2026-09-05"),
    ("KB-102", "[SYNTHETIC] FreshMart Koramangala - Category Performance Report Aug 2026",
     "Packaged Foods contributed 22% of store revenue but only 14% of shelf space, the widest gap of any category.",
     "account_report", "Packaged Foods", "2026-09-02"),
    ("KB-103", "[SYNTHETIC] Internal Margin Sheet - Q4 2026 Trade Terms",
     "NutriChoice 6-pack carries a 20% retailer margin versus 19% on the single pack, with a 4% Q4 volume rebate above 500 units.",
     "internal_margin", "Packaged Foods", "2026-09-20"),
    ("KB-104", "[SYNTHETIC] Shopper Panel Study - Bengaluru Urban, Jul 2026",
     "63% of urban Bengaluru shoppers buying health biscuits purchase multipacks when placed at eye level, versus 31% at bottom shelf.",
     "shopper_panel", "Packaged Foods", "2026-07-28"),
    ("KB-105", "[SYNTHETIC] Health Week Campaign Post-Mortem - Mar 2026",
     "The Health Week end-cap delivered an 18% category uplift at 6 comparable FreshMart stores, with zero cannibalisation of the single pack.",
     "campaign_review", "Packaged Foods", "2026-03-30"),
    ("KB-106", "[SYNTHETIC] Supply Chain Scorecard - Sep 2026",
     "Fill rate recovered to 96.2% in September after the Hosur depot expansion, up from 82% in August.",
     "supply_chain", "All", "2026-09-25"),
    ("KB-107", "[SYNTHETIC] Coffee Category Tracker - Sep 2026",
     "Nescafe Classic 200g holds 34% value share and 25% retailer margin, the highest margin SKU in the instant coffee bay.",
     "syndicated_audit", "Packaged Foods", "2026-09-18"),
]

PLANOGRAM_RULES = [
    ("PG-Q4-2026-R1", "Facing count", "Minimum 2 visible facings per SKU variant", 0.25),
    ("PG-Q4-2026-R2", "Product grouping", "All variants of a brand blocked together, no cross-brand interleaving", 0.20),
    ("PG-Q4-2026-R3", "Shelf position", "Health range at eye level (shelf 3 of 5), value packs on shelf 4", 0.25),
    ("PG-Q4-2026-R4", "Price tag visibility", "Every visible SKU has a clean, readable price tag aligned on the shelf edge", 0.15),
    ("PG-Q4-2026-R5", "Product condition", "No crushed, expired or rear-faced packs; all packs front-faced", 0.15),
]


def build_catalogue() -> list[dict]:
    """Fixture SKUs plus a generated long tail, 60 SKUs in total."""
    products = []
    for pid, name, cat, brand, price, margin, reorder, units30, _stock in FIXTURE_PRODUCTS:
        products.append({
            "product_id": pid, "product_name": name, "category": cat, "brand": brand,
            "list_price": price, "margin_rate": margin,
            "default_reorder_point": reorder, "pack_size": name.split()[-1],
            "is_active": True, "first_listed_date": "2024-04-01",
            "_units30": units30,
        })
    n = 0
    for cat, (brands, items) in LONG_TAIL.items():
        for i, brand in enumerate(brands):
            for offset in (0, 2):
                item, price, margin = items[(i + offset) % len(items)]
                n += 1
                products.append({
                    "product_id": f"L{n:03d}",
                    "product_name": f"{brand} {item}",
                    "category": cat, "brand": brand,
                    "list_price": price, "margin_rate": margin,
                    "default_reorder_point": 20, "pack_size": item.split()[-1],
                    "is_active": True, "first_listed_date": "2024-04-01",
                    "_units30": None,
                })
    return products


def weekday_label(d: dt.date) -> str:
    return d.strftime("%a")


def daily_target(d: dt.date, as_of: dt.date, rng: random.Random) -> tuple[float, int]:
    """Net revenue and basket count for one day."""
    base_rev, base_txn = WEEK_SHAPE[weekday_label(d)]
    age = (as_of - d).days
    if age < 7:
        return float(base_rev), base_txn
    # Mild growth toward the present plus noise, so ARIMA_PLUS has a trend and a
    # weekly season to find rather than a flat repeat of the same 7 numbers.
    trend = 1.0 - 0.0011 * age
    return (
        base_rev * trend * rng.gauss(1.0, 0.045),
        max(20, round(base_txn * trend * rng.gauss(1.0, 0.03))),
    )


def active_promo(cat: str, d: dt.date) -> dict | None:
    label = weekday_label(d)
    for p in PROMOTIONS:
        if p["category"] != cat:
            continue
        if p["active_weekdays"] and label not in p["active_weekdays"].split(","):
            continue
        return p
    return None


def make_line(prod: dict, qty: int, d: dt.date) -> dict:
    gross = prod["list_price"] * qty
    promo = active_promo(prod["category"], d)
    discount = round(gross * promo["discount_pct"], 2) if promo else 0.0
    return {
        "product_id": prod["product_id"],
        "quantity": qty,
        "unit_price": float(prod["list_price"]),
        "discount_amount": discount,
        "line_revenue": round(gross - discount, 2),
        "promotion_id": promo["promotion_id"] if promo else None,
    }


def generate(as_of: dt.date, days: int, out: Path) -> dict[str, int]:
    rng = random.Random(RNG_SEED)
    catalogue = build_catalogue()
    by_id = {p["product_id"]: p for p in catalogue}
    fixture_ids = [p[0] for p in FIXTURE_PRODUCTS]
    long_tail = [p for p in catalogue if p["product_id"].startswith("L")]
    cheapest = min(long_tail, key=lambda p: p["list_price"])

    segment_names = [s[0] for s in SEGMENTS]
    segment_weights = [s[1] for s in SEGMENTS]

    customers: dict[str, str] = {}
    recent: list[str] = []  # bounded pool of customers seen lately
    RECENT_CAP = 31000
    next_customer = 1

    txn_rows: list[dict] = []
    traffic_rows: list[dict] = []
    units_last_30d: dict[str, int] = {}

    start = as_of - dt.timedelta(days=days - 1)
    for offset in range(days):
        d = start + dt.timedelta(days=offset)
        target_rev, basket_count = daily_target(d, as_of, rng)
        day_factor = target_rev / AVG_DAILY_REVENUE

        lines: list[dict] = []
        running = 0.0

        # 1. The named SKUs, at their fixture velocity scaled by the day.
        for pid in fixture_ids:
            prod = by_id[pid]
            expected = prod["_units30"] / 30.0 * day_factor * rng.gauss(1.0, 0.15)
            remaining = max(0, int(round(expected)))
            while remaining > 0:
                qty = min(remaining, rng.choice([1, 1, 1, 2, 3]))
                line = make_line(prod, qty, d)
                lines.append(line)
                running += line["line_revenue"]
                remaining -= qty

        # 2. Long tail carries the rest of the day's revenue.
        attempts = 0
        while running < target_rev - 1 and attempts < 20000:
            attempts += 1
            prod = rng.choice(long_tail)
            qty = rng.choice([1, 1, 2])
            line = make_line(prod, qty, d)
            if running + line["line_revenue"] > target_rev:
                continue
            lines.append(line)
            running += line["line_revenue"]

        # 3. Close the last few rupees exactly, so the revenue widget reproduces
        #    the fixture. Overshoot is absorbed as a discount on this one line,
        #    which is always smaller than the cheapest unit price.
        gap = target_rev - running
        if gap > 0:
            qty = max(1, math.ceil(gap / cheapest["list_price"]))
            line = make_line(cheapest, qty, d)
            overshoot = round(running + line["line_revenue"] - target_rev, 2)
            if overshoot > 0:
                line["discount_amount"] = round(line["discount_amount"] + overshoot, 2)
                line["line_revenue"] = round(line["line_revenue"] - overshoot, 2)
            lines.append(line)
            running += line["line_revenue"]

        # 4. Deal the lines into baskets.
        rng.shuffle(lines)
        basket_count = min(basket_count, len(lines))
        baskets: list[list[dict]] = [[] for _ in range(basket_count)]
        for i, line in enumerate(lines):
            baskets[i % basket_count].append(line)

        for b_index, basket in enumerate(baskets):
            if rng.random() < 0.15:
                customer_id, segment = None, None
            else:
                if recent and rng.random() < 0.72:
                    customer_id = rng.choice(recent)
                else:
                    customer_id = f"C{next_customer:06d}"
                    next_customer += 1
                    customers[customer_id] = rng.choices(segment_names, segment_weights)[0]
                segment = customers[customer_id]
                recent.append(customer_id)
                if len(recent) > RECENT_CAP:
                    del recent[: len(recent) - RECENT_CAP]

            hour = rng.choices(
                range(8, 22),
                weights=[3, 5, 6, 6, 7, 6, 5, 5, 6, 8, 10, 11, 9, 6],
            )[0]
            ts = dt.datetime.combine(
                d, dt.time(hour, rng.randrange(60), rng.randrange(60))
            ).isoformat() + "Z"
            txn_id = f"T{d.strftime('%Y%m%d')}-{b_index:05d}"

            for line_no, line in enumerate(basket, start=1):
                txn_rows.append({
                    "transaction_id": txn_id,
                    "line_number": line_no,
                    "txn_ts": ts,
                    "txn_date": d.isoformat(),
                    "store_id": STORE_ID,
                    "product_id": line["product_id"],
                    "customer_id": customer_id,
                    "segment_name": segment,
                    "quantity": line["quantity"],
                    "unit_price": line["unit_price"],
                    "discount_amount": line["discount_amount"],
                    "line_revenue": line["line_revenue"],
                    "promotion_id": line["promotion_id"],
                    "channel": "in_store",
                    "is_return": False,
                })
                if (as_of - d).days < 30:
                    units_last_30d[line["product_id"]] = (
                        units_last_30d.get(line["product_id"], 0) + line["quantity"]
                    )

        conversion = 0.68 if (as_of - d).days < 7 else rng.uniform(0.62, 0.72)
        footfall = round(basket_count / conversion)
        traffic_rows.append({
            "traffic_date": d.isoformat(),
            "store_id": STORE_ID,
            "footfall": footfall,
            "unique_visitors": round(footfall * 0.86),
        })

    # Inventory: one snapshot, for the as-of date. In production this is a daily
    # extract from the store system, not a generated history.
    fixture_stock = {p[0]: p[8] for p in FIXTURE_PRODUCTS}
    fixture_reorder = {p[0]: p[6] for p in FIXTURE_PRODUCTS}
    inventory_rows = []
    for prod in catalogue:
        pid = prod["product_id"]
        velocity = units_last_30d.get(pid, 0) / 30.0
        if pid in fixture_stock:
            on_hand = fixture_stock[pid]
            reorder = fixture_reorder[pid]
        else:
            on_hand = max(0, round(velocity * rng.uniform(4, 16)))
            reorder = max(5, round(velocity * 3))
        lead = LEAD_TIME_DAYS[prod["category"]]
        inventory_rows.append({
            "snapshot_date": as_of.isoformat(),
            "store_id": STORE_ID,
            "product_id": pid,
            "units_on_hand": on_hand,
            "reorder_point": reorder,
            "units_on_order": round(velocity * lead) if on_hand <= reorder else 0,
            "lead_time_days": lead,
        })

    stores = [
        {
            "store_id": STORE_ID,
            "store_name": "FreshMart Express - Koramangala",
            "city": "Bengaluru", "zone": "South India",
            "format_segment": "Urban Grocery", "sqft": 4200,
            "open_date": "2021-03-15",
            "daily_revenue_target": 90000,
            "latest_nps": 61,
            "nps_as_of": as_of.isoformat(),
        },
        {
            "store_id": SECOND_STORE_ID,
            "store_name": "DailyNeeds Supermart - Jayanagar",
            "city": "Bengaluru", "zone": "South India",
            "format_segment": "Value Format", "sqft": 3100,
            "open_date": "2022-07-11",
            "daily_revenue_target": 62000,
            "latest_nps": 54,
            "nps_as_of": as_of.isoformat(),
        },
    ]

    products_rows = [{k: v for k, v in p.items() if not k.startswith("_")} for p in catalogue]

    segments_rows = [
        {
            "as_of_date": as_of.isoformat(), "store_id": STORE_ID,
            "segment_name": name, "share_pct": pct,
            "avg_basket_value": basket, "visits_per_week": visits,
            "description": desc,
        }
        for name, pct, basket, visits, desc in SEGMENTS
    ]

    promo_rows = [
        {**p, "start_date": (as_of - dt.timedelta(days=30)).isoformat(),
         "end_date": (as_of + dt.timedelta(days=30)).isoformat()}
        for p in PROMOTIONS
    ]

    reps = [{
        "rep_id": "TSE-4417", "rep_name": "Anita Sharma",
        "role_title": "Territory Sales Executive", "territory": "Bengaluru South",
        "quota_month": 2400000, "visits_planned_month": 22,
    }]

    accounts = [
        {
            "account_id": "ACC-01", "account_name": "FreshMart Express",
            "account_type": "Modern Trade - Urban Grocery", "store_count": 14,
            "tier": "Platinum", "relationship_years": 7,
            "ytd_value": 18400000, "growth_yoy": 0.12,
            "contact_name": "Vikram Rao",
            "contact_role": "Category Buyer - Packaged Foods",
            "contact_style": "Data-driven, margin-focused, time-pressed",
        },
        {
            "account_id": "ACC-02", "account_name": "DailyNeeds Supermart",
            "account_type": "Modern Trade - Value Format", "store_count": 31,
            "tier": "Gold", "relationship_years": 3,
            "ytd_value": 9200000, "growth_yoy": -0.04,
            "contact_name": "Meera Iyer",
            "contact_role": "Regional Merchandising Head",
            "contact_style": "Price-sensitive, wants promo support, sceptical of new SKUs",
        },
    ]

    visits = [
        {
            "visit_id": "V-00118", "account_id": "ACC-01", "rep_id": "TSE-4417",
            "store_id": STORE_ID, "store_name": "FreshMart Express - Koramangala",
            "visit_date": "2026-10-01", "visit_time": "10:30",
            "duration_minutes": 90, "status": "scheduled",
            "last_visit_date": "2026-08-21",
            "visit_frequency": "every 5-7 days (Index Score based)",
            "objective": "Recover the NutriChoice 6-pack listing and secure end-cap for Health Week",
            "open_tasks": [
                "Close pending audit on 4 assets (chillers BLR-KOR-014-C1 to C4)",
                "Collect signed planogram acknowledgement for Q4 reset",
                "Present Nescafe Classic 200g margin case",
            ],
            "last_order_value": 142000, "orders_last_6m": 7, "avg_order_value": 128000,
            "listings_lost": ["Britannia NutriChoice 6-pack (delisted Jul 2026)"],
        },
        {
            "visit_id": "V-00119", "account_id": "ACC-02", "rep_id": "TSE-4417",
            "store_id": SECOND_STORE_ID, "store_name": "DailyNeeds Supermart - Jayanagar",
            "visit_date": "2026-10-02", "visit_time": "14:00",
            "duration_minutes": 60, "status": "scheduled",
            "last_visit_date": "2026-09-18",
            "visit_frequency": "every 14 days",
            "objective": "Arrest the -4% YoY decline, push value packs ahead of festive season",
            "open_tasks": [
                "Resolve 2 short-supply complaints",
                "Re-negotiate shelf share in Snacks bay",
            ],
            "last_order_value": 86000, "orders_last_6m": 5, "avg_order_value": 91000,
            "listings_lost": [],
        },
    ]

    objections = [
        ("OBJ-001", "V-00118", "ACC-01",
         "Your NutriChoice 6-pack moved 40% slower than the single pack last quarter, why should I relist it?",
         "velocity", "2026-08-21"),
        ("OBJ-002", "V-00118", "ACC-01",
         "Nescafe at Rs 395 is Rs 20 above the competing SKU and my margin is thinner.",
         "price", "2026-08-21"),
        ("OBJ-003", "V-00118", "ACC-01",
         "I only have one end-cap free and three brands are asking for it.",
         "space", "2026-08-21"),
        ("OBJ-004", "V-00119", "ACC-02",
         "Your fill rate dropped to 82% last month, I lost sales because of you.",
         "supply", "2026-09-18"),
        ("OBJ-005", "V-00119", "ACC-02",
         "DailyNeeds shoppers want value packs, your portfolio is premium-heavy.",
         "assortment", "2026-09-18"),
    ]
    objection_rows = [
        {"objection_id": oid, "visit_id": vid, "account_id": aid,
         "objection_text": text, "theme": theme, "raised_on": on, "resolved": False}
        for oid, vid, aid, text, theme, on in objections
    ]

    kb_rows = [
        {"doc_id": did, "title": title, "fact": fact, "source_type": src,
         "category": cat, "published_date": pub, "embedding": [], "is_synthetic": True}
        for did, title, fact, src, cat, pub in KB_DOCS
    ]

    planogram_rows = [
        {"planogram_id": "PG-Q4-2026",
         "planogram_name": "Q4 2026 Packaged Foods Reset - Modern Trade Urban",
         "bay": "Aisle 4, Bay 2 - Biscuits & Breakfast",
         "rule_id": rid, "rule_name": name, "spec": spec, "weight": weight,
         "effective_from": "2026-09-01", "effective_to": "2026-12-31"}
        for rid, name, spec, weight in PLANOGRAM_RULES
    ]

    tables = {
        "stores": stores,
        "products": products_rows,
        "sales_reps": reps,
        "accounts": accounts,
        "sales_transactions": txn_rows,
        "store_traffic_daily": traffic_rows,
        "inventory_snapshots": inventory_rows,
        "customer_segments": segments_rows,
        "promotions": promo_rows,
        "visits": visits,
        "visit_objections": objection_rows,
        "kb_documents": kb_rows,
        "planogram_rules": planogram_rows,
    }

    out.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, rows in tables.items():
        path = out / f"{name}.ndjson"
        with path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        counts[name] = len(rows)
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="seed_out", type=Path)
    # A Sunday, so the 7 day window ends on the peak day the fixture reports as
    # "today" and the two planned visits are still in the future.
    ap.add_argument("--as-of", default="2026-09-27")
    ap.add_argument("--days", default=180, type=int)
    args = ap.parse_args()

    as_of = dt.date.fromisoformat(args.as_of)
    if as_of.strftime("%a") != "Sun":
        print(f"note: --as-of {as_of} is a {as_of.strftime('%A')}, not a Sunday")
    counts = generate(as_of, args.days, args.out)
    width = max(len(k) for k in counts)
    for name, n in counts.items():
        print(f"{name.ljust(width)}  {n:>8,} rows")
    print(f"\nwritten to {args.out.resolve()}")


if __name__ == "__main__":
    main()
