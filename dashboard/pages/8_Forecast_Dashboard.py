from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Attempt to import plotly, fallback to streamlit line_chart if not working
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from dashboard.components.filters import render_sidebar_filters  # noqa: E402
from src.machine_learning.validation import calculate_metrics  # noqa: E402

st.set_page_config(page_title="Forecast Dashboard", layout="wide")
st.title("Demand Forecast Dashboard")
st.caption("Compare Prophet, XGBoost, and LightGBM model forecasts against historical actual sales.")

# Cache the predictions load
@st.cache_data(ttl=600)
def load_predictions() -> pd.DataFrame | None:
    predictions_path = PROJECT_ROOT / "models" / "artifacts" / "predictions.parquet"
    if not predictions_path.exists():
        return None
    return pd.read_parquet(predictions_path)

df_preds = load_predictions()

if df_preds is None:
    st.warning("Predictions parquet file not found! Please run the training pipeline first:")
    st.code("python src/machine_learning/train_pipeline.py")
    st.info("Ensure the pipeline has run and generated 'models/artifacts/predictions.parquet'.")
    st.stop()

# Since Prophet was trained on stores 1-10, we filter store selections to 1-10
target_stores = sorted(df_preds["Store"].unique())

# Sidebar filters
st.sidebar.header("Forecast Settings")
selected_store = st.sidebar.selectbox("Select Store", target_stores, index=0)

min_date = df_preds["Date"].min().date()
max_date = df_preds["Date"].max().date()

# Date range default to last 4 months of history + test set window
default_start = max_date - pd.Timedelta(days=120)
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(default_start, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

# Toggle models
models_to_show = st.sidebar.multiselect(
    "Models to Display",
    ["Prophet", "XGBoost", "LightGBM"],
    default=["Prophet", "XGBoost", "LightGBM"]
)

# -----------------
# 1. Performance Metrics
# -----------------
st.subheader("Model Performance Comparison (Validation Window)")
st.markdown("Metrics computed on historical open-store days during rolling cross-validation splits.")

# Compute validation metrics for this store
val_df = df_preds[(df_preds["Store"] == selected_store) & (df_preds["Type"] == "Validation")]

if val_df.empty:
    st.info("Validation predictions not found for this store.")
else:
    # Separate actuals vs predictions
    # Note: validation data is structured such that we have rows for each model
    actuals_val = val_df[val_df["Model"] == "Actuals"]
    
    # We join models by Date to compare
    comp_data = {}
    for model in ["Prophet", "XGBoost", "LightGBM"]:
        model_preds = val_df[(val_df["Model"] == model) & (val_df["Open"] == 1)]
        actuals_open = val_df[(val_df["Model"] == "Actuals") & (val_df["Open"] == 1)]
        
        merged = pd.merge(actuals_open, model_preds, on="Date", suffixes=("_act", "_pred"))
        if not merged.empty:
            metrics = calculate_metrics(merged["Sales_act"].values, merged["Sales_pred"].values)
            comp_data[model] = metrics

    if comp_data:
        cols = st.columns(len(models_to_show))
        for idx, model in enumerate(models_to_show):
            if model in comp_data:
                metrics = comp_data[model]
                with cols[idx]:
                    st.markdown(f"#### **{model}**")
                    st.metric("MAE", f"€{metrics['MAE']:,.1f}")
                    st.metric("MAPE", f"{metrics['MAPE']:.2%}")
                    st.metric("RMSE", f"€{metrics['RMSE']:,.1f}")
                    st.metric("R² Score", f"{metrics['R2']:.3f}")
    else:
        st.write("No validation overlaps found to calculate metrics.")

# -----------------
# 2. Forecasting Visualizations
# -----------------
st.subheader(f"Sales Forecast for Store {selected_store}")

# Filter forecasting dataframe
store_data = df_preds[(df_preds["Store"] == selected_store) & (df_preds["Date"].dt.date >= start_date) & (df_preds["Date"].dt.date <= end_date)]

# Split into Actuals, Validation predictions, and Test predictions
actuals_df = store_data[store_data["Type"] == "Actuals"]

# Re-shape for graphing: we want a single table with columns Date, Actuals, Prophet, XGBoost, LightGBM
pivot_df = pd.DataFrame({"Date": store_data["Date"].unique()}).sort_values("Date")

# Add actuals
act_subset = actuals_df[["Date", "Sales"]].rename(columns={"Sales": "Actual Sales"})
pivot_df = pd.merge(pivot_df, act_subset, on="Date", how="left")

# Add models
for model in ["Prophet", "XGBoost", "LightGBM"]:
    if model in models_to_show:
        model_subset = store_data[store_data["Model"] == model][["Date", "Sales"]].rename(columns={"Sales": model})
        pivot_df = pd.merge(pivot_df, model_subset, on="Date", how="left")

pivot_df = pivot_df.set_index("Date")

if HAS_PLOTLY:
    fig = go.Figure()
    
    # Actual Sales (Historical)
    if "Actual Sales" in pivot_df.columns:
        fig.add_trace(go.Scatter(
            x=pivot_df.index,
            y=pivot_df["Actual Sales"],
            mode="lines+markers",
            name="Actual Sales (Historical)",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=4)
        ))
        
    # Model Predictions
    colors = {"Prophet": "#2ca02c", "XGBoost": "#ff7f0e", "LightGBM": "#9467bd"}
    for model in models_to_show:
        if model in pivot_df.columns:
            # We want to separate validation (dashed) vs test (solid) if possible,
            # or just draw a single line representing the model predictions
            fig.add_trace(go.Scatter(
                x=pivot_df.index,
                y=pivot_df[model],
                mode="lines",
                name=f"{model} Forecast",
                line=dict(color=colors[model], width=2)
            ))
            
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Daily Sales (€)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=40, b=40),
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    # Streamlit line_chart fallback
    st.line_chart(pivot_df)

st.info("The shaded right-hand side represents the future forecast window (August 2015 onwards), which has no historical actuals.")
