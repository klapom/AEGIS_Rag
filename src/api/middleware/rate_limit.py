"""Custom middleware for FastAPI application.

This module provides rate limiting and other middleware functionality.

Sprint Context: Sprint 22 (2025-11-11) - Feature 22.2: API Security Hardening
Task: 22.2.3 - Add Rate Limiting and Fix CORS Configuration

Features:
    - slowapi-based rate limiting (per IP address)
    - Configurable limits per endpoint
    - Standardized error responses (integrates with Feature 22.2.2)
    - Rate limit headers in all responses
    - Request ID correlation (integrates with Feature 22.2.1)

Architecture:
    Request → slowapi checks limit → Allow/Deny → Add headers → Response
    If exceeded: Return 429 with ErrorResponse format

Rate Limits:
    - Global: 100 requests/minute (development)
    - Upload: 10 requests/minute
    - Search: 100 requests/minute
    - Configurable via settings (environment variables)

Example:
    >>> from src.api.middleware.rate_limit import limiter
    >>> from fastapi import Request
    >>>
    >>> @router.post("/search")
    >>> @limiter.limit("100/minute")  # 100 requests per minute per IP
    >>> async def search(request: Request, query: str):
    ...     return {"results": [...]}
"""

from datetime import UTC, datetime

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.core.config import get_settings
from src.core.models import ErrorCode, ErrorDetail, ErrorResponse

settings = get_settings()
logger = structlog.get_logger(__name__)

# Rate limiter configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],  # From config
    storage_uri=settings.rate_limit_storage_uri,  # memory:// or redis://
    enabled=settings.rate_limit_enabled,
)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors.

    This handler provides standardized error responses for rate limit violations,
    integrating with Sprint 22 Feature 22.2.2 (Standardized Error Responses) and
    Feature 22.2.1 (Request ID Tracking).

    Args:
        request: FastAPI request
        exc: RateLimitExceeded exception from slowapi

    Returns:
        JSONResponse with 429 status code and ErrorResponse format

    Example Response:
        {
            "error": {
                "code": "TOO_MANY_REQUESTS",
                "message": "Rate limit exceeded. Please try again later.",
                "details": {
                    "limit": 100,
                    "window": "1 minute",
                    "client_ip": "192.168.1.1"
                },
                "request_id": "a1b2c3d4-...",
                "timestamp": "2025-11-11T14:30:00Z",
                "path": "/api/v1/retrieval/search"
            }
        }
    """
    # Get request ID from request state (set by RequestIDMiddleware)
    request_id = getattr(request.state, "request_id", "unknown")

    # Log rate limit violation with request ID
    logger.warning(
        "rate_limit_exceeded",
        client_ip=get_remote_address(request),
        path=request.url.path,
        request_id=request_id,
    )

    # Parse rate limit details from exception
    # slowapi format: "1 per 1 minute" or similar
    limit_str = str(exc.detail) if hasattr(exc, "detail") else ""
    parts = limit_str.split(" per ")
    limit = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
    window = parts[1] if len(parts) > 1 else "1 minute"

    # Create standardized error response (Sprint 22 Feature 22.2.2)
    error_response = ErrorResponse(
        error=ErrorDetail(
            code=ErrorCode.TOO_MANY_REQUESTS,
            message="Rate limit exceeded. Please try again later.",
            details={
                "limit": limit,
                "window": window,
                "client_ip": get_remote_address(request),
            },
            request_id=request_id,
            timestamp=datetime.now(UTC),
            path=request.url.path,
        )
    )

    # Return 429 with rate limit headers
    return JSONResponse(
        status_code=429,
        content=error_response.model_dump(mode="json"),
        headers={
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(datetime.now(UTC).timestamp()) + 60),
            "Retry-After": "60",  # Seconds
            "X-Request-ID": request_id,
        },
    )


async def log_request_middleware(request: Request, call_next):
    """Log all incoming requests.

    Args:
        request: FastAPI request
        call_next: Next middleware/route handler

    Returns:
        Response from next handler
    """
    logger.info(
        "Incoming request",
        method=request.method,
        path=request.url.path,
        client_ip=get_remote_address(request),
    )

    response = await call_next(request)

    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )

    return response
