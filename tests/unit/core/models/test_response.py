"""Unit tests for standardized API response models.

Sprint 117 Feature 117.8: Response Format Standardization (3 SP)

Tests for:
- ApiResponse (success response wrapper)
- ApiErrorResponse (error response wrapper)
- RequestMetadata
- PaginationMeta
- ApiError
"""

import pytest
from datetime import datetime

from src.core.models.response import (
    ApiError,
    ApiErrorResponse,
    ApiResponse,
    PaginationMeta,
    RequestMetadata,
)


class TestRequestMetadata:
    """Tests for RequestMetadata model."""

    def test_create_minimal_metadata(self):
        """Test creating metadata with minimal required fields."""
        metadata = RequestMetadata(
            request_id="req_abc123",
            timestamp="2026-01-20T16:00:00Z",
        )

        assert metadata.request_id == "req_abc123"
        assert metadata.timestamp == "2026-01-20T16:00:00Z"
        assert metadata.processing_time_ms is None
        assert metadata.api_version == "v1"  # default

    def test_create_full_metadata(self):
        """Test creating metadata with all fields."""
        metadata = RequestMetadata(
            request_id="req_xyz789",
            timestamp="2026-01-20T16:00:00Z",
            processing_time_ms=342.5,
            api_version="v2",
        )

        assert metadata.request_id == "req_xyz789"
        assert metadata.timestamp == "2026-01-20T16:00:00Z"
        assert metadata.processing_time_ms == 342.5
        assert metadata.api_version == "v2"

    def test_metadata_serialization(self):
        """Test metadata can be serialized to dict."""
        metadata = RequestMetadata(
            request_id="req_test",
            timestamp="2026-01-20T16:00:00Z",
            processing_time_ms=100.0,
        )

        data = metadata.model_dump()
        assert data["request_id"] == "req_test"
        assert data["timestamp"] == "2026-01-20T16:00:00Z"
        assert data["processing_time_ms"] == 100.0
        assert data["api_version"] == "v1"


class TestPaginationMeta:
    """Tests for PaginationMeta model."""

    def test_create_pagination(self):
        """Test creating pagination metadata."""
        pagination = PaginationMeta(
            page=1,
            page_size=20,
            total=100,
            has_more=True,
        )

        assert pagination.page == 1
        assert pagination.page_size == 20
        assert pagination.total == 100
        assert pagination.has_more is True

    def test_pagination_no_more_pages(self):
        """Test pagination when no more pages available."""
        pagination = PaginationMeta(
            page=5,
            page_size=20,
            total=100,
            has_more=False,
        )

        assert pagination.has_more is False

    def test_pagination_validation_page_gte_1(self):
        """Test page number must be >= 1."""
        with pytest.raises(ValueError):
            PaginationMeta(
                page=0,  # Invalid
                page_size=20,
                total=100,
                has_more=True,
            )

    def test_pagination_validation_page_size_range(self):
        """Test page_size must be between 1 and 100."""
        with pytest.raises(ValueError):
            PaginationMeta(
                page=1,
                page_size=0,  # Invalid
                total=100,
                has_more=True,
            )

        with pytest.raises(ValueError):
            PaginationMeta(
                page=1,
                page_size=101,  # Invalid (>100)
                total=100,
                has_more=True,
            )


class TestApiError:
    """Tests for ApiError model."""

    def test_create_minimal_error(self):
        """Test creating error with minimal fields."""
        error = ApiError(
            code="DOMAIN_NOT_FOUND",
            message="Domain 'medical' not found",
        )

        assert error.code == "DOMAIN_NOT_FOUND"
        assert error.message == "Domain 'medical' not found"
        assert error.details is None

    def test_create_error_with_details(self):
        """Test creating error with additional details."""
        error = ApiError(
            code="VALIDATION_ERROR",
            message="Validation failed for field 'name'",
            details={"field": "name", "issue": "Must be 3-50 characters"},
        )

        assert error.code == "VALIDATION_ERROR"
        assert error.details == {"field": "name", "issue": "Must be 3-50 characters"}


class TestApiResponse:
    """Tests for ApiResponse model."""

    def test_create_success_response_simple(self):
        """Test creating success response with simple data."""
        metadata = RequestMetadata(
            request_id="req_123",
            timestamp="2026-01-20T16:00:00Z",
            processing_time_ms=100.0,
        )

        response = ApiResponse(
            success=True,
            data={"status": "ok"},
            metadata=metadata,
        )

        assert response.success is True
        assert response.data == {"status": "ok"}
        assert response.metadata.request_id == "req_123"
        assert response.pagination is None

    def test_create_success_response_with_list(self):
        """Test creating success response with list data."""
        metadata = RequestMetadata(
            request_id="req_456",
            timestamp="2026-01-20T16:00:00Z",
        )

        domains = [
            {"id": "1", "name": "tech_docs"},
            {"id": "2", "name": "legal"},
        ]

        response = ApiResponse(
            data=domains,
            metadata=metadata,
        )

        assert response.success is True  # default
        assert len(response.data) == 2
        assert response.data[0]["name"] == "tech_docs"

    def test_create_paginated_response(self):
        """Test creating response with pagination."""
        metadata = RequestMetadata(
            request_id="req_789",
            timestamp="2026-01-20T16:00:00Z",
            processing_time_ms=250.0,
        )

        pagination = PaginationMeta(
            page=1,
            page_size=20,
            total=100,
            has_more=True,
        )

        response = ApiResponse(
            data=[{"id": i} for i in range(20)],
            metadata=metadata,
            pagination=pagination,
        )

        assert response.success is True
        assert len(response.data) == 20
        assert response.pagination.page == 1
        assert response.pagination.has_more is True

    def test_response_serialization(self):
        """Test response can be serialized to dict."""
        metadata = RequestMetadata(
            request_id="req_test",
            timestamp="2026-01-20T16:00:00Z",
            processing_time_ms=50.0,
        )

        response = ApiResponse(
            data={"name": "test_domain"},
            metadata=metadata,
        )

        data = response.model_dump()
        assert data["success"] is True
        assert data["data"]["name"] == "test_domain"
        assert data["metadata"]["request_id"] == "req_test"
        assert data["pagination"] is None


class TestApiErrorResponse:
    """Tests for ApiErrorResponse model."""

    def test_create_error_response(self):
        """Test creating error response."""
        metadata = RequestMetadata(
            request_id="req_error",
            timestamp="2026-01-20T16:00:00Z",
        )

        error = ApiError(
            code="DOMAIN_NOT_FOUND",
            message="Domain 'medical' not found",
            details={"domain_name": "medical"},
        )

        response = ApiErrorResponse(
            success=False,
            error=error,
            metadata=metadata,
        )

        assert response.success is False
        assert response.error.code == "DOMAIN_NOT_FOUND"
        assert response.error.message == "Domain 'medical' not found"
        assert response.error.details["domain_name"] == "medical"
        assert response.metadata.request_id == "req_error"

    def test_error_response_serialization(self):
        """Test error response can be serialized to dict."""
        metadata = RequestMetadata(
            request_id="req_err_123",
            timestamp="2026-01-20T16:00:00Z",
        )

        error = ApiError(
            code="VALIDATION_ERROR",
            message="Invalid input",
        )

        response = ApiErrorResponse(
            error=error,
            metadata=metadata,
        )

        data = response.model_dump()
        assert data["success"] is False  # default
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert data["error"]["message"] == "Invalid input"
        assert data["metadata"]["request_id"] == "req_err_123"


class TestResponseIntegration:
    """Integration tests for response models."""

    def test_full_success_response_structure(self):
        """Test complete success response structure matches spec."""
        metadata = RequestMetadata(
            request_id="req_abc123",
            timestamp="2026-01-20T16:00:00Z",
            processing_time_ms=342.0,
            api_version="v1",
        )

        pagination = PaginationMeta(
            page=1,
            page_size=20,
            total=100,
            has_more=True,
        )

        response = ApiResponse(
            success=True,
            data={"status": "ok"},
            metadata=metadata,
            pagination=pagination,
        )

        data = response.model_dump()

        # Verify structure matches spec
        assert "success" in data
        assert "data" in data
        assert "metadata" in data
        assert "pagination" in data

        assert data["success"] is True
        assert data["metadata"]["request_id"] == "req_abc123"
        assert data["metadata"]["timestamp"] == "2026-01-20T16:00:00Z"
        assert data["metadata"]["processing_time_ms"] == 342.0
        assert data["metadata"]["api_version"] == "v1"

        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 20
        assert data["pagination"]["total"] == 100
        assert data["pagination"]["has_more"] is True

    def test_full_error_response_structure(self):
        """Test complete error response structure matches spec."""
        metadata = RequestMetadata(
            request_id="req_xyz789",
            timestamp="2026-01-20T16:00:00Z",
            api_version="v1",
        )

        error = ApiError(
            code="DOMAIN_NOT_FOUND",
            message="Domain 'medical' not found",
            details={
                "domain_name": "medical",
                "suggestion": "Available domains: general, finance",
            },
        )

        response = ApiErrorResponse(
            success=False,
            error=error,
            metadata=metadata,
        )

        data = response.model_dump()

        # Verify structure matches spec
        assert "success" in data
        assert "error" in data
        assert "metadata" in data

        assert data["success"] is False
        assert data["error"]["code"] == "DOMAIN_NOT_FOUND"
        assert data["error"]["message"] == "Domain 'medical' not found"
        assert data["error"]["details"]["domain_name"] == "medical"

        assert data["metadata"]["request_id"] == "req_xyz789"
        assert data["metadata"]["timestamp"] == "2026-01-20T16:00:00Z"
        assert data["metadata"]["api_version"] == "v1"
