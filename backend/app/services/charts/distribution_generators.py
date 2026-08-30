"""Distribution chart generators for histograms, pie charts, and stacked charts."""
from typing import Any

import numpy as np
import pandas as pd

# =============================================================================
# Constants for bin configurations
# =============================================================================

# Time column mappings
TIME_COLUMN_MAP = {
    "day": "StartDay",
    "week": "StartYearWeek",
    "month": "StartYearMonth",
    "year": "StartYear",
}

# Histogram bin edges for time-based distributions (in hours)
HISTOGRAM_BIN_EDGES = [0, 1, 4, 12, 24, 72, 168, float('inf')]
HISTOGRAM_BIN_LABELS = ["< 1h", "1h - 4h", "4h - 12h", "12h - 24h", "1d - 3d", "3d - 7d", "> 7d"]

# Job duration stacked chart bins (7 bins with green gradient)
DURATION_BINS = [
    ("< 1h", 0, 1),
    ("1h-4h", 1, 4),
    ("4h-12h", 4, 12),
    ("12h-24h", 12, 24),
    ("1d-3d", 24, 72),
    ("3d-7d", 72, 168),
    ("> 7d", 168, float('inf')),
]
DURATION_COLORS = [
    "#d4edda",  # Very light green
    "#c3e6cb",
    "#a3d5a1",
    "#7bc77e",
    "#52b058",
    "#3d9142",
    "#28a745",  # Dark green
]

# Waiting time stacked chart bins (6 bins with red gradient)
WAITING_TIME_BINS = [
    ("< 30min", 0, 0.5),
    ("30min-1h", 0.5, 1),
    ("1h-4h", 1, 4),
    ("4h-12h", 4, 12),
    ("12h-24h", 12, 24),
    ("> 24h", 24, float('inf')),
]
WAITING_TIME_COLORS = [
    "#ffe5e5",  # Very light red
    "#ffb3b3",
    "#ff8080",
    "#ff4d4d",
    "#ff1a1a",
    "#cc0000",  # Dark red
]


# =============================================================================
# Generic helper functions
# =============================================================================

def _get_time_column(df: pd.DataFrame, period_type: str) -> tuple[pd.DataFrame, str | None]:
    """Get the appropriate time column for the period type, handling year extraction.

    Returns:
        Tuple of (possibly modified DataFrame, time_column name or None if not found)
    """
    time_column = TIME_COLUMN_MAP.get(period_type, "StartYearMonth")

    if time_column not in df.columns:
        if period_type == "year" and "StartYearMonth" in df.columns:
            df_copy = df.copy()
            df_copy["StartYear"] = df_copy["StartYearMonth"].astype(str).str[:4]
            return df_copy, "StartYear"
        return df, None

    return df, time_column


def _generate_stacked_distribution(
    df: pd.DataFrame,
    value_column: str,
    period_type: str,
    bins: list[tuple[str, float, float]],
    colors: list[str],
    bin_column_name: str,
    filter_nulls: bool = False,
    reverse_series: bool = False,
) -> dict[str, Any]:
    """Generic function to create stacked percentage bar charts over time.

    Args:
        df: Input DataFrame
        value_column: Column containing the values to bin
        period_type: Time period (day, week, month, year)
        bins: List of (label, min_value, max_value) tuples
        colors: List of colors corresponding to each bin
        bin_column_name: Name for the temporary bin column
        filter_nulls: Whether to filter out null values
        reverse_series: Whether to reverse the series order

    Returns:
        {"x": time_periods, "series": [{"name": label, "data": percentages, "color": color}, ...]}
    """
    if value_column not in df.columns:
        return {"x": [], "series": []}

    df_work, time_column = _get_time_column(df, period_type)
    if time_column is None:
        return {"x": [], "series": []}

    # Only the two columns take part; copying them is cheap
    df_work = df_work[[time_column, value_column]]
    if filter_nulls:
        df_work = df_work[df_work[value_column].notna()]
        if df_work.empty:
            return {"x": [], "series": []}
    df_work = df_work.copy()

    # Categorize values into bins
    bin_edges = [b[1] for b in bins] + [float('inf')]
    bin_labels = [b[0] for b in bins]

    df_work[bin_column_name] = pd.cut(
        df_work[value_column],
        bins=bin_edges,
        labels=bin_labels,
        right=False,
        include_lowest=True
    )

    # Count per time period and bin
    grouped = df_work.groupby([time_column, bin_column_name], observed=False).size().unstack(fill_value=0)

    if grouped.empty:
        return {"x": [], "series": []}

    # Convert to percentages
    grouped_pct = grouped.div(grouped.sum(axis=1), axis=0) * 100

    # Build series
    time_periods = grouped_pct.index.tolist()
    series = []

    for i, (bin_label, _, _) in enumerate(bins):
        if bin_label in grouped_pct.columns:
            series.append({
                "name": bin_label,
                "data": grouped_pct[bin_label].tolist(),
                "color": colors[i],
            })

    if reverse_series:
        series.reverse()

    return {
        "x": time_periods,
        "series": series,
    }


def _generate_trends(
    df: pd.DataFrame,
    value_column: str,
    period_type: str,
    color_by: str | None,
    stat: str,
    filter_nulls: bool = False,
    filter_positive: bool = False,
) -> dict[str, Any]:
    """Generic function to generate statistical trends over time.

    Args:
        df: Input DataFrame
        value_column: Column to calculate statistics on
        period_type: Time period (day, week, month, year)
        color_by: Optional grouping dimension for multi-line mode
        stat: Statistic to use when color_by is specified (mean, median, max, p25, p50, etc.)
        filter_nulls: Filter out null values
        filter_positive: Filter to only positive values

    Returns:
        Without color_by: {"x": periods, "stats": {"mean": [...], "median": [...], ...}}
        With color_by: {"x": periods, "series": [{"name": group, "data": [...]}, ...]}
    """
    if value_column not in df.columns:
        return {"x": [], "stats": {}}

    df_work, time_column = _get_time_column(df, period_type)
    if time_column is None:
        return {"x": [], "stats": {}}

    # Work on the few columns needed so row filters do not copy the whole frame
    columns = [time_column, value_column] + ([color_by] if color_by and color_by in df_work.columns else [])
    df_work = df_work[columns]

    # Apply filters
    if filter_nulls:
        df_work = df_work[df_work[value_column].notna()]
    if filter_positive:
        df_work = df_work[df_work[value_column] > 0]

    if df_work.empty:
        return {"x": [], "stats": {}}

    all_periods = sorted(df_work[time_column].unique())

    def stat_series(grouped, stat_name: str) -> pd.Series:
        if stat_name == "mean":
            return grouped.mean()
        if stat_name == "max":
            return grouped.max()
        if stat_name.startswith("p"):
            return grouped.quantile(int(stat_name[1:]) / 100.0)
        return grouped.median()

    # Multi-line mode when color_by is specified: one statistic per (group, period)
    if color_by and color_by != "None" and color_by in df_work.columns:
        with_group = df_work[df_work[color_by].notna()]
        groups = sorted(with_group[color_by].unique())
        values = stat_series(with_group.groupby([color_by, time_column])[value_column], stat)
        table = values.unstack(time_column).reindex(index=groups, columns=all_periods).fillna(0.0)
        series = [{"name": str(group), "data": [float(v) for v in table.loc[group]]} for group in groups]
        return {"x": all_periods, "series": series}

    # Single line mode: all statistics per period in one pass
    grouped = df_work.groupby(time_column)[value_column]
    stats_table = pd.DataFrame(
        {
            "mean": grouped.mean(),
            "median": grouped.median(),
            "max": grouped.max(),
            **{f"p{q}": grouped.quantile(q / 100.0) for q in (25, 50, 75, 90, 95, 99)},
        }
    ).reindex(all_periods).fillna(0.0)
    return {
        "x": all_periods,
        "stats": {column: [float(v) for v in stats_table[column]] for column in stats_table.columns},
    }


# =============================================================================
# Public API functions
# =============================================================================

def generate_by_dimension(df: pd.DataFrame, group_by: str | None, metric: str = "count", top_n: int = 10, period_type: str = "month") -> dict[str, list]:
    """Generic aggregation function that groups by a dimension.

    Args:
        df: Input DataFrame
        group_by: Column to group by (Account, Partition, State, QOS, User, or None)
        metric: What to aggregate - 'count' for job counts, 'CPUHours', or 'GPUHours'
        top_n: Number of top groups to return
        period_type: Time period type (day, week, month, year) - used for histogram mode

    Returns:
        When group_by is None: Histogram data {"x": bins, "y": counts, "mean": value, "median": value, "type": "histogram"}
        When group_by is set: Bar chart data {"x": labels, "y": values}
    """
    column_map = {
        "Account": "Account",
        "Partition": "Partition",
        "State": "State",
        "QOS": "QOS",
        "User": "User",
    }

    # If no grouping, behavior depends on metric type
    if not group_by or group_by not in column_map:
        # For CPU/GPU hours: create per-period histogram
        if metric in ["CPUHours", "GPUHours", "MemGBHours"]:
            if metric not in df.columns:
                return {"x": [], "y": [], "mean": 0, "median": 0, "type": "histogram"}

            df_work, time_column = _get_time_column(df, period_type)
            if time_column is None:
                return {"x": [], "y": [], "mean": 0, "median": 0, "type": "histogram"}

            usage_per_period = df_work.groupby(time_column)[metric].sum()

            if len(usage_per_period) == 0:
                return {"x": [], "y": [], "mean": 0, "median": 0, "type": "histogram"}

            mean_val = float(usage_per_period.mean())
            median_val = float(usage_per_period.median())

            n_bins = 20
            counts, bin_edges = np.histogram(usage_per_period, bins=n_bins)
            bin_centers = [(bin_edges[i] + bin_edges[i+1]) / 2 for i in range(len(bin_edges)-1)]

            return {
                "x": bin_centers,
                "y": counts.tolist(),
                "mean": mean_val,
                "median": median_val,
                "type": "histogram",
            }

        # For job counts: create histogram showing distribution of jobs per user
        if "User" not in df.columns:
            return {"x": [], "y": [], "mean": 0, "median": 0}

        jobs_per_user = df["User"].value_counts()

        if len(jobs_per_user) == 0:
            return {"x": [], "y": [], "mean": 0, "median": 0}

        mean_val = float(jobs_per_user.mean())
        median_val = float(jobs_per_user.median())

        n_bins = min(30, max(10, int(np.ceil(np.sqrt(len(jobs_per_user))))))
        counts, bin_edges = np.histogram(jobs_per_user, bins=n_bins)
        bin_labels = [f"{int(bin_edges[i])}-{int(bin_edges[i+1])}" for i in range(len(bin_edges)-1)]
        bin_centers = [(bin_edges[i] + bin_edges[i+1]) / 2 for i in range(len(bin_edges)-1)]

        return {
            "x": bin_centers,
            "y": counts.tolist(),
            "mean": mean_val,
            "median": median_val,
            "bin_labels": bin_labels,
        }

    group_column = column_map.get(group_by, "Account")

    if group_column not in df.columns:
        return {"type": "pie", "labels": [], "values": []}

    if metric == "count":
        all_grouped = df[group_column].value_counts()
    elif metric in ["CPUHours", "GPUHours"]:
        if metric not in df.columns:
            return {"type": "pie", "labels": [], "values": []}
        all_grouped = df.groupby(group_column)[metric].sum().sort_values(ascending=False)
    else:
        return {"type": "pie", "labels": [], "values": []}

    # Get top N
    top_items = all_grouped.head(top_n)

    # Calculate "Others" if there are more items
    others_value = 0
    if len(all_grouped) > top_n:
        others_value = float(all_grouped.iloc[top_n:].sum())

    labels = [str(x) for x in top_items.index.tolist()]
    values = top_items.values.tolist()

    if others_value > 0:
        labels.append(f"Others ({len(all_grouped) - top_n})")
        values.append(others_value)

    return {
        "type": "pie",
        "labels": labels,
        "values": values,
    }


def generate_jobs_by_account(df: pd.DataFrame) -> dict[str, list]:
    """Aggregate jobs by account (top 10)."""
    if "Account" not in df.columns:
        return {"x": [], "y": []}

    counts = df["Account"].value_counts().head(10)
    return {
        "x": counts.index.tolist(),
        "y": counts.values.tolist(),
    }


def generate_jobs_by_partition(df: pd.DataFrame) -> dict[str, list]:
    """Aggregate jobs by partition (top 10)."""
    if "Partition" not in df.columns:
        return {"x": [], "y": []}

    counts = df["Partition"].value_counts().head(10)
    return {
        "x": counts.index.tolist(),
        "y": counts.values.tolist(),
    }


def generate_jobs_by_state(df: pd.DataFrame) -> dict[str, list]:
    """Aggregate jobs by state."""
    if "State" not in df.columns:
        return {"labels": [], "values": []}

    counts = df["State"].value_counts()
    return {
        "labels": counts.index.tolist(),
        "values": counts.values.tolist(),
    }


def _aggregate_value_histogram(
    df: pd.DataFrame,
    value_column: str,
    color_by: str | None = None,
    filter_positive: bool = False,
    top_n: int = 15,
) -> dict[str, Any]:
    """Generic function to create histograms or pie charts for numeric value distributions.

    When color_by is None: Returns histogram with predefined time bins.
    When color_by is set: Returns pie chart showing total hours by group.
    """
    if value_column not in df.columns:
        return {"x": [], "y": [], "median": 0, "average": 0}

    if filter_positive:
        df_work = df[df[value_column] > 0].copy()
    else:
        df_work = df.copy()

    values = df_work[value_column].dropna()

    if values.empty:
        return {"x": [], "y": [], "median": 0, "average": 0}

    median_val = float(values.median())
    mean_val = float(values.mean())

    # Histogram mode when no grouping
    if not color_by or color_by == "None":
        counts, _ = np.histogram(values, bins=HISTOGRAM_BIN_EDGES)
        total = counts.sum()
        percentages = [(count / total * 100) if total > 0 else 0 for count in counts]

        return {
            "type": "histogram",
            "x": HISTOGRAM_BIN_LABELS,
            "y": percentages,
            "median": median_val,
            "average": mean_val,
        }

    # Pie chart mode when grouped
    if color_by not in df_work.columns:
        return {"type": "pie", "labels": [], "values": []}

    # Sum total hours per group
    all_grouped = df_work.groupby(color_by)[value_column].sum().sort_values(ascending=False)

    if all_grouped.empty:
        return {"type": "pie", "labels": [], "values": []}

    # Get top N
    top_items = all_grouped.head(top_n)

    # Calculate "Others" if there are more items
    others_value = 0
    if len(all_grouped) > top_n:
        others_value = float(all_grouped.iloc[top_n:].sum())

    labels = [str(x) for x in top_items.index.tolist()]
    values = top_items.values.tolist()

    if others_value > 0:
        labels.append(f"Others ({len(all_grouped) - top_n})")
        values.append(others_value)

    return {
        "type": "pie",
        "labels": labels,
        "values": values,
        "median": median_val,
        "average": mean_val,
    }


def generate_waiting_times_hist(df: pd.DataFrame, color_by: str | None = None) -> dict[str, Any]:
    """Aggregate waiting times into histogram bins with numeric x-axis."""
    return _aggregate_value_histogram(df, "WaitingTimeHours", color_by, filter_positive=False)


def generate_job_duration_hist(df: pd.DataFrame, color_by: str | None = None) -> dict[str, Any]:
    """Aggregate job durations into histogram bins with numeric x-axis."""
    return _aggregate_value_histogram(df, "ElapsedHours", color_by, filter_positive=True)


def _aggregate_period_distribution(
    df: pd.DataFrame,
    period_type: str,
    color_by: str | None,
    agg_func,
    metric_name: str,
    allowed_pie_dimensions: list[str] | None = None
) -> dict[str, Any]:
    """Generic function to create distribution histograms for period-based metrics."""
    if df.empty:
        return {"type": "empty", "x": [], "y": []}

    if color_by and color_by in df.columns:
        grouped = agg_func(df, color_by)

        if grouped.empty:
            return {"type": "empty", "x": [], "y": []}

        grouped_sorted = grouped.sort_values(ascending=False)

        return {
            "x": [str(x) for x in grouped_sorted.index.tolist()],
            "y": grouped_sorted.values.tolist(),
        }

    df_work, time_column = _get_time_column(df, period_type)
    if time_column is None:
        return {"type": "empty", "x": [], "y": []}

    values_per_period = agg_func(df_work, time_column)

    if values_per_period.empty:
        return {"type": "empty", "x": [], "y": []}

    values = values_per_period.values
    num_bins = min(20, max(5, len(values)))

    counts, bin_edges = np.histogram(values, bins=num_bins)
    bin_centers = [(bin_edges[i] + bin_edges[i+1]) / 2 for i in range(len(bin_edges)-1)]

    avg_value = float(values.mean())
    median_value = float(np.median(values))

    return {
        "type": "histogram",
        "x": bin_centers,
        "y": counts.tolist(),
        "average": avg_value,
        "median": median_value,
    }


def generate_active_users_distribution(df: pd.DataFrame, period_type: str = "month", color_by: str | None = None) -> dict[str, Any]:
    """Aggregate active users distribution.

    Shows histogram of how many unique users were active per period.
    Valid color_by options:
    - Account: shows unique users per account
    - User: shows most active users (periods active per user)
    Partition/QoS are ignored since users span multiple partitions/QoS.
    """
    if "User" not in df.columns:
        return {"type": "empty", "x": [], "y": []}

    # Only Account and User make sense for user distribution
    effective_color_by = color_by if color_by in ("Account", "User") else None

    # For "User" mode: count periods each user was active (most active users)
    if effective_color_by == "User":
        df_work, time_column = _get_time_column(df, period_type)
        if time_column is None:
            return {"type": "empty", "x": [], "y": []}

        # Count unique periods per user
        periods_per_user = df_work.groupby("User")[time_column].nunique().sort_values(ascending=False)

        if periods_per_user.empty:
            return {"type": "empty", "x": [], "y": []}

        # Return top 15 users
        top_users = periods_per_user.head(15)
        labels = [str(x) for x in top_users.index.tolist()]
        values = top_users.values.tolist()

        # Add "Others" if more users exist
        if len(periods_per_user) > 15:
            others_count = int(periods_per_user.iloc[15:].sum())
            labels.append(f"Others ({len(periods_per_user) - 15})")
            values.append(others_count)

        return {
            "type": "pie",
            "labels": labels,
            "values": values,
        }

    # For "Account" mode: count unique users per account
    if effective_color_by == "Account":
        users_per_account = df.groupby("Account")["User"].nunique().sort_values(ascending=False)

        if users_per_account.empty:
            return {"type": "empty", "x": [], "y": []}

        top_accounts = users_per_account.head(15)
        labels = [str(x) for x in top_accounts.index.tolist()]
        values = top_accounts.values.tolist()

        if len(users_per_account) > 15:
            others_count = int(users_per_account.iloc[15:].sum())
            labels.append(f"Others ({len(users_per_account) - 15})")
            values.append(others_count)

        return {
            "type": "pie",
            "labels": labels,
            "values": values,
        }

    # Default: histogram of users per period
    def agg_unique_users(data, group_col):
        return data.groupby(group_col)["User"].nunique()

    return _aggregate_period_distribution(
        df=df,
        period_type=period_type,
        color_by=None,
        agg_func=agg_unique_users,
        metric_name="Active users",
        allowed_pie_dimensions=[]
    )


def generate_jobs_distribution(df: pd.DataFrame, period_type: str = "month", color_by: str | None = None, top_n: int = 15) -> dict[str, Any]:
    """Aggregate jobs distribution.

    When color_by is set to a valid dimension:
        Shows pie chart of jobs grouped by that dimension.

    When color_by is None:
        Shows histogram of jobs per period distribution.

    Args:
        df: Input DataFrame
        period_type: Time period for histogram mode
        color_by: Dimension to group by (User, Account, Partition, State, QOS)
        top_n: Number of top items to show in pie chart

    Returns:
        Pie chart or histogram data
    """
    if df.empty:
        return {"type": "histogram", "x": [], "y": []}

    # Pie chart mode for grouping dimensions
    pie_chart_dimensions = ["User", "Account", "Partition", "State", "QOS"]

    if color_by in pie_chart_dimensions and color_by in df.columns:
        # Count jobs per group
        job_counts = df.groupby(color_by).size().sort_values(ascending=False)

        top_items = job_counts.head(top_n)

        # Calculate "Others" if there are more items
        others_count = 0
        if len(job_counts) > top_n:
            others_count = int(job_counts.iloc[top_n:].sum())

        labels = [str(x) for x in top_items.index.tolist()]
        values = top_items.values.tolist()

        if others_count > 0:
            labels.append(f"Others ({len(job_counts) - top_n})")
            values.append(others_count)

        return {
            "type": "pie",
            "labels": labels,
            "values": values,
        }

    # Histogram mode (default) - jobs per period distribution
    def agg_job_count(data, group_col):
        return data.groupby(group_col).size()

    return _aggregate_period_distribution(
        df=df,
        period_type=period_type,
        color_by=None,  # Always histogram when no meaningful grouping
        agg_func=agg_job_count,
        metric_name="Jobs",
        allowed_pie_dimensions=None
    )


def generate_job_duration_stacked(df: pd.DataFrame, period_type: str = "month") -> dict[str, Any]:
    """Aggregate job duration distribution as stacked percentage bar chart over time."""
    return _generate_stacked_distribution(
        df=df,
        value_column="ElapsedHours",
        period_type=period_type,
        bins=DURATION_BINS,
        colors=DURATION_COLORS,
        bin_column_name="DurationBin",
        filter_nulls=False,
        reverse_series=True,  # Long duration jobs at bottom
    )


def generate_waiting_times_stacked(df: pd.DataFrame, period_type: str = "month") -> dict[str, Any]:
    """Aggregate waiting time distribution as stacked percentage bar chart over time."""
    return _generate_stacked_distribution(
        df=df,
        value_column="WaitingTimeHours",
        period_type=period_type,
        bins=WAITING_TIME_BINS,
        colors=WAITING_TIME_COLORS,
        bin_column_name="WaitingBin",
        filter_nulls=True,
        reverse_series=True,  # Dark red (>24h) at bottom
    )


def generate_waiting_times_trends(df: pd.DataFrame, period_type: str = "month", color_by: str | None = None, stat: str = "median") -> dict[str, Any]:
    """Aggregate waiting time statistics (mean, median, max, percentiles) by time period."""
    return _generate_trends(
        df=df,
        value_column="WaitingTimeHours",
        period_type=period_type,
        color_by=color_by,
        stat=stat,
        filter_nulls=True,
        filter_positive=False,
    )


def generate_job_duration_trends(df: pd.DataFrame, period_type: str = "month", color_by: str | None = None, stat: str = "median") -> dict[str, Any]:
    """Aggregate job duration statistics (mean, median, max, percentiles) by time period."""
    return _generate_trends(
        df=df,
        value_column="ElapsedHours",
        period_type=period_type,
        color_by=color_by,
        stat=stat,
        filter_nulls=True,
        filter_positive=True,
    )


def generate_cpus_per_job(df: pd.DataFrame) -> dict[str, list]:
    """Aggregate CPUs per job distribution."""
    cpu_col = "AllocCPUS" if "AllocCPUS" in df.columns else "CPUs"
    if cpu_col not in df.columns:
        return {"x": [], "y": []}

    counts = df[cpu_col].value_counts().sort_index().head(20)
    return {
        "x": counts.index.tolist(),
        "y": counts.values.tolist(),
    }


def generate_gpus_per_job(df: pd.DataFrame) -> dict[str, list]:
    """Aggregate GPUs per job distribution (only jobs with GPUs, limited to 20 bins)."""
    gpu_col = "AllocGPUS" if "AllocGPUS" in df.columns else "GPUs"
    if gpu_col not in df.columns:
        return {"x": [], "y": []}

    gpu_jobs = df[df[gpu_col] > 0]
    if gpu_jobs.empty:
        return {"x": [], "y": []}

    counts = gpu_jobs[gpu_col].value_counts().sort_index().head(20)
    return {
        "x": counts.index.tolist(),
        "y": counts.values.tolist(),
    }


def generate_nodes_per_job(df: pd.DataFrame) -> dict[str, list]:
    """Aggregate nodes per job distribution."""
    node_col = "AllocNodes" if "AllocNodes" in df.columns else "Nodes"
    if node_col not in df.columns:
        return {"x": [], "y": []}

    node_jobs = df[df[node_col] > 0]
    if node_jobs.empty:
        return {"x": [], "y": []}

    counts = node_jobs[node_col].value_counts().sort_index().head(20)
    return {
        "x": counts.index.tolist(),
        "y": counts.values.tolist(),
    }


def generate_cpu_hours_by_account(df: pd.DataFrame) -> dict[str, list]:
    """Aggregate CPU hours by account (top 10)."""
    if "Account" not in df.columns or "CPUHours" not in df.columns:
        return {"x": [], "y": []}

    totals = df.groupby("Account")["CPUHours"].sum().sort_values(ascending=False).head(10)
    return {
        "x": totals.index.tolist(),
        "y": totals.values.tolist(),
    }


def generate_gpu_hours_by_account(df: pd.DataFrame) -> dict[str, list]:
    """Aggregate GPU hours by account (top 10)."""
    if "Account" not in df.columns or "GPUHours" not in df.columns:
        return {"x": [], "y": []}

    gpu_df = df[df["GPUHours"] > 0]
    if gpu_df.empty:
        return {"x": [], "y": []}

    totals = gpu_df.groupby("Account")["GPUHours"].sum().sort_values(ascending=False).head(10)
    return {
        "x": totals.index.tolist(),
        "y": totals.values.tolist(),
    }


def generate_user_activity_frequency(
    df: pd.DataFrame,
    period_type: str = "day",
    color_by: str | None = None,
    top_n: int = 15,
) -> dict[str, Any]:
    """Generate distribution of user activity frequency.

    When color_by is None or not "User":
        Shows histogram of how many users were active on N days/weeks/months.
        E.g., "50 users were active on 1-5 days, 30 users on 6-10 days, etc."

    When color_by="User":
        Shows pie chart of top N most active users by number of active periods.

    Args:
        df: Input DataFrame with job data
        period_type: Time granularity for counting activity (day, week, month)
        color_by: Optional grouping dimension - "User" triggers pie chart mode
        top_n: Number of top users to show in pie chart mode

    Returns:
        Histogram or pie chart data depending on color_by
    """
    if df.empty or "User" not in df.columns:
        return {"type": "histogram", "x": [], "y": [], "bin_labels": []}

    # Get appropriate time column based on period type
    # Use Submit-based columns for user activity (when they submitted jobs)
    submit_time_column_map = {
        "day": "SubmitDay",
        "week": "SubmitYearWeek",
        "month": "SubmitYearMonth",
        "year": "SubmitYear",
    }
    time_column = submit_time_column_map.get(period_type, "SubmitDay")

    if time_column not in df.columns:
        # Fallback to Start-based columns
        time_column = TIME_COLUMN_MAP.get(period_type, "StartDay")
        if time_column not in df.columns:
            return {"type": "histogram", "x": [], "y": [], "bin_labels": []}

    # Count unique periods per user
    user_period_counts = df.groupby("User")[time_column].nunique()

    if user_period_counts.empty:
        return {"type": "histogram", "x": [], "y": [], "bin_labels": []}

    # Period label for display
    period_label = {
        "day": "days",
        "week": "weeks",
        "month": "months",
        "year": "years",
    }.get(period_type, "periods")

    total_periods = df[time_column].nunique()
    total_users = len(user_period_counts)

    # Pie chart mode for meaningful groupings
    pie_chart_dimensions = ["User", "Account", "Partition", "QOS"]

    if color_by in pie_chart_dimensions:
        if color_by == "User":
            # Show top users by activity (days/weeks active)
            top_items = user_period_counts.sort_values(ascending=False).head(top_n)
            others_label = "Others ({} users)"
        else:
            # For Account/Partition/QOS: sum user-periods per group
            # This shows which groups have the most user-activity
            if color_by not in df.columns:
                # Fall through to histogram if column doesn't exist
                pass
            else:
                # Count user-periods per group (sum of active periods across all users in group)
                group_activity = df.groupby(color_by).apply(
                    lambda g: g.groupby("User")[time_column].nunique().sum()
                ).sort_values(ascending=False)

                top_items = group_activity.head(top_n)
                others_label = "Others ({} " + color_by.lower() + "s)"

        if color_by == "User" or (color_by in df.columns):
            # Calculate "Others" if there are more items
            all_items = user_period_counts if color_by == "User" else group_activity
            others_count = 0
            if len(all_items) > top_n:
                others_count = int(all_items.sort_values(ascending=False).iloc[top_n:].sum())

            labels = [str(x) for x in top_items.index.tolist()]
            values = top_items.values.tolist()

            if others_count > 0:
                labels.append(others_label.format(len(all_items) - top_n))
                values.append(others_count)

            return {
                "type": "pie",
                "labels": labels,
                "values": values,
                "total_periods": total_periods,
                "total_users": total_users,
                "period_label": period_label,
            }

    # Histogram mode (default)
    max_periods = int(user_period_counts.max())

    # Create appropriate bins based on the range
    if max_periods <= 10:
        # Small range: use 1-period bins
        bins = list(range(1, max_periods + 2))
        bin_labels = [str(i) for i in range(1, max_periods + 1)]
    elif max_periods <= 30:
        # Medium range: use 5-period bins
        bins = list(range(1, max_periods + 6, 5))
        bins[-1] = max_periods + 1  # Ensure last bin captures all
        bin_labels = [f"{bins[i]}-{bins[i+1]-1}" for i in range(len(bins)-1)]
    else:
        # Large range: use 10-period bins
        bins = list(range(1, max_periods + 11, 10))
        bins[-1] = max_periods + 1
        bin_labels = [f"{bins[i]}-{bins[i+1]-1}" for i in range(len(bins)-1)]

    # Create histogram
    counts, _ = np.histogram(user_period_counts.values, bins=bins)

    # Calculate statistics
    avg_periods = float(user_period_counts.mean())
    median_periods = float(user_period_counts.median())

    return {
        "type": "histogram",
        "x": bin_labels,
        "y": counts.tolist(),
        "average": avg_periods,
        "median": median_periods,
        "total_periods": total_periods,
        "total_users": total_users,
        "period_label": period_label,
    }
