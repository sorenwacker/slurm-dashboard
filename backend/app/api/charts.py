"""API endpoints for aggregated chart data.

This module provides endpoints that return pre-aggregated chart data instead of raw job records,
significantly improving performance by reducing payload size and leveraging pandas aggregation speed.
"""
import hashlib
import json

# Import datastore
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from ..config import get_cluster_config
from ..core.config import get_settings
from ..core.saml_auth import get_current_user_saml
from ..models.data_models import FilterRequest
from ..services.charts import (
    format_accounts_in_df,
    generate_active_users_distribution,
    generate_active_users_over_time,
    generate_by_dimension,
    generate_cpu_usage_over_time,
    generate_cpus_per_job,
    generate_gpu_usage_over_time,
    generate_gpus_per_job,
    generate_job_duration_hist,
    generate_job_duration_over_time,
    generate_job_duration_stacked,
    generate_job_duration_trends,
    generate_jobs_by_partition,
    generate_jobs_by_state,
    generate_jobs_distribution,
    generate_jobs_over_time,
    generate_memory_efficiency_over_time,
    generate_memory_per_job,
    generate_memory_usage_over_time,
    generate_node_usage,
    generate_nodes_per_job,
    generate_user_activity_frequency,
    generate_waiting_times_hist,
    generate_waiting_times_over_time,
    generate_waiting_times_stacked,
    generate_waiting_times_trends,
    total_memory_gb_hours,
    generate_cpu_efficiency_over_time,
    generate_efficiency_by_group,
)

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

if TYPE_CHECKING:
    from slurm_usage_history.app.duckdb_datastore import DuckDBDataStore

try:
    from slurm_usage_history.app.datastore import PandasDataStore
    from slurm_usage_history.app.duckdb_datastore import DuckDBDataStore
except ImportError:
    DuckDBDataStore = None  # type: ignore
    PandasDataStore = None  # type: ignore

router = APIRouter()
settings = get_settings()

# Import shared datastore singleton
from ..datastore_singleton import get_datastore

# Every column any chart reads, in every naming generation of the parquet files.
# The datastore intersects this with what the files contain.
CHART_COLUMNS = [
    "User", "Account", "Partition", "QOS", "State",
    "Submit", "Start", "End", "NodeList",
    "CPUHours", "CPU-hours", "GPUHours", "GPU-hours", "MemGBHours",
    "AllocCPUS", "CPUs", "AllocGPUS", "GPUs", "AllocNodes", "Nodes",
    "ReqMemMB", "MaxRSSMB", "MaxRSS", "CPUUsedHours",
    "WaitingTimeHours", "WaitingTime [h]", "WaitingTime", "ElapsedHours", "Elapsed [h]",
    "SubmitDay", "SubmitYearWeek", "SubmitYearMonth", "SubmitYear",
    "StartDay", "StartYearWeek", "StartYearMonth", "StartYear",
]

# Simple in-memory cache for chart data
# Cache structure: {cache_key: (timestamp, data)}
_chart_cache: dict[str, tuple[datetime, dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes cache TTL


def _generate_cache_key(request: FilterRequest) -> str:
    """Generate a cache key from the filter request."""
    # Create a dictionary with all filter parameters
    cache_dict = {
        "hostname": request.hostname,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "partitions": sorted(request.partitions) if request.partitions else [],
        "accounts": sorted(request.accounts) if request.accounts else [],
        "users": sorted(request.users) if request.users else [],
        "qos": sorted(request.qos) if request.qos else [],
        "states": sorted(request.states) if request.states else [],
        "period_type": request.period_type,
        "color_by": request.color_by,
        "account_segments": request.account_segments,
        "complete_periods_only": request.complete_periods_only,
        # Note: normalize_node_usage removed - now handled client-side
        # Note: hide_unused_nodes and sort_by_usage removed - now handled client-side
    }
    # Convert to JSON string and hash it
    cache_str = json.dumps(cache_dict, sort_keys=True)
    return hashlib.md5(cache_str.encode()).hexdigest()


def _get_from_cache(cache_key: str) -> dict[str, Any] | None:
    """Get data from cache if it exists and is not expired."""
    if cache_key in _chart_cache:
        timestamp, data = _chart_cache[cache_key]
        age_seconds = (datetime.now() - timestamp).total_seconds()
        if age_seconds < CACHE_TTL_SECONDS:
            return data
        # Remove expired entry
        del _chart_cache[cache_key]
    return None


def _save_to_cache(cache_key: str, data: dict[str, Any]) -> None:
    """Save data to cache with current timestamp."""
    _chart_cache[cache_key] = (datetime.now(), data)

    # Simple cache cleanup: remove old entries if cache gets too large
    if len(_chart_cache) > 100:
        # Remove the oldest 20 entries
        sorted_keys = sorted(_chart_cache.keys(), key=lambda k: _chart_cache[k][0])
        for key in sorted_keys[:20]:
            del _chart_cache[key]


def clear_chart_cache() -> None:
    """Clear all cached chart data. Called when data is reloaded."""
    global _chart_cache
    _chart_cache = {}


@router.post("/charts")
async def get_aggregated_charts(request: FilterRequest, current_user: dict = Depends(get_current_user_saml)) -> dict[str, Any]:
    """Get all aggregated chart data in a single request.

    This endpoint performs all aggregations on the backend using pandas,
    returning only the aggregated data needed for charts. This reduces
    the payload from ~138MB to ~10-50KB.

    Caching: Results are cached for 5 minutes to improve performance for
    repeated queries with the same parameters.

    Args:
        request: Filter parameters (hostname, dates, partitions, accounts, etc.)

    Returns:
        Dictionary containing all aggregated chart data
    """
    try:
        # Check cache first
        cache_key = _generate_cache_key(request)
        cached_data = _get_from_cache(cache_key)
        if cached_data is not None:
            # Add cache hit indicator for debugging
            cached_data["_cached"] = True
            return cached_data

        datastore = get_datastore()

        # One DuckDB scan: jobs overlapping the range are a superset of jobs submitted in it
        # (Start >= Submit), so the submit-based frame is a row subset of the overlap frame.
        overlap_df = datastore.filter(
            hostname=request.hostname,
            start_date=request.start_date,
            end_date=request.end_date,
            partitions=request.partitions,
            accounts=request.accounts,
            users=request.users,
            qos=request.qos,
            states=request.states,
            complete_periods_only=request.complete_periods_only,
            period_type=request.period_type,
            time_base="overlap",
            columns=CHART_COLUMNS,
        )
        df = _submitted_in_range(overlap_df, request.start_date, request.end_date)

        if df.empty:
            return _empty_charts_response()

        # Apply account formatting if requested
        if request.account_segments:
            df = format_accounts_in_df(df, request.account_segments)

        # Generate all chart aggregations
        period_type = request.period_type or "month"
        color_by = request.color_by  # Can be: Account, Partition, State, QOS, User, or None

        # Node utilization uses jobs overlapping the window and the window length as capacity time
        window = _window(request, df)
        total_hours = (window[1] - window[0]).total_seconds() / 3600.0 if window else None
        if request.account_segments:
            overlap_df = format_accounts_in_df(overlap_df, request.account_segments)
        node_usage = generate_node_usage(
            overlap_df,
            color_by=color_by,
            hide_unused=False,  # Always return all nodes (client handles hiding)
            window=window,
            capacities=get_cluster_config().get_all_node_capacities(request.hostname),
        )

        charts_data = {
            "summary": _generate_summary(df),
            "cpu_usage_over_time": generate_cpu_usage_over_time(df, period_type, color_by),
            "gpu_usage_over_time": generate_gpu_usage_over_time(df, period_type, color_by),
            "active_users_over_time": generate_active_users_over_time(df, period_type, color_by),
            "jobs_over_time": generate_jobs_over_time(df, period_type, color_by),
            # Distribution charts - use color_by for dynamic grouping
            "jobs_by_account": generate_by_dimension(df, color_by, metric="count", period_type=period_type),
            "jobs_by_partition": generate_jobs_by_partition(df),  # Keep for now
            "jobs_by_state": generate_jobs_by_state(df),  # Keep for now
            # Timing histograms (always ungrouped - ignore color_by)
            "waiting_times_hist": generate_waiting_times_hist(df, None),
            "job_duration_hist": generate_job_duration_hist(df, None),
            # Distribution charts
            "active_users_distribution": generate_active_users_distribution(df, period_type, color_by),
            "jobs_distribution": generate_jobs_distribution(df, period_type, color_by),
            # Stacked percentage charts (new)
            "job_duration_stacked": generate_job_duration_stacked(df, period_type),
            "waiting_times_stacked": generate_waiting_times_stacked(df, period_type),
            # Timing over time (always ungrouped - ignore color_by)
            "waiting_times_over_time": generate_waiting_times_over_time(df, period_type, None),
            "job_duration_over_time": generate_job_duration_over_time(df, period_type, None),
            # Timing trends (always ungrouped - ignore color_by)
            "waiting_times_trends": generate_waiting_times_trends(df, period_type, None),
            "job_duration_trends": generate_job_duration_trends(df, period_type, None),
            # Resource allocation
            "cpus_per_job": generate_cpus_per_job(df),
            "gpus_per_job": generate_gpus_per_job(df),
            "nodes_per_job": generate_nodes_per_job(df),
            # Resource distribution charts - use color_by for dynamic grouping (with period_type for histogram mode)
            "cpu_hours_by_account": generate_by_dimension(df, color_by, metric="CPUHours", period_type=period_type),
            "gpu_hours_by_account": generate_by_dimension(df, color_by, metric="GPUHours", period_type=period_type),
            # Memory charts (jobs without memory data are excluded, never counted as zero)
            "memory_usage_over_time": generate_memory_usage_over_time(df, period_type, color_by),
            "memory_hours_by_account": generate_by_dimension(df, color_by, metric="MemGBHours", period_type=period_type),
            "memory_efficiency_over_time": generate_memory_efficiency_over_time(df, period_type),
            "cpu_efficiency_over_time": generate_cpu_efficiency_over_time(df, period_type),
            "efficiency_by_group": generate_efficiency_by_group(df, color_by),
            "memory_per_job": generate_memory_per_job(df),
            # Node usage charts (include total_hours for client-side normalization)
            "node_cpu_usage": {**node_usage["cpu_usage"], "total_hours": total_hours},
            "node_gpu_usage": {**node_usage["gpu_usage"], "total_hours": total_hours},
            "node_memory_usage": {**node_usage["memory_usage"], "total_hours": total_hours},
            "cluster_utilization": node_usage["cluster_utilization"],
            # User activity frequency distribution
            "user_activity_frequency": generate_user_activity_frequency(df, period_type, color_by),
        }

        # Save to cache before returning
        _save_to_cache(cache_key, charts_data)

        return charts_data

    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Charts endpoint error: {e!s}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error generating charts: {e!s}")


def _submitted_in_range(df: pd.DataFrame, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    """Rows submitted inside [start_date, end_date]; the whole frame when no bound is given."""
    if df.empty or "Submit" not in df.columns or not (start_date or end_date):
        return df
    submit = pd.to_datetime(df["Submit"])
    mask = pd.Series(True, index=df.index)
    if start_date:
        mask &= submit >= pd.Timestamp(start_date)
    if end_date:
        mask &= submit < pd.Timestamp(end_date) + pd.Timedelta(days=1)
    return df[mask]


def _window(request: FilterRequest, df: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    """Selected range as (start, end_exclusive); falls back to the submit range of the data."""
    if request.start_date and request.end_date:
        start = pd.Timestamp(request.start_date)
        end = pd.Timestamp(request.end_date) + pd.Timedelta(days=1)
    elif "Submit" in df.columns and not df.empty:
        start = pd.to_datetime(df["Submit"].min()).normalize()
        end = pd.to_datetime(df["Submit"].max()).normalize() + pd.Timedelta(days=1)
    else:
        return None
    return (start, end) if end > start else None


def _empty_charts_response() -> dict[str, Any]:
    """Return empty chart data structure."""
    return {
        "summary": {"total_jobs": 0, "total_cpu_hours": 0, "total_gpu_hours": 0, "total_memory_gb_hours": 0, "total_users": 0},
        "cpu_usage_over_time": {"x": [], "y": []},
        "gpu_usage_over_time": {"x": [], "y": []},
        "active_users_over_time": {"x": [], "y": []},
        "jobs_over_time": {"x": [], "y": []},
        "jobs_by_account": {"x": [], "y": []},
        "jobs_by_partition": {"x": [], "y": []},
        "jobs_by_state": {"labels": [], "values": []},
        "waiting_times_hist": {"x": [], "y": []},
        "job_duration_hist": {"x": [], "y": []},
        "waiting_times_over_time": {"x": [], "y": []},
        "job_duration_over_time": {"x": [], "y": []},
        "cpus_per_job": {"x": [], "y": []},
        "gpus_per_job": {"x": [], "y": []},
        "nodes_per_job": {"x": [], "y": []},
        "cpu_hours_by_account": {"x": [], "y": []},
        "gpu_hours_by_account": {"x": [], "y": []},
        "node_cpu_usage": {"x": [], "y": []},
        "node_gpu_usage": {"x": [], "y": []},
        "memory_usage_over_time": {"x": [], "y": []},
        "memory_hours_by_account": {"x": [], "y": []},
        "memory_efficiency_over_time": {"x": [], "y": []},
        "cpu_efficiency_over_time": {"x": [], "y": []},
        "efficiency_by_group": {"x": [], "series": []},
        "memory_per_job": {"x": [], "y": []},
        "node_memory_usage": {"x": [], "y": []},
        "cluster_utilization": {"cpu": None, "gpu": None, "memory": None, "memory_coverage": 0.0},
    }


def _generate_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Generate summary statistics."""
    return {
        "total_jobs": len(df),
        "total_cpu_hours": float(df["CPUHours"].sum()) if "CPUHours" in df.columns else 0.0,
        "total_gpu_hours": float(df["GPUHours"].sum()) if "GPUHours" in df.columns else 0.0,
        "total_memory_gb_hours": total_memory_gb_hours(df),
        "total_users": int(df["User"].nunique()) if "User" in df.columns else 0,
    }


