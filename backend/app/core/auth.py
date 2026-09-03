from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from ..db.clusters import get_cluster_db
from .config import get_settings

settings = get_settings()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Cluster name returned for keys from the legacy API_KEYS setting, which are not bound to a cluster
LEGACY_KEY_CLUSTER = "unknown"


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key from request header.

    Checks both cluster database and legacy API keys from .env.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        The cluster name associated with the API key

    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
        )

    # Check cluster database first
    db = get_cluster_db()
    cluster_name = db.verify_api_key(api_key)

    if cluster_name:
        return cluster_name

    # Fallback to legacy API keys from .env for backward compatibility
    legacy_api_keys = settings.get_api_keys()
    if api_key in legacy_api_keys:
        return LEGACY_KEY_CLUSTER

    # No valid key found
    if not legacy_api_keys and not db.has_active_api_keys():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No API keys configured on server",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )
