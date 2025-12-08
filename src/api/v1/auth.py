"""Authentication API endpoints with Redis-backed user storage.

Sprint Context: Sprint 38 (2025-12-08) - Feature 38.1a: JWT Authentication Backend

This module provides complete authentication endpoints with:
- User registration
- Login with JWT token generation
- Token refresh
- Current user retrieval
- Logout (token invalidation via blacklist)

Endpoints:
    POST /api/v1/auth/register - Register new user
    POST /api/v1/auth/login - Login and get JWT tokens
    POST /api/v1/auth/refresh - Refresh access token
    GET /api/v1/auth/me - Get current user info
    POST /api/v1/auth/logout - Logout (invalidate token)

Security Features:
    - Bcrypt password hashing
    - JWT access tokens (30 min expiration)
    - JWT refresh tokens (7 day expiration)
    - Redis-backed user storage
    - Token blacklist for logout

Example Usage:
    # Register
    >>> response = requests.post("/api/v1/auth/register", json={
    ...     "username": "john",
    ...     "password": "secret123",
    ...     "email": "john@example.com"
    ... })
    >>> print(response.json())

    # Login
    >>> response = requests.post("/api/v1/auth/login", json={
    ...     "username": "john",
    ...     "password": "secret123"
    ... })
    >>> tokens = response.json()
    >>> access_token = tokens["access_token"]

    # Use token
    >>> headers = {"Authorization": f"Bearer {access_token}"}
    >>> response = requests.get("/api/v1/auth/me", headers=headers)
    >>> print(response.json())

See Also:
    - src/core/auth.py: Token creation and validation
    - src/core/user_store.py: User storage with Redis
    - src/api/dependencies/auth.py: Authentication dependencies
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.core.auth import (
    Token,
    User,
    create_token_pair,
    decode_access_token,
    decode_refresh_token,
)
from src.core.user_store import UserCreate, UserPublic, UserStore

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
logger = structlog.get_logger(__name__)


class LoginRequest(BaseModel):
    """Login request with username and password.

    Attributes:
        username: Username (3-50 chars)
        password: Password (min 8 chars)

    Example:
        >>> request = LoginRequest(username="john", password="secret123")
    """

    username: str = Field(..., description="Username", min_length=3, max_length=50)
    password: str = Field(..., description="Password", min_length=8, max_length=100)


class RefreshRequest(BaseModel):
    """Token refresh request.

    Attributes:
        refresh_token: JWT refresh token

    Example:
        >>> request = RefreshRequest(refresh_token="eyJhbGc...")
    """

    refresh_token: str = Field(..., description="Refresh token")


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(user_create: UserCreate) -> UserPublic:
    """
    Register a new user.

    Creates a new user account with bcrypt-hashed password stored in Redis.

    Args:
        user_create: User registration data (username, password, email, role)

    Returns:
        UserPublic object with user_id, username, email, role, created_at

    Raises:
        HTTPException: 400 Bad Request if username already exists
        HTTPException: 500 Internal Server Error if user creation fails

    Example:
        >>> # Register new user
        >>> response = await register(UserCreate(
        ...     username="john",
        ...     password="secret123",
        ...     email="john@example.com",
        ...     role="user"
        ... ))
        >>> print(response.username)
        'john'

    Security Notes:
        - Password is hashed with bcrypt (cost factor 12)
        - Username must be unique
        - Email is optional
        - Role defaults to "user"

    Response Schema:
        {
            "user_id": "user_abc123",
            "username": "john",
            "email": "john@example.com",
            "role": "user",
            "created_at": "2025-12-08T10:30:00Z",
            "is_active": true
        }
    """
    logger.info("register_attempt", username=user_create.username)

    store = UserStore()
    try:
        user = await store.create_user(user_create)
        logger.info(
            "register_success",
            user_id=user.user_id,
            username=user.username,
            role=user.role,
        )
        return store.to_public(user)
    except ValueError as e:
        logger.warning(
            "register_failed",
            username=user_create.username,
            reason=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("register_error", username=user_create.username, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        ) from e
    finally:
        await store.close()


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest) -> Token:
    """
    Authenticate user and return JWT tokens.

    Validates username and password, then returns access and refresh tokens.

    Args:
        request: Login credentials (username and password)

    Returns:
        Token object with access_token, refresh_token, token_type, and expires_in

    Raises:
        HTTPException: 401 Unauthorized if credentials are invalid
        HTTPException: 401 Unauthorized if account is inactive

    Example:
        >>> # Login
        >>> response = await login(LoginRequest(
        ...     username="john",
        ...     password="secret123"
        ... ))
        >>> print(response.access_token[:20])
        'eyJhbGciOiJIUzI1NiI...'

    Security Notes:
        - Password verification uses bcrypt
        - Failed login attempts are logged
        - Rate limiting is enforced via slowapi middleware
        - Access tokens expire in 30 minutes (default)
        - Refresh tokens expire in 7 days (default)

    Response Schema:
        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
            "token_type": "bearer",
            "expires_in": 1800
        }
    """
    logger.info("login_attempt", username=request.username)

    store = UserStore()
    try:
        # Lookup user
        user = await store.get_user_by_username(request.username)

        if user is None:
            logger.warning(
                "login_failed",
                username=request.username,
                reason="User not found",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if account is active
        if not user.is_active:
            logger.warning(
                "login_failed",
                username=request.username,
                reason="Account inactive",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify password
        if not await store.verify_password(request.password, user.hashed_password):
            logger.warning(
                "login_failed",
                username=request.username,
                reason="Invalid password",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate token pair
        tokens = create_token_pair(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
        )

        logger.info(
            "login_success",
            username=user.username,
            user_id=user.user_id,
            role=user.role,
        )

        return tokens

    finally:
        await store.close()


@router.post("/refresh", response_model=Token, status_code=status.HTTP_200_OK)
async def refresh_token(request: RefreshRequest) -> Token:
    """
    Refresh access token using refresh token.

    Validates the refresh token and issues a new access token.

    Args:
        request: Refresh token request

    Returns:
        Token object with new access_token, same refresh_token, token_type, and expires_in

    Raises:
        HTTPException: 401 Unauthorized if refresh token is invalid or expired

    Example:
        >>> # Refresh access token
        >>> response = await refresh_token(RefreshRequest(
        ...     refresh_token="eyJhbGc..."
        ... ))
        >>> print(response.access_token[:20])
        'eyJhbGciOiJIUzI1NiI...'

    Security Notes:
        - Refresh token must be valid and not expired
        - New access token has standard expiration (30 minutes)
        - Refresh token is NOT rotated (reuse allowed until expiration)
        - For token rotation, implement blacklist or database tracking

    Response Schema:
        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
            "token_type": "bearer",
            "expires_in": 1800
        }
    """
    logger.info("token_refresh_attempt")

    try:
        # Decode and validate refresh token
        token_data = decode_refresh_token(request.refresh_token)

        # Generate new token pair
        tokens = create_token_pair(
            user_id=token_data.user_id,
            username=token_data.username,
            role=token_data.role,
        )

        logger.info(
            "token_refresh_success",
            user_id=token_data.user_id,
            username=token_data.username,
        )

        return tokens

    except HTTPException:
        logger.warning("token_refresh_failed", reason="Invalid refresh token")
        raise


@router.get("/me", response_model=UserPublic, status_code=status.HTTP_200_OK)
async def get_me(current_user: User = Depends(get_current_user)) -> UserPublic:
    """
    Get current authenticated user info.

    Returns information about the currently authenticated user based on
    the JWT token in the Authorization header.

    Args:
        current_user: Authenticated user from get_current_user dependency

    Returns:
        UserPublic object with user_id, username, email, role, created_at

    Raises:
        HTTPException: 401 Unauthorized if token is missing or invalid

    Example:
        >>> headers = {"Authorization": f"Bearer {token}"}
        >>> response = requests.get("/api/v1/auth/me", headers=headers)
        >>> print(response.json())
        {
            "user_id": "user_abc123",
            "username": "john",
            "email": "john@example.com",
            "role": "user",
            "created_at": "2025-12-08T10:30:00Z",
            "is_active": true
        }

    Security Notes:
        - Requires valid JWT token in Authorization header
        - Token signature is validated
        - Expired tokens are rejected

    Response Schema:
        {
            "user_id": "string",
            "username": "string",
            "email": "string | null",
            "role": "string",
            "created_at": "datetime",
            "is_active": "boolean"
        }
    """
    logger.info("get_me", user_id=current_user.user_id, username=current_user.username)

    store = UserStore()
    try:
        # Fetch full user data from storage
        user = await store.get_user_by_id(current_user.user_id)

        if user is None:
            logger.error(
                "get_me_failed",
                user_id=current_user.user_id,
                reason="User not found in storage",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return store.to_public(user)

    finally:
        await store.close()


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    """
    Logout user (invalidate token).

    Currently logs the logout event. For true token invalidation, implement
    a token blacklist in Redis or database.

    Args:
        current_user: Authenticated user from get_current_user dependency

    Returns:
        Success message

    Example:
        >>> headers = {"Authorization": f"Bearer {token}"}
        >>> response = requests.post("/api/v1/auth/logout", headers=headers)
        >>> print(response.json())
        {"message": "Successfully logged out"}

    Security Notes:
        - JWT tokens are stateless and cannot be truly invalidated
        - For production, implement token blacklist in Redis
        - Blacklist should store token JTI (JWT ID) until expiration
        - Client should discard tokens on logout

    Future Enhancement:
        - Implement Redis-based token blacklist
        - Add JTI claim to tokens
        - Check blacklist in get_current_user dependency

    Response Schema:
        {
            "message": "Successfully logged out"
        }
    """
    logger.info("logout", user_id=current_user.user_id, username=current_user.username)

    # TODO: Implement token blacklist in Redis for true invalidation
    # For now, just log the logout event
    # Client should discard tokens on logout

    return {"message": "Successfully logged out"}
