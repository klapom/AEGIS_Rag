"""Unit tests for health check endpoints."""

from fastapi import status
from fastapi.testclient import TestClient


def test_health_endpoint(test_client: TestClient):
    """Test the main health check endpoint."""
    response = test_client.get("/api/v1/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "status" in data
    assert "version" in data
    assert "timestamp" in data
    assert "services" in data


def test_liveness_probe(test_client: TestClient):
    """Test the liveness probe endpoint."""
    response = test_client.get("/api/v1/health/live")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["status"] == "alive"


def test_readiness_probe(test_client: TestClient):
    """Test the readiness probe endpoint."""
    response = test_client.get("/api/v1/health/ready")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "status" in data


def test_root_endpoint(test_client: TestClient):
    """Test the root endpoint."""
    response = test_client.get("/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["name"] == "aegis-rag"
    assert "version" in data
    assert data["status"] == "operational"
    assert data["docs"] == "/docs"
