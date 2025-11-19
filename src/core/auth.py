"""Authentication models and utilities for JWT-based auth.

Sprint Context: Sprint 22 (2025-11-11) - Feature 22.2: API Security Hardening
Task: 22.2.4 - Standardize Authentication Across All Endpoints

This module provides JWT token models, creation, and validation utilities
for consistent authentication across all protected endpoints.

Security Features:
    - JWT tokens with configurable expiration (default: 60 minutes)
    - HS256 algorithm for token signing
    - Role-based access control (user, admin, superadmin)
    - Token expiration validation

Usage:
    >>> from src.core.auth import create_access_token, decode_access_token
    >>> token = create_access_token("user123", "john_doe", "user")
    >>> print(token.access_token)
    >>> token_data = decode_access_token(token.access_token)
    >>> print(token_data.username)

Notes:
    - JWT_SECRET_KEY must be set in environment variables (min 32 chars for production)
    - Tokens are stateless (no server-side session storage)
    - Token validation happens on every request via get_current_user dependency

See Also:
    - src/api/dependencies.py: FastAPI dependencies for authentication
    - src/api/v1/auth.py: Login endpoint implementation
"""

from datetime import UTC, datetime, timedelta

import structlog
from fastapi import HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel

from src.core.config import settings

logger = structlog.get_logger(__name__)

# JWT Configuration
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60


class TokenData(BaseModel):
    """JWT token payload.

    This model defines the data structure stored in JWT tokens.

    Attributes:
        user_id: Unique user identifier
        username: Username for display/logging
        role: User role (user, admin, superadmin)
        exp: Token expiration timestamp (automatically set)

    Example:
        >>> token_data = TokenData(
        ...     user_id="user_001",
        ...     username="john_doe",
        ...     role="user",
        ...     exp=datetime.now(timezone.utc) + timedelta(hours=1)
        ... )
    """

    user_id: str
    username: str
    role: str = "user"  # user, admin, superadmin
    exp: datetime


class User(BaseModel):
    """User model for authenticated requests.

    This model represents an authenticated user in the system.
    It's returned by get_current_user dependency and used throughout
    protected endpoints.

    Attributes:
        user_id: Unique user identifier
        username: Username for display/logging
        role: User role (user, admin, superadmin)
        email: Optional email address

    Methods:
        is_admin: Check if user has admin privileges

    Example:
        >>> user = User(user_id="user_001", username="john_doe", role="admin")
        >>> user.is_admin()
        True
    """

    user_id: str
    username: str
    role: str
    email: str | None = None

    def is_admin(self) -> bool:
        """Check if user has admin privileges.

        Returns:
            True if user has admin or superadmin role, False otherwise

        Example:
            >>> admin = User(user_id="1", username="admin", role="admin")
            >>> admin.is_admin()
            True
            >>> user = User(user_id="2", username="user", role="user")
            >>> user.is_admin()
            False
        """
        return self.role in ["admin", "superadmin"]  # type: ignore[no-any-return]


class Token(BaseModel):
    """JWT token response.

    This model is returned from the login endpoint after successful
    authentication.

    Attributes:
        access_token: JWT access token string
        token_type: Token type (always "bearer")
        expires_in: Token lifetime in seconds

    Example:
        >>> token = Token(
        ...     access_token="eyJhbGc...",
        ...     token_type="bearer",
        ...     expires_in=3600
        ... )
        >>> print(f"Token expires in {token.expires_in} seconds")
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds


def create_access_token(user_id: str, username: str, role: str = "user") -> Token:
    """Generate JWT access token.

    Creates a signed JWT token with user information and expiration.
    The token is signed using the JWT_SECRET_KEY from settings.

    Args:
        user_id: Unique user identifier
        username: Username for display/logging
        role: User role (default: "user")

    Returns:
        Token object with access_token, token_type, and expires_in

    Raises:
        HTTPException: If token creation fails (500 Internal Server Error)

    Example:
        >>> token = create_access_token("user_001", "john_doe", "user")
        >>> print(token.access_token)
        'eyJhbGciOiJIUzI1NiIsInR5cCI6...'
        >>> print(token.expires_in)
        3600

    Security Notes:
        - JWT_SECRET_KEY must be strong (min 32 chars) in production
        - Tokens are stateless - cannot be revoked without additional infrastructure
        - Token expiration is hardcoded to JWT_EXPIRATION_MINUTES
    """
    expires = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRATION_MINUTES)

    # Create payload with Unix timestamp for expiration
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": expires,  # python-jose will convert datetime to timestamp
    }

    try:
        # Get secret key from settings
        secret_key = settings.api_secret_key.get_secret_value()

        # Encode token
        encoded_jwt = jwt.encode(
            payload,
            secret_key,
            algorithm=JWT_ALGORITHM,
        )

        logger.debug(
            "access_token_created",
            user_id=user_id,
            username=username,
            role=role,
            expires_at=expires.isoformat(),
        )

        return Token(
            access_token=encoded_jwt,
            token_type="bearer",
            expires_in=JWT_EXPIRATION_MINUTES * 60,
        )

    except Exception as e:
        logger.error("token_creation_failed", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create access token",
        ) from e


def decode_access_token(token: str) -> TokenData:
    """Decode and validate JWT token.

    Validates the JWT signature and expiration, then returns the token payload.

    Args:
        token: JWT token string

    Returns:
        TokenData object with user_id, username, role, and exp

    Raises:
        HTTPException: If token is expired (401 Unauthorized)
        HTTPException: If token is invalid or malformed (401 Unauthorized)

    Example:
        >>> token = "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
        >>> token_data = decode_access_token(token)
        >>> print(token_data.username)
        'john_doe'

    Security Notes:
        - Token signature is validated using JWT_SECRET_KEY
        - Expiration is checked automatically by PyJWT
        - Invalid tokens raise 401 Unauthorized
    """
    try:
        secret_key = settings.api_secret_key.get_secret_value()

        # Decode and validate token
        payload = jwt.decode(token, secret_key, algorithms=[JWT_ALGORITHM])

        # Parse payload into TokenData
        token_data = TokenData(**payload)

        logger.debug("token_decoded", user_id=token_data.user_id, username=token_data.username)

        return token_data

    except JWTError as e:
        # Handle both ExpiredSignatureError and other JWT errors
        error_type = type(e).__name__
        if "expired" in error_type.lower() or "expired" in str(e).lower():
            logger.warning("token_expired", token_preview=token[:20] + "...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
        else:
            logger.warning("token_invalid", error=str(e), token_preview=token[:20] + "...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
    except Exception as e:
        logger.error("token_decode_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
