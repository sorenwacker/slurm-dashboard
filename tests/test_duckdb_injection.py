"""Request values must reach DuckDB as bound parameters, never as SQL text."""

import pandas as pd
import pytest

from slurm_usage_history.app.duckdb_datastore import DuckDBDataStore, Singleton

EMPTY_FILTER_VALUES = {"partitions": [], "accounts": [], "users": [], "qos": [], "states": []}


@pytest.fixture(autouse=True)
def reset_datastore_singleton():
    Singleton._instances = {}


@pytest.fixture
def store(tmp_path):
    data_dir = tmp_path / "host" / "data"
    data_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "JobID": ["1", "2"],
            "User": ["alice", "bob"],
            "Account": ["acc-a", "acc-b"],
            "Partition": ["general,gpu", "cpu"],
            "QOS": ["short", "long"],
            "State": ["COMPLETED", "FAILED"],
            "Submit": pd.to_datetime(["2026-01-01T00:00:00", "2026-02-01T00:00:00"]),
            "Start": pd.to_datetime(["2026-01-01T01:00:00", "2026-02-01T01:00:00"]),
            "End": pd.to_datetime(["2026-01-01T03:00:00", "2026-02-01T03:00:00"]),
            "NodeList": ["n1", "n2"],
            "CPUHours": [1.0, 1.0],
            "GPUHours": [0.0, 0.0],
        }
    ).to_parquet(data_dir / "jobs.parquet")
    return DuckDBDataStore(str(tmp_path))


def test_quoted_list_value_is_matched_literally(store):
    df = store.filter("host", users=["x') OR 1=1 --"], format_accounts=False)
    assert df.empty


def test_injected_statement_is_not_executed(store, tmp_path):
    target = tmp_path / "pwned.txt"
    payload = f"x'); COPY (SELECT 'pwned') TO '{target}' (FORMAT CSV, HEADER false); --"

    df = store.filter("host", states=[payload], format_accounts=False)

    assert df.empty
    assert not target.exists()


def test_quoted_partition_value_is_matched_literally(store):
    df = store.filter("host", partitions=["x') OR 1=1 --"], format_accounts=False)
    assert df.empty


def test_malformed_date_is_rejected_not_executed(store):
    with pytest.raises(ValueError, match="unable to parse"):
        store.filter("host", start_date="2026-01-01' OR 1=1 --", format_accounts=False)
    with pytest.raises(ValueError, match="unable to parse"):
        store.get_filter_values_for_period("host", start_date="2026-01-01' OR 1=1 --")


def test_quoted_value_in_period_lookup_is_literal(store, tmp_path):
    target = tmp_path / "pwned2.txt"
    payload = f"2026-01-01'); COPY (SELECT 'pwned') TO '{target}' (FORMAT CSV, HEADER false); --"
    with pytest.raises(ValueError, match="unable to parse"):
        store.get_filter_values_for_period("host", end_date=payload)
    assert not target.exists()


def test_unknown_hostname_returns_empty_results(store):
    assert store.filter("../host", format_accounts=False).empty
    assert store.filter("host') UNION ALL SELECT 1 --", format_accounts=False).empty
    assert store.get_filter_values_for_period("../host") == EMPTY_FILTER_VALUES


def test_legitimate_filters_still_apply(store):
    by_user = store.filter("host", users=["alice"], format_accounts=False)
    by_partition = store.filter("host", partitions=["gpu"], format_accounts=False)
    by_date = store.filter("host", start_date="2026-01-15", end_date="2026-02-15", format_accounts=False)
    by_state_and_qos = store.filter("host", states=["FAILED"], qos=["long"], format_accounts=False)
    in_period = store.get_filter_values_for_period("host", start_date="2026-01-15", end_date="2026-02-15")

    assert list(by_user["JobID"]) == ["1"]
    assert list(by_partition["JobID"]) == ["1"]
    assert list(by_date["JobID"]) == ["2"]
    assert list(by_state_and_qos["JobID"]) == ["2"]
    assert in_period == {
        "partitions": ["cpu"],
        "accounts": ["acc-b"],
        "users": ["bob"],
        "qos": ["long"],
        "states": ["FAILED"],
    }
