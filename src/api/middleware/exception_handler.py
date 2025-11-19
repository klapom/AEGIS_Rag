"""Exception handler middleware for standardized error responses.

Sprint 22 Feature 22.2.2: Standardized API error responses across all endpoints.

This module provides global exception handlers that convert all errors into
a standardized ErrorResponse format with request IDs for log correlation.
"""

from datetime import UTC, datetime

import structlog
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.exceptions import AegisRAGException
from src.core.models import ErrorCode, ErrorDetail, ErrorResponse

logger = structlog.get_logger(__name__)


async def aegis_exception_handler(request: Request, exc: AegisRAGException) -> JSONResponse:
    """Handle custom AegisRAG exceptions.

    Args:
        request: FastAPI request object
        exc: AegisRAGException instance

    Returns:
        JSONResponse with standardized error format
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        "aegis_exception",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        status_code=exc.status_code,
        path=request.url.path,
        request_id=request_id,
    )

    error_response = ErrorResponse(
        error=ErrorDetail(
            code=exc.error_code,
            message=exc.message,
            details=exc.details,
            request_id=request_id,
            timestamp=datetime.now(UTC),
            path=request.url.path,
        )
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode="json"),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard HTTP exceptions.

    Args:
        request: FastAPI request object
        exc: StarletteHTTPException instance

    Returns:
        JSONResponse with standardized error format
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Map HTTP status codes to error codes
    status_to_code = {
        400: ErrorCode.BAD_REQUEST,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        405: ErrorCode.METHOD_NOT_ALLOWED,
        409: ErrorCode.CONFLICT,
        422: ErrorCode.UNPROCESSABLE_ENTITY,
        429: ErrorCode.TOO_MANY_REQUESTS,
        500: ErrorCode.INTERNAL_SERVER_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE,
        504: ErrorCode.GATEWAY_TIMEOUT,
    }

    error_code = status_to_code.get(exc.status_code, ErrorCode.INTERNAL_SERVER_ERROR)

    logger.error(
        "http_exception",
        error_code=error_code,
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        request_id=request_id,
    )

    error_response = ErrorResponse(
        error=ErrorDetail(
            code=error_code,
            message=str(exc.detail),
            request_id=request_id,
            timestamp=datetime.now(UTC),
            path=request.url.path,
        )
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode="json"),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors.

    Args:
        request: FastAPI request object
        exc: RequestValidationError instance

    Returns:
        JSONResponse with standardized error format including validation details
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Convert validation errors to JSON-serializable format
    validation_errors = []
    for error in exc.errors():
        validation_errors.append(
            {
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
            }
        )

    logger.warning(
        "validation_error",
        validation_errors=validation_errors,
        path=request.url.path,
        request_id=request_id,
    )

    error_response = ErrorResponse(
        error=ErrorDetail(
            code=ErrorCode.UNPROCESSABLE_ENTITY,
            message="Request validation failed",
            details={"validation_errors": validation_errors},
            request_id=request_id,
            timestamp=datetime.now(UTC),
            path=request.url.path,
        )
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode="json"),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected exceptions.

    Args:
        request: FastAPI request object
        exc: Generic Exception instance

    Returns:
        JSONResponse with standardized error format
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        "unhandled_exception",
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=request.url.path,
        request_id=request_id,
        exc_info=True,
    )

    # Don't leak internal error details in production
    # (check debug mode from settings if available)
    error_details = None
    try:
        from src.core.config import get_settings

        settings = get_settings()
        if settings.debug:
            error_details = {"error_type": type(exc).__name__, "error_message": str(exc)}
    except Exception:
        # If we can't load settings, don't expose details
        pass

    error_response = ErrorResponse(
        error=ErrorDetail(
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            details=error_details,
            request_id=request_id,
            timestamp=datetime.now(UTC),
            path=request.url.path,
        )
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode="json"),
    )
