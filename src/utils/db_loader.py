from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_STORE_COLUMN_MAP = {
    "Store": "store_id",
    "StoreType": "store_type",
    "Assortment": "assortment",
    "CompetitionDistance": "competition_distance_m",
    "CompetitionOpenSinceMonth": "competition_open_since_month",
    "CompetitionOpenSinceYear": "competition_open_since_year",
    "Promo2": "promo2_enrolled",
    "Promo2SinceWeek": "promo2_since_week",
    "Promo2SinceYear": "promo2_since_year",
    "PromoInterval": "promo_interval",
}

_FACT_COLUMN_MAP = {
    "Store": "store_id",
    "Date": "sale_date",
    "DayOfWeek": "day_of_week",
    "Sales": "sales",
    "Customers": "customers",
    "Open": "is_open",
    "Promo": "is_promo",
    "StateHoliday": "state_holiday",
    "SchoolHoliday": "is_school_holiday",
}


def get_postgres_engine() -> Engine:
    """Build a SQLAlchemy engine from config or environment variables."""
    from config import cfg
    host = os.environ.get("DB_HOST", cfg.db_host)
    port = os.environ.get("DB_PORT", str(cfg.db_port))
    name = os.environ.get("DB_NAME", cfg.db_name)
    user = os.environ.get("DB_USER", cfg.db_user)
    password = os.environ.get("DB_PASSWORD", cfg.db_password)
    return create_engine(f"postgresql+pg8000://{user}:{password}@{host}:{port}/{name}")


def _prepare_dim_store(train_df: pd.DataFrame) -> pd.DataFrame:
    dim_store = (
        train_df[list(_STORE_COLUMN_MAP.keys())]
        .drop_duplicates(subset="Store")
        .rename(columns=_STORE_COLUMN_MAP)
    )
    dim_store["promo2_enrolled"] = dim_store["promo2_enrolled"].astype(bool)
    return dim_store.astype(object).where(pd.notna(dim_store), None)


def _prepare_fact_sales(train_df: pd.DataFrame) -> pd.DataFrame:
    fact_sales = train_df[list(_FACT_COLUMN_MAP.keys())].rename(columns=_FACT_COLUMN_MAP)
    fact_sales["is_open"] = fact_sales["is_open"].astype(bool)
    fact_sales["is_promo"] = fact_sales["is_promo"].astype(bool)
    fact_sales["is_school_holiday"] = fact_sales["is_school_holiday"].astype(bool)
    fact_sales["state_holiday"] = fact_sales["state_holiday"].astype(str)
    return fact_sales


def load_rossmann_to_postgres(processed_dir: Path, engine: Engine | None = None) -> None:
    """Load the Phase 3 merged training dataset into the dim_store/fact_sales warehouse tables.

    Run sql/schemas/01_create_tables.sql against the target database first.
    """
    engine = engine or get_postgres_engine()
    train = pd.read_parquet(processed_dir / "rossmann_train_store_merged.parquet")

    dim_store = _prepare_dim_store(train)
    fact_sales = _prepare_fact_sales(train)

    with engine.begin() as conn:
        dim_store.to_sql("dim_store", conn, if_exists="append", index=False, method="multi", chunksize=500)
    with engine.begin() as conn:
        fact_sales.to_sql("fact_sales", conn, if_exists="append", index=False, method="multi", chunksize=5000)
