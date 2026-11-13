import csv
import sqlite3
from config import RAW_DIR, OUTPUT_DIR

TABLES = {
    "categories": "category_id TEXT PRIMARY KEY, category_name TEXT NOT NULL, parent_category_id TEXT, is_seasonal TEXT, created_at TEXT",
    "customers": "customer_id TEXT PRIMARY KEY, created_at TEXT, segment TEXT, is_active TEXT",
    "products": "product_id TEXT PRIMARY KEY, product_name TEXT, category_id TEXT, price REAL, inventory_qty INTEGER, product_status TEXT, created_at TEXT, is_cold_start TEXT",
    "sessions": "session_id TEXT PRIMARY KEY, customer_id TEXT, started_at TEXT, ended_at TEXT, device TEXT, is_bot TEXT, split TEXT",
    "pageviews": "event_id TEXT PRIMARY KEY, session_id TEXT, customer_id TEXT, product_id TEXT, event_type TEXT, event_time TEXT, is_test_event TEXT",
    "carts": "cart_id TEXT PRIMARY KEY, customer_id TEXT, session_id TEXT, created_at TEXT, cart_status TEXT",
    "cart_lines": "cart_line_id TEXT PRIMARY KEY, cart_id TEXT, product_id TEXT, quantity INTEGER, unit_price REAL, line_total REAL",
    "orders": "order_id TEXT PRIMARY KEY, customer_id TEXT, session_id TEXT, order_time TEXT, order_status TEXT, currency TEXT",
    "order_lines": "order_line_id TEXT PRIMARY KEY, order_id TEXT, product_id TEXT, quantity INTEGER, unit_price REAL, line_total REAL",
    "product_relations": "relation_id TEXT PRIMARY KEY, product_id TEXT, related_product_id TEXT, relation_type TEXT, strength INTEGER, effective_from TEXT, effective_to TEXT",
    "recommendations": "recommendation_id TEXT PRIMARY KEY, customer_id TEXT, product_id TEXT, generated_at TEXT, score REAL, model_version TEXT, is_eligible TEXT",
}
FILES = {
    "categories": "categories.csv", "customers": "customers.csv", "products": "products.csv",
    "sessions": "sessions.csv", "pageviews": "pageviews.csv", "carts": "carts.csv",
    "cart_lines": "cart_lines.csv", "orders": "orders.csv", "order_lines": "order_lines.csv",
    "product_relations": "product_relations.csv", "recommendations": "recommendations.csv",
}

def export_sql():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    db = OUTPUT_DIR / "smartcart_seed.sqlite"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    for table, definition in TABLES.items():
        cur.execute(f"CREATE TABLE {table} ({definition})")
        with (RAW_DIR / FILES[table]).open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames
            placeholders = ",".join(["?"] * len(columns))
            sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
            batch = []
            for row in reader:
                batch.append([row[c] for c in columns])
                if len(batch) >= 10000:
                    cur.executemany(sql, batch)
                    batch = []
            if batch:
                cur.executemany(sql, batch)
    con.commit()
    con.close()
    return str(db)
