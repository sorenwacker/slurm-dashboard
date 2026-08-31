"""Efficiency charts: consumed resources relative to allocated resources."""

from typing import Any

import pandas as pd

from .distribution_generators import _get_time_column

TOP_GROUPS = 15


def _ratio(df: pd.DataFrame, used: str, allocated: str) -> pd.Series | None:
    """Per-row pair filter: both values known and allocation positive."""
    if used not in df.columns or allocated not in df.columns:
        return None
    known = df[used].notna() & df[allocated].notna() & (df[allocated] > 0)
    return known if known.any() else None


def generate_cpu_efficiency_over_time(df: pd.DataFrame, period_type: str) -> dict[str, Any]:
    """Consumed core-time over allocated core-time per period, in percent.

    Only jobs reporting ``CPUUsedHours`` (sacct ``TotalCPU``) contribute; periods without them are omitted.
    """
    known = _ratio(df, "CPUUsedHours", "CPUHours")
    if known is None:
        return {"x": [], "y": []}
    df_work, time_column = _get_time_column(df[known], period_type)
    if time_column is None:
        return {"x": [], "y": []}
    grouped = df_work.groupby(time_column)[["CPUUsedHours", "CPUHours"]].sum().sort_index()
    efficiency = grouped["CPUUsedHours"] / grouped["CPUHours"] * 100.0
    return {"x": efficiency.index.tolist(), "y": [float(v) for v in efficiency.values]}


def generate_efficiency_by_group(df: pd.DataFrame, group_by: str | None) -> dict[str, Any]:
    """CPU and memory efficiency per group, for the groups with the most allocated CPU-hours.

    ``group_by`` defaults to Account. Memory efficiency uses peak usage and is an upper bound.
    """
    group_column = group_by if group_by and group_by in df.columns else "Account"
    if group_column not in df.columns:
        return {"x": [], "series": []}
    cpu_known = _ratio(df, "CPUUsedHours", "CPUHours")
    mem_known = _ratio(df, "MaxRSSMB", "ReqMemMB")
    if cpu_known is None and mem_known is None:
        return {"x": [], "series": []}

    groups = (
        df.groupby(group_column)["CPUHours"].sum().sort_values(ascending=False).head(TOP_GROUPS).index.tolist()
        if "CPUHours" in df.columns
        else sorted(df[group_column].dropna().unique())[:TOP_GROUPS]
    )
    series = []
    for name, known, used, allocated in (
        ("CPU", cpu_known, "CPUUsedHours", "CPUHours"),
        ("Memory", mem_known, "MaxRSSMB", "ReqMemMB"),
    ):
        if known is None:
            continue
        sums = df[known].groupby(df[known][group_column])[[used, allocated]].sum()
        data = []
        for group in groups:
            if group in sums.index and sums.at[group, allocated] > 0:
                data.append(float(sums.at[group, used] / sums.at[group, allocated] * 100.0))
            else:
                data.append(0.0)
        series.append({"name": name, "data": data})
    return {"x": [str(g) for g in groups], "series": series}
