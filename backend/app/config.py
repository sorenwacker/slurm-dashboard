"""Configuration management for cluster labels and node synonyms."""

from pathlib import Path
from typing import Any

import yaml


def default_cluster_config_path() -> Path:
    """CLUSTER_CONFIG_PATH from settings, or backend/config/clusters.yaml inside the checkout."""
    from .core.config import get_settings

    configured = get_settings().cluster_config_path
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).parent.parent / "config" / "clusters.yaml"


class ClusterConfig:
    """Manages cluster configuration from YAML file."""

    def __init__(self, config_path: str | None = None):
        """Initialize cluster configuration.

        Args:
            config_path: Path to clusters.yaml file. If None, uses default location.
        """
        if config_path is None:
            config_path = default_cluster_config_path()

        self.config_path = Path(config_path)
        self.config: dict[str, Any] = {}
        self._node_synonym_map: dict[str, dict[str, str]] = {}
        self._account_labels: dict[str, dict[str, Any]] = {}
        self._partition_labels: dict[str, dict[str, Any]] = {}

        if self.config_path.exists():
            self.load_config()
        else:
            print(f"Warning: Config file not found at {self.config_path}")
            print("Using default configuration (no label mapping)")

    def load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)

            # Build synonym maps for fast lookup
            self._build_synonym_maps()

            print(f"Loaded cluster configuration from {self.config_path}")
        except Exception as e:
            print(f"Error loading config: {e}")
            self.config = {}

    def _build_synonym_maps(self) -> None:
        """Build reverse lookup maps for node synonyms."""
        clusters = self.config.get("clusters", {})

        for cluster_name, cluster_config in clusters.items():
            # Build node synonym map
            node_map = {}
            node_labels = cluster_config.get("node_labels", {})

            for canonical_name, node_info in node_labels.items():
                # Map canonical name to itself
                node_map[canonical_name] = canonical_name

                # Map each synonym to canonical name
                synonyms = node_info.get("synonyms", [])
                for synonym in synonyms:
                    node_map[synonym] = canonical_name

                    # If case insensitive, also add lowercase version
                    if not self._is_case_sensitive():
                        node_map[synonym.lower()] = canonical_name

                # If case insensitive, add lowercase canonical name
                if not self._is_case_sensitive():
                    node_map[canonical_name.lower()] = canonical_name

            self._node_synonym_map[cluster_name] = node_map

            # Store account labels
            self._account_labels[cluster_name] = cluster_config.get("account_labels", {})

            # Store partition labels
            self._partition_labels[cluster_name] = cluster_config.get("partition_labels", {})

    def _is_case_sensitive(self) -> bool:
        """Check if node name matching should be case sensitive."""
        return self.config.get("settings", {}).get("case_sensitive", False)

    def normalize_node_name(self, cluster: str, node_name: str) -> str:
        """Normalize a node name to its canonical form.

        Args:
            cluster: Cluster name (e.g., "DAIC")
            node_name: Raw node name from SLURM (e.g., "gpu5", "Gpu05")

        Returns:
            Canonical node name (e.g., "gpu05")
        """
        if cluster not in self._node_synonym_map:
            return node_name

        node_map = self._node_synonym_map[cluster]

        # Try exact match first
        if node_name in node_map:
            return node_map[node_name]

        # Try case-insensitive match if enabled
        if not self._is_case_sensitive():
            lower_name = node_name.lower()
            if lower_name in node_map:
                return node_map[lower_name]

        # No mapping found, return original
        return node_name

    def get_node_info(self, cluster: str, node_name: str) -> dict[str, Any]:
        """Get detailed information about a node.

        Args:
            cluster: Cluster name
            node_name: Node name (will be normalized)

        Returns:
            Dictionary with node information (type, description, etc.)
        """
        normalized = self.normalize_node_name(cluster, node_name)

        cluster_config = self.config.get("clusters", {}).get(cluster, {})
        node_labels = cluster_config.get("node_labels", {})

        if normalized in node_labels:
            return node_labels[normalized]

        # Return default info
        return {
            "type": self.config.get("settings", {}).get("default_node_type", "cpu"),
            "description": f"Node {normalized}",
        }

    def get_account_label(self, cluster: str, account_name: str) -> dict[str, Any]:
        """Get display information for an account.

        Args:
            cluster: Cluster name
            account_name: Account name

        Returns:
            Dictionary with account display information
        """
        if cluster in self._account_labels:
            return self._account_labels[cluster].get(
                account_name,
                {
                    "display_name": account_name,
                    "short_name": account_name,
                },
            )

        return {
            "display_name": account_name,
            "short_name": account_name,
        }

    def get_partition_label(self, cluster: str, partition_name: str) -> dict[str, Any]:
        """Get display information for a partition.

        Args:
            cluster: Cluster name
            partition_name: Partition name

        Returns:
            Dictionary with partition display information
        """
        if cluster in self._partition_labels:
            return self._partition_labels[cluster].get(
                partition_name,
                {
                    "display_name": partition_name,
                    "description": f"{partition_name} partition",
                },
            )

        return {
            "display_name": partition_name,
            "description": f"{partition_name} partition",
        }

    def get_cluster_display_name(self, cluster: str) -> str:
        """Get display name for a cluster.

        Args:
            cluster: Cluster name

        Returns:
            Display name or original cluster name if not configured
        """
        cluster_config = self.config.get("clusters", {}).get(cluster, {})
        return cluster_config.get("display_name", cluster)

    def get_cluster_metadata(self, cluster: str) -> dict[str, Any]:
        """Get metadata for a cluster.

        Args:
            cluster: Cluster name

        Returns:
            Dictionary with cluster metadata
        """
        cluster_config = self.config.get("clusters", {}).get(cluster, {})
        return cluster_config.get("metadata", {})

    def get_all_clusters(self) -> list[str]:
        """Get list of all configured cluster names.

        Returns:
            List of cluster names
        """
        return list(self.config.get("clusters", {}).keys())

    def get_node_hardware(self, cluster: str, node_name: str) -> dict[str, int]:
        """Get hardware specifications for a node.

        Returns CPU cores and GPU count, using node-specific config if available,
        then checking node_type_patterns, then falling back to hardware defaults.

        Args:
            cluster: Cluster name
            node_name: Node name (will be normalized)

        Returns:
            Dictionary with 'cpu_cores', 'gpu_count', 'memory_gb' and 'known' keys; 'known' is False when the
            values are type defaults rather than configured hardware; memory_gb is 0 when unknown
        """
        import re

        node_info = self.get_node_info(cluster, node_name)

        # Check for node-specific hardware config
        hardware = node_info.get("hardware", {})
        memory_gb = int(hardware.get("ram", {}).get("total_gb", 0) or 0) if hardware else 0
        if hardware:
            cpu_cores = hardware.get("cpu", {}).get("cores", 0)
            gpus = hardware.get("gpus", [])
            gpu_count = sum(g.get("count", 0) for g in gpus) if gpus else 0
            if cpu_cores > 0:
                return {"cpu_cores": cpu_cores, "gpu_count": gpu_count, "memory_gb": memory_gb, "known": True}

        # Check node_type_patterns for matching pattern
        patterns = self.config.get("settings", {}).get("node_type_patterns", {})
        for pattern_name, pattern_config in patterns.items():
            pattern = pattern_config.get("pattern", "")
            if pattern and re.match(pattern, node_name, re.IGNORECASE):
                return {
                    "cpu_cores": pattern_config.get("cpu_cores", 48),
                    "gpu_count": pattern_config.get("gpu_count", 0),
                    "memory_gb": memory_gb,
                    "known": True,
                }

        # Fall back to hardware defaults based on node type
        node_type = node_info.get("type", "cpu")
        defaults = self.config.get("settings", {}).get("hardware_defaults", {})
        type_defaults = defaults.get(node_type, {})

        # Defaults are not measurements: callers must not normalize against them
        return {
            "cpu_cores": type_defaults.get("cpu_cores", 64),
            "gpu_count": type_defaults.get("gpu_count", 0),
            "memory_gb": memory_gb,
            "known": False,
        }

    def get_all_node_capacities(self, cluster: str) -> dict[str, dict[str, Any]]:
        """Hardware and type of every configured node of a cluster, keyed by canonical node name."""
        node_labels = self.config.get("clusters", {}).get(cluster, {}).get("node_labels", {}) or {}
        return {
            node: {
                **self.get_node_hardware(cluster, node),
                "type": (info or {}).get("type", "cpu"),
                # Written only by the agent sync: the node exists in SLURM right now
                "synced": "partitions" in (info or {}),
            }
            for node, info in node_labels.items()
        }

    def get_hardware_defaults(self) -> dict[str, dict[str, int]]:
        """Get hardware defaults for all node types.

        Returns:
            Dictionary with node type keys ('gpu', 'cpu') and hardware specs
        """
        defaults = self.config.get("settings", {}).get("hardware_defaults", {})
        return {
            "gpu": {
                "cpu_cores": defaults.get("gpu", {}).get("cpu_cores", 48),
                "gpu_count": defaults.get("gpu", {}).get("gpu_count", 4),
            },
            "cpu": {
                "cpu_cores": defaults.get("cpu", {}).get("cpu_cores", 24),
                "gpu_count": defaults.get("cpu", {}).get("gpu_count", 0),
            },
        }


# Global instance
_cluster_config: ClusterConfig | None = None


def get_cluster_config() -> ClusterConfig:
    """Get global cluster configuration instance.

    Returns:
        ClusterConfig instance
    """
    global _cluster_config
    if _cluster_config is None:
        _cluster_config = ClusterConfig()
    return _cluster_config


def reload_cluster_config() -> ClusterConfig:
    """Reload cluster configuration from file.

    Returns:
        Reloaded ClusterConfig instance
    """
    global _cluster_config
    _cluster_config = ClusterConfig()
    return _cluster_config
