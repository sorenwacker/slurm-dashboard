"""Main report generation logic."""

from datetime import datetime
from typing import Any

import pandas as pd

from ...api.dashboard import get_datastore
from .comparison_metrics import calculate_comparison_metrics
from .report_formatters import convert_numpy_to_native
from .report_helpers import calculate_duration_stats, calculate_waiting_time_stats


def generate_report_data(
    hostname: str,
    start_date: str,
    end_date: str,
    report_type: str,
) -> dict[str, Any]:
    """Generate aggregated report data for the specified period."""
    datastore = get_datastore()

    # Filter data for the period
    df = datastore.filter(
        hostname=hostname,
        start_date=start_date,
        end_date=end_date,
    )

    if df.empty:
        return {
            "report_type": report_type,
            "hostname": hostname,
            "period": {
                "start_date": start_date,
                "end_date": end_date,
            },
            "summary": {
                "total_jobs": 0,
                "total_cpu_hours": 0.0,
                "total_gpu_hours": 0.0,
                "total_users": 0,
                "avg_job_duration_hours": 0.0,
                "median_job_duration_hours": 0.0,
                "avg_waiting_time_hours": 0.0,
                "median_waiting_time_hours": 0.0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "success_rate": 0.0,
            },
            "job_duration_stats": {},
            "waiting_time_stats": {},
            "by_account": [],
            "by_user": [],
            "by_partition": [],
            "by_state": [],
            "timeline": [],
            "comparison": None,
        }

    # Calculate job duration and waiting time statistics
    duration_stats = calculate_duration_stats(df)
    waiting_stats = calculate_waiting_time_stats(df)

    # Job state statistics
    completed_jobs = len(df[df["State"] == "COMPLETED"]) if "State" in df.columns else 0
    failed_jobs = len(df[df["State"].isin(["FAILED", "TIMEOUT", "CANCELLED"])]) if "State" in df.columns else 0
    total_finished = completed_jobs + failed_jobs
    success_rate = (completed_jobs / total_finished * 100) if total_finished > 0 else 0.0

    # Summary statistics
    summary = {
        "total_jobs": len(df),
        "total_cpu_hours": float(df["CPUHours"].sum()) if "CPUHours" in df.columns else 0.0,
        "total_gpu_hours": float(df["GPUHours"].sum()) if "GPUHours" in df.columns else 0.0,
        "total_users": int(df["User"].nunique()) if "User" in df.columns else 0,
        "avg_job_duration_hours": duration_stats["mean"],
        "median_job_duration_hours": duration_stats["median"],
        "avg_waiting_time_hours": waiting_stats["mean"],
        "median_waiting_time_hours": waiting_stats["median"],
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "success_rate": success_rate,
    }

    # Aggregation by account
    by_account = []
    if "Account" in df.columns:
        account_stats = (
            df.groupby("Account")
            .agg(
                jobs=("Account", "size"),
                cpu_hours=("CPUHours", "sum"),
                gpu_hours=("GPUHours", "sum"),
                users=("User", "nunique"),
            )
            .reset_index()
        )
        account_stats.columns = ["account", "jobs", "cpu_hours", "gpu_hours", "users"]
        by_account = convert_numpy_to_native(account_stats.to_dict(orient="records"))

    # User data is intentionally not aggregated to protect privacy
    # Only aggregate-level metrics (total_users count) are included
    by_user = []

    # Aggregation by partition
    by_partition = []
    if "Partition" in df.columns:
        partition_stats = (
            df.groupby("Partition")
            .agg(
                jobs=("Partition", "size"),
                cpu_hours=("CPUHours", "sum"),
                gpu_hours=("GPUHours", "sum"),
                users=("User", "nunique"),
            )
            .reset_index()
        )
        partition_stats.columns = ["partition", "jobs", "cpu_hours", "gpu_hours", "users"]
        by_partition = convert_numpy_to_native(partition_stats.to_dict(orient="records"))

    # Aggregation by state
    by_state = []
    if "State" in df.columns:
        state_stats = df.groupby("State").agg(jobs=("State", "size")).reset_index()
        state_stats.columns = ["state", "jobs"]
        by_state = convert_numpy_to_native(state_stats.to_dict(orient="records"))

    # Generate timeline data with appropriate aggregation based on report type
    timeline = []

    # Determine which time column to use based on report type
    # Use Submit time to match datastore filtering and prevent date leakage
    if "Annual" in report_type:
        # Annual reports: aggregate by month
        time_column = "SubmitYearMonth"
    elif "Quarterly" in report_type:
        # Quarterly reports: aggregate by week
        time_column = "SubmitYearWeek"
    else:
        # Monthly reports: aggregate by day
        time_column = "SubmitDay"

    if time_column in df.columns:
        timeline_stats = (
            df.groupby(time_column)
            .agg(
                jobs=(time_column, "size"),
                cpu_hours=("CPUHours", "sum"),
                gpu_hours=("GPUHours", "sum"),
                users=("User", "nunique"),
            )
            .reset_index()
        )
        timeline_stats.columns = ["date", "jobs", "cpu_hours", "gpu_hours", "users"]

        # For week and month aggregations, convert datetime to string for JSON serialization
        if time_column in ["SubmitYearWeek", "SubmitYearMonth"]:
            timeline_stats["date"] = pd.to_datetime(timeline_stats["date"]).dt.strftime("%Y-%m-%d")

        timeline = convert_numpy_to_native(timeline_stats.to_dict(orient="records"))

    # Calculate comparison with previous period
    comparison = calculate_comparison_metrics(hostname, start_date, end_date, summary, report_type)

    return {
        "report_type": report_type,
        "hostname": hostname,
        "period": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "summary": summary,
        "job_duration_stats": duration_stats,
        "waiting_time_stats": waiting_stats,
        "by_account": sorted(by_account, key=lambda x: x["cpu_hours"], reverse=True),
        "by_user": sorted(by_user, key=lambda x: x["cpu_hours"], reverse=True),
        "by_partition": sorted(by_partition, key=lambda x: x["cpu_hours"], reverse=True),
        "by_state": sorted(by_state, key=lambda x: x["jobs"], reverse=True),
        "timeline": timeline,
        "comparison": comparison,
        "generated_at": datetime.now().isoformat(),
    }
