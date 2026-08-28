"""Per-cluster admin endpoints: status and in-place label edits."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..config import get_cluster_config, reload_cluster_config
from ..core.admin_auth import get_current_admin
from ..datastore_singleton import get_datastore
from ..db.clusters import get_cluster_db
from ..models.admin_models import (
    AccountLabelUpdate,
    ClusterIdentityUpdate,
    NodeLabelUpdate,
    PartitionLabelUpdate,
)
from ..services.cluster_config_store import ClusterConfigStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clusters/by-name/{cluster_name}", tags=["cluster-admin"])


def get_store() -> ClusterConfigStore:
    """Store bound to the clusters.yaml the running configuration was loaded from."""
    return ClusterConfigStore(get_cluster_config().config_path)


def _no_config(cluster_name: str) -> str:
    return f"No configuration for cluster '{cluster_name}'"


def _cluster_entry(cluster_name: str) -> dict[str, Any]:
    entry = get_store().get_cluster(cluster_name)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No configuration for cluster '{cluster_name}'"
        )
    return entry


def _update_entry(cluster_name: str, section: str, key: str, changes: dict[str, Any]) -> dict[str, Any]:
    def mutate(cluster: dict[str, Any]) -> None:
        labels = cluster.setdefault(section, {}) or {}
        cluster[section] = labels
        if key not in labels:
            raise KeyError(key)
        labels[key].update(changes)

    try:
        updated = get_store().update_cluster(cluster_name, mutate)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown entry {e}") from e
    reload_cluster_config()
    return updated[section][key]


def _data_status(cluster_name: str) -> dict[str, Any]:
    try:
        min_date, max_date = get_datastore().get_min_max_dates(cluster_name)
    except Exception as e:  # datastore may not know the cluster yet
        logger.debug("No data status for %s: %s", cluster_name, e)
        min_date = max_date = None
    record = get_cluster_db().get_cluster_by_name(cluster_name) or {}
    return {
        "min_date": min_date,
        "max_date": max_date,
        "last_submission": record.get("last_submission"),
        "total_jobs_submitted": record.get("total_jobs_submitted", 0),
    }


@router.get("/status")
async def cluster_status(cluster_name: str, _admin: str = Depends(get_current_admin)) -> dict[str, Any]:
    """Sync and data status of one cluster, plus whether it has a configuration entry."""
    record = get_cluster_db().get_cluster_by_name(cluster_name)
    entry = get_store().get_cluster(cluster_name)
    if record is None and entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown cluster '{cluster_name}'")

    nodes = (entry or {}).get("node_labels") or {}
    synced = [n for n, info in nodes.items() if (info or {}).get("hardware")]
    metadata = (entry or {}).get("metadata") or {}
    return {
        "name": cluster_name,
        "id": record["id"] if record else None,
        "config_present": entry is not None,
        "identity": {
            "display_name": (entry or {}).get("display_name"),
            "description": (entry or {}).get("description"),
            "location": metadata.get("location"),
            "owner": metadata.get("owner"),
            "contact": metadata.get("contact"),
            "url": metadata.get("url"),
        },
        "sync": {
            "last_sync": metadata.get("last_hardware_sync"),
            "slurm_version": metadata.get("slurm_version"),
            "slurm_cluster_name": metadata.get("slurm_cluster_name"),
            "nodes_synced": len(synced),
            "nodes_from_data_only": len(nodes) - len(synced),
            "partitions": len((entry or {}).get("partition_labels") or {}),
            "accounts": len((entry or {}).get("account_labels") or {}),
        },
        "data": _data_status(cluster_name),
    }


@router.patch("/identity")
async def update_identity(
    cluster_name: str, request: ClusterIdentityUpdate, _admin: str = Depends(get_current_admin)
) -> dict[str, Any]:
    """Update display name, description and metadata.

    Description, contact and location are mirrored to the cluster record.
    """
    changes = request.model_dump(exclude_none=True)

    def mutate(cluster: dict[str, Any]) -> None:
        for key in ("display_name", "description"):
            if key in changes:
                cluster[key] = changes[key]
        metadata = cluster.setdefault("metadata", {}) or {}
        cluster["metadata"] = metadata
        for key in ("location", "owner", "contact", "url"):
            if key in changes:
                metadata[key] = changes[key]

    try:
        updated = get_store().update_cluster(cluster_name, mutate)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No configuration for cluster '{cluster_name}'"
        ) from e
    reload_cluster_config()

    db = get_cluster_db()
    record = db.get_cluster_by_name(cluster_name)
    if record:
        db.update_cluster(
            cluster_id=record["id"],
            description=changes.get("description"),
            contact_email=changes.get("contact"),
            location=changes.get("location"),
        )
    metadata = updated.get("metadata") or {}
    return {
        "display_name": updated.get("display_name"),
        "description": updated.get("description"),
        **{k: metadata.get(k) for k in ("location", "owner", "contact", "url")},
    }


@router.patch("/nodes/{node_name}")
async def update_node_label(
    cluster_name: str, node_name: str, request: NodeLabelUpdate, _admin: str = Depends(get_current_admin)
) -> dict[str, Any]:
    """Update a node's synonyms, description or type. Hardware is owned by the agent sync."""
    return _update_entry(cluster_name, "node_labels", node_name, request.model_dump(exclude_none=True))


@router.patch("/partitions/{partition_name}")
async def update_partition_label(
    cluster_name: str, partition_name: str, request: PartitionLabelUpdate, _admin: str = Depends(get_current_admin)
) -> dict[str, Any]:
    """Update a partition's display name or description."""
    return _update_entry(cluster_name, "partition_labels", partition_name, request.model_dump(exclude_none=True))


@router.patch("/accounts/{account_name}")
async def update_account_label(
    cluster_name: str, account_name: str, request: AccountLabelUpdate, _admin: str = Depends(get_current_admin)
) -> dict[str, Any]:
    """Update an account's display name, short name, faculty or department."""
    return _update_entry(cluster_name, "account_labels", account_name, request.model_dump(exclude_none=True))


@router.get("/config")
async def cluster_config_entry(cluster_name: str, _admin: str = Depends(get_current_admin)) -> dict[str, Any]:
    """The cluster's full entry in clusters.yaml."""
    return _cluster_entry(cluster_name)
