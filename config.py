from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
GROUND_TRUTH_DIR = DATA_DIR / "ground_truth"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

SEED = 20261022

# Starter scale is quick to run and useful for development.
STARTER_SCALE = {
    "customers": 500,
    "products": 300,
    "sessions": 5000,
    "orders": 1000,
}

# Required challenge scale. Use --scale full to generate this volume.
FULL_SCALE = {
    "customers": 20000,
    "products": 10000,
    "sessions": 500000,
    "orders": 100000,
}
