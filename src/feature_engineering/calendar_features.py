from __future__ import annotations

import pandas as pd


def add_calendar_features(df: pd.DataFrame, date_col: str = "Date") -> pd.DataFrame:
    """Derive calendar-rhythm features from a date column."""
    out = df.copy()
    dt = out[date_col].dt

    out["month"] = dt.month.astype("int8")
    out["week_of_year"] = dt.isocalendar().week.astype("int8")
    out["quarter"] = dt.quarter.astype("int8")
    out["year"] = dt.year.astype("int16")
    out["day_of_month"] = dt.day.astype("int8")
    out["is_weekend"] = out["DayOfWeek"].isin([6, 7]).astype("int8")
    out["is_month_start"] = dt.is_month_start.astype("int8")
    out["is_month_end"] = dt.is_month_end.astype("int8")

    return out
