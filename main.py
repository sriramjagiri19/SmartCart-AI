
import argparse
import json
import hashlib

from config import STARTER_SCALE, FULL_SCALE, SEED, RAW_DIR, OUTPUT_DIR
from src.generator import generate
from src.validation import validate
from src.recommender import build_recommendations, evaluate
from src.export_sql import export_sql
from src.export_json import export_json


def checksum(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def run(scale_name, seed):
    scale = STARTER_SCALE if scale_name == "starter" else FULL_SCALE

    counts = generate(scale, seed=seed)

    recommendations = build_recommendations()

    metrics = evaluate(recommendations)

    validation = validate()

    db_path = export_sql()

    json_exports = export_json()

    checksums = {
        p.name: checksum(p)
        for p in sorted(RAW_DIR.glob("*.csv"))
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "seed": seed,
        "scale": scale_name,
        "row_counts": counts,
        "validation": validation,
        "recommendation_metrics": metrics,
        "sqlite_database": db_path,
        "json_exports": json_exports,
        "csv_sha256": checksums,
    }

    summary_path = OUTPUT_DIR / "run_summary.json"

    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8"
    )

    print(json.dumps({
        "row_counts": counts,
        "validation_passed": validation["passed_checks"],
        "validation_failed": validation["failed_checks"],
        "recommendation_metrics": metrics,
        "sqlite_database": db_path,
        "json_files_exported": len(json_exports),
        "json_total_rows": sum(
            item["rows"] for item in json_exports.values()
        ),
        "summary_file": str(summary_path),
    }, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SmartCart AI synthetic data and recommendation pipeline"
    )

    parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=SEED
    )

    args = parser.parse_args()

    run(args.scale, args.seed)
