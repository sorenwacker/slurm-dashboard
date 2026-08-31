#!/usr/bin/env python3
"""
Weekly data consolidation script
Consolidates any orphaned timestamped files into yearly files
Run via cron: 0 2 * * 0 (Sunday 2 AM)
"""

import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def consolidate_cluster_data(data_dir: Path):
    """Consolidate all timestamped files into yearly files"""

    weekly_data_dir = data_dir / "weekly-data"
    if not weekly_data_dir.exists():
        logger.warning(f"Directory does not exist: {weekly_data_dir}")
        return

    # Find all timestamped files (jobs_YYYYMMDD_*.parquet)
    timestamped_files = sorted(weekly_data_dir.glob("jobs_????????_*.parquet"))

    if not timestamped_files:
        logger.info(f"No timestamped files to consolidate in {weekly_data_dir}")
        return

    logger.info(f"Found {len(timestamped_files)} timestamped files to consolidate")

    # Load all timestamped files grouped by year
    year_data = {}

    for f in timestamped_files:
        logger.info(f"Loading {f.name}")
        try:
            df = pd.read_parquet(f)

            # Determine year from data
            if "Submit" in df.columns:
                df["Submit"] = pd.to_datetime(df["Submit"])
                year = df["Submit"].dt.year.mode()[0] if len(df) > 0 else None

                if year:
                    if year not in year_data:
                        year_data[year] = []
                    year_data[year].append(df)
                    logger.info(f"  {len(df)} jobs for year {year}")
        except Exception as e:
            logger.error(f"Error loading {f.name}: {e}")

    # Consolidate each year
    for year, dfs in year_data.items():
        year_file = weekly_data_dir / f"jobs_{year}.parquet"

        # Load existing yearly file if it exists
        if year_file.exists():
            try:
                existing_df = pd.read_parquet(year_file)
                dfs.insert(0, existing_df)
                logger.info(f"Loaded existing {year} file with {len(existing_df)} jobs")
            except Exception as e:
                logger.warning(f"Failed to load existing {year} file: {e}")

        # Concatenate all dataframes for this year
        combined_df = pd.concat(dfs, ignore_index=True)
        logger.info(f"Combined {len(combined_df)} total jobs for {year}")

        # Deduplicate by JobID
        if "JobID" in combined_df.columns:
            before = len(combined_df)
            combined_df = combined_df.drop_duplicates(subset=["JobID"], keep="last")
            logger.info(f"Deduplicated {before - len(combined_df)} jobs, {len(combined_df)} unique")

        # Save consolidated file
        combined_df.to_parquet(year_file, index=False)
        logger.info(f"Saved {len(combined_df)} jobs to {year_file.name}")

    # Remove timestamped files
    for f in timestamped_files:
        logger.info(f"Removing {f.name}")
        f.unlink()

    logger.info("Consolidation complete!")


def main():
    # Consolidate data for all clusters
    data_path = Path("/data/slurm-usage-history")

    if not data_path.exists():
        logger.error(f"Data path does not exist: {data_path}")
        return 1

    # Find all cluster directories
    cluster_dirs = [d for d in data_path.iterdir() if d.is_dir()]
    logger.info(f"Found {len(cluster_dirs)} cluster directories")

    for cluster_dir in cluster_dirs:
        logger.info(f"\nConsolidating data for {cluster_dir.name}")
        try:
            consolidate_cluster_data(cluster_dir)
        except Exception as e:
            logger.error(f"Error consolidating {cluster_dir.name}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
