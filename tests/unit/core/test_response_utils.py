"""Unit tests for response utility functions.

Sprint 117 Feature 117.8: Response Format Standardization (3 SP)

Tests for:
- success_response()
- paginated_response()
- error_response()
- ResponseTimer context manager
- FastAPI Request integration helpers
"""

import time
from unittest.mock import Mock

import pytest

from src.core.models.response import ApiErrorResponse, ApiResponse, PaginationMeta
from src.core.response_utils import (
    ResponseTimer,
    error_response,
    error_response_from_request,
    get_request_metadata,
    paginated_response,
    paginated_response_from_request,
    success_response,
    success_response_from_request,
)


class TestSuccessResponse:
    """Tests for success_response utility."""

    def test_success_response_minimal(self):
        """Test creating success response with minimal parameters."""
        data = {"status": "ok", "name": "test_domain"}
        response = success_response(data)

        assert response.success is True
        assert response.data == data
        assert response.metadata.request_id.startswith("req_")
        assert response.metadata.api_version == "v1"
        assert response.pagination is None

    def test_success_response_with_request_id(self):
        """Test success response with explicit request_id."""
        data = {"id": "123"}
        response = success_response(data, request_id="req_custom123")

        assert response.metadata.request_id == "req_custom123"

    def test_success_response_with_processing_time(self):
        """Test success response with processing time."""
        data = {"result": "done"}
        response = success_response(data, processing_time_ms=250.5)

        assert response.metadata.processing_time_ms == 250.5

    def test_success_response_with_api_version(self):
        """Test success response with custom API version."""
        data = {"value": 42}
        response = success_response(data, api_version="v2")

        assert response.metadata.api_version == "v2"

    def test_success_response_timestamp_format(self):
        """Test success response has valid ISO 8601 timestamp."""
        response = success_response({"test": "data"})

        # Should be ISO 8601 format with Z suffix
        assert "T" in response.metadata.timestamp
        assert response.metadata.timestamp.endswith("Z")


class TestPaginatedResponse:
    """Tests for paginated_response utility."""

    def test_paginated_response_has_more(self):
        """Test paginated response when more pages available."""
        items = [{"id": i} for i in range(20)]
        response = paginated_response(items, page=1, page_size=20, total=100)

        assert response.success is True
        assert len(response.data) == 20
        assert response.pagination.page == 1
        assert response.pagination.page_size == 20
        assert response.pagination.total == 100
        assert response.pagination.has_more is True  # 1*20 < 100

    def test_paginated_response_no_more(self):
        """Test paginated response when no more pages."""
        items = [{"id": i} for i in range(20)]
        response = paginated_response(items, page=5, page_size=20, total=100)

        assert response.pagination.has_more is False  # 5*20 >= 100

    def test_paginated_response_last_partial_page(self):
        """Test paginated response with partial last page."""
        items = [{"id": i} for i in range(10)]  # Only 10 items
        response = paginated_response(items, page=5, page_size=20, total=90)

        assert len(response.data) == 10
        assert response.pagination.has_more is False  # 5*20 >= 90

    def test_paginated_response_empty_page(self):
        """Test paginated response with empty results."""
        response = paginated_response([], page=1, page_size=20, total=0)

        assert len(response.data) == 0
        assert response.pagination.total == 0
        assert response.pagination.has_more is False


class TestErrorResponse:
    """Tests for error_response utility."""

    def test_error_response_minimal(self):
        """Test creating error response with minimal parameters."""
        response = error_response(
            code="DOMAIN_NOT_FOUND",
            message="Domain 'medical' not found",
        )

        assert response.success is False
        assert response.error.code == "DOMAIN_NOT_FOUND"
        assert response.error.message == "Domain 'medical' not found"
        assert response.error.details is None
        assert response.metadata.request_id.startswith("req_")

    def test_error_response_with_details(self):
        """Test error response with additional details."""
        response = error_response(
            code="VALIDATION_ERROR",
            message="Invalid input",
            details={"field": "name", "issue": "Too short"},
        )

        assert response.error.code == "VALIDATION_ERROR"
        assert response.error.details["field"] == "name"
        assert response.error.details["issue"] == "Too short"

    def test_error_response_with_request_id(self):
        """Test error response with explicit request_id."""
        response = error_response(
            code="INTERNAL_ERROR",
            message="Something went wrong",
            request_id="req_error123",
        )

        assert response.metadata.request_id == "req_error123"

    def test_error_response_no_processing_time(self):
        """Test error response doesn't include processing time."""
        response = error_response(
            code="NOT_FOUND",
            message="Resource not found",
        )

        # Error responses shouldn't track processing time
        assert response.metadata.processing_time_ms is None


class TestResponseTimer:
    """Tests for ResponseTimer context manager."""

    def test_timer_tracks_elapsed_time(self):
        """Test timer correctly tracks elapsed time."""
        with ResponseTimer() as timer:
            time.sleep(0.1)  # Sleep 100ms

        # Allow some variance for system timing
        assert timer.elapsed_ms >= 100
        assert timer.elapsed_ms < 150

    def test_timer_generates_request_id(self):
        """Test timer auto-generates request_id."""
        with ResponseTimer() as timer:
            pass

        assert timer.request_id.startswith("req_")

    def test_timer_uses_custom_request_id(self):
        """Test timer uses provided request_id."""
        with ResponseTimer(request_id="req_custom") as timer:
            pass

        assert timer.request_id == "req_custom"

    def test_timer_success_response(self):
        """Test timer creates success response with timing."""
        with ResponseTimer(request_id="req_timer1") as timer:
            time.sleep(0.05)  # 50ms
            data = {"status": "complete"}

        response = timer.success_response(data)

        assert response.success is True
        assert response.data == data
        assert response.metadata.request_id == "req_timer1"
        assert response.metadata.processing_time_ms >= 50

    def test_timer_paginated_response(self):
        """Test timer creates paginated response with timing."""
        with ResponseTimer() as timer:
            time.sleep(0.02)  # 20ms
            items = [{"id": i} for i in range(10)]

        response = timer.paginated_response(items, page=1, page_size=10, total=100)

        assert response.success is True
        assert len(response.data) == 10
        assert response.pagination.total == 100
        assert response.metadata.processing_time_ms >= 20

    def test_timer_error_response(self):
        """Test timer creates error response with metadata."""
        with ResponseTimer(request_id="req_err") as timer:
            pass

        response = timer.error_response(
            code="VALIDATION_ERROR",
            message="Invalid input",
        )

        assert response.success is False
        assert response.error.code == "VALIDATION_ERROR"
        assert response.metadata.request_id == "req_err"

    def test_timer_not_started_raises_error(self):
        """Test accessing elapsed_ms before timer starts raises error."""
        timer = ResponseTimer()

        with pytest.raises(RuntimeError, match="Timer not started"):
            _ = timer.elapsed_ms


class TestFastAPIRequestIntegration:
    """Tests for FastAPI Request integration helpers."""

    def test_get_request_metadata(self):
        """Test extracting metadata from FastAPI Request."""
        # Mock FastAPI Request
        mock_request = Mock()
        mock_request.state.request_id = "req_fastapi123"
        mock_request.state.start_time = time.time() - 0.1  # Started 100ms ago

        request_id, processing_time = get_request_metadata(mock_request)

        assert request_id == "req_fastapi123"
        assert processing_time >= 100

    def test_get_request_metadata_no_middleware_raises(self):
        """Test get_request_metadata raises if middleware not installed."""
        mock_request = Mock()
        mock_request.state = Mock(spec=[])  # No attributes

        with pytest.raises(AttributeError, match="Request metadata not found"):
            get_request_metadata(mock_request)

    def test_success_response_from_request(self):
        """Test creating success response from FastAPI Request."""
        mock_request = Mock()
        mock_request.state.request_id = "req_api1"
        mock_request.state.start_time = time.time() - 0.05

        data = {"domain": "tech_docs"}
        response = success_response_from_request(data, mock_request)

        assert response.success is True
        assert response.data == data
        assert response.metadata.request_id == "req_api1"
        assert response.metadata.processing_time_ms >= 50

    def test_paginated_response_from_request(self):
        """Test creating paginated response from FastAPI Request."""
        mock_request = Mock()
        mock_request.state.request_id = "req_paginated"
        mock_request.state.start_time = time.time() - 0.02

        items = [{"id": 1}, {"id": 2}]
        response = paginated_response_from_request(
            items,
            page=1,
            page_size=20,
            total=100,
            request=mock_request,
        )

        assert response.success is True
        assert len(response.data) == 2
        assert response.pagination.has_more is True
        assert response.metadata.request_id == "req_paginated"

    def test_error_response_from_request(self):
        """Test creating error response from FastAPI Request."""
        mock_request = Mock()
        mock_request.state.request_id = "req_error_api"

        response = error_response_from_request(
            code="DOMAIN_NOT_FOUND",
            message="Not found",
            request=mock_request,
        )

        assert response.success is False
        assert response.error.code == "DOMAIN_NOT_FOUND"
        assert response.metadata.request_id == "req_error_api"


class TestResponseUtilsIntegration:
    """Integration tests for response utilities."""

    def test_full_request_lifecycle(self):
        """Test complete request lifecycle with timer."""
        # Simulate request processing
        with ResponseTimer(request_id="req_lifecycle") as timer:
            # Simulate some work
            time.sleep(0.05)

            # Simulate retrieving data
            domains = [
                {"id": "1", "name": "tech"},
                {"id": "2", "name": "legal"},
            ]

        # Create paginated response
        response = timer.paginated_response(
            items=domains,
            page=1,
            page_size=20,
            total=50,
        )

        # Verify complete response structure
        assert response.success is True
        assert len(response.data) == 2
        assert response.metadata.request_id == "req_lifecycle"
        assert response.metadata.processing_time_ms >= 50
        assert response.pagination.total == 50
        assert response.pagination.has_more is True

    def test_error_handling_with_timer(self):
        """Test error handling within timer context."""
        try:
            with ResponseTimer(request_id="req_err_flow") as timer:
                # Simulate error condition
                raise ValueError("Domain not found")
        except ValueError:
            # Create error response
            response = timer.error_response(
                code="DOMAIN_NOT_FOUND",
                message="Domain 'medical' not found",
                details={"domain": "medical"},
            )

        assert response.success is False
        assert response.error.code == "DOMAIN_NOT_FOUND"
        assert response.error.details["domain"] == "medical"
        assert response.metadata.request_id == "req_err_flow"
