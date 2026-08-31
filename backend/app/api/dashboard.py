import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query

from ..core.config import get_settings
from ..core.saml_auth import get_current_user_saml
from ..models.data_models import FilterRequest, HealthResponse, MetadataResponse

# Add parent directory to path to import the original datastore
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

try:
    from slurm_usage_history.app.datastore import PandasDataStore
    from slurm_usage_history.app.duckdb_datastore import DuckDBDataStore
except ImportError:
    DuckDBDataStore = None
    PandasDataStore = None

router = APIRouter()
settings = get_settings()

# Import shared datastore singleton
from ..datastore_singleton import get_datastore


def convert_numpy_to_native(obj: Any) -> Any:
    """Convert numpy/pandas types to Python native types for JSON serialization."""
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {key: convert_numpy_to_native(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [convert_numpy_to_native(item) for item in obj]
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if obj is None or isinstance(obj, (str, int, float)):
        return obj
    return str(obj)


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    try:
        datastore = get_datastore()
        hostnames = datastore.get_hostnames()
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            data_loaded=len(hostnames) > 0,
            hostnames=hostnames,
        )
    except Exception:
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            data_loaded=False,
            hostnames=[],
        )


@router.get("/version")
async def get_version() -> dict:
    """Get application version."""
    try:
        from _version import __version__

        return {"version": __version__}
    except ImportError:
        return {"version": "unknown"}


@router.get("/metadata", response_model=MetadataResponse)
async def get_metadata(
    hostname: str | None = Query(None, description="Filter metadata for specific hostname"),
    start_date: str | None = Query(None, description="Filter metadata from this date"),
    end_date: str | None = Query(None, description="Filter metadata until this date"),
    current_user: dict = Depends(get_current_user_saml),
) -> MetadataResponse:
    """Get metadata for all clusters including available filters.

    If start_date/end_date are provided, filter values will only include
    values present in that date range, preventing empty graphs.
    """
    try:
        datastore = get_datastore()
        hostnames = datastore.get_hostnames()

        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"[METADATA] Initial hostnames from datastore: {hostnames}")
        logger.info(f"[METADATA] Query parameter hostname: {hostname}")

        # If hostname filter is provided, only return metadata for that hostname
        if hostname:
            if hostname not in hostnames:
                raise HTTPException(status_code=404, detail=f"Hostname {hostname} not found")
            hostnames = [hostname]
            logger.info(f"[METADATA] Filtered to: {hostnames}")

        partitions = {}
        accounts = {}
        users = {}
        qos = {}
        states = {}
        date_ranges = {}

        for host in hostnames:
            # If date range is provided, get filter values from filtered data
            if start_date or end_date:
                filter_values = datastore.get_filter_values_for_period(
                    hostname=host, start_date=start_date, end_date=end_date
                )
                partitions[host] = filter_values["partitions"]
                accounts[host] = filter_values["accounts"]
                users[host] = filter_values["users"]
                qos[host] = filter_values["qos"]
                states[host] = filter_values["states"]
            else:
                # Otherwise get all values from full dataset
                partitions[host] = datastore.get_partitions(host)
                accounts[host] = datastore.get_accounts(host)
                users[host] = datastore.get_users(host)
                qos[host] = datastore.get_qos(host)
                states[host] = datastore.get_states(host)

            min_date, max_date = datastore.get_min_max_dates(host)
            date_ranges[host] = {"min_date": min_date or "", "max_date": max_date or ""}

        # Determine which hostnames to return
        returned_hostnames = list(hostnames) if hostname else datastore.get_hostnames()
        logger.info(f"[METADATA] Returning hostnames: {returned_hostnames}")

        return MetadataResponse(
            hostnames=returned_hostnames,
            partitions=partitions,
            accounts=accounts,
            users=users,
            qos=qos,
            states=states,
            date_ranges=date_ranges,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching metadata: {e!s}")


@router.post("/reload-data")
async def reload_data(hostname: str | None = None, current_user: dict = Depends(get_current_user_saml)) -> dict:
    """Reload data from disk, checking for new/updated files.

    Args:
        hostname: Optional cluster hostname to reload. If not provided, checks all clusters.

    Returns:
        Status message with information about updated clusters.
    """
    try:
        # Clear chart cache since we're reloading data
        from .charts import clear_chart_cache

        clear_chart_cache()

        datastore = get_datastore()

        if hostname:
            # Reload specific cluster
            if hostname not in datastore.get_hostnames():
                raise HTTPException(status_code=404, detail=f"Cluster '{hostname}' not found")

            # Force reload by checking for updates
            updated = datastore.check_for_updates()

            return {
                "status": "success",
                "message": f"Data reload completed for {hostname}",
                "updated": updated,
                "hostname": hostname,
            }
        # Check all clusters for updates
        updated = datastore.check_for_updates()

        # Re-initialize hosts to pick up any new cluster directories
        datastore._initialize_hosts()
        hostnames = datastore.get_hostnames()

        # Load data for any newly discovered clusters
        for host in hostnames:
            if datastore.hosts[host]["data"] is None:
                datastore._load_host_data(host)

        return {
            "status": "success",
            "message": "Data reload completed for all clusters",
            "updated": updated,
            "clusters": hostnames,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reloading data: {e!s}")


@router.post("/filter")
async def filter_data(request: FilterRequest, current_user: dict = Depends(get_current_user_saml)) -> dict:
    """Filter data based on provided criteria and return aggregated results."""
    try:
        datastore = get_datastore()

        # Apply filters
        df = datastore.filter(
            hostname=request.hostname,
            start_date=request.start_date,
            end_date=request.end_date,
            partitions=request.partitions,
            accounts=request.accounts,
            users=request.users,
            qos=request.qos,
            states=request.states,
            complete_periods_only=request.complete_periods_only,
            period_type=request.period_type,
        )

        if df.empty:
            return {
                "total_jobs": 0,
                "total_cpu_hours": 0.0,
                "total_gpu_hours": 0.0,
                "total_users": 0,
                "data": [],
            }

        # Convert to records for JSON serialization
        records = df.to_dict(orient="records")

        # Convert numpy types to native Python types
        records = [convert_numpy_to_native(record) for record in records]

        # Calculate summary statistics
        summary = {
            "total_jobs": len(df),
            "total_cpu_hours": float(df["CPUHours"].sum()) if "CPUHours" in df.columns else 0.0,
            "total_gpu_hours": float(df["GPUHours"].sum()) if "GPUHours" in df.columns else 0.0,
            "total_users": int(df["User"].nunique()) if "User" in df.columns else 0,
            "data": records,
        }

        return summary

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error filtering data: {e!s}")


@router.get("/stats/{hostname}")
async def get_cluster_stats(
    hostname: str,
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    current_user: dict = Depends(get_current_user_saml),
) -> dict:
    """Get statistics for a specific cluster."""
    try:
        datastore = get_datastore()

        if hostname not in datastore.get_hostnames():
            raise HTTPException(status_code=404, detail=f"Cluster {hostname} not found")

        df = datastore.filter(
            hostname=hostname,
            start_date=start_date,
            end_date=end_date,
        )

        if df.empty:
            return {
                "hostname": hostname,
                "total_jobs": 0,
                "total_cpu_hours": 0.0,
                "total_gpu_hours": 0.0,
                "total_users": 0,
                "partitions": [],
            }

        stats = {
            "hostname": hostname,
            "total_jobs": len(df),
            "total_cpu_hours": float(df["CPUHours"].sum()) if "CPUHours" in df.columns else 0.0,
            "total_gpu_hours": float(df["GPUHours"].sum()) if "GPUHours" in df.columns else 0.0,
            "total_users": df["User"].nunique() if "User" in df.columns else 0,
            "partitions": df["Partition"].unique().tolist() if "Partition" in df.columns else [],
        }

        return stats

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {e!s}")
