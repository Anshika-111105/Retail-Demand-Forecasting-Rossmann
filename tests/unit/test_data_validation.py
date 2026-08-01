from __future__ import annotations

import pandas as pd
import pytest

from src.utils.data_validation import validate_rossmann_dataset


def test_valid_dataset_passes():
    df = pd.DataFrame({
        "Store": [1, 2],
        "Date": pd.to_datetime(["2015-01-01", "2015-01-01"]),
        "Sales": [100.0, 200.0],
        "Open": [1, 1],
        "Promo": [0, 1],
        "StateHoliday": ["0", "a"],
        "SchoolHoliday": [0, 1]
    })
    # Should not raise any assertion errors
    validate_rossmann_dataset(df, is_test=False)


def test_missing_column_raises_error():
    # DataFrame missing the target column 'Sales' when is_test=False
    df = pd.DataFrame({
        "Store": [1],
        "Date": pd.to_datetime(["2015-01-01"]),
        "Open": [1],
        "Promo": [0],
        "StateHoliday": ["0"],
        "SchoolHoliday": [0]
    })
    with pytest.raises(AssertionError) as excinfo:
        validate_rossmann_dataset(df, is_test=False)
    assert "Missing columns" in str(excinfo.value)


def test_nulls_raise_error():
    df = pd.DataFrame({
        "Store": [1, 2],
        "Date": [pd.Timestamp("2015-01-01"), pd.NaT],
        "Sales": [100.0, 200.0],
        "Open": [1, 1],
        "Promo": [0, 1],
        "StateHoliday": ["0", "a"],
        "SchoolHoliday": [0, 1]
    })
    with pytest.raises(AssertionError) as excinfo:
        validate_rossmann_dataset(df, is_test=False)
    assert "Column 'Date' contains" in str(excinfo.value)


def test_negative_sales_raise_error():
    df = pd.DataFrame({
        "Store": [1],
        "Date": pd.to_datetime(["2015-01-01"]),
        "Sales": [-50.0],
        "Open": [1],
        "Promo": [0],
        "StateHoliday": ["0"],
        "SchoolHoliday": [0]
    })
    with pytest.raises(AssertionError) as excinfo:
        validate_rossmann_dataset(df, is_test=False)
    assert "negative Sales record" in str(excinfo.value)


def test_closed_with_sales_raises_error():
    # If store is closed (Open=0), sales must be 0
    df = pd.DataFrame({
        "Store": [1],
        "Date": pd.to_datetime(["2015-01-01"]),
        "Sales": [150.0],
        "Open": [0],
        "Promo": [0],
        "StateHoliday": ["0"],
        "SchoolHoliday": [0]
    })
    with pytest.raises(AssertionError) as excinfo:
        validate_rossmann_dataset(df, is_test=False)
    assert "closed store(s) with Sales > 0" in str(excinfo.value)
