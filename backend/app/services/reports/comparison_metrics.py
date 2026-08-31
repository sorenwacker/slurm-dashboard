"""Previous period comparison calculations."""

from typing import Any

import pandas as pd

from ...api.dashboard import get_datastore
from .report_formatters import convert_numpy_to_native


def calculate_previous_period_dates(
    start_date: str,
    end_date: str,
    report_type: str,
) -> tuple[str, str] | None:
    """Calculate the previous period dates based on report type."""
    try:
        start_dt = pd.Timestamp(start_date)
        end_dt = pd.Timestamp(end_date)

        # Determine period length
        period_length = (end_dt - start_dt).days + 1

        # Calculate previous period by going back the same number of days
        prev_end_dt = start_dt - pd.Timedelta(days=1)
        prev_start_dt = prev_end_dt - pd.Timedelta(days=period_length - 1)

        return prev_start_dt.strftime("%Y-%m-%d"), prev_end_dt.strftime("%Y-%m-%d")
    except Exception:
        return None


def calculate_comparison_metrics(
    hostname: str,
    start_date: str,
    end_date: str,
    current_summary: dict[str, Any],
    report_type: str,
) -> dict[str, Any] | None:
    """Calculate comparison metrics with the previous period."""
    # Get previous period dates
    prev_dates = calculate_previous_period_dates(start_date, end_date, "")
    if not prev_dates:
        return None

    prev_start, prev_end = prev_dates

    # Query previous period data
    datastore = get_datastore()
    prev_df = datastore.filter(
        hostname=hostname,
        start_date=prev_start,
        end_date=prev_end,
    )

    if prev_df.empty:
        return None

    # Calculate previous period metrics
    prev_total_jobs = len(prev_df)
    prev_total_cpu_hours = float(prev_df["CPUHours"].sum()) if "CPUHours" in prev_df.columns else 0.0
    prev_total_gpu_hours = float(prev_df["GPUHours"].sum()) if "GPUHours" in prev_df.columns else 0.0
    prev_total_users = int(prev_df["User"].nunique()) if "User" in prev_df.columns else 0

    # Calculate percentage changes
    def calc_change_percent(current: float, previous: float) -> float:
        if previous > 0:
            return ((current - previous) / previous) * 100
        if current > 0:
            return 100.0  # If previous was 0 and current is positive, 100% increase
        return 0.0

    jobs_change = calc_change_percent(
        current_summary["total_jobs"],
        prev_total_jobs
    )
    cpu_change = calc_change_percent(
        current_summary["total_cpu_hours"],
        prev_total_cpu_hours
    )
    gpu_change = calc_change_percent(
        current_summary["total_gpu_hours"],
        prev_total_gpu_hours
    )
    users_change = calc_change_percent(
        current_summary["total_users"],
        prev_total_users
    )

    # Generate previous period timeline with same aggregation as current period
    prev_timeline = []

    # Determine which time column to use based on report type
    if "Annual" in report_type:
        time_column = "StartYearMonth"
    elif "Quarterly" in report_type:
        time_column = "StartYearWeek"
    else:
        time_column = "SubmitDay"

    if time_column in prev_df.columns:
        prev_timeline_stats = (
            prev_df.groupby(time_column)
            .agg(
                jobs=(time_column, "size"),
                cpu_hours=("CPUHours", "sum"),
                gpu_hours=("GPUHours", "sum"),
                users=("User", "nunique"),
            )
            .reset_index()
        )
        prev_timeline_stats.columns = ["date", "jobs", "cpu_hours", "gpu_hours", "users"]

        # For week and month aggregations, convert datetime to string for JSON serialization
        if time_column in ["StartYearWeek", "StartYearMonth"]:
            prev_timeline_stats["date"] = pd.to_datetime(prev_timeline_stats["date"]).dt.strftime("%Y-%m-%d")

        prev_timeline = convert_numpy_to_native(prev_timeline_stats.to_dict(orient="records"))

    return {
        "previous_period_start": prev_start,
        "previous_period_end": prev_end,
        "jobs_change_percent": round(jobs_change, 1),
        "cpu_hours_change_percent": round(cpu_change, 1),
        "gpu_hours_change_percent": round(gpu_change, 1),
        "users_change_percent": round(users_change, 1),
        "previous_timeline": prev_timeline,
    }
