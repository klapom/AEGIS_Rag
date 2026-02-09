"""Unit tests for HyDE (Hypothetical Document Embeddings) Query Expansion.

Sprint 128 Feature 128.4: HyDE Query Expansion Tests

This module tests the HyDE generator's ability to:
1. Generate hypothetical answer documents from queries
2. Embed hypothetical documents with BGE-M3
3. Search Qdrant with hypothetical embeddings
4. Cache hypothetical documents in Redis
5. Handle failures gracefully

Test Strategy:
    - Mock LLM proxy for hypothetical generation
    - Mock embedding service for embedding generation
    - Mock Qdrant client for search operations
    - Mock Redis for cache operations
    - Test cache hit/miss scenarios
    - Test error handling and fallback
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.retrieval.hyde import HyDEGenerator, get_hyde_generator
from src.domains.llm_integration.models import LLMResponse


@pytest.fixture
def mock_llm_proxy():
    """Mock LLM proxy for hypothetical document generation."""
    proxy = MagicMock()
    proxy.generate = AsyncMock(
        return_value=LLMResponse(
            content="Amsterdam is the capital and most populous city of the Netherlands. "
            "It is known for its artistic heritage, elaborate canal system, "
            "and narrow houses with gabled facades.",
            provider="local_ollama",
            model="nemotron-no-think:latest",
            tokens_used=50,
            tokens_input=20,
            tokens_output=30,
            cost_usd=0.0,
            latency_ms=100.0,
            routing_reason="default_local",
            fallback_used=False,
        )
    )
    return proxy


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for BGE-M3 embeddings."""
    service = MagicMock()
    service.embed_single = AsyncMock(return_value=[0.1] * 1024)  # 1024-dim embedding
    return service


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for cache operations."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)  # Cache miss by default
    client.setex = AsyncMock()
    return client


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for search operations."""
    client = MagicMock()

    # Mock search result
    hit = MagicMock()
    hit.id = "chunk_1"
    hit.score = 0.95
    hit.payload = {
        "content": "Amsterdam is the capital of the Netherlands.",
        "document_id": "doc_1",
        "namespace_id": "default",
    }

    client.search = MagicMock(return_value=[hit])
    return client


@pytest.mark.asyncio
async def test_generate_hypothetical_document(mock_llm_proxy, mock_redis_client):
    """Test hypothetical document generation with LLM."""
    with (
        patch("src.components.retrieval.hyde.get_aegis_llm_proxy", return_value=mock_llm_proxy),
        patch("src.components.retrieval.hyde.get_embedding_service"),
    ):
        hyde = HyDEGenerator()
        hyde._redis_client = mock_redis_client

        # Generate hypothetical document
        query = "What is Amsterdam?"
        doc = await hyde.generate_hypothetical_document(query)

        # Verify LLM was called
        assert mock_llm_proxy.generate.called
        task = mock_llm_proxy.generate.call_args[0][0]
        assert query in task.prompt
        assert "Write a short passage" in task.prompt

        # Verify result
        assert doc == mock_llm_proxy.generate.return_value.content
        assert "Amsterdam" in doc
        assert "Netherlands" in doc

        # Verify cache was updated
        assert mock_redis_client.setex.called
        cache_key = mock_redis_client.setex.call_args[0][0]
        assert cache_key.startswith("hyde:")


@pytest.mark.asyncio
async def test_generate_hypothetical_document_cache_hit(mock_llm_proxy, mock_redis_client):
    """Test hypothetical document generation with cache hit."""
    cached_doc = "Cached Amsterdam description from Redis"
    mock_redis_client.get = AsyncMock(return_value=cached_doc)

    with (
        patch("src.components.retrieval.hyde.get_aegis_llm_proxy", return_value=mock_llm_proxy),
        patch("src.components.retrieval.hyde.get_embedding_service"),
    ):
        hyde = HyDEGenerator()
        hyde._redis_client = mock_redis_client

        # Generate hypothetical document (should hit cache)
        query = "What is Amsterdam?"
        doc = await hyde.generate_hypothetical_document(query)

        # Verify cache was checked
        assert mock_redis_client.get.called

        # Verify LLM was NOT called (cache hit)
        assert not mock_llm_proxy.generate.called

        # Verify cached result was returned
        assert doc == cached_doc


@pytest.mark.asyncio
async def test_generate_hypothetical_document_cache_failure(mock_llm_proxy, mock_redis_client):
    """Test hypothetical document generation when cache fails."""
    mock_redis_client.get = AsyncMock(side_effect=Exception("Redis connection failed"))
    mock_redis_client.setex = AsyncMock(side_effect=Exception("Redis connection failed"))

    with (
        patch("src.components.retrieval.hyde.get_aegis_llm_proxy", return_value=mock_llm_proxy),
        patch("src.components.retrieval.hyde.get_embedding_service"),
    ):
        hyde = HyDEGenerator()
        hyde._redis_client = mock_redis_client

        # Generate hypothetical document (cache fails, should still work)
        query = "What is Amsterdam?"
        doc = await hyde.generate_hypothetical_document(query)

        # Verify LLM was called despite cache failure
        assert mock_llm_proxy.generate.called

        # Verify result was returned
        assert doc == mock_llm_proxy.generate.return_value.content


@pytest.mark.asyncio
async def test_hyde_search(
    mock_llm_proxy, mock_embedding_service, mock_redis_client, mock_qdrant_client
):
    """Test full HyDE search pipeline."""
    with (
        patch("src.components.retrieval.hyde.get_aegis_llm_proxy", return_value=mock_llm_proxy),
        patch(
            "src.components.retrieval.hyde.get_embedding_service",
            return_value=mock_embedding_service,
        ),
        patch("qdrant_client.QdrantClient", return_value=mock_qdrant_client),
    ):
        hyde = HyDEGenerator()
        hyde._redis_client = mock_redis_client

        # Execute HyDE search
        query = "What is Amsterdam?"
        results = await hyde.hyde_search(query, top_k=10)

        # Verify LLM generated hypothetical document
        assert mock_llm_proxy.generate.called

        # Verify embedding was generated
        assert mock_embedding_service.embed_single.called

        # Verify Qdrant was searched
        assert mock_qdrant_client.search.called
        search_args = mock_qdrant_client.search.call_args

        # Verify search used hypothetical embedding
        assert search_args.kwargs["query_vector"] == ("dense", [0.1] * 1024)
        assert search_args.kwargs["limit"] == 10

        # Verify results
        assert len(results) == 1
        assert results[0]["id"] == "chunk_1"
        assert results[0]["score"] == 0.95
        assert results[0]["source"] == "hyde"
        assert "Amsterdam" in results[0]["content"]


@pytest.mark.asyncio
async def test_hyde_search_with_namespaces(
    mock_llm_proxy, mock_embedding_service, mock_redis_client, mock_qdrant_client
):
    """Test HyDE search with namespace filtering."""
    with (
        patch("src.components.retrieval.hyde.get_aegis_llm_proxy", return_value=mock_llm_proxy),
        patch(
            "src.components.retrieval.hyde.get_embedding_service",
            return_value=mock_embedding_service,
        ),
        patch("qdrant_client.QdrantClient", return_value=mock_qdrant_client),
    ):
        hyde = HyDEGenerator()
        hyde._redis_client = mock_redis_client

        # Execute HyDE search with namespaces
        query = "What is Amsterdam?"
        namespaces = ["research_papers", "wiki"]
        results = await hyde.hyde_search(query, top_k=10, namespaces=namespaces)

        # Verify Qdrant search was called with namespace filter
        assert mock_qdrant_client.search.called
        search_args = mock_qdrant_client.search.call_args

        # Check filter was applied
        assert search_args.kwargs["query_filter"] is not None


@pytest.mark.asyncio
async def test_hyde_search_llm_failure(
    mock_llm_proxy, mock_embedding_service, mock_redis_client, mock_qdrant_client
):
    """Test HyDE search when LLM generation fails."""
    mock_llm_proxy.generate = AsyncMock(side_effect=Exception("LLM service unavailable"))

    with (
        patch("src.components.retrieval.hyde.get_aegis_llm_proxy", return_value=mock_llm_proxy),
        patch(
            "src.components.retrieval.hyde.get_embedding_service",
            return_value=mock_embedding_service,
        ),
        patch("qdrant_client.QdrantClient", return_value=mock_qdrant_client),
    ):
        hyde = HyDEGenerator()
        hyde._redis_client = mock_redis_client

        # Execute HyDE search (should fail gracefully)
        query = "What is Amsterdam?"

        with pytest.raises(Exception) as exc_info:
            await hyde.hyde_search(query, top_k=10)

        assert "LLM service unavailable" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hyde_search_embedding_failure(
    mock_llm_proxy, mock_embedding_service, mock_redis_client, mock_qdrant_client
):
    """Test HyDE search when embedding generation fails."""
    mock_embedding_service.embed_single = AsyncMock(
        side_effect=Exception("Embedding service unavailable")
    )

    with (
        patch("src.components.retrieval.hyde.get_aegis_llm_proxy", return_value=mock_llm_proxy),
        patch(
            "src.components.retrieval.hyde.get_embedding_service",
            return_value=mock_embedding_service,
        ),
        patch("qdrant_client.QdrantClient", return_value=mock_qdrant_client),
    ):
        hyde = HyDEGenerator()
        hyde._redis_client = mock_redis_client

        # Execute HyDE search (should fail gracefully)
        query = "What is Amsterdam?"

        with pytest.raises(Exception) as exc_info:
            await hyde.hyde_search(query, top_k=10)

        assert "Embedding service unavailable" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hyde_cache_key_generation(mock_llm_proxy, mock_redis_client):
    """Test cache key generation for queries."""
    with (
        patch("src.components.retrieval.hyde.get_aegis_llm_proxy", return_value=mock_llm_proxy),
        patch("src.components.retrieval.hyde.get_embedding_service"),
    ):
        hyde = HyDEGenerator()

        # Generate cache keys
        key1 = hyde._cache_key("What is Amsterdam?")
        key2 = hyde._cache_key("What is Amsterdam?")  # Same query
        key3 = hyde._cache_key("What is Berlin?")  # Different query

        # Verify cache keys
        assert key1.startswith("hyde:")
        assert key1 == key2  # Same query → same key
        assert key1 != key3  # Different query → different key


def test_get_hyde_generator_singleton():
    """Test HyDE generator singleton pattern."""
    with (
        patch("src.components.retrieval.hyde.get_aegis_llm_proxy"),
        patch("src.components.retrieval.hyde.get_embedding_service"),
    ):
        # Get singleton instance
        hyde1 = get_hyde_generator()
        hyde2 = get_hyde_generator()

        # Verify same instance
        assert hyde1 is hyde2


@pytest.mark.asyncio
async def test_generate_hypothetical_document_low_temperature(mock_llm_proxy, mock_redis_client):
    """Test that hypothetical document generation uses low temperature for consistency."""
    with (
        patch("src.components.retrieval.hyde.get_aegis_llm_proxy", return_value=mock_llm_proxy),
        patch("src.components.retrieval.hyde.get_embedding_service"),
    ):
        hyde = HyDEGenerator()
        hyde._redis_client = mock_redis_client

        # Generate hypothetical document
        query = "What is Amsterdam?"
        await hyde.generate_hypothetical_document(query)

        # Verify LLM task used low temperature
        task = mock_llm_proxy.generate.call_args[0][0]
        assert task.temperature == 0.3  # Low temperature for consistent output


@pytest.mark.asyncio
async def test_hyde_search_result_format(
    mock_llm_proxy, mock_embedding_service, mock_redis_client, mock_qdrant_client
):
    """Test HyDE search result format matches expected schema."""
    with (
        patch("src.components.retrieval.hyde.get_aegis_llm_proxy", return_value=mock_llm_proxy),
        patch(
            "src.components.retrieval.hyde.get_embedding_service",
            return_value=mock_embedding_service,
        ),
        patch("qdrant_client.QdrantClient", return_value=mock_qdrant_client),
    ):
        hyde = HyDEGenerator()
        hyde._redis_client = mock_redis_client

        # Execute HyDE search
        query = "What is Amsterdam?"
        results = await hyde.hyde_search(query, top_k=10)

        # Verify result format
        assert isinstance(results, list)
        assert len(results) > 0

        result = results[0]
        assert "id" in result
        assert "score" in result
        assert "content" in result
        assert "metadata" in result
        assert "source" in result
        assert result["source"] == "hyde"
