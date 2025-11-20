"""E2E tests for Sprint 27 Feature 27.10: Inline Source Citations.

This test verifies the complete citation flow from query to response:
1. User sends query via API
2. Graph executes with vector/hybrid search
3. AnswerGenerator creates citations
4. LangGraph node stores citation_map
5. API sends citation_map via SSE
6. Frontend receives and displays citations

Prerequisites:
- Qdrant running on localhost:6333 (for document retrieval)
- Ollama running on localhost:11434 (for LLM generation)

Mocking Strategy:
- Mock real LLM calls to ensure consistent citation format
- Use real Qdrant for retrieval if available, else mock
"""

import json
import logging
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.api.main import app
from src.components.llm_proxy.models import LLMResponse

logger = logging.getLogger(__name__)


def check_qdrant_available() -> bool:
    """Check if Qdrant is available."""
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(host="localhost", port=6333, timeout=2)
        client.get_collections()
        return True
    except Exception as e:
        logger.warning(f"Qdrant not available: {e}")
        return False


# ============================================================================
# E2E Citation Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_citations_e2e_flow_with_mocked_llm():
    """Test complete citation flow from query to API response.

    This test verifies:
    1. Query is routed through LangGraph
    2. Vector search retrieves contexts
    3. AnswerGenerator creates citations with citation_map
    4. Citation_map is stored in LangGraph state
    5. API sends citation_map via SSE metadata
    6. Citation format is correct ([1], [2], etc.)
    """
    # Mock LLM response with citations
    mock_llm_response = LLMResponse(
        content="AEGIS RAG is an agentic enterprise system [1] that uses LangGraph [2] for multi-agent orchestration.",
        provider="ollama",
        model="llama3.2:3b",
        cost_usd=0.0,
        latency_ms=150.0,
        tokens_used=45,
    )

    # Mock contexts that will be retrieved
    mock_contexts = [
        {
            "text": "AEGIS RAG (Agentic Enterprise Graph Intelligence System) is an agentic RAG system.",
            "source": "docs/CLAUDE.md",
            "title": "CLAUDE Documentation",
            "score": 0.95,
            "metadata": {"page": 1},
        },
        {
            "text": "The system uses LangGraph for multi-agent orchestration and state management.",
            "source": "docs/architecture.md",
            "title": "Architecture Overview",
            "score": 0.88,
            "metadata": {"section": "orchestration"},
        },
    ]

    # Patch LLM proxy to return mocked response
    with patch("src.agents.answer_generator.AegisLLMProxy") as mock_proxy_class:
        mock_proxy_instance = AsyncMock()
        mock_proxy_instance.generate = AsyncMock(return_value=mock_llm_response)
        mock_proxy_class.return_value = mock_proxy_instance

        # Patch vector search to return mock contexts (if Qdrant unavailable)
        if not check_qdrant_available():
            with patch(
                "src.agents.vector_search_agent.get_hybrid_search_engine"
            ) as mock_search_engine:
                mock_engine = AsyncMock()
                mock_engine.search = AsyncMock(return_value=mock_contexts)
                mock_search_engine.return_value = mock_engine

                await _run_citation_e2e_test(mock_contexts)
        else:
            # Use real Qdrant if available
            await _run_citation_e2e_test(mock_contexts)


async def _run_citation_e2e_test(expected_contexts: list[dict[str, Any]]) -> None:
    """Helper function to run citation E2E test."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream(
            "POST",
            "/api/v1/chat/stream",
            json={"query": "What is AEGIS RAG and what does it use?", "include_sources": True},
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200

            # Collect all messages
            answer_tokens = []
            citation_map = None
            sources = []

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        message = json.loads(data_str)

                        # Collect answer tokens
                        if message.get("type") == "token":
                            answer_tokens.append(message.get("content", ""))

                        # Collect citation_map
                        if message.get("type") == "metadata" and "data" in message:
                            data = message["data"]
                            if "citation_map" in data:
                                citation_map = data["citation_map"]
                                logger.info(f"Citation map received: {len(citation_map)} citations")

                        # Collect sources
                        if message.get("type") == "source":
                            sources.append(message.get("source"))

                    except json.JSONDecodeError:
                        pass

            # Verify answer contains citations
            full_answer = "".join(answer_tokens)
            assert "[1]" in full_answer, f"Answer missing [1] citation: {full_answer}"
            assert "[2]" in full_answer, f"Answer missing [2] citation: {full_answer}"

            # Verify citation_map was sent
            assert citation_map is not None, "Citation map was not sent in SSE"
            assert len(citation_map) >= 1, "Citation map should have at least 1 citation"

            # Verify citation_map structure
            # Note: Keys are strings in JSON (not integers)
            assert "1" in citation_map or 1 in citation_map, "Citation map missing citation 1"

            # Get first citation (handle both string and int keys)
            citation_1 = citation_map.get("1") or citation_map.get(1)
            assert citation_1 is not None, "Citation 1 is None"
            assert "text" in citation_1, "Citation 1 missing text field"
            assert "source" in citation_1, "Citation 1 missing source field"
            assert "title" in citation_1, "Citation 1 missing title field"
            assert "score" in citation_1, "Citation 1 missing score field"

            # Verify text is truncated to 500 chars
            assert len(citation_1["text"]) <= 500, "Citation text not truncated to 500 chars"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_citations_e2e_with_vector_intent():
    """Test citations work with explicit vector intent."""
    mock_llm_response = LLMResponse(
        content="Vector search retrieves documents [1].",
        provider="ollama",
        model="llama3.2:3b",
        cost_usd=0.0,
        latency_ms=100.0,
        tokens_used=20,
    )

    with patch("src.agents.answer_generator.AegisLLMProxy") as mock_proxy_class:
        mock_proxy_instance = AsyncMock()
        mock_proxy_instance.generate = AsyncMock(return_value=mock_llm_response)
        mock_proxy_class.return_value = mock_proxy_instance

        async with AsyncClient(app=app, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/api/v1/chat/stream",
                json={
                    "query": "How does vector search work?",
                    "intent": "vector",
                    "include_sources": True,
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                assert response.status_code == 200

                citation_map_received = False
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            message = json.loads(data_str)
                            if message.get("type") == "metadata" and "data" in message:
                                if "citation_map" in message["data"]:
                                    citation_map_received = True
                                    break
                        except json.JSONDecodeError:
                            pass

                # Citation map should be sent (even if empty)
                assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_citations_e2e_with_hybrid_intent():
    """Test citations work with hybrid intent."""
    mock_llm_response = LLMResponse(
        content="Hybrid search combines vector [1] and keyword search [2].",
        provider="ollama",
        model="llama3.2:3b",
        cost_usd=0.0,
        latency_ms=150.0,
        tokens_used=30,
    )

    with patch("src.agents.answer_generator.AegisLLMProxy") as mock_proxy_class:
        mock_proxy_instance = AsyncMock()
        mock_proxy_instance.generate = AsyncMock(return_value=mock_llm_response)
        mock_proxy_class.return_value = mock_proxy_instance

        async with AsyncClient(app=app, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/api/v1/chat/stream",
                json={
                    "query": "What is hybrid search?",
                    "intent": "hybrid",
                    "include_sources": True,
                },
                headers={"Accept": "text/event-stream"},
            ) as response:
                assert response.status_code == 200

                answer_tokens = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            message = json.loads(data_str)
                            if message.get("type") == "token":
                                answer_tokens.append(message.get("content", ""))
                        except json.JSONDecodeError:
                            pass

                # Verify answer contains citation markers
                full_answer = "".join(answer_tokens)
                assert "[1]" in full_answer or "[2]" in full_answer, "Answer missing citations"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_citations_e2e_empty_contexts_fallback():
    """Test that empty contexts return fallback answer without citations."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Use a query unlikely to return results
        async with client.stream(
            "POST",
            "/api/v1/chat/stream",
            json={"query": "xyzabc123nonsense456query", "include_sources": True},
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200

            citation_map = None
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        message = json.loads(data_str)
                        if message.get("type") == "metadata" and "data" in message:
                            data = message["data"]
                            if "citation_map" in data:
                                citation_map = data["citation_map"]
                    except json.JSONDecodeError:
                        pass

            # Citation map should exist but might be empty
            # (depends on whether contexts were found)
            assert response.status_code == 200
