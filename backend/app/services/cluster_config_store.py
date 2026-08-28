"""Read and update single cluster entries in clusters.yaml."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml


class ClusterConfigStore:
    """Loads clusters.yaml, applies a change to one cluster entry, and writes it back."""

    def __init__(self, config_path: Path):
        self.config_path = Path(config_path)

    def read(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        with open(self.config_path) as f:
            return yaml.safe_load(f) or {}

    def get_cluster(self, cluster_name: str) -> dict[str, Any] | None:
        return self.read().get("clusters", {}).get(cluster_name)

    def update_cluster(self, cluster_name: str, mutate: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        """Apply ``mutate`` to the cluster entry and persist the file.

        Raises:
            KeyError: If the cluster has no entry in the configuration.
        """
        config = self.read()
        clusters = config.setdefault("clusters", {})
        if cluster_name not in clusters:
            raise KeyError(cluster_name)
        mutate(clusters[cluster_name])
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return clusters[cluster_name]
