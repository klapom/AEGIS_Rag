"""
Integration test fixtures with automatic LLM mocking for CI.

Sprint 52 Feature 52.4: CI/CD Pipeline Optimization
Provides automatic mocking of LLM and embedding services when running in CI
environments (GitHub Actions) where Ollama and GPU are not available.

Local development with real Ollama is unaffected (CI environment variable not set).

Key Features:
- Auto-detects CI environment via CI=true (GitHub Actions sets this)
- Mocks AegisLLMProxy for all LLM generation calls
- Mocks EmbeddingService for vector embeddings
- Does not interfere with local development (real Ollama used locally)
- Supports tests marked with @pytest.mark.requires_llm (skipped in CI)
- Supports tests marked with @pytest.mark.cloud (skipped in CI)
"""

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


def _is_ci_environment() -> bool:
    """
    Detect if running in CI environment.

    CI flag is set by GitHub Actions automatically.

    Returns:
        True if CI=true, False otherwise
    """
    return os.getenv("CI", "false").lower() == "true"


@pytest.fixture(autouse=True)
def auto_mock_llm_for_ci(monkeypatch):
    """
    Automatically mock AegisLLMProxy when running in CI.

    This fixture activates only when CI=true (set by GitHub Actions).
    Local development with real Ollama is unaffected.

    Mocked Response Structure:
        - content: str = "Mocked LLM response for CI testing"
        - provider: str = "mock"
        - model: str = "test-model"
        - tokens_used: int = 150
        - cost_usd: float = 0.0
        - latency_ms: float = 10.0

    Sprint 52.4: CI/CD Pipeline Optimization
    Related: ADR-033 (Multi-Cloud LLM Execution)
    """
    if not _is_ci_environment():
        yield  # Use real LLM in local development
        return

    try:
        from src.components.llm_proxy.aegis_llm_proxy import AegisLLMProxy
        from src.components.llm_proxy.models import LLMResponse

        # Create mock response matching LLMResponse schema
        mock_response = LLMResponse(
            content="Mocked LLM response for CI testing (Ollama unavailable)",
            provider="mock",
            model="test-model",
            tokens_used=150,
            cost_usd=0.0,
            latency_ms=10.0,
        )

        # Mock both sync and async generate methods
        monkeypatch.setattr(
            AegisLLMProxy,
            "generate",
            AsyncMock(return_value=mock_response),
        )

        # Also mock streaming method if it exists
        mock_stream = AsyncMock()
        mock_stream.__aiter__ = MagicMock(return_value=mock_stream)
        mock_stream.__anext__ = AsyncMock(
            side_effect=StopAsyncIteration,
            return_value=None,
        )
        monkeypatch.setattr(
            AegisLLMProxy,
            "generate_streaming",
            AsyncMock(return_value=mock_stream),
        )

        print("[CI MODE] AegisLLMProxy fully mocked for CI testing")
        yield

    except ImportError:
        # If module doesn't exist, skip silently
        yield


@pytest.fixture(autouse=True)
def auto_mock_embeddings_for_ci(monkeypatch):
    """
    Automatically mock EmbeddingService when running in CI.

    This fixture activates only when CI=true.
    Provides mock 1024-dim embeddings (BGE-M3 spec).

    Mocked Methods:
        - embed_text() -> list[float] (1024-dim)
        - embed_batch() -> list[list[float]]

    Sprint 52.4: CI/CD Pipeline Optimization
    """
    if not _is_ci_environment():
        yield  # Use real embeddings in local development
        return

    try:
        from src.components.shared.embedding_service import EmbeddingService

        def _mock_embed_text(text: str) -> list[float]:
            """Generate deterministic mock embedding from text."""
            # Deterministic embedding based on text hash for reproducibility
            hash_val = hash(text) % 256
            embedding = np.random.RandomState(hash_val).rand(1024).tolist()
            return embedding

        async def _mock_embed_batch(texts: list[str]) -> list[list[float]]:
            """Generate mock embeddings for batch of texts."""
            return [_mock_embed_text(text) for text in texts]

        # Patch embedding service methods
        monkeypatch.setattr(
            EmbeddingService,
            "embed_text",
            AsyncMock(side_effect=_mock_embed_text),
        )
        monkeypatch.setattr(
            EmbeddingService,
            "embed_batch",
            AsyncMock(side_effect=_mock_embed_batch),
        )

        # Ensure dimension is correct (BGE-M3 = 1024)
        monkeypatch.setattr(
            EmbeddingService,
            "get_embedding_dimension",
            MagicMock(return_value=1024),
        )

        print("[CI MODE] EmbeddingService mocked with 1024-dim vectors")
        yield

    except ImportError:
        # If module doesn't exist, skip silently
        yield


@pytest.fixture(autouse=True)
def skip_requires_llm_in_ci(request):
    """
    Skip tests marked with @pytest.mark.requires_llm in CI.

    These tests require real Ollama and should only run in local development.

    Sprint 52.4: CI/CD Pipeline Optimization
    """
    if _is_ci_environment() and "requires_llm" in request.keywords:
        pytest.skip("Test requires real Ollama (not available in CI)")


@pytest.fixture(autouse=True)
def skip_cloud_in_ci(request):
    """
    Skip tests marked with @pytest.mark.cloud in CI.

    Cloud API tests require API keys (DashScope, OpenAI, etc.)
    and should only run in local development or specific CI environments.

    Sprint 52.4: CI/CD Pipeline Optimization
    """
    if _is_ci_environment() and "cloud" in request.keywords:
        pytest.skip("Test requires cloud API keys (not available in CI)")
