from __future__ import annotations

import logging
import warnings
import numpy as np
import pandas as pd
from typing import Dict, List, Union

# Suppress Prophet's verbose log output
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=FutureWarning)

from prophet import Prophet
import xgboost as xgb
import lightgbm as lgb

logger = logging.getLogger(__name__)


def build_prophet_holidays(df: pd.DataFrame) -> pd.DataFrame:
    """Build a holiday DataFrame for Prophet using StateHoliday codes."""
    if "StateHoliday" not in df.columns:
        return pd.DataFrame(columns=["holiday", "ds"])

    # Extract non-zero state holidays
    holiday_rows = df[df["StateHoliday"].astype(str) != "0"]
    if holiday_rows.empty:
        return pd.DataFrame(columns=["holiday", "ds"])

    holidays_df = pd.DataFrame({
        "ds": holiday_rows["Date"],
        "holiday": holiday_rows["StateHoliday"].astype(str)
    })
    
    # Map Rossmann codes to readable holiday names
    holiday_names = {"a": "public_holiday", "b": "easter", "c": "christmas"}
    holidays_df["holiday"] = holidays_df["holiday"].map(holiday_names).fillna("state_holiday")
    
    # Clean duplicates
    return holidays_df.drop_duplicates(subset=["ds"])


class RossmannProphetWrapper:
    """Wrapper to fit and predict using per-store Prophet models."""

    def __init__(self, stores_to_train: List[int] | None = None):
        self.stores_to_train = stores_to_train
        self.models: Dict[int, Prophet] = {}

    def fit(self, df: pd.DataFrame) -> RossmannProphetWrapper:
        """Fit a separate Prophet model for each store in the dataset."""
        df_clean = df[df["Open"] == 1].copy()
        unique_stores = df_clean["Store"].unique()
        
        stores = unique_stores if self.stores_to_train is None else [s for s in self.stores_to_train if s in unique_stores]
        
        logger.info(f"Training Prophet models for {len(stores)} stores...")
        
        for store_id in stores:
            store_data = df_clean[df_clean["Store"] == store_id]
            
            # Prepare prophet input
            prophet_df = pd.DataFrame({
                "ds": store_data["Date"],
                "y": store_data["Sales"],
                "Promo": store_data["Promo"],
                "SchoolHoliday": store_data["SchoolHoliday"]
            })
            
            holidays_df = build_prophet_holidays(store_data)
            
            # Initialize and configure Prophet
            # weekly_seasonality and yearly_seasonality are crucial for Rossmann
            model = Prophet(
                holidays=holidays_df,
                weekly_seasonality=True,
                yearly_seasonality=True,
                daily_seasonality=False
            )
            model.add_regressor("Promo")
            model.add_regressor("SchoolHoliday")
            
            # Fit model
            model.fit(prophet_df)
            self.models[store_id] = model
            
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Generate predictions. Closed-store days (Open == 0) are forced to 0."""
        df_reset = df.reset_index(drop=True)
        predictions = np.zeros(len(df_reset))
        
        # We group by Store and make batch predictions per store
        for store_id, group in df_reset.groupby("Store"):
            indices = group.index
            
            # Days when store is closed are 0
            open_mask = (group["Open"] == 1).values
            if not np.any(open_mask):
                continue
                
            if store_id not in self.models:
                # If no model is trained for this store, predict using simple average fallback
                predictions[indices] = 0.0
                continue
                
            # Filter only open days for Prophet prediction
            open_group = group.iloc[open_mask]
            
            prophet_df = pd.DataFrame({
                "ds": open_group["Date"],
                "Promo": open_group["Promo"],
                "SchoolHoliday": open_group["SchoolHoliday"]
            })
            
            model = self.models[store_id]
            forecast = model.predict(prophet_df)
            
            # Set predictions, clip at 0 to avoid negative values
            preds = np.clip(forecast["yhat"].values, 0, None)
            
            # Store back in predictions array at correct indices
            open_indices = indices[open_mask]
            predictions[open_indices] = preds
            
        return predictions


class RossmannTreeWrapper:
    """Wrapper to fit and predict using a global XGBoost or LightGBM model."""

    def __init__(self, model_type: str = "lightgbm", params: dict | None = None):
        self.model_type = model_type.lower()
        self.params = params or {}
        self.model = None
        self.feature_cols: List[str] = []
        self.cat_cols: List[str] = ["Store", "DayOfWeek", "StoreType", "Assortment", "StateHoliday", "state_holiday_type"]

    def _prepare_features(self, df: pd.DataFrame, is_training: bool = True) -> tuple[pd.DataFrame, pd.Series | None]:
        """Separate target, convert categoricals, and drop non-feature columns."""
        df_copy = df.copy()
        
        # Set categorical types
        for col in self.cat_cols:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].astype("category")

        # Determine feature columns
        cols_to_drop = ["Date", "Sales", "Customers"]
        feature_cols = [c for c in df_copy.columns if c not in cols_to_drop]
        
        X = df_copy[feature_cols]
        y = df_copy["Sales"] if is_training and "Sales" in df_copy.columns else None
        
        if is_training:
            self.feature_cols = feature_cols
            
        return X[self.feature_cols], y

    def fit(self, df: pd.DataFrame) -> RossmannTreeWrapper:
        """Fit a single global model across all stores. Exclude closed days."""
        # Only learn from open days
        df_open = df[df["Open"] == 1].copy()
        X, y = self._prepare_features(df_open, is_training=True)
        
        logger.info(f"Training global {self.model_type} model on {X.shape[0]} rows with {X.shape[1]} features...")
        
        if self.model_type == "lightgbm":
            # Native categorical support in LightGBM
            default_params = {
                "n_estimators": 100,
                "learning_rate": 0.1,
                "max_depth": 8,
                "num_leaves": 63,
                "random_state": 42,
                "n_jobs": -1,
                "verbose": -1
            }
            default_params.update(self.params)
            self.model = lgb.LGBMRegressor(**default_params)
            self.model.fit(X, y)
            
        elif self.model_type == "xgboost":
            # Native categorical support in XGBoost
            default_params = {
                "n_estimators": 100,
                "learning_rate": 0.1,
                "max_depth": 6,
                "random_state": 42,
                "enable_categorical": True,
                "n_jobs": -1
            }
            default_params.update(self.params)
            self.model = xgb.XGBRegressor(**default_params)
            self.model.fit(X, y)
        else:
            raise ValueError(f"Unknown model_type: {self.model_type}")
            
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict sales. Force closed days (Open == 0) to 0."""
        predictions = np.zeros(len(df))
        
        open_mask = (df["Open"] == 1).values
        if not np.any(open_mask):
            return predictions
            
        df_open = df.iloc[open_mask].copy()
        X, _ = self._prepare_features(df_open, is_training=False)
        
        # Predict
        preds = self.model.predict(X)
        
        # Post-process: clip negative values to 0
        preds = np.clip(preds, 0, None)
        
        # Store predictions for open days
        predictions[open_mask] = preds
        return predictions
