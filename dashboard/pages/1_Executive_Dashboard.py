from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.db import in_clause, run_query  # noqa: E402
from dashboard.components.filters import promo_sql_clause, render_sidebar_filters  # noqa: E402

st.set_page_config(page_title="Executive Dashboard", layout="wide")
st.title("Executive Dashboard")
st.caption("Chain-wide health check: revenue, traffic, and top/bottom performers.")

f = render_sidebar_filters()
store_clause = in_clause(f["store_ids"])
promo_clause = promo_sql_clause(f["promo_filter"])

if not f["store_ids"]:
    st.warning("No stores match the current filters.")
    st.stop()

kpis = run_query(
    f"""
    SELECT
        SUM(f.sales) AS total_sales,
        SUM(f.customers) AS total_customers,
        AVG(f.sales) AS avg_daily_sales,
        SUM(f.sales)::NUMERIC / NULLIF(SUM(f.customers), 0) AS sales_per_customer
    FROM fact_sales f
    WHERE f.store_id IN {store_clause}
      AND f.sale_date BETWEEN :start_date AND :end_date
      AND f.is_open = TRUE
      {promo_clause}
    """,
    {"start_date": f["start_date"], "end_date": f["end_date"]},
).iloc[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Revenue", f"€{kpis['total_sales']:,.0f}")
col2.metric("Total Customers", f"{kpis['total_customers']:,.0f}")
col3.metric("Avg Daily Sales / Store-Day", f"€{kpis['avg_daily_sales']:,.0f}")
col4.metric("Sales per Customer", f"€{kpis['sales_per_customer']:,.2f}")

st.subheader("Monthly Revenue Trend")
monthly = run_query(
    f"""
    SELECT DATE_TRUNC('month', f.sale_date)::DATE AS sale_month, SUM(f.sales) AS monthly_sales
    FROM fact_sales f
    WHERE f.store_id IN {store_clause}
      AND f.sale_date BETWEEN :start_date AND :end_date
      AND f.is_open = TRUE
      {promo_clause}
    GROUP BY sale_month
    ORDER BY sale_month
    """,
    {"start_date": f["start_date"], "end_date": f["end_date"]},
)
st.line_chart(monthly.set_index("sale_month")["monthly_sales"])

st.subheader("Top & Bottom 5 Stores by Revenue")
by_store = run_query(
    f"""
    SELECT f.store_id, ds.store_type, ds.assortment, SUM(f.sales) AS total_sales
    FROM fact_sales f
    JOIN dim_store ds ON ds.store_id = f.store_id
    WHERE f.store_id IN {store_clause}
      AND f.sale_date BETWEEN :start_date AND :end_date
      AND f.is_open = TRUE
      {promo_clause}
    GROUP BY f.store_id, ds.store_type, ds.assortment
    ORDER BY total_sales DESC
    """,
    {"start_date": f["start_date"], "end_date": f["end_date"]},
)

col_top, col_bottom = st.columns(2)
col_top.markdown("**Top 5**")
col_top.dataframe(by_store.head(5), hide_index=True)
col_bottom.markdown("**Bottom 5**")
col_bottom.dataframe(by_store.tail(5).sort_values("total_sales"), hide_index=True)
