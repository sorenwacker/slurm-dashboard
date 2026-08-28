import logging
import traceback
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from ..core.admin_auth import get_current_admin
from ..core.auth import verify_api_key
from ..core.config import get_settings
from ..datastore_singleton import get_datastore
from ..db.clusters import get_cluster_db
from ..models.data_models import DataIngestionRequest, DataIngestionResponse

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("/ingest", response_model=DataIngestionResponse)
async def ingest_data(
    request: DataIngestionRequest,
    cluster_name: str = Depends(verify_api_key),
) -> DataIngestionResponse:
    """Ingest job data for a specific cluster.

    This endpoint accepts job records and stores them as parquet files.
    Requires API key authentication via X-API-Key header.

    Args:
        request: Data ingestion request containing hostname and job records
        api_key: Verified API key from header

    Returns:
        DataIngestionResponse with ingestion status
    """
    try:
        # Create directory structure for hostname
        data_dir = Path(settings.data_path) / request.hostname / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        # Convert jobs to DataFrame
        jobs_data = [job.model_dump() for job in request.jobs]
        df = pd.DataFrame(jobs_data)

        # Convert datetime columns
        datetime_cols = ["Submit", "Start", "End"]
        for col in datetime_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])

        # Normalize column names for consistency
        rename_map = {
            "AllocNodes": "Nodes",
            "AllocCPUS": "CPUs",
            "AllocGPUS": "GPUs"
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        # Add derived columns for efficient querying
        if "Submit" in df.columns:
            df["SubmitDay"] = df["Submit"].dt.normalize()
            df["SubmitYearMonth"] = df["Submit"].dt.to_period("M").astype(str)
            df["SubmitYearWeek"] = df["Submit"].dt.to_period("W").dt.start_time.dt.strftime("%Y-%m-%d")
            df["SubmitYear"] = df["Submit"].dt.year

        if "Start" in df.columns:
            df["StartDay"] = df["Start"].dt.normalize()
            df["StartYearMonth"] = df["Start"].dt.to_period("M").astype(str)
            # Vectorized so NaT (jobs that never started) stays NaT instead of raising
            df["StartYearWeek"] = df["Start"].dt.to_period("W").dt.start_time.dt.strftime("%Y-%m-%d")
            df["StartYear"] = df["Start"].dt.year

        # Calculate timing columns
        if "Submit" in df.columns and "Start" in df.columns:
            df["WaitingTimeHours"] = (df["Start"] - df["Submit"]).dt.total_seconds() / 3600.0
        if "Start" in df.columns and "End" in df.columns:
            df["ElapsedHours"] = (df["End"] - df["Start"]).dt.total_seconds() / 3600.0

        # Group by year and append to yearly files (instead of creating timestamped files)
        years = df["SubmitYear"].unique() if "SubmitYear" in df.columns else []
        jobs_saved = 0

        for year in sorted(years):
            year_df = df[df["SubmitYear"] == year].copy()
            year_file = data_dir / f"jobs_{year}.parquet"

            # Load existing file if it exists
            if year_file.exists():
                try:
                    existing_df = pd.read_parquet(year_file)
                    logger.info(f"Appending {len(year_df)} jobs to existing {year} file with {len(existing_df)} jobs")

                    # Concatenate
                    combined_df = pd.concat([existing_df, year_df], ignore_index=True)

                    # Deduplicate by JobID (keep latest)
                    if "JobID" in combined_df.columns:
                        before = len(combined_df)
                        combined_df = combined_df.drop_duplicates(subset=["JobID"], keep="last")
                        logger.info(f"Deduplicated {before - len(combined_df)} duplicate jobs")

                    year_df = combined_df
                except Exception as e:
                    logger.warning(f"Failed to load existing {year} file, will overwrite: {e}")
            else:
                logger.info(f"Creating new {year} file with {len(year_df)} jobs")

            # Save yearly file
            year_df.to_parquet(year_file, index=False, engine="pyarrow")
            jobs_saved += len(year_df)
            logger.info(f"Saved {len(year_df)} jobs to {year_file.name}")

        # Update submission stats
        db = get_cluster_db()
        db.update_submission_stats(request.hostname, len(request.jobs))

        # Trigger datastore reload for this hostname
        try:
            logger.info(f"Triggering datastore reload after ingesting data for {request.hostname}")
            datastore = get_datastore()
            datastore.load_data()
            logger.info(f"Datastore reload completed. New date range: {datastore.get_min_max_dates(request.hostname)}")
        except Exception as e:
            # Log but don't fail the ingestion
            logger.error(f"Failed to reload datastore after ingestion: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

        return DataIngestionResponse(
            success=True,
            message=f"Successfully ingested {len(request.jobs)} jobs for {request.hostname}",
            jobs_processed=len(request.jobs),
            hostname=request.hostname,
        )

    except Exception as e:
        logger.error(f"Error ingesting data for {request.hostname}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error ingesting data: {str(e)}",
        ) from e


@router.post("/reload")
async def reload_datastore(
    admin: dict = Depends(get_current_admin),
) -> dict:
    """Manually trigger datastore reload.

    This endpoint forces a reload of all metadata from parquet files.
    Useful after data ingestion if automatic reload fails.
    Requires admin authentication.

    Returns:
        Status message with hostnames and date ranges
    """
    try:
        logger.info(f"Admin {admin} triggered manual datastore reload")
        datastore = get_datastore()
        datastore.load_data()

        # Get updated metadata
        hostnames = datastore.get_hostnames()
        date_ranges = {}
        for hostname in hostnames:
            min_date, max_date = datastore.get_min_max_dates(hostname)
            date_ranges[hostname] = {"min_date": min_date, "max_date": max_date}

        logger.info(f"Datastore reload completed. Hostnames: {hostnames}")

        return {
            "success": True,
            "message": f"Datastore reloaded successfully for {len(hostnames)} cluster(s)",
            "hostnames": hostnames,
            "date_ranges": date_ranges,
        }

    except Exception as e:
        logger.error(f"Manual datastore reload failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error reloading datastore: {str(e)}",
        )
