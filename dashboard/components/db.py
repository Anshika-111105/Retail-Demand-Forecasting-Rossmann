from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

from src.utils.db_loader import get_postgres_engine  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")


@st.cache_resource
def get_engine():
    """One pooled SQLAlchemy engine shared across all pages/reruns in a session."""
    return get_postgres_engine()


@st.cache_data(ttl=600)
def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Run a parameterized SQL query and return the result as a DataFrame, cached for 10 minutes."""
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def in_clause(values: list[int]) -> str:
    """Build a safe SQL IN (...) clause for a list of integer store IDs (never free text)."""
    if not values:
        return "(-1)"  # matches nothing
    return "(" + ",".join(str(int(v)) for v in values) + ")"
