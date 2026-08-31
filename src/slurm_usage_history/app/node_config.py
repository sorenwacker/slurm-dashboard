# src/slurm_usage_history/app/node_config.py

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml


class NodeConfiguration:
    """Class to handle node configuration for resources normalization."""

    def __init__(self, config_file: str | None = None):
        """
        Initialize the Node Configuration.

        Args:
            config_file: Path to config file (YAML or JSON)
        """
        self.config: dict[str, Any] = {}
        self.config_file: str | None = config_file

        if config_file:
            self.load_config(config_file)
        else:
            # Look for config in default locations
            self._load_default_config()

    def _load_default_config(self) -> None:
        """Try to load configuration from default locations."""
        # Check for configs in common locations
        possible_paths: list[str] = [
            os.path.expanduser("~/.config/slurm_usage/node_config.yaml"),
            os.path.expanduser("~/.config/slurm_usage/node_config.json"),
            "/etc/slurm_usage/node_config.yaml",
            "/etc/slurm_usage/node_config.json",
            "node_config.yaml",
            "node_config.json",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                self.load_config(path)
                return

    def load_config(self, config_file: str) -> bool:
        """
        Load configuration from a file.

        Args:
            config_file: Path to config file (YAML or JSON)

        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            path = Path(config_file)

            if not path.exists():
                logger.warning(f"Config file not found: {config_file}")
                return False

            if path.suffix.lower() in [".yaml", ".yml"]:
                with open(path) as f:
                    self.config = yaml.safe_load(f)
            elif path.suffix.lower() == ".json":
                with open(path) as f:
                    self.config = json.load(f)
            else:
                logger.error(f"Unsupported config file format: {path.suffix}")
                return False

            self.config_file = config_file
            logger.info(f"Loaded node configuration from {config_file}")
            return True

        except Exception as e:
            logger.error(f"Error loading config: {e!s}")
            return False

    def get_node_cpu_count(self, node_name: str) -> int:
        """
        Get CPU count for a specific node.

        Args:
            node_name: Name of the node

        Returns:
            int: Number of CPUs for the node, or 1 if not configured
        """
        if not self.config or "nodes" not in self.config:
            return 1

        # Try exact match
        if node_name in self.config["nodes"]:
            return self.config["nodes"][node_name].get("cpus", 1)

        # Try pattern matching
        for pattern, node_config in self.config.get("node_patterns", {}).items():
            if self._match_pattern(node_name, pattern):
                return node_config.get("cpus", 1)

        # Return default
        return self.config.get("default_cpus", 1)

    def get_node_gpu_count(self, node_name: str) -> int:
        """
        Get GPU count for a specific node.

        Args:
            node_name: Name of the node

        Returns:
            int: Number of GPUs for the node, or 0 if not configured
        """
        if not self.config or "nodes" not in self.config:
            return 0

        # Try exact match
        if node_name in self.config["nodes"]:
            return self.config["nodes"][node_name].get("gpus", 0)

        # Try pattern matching
        for pattern, node_config in self.config.get("node_patterns", {}).items():
            if self._match_pattern(node_name, pattern):
                return node_config.get("gpus", 0)

        # Return default
        return self.config.get("default_gpus", 0)

    def _match_pattern(self, node_name: str, pattern: str) -> bool:
        """
        Check if a node name matches a pattern.

        Args:
            node_name: Name of the node
            pattern: Pattern to match (supports * wildcard)

        Returns:
            bool: True if node name matches pattern
        """
        # Convert pattern to regex
        regex_pattern = pattern.replace("*", ".*")
        return re.match(f"^{regex_pattern}$", node_name) is not None

    def get_all_node_resources(self, node_names: list[str]) -> dict[str, dict[str, int]]:
        """
        Get CPU and GPU counts for a list of nodes.

        Args:
            node_names: List of node names

        Returns:
            dict: Dictionary mapping node names to resource dictionaries
        """
        resources: dict[str, dict[str, int]] = {}

        for node in node_names:
            resources[node] = {
                "cpus": self.get_node_cpu_count(node),
                "gpus": self.get_node_gpu_count(node),
            }

        return resources


# Example config file structure (YAML):
"""
default_cpus: 32
default_gpus: 0

# Specific node configurations
nodes:
  node001:
    cpus: 64
    gpus: 4
  node002:
    cpus: 64
    gpus: 4
  gpu-node001:
    cpus: 32
    gpus: 8

# Pattern matching for nodes with similar configurations
node_patterns:
  "cpu-node*":
    cpus: 32
    gpus: 0
  "gpu-node*":
    cpus: 32
    gpus: 8
  "bigmem-node*":
    cpus: 128
    gpus: 0
"""
