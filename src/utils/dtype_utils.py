from __future__ import annotations

from typing import Sequence

import pandas as pd


def downcast_numeric(df: pd.DataFrame, int_cols: Sequence[str], float_cols: Sequence[str]) -> pd.DataFrame:
    """Downcast integer and float columns to the smallest safe dtype."""
    out = df.copy()
    for col in int_cols:
        out[col] = pd.to_numeric(out[col], downcast="integer")
    for col in float_cols:
        out[col] = pd.to_numeric(out[col], downcast="float")
    return out


def to_category(df: pd.DataFrame, cols: Sequence[str]) -> pd.DataFrame:
    """Cast low-cardinality identifier/text columns to pandas ``category`` dtype."""
    out = df.copy()
    for col in cols:
        out[col] = out[col].astype("category")
    return out
