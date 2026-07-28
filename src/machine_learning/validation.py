from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def time_series_cv_splits(df: pd.DataFrame, n_folds: int = 3, val_window_days: int = 42) -> list[tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp, pd.Timestamp]]:
    """Generate train/validation splits based on rolling cutoff dates.
    
    val_window_days defaults to 42 days (~6 weeks) to match the Kaggle test horizon.
    """
    df_sorted = df.sort_values("Date").reset_index(drop=True)
    max_date = df_sorted["Date"].max()
    
    splits = []
    for fold in range(n_folds):
        # Determine the start of the validation window for this fold
        # Fold 0 is the oldest (furthest back), Fold 2 is the newest
        offset_days = (n_folds - fold) * val_window_days
        val_start = max_date - pd.Timedelta(days=offset_days)
        val_end = val_start + pd.Timedelta(days=val_window_days - 1)
        
        train_df = df_sorted[df_sorted["Date"] < val_start].copy()
        val_df = df_sorted[(df_sorted["Date"] >= val_start) & (df_sorted["Date"] <= val_end)].copy()
        
        splits.append((train_df, val_df, val_start, val_end))
        
    return splits


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Compute MAE, RMSE, MAPE, and R2 on a set of true vs predicted sales."""
    # Avoid divide-by-zero for MAPE
    non_zero_mask = y_true > 0
    if not np.any(non_zero_mask):
        mape = np.nan
    else:
        mape = np.mean(np.abs((y_true[non_zero_mask] - y_pred[non_zero_mask]) / y_true[non_zero_mask])) * 100
        
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    
    return {
        "MAE": float(mae),
        "RMSE": float(rmse),
        "MAPE": float(mape),
        "R2": float(r2)
    }


def evaluate_predictions(df: pd.DataFrame, y_pred: np.ndarray) -> dict[str, float]:
    """Evaluate predictions on open-store days only, as closed-store days are structural zeros."""
    open_mask = (df["Open"] == 1).values
    if not np.any(open_mask):
        return {"MAE": np.nan, "RMSE": np.nan, "MAPE": np.nan, "R2": np.nan}
        
    y_true = df["Sales"].values[open_mask]
    y_pred_open = y_pred[open_mask]
    
    return calculate_metrics(y_true, y_pred_open)
