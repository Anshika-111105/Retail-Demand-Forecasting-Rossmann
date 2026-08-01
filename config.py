"""Central configuration loader for the RetailX Demand Forecasting & Inventory Optimization Platform.

Loads configuration parameters from config/config.yaml with fallback defaults and environment overrides.
"""
from __future__ import annotations

import os
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent


class Config:
    def __init__(self, config_path: Path | str | None = None):
        if config_path is None:
            config_path = PROJECT_ROOT / "config" / "config.yaml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            # Fallback configuration in case the YAML file is not found
            self.db_host = os.environ.get("DB_HOST", "localhost")
            self.db_port = int(os.environ.get("DB_PORT", 55432))
            self.db_name = os.environ.get("DB_NAME", "rossmann")
            self.db_user = os.environ.get("DB_USER", "rossmann")
            self.db_password = os.environ.get("DB_PASSWORD", "rossmann")
            
            self.target_stores = list(range(1, 11))
            self.val_window_days = 42
            self.n_folds = 3
            self.random_seed = 42
            self.data_dir = "./data"
            self.logs_dir = "./logs"
            
            self.lgbm_params = {}
            self.xgb_params = {}
            return

        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}

        db = data.get("database", {})
        self.db_host = os.environ.get("DB_HOST", db.get("host", "localhost"))
        self.db_port = int(os.environ.get("DB_PORT", db.get("port", 55432)))
        self.db_name = os.environ.get("DB_NAME", db.get("name", "rossmann"))
        self.db_user = os.environ.get("DB_USER", db.get("user", "rossmann"))
        self.db_password = os.environ.get("DB_PASSWORD", db.get("password", "rossmann"))

        pipe = data.get("pipeline", {})
        self.target_stores = pipe.get("target_stores", list(range(1, 11)))
        self.val_window_days = pipe.get("val_window_days", 42)
        self.n_folds = pipe.get("n_folds", 3)
        self.random_seed = pipe.get("random_seed", 42)
        self.data_dir = pipe.get("data_dir", "./data")
        self.logs_dir = pipe.get("logs_dir", "./logs")

        models = data.get("models", {})
        self.lgbm_params = models.get("lightgbm", {})
        self.xgb_params = models.get("xgboost", {})


# Singleton config instance
cfg = Config()
