from __future__ import annotations

import numpy as np
import pandas as pd


def add_competition_features(df: pd.DataFrame, date_col: str = "Date") -> pd.DataFrame:
    """Competition-exposure features."""
    out = df.copy()

    out["has_competition"] = out["CompetitionDistance"].notna().astype("int8")

    # Sentinel fill only after has_competition already captures the "no competitor" case,
    # so tree-based models never have to treat a raw NaN distance as an unbounded value.
    max_distance = out["CompetitionDistance"].max()
    sentinel_distance = max_distance if pd.notna(max_distance) else 0.0
    out["competition_distance"] = out["CompetitionDistance"].fillna(sentinel_distance).astype("float32")

    competition_open_date = pd.to_datetime(
        dict(
            year=out["CompetitionOpenSinceYear"],
            month=out["CompetitionOpenSinceMonth"],
            day=1,
        ),
        errors="coerce",
    )
    days_since = (out[date_col] - competition_open_date).dt.days
    # Negative means the competitor had not yet opened as of this row's date -> not yet felt.
    out["competition_open_since_days"] = days_since.where(days_since >= 0, np.nan).astype("float32")

    return out
