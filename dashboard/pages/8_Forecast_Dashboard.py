from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Forecast Dashboard", layout="wide")
st.title("Forecast Dashboard")

st.info(
    "Not available yet — this page will plot per-store Prophet / XGBoost / LightGBM forecasts "
    "against recent actuals, with confidence bands and MAE/RMSE/MAPE model-comparison metrics. "
    "It depends on trained models from Phase 7, which hasn't been built yet.\n\n"
    "See [docs/Phase7_Machine_Learning_Strategy.md](../../docs/Phase7_Machine_Learning_Strategy.md) "
    "for the modeling plan."
)
