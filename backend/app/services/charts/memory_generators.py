"""Chart generators for job memory requests, peak usage and memory-hours."""

from typing import Any

import pandas as pd

from .distribution_generators import _get_time_column
from .timeline_generators import _generate_timeline

MB_PER_GB = 1024.0


def generate_memory_usage_over_time(df: pd.DataFrame, period_type: str, color_by: str | None) -> dict[str, Any]:
    """Allocated memory-hours (GB-hours) per period; jobs with unknown memory are excluded."""
    return _generate_timeline(
        df,
        value_column="MemGBHours",
        period_type=period_type,
        color_by=color_by,
        time_base="start",
        aggregation="sum",
        filter_nulls=True,
        normalize_weeks=True,
    )


def generate_memory_efficiency_over_time(df: pd.DataFrame, period_type: str) -> dict[str, Any]:
    """Share of requested memory that was used per period: sum(MaxRSSMB) / sum(ReqMemMB) in percent.

    Only jobs reporting both values contribute; periods without such jobs are omitted.
    """
    if "ReqMemMB" not in df.columns or "MaxRSSMB" not in df.columns:
        return {"x": [], "y": []}
    known = df[df["ReqMemMB"].notna() & df["MaxRSSMB"].notna() & (df["ReqMemMB"] > 0)]
    if known.empty:
        return {"x": [], "y": []}
    df_work, time_column = _get_time_column(known, period_type)
    if time_column is None:
        return {"x": [], "y": []}
    grouped = df_work.groupby(time_column)[["ReqMemMB", "MaxRSSMB"]].sum().sort_index()
    efficiency = grouped["MaxRSSMB"] / grouped["ReqMemMB"] * 100.0
    return {"x": efficiency.index.tolist(), "y": [float(v) for v in efficiency.values]}


def generate_memory_per_job(df: pd.DataFrame) -> dict[str, list]:
    """Distribution of requested memory per job in whole GB (20 most common sizes)."""
    if "ReqMemMB" not in df.columns:
        return {"x": [], "y": []}
    known = df["ReqMemMB"].dropna()
    if known.empty:
        return {"x": [], "y": []}
    gb = (known / MB_PER_GB).round().astype(int)
    counts = gb.value_counts().sort_index().head(20)
    return {"x": counts.index.tolist(), "y": counts.values.tolist()}


def total_memory_gb_hours(df: pd.DataFrame) -> float:
    """Sum of allocated memory-hours over jobs with known memory."""
    if "MemGBHours" not in df.columns:
        return 0.0
    return float(df["MemGBHours"].fillna(0.0).sum())
