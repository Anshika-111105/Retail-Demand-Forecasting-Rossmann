from __future__ import annotations

import numpy as np
import pandas as pd

# Rossmann's PromoInterval uses "Sept" (not the usual "Sep") for September.
_MONTH_ABBR = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sept", 10: "Oct", 11: "Nov", 12: "Dec",
}


def add_holiday_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Binary/typed holiday indicators derived from the raw StateHoliday/SchoolHoliday columns."""
    out = df.copy()
    out["is_state_holiday"] = (out["StateHoliday"].astype(str) != "0").astype("int8")
    out["state_holiday_type"] = out["StateHoliday"].astype(str)
    out["school_holiday_active"] = out["SchoolHoliday"].astype("int8")
    return out


def add_promo2_active_flag(df: pd.DataFrame, date_col: str = "Date") -> pd.DataFrame:
    """Whether a store's recurring Promo2 campaign is running on the given date"""
    out = df.copy()
    dt = out[date_col].dt
    month_abbr = dt.month.map(_MONTH_ABBR)
    iso_year = dt.isocalendar().year.astype("int32")
    iso_week = dt.isocalendar().week.astype("int32")

    promo_interval = out["PromoInterval"].astype(object).fillna("").astype(str)
    month_in_interval = pd.Series(
        [
            (abbr in interval.split(",")) if interval else False
            for abbr, interval in zip(month_abbr, promo_interval)
        ],
        index=out.index,
    )

    since_year = out["Promo2SinceYear"]
    since_week = out["Promo2SinceWeek"]
    enrolled_by_now = (iso_year > since_year) | ((iso_year == since_year) & (iso_week >= since_week))

    out["promo2_active_today"] = (
        (out["Promo2"] == 1) & month_in_interval & enrolled_by_now.fillna(False)
    ).astype("int8")
    return out


def add_promo_duration(df: pd.DataFrame, store_col: str = "Store", date_col: str = "Date") -> pd.DataFrame:
    """Consecutive days into the current Promo streak, per store (0 on non-promo days)."""
    out = df.sort_values([store_col, date_col]).copy()

    # A new "block" starts each time Promo flips 0<->1 (or a new store begins); within a
    # block, cumcount+1 gives the day-into-streak, then non-promo blocks are zeroed out.
    block = out.groupby(store_col)["Promo"].transform(lambda s: (s != s.shift()).cumsum())
    duration = out.groupby([out[store_col], block]).cumcount() + 1
    out["promo_duration_days"] = np.where(out["Promo"] == 1, duration, 0).astype("int32")

    return out.sort_index()
