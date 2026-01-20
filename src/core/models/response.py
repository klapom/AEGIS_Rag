"""Standard API Response Models for AegisRAG.

Sprint 117 Feature 117.8: Response Format Standardization (3 SP)

This module provides standardized response envelopes for all API endpoints,
ensuring consistent structure for success and error responses with metadata.

Standard Success Format:
    {
        "success": true,
        "data": {...},
        "metadata": {
            "request_id": "req_abc123",
            "timestamp": "2026-01-20T16:00:00Z",
            "processing_time_ms": 342,
            "api_version": "v1"
        },
        "pagination": {
            "page": 1,
            "page_size": 20,
            "total": 100,
            "has_more": true
        }
    }

Standard Error Format:
    {
        "success": false,
        "error": {
            "code": "DOMAIN_NOT_FOUND",
            "message": "Domain 'medical' not found",
            "details": {...}
        },
        "metadata": {
            "request_id": "req_abc123",
            "timestamp": "2026-01-20T16:00:00Z",
            "api_version": "v1"
        }
    }
"""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# Generic type for response data
T = TypeVar("T")


class RequestMetadata(BaseModel):
    """Metadata about the API request and processing.

    Included in both success and error responses for request tracking,
    debugging, and performance monitoring.

    Attributes:
        request_id: Unique request identifier for tracing
        timestamp: ISO 8601 timestamp when request was processed
        processing_time_ms: Time taken to process request in milliseconds
        api_version: API version used (e.g., "v1")
    """

    request_id: str = Field(
        ...,
        description="Unique request identifier",
        examples=["req_abc123", "req_xyz789"],
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp",
        examples=["2026-01-20T16:00:00Z"],
    )
    processing_time_ms: float | None = Field(
        None,
        description="Processing time in milliseconds",
        ge=0.0,
        examples=[342.5, 1250.8],
    )
    api_version: str = Field(
        default="v1",
        description="API version",
        examples=["v1", "v2"],
    )


class PaginationMeta(BaseModel):
    """Pagination information for list responses.

    Provides details about pagination state for paginated endpoints,
    enabling clients to navigate through result sets.

    Attributes:
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total: Total number of items available
        has_more: Whether more pages are available
    """

    page: int = Field(
        ...,
        description="Current page number (1-indexed)",
        ge=1,
        examples=[1, 2, 5],
    )
    page_size: int = Field(
        ...,
        description="Number of items per page",
        ge=1,
        le=100,
        examples=[20, 50, 100],
    )
    total: int = Field(
        ...,
        description="Total number of items",
        ge=0,
        examples=[100, 250, 0],
    )
    has_more: bool = Field(
        ...,
        description="Whether more pages are available",
        examples=[True, False],
    )


class ApiError(BaseModel):
    """Error details for failed API requests.

    Standard error structure providing machine-readable error codes,
    human-readable messages, and optional details for debugging.

    Attributes:
        code: Machine-readable error code (from DomainErrorCode enum)
        message: Human-readable error message
        details: Optional additional error details for debugging
    """

    code: str = Field(
        ...,
        description="Machine-readable error code",
        examples=["DOMAIN_NOT_FOUND", "VALIDATION_ERROR", "UNAUTHORIZED"],
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
        examples=[
            "Domain 'medical' not found",
            "Validation failed for field 'name'",
            "Unauthorized access",
        ],
    )
    details: dict[str, Any] | None = Field(
        None,
        description="Additional error details",
        examples=[
            {"domain_name": "medical", "suggestion": "Available domains: general, finance"},
            {"field": "name", "issue": "Must be 3-50 characters"},
        ],
    )


class ApiResponse(BaseModel, Generic[T]):
    """Generic success response wrapper.

    Wraps successful API responses with standard metadata and optional pagination.
    Uses generics to type-hint the data payload.

    Type Parameters:
        T: Type of the data payload

    Attributes:
        success: Always True for success responses
        data: Response payload (type T)
        metadata: Request metadata (request_id, timestamp, etc.)
        pagination: Optional pagination info for list responses
    """

    success: bool = Field(
        default=True,
        description="Whether request succeeded",
    )
    data: T = Field(
        ...,
        description="Response payload",
    )
    metadata: RequestMetadata = Field(
        ...,
        description="Request metadata",
    )
    pagination: PaginationMeta | None = Field(
        None,
        description="Pagination info (for list responses)",
    )


class ApiErrorResponse(BaseModel):
    """Error response wrapper.

    Standard error response format with error details and request metadata.
    Provides consistent error structure across all API endpoints.

    Attributes:
        success: Always False for error responses
        error: Error details (code, message, details)
        metadata: Request metadata (request_id, timestamp)
    """

    success: bool = Field(
        default=False,
        description="Whether request succeeded",
    )
    error: ApiError = Field(
        ...,
        description="Error details",
    )
    metadata: RequestMetadata = Field(
        ...,
        description="Request metadata",
    )
