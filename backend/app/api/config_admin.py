"""Configuration admin API endpoints for YAML cluster configuration management."""
from pathlib import Path
from typing import Any, Dict

import yaml
from fastapi import APIRouter, Depends, HTTPException

from ..config import get_cluster_config, reload_cluster_config
from ..core.admin_auth import get_current_admin

router = APIRouter()


def get_config_path() -> Path:
    """Get path to configuration file."""
    config = get_cluster_config()
    return config.config_path


@router.get("/config")
async def get_configuration(admin: str = Depends(get_current_admin)):
    """Get current cluster configuration.

    Returns the complete YAML configuration including all clusters,
    node labels, account labels, and settings.
    """
    try:
        config = get_cluster_config()

        return {
            "clusters": config.config.get("clusters", {}),
            "settings": config.config.get("settings", {}),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading configuration: {str(e)}")


@router.get("/config/{cluster_name}")
async def get_cluster_configuration(cluster_name: str, admin: str = Depends(get_current_admin)):
    """Get configuration for a specific cluster.

    Args:
        cluster_name: Name of the cluster (e.g., "DAIC")

    Returns:
        Cluster configuration including labels and metadata
    """
    try:
        config = get_cluster_config()
        clusters = config.config.get("clusters", {})

        if cluster_name not in clusters:
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_name} not found")

        return clusters[cluster_name]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading cluster configuration: {str(e)}")


@router.post("/config/reload")
async def reload_configuration(admin: str = Depends(get_current_admin)):
    """Reload configuration from file.

    Useful after manual edits to the YAML file.

    Returns:
        Success message with loaded clusters
    """
    try:
        config = reload_cluster_config()
        clusters = config.get_all_clusters()

        return {
            "status": "success",
            "message": "Configuration reloaded successfully",
            "clusters": clusters,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reloading configuration: {str(e)}")


@router.put("/config")
async def update_configuration(config_data: Dict[str, Any], admin: str = Depends(get_current_admin)):
    """Update the entire cluster configuration.

    This endpoint allows you to update the complete YAML configuration.
    The configuration will be validated and written to the file.

    Args:
        config_data: Complete configuration object with clusters and settings

    Returns:
        Success message
    """
    try:
        # Validate that we have the required structure
        if "clusters" not in config_data:
            raise HTTPException(status_code=400, detail="Configuration must include 'clusters' key")

        # Get config path
        config_path = get_config_path()

        # Create backup of existing config
        if config_path.exists():
            backup_path = config_path.with_suffix(".yaml.backup")
            import shutil
            shutil.copy2(config_path, backup_path)

        # Write new configuration
        with open(config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        # Reload configuration to validate
        reload_cluster_config()

        return {
            "status": "success",
            "message": "Configuration updated successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        # If there was an error, try to restore from backup
        config_path = get_config_path()
        backup_path = config_path.with_suffix(".yaml.backup")
        if backup_path.exists():
            import shutil
            shutil.copy2(backup_path, config_path)
            reload_cluster_config()

        raise HTTPException(status_code=500, detail=f"Error updating configuration: {str(e)}")


@router.post("/generate-demo-cluster")
async def generate_demo_cluster(admin: str = Depends(get_current_admin)):
    """Generate a demo cluster with 2 years of synthetic data.

    Creates a DemoCluster with:
    - 2 years of data (2023-2024)
    - 100 users (power users, regular users, students)
    - Seasonal patterns (more active in spring and fall)
    - Simulated outages with longer waiting times
    - 30 nodes (15 GPU, 15 CPU)
    - 3 partitions (general, cpu, gpu)
    - Realistic job patterns and resource usage

    Returns:
        Status and statistics about generated data
    """
    try:
        import sys
        import subprocess
        from pathlib import Path
        from datetime import datetime, date

        # Import the generator
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))
        from generate_test_cluster_data import SyntheticClusterDataGenerator

        cluster_name = "DemoCluster"

        # Get data directory
        from ..core.config import get_settings
        settings = get_settings()
        output_dir = Path(settings.data_path) / cluster_name / "data"

        # Check if demo cluster already exists - if so, delete it first
        if output_dir.exists() and list(output_dir.glob("*.parquet")):
            import shutil
            # Delete existing demo cluster data
            shutil.rmtree(output_dir.parent)  # Delete the entire DemoCluster directory

            # Remove from YAML configuration
            config_path = get_config_path()
            if config_path.exists():
                with open(config_path, "r") as f:
                    existing_config = yaml.safe_load(f) or {}
                if "clusters" in existing_config and cluster_name in existing_config["clusters"]:
                    del existing_config["clusters"][cluster_name]
                    import tempfile
                    import os
                    config_dir = config_path.parent
                    with tempfile.NamedTemporaryFile(mode='w', dir=config_dir, delete=False, suffix='.yaml') as f:
                        temp_path = f.name
                        yaml.dump(existing_config, f, default_flow_style=False, sort_keys=False)
                    os.replace(temp_path, config_path)

            # Remove from database if exists
            from ..db.clusters import get_cluster_db
            cluster_db_instance = get_cluster_db()
            for cluster in cluster_db_instance.get_all_clusters():
                if cluster["name"] == cluster_name:
                    cluster_db_instance.delete_cluster(cluster["id"])
                    break

        # Define outage periods (2-3 outages during the 2-year period)
        outages = [
            (date(2023, 6, 15), date(2023, 6, 18)),   # 3-day summer outage
            (date(2023, 11, 20), date(2023, 11, 22)), # 2-day fall outage
            (date(2024, 4, 10), date(2024, 4, 13))    # 3-day spring outage
        ]

        # Create generator with demo configuration
        generator = SyntheticClusterDataGenerator(
            cluster_name=cluster_name,
            seed=42,
            num_users=100,
            simple_partitions=True
        )

        # Generate dataset
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2024, 12, 31)
        jobs_per_day = 150  # Average jobs per day

        df = generator.generate_dataset(
            start_date=start_date,
            end_date=end_date,
            jobs_per_day=jobs_per_day,
            seasonal_pattern=True,
            outages=outages
        )

        # Save data
        generator.save_weekly_data(df, output_dir)

        # Auto-generate configuration
        from pathlib import Path
        import pandas as pd

        config_path = get_config_path()
        if config_path.exists():
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f) or {}
        else:
            config_data = {"clusters": {}, "settings": {}}

        if "clusters" not in config_data:
            config_data["clusters"] = {}

        # Create cluster configuration
        cluster_config = {
            "display_name": "Demo Cluster",
            "description": "Synthetic demo cluster with 2 years of realistic job data",
            "metadata": {
                "location": "Demo Environment",
                "owner": "Demo",
                "contact": "demo@example.com",
            },
            "node_labels": {},
            "account_labels": {},
            "partition_labels": {
                "general": {
                    "display_name": "General Partition",
                    "description": "General purpose partition"
                },
                "cpu": {
                    "display_name": "CPU Partition",
                    "description": "CPU-only partition"
                },
                "gpu": {
                    "display_name": "GPU Partition",
                    "description": "GPU partition"
                }
            }
        }

        # Extract node and account info from generated data
        all_nodes = set()
        for nodes_str in df["NodeList"].dropna().unique():
            if isinstance(nodes_str, str):
                all_nodes.update(nodes_str.split(","))

        for node in sorted(all_nodes):
            node_type = "gpu" if "gpu" in node.lower() else "cpu"
            cluster_config["node_labels"][node] = {
                "synonyms": [],
                "type": node_type,
                "description": f"{node_type.upper()} Node {node}",
                "hardware": {
                    "cpu": {"cores": 48 if node_type == "gpu" else 32},
                    "ram": {"total_gb": 384 if node_type == "gpu" else 192},
                    "gpus": [{"model": "demo", "count": 4}] if node_type == "gpu" else [],
                },
            }

        for account in sorted(df["Account"].dropna().unique()):
            cluster_config["account_labels"][account] = {
                "display_name": account,
                "short_name": account.split("-")[-1].upper() if "-" in account else account
            }

        config_data["clusters"][cluster_name] = cluster_config

        # Write configuration atomically
        import tempfile
        import os
        config_dir = config_path.parent
        with tempfile.NamedTemporaryFile(mode='w', dir=config_dir, delete=False, suffix='.yaml') as f:
            temp_path = f.name
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        os.replace(temp_path, config_path)

        # Reload configuration and datastore
        reload_cluster_config()

        # Trigger datastore reload
        from ..datastore_singleton import get_datastore
        datastore = get_datastore()
        datastore.check_for_updates()

        # Create physical cluster entry in database
        from ..db.clusters import get_cluster_db

        cluster_db = get_cluster_db()

        # Check if demo cluster already exists in database
        existing_clusters = cluster_db.get_all_clusters()
        demo_exists = any(c["name"] == cluster_name for c in existing_clusters)

        if not demo_exists:
            # Create cluster in database (API key is auto-generated)
            cluster_db.create_cluster(
                name=cluster_name,
                description="Synthetic demo cluster with 2 years of realistic job data (2023-2024)",
                contact_email="demo@example.com",
                location="Demo Environment"
            )

        return {
            "status": "success",
            "message": f"Demo cluster generated successfully",
            "cluster_name": cluster_name,
            "stats": {
                "total_jobs": len(df),
                "date_range": f"{df['Submit'].min()} to {df['Submit'].max()}",
                "users": len(df["User"].unique()),
                "accounts": len(df["Account"].unique()),
                "partitions": len(df["Partition"].unique()),
                "nodes": len(all_nodes),
                "total_cpu_hours": float(df["CPU-hours"].sum()),
                "total_gpu_hours": float(df["GPU-hours"].sum()),
                "outages": len(outages)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Error generating demo cluster: {str(e)}\n{traceback.format_exc()}"
        )


@router.post("/config/{cluster_name}/cleanup-invalid-nodes")
async def cleanup_invalid_nodes(cluster_name: str, admin: str = Depends(get_current_admin)):
    """Clean up invalid nodes from cluster configuration.

    Removes nodes that are just numbers, ranges, or contain brackets (malformed SLURM notation).

    Args:
        cluster_name: Name of the cluster to clean

    Returns:
        Statistics about cleaned nodes
    """
    try:
        import re

        config_path = get_config_path()
        if not config_path.exists():
            raise HTTPException(status_code=404, detail="Config file not found")

        # Load config
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f) or {}

        if cluster_name not in config_data.get("clusters", {}):
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_name} not found")

        # Get nodes
        cluster_config = config_data["clusters"][cluster_name]
        nodes = cluster_config.get("node_labels", {})
        original_count = len(nodes)

        # Filter out invalid nodes
        valid_nodes = {}
        invalid_nodes = []
        for node_name, node_info in nodes.items():
            # Skip invalid: just numbers/ranges/brackets without letters
            if re.match(r'^[\d\-\[\]]+$', node_name) or ']' in node_name or '[' in node_name:
                invalid_nodes.append(node_name)
                continue
            # Keep only nodes starting with letter
            if re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', node_name):
                valid_nodes[node_name] = node_info
            else:
                invalid_nodes.append(node_name)

        # Update config
        config_data["clusters"][cluster_name]["node_labels"] = valid_nodes

        # Write atomically
        import tempfile, os
        config_dir = config_path.parent
        with tempfile.NamedTemporaryFile(mode='w', dir=config_dir, delete=False, suffix='.yaml') as f:
            temp_path = f.name
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        os.replace(temp_path, config_path)

        # Reload
        reload_cluster_config()

        return {
            "status": "success",
            "message": f"Cleaned up {len(invalid_nodes)} invalid nodes",
            "stats": {
                "original_count": original_count,
                "removed_count": len(invalid_nodes),
                "remaining_count": len(valid_nodes),
                "sample_removed": invalid_nodes[:10] if invalid_nodes else []
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"Error cleaning up nodes: {str(e)}\n{traceback.format_exc()}")


@router.delete("/config/{cluster_name}/cleanup")
async def cleanup_demo_cluster(cluster_name: str, admin: str = Depends(get_current_admin)):
    """Delete a demo cluster's data and configuration.

    This removes:
    - Data directory
    - YAML configuration entry
    - Database entry (if exists)

    Args:
        cluster_name: Name of the cluster to delete

    Returns:
        Success message
    """
    try:
        from pathlib import Path
        from ..core.config import get_settings
        import shutil

        settings = get_settings()

        # Delete data directory
        data_dir = Path(settings.data_path) / cluster_name
        if data_dir.exists():
            shutil.rmtree(data_dir)

        # Remove from YAML configuration
        config_path = get_config_path()
        if config_path.exists():
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f) or {}

            if "clusters" in config_data and cluster_name in config_data["clusters"]:
                del config_data["clusters"][cluster_name]

                # Write back
                import tempfile
                import os
                config_dir = config_path.parent
                with tempfile.NamedTemporaryFile(mode='w', dir=config_dir, delete=False, suffix='.yaml') as f:
                    temp_path = f.name
                    yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
                os.replace(temp_path, config_path)

        # Remove from database if exists
        from ..db.clusters import get_cluster_db
        cluster_db = get_cluster_db()
        existing_clusters = cluster_db.get_all_clusters()
        for cluster in existing_clusters:
            if cluster["name"] == cluster_name:
                cluster_db.delete_cluster(cluster["id"])
                break

        # Reload configuration
        reload_cluster_config()

        # Trigger datastore reload
        from ..datastore_singleton import get_datastore
        datastore = get_datastore()
        datastore.check_for_updates()

        return {
            "status": "success",
            "message": f"Cluster {cluster_name} cleaned up successfully"
        }
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up cluster: {str(e)}\n{traceback.format_exc()}"
        )


@router.put("/config/{cluster_name}")
async def update_cluster_configuration(cluster_name: str, cluster_data: Dict[str, Any], admin: str = Depends(get_current_admin)):
    """Update configuration for a specific cluster.

    This endpoint allows you to update the configuration for a single cluster.
    More convenient than updating the entire configuration file.

    Args:
        cluster_name: Name of the cluster (e.g., "DAIC")
        cluster_data: Cluster configuration object

    Returns:
        Success message
    """
    try:
        # Get config path
        config_path = get_config_path()

        # Load current configuration
        if config_path.exists():
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f) or {}
        else:
            config_data = {"clusters": {}, "settings": {}}

        # Ensure clusters key exists
        if "clusters" not in config_data:
            config_data["clusters"] = {}

        # Create backup
        backup_path = config_path.with_suffix(".yaml.backup")
        if config_path.exists():
            import shutil
            shutil.copy2(config_path, backup_path)

        # Update the specific cluster
        config_data["clusters"][cluster_name] = cluster_data

        # Write updated configuration
        with open(config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        # Reload configuration to validate
        reload_cluster_config()

        return {
            "status": "success",
            "message": f"Configuration updated successfully for cluster {cluster_name}",
        }
    except Exception as e:
        # If there was an error, try to restore from backup
        config_path = get_config_path()
        backup_path = config_path.with_suffix(".yaml.backup")
        if backup_path.exists():
            import shutil
            shutil.copy2(backup_path, config_path)
            reload_cluster_config()

        raise HTTPException(status_code=500, detail=f"Error updating cluster configuration: {str(e)}")
