"""Tests for consumed core-time parsing and the efficiency charts."""

import pandas as pd
import pytest
from backend.app.services.charts.efficiency_generators import (
    generate_cpu_efficiency_over_time,
    generate_efficiency_by_group,
)

from slurm_usage_history.scripts.exporter import SlurmDataExtractor, parse_duration_hours


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("02:30:00", 2.5),
        ("1-12:00:00", 36.0),
        ("05:30", None if False else 5.5 / 60),
        ("00:00:00", 0.0),
        ("", None),
        ("None", None),
        (None, None),
        ("junk", None),
    ],
)
def test_parse_duration_hours(value, expected):
    result = parse_duration_hours(value)
    assert result == pytest.approx(expected) if expected is not None else result is None


def test_exporter_emits_cpu_used_hours():
    row = {
        "JobID": "1",
        "User": "alice",
        "QOS": "normal",
        "Account": "acc",
        "Partition": "general",
        "Submit": "2026-08-01T10:00:00",
        "Start": "2026-08-01T10:00:00",
        "End": "2026-08-01T12:00:00",
        "State": "COMPLETED",
        "Elapsed": "02:00:00",
        "AllocCPUS": "4",
        "NodeList": "n1",
        "AllocTRES": "cpu=4,mem=8G",
        "ReqMem": "",
        "MaxRSS": "",
        "TotalCPU": "06:00:00",
        "Cluster": "TEST",
    }
    (job,) = SlurmDataExtractor(cluster_name="TEST").format_jobs(pd.DataFrame([row]))
    assert job["CPUUsedHours"] == 6.0

    row["TotalCPU"] = ""
    (job,) = SlurmDataExtractor(cluster_name="TEST").format_jobs(pd.DataFrame([row]))
    assert job["CPUUsedHours"] is None


def frame():
    return pd.DataFrame(
        {
            "StartYearMonth": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-02-01", "2026-02-01"]),
            "Account": ["a", "b", "a", "b"],
            "CPUHours": [10.0, 10.0, 10.0, 10.0],
            "CPUUsedHours": [5.0, 10.0, None, 2.0],
            "ReqMemMB": [1000.0, 1000.0, None, 4000.0],
            "MaxRSSMB": [500.0, None, 200.0, 1000.0],
        }
    )


def test_cpu_efficiency_over_time_uses_only_jobs_reporting_used_time():
    result = generate_cpu_efficiency_over_time(frame(), "month")
    assert result["y"] == [75.0, 20.0]


def test_cpu_efficiency_empty_without_column():
    assert generate_cpu_efficiency_over_time(frame().drop(columns=["CPUUsedHours"]), "month") == {"x": [], "y": []}


def test_efficiency_by_group():
    result = generate_efficiency_by_group(frame(), "Account")
    assert result["x"] == ["a", "b"]
    series = {s["name"]: s["data"] for s in result["series"]}
    assert series["CPU"] == [50.0, pytest.approx(12.0 / 20.0 * 100)]
    assert series["Memory"] == [50.0, 25.0]


def test_efficiency_by_group_defaults_to_account():
    assert generate_efficiency_by_group(frame(), None)["x"] == ["a", "b"]
    empty = generate_efficiency_by_group(frame().drop(columns=["CPUUsedHours", "MaxRSSMB"]), "Account")
    assert empty == {"x": [], "series": []}
