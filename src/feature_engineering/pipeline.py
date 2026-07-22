from __future__ import annotations

from typing import Optional

import pandas as pd

from src.feature_engineering.calendar_features import add_calendar_features
from src.feature_engineering.competition_features import add_competition_features
from src.feature_engineering.lag_rolling_features import (
    add_lag_rolling_features,
    apply_customer_traffic_lookup,
    build_customer_traffic_lookup,
)
from src.feature_engineering.promo_holiday_features import (
    add_holiday_indicators,
    add_promo2_active_flag,
    add_promo_duration,
)


def _add_stateless_features(df: pd.DataFrame) -> pd.DataFrame:
    """Feature groups that only need the row itself (no cross-row/store history)."""
    out = add_calendar_features(df)
    out = add_holiday_indicators(out)
    out = add_promo2_active_flag(out)
    out = add_competition_features(out)
    return out


def build_feature_table(
    train_df: pd.DataFrame, test_df: Optional[pd.DataFrame] = None
) -> tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    """Run the full feature-engineering pipeline on processed train (and test) data."""
    train_feat = _add_stateless_features(train_df)
    train_feat = add_promo_duration(train_feat)

    test_feat = None
    if test_df is not None:
        test_feat = _add_stateless_features(test_df)
        test_feat = add_promo_duration(test_feat)

    train_feat, test_feat = add_lag_rolling_features(train_feat, test_feat)

    customer_lookup = build_customer_traffic_lookup(train_df)
    train_feat = apply_customer_traffic_lookup(train_feat, customer_lookup)
    if test_feat is not None:
        test_feat = apply_customer_traffic_lookup(test_feat, customer_lookup)

    return train_feat, test_feat
