"""Tests for hashed API key storage and the writable config path setting."""

import json

from backend.app.config import ClusterConfig, default_cluster_config_path
from backend.app.core.config import get_settings
from backend.app.db.clusters import ClusterDB, hash_api_key


def stored(db, name):
    return next(c for c in json.loads(db.db_path.read_text())["clusters"].values() if c["name"] == name)


def test_create_returns_key_once_and_stores_only_hash(tmp_path):
    db = ClusterDB(str(tmp_path / "clusters.json"))
    created = db.create_cluster(name="A")

    record = stored(db, "A")
    assert "api_key" not in record
    assert record["api_key_hash"] == hash_api_key(created["api_key"])
    assert record["api_key_prefix"] == created["api_key"][:8]
    assert "api_key" not in db.get_cluster(created["id"])
    assert db.verify_api_key(created["api_key"]) == "A"
    assert db.verify_api_key("wrong") is None


def test_rotate_and_deploy_key_exchange_issue_fresh_keys(tmp_path):
    db = ClusterDB(str(tmp_path / "clusters.json"))
    created = db.create_cluster(name="A")

    rotated = db.rotate_api_key(created["id"])
    assert db.verify_api_key(created["api_key"]) is None
    assert db.verify_api_key(rotated) == "A"

    deploy_key = db.generate_deploy_key(created["id"])
    exchanged = db.exchange_deploy_key(deploy_key, client_ip="10.0.0.1")
    assert exchanged["cluster_name"] == "A"
    assert db.verify_api_key(rotated) is None
    assert db.verify_api_key(exchanged["api_key"]) == "A"
    assert "api_key" not in stored(db, "A")


def test_legacy_plaintext_key_is_migrated_on_first_use(tmp_path):
    path = tmp_path / "clusters.json"
    path.write_text(
        json.dumps(
            {
                "clusters": {
                    "id1": {
                        "id": "id1",
                        "name": "OLD",
                        "api_key": "plain-key",
                        "active": True,
                        "api_key_created": "2025-01-01T00:00:00",
                    }
                },
                "stats": {},
            }
        )
    )
    db = ClusterDB(str(path))

    assert db.has_active_api_keys() is True
    assert db.verify_api_key("plain-key") == "OLD"
    record = stored(db, "OLD")
    assert "api_key" not in record
    assert record["api_key_hash"] == hash_api_key("plain-key")
    assert db.verify_api_key("plain-key") == "OLD"


def test_inactive_cluster_key_is_rejected(tmp_path):
    db = ClusterDB(str(tmp_path / "clusters.json"))
    created = db.create_cluster(name="A")
    db.update_cluster(created["id"], active=False)
    assert db.verify_api_key(created["api_key"]) is None


def test_cluster_config_path_setting(tmp_path, monkeypatch):
    monkeypatch.setenv("CLUSTER_CONFIG_PATH", str(tmp_path / "live" / "clusters.yaml"))
    get_settings.cache_clear()
    try:
        assert default_cluster_config_path() == tmp_path / "live" / "clusters.yaml"
        assert ClusterConfig().config_path == tmp_path / "live" / "clusters.yaml"
    finally:
        get_settings.cache_clear()


def test_cluster_config_path_default_inside_checkout(monkeypatch):
    monkeypatch.delenv("CLUSTER_CONFIG_PATH", raising=False)
    get_settings.cache_clear()
    try:
        assert default_cluster_config_path().parts[-3:] == ("backend", "config", "clusters.yaml")
    finally:
        get_settings.cache_clear()
