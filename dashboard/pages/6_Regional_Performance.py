from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.db import in_clause, run_query  # noqa: E402
from dashboard.components.filters import promo_sql_clause, render_sidebar_filters  # noqa: E402

st.set_page_config(page_title="Regional Performance", layout="wide")
st.title("Regional Performance")
st.caption(
    "Rossmann publishes no geographic region field, so StoreType/Assortment segment "
    "stands in as the regional/format-level comparison (see docs/Phase6_Dashboard_Design.md)."
)

f = render_sidebar_filters()
store_clause = in_clause(f["store_ids"])
promo_clause = promo_sql_clause(f["promo_filter"])

if not f["store_ids"]:
    st.warning("No stores match the current filters.")
    st.stop()

segment_totals = run_query(
    f"""
    SELECT ds.store_type, ds.assortment, SUM(f.sales) AS total_sales, COUNT(DISTINCT f.store_id) AS n_stores
    FROM fact_sales f
    JOIN dim_store ds ON ds.store_id = f.store_id
    WHERE f.store_id IN {store_clause}
      AND f.sale_date BETWEEN :start_date AND :end_date
      AND f.is_open = TRUE
      {promo_clause}
    GROUP BY ds.store_type, ds.assortment
    ORDER BY total_sales DESC
    """,
    {"start_date": f["start_date"], "end_date": f["end_date"]},
)
segment_totals["segment"] = segment_totals["store_type"] + " / " + segment_totals["assortment"]

st.subheader("Total Revenue by Store Type / Assortment Segment")
st.bar_chart(segment_totals.set_index("segment")["total_sales"])

st.subheader("Top 3 Stores Within Each Segment")
top3 = run_query(
    f"""
    WITH store_totals AS (
        SELECT f.store_id, ds.store_type, ds.assortment, SUM(f.sales) AS total_sales
        FROM fact_sales f
        JOIN dim_store ds ON ds.store_id = f.store_id
        WHERE f.store_id IN {store_clause}
          AND f.sale_date BETWEEN :start_date AND :end_date
          AND f.is_open = TRUE
          {promo_clause}
        GROUP BY f.store_id, ds.store_type, ds.assortment
    ),
    ranked AS (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY store_type, assortment ORDER BY total_sales DESC) AS rank_in_segment
        FROM store_totals
    )
    SELECT store_id, store_type, assortment, total_sales, rank_in_segment
    FROM ranked WHERE rank_in_segment <= 3
    ORDER BY store_type, assortment, rank_in_segment
    """,
    {"start_date": f["start_date"], "end_date": f["end_date"]},
)
st.dataframe(top3, hide_index=True, use_container_width=True)
