
import csv
from collections import defaultdict, Counter

from config import RAW_DIR, PROCESSED_DIR


def read_csv(name):
    with (RAW_DIR / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_popularity_recommendations(top_k=5):
    products = read_csv("products.csv")
    sessions = read_csv("sessions.csv")
    orders = read_csv("orders.csv")
    order_lines = read_csv("order_lines.csv")
    customers = read_csv("customers.csv")

    product_map = {p["product_id"]: p for p in products}
    session_map = {s["session_id"]: s for s in sessions}
    order_map = {o["order_id"]: o for o in orders}

    eligible = {
        p["product_id"]
        for p in products
        if p["product_status"] == "active"
        and int(p["inventory_qty"]) > 0
        and p["category_id"]
    }

    train_sessions = {
        s["session_id"]
        for s in sessions
        if s["split"] == "train"
        and s["is_bot"].lower() == "false"
    }

    train_orders = {
        o["order_id"]
        for o in orders
        if o["order_status"] == "completed"
        and o["session_id"] in train_sessions
    }

    popularity = Counter()
    bought = defaultdict(set)

    for line in order_lines:
        if line["order_id"] not in train_orders:
            continue

        order = order_map[line["order_id"]]
        pid = line["product_id"]

        if pid in eligible:
            popularity[pid] += int(line["quantity"])
            bought[order["customer_id"]].add(pid)

    ranked_products = [
        pid for pid, count in popularity.most_common()
        if pid in eligible
    ]

    output = []

    for customer in customers:
        customer_id = customer["customer_id"]
        recommendations = []

        for pid in ranked_products:
            if pid in bought[customer_id]:
                continue

            recommendations.append(pid)

            if len(recommendations) == top_k:
                break

        for rank, pid in enumerate(recommendations, 1):
            output.append({
                "customer_id": customer_id,
                "product_id": pid,
                "rank": rank,
                "score": popularity[pid],
                "reason": "global_popularity"
            })

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    with (PROCESSED_DIR / "popularity_recommendations.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
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
