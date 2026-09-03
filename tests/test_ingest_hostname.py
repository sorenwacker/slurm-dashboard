"""Ingested jobs land in the directory of the cluster that owns the API key."""

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


JOB = {
    "JobID": "1",
    "User": "alice",
    "Account": "acc",
    "Partition": "general",
    "State": "COMPLETED",
    "Submit": "2026-03-01T10:00:00",
    "Start": "2026-03-01T11:00:00",
    "End": "2026-03-01T12:00:00",
}


def make_client(tmp_path, monkeypatch, key_cluster):
    monkeypatch.setattr(data_api.settings, "data_path", str(tmp_path))
    db = FakeDB()
    monkeypatch.setattr(data_api, "get_cluster_db", lambda: db)
    monkeypatch.setattr(data_api, "get_datastore", FakeDatastore)
    app = FastAPI()
    app.include_router(data_api.router, prefix="/api/data")
    app.dependency_overrides[verify_api_key] = lambda: key_cluster
    return TestClient(app), db


def files_under(path):
    return sorted(str(p.relative_to(path)) for p in path.rglob("*") if p.is_file())


def test_jobs_are_written_under_the_keys_cluster(tmp_path, monkeypatch):
    client, db = make_client(tmp_path, monkeypatch, "DAIC")

    response = client.post("/api/data/ingest", json={"hostname": "DAIC", "jobs": [JOB]})

    assert response.status_code == 200, response.text
    assert files_under(tmp_path) == ["DAIC/data/jobs_2026.parquet"]
    assert db.calls == [("DAIC", 1)]


def test_hostname_of_another_cluster_is_rejected(tmp_path, monkeypatch):
    client, db = make_client(tmp_path, monkeypatch, "DAIC")

    response = client.post("/api/data/ingest", json={"hostname": "OTHER", "jobs": [JOB]})

    assert response.status_code == 403, response.text
    assert files_under(tmp_path) == []
    assert db.calls == []


@pytest.mark.parametrize("hostname", ["../outside", "a/b", "..", ".hidden"])
def test_hostname_with_path_components_is_rejected_for_legacy_keys(tmp_path, monkeypatch, hostname):
    client, _ = make_client(tmp_path, monkeypatch, "unknown")

    response = client.post("/api/data/ingest", json={"hostname": hostname, "jobs": [JOB]})

    assert response.status_code == 400, response.text
    assert files_under(tmp_path) == []
    assert not (tmp_path.parent / "outside").exists()


def test_legacy_key_may_name_any_plain_cluster(tmp_path, monkeypatch):
    client, db = make_client(tmp_path, monkeypatch, "unknown")

    response = client.post("/api/data/ingest", json={"hostname": "DAIC (new)", "jobs": [JOB]})

    assert response.status_code == 200, response.text
    assert files_under(tmp_path) == ["DAIC (new)/data/jobs_2026.parquet"]
    assert db.calls == [("DAIC (new)", 1)]
