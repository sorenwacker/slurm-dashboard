"""Models for admin functionality - cluster and API key management."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class AdminRole(str, Enum):
    """Admin role levels."""

    ADMIN = "admin"  # Can ONLY access user data (color by user, analytics, exports)
    SUPERADMIN = "superadmin"  # Full access: cluster management + user data


class ClusterCreate(BaseModel):
    """Request model for creating a new cluster."""

    name: str = Field(..., description="Cluster name/hostname", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Cluster description")
    contact_email: Optional[str] = Field(None, description="Admin contact email")
    location: Optional[str] = Field(None, description="Physical location")


class ClusterUpdate(BaseModel):
    """Request model for updating a cluster."""

    description: Optional[str] = None
    contact_email: Optional[str] = None
    location: Optional[str] = None
    active: Optional[bool] = None


class ClusterResponse(BaseModel):
    """Response model for cluster information."""

    id: str
    name: str
    description: Optional[str]
    contact_email: Optional[str]
    location: Optional[str]
    api_key: str
    api_key_created: datetime
    active: bool
    created_at: datetime
    updated_at: datetime
    last_submission: Optional[datetime] = None
    total_jobs_submitted: int = 0

    # Deploy key fields
    deploy_key_created: Optional[datetime] = None
    deploy_key_expires_at: Optional[datetime] = None
    deploy_key_used: Optional[bool] = None
    deploy_key_used_at: Optional[datetime] = None
    deploy_key_used_from_ip: Optional[str] = None


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
    email: Optional[str] = None


class AdminUser(BaseModel):
    """Admin user model with role."""

    username: str
    email: EmailStr
    role: AdminRole
    full_name: Optional[str] = None
    is_active: bool = True


class ClusterIdentityUpdate(BaseModel):
    """Hand-maintained identity fields of a cluster entry in clusters.yaml."""

    display_name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    owner: Optional[str] = None
    contact: Optional[str] = None
    url: Optional[str] = None


class NodeLabelUpdate(BaseModel):
    """Hand-maintained fields of a node entry; hardware comes from the agent and is not editable."""

    synonyms: Optional[list[str]] = None
    description: Optional[str] = None
    type: Optional[str] = Field(default=None, pattern="^(cpu|gpu|login|storage)$")


class PartitionLabelUpdate(BaseModel):
    """Hand-maintained fields of a partition entry."""

    display_name: Optional[str] = None
    description: Optional[str] = None


class AccountLabelUpdate(BaseModel):
    """Hand-maintained fields of an account entry."""

    display_name: Optional[str] = None
    short_name: Optional[str] = None
    faculty: Optional[str] = None
    department: Optional[str] = None
