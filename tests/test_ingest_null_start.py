"""Tests for ingesting jobs that never started (null Start/End)."""

import pandas as pd
import pytest
from backend.app.api import data as data_api
from backend.app.core.auth import verify_api_key
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeDB:
    def __init__(self):
        self.calls = []

    def update_submission_stats(self, hostname, count):
        self.calls.append((hostname, count))


class FakeDatastore:
    def load_data(self):
        pass

    def get_min_max_dates(self, _hostname):
        return (None, None)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(data_api.settings, "data_path", str(tmp_path))
    db = FakeDB()
    monkeypatch.setattr(data_api, "get_cluster_db", lambda: db)
    monkeypatch.setattr(data_api, "get_datastore", FakeDatastore)
    app = FastAPI()
    app.include_router(data_api.router, prefix="/api/data")
    app.dependency_overrides[verify_api_key] = lambda: "TEST"
    return TestClient(app), tmp_path, db


def job(job_id, start, end):
    return {
        "JobID": job_id,
        "User": "alice",
        "Account": "acc",
        "Partition": "general",
        "State": "CANCELLED" if start is None else "COMPLETED",
        "Submit": "2026-03-01T10:00:00",
        "Start": start,
        "End": end,
        "CPUHours": 0.0,
        "GPUHours": 0.0,
        "AllocCPUS": 0,
        "AllocGPUS": 0,
        "AllocNodes": 0,
        "NodeList": None,
        "ReqMemMB": 4096.0,
        "MaxRSSMB": None,
    }


def test_ingest_accepts_jobs_that_never_started(client):
    test_client, data_path, db = client
    payload = {
        "hostname": "DAIC (new)",
        "jobs": [job("1", None, None), job("2", "2026-03-01T11:00:00", "2026-03-01T12:00:00")],
    }

    response = test_client.post("/api/data/ingest", json=payload)

    assert response.status_code == 200, response.text
    df = pd.read_parquet(data_path / "DAIC (new)" / "data" / "jobs_2026.parquet").set_index("JobID")
    assert pd.isna(df.loc["1", "Start"])
    assert pd.isna(df.loc["1", "StartYearWeek"])
    assert pd.isna(df.loc["1", "ElapsedHours"])
    assert df.loc["2", "StartYearWeek"] == "2026-02-23"
    assert df.loc["2", "ElapsedHours"] == 1.0
    assert df.loc["2", "ReqMemMB"] == 4096.0
    assert db.calls == [("DAIC (new)", 2)]
