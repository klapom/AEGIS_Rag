"""Unit tests for health check endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient


def test_health_endpoint(test_client: TestClient):
    """Test the main health check endpoint."""
    response = test_client.get("/api/v1/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert data["status"] == "healthy"


def test_liveness_probe(test_client: TestClient):
    """Test the liveness probe endpoint."""
    response = test_client.get("/api/v1/health/live")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["status"] == "alive"


@patch("src.api.v1.health.QdrantClientWrapper")
def test_readiness_probe(mock_qdrant_class, test_client: TestClient):
    """Test the readiness probe endpoint."""
    # Mock Qdrant client to return successfully
    mock_qdrant = AsyncMock()
    mock_qdrant.list_collections = AsyncMock(return_value=[])
    mock_qdrant_class.return_value = mock_qdrant

    response = test_client.get("/api/v1/health/ready")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "status" in data
    assert data["status"] == "ready"


def test_root_endpoint(test_client: TestClient):
    """Test the root endpoint."""
    response = test_client.get("/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["name"] == "aegis-rag"
    assert "version" in data
    assert data["status"] == "operational"
    assert data["docs"] == "/docs"
