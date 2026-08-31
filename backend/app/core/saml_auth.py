"""SAML authentication module for SSO."""

import json
import os
from pathlib import Path

from fastapi import Cookie, HTTPException, Request, status
from onelogin.saml2.auth import OneLogin_Saml2_Auth

from .config import get_settings

settings = get_settings()


def load_saml_settings() -> dict:
    """Load SAML settings from configuration file.

    Returns:
        Dictionary containing SAML settings

    Raises:
        FileNotFoundError: If settings file doesn't exist
        JSONDecodeError: If settings file is invalid
    """
    saml_settings_path = os.getenv("SAML_SETTINGS_PATH", "saml/settings.json")

    if not os.path.exists(saml_settings_path):
        raise FileNotFoundError(f"SAML settings file not found: {saml_settings_path}")

    with open(saml_settings_path) as f:
        saml_settings = json.load(f)

    # Load certificates from files
    cert_path = Path(saml_settings_path).parent / "certs"
    sp_cert_file = cert_path / "sp.crt"
    sp_key_file = cert_path / "sp.key"

    if sp_cert_file.exists():
        with open(sp_cert_file) as f:
            saml_settings["sp"]["x509cert"] = f.read()

    if sp_key_file.exists():
        with open(sp_key_file) as f:
            saml_settings["sp"]["privateKey"] = f.read()

    return saml_settings


def init_saml_auth(request: Request) -> OneLogin_Saml2_Auth:
    """Initialize SAML auth object from request.

    Args:
        request: FastAPI request object

    Returns:
        Configured SAML auth object
    """
    # Prepare request data in format expected by python3-saml
    request_data = {
        "https": "on" if request.url.scheme == "https" else "off",
        "http_host": request.url.hostname,
        "server_port": request.url.port or (443 if request.url.scheme == "https" else 80),
        "script_name": request.url.path,
        "get_data": dict(request.query_params),
        "post_data": {},
    }

    saml_settings = load_saml_settings()
    return OneLogin_Saml2_Auth(request_data, saml_settings)


def is_saml_enabled() -> bool:
    """Check if SAML authentication is enabled.

    Returns:
        True if SAML is enabled, False otherwise
    """
    return os.getenv("ENABLE_SAML", "false").lower() == "true"


async def get_current_user_saml(session_token: str | None = Cookie(None, alias="session_token")) -> dict:
    """Get current user from SAML session token.

    Args:
        session_token: JWT session token from cookie

    Returns:
        User information dictionary

    Raises:
        HTTPException: If user is not authenticated
    """
    if not is_saml_enabled():
        # SAML is disabled, allow access
        return {"username": "anonymous", "attributes": {}}

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify JWT token
    import jwt

    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Secret key not configured",
        )

    try:
        payload = jwt.decode(session_token, secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_session_token(user_data: dict, expiry_hours: int = 24) -> str:
    """Create JWT session token for user.

    Args:
        user_data: User information to encode
        expiry_hours: Token expiry time in hours

    Returns:
        JWT token string
    """
    from datetime import datetime, timedelta

    import jwt

    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise ValueError("Secret key not configured")

    payload = {
        **user_data,
        "exp": datetime.utcnow() + timedelta(hours=expiry_hours),
        "iat": datetime.utcnow(),
    }

    return jwt.encode(payload, secret_key, algorithm="HS256")
