# src/slurmo/app/data_fetcher.py

import argparse
import io
import os
import re
import subprocess
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

import pandas as pd
from tqdm import tqdm

from ..tools import categorize_time, month_to_date, unpack_nodelist_string, week_to_date


def parse_iso_week(iso_week_str: str) -> tuple[int, int]:
    """
    Parse an ISO week string in the format YYYY-Www (e.g., 2025-W01).

    Args:
        iso_week_str: ISO week string in the format YYYY-Www

    Returns:
        Tuple of (year, week_number)
    """
    match = re.match(r'(\d{4})-W(\d{1,2})', iso_week_str)
    if not match:
        msg = f"Invalid ISO week format: {iso_week_str}. Expected format: YYYY-Www (e.g., 2025-W01)"
        raise ValueError(msg)

    year = int(match.group(1))
    week = int(match.group(2))

    if week < 1 or week > 53:
        msg = f"Invalid week number: {week}. Week number must be between 1 and 53."
        raise ValueError(msg)

    return year, week


def calculate_date_range(
    weeks_back: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None
) -> tuple[int, int, int, int]:
    """
    Calculate date range for data extraction based on different inputs.

    Args:
        weeks_back: Number of weeks to go back from today
        from_date: Starting date in ISO week format (YYYY-Www)
        to_date: Ending date in ISO week format (YYYY-Www)

    Returns:
        Tuple of (from_year, from_week, until_year, until_week)
    """
    today = datetime.today()
    until_year = today.year
    until_week = today.isocalendar()[1]

    if weeks_back is not None:
        # Calculate date range based on weeks_back
        weeks_ago = today - timedelta(weeks=weeks_back)
        from_year = weeks_ago.year
        from_week = weeks_ago.isocalendar()[1]
    elif from_date is not None:
        # Parse from_date in ISO week format
        from_year, from_week = parse_iso_week(from_date)

        if to_date is not None:
            # Parse to_date in ISO week format
            until_year, until_week = parse_iso_week(to_date)
    else:
        # Default: 4 weeks back
        four_weeks_ago = today - timedelta(weeks=4)
        from_year = four_weeks_ago.year
        from_week = four_weeks_ago.isocalendar()[1]

    return from_year, from_week, until_year, until_week


class UsageDataFetcher:
    """
    Fetches usage data from the SLURM database.
    """

    def __init__(self, command_executor: Callable | None = None):
        """
        Initialize the UsageDataFetcher with an optional command executor.
        This allows dependency injection for better testing.

        Args:
            command_executor: Function to execute shell commands.
        """
        self.command_executor: Callable = command_executor or subprocess.run

    def export_usage_data(
        self,
        from_year: int,
        from_week: int,
        until_year: int | None = None,
        until_week: int | None = None,
        verbose: bool = False
    ) -> pd.DataFrame:
        """
        Export usage data for the specified date range.

        Args:
            from_year: Starting year
            from_week: Starting week
            until_year: Ending year (default: from_year)
            until_week: Ending week (default: from_week)
            verbose: Whether to print verbose output

        Returns:
            DataFrame containing the combined usage data
        """
        if until_year is None:
            until_year = from_year
        if until_week is None:
            until_week = from_week

        combined_df = pd.DataFrame()

        current_year = from_year
        current_week = from_week

        while (current_year < until_year) or (
            current_year == until_year and current_week <= until_week
        ):
            # Get the start and end dates of the week
            start_date, end_date = self.get_week_dates(current_year, current_week)

            # Format the dates as strings
            sacct_start = start_date.strftime("%Y-%m-%d")
            sacct_end = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")

            # Run the sacct command and get the DataFrame
            weekly_df = self.run_sacct_command(sacct_start, sacct_end, verbose=verbose)

            # Append the weekly data to the combined DataFrame
            combined_df = pd.concat([combined_df, weekly_df], ignore_index=True)

            # Increment the week
            if current_week == 52:
                current_week = 1
                current_year += 1
            else:
                current_week += 1

        return combined_df

    def run_sacct_command(
        self,
        sacct_start: str,
        sacct_end: str,
        verbose: bool = False
    ) -> pd.DataFrame:
        """
        Run the sacct command and return the output as a DataFrame.

        Args:
            sacct_start: Start time for the command.
            sacct_end: End time for the command.
            verbose: Whether to print verbose output.

        Returns:
            DataFrame containing the command output.
        """

        format_string = "--format=JobID,User,QOS,Account,Partition,Submit,Start,End,State,Elapsed,AveDiskRead,AveDiskWrite,AveCPU,MaxRSS,AllocCPUS,TotalCPU,NodeList,AllocTRES,Cluster"

        command: list[str] = [
            "sacct",
            format_string,
            "--parsable2",
            "--allusers",
            f"--starttime={sacct_start}",
            f"--endtime={sacct_end}",
        ]

        if verbose:
            print(" ".join(command))

        result = self.command_executor(
            command,
            stdout=subprocess.PIPE,
            text=True,
            encoding="latin-1",
            errors="ignore",
        )
        output = cast(subprocess.CompletedProcess, result).stdout

        # Filter out any lines containing "RUNNING" or "Unknown" states
        filtered_output = "\n".join(
            line
            for line in output.splitlines()
            if "RUNNING" not in line and "Unknown" not in line
        )

        df = pd.read_csv(io.StringIO(filtered_output), sep="|")
        if verbose:
            print(df.head())
        return df

    @staticmethod
    def get_week_dates(
        year: int,
        week: int,
        chunk_size: int = 7
    ) -> tuple[datetime, datetime]:
        """
        Calculate the start and end dates of a specific week.

        Args:
            year: The year.
            week: The week number.
            chunk_size: Number of days in the week (default is 7).

        Returns:
            Tuple containing the start and end dates of the week.
        """
        start_date = datetime.strptime(f"{year}-W{week:02d}-1", "%G-W%V-%u")
        end_date = start_date + timedelta(days=chunk_size - 1)
        return start_date, end_date


class UsageDataFormatter:
    """
    Formats the usage data DataFrame.
    """

    def __init__(self):
        """Initialize the UsageDataFormatter."""

    def format_usage_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Format the usage data DataFrame:
        - Convert Start, End, and Submit columns to datetime format.
        - Split AllocTRES into separate columns: billing, cpu, gres_gpu, mem, node.

        Args:
            df: DataFrame containing usage data fetched from sacct command.

        Returns:
            Formatted DataFrame with datetime columns and split AllocTRES.
        """
        # Convert Start, End, and Submit columns to datetime format
        df["Start"] = pd.to_datetime(df["Start"])
        df["End"] = pd.to_datetime(df["End"])
        df["Submit"] = pd.to_datetime(df["Submit"])

        df[["billing", "cpu", "gres_gpu", "mem", "node"]] = df["AllocTRES"].str.split(
            ",", expand=True
        )
        df["CPUs"] = df["cpu"].str.extract(r"cpu=(\d+)").fillna(0).astype(int)
        df["GPUs"] = df["gres_gpu"].str.extract(r"gres/gpu=(\d+)").fillna(0).astype(int)
        df["mem"] = df["mem"].str.extract(r"mem=(\d+[MG])")
        df["Memory [GB]"] = df.mem.apply(self.convert_mem_to_gb).astype(float)
        df["Nodes"] = df["node"].str.extract(r"node=(\d+)").fillna(0).astype(int)

        df["JobIDgroup"] = df.JobID.apply(lambda s: s.split(".")[0])
        df["Elapsed"] = df.End - df.Start
        df["Elapsed [h]"] = df["Elapsed"].apply(lambda x: x.total_seconds() / 3600)

        df = df.ffill()

        df["State"] = df.State.apply(lambda x: x.split()[0])

        df["StartDay"] = df.Start.dt.normalize()
        df["StartWeekDay"] = df.Start.dt.day_name()
        df["StartWeek"] = df.Start.dt.isocalendar().week
        df["StartMonth"] = df.Start.dt.month
        df["StartYear"] = df.Start.dt.year
        df["StartYear_iso"] = df.Start.dt.isocalendar().year
        df["StartYearWeek"] = (
            df.StartYear_iso.astype(str)
            + "-"
            + df.StartWeek.apply(lambda x: f"{x:02d}")
        )
        df["StartYearMonth"] = (
            df.StartYear.astype(str) + "-" + df.StartMonth.apply(lambda x: f"{x:02d}")
        )

        df["SubmitDay"] = df.Submit.dt.normalize()
        df["SubmitWeekDay"] = df.Submit.dt.day_name()
        df["SubmitWeek"] = df.Submit.dt.isocalendar().week
        df["SubmitMonth"] = df.Submit.dt.month
        df["SubmitYear"] = df.Submit.dt.year
        df["SubmitYear_iso"] = df.Submit.dt.isocalendar().year
        df["SubmitYearWeek"] = (
            df.SubmitYear_iso.astype(str)
            + "-"
            + df.SubmitWeek.apply(lambda x: f"{x:02d}")
        )
        df["SubmitYearMonth"] = (
            df.SubmitYear.astype(str) + "-" + df.SubmitMonth.apply(lambda x: f"{x:02d}")
        )

        df = df.query("JobID == JobIDgroup")
        df = df.drop(["AllocTRES", "mem", "JobIDgroup"], axis=1)

        df["WaitingTime [h]"] = (df.Start - df.Submit).dt.total_seconds() / 3600
        df["GPU-hours"] = df["Elapsed [h]"].fillna(0).astype(float) * df["GPUs"].fillna(
            0
        ).astype(float)
        df["CPU-hours"] = df["Elapsed [h]"].fillna(0).astype(float) * df["CPUs"].fillna(
            0
        ).astype(float)

        df["NodeList"] = df["NodeList"].apply(unpack_nodelist_string)

        df["StartYearWeek"] = df["StartYearWeek"].apply(week_to_date)
        df["StartYearMonth"] = df["StartYearMonth"].apply(month_to_date)
        df["SubmitYearWeek"] = df["SubmitYearWeek"].apply(week_to_date)
        df["SubmitYearMonth"] = df["SubmitYearMonth"].apply(month_to_date)
        df["SubmitDay"] = df["Submit"].dt.normalize()
        df["StartDay"] = df["Start"].dt.normalize()

        df["JobDuration"] = pd.Categorical(
            df["Elapsed [h]"].apply(categorize_time),
            categories=["<5s", "<1min", "<5min", "<1h", "<5h", "<24h", ">=24h"],
            ordered=True,
        )

        columns: list[str] = [
            "User",
            "QOS",
            "Account",
            "Partition",
            "Submit",
            "Start",
            "End",
            "SubmitDay",
            "SubmitWeekDay",
            "SubmitYearWeek",
            "SubmitYearMonth",
            "StartDay",
            "StartWeekDay",
            "StartYearWeek",
            "StartYearMonth",
            "State",
            "WaitingTime [h]",
            "Elapsed [h]",
            "Nodes",
            "NodeList",
            "CPUs",
            "GPUs",
            "CPU-hours",
            "GPU-hours",
            "AveCPU",
            "TotalCPU",
            "AveDiskRead",
            "AveDiskWrite",
            "MaxRSS",
            "Cluster"
        ]

        return df[columns]

    @staticmethod
    def convert_mem_to_gb(mem_value: str | float | None) -> float:
        """
        Convert memory value to gigabytes.

        Args:
            mem_value: Memory value with unit (e.g., "1000M" or "1G")

        Returns:
            Float value in gigabytes
        """
        if isinstance(mem_value, float):
            return mem_value

        if mem_value is None:
            return 0.0

        numeric_part = float(mem_value[:-1])
        unit = mem_value[-1]

        if unit == "M":
            multiplier = 1 / 1024
        elif unit == "G":
            multiplier = 1
        else:
            msg = f"Unsupported memory unit in {mem_value}"
            raise ValueError(msg)

        return numeric_part * multiplier


class DataExporter:
    """
    Exports the fetched and formatted data.
    """

    def __init__(
        self,
        data_fetcher: UsageDataFetcher,
        data_formatter: UsageDataFormatter,
        api_url: str | None = None,
        api_key: str | None = None,
        cluster_name: str | None = None,
    ):
        """
        Initialize the DataExporter.

        Args:
            data_fetcher: UsageDataFetcher instance
            data_formatter: UsageDataFormatter instance
            api_url: Optional API URL for uploading data (e.g., https://dashboard.example.com/api)
            api_key: Optional API key for authentication
            cluster_name: Optional cluster name for API uploads
        """
        self.data_fetcher = data_fetcher
        self.data_formatter = data_formatter
        self.api_url = api_url
        self.api_key = api_key
        self.cluster_name = cluster_name

    def upload_file_to_api(self, file_path: str) -> bool:
        """
        Upload a parquet file to the dashboard API.

        The cluster is automatically determined from the API key.

        Args:
            file_path: Path to the parquet file

        Returns:
            True if upload successful, False otherwise
        """
        if not self.api_url or not self.api_key:
            raise ValueError("API URL and API key are required for API uploads")

        try:
            import requests
        except ImportError:
            print("Error: 'requests' library is required for API uploads.")
            print("Install with: pip install requests")
            return False

        try:
            file_name = Path(file_path).name
            upload_url = f"{self.api_url.rstrip('/')}/agent/upload"

            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, "application/octet-stream")}
                headers = {"X-API-Key": self.api_key}

                response = requests.post(
                    upload_url,
                    files=files,
                    headers=headers,
                    timeout=60,
                )

                if response.status_code in (200, 201):
                    return True
                print(f"Upload failed: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"Error uploading file to API: {e}")
            return False

    def get_server_file_list(self) -> set:
        """Get list of files already uploaded to the server.

        The cluster is automatically determined from the API key.

        Returns:
            Set of filenames that exist on the server
        """
        if not self.api_url or not self.api_key:
            # API not configured, return empty set
            return set()

        try:
            list_url = f"{self.api_url.rstrip('/')}/agent/list-files"
            headers = {"X-API-Key": self.api_key}

            response = requests.get(list_url, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                print(f"✓ Server has {len(files)} files already uploaded")
                return set(files)
            print(f"Warning: Could not get server file list (HTTP {response.status_code})")
            return set()

        except Exception as e:
            print(f"Warning: Could not get server file list: {e}")
            return set()

    def fetch_data_weekly(
        self,
        from_year: int,
        from_week: int,
        until_year: int | None = None,
        until_week: int | None = None,
        output_dir: str = "slurmo_weekly_data",
        overwrite: bool = False,
        verbose: bool = False,
    ) -> list[str]:
        """
        Fetch data weekly and save to Parquet files.

        Args:
            from_year: Starting year
            from_week: Starting week
            until_year: Ending year (default: from_year)
            until_week: Ending week (default: from_week)
            output_dir: Directory to save Parquet files
            overwrite: Whether to overwrite existing files
            verbose: Whether to print verbose output

        Returns:
            List of paths to saved Parquet files
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Set until_year and until_week to from_year and from_week if not provided
        if until_year is None:
            until_year = from_year
        if until_week is None:
            until_week = from_week

        # Get list of files already on the server (if API is configured)
        server_files = self.get_server_file_list()

        current_year = from_year
        current_week = from_week
        data_files: list[str] = []

        # Use tqdm for progress bar
        pbar = tqdm(
            total=((until_year - from_year) * 52) + (until_week - from_week) + 1,
            desc="Fetching Weekly Data",
            unit="week",
        )

        while (current_year < until_year) or (
            current_year == until_year and current_week <= until_week
        ):
            try:
                # Check if the data file already exists (locally or on server)
                file_name = f"week_{current_year}_W{current_week:02.0f}.parquet"
                file_path = os.path.join(output_dir, file_name)

                # Skip if file exists locally or on server (unless overwrite is True)
                file_exists_locally = os.path.exists(file_path)
                file_exists_on_server = file_name in server_files

                if overwrite or (not file_exists_locally and not file_exists_on_server):
                    # Export usage data for the current week
                    weekly_data = self.data_fetcher.export_usage_data(
                        current_year,
                        current_week,
                        current_year,
                        current_week,
                        verbose=verbose,
                    )

                    # Format the usage data
                    formatted_data = self.data_formatter.format_usage_data(weekly_data)

                    # Save formatted data as Parquet file
                    formatted_data.to_parquet(file_path, index=False, engine="pyarrow")

                    # Upload to API if configured
                    if self.api_url and self.api_key and self.cluster_name:
                        upload_success = self.upload_file_to_api(file_path)
                        if upload_success:
                            print(f"  ✓ Uploaded {file_path} to dashboard API")
                        else:
                            print(f"  ✗ Failed to upload {file_path}")

                    delay = 5
                    time.sleep(delay)

                    # Append file path to list of saved files
                    data_files.append(file_path)
                else:
                    # File already exists - skip collection
                    if file_exists_on_server and not file_exists_locally:
                        print(f"  ⊙ Skipping {file_name} (already on server)")
                    elif file_exists_locally:
                        print(f"  ⊙ Skipping {file_name} (exists locally)")
                        data_files.append(file_path)

                # Update progress bar
                pbar.update(1)
            except Exception as e:
                msg = f"Error fetching data for week {current_year}-W{current_week:02.0f}: {e}"
                print(msg)

            # Move to the next week
            if current_week == 52:
                current_week = 1
                current_year += 1
            else:
                current_week += 1

        pbar.close()
        return data_files


def main() -> None:
    """Main entry point for the data fetcher."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Fetch and export SLURM usage data.")

    # Define mutually exclusive group for date selection
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument(
        "--weeks",
        type=int,
        help="Number of weeks to go back from today",
    )
    date_group.add_argument(
        "--from",
        dest="from_date",
        type=str,
        help="Starting date in ISO week format (e.g., 2025-W01)",
    )

    # Other arguments
    parser.add_argument(
        "--to",
        dest="to_date",
        type=str,
        help="Ending date in ISO week format (e.g., 2025-W52). Only valid with --from",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/hostname/data",
        help="Directory to save the Parquet files.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files if they are already present.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", default=False)

    # API upload arguments
    parser.add_argument(
        "--api-url",
        type=str,
        help="Dashboard API URL for uploading data (e.g., https://dashboard.example.com/api)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="API key for authentication with the dashboard",
    )

    # Legacy support for older interface
    parser.add_argument(
        "--from-year",
        type=int,
        help=argparse.SUPPRESS,  # Hide from help
    )
    parser.add_argument(
        "--from-week",
        type=int,
        help=argparse.SUPPRESS,  # Hide from help
    )
    parser.add_argument(
        "--until-year",
        type=int,
        help=argparse.SUPPRESS,  # Hide from help
    )
    parser.add_argument(
        "--until-week",
        type=int,
        help=argparse.SUPPRESS,  # Hide from help
    )

    args = parser.parse_args()

    # Handle the different date specification options
    if args.from_year is not None and args.from_week is not None:
        # Legacy mode
        from_year = args.from_year
        from_week = args.from_week
        until_year = args.until_year or from_year
        until_week = args.until_week or from_week
    else:
        # New mode
        from_year, from_week, until_year, until_week = calculate_date_range(
            weeks_back=args.weeks,
            from_date=args.from_date,
            to_date=args.to_date
        )

    # Validate API upload configuration
    if args.api_url or args.api_key:
        if not (args.api_url and args.api_key):
            parser.error(
                "For API uploads, both --api-url and --api-key are required"
            )

    # Extract cluster name from output directory path
    # E.g., /data/slurm-usage/DAIC -> DAIC
    cluster_name = Path(args.output_dir).name

    # Create instances of fetcher and formatter
    data_fetcher = UsageDataFetcher()
    data_formatter = UsageDataFormatter()

    # Create and run the data exporter
    exporter = DataExporter(
        data_fetcher,
        data_formatter,
        api_url=args.api_url,
        api_key=args.api_key,
        cluster_name=cluster_name,
    )
    exporter.fetch_data_weekly(
        from_year=from_year,
        from_week=from_week,
        until_year=until_year,
        until_week=until_week,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
