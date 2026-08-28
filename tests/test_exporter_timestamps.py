"""Tests for timestamp normalization in the exporter output."""

import pandas as pd

from slurm_usage_history.scripts.exporter import SlurmDataExtractor, normalize_timestamp


def test_normalize_timestamp_treats_slurm_placeholders_as_missing():
    for value in (None, "", "None", "Unknown", float("nan"), "nan"):
        assert normalize_timestamp(value) is None
    assert normalize_timestamp("2026-08-01T10:00:00") == "2026-08-01T10:00:00"
    assert normalize_timestamp(pd.Timestamp("2026-08-01T10:00:00")) == "2026-08-01 10:00:00"


def test_format_jobs_sends_null_for_jobs_that_never_started():
    row = {
        "JobID": "1",
        "User": "alice",
        "QOS": "normal",
        "Account": "acc",
        "Partition": "general",
        "Submit": "2026-08-01T10:00:00",
        "Start": "None",
        "End": "Unknown",
        "State": "CANCELLED by 1000",
        "Elapsed": "00:00:00",
        "AllocCPUS": "0",
        "NodeList": "None assigned",
        "AllocTRES": "",
        "ReqMem": "",
        "MaxRSS": "",
        "Cluster": "TEST",
    }
    (job,) = SlurmDataExtractor(cluster_name="TEST").format_jobs(pd.DataFrame([row]))
    assert job["Start"] is None
    assert job["End"] is None
    assert job["State"] == "CANCELLED"
