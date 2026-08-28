"""Tests for the per-cluster admin endpoints."""

import pytest
import yaml
from backend.app.api import cluster_admin
from backend.app.core.admin_auth import get_current_admin
from backend.app.db.clusters import ClusterDB
from backend.app.services.cluster_config_store import ClusterConfigStore
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeDatastore:
    def get_min_max_dates(self, hostname):
        return ("2026-01-12", "2026-08-27") if hostname == "DAIC" else (None, None)


@pytest.fixture
def env(tmp_path, monkeypatch):
    config_path = tmp_path / "clusters.yaml"
    config_path.write_text(
        yaml.dump(
            {
                "clusters": {
                    "DAIC": {
                        "display_name": "DAIC",
                        "description": "d",
                        "metadata": {
                            "location": "Delft",
                            "last_hardware_sync": "2026-08-28T12:18:17+00:00",
                            "slurm_version": "23.11",
                        },
                        "node_labels": {
                            "gpu01": {"synonyms": [], "type": "gpu", "hardware": {"cpu": {"cores": 48}}},
                            "old01": {"synonyms": [], "type": "cpu"},
                        },
                        "partition_labels": {"general": {"slurm": {"default": True}}},
                        "account_labels": {"ewi": {"slurm": {"description": "EWI"}}},
                    }
                },
                "settings": {},
            }
        )
    )
    db = ClusterDB(str(tmp_path / "clusters.json"))
    record = db.create_cluster(name="DAIC", description="d", contact_email="a@b", location="Delft")
    db.create_cluster(name="NOYAML")
    monkeypatch.setattr(cluster_admin, "get_store", lambda: ClusterConfigStore(config_path))
    monkeypatch.setattr(cluster_admin, "get_cluster_db", lambda: db)
    monkeypatch.setattr(cluster_admin, "get_datastore", FakeDatastore)
    reloads = []
    monkeypatch.setattr(cluster_admin, "reload_cluster_config", lambda: reloads.append(True))
    app = FastAPI()
    app.include_router(cluster_admin.router, prefix="/api/admin")
    app.dependency_overrides[get_current_admin] = lambda: "admin"
    return TestClient(app), config_path, db, record, reloads


def load(config_path):
    return yaml.safe_load(config_path.read_text())["clusters"]["DAIC"]


def test_status_reports_sync_and_data(env):
    client, _, _, record, _ = env
    body = client.get("/api/admin/clusters/by-name/DAIC/status").json()

    assert body["id"] == record["id"]
    assert body["config_present"] is True
    assert body["identity"]["location"] == "Delft"
    assert body["sync"] == {
        "last_sync": "2026-08-28T12:18:17+00:00",
        "slurm_version": "23.11",
        "slurm_cluster_name": None,
        "nodes_synced": 1,
        "nodes_from_data_only": 1,
        "partitions": 1,
        "accounts": 1,
    }
    assert body["data"]["min_date"] == "2026-01-12"
    assert body["data"]["total_jobs_submitted"] == 0


def test_status_for_cluster_without_yaml_entry(env):
    client, *_ = env
    body = client.get("/api/admin/clusters/by-name/NOYAML/status").json()
    assert body["config_present"] is False
    assert body["sync"]["nodes_synced"] == 0
    assert client.get("/api/admin/clusters/by-name/NOPE/status").status_code == 404


def test_identity_update_writes_yaml_and_mirrors_record(env):
    client, config_path, db, record, reloads = env
    response = client.patch(
        "/api/admin/clusters/by-name/DAIC/identity",
        json={"display_name": "DAIC cluster", "contact": "ops@tudelft.nl", "owner": "REIT"},
    )

    assert response.status_code == 200, response.text
    entry = load(config_path)
    assert entry["display_name"] == "DAIC cluster"
    assert entry["metadata"]["contact"] == "ops@tudelft.nl"
    assert entry["metadata"]["owner"] == "REIT"
    assert entry["metadata"]["location"] == "Delft"
    assert db.get_cluster(record["id"])["contact_email"] == "ops@tudelft.nl"
    assert reloads == [True]


def test_node_label_update_keeps_hardware(env):
    client, config_path, *_ = env
    response = client.patch(
        "/api/admin/clusters/by-name/DAIC/nodes/gpu01",
        json={"synonyms": ["GPU01", "gpu-01"], "description": "A40 node", "type": "gpu"},
    )

    assert response.status_code == 200, response.text
    node = load(config_path)["node_labels"]["gpu01"]
    assert node["synonyms"] == ["GPU01", "gpu-01"]
    assert node["description"] == "A40 node"
    assert node["hardware"] == {"cpu": {"cores": 48}}


def test_node_label_update_rejects_unknown_type_and_node(env):
    client, *_ = env
    assert client.patch("/api/admin/clusters/by-name/DAIC/nodes/gpu01", json={"type": "quantum"}).status_code == 422
    assert client.patch("/api/admin/clusters/by-name/DAIC/nodes/nope", json={"type": "cpu"}).status_code == 404


def test_partition_and_account_updates_keep_slurm_facts(env):
    client, config_path, *_ = env
    assert (
        client.patch(
            "/api/admin/clusters/by-name/DAIC/partitions/general", json={"display_name": "General"}
        ).status_code
        == 200
    )
    assert (
        client.patch(
            "/api/admin/clusters/by-name/DAIC/accounts/ewi", json={"short_name": "EWI", "faculty": "EEMCS"}
        ).status_code
        == 200
    )

    entry = load(config_path)
    assert entry["partition_labels"]["general"] == {"slurm": {"default": True}, "display_name": "General"}
    assert entry["account_labels"]["ewi"] == {"slurm": {"description": "EWI"}, "short_name": "EWI", "faculty": "EEMCS"}


def test_config_entry_endpoint(env):
    client, *_ = env
    assert client.get("/api/admin/clusters/by-name/DAIC/config").json()["display_name"] == "DAIC"
    assert client.get("/api/admin/clusters/by-name/NOYAML/config").status_code == 404
