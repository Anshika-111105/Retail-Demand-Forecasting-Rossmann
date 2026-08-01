"""Unified CLI Entry Point for the RetailX Demand Forecasting & Inventory Optimization Platform.

Supports database loading, pipeline training, running tests, and launching the Streamlit dashboard.
"""
from __future__ import annotations

import argparse
import sys
import subprocess
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_db_load():
    """Load processed Rossmann datasets into PostgreSQL database."""
    print("Loading datasets into PostgreSQL warehouse...")
    from src.utils.db_loader import load_rossmann_to_postgres
    processed_dir = PROJECT_ROOT / "data" / "processed"
    try:
        load_rossmann_to_postgres(processed_dir)
        print("Data loaded successfully!")
    except Exception as e:
        print(f"Error loading data: {e}", file=sys.stderr)
        sys.exit(1)


def run_train_pipeline():
    """Train Prophet, XGBoost, and LightGBM models."""
    print("Running training and validation pipeline...")
    script_path = PROJECT_ROOT / "src" / "machine_learning" / "train_pipeline.py"
    res = subprocess.run([sys.executable, str(script_path)])
    sys.exit(res.returncode)


def run_dashboard():
    """Start the Streamlit dashboard application."""
    print("Starting Streamlit Dashboard server...")
    app_path = PROJECT_ROOT / "dashboard" / "app.py"
    cmd = [
        sys.executable,
        "-m", "streamlit", "run", str(app_path),
        "--server.headless", "true",
        "--server.port", "8501"
    ]
    try:
        res = subprocess.run(cmd)
        sys.exit(res.returncode)
    except KeyboardInterrupt:
        print("\nDashboard server stopped.")


def run_tests():
    """Run all unit tests using pytest."""
    print("Running test suite...")
    res = subprocess.run([sys.executable, "-m", "pytest"])
    sys.exit(res.returncode)


def main():
    parser = argparse.ArgumentParser(
        description="RetailX Demand Forecasting & Inventory Optimization CLI."
    )
    parser.add_argument(
        "--action",
        choices=["load-db", "train", "run-dashboard", "test"],
        required=True,
        help="Action to perform: load-db, train, run-dashboard, or test."
    )

    args = parser.parse_args()

    if args.action == "load-db":
        run_db_load()
    elif args.action == "train":
        run_train_pipeline()
    elif args.action == "run-dashboard":
        run_dashboard()
    elif args.action == "test":
        run_tests()


if __name__ == "__main__":
    main()
