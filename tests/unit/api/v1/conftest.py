"""Pytest configuration and fixtures for api/v1 unit tests.

Sprint 58: Provides properly patched test clients for endpoint testing.

The key insight is that patches must be applied BEFORE the app is imported,
since Python caches modules in sys.modules.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def admin_test_client():
    """Create a test client with admin dependencies mocked.

    This fixture patches all external dependencies BEFORE importing the app,
    ensuring the mocks take effect properly.

    Returns:
        TestClient with mocked dependencies for admin endpoint testing
    """
    # Mock Qdrant client
    mock_qdrant = AsyncMock()
    mock_qdrant.get_collection_info = AsyncMock(return_value=MagicMock(points_count=1523))

    # Mock embedding service
    mock_embedding = MagicMock()
    mock_embedding.embedding_dim = 1024
    mock_embedding.model_name = "BAAI/bge-m3"

    # Mock Neo4j client
    mock_neo4j = AsyncMock()
    mock_neo4j.execute_query = AsyncMock(
        side_effect=[
            [{"count": 856}],  # entities
            [{"count": 1204}],  # relations
        ]
    )

    # Mock Redis memory
    mock_redis = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_redis_client.scan = AsyncMock(return_value=(0, [b"conversation:123"]))
    mock_redis.client = AsyncMock(return_value=mock_redis_client)

    # Mock hybrid search
    mock_hybrid = MagicMock()
    mock_bm25 = MagicMock()
    mock_bm25.is_fitted = MagicMock(return_value=True)
    mock_bm25.get_corpus_size = MagicMock(return_value=342)
    mock_hybrid.bm25_search = mock_bm25

    # Apply patches BEFORE importing app
    with (
        patch("src.api.v1.admin.get_qdrant_client", return_value=mock_qdrant),
        patch("src.api.v1.admin.get_embedding_service", return_value=mock_embedding),
        patch("src.components.graph_rag.neo4j_client.get_neo4j_client", return_value=mock_neo4j),
        patch("src.components.memory.get_redis_memory", return_value=mock_redis),
        patch("src.api.v1.retrieval.get_hybrid_search", return_value=mock_hybrid),
        patch(
            "src.api.v1.admin.get_last_reindex_timestamp", new_callable=AsyncMock
        ) as mock_reindex,
    ):

        mock_reindex.return_value = "2025-12-18T10:30:00"

        # Import app after patches are in place
        from src.api.main import app

        # Create test client
        client = TestClient(app)

        # Store mocks on client for test access
        client._mocks = {
            "qdrant": mock_qdrant,
            "embedding": mock_embedding,
            "neo4j": mock_neo4j,
            "redis": mock_redis,
            "hybrid": mock_hybrid,
            "reindex": mock_reindex,
        }

        yield client


@pytest.fixture
def namespace_test_client():
    """Create a test client for namespace endpoint testing.

    Patches NamespaceManager at source location since it's imported lazily.
    """
    mock_namespace_info = MagicMock()
    mock_namespace_info.namespace_id = "default"
    mock_namespace_info.namespace_type = "general"
    mock_namespace_info.document_count = 42
    mock_namespace_info.description = "Default namespace"

    mock_manager = AsyncMock()
    mock_manager.list_namespaces = AsyncMock(return_value=[mock_namespace_info])

    # Patch at source location (lazy import inside function)
    with patch("src.core.namespace.NamespaceManager", return_value=mock_manager):
        from src.api.main import app

        client = TestClient(app)
        client._mocks = {"manager": mock_manager, "namespace_info": mock_namespace_info}
        yield client


def _create_graph_result_mock(single_value=None, data_value=None):
    """Create a properly configured async result mock for Neo4j queries.

    The Neo4j driver returns a Result object that has async methods
    like .single() and .data().
    """
    result = AsyncMock()
    if single_value is not None:
        result.single = AsyncMock(return_value=single_value)
    if data_value is not None:
        result.data = AsyncMock(return_value=data_value)
    return result


@pytest.fixture
def graph_test_client():
    """Create a test client for graph stats endpoint testing.

    Patches Neo4j client with comprehensive mock data for graph statistics.
    Uses proper async mock chain for Neo4j driver session.
    """
    # Create result mocks for each query
    entity_result = _create_graph_result_mock(single_value={"count": 856})
    rel_result = _create_graph_result_mock(single_value={"count": 1204})
    entity_types_result = _create_graph_result_mock(
        data_value=[
            {"type": "PERSON", "count": 450},
            {"type": "ORGANIZATION", "count": 300},
            {"type": "LOCATION", "count": 106},
        ]
    )
    rel_types_result = _create_graph_result_mock(
        data_value=[
            {"type": "RELATES_TO", "count": 700},
            {"type": "MENTIONED_IN", "count": 350},
            {"type": "WORKS_AT", "count": 154},
        ]
    )
    community_result = _create_graph_result_mock(
        data_value=[
            {"community": 1, "size": 100},
            {"community": 2, "size": 80},
            {"community": 3, "size": 60},
        ]
    )
    orphan_result = _create_graph_result_mock(single_value={"count": 5})
    summary_result = _create_graph_result_mock(single_value={"generated": 2, "pending": 1})

    # Create mock session with run method that returns results in order
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(
        side_effect=[
            entity_result,
            rel_result,
            entity_types_result,
            rel_types_result,
            community_result,
            orphan_result,
            summary_result,
        ]
    )

    # Mock the async context manager for session
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    # Mock driver.session() to return our mock session
    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)

    mock_neo4j = MagicMock()
    mock_neo4j.driver = mock_driver

    with patch("src.components.graph_rag.neo4j_client.get_neo4j_client", return_value=mock_neo4j):
        from src.api.main import app

        client = TestClient(app)
        client._mocks = {
            "neo4j": mock_neo4j,
            "session": mock_session,
        }
        yield client
