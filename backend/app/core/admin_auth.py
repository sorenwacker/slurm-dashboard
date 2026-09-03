"""Admin authentication and authorization."""

import logging
import secrets
from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# JWT token security
security = HTTPBearer()

# Value older example files shipped; treated as unset so it can never sign a token
PLACEHOLDER_SECRET_KEY = "change-this-to-a-random-secret-key-in-production"


def resolve_signing_key(configured: str | None) -> str:
    """The configured ADMIN_SECRET_KEY, or a random per-process key when it is unset or the placeholder."""
    if configured and configured != PLACEHOLDER_SECRET_KEY:
        return configured
    logger.warning("ADMIN_SECRET_KEY is not set; using a random key, so admin sessions end when the server restarts")
    return secrets.token_urlsafe(48)


# JWT Configuration
SECRET_KEY = resolve_signing_key(settings.admin_secret_key)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verify JWT token and return username."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not isinstance(username, str) or not is_configured_admin(username):
            raise credentials_exception
        return username
    except jwt.PyJWTError as e:
        raise credentials_exception from e


def is_configured_admin(subject: str) -> bool:
    """Whether a token subject names a password admin or an admin email."""
    return subject in settings.get_admin_users() or settings.is_admin_email(subject)


def authenticate_admin(username: str, password: str) -> str | None:
    """Authenticate admin user and return username if valid."""
    # Get admin credentials from settings
    admin_users = settings.get_admin_users()

    if username not in admin_users:
        return None

    stored_hash = admin_users[username]
    if not verify_password(password, stored_hash):
        return None

    return username


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)


async def get_current_admin(username: str = Depends(verify_token)) -> str:
    """Dependency to get current authenticated admin."""
    return username
