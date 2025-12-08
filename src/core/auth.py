"""Authentication models and utilities for JWT-based auth.

Sprint Context: Sprint 38 (2025-12-08) - Feature 38.1a: JWT Authentication Backend

This module provides JWT token models, creation, and validation utilities
for consistent authentication across all protected endpoints.

Security Features:
    - JWT access tokens with configurable expiration (default: 30 minutes)
    - JWT refresh tokens with longer expiration (default: 7 days)
    - HS256 algorithm for token signing
    - Role-based access control (user, admin, superadmin)
    - Token expiration validation
    - Separate token types (access vs refresh)

Usage:
    >>> from src.core.auth import create_token_pair, decode_access_token
    >>> tokens = create_token_pair("user123", "john_doe", "user")
    >>> print(tokens.access_token)
    >>> token_data = decode_access_token(tokens.access_token)
    >>> print(token_data.username)

Notes:
    - JWT_SECRET_KEY is auto-generated if not set (not recommended for production)
    - Tokens are stateless (no server-side session storage)
    - Token validation happens on every request via get_current_user dependency
    - Refresh tokens can be used to obtain new access tokens

See Also:
    - src/api/dependencies/auth.py: FastAPI dependencies for authentication
    - src/api/v1/auth.py: Login endpoint implementation
    - src/core/user_store.py: User storage with Redis backend
"""

from datetime import UTC, datetime, timedelta

import structlog
from fastapi import HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel

from src.core.config import settings

logger = structlog.get_logger(__name__)

class TokenData(BaseModel):
    """JWT token payload.

    This model defines the data structure stored in JWT tokens.

    Attributes:
        user_id: Unique user identifier
        username: Username for display/logging
        role: User role (user, admin, superadmin)
        token_type: Token type (access or refresh)
        exp: Token expiration timestamp (automatically set)

    Example:
        >>> token_data = TokenData(
        ...     user_id="user_001",
        ...     username="john_doe",
        ...     role="user",
        ...     token_type="access",
        ...     exp=datetime.now(UTC) + timedelta(hours=1)
        ... )
    """

    user_id: str
    username: str
    role: str = "user"  # user, admin, superadmin
    token_type: str = "access"  # access or refresh
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
    """JWT token response with access and refresh tokens.

    This model is returned from the login endpoint after successful
    authentication.

    Attributes:
        access_token: JWT access token string (short-lived)
        refresh_token: JWT refresh token string (long-lived)
        token_type: Token type (always "bearer")
        expires_in: Access token lifetime in seconds

    Example:
        >>> token = Token(
        ...     access_token="eyJhbGc...",
        ...     refresh_token="eyJhbGc...",
        ...     token_type="bearer",
        ...     expires_in=1800
        ... )
        >>> print(f"Access token expires in {token.expires_in} seconds")
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds (for access token)


def _create_token(
    user_id: str,
    username: str,
    role: str,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    """Internal function to create a JWT token.

    Args:
        user_id: Unique user identifier
        username: Username for display/logging
        role: User role
        token_type: Token type (access or refresh)
        expires_delta: Token expiration duration

    Returns:
        Encoded JWT token string

    Raises:
        HTTPException: If token creation fails
    """
    expires = datetime.now(UTC) + expires_delta

    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "token_type": token_type,
        "exp": expires,
    }

    try:
        secret_key = settings.jwt_secret

        encoded_jwt = jwt.encode(
            payload,
            secret_key,
            algorithm=settings.jwt_algorithm,
        )

        logger.debug(
            f"{token_type}_token_created",
            user_id=user_id,
            username=username,
            role=role,
            expires_at=expires.isoformat(),
        )

        return encoded_jwt  # type: ignore[no-any-return]

    except Exception as e:
        logger.error("token_creation_failed", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create {token_type} token",
        ) from e


def create_access_token(user_id: str, username: str, role: str = "user") -> str:
    """Generate JWT access token (short-lived).

    Args:
        user_id: Unique user identifier
        username: Username for display/logging
        role: User role (default: "user")

    Returns:
        Encoded JWT access token string

    Example:
        >>> token = create_access_token("user_001", "john_doe", "user")
        >>> print(token[:20])
        'eyJhbGciOiJIUzI1NiI...'
    """
    return _create_token(
        user_id=user_id,
        username=username,
        role=role,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str, username: str, role: str = "user") -> str:
    """Generate JWT refresh token (long-lived).

    Args:
        user_id: Unique user identifier
        username: Username for display/logging
        role: User role (default: "user")

    Returns:
        Encoded JWT refresh token string

    Example:
        >>> token = create_refresh_token("user_001", "john_doe", "user")
        >>> print(token[:20])
        'eyJhbGciOiJIUzI1NiI...'
    """
    return _create_token(
        user_id=user_id,
        username=username,
        role=role,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def create_token_pair(user_id: str, username: str, role: str = "user") -> Token:
    """Generate access and refresh token pair.

    Creates both access and refresh tokens for a user.
    This is the primary function to use for authentication.

    Args:
        user_id: Unique user identifier
        username: Username for display/logging
        role: User role (default: "user")

    Returns:
        Token object with access_token, refresh_token, token_type, and expires_in

    Raises:
        HTTPException: If token creation fails (500 Internal Server Error)

    Example:
        >>> tokens = create_token_pair("user_001", "john_doe", "user")
        >>> print(tokens.access_token[:20])
        'eyJhbGciOiJIUzI1NiI...'
        >>> print(tokens.expires_in)
        1800

    Security Notes:
        - JWT_SECRET_KEY is auto-generated if not set (not recommended for production)
        - Tokens are stateless - cannot be revoked without additional infrastructure
        - Access tokens expire in 30 minutes (default)
        - Refresh tokens expire in 7 days (default)
    """
    access_token = create_access_token(user_id, username, role)
    refresh_token = create_refresh_token(user_id, username, role)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


def decode_token(token: str, expected_type: str = "access") -> TokenData:
    """Decode and validate JWT token.

    Validates the JWT signature, expiration, and token type, then returns the token payload.

    Args:
        token: JWT token string
        expected_type: Expected token type (access or refresh)

    Returns:
        TokenData object with user_id, username, role, token_type, and exp

    Raises:
        HTTPException: If token is expired (401 Unauthorized)
        HTTPException: If token is invalid, malformed, or wrong type (401 Unauthorized)

    Example:
        >>> token = "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
        >>> token_data = decode_token(token, "access")
        >>> print(token_data.username)
        'john_doe'

    Security Notes:
        - Token signature is validated using JWT_SECRET_KEY
        - Expiration is checked automatically by PyJWT
        - Token type is validated to prevent misuse
        - Invalid tokens raise 401 Unauthorized
    """
    try:
        secret_key = settings.jwt_secret

        # Decode and validate token
        payload = jwt.decode(token, secret_key, algorithms=[settings.jwt_algorithm])

        # Parse payload into TokenData
        token_data = TokenData(**payload)

        # Validate token type
        if token_data.token_type != expected_type:
            logger.warning(
                "token_type_mismatch",
                expected=expected_type,
                actual=token_data.token_type,
                token_preview=token[:20] + "...",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {expected_type}, got {token_data.token_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.debug(
            "token_decoded",
            user_id=token_data.user_id,
            username=token_data.username,
            token_type=token_data.token_type,
        )

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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("token_decode_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def decode_access_token(token: str) -> TokenData:
    """Decode and validate JWT access token.

    Args:
        token: JWT access token string

    Returns:
        TokenData object

    Raises:
        HTTPException: If token is invalid

    Example:
        >>> token_data = decode_access_token("eyJhbGc...")
        >>> print(token_data.username)
    """
    return decode_token(token, expected_type="access")


def decode_refresh_token(token: str) -> TokenData:
    """Decode and validate JWT refresh token.

    Args:
        token: JWT refresh token string

    Returns:
        TokenData object

    Raises:
        HTTPException: If token is invalid

    Example:
        >>> token_data = decode_refresh_token("eyJhbGc...")
        >>> print(token_data.username)
    """
    return decode_token(token, expected_type="refresh")
