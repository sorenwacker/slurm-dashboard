"""Helper functions for date calculations and statistics."""

from typing import Any

import pandas as pd


def get_month_date_range(year: int, month: int) -> tuple[str, str]:
    """Get the start and end date for a given month."""
    start_date = f"{year}-{month:02d}-01"

    # Calculate last day of month
    if month == 12:
        end_year = year + 1
        end_month = 1
    else:
        end_year = year
        end_month = month + 1

    # Use first day of next month and subtract 1 day
    next_month_start = pd.Timestamp(f"{end_year}-{end_month:02d}-01")
    end_date = (next_month_start - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    return start_date, end_date


def get_year_date_range(year: int) -> tuple[str, str]:
    """Get the start and end date for a given year."""
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    return start_date, end_date


def get_quarter_date_range(year: int, quarter: int) -> tuple[str, str]:
    """Get the start and end date for a given quarter (Q1-Q4)."""
    if not 1 <= quarter <= 4:
        msg = f"Quarter must be between 1 and 4, got {quarter}"
        raise ValueError(msg)

    # Define quarter start months
    quarter_start_months = {1: 1, 2: 4, 3: 7, 4: 10}
    start_month = quarter_start_months[quarter]

    # Calculate end month
    if quarter == 4:
        end_month = 12
        end_year = year
    else:
        end_month = start_month + 2
        end_year = year

    start_date = f"{year}-{start_month:02d}-01"

    # Calculate last day of the quarter's final month
    if end_month == 12:
        next_month_start = pd.Timestamp(f"{end_year + 1}-01-01")
    else:
        next_month_start = pd.Timestamp(f"{end_year}-{end_month + 1:02d}-01")

    end_date = (next_month_start - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    return start_date, end_date


def _empty_stats() -> dict[str, float]:
    """Return empty statistics dictionary."""
    return {
        "mean": 0.0,
        "median": 0.0,
        "p25": 0.0,
        "p75": 0.0,
        "p90": 0.0,
        "min": 0.0,
        "max": 0.0,
    }


def calculate_column_stats(df: pd.DataFrame, column: str) -> dict[str, Any]:
    """Calculate statistics for a numeric column.

    Args:
        df: Input DataFrame
        column: Name of the column to calculate statistics for

    Returns:
        Dictionary with mean, median, p25, p75, p90, min, max values
    """
    if df.empty or column not in df.columns:
        return _empty_stats()

    values = df[column].dropna()
    if len(values) == 0:
        return _empty_stats()

    return {
        "mean": float(values.mean()),
        "median": float(values.median()),
        "p25": float(values.quantile(0.25)),
        "p75": float(values.quantile(0.75)),
        "p90": float(values.quantile(0.90)),
        "min": float(values.min()),
        "max": float(values.max()),
    }


def calculate_duration_stats(df: pd.DataFrame) -> dict[str, Any]:
    """Calculate job duration statistics in hours."""
    return calculate_column_stats(df, "JobDuration")


def calculate_waiting_time_stats(df: pd.DataFrame) -> dict[str, Any]:
    """Calculate waiting time statistics in hours."""
    return calculate_column_stats(df, "WaitingTime")
