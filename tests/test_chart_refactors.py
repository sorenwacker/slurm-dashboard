"""Hand-computed expectations for the vectorized trend and timeline generators."""

import pandas as pd
import pytest
from backend.app.services.charts.distribution_generators import generate_waiting_times_trends
from backend.app.services.charts.timeline_generators import generate_jobs_over_time


def frame():
    return pd.DataFrame(
        {
            "StartYearMonth": pd.to_datetime(["2026-01-01"] * 4 + ["2026-02-01"] * 2),
            "SubmitYearMonth": pd.to_datetime(["2026-01-01"] * 4 + ["2026-02-01"] * 2),
            "WaitingTimeHours": [1.0, 2.0, 3.0, 4.0, 10.0, 20.0],
            "Account": ["a", "a", "b", "b", "a", None],
        }
    )


def test_trends_single_line_statistics():
    result = generate_waiting_times_trends(frame(), "month", None)
    assert result["x"] == sorted(frame()["StartYearMonth"].unique())
    assert result["stats"]["mean"] == [2.5, 15.0]
    assert result["stats"]["median"] == [2.5, 15.0]
    assert result["stats"]["max"] == [4.0, 20.0]
    assert result["stats"]["p25"] == [1.75, 12.5]
    assert result["stats"]["p99"] == pytest.approx([3.97, 19.9])


def test_trends_multi_line_uses_zero_for_missing_periods():
    result = generate_waiting_times_trends(frame(), "month", "Account")
    assert [s["name"] for s in result["series"]] == ["a", "b"]
    assert result["series"][0]["data"] == [1.5, 10.0]
    assert result["series"][1]["data"] == [3.5, 0.0]


def test_timeline_series_are_pivoted_per_period():
    result = generate_jobs_over_time(frame(), "month", "Account")
    series = {s["name"]: s["data"] for s in result["series"]}
    assert series["a"] == [2, 1]
    assert series["b"] == [2, 0]
    assert all(isinstance(v, int) for v in series["a"])


def test_distribution_generators_keyword_interface():
    """These call _aggregate_period_distribution with keyword arguments; renames break at runtime."""
    from backend.app.services.charts.distribution_generators import (
        generate_active_users_distribution,
        generate_jobs_distribution,
    )

    df = frame().assign(User=["u1", "u2", "u1", "u2", "u3", "u3"])
    assert generate_active_users_distribution(df, "month") is not None
    assert generate_jobs_distribution(df, "month") is not None


def test_job_duration_histogram_has_fine_short_bins():
    from backend.app.services.charts.distribution_generators import generate_job_duration_hist

    df = pd.DataFrame({"ElapsedHours": [10 / 3600, 2 / 60, 7 / 60, 20 / 60, 0.75, 2.0]})
    result = generate_job_duration_hist(df)
    assert result["x"][:5] == ["< 30s", "30s - 5min", "5 - 10min", "10 - 30min", "30min - 1h"]
    by_bin = dict(zip(result["x"], result["y"], strict=True))
    for bin_label in ("< 30s", "30s - 5min", "5 - 10min", "10 - 30min", "30min - 1h", "1h - 4h"):
        assert by_bin[bin_label] == pytest.approx(100 / 6)


def test_duration_stacked_bins_match_histogram_edges():
    from backend.app.services.charts.distribution_generators import DURATION_BINS, DURATION_COLORS

    assert [b[0] for b in DURATION_BINS[:4]] == ["< 30s", "30s-5min", "5-10min", "10-30min"]
    assert len(DURATION_BINS) == len(DURATION_COLORS)


def test_waiting_time_histogram_has_fine_short_bins():
    from backend.app.services.charts.distribution_generators import (
        generate_waiting_times_hist,
    )

    df = pd.DataFrame(
        {
            "WaitingTimeHours": [10 / 3600, 2 / 60, 7 / 60, 20 / 60, 0.75, 2.0],
            "User": ["u1"] * 6,
        }
    )
    result = generate_waiting_times_hist(df)
    assert result["x"][:5] == ["< 30s", "30s - 5min", "5 - 10min", "10 - 30min", "30min - 1h"]
    counts = dict(zip(result["x"], result["y"], strict=True))
    for bin_label in ("< 30s", "30s - 5min", "5 - 10min", "10 - 30min", "30min - 1h", "1h - 4h"):
        assert counts[bin_label] > 0


def test_waiting_stacked_bins_match_histogram_edges():
    from backend.app.services.charts.distribution_generators import (
        TIME_HISTOGRAM_BIN_EDGES,
        WAITING_TIME_BINS,
        WAITING_TIME_COLORS,
    )

    assert [b[0] for b in WAITING_TIME_BINS[:4]] == ["< 30s", "30s-5min", "5-10min", "10-30min"]
    assert [b[1] for b in WAITING_TIME_BINS] == TIME_HISTOGRAM_BIN_EDGES[:-1]
    assert len(WAITING_TIME_BINS) == len(WAITING_TIME_COLORS)
