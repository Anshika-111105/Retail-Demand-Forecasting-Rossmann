from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def _compute_lag_rolling_for_series(full_idx: pd.DatetimeIndex, masked_sales: np.ndarray) -> pd.DataFrame:
    """Lag/rolling/expanding features for one store's daily (gap-filled) sales series."""
    s = pd.Series(masked_sales, index=full_idx)
    prior = s.shift(1)

    feats = pd.DataFrame(index=full_idx)
    feats["sales_lag_7"] = s.shift(7)
    feats["sales_lag_14"] = s.shift(14)
    feats["sales_lag_28"] = s.shift(28)
    feats["sales_rolling_mean_7"] = prior.rolling(7, min_periods=1).mean()
    feats["sales_rolling_mean_30"] = prior.rolling(30, min_periods=1).mean()
    feats["sales_rolling_std_7"] = prior.rolling(7, min_periods=2).std()
    feats["sales_rolling_std_30"] = prior.rolling(30, min_periods=2).std()
    feats["sales_expanding_mean"] = prior.expanding(min_periods=1).mean()
    feats["sales_trend_7_30"] = (
        feats["sales_rolling_mean_7"] / feats["sales_rolling_mean_30"].replace(0, np.nan)
    )
    return feats.astype("float32")


def add_lag_rolling_features(
    train_df: pd.DataFrame,
    test_df: Optional[pd.DataFrame] = None,
    store_col: str = "Store",
    date_col: str = "Date",
    sales_col: str = "Sales",
    open_col: str = "Open",
) -> tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    """Attach lag/rolling/expanding sales-momentum features to train (and optionally test)."""
    combined = train_df[[store_col, date_col, sales_col, open_col]].copy()
    if test_df is not None:
        test_part = test_df[[store_col, date_col, open_col]].copy()
        test_part[sales_col] = np.nan
        combined = pd.concat([combined, test_part], ignore_index=True)

    combined = combined.sort_values([store_col, date_col]).reset_index(drop=True)
    combined["_masked_sales"] = combined[sales_col].where(combined[open_col] == 1)

    feature_rows = []
    for store_id, grp in combined.groupby(store_col, sort=False):
        full_idx = pd.date_range(grp[date_col].min(), grp[date_col].max(), freq="D")
        series = grp.set_index(date_col)["_masked_sales"].reindex(full_idx).to_numpy()
        feats = _compute_lag_rolling_for_series(full_idx, series)
        feats = feats.loc[grp[date_col].to_numpy()].reset_index(drop=True)
        feats.insert(0, date_col, grp[date_col].to_numpy())
        feats.insert(0, store_col, store_id)
        feature_rows.append(feats)

    feature_table = pd.concat(feature_rows, ignore_index=True)

    train_out = train_df.merge(feature_table, on=[store_col, date_col], how="left", validate="one_to_one")
    if test_df is None:
        return train_out, None

    test_out = test_df.merge(feature_table, on=[store_col, date_col], how="left", validate="one_to_one")
    return train_out, test_out


def build_customer_traffic_lookup(
    train_df: pd.DataFrame,
    store_col: str = "Store",
    dow_col: str = "DayOfWeek",
    customers_col: str = "Customers",
    open_col: str = "Open",
) -> pd.DataFrame:
    """Historical average customer traffic per (store, day-of-week), from training data only.

    ``Customers`` does not exist in ``test.csv``, so it can never be a raw per-row
    feature. This pre-aggregated lookup is the sanctioned way to carry a foot-traffic
    signal into both train and test without leaking the unavailable column.
    """
    return (
        train_df.loc[train_df[open_col] == 1]
        .groupby([store_col, dow_col])[customers_col]
        .mean()
        .rename("avg_customers_store_dow")
        .reset_index()
    )


def apply_customer_traffic_lookup(
    df: pd.DataFrame,
    lookup: pd.DataFrame,
    store_col: str = "Store",
    dow_col: str = "DayOfWeek",
) -> pd.DataFrame:
    """Join the training-derived customer-traffic lookup onto any (train or test) frame."""
    return df.merge(lookup, on=[store_col, dow_col], how="left")
