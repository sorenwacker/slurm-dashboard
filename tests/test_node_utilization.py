"""Tests for per-node resource-hour attribution and cluster utilization gauges."""

import pandas as pd
import pytest
from backend.app.services.charts.node_generators import (
    cluster_utilization,
    generate_node_usage,
    node_resource_hours,
    window_fraction,
)

WINDOW = (pd.Timestamp("2026-08-01"), pd.Timestamp("2026-08-03"))  # 48 hours


def jobs():
    return pd.DataFrame(
        {
            # 2-node job fully inside the window: 10 h, 8 CPUs -> 80 CPU-hours split 40/40
            # single-node job straddling the window end: 20 h of which 10 h inside
            # job entirely before the window
            "NodeList": [["n1", "n2"], "n1", "n3"],
            "Start": pd.to_datetime(["2026-08-01T00:00", "2026-08-02T14:00", "2026-07-30T00:00"]),
            "End": pd.to_datetime(["2026-08-01T10:00", "2026-08-03T10:00", "2026-07-30T05:00"]),
            "CPUHours": [80.0, 80.0, 5.0],
            "GPUHours": [20.0, 0.0, 0.0],
            "MemGBHours": [640.0, None, 5.0],
            "Account": ["a", "b", "a"],
        }
    )


def test_window_fraction_clips_to_window():
    assert window_fraction(jobs(), WINDOW).round(3).tolist() == [1.0, 0.5, 0.0]


def test_window_fraction_is_one_without_window_or_timestamps():
    assert window_fraction(jobs(), None).tolist() == [1.0, 1.0, 1.0]
    assert window_fraction(jobs().drop(columns=["End"]), WINDOW).tolist() == [1.0, 1.0, 1.0]


def test_window_fraction_treats_running_jobs_as_ending_at_window_end():
    df = pd.DataFrame({"Start": pd.to_datetime(["2026-08-02T00:00"]), "End": [pd.NaT]})
    assert window_fraction(df, WINDOW).tolist() == [1.0]


def test_node_hours_split_multi_node_jobs_and_clip_to_window():
    hours = node_resource_hours(jobs(), WINDOW).set_index("NodeList")
    assert hours.loc["n1", "CPUHours"] == 40.0 + 40.0
    assert hours.loc["n2", "CPUHours"] == 40.0
    assert hours.loc["n3", "CPUHours"] == 0.0
    assert hours.loc["n1", "GPUHours"] == 10.0
    assert hours.loc["n1", "MemGBHours"] == 320.0
    assert hours.loc["n2", "MemGBHours"] == 320.0


def test_node_hours_with_color_by():
    hours = node_resource_hours(jobs(), WINDOW, color_by="Account").set_index(["NodeList", "Account"])
    assert hours.loc[("n1", "a"), "CPUHours"] == 40.0
    assert hours.loc[("n1", "b"), "CPUHours"] == 40.0


def test_node_hours_keeps_full_hours_without_window():
    hours = node_resource_hours(jobs(), None).set_index("NodeList")
    assert hours.loc["n1", "CPUHours"] == 40.0 + 80.0
    assert hours.loc["n3", "CPUHours"] == 5.0


CAPACITIES = {
    "n1": {"cpu_cores": 8, "gpu_count": 2, "memory_gb": 64, "known": True, "type": "gpu"},
    "n2": {"cpu_cores": 8, "gpu_count": 0, "memory_gb": 64, "known": True, "type": "cpu"},
    "idle": {"cpu_cores": 4, "gpu_count": 0, "memory_gb": 0, "known": True, "type": "cpu"},
    "unknown": {"cpu_cores": 64, "gpu_count": 0, "memory_gb": 0, "known": False, "type": "cpu"},
    "login": {"cpu_cores": 8, "gpu_count": 0, "memory_gb": 32, "known": True, "type": "login"},
}


def test_cluster_utilization_is_capacity_weighted_over_configured_nodes():
    hours = node_resource_hours(jobs(), WINDOW)
    result = cluster_utilization(hours, CAPACITIES, 48.0)
    # CPU: used 80 + 40 = 120 over (8 + 8 + 4) * 48 = 960 -> 12.5 %; unknown and login excluded
    assert result["cpu"] == pytest.approx(12.5)
    # GPU: 10 over 2 * 48 = 96
    assert result["gpu"] == pytest.approx(10.0 / 96.0 * 100.0)
    # memory: 640 over (64 + 64) * 48 = 6144; idle has no memory capacity
    assert result["memory"] == pytest.approx(640.0 / 6144.0 * 100.0)


def test_cluster_utilization_none_without_capacity_or_window():
    hours = node_resource_hours(jobs(), WINDOW)
    assert cluster_utilization(hours, {"unknown": CAPACITIES["unknown"]}, 48.0) == {
        "cpu": None,
        "gpu": None,
        "memory": None,
    }
    assert cluster_utilization(hours, CAPACITIES, None)["cpu"] is None


def test_generate_node_usage_shapes():
    result = generate_node_usage(jobs(), window=WINDOW, capacities=CAPACITIES)
    assert result["cpu_usage"]["x"] == ["n1", "n2"]
    assert result["cpu_usage"]["y"] == [80.0, 40.0]
    assert result["cpu_usage"]["hardware_config"]["n1"]["known"] is True
    assert result["gpu_usage"]["x"] == ["n1", "n2"]
    assert result["memory_usage"]["y"] == [320.0, 320.0]
    assert result["cluster_utilization"]["cpu"] == pytest.approx(12.5)
    assert result["cluster_utilization"]["memory_coverage"] == pytest.approx(2 / 3)


def test_generate_node_usage_marks_unconfigured_nodes_unknown():
    result = generate_node_usage(jobs(), window=WINDOW, capacities={})
    assert result["cpu_usage"]["hardware_config"]["n1"] == {"known": False}
    assert result["cluster_utilization"] == {
        "cpu": None,
        "gpu": None,
        "memory": None,
        "memory_coverage": pytest.approx(2 / 3),
    }


def test_memory_coverage_without_memory_column():
    result = generate_node_usage(jobs().drop(columns=["MemGBHours"]), window=WINDOW, capacities=CAPACITIES)
    assert result["cluster_utilization"]["memory_coverage"] == 0.0
    assert result["cluster_utilization"]["memory"] is None
