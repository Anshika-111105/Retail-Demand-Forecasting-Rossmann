from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from dashboard.components.db import run_query

MIN_DATE = dt.date(2013, 1, 1)
MAX_DATE = dt.date(2015, 7, 31)


@st.cache_data(ttl=3600)
def _load_store_dimension() -> pd.DataFrame:
    return run_query("SELECT store_id, store_type, assortment FROM dim_store ORDER BY store_id")


def render_sidebar_filters() -> dict:
    """Render the global filter widgets shared by every page and return the selection."""
    stores = _load_store_dimension()

    st.sidebar.header("Filters")

    store_types = st.sidebar.multiselect(
        "Store Type",
        sorted(stores["store_type"].unique()),
        default=sorted(stores["store_type"].unique()),
    )
    assortments = st.sidebar.multiselect(
        "Assortment",
        sorted(stores["assortment"].unique()),
        default=sorted(stores["assortment"].unique()),
    )

    eligible = stores[stores["store_type"].isin(store_types) & stores["assortment"].isin(assortments)]
    eligible_store_ids = eligible["store_id"].tolist()

    store_selection = st.sidebar.multiselect(
        "Store (empty = all matching Type/Assortment)", eligible_store_ids, default=[]
    )
    selected_store_ids = store_selection or eligible_store_ids

    date_range = st.sidebar.date_input(
        "Date range", value=(MIN_DATE, MAX_DATE), min_value=MIN_DATE, max_value=MAX_DATE
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = MIN_DATE, MAX_DATE

    promo_filter = st.sidebar.radio("Promo status", ["All", "Promo days only", "Non-promo days only"])

    st.sidebar.caption(f"{len(selected_store_ids)} store(s) selected")

    return {
        "store_ids": selected_store_ids,
        "start_date": start_date,
        "end_date": end_date,
        "promo_filter": promo_filter,
    }


def promo_sql_clause(promo_filter: str, alias: str = "f") -> str:
    if promo_filter == "Promo days only":
        return f"AND {alias}.is_promo = TRUE"
    if promo_filter == "Non-promo days only":
        return f"AND {alias}.is_promo = FALSE"
    return ""
