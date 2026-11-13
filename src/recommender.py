
import csv
import math
from collections import defaultdict, Counter

from config import RAW_DIR, PROCESSED_DIR


def read_csv(name):
    path = RAW_DIR / name
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_recommendations(top_k=5):
    products = read_csv("products.csv")
    customers = read_csv("customers.csv")
    sessions = read_csv("sessions.csv")
    orders = read_csv("orders.csv")
    order_lines = read_csv("order_lines.csv")
    pageviews = read_csv("pageviews.csv")
    carts = read_csv("carts.csv")
    cart_lines = read_csv("cart_lines.csv")

    product_map = {p["product_id"]: p for p in products}
    session_map = {s["session_id"]: s for s in sessions}
    order_map = {o["order_id"]: o for o in orders}
    cart_map = {c["cart_id"]: c for c in carts}

    eligible_products = {
        p["product_id"]: p
        for p in products
        if p["product_status"] == "active"
        and int(p["inventory_qty"]) > 0
        and p["category_id"]
    }

    # Only non-bot training sessions are used.
    train_sessions = {
        s["session_id"]
        for s in sessions
        if s["split"] == "train"
        and str(s["is_bot"]).lower() == "false"
    }

    # Customer purchase history and product popularity.
    customer_bought = defaultdict(set)
    category_popularity = defaultdict(Counter)
    product_popularity = Counter()
    order_products = defaultdict(set)

    train_order_ids = {
        o["order_id"]
        for o in orders
        if o["order_status"] == "completed"
        and o["session_id"] in train_sessions
    }

    for line in order_lines:
        if line["order_id"] not in train_order_ids:
            continue

        order = order_map[line["order_id"]]
        customer_id = order["customer_id"]
        product_id = line["product_id"]

        if product_id not in product_map:
            continue

        quantity = int(line["quantity"])
        category_id = product_map[product_id]["category_id"]

        customer_bought[customer_id].add(product_id)
        product_popularity[product_id] += quantity
        category_popularity[customer_id][category_id] += quantity
        order_products[line["order_id"]].add(product_id)

    # Build product-to-product relationships using training orders only.
    related_products = defaultdict(Counter)

    for product_ids in order_products.values():
        product_ids = sorted(product_ids)

        for i, product_a in enumerate(product_ids):
            for product_b in product_ids[i + 1:]:
                related_products[product_a][product_b] += 1
                related_products[product_b][product_a] += 1

    # Collect valid product views from training sessions.
    customer_views = defaultdict(Counter)

    for event in pageviews:
        session_id = event["session_id"]

        if session_id not in train_sessions:
            continue

        if str(event["is_test_event"]).lower() == "true":
            continue

        if event["product_id"] not in eligible_products:
            continue

        if event["event_type"] != "product_view":
            continue

        customer_views[event["customer_id"]][event["product_id"]] += 1

    # Collect cart activity from training sessions only.
    customer_carts = defaultdict(Counter)

    valid_train_carts = {
        cart["cart_id"]
        for cart in carts
        if cart["session_id"] in train_sessions
    }

    for line in cart_lines:
        if line["cart_id"] not in valid_train_carts:
            continue

        if line["product_id"] not in eligible_products:
            continue

        cart = cart_map[line["cart_id"]]
        customer_carts[cart["customer_id"]][line["product_id"]] += int(
            line["quantity"]
        )

    # Precompute products ranked by training popularity.
    popular_products = [
        pid for pid, count in product_popularity.most_common()
        if pid in eligible_products
    ]

    category_products = defaultdict(list)

    for pid in eligible_products:
        category_id = product_map[pid]["category_id"]
        category_products[category_id].append(pid)

    for category_id in category_products:
        category_products[category_id].sort(
            key=lambda pid: (-product_popularity[pid], pid)
        )

    output = []

    for customer in customers:
        customer_id = customer["customer_id"]

        bought = customer_bought[customer_id]
        views = customer_views[customer_id]
        cart_history = customer_carts[customer_id]
        preferred_categories = category_popularity[customer_id]

        scores = defaultdict(float)
        reasons = defaultdict(Counter)

        def add_score(product_id, score, reason):
            if product_id not in eligible_products:
                return

            if product_id in bought:
                return

            scores[product_id] += score
            reasons[product_id][reason] += score

        # 1. General popularity helps cold-start customers.
        for pid in popular_products[:100]:
            add_score(
                pid,
                0.5 * math.log1p(product_popularity[pid]),
                "popularity"
            )

        # 2. Customer category preferences.
        for category_id, quantity in preferred_categories.most_common(3):
            category_weight = math.log1p(quantity)

            for pid in category_products.get(category_id, [])[:50]:
                add_score(
                    pid,
                    1.5 * category_weight
                    + 0.25 * math.log1p(product_popularity[pid]),
                    "preferred_category"
                )

        # 3. Products related to previous purchases.
        for seed_product in bought:
            for related_id, strength in related_products[seed_product].most_common(30):
                add_score(
                    related_id,
                    2.5 * math.log1p(strength),
                    "purchase_relation"
                )

        # 4. Products related to viewed products.
        for seed_product, view_count in views.most_common(20):
            for related_id, strength in related_products[seed_product].most_common(20):
                add_score(
                    related_id,
                    1.5 * math.log1p(strength)
                    * math.log1p(view_count),
                    "view_relation"
                )

        # 5. Directly viewed products.
        for pid, count in views.items():
            add_score(
                pid,
                2.0 * math.log1p(count),
                "view_history"
            )

        # 6. Products added to carts get a stronger signal.
        for pid, quantity in cart_history.items():
            add_score(
                pid,
                3.0 * math.log1p(quantity),
                "cart_history"
            )

        # Sort by score, then product ID for deterministic results.
        ranked = sorted(
            scores,
            key=lambda pid: (-scores[pid], pid)
        )[:top_k]

        for rank, pid in enumerate(ranked, 1):
            reason = (
                reasons[pid].most_common(1)[0][0]
                if reasons[pid]
                else "cold_start_popularity"
            )

            output.append({
                "customer_id": customer_id,
                "product_id": pid,
                "rank": rank,
                "score": round(scores[pid], 4),
                "reason": reason
            })

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    output_path = PROCESSED_DIR / "model_recommendations.csv"

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "customer_id",
                "product_id",
                "rank",
                "score",
                "reason"
            ]
        )
        writer.writeheader()
        writer.writerows(output)

    return output


def evaluate(recommendations=None, k=5):
    if recommendations is None:
        recommendations = build_recommendations(k)

    orders = read_csv("orders.csv")
    order_lines = read_csv("order_lines.csv")
    products = read_csv("products.csv")
    sessions = read_csv("sessions.csv")

    session_split = {
        s["session_id"]: s["split"]
        for s in sessions
    }

    order_map = {
        o["order_id"]: o
        for o in orders
    }

    # Test purchases are evaluation labels only.
    test_truth = defaultdict(set)

    for line in order_lines:
        order = order_map.get(line["order_id"])

        if (
            order
            and order["order_status"] == "completed"
            and order["session_id"]
            and session_split.get(order["session_id"]) == "test"
        ):
            test_truth[order["customer_id"]].add(line["product_id"])

    by_customer = defaultdict(list)

    for row in recommendations:
        by_customer[row["customer_id"]].append(row["product_id"])

    precisions = []
    recalls = []

    for customer_id, truth in test_truth.items():
        predicted = set(by_customer.get(customer_id, [])[:k])

        if predicted:
            precisions.append(
                len(predicted & truth) / len(predicted)
            )

        if truth:
            recalls.append(
                len(predicted & truth) / len(truth)
            )

    all_products = {
        p["product_id"] for p in products
    }

    recommended_products = {
        row["product_id"] for row in recommendations
    }

    product_map = {
        p["product_id"]: p for p in products
    }

    invalid = sum(
        1
        for row in recommendations
        if row["product_id"] not in product_map
        or product_map[row["product_id"]]["product_status"] != "active"
        or int(product_map[row["product_id"]]["inventory_qty"]) <= 0
        or not product_map[row["product_id"]]["category_id"]
    )

    return {
        "precision_at_k": round(
            sum(precisions) / max(1, len(precisions)), 4
        ),
        "recall_at_k": round(
            sum(recalls) / max(1, len(recalls)), 4
        ),
        "catalog_coverage": round(
            len(recommended_products) / max(1, len(all_products)), 4
        ),
        "recommendation_count": len(recommendations),
        "unavailable_recommendation_count": invalid,
        "k": k,
        "evaluation_method": (
            "Train on completed purchases, valid product views and cart "
            "activity from pre-2026-09-01 training sessions; evaluate "
            "against post-boundary test purchases."
        ),
        "evaluation_note": (
            "Offline metrics on synthetic data; not a production "
            "performance claim."
        )
    }
