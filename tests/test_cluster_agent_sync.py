"""Tests for the sync-config agent command."""

import json

import pytest

from slurm_usage_history.scripts import cluster_agent


@pytest.fixture
def agent_config(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"api_url": "https://dash.example", "api_key": "k", "timeout": 5}))
    return path


def test_sync_config_posts_inventory(agent_config, monkeypatch):
    inventory = {"nodes": {"n1": {"cpu_cores": 8, "memory_gb": 32, "gpus": [], "partitions": []}}}
    monkeypatch.setattr(cluster_agent, "collect_cluster_inventory", lambda: inventory)
    posted = {}

    class Response:
        status_code = 201

        def json(self):
            return {"nodes": {"added": 1, "updated": 0}}

    def fake_post(url, **kwargs):
        posted["url"] = url
        posted["kwargs"] = kwargs
        return Response()

    monkeypatch.setattr(cluster_agent.requests, "post", fake_post)

    result = cluster_agent.sync_config(agent_config, dry_run=False)

    assert result == {"nodes": {"added": 1, "updated": 0}}
    assert posted["url"] == "https://dash.example/api/agent/upload-config"
    assert posted["kwargs"]["headers"] == {"X-API-Key": "k"}
    assert posted["kwargs"]["timeout"] == 5
    assert "nodes:" in posted["kwargs"]["files"]["file"][1]


def test_sync_config_dry_run_does_not_post(agent_config, monkeypatch, capsys):
    monkeypatch.setattr(cluster_agent, "collect_cluster_inventory", lambda: {"nodes": {"n1": {"cpu_cores": 8}}})
    monkeypatch.setattr(cluster_agent.requests, "post", lambda *_a, **_k: pytest.fail("must not post"))

    result = cluster_agent.sync_config(agent_config, dry_run=True)

    assert result is None
    assert "n1" in capsys.readouterr().out


def test_sync_config_raises_on_server_error(agent_config, monkeypatch):
    monkeypatch.setattr(cluster_agent, "collect_cluster_inventory", lambda: {"nodes": {}})

    class Response:
        status_code = 500
        text = "boom"

    monkeypatch.setattr(cluster_agent.requests, "post", lambda *_a, **_k: Response())
    with pytest.raises(RuntimeError, match="boom"):
        cluster_agent.sync_config(agent_config, dry_run=False)


def test_run_command_syncs_before_exporter(agent_config, monkeypatch):
    order = []
    monkeypatch.setattr(cluster_agent, "sync_config", lambda path, dry_run: order.append(("sync", str(path), dry_run)))

    class Result:
        returncode = 0

    monkeypatch.setattr(cluster_agent.subprocess, "run", lambda cmd: order.append(("exporter", cmd)) or Result())
    args = cluster_agent.build_parser().parse_args(["run", "--config", str(agent_config), "--sync-config"])

    with pytest.raises(SystemExit) as exc:
        args.func(args)

    assert exc.value.code == 0
    assert order[0][0] == "sync"
    assert order[1][0] == "exporter"


def test_run_command_continues_when_sync_fails(agent_config, monkeypatch, capsys):
    def failing_sync(_path, _dry_run):
        message = "scontrol missing"
        raise RuntimeError(message)

    monkeypatch.setattr(cluster_agent, "sync_config", failing_sync)

    class Result:
        returncode = 0

    monkeypatch.setattr(cluster_agent.subprocess, "run", lambda _cmd: Result())
    args = cluster_agent.build_parser().parse_args(["run", "--config", str(agent_config), "--sync-config"])

    with pytest.raises(SystemExit) as exc:
        args.func(args)

    assert exc.value.code == 0
    assert "scontrol missing" in capsys.readouterr().err
