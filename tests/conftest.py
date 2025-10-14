"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.config import get_settings


@pytest.fixture
def test_client() -> TestClient:
    """
    Create a FastAPI test client.

    Returns:
        Test client for API testing
    """
    return TestClient(app)


@pytest.fixture
def settings():
    """
    Get application settings.

    Returns:
        Settings instance
    """
    return get_settings()


@pytest.fixture
def sample_query() -> str:
    """
    Sample query for testing.

    Returns:
        Sample query string
    """
    return "What are the main components of AEGIS RAG?"


@pytest.fixture
def sample_documents() -> list[dict]:
    """
    Sample documents for testing.

    Returns:
        List of sample document dicts
    """
    return [
        {
            "id": "doc1",
            "content": "AEGIS RAG consists of four main components: Vector Search, Graph Reasoning, Temporal Memory, and Tool Integration.",
            "metadata": {"source": "architecture.md", "page": 1},
        },
        {
            "id": "doc2",
            "content": "The Vector Search component uses Qdrant for hybrid search with BM25 and vector similarity.",
            "metadata": {"source": "tech-stack.md", "page": 2},
        },
        {
            "id": "doc3",
            "content": "Graph Reasoning is powered by LightRAG and Neo4j for multi-hop reasoning.",
            "metadata": {"source": "components.md", "page": 1},
        },
    ]
