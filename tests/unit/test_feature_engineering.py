from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

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


def _toy_store_row(**overrides):
    row = {
        "Store": 1,
        "StoreType": "a",
        "Assortment": "a",
        "CompetitionDistance": 500.0,
        "CompetitionOpenSinceMonth": 1.0,
        "CompetitionOpenSinceYear": 2010.0,
        "Promo2": 1,
        "Promo2SinceWeek": 10.0,
        "Promo2SinceYear": 2014.0,
        "PromoInterval": "Jan,Apr,Jul,Oct",
    }
    row.update(overrides)
    return row


def _toy_daily_frame(store_row: dict, dates: pd.DatetimeIndex, **col_overrides) -> pd.DataFrame:
    n = len(dates)
    df = pd.DataFrame(
        {
            "Date": dates,
            "DayOfWeek": dates.dayofweek.map(lambda d: d + 1),  # pandas Mon=0 -> Kaggle Mon=1
            "Sales": [100] * n,
            "Customers": [10] * n,
            "Open": [1] * n,
            "Promo": [0] * n,
            "StateHoliday": ["0"] * n,
            "SchoolHoliday": [0] * n,
        }
    )
    for k, v in store_row.items():
        df[k] = v
    for k, v in col_overrides.items():
        df[k] = v
    return df


class TestCalendarFeatures:
    def test_weekend_flag_matches_kaggle_encoding(self):
        dates = pd.to_datetime(["2015-01-03", "2015-01-04", "2015-01-05"])  # Sat, Sun, Mon
        df = pd.DataFrame({"Date": dates, "DayOfWeek": [6, 7, 1]})
        out = add_calendar_features(df)
        assert out["is_weekend"].tolist() == [1, 1, 0]

    def test_month_start_and_end_flags(self):
        dates = pd.to_datetime(["2015-02-01", "2015-02-15", "2015-02-28"])
        df = pd.DataFrame({"Date": dates, "DayOfWeek": [7, 7, 6]})
        out = add_calendar_features(df)
        assert out["is_month_start"].tolist() == [1, 0, 0]
        assert out["is_month_end"].tolist() == [0, 0, 1]


class TestHolidayIndicators:
    def test_state_holiday_flag_and_type(self):
        df = pd.DataFrame({"StateHoliday": ["0", "a", "b", "c"], "SchoolHoliday": [0, 1, 0, 1]})
        out = add_holiday_indicators(df)
        assert out["is_state_holiday"].tolist() == [0, 1, 1, 1]
        assert out["state_holiday_type"].tolist() == ["0", "a", "b", "c"]
        assert out["school_holiday_active"].tolist() == [0, 1, 0, 1]


class TestPromo2ActiveFlag:
    def test_active_when_enrolled_and_month_and_week_match(self):
        # Store enrolled from ISO week 10, 2014; PromoInterval includes January.
        store_row = _toy_store_row(Promo2SinceWeek=10.0, Promo2SinceYear=2014.0)
        dates = pd.to_datetime(["2015-01-15"])  # January, well after enrollment
        df = _toy_daily_frame(store_row, dates)
        out = add_promo2_active_flag(df)
        assert out["promo2_active_today"].iloc[0] == 1

    def test_inactive_when_month_not_in_interval(self):
        store_row = _toy_store_row(PromoInterval="Feb,May,Aug,Nov")
        dates = pd.to_datetime(["2015-01-15"])
        df = _toy_daily_frame(store_row, dates)
        out = add_promo2_active_flag(df)
        assert out["promo2_active_today"].iloc[0] == 0

    def test_inactive_before_enrollment_date(self):
        store_row = _toy_store_row(Promo2SinceWeek=30.0, Promo2SinceYear=2015.0)
        dates = pd.to_datetime(["2015-01-15"])  # before week 30 of 2015
        df = _toy_daily_frame(store_row, dates)
        out = add_promo2_active_flag(df)
        assert out["promo2_active_today"].iloc[0] == 0

    def test_inactive_when_not_enrolled_in_promo2(self):
        store_row = _toy_store_row(Promo2=0, PromoInterval=None, Promo2SinceWeek=np.nan, Promo2SinceYear=np.nan)
        dates = pd.to_datetime(["2015-01-15"])
        df = _toy_daily_frame(store_row, dates)
        out = add_promo2_active_flag(df)
        assert out["promo2_active_today"].iloc[0] == 0

    def test_handles_sept_abbreviation(self):
        store_row = _toy_store_row(PromoInterval="Mar,Jun,Sept,Dec")
        dates = pd.to_datetime(["2015-09-10"])
        df = _toy_daily_frame(store_row, dates)
        out = add_promo2_active_flag(df)
        assert out["promo2_active_today"].iloc[0] == 1


class TestPromoDuration:
    def test_resets_between_streaks_and_across_stores(self):
        df = pd.DataFrame(
            {
                "Store": [1, 1, 1, 1, 2, 2],
                "Date": pd.to_datetime(
                    ["2015-01-01", "2015-01-02", "2015-01-03", "2015-01-04", "2015-01-01", "2015-01-02"]
                ),
                "Promo": [1, 1, 0, 1, 1, 1],
            }
        )
        out = add_promo_duration(df)
        result = out.set_index(["Store", "Date"])["promo_duration_days"]
        assert result[(1, "2015-01-01")] == 1
        assert result[(1, "2015-01-02")] == 2
        assert result[(1, "2015-01-03")] == 0
        assert result[(1, "2015-01-04")] == 1
        assert result[(2, "2015-01-01")] == 1
        assert result[(2, "2015-01-02")] == 2


class TestCompetitionFeatures:
    def test_no_competitor_is_flagged_not_imputed_as_zero(self):
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2015-01-01"]),
                "CompetitionDistance": [np.nan],
                "CompetitionOpenSinceMonth": [np.nan],
                "CompetitionOpenSinceYear": [np.nan],
            }
        )
        out = add_competition_features(df)
        assert out["has_competition"].iloc[0] == 0
        assert not np.isnan(out["competition_distance"].iloc[0])  # sentinel-filled, not left NaN
        assert np.isnan(out["competition_open_since_days"].iloc[0])

    def test_competition_open_since_days_is_nonnegative_and_correct(self):
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2015-06-01"]),
                "CompetitionDistance": [1000.0],
                "CompetitionOpenSinceMonth": [1.0],
                "CompetitionOpenSinceYear": [2015.0],
            }
        )
        out = add_competition_features(df)
        assert out["competition_open_since_days"].iloc[0] == pytest.approx(151, abs=1)

    def test_future_competitor_open_date_yields_nan_not_negative(self):
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2015-01-01"]),
                "CompetitionDistance": [1000.0],
                "CompetitionOpenSinceMonth": [12.0],
                "CompetitionOpenSinceYear": [2015.0],
            }
        )
        out = add_competition_features(df)
        assert np.isnan(out["competition_open_since_days"].iloc[0])


class TestLagRollingFeatures:
    def test_no_current_day_leakage(self):
        dates = pd.date_range("2015-01-01", periods=10, freq="D")
        sales = list(range(100, 110))
        df = pd.DataFrame(
            {
                "Store": 1,
                "Date": dates,
                "Sales": sales,
                "Open": 1,
            }
        )
        train_out, _ = add_lag_rolling_features(df)
        last = train_out.iloc[-1]
        # rolling_mean_7 on the final row must average the 7 days *before* it, excluding itself.
        expected = np.mean(sales[-8:-1])
        assert last["sales_rolling_mean_7"] == pytest.approx(expected)

    def test_lag_7_matches_value_seven_days_prior(self):
        dates = pd.date_range("2015-01-01", periods=10, freq="D")
        sales = list(range(100, 110))
        df = pd.DataFrame({"Store": 1, "Date": dates, "Sales": sales, "Open": 1})
        train_out, _ = add_lag_rolling_features(df)
        row = train_out[train_out["Date"] == dates[9]].iloc[0]
        assert row["sales_lag_7"] == sales[2]

    def test_closed_days_excluded_from_rolling_mean(self):
        dates = pd.date_range("2015-01-01", periods=5, freq="D")
        df = pd.DataFrame(
            {
                "Store": 1,
                "Date": dates,
                "Sales": [100, 0, 100, 100, 100],
                "Open": [1, 0, 1, 1, 1],
            }
        )
        train_out, _ = add_lag_rolling_features(df)
        last = train_out.iloc[-1]
        # closed-day (index 1) sales must not dilute the rolling mean toward 0
        assert last["sales_rolling_mean_7"] == pytest.approx(100.0)

    def test_store_gap_does_not_shift_lag_alignment(self):
        # Store 1 has a real gap (missing row) on 2015-01-04; lag_7 for 2015-01-10 must
        # still mean "7 calendar days back" (2015-01-03), not "7 rows back".
        dates = pd.to_datetime(
            ["2015-01-01", "2015-01-02", "2015-01-03", "2015-01-05", "2015-01-06",
             "2015-01-07", "2015-01-08", "2015-01-09", "2015-01-10"]
        )
        sales = [10, 20, 30, 50, 60, 70, 80, 90, 100]
        df = pd.DataFrame({"Store": 1, "Date": dates, "Sales": sales, "Open": 1})
        train_out, _ = add_lag_rolling_features(df)
        row = train_out[train_out["Date"] == pd.Timestamp("2015-01-10")].iloc[0]
        assert row["sales_lag_7"] == 30  # value on 2015-01-03

    def test_test_rows_beyond_lag_depth_are_nan(self):
        train_dates = pd.date_range("2015-01-01", periods=10, freq="D")
        train_df = pd.DataFrame(
            {"Store": 1, "Date": train_dates, "Sales": range(100, 110), "Open": 1}
        )
        test_dates = pd.date_range(train_dates[-1] + pd.Timedelta(days=1), periods=10, freq="D")
        test_df = pd.DataFrame({"Store": 1, "Date": test_dates, "Open": 1})

        _, test_out = add_lag_rolling_features(train_df, test_df)
        early = test_out[test_out["Date"] == test_dates[0]].iloc[0]
        late = test_out[test_out["Date"] == test_dates[-1]].iloc[0]
        assert not np.isnan(early["sales_lag_7"])  # still reachable from train tail
        assert np.isnan(late["sales_lag_7"])  # falls inside the unknown test window


class TestCustomerTrafficLookup:
    def test_lookup_never_exposes_raw_customers_column(self):
        train_df = pd.DataFrame(
            {
                "Store": [1, 1, 1],
                "DayOfWeek": [1, 1, 1],
                "Customers": [10, 20, 30],
                "Open": [1, 1, 1],
            }
        )
        lookup = build_customer_traffic_lookup(train_df)
        assert "Customers" not in lookup.columns
        assert lookup["avg_customers_store_dow"].iloc[0] == pytest.approx(20.0)

    def test_apply_lookup_works_on_frame_without_customers_column(self):
        # Simulates test.csv, which has no Customers column at all.
        train_df = pd.DataFrame(
            {"Store": [1, 1], "DayOfWeek": [1, 1], "Customers": [10, 30], "Open": [1, 1]}
        )
        lookup = build_customer_traffic_lookup(train_df)
        test_df = pd.DataFrame({"Store": [1], "DayOfWeek": [1]})
        out = apply_customer_traffic_lookup(test_df, lookup)
        assert out["avg_customers_store_dow"].iloc[0] == pytest.approx(20.0)
