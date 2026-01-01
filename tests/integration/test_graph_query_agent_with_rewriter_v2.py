"""Integration tests for Graph Query Agent with Query Rewriter v2.

Sprint 69 Feature 69.5: Query Rewriter v2 - Graph-Intent Extraction (8 SP)

Tests cover:
- End-to-end graph query with intent extraction
- Integration between QueryRewriterV2 and GraphQueryAgent
- Graph traversal guided by Cypher hints
- Performance benchmarks for complete flow
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.graph_query_agent import GraphQueryAgent
from src.components.retrieval.query_rewriter_v2 import QueryRewriterV2
from src.domains.llm_integration.models import LLMResponse


@pytest.fixture
def mock_llm_proxy():
    """Create mock LLM proxy."""
    mock = AsyncMock()
    mock.generate = AsyncMock()
    return mock


@pytest.fixture
def mock_dual_level_search():
    """Create mock DualLevelSearch."""
    mock = AsyncMock()
    mock.local_search = AsyncMock()
    mock.global_search = AsyncMock()
    mock.hybrid_search = AsyncMock()
    return mock


@pytest.fixture
def mock_community_service():
    """Create mock SectionCommunityService."""
    mock = AsyncMock()
    mock.retrieve_by_community = AsyncMock()
    return mock


@pytest.fixture
def graph_query_agent_with_rewriter(
    mock_llm_proxy,
    mock_dual_level_search,
    mock_community_service,
):
    """Create GraphQueryAgent with QueryRewriterV2."""
    with patch("src.components.retrieval.query_rewriter_v2.get_aegis_llm_proxy") as mock_get_proxy:
        mock_get_proxy.return_value = mock_llm_proxy
        query_rewriter_v2 = QueryRewriterV2()

        agent = GraphQueryAgent(
            dual_level_search=mock_dual_level_search,
            community_service=mock_community_service,
            query_rewriter_v2=query_rewriter_v2,
        )
        return agent


class TestGraphQueryWithIntentExtraction:
    """Test graph query agent with intent extraction integration."""

    @pytest.mark.asyncio
    async def test_entity_relationships_query_flow(
        self,
        graph_query_agent_with_rewriter,
        mock_llm_proxy,
        mock_dual_level_search,
    ):
        """Test complete flow for entity relationships query."""
        # Arrange
        query = "How is authentication related to authorization?"
        state = {
            "query": query,
            "intent": "graph",
            "metadata": {},
        }

        # Mock intent extraction response
        intent_response = LLMResponse(
            content=json.dumps({
                "graph_intents": ["entity_relationships"],
                "entities_mentioned": ["authentication", "authorization"],
                "relationship_types": ["RELATES_TO"],
                "traversal_depth": None,
                "confidence": 0.9,
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=150,
            cost_usd=0.0,
        )
        mock_llm_proxy.generate.return_value = intent_response

        # Mock graph search response
        from src.core.models import GraphQueryResult

        mock_dual_level_search.hybrid_search.return_value = GraphQueryResult(
            query=query,
            answer="Authentication and authorization are related security concepts.",
            entities=[
                {"id": "e1", "name": "authentication", "type": "CONCEPT", "description": "User identity verification"},
                {"id": "e2", "name": "authorization", "type": "CONCEPT", "description": "Access control"},
            ],
            relationships=[
                {"id": "r1", "source": "e1", "target": "e2", "type": "RELATES_TO"},
            ],
            topics=[],
            context="Authentication verifies identity, authorization controls access.",
            mode="hybrid",
            metadata={},
        )

        # Act
        result_state = await graph_query_agent_with_rewriter.process(state)

        # Assert
        assert "graph_query_result" in result_state
        graph_result = result_state["graph_query_result"]

        # Verify intent extraction metadata
        assert "graph_intents" in graph_result["metadata"]
        assert "entity_relationships" in graph_result["metadata"]["graph_intents"]
        assert "authentication" in graph_result["metadata"]["entities_mentioned"]
        assert "authorization" in graph_result["metadata"]["entities_mentioned"]
        assert len(graph_result["metadata"]["cypher_hints"]) > 0
        assert graph_result["metadata"]["intent_confidence"] == 0.9

        # Verify graph search was executed
        assert graph_result["entities"] is not None
        assert len(graph_result["entities"]) > 0

    @pytest.mark.asyncio
    async def test_multi_hop_query_flow(
        self,
        graph_query_agent_with_rewriter,
        mock_llm_proxy,
        mock_dual_level_search,
    ):
        """Test complete flow for multi-hop query."""
        # Arrange
        query = "How does RAG influence LLM performance through retrieval quality?"
        state = {
            "query": query,
            "intent": "graph",
            "metadata": {},
        }

        # Mock intent extraction response
        intent_response = LLMResponse(
            content=json.dumps({
                "graph_intents": ["multi_hop"],
                "entities_mentioned": ["RAG", "LLM performance", "retrieval quality"],
                "relationship_types": [],
                "traversal_depth": 2,
                "confidence": 0.85,
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=180,
            cost_usd=0.0,
        )
        mock_llm_proxy.generate.return_value = intent_response

        # Mock graph search response
        from src.core.models import GraphQueryResult

        mock_dual_level_search.hybrid_search.return_value = GraphQueryResult(
            query=query,
            answer="RAG improves LLM performance by enhancing retrieval quality.",
            entities=[
                {"id": "e1", "name": "RAG", "type": "CONCEPT", "description": "Retrieval-Augmented Generation"},
                {"id": "e2", "name": "retrieval quality", "type": "METRIC", "description": "Quality of retrieved docs"},
                {"id": "e3", "name": "LLM performance", "type": "METRIC", "description": "LLM output quality"},
            ],
            relationships=[
                {"id": "r1", "source": "e1", "target": "e2", "type": "INFLUENCES"},
                {"id": "r2", "source": "e2", "target": "e3", "type": "IMPROVES"},
            ],
            topics=[],
            context="RAG → retrieval quality → LLM performance",
            mode="hybrid",
            metadata={},
        )

        # Act
        result_state = await graph_query_agent_with_rewriter.process(state)

        # Assert
        graph_result = result_state["graph_query_result"]

        # Verify multi-hop intent and traversal depth
        assert "multi_hop" in graph_result["metadata"]["graph_intents"]
        assert len(graph_result["metadata"]["cypher_hints"]) > 0
        # Should have path-based Cypher hint
        cypher_hints = graph_result["metadata"]["cypher_hints"]
        assert any("*1..2" in hint or "*1..3" in hint for hint in cypher_hints)

    @pytest.mark.asyncio
    async def test_community_discovery_query_flow(
        self,
        graph_query_agent_with_rewriter,
        mock_llm_proxy,
        mock_dual_level_search,
    ):
        """Test complete flow for community discovery query."""
        # Arrange
        query = "Find all entities related to vector search"
        state = {
            "query": query,
            "intent": "graph",
            "metadata": {},
        }

        # Mock intent extraction response
        intent_response = LLMResponse(
            content=json.dumps({
                "graph_intents": ["community_discovery"],
                "entities_mentioned": ["vector search"],
                "relationship_types": [],
                "traversal_depth": None,
                "confidence": 0.88,
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=160,
            cost_usd=0.0,
        )
        mock_llm_proxy.generate.return_value = intent_response

        # Mock graph search response
        from src.core.models import GraphQueryResult

        mock_dual_level_search.hybrid_search.return_value = GraphQueryResult(
            query=query,
            answer="Found community of entities related to vector search.",
            entities=[
                {"id": "e1", "name": "vector search", "type": "CONCEPT", "description": "Similarity search"},
                {"id": "e2", "name": "embeddings", "type": "CONCEPT", "description": "Vector representations"},
                {"id": "e3", "name": "Qdrant", "type": "TECHNOLOGY", "description": "Vector database"},
            ],
            relationships=[],
            topics=[],
            context="Vector search community includes embeddings, Qdrant, similarity metrics.",
            mode="hybrid",
            metadata={},
        )

        # Act
        result_state = await graph_query_agent_with_rewriter.process(state)

        # Assert
        graph_result = result_state["graph_query_result"]

        # Verify community intent
        assert "community_discovery" in graph_result["metadata"]["graph_intents"]
        assert "vector search" in graph_result["metadata"]["entities_mentioned"]
        assert len(graph_result["metadata"]["cypher_hints"]) > 0


class TestErrorHandlingIntegration:
    """Test error handling in integrated flow."""

    @pytest.mark.asyncio
    async def test_intent_extraction_failure_fallback(
        self,
        graph_query_agent_with_rewriter,
        mock_llm_proxy,
        mock_dual_level_search,
    ):
        """Test that graph query continues even if intent extraction fails."""
        # Arrange
        query = "Test query"
        state = {
            "query": query,
            "intent": "graph",
            "metadata": {},
        }

        # Mock LLM failure
        mock_llm_proxy.generate.side_effect = Exception("LLM error")

        # Mock graph search response (should still execute)
        from src.core.models import GraphQueryResult

        mock_dual_level_search.hybrid_search.return_value = GraphQueryResult(
            query=query,
            answer="Test answer",
            entities=[],
            relationships=[],
            topics=[],
            context="Test context",
            mode="hybrid",
            metadata={},
        )

        # Act
        result_state = await graph_query_agent_with_rewriter.process(state)

        # Assert - graph query should succeed despite intent extraction failure
        assert "graph_query_result" in result_state
        graph_result = result_state["graph_query_result"]

        # Intent extraction should have empty results
        assert graph_result["metadata"]["graph_intents"] == []
        assert graph_result["metadata"]["cypher_hints"] == []
        assert graph_result["metadata"]["intent_confidence"] == 0.0

        # But graph search should still have executed
        assert graph_result["answer"] == "Test answer"


class TestPerformanceIntegration:
    """Test performance characteristics of integrated flow."""

    @pytest.mark.asyncio
    async def test_latency_within_target(
        self,
        graph_query_agent_with_rewriter,
        mock_llm_proxy,
        mock_dual_level_search,
    ):
        """Test that total latency is within performance target."""
        # Arrange
        query = "How is X related to Y?"
        state = {
            "query": query,
            "intent": "graph",
            "metadata": {},
        }

        # Mock intent extraction response
        intent_response = LLMResponse(
            content=json.dumps({
                "graph_intents": ["entity_relationships"],
                "entities_mentioned": ["X", "Y"],
                "relationship_types": [],
                "traversal_depth": None,
                "confidence": 0.9,
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=150,
            cost_usd=0.0,
        )
        mock_llm_proxy.generate.return_value = intent_response

        # Mock graph search response
        from src.core.models import GraphQueryResult

        mock_dual_level_search.hybrid_search.return_value = GraphQueryResult(
            query=query,
            answer="X and Y are related.",
            entities=[],
            relationships=[],
            topics=[],
            context="Test",
            mode="hybrid",
            metadata={},
        )

        # Act
        result_state = await graph_query_agent_with_rewriter.process(state)

        # Assert
        graph_result = result_state["graph_query_result"]

        # Performance target: +80ms for intent extraction
        # In mock test, latency should be minimal
        intent_latency = graph_result["metadata"]["intent_extraction_latency_ms"]
        assert intent_latency < 100  # Mock should be fast

        # Total graph query latency should be reasonable
        total_latency = graph_result["metadata"]["latency_ms"]
        assert total_latency < 1000  # Well within target


class TestCypherHintUsage:
    """Test that Cypher hints are properly generated and available."""

    @pytest.mark.asyncio
    async def test_cypher_hints_available_in_result(
        self,
        graph_query_agent_with_rewriter,
        mock_llm_proxy,
        mock_dual_level_search,
    ):
        """Test that Cypher hints are available in result metadata."""
        # Arrange
        query = "How is A related to B?"
        state = {
            "query": query,
            "intent": "graph",
            "metadata": {},
        }

        # Mock intent extraction response
        intent_response = LLMResponse(
            content=json.dumps({
                "graph_intents": ["entity_relationships"],
                "entities_mentioned": ["A", "B"],
                "relationship_types": ["RELATES_TO"],
                "traversal_depth": None,
                "confidence": 0.9,
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=150,
            cost_usd=0.0,
        )
        mock_llm_proxy.generate.return_value = intent_response

        # Mock graph search response
        from src.core.models import GraphQueryResult

        mock_dual_level_search.hybrid_search.return_value = GraphQueryResult(
            query=query,
            answer="A and B are related.",
            entities=[],
            relationships=[],
            topics=[],
            context="Test",
            mode="hybrid",
            metadata={},
        )

        # Act
        result_state = await graph_query_agent_with_rewriter.process(state)

        # Assert
        graph_result = result_state["graph_query_result"]
        cypher_hints = graph_result["metadata"]["cypher_hints"]

        # Should have Cypher hints
        assert len(cypher_hints) > 0

        # Hints should be valid Cypher patterns
        for hint in cypher_hints:
            assert isinstance(hint, str)
            assert "MATCH" in hint
            assert "RETURN" in hint

        # Should mention entities
        hint_text = " ".join(cypher_hints)
        assert "A" in hint_text
        assert "B" in hint_text


class TestMultipleIntentsIntegration:
    """Test handling of multiple combined intents."""

    @pytest.mark.asyncio
    async def test_multiple_intents_generate_multiple_hints(
        self,
        graph_query_agent_with_rewriter,
        mock_llm_proxy,
        mock_dual_level_search,
    ):
        """Test that multiple intents generate multiple Cypher hints."""
        # Arrange
        query = "How are RAG and LLMs connected and what communities do they belong to?"
        state = {
            "query": query,
            "intent": "graph",
            "metadata": {},
        }

        # Mock intent extraction response with multiple intents
        intent_response = LLMResponse(
            content=json.dumps({
                "graph_intents": ["entity_relationships", "community_discovery"],
                "entities_mentioned": ["RAG", "LLMs"],
                "relationship_types": ["RELATES_TO"],
                "traversal_depth": None,
                "confidence": 0.87,
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=200,
            cost_usd=0.0,
        )
        mock_llm_proxy.generate.return_value = intent_response

        # Mock graph search response
        from src.core.models import GraphQueryResult

        mock_dual_level_search.hybrid_search.return_value = GraphQueryResult(
            query=query,
            answer="RAG and LLMs are related through retrieval mechanisms.",
            entities=[],
            relationships=[],
            topics=[],
            context="Test",
            mode="hybrid",
            metadata={},
        )

        # Act
        result_state = await graph_query_agent_with_rewriter.process(state)

        # Assert
        graph_result = result_state["graph_query_result"]

        # Should have multiple intents
        assert len(graph_result["metadata"]["graph_intents"]) == 2
        assert "entity_relationships" in graph_result["metadata"]["graph_intents"]
        assert "community_discovery" in graph_result["metadata"]["graph_intents"]

        # Should have multiple Cypher hints (at least one per intent)
        assert len(graph_result["metadata"]["cypher_hints"]) >= 2
