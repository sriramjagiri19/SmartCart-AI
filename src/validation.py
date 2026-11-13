import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from config import RAW_DIR,PROCESSED_DIR, GROUND_TRUTH_DIR, OUTPUT_DIR

def read_csv(name):
    with (RAW_DIR / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def validate():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    customers = read_csv("customers.csv")
    categories = read_csv("categories.csv")
    products = read_csv("products.csv")
    sessions = read_csv("sessions.csv")
    pageviews = read_csv("pageviews.csv")
    carts = read_csv("carts.csv")
    cart_lines = read_csv("cart_lines.csv")
    orders = read_csv("orders.csv")
    order_lines = read_csv("order_lines.csv")
    recs = read_csv("recommendations.csv")

    checks = []
    def check(name, passed, details=""):
        checks.append({"check": name, "passed": bool(passed), "details": details})

    def unique(rows, key):
        vals = [r[key] for r in rows]
        return len(vals) == len(set(vals))

    check("customer_primary_key_unique", unique(customers, "customer_id"))
    check("category_primary_key_unique", unique(categories, "category_id"))
    check("product_primary_key_unique", unique(products, "product_id"))
    check("session_primary_key_unique", unique(sessions, "session_id"))
    check("pageview_primary_key_unique", unique(pageviews, "event_id"))
    check("cart_primary_key_unique", unique(carts, "cart_id"))
    check("cart_line_primary_key_unique", unique(cart_lines, "cart_line_id"))
    check("order_primary_key_unique", unique(orders, "order_id"))
    check("order_line_primary_key_unique", unique(order_lines, "order_line_id"))
    check("recommendation_primary_key_unique", unique(recs, "recommendation_id"))

    customer_ids = {r["customer_id"] for r in customers}
    category_ids = {r["category_id"] for r in categories}
    product_ids = {r["product_id"] for r in products}
    session_ids = {r["session_id"] for r in sessions}
    cart_ids = {r["cart_id"] for r in carts}
    order_ids = {r["order_id"] for r in orders}

    check("session_customer_fk", all(r["customer_id"] in customer_ids for r in sessions))
    check("product_category_fk_except_labelled_case",
          all((r["category_id"] in category_ids) or r["category_id"] == "" for r in products))
    check("pageview_session_fk", all(r["session_id"] in session_ids for r in pageviews))
    check("pageview_customer_fk", all(r["customer_id"] in customer_ids for r in pageviews))
    check("pageview_product_fk", all(r["product_id"] in product_ids for r in pageviews))
    check("cart_session_fk", all(r["session_id"] in session_ids for r in carts))
    check("cart_customer_fk", all(r["customer_id"] in customer_ids for r in carts))
    check("cart_line_cart_fk", all(r["cart_id"] in cart_ids for r in cart_lines))
    check("cart_line_product_fk", all(r["product_id"] in product_ids for r in cart_lines))
    check("order_customer_fk", all(r["customer_id"] in customer_ids for r in orders))
    check("order_session_fk_optional", all((not r["session_id"]) or r["session_id"] in session_ids for r in orders))
    check("order_line_order_fk", all(r["order_id"] in order_ids for r in order_lines))
    check("order_line_product_fk", all(r["product_id"] in product_ids for r in order_lines))
    check("recommendation_customer_fk", all(r["customer_id"] in customer_ids for r in recs))
    check("recommendation_product_fk", all(r["product_id"] in product_ids for r in recs))

    # Reconcile line totals from quantity * unit price.
    def amounts_ok(rows):
        return all(abs(float(r["line_total"]) - int(r["quantity"]) * float(r["unit_price"])) < 0.02 for r in rows)
    check("cart_line_arithmetic", amounts_ok(cart_lines))
    check("order_line_arithmetic", amounts_ok(order_lines))
    check("allowed_product_status", all(r["product_status"] in {"active","out_of_stock","discontinued"} for r in products))
    check("allowed_session_split", all(r["split"] in {"train","test"} for r in sessions))

    # Leakage: all sessions in test partition start on/after split boundary.
    boundary = "2026-09-01"
    temporal_ok = all((r["split"] == "train" and r["started_at"] < boundary) or
                      (r["split"] == "test" and r["started_at"] >= boundary) for r in sessions)
    check("chronological_session_split", temporal_ok)

    # Detect a test-labelled event attached to a training session.
    session_split = {r["session_id"]: r["split"] for r in sessions}
    leaked_events = [
        r for r in pageviews
        if r["is_test_event"].lower() == "true"
        and session_split.get(r["session_id"]) == "train"
    ]
    check("test_event_leakage_detected", len(leaked_events) >= 1,
          f"{len(leaked_events)} test-labelled event(s) attached to train session(s)")

    # Detect labelled exceptions without silently treating them as normal rows.

    # Validate the four specific ground-truth cases
    truth_path = GROUND_TRUTH_DIR / "ground_truth.csv"

    with truth_path.open(newline="", encoding="utf-8") as f:
        truth = list(csv.DictReader(f))

    expected_cases = {
        "GT-001": ("purchase_before_session_view", "flag_invalid_temporal_sequence"),
        "GT-002": ("missing_product_category", "flag_missing_category"),
        "GT-003": ("test_event_leaks_into_training", "exclude_from_training"),
        "GT-004": ("discontinued_product_recommended", "reject_recommendation")
    }

    actual_cases = {
        row["case_id"]: (row["issue_type"], row["expected_decision"])
        for row in truth
    }

    check(
        "four_labelled_edge_cases_present",
        all(actual_cases.get(k) == v for k, v in expected_cases.items()),
        f"Found {len(actual_cases)} ground-truth cases"
    )

    # Verify the deliberate test-event leakage
    check(
        "test_event_leakage_detected",
        len(leaked_events) >= 1,
        f"{len(leaked_events)} leaked event(s) detected"
    )

    # Verify unavailable products in raw recommendation anomalies
    rec_product = {p["product_id"]: p for p in products}

    rejected_bad_recs = [
        r for r in recs
        if r["product_id"] in rec_product
        and (
            rec_product[r["product_id"]]["product_status"] != "active"
            or int(rec_product[r["product_id"]]["inventory_qty"]) <= 0
        )
    ]

    check(
        "unavailable_recommendations_detectable",
        len(rejected_bad_recs) >= 1,
        f"{len(rejected_bad_recs)} unavailable recommendation(s) detected"
    )

    # Verify final model recommendations contain only eligible products
    model_path = PROCESSED_DIR / "model_recommendations.csv"

    with model_path.open(newline="", encoding="utf-8") as f:
        model_recs = list(csv.DictReader(f))

    final_invalid = [
        r for r in model_recs
        if r["product_id"] not in rec_product
        or rec_product[r["product_id"]]["product_status"] != "active"
        or int(rec_product[r["product_id"]]["inventory_qty"]) <= 0
        or not rec_product[r["product_id"]]["category_id"]
    ]

    check(
        "final_recommendations_exclude_unavailable_products",
        len(final_invalid) == 0,
        f"{len(final_invalid)} invalid final recommendation(s)"
    )

    report = {
        "total_checks": len(checks),
        "passed_checks": sum(c["passed"] for c in checks),
        "failed_checks": sum(not c["passed"] for c in checks),
        "checks": checks,
        "notes": [
            "The missing-category product is a deliberate labelled anomaly.",
            "The temporal anomaly is deliberately retained for detection.",
            "Ground truth is stored separately and must not be used as model input."
        ]
    }
    (OUTPUT_DIR / "validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
