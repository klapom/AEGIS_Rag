"""Unit tests for UnifiedMemoryAPI (Feature 9.4).

Tests:
1. test_unified_api_initialization - Test API setup
2. test_store_to_redis - Test storing to Layer 1 (Redis)
3. test_retrieve_with_routing - Test intelligent layer routing
4. test_retrieve_with_fallback - Test graceful degradation
5. test_search_specific_layers - Test layer-specific search
6. test_delete_from_redis - Test deletion from single layer
7. test_delete_from_all_layers - Test deletion across all layers
8. test_store_conversation_turn - Test conversation storage
9. test_get_session_summary - Test session summary
10. test_health_check - Test health monitoring
11. test_metrics_collection - Test Prometheus metrics
12. test_retry_logic - Test automatic retries
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.components.memory.unified_api import UnifiedMemoryAPI


@pytest.fixture
def mock_redis_memory():
    """Mock Redis memory manager."""
    # Create mock client first
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)

    # Create mock redis memory
    mock = MagicMock()
    mock.store = AsyncMock(return_value=True)
    mock.retrieve = AsyncMock(return_value="test_value")
    mock.delete = AsyncMock(return_value=True)

    # Mock the async client property - use an async function
    async def get_client():
        return mock_client

    # Assign the coroutine function (not called) as a property
    type(mock).client = property(lambda self: get_client())

    return mock


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client."""
    return Mock()


@pytest.fixture
def mock_memory_router():
    """Mock memory router."""
    mock = AsyncMock()
    mock.search_memory = AsyncMock(
        return_value={
            "short_term": [{"content": "redis result"}],
            "long_term": [{"content": "qdrant result"}],
        }
    )
    mock.store_conversation_turn = AsyncMock(return_value={"short_term": True, "episodic": True})
    mock.get_session_summary = AsyncMock(
        return_value={
            "short_term": {"message_count": 5},
            "long_term": {"available": True},
        }
    )
    return mock


@pytest.fixture
def unified_api(mock_redis_memory, mock_qdrant_client, mock_memory_router):
    """Create unified API with mocked dependencies."""
    with (
        patch("src.components.memory.unified_api.get_redis_memory", return_value=mock_redis_memory),
        patch(
            "src.components.memory.unified_api.get_qdrant_client", return_value=mock_qdrant_client
        ),
        patch(
            "src.components.memory.unified_api.get_memory_router", return_value=mock_memory_router
        ),
        patch("src.components.memory.unified_api.settings") as mock_settings,
    ):
        mock_settings.graphiti_enabled = False

        api = UnifiedMemoryAPI(session_id="test_session", enable_metrics=False)
        return api


class TestUnifiedMemoryAPI:
    """Test suite for UnifiedMemoryAPI."""

    def test_unified_api_initialization(self, unified_api):
        """Test 1: Test API initialization."""
        assert unified_api is not None
        assert unified_api.session_id == "test_session"
        assert unified_api.redis_memory is not None
        assert unified_api.qdrant_client is not None
        assert unified_api.memory_router is not None
        assert unified_api.enable_metrics is False

    @pytest.mark.asyncio
    async def test_store_to_redis(self, unified_api, mock_redis_memory):
        """Test 2: Test storing data to Redis (Layer 1)."""
        result = await unified_api.store(
            key="test_key",
            value="test_value",
            ttl_seconds=3600,
            namespace="memory",
        )

        assert result is True
        mock_redis_memory.store.assert_called_once()

        # Verify call arguments
        call_args = mock_redis_memory.store.call_args
        assert call_args.kwargs["key"] == "test_key"
        assert call_args.kwargs["value"] == "test_value"
        assert call_args.kwargs["ttl_seconds"] == 3600
        assert call_args.kwargs["namespace"] == "memory"

    @pytest.mark.asyncio
    async def test_store_with_metadata(self, unified_api, mock_redis_memory):
        """Test storing with metadata."""
        metadata = {"category": "important", "tags": ["work", "urgent"]}

        result = await unified_api.store(
            key="important_item",
            value="critical data",
            metadata=metadata,
        )

        assert result is True
        mock_redis_memory.store.assert_called_once()

        # Verify metadata was merged
        call_args = mock_redis_memory.store.call_args
        stored_value = call_args.kwargs["value"]
        assert "value" in stored_value
        assert "metadata" in stored_value
        assert stored_value["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_retrieve_with_routing(self, unified_api, mock_memory_router):
        """Test 3: Test retrieval with intelligent routing."""
        results = await unified_api.retrieve(
            query="What is machine learning?",
            limit=10,
        )

        assert "short_term" in results
        assert "long_term" in results
        assert "total_results" in results
        assert "layers_searched" in results
        assert "query" in results
        assert "latency_ms" in results

        # Verify router was called
        mock_memory_router.search_memory.assert_called_once()
        call_args = mock_memory_router.search_memory.call_args
        assert call_args.kwargs["query"] == "What is machine learning?"
        assert call_args.kwargs["limit"] == 10

        # Verify metadata
        assert results["total_results"] == 2
        assert "short_term" in results["layers_searched"]
        assert "long_term" in results["layers_searched"]

    @pytest.mark.asyncio
    async def test_retrieve_with_fallback(self, unified_api, mock_memory_router):
        """Test 4: Test graceful degradation on errors."""
        # Simulate router failure
        mock_memory_router.search_memory = AsyncMock(side_effect=Exception("Router failed"))

        results = await unified_api.retrieve(query="test query")

        # Should return empty results with error
        assert results["total_results"] == 0
        assert "error" in results
        assert results["short_term"] == []
        assert results["long_term"] == []
        assert results["episodic"] == []

    @pytest.mark.asyncio
    async def test_search_specific_layers(self, unified_api):
        """Test 5: Test searching specific layers."""
        # Search only long-term layer
        results = await unified_api.search(
            query="machine learning",
            layers=["long_term"],
            top_k=5,
        )

        assert isinstance(results, list)

        # Search multiple layers
        results = await unified_api.search(
            query="test",
            layers=["short_term", "long_term"],
            top_k=10,
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_delete_from_redis(self, unified_api, mock_redis_memory):
        """Test 6: Test deletion from Redis only."""
        results = await unified_api.delete(
            key="test_key",
            namespace="memory",
            all_layers=False,
        )

        assert "short_term" in results
        assert results["short_term"] is True
        assert "long_term" not in results
        assert "episodic" not in results

        mock_redis_memory.delete.assert_called_once_with(
            key="test_key",
            namespace="memory",
        )

    @pytest.mark.asyncio
    async def test_delete_from_all_layers(self, unified_api, mock_redis_memory):
        """Test 7: Test deletion across all layers."""
        results = await unified_api.delete(
            key="test_key",
            all_layers=True,
        )

        assert "short_term" in results
        assert "long_term" in results
        assert "episodic" in results

        # Redis should still be called
        mock_redis_memory.delete.assert_called_once()

        # Other layers are placeholder implementations
        assert results["long_term"] is False
        assert results["episodic"] is False

    @pytest.mark.asyncio
    async def test_store_conversation_turn(self, unified_api, mock_memory_router):
        """Test 8: Test conversation turn storage."""
        results = await unified_api.store_conversation_turn(
            user_message="Hello, how are you?",
            assistant_message="I'm doing well, thanks!",
            metadata={"intent": "greeting"},
        )

        assert "short_term" in results
        assert "episodic" in results

        # Verify router was called
        mock_memory_router.store_conversation_turn.assert_called_once()
        call_args = mock_memory_router.store_conversation_turn.call_args
        assert call_args.kwargs["user_message"] == "Hello, how are you?"
        assert call_args.kwargs["assistant_message"] == "I'm doing well, thanks!"
        assert call_args.kwargs["metadata"]["intent"] == "greeting"

    @pytest.mark.asyncio
    async def test_get_session_summary(self, unified_api, mock_memory_router):
        """Test 9: Test session summary retrieval."""
        summary = await unified_api.get_session_summary()

        assert "session_id" in summary
        assert summary["session_id"] == "test_session"
        assert "short_term" in summary
        assert "long_term" in summary

        mock_memory_router.get_session_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check(self, unified_api, mock_redis_memory):
        """Test 10: Test health check for all layers."""
        health = await unified_api.health_check()

        assert "redis" in health
        assert "qdrant" in health
        assert "graphiti" in health

        # Redis should be healthy
        assert health["redis"]["healthy"] is True
        assert "latency_ms" in health["redis"]

        # Qdrant placeholder
        assert health["qdrant"]["healthy"] is True

        # Graphiti disabled
        assert health["graphiti"]["healthy"] is False
        assert health["graphiti"]["enabled"] is False

        # Verify Redis ping was called
        redis_client = await mock_redis_memory.client
        redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_redis_failure(self, unified_api, mock_redis_memory):
        """Test health check when Redis fails."""
        # Simulate Redis failure
        redis_client = await mock_redis_memory.client
        redis_client.ping = AsyncMock(side_effect=Exception("Connection failed"))

        health = await unified_api.health_check()

        assert health["redis"]["healthy"] is False
        assert "error" in health["redis"]

    def test_metrics_collection(self):
        """Test 11: Test Prometheus metrics collection."""
        with (
            patch("src.components.memory.unified_api.get_redis_memory"),
            patch("src.components.memory.unified_api.get_qdrant_client"),
            patch("src.components.memory.unified_api.get_memory_router"),
            patch("src.components.memory.unified_api.settings") as mock_settings,
        ):
            mock_settings.graphiti_enabled = False

            # API with metrics enabled
            api = UnifiedMemoryAPI(session_id="test", enable_metrics=True)

            assert api.enable_metrics is True
            assert api.store_counter is not None
            assert api.retrieve_counter is not None
            assert api.latency_histogram is not None

    @pytest.mark.asyncio
    async def test_store_error_handling(self, unified_api, mock_redis_memory):
        """Test error handling during store operations."""
        # Simulate store failure
        mock_redis_memory.store = AsyncMock(side_effect=Exception("Redis error"))

        result = await unified_api.store(
            key="test",
            value="test",
        )

        # Should return False instead of raising
        assert result is False

    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test 12: Test automatic retry logic for retrieve."""
        mock_router = AsyncMock()

        # Fail twice, succeed on third attempt
        mock_router.search_memory = AsyncMock(
            side_effect=[
                Exception("First failure"),
                Exception("Second failure"),
                {"short_term": [], "long_term": []},  # Success
            ]
        )

        with (
            patch("src.components.memory.unified_api.get_redis_memory"),
            patch("src.components.memory.unified_api.get_qdrant_client"),
            patch("src.components.memory.unified_api.get_memory_router", return_value=mock_router),
            patch("src.components.memory.unified_api.settings") as mock_settings,
        ):
            mock_settings.graphiti_enabled = False

            api = UnifiedMemoryAPI(enable_metrics=False)

            # Should retry and eventually succeed
            results = await api.retrieve(query="test")

            # Verify retries happened (should be called 3 times)
            assert mock_router.search_memory.call_count == 3
            assert results["total_results"] == 0

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test behavior when all retries are exhausted."""
        mock_router = AsyncMock()

        # Always fail
        mock_router.search_memory = AsyncMock(side_effect=Exception("Persistent failure"))

        with (
            patch("src.components.memory.unified_api.get_redis_memory"),
            patch("src.components.memory.unified_api.get_qdrant_client"),
            patch("src.components.memory.unified_api.get_memory_router", return_value=mock_router),
            patch("src.components.memory.unified_api.settings") as mock_settings,
        ):
            mock_settings.graphiti_enabled = False

            api = UnifiedMemoryAPI(enable_metrics=False)

            # Should fall back to empty results after retries
            results = await api.retrieve(query="test")

            # Should have tried 3 times
            assert mock_router.search_memory.call_count == 3

            # Should return graceful error response
            assert results["total_results"] == 0
            assert "error" in results
