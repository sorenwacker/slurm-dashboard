"""Tests for the waiting-time versus job-duration scatter sample."""

import pandas as pd
from backend.app.services.charts.distribution_generators import generate_wait_duration_scatter


def frame(n=6):
    return pd.DataFrame(
        {
            "WaitingTimeHours": [0.0, 0.5, 2.0, 24.0, None, 1.0][:n],
            "ElapsedHours": [1.0, 2.0, 0.0, 48.0, 1.0, None][:n],
            "Account": ["a", "a", "b", "b", "a", "b"][:n],
        }
    )


def test_scatter_pairs_and_display_floor():
    result = generate_wait_duration_scatter(frame(), None)
    (series,) = result["series"]
    # rows with a missing value drop out; zeros are floored at one minute for the log axes
    assert series["x"] == [1.0, 2.0, 1 / 60, 48.0]
    assert series["y"] == [1 / 60, 0.5, 2.0, 24.0]
    assert result["sampled"] is False
    assert result["total_jobs"] == 4


def test_scatter_groups_by_colour_dimension():
    result = generate_wait_duration_scatter(frame(), "Account")
    by_name = {s["name"]: s for s in result["series"]}
    assert set(by_name) == {"a", "b"}
    assert len(by_name["a"]["x"]) == 2
    assert len(by_name["b"]["x"]) == 2


def test_scatter_samples_deterministically_above_the_cap():
    big = pd.DataFrame(
        {
            "WaitingTimeHours": [float(i % 50) for i in range(20000)],
            "ElapsedHours": [float(i % 70) + 0.1 for i in range(20000)],
            "Account": ["a"] * 20000,
        }
    )
    first = generate_wait_duration_scatter(big, None, max_points=5000)
    second = generate_wait_duration_scatter(big, None, max_points=5000)
    (s1,), (s2,) = first["series"], second["series"]
    assert len(s1["x"]) == 5000
    assert s1["x"] == s2["x"]
    assert first["sampled"] is True
    assert first["total_jobs"] == 20000


def test_scatter_empty_without_columns():
    assert generate_wait_duration_scatter(frame().drop(columns=["ElapsedHours"]), None) == {
        "series": [],
        "sampled": False,
        "total_jobs": 0,
    }
