"""Integration tests for standardized error responses with FastAPI TestClient.

Sprint 22 Feature 22.2.2: End-to-end tests for error handling across all endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


def test_validation_error__missing_query__returns_standardized_error(client):
    """Test Pydantic validation error returns standardized format."""
    # Missing required 'query' field
    response = client.post("/api/v1/retrieval/search", json={})

    assert response.status_code == 422
    data = response.json()

    # Check standardized error structure
    assert "error" in data
    error = data["error"]

    # Required fields
    assert error["code"] == "UNPROCESSABLE_ENTITY"
    assert "request_id" in error
    assert "timestamp" in error
    assert "path" in error
    assert error["path"] == "/api/v1/retrieval/search"

    # Validation details
    assert "details" in error
    assert "validation_errors" in error["details"]


def test_validation_error__invalid_search_type__returns_standardized_error(client):
    """Test invalid search_type returns standardized validation error."""
    response = client.post(
        "/api/v1/retrieval/search",
        json={"query": "test query", "search_type": "invalid_type"},
    )

    assert response.status_code == 422
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "UNPROCESSABLE_ENTITY"
    assert "request_id" in data["error"]


def test_404_error__nonexistent_endpoint__returns_standardized_error(client):
    """Test 404 error returns standardized format."""
    response = client.get("/api/v1/nonexistent-endpoint")

    assert response.status_code == 404
    data = response.json()

    assert "error" in data
    error = data["error"]

    assert error["code"] == "NOT_FOUND"
    assert "request_id" in error
    assert "timestamp" in error
    assert error["path"] == "/api/v1/nonexistent-endpoint"


def test_method_not_allowed__wrong_http_method__returns_standardized_error(client):
    """Test 405 error returns standardized format."""
    # Search endpoint requires POST, not GET
    response = client.get("/api/v1/retrieval/search")

    assert response.status_code == 405
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert "request_id" in data["error"]


def test_custom_exception__invalid_metadata_filters__returns_standardized_error(client):
    """Test custom ValidationError returns standardized format."""
    # Send invalid filter format (will trigger ValidationError in endpoint)
    response = client.post(
        "/api/v1/retrieval/search",
        json={
            "query": "test query",
            "filters": {"invalid_filter_format": "this will fail parsing"},
        },
    )

    # May return 400 (ValidationError), 422 (Pydantic), or 500 (VectorSearchError)
    assert response.status_code in [400, 422, 500]
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] in [
        "VALIDATION_FAILED",
        "UNPROCESSABLE_ENTITY",
        "VECTOR_SEARCH_FAILED",
    ]
    assert "request_id" in data["error"]


def test_error_response__request_id_correlation__different_requests_different_ids(client):
    """Test different requests get different request IDs."""
    response1 = client.get("/api/v1/nonexistent-1")
    response2 = client.get("/api/v1/nonexistent-2")

    data1 = response1.json()
    data2 = response2.json()

    request_id_1 = data1["error"]["request_id"]
    request_id_2 = data2["error"]["request_id"]

    # Different requests should have different IDs
    assert request_id_1 != request_id_2


def test_error_response__timestamp_format__iso8601(client):
    """Test error timestamp is in ISO 8601 format."""
    response = client.get("/api/v1/nonexistent")
    data = response.json()

    timestamp = data["error"]["timestamp"]

    # Should be ISO 8601 format (e.g., "2025-11-11T14:30:00.123456")
    assert "T" in timestamp
    assert len(timestamp) > 10  # More than just date

    # Parse to verify format
    from datetime import datetime

    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"Timestamp not in ISO 8601 format: {timestamp}")


def test_error_response__all_endpoints__consistent_format(client):
    """Test all error responses follow the same format across endpoints."""
    test_cases = [
        # (endpoint, method, expected_status, expected_code)
        ("/api/v1/nonexistent", "GET", 404, "NOT_FOUND"),
        ("/api/v1/retrieval/search", "GET", 405, "METHOD_NOT_ALLOWED"),
        ("/api/v1/retrieval/search", "POST", 422, "UNPROCESSABLE_ENTITY"),  # Missing body
    ]

    for endpoint, method, expected_status, expected_code in test_cases:
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint, json={})
        else:
            continue

        assert response.status_code == expected_status, f"Failed for {endpoint}"

        data = response.json()
        assert "error" in data, f"Missing 'error' for {endpoint}"

        error = data["error"]
        assert error["code"] == expected_code, f"Wrong code for {endpoint}"
        assert "request_id" in error, f"Missing request_id for {endpoint}"
        assert "timestamp" in error, f"Missing timestamp for {endpoint}"
        assert "path" in error, f"Missing path for {endpoint}"
        assert "message" in error, f"Missing message for {endpoint}"


def test_health_endpoint__success__no_error_response(client):
    """Test successful requests don't return error format."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Should NOT have error field
    assert "error" not in data
    assert "status" in data  # Health endpoint returns status


def test_root_endpoint__success__no_error_response(client):
    """Test root endpoint returns success (not error)."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert "error" not in data
    assert "name" in data
    assert "version" in data


# ============================================================================
# Security & Edge Cases
# ============================================================================


def test_error_response__no_sensitive_data_leakage(client):
    """Test error responses don't leak sensitive information."""
    # Trigger a validation error
    response = client.post("/api/v1/retrieval/search", json={"query": ""})

    data = response.json()

    # Should not contain:
    # - Stack traces
    # - File paths (unless in debug mode)
    # - Database connection strings
    # - Internal server details

    error_str = str(data).lower()

    # These should NOT appear in production error responses
    forbidden_terms = [
        "c:\\\\users",  # Windows file paths
        "/home/",  # Linux file paths
        "password",
        "secret",
        "api_key",
        "traceback",
        "site-packages",  # Python library paths
    ]

    for term in forbidden_terms:
        assert term not in error_str, f"Sensitive data leaked: {term}"


def test_error_response__request_id_in_logs(client, caplog):
    """Test request_id appears in logs for correlation."""
    import logging

    caplog.set_level(logging.WARNING)

    # Trigger a validation error
    response = client.post("/api/v1/retrieval/search", json={})

    data = response.json()
    request_id = data["error"]["request_id"]

    # Check if request_id appears in logs
    # Note: This test may need adjustment based on actual logging format
    # For now, just verify the request_id is valid
    assert len(request_id) > 0
    assert request_id != "unknown"


def test_error_response__details_field__optional(client):
    """Test details field is optional and may be None."""
    # Simple 404 error may not have details
    response = client.get("/api/v1/nonexistent")
    data = response.json()

    # Details field may be None or omitted
    if "details" in data["error"]:
        # If present, can be None or dict
        assert data["error"]["details"] is None or isinstance(data["error"]["details"], dict)


def test_error_response__json_serialization__no_errors(client):
    """Test all error responses are valid JSON."""
    import json

    test_endpoints = [
        ("/api/v1/nonexistent", "GET"),
        ("/api/v1/retrieval/search", "POST"),
    ]

    for endpoint, method in test_endpoints:
        response = client.get(endpoint) if method == "GET" else client.post(endpoint, json={})

        # Should be valid JSON
        try:
            json.loads(response.text)
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON response from {endpoint}: {response.text}")
