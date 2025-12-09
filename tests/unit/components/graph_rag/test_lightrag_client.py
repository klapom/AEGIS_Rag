"""Unit tests for LightRAGClient (Sprint 27 Feature 27.2).

This module tests the LightRAGClient wrapper with mocked dependencies.

Tests cover:
- Document insertion (single and batch)
- Query operations (local, global, hybrid modes)
- Entity extraction and storage
- Error handling and retry logic
- Neo4j health checks
- Statistics retrieval
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.graph_rag.lightrag_wrapper import LightRAGClient
from src.core.models import GraphQueryResult


@pytest.fixture
def mock_lightrag():
    """Mock LightRAG instance."""
    mock = MagicMock()
    mock.ainsert = AsyncMock(return_value={"status": "success"})
    mock.aquery = AsyncMock(return_value="This is the answer from LightRAG.")
    mock.initialize_storages = AsyncMock()
    mock.chunk_entity_relation_graph = MagicMock()
    mock.chunk_entity_relation_graph._driver = MagicMock()
    return mock


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j async driver."""
    driver = AsyncMock()
    session = AsyncMock()

    # Mock session.run() for stats queries
    result = AsyncMock()
    record = MagicMock()
    record.__getitem__ = lambda self, key: 10 if key == "count" else None
    result.single = AsyncMock(return_value=record)
    session.run = AsyncMock(return_value=result)

    driver.session = MagicMock(return_value=session)
    driver.__aenter__ = AsyncMock(return_value=session)
    driver.__aexit__ = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock()
    driver.close = AsyncMock()

    return driver


@pytest.fixture
async def lightrag_client(mock_lightrag, mock_neo4j_driver):
    """LightRAG client with mocked dependencies."""
    # Patch the actual lightrag library import (lazy-loaded in _ensure_initialized)
    with patch("lightrag.LightRAG", return_value=mock_lightrag):
        # Patch neo4j.AsyncGraphDatabase since it's lazy-imported inside methods
        with patch(
            "neo4j.AsyncGraphDatabase.driver",
            return_value=mock_neo4j_driver,
        ):
            # Patch initialize_pipeline_status from lightrag (lazy-imported)
            with patch(
                "lightrag.kg.shared_storage.initialize_pipeline_status",
                new_callable=AsyncMock,
            ):
                with patch("src.components.llm_proxy.get_aegis_llm_proxy"):
                    client = LightRAGClient()
                    await client._ensure_initialized()
                    return client


# ============================================================================
# Document Insertion Tests
# ============================================================================


@pytest.mark.asyncio
async def test_lightrag_insert_document(lightrag_client):
    """Test inserting a single document."""
    documents = [{"text": "Test document content", "id": "doc1"}]

    result = await lightrag_client.insert_documents(documents)

    assert result["total"] == 1
    assert result["success"] == 1
    assert result["failed"] == 0
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] == "success"


@pytest.mark.asyncio
async def test_lightrag_insert_empty_document(lightrag_client):
    """Test handling of empty document."""
    documents = [{"text": "", "id": "doc_empty"}]

    result = await lightrag_client.insert_documents(documents)

    assert result["total"] == 1
    assert result["success"] == 0
    assert result["failed"] == 1
    assert result["results"][0]["status"] == "skipped"
    assert result["results"][0]["reason"] == "empty_text"


@pytest.mark.asyncio
async def test_lightrag_insert_multiple_documents(lightrag_client):
    """Test batch document insertion."""
    documents = [
        {"text": "Document 1 content", "id": "doc1"},
        {"text": "Document 2 content", "id": "doc2"},
        {"text": "Document 3 content", "id": "doc3"},
    ]

    result = await lightrag_client.insert_documents(documents)

    assert result["total"] == 3
    assert result["success"] == 3
    assert result["failed"] == 0
    assert len(result["results"]) == 3


@pytest.mark.asyncio
async def test_lightrag_insert_document_failure(lightrag_client):
    """Test error handling during document insertion."""
    lightrag_client.rag.ainsert = AsyncMock(side_effect=Exception("Insertion failed"))

    documents = [{"text": "Test document", "id": "doc_fail"}]
    result = await lightrag_client.insert_documents(documents)

    assert result["total"] == 1
    assert result["success"] == 0
    assert result["failed"] == 1
    assert result["results"][0]["status"] == "error"


# ============================================================================
# Query Tests
# ============================================================================


@pytest.mark.asyncio
async def test_lightrag_query_local_mode(lightrag_client):
    """Test local (entity-level) search mode."""
    query = "What is AEGIS RAG?"

    result = await lightrag_client.query_graph(query, mode="local")

    assert isinstance(result, GraphQueryResult)
    assert result.query == query
    assert result.mode == "local"
    assert result.answer == "This is the answer from LightRAG."
    assert lightrag_client.rag.aquery.called


@pytest.mark.asyncio
async def test_lightrag_query_global_mode(lightrag_client):
    """Test global (topic-level) search mode."""
    query = "What are the main topics in the knowledge base?"

    result = await lightrag_client.query_graph(query, mode="global")

    assert isinstance(result, GraphQueryResult)
    assert result.mode == "global"
    assert result.answer != ""


@pytest.mark.asyncio
async def test_lightrag_query_hybrid_mode(lightrag_client):
    """Test hybrid (combined local + global) search mode."""
    query = "Explain hybrid search in AEGIS RAG"

    result = await lightrag_client.query_graph(query, mode="hybrid")

    assert isinstance(result, GraphQueryResult)
    assert result.mode == "hybrid"
    assert result.answer != ""


@pytest.mark.asyncio
async def test_lightrag_query_empty_results(lightrag_client):
    """Test query returning empty answer."""
    lightrag_client.rag.aquery = AsyncMock(return_value="")

    result = await lightrag_client.query_graph("Non-existent topic")

    assert result.answer == ""
    assert isinstance(result, GraphQueryResult)


@pytest.mark.asyncio
async def test_lightrag_query_failure_handling(lightrag_client):
    """Test error handling during query execution."""
    lightrag_client.rag.aquery = AsyncMock(side_effect=Exception("Query failed"))

    with pytest.raises(Exception, match="Query failed"):
        await lightrag_client.query_graph("Test query")


# ============================================================================
# Statistics and Health Check Tests
# ============================================================================


@pytest.mark.asyncio
async def test_lightrag_get_stats(lightrag_client):
    """Test retrieving graph statistics."""
    # Create a mock driver for the get_stats() method which creates its own connection
    mock_result = AsyncMock()
    mock_record = MagicMock()
    mock_record.__getitem__ = lambda self, key: 10 if key == "count" else None
    mock_result.single = AsyncMock(return_value=mock_record)

    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    mock_driver = AsyncMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    mock_driver.close = AsyncMock()

    # Patch at the source module where neo4j is imported (lazy import in get_stats)
    with patch("neo4j.AsyncGraphDatabase.driver", return_value=mock_driver):
        stats = await lightrag_client.get_stats()

    assert "entity_count" in stats
    assert "relationship_count" in stats
    assert stats["entity_count"] == 10
    assert stats["relationship_count"] == 10


@pytest.mark.asyncio
async def test_lightrag_health_check(lightrag_client):
    """Test Neo4j health check."""
    # Create a mock driver for the health_check() method which creates its own connection
    mock_result = AsyncMock()
    mock_record = MagicMock()
    mock_record.__getitem__ = lambda self, key: 1 if key == "health" else None
    mock_result.single = AsyncMock(return_value=mock_record)

    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    mock_driver = AsyncMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    mock_driver.close = AsyncMock()

    # Patch at the source module where neo4j is imported (lazy import in health_check)
    with patch("neo4j.AsyncGraphDatabase.driver", return_value=mock_driver):
        healthy = await lightrag_client.health_check()

    assert healthy is True


@pytest.mark.asyncio
async def test_lightrag_health_check_failure(lightrag_client):
    """Test health check failure handling."""
    # Create a mock driver that simulates connection failure
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(side_effect=Exception("Connection failed"))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()

    mock_driver = AsyncMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    mock_driver.close = AsyncMock()

    # Patch at the source module where neo4j is imported (lazy import in health_check)
    with patch("neo4j.AsyncGraphDatabase.driver", return_value=mock_driver):
        healthy = await lightrag_client.health_check()

    assert healthy is False


# ============================================================================
# Concurrent Operations Tests
# ============================================================================


@pytest.mark.asyncio
async def test_lightrag_concurrent_queries(lightrag_client):
    """Test concurrent query execution."""
    import asyncio

    queries = [
        "What is vector search?",
        "Explain graph reasoning",
        "What is temporal memory?",
    ]

    results = await asyncio.gather(*[lightrag_client.query_graph(q, mode="local") for q in queries])

    assert len(results) == 3
    assert all(isinstance(r, GraphQueryResult) for r in results)
    assert all(r.answer != "" for r in results)


@pytest.mark.asyncio
async def test_lightrag_concurrent_insertions(lightrag_client):
    """Test concurrent document insertions."""
    import asyncio

    doc_batches = [[{"text": f"Document {i}", "id": f"doc{i}"}] for i in range(3)]

    results = await asyncio.gather(
        *[lightrag_client.insert_documents(batch) for batch in doc_batches]
    )

    assert len(results) == 3
    assert all(r["success"] == 1 for r in results)


# ============================================================================
# Initialization Tests
# ============================================================================


@pytest.mark.asyncio
async def test_lightrag_lazy_initialization():
    """Test lazy initialization of LightRAG."""
    # Patch at the source module where LightRAG is imported from (lazy import)
    with patch("lightrag.LightRAG") as mock_lightrag_cls, patch(
        "lightrag.kg.shared_storage.initialize_pipeline_status",
        new_callable=AsyncMock,
    ), patch("src.components.llm_proxy.get_aegis_llm_proxy"):
        mock_instance = MagicMock()
        mock_instance.initialize_storages = AsyncMock()
        mock_instance.chunk_entity_relation_graph = MagicMock()
        mock_instance.chunk_entity_relation_graph._driver = MagicMock()
        mock_lightrag_cls.return_value = mock_instance

        client = LightRAGClient()
        assert not client._initialized

        await client._ensure_initialized()
        assert client._initialized
        assert mock_lightrag_cls.called


@pytest.mark.asyncio
async def test_lightrag_initialization_failure():
    """Test handling of initialization failure."""
    # Patch at the source module where LightRAG is imported from (lazy import)
    with patch(
        "lightrag.LightRAG",
        side_effect=ImportError("LightRAG not installed"),
    ):
        client = LightRAGClient()

        with pytest.raises(ImportError, match="LightRAG not installed"):
            await client._ensure_initialized()
