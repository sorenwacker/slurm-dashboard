"""Read cluster configuration (nodes, partitions, accounts, versions) from SLURM."""

import logging
import subprocess

logger = logging.getLogger(__name__)

MB_PER_GB = 1024


def parse_gres(gres: str) -> list[dict[str, object]]:
    """Parse a SLURM Gres string into a list of GPU entries.

    Args:
        gres: Gres value as printed by scontrol, e.g. ``gpu:a100:4(S:0-1)``.

    Returns:
        One ``{"model", "count"}`` entry per gpu GRES; non-gpu GRES are ignored.
    """
    gpus: list[dict[str, object]] = []
    if not gres or gres == "(null)":
        return gpus

    for item in gres.split(","):
        parts = item.split("(", 1)[0].strip().split(":")
        if parts[0] != "gpu" or len(parts) < 2:
            continue
        if len(parts) == 2:
            model, count = "gpu", parts[1]
        else:
            model, count = parts[1], parts[2]
        try:
            gpus.append({"model": model, "count": int(count)})
        except ValueError:
            continue
    return gpus


def _oneliner_records(text: str, key: str) -> list[dict[str, str]]:
    """Split ``scontrol --oneliner`` output into one key=value dict per line starting with ``key=``."""
    records = []
    for line in text.splitlines():
        if not line.startswith(f"{key}="):
            continue
        records.append(dict(token.split("=", 1) for token in line.split() if "=" in token))
    return records


def _int(value: str | None) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def parse_scontrol_nodes(text: str) -> dict[str, dict[str, object]]:
    """Parse ``scontrol show node --oneliner`` output.

    Returns:
        Mapping of node name to ``cpu_cores`` (``CPUTot``, the CPUs SLURM schedules), ``sockets``,
        ``cores_per_socket``, ``threads_per_core``, ``memory_gb``, ``gpus``, ``partitions`` and ``features``.
    """
    nodes: dict[str, dict[str, object]] = {}
    for fields in _oneliner_records(text, "NodeName"):
        features = fields.get("AvailableFeatures", "")
        nodes[fields["NodeName"]] = {
            "cpu_cores": _int(fields.get("CPUTot")),
            "sockets": _int(fields.get("Sockets")),
            "cores_per_socket": _int(fields.get("CoresPerSocket")),
            "threads_per_core": _int(fields.get("ThreadsPerCore")),
            "memory_gb": round(_int(fields.get("RealMemory")) / MB_PER_GB),
            "gpus": parse_gres(fields.get("Gres", "")),
            "partitions": [p for p in fields.get("Partitions", "").split(",") if p],
            "features": [f for f in features.split(",") if f and f != "(null)"],
        }
    return nodes


def parse_scontrol_partitions(text: str) -> dict[str, dict[str, object]]:
    """Parse ``scontrol show partition --oneliner`` output into per-partition facts."""
    partitions: dict[str, dict[str, object]] = {}
    for fields in _oneliner_records(text, "PartitionName"):
        partitions[fields["PartitionName"]] = {
            "nodes": fields.get("Nodes", ""),
            "total_cpus": _int(fields.get("TotalCPUs")),
            "total_nodes": _int(fields.get("TotalNodes")),
            "max_time": fields.get("MaxTime", ""),
            "default": fields.get("Default", "NO").upper() == "YES",
            "state": fields.get("State", ""),
        }
    return partitions


def parse_sacctmgr_accounts(text: str) -> dict[str, dict[str, str]]:
    """Parse ``sacctmgr show account format=Account,Descr,Org -P -n`` output."""
    accounts: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        name = parts[0].strip()
        if not name:
            continue
        accounts[name] = {
            "description": parts[1].strip() if len(parts) > 1 else "",
            "organization": parts[2].strip() if len(parts) > 2 else "",
        }
    return accounts


def parse_scontrol_config(text: str) -> dict[str, str]:
    """Extract cluster name and SLURM version from ``scontrol show config`` output."""
    values = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return {
        "slurm_cluster_name": values.get("ClusterName", ""),
        "slurm_version": values.get("SLURM_VERSION", ""),
    }


def build_inventory(
    nodes: dict[str, dict[str, object]],
    partitions: dict[str, dict[str, object]] | None = None,
    accounts: dict[str, dict[str, str]] | None = None,
    cluster: dict[str, str] | None = None,
) -> dict[str, object]:
    """Wrap parsed sections in the document format accepted by the dashboard."""
    return {
        "cluster": cluster or {},
        "nodes": nodes,
        "partitions": partitions or {},
        "accounts": accounts or {},
    }


def _run(cmd: list[str]) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        stderr = getattr(e, "stderr", "") or ""
        message = f"{cmd[0]} failed: {stderr or e}"
        raise RuntimeError(message) from e
    return result.stdout


def collect_cluster_inventory() -> dict[str, object]:
    """Run scontrol and sacctmgr and return the cluster inventory document.

    Accounts are skipped with a warning when sacctmgr is unavailable; scontrol failures raise.

    Raises:
        RuntimeError: If scontrol is missing or exits with an error.
    """
    nodes = parse_scontrol_nodes(_run(["scontrol", "show", "node", "--oneliner"]))
    partitions = parse_scontrol_partitions(_run(["scontrol", "show", "partition", "--oneliner"]))
    cluster = parse_scontrol_config(_run(["scontrol", "show", "config"]))
    try:
        accounts = parse_sacctmgr_accounts(
            _run(["sacctmgr", "show", "account", "format=Account,Descr,Org", "-P", "-n"])
        )
    except RuntimeError as e:
        logger.warning("Accounts skipped: %s", e)
        accounts = {}
    return build_inventory(nodes, partitions, accounts, cluster)
