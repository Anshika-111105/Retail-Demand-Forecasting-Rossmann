from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.db import in_clause, run_query  # noqa: E402
from dashboard.components.filters import promo_sql_clause, render_sidebar_filters  # noqa: E402

st.set_page_config(page_title="Sales Analytics", layout="wide")
st.title("Sales Analytics")
st.caption("Daily sales trend with 7-day and 30-day rolling averages.")

f = render_sidebar_filters()
store_clause = in_clause(f["store_ids"])
promo_clause = promo_sql_clause(f["promo_filter"])

if not f["store_ids"]:
    st.warning("No stores match the current filters.")
    st.stop()

single_store = len(f["store_ids"]) == 1

if single_store:
    st.info(f"Showing store {f['store_ids'][0]} with per-store rolling averages.")
    series = run_query(
        f"""
        SELECT
            f.sale_date,
            f.sales,
            ROUND(AVG(f.sales) OVER (ORDER BY f.sale_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS rolling_avg_7d,
            ROUND(AVG(f.sales) OVER (ORDER BY f.sale_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 2) AS rolling_avg_30d
        FROM fact_sales f
        WHERE f.store_id IN {store_clause}
          AND f.sale_date BETWEEN :start_date AND :end_date
          AND f.is_open = TRUE
          {promo_clause}
        ORDER BY f.sale_date
        """,
        {"start_date": f["start_date"], "end_date": f["end_date"]},
    )
    st.line_chart(series.set_index("sale_date")[["sales", "rolling_avg_7d", "rolling_avg_30d"]])
else:
    st.info(f"{len(f['store_ids'])} stores selected — showing aggregated daily total with rolling averages.")
    daily_total = run_query(
        f"""
        WITH daily AS (
            SELECT f.sale_date, SUM(f.sales) AS sales
            FROM fact_sales f
            WHERE f.store_id IN {store_clause}
              AND f.sale_date BETWEEN :start_date AND :end_date
              AND f.is_open = TRUE
              {promo_clause}
            GROUP BY f.sale_date
        )
        SELECT
            sale_date,
            sales,
            ROUND(AVG(sales) OVER (ORDER BY sale_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS rolling_avg_7d,
            ROUND(AVG(sales) OVER (ORDER BY sale_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 2) AS rolling_avg_30d
        FROM daily
        ORDER BY sale_date
        """,
        {"start_date": f["start_date"], "end_date": f["end_date"]},
    )
    st.line_chart(daily_total.set_index("sale_date")[["sales", "rolling_avg_7d", "rolling_avg_30d"]])
