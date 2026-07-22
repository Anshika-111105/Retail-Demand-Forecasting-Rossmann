# Retail Demand Forecasting & Inventory Optimization Platform

RetailX analytics platform — built following CRISP-DM methodology — covering
data preparation, exploratory analysis, feature engineering, demand
forecasting (Prophet, XGBoost, LightGBM), and an inventory-optimization
dashboard on top of the Kaggle **Rossmann Store Sales** dataset (1,115+
drugstore locations across multiple regions).

## Project Structure

```
.
├── data/
│   ├── raw/                # Original, immutable Rossmann source files (never edited)
│   ├── interim/             # Intermediate outputs between cleaning steps
│   ├── processed/           # Final, analysis-ready merged dataset (train + store)
│   └── external/            # Third-party/supplementary data (e.g. German public holidays, macro data)
├── notebooks/                # Exploratory & phase-driven Jupyter notebooks (numbered)
├── sql/
│   ├── schemas/              # DDL — table/view definitions for the warehouse
│   ├── queries/               # Ad-hoc and reporting SQL queries
│   └── views/                 # Reusable SQL views for BI/reporting
├── dashboard/
│   ├── pages/                 # Streamlit multi-page app pages
│   ├── components/            # Reusable UI components (charts, filters, KPIs)
│   └── assets/                 # Static assets (logos, css, images)
├── src/
│   ├── feature_engineering/    # Feature creation logic (lags, rolling stats, calendar features)
│   ├── machine_learning/       # Model training, evaluation, inference code
│   └── utils/                  # Shared helpers (I/O, logging, validation)
├── config/                     # Environment/pipeline configuration files (YAML/JSON)
├── models/
│   ├── trained/                 # Serialized trained model artifacts
│   └── artifacts/                # Metrics, feature importances, encoders, scalers
├── reports/
│   ├── figures/                  # Generated charts/plots for reporting
│   └── screenshots/               # Dashboard/app screenshots for documentation
├── docs/                          # Phase-by-phase CRISP-DM documentation
├── logs/                          # Runtime/pipeline execution logs
├── tests/
│   ├── unit/                       # Unit tests for individual functions/modules
│   └── integration/                 # End-to-end pipeline tests
├── deployment/
│   ├── docker/                       # Dockerfile(s) and container configs
│   └── ci_cd/                         # CI/CD pipeline definitions
├── README.md                          # Project overview (this file)
├── requirements.txt                    # Python dependencies
├── .gitignore                          # Files/folders excluded from version control
├── LICENSE                              # Project license
├── .env.example                         # Template for required environment variables
├── config.py                            # Central configuration loader
└── main.py                              # Project entry point
```

### Folder Purpose Summary

| Folder | Purpose |
|---|---|
| `data/raw` | Untouched original Rossmann CSVs (`train.csv`, `store.csv`, `test.csv`, `sample_submission.csv`) — single source of truth |
| `data/interim` | Partially cleaned/transformed data between pipeline steps |
| `data/processed` | Final merged, analysis-ready dataset (`train.csv` joined with `store.csv`) |
| `data/external` | Supplementary external data not part of the original Rossmann release |
| `notebooks` | Numbered, phase-aligned notebooks (e.g. `01_data_preparation.ipynb`) |
| `sql` | All SQL assets for warehouse modeling and reporting |
| `dashboard` | Streamlit application for inventory/demand visualization |
| `src/feature_engineering` | Reusable feature-building code for modeling |
| `src/machine_learning` | Training/evaluation/inference logic for Prophet/XGBoost/LightGBM |
| `src/utils` | Shared, generic helper functions used across the codebase |
| `config` | Non-secret configuration files (paths, parameters, column maps) |
| `models` | Persisted model binaries and their supporting artifacts |
| `reports` | Output visuals and screenshots for stakeholders/documentation |
| `docs` | CRISP-DM phase deliverables and technical write-ups |
| `logs` | Structured logs from data pipelines and model runs |
| `tests` | Automated unit and integration tests |
| `deployment` | Containerization and CI/CD configuration |

## Dataset

**Source:** [Rossmann Store Sales](https://www.kaggle.com/c/rossmann-store-sales) (Kaggle)

Rossmann operates 1,115+ drugstores across several European regions. The
dataset provides ~2.5 years (2013-01-01 to 2015-07-31) of daily sales history
per store (`train.csv`), a store attribute table with competition and
promotion metadata (`store.csv`), and a held-out test window (`test.csv`).
It was chosen over the original M5 Forecasting – Accuracy dataset because it
is already in a long (tidy) daily format — no wide-to-long reshape is
required — keeping memory footprint and feature-engineering runtime workable
on constrained local hardware (8 GB RAM, no discrete GPU) while still
representing a realistic multi-store demand forecasting and inventory
optimization problem.

See [docs/Phase1_Business_Understanding.md](docs/Phase1_Business_Understanding.md)
and [docs/Phase2_Data_Understanding.md](docs/Phase2_Data_Understanding.md) for
the full business and data understanding write-ups.
