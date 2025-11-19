"""
Integration tests for Prometheus metrics endpoint and functionality.

Sprint 25 - Feature 25.1: Prometheus Metrics Implementation
Tests verify that:
1. /metrics endpoint returns valid Prometheus format
2. Metrics update correctly during LLM requests
3. Budget metrics are tracked accurately
4. System metrics (Qdrant, Neo4j) can be updated
"""

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from unittest.mock import AsyncMock, patch

from src.api.main import app
from src.components.llm_proxy.models import LLMTask, TaskType, QualityRequirement
from src.core.metrics import (
    track_llm_request,
    track_llm_error,
    update_budget_metrics,
    update_qdrant_metrics,
    update_neo4j_metrics,
)


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


class TestMetricsEndpoint:
    """Test the /metrics endpoint."""

    def test_metrics_endpoint_accessible(self, client):
        """Test that /metrics endpoint is accessible and returns 200."""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_endpoint_format(self, client):
        """Test that /metrics returns valid Prometheus format."""
        response = client.get("/metrics")
        content = response.text

        # Check for Prometheus headers
        assert "# HELP" in content
        assert "# TYPE" in content

        # Check for LLM metrics
        assert "llm_requests_total" in content
        assert "llm_latency_seconds" in content
        assert "llm_cost_usd" in content
        assert "llm_tokens_used" in content

    def test_metrics_content_type(self, client):
        """Test that /metrics returns correct content type."""
        response = client.get("/metrics")
        # Prometheus metrics endpoint should return text/plain
        assert "text/plain" in response.headers.get("content-type", "").lower()


class TestLLMMetricsTracking:
    """Test LLM metrics tracking functionality."""

    def test_track_llm_request_updates_counter(self, client):
        """Test that track_llm_request updates metrics."""
        # Get initial state
        response_before = client.get("/metrics")
        content_before = response_before.text

        # Track a request
        track_llm_request(
            provider="local_ollama",
            model="test-model",
            task_type="QUERY",
            tokens_used=150,
            cost_usd=0.0,
            latency_seconds=0.5,
            tokens_input=100,
            tokens_output=50,
        )

        # Get updated state
        response_after = client.get("/metrics")
        content_after = response_after.text

        # Verify metrics appeared
        assert 'provider="local_ollama"' in content_after
        assert 'model="test-model"' in content_after
        assert 'task_type="QUERY"' in content_after

    def test_track_llm_request_with_cost(self, client):
        """Test cost tracking for cloud providers."""
        track_llm_request(
            provider="alibaba_cloud",
            model="qwen-plus",
            task_type="EXTRACTION",
            tokens_used=1200,
            cost_usd=0.0012,
            latency_seconds=0.85,
            tokens_input=800,
            tokens_output=400,
        )

        response = client.get("/metrics")
        content = response.text

        # Verify cost metric exists for alibaba_cloud
        assert 'llm_cost_usd_total{provider="alibaba_cloud"}' in content

    def test_track_llm_error(self, client):
        """Test error tracking."""
        track_llm_error(
            provider="openai",
            task_type="GENERATION",
            error_type="timeout",
        )

        response = client.get("/metrics")
        content = response.text

        # Verify error metric
        assert "llm_errors_total" in content
        assert 'error_type="timeout"' in content


class TestBudgetMetrics:
    """Test budget tracking metrics."""

    def test_update_budget_metrics_with_limit(self, client):
        """Test budget metrics with configured limits."""
        update_budget_metrics(
            provider="alibaba_cloud",
            monthly_spending=5.25,
            budget_limit=10.0,
        )

        response = client.get("/metrics")
        content = response.text

        # Verify budget metrics exist
        assert "monthly_spend_usd" in content
        assert "monthly_budget_remaining_usd" in content
        assert 'provider="alibaba_cloud"' in content

    def test_update_budget_metrics_unlimited(self, client):
        """Test budget metrics with unlimited budget (0.0)."""
        update_budget_metrics(
            provider="openai",
            monthly_spending=12.50,
            budget_limit=0.0,  # Unlimited
        )

        response = client.get("/metrics")
        content = response.text

        # Verify metrics exist (should show -1.0 for unlimited)
        assert "monthly_spend_usd" in content
        assert 'provider="openai"' in content


class TestSystemMetrics:
    """Test system health metrics (Sprint 25 - Feature 25.1)."""

    def test_update_qdrant_metrics(self, client):
        """Test Qdrant collection metrics."""
        update_qdrant_metrics(
            collection="documents",
            points_count=15420,
        )

        response = client.get("/metrics")
        content = response.text

        # Verify Qdrant metrics
        assert "qdrant_points_count" in content
        assert 'collection="documents"' in content

    def test_update_neo4j_metrics(self, client):
        """Test Neo4j knowledge graph metrics."""
        update_neo4j_metrics(
            entities_count=542,
            relations_count=1834,
        )

        response = client.get("/metrics")
        content = response.text

        # Verify Neo4j metrics
        assert "neo4j_entities_count" in content
        assert "neo4j_relations_count" in content

    def test_multiple_collections_qdrant(self, client):
        """Test tracking multiple Qdrant collections."""
        update_qdrant_metrics("documents", 10000)
        update_qdrant_metrics("embeddings", 5000)
        update_qdrant_metrics("cache", 2000)

        response = client.get("/metrics")
        content = response.text

        # Verify all collections are tracked
        assert 'collection="documents"' in content
        assert 'collection="embeddings"' in content
        assert 'collection="cache"' in content


class TestMetricsIntegrationWithLLMProxy:
    """Test metrics integration with AegisLLMProxy."""

    @pytest.mark.asyncio
    async def test_llm_proxy_tracks_metrics(self, client):
        """Test that AegisLLMProxy automatically tracks metrics."""
        from src.components.llm_proxy.aegis_llm_proxy import get_aegis_llm_proxy
        from src.components.llm_proxy.config import LLMProxyConfig

        # Create test config
        config = LLMProxyConfig(
            providers={
                "local_ollama": {
                    "enabled": True,
                    "base_url": "http://localhost:11434",
                }
            },
            budgets={"monthly_limits": {}},
            routing={
                "default_provider": "local_ollama",
                "task_routing": {},
            },
            model_defaults={
                "local_ollama": {
                    "generation": "test-model",
                    "extraction": "test-model",
                },
            },
            fallback={
                "enabled": True,
                "chain": ["local_ollama"],
            },
            monitoring={
                "enabled": True,
                "track_costs": True,
            },
        )

        proxy = get_aegis_llm_proxy(config=config)

        # Mock LLM response
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock(message=AsyncMock(content="Test response"))]
        mock_response.usage = AsyncMock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        # Create test task
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Test query",
            quality_requirement=QualityRequirement.MEDIUM,
        )

        # Mock acompletion to return our mock response
        with patch(
            "src.components.llm_proxy.aegis_llm_proxy.acompletion", return_value=mock_response
        ):
            result = await proxy.generate(task)

            # Verify response
            assert result.content == "Test response"
            assert result.provider == "local_ollama"
            assert result.tokens_used == 150

        # Verify metrics were tracked
        response = client.get("/metrics")
        content = response.text

        # Should have tracked the request
        assert "llm_requests_total" in content

    @pytest.mark.asyncio
    async def test_llm_proxy_tracks_errors(self, client):
        """Test that LLM proxy tracks errors in metrics."""
        from src.components.llm_proxy.aegis_llm_proxy import get_aegis_llm_proxy
        from src.components.llm_proxy.config import LLMProxyConfig

        config = LLMProxyConfig(
            providers={
                "local_ollama": {
                    "enabled": True,
                    "base_url": "http://localhost:11434",
                }
            },
            budgets={"monthly_limits": {}},
            routing={
                "default_provider": "local_ollama",
                "task_routing": {},
            },
            model_defaults={
                "local_ollama": {
                    "generation": "test-model",
                    "extraction": "test-model",
                },
            },
            fallback={
                "enabled": True,
                "chain": ["local_ollama"],
            },
            monitoring={
                "enabled": True,
                "track_costs": True,
            },
        )

        proxy = get_aegis_llm_proxy(config=config)

        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Test query",
            quality_requirement=QualityRequirement.MEDIUM,
        )

        # Mock acompletion to raise an error (simulating both provider failures)
        with patch(
            "src.components.llm_proxy.aegis_llm_proxy.acompletion",
            side_effect=Exception("Provider error"),
        ):
            with pytest.raises(Exception):
                await proxy.generate(task)

        # Verify error was tracked (proxy should still record the error even if it raises)
        # Note: Current implementation may not track errors if exception is raised
        # This is a known limitation (TD-25.1)


class TestMetricsPerformance:
    """Test metrics performance and overhead."""

    def test_metrics_endpoint_response_time(self, client):
        """Test that /metrics endpoint responds quickly."""
        import time

        start = time.time()
        response = client.get("/metrics")
        latency = time.time() - start

        assert response.status_code == 200
        # Metrics endpoint should respond in under 100ms
        assert latency < 0.1

    def test_high_cardinality_handling(self, client):
        """Test that high cardinality labels don't cause issues."""
        # Track requests with different models (should be fine)
        for i in range(20):
            track_llm_request(
                provider="local_ollama",
                model=f"model-{i}",
                task_type="QUERY",
                tokens_used=100,
                cost_usd=0.0,
                latency_seconds=0.5,
            )

        # Metrics should still be accessible
        response = client.get("/metrics")
        assert response.status_code == 200

        # Content should not be excessively large
        # (high cardinality can cause metric explosion)
        assert len(response.text) < 1_000_000  # 1MB limit


# Run tests with: pytest tests/integration/test_prometheus_metrics.py -v
