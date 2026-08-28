"""Tests for reading the cluster configuration from scontrol and sacctmgr."""

import subprocess

import pytest

from slurm_usage_history.scripts.node_inventory import (
    build_inventory,
    collect_cluster_inventory,
    parse_gres,
    parse_sacctmgr_accounts,
    parse_scontrol_config,
    parse_scontrol_nodes,
    parse_scontrol_partitions,
)

SCONTROL_NODES = "\n".join(
    [
        "NodeName=gpu01 Arch=x86_64 CoresPerSocket=24 CPUAlloc=0 CPUTot=48 CPULoad=0.01 AvailableFeatures=a40,avx2 "
        "Gres=gpu:a100:4(S:0-1) NodeAddr=gpu01 RealMemory=385000 AllocMem=0 Sockets=2 ThreadsPerCore=1 "
        "State=IDLE Partitions=gpu,general",
        "NodeName=cpu01 Arch=x86_64 CoresPerSocket=12 CPUAlloc=0 CPUTot=24 CPULoad=0.00 AvailableFeatures=(null) "
        "Gres=(null) NodeAddr=cpu01 RealMemory=192000 AllocMem=0 Sockets=2 ThreadsPerCore=1 State=IDLE "
        "Partitions=general",
        "NodeName=mixed01 CPUTot=64 Gres=gpu:a100:2,gpu:v100:2 RealMemory=512000 Partitions=gpu",
        "",
    ]
)
SCONTROL_PARTITIONS = "\n".join(
    [
        "PartitionName=general AllowGroups=ALL Default=YES MaxTime=7-00:00:00 Nodes=gpu01,cpu01 State=UP "
        "TotalCPUs=72 TotalNodes=2",
        "PartitionName=gpu AllowGroups=ALL Default=NO MaxTime=UNLIMITED Nodes=gpu01 State=UP TotalCPUs=48 TotalNodes=1",
    ]
)
SACCTMGR_ACCOUNTS = "root|default root account|\newi-insy|INSY department|ewi\nbroken\n\n"
SCONTROL_CONFIG = "\n".join(
    [
        "Configuration data as of 2026-08-28T12:00:00",
        "ClusterName              = daic",
        "SLURM_VERSION            = 23.11.4",
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
        "sockets": 2,
        "cores_per_socket": 24,
        "threads_per_core": 1,
        "memory_gb": 376,
        "gpus": [{"model": "a100", "count": 4}],
        "partitions": ["gpu", "general"],
        "features": ["a40", "avx2"],
    }
    assert nodes["cpu01"]["gpus"] == []
    assert nodes["cpu01"]["features"] == []
    assert nodes["cpu01"]["memory_gb"] == 188
    assert nodes["mixed01"]["gpus"] == [{"model": "a100", "count": 2}, {"model": "v100", "count": 2}]
    assert nodes["mixed01"]["sockets"] == 0


def test_parse_scontrol_nodes_ignores_blank_and_error_lines():
    nodes = parse_scontrol_nodes("\nNo nodes in the system\nNodeName=n1 CPUTot=8 RealMemory=1024\n")
    assert list(nodes) == ["n1"]
    assert nodes["n1"]["cpu_cores"] == 8
    assert nodes["n1"]["memory_gb"] == 1


def test_parse_scontrol_partitions():
    partitions = parse_scontrol_partitions(SCONTROL_PARTITIONS)
    assert partitions["general"] == {
        "nodes": "gpu01,cpu01",
        "total_cpus": 72,
        "total_nodes": 2,
        "max_time": "7-00:00:00",
        "default": True,
        "state": "UP",
    }
    assert partitions["gpu"]["default"] is False
    assert partitions["gpu"]["max_time"] == "UNLIMITED"


def test_parse_sacctmgr_accounts():
    accounts = parse_sacctmgr_accounts(SACCTMGR_ACCOUNTS)
    assert accounts == {
        "root": {"description": "default root account", "organization": ""},
        "ewi-insy": {"description": "INSY department", "organization": "ewi"},
        "broken": {"description": "", "organization": ""},
    }


def test_parse_scontrol_config():
    assert parse_scontrol_config(SCONTROL_CONFIG) == {"slurm_cluster_name": "daic", "slurm_version": "23.11.4"}


def test_build_inventory_wraps_sections():
    assert build_inventory({"n1": {"cpu_cores": 1}}) == {
        "cluster": {},
        "nodes": {"n1": {"cpu_cores": 1}},
        "partitions": {},
        "accounts": {},
    }


OUTPUTS = {
    "node": SCONTROL_NODES,
    "partition": SCONTROL_PARTITIONS,
    "config": SCONTROL_CONFIG,
    "account": SACCTMGR_ACCOUNTS,
}


def fake_run_factory(calls, fail_sacctmgr=False):
    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        if cmd[0] == "sacctmgr":
            if fail_sacctmgr:
                raise subprocess.CalledProcessError(1, cmd, stderr="sacctmgr: error: no accounting")
            return subprocess.CompletedProcess(cmd, 0, stdout=OUTPUTS["account"], stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout=OUTPUTS[cmd[2]], stderr="")

    return fake_run


def test_collect_cluster_inventory_runs_all_commands(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", fake_run_factory(calls))

    inventory = collect_cluster_inventory()

    assert [c[:3] for c in calls] == [
        ["scontrol", "show", "node"],
        ["scontrol", "show", "partition"],
        ["scontrol", "show", "config"],
        ["sacctmgr", "show", "account"],
    ]
    assert set(inventory["nodes"]) == {"gpu01", "cpu01", "mixed01"}
    assert set(inventory["partitions"]) == {"general", "gpu"}
    assert inventory["accounts"]["ewi-insy"]["organization"] == "ewi"
    assert inventory["cluster"]["slurm_version"] == "23.11.4"


def test_collect_cluster_inventory_skips_accounts_when_sacctmgr_fails(monkeypatch, caplog):
    monkeypatch.setattr(subprocess, "run", fake_run_factory([], fail_sacctmgr=True))

    inventory = collect_cluster_inventory()

    assert inventory["accounts"] == {}
    assert set(inventory["nodes"]) == {"gpu01", "cpu01", "mixed01"}
    assert "Accounts skipped" in caplog.text


def test_collect_cluster_inventory_raises_on_scontrol_failure(monkeypatch):
    def fake_run(cmd, **_kwargs):
        raise subprocess.CalledProcessError(1, cmd, stderr="scontrol: error")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="scontrol"):
        collect_cluster_inventory()
