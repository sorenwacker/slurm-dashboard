"""Tests for memory fields produced by the exporter."""

import pandas as pd

from slurm_usage_history.scripts.exporter import SlurmDataExtractor


def make_extractor():
    return SlurmDataExtractor(cluster_name="TEST")


def raw_rows():
    base = {
        "QOS": "normal",
        "Account": "acc",
        "Partition": "general",
        "Submit": "2026-01-01T00:00:00",
        "Start": "2026-01-01T01:00:00",
        "End": "2026-01-01T03:00:00",
        "State": "COMPLETED",
        "Elapsed": "02:00:00",
        "AllocCPUS": "4",
        "NodeList": "node1",
        "Cluster": "TEST",
    }
    return [
        {**base, "JobID": "100", "User": "alice", "AllocTRES": "cpu=4,mem=16G,node=1", "ReqMem": "16G", "MaxRSS": ""},
        {
            **base,
            "JobID": "100.batch",
            "User": "",
            "AllocTRES": "cpu=4,mem=16G,node=1",
            "ReqMem": "",
            "MaxRSS": "1000K",
        },
        {**base, "JobID": "100.0", "User": "", "AllocTRES": "cpu=4,mem=16G,node=1", "ReqMem": "", "MaxRSS": "2G"},
        {**base, "JobID": "101", "User": "bob", "AllocTRES": "cpu=4,node=1", "ReqMem": "4000Mc", "MaxRSS": ""},
        {**base, "JobID": "102", "User": "carol", "AllocTRES": "", "ReqMem": "", "MaxRSS": ""},
    ]


def test_format_jobs_folds_step_maxrss_into_job():
    jobs = {j["JobID"]: j for j in make_extractor().format_jobs(pd.DataFrame(raw_rows()))}

    assert set(jobs) == {"100", "101", "102"}
    assert jobs["100"]["ReqMemMB"] == 16384.0
    assert jobs["100"]["MaxRSSMB"] == 2048.0


def test_format_jobs_falls_back_to_reqmem_per_cpu():
    jobs = {j["JobID"]: j for j in make_extractor().format_jobs(pd.DataFrame(raw_rows()))}
    assert jobs["101"]["ReqMemMB"] == 16000.0
    assert jobs["101"]["MaxRSSMB"] is None


def test_format_jobs_leaves_memory_unknown_when_absent():
    jobs = {j["JobID"]: j for j in make_extractor().format_jobs(pd.DataFrame(raw_rows()))}
    assert jobs["102"]["ReqMemMB"] is None
    assert jobs["102"]["MaxRSSMB"] is None


def test_sacct_format_requests_reqmem():
    assert "ReqMem" in SlurmDataExtractor.SACCT_FORMAT.split(",")
