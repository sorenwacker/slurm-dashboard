"""Tests for memory chart generators and node memory capacity lookups."""

import pandas as pd
import yaml
from backend.app.config import ClusterConfig
from backend.app.services.charts.memory_generators import (
    generate_memory_efficiency_over_time,
    generate_memory_per_job,
    generate_memory_usage_over_time,
)
from backend.app.services.charts.node_generators import generate_node_usage


def jobs_df():
    return pd.DataFrame(
        {
            "StartYearMonth": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-02-01", "2026-02-01"]),
            "Account": ["a", "b", "a", "a"],
            "ReqMemMB": [16384.0, 8192.0, None, 4096.0],
            "MaxRSSMB": [4096.0, 8192.0, 100.0, None],
            "MemGBHours": [32.0, 8.0, None, 2.0],
            "NodeList": [["n1"], ["n1"], ["n2"], ["n2"]],
            "CPUHours": [1.0, 1.0, 1.0, 1.0],
            "GPUHours": [0.0, 0.0, 0.0, 0.0],
        }
    )


def test_memory_usage_over_time_sums_gb_hours_ignoring_unknown():
    result = generate_memory_usage_over_time(jobs_df(), "month", None)
    assert result["y"] == [40.0, 2.0]


def test_memory_usage_over_time_with_color_by():
    result = generate_memory_usage_over_time(jobs_df(), "month", "Account")
    assert {s["name"]: s["data"] for s in result["series"]} == {"a": [32.0, 2.0], "b": [8.0, 0.0]}


def test_memory_efficiency_uses_only_jobs_with_both_values():
    result = generate_memory_efficiency_over_time(jobs_df(), "month")
    assert result["y"] == [50.0]
    assert len(result["x"]) == 1


def test_memory_per_job_histogram_in_gb():
    result = generate_memory_per_job(jobs_df())
    assert result["x"] == [4, 8, 16]
    assert result["y"] == [1, 1, 1]


def test_generators_return_empty_without_memory_columns():
    df = jobs_df().drop(columns=["ReqMemMB", "MaxRSSMB", "MemGBHours"])
    assert generate_memory_usage_over_time(df, "month", None) == {"x": [], "y": []}
    assert generate_memory_efficiency_over_time(df, "month") == {"x": [], "y": []}
    assert generate_memory_per_job(df) == {"x": [], "y": []}


def test_node_usage_includes_memory_usage():
    result = generate_node_usage(jobs_df())
    assert result["memory_usage"]["x"] == ["n1", "n2"]
    assert result["memory_usage"]["y"] == [40.0, 2.0]


def test_node_usage_memory_empty_without_column():
    result = generate_node_usage(jobs_df().drop(columns=["MemGBHours"]))
    assert result["memory_usage"]["x"] == []


def test_get_node_hardware_reports_memory(tmp_path):
    path = tmp_path / "clusters.yaml"
    path.write_text(
        yaml.dump(
            {
                "clusters": {
                    "T": {
                        "node_labels": {
                            "n1": {
                                "type": "cpu",
                                "hardware": {"cpu": {"cores": 8}, "ram": {"total_gb": 128}, "gpus": []},
                            },
                            "n2": {"type": "cpu"},
                        }
                    }
                },
                "settings": {"hardware_defaults": {"cpu": {"cpu_cores": 4, "gpu_count": 0}}},
            }
        )
    )
    config = ClusterConfig(str(path))
    assert config.get_node_hardware("T", "n1") == {"cpu_cores": 8, "gpu_count": 0, "memory_gb": 128}
    assert config.get_node_hardware("T", "n2")["memory_gb"] == 0
