from __future__ import annotations

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def validate_rossmann_dataset(df: pd.DataFrame, is_test: bool = False) -> None:
    """Validate data schema, completeness, range boundaries, and logical consistency.
    
    Raises AssertionError if any check fails.
    """
    logger.info("Running runtime data validation checks...")
    
    # 1. Schema check: Required columns
    required_cols = ["Store", "Date", "Open", "Promo", "StateHoliday", "SchoolHoliday"]
    if not is_test:
        required_cols.append("Sales")
        
    missing_cols = [col for col in required_cols if col not in df.columns]
    assert not missing_cols, f"Schema validation failed: Missing columns: {missing_cols}"
    
    # 2. Key column null checks (crucial columns must not contain NaN)
    for col in required_cols:
        null_count = df[col].isnull().sum()
        assert null_count == 0, f"Integrity check failed: Column '{col}' contains {null_count} null value(s)."
        
    # 3. Duplicate checks (uniqueness constraint on primary key)
    duplicate_count = df.duplicated(subset=["Store", "Date"]).sum()
    assert duplicate_count == 0, f"Uniqueness check failed: Found {duplicate_count} duplicate row(s) for primary key (Store, Date)."
    
    # 4. Logical value range checks
    assert df["Store"].min() >= 1, "Value range check failed: Store IDs must be >= 1."
    assert set(df["Open"].unique()).issubset({0, 1}), "Value range check failed: Open flag must be binary (0 or 1)."
    assert set(df["Promo"].unique()).issubset({0, 1}), "Value range check failed: Promo flag must be binary (0 or 1)."
    assert set(df["SchoolHoliday"].unique()).issubset({0, 1}), "Value range check failed: SchoolHoliday flag must be binary (0 or 1)."
    
    # StateHoliday values must belong to the valid Rossmann encoding set
    valid_state_holidays = {"0", "a", "b", "c"}
    state_holiday_set = {str(val).strip() for val in df["StateHoliday"].unique() if pd.notna(val)}
    # If pandas categorized string '0.0' or other forms, convert/check safely
    state_holiday_set = {v.replace(".0", "") for v in state_holiday_set}
    invalid_holidays = state_holiday_set - valid_state_holidays
    assert not invalid_holidays, f"Value range check failed: StateHoliday contains invalid code(s): {invalid_holidays}"
    
    # 5. Target column sanity check (only on training/validation datasets)
    if not is_test:
        # Sales must be non-negative
        negative_sales = (df["Sales"] < 0).sum()
        assert negative_sales == 0, f"Value range check failed: Found {negative_sales} negative Sales record(s)."
        
        # Closed stores should not have sales
        closed_with_sales = df[(df["Open"] == 0) & (df["Sales"] > 0)].shape[0]
        assert closed_with_sales == 0, f"Logical consistency check failed: Found {closed_with_sales} closed store(s) with Sales > 0."

    logger.info("All data validation checks passed successfully!")
