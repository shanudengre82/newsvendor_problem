"""CSV data loading and validation for daily demand data."""
import pandas as pd
import numpy as np
from io import StringIO
from datetime import timedelta


class DataFormatError(Exception):
    """Raised when CSV data does not meet format requirements."""
    pass


def template_csv() -> str:
    """
    Return a template CSV string with the required format.

    Returns:
        Example CSV content as a string.
    """
    return """date,actual,forecast
2026-01-01,10,12
2026-01-02,11,13
2026-01-03,12,14
2026-01-04,,15
2026-01-05,,16
"""


def load_daily_csv(file_or_buffer) -> tuple:
    """
    Load and validate a daily demand CSV file.

    Expected format:
      - Columns (exact, lowercase): date, actual, forecast
      - date: ISO YYYY-MM-DD, sorted ascending, no gaps, no duplicates, daily frequency
      - actual: non-negative number or blank (blank only in trailing rows = future window)
      - forecast: non-negative number, always required
      - At least 30 rows with an actual value (history rows)

    Args:
        file_or_buffer: Path, file object, or StringIO buffer

    Returns:
        Tuple (history_df, future_df) where:
          - history_df: Rows with non-blank actual (training data)
          - future_df: Rows with blank actual (forecast-only window)

        Both are DataFrames with columns: date (Timestamp), actual (float), forecast (float).
        For future_df, actual is NaN.

    Raises:
        DataFormatError: If format is invalid.
    """
    try:
        df = pd.read_csv(file_or_buffer)
    except Exception as e:
        raise DataFormatError(f"Failed to read CSV: {e}")

    # Check columns
    required_cols = {"date", "actual", "forecast"}
    actual_cols = set(df.columns)
    if not required_cols.issubset(actual_cols):
        missing = required_cols - actual_cols
        raise DataFormatError(f"Missing columns: {', '.join(missing)}")

    # Keep only required columns
    df = df[["date", "actual", "forecast"]].copy()

    # Parse date
    try:
        df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    except Exception:
        raise DataFormatError("Invalid date format. Use YYYY-MM-DD.")

    # Check date column for each row
    for idx, row in df.iterrows():
        if pd.isna(row["date"]):
            raise DataFormatError(f"Row {idx}: missing or invalid date")

    # Check sorting
    if not df["date"].is_monotonic_increasing:
        raise DataFormatError("Dates must be sorted in ascending order.")

    # Check for duplicates
    if df["date"].duplicated().any():
        dup_date = df.loc[df["date"].duplicated(keep=False), "date"].iloc[0]
        raise DataFormatError(f"Duplicate date: {dup_date}")

    # Check for gaps (every consecutive day required)
    for i in range(1, len(df)):
        expected_date = df.iloc[i - 1]["date"] + timedelta(days=1)
        actual_date = df.iloc[i]["date"]
        if actual_date != expected_date:
            raise DataFormatError(
                f"Gap in dates: missing {expected_date.date()} after {df.iloc[i-1]['date'].date()}"
            )

    # Validate numeric columns before parsing
    for col in ["actual", "forecast"]:
        for idx, val in enumerate(df[col]):
            if pd.isna(val):
                # Blank values are allowed (checked later)
                continue
            try:
                float(val)
            except (ValueError, TypeError):
                raise DataFormatError(
                    f"Row {idx}: {col} must be numeric"
                )

    # Parse numeric columns (handle blanks)
    for col in ["actual", "forecast"]:
        # Convert to numeric, invalid → NaN
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Validate: forecast must never be blank
    forecast_blank = df["forecast"].isna()
    if forecast_blank.any():
        for idx in df[forecast_blank].index:
            raise DataFormatError(
                f"Row {idx}: forecast is blank (required on every row)"
            )

    # Validate: actual must be blank only in trailing rows (after the last non-blank)
    actual_blank = df["actual"].isna()
    if actual_blank.any():
        # Find first and last non-blank actual
        non_blank_indices = df[~actual_blank].index
        if len(non_blank_indices) > 0:
            last_non_blank_idx = non_blank_indices[-1]

            # Check if any blanks exist before the last non-blank
            blanks_in_history = df.loc[:last_non_blank_idx, "actual"].isna()
            if blanks_in_history.any():
                idx = df.loc[:last_non_blank_idx][blanks_in_history].index[0]
                raise DataFormatError(
                    f"Row {idx}: blank actual in the middle of the series (blanks allowed only in trailing rows)"
                )

    # Validate non-negativity
    invalid_actual = (~actual_blank) & (df["actual"] < 0)
    if invalid_actual.any():
        idx = df[invalid_actual].index[0]
        raise DataFormatError(f"Row {idx}: actual must be non-negative")

    invalid_forecast = df["forecast"] < 0
    if invalid_forecast.any():
        idx = df[invalid_forecast].index[0]
        raise DataFormatError(f"Row {idx}: forecast must be non-negative")

    # Split history and future
    history = df[~actual_blank].copy()
    future = df[actual_blank].copy()

    # Check minimum history size
    if len(history) < 30:
        raise DataFormatError(
            f"At least 30 history rows (with actual values) required. Found {len(history)}."
        )

    return history, future
