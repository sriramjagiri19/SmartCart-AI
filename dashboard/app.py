
import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "outputs"

st.set_page_config(
    page_title="SmartCart AI",
    page_icon="🛒",
    layout="wide"
)

st.title("SmartCart AI")
st.caption(
    "Synthetic e-commerce data quality and product recommendation analytics"
)

summary_path = OUT / "run_summary.json"

if not summary_path.exists():
    st.warning(
        "No pipeline output found. Run python main.py --scale starter first."
    )
    st.stop()

summary = json.loads(summary_path.read_text(encoding="utf-8"))

counts = summary["row_counts"]

st.header("Dataset overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Customers", f'{counts.get("customers.csv", 0):,}')
c2.metric("Products", f'{counts.get("products.csv", 0):,}')
c3.metric("Sessions", f'{counts.get("sessions.csv", 0):,}')
c4.metric("Orders", f'{counts.get("orders.csv", 0):,}')

st.divider()

st.header("Data validation")

report = summary["validation"]

a, b, c = st.columns(3)

a.metric("Checks passed", report["passed_checks"])
b.metric("Checks failed", report["failed_checks"])
c.metric("Total checks", report["total_checks"])

st.dataframe(
    pd.DataFrame(report["checks"]),
    use_container_width=True,
    hide_index=True
)

st.divider()

st.header("Recommendation evaluation")

metrics = summary["recommendation_metrics"]

metric_columns = st.columns(len(metrics))

for column, (name, value) in zip(metric_columns, metrics.items()):
    if isinstance(value, float):
        column.metric(name.replace("_", " ").title(), f"{value:.4f}")
    else:
        column.metric(name.replace("_", " ").title(), value)

st.divider()

st.header("Dataset preview")

dataset_files = sorted(RAW.glob("*.csv"))

if dataset_files:
    dataset_names = [file.name for file in dataset_files]

    selected_dataset = st.selectbox(
        "Choose a dataset",
        dataset_names
    )

    selected_path = RAW / selected_dataset

    preview = pd.read_csv(
        selected_path,
        nrows=100
    )

    st.caption(
        f"Showing first {len(preview):,} rows "
        f"and {len(preview.columns)} columns"
    )

    st.dataframe(
        preview,
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("No CSV datasets found.")

st.divider()

st.header("Export information")

json_exports = summary.get("json_exports", {})

col1, col2, col3 = st.columns(3)

col1.metric("CSV datasets", len(dataset_files))
col2.metric("JSON datasets", len(json_exports))
col3.metric(
    "JSON records",
    f'{sum(item["rows"] for item in json_exports.values()):,}'
)

st.divider()

st.header("Run information")

st.write({
    "Seed": summary["seed"],
    "Scale": summary["scale"],
    "SQLite database": summary["sqlite_database"]
})
