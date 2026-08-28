"""Node usage chart generators for CPU and GPU usage by node."""
from typing import Any

import numpy as np
import pandas as pd

# Import SLURM nodelist expansion
try:
    from slurm_usage_history.tools import unpack_nodelist_string
except ImportError:
    # Fallback if not available
    def unpack_nodelist_string(s):
        return [s] if s else []


def generate_node_usage(
    df: pd.DataFrame,
    color_by: str | None = None,
    hide_unused: bool = True,
    sort_by_usage: bool = False,
    normalize: bool = False,
    cluster_name: str | None = None,
    total_hours: float | None = None,
) -> dict[str, Any]:
    """Aggregate CPU and GPU usage by node.

    Args:
        df: Input DataFrame
        color_by: Optional dimension to group by (Account, Partition, State, QOS, User)
        hide_unused: Hide nodes with 0 usage
        sort_by_usage: Sort nodes by usage (default: alphabetical)
        normalize: If True, normalize usage to percentage of max capacity (0-100%)
        cluster_name: Cluster name for hardware lookups (required if normalize=True)
        total_hours: Total hours in time range for normalization (required if normalize=True)

    Returns:
        Dictionary with cpu_usage and gpu_usage data. If normalize=True, values
        represent percentage utilization (0-100).
    """
    # Import cluster config for hardware lookups (only when needed)
    from ...config import get_cluster_config

    # Helper function to normalize a single value to percentage
    def normalize_value(value: float, max_capacity: float) -> float:
        if max_capacity <= 0:
            return 0.0
        return min(100.0, (value / max_capacity) * 100.0)

    # Get hardware config if normalization is requested
    cluster_config = None
    if normalize and cluster_name and total_hours and total_hours > 0:
        cluster_config = get_cluster_config()

    empty = {"x": [], "y": [], "series": []}
    if "NodeList" not in df.columns:
        return {"cpu_usage": empty, "gpu_usage": empty, "memory_usage": empty}

    # Explode NodeList to get one row per node
    cols = ["NodeList", "CPUHours", "GPUHours"]
    has_memory = "MemGBHours" in df.columns
    if has_memory:
        cols.append("MemGBHours")
    if color_by and color_by in df.columns:
        cols.append(color_by)

    node_df = df[cols].copy()

    # NodeList can be:
    # 1. A numpy array like array(['node1', 'node2'])
    # 2. A list like ['node1', 'node2']
    # 3. A comma-separated string like "node1,node2"
    # 4. Compressed SLURM notation like "gpu[01-11,14-24]" (legacy data)
    def process_nodelist(val):
        result = []

        # If it's a numpy array, convert to list
        if isinstance(val, np.ndarray):
            result = val.tolist()
        # If it's already a list or tuple, use as is
        elif isinstance(val, (list, tuple)):
            result = list(val)
        # Otherwise it's a string
        else:
            val_str = str(val).strip()
            # Check if it contains compressed SLURM notation (has brackets)
            if '[' in val_str or ']' in val_str:
                # Expand using unpack_nodelist_string
                result = unpack_nodelist_string(val_str)
            else:
                # Simple comma-separated list
                result = [x.strip() for x in val_str.split(",") if x.strip()]

        return result if result else []

    node_df["NodeList"] = node_df["NodeList"].apply(process_nodelist)
    node_df = node_df.explode("NodeList")
    node_df = node_df[node_df["NodeList"].notna()]
    node_df["NodeList"] = node_df["NodeList"].astype(str).str.strip()

    # DO NOT normalize node names - keep them as they appear in SLURM data

    if node_df.empty:
        return {"cpu_usage": empty, "gpu_usage": empty, "memory_usage": empty}

    memory_usage = _memory_by_node(node_df, color_by, hide_unused) if has_memory else dict(empty)

    # Group by node (and optionally color_by dimension)
    if color_by and color_by in node_df.columns:
        groupby_cols = ["NodeList", color_by]
        cpu_grouped = node_df.groupby(groupby_cols)["CPUHours"].sum().reset_index()
        gpu_grouped = node_df.groupby(groupby_cols)["GPUHours"].sum().reset_index()
    else:
        cpu_grouped = node_df.groupby("NodeList")["CPUHours"].sum().reset_index()
        gpu_grouped = node_df.groupby("NodeList")["GPUHours"].sum().reset_index()

    # Hide unused nodes if requested
    if hide_unused:
        cpu_grouped = cpu_grouped[cpu_grouped["CPUHours"] > 0]
        gpu_grouped = gpu_grouped[gpu_grouped["GPUHours"] > 0]

    # Pre-compute max capacities and hardware config for each node (needed for sorting when normalized)
    all_nodes = set(cpu_grouped["NodeList"].unique()) | set(gpu_grouped["NodeList"].unique())
    cpu_max_capacities = {}
    gpu_max_capacities = {}
    hardware_config = {}  # Store per-node hardware specs for hover info
    config = get_cluster_config()
    for node in all_nodes:
        hw = config.get_node_hardware(cluster_name, node) if cluster_name else {"cpu_cores": 64, "gpu_count": 0}
        hardware_config[node] = hw
        if cluster_config and total_hours:
            cpu_max_capacities[node] = hw["cpu_cores"] * total_hours
            gpu_max_capacities[node] = hw["gpu_count"] * total_hours

    # Sort nodes
    if sort_by_usage:
        if color_by and color_by in cpu_grouped.columns:
            cpu_total_per_node = cpu_grouped.groupby("NodeList")["CPUHours"].sum()
            gpu_total_per_node = gpu_grouped.groupby("NodeList")["GPUHours"].sum()
        else:
            cpu_total_per_node = cpu_grouped.set_index("NodeList")["CPUHours"]
            gpu_total_per_node = gpu_grouped.set_index("NodeList")["GPUHours"]

        # If normalizing, sort by percentage utilization instead of raw hours
        if cluster_config:
            cpu_normalized = pd.Series({
                node: normalize_value(float(cpu_total_per_node.get(node, 0)), cpu_max_capacities.get(node, 1))
                for node in cpu_total_per_node.index
            })
            gpu_normalized = pd.Series({
                node: normalize_value(float(gpu_total_per_node.get(node, 0)), gpu_max_capacities.get(node, 1))
                for node in gpu_total_per_node.index
            })
            cpu_sorted_nodes = cpu_normalized.sort_values(ascending=False).index.tolist()
            gpu_sorted_nodes = gpu_normalized.sort_values(ascending=False).index.tolist()
        else:
            cpu_sorted_nodes = cpu_total_per_node.sort_values(ascending=False).index.tolist()
            gpu_sorted_nodes = gpu_total_per_node.sort_values(ascending=False).index.tolist()
    else:
        # Alphabetical sort (natural sort would be better but requires natsort library)
        cpu_sorted_nodes = sorted(cpu_grouped["NodeList"].unique())
        gpu_sorted_nodes = sorted(gpu_grouped["NodeList"].unique())

    # Build response
    if color_by and color_by in cpu_grouped.columns:
        # Multi-series for stacked bar chart
        cpu_series = []
        all_groups = cpu_grouped.groupby(color_by)["CPUHours"].sum().sort_values(ascending=False).index.tolist()
        for group in all_groups:
            group_data = cpu_grouped[cpu_grouped[color_by] == group]
            data = []
            for node in cpu_sorted_nodes:
                node_value = group_data[group_data["NodeList"] == node]["CPUHours"].sum()
                value = float(node_value) if node_value > 0 else 0.0
                if cluster_config and node in cpu_max_capacities:
                    value = normalize_value(value, cpu_max_capacities[node])
                data.append(value)
            cpu_series.append({
                "name": str(group),
                "data": data,
            })

        gpu_series = []
        all_groups = gpu_grouped.groupby(color_by)["GPUHours"].sum().sort_values(ascending=False).index.tolist()
        for group in all_groups:
            group_data = gpu_grouped[gpu_grouped[color_by] == group]
            data = []
            for node in gpu_sorted_nodes:
                node_value = group_data[group_data["NodeList"] == node]["GPUHours"].sum()
                value = float(node_value) if node_value > 0 else 0.0
                if cluster_config and node in gpu_max_capacities:
                    value = normalize_value(value, gpu_max_capacities[node])
                data.append(value)
            gpu_series.append({
                "name": str(group),
                "data": data,
            })

        return {
            "cpu_usage": {
                "x": cpu_sorted_nodes,
                "series": cpu_series,
                "normalized": cluster_config is not None,
                "hardware_config": {node: hardware_config.get(node, {}) for node in cpu_sorted_nodes},
            },
            "gpu_usage": {
                "x": gpu_sorted_nodes,
                "series": gpu_series,
                "normalized": cluster_config is not None,
                "hardware_config": {node: hardware_config.get(node, {}) for node in gpu_sorted_nodes},
            },
            "memory_usage": _with_hardware(memory_usage, config, cluster_name),
        }
    else:
        # Single series
        cpu_data = []
        for node in cpu_sorted_nodes:
            value = float(cpu_grouped[cpu_grouped["NodeList"] == node]["CPUHours"].sum())
            if cluster_config and node in cpu_max_capacities:
                value = normalize_value(value, cpu_max_capacities[node])
            cpu_data.append(value)

        gpu_data = []
        for node in gpu_sorted_nodes:
            value = float(gpu_grouped[gpu_grouped["NodeList"] == node]["GPUHours"].sum())
            if cluster_config and node in gpu_max_capacities:
                value = normalize_value(value, gpu_max_capacities[node])
            gpu_data.append(value)

        return {
            "cpu_usage": {
                "x": cpu_sorted_nodes,
                "y": cpu_data,
                "normalized": cluster_config is not None,
                "hardware_config": {node: hardware_config.get(node, {}) for node in cpu_sorted_nodes},
            },
            "gpu_usage": {
                "x": gpu_sorted_nodes,
                "y": gpu_data,
                "normalized": cluster_config is not None,
                "hardware_config": {node: hardware_config.get(node, {}) for node in gpu_sorted_nodes},
            },
            "memory_usage": _with_hardware(memory_usage, config, cluster_name),
        }


def _memory_by_node(node_df: pd.DataFrame, color_by: str | None, hide_unused: bool) -> dict[str, Any]:
    """Allocated memory-hours per node (alphabetical), optionally split by color_by."""
    known = node_df[node_df["MemGBHours"].notna()]
    if hide_unused:
        known = known[known["MemGBHours"] > 0]
    if known.empty:
        return {"x": [], "y": [], "series": []}
    nodes = sorted(known["NodeList"].unique())
    if color_by and color_by in known.columns:
        grouped = known.groupby([color_by, "NodeList"])["MemGBHours"].sum()
        groups = known.groupby(color_by)["MemGBHours"].sum().sort_values(ascending=False).index.tolist()
        series = [
            {"name": str(group), "data": [float(grouped.get((group, node), 0.0)) for node in nodes]}
            for group in groups
        ]
        return {"x": nodes, "series": series, "normalized": False}
    totals = known.groupby("NodeList")["MemGBHours"].sum()
    return {"x": nodes, "y": [float(totals[node]) for node in nodes], "normalized": False}


def _with_hardware(usage: dict[str, Any], config, cluster_name: str | None) -> dict[str, Any]:
    """Attach per-node hardware so the client can normalize memory-hours against ram.total_gb."""
    if not usage.get("x"):
        return usage
    hardware = {
        node: (config.get_node_hardware(cluster_name, node) if cluster_name else {"cpu_cores": 64, "gpu_count": 0, "memory_gb": 0})
        for node in usage["x"]
    }
    return {**usage, "hardware_config": hardware}
