from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

st.set_page_config(page_title="Inventory Planning Dashboard", layout="wide")
st.title("Inventory Planning Dashboard")
st.caption("Forecast-driven stock levels optimization, safety stock recommendations, and risk assessment.")

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

target_stores = sorted(df_preds["Store"].unique())

# Sidebar filters
st.sidebar.header("Inventory Settings")
selected_model = st.sidebar.selectbox("Select Model for Recommendation", ["LightGBM", "XGBoost", "Prophet"], index=0)
selected_store = st.sidebar.selectbox("Select Store", target_stores, index=0)

# Lead time (days it takes to restock) and Service Level
lead_time_days = st.sidebar.slider("Lead Time (Days to Restock)", min_value=1, max_value=14, value=5)
service_level_z = st.sidebar.selectbox(
    "Service Level Target (Safety Stock)",
    options=[1.28, 1.65, 1.96, 2.33],
    format_func=lambda x: {1.28: "90% (Z=1.28)", 1.65: "95% (Z=1.65)", 1.96: "97.5% (Z=1.96)", 2.33: "99% (Z=2.33)"}[x],
    index=1
)

# -----------------
# 1. Store Inventory Assessment
# -----------------
st.subheader(f"Demand & Reorder Recommendations for Store {selected_store}")

# Historical actual open-days baseline (last 30 open days in train)
store_actuals = df_preds[(df_preds["Store"] == selected_store) & (df_preds["Type"] == "Actuals") & (df_preds["Open"] == 1)].sort_values("Date")
if store_actuals.empty:
    st.error("No historical actuals found for this store.")
    st.stop()

last_30_actuals = store_actuals.tail(30)
baseline_avg_sales = last_30_actuals["Sales"].mean()
baseline_std_sales = last_30_actuals["Sales"].std()

# Forecast open-days in test set
store_test = df_preds[(df_preds["Store"] == selected_store) & (df_preds["Type"] == "Test") & (df_preds["Model"] == selected_model)]
if store_test.empty:
    st.error("No test forecasts found for this store and model.")
    st.stop()

# Total forecast days and open days
total_forecast_days = len(store_test)
open_test_days = store_test[store_test["Open"] == 1]
total_forecast_demand = open_test_days["Sales"].sum()
avg_forecast_sales = open_test_days["Sales"].mean()

# Calculate safety stock and reorder point
# Safety Stock = Z * std_demand * sqrt(lead_time)
safety_stock = service_level_z * baseline_std_sales * np.sqrt(lead_time_days)
# Reorder Point = (avg_forecast_sales * lead_time) + safety_stock
reorder_point = (avg_forecast_sales * lead_time_days) + safety_stock

# Calculate baseline projection for equivalent open days
equivalent_baseline_demand = baseline_avg_sales * len(open_test_days)

# Deviation
demand_deviation = total_forecast_demand - equivalent_baseline_demand
pct_deviation = (demand_deviation / equivalent_baseline_demand) if equivalent_baseline_demand > 0 else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Forecasted Total Demand (6-weeks)", f"€{total_forecast_demand:,.0f}")
col2.metric("Equivalent Baseline Demand", f"€{equivalent_baseline_demand:,.0f}")

# Color color-coding deviation metric
deviation_label = f"€{demand_deviation:+,.0f} ({pct_deviation:+.1%})"
if pct_deviation > 0.15:
    col3.metric("Deviation vs. Baseline", deviation_label, delta_color="inverse")
    st.warning("⚠️ **High Demand Spike (Stockout Risk):** Forecasted demand is significantly higher than historical baseline. Consider pre-positioning inventory.")
elif pct_deviation < -0.15:
    col3.metric("Deviation vs. Baseline", deviation_label)
    st.error("📉 **Low Demand (Overstock Risk):** Forecasted demand is significantly lower than historical baseline. Consider reducing orders to avoid carrying costs.")
else:
    col3.metric("Deviation vs. Baseline", deviation_label, delta_color="normal")
    st.success("✅ **Stable Demand:** Forecasted demand is in-line with the historical baseline.")

col4.metric("Suggested Reorder Point", f"€{reorder_point:,.0f}", help=f"Reorder when stock drops below this value. Includes €{safety_stock:,.0f} safety stock.")

# -----------------
# 2. Cumulative Demand Projection Chart
# -----------------
st.subheader("Cumulative Demand Projection over Forecast Period")

open_test_days = open_test_days.sort_values("Date")
open_test_days["Cumulative Forecast"] = open_test_days["Sales"].cumsum()
open_test_days["Cumulative Baseline"] = [baseline_avg_sales * (i+1) for i in range(len(open_test_days))]

if HAS_PLOTLY:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=open_test_days["Date"],
        y=open_test_days["Cumulative Forecast"],
        mode="lines",
        name=f"Cumulative Forecast ({selected_model})",
        line=dict(color="#2ca02c", width=3)
    ))
    fig.add_trace(go.Scatter(
        x=open_test_days["Date"],
        y=open_test_days["Cumulative Baseline"],
        mode="lines",
        name="Cumulative Baseline (Historical)",
        line=dict(color="#1f77b4", width=2, dash="dash")
    ))
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Cumulative Demand (€)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.01),
        margin=dict(l=40, r=40, t=40, b=40),
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    chart_df = open_test_days.set_index("Date")[["Cumulative Forecast", "Cumulative Baseline"]]
    st.line_chart(chart_df)

# -----------------
# 3. Multi-Store Summary Table
# -----------------
st.subheader("All-Stores Inventory Summary")
st.markdown(f"Consolidated forecast analysis and risk assessment using the selected **{selected_model}** model.")

summary_records = []
for s_id in target_stores:
    s_actuals = df_preds[(df_preds["Store"] == s_id) & (df_preds["Type"] == "Actuals") & (df_preds["Open"] == 1)].sort_values("Date")
    s_test = df_preds[(df_preds["Store"] == s_id) & (df_preds["Type"] == "Test") & (df_preds["Model"] == selected_model)]
    
    if not s_actuals.empty and not s_test.empty:
        s_base_avg = s_actuals.tail(30)["Sales"].mean()
        s_base_std = s_actuals.tail(30)["Sales"].std()
        
        s_test_open = s_test[s_test["Open"] == 1]
        s_test_demand = s_test_open["Sales"].sum()
        s_test_avg = s_test_open["Sales"].mean()
        
        s_base_equiv = s_base_avg * len(s_test_open)
        s_dev = s_test_demand - s_base_equiv
        s_pct_dev = (s_dev / s_base_equiv) if s_base_equiv > 0 else 0.0
        
        # Risk assessment
        if s_pct_dev > 0.15:
            risk = "⚠️ Stockout Risk"
        elif s_pct_dev < -0.15:
            risk = "📉 Overstock Risk"
        else:
            risk = "✅ Normal"
            
        s_safety = service_level_z * s_base_std * np.sqrt(lead_time_days)
        s_reorder = (s_test_avg * lead_time_days) + s_safety
        
        summary_records.append({
            "Store": s_id,
            "Baseline Demand (€)": round(s_base_equiv, 2),
            "Forecasted Demand (€)": round(s_test_demand, 2),
            "Deviation (€)": round(s_dev, 2),
            "Dev (%)": f"{s_pct_dev:+.1%}",
            "Risk Assessment": risk,
            "Safety Stock (€)": round(s_safety, 2),
            "Reorder Point (€)": round(s_reorder, 2)
        })

summary_df = pd.DataFrame(summary_records)
st.dataframe(summary_df, use_container_width=True, hide_index=True)
