"""Automatic node discovery and cluster config synchronization."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Set

import yaml

logger = logging.getLogger(__name__)


class NodeDiscoveryService:
    """Service for discovering nodes from data and updating cluster configuration."""

    def __init__(self, config_path: Path | None = None):
        """Initialize the node discovery service.

        Args:
            config_path: Path to clusters.yaml file
        """
        if config_path is None:
            # Default to project config directory
            config_path = Path(__file__).parent.parent.parent / "config" / "clusters.yaml"

        self.config_path = Path(config_path)

    def discover_and_update_nodes(self, cluster_name: str, node_names: Set[str]) -> int:
        """Discover new nodes from data and add them to cluster config.

        This function checks if each node exists in the cluster config either as:
        1. A canonical node name (main entry in node_labels)
        2. A synonym (alias) of another node

        If a node is not found in either case, it's automatically added to the config.

        Args:
            cluster_name: Name of the cluster (e.g., "DAIC")
            node_names: Set of node names discovered from data

        Returns:
            Number of nodes added to the configuration
        """
        if not node_names:
            logger.info(f"No nodes to discover for cluster {cluster_name}")
            return 0

        # Load current config
        if not self.config_path.exists():
            logger.warning(f"Cluster config not found at {self.config_path}, cannot auto-discover nodes")
            return 0

        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load cluster config: {e}")
            return 0

        # Check if auto-generate is enabled
        auto_generate = config.get("settings", {}).get("auto_generate_labels", False)
        if not auto_generate:
            logger.debug("auto_generate_labels is disabled, skipping node discovery")
            return 0

        # Ensure cluster exists in config
        clusters = config.setdefault("clusters", {})
        cluster_config = clusters.setdefault(cluster_name, {})
        node_labels = cluster_config.setdefault("node_labels", {})

        # Build set of all known nodes (canonical + synonyms)
        known_nodes = self._get_all_known_nodes(cluster_config)

        # Find new nodes
        case_sensitive = config.get("settings", {}).get("case_sensitive", False)
        new_nodes = []

        for node_name in node_names:
            if self._is_node_known(node_name, known_nodes, case_sensitive):
                continue

            # New node discovered
            new_nodes.append(node_name)
            logger.info(f"Discovered new node: {node_name} in cluster {cluster_name}")

            # Add to config
            node_labels[node_name] = {
                "synonyms": [],
                "type": config.get("settings", {}).get("default_node_type", "cpu"),
                "description": f"Node {node_name}",
            }

        if not new_nodes:
            logger.debug(f"No new nodes discovered for cluster {cluster_name}")
            return 0

        # Write updated config back to file
        try:
            with open(self.config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Added {len(new_nodes)} new nodes to {cluster_name} config: {', '.join(new_nodes)}")
            return len(new_nodes)

        except Exception as e:
            logger.error(f"Failed to write updated cluster config: {e}")
            return 0

    def sync_hardware(self, cluster_name: str, inventory: dict[str, Any]) -> dict[str, int]:
        """Merge agent-reported node hardware into the cluster configuration.

        For every node in ``inventory["nodes"]`` the ``hardware`` block and
        ``partitions`` list are overwritten; ``synonyms`` and ``description``
        are kept. The node ``type`` follows the GPU count unless it is a
        special type such as ``login`` or ``storage``. Nodes not reported by
        the agent are left untouched.

        Args:
            cluster_name: Name of the cluster
            inventory: Document of the form ``{"nodes": {name: {cpu_cores, memory_gb, gpus, partitions}}}``

        Returns:
            Counts of nodes ``added`` and ``updated``

        Raises:
            ValueError: If the inventory does not contain a ``nodes`` mapping
        """
        nodes = inventory.get("nodes") if isinstance(inventory, dict) else None
        if not isinstance(nodes, dict):
            message = "Inventory must contain a 'nodes' mapping"
            raise ValueError(message)

        config = self._load_config()
        cluster_config = config.setdefault("clusters", {}).setdefault(cluster_name, {})
        node_labels = cluster_config.setdefault("node_labels", {})
        default_type = config.get("settings", {}).get("default_node_type", "cpu")

        added = updated = 0
        for node_name, spec in nodes.items():
            gpus = [{"model": g["model"], "count": int(g["count"])} for g in spec.get("gpus", [])]
            hardware = {
                "cpu": {"cores": int(spec.get("cpu_cores", 0))},
                "ram": {"total_gb": int(spec.get("memory_gb", 0))},
                "gpus": gpus,
            }
            if node_name in node_labels:
                updated += 1
            else:
                added += 1
                node_labels[node_name] = {"synonyms": [], "type": default_type, "description": f"Node {node_name}"}
            entry = node_labels[node_name]
            entry["hardware"] = hardware
            entry["partitions"] = list(spec.get("partitions", []))
            if entry.get("type") in (None, "cpu", "gpu"):
                entry["type"] = "gpu" if gpus else "cpu"

        synced_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cluster_config.setdefault("metadata", {})["last_hardware_sync"] = synced_at
        self._write_config(config)
        logger.info("Hardware sync for %s: %d nodes added, %d updated", cluster_name, added, updated)
        return {"added": added, "updated": updated}

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        with open(self.config_path) as f:
            return yaml.safe_load(f) or {}

    def _write_config(self, config: dict[str, Any]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    def _get_all_known_nodes(self, cluster_config: dict) -> Set[str]:
        """Get set of all known node names (canonical + synonyms).

        Args:
            cluster_config: Cluster configuration dictionary

        Returns:
            Set of all known node names
        """
        known = set()
        node_labels = cluster_config.get("node_labels", {})

        for canonical_name, node_info in node_labels.items():
            # Add canonical name
            known.add(canonical_name)

            # Add all synonyms
            synonyms = node_info.get("synonyms", [])
            known.update(synonyms)

        return known

    def _is_node_known(self, node_name: str, known_nodes: Set[str], case_sensitive: bool) -> bool:
        """Check if a node is already known in the config.

        Args:
            node_name: Node name to check
            known_nodes: Set of known node names
            case_sensitive: Whether matching should be case-sensitive

        Returns:
            True if node is known, False otherwise
        """
        if case_sensitive:
            return node_name in known_nodes

        # Case-insensitive matching
        node_name_lower = node_name.lower()
        return any(known.lower() == node_name_lower for known in known_nodes)


# Global instance
_node_discovery_service = None


def get_node_discovery_service() -> NodeDiscoveryService:
    """Get singleton instance of node discovery service.

    Returns:
        NodeDiscoveryService instance
    """
    global _node_discovery_service
    if _node_discovery_service is None:
        _node_discovery_service = NodeDiscoveryService()
    return _node_discovery_service
