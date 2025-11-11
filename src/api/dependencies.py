"""FastAPI dependency functions.

Sprint Context: Sprint 22 (2025-11-11) - Feature 22.2: API Security Hardening
Task: 22.2.1 - Implement Request ID Tracking Middleware
Task: 22.2.4 - Standardize Authentication Across All Endpoints

This module provides FastAPI dependency injection functions for common request
context like request IDs, authentication, rate limiting, etc.

Dependencies:
    - get_request_id: Extract request ID from request state
    - get_current_user: Validate JWT and return authenticated user (required)
    - get_current_admin_user: Validate JWT and require admin role
    - get_optional_user: Optional authentication (None if not authenticated)

Example:
    >>> from fastapi import Depends
    >>> from src.api.dependencies import get_request_id, get_current_user
    >>> from src.core.auth import User
    >>>
    >>> @router.post("/upload")
    >>> async def upload(
    ...     file: UploadFile,
    ...     request_id: str = Depends(get_request_id),
    ...     current_user: User = Depends(get_current_user)
    ... ):
    ...     logger.info("upload_started", request_id=request_id)
    ...     return {"request_id": request_id, "user": current_user.username}

Notes:
    - All dependencies are designed to be async-safe
    - Request ID is automatically set by RequestIDMiddleware
    - User info is automatically bound to structlog context
    - Use Depends() to inject dependencies into route handlers

See Also:
    - src/api/middleware/request_id.py: RequestIDMiddleware
    - src/core/auth.py: Authentication models and utilities
    - FastAPI Dependencies: https://fastapi.tiangolo.com/tutorial/dependencies/
"""

from typing import Optional

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.auth import User, decode_access_token

logger = structlog.get_logger(__name__)

# HTTP Bearer token extraction
security = HTTPBearer(auto_error=False)


def get_request_id(request: Request) -> str:
    """
    FastAPI dependency to extract request ID from request state.

    This dependency retrieves the request ID that was set by the
    RequestIDMiddleware. If the middleware is not registered or the
    request ID is not available, it returns "unknown".

    Args:
        request: FastAPI request object (automatically injected)

    Returns:
        str: Request ID (UUID format) or "unknown" if not available

    Example:
        >>> from fastapi import APIRouter, Depends
        >>> from src.api.dependencies import get_request_id
        >>> import structlog
        >>>
        >>> router = APIRouter()
        >>> logger = structlog.get_logger(__name__)
        >>>
        >>> @router.post("/upload")
        >>> async def upload(
        ...     file: UploadFile,
        ...     request_id: str = Depends(get_request_id)
        ... ):
        ...     logger.info("upload_started", request_id=request_id)
        ...     # Process file...
        ...     return {"status": "success", "request_id": request_id}

    Usage Patterns:
        # Basic usage (explicit request ID in response)
        @router.post("/upload")
        async def upload(request_id: str = Depends(get_request_id)):
            return {"request_id": request_id}

        # With logging (request ID already in logs via contextvars)
        @router.post("/process")
        async def process(request_id: str = Depends(get_request_id)):
            logger.info("processing_started")  # request_id auto-included
            return {"status": "ok"}

        # With error handling (include request ID in error response)
        @router.post("/risky")
        async def risky(request_id: str = Depends(get_request_id)):
            try:
                # ... risky operation ...
            except Exception as e:
                logger.error("operation_failed", error=str(e))
                raise HTTPException(
                    status_code=500,
                    detail={"error": str(e), "request_id": request_id}
                )

    Notes:
        - RequestIDMiddleware MUST be registered for this to work
        - Request ID is automatically bound to structlog context
        - Useful for including request ID in response bodies
        - Returns "unknown" if middleware is missing (graceful degradation)

    Performance:
        - Overhead: <1 microsecond (simple attribute access)
        - No I/O or computation involved

    See Also:
        - RequestIDMiddleware: Sets request.state.request_id
        - structlog.contextvars: Automatic context binding for logs
    """
    return getattr(request.state, "request_id", "unknown")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """
    FastAPI dependency to extract and validate JWT token.

    This dependency validates the JWT token from the Authorization header
    and returns the authenticated user. User information is automatically
    bound to the structlog context for request correlation.

    Args:
        credentials: HTTP Bearer token from Authorization header (auto-injected)

    Returns:
        User object with user_id, username, and role

    Raises:
        HTTPException: 401 Unauthorized if token is missing, expired, or invalid

    Example:
        >>> @router.post("/protected")
        >>> async def protected_endpoint(current_user: User = Depends(get_current_user)):
        ...     logger.info("protected_action")  # user_id auto-included in logs
        ...     return {"message": f"Hello {current_user.username}"}

    Usage Patterns:
        # Require authentication for endpoint
        @router.post("/upload")
        async def upload(current_user: User = Depends(get_current_user)):
            # Only authenticated users reach here
            pass

        # Access user information
        @router.get("/profile")
        async def profile(current_user: User = Depends(get_current_user)):
            return {"username": current_user.username, "role": current_user.role}

    Security Notes:
        - Token must be in "Authorization: Bearer <token>" header format
        - Token signature is validated using JWT_SECRET_KEY
        - Expired tokens are rejected with 401 Unauthorized
        - User info is bound to structlog context for correlation

    Performance:
        - Overhead: <5ms per request (JWT decode + validation)
        - No database queries (stateless authentication)

    See Also:
        - get_current_admin_user: Require admin role
        - get_optional_user: Optional authentication
        - src/core/auth.py: Token creation and validation
    """
    if credentials is None:
        logger.warning("auth_missing", reason="No Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    token_data = decode_access_token(token)

    user = User(
        user_id=token_data.user_id,
        username=token_data.username,
        role=token_data.role,
    )

    # Bind user to structlog context (like request_id)
    structlog.contextvars.bind_contextvars(
        user_id=user.user_id,
        username=user.username,
        role=user.role,
    )

    logger.info("auth_success", user_id=user.user_id, role=user.role)

    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency for admin-only endpoints.

    This dependency builds on get_current_user to additionally verify
    that the authenticated user has admin privileges (admin or superadmin role).

    Args:
        current_user: Authenticated user from get_current_user (auto-injected)

    Returns:
        User object if user has admin privileges

    Raises:
        HTTPException: 401 Unauthorized if not authenticated
        HTTPException: 403 Forbidden if authenticated but not admin

    Example:
        >>> @router.post("/admin/reindex")
        >>> async def admin_action(admin: User = Depends(get_current_admin_user)):
        ...     # Only admins reach here
        ...     logger.info("admin_action_started")
        ...     return {"status": "reindex started"}

    Usage Patterns:
        # Require admin role for endpoint
        @router.delete("/admin/documents/{doc_id}")
        async def delete_document(
            doc_id: str,
            admin: User = Depends(get_current_admin_user)
        ):
            # Only admin/superadmin users reach here
            pass

        # Check role explicitly
        @router.post("/admin/settings")
        async def update_settings(admin: User = Depends(get_current_admin_user)):
            if admin.role == "superadmin":
                # Superadmin-only logic
                pass

    Security Notes:
        - First validates authentication (via get_current_user)
        - Then checks role is "admin" or "superadmin"
        - Non-admin users receive 403 Forbidden (not 401)
        - Failed auth attempts are logged with reason

    See Also:
        - get_current_user: Base authentication dependency
        - User.is_admin(): Check admin privileges
    """
    if not current_user.is_admin():
        logger.warning(
            "auth_forbidden",
            user_id=current_user.user_id,
            role=current_user.role,
            reason="Admin role required",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """
    Dependency for endpoints that support optional authentication.

    This dependency attempts to authenticate the user if a token is provided,
    but does not raise an error if authentication fails. This is useful for
    endpoints that provide enhanced functionality for authenticated users but
    still work for unauthenticated users.

    Args:
        credentials: HTTP Bearer token from Authorization header (auto-injected)

    Returns:
        User object if authenticated, None if not authenticated or token invalid

    Example:
        >>> @router.get("/public-but-better-when-authed")
        >>> async def endpoint(user: Optional[User] = Depends(get_optional_user)):
        ...     if user:
        ...         logger.info("personalized_response")
        ...         return {"message": f"Welcome back {user.username}"}
        ...     else:
        ...         logger.info("anonymous_response")
        ...         return {"message": "Welcome guest"}

    Usage Patterns:
        # Personalized vs generic response
        @router.get("/recommendations")
        async def recommendations(user: Optional[User] = Depends(get_optional_user)):
            if user:
                # Return personalized recommendations
                return get_user_recommendations(user.user_id)
            else:
                # Return popular items
                return get_popular_items()

        # Conditional rate limits
        @router.post("/search")
        async def search(
            query: str,
            user: Optional[User] = Depends(get_optional_user)
        ):
            limit = 100 if user else 10  # Higher limit for authenticated users
            return perform_search(query, limit)

    Security Notes:
        - Does NOT raise exceptions for missing/invalid tokens
        - Invalid tokens are treated as unauthenticated (returns None)
        - Failed auth attempts are NOT logged (to avoid spam)
        - User context is NOT bound to structlog if authentication fails

    Performance:
        - Same overhead as get_current_user when token is valid
        - No overhead when no token is provided

    See Also:
        - get_current_user: Required authentication
        - get_current_admin_user: Admin-only endpoints
    """
    if credentials is None:
        return None

    try:
        token_data = decode_access_token(credentials.credentials)
        user = User(
            user_id=token_data.user_id,
            username=token_data.username,
            role=token_data.role,
        )

        # Bind user to structlog context
        structlog.contextvars.bind_contextvars(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
        )

        return user
    except HTTPException:
        # Invalid token - treat as unauthenticated (don't log to avoid spam)
        return None
