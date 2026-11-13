import csv
import json
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from config import SEED, RAW_DIR, GROUND_TRUTH_DIR, PROCESSED_DIR

CATEGORIES = [
    ("CAT-000001", "Electronics", None, False),
    ("CAT-000002", "Home", None, False),
    ("CAT-000003", "Fashion", None, False),
    ("CAT-000004", "Books", None, False),
    ("CAT-000005", "Sports", None, False),
    ("CAT-000006", "Seasonal", None, True),
    ("CAT-000007", "Phones", "CAT-000001", False),
    ("CAT-000008", "Laptops", "CAT-000001", False),
    ("CAT-000009", "Kitchen", "CAT-000002", False),
    ("CAT-000010", "Furniture", "CAT-000002", False),
    ("CAT-000011", "Men Clothing", "CAT-000003", False),
    ("CAT-000012", "Women Clothing", "CAT-000003", False),
    ("CAT-000013", "Fiction", "CAT-000004", False),
    ("CAT-000014", "Fitness", "CAT-000005", False),
    ("CAT-000015", "Holiday Decor", "CAT-000006", True),
]

def ensure_dirs():
    for path in [RAW_DIR, GROUND_TRUTH_DIR, PROCESSED_DIR]:
        path.mkdir(parents=True, exist_ok=True)

def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def generate(scale, seed=SEED, inject_anomalies=True):
    """Generate reproducible synthetic data. Returns row counts and metadata."""
    ensure_dirs()
    random.seed(seed)
    rng = np.random.default_rng(seed)
    customers_n = scale["customers"]
    products_n = scale["products"]
    sessions_n = scale["sessions"]
    orders_n = scale["orders"]

    categories = [
        {"category_id": c[0], "category_name": c[1], "parent_category_id": c[2],
         "is_seasonal": c[3], "created_at": "2026-01-01T00:00:00Z"}
        for c in CATEGORIES
    ]
    category_ids = [c["category_id"] for c in categories]
    leaf_categories = [c[0] for c in CATEGORIES if c[2] is not None]
    customers = []
    for i in range(1, customers_n + 1):
        customers.append({
            "customer_id": f"CUS-{i:06d}",
            "created_at": (datetime(2025, 1, 1, tzinfo=timezone.utc) +
                           timedelta(days=int(rng.integers(0, 650)))).isoformat(),
            "segment": random.choices(["regular", "new", "high_value"], [0.72, 0.20, 0.08])[0],
            "is_active": random.random() > 0.04,
        })

    products = []
    for i in range(1, products_n + 1):
        cat = random.choice(leaf_categories)
        status = random.choices(["active", "out_of_stock", "discontinued"], [0.88, 0.08, 0.04])[0]
        products.append({
            "product_id": f"SKU-{i:06d}",
            "product_name": f"{cat.split('-')[-1]} Product {i:05d}",
            "category_id": cat,
            "price": round(float(rng.uniform(5, 1500)), 2),
            "inventory_qty": int(rng.integers(0, 250)),
            "product_status": status,
            "created_at": (datetime(2025, 1, 1, tzinfo=timezone.utc) +
                           timedelta(days=int(rng.integers(0, 650)))).isoformat(),
            "is_cold_start": i > int(products_n * 0.85),
        })

    # Build a stable product pool for event generation.
    product_ids = [p["product_id"] for p in products]
    active_ids = [p["product_id"] for p in products if p["product_status"] == "active" and p["inventory_qty"] > 0]
    if not active_ids:
        active_ids = product_ids[:]
    product_by_id = {p["product_id"]: p for p in products}

    # Build product pools by category.
    products_by_category = defaultdict(list)

    for product in products:
        products_by_category[product["category_id"]].append(
            product["product_id"]
    )

    # Assign two stable preferred categories to each customer.
    customer_preferences = {}

    for customer in customers:
        customer_preferences[customer["customer_id"]] = list(
            rng.choice(leaf_categories, size=2, replace=False)
    )


    sessions = []
    pageviews = []
    carts = []
    cartlines = []
    orders = []
    orderlines = []
    recommendations = []
    ground_truth = []
    session_by_customer = defaultdict(list)

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(1, sessions_n + 1):
        cust = customers[int(rng.integers(0, customers_n))]
        sid = f"SES-2026-{i:06d}"
        began = start + timedelta(seconds=int(rng.integers(0, 300 * 86400)))
        is_bot = random.random() < 0.025
        split = "train" if began < datetime(2026, 9, 1, tzinfo=timezone.utc) else "test"
        sessions.append({
            "session_id": sid, "customer_id": cust["customer_id"],
            "started_at": began.isoformat(),
            "ended_at": (began + timedelta(minutes=int(rng.integers(1, 90)))).isoformat(),
            "device": random.choice(["mobile", "desktop", "tablet"]),
            "is_bot": is_bot, "split": split,
        })
        session_by_customer[cust["customer_id"]].append(sid)

        n_views = int(rng.integers(1, 5 if not is_bot else 10))

        preferred_categories = customer_preferences[cust["customer_id"]]

        preferred_pool = [
            pid
            for category_id in preferred_categories
            for pid in products_by_category[category_id]
]

        viewed = []

        while len(viewed) < min(n_views, len(product_ids)):
            if is_bot or random.random() >= 0.8:
                pool = product_ids
            else:
                pool = preferred_pool

            candidate = random.choice(pool)

            if candidate not in viewed:
                viewed.append(candidate)

        for j, pid in enumerate(viewed, 1):
            event_time = began + timedelta(seconds=j * int(rng.integers(15, 180)))
            pageviews.append({
                "event_id": f"EVT-{sid}-{j:03d}", "session_id": sid,
                "customer_id": cust["customer_id"], "product_id": pid,
                "event_type": "product_view", "event_time": event_time.isoformat(),
                "is_test_event": False,
            })

    # Create orders with real parent customers and valid order lines.
    # Purchase products are selected from viewed items when possible.
    session_lookup = {s["session_id"]: s for s in sessions}
    views_by_session = defaultdict(list)
    for v in pageviews:
        views_by_session[v["session_id"]].append(v)

    order_to_session = {}
    for i in range(1, orders_n + 1):
        cust = customers[int(rng.integers(0, customers_n))]
        possible_sessions = session_by_customer[cust["customer_id"]]
        sid = random.choice(possible_sessions) if possible_sessions else None
        if sid:
            viewed_ids = [v["product_id"] for v in views_by_session[sid]]
        else:
            viewed_ids = []
        candidates = viewed_ids or random.sample(active_ids, min(3, len(active_ids)))
        chosen = random.sample(candidates, min(len(candidates), int(rng.integers(1, 4))))
        if sid:
            view_times = [datetime.fromisoformat(v["event_time"]) for v in views_by_session[sid]]
            order_time = (max(view_times) + timedelta(minutes=5)) if view_times else datetime.fromisoformat(session_lookup[sid]["started_at"]) + timedelta(minutes=5)
        else:
            order_time = start
        order_id = f"ORD-2026-{i:06d}"
        orders.append({
            "order_id": order_id, "customer_id": cust["customer_id"],
            "session_id": sid, "order_time": order_time.isoformat(),
            "order_status": random.choices(["completed", "cancelled"], [0.94, 0.06])[0],
            "currency": "USD",
        })
        order_to_session[order_id] = sid
        for j, pid in enumerate(chosen, 1):
            p = product_by_id[pid]
            qty = int(rng.integers(1, 4))
            orderlines.append({
                "order_line_id": f"OL-{i:06d}-{j:02d}", "order_id": order_id,
                "product_id": pid, "quantity": qty, "unit_price": p["price"],
                "line_total": round(qty * p["price"], 2),
            })

    # Cart and cart-line snapshots: subset of sessions, with valid references.
    cart_counter = 0
    for s in sessions:
        if random.random() < 0.22:
            cart_counter += 1
            cart_id = f"CART-2026-{cart_counter:06d}"
            cart_time = datetime.fromisoformat(s["started_at"]) + timedelta(minutes=2)
            carts.append({
                "cart_id": cart_id, "customer_id": s["customer_id"],
                "session_id": s["session_id"], "created_at": cart_time.isoformat(),
                "cart_status": random.choice(["active", "converted", "abandoned"]),
            })
            seen = [v["product_id"] for v in views_by_session[s["session_id"]]]
            for j, pid in enumerate(seen[:3], 1):
                p = product_by_id[pid]
                qty = int(rng.integers(1, 3))
                cartlines.append({
                    "cart_line_id": f"CL-{cart_counter:06d}-{j:02d}",
                    "cart_id": cart_id, "product_id": pid, "quantity": qty,
                    "unit_price": p["price"], "line_total": round(qty * p["price"], 2),
                })

     # Product relations are derived only from completed training orders.
    co_counts = defaultdict(int)
    lines_by_order = defaultdict(list)

    train_completed_orders = {
    o["order_id"]
    for o in orders
    if o["order_status"] == "completed"
    and o["session_id"] in session_lookup
    and session_lookup[o["session_id"]]["split"] == "train"
    and not session_lookup[o["session_id"]]["is_bot"]
}

    for line in orderlines:
        if line["order_id"] in train_completed_orders:
           lines_by_order[line["order_id"]].append(line["product_id"])
    for ids in lines_by_order.values():
        unique_ids = sorted(set(ids))
        for a in range(len(unique_ids)):
            for b in range(a + 1, len(unique_ids)):
                co_counts[(unique_ids[a], unique_ids[b])] += 1
    relations = []
    for idx, ((a, b), count) in enumerate(sorted(co_counts.items(), key=lambda x: (-x[1], x[0]))[:max(100, products_n * 2)], 1):
        relations.append({
            "relation_id": f"REL-{idx:07d}", "product_id": a,
            "related_product_id": b, "relation_type": "co_purchase",
            "strength": count, "effective_from": "2026-01-01T00:00:00Z",
            "effective_to": "",
        })

    # Recommendations are generated from category similarity and relation history.
    purchased_by_customer = defaultdict(set)
    for o in orders:
        if o["order_status"] == "completed":
            for line in lines_by_order[o["order_id"]]:
                purchased_by_customer[o["customer_id"]].add(line)
    products_by_cat = defaultdict(list)
    for p in products:
        products_by_cat[p["category_id"]].append(p["product_id"])
    rec_counter = 0
    for cust in customers[:min(customers_n, 2000)]:
        already = purchased_by_customer[cust["customer_id"]]
        seed_product = random.choice(product_ids)
        cat = product_by_id[seed_product]["category_id"]
        candidates = [pid for pid in products_by_cat[cat] if pid not in already and
                      product_by_id[pid]["product_status"] == "active" and
                      product_by_id[pid]["inventory_qty"] > 0]
        random.shuffle(candidates)
        for pid in candidates[:3]:
            rec_counter += 1
            recommendations.append({
                "recommendation_id": f"REC-{rec_counter:07d}",
                "customer_id": cust["customer_id"], "product_id": pid,
                "generated_at": "2026-10-01T00:00:00Z",
                "score": round(random.uniform(0.5, 1.0), 4),
                "model_version": "category-baseline-v1",
                "is_eligible": True,
            })

    if inject_anomalies and products and sessions and orders:
        # Explicit, labelled negative scenarios. They are added only to the event/recommendation inputs.
        # 1: Purchase before a valid view.
        bad_order_id = "ORD-ANOM-000001"
        orders.append({
            "order_id": bad_order_id, "customer_id": customers[0]["customer_id"],
            "session_id": sessions[0]["session_id"],
            "order_time": "2025-12-01T00:00:00+00:00",
            "order_status": "completed", "currency": "USD",
        })
        orderlines.append({
            "order_line_id": "OL-ANOM-000001-01", "order_id": bad_order_id,
            "product_id": products[0]["product_id"], "quantity": 1,
            "unit_price": products[0]["price"], "line_total": products[0]["price"],
        })
        ground_truth.append({"case_id": "GT-001", "record_type": "Order",
                             "record_id": bad_order_id, "issue_type": "purchase_before_session_view",
                             "expected_decision": "flag_invalid_temporal_sequence"})
        # 2: Product missing category (deliberately labelled, not a random FK corruption).
        products.append({
            "product_id": f"SKU-{products_n + 1:06d}", "product_name": "Anomaly Missing Category",
            "category_id": "", "price": 19.99, "inventory_qty": 5,
            "product_status": "active", "created_at": "2026-10-01T00:00:00+00:00",
            "is_cold_start": True,
        })
        ground_truth.append({"case_id": "GT-002", "record_type": "Product",
                             "record_id": f"SKU-{products_n + 1:06d}", "issue_type": "missing_product_category",
                             "expected_decision": "flag_missing_category"})
        # 3: A test event marked as training leakage.
        leak_session = next((s for s in sessions if s["split"] == "train"), sessions[0])
        leak_id = "EVT-LEAK-000001"
        pageviews.append({
            "event_id": leak_id, "session_id": leak_session["session_id"],
            "customer_id": leak_session["customer_id"], "product_id": products[0]["product_id"],
            "event_type": "product_view", "event_time": "2026-10-15T12:00:00+00:00",
            "is_test_event": True,
        })
        ground_truth.append({"case_id": "GT-003", "record_type": "PageView",
                             "record_id": leak_id, "issue_type": "test_event_leaks_into_training",
                             "expected_decision": "exclude_from_training"})
        # 4: Recommendation of discontinued item.
        discontinued = next((p for p in products if p["product_status"] == "discontinued"), None)
        if discontinued:
            rec_id = "REC-ANOM-000001"
            recommendations.append({
                "recommendation_id": rec_id, "customer_id": customers[0]["customer_id"],
                "product_id": discontinued["product_id"], "generated_at": "2026-10-01T00:00:00+00:00",
                "score": 0.99, "model_version": "injected-bad-v1", "is_eligible": False,
            })
            ground_truth.append({"case_id": "GT-004", "record_type": "Recommendation",
                                 "record_id": rec_id, "issue_type": "discontinued_product_recommended",
                                 "expected_decision": "reject_recommendation"})

    schemas = {
        "categories.csv": (["category_id","category_name","parent_category_id","is_seasonal","created_at"], categories),
        "customers.csv": (["customer_id","created_at","segment","is_active"], customers),
        "products.csv": (["product_id","product_name","category_id","price","inventory_qty","product_status","created_at","is_cold_start"], products),
        "sessions.csv": (["session_id","customer_id","started_at","ended_at","device","is_bot","split"], sessions),
        "pageviews.csv": (["event_id","session_id","customer_id","product_id","event_type","event_time","is_test_event"], pageviews),
        "carts.csv": (["cart_id","customer_id","session_id","created_at","cart_status"], carts),
        "cart_lines.csv": (["cart_line_id","cart_id","product_id","quantity","unit_price","line_total"], cartlines),
        "orders.csv": (["order_id","customer_id","session_id","order_time","order_status","currency"], orders),
        "order_lines.csv": (["order_line_id","order_id","product_id","quantity","unit_price","line_total"], orderlines),
        "product_relations.csv": (["relation_id","product_id","related_product_id","relation_type","strength","effective_from","effective_to"], relations),
        "recommendations.csv": (["recommendation_id","customer_id","product_id","generated_at","score","model_version","is_eligible"], recommendations),
    }
    counts = {}
    for filename, (fields, rows) in schemas.items():
        write_csv(RAW_DIR / filename, fields, rows)
        counts[filename] = len(rows)

    write_csv(GROUND_TRUTH_DIR / "ground_truth.csv",
              ["case_id","record_type","record_id","issue_type","expected_decision"], ground_truth)

    manifest = {
        "seed": seed, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generator": "SmartCart-AI synthetic generator",
        "provenance": "Entirely synthetic data; no personal or confidential source data used.",
        "scale": scale, "row_counts": counts,
    }
    (PROCESSED_DIR / "source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return counts
