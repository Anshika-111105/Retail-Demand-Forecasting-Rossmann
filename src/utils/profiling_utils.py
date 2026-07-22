from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd


def profile_dataframe(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Produce a per-column profiling summary: dtype, nulls, uniqueness."""
    summary = pd.DataFrame(
        {
            "dtype": df.dtypes.astype(str),
            "null_count": df.isnull().sum(),
            "null_pct": (df.isnull().mean() * 100).round(2),
            "n_unique": df.nunique(),
            "memory_mb": (df.memory_usage(deep=True) / 1e6).round(3).iloc[1:].reindex(df.columns),
        }
    )
    return summary


def duplicate_report(df: pd.DataFrame, key_cols: Sequence[str]) -> dict:
    """Report full-row and composite-key duplicate counts."""
    return {
        "full_row_duplicates": int(df.duplicated().sum()),
        "key_duplicates": int(df.duplicated(subset=list(key_cols)).sum()),
    }


def detect_outliers_iqr(series: pd.Series, k: float = 1.5) -> pd.Series:
    """Flag values outside the IQR fence. Detection only — no removal/analysis."""
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - k * iqr, q3 + k * iqr
    return (series < lower) | (series > upper)


def memory_usage_mb(df: pd.DataFrame) -> float:
    """Return total deep memory usage of a DataFrame in megabytes."""
    return float(df.memory_usage(deep=True).sum() / 1e6)
