"""Shared datastore singleton to ensure single initialization across all modules."""

import logging
import sys
from pathlib import Path

# Add parent directory to path to import the original datastore
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from slurm_usage_history.app.datastore import PandasDataStore
    from slurm_usage_history.app.duckdb_datastore import DuckDBDataStore
except ImportError:
    DuckDBDataStore = None  # type: ignore
    PandasDataStore = None  # type: ignore

from .core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global datastore instance
_datastore: DuckDBDataStore | None = None


def get_datastore():
    """Get or initialize the shared datastore singleton.

    Uses DuckDBDataStore by default for better performance and lower memory usage.
    Falls back to PandasDataStore if DuckDB is not available.
    """
    global _datastore
    if _datastore is None:
        logger.info("Initializing shared datastore singleton...")
        # Prefer DuckDBDataStore for better performance
        if DuckDBDataStore is not None:
            _datastore = DuckDBDataStore(directory=settings.data_path)
            _datastore.load_data()
            _datastore.start_auto_refresh(interval=settings.auto_refresh_interval)
            logger.info(f"Shared datastore initialized with hostnames: {_datastore.get_hostnames()}")
        elif PandasDataStore is not None:
            # Fallback to PandasDataStore if DuckDB not available
            _datastore = PandasDataStore(directory=settings.data_path)
            _datastore.load_data()
            _datastore.start_auto_refresh(interval=settings.auto_refresh_interval)
            logger.info(f"Shared datastore (Pandas) initialized with hostnames: {_datastore.get_hostnames()}")
        else:
            from fastapi import HTTPException

            raise HTTPException(status_code=500, detail="DataStore not available")
    return _datastore
