# SmartCart AI

## Synthetic E-Commerce Data Generation & Product Recommendation Engine

SmartCart AI is a reproducible Python project that generates large-scale synthetic e-commerce data, validates data quality, identifies labelled anomalies, and generates personalized product recommendations using a hybrid recommendation engine.

The project includes a complete data generation pipeline, CSV and JSON exports, a SQLite database, recommendation evaluation, and an interactive Streamlit dashboard.

## Key Features

- **Synthetic data generation:** Starter and full-scale datasets with a configurable random seed.
- **11 related entities:** Customers, Products, Categories, Sessions, PageViews, Carts, CartLines, Orders, OrderLines, ProductRelations, and Recommendations.
- **Multiple export formats:** CSV, JSON, and SQLite.
- **Data validation:** Relational integrity, business rules, and data quality checks.
- **Anomaly detection:** Four deliberate, labelled edge cases maintained separately in ground truth.
- **Chronological data splitting:** Training sessions before 2026-09-01 and testing sessions on or after that date.
- **Hybrid recommendation engine:** Combines popularity, customer category preferences, product views, cart activity, and co-purchase relationships.
- **Recommendation eligibility:** Excludes previously purchased, unavailable, and discontinued products.
- **Cold-start handling:** Provides fallback recommendations for customers with limited or no purchase history.
- **Model evaluation:** Precision@K, Recall@K, and catalog coverage.
- **Interactive dashboard:** Streamlit-based analytics and dataset preview.
- **Automated tests:** Pytest-based pipeline tests.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core development |
| NumPy | Synthetic data generation |
| Pandas | Data processing and analysis |
| SQLite | Relational database export |
| Streamlit | Interactive dashboard |
| Pytest | Automated testing |

## Project Structure

```text
SmartCart-AI/
│
├── dashboard/
│   └── app.py
│
├── data/
│   ├── raw/              # Generated CSV datasets
│   ├── processed/        # Recommendations and manifest
│   ├── ground_truth/     # Separate anomaly labels
│   └── json/             # JSON entity exports
│
├── docs/
│   ├── architecture.md
│   └── data_dictionary.md
│
├── outputs/
│   ├── run_summary.json
│   ├── validation_report.json
│   └── smartcart_seed.sqlite
│
├── src/
│   ├── baseline.py
│   ├── compare_models.py
│   ├── export_json.py
│   ├── export_sql.py
│   ├── generator.py
│   ├── recommender.py
│   └── validation.py
│
├── tests/
│   └── test_pipeline.py
│
├── config.py
├── main.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Requirements

- Python 3.10 or newer
- pip
- Git (optional)

## Installation (Windows)

Clone the repository or download the project.

Open PowerShell in the project directory.

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Running the Pipeline

### Starter dataset

For quick development and testing:

```powershell
python main.py --scale starter
```

### Full-scale dataset

To generate the full challenge dataset:

```powershell
python main.py --scale full
```

### Custom random seed

```powershell
python main.py --scale full --seed 20261022
```

The default random seed is `20261022`.

The full-scale configuration starts with:

- 20,000 customers
- 10,000 products
- 500,000 sessions
- 100,000 orders

The generated dataset also contains deliberate anomaly records, so some final entity counts are slightly higher than the base targets.

## Data Generation and Exports

The pipeline generates 11 related entity datasets.

| Entity | CSV / JSON filename |
|---|---|
| Categories | categories |
| Customers | customers |
| Products | products |
| Sessions | sessions |
| PageViews | pageviews |
| Carts | carts |
| CartLines | cart_lines |
| Orders | orders |
| OrderLines | order_lines |
| ProductRelations | product_relations |
| Recommendations | recommendations |

Generated files:

- `data/raw/` — CSV datasets.
- `data/json/` — JSON arrays for all 11 entities.
- `data/ground_truth/ground_truth.csv` — separately maintained anomaly labels.
- `data/processed/` — recommendation outputs and source manifest.
- `outputs/smartcart_seed.sqlite` — SQLite database containing entity tables.
- `outputs/run_summary.json` — generation summary, evaluation metrics, export information, and CSV checksums.
- `outputs/validation_report.json` — validation results.

JSON exports can also be generated independently:

```powershell
python -m src.export_json
```

## Recommendation Engine

SmartCart AI implements a hybrid recommendation approach using multiple customer and product signals:

1. Product popularity.
2. Customer category preferences.
3. Products frequently purchased together.
4. Product viewing activity.
5. Cart activity.

The engine applies eligibility filters to avoid recommending products that customers have already purchased or that are unavailable or discontinued.

Customers with insufficient interaction history receive fallback recommendations.

### Evaluation Metrics

The recommendation engine is evaluated using:

- **Precision@K:** Proportion of recommended products that match held-out purchases.
- **Recall@K:** Proportion of held-out purchased products retrieved by recommendations.
- **Catalog Coverage:** Percentage of the eligible product catalog recommended.

Evaluation uses a chronological train/test split to reduce information leakage.

### Current Full-Scale Evaluation

The current generated dataset produced the following hybrid recommendation results:

| Metric | Result |
|---|---:|
| Precision@5 | 0.0008 |
| Recall@5 | 0.0016 |
| Catalog Coverage | 50.31% |
| Recommendation Count | 100,000 |
| Unavailable Recommendations | 0 |

These are offline metrics on synthetic data. They are illustrative experimental results, not claims of production recommendation performance.

## Streamlit Dashboard

Launch the dashboard:

```powershell
python -m streamlit run dashboard/app.py
```

Open the local URL displayed in your terminal, usually:

```text
http://localhost:8501
```

Dashboard features:

- Dataset overview.
- Data validation results.
- Recommendation evaluation metrics.
- CSV dataset preview.
- CSV and JSON export information.
- Pipeline run information.

The dashboard previews only the first 100 rows of the selected CSV to avoid loading large datasets entirely into memory.

## Validation and Testing

Run the automated test suite:

```powershell
python -m pytest -v
```

The full-scale pipeline has completed with:

- 35 validation checks passed.
- 0 validation failures.

**Note:** The starter pipeline test regenerates starter-scale data. Run the full pipeline again afterward if you want to restore the full-scale generated files.

## Reproducibility

Run the pipeline with the same scale and seed:

```powershell
python main.py --scale starter --seed 20261022
```

The pipeline calculates SHA-256 checksums for generated CSV files. Compare the checksums in `outputs/run_summary.json` to verify reproducibility.

The manifest generation timestamp is metadata and will differ between runs. Generated data should remain deterministic for a fixed scale and seed.

## Data Provenance and Privacy

All records are synthetically generated by this project.

No real customer information, credentials, confidential business data, or external customer datasets are used.

The ground-truth anomaly labels are stored separately from recommendation features.

## Project Limitations

- The dataset is synthetic and does not represent real customer behaviour.
- Recommendation evaluation results depend on the generated interaction patterns.
- Offline metrics should not be interpreted as real-world business impact.
- The project is an experimental recommendation and data engineering demonstration, not a production e-commerce platform.

## Future Improvements

- Add additional recommendation algorithms.
- Improve recommendation ranking and evaluation.
- Introduce interactive customer-level recommendation explanations.
- Add API endpoints for recommendation serving.
- Explore scalable processing for larger datasets.

---

**SmartCart AI — Synthetic Data Generation, Data Quality Validation & Hybrid Product Recommendations.**