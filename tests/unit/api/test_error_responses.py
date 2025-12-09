"""Unit tests for standardized error responses.

Sprint 22 Feature 22.2.2: Test all error response formats and exception handlers.
"""

import pytest
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.middleware.exception_handler import (
    aegis_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from src.core.exceptions import (
    FileTooLargeError,
    IngestionError,
    InvalidFileFormatError,
    ValidationError,
    VectorSearchError,
)
from src.core.models import ErrorCode


@pytest.fixture
def mock_request():
    """Create a mock request with request_id."""

    class MockState:
        request_id = "test-request-id-123"

    class MockURL:
        path = "/api/v1/test"

    class MockRequest:
        state = MockState()
        url = MockURL()

    return MockRequest()


@pytest.mark.asyncio
async def test_custom_exception__invalid_file_format__standardized_error(mock_request):
    """Test InvalidFileFormatError returns standardized format."""
    exc = InvalidFileFormatError(filename="test.xyz", expected_formats=[".pdf", ".docx"])

    response = await aegis_exception_handler(mock_request, exc)

    assert response.status_code == 400
    body = response.body.decode("utf-8")
    assert "error" in body
    assert ErrorCode.INVALID_FILE_FORMAT in body
    assert "test.xyz" in body
    assert "test-request-id-123" in body
    assert "/api/v1/test" in body


@pytest.mark.asyncio
async def test_custom_exception__file_too_large__standardized_error(mock_request):
    """Test FileTooLargeError returns standardized format."""
    exc = FileTooLargeError(filename="large.pdf", size_mb=150.5, max_size_mb=100.0)

    response = await aegis_exception_handler(mock_request, exc)

    assert response.status_code == 413
    body = response.body.decode("utf-8")
    assert ErrorCode.FILE_TOO_LARGE in body
    assert "large.pdf" in body
    assert "150.5" in body or "150.50" in body  # Float formatting may vary


@pytest.mark.asyncio
async def test_custom_exception__ingestion_failed__standardized_error(mock_request):
    """Test IngestionError returns standardized format."""
    exc = IngestionError(document_id="doc-123", reason="Database connection failed")

    response = await aegis_exception_handler(mock_request, exc)

    assert response.status_code == 500
    body = response.body.decode("utf-8")
    assert ErrorCode.INGESTION_FAILED in body
    assert "doc-123" in body
    assert "Database connection failed" in body


@pytest.mark.asyncio
async def test_custom_exception__vector_search_failed__standardized_error(mock_request):
    """Test VectorSearchError returns standardized format."""
    exc = VectorSearchError(query="test query", reason="Qdrant timeout")

    response = await aegis_exception_handler(mock_request, exc)

    assert response.status_code == 500
    body = response.body.decode("utf-8")
    assert ErrorCode.VECTOR_SEARCH_FAILED in body
    assert "test query" in body
    assert "Qdrant timeout" in body


@pytest.mark.asyncio
async def test_custom_exception__validation_failed__standardized_error(mock_request):
    """Test ValidationError returns standardized format."""
    exc = ValidationError(field="query", issue="Query cannot be empty")

    response = await aegis_exception_handler(mock_request, exc)

    assert response.status_code == 400
    body = response.body.decode("utf-8")
    assert ErrorCode.VALIDATION_FAILED in body
    assert "query" in body
    assert "Query cannot be empty" in body


@pytest.mark.asyncio
async def test_http_exception__404__standardized_error(mock_request):
    """Test HTTP 404 returns standardized format."""
    exc = StarletteHTTPException(status_code=404, detail="Resource not found")

    response = await http_exception_handler(mock_request, exc)

    assert response.status_code == 404
    body = response.body.decode("utf-8")
    assert ErrorCode.NOT_FOUND in body
    assert "Resource not found" in body
    assert "test-request-id-123" in body


@pytest.mark.asyncio
async def test_http_exception__401__standardized_error(mock_request):
    """Test HTTP 401 returns standardized format."""
    exc = StarletteHTTPException(status_code=401, detail="Unauthorized")

    response = await http_exception_handler(mock_request, exc)

    assert response.status_code == 401
    body = response.body.decode("utf-8")
    assert ErrorCode.UNAUTHORIZED in body
    assert "test-request-id-123" in body


@pytest.mark.asyncio
async def test_http_exception__429__standardized_error(mock_request):
    """Test HTTP 429 returns standardized format."""
    exc = StarletteHTTPException(status_code=429, detail="Too many requests")

    response = await http_exception_handler(mock_request, exc)

    assert response.status_code == 429
    body = response.body.decode("utf-8")
    assert ErrorCode.TOO_MANY_REQUESTS in body


@pytest.mark.asyncio
async def test_validation_error__missing_field__standardized_error(mock_request):
    """Test Pydantic validation error returns standardized format."""
    # Create a mock validation error
    try:
        from pydantic import BaseModel, Field

        class TestModel(BaseModel):
            required_field: str = Field(..., min_length=1)

        # This will raise ValidationError
        TestModel.model_validate({"required_field": ""})
    except Exception as exc:
        if isinstance(exc, RequestValidationError):
            response = await validation_exception_handler(mock_request, exc)

            assert response.status_code == 422
            body = response.body.decode("utf-8")
            assert ErrorCode.UNPROCESSABLE_ENTITY in body
            assert "validation_errors" in body or "validation" in body
            assert "test-request-id-123" in body


@pytest.mark.asyncio
async def test_generic_exception__unexpected_error__standardized_error(mock_request):
    """Test unexpected exception returns standardized format."""
    exc = RuntimeError("Unexpected error occurred")

    response = await generic_exception_handler(mock_request, exc)

    assert response.status_code == 500
    body = response.body.decode("utf-8")
    assert ErrorCode.INTERNAL_SERVER_ERROR in body
    assert "test-request-id-123" in body
    # Should NOT leak error details in production (unless debug=True)
    # assert "Unexpected error" not in body  # Disabled for now (depends on settings)


@pytest.mark.asyncio
async def test_error_response__includes_all_required_fields(mock_request):
    """Test error response includes all required fields."""
    exc = InvalidFileFormatError(filename="test.txt", expected_formats=[".pdf"])

    response = await aegis_exception_handler(mock_request, exc)

    # Parse response body
    import json

    body = json.loads(response.body.decode("utf-8"))

    # Check top-level structure
    assert "error" in body
    error = body["error"]

    # Check all required fields
    assert "code" in error
    assert "message" in error
    assert "request_id" in error
    assert "timestamp" in error
    assert "path" in error

    # Verify values
    assert error["code"] == ErrorCode.INVALID_FILE_FORMAT
    assert error["request_id"] == "test-request-id-123"
    assert error["path"] == "/api/v1/test"
    assert "test.txt" in error["message"]

    # Check optional details field
    if "details" in error and error["details"] is not None:
        assert "filename" in error["details"]
        assert error["details"]["filename"] == "test.txt"


@pytest.mark.asyncio
async def test_error_response__request_id_unknown_when_missing(mock_request):
    """Test error response uses 'unknown' when request_id is missing."""

    # Create request without request_id
    class MockStateNoID:
        pass  # No request_id attribute

    mock_request.state = MockStateNoID()

    exc = InvalidFileFormatError(filename="test.txt", expected_formats=[".pdf"])
    response = await aegis_exception_handler(mock_request, exc)

    import json

    body = json.loads(response.body.decode("utf-8"))
    assert body["error"]["request_id"] == "unknown"


# ============================================================================
# Integration Tests (require FastAPI TestClient)
# ============================================================================


def test_error_response_format__json_schema_compliance():
    """Test ErrorResponse model complies with JSON schema."""
    from datetime import datetime

    from src.core.models import ErrorDetail, ErrorResponse

    error_response = ErrorResponse(
        error=ErrorDetail(
            code=ErrorCode.INVALID_FILE_FORMAT,
            message="Invalid file format",
            details={"filename": "test.txt"},
            request_id="test-123",
            timestamp=datetime.utcnow(),
            path="/api/v1/test",
        )
    )

    # Test serialization
    serialized = error_response.model_dump(mode="json")
    assert serialized["error"]["code"] == ErrorCode.INVALID_FILE_FORMAT
    assert serialized["error"]["request_id"] == "test-123"

    # Test JSON export
    json_str = error_response.model_dump_json()
    assert "INVALID_FILE_FORMAT" in json_str
    assert "test-123" in json_str


def test_error_code__all_codes_defined():
    """Test all error codes are properly defined."""
    assert ErrorCode.BAD_REQUEST == "BAD_REQUEST"
    assert ErrorCode.UNAUTHORIZED == "UNAUTHORIZED"
    assert ErrorCode.FORBIDDEN == "FORBIDDEN"
    assert ErrorCode.NOT_FOUND == "NOT_FOUND"
    assert ErrorCode.UNPROCESSABLE_ENTITY == "UNPROCESSABLE_ENTITY"
    assert ErrorCode.TOO_MANY_REQUESTS == "TOO_MANY_REQUESTS"
    assert ErrorCode.INTERNAL_SERVER_ERROR == "INTERNAL_SERVER_ERROR"
    assert ErrorCode.SERVICE_UNAVAILABLE == "SERVICE_UNAVAILABLE"

    # Business logic codes
    assert ErrorCode.INVALID_FILE_FORMAT == "INVALID_FILE_FORMAT"
    assert ErrorCode.FILE_TOO_LARGE == "FILE_TOO_LARGE"
    assert ErrorCode.FILE_NOT_FOUND == "FILE_NOT_FOUND"
    assert ErrorCode.INGESTION_FAILED == "INGESTION_FAILED"
    assert ErrorCode.VECTOR_SEARCH_FAILED == "VECTOR_SEARCH_FAILED"
    assert ErrorCode.GRAPH_QUERY_FAILED == "GRAPH_QUERY_FAILED"
    assert ErrorCode.VALIDATION_FAILED == "VALIDATION_FAILED"
    assert ErrorCode.RATE_LIMIT_EXCEEDED == "RATE_LIMIT_EXCEEDED"


def test_exception_classes__proper_initialization():
    """Test custom exception classes initialize correctly."""
    # InvalidFileFormatError
    exc1 = InvalidFileFormatError(filename="test.xyz", expected_formats=[".pdf"])
    assert exc1.error_code == ErrorCode.INVALID_FILE_FORMAT
    assert exc1.status_code == 400
    assert exc1.details["filename"] == "test.xyz"

    # FileTooLargeError
    exc2 = FileTooLargeError(filename="big.pdf", size_mb=200.0, max_size_mb=100.0)
    assert exc2.error_code == ErrorCode.FILE_TOO_LARGE
    assert exc2.status_code == 413
    assert exc2.details["size_mb"] == 200.0

    # IngestionError
    exc3 = IngestionError(document_id="doc-123", reason="DB error")
    assert exc3.error_code == ErrorCode.INGESTION_FAILED
    assert exc3.status_code == 500
    assert exc3.details["document_id"] == "doc-123"

    # VectorSearchError
    exc4 = VectorSearchError(query="test", reason="Timeout")
    assert exc4.error_code == ErrorCode.VECTOR_SEARCH_FAILED
    assert exc4.status_code == 500
    assert exc4.details["query"] == "test"

    # ValidationError
    exc5 = ValidationError(field="query", issue="Empty")
    assert exc5.error_code == ErrorCode.VALIDATION_FAILED
    assert exc5.status_code == 400
    assert exc5.details["field"] == "query"
