from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import STARTER_SCALE, RAW_DIR
from src.generator import generate
from src.validation import validate
from src.recommender import build_recommendations, evaluate

def test_starter_pipeline():
    generate(STARTER_SCALE, seed=20261022)
    report = validate()
    assert report["total_checks"] > 0
    assert report["passed_checks"] > 0

def test_recommendations_exclude_unavailable_products():
    recs = build_recommendations(top_k=3)
    products = {}
    import csv
    with (RAW_DIR / "products.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            products[row["product_id"]] = row
    assert all(products[r["product_id"]]["product_status"] == "active" for r in recs)
    assert all(int(products[r["product_id"]]["inventory_qty"]) > 0 for r in recs)

def test_metrics_are_computed():
    metrics = evaluate(build_recommendations(top_k=3), k=3)
    assert "precision_at_k" in metrics
    assert "recall_at_k" in metrics
    assert "catalog_coverage" in metrics
