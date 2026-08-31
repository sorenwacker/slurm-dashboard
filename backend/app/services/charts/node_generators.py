"""Per-node resource-hours, utilization and cluster gauges.

See docs/user-guide/utilization.md for the definitions implemented here.
"""

from typing import Any

import numpy as np
import pandas as pd

from slurm_usage_history.tools import unpack_nodelist_string

RESOURCES = {
    "cpu": {"hours": "CPUHours", "capacity": "cpu_cores"},
    "gpu": {"hours": "GPUHours", "capacity": "gpu_count"},
    "memory": {"hours": "MemGBHours", "capacity": "memory_gb"},
}
COMPUTE_NODE_TYPES = {"cpu", "gpu"}


def _expand_nodelist(value: Any) -> list[str]:
    if isinstance(value, np.ndarray):
        return [str(v).strip() for v in value.tolist() if str(v).strip()]
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    text = str(value).strip()
    if not text or text.lower() in ("none", "nan", "none assigned"):
        return []
    if "[" in text or "]" in text:
        return unpack_nodelist_string(text)
    return [part.strip() for part in text.split(",") if part.strip()]


def window_fraction(df: pd.DataFrame, window: tuple[pd.Timestamp, pd.Timestamp] | None) -> pd.Series:
    """Share of each job's runtime that falls inside ``[window_start, window_end)``.

    1.0 for every job when the window or the Start/End columns are missing.
    """
    if window is None or "Start" not in df.columns or "End" not in df.columns:
        return pd.Series(1.0, index=df.index)
    start = pd.to_datetime(df["Start"], errors="coerce")
    end = pd.to_datetime(df["End"], errors="coerce").fillna(window[1])
    elapsed = (end - start).dt.total_seconds()
    overlap = (end.clip(upper=window[1]) - start.clip(lower=window[0])).dt.total_seconds().clip(lower=0)
    fraction = (overlap / elapsed.where(elapsed > 0)).fillna(0.0)
    return fraction.where(start.notna(), 0.0)


def node_resource_hours(
    df: pd.DataFrame,
    window: tuple[pd.Timestamp, pd.Timestamp] | None = None,
    color_by: str | None = None,
) -> pd.DataFrame:
    """One row per (node[, color_by]) with CPUHours, GPUHours and MemGBHours attributed to that node.

    Each job's hours are scaled to the part of its runtime inside the window and split
    equally over the nodes in its node list.
    """
    columns = ["CPUHours", "GPUHours", "MemGBHours"]
    if "NodeList" not in df.columns or df.empty:
        return pd.DataFrame(columns=["NodeList", *columns])

    raw = df["NodeList"]
    # Node lists repeat heavily (a few hundred distinct values for ~1M jobs), so all
    # per-value work happens on the distinct values; per-row operations are dict maps.
    try:
        uniques = raw.dropna().unique()
        all_strings = all(isinstance(u, str) for u in uniques)
    except TypeError:  # unhashable entries (lists/arrays)
        all_strings = False

    work = pd.DataFrame(index=df.index)
    fraction = window_fraction(df, window)
    if all_strings:
        expanded = {value: _expand_nodelist(value) for value in uniques}
        lengths = raw.map({value: len(nodes) for value, nodes in expanded.items()})
        share = fraction / lengths.replace(0, np.nan)
    else:
        node_lists = raw.map(_expand_nodelist)
        share = fraction / node_lists.map(len).replace(0, np.nan)
    for column in columns:
        if column in df.columns:
            work[column] = pd.to_numeric(df[column], errors="coerce") * share
        else:
            work[column] = np.nan
    group_cols = []
    if color_by and color_by in df.columns:
        work[color_by] = df[color_by]
        group_cols.append(color_by)

    if all_strings:
        # Aggregate per distinct node-list string first, then explode the small result
        work["_nodes"] = raw
        grouped = work.groupby(["_nodes", *group_cols], as_index=False, dropna=False)[columns].sum(min_count=1)
        grouped["NodeList"] = grouped["_nodes"].map(expanded)
        exploded = grouped.drop(columns=["_nodes"]).explode("NodeList")
    else:
        work["NodeList"] = node_lists
        exploded = work.explode("NodeList")

    exploded = exploded[exploded["NodeList"].notna() & (exploded["NodeList"] != "")]
    exploded["NodeList"] = exploded["NodeList"].astype(str)
    return exploded.groupby(["NodeList", *group_cols], as_index=False)[columns].sum(min_count=1)


def _chart(node_hours: pd.DataFrame, hours_column: str, color_by: str | None, hide_unused: bool) -> dict[str, Any]:
    known = node_hours[node_hours[hours_column].notna()]
    if hide_unused:
        known = known[known[hours_column] > 0]
    if known.empty:
        return {"x": [], "y": [], "series": []}
    nodes = sorted(known["NodeList"].unique())
    if color_by and color_by in known.columns:
        grouped = known.groupby([color_by, "NodeList"])[hours_column].sum()
        groups = known.groupby(color_by)[hours_column].sum().sort_values(ascending=False).index.tolist()
        series = [
            {"name": str(group), "data": [float(grouped.get((group, node), 0.0)) for node in nodes]} for group in groups
        ]
        return {"x": nodes, "series": series}
    totals = known.groupby("NodeList")[hours_column].sum()
    return {"x": nodes, "y": [float(totals[node]) for node in nodes]}


def cluster_utilization(
    node_hours: pd.DataFrame, capacities: dict[str, dict[str, Any]], window_hours: float | None
) -> dict[str, float | None]:
    """Capacity-weighted utilization per resource over all configured compute nodes with known capacity.

    ``capacities`` maps every configured node to its hardware dict (``cpu_cores``, ``gpu_count``,
    ``memory_gb``, ``known``, ``synced``, ``type``). Nodes with unknown or zero capacity are left out
    of both sums, and so are configured nodes that SLURM does not report (not ``synced``) and that ran
    nothing in the window - those are usually decommissioned and would dilute the denominator.
    """
    if not window_hours or window_hours <= 0:
        return dict.fromkeys(RESOURCES)
    used = (
        node_hours.groupby("NodeList")[[spec["hours"] for spec in RESOURCES.values()]].sum(min_count=1)
        if not node_hours.empty
        else pd.DataFrame()
    )
    active_nodes = set(used[used.fillna(0.0).sum(axis=1) > 0].index) if not used.empty else set()
    result: dict[str, float | None] = {}
    for resource, spec in RESOURCES.items():
        if used.empty or used[spec["hours"]].notna().sum() == 0:
            result[resource] = None  # no job reported this resource, so 0 % would be false
            continue
        total_capacity = 0.0
        total_used = 0.0
        for node, hw in capacities.items():
            if hw.get("type", "cpu") not in COMPUTE_NODE_TYPES or not hw.get("known"):
                continue
            if not hw.get("synced") and node not in active_nodes:
                continue  # in the config but neither reported by SLURM nor used in the window
            capacity = float(hw.get(spec["capacity"]) or 0)
            if capacity <= 0:
                continue
            total_capacity += capacity * window_hours
            if node in used.index and pd.notna(used.at[node, spec["hours"]]):
                total_used += float(used.at[node, spec["hours"]])
        result[resource] = min(100.0, total_used / total_capacity * 100.0) if total_capacity > 0 else None
    return result


def generate_node_usage(
    df: pd.DataFrame,
    color_by: str | None = None,
    hide_unused: bool = True,
    window: tuple[pd.Timestamp, pd.Timestamp] | None = None,
    capacities: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Per-node CPU, GPU and memory hours plus capacity-weighted cluster utilization.

    Args:
        df: Jobs overlapping the window (Start/End, NodeList, CPUHours, GPUHours, MemGBHours)
        color_by: Optional dimension to split each node's bar by
        hide_unused: Drop nodes without hours from the charts
        window: ``(start, end_exclusive)`` timestamps of the selected range
        capacities: Hardware for every configured node of the cluster (``ClusterConfig.get_node_hardware``)
    """
    node_hours = node_resource_hours(df, window, color_by)
    capacities = capacities or {}
    window_hours = (window[1] - window[0]).total_seconds() / 3600.0 if window else None
    charts = {}
    for resource, spec in RESOURCES.items():
        chart = _chart(node_hours, spec["hours"], color_by, hide_unused)
        chart["hardware_config"] = {node: capacities.get(node, {"known": False}) for node in chart["x"]}
        charts[f"{resource}_usage"] = chart
    charts["cluster_utilization"] = {
        **cluster_utilization(node_hours, capacities, window_hours),
        "memory_coverage": memory_coverage(df),
    }
    return charts


def memory_coverage(df: pd.DataFrame) -> float:
    """Share of jobs with known requested memory; the memory gauge is only meaningful near 1.0."""
    if df.empty or "MemGBHours" not in df.columns:
        return 0.0
    return float(pd.to_numeric(df["MemGBHours"], errors="coerce").notna().mean())
