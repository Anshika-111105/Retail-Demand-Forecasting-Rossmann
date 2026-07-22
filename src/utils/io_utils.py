from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def load_csv(path: Path, **read_csv_kwargs) -> pd.DataFrame:
    """Load a CSV file into a DataFrame with basic existence validation and logging."""
    if not path.exists():
        raise FileNotFoundError(f"Expected raw data file not found: {path}")

    df = pd.read_csv(path, **read_csv_kwargs)
    logger.info("Loaded %s -> shape=%s", path.name, df.shape)
    return df


def save_parquet(df: pd.DataFrame, path: Path) -> None:
    """Persist a DataFrame to Parquet, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    logger.info("Saved %s -> shape=%s, size=%.2f MB", path.name, df.shape, path.stat().st_size / 1e6)
