"""Response utilities for standardized API responses.

Sprint 117 Feature 117.8: Response Format Standardization (3 SP)

This module provides utility functions for creating standardized API responses
with consistent metadata, pagination, and error handling.

Usage:
    # Success response
    >>> from src.core.response_utils import success_response
    >>> data = {"name": "tech_docs", "status": "ready"}
    >>> response = success_response(data, request_id="req_123")

    # Paginated response
    >>> from src.core.response_utils import paginated_response
    >>> items = [{"id": 1}, {"id": 2}, {"id": 3}]
    >>> response = paginated_response(items, page=1, page_size=20, total=100)

    # Error response
    >>> from src.core.response_utils import error_response
    >>> response = error_response(
    ...     code="DOMAIN_NOT_FOUND",
    ...     message="Domain 'medical' not found",
    ...     details={"domain_name": "medical"}
    ... )
"""

import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypeVar

from src.core.models.response import (
    ApiError,
    ApiErrorResponse,
    ApiResponse,
    PaginationMeta,
    RequestMetadata,
)

if TYPE_CHECKING:
    from fastapi import Request

# Type variable for generic responses
T = TypeVar("T")


def _generate_request_id() -> str:
    """Generate a unique request ID.

    Returns:
        Unique request ID in format 'req_<uuid>'

    Example:
        >>> request_id = _generate_request_id()
        >>> request_id.startswith('req_')
        True
    """
    return f"req_{uuid.uuid4().hex[:12]}"


def _create_metadata(
    request_id: str | None = None,
    processing_time_ms: float | None = None,
    api_version: str = "v1",
) -> RequestMetadata:
    """Create request metadata.

    Args:
        request_id: Unique request identifier (auto-generated if None)
        processing_time_ms: Processing time in milliseconds
        api_version: API version (default: "v1")

    Returns:
        RequestMetadata object with timestamp and request info
    """
    # Format timestamp with Z suffix (ISO 8601 UTC format)
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    return RequestMetadata(
        request_id=request_id or _generate_request_id(),
        timestamp=timestamp,
        processing_time_ms=processing_time_ms,
        api_version=api_version,
    )


def success_response(
    data: T,
    request_id: str | None = None,
    processing_time_ms: float | None = None,
    pagination: PaginationMeta | None = None,
    api_version: str = "v1",
) -> ApiResponse[T]:
    """Create a standardized success response.

    Wraps successful API responses with standard metadata envelope.

    Args:
        data: Response payload (any type)
        request_id: Unique request identifier (auto-generated if None)
        processing_time_ms: Processing time in milliseconds
        pagination: Optional pagination metadata
        api_version: API version (default: "v1")

    Returns:
        ApiResponse[T] with success=True and standardized metadata

    Example:
        >>> data = {"name": "tech_docs", "status": "ready"}
        >>> response = success_response(data, request_id="req_123")
        >>> response.success
        True
        >>> response.data["name"]
        'tech_docs'
    """
    metadata = _create_metadata(
        request_id=request_id,
        processing_time_ms=processing_time_ms,
        api_version=api_version,
    )

    return ApiResponse(
        success=True,
        data=data,
        metadata=metadata,
        pagination=pagination,
    )


def paginated_response(
    items: list[T],
    page: int,
    page_size: int,
    total: int,
    request_id: str | None = None,
    processing_time_ms: float | None = None,
    api_version: str = "v1",
) -> ApiResponse[list[T]]:
    """Create a paginated success response.

    Wraps paginated list responses with pagination metadata and standard envelope.

    Args:
        items: List of items for current page
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total: Total number of items available
        request_id: Unique request identifier (auto-generated if None)
        processing_time_ms: Processing time in milliseconds
        api_version: API version (default: "v1")

    Returns:
        ApiResponse[list[T]] with pagination metadata

    Example:
        >>> items = [{"id": 1}, {"id": 2}, {"id": 3}]
        >>> response = paginated_response(items, page=1, page_size=20, total=100)
        >>> response.pagination.has_more
        True
        >>> response.pagination.total
        100
    """
    # Calculate has_more
    has_more = (page * page_size) < total

    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        has_more=has_more,
    )

    return success_response(
        data=items,
        request_id=request_id,
        processing_time_ms=processing_time_ms,
        pagination=pagination,
        api_version=api_version,
    )


def error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
    api_version: str = "v1",
) -> ApiErrorResponse:
    """Create a standardized error response.

    Wraps error responses with standard error structure and metadata.

    Args:
        code: Machine-readable error code (from ErrorCode class)
        message: Human-readable error message
        details: Optional additional error details for debugging
        request_id: Unique request identifier (auto-generated if None)
        api_version: API version (default: "v1")

    Returns:
        ApiErrorResponse with success=False and error details

    Example:
        >>> response = error_response(
        ...     code="DOMAIN_NOT_FOUND",
        ...     message="Domain 'medical' not found",
        ...     details={"domain_name": "medical"}
        ... )
        >>> response.success
        False
        >>> response.error.code
        'DOMAIN_NOT_FOUND'
    """
    metadata = _create_metadata(
        request_id=request_id,
        processing_time_ms=None,  # Error responses don't track processing time
        api_version=api_version,
    )

    error = ApiError(
        code=code,
        message=message,
        details=details,
    )

    return ApiErrorResponse(
        success=False,
        error=error,
        metadata=metadata,
    )


def get_request_metadata(request: "Request") -> tuple[str, float]:
    """Extract request metadata from FastAPI Request object.

    Retrieves request_id and processing time from request.state, which are
    populated by the RequestIDMiddleware.

    Args:
        request: FastAPI Request object

    Returns:
        Tuple of (request_id, processing_time_ms)

    Raises:
        AttributeError: If RequestIDMiddleware is not installed

    Example:
        >>> from fastapi import Request
        >>> request_id, processing_time = get_request_metadata(request)
        >>> response = success_response(data, request_id=request_id, processing_time_ms=processing_time)
    """
    try:
        request_id = request.state.request_id
        start_time = request.state.start_time
        processing_time_ms = (time.time() - start_time) * 1000
        return request_id, processing_time_ms
    except AttributeError as e:
        raise AttributeError(
            "Request metadata not found. Ensure RequestIDMiddleware is installed."
        ) from e


def success_response_from_request(
    data: T,
    request: "Request",
    pagination: PaginationMeta | None = None,
    api_version: str = "v1",
) -> ApiResponse[T]:
    """Create success response using request metadata.

    Convenience function that extracts request_id and processing_time_ms
    from the FastAPI Request object.

    Args:
        data: Response payload
        request: FastAPI Request object
        pagination: Optional pagination metadata
        api_version: API version (default: "v1")

    Returns:
        ApiResponse[T] with request metadata from request object

    Example:
        >>> from fastapi import Request
        >>> @router.get("/domains")
        >>> async def list_domains(request: Request):
        ...     domains = await get_domains()
        ...     return success_response_from_request(domains, request)
    """
    request_id, processing_time_ms = get_request_metadata(request)
    return success_response(
        data=data,
        request_id=request_id,
        processing_time_ms=processing_time_ms,
        pagination=pagination,
        api_version=api_version,
    )


def paginated_response_from_request(
    items: list[T],
    page: int,
    page_size: int,
    total: int,
    request: "Request",
    api_version: str = "v1",
) -> ApiResponse[list[T]]:
    """Create paginated response using request metadata.

    Convenience function that extracts request_id and processing_time_ms
    from the FastAPI Request object.

    Args:
        items: List of items for current page
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total: Total number of items available
        request: FastAPI Request object
        api_version: API version (default: "v1")

    Returns:
        ApiResponse[list[T]] with pagination and request metadata

    Example:
        >>> from fastapi import Request
        >>> @router.get("/domains")
        >>> async def list_domains(request: Request, page: int = 1):
        ...     domains, total = await get_domains_paginated(page)
        ...     return paginated_response_from_request(domains, page, 20, total, request)
    """
    request_id, processing_time_ms = get_request_metadata(request)
    return paginated_response(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        request_id=request_id,
        processing_time_ms=processing_time_ms,
        api_version=api_version,
    )


def error_response_from_request(
    code: str,
    message: str,
    request: "Request",
    details: dict[str, Any] | None = None,
    api_version: str = "v1",
) -> ApiErrorResponse:
    """Create error response using request metadata.

    Convenience function that extracts request_id from the FastAPI Request object.

    Args:
        code: Machine-readable error code
        message: Human-readable error message
        request: FastAPI Request object
        details: Optional additional error details
        api_version: API version (default: "v1")

    Returns:
        ApiErrorResponse with request metadata

    Example:
        >>> from fastapi import Request
        >>> @router.get("/domains/{name}")
        >>> async def get_domain(name: str, request: Request):
        ...     if not domain_exists(name):
        ...         return error_response_from_request(
        ...             "DOMAIN_NOT_FOUND",
        ...             f"Domain '{name}' not found",
        ...             request
        ...         )
    """
    request_id = request.state.request_id
    return error_response(
        code=code,
        message=message,
        details=details,
        request_id=request_id,
        api_version=api_version,
    )


class ResponseTimer:
    """Context manager for tracking request processing time.

    Automatically tracks elapsed time and can be used to create
    responses with accurate processing_time_ms.

    Example:
        >>> with ResponseTimer() as timer:
        ...     # Do some processing
        ...     time.sleep(0.1)
        ...     result = {"status": "done"}
        ...
        >>> response = timer.success_response(result)
        >>> response.metadata.processing_time_ms > 100
        True
    """

    def __init__(self, request_id: str | None = None, api_version: str = "v1") -> None:
        """Initialize timer.

        Args:
            request_id: Unique request identifier (auto-generated if None)
            api_version: API version (default: "v1")
        """
        self.request_id = request_id or _generate_request_id()
        self.api_version = api_version
        self.start_time: float | None = None
        self.end_time: float | None = None

    def __enter__(self) -> "ResponseTimer":
        """Start timing."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop timing."""
        self.end_time = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds.

        Returns:
            Elapsed time in milliseconds

        Raises:
            RuntimeError: If timer has not been started
        """
        if self.start_time is None:
            raise RuntimeError("Timer not started")

        end = self.end_time if self.end_time is not None else time.perf_counter()
        return (end - self.start_time) * 1000

    def success_response(
        self,
        data: T,
        pagination: PaginationMeta | None = None,
    ) -> ApiResponse[T]:
        """Create success response with tracked processing time.

        Args:
            data: Response payload
            pagination: Optional pagination metadata

        Returns:
            ApiResponse[T] with processing time metadata
        """
        return success_response(
            data=data,
            request_id=self.request_id,
            processing_time_ms=self.elapsed_ms,
            pagination=pagination,
            api_version=self.api_version,
        )

    def paginated_response(
        self,
        items: list[T],
        page: int,
        page_size: int,
        total: int,
    ) -> ApiResponse[list[T]]:
        """Create paginated response with tracked processing time.

        Args:
            items: List of items for current page
            page: Current page number (1-indexed)
            page_size: Number of items per page
            total: Total number of items available

        Returns:
            ApiResponse[list[T]] with pagination and processing time metadata
        """
        return paginated_response(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            request_id=self.request_id,
            processing_time_ms=self.elapsed_ms,
            api_version=self.api_version,
        )

    def error_response(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> ApiErrorResponse:
        """Create error response with request metadata.

        Args:
            code: Machine-readable error code
            message: Human-readable error message
            details: Optional additional error details

        Returns:
            ApiErrorResponse with error details
        """
        return error_response(
            code=code,
            message=message,
            details=details,
            request_id=self.request_id,
            api_version=self.api_version,
        )
