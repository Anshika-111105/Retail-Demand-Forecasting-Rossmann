from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from datetime import datetime

from src.machine_learning.models import build_prophet_holidays, RossmannProphetWrapper, RossmannTreeWrapper
from src.machine_learning.validation import time_series_cv_splits, calculate_metrics, evaluate_predictions


def _toy_data(n_days=60, stores=[1, 2]):
    dates = pd.date_range("2015-01-01", periods=n_days, freq="D")
    data = []
    for store in stores:
        for i, dt in enumerate(dates):
            # Sales fluctuate, closed on Sundays
            is_sunday = dt.dayofweek == 6
            open_flag = 0 if is_sunday else 1
            sales = 0 if not open_flag else (100 + (i % 7) * 20 + store * 10)
            data.append({
                "Store": store,
                "Date": dt,
                "Sales": sales,
                "Customers": 10 if open_flag else 0,
                "Open": open_flag,
                "Promo": 1 if i % 5 == 0 else 0,
                "StateHoliday": "a" if i == 15 else "0",
                "SchoolHoliday": 1 if i % 10 == 0 else 0,
                "StoreType": "a" if store == 1 else "c",
                "Assortment": "a" if store == 1 else "c",
                "state_holiday_type": "public_holiday" if i == 15 else "none",
                "competition_distance": 500.0,
                "competition_open_since_days": 100.0,
                "sales_lag_7": 100.0,
                "sales_lag_14": 100.0,
                "sales_lag_28": 100.0,
                "sales_rolling_mean_7": 100.0,
                "sales_rolling_mean_30": 100.0,
                "sales_rolling_std_7": 10.0,
                "sales_rolling_std_30": 10.0,
                "sales_expanding_mean": 100.0,
                "sales_trend_7_30": 1.0,
                "avg_customers_store_dow": 10.0
            })
    return pd.DataFrame(data)


class TestValidationSplitter:
    def test_time_series_cv_splits_correct_dates(self):
        df = _toy_data(n_days=100)
        # 3 folds of 10 days each
        splits = time_series_cv_splits(df, n_folds=3, val_window_days=10)
        assert len(splits) == 3
        
        # Max date is 2015-04-10
        # Fold 2 validation: last 10 days (2015-04-01 to 2015-04-10)
        # Fold 1 validation: 2015-03-22 to 2015-03-31
        # Fold 0 validation: 2015-03-12 to 2015-03-21
        
        for fold, (train_fold, val_fold, start, end) in enumerate(splits):
            assert train_fold["Date"].max() < val_fold["Date"].min()
            assert len(val_fold["Date"].unique()) == 10
            # Ensure no data leakage (no train dates in validation)
            assert not any(train_fold["Date"].isin(val_fold["Date"]))


class TestProphetWrapper:
    def test_build_prophet_holidays(self):
        df = pd.DataFrame({
            "Date": pd.to_datetime(["2015-01-01", "2015-01-02", "2015-01-03"]),
            "StateHoliday": ["0", "a", "0"]
        })
        holidays_df = build_prophet_holidays(df)
        assert len(holidays_df) == 1
        assert holidays_df.iloc[0]["holiday"] == "public_holiday"
        assert holidays_df.iloc[0]["ds"] == pd.Timestamp("2015-01-02")

    def test_fit_and_predict_prophet(self):
        df = _toy_data(n_days=30, stores=[1])
        wrapper = RossmannProphetWrapper(stores_to_train=[1])
        wrapper.fit(df)
        
        assert 1 in wrapper.models
        
        preds = wrapper.predict(df)
        assert len(preds) == len(df)
        
        # Closed days must be predicted as exactly 0
        closed_indices = df[df["Open"] == 0].index
        assert np.all(preds[closed_indices] == 0.0)
        
        # Open days should have positive predictions
        open_indices = df[df["Open"] == 1].index
        assert np.all(preds[open_indices] >= 0.0)


class TestTreeWrapper:
    @pytest.mark.parametrize("model_type", ["lightgbm", "xgboost"])
    def test_fit_and_predict_trees(self, model_type):
        df = _toy_data(n_days=40, stores=[1, 2])
        wrapper = RossmannTreeWrapper(model_type=model_type)
        wrapper.fit(df)
        
        preds = wrapper.predict(df)
        assert len(preds) == len(df)
        
        # Closed days must be 0
        closed_indices = df[df["Open"] == 0].index
        assert np.all(preds[closed_indices] == 0.0)
        
        # Open days should have valid predictions
        open_indices = df[df["Open"] == 1].index
        assert np.all(preds[open_indices] >= 0.0)


class TestMetricsCalculation:
    def test_calculate_metrics_values(self):
        y_true = np.array([100.0, 200.0, 300.0])
        y_pred = np.array([110.0, 190.0, 300.0])
        
        metrics = calculate_metrics(y_true, y_pred)
        assert metrics["MAE"] == pytest.approx(6.666666, abs=1e-5)
        assert metrics["RMSE"] == pytest.approx(8.164965, abs=1e-5)
        # Percentage errors: 10%, 5%, 0% -> average is 5%
        assert metrics["MAPE"] == pytest.approx(5.0, abs=1e-5)
        assert metrics["R2"] > 0.9

    def test_evaluate_predictions_excludes_closed_days(self):
        df = pd.DataFrame({
            "Sales": [100.0, 0.0, 200.0],
            "Open": [1, 0, 1]
        })
        # If prediction on closed day is way off (e.g. 50.0), it should be ignored because Open == 0
        y_pred = np.array([100.0, 50.0, 200.0])
        
        metrics = evaluate_predictions(df, y_pred)
        # MAE should be 0 because actuals are 100, 200 and preds on open days are 100, 200
        assert metrics["MAE"] == 0.0
