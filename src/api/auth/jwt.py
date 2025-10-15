"""JWT-based authentication for API endpoints.

This module provides JWT token generation and validation for securing API endpoints.
Authentication can be disabled via settings.api_auth_enabled for testing.
"""

from datetime import datetime, timedelta

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings

logger = structlog.get_logger(__name__)

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security
security = HTTPBearer(auto_error=False)  # auto_error=False allows optional auth
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT access token.

    Args:
        data: Payload data to encode (must include "sub" for subject)
        expires_delta: Token expiration time (default: 30 minutes)

    Returns:
        Encoded JWT token

    Example:
        >>> token = create_access_token({"sub": "admin"})
        >>> # Returns: "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
    """
    to_encode = data.copy()

    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    # Encode token
    try:
        # Get secret key from settings
        secret_key = settings.api_secret_key.get_secret_value()
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)

        logger.debug(
            "Access token created",
            subject=data.get("sub"),
            expires_at=expire.isoformat(),
        )

        return encoded_jwt

    except Exception as e:
        logger.error("Failed to create access token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create access token",
        ) from e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str | None:
    """Validate JWT token and extract user.

    This dependency can be used to protect endpoints with authentication.
    If settings.api_auth_enabled is False, authentication is skipped.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        Username from token or None if auth is disabled

    Raises:
        HTTPException: If token is invalid or missing (when auth is enabled)

    Example:
        >>> @router.get("/protected")
        >>> async def protected_endpoint(user: str = Depends(get_current_user)):
        >>>     return {"user": user}
    """
    # Skip authentication if disabled in settings
    if not settings.api_auth_enabled:
        logger.debug("Authentication disabled - allowing request")
        return None

    # Check if credentials were provided
    if credentials is None:
        logger.warning("Missing authentication credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # Decode and validate token
        secret_key = settings.api_secret_key.get_secret_value()
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])

        # Extract username
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token missing subject claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.debug("Authentication successful", user=username)
        return username

    except JWTError as e:
        logger.warning("Invalid JWT token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error",
        ) from e


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash.

    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password

    Returns:
        True if password matches hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hashed password
    """
    return pwd_context.hash(password)
