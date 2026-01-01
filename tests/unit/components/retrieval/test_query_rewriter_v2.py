"""Unit tests for Query Rewriter v2 - Graph Intent Extraction.

Sprint 69 Feature 69.5: Query Rewriter v2 - Graph-Intent Extraction (8 SP)

Tests cover:
- LLM-based graph intent extraction
- Cypher hint generation for various intent types
- Edge cases and error handling
- Performance benchmarks
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.retrieval.query_rewriter_v2 import (
    GraphIntentResult,
    QueryRewriterV2,
    extract_graph_intents,
    get_query_rewriter_v2,
)
from src.domains.llm_integration.models import LLMResponse


@pytest.fixture
def mock_llm_proxy():
    """Create mock LLM proxy."""
    mock = AsyncMock()
    mock.generate = AsyncMock()
    return mock


@pytest.fixture
def query_rewriter_v2(mock_llm_proxy):
    """Create QueryRewriterV2 instance with mocked LLM."""
    with patch("src.components.retrieval.query_rewriter_v2.get_aegis_llm_proxy") as mock_get_proxy:
        mock_get_proxy.return_value = mock_llm_proxy
        rewriter = QueryRewriterV2()
        return rewriter


class TestGraphIntentExtraction:
    """Test graph intent extraction functionality."""

    @pytest.mark.asyncio
    async def test_entity_relationships_intent(self, query_rewriter_v2, mock_llm_proxy):
        """Test extraction of entity_relationships intent."""
        # Arrange
        query = "How is authentication related to authorization?"
        llm_response = LLMResponse(
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
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert
        assert result.query == query
        assert "entity_relationships" in result.graph_intents
        assert "authentication" in result.entities_mentioned
        assert "authorization" in result.entities_mentioned
        assert "RELATES_TO" in result.relationship_types
        assert result.confidence == 0.9
        assert len(result.cypher_hints) > 0
        assert "authentication" in result.cypher_hints[0]
        assert "authorization" in result.cypher_hints[0]

    @pytest.mark.asyncio
    async def test_multi_hop_intent(self, query_rewriter_v2, mock_llm_proxy):
        """Test extraction of multi_hop intent."""
        # Arrange
        query = "How does RAG influence LLM performance through retrieval quality?"
        llm_response = LLMResponse(
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
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert
        assert "multi_hop" in result.graph_intents
        assert result.traversal_depth == 2
        assert len(result.cypher_hints) > 0
        # Should have path-based Cypher hint
        assert any("*1..2" in hint or "*1..3" in hint for hint in result.cypher_hints)

    @pytest.mark.asyncio
    async def test_community_discovery_intent(self, query_rewriter_v2, mock_llm_proxy):
        """Test extraction of community_discovery intent."""
        # Arrange
        query = "Find all entities related to vector search"
        llm_response = LLMResponse(
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
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert
        assert "community_discovery" in result.graph_intents
        assert "vector search" in result.entities_mentioned
        assert len(result.cypher_hints) > 0
        # Should have community detection hint
        assert any("community" in hint.lower() or "collect" in hint for hint in result.cypher_hints)

    @pytest.mark.asyncio
    async def test_temporal_patterns_intent(self, query_rewriter_v2, mock_llm_proxy):
        """Test extraction of temporal_patterns intent."""
        # Arrange
        query = "How has the RAG architecture evolved over time?"
        llm_response = LLMResponse(
            content=json.dumps({
                "graph_intents": ["temporal_patterns"],
                "entities_mentioned": ["RAG architecture"],
                "relationship_types": [],
                "traversal_depth": None,
                "confidence": 0.82,
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=170,
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert
        assert "temporal_patterns" in result.graph_intents
        assert len(result.cypher_hints) > 0
        # Should have timestamp-based hint
        assert any("timestamp" in hint.lower() for hint in result.cypher_hints)

    @pytest.mark.asyncio
    async def test_attribute_search_intent(self, query_rewriter_v2, mock_llm_proxy):
        """Test extraction of attribute_search intent."""
        # Arrange
        query = "What is the definition of RAG?"
        llm_response = LLMResponse(
            content=json.dumps({
                "graph_intents": ["attribute_search"],
                "entities_mentioned": ["RAG"],
                "relationship_types": [],
                "traversal_depth": None,
                "confidence": 0.92,
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=140,
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert
        assert "attribute_search" in result.graph_intents
        assert "RAG" in result.entities_mentioned
        assert len(result.cypher_hints) > 0
        # Should have property-based hint
        assert any("properties" in hint or "description" in hint for hint in result.cypher_hints)

    @pytest.mark.asyncio
    async def test_multiple_intents(self, query_rewriter_v2, mock_llm_proxy):
        """Test extraction of multiple combined intents."""
        # Arrange
        query = "How are RAG and LLMs connected and what communities do they belong to?"
        llm_response = LLMResponse(
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
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert
        assert "entity_relationships" in result.graph_intents
        assert "community_discovery" in result.graph_intents
        assert len(result.cypher_hints) >= 2  # Should have hints for both intents


class TestCypherHintGeneration:
    """Test Cypher hint generation for various patterns."""

    @pytest.mark.asyncio
    async def test_entity_relationship_cypher_hint(self, query_rewriter_v2, mock_llm_proxy):
        """Test Cypher hint for entity relationships."""
        # Arrange
        query = "How is X related to Y?"
        llm_response = LLMResponse(
            content=json.dumps({
                "graph_intents": ["entity_relationships"],
                "entities_mentioned": ["X", "Y"],
                "relationship_types": ["RELATES_TO"],
                "traversal_depth": None,
                "confidence": 0.9,
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=150,
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert
        assert len(result.cypher_hints) > 0
        hint = result.cypher_hints[0]
        assert "MATCH" in hint
        assert "Entity" in hint
        assert ":RELATES_TO" in hint
        assert "X" in hint
        assert "Y" in hint

    @pytest.mark.asyncio
    async def test_multi_hop_cypher_hint(self, query_rewriter_v2, mock_llm_proxy):
        """Test Cypher hint for multi-hop traversal."""
        # Arrange
        query = "Find path from A to B"
        llm_response = LLMResponse(
            content=json.dumps({
                "graph_intents": ["multi_hop"],
                "entities_mentioned": ["A", "B"],
                "relationship_types": [],
                "traversal_depth": 3,
                "confidence": 0.85,
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=160,
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert
        assert len(result.cypher_hints) > 0
        hint = result.cypher_hints[0]
        assert "MATCH path" in hint
        assert "*1..3" in hint  # Traversal depth
        assert "A" in hint
        assert "B" in hint

    @pytest.mark.asyncio
    async def test_community_cypher_hint_with_entity(self, query_rewriter_v2, mock_llm_proxy):
        """Test Cypher hint for community discovery with specific entity."""
        # Arrange
        query = "Find community around RAG"
        llm_response = LLMResponse(
            content=json.dumps({
                "graph_intents": ["community_discovery"],
                "entities_mentioned": ["RAG"],
                "relationship_types": [],
                "traversal_depth": None,
                "confidence": 0.88,
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=150,
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert
        assert len(result.cypher_hints) > 0
        hint = result.cypher_hints[0]
        assert "seed" in hint
        assert "community" in hint or "collect" in hint
        assert "RAG" in hint


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, query_rewriter_v2, mock_llm_proxy):
        """Test handling of invalid JSON from LLM."""
        # Arrange
        query = "Test query"
        llm_response = LLMResponse(
            content="This is not valid JSON",
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=50,
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert - should return empty result
        assert result.query == query
        assert result.graph_intents == []
        assert result.entities_mentioned == []
        assert result.confidence == 0.0
        assert result.cypher_hints == []

    @pytest.mark.asyncio
    async def test_llm_exception(self, query_rewriter_v2, mock_llm_proxy):
        """Test handling of LLM generation exception."""
        # Arrange
        query = "Test query"
        mock_llm_proxy.generate.side_effect = Exception("LLM error")

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert - should return empty result
        assert result.query == query
        assert result.graph_intents == []
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_markdown_wrapped_json(self, query_rewriter_v2, mock_llm_proxy):
        """Test handling of JSON wrapped in markdown code blocks."""
        # Arrange
        query = "Test query"
        json_content = {
            "graph_intents": ["entity_relationships"],
            "entities_mentioned": ["A", "B"],
            "relationship_types": [],
            "traversal_depth": None,
            "confidence": 0.8,
        }
        llm_response = LLMResponse(
            content=f"```json\n{json.dumps(json_content)}\n```",
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=150,
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert - should parse successfully
        assert "entity_relationships" in result.graph_intents
        assert "A" in result.entities_mentioned
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_missing_optional_fields(self, query_rewriter_v2, mock_llm_proxy):
        """Test handling of missing optional fields in LLM response."""
        # Arrange
        query = "Test query"
        llm_response = LLMResponse(
            content=json.dumps({
                "graph_intents": ["entity_relationships"],
                # Missing: entities_mentioned, relationship_types, etc.
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=100,
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert - should fill in defaults
        assert "entity_relationships" in result.graph_intents
        assert result.entities_mentioned == []
        assert result.confidence == 0.5  # Default


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_latency_tracking(self, query_rewriter_v2, mock_llm_proxy):
        """Test that latency is tracked correctly."""
        # Arrange
        query = "Test query"
        llm_response = LLMResponse(
            content=json.dumps({
                "graph_intents": ["entity_relationships"],
                "entities_mentioned": ["A"],
                "relationship_types": [],
                "traversal_depth": None,
                "confidence": 0.8,
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=150,
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert
        assert result.latency_ms > 0
        # Performance target: <200ms (including LLM overhead of +80ms)
        # In mock test, this should be very fast
        assert result.latency_ms < 100  # Mock should be near-instant


class TestSingletonAndFactory:
    """Test singleton pattern and factory functions."""

    def test_get_query_rewriter_v2_singleton(self):
        """Test get_query_rewriter_v2 returns singleton."""
        with patch("src.components.retrieval.query_rewriter_v2.get_aegis_llm_proxy"):
            rewriter1 = get_query_rewriter_v2()
            rewriter2 = get_query_rewriter_v2()
            # Should return same instance when no classifier provided
            assert rewriter1 is rewriter2

    def test_get_query_rewriter_v2_with_classifier(self):
        """Test get_query_rewriter_v2 with custom classifier."""
        with patch("src.components.retrieval.query_rewriter_v2.get_aegis_llm_proxy"):
            mock_classifier = MagicMock()
            rewriter = get_query_rewriter_v2(intent_classifier=mock_classifier)
            # Should return new instance with classifier
            assert rewriter is not None
            assert rewriter.intent_classifier is mock_classifier

    @pytest.mark.asyncio
    async def test_extract_graph_intents_convenience_function(self):
        """Test extract_graph_intents convenience function."""
        with patch("src.components.retrieval.query_rewriter_v2.get_aegis_llm_proxy") as mock_get_proxy:
            mock_llm = AsyncMock()
            mock_get_proxy.return_value = mock_llm
            mock_llm.generate.return_value = LLMResponse(
                content=json.dumps({
                    "graph_intents": ["entity_relationships"],
                    "entities_mentioned": ["A"],
                    "relationship_types": [],
                    "traversal_depth": None,
                    "confidence": 0.8,
                }),
                provider="ollama",
                model="llama3.2:8b",
                tokens_used=150,
            )

            # Act
            result = await extract_graph_intents("Test query")

            # Assert
            assert result is not None
            assert "entity_relationships" in result.graph_intents


class TestCypherHintQuality:
    """Test quality and correctness of Cypher hints."""

    @pytest.mark.asyncio
    async def test_cypher_hint_syntax_valid(self, query_rewriter_v2, mock_llm_proxy):
        """Test that generated Cypher hints have valid syntax."""
        # Arrange
        query = "How is A related to B?"
        llm_response = LLMResponse(
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
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert - basic syntax checks
        for hint in result.cypher_hints:
            assert "MATCH" in hint
            assert "RETURN" in hint
            # Should have balanced parentheses
            assert hint.count("(") == hint.count(")")
            # Should have balanced brackets
            assert hint.count("[") == hint.count("]")

    @pytest.mark.asyncio
    async def test_no_cypher_hints_for_empty_intents(self, query_rewriter_v2, mock_llm_proxy):
        """Test that no Cypher hints generated for empty intents."""
        # Arrange
        query = "Test query"
        llm_response = LLMResponse(
            content=json.dumps({
                "graph_intents": [],
                "entities_mentioned": [],
                "relationship_types": [],
                "traversal_depth": None,
                "confidence": 0.5,
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=100,
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert
        assert result.cypher_hints == []

    @pytest.mark.asyncio
    async def test_cypher_hints_entity_escaping(self, query_rewriter_v2, mock_llm_proxy):
        """Test that entity names with special characters are handled safely."""
        # Arrange
        query = "How is 'auth-system' related to 'user-mgmt'?"
        llm_response = LLMResponse(
            content=json.dumps({
                "graph_intents": ["entity_relationships"],
                "entities_mentioned": ["auth-system", "user-mgmt"],
                "relationship_types": [],
                "traversal_depth": None,
                "confidence": 0.85,
            }),
            provider="ollama",
            model="llama3.2:8b",
            tokens_used=150,
        )
        mock_llm_proxy.generate.return_value = llm_response

        # Act
        result = await query_rewriter_v2.extract_graph_intents(query)

        # Assert
        assert len(result.cypher_hints) > 0
        # Should handle hyphens in entity names
        hint = result.cypher_hints[0]
        assert "auth-system" in hint or "auth" in hint
        assert "user-mgmt" in hint or "user" in hint
