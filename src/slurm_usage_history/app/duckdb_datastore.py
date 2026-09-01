"""DuckDB-based DataStore for efficient querying of parquet files.

This implementation uses DuckDB to query parquet files directly without
loading all data into memory, providing much better performance and
scalability compared to the pandas-based approach.
"""

import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

try:
    import duckdb

    DUCKDB_AVAILABLE = True
except ImportError as e:
    DUCKDB_AVAILABLE = False
    duckdb = None  # type: ignore[assignment]
    logging.error(f"DuckDB not available: {e}. Install with: pip install duckdb")

import pandas as pd

from slurm_usage_history.memory import add_memory_columns

logger = logging.getLogger(__name__)


class Singleton(type):
    """Metaclass to implement the Singleton pattern."""

    _instances: ClassVar[dict[type, Any]] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
            return cls._instances[cls]


class DuckDBDataStore(metaclass=Singleton):
    """DataStore implementation using DuckDB for efficient parquet querying.

    Advantages over PandasDataStore:
    - Low memory usage (queries parquet directly, no loading into RAM)
    - Fast aggregations (DuckDB is optimized for analytics)
    - Handles large datasets efficiently
    - Can work with all historical data without memory constraints
    """

    def __init__(
        self,
        directory: str | Path | None = None,
        auto_refresh_interval: int = 600,
        account_formatter: Any | None = None,
    ):
        """Initialize the DuckDBDataStore.

        Args:
            directory: Path to the data directory
            auto_refresh_interval: Refresh interval in seconds
            account_formatter: Formatter for account names

        Raises:
            ImportError: If DuckDB is not installed
        """
        if not DUCKDB_AVAILABLE or duckdb is None:
            msg = "DuckDB is required but not installed. Install with: pip install duckdb or uv add duckdb"
            raise ImportError(msg)

        logger.info("Initializing DuckDBDataStore (low-memory mode)")
        self.directory = Path(directory).expanduser() if directory else Path.cwd()
        self.auto_refresh_interval = auto_refresh_interval
        self.account_formatter = account_formatter
        self._refresh_thread: threading.Thread | None = None
        self._stop_refresh_flag: threading.Event = threading.Event()
        self._file_timestamps: dict[str, dict[Path, float]] = {}

        # Metadata cache (lightweight)
        self.hosts: dict[str, dict[str, Any]] = {}

        # DuckDB connection (thread-local for thread safety)
        self._local = threading.local()

        self._initialize_hosts()

        # Import account formatter if not provided
        if account_formatter is None:
            try:
                from .account_formatter import formatter as default_formatter

                self.account_formatter = default_formatter
            except ImportError:
                self.account_formatter = None

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get a thread-local DuckDB connection.

        DuckDB connections are not thread-safe, so we maintain one per thread.
        """
        if not hasattr(self._local, "conn") or self._local.conn is None:
            # Create DuckDB extension directory in /tmp to avoid read-only filesystem issues
            # Use process ID to avoid conflicts between multiple workers
            extension_dir = f"/tmp/.duckdb-{os.getpid()}"
            os.makedirs(extension_dir, exist_ok=True)

            # Connect with explicit extension directory configuration
            self._local.conn = duckdb.connect(":memory:", config={"extension_directory": extension_dir})

            # Install and load parquet extension
            self._local.conn.execute("INSTALL parquet")
            self._local.conn.execute("LOAD parquet")
        return self._local.conn

    def _initialize_hosts(self) -> None:
        """Scan directory for hostnames and initialize metadata."""
        for entry in self.directory.iterdir():
            if entry.is_dir():
                self.hosts[entry.name] = {
                    "max_date": None,
                    "min_date": None,
                    "partitions": None,
                    "accounts": None,
                    "users": None,
                    "qos": None,
                    "states": None,
                    "parquet_files": [],
                }

    def get_hostnames(self) -> list[str]:
        """Retrieve the list of hostnames, filtered by active status."""
        try:
            # Read cluster database directly to check active status
            import json
            from pathlib import Path

            # Try multiple possible locations for clusters.json
            possible_paths = [
                Path("data/clusters.json"),
                Path("backend/data/clusters.json"),
                Path("/app/data/clusters.json"),
                Path("/app/backend/data/clusters.json"),
            ]

            cluster_data = None
            for db_path in possible_paths:
                if db_path.exists():
                    with open(db_path) as f:
                        cluster_data = json.load(f)
                    break

            if cluster_data and cluster_data.get("clusters"):
                active_clusters = {
                    cluster["name"]
                    for cluster in cluster_data.get("clusters", {}).values()
                    if cluster.get("active", True)
                }
                # Only filter if we have active clusters defined
                if active_clusters:
                    return [hostname for hostname in self.hosts if hostname in active_clusters]
        except Exception as e:
            logger.warning(f"Failed to filter by active clusters: {e}")

        # If cluster DB not available, return all hosts
        return list(self.hosts.keys())

    def load_data(self) -> None:
        """Load metadata for all hosts.

        Unlike PandasDataStore, this doesn't load actual data into memory.
        It only scans parquet files to extract metadata like date ranges
        and unique values for filters.
        """
        import time

        start_time = time.time()
        for hostname in self.get_hostnames():
            logger.info(f"Loading metadata for {hostname}...")
            host_start = time.time()
            self._load_host_metadata(hostname)
            host_elapsed = time.time() - host_start
            logger.info(f"Loaded metadata for {hostname} in {host_elapsed:.2f}s")

        total_elapsed = time.time() - start_time
        logger.info(f"Total metadata loading time: {total_elapsed:.2f}s for {len(self.get_hostnames())} hosts")

    def _load_host_metadata(self, hostname: str) -> None:
        """Load metadata for a specific hostname.

        Args:
            hostname: The hostname to load metadata for
        """
        # Try new structure first (data), then fallback to old structure (weekly-data)
        host_dir = self.directory / hostname / "data"
        if not host_dir.exists() or not host_dir.is_dir():
            host_dir = self.directory / hostname / "weekly-data"
            if not host_dir.exists() or not host_dir.is_dir():
                logger.warning(f"Directory not found for hostname: {hostname}")
                return

        parquet_files = list(host_dir.glob("*.parquet"))
        if not parquet_files:
            logger.warning(f"No Parquet files found in directory: {host_dir}")
            return

        # Store file paths for this host
        self.hosts[hostname]["parquet_files"] = parquet_files

        # Store file timestamps for change detection
        self._file_timestamps[hostname] = {}
        for file_path in parquet_files:
            self._file_timestamps[hostname][file_path] = file_path.stat().st_mtime

        # Build file list for DuckDB query
        file_pattern = str(host_dir / "*.parquet")

        # Get connection
        conn = self._get_connection()

        try:
            # Query metadata from parquet files (fast, only scans metadata)
            # Get date ranges
            result = conn.execute(
                f"""
                SELECT
                    MIN(Submit) as min_date,
                    MAX(Submit) as max_date
                FROM read_parquet('{file_pattern}', union_by_name=true)
                """
            ).fetchone()

            if result:
                min_date, max_date = result
                self.hosts[hostname]["min_date"] = min_date.strftime("%Y-%m-%d") if min_date else None
                self.hosts[hostname]["max_date"] = max_date.strftime("%Y-%m-%d") if max_date else None

            # Get unique values for filters (this might be slow for large datasets)
            # We'll query each column separately to avoid loading everything
            for col, key in [
                ("Partition", "partitions"),
                ("Account", "accounts"),
                ("User", "users"),
                ("QOS", "qos"),
                ("State", "states"),
            ]:
                try:
                    unique_values = conn.execute(
                        f"""
                        SELECT DISTINCT {col}
                        FROM read_parquet('{file_pattern}', union_by_name=true)
                        WHERE {col} IS NOT NULL
                        ORDER BY {col}
                        """
                    ).fetchall()

                    # Special handling for Partition: split comma-separated values
                    if col == "Partition":
                        partition_set = set()
                        for val in unique_values:
                            # Split by comma and strip whitespace
                            partitions = [p.strip() for p in val[0].split(",") if p.strip()]
                            partition_set.update(partitions)
                        self.hosts[hostname][key] = sorted(partition_set)
                    else:
                        self.hosts[hostname][key] = [val[0] for val in unique_values]
                except Exception as e:
                    logger.warning(f"Could not load unique values for {col}: {e}")
                    self.hosts[hostname][key] = []

            # Extract unique node names for auto-discovery
            try:
                # NodeList can be either an array or a string (depending on parquet file version)
                # Try to handle both cases
                try:
                    # Try as array first
                    node_names = conn.execute(
                        f"""
                        SELECT DISTINCT unnest(NodeList) as node
                        FROM read_parquet('{file_pattern}', union_by_name=true, hive_partitioning=false)
                        WHERE NodeList IS NOT NULL AND typeof(NodeList) = 'VARCHAR[]'
                        ORDER BY node
                        """
                    ).fetchall()
                    discovered_nodes = {val[0] for val in node_names if val[0]}
                except Exception:
                    # Fall back to string handling (some files may have VARCHAR instead of array)
                    discovered_nodes = set()

                # Also try to get nodes from string-type NodeList columns
                try:
                    node_names_str = conn.execute(
                        f"""
                        SELECT DISTINCT NodeList as node
                        FROM read_parquet('{file_pattern}', union_by_name=true, hive_partitioning=false)
                        WHERE NodeList IS NOT NULL AND typeof(NodeList) = 'VARCHAR'
                        ORDER BY node
                        """
                    ).fetchall()
                    discovered_nodes.update(val[0] for val in node_names_str if val[0])
                except Exception:
                    pass

                if discovered_nodes:
                    # Run auto-discovery to update cluster config
                    self._auto_discover_nodes(hostname, discovered_nodes)

            except Exception as e:
                logger.warning(f"Could not extract nodes for auto-discovery: {e}")

            logger.info(
                f"Successfully loaded metadata for {hostname}: "
                f"{len(parquet_files)} files, "
                f"date range {self.hosts[hostname]['min_date']} to {self.hosts[hostname]['max_date']}"
            )

        except Exception as e:
            logger.error(f"Error loading metadata for {hostname}: {e}")
            # Set defaults
            self.hosts[hostname]["min_date"] = None
            self.hosts[hostname]["max_date"] = None
            for key in ["partitions", "accounts", "users", "qos", "states"]:
                self.hosts[hostname][key] = []

    def _auto_discover_nodes(self, hostname: str, node_names: set[str]) -> None:
        """Auto-discover nodes from data and update cluster config.

        Args:
            hostname: Cluster/hostname
            node_names: Set of unique node names found in data
        """
        if not node_names:
            return

        try:
            # Import node discovery service from backend
            # This is in the backend app, so we need to check if it's available
            import sys
            from pathlib import Path

            # Try to import from backend
            backend_path = Path(__file__).parent.parent.parent / "backend"
            if backend_path.exists() and str(backend_path) not in sys.path:
                sys.path.insert(0, str(backend_path))

            from app.services.node_discovery import get_node_discovery_service

            discovery_service = get_node_discovery_service()
            added_count = discovery_service.discover_and_update_nodes(hostname, node_names)

            if added_count > 0:
                logger.info(f"Auto-discovery: Added {added_count} new nodes to {hostname} cluster config")

        except ImportError as e:
            # Node discovery service not available (e.g., running from legacy code location)
            logger.debug(f"Node auto-discovery not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to run node auto-discovery: {e}")

    def get_min_max_dates(self, hostname: str) -> tuple[str | None, str | None]:
        """Get minimum and maximum dates for the specified hostname."""
        return self.hosts[hostname]["min_date"], self.hosts[hostname]["max_date"]

    def get_partitions(self, hostname: str) -> list[str]:
        """Get available partitions for the specified hostname."""
        return self.hosts[hostname]["partitions"] or []

    def get_accounts(self, hostname: str) -> list[str]:
        """Get available accounts for the specified hostname."""
        return self.hosts[hostname]["accounts"] or []

    def get_users(self, hostname: str) -> list[str]:
        """Get available users for the specified hostname."""
        return self.hosts[hostname]["users"] or []

    def get_qos(self, hostname: str) -> list[str]:
        """Get available QOS options for the specified hostname."""
        return self.hosts[hostname]["qos"] or []

    def get_states(self, hostname: str) -> list[str]:
        """Get available states for the specified hostname."""
        return self.hosts[hostname]["states"] or []

    def get_filter_values_for_period(
        self,
        hostname: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, list[str]]:
        """Get unique filter values for a specific time period.

        This ensures filter dropdowns only show values that exist in the
        selected date range, preventing empty graphs.

        Args:
            hostname: The hostname to query
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)

        Returns:
            Dictionary with lists of unique values for each filter dimension
        """
        host_dir = self.directory / hostname / "data"
        file_pattern = str(host_dir / "*.parquet")

        # Build WHERE clause for date filtering
        where_clauses = []
        if start_date:
            where_clauses.append(f"Submit >= '{start_date}'")
        if end_date:
            # Make end_date inclusive by adding 1 day and using < comparison
            end_date_exclusive = (pd.to_datetime(end_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            where_clauses.append(f"Submit < '{end_date_exclusive}'")
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        conn = self._get_connection()

        result: dict[str, list[Any]] = {
            "partitions": [],
            "accounts": [],
            "users": [],
            "qos": [],
            "states": [],
        }

        # Query unique values for each dimension within the date range
        for col, key in [
            ("Partition", "partitions"),
            ("Account", "accounts"),
            ("User", "users"),
            ("QOS", "qos"),
            ("State", "states"),
        ]:
            try:
                unique_values = conn.execute(
                    f"""
                    SELECT DISTINCT {col}
                    FROM read_parquet('{file_pattern}', union_by_name=true)
                    WHERE {where_sql} AND {col} IS NOT NULL
                    ORDER BY {col}
                    """
                ).fetchall()

                # Special handling for Partition: split comma-separated values
                if col == "Partition":
                    partition_set = set()
                    for val in unique_values:
                        # Split by comma and strip whitespace
                        partitions = [p.strip() for p in val[0].split(",") if p.strip()]
                        partition_set.update(partitions)
                    result[key] = sorted(partition_set)
                else:
                    result[key] = [val[0] for val in unique_values]
            except Exception as e:
                logger.warning(f"Could not load unique values for {col} in period: {e}")
                result[key] = []

        return result

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
        complete_periods_only: bool = False,  # noqa: ARG002  (interface compatibility with PandasDataStore)
        period_type: str = "month",  # noqa: ARG002  (interface compatibility with PandasDataStore)
        format_accounts: bool = True,
        account_segments: int | None = None,  # noqa: ARG002  (interface compatibility with PandasDataStore)
        time_base: str = "submit",
        columns: list[str] | None = None,
    ) -> pd.DataFrame:
        """Filter data using DuckDB and return as pandas DataFrame.

        This method builds a SQL query to filter the parquet files directly,
        only loading the filtered results into memory.

        Args:
            hostname: The hostname to query
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            partitions: List of partitions to include
            accounts: List of accounts to include
            users: List of users to include
            qos: List of QOS values to include
            states: List of states to include
            complete_periods_only: Not used in DuckDB implementation (kept for compatibility)
            period_type: Not used in DuckDB implementation (kept for compatibility)
            format_accounts: Whether to format account names
            account_segments: Number of segments for account formatting
            time_base: "submit" selects jobs submitted in the range; "overlap" selects jobs whose
                runtime overlaps the range (used for node utilization)
            columns: Read only these columns (intersected with what the files contain);
                None reads everything

        Returns:
            Filtered DataFrame
        """
        host_dir = self.directory / hostname / "data"
        file_pattern = str(host_dir / "*.parquet")

        # Build WHERE clause
        where_clauses = []

        end_date_exclusive = None
        if end_date:
            # Make end_date inclusive by adding 1 day and using < comparison
            end_date_exclusive = (pd.to_datetime(end_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        if time_base == "overlap":
            if start_date:
                where_clauses.append(f'("End" IS NULL OR "End" >= \'{start_date}\')')
            if end_date_exclusive:
                where_clauses.append(f"Start < '{end_date_exclusive}'")
        else:
            if start_date:
                where_clauses.append(f"Submit >= '{start_date}'")
            if end_date_exclusive:
                where_clauses.append(f"Submit < '{end_date_exclusive}'")
        if partitions:
            # Handle comma-separated partitions: match if any selected partition appears in the list
            partition_conditions = []
            for partition in partitions:
                # Match if partition appears as whole word in comma-separated list
                # Using list_contains with string_split for accurate matching
                partition_conditions.append(f"list_contains(string_split(Partition, ','), '{partition}')")
            where_clauses.append(f"({' OR '.join(partition_conditions)})")
        if accounts:
            account_list = "', '".join(accounts)
            where_clauses.append(f"Account IN ('{account_list}')")
        if users:
            user_list = "', '".join(users)
            where_clauses.append(f"User IN ('{user_list}')")
        if qos:
            qos_values = "', '".join(qos)
            where_clauses.append(f"QOS IN ('{qos_values}')")
        if states:
            state_list = "', '".join(states)
            where_clauses.append(f"State IN ('{state_list}')")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Build and execute query. Column names vary across file generations, so a
        # requested projection is intersected with what the files actually contain
        # and the variants are normalized in pandas afterwards.
        import time

        query_start = time.time()

        conn = self._get_connection()
        select_sql = "*"
        if columns:
            available = {
                row[0]
                for row in conn.execute(
                    f"DESCRIBE SELECT * FROM read_parquet('{file_pattern}', union_by_name=true, binary_as_string=true)"
                ).fetchall()
            }
            selected = [c for c in columns if c in available]
            if selected:
                select_sql = ", ".join(f'"{c}"' for c in selected)
        query = f"""
        SELECT {select_sql}
        FROM read_parquet('{file_pattern}', union_by_name=true, binary_as_string=true)
        WHERE {where_sql}
        """

        df = conn.execute(query).df()

        query_elapsed = time.time() - query_start
        logger.debug(f"DuckDB query completed in {query_elapsed:.3f}s, returned {len(df)} rows")

        # Handle column name variations due to union_by_name
        # Some parquet files use "CPU-hours" while others use "CPUHours"
        if "CPU-hours" in df.columns and "CPUHours" in df.columns:
            # Merge the columns, preferring non-NaN values
            df["CPUHours"] = df["CPUHours"].fillna(df["CPU-hours"])
            df = df.drop(columns=["CPU-hours"])
        elif "CPU-hours" in df.columns:
            df = df.rename(columns={"CPU-hours": "CPUHours"})

        if "GPU-hours" in df.columns and "GPUHours" in df.columns:
            df["GPUHours"] = df["GPUHours"].fillna(df["GPU-hours"])
            df = df.drop(columns=["GPU-hours"])
        elif "GPU-hours" in df.columns:
            df = df.rename(columns={"GPU-hours": "GPUHours"})

        # Normalize column names and create derived columns
        # Handle both old and new parquet file formats

        # Timing columns
        if "WaitingTimeHours" not in df.columns:
            if "WaitingTime [h]" in df.columns:
                df = df.rename(columns={"WaitingTime [h]": "WaitingTimeHours"})
            elif "WaitingTime" in df.columns:
                df = df.rename(columns={"WaitingTime": "WaitingTimeHours"})
            elif "Submit" in df.columns and "Start" in df.columns:
                df["WaitingTimeHours"] = (
                    pd.to_datetime(df["Start"]) - pd.to_datetime(df["Submit"])
                ).dt.total_seconds() / 3600.0

        if "ElapsedHours" not in df.columns:
            if "Elapsed [h]" in df.columns:
                df = df.rename(columns={"Elapsed [h]": "ElapsedHours"})
            elif "Start" in df.columns and "End" in df.columns:
                df["ElapsedHours"] = (
                    pd.to_datetime(df["End"]) - pd.to_datetime(df["Start"])
                ).dt.total_seconds() / 3600.0

        df = add_memory_columns(df)

        # Resource allocation columns
        if "Nodes" not in df.columns and "AllocNodes" in df.columns:
            df = df.rename(columns={"AllocNodes": "Nodes"})
        if "CPUs" not in df.columns and "AllocCPUS" in df.columns:
            df = df.rename(columns={"AllocCPUS": "CPUs"})
        if "GPUs" not in df.columns and "AllocGPUS" in df.columns:
            df = df.rename(columns={"AllocGPUS": "GPUs"})

        # Start time period columns (for trend charts)
        if "Start" in df.columns:
            if "StartYearMonth" not in df.columns:
                df["StartYearMonth"] = pd.to_datetime(df["Start"]).dt.to_period("M").apply(lambda r: r.start_time)
            if "StartYearWeek" not in df.columns:
                df["StartYearWeek"] = pd.to_datetime(df["Start"]).dt.to_period("W").apply(lambda r: r.start_time)
            if "StartYear" not in df.columns:
                df["StartYear"] = pd.to_datetime(df["Start"]).dt.year

        # Apply account formatting if requested and available
        if format_accounts and self.account_formatter and "Account" in df.columns:
            df["Account"] = df["Account"].apply(self.account_formatter.format_account)

        total_elapsed = time.time() - query_start
        if total_elapsed > 1.0:
            logger.info(f"Filter query took {total_elapsed:.3f}s for {len(df)} rows from {hostname}")

        return df

    def start_auto_refresh(self, interval: int | None = None) -> None:
        """Start the background thread for automatic data refresh."""
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
            target=self._auto_refresh_worker, daemon=True, name="DuckDBDataStore-AutoRefresh"
        )
        self._refresh_thread.start()
        logger.info(f"Started auto-refresh thread (every {self.auto_refresh_interval} seconds)")

    def stop_auto_refresh(self) -> None:
        """Stop the background thread for automatic data refresh."""
        if self._refresh_thread is None or not self._refresh_thread.is_alive():
            logger.info("No auto-refresh thread is running")
            return

        logger.info("Stopping auto-refresh thread...")
        self._stop_refresh_flag.set()
        self._refresh_thread.join(timeout=5.0)
        if self._refresh_thread.is_alive():
            logger.warning("Warning: Auto-refresh thread did not terminate gracefully")
        else:
            logger.info("Auto-refresh thread stopped successfully")

    def _auto_refresh_worker(self) -> None:
        """Worker method for the auto-refresh thread."""
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

    def check_for_updates(self) -> bool:
        """Check all hosts for new or changed files and reload metadata if necessary."""
        updated = False

        for hostname in self.get_hostnames():
            host_updates = self._check_host_updates(hostname)
            if host_updates:
                logger.info(f"Updates detected for host {hostname}, reloading metadata...")
                try:
                    self._load_host_metadata(hostname)
                    updated = True
                except Exception as e:
                    logger.error(f"Error reloading metadata for {hostname}: {e!s}")

        return updated

    def _check_host_updates(self, hostname: str) -> bool:
        """Check if files for a specific host have been updated or new files added."""
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
            return True

        # Deleted files
        deleted_files = set(old_timestamps.keys()) - set(current_files.keys())
        if deleted_files:
            return True

        # Modified files
        for file_path, timestamp in current_files.items():
            if file_path in old_timestamps and timestamp != old_timestamps[file_path]:
                return True

        return False
