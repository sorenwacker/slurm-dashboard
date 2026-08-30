"""Timeline chart generators for CPU, GPU, jobs, and users over time."""
import logging
from typing import Any, Literal

import pandas as pd

logger = logging.getLogger(__name__)

# Time column mappings for different time bases
TIME_COLUMN_MAP_START = {
    "day": "StartDay",
    "week": "StartYearWeek",
    "month": "StartYearMonth",
    "year": "StartYear",
}

TIME_COLUMN_MAP_SUBMIT = {
    "day": "SubmitDay",
    "week": "SubmitYearWeek",
    "month": "SubmitYearMonth",
    "year": "SubmitYear",
}


def _generate_timeline(
    df: pd.DataFrame,
    value_column: str | None,
    period_type: str,
    color_by: str | None,
    time_base: Literal["start", "submit"],
    aggregation: Literal["sum", "mean", "nunique", "count"],
    filter_nulls: bool = False,
    filter_positive: bool = False,
    normalize_weeks: bool = False,
) -> dict[str, Any]:
    """Generic timeline aggregation function.

    Args:
        df: Input DataFrame
        value_column: Column to aggregate (None for count aggregation)
        period_type: Time period (day, week, month, year)
        color_by: Optional dimension to group by (Account, Partition, State, QOS, User)
        time_base: Use "start" or "submit" time columns
        aggregation: Aggregation method (sum, mean, nunique, count)
        filter_nulls: Filter out null values in value_column before aggregation
        filter_positive: Filter to only positive values in value_column
        normalize_weeks: Normalize week timestamps to Monday 00:00:00

    Returns:
        Without color_by: {"x": [...], "y": [...]}
        With color_by: {"x": [...], "series": [{"name": "group", "data": [...]}, ...]}
    """
    # Check required column exists (except for count aggregation)
    if value_column and value_column not in df.columns:
        return {"x": [], "y": []}

    # Select time column based on period type and time base
    time_column_map = TIME_COLUMN_MAP_START if time_base == "start" else TIME_COLUMN_MAP_SUBMIT
    fallback_month_col = "StartYearMonth" if time_base == "start" else "SubmitYearMonth"
    fallback_year_col = "StartYear" if time_base == "start" else "SubmitYear"

    time_column = time_column_map.get(period_type, fallback_month_col.replace("YearMonth", "YearMonth"))

    # Handle year extraction if needed
    df_copy = df
    if time_column not in df.columns:
        if period_type == "year" and fallback_month_col in df.columns:
            df_copy = df.copy()
            df_copy[fallback_year_col] = df_copy[fallback_month_col].astype(str).str[:4]
        else:
            logger.warning(f"Time column '{time_column}' not found in DataFrame. Available columns: {df.columns.tolist()}")
            return {"x": [], "y": []}

    # Keep only the columns this chart aggregates so the filters below copy little
    needed = [time_column] + [c for c in (value_column, color_by) if c and c in df_copy.columns and c != time_column]
    df_copy = df_copy[needed].copy()

    # Normalize week timestamps to Monday 00:00:00 if needed
    if normalize_weeks and period_type == "week" and time_column in df_copy.columns:
        df_copy = df_copy.copy() if df_copy is df else df_copy
        df_copy[time_column] = pd.to_datetime(df_copy[time_column])
        df_copy[time_column] = df_copy[time_column].dt.to_period('W-MON').dt.start_time

    # Apply filters if needed
    if filter_nulls and value_column:
        df_copy = df_copy[df_copy[value_column].notna()].copy() if df_copy is df else df_copy[df_copy[value_column].notna()]
        if df_copy.empty:
            return {"x": [], "y": []}

    if filter_positive and value_column:
        df_copy = df_copy[df_copy[value_column] > 0].copy() if df_copy is df else df_copy[df_copy[value_column] > 0]
        if df_copy.empty:
            return {"x": [], "y": []}

    # Define aggregation functions
    def aggregate_simple(data: pd.DataFrame, group_col: str) -> pd.Series:
        if aggregation == "sum":
            return data.groupby(group_col)[value_column].sum()
        if aggregation == "mean":
            return data.groupby(group_col)[value_column].mean()
        if aggregation == "nunique":
            return data.groupby(group_col)[value_column].nunique()
        if aggregation == "count":
            return data[group_col].value_counts()
        raise ValueError(f"Unknown aggregation: {aggregation}")

    # If no color_by, return simple time series
    if not color_by or color_by not in df_copy.columns:
        grouped = aggregate_simple(df_copy, time_column).sort_index()
        return {
            "x": grouped.index.tolist(),
            "y": grouped.values.tolist(),
        }

    # With color_by, return multi-series data for stacked chart
    if aggregation == "count":
        grouped = df_copy.groupby([time_column, color_by]).size().reset_index(name="_agg_value")
        agg_col = "_agg_value"
    elif aggregation == "nunique":
        grouped = df_copy.groupby([time_column, color_by])[value_column].nunique().reset_index(name="_agg_value")
        agg_col = "_agg_value"
    else:
        agg_func = "sum" if aggregation == "sum" else "mean"
        grouped = df_copy.groupby([time_column, color_by])[value_column].agg(agg_func).reset_index()
        agg_col = value_column

    # Get all groups sorted by total/average value
    if aggregation == "nunique":
        # For unique counts, count total unique per group across all time
        all_groups = []
        for group in df_copy[color_by].unique():
            group_value = df_copy[df_copy[color_by] == group][value_column].nunique()
            all_groups.append((group, group_value))
        all_groups = sorted(all_groups, key=lambda x: x[1], reverse=True)
        all_groups = [g[0] for g in all_groups]
    else:
        sort_agg = "sum" if aggregation in ("sum", "count") else "mean"
        all_groups = grouped.groupby(color_by)[agg_col].agg(sort_agg).sort_values(ascending=False).index.tolist()

    # One pivot instead of one DataFrame filter per (group, period) cell
    all_periods = sorted(df_copy[time_column].unique())
    table = (
        grouped.pivot_table(index=color_by, columns=time_column, values=agg_col, aggfunc="sum", fill_value=0)
        .reindex(index=all_groups, columns=all_periods)
        .fillna(0)
    )
    integer_valued = aggregation in ("count", "nunique")
    series = [
        {
            "name": str(group),
            "data": [int(v) if integer_valued else float(v) for v in table.loc[group]],
        }
        for group in all_groups
    ]

    return {
        "x": all_periods,
        "series": series,
    }


# Public API functions - maintain backward compatibility

def generate_cpu_usage_over_time(
    df: pd.DataFrame,
    period_type: str = "month",
    color_by: str | None = None
) -> dict[str, list]:
    """Aggregate CPU usage by time period, optionally grouped by a dimension.

    Args:
        df: Input DataFrame
        period_type: Time period (day, week, month, year)
        color_by: Optional dimension to group by (Account, Partition, State, QOS, User)

    Returns:
        Without color_by: {"x": [...], "y": [...]}
        With color_by: {"x": [...], "series": [{"name": "group", "data": [...]}, ...]}
    """
    return _generate_timeline(
        df=df,
        value_column="CPUHours",
        period_type=period_type,
        color_by=color_by,
        time_base="start",
        aggregation="sum",
        normalize_weeks=True,
    )


def generate_gpu_usage_over_time(
    df: pd.DataFrame,
    period_type: str = "month",
    color_by: str | None = None
) -> dict[str, list]:
    """Aggregate GPU usage by time period, optionally grouped by a dimension.

    Args:
        df: Input DataFrame
        period_type: Time period (day, week, month, year)
        color_by: Optional dimension to group by (Account, Partition, State, QOS, User)

    Returns:
        Without color_by: {"x": [...], "y": [...]}
        With color_by: {"x": [...], "series": [{"name": "group", "data": [...]}, ...]}
    """
    return _generate_timeline(
        df=df,
        value_column="GPUHours",
        period_type=period_type,
        color_by=color_by,
        time_base="start",
        aggregation="sum",
        normalize_weeks=True,
    )


def generate_active_users_over_time(
    df: pd.DataFrame,
    period_type: str = "month",
    color_by: str | None = None
) -> dict[str, list]:
    """Aggregate active users by time period, optionally grouped by account.

    Args:
        df: Input DataFrame
        period_type: Time period (day, week, month, year)
        color_by: Optional dimension to group by. Only "Account" is valid for
                  user counts. Other dimensions are ignored because a user can
                  use multiple partitions/QoS, making those groupings meaningless.

    Returns:
        Without color_by: {"x": [...], "y": [...]}
        With color_by: {"x": [...], "series": [{"name": "group", "data": [...]}, ...]}
    """
    # Only Account makes sense for user grouping - users can span partitions/QoS
    effective_color_by = color_by if color_by == "Account" else None

    return _generate_timeline(
        df=df,
        value_column="User",
        period_type=period_type,
        color_by=effective_color_by,
        time_base="submit",
        aggregation="nunique",
    )


def generate_jobs_over_time(
    df: pd.DataFrame,
    period_type: str = "month",
    color_by: str | None = None
) -> dict[str, list]:
    """Aggregate job counts by time period, optionally grouped by a dimension.

    Args:
        df: Input DataFrame
        period_type: Time period (day, week, month, year)
        color_by: Optional dimension to group by (Account, Partition, State, QOS, User)

    Returns:
        Without color_by: {"x": [...], "y": [...]}
        With color_by: {"x": [...], "series": [{"name": "group", "data": [...]}, ...]}
    """
    return _generate_timeline(
        df=df,
        value_column=None,
        period_type=period_type,
        color_by=color_by,
        time_base="submit",
        aggregation="count",
    )


def generate_waiting_times_over_time(
    df: pd.DataFrame,
    period_type: str = "month",
    color_by: str | None = None
) -> dict[str, list]:
    """Aggregate average waiting times by time period, optionally grouped by a dimension.

    Args:
        df: Input DataFrame
        period_type: Time period (day, week, month, year)
        color_by: Optional dimension to group by (Account, Partition, State, QOS, User)

    Returns:
        Without color_by: {"x": [...], "y": [...]}
        With color_by: {"x": [...], "series": [{"name": "group", "data": [...]}, ...]}
    """
    return _generate_timeline(
        df=df,
        value_column="WaitingTimeHours",
        period_type=period_type,
        color_by=color_by,
        time_base="submit",
        aggregation="mean",
        filter_nulls=True,
    )


def generate_job_duration_over_time(
    df: pd.DataFrame,
    period_type: str = "month",
    color_by: str | None = None
) -> dict[str, list]:
    """Aggregate average job duration by time period, optionally grouped by a dimension.

    Args:
        df: Input DataFrame
        period_type: Time period (day, week, month, year)
        color_by: Optional dimension to group by (Account, Partition, State, QOS, User)

    Returns:
        Without color_by: {"x": [...], "y": [...]}
        With color_by: {"x": [...], "series": [{"name": "group", "data": [...]}, ...]}
    """
    return _generate_timeline(
        df=df,
        value_column="ElapsedHours",
        period_type=period_type,
        color_by=color_by,
        time_base="submit",
        aggregation="mean",
        filter_nulls=True,
        filter_positive=True,
    )
