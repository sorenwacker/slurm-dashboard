#!/usr/bin/env python3
"""
SLURM Usage History Exporter - Standalone cluster agent
Extracts SLURM job data and submits it to the dashboard API
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from slurm_usage_history.memory import parse_memory_to_mb, parse_reqmem_to_mb


def parse_duration_hours(value) -> float | None:
    """Convert a SLURM duration ([D-]HH:MM:SS or MM:SS[.ms]) to hours; None when absent or unparseable."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() in ("none", "unknown", "nan"):
        return None
    days = 0
    if "-" in text:
        day_part, text = text.split("-", 1)
        try:
            days = int(day_part)
        except ValueError:
            return None
    parts = text.split(":")
    try:
        if len(parts) == 3:
            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            seconds = int(parts[0]) * 60 + float(parts[1])
        else:
            return None
    except ValueError:
        return None
    return days * 24.0 + seconds / 3600.0


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("slurm-usage-history-exporter")


SLURM_MISSING_VALUES = {"", "none", "unknown", "nan", "nat"}


def normalize_timestamp(value) -> str | None:
    """Return a timestamp string, or None for sacct placeholders such as ``None`` and ``Unknown``."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if text.lower() in SLURM_MISSING_VALUES:
        return None
    return text


class SlurmDataExtractor:
    """Extracts job data from SLURM using sacct command"""

    SACCT_FORMAT = (
        "JobID,User,QOS,Account,Partition,Submit,Start,End,State,"
        "Elapsed,AveDiskRead,AveDiskWrite,AveCPU,MaxRSS,AllocCPUS,"
        "TotalCPU,NodeList,AllocTRES,ReqMem,Cluster"
    )

    def __init__(self, cluster_name: str | None = None):
        self.cluster_name = cluster_name or self._get_cluster_name()
        logger.info(f"Initialized extractor for cluster: {self.cluster_name}")

    def _get_cluster_name(self) -> str:
        """Auto-detect cluster name from SLURM or hostname"""
        try:
            result = subprocess.run(
                ["scontrol", "show", "config"], capture_output=True, text=True, timeout=10, check=False
            )
            for line in result.stdout.split("\n"):
                if line.startswith("ClusterName"):
                    return line.split("=")[1].strip()
        except Exception as e:
            logger.warning(f"Could not detect cluster name from SLURM: {e}")

        # Fallback to hostname
        import socket

        return socket.gethostname().split(".")[0]

    def extract_jobs(self, start_date: str, end_date: str, all_users: bool = True) -> pd.DataFrame:
        """
        Extract jobs from SLURM using sacct

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            all_users: If True, fetch data for all users (requires admin)

        Returns:
            DataFrame with job records
        """
        logger.info(f"Extracting jobs from {start_date} to {end_date}")

        cmd = [
            "sacct",
            f"--format={self.SACCT_FORMAT}",
            "--parsable2",
            f"--starttime={start_date}",
            f"--endtime={end_date}",
        ]

        if all_users:
            cmd.append("--allusers")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True)

            if not result.stdout.strip():
                logger.warning("No data returned from sacct")
                return pd.DataFrame()

            # Parse the pipe-separated output
            lines = result.stdout.strip().split("\n")
            headers = lines[0].split("|")
            data = [line.split("|") for line in lines[1:]]

            df = pd.DataFrame(data, columns=headers)
            logger.info(f"Extracted {len(df)} raw job records")

            # Filter out unwanted states
            df = df[~df["State"].isin(["RUNNING", "Unknown", "PENDING"])]
            logger.info(f"Filtered to {len(df)} completed job records")

            # Filter by Submit date to ensure we only get jobs within the requested range
            # sacct filters by End time, but we want to filter by Submit time
            if not df.empty and "Submit" in df.columns:
                df["Submit"] = pd.to_datetime(df["Submit"], errors="coerce")
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)  # Make end_date inclusive

                initial_count = len(df)
                df = df[(df["Submit"] >= start_dt) & (df["Submit"] < end_dt)]
                filtered_count = initial_count - len(df)

                if filtered_count > 0:
                    logger.info(f"Filtered out {filtered_count} jobs outside Submit date range")

            return df

        except subprocess.TimeoutExpired:
            logger.error("sacct command timed out")
            raise
        except subprocess.CalledProcessError as e:
            logger.error(f"sacct command failed: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Error extracting jobs: {e}")
            raise

    def format_jobs(self, df: pd.DataFrame) -> list[dict]:
        """
        Format raw SLURM data into dashboard API format

        Args:
            df: Raw DataFrame from sacct

        Returns:
            List of job dictionaries ready for API submission
        """
        if df.empty:
            return []

        logger.info("Formatting job data")

        # Helper to normalize field values (handle nulls and empty strings)
        def normalize_field(value, default="unknown"):
            """Normalize field value by handling nulls and empty strings"""
            if pd.isna(value):
                return default
            str_val = str(value).strip()
            if not str_val or str_val.lower() in ("nan", "none"):
                return default
            return str_val

        # Normalize job state (e.g., "CANCELLED by 12345" -> "CANCELLED")
        def normalize_state(state_str):
            """Normalize SLURM job state by removing suffixes like 'by XXX'"""
            if pd.isna(state_str) or not state_str:
                return "UNKNOWN"
            state = str(state_str).strip()
            if not state or state.lower() in ("nan", "none"):
                return "UNKNOWN"
            # Handle "CANCELLED by XXX", "TIMEOUT by XXX", etc.
            if " by " in state:
                return state.split(" by ")[0].strip()
            return state

        # Parse AllocTRES to extract CPU, GPU, memory info
        def parse_alloc_tres(tres_str):
            """Parse AllocTRES string like 'cpu=4,mem=16G,gres/gpu=2'"""
            result = {"cpu": 0, "gpu": 0, "mem": None}
            if pd.isna(tres_str) or not tres_str:
                return result

            for item in tres_str.split(","):
                if "=" in item:
                    key, val = item.split("=", 1)
                    key = key.strip().lower()

                    if "cpu" in key:
                        result["cpu"] = int(val)
                    elif "gpu" in key:
                        result["gpu"] = int(val)
                    elif "mem" in key:
                        result["mem"] = parse_memory_to_mb(val)

            return result

        # Parse elapsed time to hours
        def elapsed_to_hours(elapsed_str):
            """Convert SLURM elapsed time format to hours"""
            if pd.isna(elapsed_str) or not elapsed_str:
                return 0.0

            try:
                # Format can be: days-HH:MM:SS, HH:MM:SS, MM:SS
                total_seconds = 0

                if "-" in elapsed_str:
                    days, time_part = elapsed_str.split("-")
                    total_seconds += int(days) * 86400
                else:
                    time_part = elapsed_str

                parts = time_part.split(":")
                if len(parts) == 3:
                    hours, mins, secs = parts
                    total_seconds += int(hours) * 3600 + int(mins) * 60 + float(secs)
                elif len(parts) == 2:
                    mins, secs = parts
                    total_seconds += int(mins) * 60 + float(secs)

                return total_seconds / 3600.0
            except Exception as e:
                logger.warning(f"Could not parse elapsed time '{elapsed_str}': {e}")
                return 0.0

        # MaxRSS is reported on step rows (e.g. 100.batch, 100.0); fold the
        # maximum over all steps onto the parent job before the steps are dropped.
        base_job_id = df["JobID"].astype(str).str.split(".").str[0]
        if "MaxRSS" in df.columns:
            step_max_rss = df["MaxRSS"].map(parse_memory_to_mb).groupby(base_job_id).max()
        else:
            step_max_rss = pd.Series(dtype=float)
        df["MaxRSSMB"] = base_job_id.map(step_max_rss)

        # Apply formatting
        df["AllocTRESParsed"] = df["AllocTRES"].apply(parse_alloc_tres)
        df["AllocCPUS"] = df["AllocTRESParsed"].apply(lambda x: x["cpu"] if x["cpu"] > 0 else 0)
        df["AllocGPUS"] = df["AllocTRESParsed"].apply(lambda x: x["gpu"])
        df["ElapsedHours"] = df["Elapsed"].apply(elapsed_to_hours)

        # Calculate resource-hours
        df["CPUHours"] = df["ElapsedHours"] * df["AllocCPUS"]
        df["GPUHours"] = df["ElapsedHours"] * df["AllocGPUS"]

        # Count nodes
        def count_nodes(nodelist):
            if pd.isna(nodelist) or not nodelist:
                return 0
            # Simple count - could be improved for range notation
            return len([n for n in nodelist.split(",") if n.strip()])

        df["AllocNodes"] = df["NodeList"].apply(count_nodes)

        # Requested memory: AllocTRES mem= first, sacct ReqMem as fallback
        def requested_memory(row):
            tres_mem = row["AllocTRESParsed"]["mem"]
            if tres_mem is not None:
                return tres_mem
            if "ReqMem" not in row:
                return None
            return parse_reqmem_to_mb(row["ReqMem"], row["AllocCPUS"], row["AllocNodes"])

        df["ReqMemMB"] = df.apply(requested_memory, axis=1)

        # Consumed core-time (TotalCPU) as a measured counterpart to CPUHours
        if "TotalCPU" in df.columns:
            df["CPUUsedHours"] = df["TotalCPU"].map(parse_duration_hours)
        else:
            df["CPUUsedHours"] = None

        # Filter out jobs with missing critical fields (malformed data)
        initial_count = len(df)

        # Check for empty/null User
        df = df[
            df["User"].notna()
            & (df["User"].astype(str).str.strip() != "")
            & (df["User"].astype(str).str.lower() != "nan")
        ]

        # Check for empty/null Partition
        df = df[
            df["Partition"].notna()
            & (df["Partition"].astype(str).str.strip() != "")
            & (df["Partition"].astype(str).str.lower() != "nan")
        ]

        filtered_count = initial_count - len(df)
        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} jobs with missing User or Partition fields")

        # Convert to list of dicts
        jobs = []
        for _, row in df.iterrows():
            job = {
                "JobID": str(row["JobID"]),
                "User": normalize_field(row["User"], "unknown"),
                "Account": normalize_field(row["Account"], "unknown"),
                "Partition": normalize_field(row["Partition"], "unknown"),
                "State": normalize_state(row["State"]),
                "QOS": normalize_field(row["QOS"], None),
                "Submit": str(row["Submit"]),
                "Start": normalize_timestamp(row["Start"]),
                "End": normalize_timestamp(row["End"]),
                "CPUHours": float(row["CPUHours"]),
                "GPUHours": float(row["GPUHours"]),
                "AllocCPUS": int(row["AllocCPUS"]),
                "AllocGPUS": int(row["AllocGPUS"]),
                "AllocNodes": int(row["AllocNodes"]),
                "NodeList": str(row["NodeList"]) if pd.notna(row["NodeList"]) else None,
                "ReqMemMB": float(row["ReqMemMB"]) if pd.notna(row["ReqMemMB"]) else None,
                "MaxRSSMB": float(row["MaxRSSMB"]) if pd.notna(row["MaxRSSMB"]) else None,
                "CPUUsedHours": float(row["CPUUsedHours"]) if pd.notna(row["CPUUsedHours"]) else None,
            }
            jobs.append(job)

        logger.info(f"Formatted {len(jobs)} jobs for submission")
        return jobs


class DashboardClient:
    """Client for submitting data to the dashboard API"""

    def __init__(self, api_url: str, api_key: str, timeout: int = 30):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

        # Configure session with retries
        # Retry with exponential backoff: 2s, 4s, 8s, 16s, 32s (total ~62s + request time)
        self.session = requests.Session()
        retry_strategy = Retry(
            total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["POST", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"Initialized dashboard client for {api_url}")

    def submit_jobs(self, hostname: str, jobs: list[dict]) -> dict:
        """
        Submit job data to the dashboard API

        Args:
            hostname: Cluster hostname
            jobs: List of job dictionaries

        Returns:
            API response dictionary
        """
        if not jobs:
            logger.warning("No jobs to submit")
            return {"success": False, "message": "No jobs to submit"}

        endpoint = f"{self.api_url}/api/data/ingest"
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        payload = {"hostname": hostname, "jobs": jobs}

        logger.info(f"Submitting {len(jobs)} jobs to {endpoint}")

        try:
            response = self.session.post(endpoint, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Successfully submitted: {result.get('message', 'OK')}")
            return result

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            logger.error(f"Response: {e.response.text}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out: {e}")
            raise
        except Exception as e:
            logger.error(f"Error submitting jobs: {e}")
            raise

    def check_health(self) -> dict:
        """Check dashboard health status"""
        endpoint = f"{self.api_url}/api/dashboard/health"
        try:
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise


def load_config(config_path: Path) -> dict:
    """Load configuration from JSON file"""
    logger.info(f"Loading configuration from {config_path}")

    if not config_path.exists():
        msg = f"Configuration file not found: {config_path}"
        raise FileNotFoundError(msg)

    with open(config_path) as f:
        config = json.load(f)

    # Validate required fields
    required = ["api_url", "api_key"]
    for field in required:
        if field not in config:
            msg = f"Missing required configuration field: {field}"
            raise ValueError(msg)

    return config


def generate_weekly_chunks(start_date: str, end_date: str) -> list[tuple]:
    """
    Split date range into weekly chunks to avoid overloading SLURM and API.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of (chunk_start, chunk_end) tuples
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    chunks = []
    current = start

    while current <= end:
        chunk_end = min(current + timedelta(days=6), end)
        chunks.append((current.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")))
        current = chunk_end + timedelta(days=1)

    return chunks


def main():
    parser = argparse.ArgumentParser(description="Extract SLURM job data and submit to dashboard")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("/etc/slurm-usage-history-exporter/config.json"),
        help="Path to configuration file (default: /etc/slurm-usage-history-exporter/config.json)",
    )
    parser.add_argument("--start-date", type=str, help="Start date in YYYY-MM-DD format (default: 7 days ago)")
    parser.add_argument("--end-date", type=str, help="End date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--cluster-name", type=str, help="Override cluster name (auto-detected if not provided)")
    parser.add_argument("--dry-run", action="store_true", help="Extract and format data but do not submit to API")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Calculate date range
    end_date = args.end_date or datetime.now().strftime("%Y-%m-%d")
    start_date = args.start_date or (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    # Split into weekly chunks to avoid overloading SLURM and API
    chunks = generate_weekly_chunks(start_date, end_date)
    logger.info(f"Processing {len(chunks)} weekly chunk(s) from {start_date} to {end_date}")

    try:
        # Load configuration
        config = load_config(args.config)

        # Use cluster name from CLI arg, config file, or auto-detect (in that order)
        cluster_name = args.cluster_name or config.get("cluster_name") or None

        # Initialize extractor
        extractor = SlurmDataExtractor(cluster_name=cluster_name)

        # Initialize dashboard client (unless dry run)
        client = None
        if not args.dry_run:
            client = DashboardClient(
                api_url=config["api_url"], api_key=config["api_key"], timeout=config.get("timeout", 120)
            )
            # Check health first
            health = client.check_health()
            logger.info(f"Dashboard health: {health.get('status', 'unknown')}")

        # Process each chunk
        total_jobs = 0
        total_cpu_hours = 0.0
        total_gpu_hours = 0.0

        for i, (chunk_start, chunk_end) in enumerate(chunks, 1):
            logger.info(f"Processing chunk {i}/{len(chunks)}: {chunk_start} to {chunk_end}")

            # Extract jobs for this chunk
            df = extractor.extract_jobs(chunk_start, chunk_end)

            if df.empty:
                logger.info(f"  No jobs in chunk {i}")
                continue

            # Format jobs
            jobs = extractor.format_jobs(df)
            chunk_cpu_hours = sum(j["CPUHours"] for j in jobs)
            chunk_gpu_hours = sum(j["GPUHours"] for j in jobs)

            logger.info(
                f"  Chunk {i}: {len(jobs)} jobs, {chunk_cpu_hours:.2f} CPU-hours, {chunk_gpu_hours:.2f} GPU-hours"
            )

            total_jobs += len(jobs)
            total_cpu_hours += chunk_cpu_hours
            total_gpu_hours += chunk_gpu_hours

            if args.dry_run:
                # Show sample of first job in first chunk
                if i == 1 and jobs:
                    logger.info(f"  Sample job: {json.dumps(jobs[0], indent=2)}")
            else:
                # Submit chunk to dashboard
                result = client.submit_jobs(extractor.cluster_name, jobs)
                logger.info(f"  Chunk {i} submitted: {result.get('message', 'OK')}")

        # Summary
        if args.dry_run:
            logger.info("DRY RUN SUMMARY:")
            logger.info(f"  Cluster: {extractor.cluster_name}")
            logger.info(f"  Total jobs: {total_jobs}")
            logger.info(f"  Total CPU-hours: {total_cpu_hours:.2f}")
            logger.info(f"  Total GPU-hours: {total_gpu_hours:.2f}")
        else:
            logger.info("SUBMISSION COMPLETE:")
            logger.info(f"  Total jobs submitted: {total_jobs}")
            logger.info(f"  Total CPU-hours: {total_cpu_hours:.2f}")
            logger.info(f"  Total GPU-hours: {total_gpu_hours:.2f}")

        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
