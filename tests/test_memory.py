"""Tests for memory value parsing and derived memory columns."""

import math

import pandas as pd
import pytest

from slurm_usage_history.app.duckdb_datastore import DuckDBDataStore
from slurm_usage_history.memory import add_memory_columns, parse_memory_to_mb, parse_reqmem_to_mb


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("16G", 16384.0),
        ("1.5G", 1536.0),
        ("4000M", 4000.0),
        ("512K", 0.5),
        ("1T", 1048576.0),
        ("2048", 2048.0),
        ("16GB", 16384.0),
        ("0", 0.0),
        ("", None),
        (None, None),
        (float("nan"), None),
        ("junk", None),
    ],
)
def test_parse_memory_to_mb(value, expected):
    assert parse_memory_to_mb(value) == expected


@pytest.mark.parametrize(
    ("value", "cpus", "nodes", "expected"),
    [
        ("4000Mc", 4, 1, 16000.0),
        ("64Gn", 1, 2, 131072.0),
        ("16G", 8, 1, 16384.0),
        ("", 4, 1, None),
    ],
)
def test_parse_reqmem_to_mb(value, cpus, nodes, expected):
    assert parse_reqmem_to_mb(value, cpus, nodes) == expected


def test_add_memory_columns_derives_gb_hours():
    df = pd.DataFrame({"ReqMemMB": [16384.0, None], "ElapsedHours": [2.0, 3.0]})
    out = add_memory_columns(df)
    assert out["MemGBHours"].tolist()[0] == 32.0
    assert math.isnan(out["MemGBHours"].tolist()[1])


def test_add_memory_columns_parses_legacy_maxrss_strings():
    df = pd.DataFrame({"MaxRSS": ["2048K", "1G", ""]})
    out = add_memory_columns(df)
    assert out["MaxRSSMB"].tolist()[:2] == [2.0, 1024.0]
    assert math.isnan(out["MaxRSSMB"].tolist()[2])


def test_add_memory_columns_keeps_existing_and_fills_gaps_from_legacy():
    df = pd.DataFrame({"MaxRSSMB": [5.0, None], "MaxRSS": ["1G", "1G"], "CPUHours": [1.0, 1.0]})
    out = add_memory_columns(df)
    assert out["MaxRSSMB"].tolist() == [5.0, 1024.0]
    assert "MemGBHours" not in out.columns


def test_duckdb_filter_derives_memory_columns_from_mixed_files(tmp_path):
    """Old parquet files (MaxRSS strings, no ReqMemMB) and new ones combine without zero-filling."""
    data_dir = tmp_path / "host" / "data"
    data_dir.mkdir(parents=True)
    common = {
        "User": ["u"],
        "Account": ["a"],
        "Partition": ["p"],
        "QOS": ["q"],
        "State": ["COMPLETED"],
        "Submit": pd.to_datetime(["2026-01-01T00:00:00"]),
        "Start": pd.to_datetime(["2026-01-01T01:00:00"]),
        "End": pd.to_datetime(["2026-01-01T03:00:00"]),
        "NodeList": ["n1"],
        "CPUHours": [8.0],
        "GPUHours": [0.0],
    }
    pd.DataFrame({**common, "JobID": ["old"], "MaxRSS": ["512M"]}).to_parquet(data_dir / "jobs_old.parquet")
    pd.DataFrame({**common, "JobID": ["new"], "ReqMemMB": [16384.0], "MaxRSSMB": [4096.0]}).to_parquet(
        data_dir / "jobs_new.parquet"
    )

    df = DuckDBDataStore(str(tmp_path)).filter("host", format_accounts=False).set_index("JobID")

    assert df.loc["new", "MemGBHours"] == 32.0
    assert df.loc["new", "MaxRSSMB"] == 4096.0
    assert math.isnan(df.loc["old", "MemGBHours"])
    assert df.loc["old", "MaxRSSMB"] == 512.0
