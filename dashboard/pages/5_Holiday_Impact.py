from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.db import in_clause, run_query  # noqa: E402
from dashboard.components.filters import render_sidebar_filters  # noqa: E402

st.set_page_config(page_title="Holiday Impact", layout="wide")
st.title("Holiday Impact")
st.caption("State-holiday and school-holiday sales vs. an ordinary-day baseline.")

f = render_sidebar_filters()
store_clause = in_clause(f["store_ids"])

if not f["store_ids"]:
    st.warning("No stores match the current filters.")
    st.stop()

holiday = run_query(
    f"""
    WITH holiday_avg AS (
        SELECT
            CASE state_holiday WHEN 'a' THEN 'public_holiday' WHEN 'b' THEN 'easter_holiday'
                 WHEN 'c' THEN 'christmas_holiday' ELSE 'none' END AS holiday_type,
            AVG(sales) AS avg_sales, COUNT(*) AS n_days
        FROM fact_sales f
        WHERE f.store_id IN {store_clause}
          AND f.sale_date BETWEEN :start_date AND :end_date
          AND f.is_open = TRUE
        GROUP BY holiday_type
    ),
    baseline AS (SELECT avg_sales AS baseline_avg_sales FROM holiday_avg WHERE holiday_type = 'none'),
    school_holiday_avg AS (
        SELECT is_school_holiday, AVG(sales) AS avg_sales, COUNT(*) AS n_days
        FROM fact_sales f
        WHERE f.store_id IN {store_clause}
          AND f.sale_date BETWEEN :start_date AND :end_date
          AND f.is_open = TRUE
        GROUP BY is_school_holiday
    )
    SELECT h.holiday_type, h.n_days, ROUND(h.avg_sales, 2) AS avg_sales,
           ROUND(100.0 * (h.avg_sales - b.baseline_avg_sales) / b.baseline_avg_sales, 1) AS pct_vs_normal_day
    FROM holiday_avg h CROSS JOIN baseline b
    UNION ALL
    SELECT CASE WHEN is_school_holiday THEN 'school_holiday' ELSE 'no_school_holiday' END, n_days,
           ROUND(avg_sales, 2),
           ROUND(100.0 * (avg_sales - (SELECT baseline_avg_sales FROM baseline)) / (SELECT baseline_avg_sales FROM baseline), 1)
    FROM school_holiday_avg
    ORDER BY pct_vs_normal_day DESC
    """,
    {"start_date": f["start_date"], "end_date": f["end_date"]},
)

st.bar_chart(holiday.set_index("holiday_type")["pct_vs_normal_day"])
st.dataframe(holiday, hide_index=True, use_container_width=True)
