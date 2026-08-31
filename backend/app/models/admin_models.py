"""Models for admin functionality - cluster and API key management."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class AdminRole(str, Enum):
    """Admin role levels."""

    ADMIN = "admin"  # Can ONLY access user data (color by user, analytics, exports)
    SUPERADMIN = "superadmin"  # Full access: cluster management + user data


class ClusterCreate(BaseModel):
    """Request model for creating a new cluster."""

    name: str = Field(..., description="Cluster name/hostname", min_length=1, max_length=100)
    description: str | None = Field(None, description="Cluster description")
    contact_email: str | None = Field(None, description="Admin contact email")
    location: str | None = Field(None, description="Physical location")


class ClusterUpdate(BaseModel):
    """Request model for updating a cluster."""

    description: str | None = None
    contact_email: str | None = None
    location: str | None = None
    active: bool | None = None


class ClusterResponse(BaseModel):
    """Response model for cluster information."""

    id: str
    name: str
    description: str | None
    contact_email: str | None
    location: str | None
    api_key: str | None = None  # full key, only in the response that issued it
    api_key_prefix: str = ""
    api_key_created: datetime
    active: bool
    created_at: datetime
    updated_at: datetime
    last_submission: datetime | None = None
    total_jobs_submitted: int = 0

    # Deploy key fields
    deploy_key_created: datetime | None = None
    deploy_key_expires_at: datetime | None = None
    deploy_key_used: bool | None = None
    deploy_key_used_at: datetime | None = None
    deploy_key_used_from_ip: str | None = None


class ClusterListResponse(BaseModel):
    """Response model for list of clusters."""

    clusters: list[ClusterResponse]
    total: int


class APIKeyRotateRequest(BaseModel):
    """Request model for rotating an API key."""

    cluster_id: str = Field(..., description="Cluster ID")


class APIKeyRotateResponse(BaseModel):
    """Response model for API key rotation."""

    cluster_id: str
    new_api_key: str
    message: str


class AdminLoginRequest(BaseModel):
    """Request model for admin login."""

    username: str
    password: str


class AdminLoginResponse(BaseModel):
    """Response model for admin login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: AdminRole
    email: str | None = None


class AdminUser(BaseModel):
    """Admin user model with role."""

    username: str
    email: EmailStr
    role: AdminRole
    full_name: str | None = None
    is_active: bool = True


class ClusterIdentityUpdate(BaseModel):
    """Hand-maintained identity fields of a cluster entry in clusters.yaml."""

    display_name: str | None = None
    description: str | None = None
    location: str | None = None
    owner: str | None = None
    contact: str | None = None
    url: str | None = None


class NodeLabelUpdate(BaseModel):
    """Hand-maintained fields of a node entry; hardware comes from the agent and is not editable."""

    synonyms: list[str] | None = None
    description: str | None = None
    type: str | None = Field(default=None, pattern="^(cpu|gpu|login|storage)$")


class PartitionLabelUpdate(BaseModel):
    """Hand-maintained fields of a partition entry."""

    display_name: str | None = None
    description: str | None = None


class AccountLabelUpdate(BaseModel):
    """Hand-maintained fields of an account entry."""

    display_name: str | None = None
    short_name: str | None = None
    faculty: str | None = None
    department: str | None = None
