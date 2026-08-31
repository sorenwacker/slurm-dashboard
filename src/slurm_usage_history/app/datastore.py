import logging
import threading
import time
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from .account_formatter import formatter
except ImportError:
    formatter = None
from ..tools import timeit

logger = logging.getLogger(__name__)


class Singleton(type):
    """Metaclass to implement the Singleton pattern.

    Ensures only one instance of a class exists.
    """

    _instances: dict[type, Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """Override the call method to implement singleton behavior.

        Args:
            *args: Variable positional arguments to pass to the class constructor.
            **kwargs: Variable keyword arguments to pass to the class constructor.

        Returns:
            The singleton instance of the class.
        """
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
            return cls._instances[cls]


class PandasDataStore(metaclass=Singleton):
    """DataStore implementation using Pandas with enhanced filtering capabilities.

    Implemented as a Singleton to ensure only one instance exists throughout
    the application lifecycle.
    """

    def __init__(
        self,
        directory: str | Path | None = None,
        auto_refresh_interval: int = 600,
        account_formatter: Any | None = None,
    ):
        """Initialize the PandasDataStore.

        Args:
            directory: Path to the data directory. Defaults to current working directory if None.
            auto_refresh_interval: Refresh interval in seconds. Defaults to 600 seconds (10 minutes).
            account_formatter: Formatter for account names. Defaults to None.
        """
        self.directory = Path(directory).expanduser() if directory else Path.cwd()
        self.hosts: dict[str, dict[str, Any]] = {}
        self.auto_refresh_interval = auto_refresh_interval
        self._refresh_thread: threading.Thread | None = None
        self._stop_refresh_flag: threading.Event = threading.Event()
        self._file_timestamps: dict[str, dict[Path, float]] = {}

        # Import the account formatter if not provided
        if account_formatter is None:
            try:
                from .account_formatter import formatter as default_formatter

                self.account_formatter = default_formatter
            except ImportError:
                self.account_formatter = None
        else:
            self.account_formatter = account_formatter

        self._initialize_hosts()

    def _initialize_hosts(self) -> None:
        """Populate the hosts dictionary with subdirectories.

        Scans the specified directory for subdirectories and initializes
        data structures for each detected host.
        """
        for entry in self.directory.iterdir():
            if entry.is_dir():
                self.hosts[entry.name] = {
                    "max_date": None,
                    "min_date": None,
                    "data": None,
                    "partitions": None,
                    "accounts": None,
                    "users": None,
                    "qos": None,
                    "states": None,
                }

    def get_hostnames(self) -> list[str]:
        """Retrieve the list of hostnames.

        Returns:
            List of available host names found in the data directory.
        """
        return list(self.hosts.keys())

    def get_min_max_dates(self, hostname: str) -> tuple[str | None, str | None]:
        """Get minimum and maximum dates for the specified hostname.

        Args:
            hostname: The cluster hostname.

        Returns:
            A tuple containing (min_date, max_date) for the specified hostname.
        """
        min_date = self.hosts[hostname]["min_date"]
        max_date = self.hosts[hostname]["max_date"]
        return min_date, max_date

    def get_partitions(self, hostname: str) -> list[str]:
        """Get available partitions for the specified hostname.

        Args:
            hostname: The cluster hostname.

        Returns:
            List of available partitions for the specified hostname.
        """
        return self.hosts[hostname]["partitions"] or []

    def get_accounts(self, hostname: str) -> list[str]:
        """Get available accounts for the specified hostname.

        Args:
            hostname: The cluster hostname.

        Returns:
            List of available accounts for the specified hostname.
        """
        return self.hosts[hostname]["accounts"] or []

    def get_users(self, hostname: str) -> list[str]:
        """Get available users for the specified hostname.

        Args:
            hostname: The cluster hostname.

        Returns:
            List of available users for the specified hostname.
        """
        return self.hosts[hostname]["users"] or []

    def get_qos(self, hostname: str) -> list[str]:
        """Get available QOS options for the specified hostname.

        Args:
            hostname: The cluster hostname.

        Returns:
            List of available QOS options for the specified hostname.
        """
        return self.hosts[hostname]["qos"] or []

    def get_states(self, hostname: str) -> list[str]:
        """Get available states for the specified hostname.

        Args:
            hostname: The cluster hostname.

        Returns:
            List of available states for the specified hostname.
        """
        return self.hosts[hostname]["states"] or []

    def start_auto_refresh(self, interval: int | None = None) -> None:
        """Start the background thread for automatic data refresh.

        Args:
            interval: Optional refresh interval in seconds. If provided, overrides
                     the interval set during initialization.

        Raises:
            ValueError: If the provided interval is not a positive integer.
        """
        if interval is not None:
            if not isinstance(interval, int) or interval <= 0:
                msg = "Refresh interval must be a positive integer"
                raise ValueError(msg)
            self.auto_refresh_interval = interval

        if self._refresh_thread is not None and self._refresh_thread.is_alive():
            logger.info("Auto-refresh is already running")
            return

        self._stop_refresh_flag.clear()
        self._refresh_thread = threading.Thread(
            target=self._auto_refresh_worker, daemon=True, name="DataStore-AutoRefresh"
        )
        self._refresh_thread.start()
        logger.info(f"Started auto-refresh thread (every {self.auto_refresh_interval} seconds)")

    def stop_auto_refresh(self) -> None:
        """Stop the background thread for automatic data refresh.

        Signals the auto-refresh thread to stop and waits for its termination.
        """
        if self._refresh_thread is None or not self._refresh_thread.is_alive():
            logger.info("No auto-refresh thread is running")
            return

        logger.info("Stopping auto-refresh thread...")
        self._stop_refresh_flag.set()
        self._refresh_thread.join(timeout=5.0)
        if self._refresh_thread.is_alive():
            logger.warning("Auto-refresh thread did not terminate gracefully")
        else:
            logger.info("Auto-refresh thread stopped successfully")

    def _auto_refresh_worker(self) -> None:
        """Worker method for the auto-refresh thread.

        Periodically checks for updates in the data and reloads if necessary.
        Runs in a background thread until signaled to stop.
        """
        while not self._stop_refresh_flag.is_set():
            try:
                updated = self.check_for_updates()
                if updated:
                    logger.info(f"Auto-refresh: Data was updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    logger.debug(f"Auto-refresh: No updates found at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception as e:
                logger.error(f"Error during auto-refresh: {e!s}")

            # Sleep for the specified interval, but check periodically if we should stop
            check_interval = 2
            for _ in range(self.auto_refresh_interval // check_interval):
                if self._stop_refresh_flag.is_set():
                    break
                time.sleep(check_interval)

    def set_refresh_interval(self, interval: int) -> bool:
        """Change the auto-refresh interval.

        Args:
            interval: New refresh interval in seconds.

        Returns:
            True if the interval was updated and auto-refresh is running,
            False if auto-refresh is not running.

        Raises:
            ValueError: If the interval is not a positive integer.
        """
        if not isinstance(interval, int) or interval <= 0:
            msg = "Refresh interval must be a positive integer"
            raise ValueError(msg)

        self.auto_refresh_interval = interval
        logger.info(f"Auto-refresh interval set to {interval} seconds")

        # Return status based on whether auto-refresh is running
        return self._refresh_thread is not None and self._refresh_thread.is_alive()

    @timeit
    def load_data(self) -> None:
        """Load all data files into the hosts dictionary.

        Iterates through all hostnames and loads their respective data.
        Performance is measured using the timeit decorator.
        """
        for hostname in self.get_hostnames():
            logger.info(f"Loading data for {hostname}...")
            self._load_host_data(hostname)

    def _load_host_data(self, hostname: str) -> None:
        """Load data for a specific hostname and update metadata.

        Args:
            hostname: The hostname to load data for.

        Processes the raw data, applies transformations, and updates metadata
        for the specified hostname.
        """
        raw_data = self._load_raw_data(hostname)
        transformed_data = self._transform_data(raw_data)
        self.hosts[hostname]["data"] = transformed_data

        # Store metadata
        self.hosts[hostname]["min_date"] = raw_data["Submit"].dt.date.min().isoformat()
        self.hosts[hostname]["max_date"] = raw_data["Submit"].dt.date.max().isoformat()

        # Store unique values for filtering
        for col, key in [
            ("Partition", "partitions"),
            ("Account", "accounts"),
            ("User", "users"),
            ("QOS", "qos"),
            ("State", "states"),
        ]:
            if col in transformed_data.columns:
                self.hosts[hostname][key] = transformed_data[col].sort_values().unique().tolist()
            else:
                self.hosts[hostname][key] = []

        # Store file timestamps for future change detection
        host_dir = self.directory / hostname / "data"
        self._file_timestamps[hostname] = {}
        for file_path in host_dir.glob("*.parquet"):
            self._file_timestamps[hostname][file_path] = file_path.stat().st_mtime

    def _load_raw_data(self, hostname: str) -> pd.DataFrame:
        """Load all Parquet files in the directory for a specific hostname.

        Args:
            hostname: The hostname to load data for.

        Returns:
            DataFrame containing the concatenated data from all Parquet files.

        Raises:
            FileNotFoundError: If the directory or Parquet files are not found.
        """
        host_dir = self.directory / hostname / "data"
        if not host_dir.exists() or not host_dir.is_dir():
            msg = f"Directory not found for hostname: {hostname}"
            raise FileNotFoundError(msg)

        parquet_files = list(host_dir.glob("*.parquet"))
        if not parquet_files:
            msg = f"No Parquet files found in directory: {host_dir}"
            raise FileNotFoundError(msg)

        return pd.concat([pd.read_parquet(file) for file in parquet_files], ignore_index=True)

    @timeit
    def _transform_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """Apply necessary transformations to the raw data.

        Args:
            raw_data: The raw DataFrame to transform.

        Returns:
            Transformed DataFrame with standardized formats.

        Handles column renaming and data type conversions if needed.
        The major time-based columns (SubmitYearMonth, SubmitYearWeek, etc.)
        are already present in the data.
        """
        # Standardize column names - rename columns with hyphens/brackets to camelCase
        column_renames = {
            "CPU-hours": "CPUHours",
            "GPU-hours": "GPUHours",
            "CPUs": "AllocCPUS",
            "GPUs": "AllocGPUS",
            "Elapsed [h]": "ElapsedHours",
            "WaitingTime [h]": "WaitingTimeHours",
        }

        for old_name, new_name in column_renames.items():
            if old_name in raw_data.columns and new_name not in raw_data.columns:
                raw_data = raw_data.rename(columns={old_name: new_name})
                logging.info(f"Renamed column '{old_name}' to '{new_name}'")

        # Ensure column existence and data types
        if "Partition" not in raw_data.columns and "Partitions" in raw_data.columns:
            raw_data["Partition"] = raw_data["Partitions"]

        # Handle multiple partitions per job (if stored as a list or string)
        if "Partition" in raw_data.columns and raw_data["Partition"].dtype == "object":
            raw_data["Partition"] = raw_data["Partition"].apply(
                lambda x: x.split(",")[0].strip() if isinstance(x, str) else x
            )

        # Extract SubmitYear for period filtering if not present
        # This is needed for the get_complete_periods method
        if "Submit" in raw_data.columns and "SubmitYear" not in raw_data.columns:
            raw_data["SubmitYear"] = raw_data["Submit"].dt.year

        # Add StartDay if not present
        if "StartDay" not in raw_data.columns and "Start" in raw_data.columns:
            raw_data["StartDay"] = raw_data["Start"].dt.normalize()
            logging.info("Added StartDay column")

        # Add SubmitDay if not present
        if "SubmitDay" not in raw_data.columns and "Submit" in raw_data.columns:
            raw_data["SubmitDay"] = raw_data["Submit"].dt.normalize()
            logging.info("Added SubmitDay column")

        return raw_data

    def check_for_updates(self) -> bool:
        """Check all hosts for new or changed files and reload if necessary.

        Returns:
            True if any host was updated, False otherwise.
        """
        updated = False

        for hostname in self.get_hostnames():
            host_updates = self._check_host_updates(hostname)
            if host_updates:
                logger.info(f"Updates detected for host {hostname}, reloading data...")
                try:
                    self._load_host_data(hostname)
                    updated = True
                    # Clear the cache since data has changed
                    self._filter_data.cache_clear()
                except Exception as e:
                    logger.error(f"Error reloading data for {hostname}: {e!s}")

        return updated

    def _check_host_updates(self, hostname: str) -> bool:
        """Check if files for a specific host have been updated or new files added.

        Args:
            hostname: The hostname to check for updates.

        Returns:
            True if there are updates, False otherwise.
        """
        host_dir = self.directory / hostname / "data"
        if not host_dir.exists() or not host_dir.is_dir():
            return False

        # Get current files and their timestamps
        current_files = {}
        for file_path in host_dir.glob("*.parquet"):
            current_files[file_path] = file_path.stat().st_mtime

        # If this is our first check for this hostname, store timestamps and return
        if hostname not in self._file_timestamps:
            self._file_timestamps[hostname] = current_files
            return False

        # Check for changes or new files
        old_timestamps = self._file_timestamps[hostname]

        # New files
        new_files = set(current_files.keys()) - set(old_timestamps.keys())
        if new_files:
            logger.info(f"New files found for {hostname}: {len(new_files)} files")
            return True

        # Changed files (timestamp differs)
        changed_files = []
        for file_path, current_time in current_files.items():
            if file_path in old_timestamps and current_time != old_timestamps[file_path]:
                changed_files.append(file_path)

        if changed_files:
            logger.info(f"Changed files found for {hostname}: {len(changed_files)} files")
            return True

        # No changes detected
        return False

    @lru_cache(maxsize=10)
    def _filter_data(
        self,
        hostname: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        partitions: frozenset[str] | None = None,
        accounts: frozenset[str] | None = None,
        users: frozenset[str] | None = None,
        qos: frozenset[str] | None = None,
        states: frozenset[str] | None = None,
    ) -> pd.DataFrame:
        """Filter data based on multiple criteria.

        Args:
            hostname: The cluster hostname.
            start_date: Start date filter (inclusive).
            end_date: End date filter (inclusive - includes entire day).
            partitions: Set of partitions to include.
            accounts: Set of accounts to include.
            users: Set of users to include.
            qos: Set of QOS values to include.
            states: Set of job states to include.

        Returns:
            Filtered DataFrame.

        Uses caching to improve performance for repeated similar queries.
        """
        df_filtered = self.hosts[hostname]["data"]

        if start_date:
            start_date = pd.to_datetime(start_date)
            df_filtered = df_filtered[df_filtered["Submit"] >= start_date]

        if end_date:
            # Make end_date inclusive of the entire day by adding 1 day and using < comparison
            end_date = pd.to_datetime(end_date) + pd.Timedelta(days=1)
            df_filtered = df_filtered[df_filtered["Submit"] < end_date]

        if partitions and "Partition" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Partition"].isin(partitions)]

        if accounts and "Account" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Account"].isin(accounts)]

        if users and "User" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["User"].isin(users)]

        if qos and "QOS" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["QOS"].isin(qos)]

        if states and "State" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["State"].isin(states)]

        return df_filtered

    def get_complete_periods(self, hostname: str, period_type: str = "month") -> list[str]:
        """Get list of complete time periods available in the data.

        Args:
            hostname: The cluster hostname.
            period_type: Type of period ('day', 'week', 'month', 'year').

        Returns:
            List of complete periods.
        """
        if hostname not in self.hosts or self.hosts[hostname]["data"] is None:
            return []

        df = self.hosts[hostname]["data"]
        now = pd.Timestamp.now()

        if period_type == "month":
            # Get year-month periods
            current_year_month = now.strftime("%Y-%m")

            # All periods except current (incomplete) month
            periods = sorted(df["SubmitYearMonth"].unique().tolist())
            if current_year_month in periods:
                periods.remove(current_year_month)

            return periods

        if period_type == "week":
            # Get week start dates
            # Calculate current week's start date
            current_week_start = now - pd.to_timedelta(now.dayofweek, unit="D")
            current_week_start_str = current_week_start.strftime("%Y-%m-%d")

            # All periods except current (incomplete) week
            periods = sorted(df["SubmitYearWeek"].unique().tolist())
            if current_week_start_str in periods:
                periods.remove(current_week_start_str)

            return periods

        if period_type == "year":
            # Get years
            current_year = now.year

            # All years except current (incomplete) year
            years = sorted(df["SubmitYear"].unique().tolist())
            if current_year in years:
                years.remove(current_year)

            return [str(year) for year in years]

        return []

    def filter(
        self,
        hostname: str,
        start_date: str | None = None,
        end_date: str | None = None,
        partitions: list[str] | None = None,
        accounts: list[str] | None = None,
        users: list[str] | None = None,
        qos: list[str] | None = None,
        states: list[str] | None = None,
        complete_periods_only: bool = False,
        period_type: str = "month",
        format_accounts: bool = True,
        account_segments: int | None = None,
    ) -> pd.DataFrame:
        """Public method to filter data with enhanced options.

        Args:
            hostname: The cluster hostname.
            start_date: Start date filter.
            end_date: End date filter.
            partitions: List of partitions to include.
            accounts: List of accounts to include.
            users: List of users to include.
            qos: List of QOS values to include.
            states: List of job states to include.
            complete_periods_only: Whether to include only complete time periods.
            period_type: Type of period when using complete_periods_only ('day', 'week', 'month', 'year').
            format_accounts: Whether to apply account name formatting.
            account_segments: Number of segments to keep.

        Returns:
            Filtered DataFrame.
        """
        if not hostname or hostname not in self.hosts or self.hosts[hostname]["data"] is None:
            # Return empty DataFrame if no data is available
            return pd.DataFrame()

        # Start with basic filtering
        df_filtered = self._filter_data(
            hostname=hostname,
            start_date=start_date if start_date else self.hosts[hostname]["min_date"],
            end_date=end_date if end_date else self.hosts[hostname]["max_date"],
            partitions=frozenset(partitions) if partitions else None,
            accounts=frozenset(accounts) if accounts else None,
            users=frozenset(users) if users else None,
            qos=frozenset(qos) if qos else None,
            states=frozenset(states) if states else None,
        )

        # Apply complete periods filter if requested
        if complete_periods_only and not df_filtered.empty:
            now = pd.Timestamp.now()

            if period_type == "month":
                # Exclude current month
                current_year_month = now.strftime("%Y-%m")
                df_filtered = df_filtered[df_filtered["SubmitYearMonth"] != current_year_month]

            elif period_type == "week":
                # Exclude current week based on SubmitYearWeek
                current_week_start = now - pd.to_timedelta(now.dayofweek, unit="D")
                current_week_start_str = current_week_start.strftime("%Y-%m-%d")
                df_filtered = df_filtered[df_filtered["SubmitYearWeek"] != current_week_start_str]

            elif period_type == "year":
                # Exclude current year
                current_year = now.year
                df_filtered = df_filtered[df_filtered["SubmitYear"] != current_year]

        # Apply account formatting if requested
        if format_accounts and "Account" in df_filtered.columns and not df_filtered.empty:
            # Create a copy to avoid modifying the cached data
            df_filtered = df_filtered.copy()

            if self.account_formatter:
                try:
                    if account_segments is not None:
                        # Temporarily store the current setting
                        original_segments = self.account_formatter.max_segments

                        # Apply custom segments just for this filter operation
                        self.account_formatter.max_segments = account_segments
                        df_filtered["Account"] = df_filtered["Account"].apply(self.account_formatter.format_account)

                        # Restore original setting
                        self.account_formatter.max_segments = original_segments
                    else:
                        # Use current global setting
                        df_filtered["Account"] = df_filtered["Account"].apply(self.account_formatter.format_account)
                except Exception as e:
                    logger.warning(f"Error applying account formatting: {e}. Using original account names.")

        return df_filtered


def get_datastore(
    directory: str | Path | None = None, auto_refresh_interval: int = 600, account_formatter: Any | None = formatter
) -> PandasDataStore:
    """Get the singleton instance of PandasDataStore.

    Args:
        directory: Path to the data directory (only used if this is the first call).
        auto_refresh_interval: Refresh interval in seconds (only used if this is the first call).
        account_formatter: Formatter for account names. Defaults to the imported formatter.

    Returns:
        The singleton instance of PandasDataStore.
    """
    return PandasDataStore(directory, auto_refresh_interval, account_formatter)
