"""Read node hardware (CPU cores, memory, GPUs, partitions) from scontrol."""

import subprocess

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


def parse_scontrol_nodes(text: str) -> dict[str, dict[str, object]]:
    """Parse ``scontrol show node --oneliner`` output.

    Args:
        text: Raw scontrol output, one node per line.

    Returns:
        Mapping of node name to ``cpu_cores``, ``memory_gb``, ``gpus`` and ``partitions``.
    """
    nodes: dict[str, dict[str, object]] = {}
    for line in text.splitlines():
        if not line.startswith("NodeName="):
            continue
        fields = dict(token.split("=", 1) for token in line.split() if "=" in token)
        partitions = fields.get("Partitions", "")
        nodes[fields["NodeName"]] = {
            "cpu_cores": int(fields.get("CPUTot", 0)),
            "memory_gb": round(int(fields.get("RealMemory", 0)) / MB_PER_GB),
            "gpus": parse_gres(fields.get("Gres", "")),
            "partitions": [p for p in partitions.split(",") if p],
        }
    return nodes


def build_inventory(nodes: dict[str, dict[str, object]]) -> dict[str, object]:
    """Wrap parsed nodes in the document format accepted by the dashboard."""
    return {"nodes": nodes}


def collect_node_inventory() -> dict[str, object]:
    """Run scontrol and return the node inventory document.

    Raises:
        RuntimeError: If scontrol is missing or exits with an error.
    """
    cmd = ["scontrol", "show", "node", "--oneliner"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        stderr = getattr(e, "stderr", "") or ""
        message = f"scontrol failed: {stderr or e}"
        raise RuntimeError(message) from e
    return build_inventory(parse_scontrol_nodes(result.stdout))
