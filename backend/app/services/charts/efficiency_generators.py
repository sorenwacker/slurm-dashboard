"""Efficiency charts: consumed resources relative to allocated resources.

Both charts follow the dashboard contract: without a colour dimension one line,
with one a line per group; groups are never listed unless the dimension is selected.
"""

from typing import Any

import pandas as pd

from .distribution_generators import _get_time_column

TOP_GROUPS = 15


def _efficiency_series(
    df: pd.DataFrame,
    period_type: str,
    color_by: str | None,
    used: str,
    allocated: str,
    weight: str | None,
    label: str,
) -> dict[str, Any]:
    required = [used, allocated] + ([weight] if weight else [])
    if any(column not in df.columns for column in required):
        return {"x": [], "series": []}
    known = df[used].notna() & df[allocated].notna() & (df[allocated] > 0)
    if weight:
        known &= df[weight] > 0
    if not known.any():
        return {"x": [], "series": []}

    df_work, time_column = _get_time_column(df[known], period_type)
    if time_column is None:
        return {"x": [], "series": []}
    weights = df_work[weight] if weight else 1.0
    frame = pd.DataFrame(
        {
            "used": df_work[used] * weights,
            "allocated": df_work[allocated] * weights,
            "period": df_work[time_column],
        }
    )

    if color_by and color_by in df_work.columns:
        frame["group"] = df_work[color_by]
        top = frame.groupby("group")["allocated"].sum().sort_values(ascending=False).head(TOP_GROUPS).index
        frame = frame[frame["group"].isin(top)]
        sums = frame.groupby(["group", "period"])[["used", "allocated"]].sum()
        efficiency = (sums["used"] / sums["allocated"] * 100.0).unstack("period")
        periods = sorted(frame["period"].unique())
        efficiency = efficiency.reindex(columns=periods)
        series = [
            {"name": str(group), "data": [None if pd.isna(v) else float(v) for v in efficiency.loc[group]]}
            for group in top
            if group in efficiency.index
        ]
        return {"x": periods, "series": series}

    sums = frame.groupby("period")[["used", "allocated"]].sum().sort_index()
    efficiency = sums["used"] / sums["allocated"] * 100.0
    return {"x": efficiency.index.tolist(), "series": [{"name": label, "data": [float(v) for v in efficiency.values]}]}


def generate_cpu_efficiency_over_time(
    df: pd.DataFrame, period_type: str, color_by: str | None = None
) -> dict[str, Any]:
    """Consumed core-time (sacct ``TotalCPU``) over allocated core-time per period, in percent."""
    return _efficiency_series(df, period_type, color_by, "CPUUsedHours", "CPUHours", None, "CPU used (%)")


def generate_memory_efficiency_over_time(
    df: pd.DataFrame, period_type: str, color_by: str | None = None
) -> dict[str, Any]:
    """Peak memory over requested memory per period, weighted by job runtime; an upper bound."""
    return _efficiency_series(df, period_type, color_by, "MaxRSSMB", "ReqMemMB", "ElapsedHours", "Memory used (%)")
