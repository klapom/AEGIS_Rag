"""Authentication API endpoints.

Sprint Context: Sprint 22 (2025-11-11) - Feature 22.2: API Security Hardening
Task: 22.2.4 - Standardize Authentication Across All Endpoints

This module provides authentication endpoints for JWT-based authentication.

Endpoints:
    POST /api/v1/auth/login - Login with username/password and get JWT token
    GET /api/v1/auth/me - Get current authenticated user info

IMPORTANT - TEMPORARY IMPLEMENTATION:
    This uses hardcoded users for Sprint 22 testing.
    Sprint 23 will replace with database-backed user management with bcrypt hashing.

Security Notes:
    - JWT tokens expire after 60 minutes
    - Tokens are stateless (no server-side session storage)
    - Password validation is case-sensitive
    - Failed login attempts are logged

Example Usage:
    # Login
    >>> response = requests.post("/api/v1/auth/login", json={
    ...     "username": "admin",
    ...     "password": "admin123"
    ... })
    >>> token = response.json()["access_token"]

    # Use token
    >>> headers = {"Authorization": f"Bearer {token}"}
    >>> response = requests.get("/api/v1/auth/me", headers=headers)
    >>> print(response.json())
    {"user_id": "user_admin", "username": "admin", "role": "admin"}

See Also:
    - src/core/auth.py: Token creation and validation
    - src/api/dependencies.py: Authentication dependencies
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.core.auth import Token, User, create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
logger = structlog.get_logger(__name__)


class LoginRequest(BaseModel):
    """Login request with username and password.

    Attributes:
        username: Username (case-sensitive)
        password: Password (case-sensitive)

    Example:
        >>> request = LoginRequest(username="admin", password="admin123")
    """

    username: str = Field(..., description="Username", min_length=1, max_length=50)
    password: str = Field(..., description="Password", min_length=1, max_length=100)


# TEMPORARY: Hardcoded users for Sprint 22
# TODO Sprint 23: Replace with database lookup + bcrypt password hashing
# Security Note: These credentials are for TESTING ONLY and MUST be changed in production
TEMP_USERS = {
    "admin": {
        "password": "admin123",
        "role": "admin",
        "user_id": "user_admin",
        "email": "admin@aegisrag.local",
    },
    "user": {
        "password": "user123",
        "role": "user",
        "user_id": "user_001",
        "email": "user@aegisrag.local",
    },
    "testuser": {
        "password": "testpass",
        "role": "user",
        "user_id": "user_test",
        "email": "test@aegisrag.local",
    },
}


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest) -> Token:
    """
    Authenticate user and return JWT token.

    **TEMPORARY IMPLEMENTATION - Sprint 22**

    Uses hardcoded users for testing. Production will use database lookup
    with bcrypt password hashing (Sprint 23).

    **Available Test Users:**
    - Username: `admin`, Password: `admin123`, Role: `admin`
    - Username: `user`, Password: `user123`, Role: `user`
    - Username: `testuser`, Password: `testpass`, Role: `user`

    Args:
        request: Login credentials (username and password)

    Returns:
        Token object with access_token, token_type, and expires_in

    Raises:
        HTTPException: 401 Unauthorized if credentials are invalid

    Example:
        >>> # Login as admin
        >>> response = await login(LoginRequest(
        ...     username="admin",
        ...     password="admin123"
        ... ))
        >>> print(response.access_token)
        'eyJhbGciOiJIUzI1NiIsInR5cCI6...'

    Security Notes:
        - Passwords are case-sensitive
        - Failed login attempts are logged
        - Rate limiting is enforced via slowapi middleware
        - JWT secret MUST be changed in production

    Response Schema:
        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
            "token_type": "bearer",
            "expires_in": 3600
        }
    """
    logger.info("login_attempt", username=request.username)

    # Lookup user (TEMPORARY - hardcoded)
    user_data = TEMP_USERS.get(request.username)

    if user_data is None or user_data["password"] != request.password:
        logger.warning(
            "login_failed",
            username=request.username,
            reason="Invalid credentials",
            note="Hardcoded users: admin/admin123, user/user123",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate JWT token
    token = create_access_token(
        user_id=user_data["user_id"],
        username=request.username,
        role=user_data["role"],
    )

    logger.info(
        "login_success",
        username=request.username,
        role=user_data["role"],
        user_id=user_data["user_id"],
    )

    return token


@router.get("/me", response_model=User, status_code=status.HTTP_200_OK)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current authenticated user info.

    This endpoint returns information about the currently authenticated user
    based on the JWT token in the Authorization header.

    Args:
        current_user: Authenticated user from get_current_user dependency

    Returns:
        User object with user_id, username, role, and email

    Raises:
        HTTPException: 401 Unauthorized if token is missing or invalid

    Example:
        >>> headers = {"Authorization": f"Bearer {token}"}
        >>> response = requests.get("/api/v1/auth/me", headers=headers)
        >>> print(response.json())
        {
            "user_id": "user_admin",
            "username": "admin",
            "role": "admin",
            "email": "admin@aegisrag.local"
        }

    Security Notes:
        - Requires valid JWT token in Authorization header
        - Token signature is validated
        - Expired tokens are rejected

    Response Schema:
        {
            "user_id": "string",
            "username": "string",
            "role": "string",
            "email": "string | null"
        }
    """
    logger.info("get_me", user_id=current_user.user_id, username=current_user.username)

    # Add email from hardcoded users (TEMPORARY)
    # Sprint 23: Fetch from database
    user_data = TEMP_USERS.get(current_user.username)
    if user_data:
        current_user.email = user_data.get("email")

    return current_user
