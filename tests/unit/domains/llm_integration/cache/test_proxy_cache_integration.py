"""
Integration tests for AegisLLMProxy with PromptCacheService.

Sprint 63 Feature 63.3: Redis Prompt Caching

Tests cover:
    - Cache integration with generate()
    - TTL selection based on task type
    - Cache bypass for streaming
    - Cache statistics via proxy
    - Namespace isolation in proxy context
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.domains.llm_integration.cache.models import CacheStats
from src.domains.llm_integration.models import (
    LLMResponse,
    LLMTask,
    QualityRequirement,
    TaskType,
)
from src.domains.llm_integration.proxy.aegis_llm_proxy import AegisLLMProxy


@pytest.fixture
def mock_cache_service():
    """Create a mock PromptCacheService."""
    cache = AsyncMock()
    cache.get_cached_response = AsyncMock(return_value=None)
    cache.cache_response = AsyncMock()
    cache.get_stats = AsyncMock(
        return_value=CacheStats(
            hits=10,
            misses=5,
            hit_rate=0.667,
            total_requests=15,
            cached_size_bytes=5000,
        )
    )
    cache.invalidate_namespace = AsyncMock(return_value=5)
    return cache


@pytest.fixture
def mock_config():
    """Create a mock LLM proxy config."""
    config = AsyncMock()
    config.is_provider_enabled.return_value = True
    config.get_budget_limit.return_value = 10.0
    config.routing = {"prefer_cloud": False}
    config.providers = {
        "local_ollama": {"base_url": "http://localhost:11434"},
    }
    config.budgets = {"monthly_limits": {}}
    return config


@pytest.fixture
def proxy_with_cache(mock_cache_service, mock_config):
    """Create AegisLLMProxy with mocked cache service."""
    with patch(
        "src.domains.llm_integration.proxy.aegis_llm_proxy.get_llm_proxy_config",
        return_value=mock_config,
    ), patch("src.domains.llm_integration.proxy.aegis_llm_proxy.CostTracker"), patch(
        "src.domains.llm_integration.proxy.aegis_llm_proxy.PromptCacheService",
        return_value=mock_cache_service,
    ):
        proxy = AegisLLMProxy(config=mock_config)
    return proxy, mock_cache_service


class TestCacheIntegrationWithProxy:
    """Test cache integration with AegisLLMProxy."""

    @pytest.mark.asyncio
    async def test_generate_cache_hit(self, proxy_with_cache):
        """Test that cache hits return immediately without LLM call."""
        proxy, cache_service = proxy_with_cache
        cached_response = "John Smith (Person) works at Acme Corp (Organization)"
        cache_service.get_cached_response.return_value = cached_response

        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract entities from text...",
            quality_requirement=QualityRequirement.MEDIUM,
        )

        with patch.object(proxy, "_execute_with_any_llm") as mock_execute:
            result = await proxy.generate(task, use_cache=True)

            # Verify cache was checked
            cache_service.get_cached_response.assert_called_once()

            # Verify LLM was NOT called (cache hit)
            mock_execute.assert_not_called()

            # Verify result from cache
            assert result.content == cached_response
            assert result.provider == "cache"
            assert result.cost_usd == 0.0
            assert result.tokens_used == 0

    @pytest.mark.asyncio
    async def test_generate_cache_miss_calls_llm(self, proxy_with_cache):
        """Test that cache misses trigger LLM call."""
        proxy, cache_service = proxy_with_cache
        cache_service.get_cached_response.return_value = None  # Cache miss

        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract entities from text...",
            quality_requirement=QualityRequirement.MEDIUM,
        )

        llm_response = LLMResponse(
            content="John Smith (Person), Acme Corp (Organization)",
            provider="local_ollama",
            model="llama3.2:8b",
            tokens_used=45,
            cost_usd=0.0,
        )

        with patch.object(
            proxy, "_execute_with_any_llm", return_value=llm_response
        ) as mock_execute, patch.object(proxy, "_track_metrics"):
            result = await proxy.generate(task, use_cache=True)

            # Verify cache was checked
            cache_service.get_cached_response.assert_called_once()

            # Verify LLM was called
            mock_execute.assert_called_once()

            # Verify response was cached
            cache_service.cache_response.assert_called_once()

            # Verify result from LLM
            assert result.content == llm_response.content
            assert result.provider == "local_ollama"

    @pytest.mark.asyncio
    async def test_generate_cache_disabled(self, proxy_with_cache):
        """Test that cache can be disabled per-request."""
        proxy, cache_service = proxy_with_cache
        cache_service.get_cached_response.return_value = "cached response"

        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract entities...",
            quality_requirement=QualityRequirement.MEDIUM,
        )

        llm_response = LLMResponse(
            content="LLM response",
            provider="local_ollama",
            model="llama3.2:8b",
            tokens_used=45,
            cost_usd=0.0,
        )

        with patch.object(
            proxy, "_execute_with_any_llm", return_value=llm_response
        ) as mock_execute, patch.object(proxy, "_track_metrics"):
            result = await proxy.generate(task, use_cache=False)

            # Verify cache was NOT checked
            cache_service.get_cached_response.assert_not_called()

            # Verify LLM was called
            mock_execute.assert_called_once()

            # Verify result from LLM (not cache)
            assert result.content == "LLM response"

    @pytest.mark.asyncio
    async def test_generate_streaming_skips_cache(self, proxy_with_cache):
        """Test that streaming responses bypass cache."""
        proxy, cache_service = proxy_with_cache

        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Generate text...",
        )

        with patch.object(proxy, "_execute_streaming") as mock_execute:

            async def stream_gen():
                yield {"content": "token1"}
                yield {"content": "token2"}

            mock_execute.return_value = stream_gen()

            # Streaming should bypass cache lookup
            async for _chunk in proxy.generate_streaming(task):
                pass

            # Verify cache was NOT checked for streaming
            cache_service.get_cached_response.assert_not_called()


class TestCacheTTLStrategy:
    """Test TTL selection based on task type."""

    def test_ttl_extraction_24_hours(self, proxy_with_cache):
        """Test that EXTRACTION tasks get 24-hour TTL."""
        proxy, _ = proxy_with_cache
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="test",
        )
        ttl = proxy._get_cache_ttl(task)
        assert ttl == 86400  # 24 hours

    def test_ttl_research_30_minutes(self, proxy_with_cache):
        """Test that RESEARCH tasks get 30-minute TTL."""
        proxy, _ = proxy_with_cache
        task = LLMTask(
            task_type=TaskType.RESEARCH,
            prompt="test",
        )
        ttl = proxy._get_cache_ttl(task)
        assert ttl == 1800  # 30 minutes

    def test_ttl_generation_1_hour(self, proxy_with_cache):
        """Test that GENERATION tasks get 1-hour TTL."""
        proxy, _ = proxy_with_cache
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="test",
        )
        ttl = proxy._get_cache_ttl(task)
        assert ttl == 3600  # 1 hour

    def test_ttl_answer_generation_1_hour(self, proxy_with_cache):
        """Test that ANSWER_GENERATION tasks get 1-hour TTL."""
        proxy, _ = proxy_with_cache
        task = LLMTask(
            task_type=TaskType.ANSWER_GENERATION,
            prompt="test",
        )
        ttl = proxy._get_cache_ttl(task)
        assert ttl == 3600

    def test_ttl_summarization_1_hour(self, proxy_with_cache):
        """Test that SUMMARIZATION tasks get 1-hour TTL."""
        proxy, _ = proxy_with_cache
        task = LLMTask(
            task_type=TaskType.SUMMARIZATION,
            prompt="test",
        )
        ttl = proxy._get_cache_ttl(task)
        assert ttl == 3600

    def test_ttl_default_1_hour(self, proxy_with_cache):
        """Test default TTL for unknown task types."""
        proxy, _ = proxy_with_cache
        task = LLMTask(
            task_type=TaskType.EMBEDDING,  # Not in TTL map
            prompt="test",
        )
        ttl = proxy._get_cache_ttl(task)
        assert ttl == 3600  # Default


class TestNamespaceIsolation:
    """Test namespace isolation in proxy context."""

    @pytest.mark.asyncio
    async def test_cache_with_namespace(self, proxy_with_cache):
        """Test that cache respects namespace parameter."""
        proxy, cache_service = proxy_with_cache
        cache_service.get_cached_response.return_value = "cached"

        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract...",
        )

        await proxy.generate(task, use_cache=True, namespace="tenant-1")

        # Verify namespace was passed to cache service
        cache_service.get_cached_response.assert_called_once()
        call_kwargs = cache_service.get_cached_response.call_args[1]
        assert call_kwargs["namespace"] == "tenant-1"

    @pytest.mark.asyncio
    async def test_cache_default_namespace(self, proxy_with_cache):
        """Test that default namespace is used when not specified."""
        proxy, cache_service = proxy_with_cache
        cache_service.get_cached_response.return_value = None

        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract...",
        )

        llm_response = LLMResponse(
            content="response",
            provider="local_ollama",
            model="test",
            tokens_used=10,
            cost_usd=0.0,
        )

        with patch.object(proxy, "_execute_with_any_llm", return_value=llm_response):
            with patch.object(proxy, "_track_metrics"):
                await proxy.generate(task, use_cache=True)

                # Verify default namespace was used
                cache_service.cache_response.assert_called_once()
                call_kwargs = cache_service.cache_response.call_args[1]
                assert call_kwargs["namespace"] == "default"


class TestProxyCacheStatistics:
    """Test cache statistics access via proxy."""

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, proxy_with_cache):
        """Test retrieving cache statistics from proxy."""
        proxy, cache_service = proxy_with_cache

        stats = await proxy.get_cache_stats()

        assert stats["hits"] == 10
        assert stats["misses"] == 5
        assert abs(stats["hit_rate"] - 0.667) < 0.001
        assert stats["total_requests"] == 15
        assert stats["cached_size_bytes"] == 5000

    @pytest.mark.asyncio
    async def test_invalidate_cache_namespace(self, proxy_with_cache):
        """Test invalidating cache by namespace via proxy."""
        proxy, cache_service = proxy_with_cache

        removed = await proxy.invalidate_cache_namespace("tenant-1")

        assert removed == 5
        cache_service.invalidate_namespace.assert_called_once_with("tenant-1")


class TestCacheErrorHandling:
    """Test error handling in cache integration."""

    @pytest.mark.asyncio
    async def test_cache_lookup_error_proceeds_to_llm(self, proxy_with_cache):
        """Test that cache lookup errors don't block LLM execution."""
        proxy, cache_service = proxy_with_cache
        cache_service.get_cached_response.side_effect = Exception("Redis error")

        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract...",
        )

        llm_response = LLMResponse(
            content="response from LLM",
            provider="local_ollama",
            model="test",
            tokens_used=10,
            cost_usd=0.0,
        )

        with patch.object(proxy, "_execute_with_any_llm", return_value=llm_response):
            with patch.object(proxy, "_track_metrics"):
                # Should not raise exception, should proceed to LLM
                result = await proxy.generate(task, use_cache=True)

                assert result.content == "response from LLM"

    @pytest.mark.asyncio
    async def test_cache_store_error_doesnt_block_response(self, proxy_with_cache):
        """Test that cache store errors don't block response."""
        proxy, cache_service = proxy_with_cache
        cache_service.get_cached_response.return_value = None  # Miss
        cache_service.cache_response.side_effect = Exception("Redis error")

        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract...",
        )

        llm_response = LLMResponse(
            content="response from LLM",
            provider="local_ollama",
            model="test",
            tokens_used=10,
            cost_usd=0.0,
        )

        with patch.object(proxy, "_execute_with_any_llm", return_value=llm_response):
            with patch.object(proxy, "_track_metrics"):
                # Should not raise exception, should return LLM response
                result = await proxy.generate(task, use_cache=True)

                assert result.content == "response from LLM"
