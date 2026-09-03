"""Agent uploads stay inside the key's cluster directory and must be parquet."""

import io

import pandas as pd
import pytest
from backend.app import datastore_singleton
from backend.app.api import agent as agent_api
from backend.app.core.agent_auth import verify_agent_api_key
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeDatastore:
    def check_for_updates(self):
        return False


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_api.get_settings(), "data_path", str(tmp_path))
    monkeypatch.setattr(datastore_singleton, "get_datastore", FakeDatastore)
    app = FastAPI()
    app.include_router(agent_api.router, prefix="/api")
    app.dependency_overrides[verify_agent_api_key] = lambda: "TEST"
    return TestClient(app), tmp_path


def parquet_bytes() -> bytes:
    buffer = io.BytesIO()
    pd.DataFrame({"JobID": ["1"], "Submit": pd.to_datetime(["2026-01-01"])}).to_parquet(buffer)
    return buffer.getvalue()


def upload(test_client, filename, content):
    return test_client.post("/api/agent/upload", files={"file": (filename, content, "application/octet-stream")})


def test_plain_filename_is_stored_in_the_cluster_directory(client):
    test_client, data_path = client
    response = upload(test_client, "jobs_2026.parquet", parquet_bytes())
    assert response.status_code == 201, response.text
    assert (data_path / "TEST" / "data" / "jobs_2026.parquet").exists()
    assert response.json()["path"] == "TEST/data/jobs_2026.parquet"


@pytest.mark.parametrize("filename", ["../../OTHER/data/jobs.parquet", "sub/jobs.parquet", "..parquet", ".parquet"])
def test_filename_with_path_components_is_rejected(client, filename):
    test_client, data_path = client
    response = upload(test_client, filename, parquet_bytes())
    assert response.status_code == 400, response.text
    written = [p for p in data_path.rglob("*") if p.is_file()]
    assert written == []


def test_non_parquet_content_is_rejected(client):
    test_client, data_path = client
    response = upload(test_client, "jobs.parquet", b"<html>not parquet</html>")
    assert response.status_code == 400, response.text
    assert not (data_path / "TEST" / "data" / "jobs.parquet").exists()
