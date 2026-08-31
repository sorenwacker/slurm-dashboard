from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobRecord(BaseModel):
    """Model for a single job record."""

    JobID: str
    User: str
    Account: str
    Partition: str
    State: str
    QOS: str | None = None
    Submit: datetime
    Start: datetime | None = None
    End: datetime | None = None
    CPUHours: float = 0.0
    GPUHours: float = 0.0
    AllocCPUS: int = 0
    AllocGPUS: int = 0
    AllocNodes: int = 0
    NodeList: str | None = None
    ReqMemMB: float | None = None
    MaxRSSMB: float | None = None
    CPUUsedHours: float | None = None


class DataIngestionRequest(BaseModel):
    """Request model for data ingestion."""

    hostname: str = Field(..., description="Cluster hostname")
    jobs: list[JobRecord] = Field(..., description="List of job records")


class DataIngestionResponse(BaseModel):
    """Response model for data ingestion."""

    success: bool
    message: str
    jobs_processed: int
    hostname: str


class FilterRequest(BaseModel):
    """Request model for data filtering."""

    hostname: str
    start_date: str | None = None
    end_date: str | None = None
    partitions: list[str] | None = None
    accounts: list[str] | None = None
    users: list[str] | None = None
    qos: list[str] | None = None
    states: list[str] | None = None
    complete_periods_only: bool = False
    period_type: str = "month"
    color_by: str | None = None  # Group/color charts by: Account, Partition, State, QoS, User
    account_segments: int | None = None  # Number of segments to keep in account names (0 = all)
    normalize_node_usage: bool = False  # Normalize node CPU/GPU usage to 100% capacity
    # Note: hide_unused_nodes and sort_by_usage removed - now handled client-side


class MetadataResponse(BaseModel):
    """Response model for metadata."""

    hostnames: list[str]
    partitions: dict[str, list[str]]
    accounts: dict[str, list[str]]
    users: dict[str, list[str]]
    qos: dict[str, list[str]]
    states: dict[str, list[str]]
    date_ranges: dict[str, dict[str, str]]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    data_loaded: bool
    hostnames: list[str]
