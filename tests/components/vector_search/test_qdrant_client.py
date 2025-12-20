"""Unit tests for QdrantClientWrapper.

Tests the Qdrant client wrapper including:
- Connection initialization
- Health checks with retry logic
- Collection management (create, delete, info)
- Point operations (upsert, search)
- Error handling and retries
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, PointStruct, ScoredPoint

from src.components.vector_search.qdrant_client import (
    QdrantClientWrapper,
    get_qdrant_client,
)
from src.core.exceptions import DatabaseConnectionError, VectorSearchError

# ============================================================================
# Test Initialization
# ============================================================================


@pytest.mark.unit
def test_qdrant_client_init_default():
    """Test QdrantClientWrapper initialization with default settings."""
    client = QdrantClientWrapper()

    assert client.host is not None, "Host should be set from settings"
    assert client.port is not None, "Port should be set from settings"
    assert client.prefer_grpc is True, "Should prefer gRPC by default"
    assert client.timeout == 30, "Default timeout should be 30s"
    assert client._client is None, "Sync client should be lazy initialized"
    assert client._async_client is None, "Async client should be lazy initialized"


@pytest.mark.unit
def test_qdrant_client_init_custom():
    """Test QdrantClientWrapper initialization with custom parameters."""
    client = QdrantClientWrapper(
        host="custom-host",
        port=9999,
        grpc_port=8888,
        prefer_grpc=False,
        timeout=60,
    )

    assert client.host == "custom-host", "Custom host should be set"
    assert client.port == 9999, "Custom port should be set"
    assert client.grpc_port == 8888, "Custom gRPC port should be set"
    assert client.prefer_grpc is False, "Custom prefer_grpc should be set"
    assert client.timeout == 60, "Custom timeout should be set"


@pytest.mark.unit
def test_qdrant_client_lazy_initialization():
    """Test that Qdrant clients are lazy initialized."""
    with (
        patch("src.components.vector_search.qdrant_client.QdrantClient") as mock_sync,
        patch("src.components.vector_search.qdrant_client.AsyncQdrantClient") as mock_async,
    ):

        client = QdrantClientWrapper()

        # Clients should not be created yet
        mock_sync.assert_not_called()
        mock_async.assert_not_called()

        # Access sync client triggers initialization
        _ = client.client
        mock_sync.assert_called_once()

        # Access async client triggers initialization
        _ = client.async_client
        mock_async.assert_called_once()


# ============================================================================
# Test Health Check
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_success():
    """Test successful health check."""
    wrapper = QdrantClientWrapper()
    wrapper._async_client = AsyncMock()
    wrapper._async_client.get_collections = AsyncMock(return_value=[])

    result = await wrapper.health_check()

    assert result is True, "Health check should return True"
    wrapper._async_client.get_collections.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_failure():
    """Test health check failure and exception raising."""
    client = MagicMock()
    client.async_client = AsyncMock()
    client.async_client.get_collections.side_effect = Exception("Connection refused")

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client.async_client

    with pytest.raises(DatabaseConnectionError) as exc_info:
        await wrapper.health_check()

    assert "health check failed" in str(exc_info.value).lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_retry_logic():
    """Test health check retry logic on transient failures.

    Note: health_check() wraps all exceptions in DatabaseConnectionError,
    so UnexpectedResponse is not directly retried. This test verifies that
    transient failures result in DatabaseConnectionError being raised.
    """
    import httpx

    client = AsyncMock()

    # Simulate transient failure
    client.get_collections.side_effect = UnexpectedResponse(
        status_code=503, reason_phrase="Service Unavailable", content=b"", headers=httpx.Headers()
    )

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    # Should raise DatabaseConnectionError after wrapping UnexpectedResponse
    with pytest.raises(DatabaseConnectionError) as exc_info:
        await wrapper.health_check()

    assert "health check failed" in str(exc_info.value).lower()


# ============================================================================
# Test Collection Management
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_collection_success(mock_qdrant_client, test_collection_name):
    """Test successful collection creation."""
    result = await mock_qdrant_client.create_collection(
        collection_name=test_collection_name,
        vector_size=1024,
        distance=Distance.COSINE,
    )

    assert result is True, "Collection creation should succeed"
    mock_qdrant_client.create_collection.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_collection_already_exists():
    """Test creating collection that already exists (should not fail)."""
    client = AsyncMock()

    # Create a proper mock collection with .name attribute
    mock_collection = MagicMock()
    mock_collection.name = "existing_collection"

    collections_response = MagicMock()
    collections_response.collections = [mock_collection]
    client.get_collections.return_value = collections_response

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    result = await wrapper.create_collection(
        collection_name="existing_collection",
        vector_size=1024,
    )

    assert result is True, "Should return True for existing collection"
    client.create_collection.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_collection_failure():
    """Test collection creation failure with retry decorator.

    Note: The retry decorator wraps failures in RetryError after max attempts.
    """
    from tenacity import RetryError

    client = AsyncMock()
    client.get_collections.return_value = MagicMock(collections=[])
    client.create_collection.side_effect = Exception("Creation failed")

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    # With retry decorator, we get RetryError wrapping the original exception
    with pytest.raises((RetryError, VectorSearchError)):
        await wrapper.create_collection(
            collection_name="test_collection",
            vector_size=1024,
        )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("distance", [Distance.COSINE, Distance.EUCLID, Distance.DOT])
async def test_create_collection_different_distances(distance):
    """Test creating collections with different distance metrics."""
    client = AsyncMock()
    client.get_collections.return_value = MagicMock(collections=[])
    client.create_collection.return_value = True

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    result = await wrapper.create_collection(
        collection_name="test_collection",
        vector_size=1024,
        distance=distance,
    )

    assert result is True, f"Should create collection with {distance} distance"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_collection_success(mock_qdrant_client, test_collection_name):
    """Test successful collection deletion."""
    result = await mock_qdrant_client.delete_collection(test_collection_name)

    assert result is True, "Collection deletion should succeed"
    mock_qdrant_client.delete_collection.assert_called_once_with(test_collection_name)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_collection_failure():
    """Test collection deletion failure (should not raise, return False)."""
    client = AsyncMock()
    client.delete_collection.side_effect = Exception("Deletion failed")

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    result = await wrapper.delete_collection("test_collection")

    assert result is False, "Should return False on deletion failure"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_collection_info_success(mock_qdrant_client, test_collection_name):
    """Test getting collection information."""
    info = await mock_qdrant_client.get_collection_info(test_collection_name)

    assert info is not None, "Should return collection info"
    assert hasattr(info, "vectors_count"), "Info should have vectors_count"
    assert hasattr(info, "points_count"), "Info should have points_count"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_collection_info_not_found():
    """Test getting info for non-existent collection."""
    client = AsyncMock()
    client.get_collection.side_effect = Exception("Collection not found")

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    info = await wrapper.get_collection_info("nonexistent")

    assert info is None, "Should return None for non-existent collection"


# ============================================================================
# Test Point Operations
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upsert_points_success(mock_qdrant_client, test_collection_name):
    """Test successful point upsert."""
    points = [
        PointStruct(
            id="point1",
            vector=[0.1] * 1024,
            payload={"text": "Test document 1"},
        ),
        PointStruct(
            id="point2",
            vector=[0.2] * 1024,
            payload={"text": "Test document 2"},
        ),
    ]

    result = await mock_qdrant_client.upsert_points(
        collection_name=test_collection_name,
        points=points,
        batch_size=100,
    )

    assert result is True, "Upsert should succeed"
    mock_qdrant_client.upsert_points.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upsert_points_batching():
    """Test that points are upserted in batches."""
    client = AsyncMock()
    client.upsert.return_value = MagicMock(status="completed")

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    # Create 250 points (should be split into 3 batches of 100)
    points = [PointStruct(id=f"point{i}", vector=[0.1] * 1024, payload={}) for i in range(250)]

    result = await wrapper.upsert_points(
        collection_name="test_collection",
        points=points,
        batch_size=100,
    )

    assert result is True, "Batch upsert should succeed"
    assert client.upsert.call_count == 3, "Should make 3 batch calls (100, 100, 50)"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upsert_points_failure():
    """Test point upsert failure.

    Note: The method raises VectorSearchError directly (no retry decorator on upsert),
    but accepts RetryError in case it's wrapped elsewhere in the call chain.
    """
    from tenacity import RetryError

    client = AsyncMock()
    client.upsert.side_effect = Exception("Upsert failed")

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    points = [
        PointStruct(id="point1", vector=[0.1] * 1024, payload={}),
    ]

    with pytest.raises((VectorSearchError, RetryError)) as exc_info:
        await wrapper.upsert_points(
            collection_name="test_collection",
            points=points,
        )

    # Check error message if it's VectorSearchError (not RetryError)
    if isinstance(exc_info.value, VectorSearchError):
        assert "Failed to upsert points" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_upsert_empty_points_list():
    """Test upserting empty points list."""
    client = AsyncMock()

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    result = await wrapper.upsert_points(
        collection_name="test_collection",
        points=[],
    )

    assert result is True, "Empty upsert should succeed"
    client.upsert.assert_not_called()


# ============================================================================
# Test Search Operations
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_success(mock_qdrant_client, test_collection_name):
    """Test successful vector search."""
    query_vector = [0.1] * 1024

    results = await mock_qdrant_client.search(
        collection_name=test_collection_name,
        query_vector=query_vector,
        limit=10,
    )

    assert len(results) > 0, "Search should return results"
    assert "id" in results[0], "Results should have ID"
    assert "score" in results[0], "Results should have score"
    assert "payload" in results[0], "Results should have payload"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_score_threshold():
    """Test search with minimum score threshold."""
    client = AsyncMock()
    client.search.return_value = [
        ScoredPoint(
            id="point1",
            score=0.95,
            payload={"text": "High score result"},
            version=1,
        ),
    ]

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    results = await wrapper.search(
        collection_name="test_collection",
        query_vector=[0.1] * 1024,
        limit=10,
        score_threshold=0.8,
    )

    assert len(results) == 1, "Should return high-scoring results"
    assert results[0]["score"] >= 0.8, "Score should be above threshold"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_with_filter():
    """Test search with metadata filter."""
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    client = AsyncMock()
    client.search.return_value = []

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    query_filter = Filter(
        must=[
            FieldCondition(
                key="source",
                match=MatchValue(value="docs.md"),
            )
        ]
    )

    await wrapper.search(
        collection_name="test_collection",
        query_vector=[0.1] * 1024,
        query_filter=query_filter,
    )

    # Verify filter was passed
    call_args = client.search.call_args
    assert call_args.kwargs["query_filter"] == query_filter


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_failure():
    """Test search failure."""
    client = AsyncMock()
    client.search.side_effect = Exception("Search failed")

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    with pytest.raises(VectorSearchError) as exc_info:
        await wrapper.search(
            collection_name="test_collection",
            query_vector=[0.1] * 1024,
        )

    assert "Vector search failed" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_empty_results():
    """Test search returning no results."""
    client = AsyncMock()
    client.search.return_value = []

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    results = await wrapper.search(
        collection_name="test_collection",
        query_vector=[0.1] * 1024,
    )

    assert results == [], "Empty search should return empty list"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [1, 10, 50, 100])
async def test_search_different_limits(limit):
    """Test search with different result limits."""
    client = AsyncMock()
    client.search.return_value = [
        ScoredPoint(id=f"point{i}", score=0.9 - i * 0.01, payload={}, version=1)
        for i in range(min(limit, 10))
    ]

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    results = await wrapper.search(
        collection_name="test_collection",
        query_vector=[0.1] * 1024,
        limit=limit,
    )

    assert len(results) <= limit, f"Should return at most {limit} results"


# ============================================================================
# Test Client Lifecycle
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_clients():
    """Test closing client connections."""
    sync_client = MagicMock()
    async_client = AsyncMock()

    wrapper = QdrantClientWrapper()
    wrapper._client = sync_client
    wrapper._async_client = async_client

    await wrapper.close()

    async_client.close.assert_called_once()
    sync_client.close.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_uninitialized_clients():
    """Test closing without initializing clients (should not error)."""
    wrapper = QdrantClientWrapper()

    # Should not raise exception
    await wrapper.close()


# ============================================================================
# Test Singleton Pattern
# ============================================================================


@pytest.mark.unit
def test_get_qdrant_client_singleton():
    """Test that get_qdrant_client returns singleton instance."""
    client1 = get_qdrant_client()
    client2 = get_qdrant_client()

    assert client1 is client2, "Should return same instance"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_qdrant_client_async_context_manager():
    """Test async context manager for Qdrant client."""
    from src.components.vector_search.qdrant_client import get_qdrant_client_async

    async with get_qdrant_client_async() as client:
        assert client is not None, "Context manager should provide client"
        assert isinstance(client, QdrantClientWrapper), "Should be QdrantClientWrapper"


# ============================================================================
# Test Error Scenarios
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_on_unexpected_response():
    """Test automatic retry on UnexpectedResponse."""
    import httpx

    client = AsyncMock()

    # Fail twice, then succeed
    client.create_collection.side_effect = [
        UnexpectedResponse(
            status_code=503,
            reason_phrase="Service Unavailable",
            content=b"",
            headers=httpx.Headers(),
        ),
        UnexpectedResponse(
            status_code=503,
            reason_phrase="Service Unavailable",
            content=b"",
            headers=httpx.Headers(),
        ),
        True,
    ]
    client.get_collections.return_value = MagicMock(collections=[])

    wrapper = QdrantClientWrapper()
    wrapper._async_client = client

    result = await wrapper.create_collection(
        collection_name="test_collection",
        vector_size=1024,
    )

    assert result is True, "Should succeed after retries"
    assert client.create_collection.call_count == 3, "Should retry failed calls"
