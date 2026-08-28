"""Tests for merging agent-reported node hardware into clusters.yaml."""

from datetime import datetime

import pytest
import yaml
from backend.app.api import agent as agent_api
from backend.app.core.agent_auth import verify_agent_api_key
from backend.app.services.node_discovery import NodeDiscoveryService
from fastapi import FastAPI
from fastapi.testclient import TestClient

INVENTORY = {
    "nodes": {
        "gpu01": {"cpu_cores": 48, "memory_gb": 376, "gpus": [{"model": "a100", "count": 4}], "partitions": ["gpu"]},
        "cpu01": {"cpu_cores": 24, "memory_gb": 188, "gpus": [], "partitions": ["general"]},
    }
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
    result = NodeDiscoveryService(config_path).sync_hardware("TEST", INVENTORY)

    node = load(config_path)["node_labels"]["gpu01"]
    assert result == {"added": 1, "updated": 1}
    assert node["synonyms"] == ["GPU01"]
    assert node["description"] == "Hand-written description"
    assert node["hardware"]["cpu"]["cores"] == 48
    assert node["hardware"]["ram"]["total_gb"] == 376
    assert node["hardware"]["gpus"] == [{"model": "a100", "count": 4}]
    assert node["partitions"] == ["gpu"]


def test_sync_sets_type_from_gpus_but_keeps_special_types(config_path):
    login = {"cpu_cores": 8, "memory_gb": 32, "gpus": [{"model": "t4", "count": 1}], "partitions": []}
    inventory = {"nodes": {**INVENTORY["nodes"], "login01": login}}
    NodeDiscoveryService(config_path).sync_hardware("TEST", inventory)

    labels = load(config_path)["node_labels"]
    assert labels["gpu01"]["type"] == "gpu"
    assert labels["cpu01"]["type"] == "cpu"
    assert labels["login01"]["type"] == "login"


def test_sync_adds_new_nodes_and_keeps_unreported_nodes(config_path):
    NodeDiscoveryService(config_path).sync_hardware("TEST", INVENTORY)

    labels = load(config_path)["node_labels"]
    assert labels["cpu01"]["description"] == "Node cpu01"
    assert labels["cpu01"]["synonyms"] == []
    assert labels["old01"]["description"] == "Decommissioned"


def test_sync_records_timestamp(config_path):
    NodeDiscoveryService(config_path).sync_hardware("TEST", INVENTORY)

    stamp = load(config_path)["metadata"]["last_hardware_sync"]
    assert datetime.fromisoformat(stamp).tzinfo is not None


def test_sync_creates_cluster_when_missing(config_path):
    result = NodeDiscoveryService(config_path).sync_hardware("NEW", INVENTORY)

    assert result == {"added": 2, "updated": 0}
    assert set(yaml.safe_load(config_path.read_text())["clusters"]["NEW"]["node_labels"]) == {"gpu01", "cpu01"}


def test_sync_rejects_invalid_inventory(config_path):
    with pytest.raises(ValueError, match="nodes"):
        NodeDiscoveryService(config_path).sync_hardware("TEST", {"foo": 1})


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
    assert response.json()["added"] == 1
    assert response.json()["updated"] == 1
    assert reloaded == [True]
    assert load(config_path)["node_labels"]["cpu01"]["hardware"]["cpu"]["cores"] == 24


def test_upload_config_endpoint_rejects_non_inventory(client):
    test_client, _ = client
    response = test_client.post(
        "/api/agent/upload-config",
        files={"file": ("x.yaml", yaml.dump({"clusters": {}}), "application/x-yaml")},
    )
    assert response.status_code == 400
