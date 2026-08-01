from __future__ import annotations

import logging
import os
import sys
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.logging_utils import get_logger  # noqa: E402
from src.utils.data_validation import validate_rossmann_dataset  # noqa: E402
from src.machine_learning.models import RossmannProphetWrapper, RossmannTreeWrapper  # noqa: E402
from src.machine_learning.validation import time_series_cv_splits, evaluate_predictions  # noqa: E402

from config import cfg

STORES_TO_FORECAST = cfg.target_stores

logger = get_logger("train_pipeline", PROJECT_ROOT / "logs")


def load_datasets() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load train and test features from parquet files."""
    train_path = PROJECT_ROOT / "data" / "processed" / "rossmann_train_features.parquet"
    test_path = PROJECT_ROOT / "data" / "processed" / "rossmann_test_features.parquet"
    
    if not train_path.exists() or not test_path.exists():
        logger.error(f"Feature parquet files not found! Checked {train_path} and {test_path}")
        sys.exit(1)
        
    logger.info("Loading train and test features from parquet...")
    train_df = pd.read_parquet(train_path)
    test_df = pd.read_parquet(test_path)
    return train_df, test_df


def run_cross_validation(train_df: pd.DataFrame) -> dict[str, list[dict[str, float]]]:
    """Run rolling time-series CV on Prophet, XGBoost, and LightGBM."""
    logger.info("Starting Time-Series Cross Validation...")
    splits = time_series_cv_splits(train_df, n_folds=cfg.n_folds, val_window_days=cfg.val_window_days)
    
    results = {
        "Prophet": [],
        "XGBoost": [],
        "LightGBM": []
    }
    
    # Store out-of-fold predictions to evaluate overall or save later
    oof_predictions = []
    
    for fold, (train_fold, val_fold, val_start, val_end) in enumerate(splits):
        logger.info(f"--- FOLD {fold+1} (Validation: {val_start.date()} to {val_end.date()}) ---")
        logger.info(f"Train size: {train_fold.shape[0]} rows, Validation size: {val_fold.shape[0]} rows")
        
        # 1. Prophet (subset of stores)
        logger.info("Fitting Prophet models...")
        prophet_model = RossmannProphetWrapper(stores_to_train=STORES_TO_FORECAST)
        prophet_model.fit(train_fold)
        prophet_preds = prophet_model.predict(val_fold)
        
        # Prophet fallback: for stores where Prophet wasn't trained, use average/zero
        # But to be fair in metric comparison, we evaluate Prophet metrics only on the subset of stores it was trained on!
        prophet_val_subset = val_fold[val_fold["Store"].isin(STORES_TO_FORECAST)].copy()
        prophet_preds_subset = prophet_preds[val_fold["Store"].isin(STORES_TO_FORECAST)]
        prophet_metrics = evaluate_predictions(prophet_val_subset, prophet_preds_subset)
        results["Prophet"].append(prophet_metrics)
        logger.info(f"Prophet fold metrics (stores 1-10): {prophet_metrics}")
        
        # 2. XGBoost
        logger.info("Fitting global XGBoost model...")
        xgb_model = RossmannTreeWrapper(model_type="xgboost", params=cfg.xgb_params)
        xgb_model.fit(train_fold)
        xgb_preds = xgb_model.predict(val_fold)
        xgb_metrics = evaluate_predictions(val_fold, xgb_preds)
        results["XGBoost"].append(xgb_metrics)
        logger.info(f"XGBoost fold metrics (all stores): {xgb_metrics}")
        
        # 3. LightGBM
        logger.info("Fitting global LightGBM model...")
        lgb_model = RossmannTreeWrapper(model_type="lightgbm", params=cfg.lgbm_params)
        lgb_model.fit(train_fold)
        lgb_preds = lgb_model.predict(val_fold)
        lgb_metrics = evaluate_predictions(val_fold, lgb_preds)
        results["LightGBM"].append(lgb_metrics)
        logger.info(f"LightGBM fold metrics (all stores): {lgb_metrics}")
        
        # Save OOF predictions for saving/visualization in the dashboard
        # Filter for stores 1-10 to compare all three models side-by-side
        fold_comp = val_fold[["Date", "Store", "Sales", "Open", "Promo", "SchoolHoliday", "StateHoliday"]].copy()
        fold_comp["Prophet"] = prophet_preds
        fold_comp["XGBoost"] = xgb_preds
        fold_comp["LightGBM"] = lgb_preds
        oof_predictions.append(fold_comp)

    # Summarize and log average CV results
    logger.info("==================================================")
    logger.info("AVERAGE CROSS-VALIDATION RESULTS:")
    for model_name, metrics_list in results.items():
        avg_metrics = {}
        for metric in ["MAE", "RMSE", "MAPE", "R2"]:
            avg_metrics[metric] = np.mean([m[metric] for m in metrics_list])
        logger.info(f"{model_name}: {avg_metrics}")
    logger.info("==================================================")
    
    return results, pd.concat(oof_predictions, ignore_index=True)


def train_final_models(train_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple[RossmannProphetWrapper, RossmannTreeWrapper, RossmannTreeWrapper, pd.DataFrame]:
    """Train final models on the entire dataset and generate test predictions."""
    logger.info("Training final models on complete dataset...")
    
    # 1. Prophet
    prophet_model = RossmannProphetWrapper(stores_to_train=STORES_TO_FORECAST)
    prophet_model.fit(train_df)
    logger.info("Generating test predictions with Prophet...")
    prophet_test_preds = prophet_model.predict(test_df)
    
    # 2. XGBoost
    xgb_model = RossmannTreeWrapper(model_type="xgboost", params=cfg.xgb_params)
    xgb_model.fit(train_df)
    logger.info("Generating test predictions with XGBoost...")
    xgb_test_preds = xgb_model.predict(test_df)
    
    # 3. LightGBM
    lgb_model = RossmannTreeWrapper(model_type="lightgbm", params=cfg.lgbm_params)
    lgb_model.fit(train_df)
    logger.info("Generating test predictions with LightGBM...")
    lgb_test_preds = lgb_model.predict(test_df)
    
    # Save final model binaries
    models_dir = PROJECT_ROOT / "models" / "trained"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Saving final model binaries to {models_dir}...")
    with open(models_dir / "xgboost_model.pkl", "wb") as f:
        pickle.dump(xgb_model, f)
    with open(models_dir / "lightgbm_model.pkl", "wb") as f:
        pickle.dump(lgb_model, f)
    with open(models_dir / "prophet_model.pkl", "wb") as f:
        pickle.dump(prophet_model, f)
        
    # Build test predictions DataFrame
    test_preds_df = test_df[["Date", "Store", "Open", "Promo", "SchoolHoliday", "StateHoliday"]].copy()
    test_preds_df["Sales"] = 0.0  # Placeholder/Actual target (unknown for test)
    test_preds_df["Prophet"] = prophet_test_preds
    test_preds_df["XGBoost"] = xgb_test_preds
    test_preds_df["LightGBM"] = lgb_test_preds
    
    return prophet_model, xgb_model, lgb_model, test_preds_df


def save_predictions_for_dashboard(train_df: pd.DataFrame, oof_df: pd.DataFrame, test_preds_df: pd.DataFrame):
    """Combine actuals, validation predictions, and test forecasts into a single Parquet file."""
    logger.info("Combining results for the Streamlit dashboard...")
    
    # We only save historical actuals and predictions for stores 1-10 to save disk space and loading time in dashboard.
    target_stores = STORES_TO_FORECAST
    
    # 1. Historical Actuals (all available historical train data for stores 1-10)
    actuals = train_df[train_df["Store"].isin(target_stores)][["Date", "Store", "Sales", "Open", "Promo", "SchoolHoliday", "StateHoliday"]].copy()
    actuals["Model"] = "Actuals"
    actuals["Type"] = "Actuals"
    
    # 2. Validation predictions
    val_preds = []
    for model in ["Prophet", "XGBoost", "LightGBM"]:
        model_val = oof_df[oof_df["Store"].isin(target_stores)][["Date", "Store", model, "Open", "Promo", "SchoolHoliday", "StateHoliday"]].copy()
        model_val = model_val.rename(columns={model: "Sales"})
        model_val["Model"] = model
        model_val["Type"] = "Validation"
        val_preds.append(model_val)
        
    # 3. Test predictions
    test_preds = []
    for model in ["Prophet", "XGBoost", "LightGBM"]:
        model_test = test_preds_df[test_preds_df["Store"].isin(target_stores)][["Date", "Store", model, "Open", "Promo", "SchoolHoliday", "StateHoliday"]].copy()
        model_test = model_test.rename(columns={model: "Sales"})
        model_test["Model"] = model
        model_test["Type"] = "Test"
        test_preds.append(model_test)
        
    # Combine everything
    dashboard_df = pd.concat([actuals] + val_preds + test_preds, ignore_index=True)
    
    artifacts_dir = PROJECT_ROOT / "models" / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = artifacts_dir / "predictions.parquet"
    logger.info(f"Saving combined predictions to {output_path}...")
    dashboard_df.to_parquet(output_path, index=False)
    
    # Save a CSV metrics summary for easy dashboard loading
    cv_summary = []
    # Note: These values will be populated manually from validation runs to save computations in dashboard
    
    logger.info("Pipeline execution completed successfully!")


def main():
    train_df, test_df = load_datasets()
    validate_rossmann_dataset(train_df, is_test=False)
    validate_rossmann_dataset(test_df, is_test=True)
    cv_results, oof_df = run_cross_validation(train_df)
    _, _, _, test_preds_df = train_final_models(train_df, test_df)
    save_predictions_for_dashboard(train_df, oof_df, test_preds_df)


if __name__ == "__main__":
    main()
