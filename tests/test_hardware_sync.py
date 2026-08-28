"""Tests for merging the agent-reported cluster inventory into clusters.yaml."""

from datetime import datetime

import pytest
import yaml
from backend.app.api import agent as agent_api
from backend.app.core.agent_auth import verify_agent_api_key
from backend.app.services.node_discovery import NodeDiscoveryService
from fastapi import FastAPI
from fastapi.testclient import TestClient

INVENTORY = {
    "cluster": {"slurm_version": "23.11.4", "slurm_cluster_name": "daic"},
    "nodes": {
        "gpu01": {
            "cpu_cores": 48,
            "sockets": 2,
            "cores_per_socket": 24,
            "threads_per_core": 1,
            "memory_gb": 376,
            "gpus": [{"model": "a100", "count": 4}],
            "partitions": ["gpu"],
            "features": ["a100"],
        },
        "cpu01": {"cpu_cores": 24, "memory_gb": 188, "gpus": [], "partitions": ["general"], "features": []},
    },
    "partitions": {
        "general": {
            "nodes": "gpu01,cpu01",
            "total_cpus": 72,
            "total_nodes": 2,
            "max_time": "7-00:00:00",
            "default": True,
            "state": "UP",
        },
        "gpu": {
            "nodes": "gpu01",
            "total_cpus": 48,
            "total_nodes": 1,
            "max_time": "UNLIMITED",
            "default": False,
            "state": "UP",
        },
    },
    "accounts": {"ewi-insy": {"description": "INSY department", "organization": "ewi"}},
}


@pytest.fixture
def config_path(tmp_path):
    path = tmp_path / "clusters.yaml"
    path.write_text(
        yaml.dump(
            {
                "clusters": {
                    "TEST": {
                        "display_name": "Test",
                        "node_labels": {
                            "gpu01": {
                                "synonyms": ["GPU01"],
                                "type": "cpu",
                                "description": "Hand-written description",
                                "hardware": {"cpu": {"cores": 1}, "ram": {"total_gb": 1, "type": "DDR4"}},
                            },
                            "login01": {"synonyms": [], "type": "login", "description": "Login node"},
                            "old01": {"synonyms": [], "type": "cpu", "description": "Decommissioned"},
                        },
                        "partition_labels": {"general": {"display_name": "General", "description": "Hand-written"}},
                        "account_labels": {"ewi-insy": {"display_name": "INSY", "short_name": "INSY"}},
                    }
                },
                "settings": {"auto_generate_labels": False},
            }
        )
    )
    return path


def load(path):
    return yaml.safe_load(path.read_text())["clusters"]["TEST"]


def test_sync_overwrites_hardware_and_keeps_labels(config_path):
    result = NodeDiscoveryService(config_path).sync_cluster("TEST", INVENTORY)

    node = load(config_path)["node_labels"]["gpu01"]
    assert result["nodes"] == {"added": 1, "updated": 1}
    assert node["synonyms"] == ["GPU01"]
    assert node["description"] == "Hand-written description"
    assert node["hardware"]["cpu"] == {"cores": 48, "sockets": 2, "cores_per_socket": 24, "threads_per_core": 1}
    assert node["hardware"]["ram"]["total_gb"] == 376
    assert node["hardware"]["gpus"] == [{"model": "a100", "count": 4}]
    assert node["partitions"] == ["gpu"]
    assert node["features"] == ["a100"]


def test_sync_sets_type_from_gpus_but_keeps_special_types(config_path):
    login = {"cpu_cores": 8, "memory_gb": 32, "gpus": [{"model": "t4", "count": 1}], "partitions": [], "features": []}
    inventory = {**INVENTORY, "nodes": {**INVENTORY["nodes"], "login01": login}}
    NodeDiscoveryService(config_path).sync_cluster("TEST", inventory)

    labels = load(config_path)["node_labels"]
    assert labels["gpu01"]["type"] == "gpu"
    assert labels["cpu01"]["type"] == "cpu"
    assert labels["login01"]["type"] == "login"


def test_sync_adds_new_nodes_without_inventing_descriptions(config_path):
    NodeDiscoveryService(config_path).sync_cluster("TEST", INVENTORY)

    labels = load(config_path)["node_labels"]
    assert "description" not in labels["cpu01"]
    assert labels["cpu01"]["synonyms"] == []
    assert labels["cpu01"]["hardware"]["cpu"] == {"cores": 24}
    assert labels["old01"]["description"] == "Decommissioned"


def test_sync_writes_partition_and_account_facts_and_keeps_hand_edits(config_path):
    result = NodeDiscoveryService(config_path).sync_cluster("TEST", INVENTORY)

    cluster = load(config_path)
    assert result["partitions"] == {"added": 1, "updated": 1}
    assert result["accounts"] == {"added": 0, "updated": 1}
    general = cluster["partition_labels"]["general"]
    assert general["display_name"] == "General"
    assert general["description"] == "Hand-written"
    assert general["slurm"]["max_time"] == "7-00:00:00"
    assert general["slurm"]["default"] is True
    assert cluster["partition_labels"]["gpu"] == {"slurm": INVENTORY["partitions"]["gpu"]}
    account = cluster["account_labels"]["ewi-insy"]
    assert account["display_name"] == "INSY"
    assert account["slurm"] == {"description": "INSY department", "organization": "ewi"}


def test_sync_records_cluster_metadata_and_timestamp(config_path):
    NodeDiscoveryService(config_path).sync_cluster("TEST", INVENTORY)

    metadata = load(config_path)["metadata"]
    assert metadata["slurm_version"] == "23.11.4"
    assert metadata["slurm_cluster_name"] == "daic"
    assert datetime.fromisoformat(metadata["last_hardware_sync"]).tzinfo is not None


def test_sync_creates_cluster_when_missing(config_path):
    result = NodeDiscoveryService(config_path).sync_cluster("NEW", INVENTORY)

    assert result["nodes"] == {"added": 2, "updated": 0}
    assert set(yaml.safe_load(config_path.read_text())["clusters"]["NEW"]["node_labels"]) == {"gpu01", "cpu01"}


def test_sync_accepts_nodes_only_inventory(config_path):
    result = NodeDiscoveryService(config_path).sync_cluster("TEST", {"nodes": INVENTORY["nodes"]})
    assert result["partitions"] == {"added": 0, "updated": 0}


def test_sync_rejects_invalid_inventory(config_path):
    with pytest.raises(ValueError, match="nodes"):
        NodeDiscoveryService(config_path).sync_cluster("TEST", {"foo": 1})


@pytest.fixture
def client(config_path, monkeypatch):
    app = FastAPI()
    app.include_router(agent_api.router, prefix="/api")
    app.dependency_overrides[verify_agent_api_key] = lambda: "TEST"
    monkeypatch.setattr(agent_api, "get_cluster_config_path", lambda: config_path)
    reloaded = []
    monkeypatch.setattr(agent_api, "reload_cluster_config", lambda: reloaded.append(True))
    return TestClient(app), reloaded


def test_upload_config_endpoint_merges_and_reloads(client, config_path):
    test_client, reloaded = client
    response = test_client.post(
        "/api/agent/upload-config",
        files={"file": ("inventory.yaml", yaml.dump(INVENTORY), "application/x-yaml")},
    )

    assert response.status_code == 201, response.text
    assert response.json()["nodes"] == {"added": 1, "updated": 1}
    assert response.json()["accounts"] == {"added": 0, "updated": 1}
    assert reloaded == [True]
    assert load(config_path)["node_labels"]["cpu01"]["hardware"]["cpu"]["cores"] == 24


def test_upload_config_endpoint_rejects_non_inventory(client):
    test_client, _ = client
    response = test_client.post(
        "/api/agent/upload-config",
        files={"file": ("x.yaml", yaml.dump({"clusters": {}}), "application/x-yaml")},
    )
    assert response.status_code == 400
