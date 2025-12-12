"""Shared fixtures for API integration tests.

Sprint 45 - Domain Training API Integration Tests

Provides reusable fixtures for:
- FastAPI test client
- Mock domain components
- Sample data (domains, training logs, samples)
- Common test utilities
"""

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


@pytest.fixture
def api_base_url() -> str:
    """Base URL for API tests."""
    return "http://localhost:8000/api/v1"


@pytest.fixture
def sample_domain_data() -> dict[str, Any]:
    """Complete sample domain object with all fields."""
    return {
        "id": str(uuid4()),
        "name": "tech_docs",
        "description": "Technical documentation for APIs and software libraries",
        "status": "ready",
        "llm_model": "qwen3:32b",
        "entity_prompt": "Extract technical entities like classes, functions, APIs",
        "relation_prompt": "Extract relationships between technical components",
        "entity_examples": json.dumps([
            {"text": "FastAPI", "label": "API_Framework"},
            {"text": "Pydantic", "label": "Validation_Library"},
            {"text": "Qdrant", "label": "Vector_Database"}
        ]),
        "relation_examples": json.dumps([
            {"head": "FastAPI", "relation": "BUILT_WITH", "tail": "Pydantic"},
            {"head": "FastAPI", "relation": "USES", "tail": "Qdrant"}
        ]),
        "training_samples": 50,
        "training_metrics": json.dumps({
            "entity_f1": 0.89,
            "entity_precision": 0.91,
            "entity_recall": 0.87,
            "relation_f1": 0.82,
            "relation_precision": 0.85,
            "relation_recall": 0.79,
            "extraction_accuracy": 0.91
        }),
        "created_at": datetime.now(UTC).isoformat(),
        "trained_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat()
    }


@pytest.fixture
def sample_general_domain() -> dict[str, Any]:
    """Sample 'general' default domain."""
    return {
        "id": str(uuid4()),
        "name": "general",
        "description": "General-purpose domain for documents that don't match specialized domains",
        "status": "ready",
        "llm_model": "llama3.2:8b",
        "entity_prompt": "Extract general named entities",
        "relation_prompt": "Extract general relationships",
        "entity_examples": json.dumps([]),
        "relation_examples": json.dumps([]),
        "training_samples": 0,
        "training_metrics": json.dumps({}),
        "created_at": datetime.now(UTC).isoformat(),
        "trained_at": None,
        "updated_at": datetime.now(UTC).isoformat()
    }


@pytest.fixture
def sample_training_log() -> dict[str, Any]:
    """Sample completed training log."""
    return {
        "id": str(uuid4()),
        "domain_id": str(uuid4()),
        "status": "completed",
        "started_at": datetime.now(UTC).isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "progress_percent": 100.0,
        "current_step": "Validation complete",
        "log_messages": json.dumps([
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": "INFO",
                "message": "Training started"
            },
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": "INFO",
                "message": "Entity extraction optimization in progress..."
            },
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": "INFO",
                "message": "Relation extraction optimization in progress..."
            },
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": "INFO",
                "message": "Training completed with F1=0.89"
            }
        ]),
        "metrics": json.dumps({
            "entity_f1": 0.89,
            "relation_f1": 0.82,
            "extraction_accuracy": 0.91
        }),
        "error_message": None
    }


@pytest.fixture
def sample_training_log_failed() -> dict[str, Any]:
    """Sample failed training log."""
    return {
        "id": str(uuid4()),
        "domain_id": str(uuid4()),
        "status": "failed",
        "started_at": datetime.now(UTC).isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "progress_percent": 35.0,
        "current_step": "Entity extraction optimization",
        "log_messages": json.dumps([
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": "INFO",
                "message": "Training started"
            },
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": "ERROR",
                "message": "CUDA out of memory during training"
            }
        ]),
        "metrics": None,
        "error_message": "CUDA out of memory: tried to allocate 4.50 GiB"
    }


@pytest.fixture
def sample_training_samples() -> list[dict[str, Any]]:
    """Sample training data for domain training."""
    return [
        {
            "text": "Python is a high-level programming language",
            "entities": ["Python"],
            "relations": []
        },
        {
            "text": "FastAPI is a modern web framework for building APIs",
            "entities": ["FastAPI"],
            "relations": []
        },
        {
            "text": "Pydantic provides data validation using Python type hints",
            "entities": ["Pydantic", "Python"],
            "relations": [{"head": "Pydantic", "relation": "USES", "tail": "Python"}]
        },
        {
            "text": "Qdrant is a vector database for similarity search",
            "entities": ["Qdrant"],
            "relations": []
        },
        {
            "text": "Neo4j stores data in a property graph format",
            "entities": ["Neo4j"],
            "relations": []
        }
    ]


@pytest.fixture
def domain_creation_request() -> dict[str, str]:
    """Sample domain creation request."""
    return {
        "name": "tech_docs",
        "description": "Technical documentation for APIs and software libraries",
        "llm_model": "qwen3:32b"
    }


@pytest.fixture
def domain_creation_request_minimal() -> dict[str, str]:
    """Minimal domain creation request (no llm_model)."""
    return {
        "name": "tech_docs",
        "description": "Technical documentation for APIs and software libraries"
    }


@pytest.fixture
def training_request(sample_training_samples) -> dict[str, list]:
    """Sample training request."""
    return {"samples": sample_training_samples}


@pytest.fixture
def ollama_models() -> list[dict[str, str | int]]:
    """Sample Ollama models list."""
    return [
        {"name": "qwen3:32b", "size": 20000000000},
        {"name": "llama3.2:8b", "size": 5000000000},
        {"name": "llama2:7b", "size": 4000000000},
        {"name": "mistral:7b", "size": 4000000000}
    ]


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Mock httpx client for HTTP requests."""
    return MagicMock()


@pytest.fixture
def mock_neo4j_transaction() -> AsyncMock:
    """Mock Neo4j transaction."""
    transaction = AsyncMock()
    transaction.run = AsyncMock()
    transaction.commit = AsyncMock()
    transaction.rollback = AsyncMock()
    return transaction


@pytest.fixture
def mock_redis_client() -> AsyncMock:
    """Mock Redis client."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock()
    client.delete = AsyncMock()
    client.exists = AsyncMock(return_value=False)
    return client


# Marker for tests that require external services
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "requires_ollama: mark test as requiring Ollama LLM service"
    )
    config.addinivalue_line(
        "markers", "requires_neo4j: mark test as requiring Neo4j database"
    )
    config.addinivalue_line(
        "markers", "requires_redis: mark test as requiring Redis service"
    )
    config.addinivalue_line(
        "markers", "requires_qdrant: mark test as requiring Qdrant vector DB"
    )
