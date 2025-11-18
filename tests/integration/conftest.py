"""
Integration test fixtures with automatic LLM mocking for CI.

Sprint 25 Feature 25.X: CI Pipeline Reliability
Provides automatic mocking of AegisLLMProxy when running in CI environments
(GitHub Actions) where Ollama is not available.

Local development with real Ollama is unaffected (CI=true not set locally).
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def mock_aegis_llm_proxy_for_ci(monkeypatch):
    """
    Automatically mock AegisLLMProxy when running in CI environments.

    This fixture activates only when CI=true (set by GitHub Actions).
    Local development with real Ollama will NOT be affected.

    Mocked Response Structure:
        - content: str = "Mocked LLM response for CI testing (Ollama unavailable)"
        - provider: str = "local_ollama"
        - model: str = "test-model"
        - tokens_used: int = 150
        - cost_usd: float = 0.0

    Usage:
        # In CI (GitHub Actions):
        # - CI=true is auto-set by GitHub Actions
        # - This fixture activates automatically (autouse=True)
        # - All AegisLLMProxy.complete() calls return mocked response

        # Local development:
        # - CI is not set (or CI=false)
        # - Fixture does nothing, real Ollama is used

    Sprint 25 Feature 25.X: CI LLM Mocking
    Related: ADR-033 (Multi-Cloud LLM Execution)
    """
    # Only mock if running in CI environment
    if os.getenv("CI") != "true":
        return  # Use real LLM in local development

    try:
        from src.components.llm_proxy.aegis_llm_proxy import AegisLLMProxy

        # Create standardized mock response matching AegisLLMProxy response format
        mock_response = MagicMock()
        mock_response.content = "Mocked LLM response for CI testing (Ollama unavailable)"
        mock_response.provider = "local_ollama"
        mock_response.model = "test-model"
        mock_response.tokens_used = 150
        mock_response.cost_usd = 0.0

        # Mock both sync and async completion methods
        mock_complete_async = AsyncMock(return_value=mock_response)

        # Patch class methods (all instances will use mocked methods)
        monkeypatch.setattr(AegisLLMProxy, "complete", mock_complete_async)
        monkeypatch.setattr(AegisLLMProxy, "acomplete", mock_complete_async)

        print("[CI MODE] AegisLLMProxy mocked - Ollama not available in CI")

    except ImportError:
        # If AegisLLMProxy doesn't exist yet, skip silently
        # (e.g., during early development or if module is deleted)
        pass
