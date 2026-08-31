"""Admin API endpoints for cluster and API key management."""

import logging
from datetime import timedelta
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..config import default_cluster_config_path
from ..core.admin_auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_admin,
    create_access_token,
    get_current_admin,
)
from ..core.config import get_settings
from ..db.clusters import get_cluster_db
from ..models.admin_models import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminRole,
    APIKeyRotateRequest,
    APIKeyRotateResponse,
    ClusterCreate,
    ClusterListResponse,
    ClusterResponse,
    ClusterUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def find_existing_data_directory(cluster_name: str) -> str | None:
    """Check if a data directory exists for this cluster (case-insensitive).

    Returns the actual directory name if found, None otherwise.
    """
    settings = get_settings()
    data_path = Path(settings.data_path)

    if not data_path.exists():
        return None

    # Check for exact match first
    exact_match = data_path / cluster_name
    if exact_match.exists() and exact_match.is_dir():
        return cluster_name

    # Check for case-insensitive match
    cluster_lower = cluster_name.lower()
    for item in data_path.iterdir():
        if item.is_dir() and item.name.lower() == cluster_lower:
            return item.name

    return None


def ensure_cluster_yaml_config(cluster_name: str, description: str | None = None,
                                contact_email: str | None = None, location: str | None = None) -> None:
    """Ensure cluster has configuration in clusters.yaml.

    Creates a default configuration if it doesn't exist.

    Args:
        cluster_name: Name of the cluster
        description: Optional description
        contact_email: Optional contact email
        location: Optional location
    """
    config_file = default_cluster_config_path()
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new
    if config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {"clusters": {}, "settings": {}}

    # Ensure structure exists
    if "clusters" not in config:
        config["clusters"] = {}
    if "settings" not in config:
        config["settings"] = {}

    # Check if cluster already exists
    if cluster_name in config["clusters"]:
        logger.info(f"Cluster {cluster_name} already exists in YAML config")
        return

    # Create default configuration
    config["clusters"][cluster_name] = {
        "display_name": cluster_name,
        "description": description or f"{cluster_name} Cluster",
        "metadata": {
            "location": location or "Unknown",
            "contact": contact_email or "admin@example.com"
        },
        "node_labels": {},
        "account_labels": {},
        "partition_labels": {}
    }

    # Ensure default settings exist
    if not config["settings"]:
        config["settings"] = {
            "default_node_type": "cpu",
            "case_sensitive": False,
            "auto_generate_labels": True
        }

    # Write back to file
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)

    logger.info(f"Created YAML configuration for cluster: {cluster_name}")


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(request: AdminLoginRequest):
    """Admin login endpoint.

    Authenticates admin user and returns JWT token.
    """
    username = authenticate_admin(request.username, request.password)

    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )

    # For password-based auth, default to superadmin role
    return AdminLoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=AdminRole.SUPERADMIN,
        email=None,
    )


@router.get("/saml-token", response_model=AdminLoginResponse)
async def get_admin_token_from_saml(request: Request):
    """Get admin token for SAML-authenticated users.

    Checks if the user is authenticated via SAML and has admin privileges,
    then issues an admin JWT token.

    Note: This endpoint uses cookie-based SAML authentication, not Bearer token.
    """
    from ..core.saml_auth import get_current_user_saml

    try:
        # Get user data from SAML session cookie using the existing dependency
        session_token = request.cookies.get("session_token")
        user_data = await get_current_user_saml(session_token=session_token)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated via SAML",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract email from SAML attributes (similar to /saml/me endpoint)
    settings = get_settings()
    email = None
    if user_data.get("attributes"):
        email_attrs = user_data["attributes"].get("email") or \
                     user_data["attributes"].get("mail") or \
                     user_data["attributes"].get("emailAddress")
        if email_attrs and isinstance(email_attrs, list) and len(email_attrs) > 0:
            email = email_attrs[0]

    # Check if user is admin
    is_admin = False
    if email:
        is_admin = settings.is_admin_email(email)

    # If not found by email, check if username (netid) matches any admin email prefix
    if not is_admin and user_data.get("username"):
        username = user_data.get("username")
        full_email = f"{username}@tudelft.nl"
        is_admin = settings.is_admin_email(full_email)
        if is_admin and not email:
            email = full_email

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have admin privileges",
        )

    # Create admin token
    username = user_data.get("username") or email or "saml_user"
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )

    return AdminLoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=AdminRole.SUPERADMIN,
        email=email,
    )


@router.get("/clusters", response_model=ClusterListResponse)
async def list_clusters(admin: str = Depends(get_current_admin)):
    """List all clusters.

    Requires admin authentication.
    """
    db = get_cluster_db()
    clusters = db.get_all_clusters()

    cluster_responses = [
        ClusterResponse(
            id=c["id"],
            name=c["name"],
            description=c.get("description"),
            contact_email=c.get("contact_email"),
            location=c.get("location"),
            api_key_prefix=c.get("api_key_prefix", ""),
            api_key_created=c["api_key_created"],
            active=c["active"],
            created_at=c["created_at"],
            updated_at=c["updated_at"],
            last_submission=c.get("last_submission"),
            total_jobs_submitted=c.get("total_jobs_submitted", 0),
            deploy_key_created=c.get("deploy_key_created"),
            deploy_key_expires_at=c.get("deploy_key_expires_at"),
            deploy_key_used=c.get("deploy_key_used"),
            deploy_key_used_at=c.get("deploy_key_used_at"),
            deploy_key_used_from_ip=c.get("deploy_key_used_from_ip"),
        )
        for c in clusters
    ]

    return ClusterListResponse(clusters=cluster_responses, total=len(cluster_responses))


@router.post("/clusters", response_model=ClusterResponse, status_code=status.HTTP_201_CREATED)
async def create_cluster(
    request: ClusterCreate,
    admin: str = Depends(get_current_admin),
):
    """Create a new cluster and generate API key.

    If a data directory already exists for this cluster (case-insensitive match),
    the cluster name will automatically match the existing directory's case.

    Requires admin authentication.
    """
    db = get_cluster_db()

    # Check for existing data directory and match its case
    existing_dir = find_existing_data_directory(request.name)
    cluster_name = existing_dir if existing_dir else request.name

    # Warn if case was changed
    if existing_dir and existing_dir != request.name:
        # Log the case correction
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Cluster name corrected from '{request.name}' to '{existing_dir}' "
            f"to match existing data directory"
        )

    if db.get_cluster_by_name(cluster_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cluster with name '{cluster_name}' already exists",
        )

    # Write the YAML entry first: if the config file is not writable the
    # request fails before any record exists, instead of leaving a cluster
    # with an API key but no configuration.
    try:
        ensure_cluster_yaml_config(
            cluster_name=cluster_name,
            description=request.description,
            contact_email=request.contact_email,
            location=request.location,
        )
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot write cluster configuration: {e}",
        ) from e

    try:
        cluster = db.create_cluster(
            name=cluster_name,
            description=request.description,
            contact_email=request.contact_email,
            location=request.location,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ClusterResponse(
        id=cluster["id"],
        name=cluster["name"],
        description=cluster.get("description"),
        contact_email=cluster.get("contact_email"),
        location=cluster.get("location"),
        api_key=cluster.get("api_key"),
        api_key_prefix=cluster.get("api_key_prefix", ""),
        api_key_created=cluster["api_key_created"],
        active=cluster["active"],
        created_at=cluster["created_at"],
        updated_at=cluster["updated_at"],
        last_submission=None,
        total_jobs_submitted=0,
        deploy_key_created=cluster.get("deploy_key_created"),
        deploy_key_expires_at=cluster.get("deploy_key_expires_at"),
        deploy_key_used=cluster.get("deploy_key_used"),
        deploy_key_used_at=cluster.get("deploy_key_used_at"),
        deploy_key_used_from_ip=cluster.get("deploy_key_used_from_ip"),
    )


@router.get("/clusters/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(
    cluster_id: str,
    admin: str = Depends(get_current_admin),
):
    """Get cluster details by ID.

    Requires admin authentication.
    """
    db = get_cluster_db()
    cluster = db.get_cluster(cluster_id)

    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found",
        )

    return ClusterResponse(
        id=cluster["id"],
        name=cluster["name"],
        description=cluster.get("description"),
        contact_email=cluster.get("contact_email"),
        location=cluster.get("location"),
        api_key=cluster.get("api_key"),
        api_key_prefix=cluster.get("api_key_prefix", ""),
        api_key_created=cluster["api_key_created"],
        active=cluster["active"],
        created_at=cluster["created_at"],
        updated_at=cluster["updated_at"],
        last_submission=cluster.get("last_submission"),
        total_jobs_submitted=cluster.get("total_jobs_submitted", 0),
        deploy_key_created=cluster.get("deploy_key_created"),
        deploy_key_expires_at=cluster.get("deploy_key_expires_at"),
        deploy_key_used=cluster.get("deploy_key_used"),
        deploy_key_used_at=cluster.get("deploy_key_used_at"),
        deploy_key_used_from_ip=cluster.get("deploy_key_used_from_ip"),
    )


@router.patch("/clusters/{cluster_id}", response_model=ClusterResponse)
async def update_cluster(
    cluster_id: str,
    request: ClusterUpdate,
    admin: str = Depends(get_current_admin),
):
    """Update cluster information.

    Requires admin authentication.
    """
    db = get_cluster_db()

    cluster = db.update_cluster(
        cluster_id=cluster_id,
        description=request.description,
        contact_email=request.contact_email,
        location=request.location,
        active=request.active,
    )

    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found",
        )

    return ClusterResponse(
        id=cluster["id"],
        name=cluster["name"],
        description=cluster.get("description"),
        contact_email=cluster.get("contact_email"),
        location=cluster.get("location"),
        api_key=cluster.get("api_key"),
        api_key_prefix=cluster.get("api_key_prefix", ""),
        api_key_created=cluster["api_key_created"],
        active=cluster["active"],
        created_at=cluster["created_at"],
        updated_at=cluster["updated_at"],
        last_submission=cluster.get("last_submission"),
        total_jobs_submitted=cluster.get("total_jobs_submitted", 0),
        deploy_key_created=cluster.get("deploy_key_created"),
        deploy_key_expires_at=cluster.get("deploy_key_expires_at"),
        deploy_key_used=cluster.get("deploy_key_used"),
        deploy_key_used_at=cluster.get("deploy_key_used_at"),
        deploy_key_used_from_ip=cluster.get("deploy_key_used_from_ip"),
    )


@router.delete("/clusters/{cluster_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cluster(
    cluster_id: str,
    admin: str = Depends(get_current_admin),
):
    """Delete a cluster.

    Requires admin authentication.
    """
    db = get_cluster_db()

    success = db.delete_cluster(cluster_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found",
        )

    return


@router.post("/clusters/rotate-key", response_model=APIKeyRotateResponse)
async def rotate_api_key(
    request: APIKeyRotateRequest,
    admin: str = Depends(get_current_admin),
):
    """Rotate API key for a cluster.

    Generates a new API key and invalidates the old one.
    Requires admin authentication.
    """
    db = get_cluster_db()

    new_key = db.rotate_api_key(request.cluster_id)

    if not new_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found",
        )

    return APIKeyRotateResponse(
        cluster_id=request.cluster_id,
        new_api_key=new_key,
        message="API key rotated successfully. Update cluster configuration with new key.",
    )


@router.get("/admin-emails")
async def get_admin_emails(admin: str = Depends(get_current_admin)):
    """Get current admin and superadmin email lists.

    Reads from database first, falls back to environment variables.
    Requires admin authentication.
    """
    import json
    from pathlib import Path

    admin_emails = []
    superadmin_emails = []

    # Try reading from database first
    db_path = Path("data/clusters.json")
    if db_path.exists():
        try:
            with open(db_path) as f:
                data = json.load(f)
            if "admin_users" in data:
                admin_emails = data["admin_users"].get("admin_emails", [])
                superadmin_emails = data["admin_users"].get("superadmin_emails", [])
        except Exception:
            pass  # Fall back to environment variables

    # Fall back to environment variables if database doesn't have them
    if not admin_emails and not superadmin_emails:
        settings = get_settings()
        if settings.admin_emails:
            admin_emails = [email.strip() for email in settings.admin_emails.split(",") if email.strip()]
        if settings.superadmin_emails:
            superadmin_emails = [email.strip() for email in settings.superadmin_emails.split(",") if email.strip()]

    return {
        "admin_emails": admin_emails,
        "superadmin_emails": superadmin_emails,
    }


@router.post("/clusters/{cluster_id}/deploy-key")
async def generate_deploy_key(cluster_id: str, admin: str = Depends(get_current_admin)):
    """Generate a one-time deployment key for a cluster.

    The deploy key can be used once to fetch the actual API key.
    Expires after 7 days.
    Requires admin authentication.
    """
    cluster_db = get_cluster_db()

    deploy_key = cluster_db.generate_deploy_key(cluster_id, expires_days=7)

    if not deploy_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found",
        )

    logger.info(f"Deploy key generated for cluster {cluster_id} by {admin}")

    return {
        "status": "success",
        "deploy_key": deploy_key,
        "message": "Deploy key generated. This key expires in 7 days and can only be used once.",
    }


@router.get("/clusters/{cluster_id}/deploy-key-status")
async def get_deploy_key_status(cluster_id: str, admin: str = Depends(get_current_admin)):
    """Get the status of the deploy key for a cluster.

    Returns information about whether the key was used, when, from what IP, and expiration.
    Requires admin authentication.
    """
    cluster_db = get_cluster_db()
    cluster = cluster_db.get_cluster(cluster_id)

    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found",
        )

    from datetime import datetime

    deploy_key_exists = cluster.get("deploy_key") is not None
    deploy_key_used = cluster.get("deploy_key_used", False)
    deploy_key_created = cluster.get("deploy_key_created")
    deploy_key_used_at = cluster.get("deploy_key_used_at")
    deploy_key_used_from_ip = cluster.get("deploy_key_used_from_ip")
    deploy_key_expires_at = cluster.get("deploy_key_expires_at")

    # Check if expired
    is_expired = False
    if deploy_key_expires_at:
        expires_dt = datetime.fromisoformat(deploy_key_expires_at)
        is_expired = datetime.utcnow() > expires_dt

    # Determine validity
    is_valid = deploy_key_exists and not deploy_key_used and not is_expired

    return {
        "cluster_id": cluster_id,
        "cluster_name": cluster["name"],
        "deploy_key_exists": deploy_key_exists,
        "deploy_key_used": deploy_key_used,
        "deploy_key_created": deploy_key_created,
        "deploy_key_expires_at": deploy_key_expires_at,
        "deploy_key_used_at": deploy_key_used_at,
        "deploy_key_used_from_ip": deploy_key_used_from_ip,
        "is_expired": is_expired,
        "is_valid": is_valid,
    }


@router.post("/admin-emails")
async def update_admin_emails(
    admin_emails: list[str],
    superadmin_emails: list[str],
    admin: str = Depends(get_current_admin),
):
    """Update admin and superadmin email lists.

    Stores admin emails in the database.
    Requires admin authentication.
    """
    import json
    from pathlib import Path

    # Use cluster database file for admin emails
    db_path = Path("data/clusters.json")
    if not db_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database file not found",
        )

    # Read current database
    try:
        with open(db_path) as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read database: {e!s}",
        )

    # Ensure admin_users section exists
    if "admin_users" not in data:
        data["admin_users"] = {}

    # Update admin emails
    data["admin_users"]["admin_emails"] = admin_emails
    data["admin_users"]["superadmin_emails"] = superadmin_emails

    # Write back to database
    try:
        with open(db_path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write database: {e!s}",
        )

    logger.info(f"Admin emails updated by {admin}: {len(admin_emails)} admins, {len(superadmin_emails)} superadmins")

    return {
        "status": "success",
        "message": "Admin emails updated successfully",
        "admin_emails": admin_emails,
        "superadmin_emails": superadmin_emails,
    }
