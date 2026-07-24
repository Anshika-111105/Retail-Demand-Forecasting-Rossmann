from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.db import in_clause, run_query  # noqa: E402
from dashboard.components.filters import promo_sql_clause, render_sidebar_filters  # noqa: E402

st.set_page_config(page_title="Store Performance", layout="wide")
st.title("Store Performance")
st.caption("Store-level ranking by revenue, average daily sales, and sales-per-customer.")

f = render_sidebar_filters()
store_clause = in_clause(f["store_ids"])
promo_clause = promo_sql_clause(f["promo_filter"])

if not f["store_ids"]:
    st.warning("No stores match the current filters.")
    st.stop()

ranking = run_query(
    f"""
    WITH store_daily AS (
        SELECT
            f.store_id,
            SUM(f.sales) AS total_sales,
            SUM(f.customers) AS total_customers,
            COUNT(*) FILTER (WHERE f.is_open) AS days_open,
            AVG(f.sales) FILTER (WHERE f.is_open) AS avg_daily_sales
        FROM fact_sales f
        WHERE f.store_id IN {store_clause}
          AND f.sale_date BETWEEN :start_date AND :end_date
          {promo_clause}
        GROUP BY f.store_id
    )
    SELECT
        sd.store_id,
        ds.store_type,
        ds.assortment,
        sd.days_open,
        sd.total_sales,
        ROUND(sd.avg_daily_sales, 2) AS avg_daily_sales,
        ROUND(sd.total_sales::NUMERIC / NULLIF(sd.total_customers, 0), 2) AS sales_per_customer,
        RANK() OVER (ORDER BY sd.total_sales DESC) AS revenue_rank,
        ROUND((PERCENT_RANK() OVER (ORDER BY sd.total_sales) * 100)::NUMERIC, 1) AS revenue_percentile
    FROM store_daily sd
    JOIN dim_store ds ON ds.store_id = sd.store_id
    ORDER BY sd.total_sales DESC
    """,
    {"start_date": f["start_date"], "end_date": f["end_date"]},
)

st.subheader(f"Top 20 of {len(ranking)} Stores by Revenue")
st.bar_chart(ranking.head(20).set_index("store_id")["total_sales"])

st.subheader("Full Ranking")
st.dataframe(ranking, hide_index=True, use_container_width=True)
