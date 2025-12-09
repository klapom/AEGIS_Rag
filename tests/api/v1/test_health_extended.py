"""Extended Unit Tests for Health Check Endpoints - Coverage Improvement.

Tests health check models and helper logic.

Author: Claude Code
Date: 2025-10-27
"""

import pytest

from src.api.v1.health import DependencyHealth, DetailedHealthResponse, HealthStatus

# ============================================================================
# HealthStatus Model Tests
# ============================================================================


@pytest.mark.unit
def test_health_status_creation_valid():
    """Test HealthStatus creation with valid data."""
    status = HealthStatus(
        status="healthy",
        version="1.0.0",
        environment="production",
    )

    assert status.status == "healthy"
    assert status.version == "1.0.0"
    assert status.environment == "production"


@pytest.mark.unit
def test_health_status_serialization():
    """Test HealthStatus serialization to dict."""
    status = HealthStatus(
        status="degraded",
        version="2.5.1",
        environment="staging",
    )

    data = status.model_dump()

    assert data["status"] == "degraded"
    assert data["version"] == "2.5.1"
    assert data["environment"] == "staging"


@pytest.mark.unit
def test_health_status_different_status_values():
    """Test HealthStatus with different status values."""
    statuses = ["healthy", "degraded", "unhealthy"]

    for status_value in statuses:
        status = HealthStatus(
            status=status_value,
            version="1.0.0",
            environment="test",
        )
        assert status.status == status_value


# ============================================================================
# DependencyHealth Model Tests
# ============================================================================


@pytest.mark.unit
def test_dependency_health_creation_valid():
    """Test DependencyHealth creation with valid data."""
    dep = DependencyHealth(
        name="Qdrant Vector Database",
        status="up",
        latency_ms=25.5,
        details={"host": "localhost", "port": 6333},
    )

    assert dep.name == "Qdrant Vector Database"
    assert dep.status == "up"
    assert dep.latency_ms == 25.5
    assert dep.details["host"] == "localhost"


@pytest.mark.unit
def test_dependency_health_status_down():
    """Test DependencyHealth with down status."""
    dep = DependencyHealth(
        name="Ollama Service",
        status="down",
        latency_ms=0.0,
        details={"error": "Connection refused"},
    )

    assert dep.status == "down"
    assert dep.latency_ms == 0.0
    assert dep.details["error"] == "Connection refused"


@pytest.mark.unit
def test_dependency_health_degraded_status():
    """Test DependencyHealth with degraded status."""
    dep = DependencyHealth(
        name="Neo4j Database",
        status="degraded",
        latency_ms=150.2,
        details={"warning": "High latency detected"},
    )

    assert dep.status == "degraded"
    assert dep.latency_ms == 150.2


@pytest.mark.unit
def test_dependency_health_serialization():
    """Test DependencyHealth serialization."""
    dep = DependencyHealth(
        name="Test Service",
        status="up",
        latency_ms=10.5,
        details={"key": "value"},
    )

    data = dep.model_dump()

    assert data["name"] == "Test Service"
    assert data["status"] == "up"
    assert data["latency_ms"] == 10.5
    assert data["details"] == {"key": "value"}


@pytest.mark.unit
def test_dependency_health_empty_details():
    """Test DependencyHealth with empty details."""
    dep = DependencyHealth(
        name="Service",
        status="up",
        latency_ms=5.0,
        details={},
    )

    assert dep.details == {}


# ============================================================================
# DetailedHealthResponse Model Tests
# ============================================================================


@pytest.mark.unit
def test_detailed_health_response_creation():
    """Test DetailedHealthResponse creation with dependencies."""
    qdrant_dep = DependencyHealth(
        name="Qdrant",
        status="up",
        latency_ms=20.0,
        details={"collections": 5},
    )

    ollama_dep = DependencyHealth(
        name="Ollama",
        status="up",
        latency_ms=15.0,
        details={"model": "nomic-embed-text"},
    )

    response = DetailedHealthResponse(
        status="healthy",
        version="1.0.0",
        environment="production",
        dependencies={
            "qdrant": qdrant_dep,
            "ollama": ollama_dep,
        },
    )

    assert response.status == "healthy"
    assert len(response.dependencies) == 2
    assert response.dependencies["qdrant"].name == "Qdrant"
    assert response.dependencies["ollama"].name == "Ollama"


@pytest.mark.unit
def test_detailed_health_response_degraded_status():
    """Test DetailedHealthResponse with degraded status."""
    qdrant_dep = DependencyHealth(
        name="Qdrant",
        status="up",
        latency_ms=20.0,
        details={},
    )

    ollama_dep = DependencyHealth(
        name="Ollama",
        status="down",
        latency_ms=0.0,
        details={"error": "Service unavailable"},
    )

    response = DetailedHealthResponse(
        status="degraded",
        version="1.0.0",
        environment="production",
        dependencies={
            "qdrant": qdrant_dep,
            "ollama": ollama_dep,
        },
    )

    assert response.status == "degraded"
    assert response.dependencies["qdrant"].status == "up"
    assert response.dependencies["ollama"].status == "down"


@pytest.mark.unit
def test_detailed_health_response_unhealthy_status():
    """Test DetailedHealthResponse with unhealthy status."""
    qdrant_dep = DependencyHealth(
        name="Qdrant",
        status="down",
        latency_ms=0.0,
        details={"error": "Connection failed"},
    )

    response = DetailedHealthResponse(
        status="unhealthy",
        version="1.0.0",
        environment="production",
        dependencies={"qdrant": qdrant_dep},
    )

    assert response.status == "unhealthy"
    assert response.dependencies["qdrant"].status == "down"


@pytest.mark.unit
def test_detailed_health_response_empty_dependencies():
    """Test DetailedHealthResponse with no dependencies."""
    response = DetailedHealthResponse(
        status="healthy",
        version="1.0.0",
        environment="test",
        dependencies={},
    )

    assert response.dependencies == {}


@pytest.mark.unit
def test_detailed_health_response_serialization():
    """Test DetailedHealthResponse serialization."""
    dep = DependencyHealth(
        name="Test",
        status="up",
        latency_ms=10.0,
        details={"key": "value"},
    )

    response = DetailedHealthResponse(
        status="healthy",
        version="1.5.0",
        environment="staging",
        dependencies={"test": dep},
    )

    data = response.model_dump()

    assert data["status"] == "healthy"
    assert data["version"] == "1.5.0"
    assert data["environment"] == "staging"
    assert "test" in data["dependencies"]
    assert data["dependencies"]["test"]["name"] == "Test"


@pytest.mark.unit
def test_detailed_health_response_multiple_dependencies():
    """Test DetailedHealthResponse with multiple dependencies."""
    deps = {
        f"service_{i}": DependencyHealth(
            name=f"Service {i}",
            status="up" if i % 2 == 0 else "down",
            latency_ms=float(i * 10),
            details={},
        )
        for i in range(5)
    }

    response = DetailedHealthResponse(
        status="degraded",
        version="2.0.0",
        environment="production",
        dependencies=deps,
    )

    assert len(response.dependencies) == 5
    assert response.dependencies["service_0"].status == "up"
    assert response.dependencies["service_1"].status == "down"
