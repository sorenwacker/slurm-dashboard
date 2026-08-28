"""Tests for cluster creation ordering between clusters.yaml and the cluster database."""

import pytest
from backend.app.api import admin as admin_api
from backend.app.core.admin_auth import get_current_admin
from backend.app.db.clusters import ClusterDB
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = ClusterDB(str(tmp_path / "clusters.json"))
    monkeypatch.setattr(admin_api, "get_cluster_db", lambda: db)
    monkeypatch.setattr(admin_api, "find_existing_data_directory", lambda _name: None)
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api/admin")
    app.dependency_overrides[get_current_admin] = lambda: "admin"
    return TestClient(app), db


def test_unwritable_yaml_creates_no_cluster_record(client, monkeypatch):
    test_client, db = client

    def unwritable(**_kwargs):
        raise PermissionError(13, "Permission denied", "clusters.yaml")

    monkeypatch.setattr(admin_api, "ensure_cluster_yaml_config", unwritable)

    response = test_client.post("/api/admin/clusters", json={"name": "NEW"})

    assert response.status_code == 500
    assert "Permission denied" in response.json()["detail"]
    assert db.get_cluster_by_name("NEW") is None


def test_yaml_written_before_record(client, monkeypatch):
    test_client, db = client
    written = []
    monkeypatch.setattr(
        admin_api, "ensure_cluster_yaml_config", lambda **kwargs: written.append(kwargs["cluster_name"])
    )

    response = test_client.post("/api/admin/clusters", json={"name": "NEW", "description": "d"})

    assert response.status_code == 201
    assert written == ["NEW"]
    assert db.get_cluster_by_name("NEW")["description"] == "d"


def test_duplicate_name_rejected_before_yaml(client, monkeypatch):
    test_client, db = client
    db.create_cluster(name="NEW")
    monkeypatch.setattr(admin_api, "ensure_cluster_yaml_config", lambda **_kwargs: pytest.fail("must not touch yaml"))

    response = test_client.post("/api/admin/clusters", json={"name": "NEW"})

    assert response.status_code == 400
