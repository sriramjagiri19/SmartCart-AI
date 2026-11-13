
import csv
import json
from pathlib import Path

from config import RAW_DIR, DATA_DIR

JSON_DIR = DATA_DIR / "json"

INTEGER_FIELDS = {
    "inventory_qty",
    "quantity",
    "strength",
}

FLOAT_FIELDS = {
    "price",
    "unit_price",
    "line_total",
    "score",
}

BOOLEAN_FIELDS = {
    "is_seasonal",
    "is_active",
    "is_bot",
    "is_test_event",
    "is_cold_start",
    "is_eligible",
}


def convert_value(key, value):
    if value == "":
        return None

    if key in BOOLEAN_FIELDS:
        return value.strip().lower() in {"true", "1", "yes"}

    if key in INTEGER_FIELDS:
        return int(value)

    if key in FLOAT_FIELDS:
        return float(value)

    return value


def export_json():
    JSON_DIR.mkdir(parents=True, exist_ok=True)

    exported = {}

    for csv_path in sorted(RAW_DIR.glob("*.csv")):
        json_path = JSON_DIR / f"{csv_path.stem}.json"
        temp_path = JSON_DIR / f"{csv_path.stem}.json.tmp"

        row_count = 0

        try:
            with csv_path.open(
                "r", encoding="utf-8", newline=""
            ) as source:
                reader = csv.DictReader(source)

                with temp_path.open(
                    "w", encoding="utf-8"
                ) as target:
                    target.write("[\n")

                    for row in reader:
                        record = {
                            key: convert_value(key, value)
                            for key, value in row.items()
                        }

                        if row_count > 0:
                            target.write(",\n")

                        json.dump(
                            record,
                            target,
                            ensure_ascii=False,
                        )

                        row_count += 1

                    target.write("\n]\n")

            temp_path.replace(json_path)

            exported[json_path.name] = {
                "rows": row_count,
                "size_bytes": json_path.stat().st_size,
            }

            print(f"Exported: {json_path.name} ({row_count:,} rows)")

        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    return exported


if __name__ == "__main__":
    results = export_json()

    print("\nJSON export completed.")
    print(f"Total files: {len(results)}")
    print(
        f"Total rows: {sum(item['rows'] for item in results.values()):,}"
    )
