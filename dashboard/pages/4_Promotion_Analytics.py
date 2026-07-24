from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.db import in_clause, run_query  # noqa: E402
from dashboard.components.filters import render_sidebar_filters  # noqa: E402

st.set_page_config(page_title="Promotion Analytics", layout="wide")
st.title("Promotion Analytics")
st.caption("Promo vs. non-promo sales uplift per store, controlling for day-of-week mix.")

f = render_sidebar_filters()
store_clause = in_clause(f["store_ids"])

if not f["store_ids"]:
    st.warning("No stores match the current filters.")
    st.stop()

if f["promo_filter"] != "All":
    st.info("The global Promo status filter is ignored on this page — it compares promo vs. non-promo directly.")

uplift = run_query(
    f"""
    WITH by_promo_dow AS (
        SELECT f.store_id, f.day_of_week, f.is_promo, AVG(f.sales) AS avg_sales
        FROM fact_sales f
        WHERE f.store_id IN {store_clause}
          AND f.sale_date BETWEEN :start_date AND :end_date
          AND f.is_open = TRUE
        GROUP BY f.store_id, f.day_of_week, f.is_promo
    ),
    paired AS (
        SELECT promo.store_id, promo.day_of_week,
               promo.avg_sales AS promo_avg_sales, base.avg_sales AS non_promo_avg_sales
        FROM by_promo_dow promo
        JOIN by_promo_dow base
          ON base.store_id = promo.store_id AND base.day_of_week = promo.day_of_week AND base.is_promo = FALSE
        WHERE promo.is_promo = TRUE
    )
    SELECT
        store_id,
        ROUND(AVG(promo_avg_sales), 2) AS avg_promo_sales,
        ROUND(AVG(non_promo_avg_sales), 2) AS avg_non_promo_sales,
        ROUND(AVG(promo_avg_sales) - AVG(non_promo_avg_sales), 2) AS uplift_absolute,
        ROUND(100.0 * (AVG(promo_avg_sales) - AVG(non_promo_avg_sales)) / NULLIF(AVG(non_promo_avg_sales), 0), 1) AS uplift_pct
    FROM paired
    GROUP BY store_id
    ORDER BY uplift_pct DESC
    """,
    {"start_date": f["start_date"], "end_date": f["end_date"]},
)

col1, col2 = st.columns(2)
col1.metric("Median Promo Uplift", f"{uplift['uplift_pct'].median():.1f}%")
col2.metric("Stores with Positive Uplift", f"{(uplift['uplift_pct'] > 0).sum()} / {len(uplift)}")

st.subheader("Top 20 Most Promo-Responsive Stores")
st.bar_chart(uplift.head(20).set_index("store_id")["uplift_pct"])

st.subheader("Full Results")
st.dataframe(uplift, hide_index=True, use_container_width=True)
