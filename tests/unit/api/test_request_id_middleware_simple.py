"""Simplified unit tests for Request ID Tracking Middleware.

Sprint Context: Sprint 22 (2025-11-11) - Feature 22.2: API Security Hardening
Task: 22.2.1 - Implement Request ID Tracking Middleware

This module contains simplified tests to verify the core functionality works.
"""

import uuid

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies import get_request_id
from src.api.middleware.request_id import RequestIDMiddleware


def test_request_id_generated__no_header__creates_uuid():
    """
    Verify middleware generates UUID when no X-Request-ID header is present.
    """
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test")

    # Verify response has X-Request-ID header
    assert "X-Request-ID" in response.headers

    # Verify it's a valid UUID format
    request_id = response.headers["X-Request-ID"]
    uuid_obj = uuid.UUID(request_id)
    assert uuid_obj.version == 4
    assert len(request_id) == 36


def test_request_id_passthrough__existing_header__reuses_id():
    """
    Verify middleware reuses existing X-Request-ID header.
    """
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app, raise_server_exceptions=False)
    custom_id = "custom-request-id-123"
    response = client.get("/test", headers={"X-Request-ID": custom_id})

    # Verify the same ID is returned
    assert response.headers["X-Request-ID"] == custom_id


def test_request_id_in_state__accessible_via_dependency():
    """
    Verify request ID is accessible via get_request_id dependency.
    """
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/test")
    def test_endpoint(request_id: str = Depends(get_request_id)):
        return {"status": "ok", "request_id": request_id}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test")

    # Verify response contains request_id from dependency
    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data

    # Verify request_id in body matches header
    assert response.headers["X-Request-ID"] == data["request_id"]


def test_request_id_uniqueness__multiple_requests__different_ids():
    """
    Verify each request gets a unique ID.
    """
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app, raise_server_exceptions=False)
    request_ids = set()

    for _ in range(10):
        response = client.get("/test")
        request_id = response.headers["X-Request-ID"]
        request_ids.add(request_id)

    # All IDs should be unique
    assert len(request_ids) == 10
