from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.db import run_query  # noqa: E402

st.set_page_config(page_title="RetailX — Rossmann Analytics Platform", layout="wide")

st.title("RetailX — Retail Demand Forecasting & Inventory Optimization Platform")
st.caption("Rossmann Store Sales — 1,115 stores, 2013-01-01 to 2015-07-31")

st.markdown(
    """
Use the pages in the sidebar to explore store performance, promotion effectiveness, holiday
impact, and regional analytics — all backed live by the PostgreSQL warehouse built in
[Phase 5](../docs/Phase5_SQL_Analytics.md). Forecast and Inventory Planning pages will go live
once [Phase 7](../docs/Phase7_Machine_Learning_Strategy.md) modeling is complete.
"""
)

summary = run_query(
    """
    SELECT
        COUNT(DISTINCT store_id) AS n_stores,
        SUM(sales) AS total_sales,
        SUM(customers) AS total_customers,
        MIN(sale_date) AS min_date,
        MAX(sale_date) AS max_date
    FROM fact_sales
    WHERE is_open = TRUE
    """
).iloc[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Stores", f"{summary['n_stores']:,}")
col2.metric("Total Revenue", f"€{summary['total_sales']:,.0f}")
col3.metric("Total Customers", f"{summary['total_customers']:,.0f}")
col4.metric("Days of History", f"{(summary['max_date'] - summary['min_date']).days:,}")
