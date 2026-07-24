from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Inventory Planning Dashboard", layout="wide")
st.title("Inventory Planning Dashboard")

st.info(
    "Not available yet — this page will compare each store's forecasted demand against its "
    "recent rolling-average baseline to flag stockout risk (forecast well above baseline, e.g. "
    "ahead of a promo/holiday) or overstock risk (forecast well below a declining baseline), "
    "with a suggested reorder-adjustment direction. It depends on the Forecast Dashboard's "
    "output, which depends on trained models from Phase 7, which hasn't been built yet.\n\n"
    "See [docs/Phase7_Machine_Learning_Strategy.md](../../docs/Phase7_Machine_Learning_Strategy.md) "
    "for the modeling plan."
)
