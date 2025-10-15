"""Custom middleware for FastAPI application.

This module provides rate limiting and other middleware functionality.
"""

import structlog
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from src.core.config import settings

logger = structlog.get_logger(__name__)

# Rate limiter configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/hour"],  # Default: 100 requests per hour per IP
    storage_uri="memory://",  # In-memory storage (use Redis in production)
)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors.

    Args:
        request: FastAPI request
        exc: RateLimitExceeded exception

    Returns:
        JSON response with 429 status code
    """
    logger.warning(
        "Rate limit exceeded",
        client_ip=get_remote_address(request),
        path=request.url.path,
    )

    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "retry_after": exc.detail if hasattr(exc, "detail") else "60 seconds",
        },
        headers={
            "Retry-After": "60",
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
