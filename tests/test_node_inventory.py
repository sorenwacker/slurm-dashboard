"""Tests for reading node hardware from scontrol output."""

import subprocess

import pytest

from slurm_usage_history.scripts.node_inventory import (
    build_inventory,
    collect_node_inventory,
    parse_gres,
    parse_scontrol_nodes,
)

SCONTROL_NODES = "\n".join(
    [
        "NodeName=gpu01 Arch=x86_64 CoresPerSocket=24 CPUAlloc=0 CPUTot=48 CPULoad=0.01 Gres=gpu:a100:4(S:0-1) "
        "NodeAddr=gpu01 RealMemory=385000 AllocMem=0 FreeMem=380000 Sockets=2 State=IDLE Partitions=gpu,general",
        "NodeName=cpu01 Arch=x86_64 CoresPerSocket=12 CPUAlloc=0 CPUTot=24 CPULoad=0.00 Gres=(null) "
        "NodeAddr=cpu01 RealMemory=192000 AllocMem=0 Sockets=2 State=IDLE Partitions=general",
        "NodeName=mixed01 CPUTot=64 Gres=gpu:a100:2,gpu:v100:2 RealMemory=512000 Partitions=gpu",
        "",
    ]
)


@pytest.mark.parametrize(
    ("gres", "expected"),
    [
        ("gpu:a100:4", [{"model": "a100", "count": 4}]),
        ("gpu:a100:4(S:0-1)", [{"model": "a100", "count": 4}]),
        ("gpu:4", [{"model": "gpu", "count": 4}]),
        ("gpu:a100:2,gpu:v100:2", [{"model": "a100", "count": 2}, {"model": "v100", "count": 2}]),
        ("(null)", []),
        ("", []),
        ("mps:100", []),
    ],
)
def test_parse_gres(gres, expected):
    assert parse_gres(gres) == expected


def test_parse_scontrol_nodes_extracts_hardware():
    nodes = parse_scontrol_nodes(SCONTROL_NODES)

    assert nodes["gpu01"] == {
        "cpu_cores": 48,
        "memory_gb": 376,
        "gpus": [{"model": "a100", "count": 4}],
        "partitions": ["gpu", "general"],
    }
    assert nodes["cpu01"]["gpus"] == []
    assert nodes["cpu01"]["memory_gb"] == 188
    assert nodes["mixed01"]["gpus"] == [{"model": "a100", "count": 2}, {"model": "v100", "count": 2}]


def test_parse_scontrol_nodes_ignores_blank_and_error_lines():
    nodes = parse_scontrol_nodes("\nNo nodes in the system\nNodeName=n1 CPUTot=8 RealMemory=1024\n")
    assert list(nodes) == ["n1"]
    assert nodes["n1"] == {"cpu_cores": 8, "memory_gb": 1, "gpus": [], "partitions": []}


def test_build_inventory_wraps_nodes():
    assert build_inventory({"n1": {"cpu_cores": 1}}) == {"nodes": {"n1": {"cpu_cores": 1}}}


def test_collect_node_inventory_runs_scontrol(monkeypatch):
    calls = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=SCONTROL_NODES, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    inventory = collect_node_inventory()

    assert calls == [["scontrol", "show", "node", "--oneliner"]]
    assert set(inventory["nodes"]) == {"gpu01", "cpu01", "mixed01"}


def test_collect_node_inventory_raises_on_scontrol_failure(monkeypatch):
    def fake_run(cmd, **_kwargs):
        raise subprocess.CalledProcessError(1, cmd, stderr="scontrol: error")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="scontrol"):
        collect_node_inventory()
