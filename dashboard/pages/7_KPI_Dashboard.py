from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.db import in_clause, run_query  # noqa: E402
from dashboard.components.filters import promo_sql_clause, render_sidebar_filters  # noqa: E402

st.set_page_config(page_title="KPI Dashboard", layout="wide")
st.title("KPI Dashboard")
st.caption("Consolidated Sales, Store/Promotion, and Traffic KPIs (see docs/Phase1_Business_Understanding.md Section 9).")

f = render_sidebar_filters()
store_clause = in_clause(f["store_ids"])
promo_clause = promo_sql_clause(f["promo_filter"])

if not f["store_ids"]:
    st.warning("No stores match the current filters.")
    st.stop()

st.subheader("Sales KPIs")
sales_kpi = run_query(
    f"""
    SELECT
        SUM(f.sales) AS total_revenue,
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

monthly = run_query(
    f"""
    SELECT DATE_TRUNC('month', f.sale_date)::DATE AS sale_month, SUM(f.sales) AS monthly_sales
    FROM fact_sales f
    WHERE f.store_id IN {store_clause}
      AND f.sale_date BETWEEN :start_date AND :end_date
      AND f.is_open = TRUE
      {promo_clause}
    GROUP BY sale_month ORDER BY sale_month
    """,
    {"start_date": f["start_date"], "end_date": f["end_date"]},
)
mom_growth = None
if len(monthly) >= 2:
    mom_growth = (monthly["monthly_sales"].iloc[-1] / monthly["monthly_sales"].iloc[-2] - 1) * 100

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue", f"€{sales_kpi['total_revenue']:,.0f}")
c2.metric("Avg Daily Sales", f"€{sales_kpi['avg_daily_sales']:,.0f}")
c3.metric("Sales per Customer", f"€{sales_kpi['sales_per_customer']:,.2f}")
c4.metric("Latest MoM Growth", f"{mom_growth:+.1f}%" if mom_growth is not None else "n/a")

st.subheader("Store / Promotion KPIs")
promo_kpi = run_query(
    f"""
    WITH by_promo_dow AS (
        SELECT f.store_id, f.day_of_week, f.is_promo, AVG(f.sales) AS avg_sales
        FROM fact_sales f
        WHERE f.store_id IN {store_clause}
          AND f.sale_date BETWEEN :start_date AND :end_date AND f.is_open = TRUE
        GROUP BY f.store_id, f.day_of_week, f.is_promo
    ),
    paired AS (
        SELECT promo.store_id,
               promo.avg_sales AS promo_avg_sales, base.avg_sales AS non_promo_avg_sales
        FROM by_promo_dow promo
        JOIN by_promo_dow base ON base.store_id = promo.store_id AND base.day_of_week = promo.day_of_week AND base.is_promo = FALSE
        WHERE promo.is_promo = TRUE
    )
    SELECT AVG(100.0 * (promo_avg_sales - non_promo_avg_sales) / NULLIF(non_promo_avg_sales, 0)) AS avg_uplift_pct
    FROM paired
    """,
    {"start_date": f["start_date"], "end_date": f["end_date"]},
).iloc[0]

top_store = run_query(
    f"""
    SELECT f.store_id, SUM(f.sales) AS total_sales
    FROM fact_sales f
    WHERE f.store_id IN {store_clause}
      AND f.sale_date BETWEEN :start_date AND :end_date AND f.is_open = TRUE {promo_clause}
    GROUP BY f.store_id ORDER BY total_sales DESC LIMIT 1
    """,
    {"start_date": f["start_date"], "end_date": f["end_date"]},
).iloc[0]

c5, c6 = st.columns(2)
c5.metric("Avg Promotion Uplift", f"{promo_kpi['avg_uplift_pct']:+.1f}%")
c6.metric("Top Store", f"#{int(top_store['store_id'])} (€{top_store['total_sales']:,.0f})")

st.subheader("Monthly Revenue Trend")
st.line_chart(monthly.set_index("sale_month")["monthly_sales"])
