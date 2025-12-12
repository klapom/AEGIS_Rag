"""Unit tests for entity/relationship extraction service.

Sprint 5: Feature 5.3 - Entity & Relationship Extraction
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.components.graph_rag.extraction_service import (
    ExtractionService,
    get_extraction_service,
)
from src.core.models import GraphEntity, GraphRelationship


class TestExtractionService:
    """Test extraction service initialization and methods."""

    @pytest.fixture
    def extraction_service(self):
        """Extraction service fixture."""
        with patch("src.components.graph_rag.extraction_service.AegisLLMProxy"):
            return ExtractionService(
                llm_model="llama3.2:8b",
                temperature=0.1,
                max_tokens=4096,
            )

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM proxy response generator."""
        from src.components.llm_proxy.models import LLMResponse

        def _response(json_data):
            return LLMResponse(
                content=json.dumps(json_data),
                provider="local_ollama",
                model="llama3.2:8b",
                tokens_used=100,
                cost_usd=0.0,
            )

        return _response

    def test_initialization(self, extraction_service):
        """Test extraction service initializes correctly."""
        assert extraction_service is not None
        assert extraction_service.llm_model == "llama3.2:8b"
        assert extraction_service.temperature == 0.1
        assert extraction_service.max_tokens == 4096

    def test_parse_json_response_valid(self, extraction_service):
        """Test JSON parsing with valid response."""
        response = '[{"name": "John", "type": "PERSON"}]'
        parsed = extraction_service._parse_json_response(response)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "John"
        assert parsed[0]["type"] == "PERSON"

    def test_parse_json_response_with_extra_text(self, extraction_service):
        """Test JSON parsing with extra text around JSON."""
        response = 'Here are the entities:\n[{"name": "John", "type": "PERSON"}]\nDone!'
        parsed = extraction_service._parse_json_response(response)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "John"

    def test_parse_json_response_invalid(self, extraction_service):
        """Test JSON parsing with invalid JSON raises ValueError."""
        response = "This is not JSON at all"
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            extraction_service._parse_json_response(response)

    def test_parse_json_response_empty(self, extraction_service):
        """Test JSON parsing with empty array."""
        response = "[]"
        parsed = extraction_service._parse_json_response(response)
        assert parsed == []

    @pytest.mark.asyncio
    async def test_extract_entities_success(self, extraction_service, mock_llm_response):
        """Test successful entity extraction."""
        mock_entities = [
            {
                "name": "John Smith",
                "type": "PERSON",
                "description": "Software engineer at Google",
            },
            {
                "name": "Google",
                "type": "ORGANIZATION",
                "description": "Technology company",
            },
        ]

        with patch.object(
            extraction_service.llm_proxy,
            "generate",
            new=AsyncMock(return_value=mock_llm_response(mock_entities)),
        ):
            text = "John Smith works at Google as a software engineer."
            entities = await extraction_service.extract_entities(text, "doc1")

            assert len(entities) == 2
            assert isinstance(entities[0], GraphEntity)
            assert entities[0].name == "John Smith"
            assert entities[0].type == "PERSON"
            assert entities[0].source_document == "doc1"
            assert entities[1].name == "Google"
            assert entities[1].type == "ORGANIZATION"

    @pytest.mark.asyncio
    async def test_extract_entities_empty_text(self, extraction_service, mock_llm_response):
        """Test entity extraction with empty text."""
        with patch.object(
            extraction_service.llm_proxy,
            "generate",
            new=AsyncMock(return_value=mock_llm_response([])),
        ):
            entities = await extraction_service.extract_entities("", "doc1")
            assert entities == []

    @pytest.mark.asyncio
    async def test_extract_entities_max_limit(self, extraction_service, mock_llm_response):
        """Test entity extraction respects max entities limit."""
        # Generate more entities than MAX_ENTITIES_PER_DOC
        mock_entities = [
            {"name": f"Entity{i}", "type": "CONCEPT", "description": f"Desc {i}"}
            for i in range(60)  # Exceeds limit of 50
        ]

        with patch.object(
            extraction_service.llm_proxy,
            "generate",
            new=AsyncMock(return_value=mock_llm_response(mock_entities)),
        ):
            entities = await extraction_service.extract_entities("test text", "doc1")
            assert len(entities) <= 50  # Should be capped at MAX_ENTITIES_PER_DOC

    @pytest.mark.asyncio
    async def test_extract_relationships_success(self, extraction_service, mock_llm_response):
        """Test successful relationship extraction."""
        entities = [
            GraphEntity(
                id="e1",
                name="John Smith",
                type="PERSON",
                description="Engineer",
            ),
            GraphEntity(
                id="e2",
                name="Google",
                type="ORGANIZATION",
                description="Company",
            ),
        ]

        mock_relationships = [
            {
                "source": "John Smith",
                "target": "Google",
                "type": "WORKS_AT",
                "description": "John Smith is employed by Google",
            }
        ]

        with patch.object(
            extraction_service.llm_proxy,
            "generate",
            new=AsyncMock(return_value=mock_llm_response(mock_relationships)),
        ):
            text = "John Smith works at Google."
            relationships = await extraction_service.extract_relationships(text, entities, "doc1")

            assert len(relationships) == 1
            assert isinstance(relationships[0], GraphRelationship)
            assert relationships[0].source == "John Smith"
            assert relationships[0].target == "Google"
            assert relationships[0].type == "WORKS_AT"
            assert relationships[0].source_document == "doc1"

    @pytest.mark.asyncio
    async def test_extract_relationships_no_entities(self, extraction_service):
        """Test relationship extraction with no entities returns empty list."""
        relationships = await extraction_service.extract_relationships("some text", [], "doc1")
        assert relationships == []

    @pytest.mark.asyncio
    async def test_extract_and_store(self, extraction_service, mock_llm_response):
        """Test combined entity and relationship extraction."""
        mock_entities = [
            {"name": "Alice", "type": "PERSON", "description": "Developer"},
            {"name": "Python", "type": "TECHNOLOGY", "description": "Programming language"},
        ]

        mock_relationships = [
            {
                "source": "Alice",
                "target": "Python",
                "type": "USES",
                "description": "Alice uses Python",
            }
        ]

        # Create a list of return values
        mock_responses = [
            mock_llm_response(mock_entities),
            mock_llm_response(mock_relationships),
        ]

        with patch.object(
            extraction_service.llm_proxy,
            "generate",
            new=AsyncMock(side_effect=mock_responses),
        ):
            result = await extraction_service.extract_and_store(
                "Alice uses Python for development", "doc1"
            )

            assert "entities" in result
            assert "relationships" in result
            assert result["entity_count"] == 2
            assert result["relationship_count"] == 1

    @pytest.mark.asyncio
    async def test_extract_batch(self, extraction_service, mock_llm_response):
        """Test batch extraction from multiple documents."""
        documents = [
            {"id": "doc1", "text": "Document 1 text"},
            {"id": "doc2", "text": "Document 2 text"},
        ]

        mock_entities = [{"name": "Entity1", "type": "CONCEPT", "description": "Test entity"}]
        mock_relationships = []

        # Create a list of return values for the mock
        mock_responses = [
            mock_llm_response(mock_entities),  # doc1 entities
            mock_llm_response(mock_relationships),  # doc1 relationships
            mock_llm_response(mock_entities),  # doc2 entities
            mock_llm_response(mock_relationships),  # doc2 relationships
        ]

        with patch.object(
            extraction_service.llm_proxy,
            "generate",
            new=AsyncMock(side_effect=mock_responses),
        ):
            result = await extraction_service.extract_batch(documents)

            assert result["total_documents"] == 2
            assert result["success_count"] == 2
            assert result["failed_count"] == 0
            assert len(result["entities"]) == 2  # 1 entity per document
            assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_extract_batch_with_failures(self, extraction_service, mock_llm_response):
        """Test batch extraction handles failures gracefully."""
        documents = [
            {"id": "doc1", "text": "Document 1 text"},
            {"id": "doc2", "text": "Document 2 text"},
        ]

        mock_entities = [{"name": "Entity1", "type": "CONCEPT", "description": "Test entity"}]

        # Create a list of return values - first doc succeeds, second fails
        mock_responses = [
            mock_llm_response(mock_entities),  # doc1 entities - succeeds
            mock_llm_response([]),  # doc1 relationships - succeeds
            Exception("Extraction failed"),  # doc2 entities - fails
        ]

        with patch.object(
            extraction_service.llm_proxy,
            "generate",
            new=AsyncMock(side_effect=mock_responses),
        ):
            result = await extraction_service.extract_batch(documents)

            assert result["total_documents"] == 2
            # First succeeds, second fails
            assert result["success_count"] == 1
            assert result["failed_count"] == 1

    def test_singleton_pattern(self):
        """Test singleton pattern for global instance."""
        instance1 = get_extraction_service()
        instance2 = get_extraction_service()
        assert instance1 is instance2


class TestExtractionServiceDomainAware:
    """Test extraction service domain-aware features (Sprint 45)."""

    @pytest.fixture
    def extraction_service(self):
        """Extraction service fixture."""
        with patch("src.components.graph_rag.extraction_service.AegisLLMProxy"):
            return ExtractionService(
                llm_model="llama3.2:8b",
                temperature=0.1,
                max_tokens=4096,
            )

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM proxy response generator."""
        from src.components.llm_proxy.models import LLMResponse

        def _response(json_data):
            return LLMResponse(
                content=json.dumps(json_data),
                provider="local_ollama",
                model="llama3.2:8b",
                tokens_used=100,
                cost_usd=0.0,
            )

        return _response

    @pytest.mark.asyncio
    async def test_get_extraction_prompts_with_domain(self, extraction_service):
        """Test getting extraction prompts with domain support (Feature 45.8).

        When domain-specific prompts are available, they should be returned
        instead of generic prompts.
        """
        # This test is placeholder for future domain-aware prompt selection
        # Currently all prompts use generic templates from extraction_prompts.py
        from src.prompts.extraction_prompts import (
            ENTITY_EXTRACTION_PROMPT,
            RELATIONSHIP_EXTRACTION_PROMPT,
        )

        # Generic prompts should contain placeholders
        assert "{text}" in ENTITY_EXTRACTION_PROMPT
        assert "{text}" in RELATIONSHIP_EXTRACTION_PROMPT
        assert "{entities}" in RELATIONSHIP_EXTRACTION_PROMPT

    @pytest.mark.asyncio
    async def test_entity_extraction_with_generic_prompts(
        self, extraction_service, mock_llm_response
    ):
        """Test entity extraction using generic extraction prompts."""
        mock_entities = [
            {
                "name": "TensorFlow",
                "type": "TECHNOLOGY",
                "description": "Machine learning framework",
            },
            {
                "name": "Google",
                "type": "ORGANIZATION",
                "description": "Technology company",
            },
        ]

        with patch.object(
            extraction_service.llm_proxy,
            "generate",
            new=AsyncMock(return_value=mock_llm_response(mock_entities)),
        ):
            text = "TensorFlow is a machine learning framework developed by Google."
            entities = await extraction_service.extract_entities(text, "ml_doc")

            assert len(entities) == 2
            assert entities[0].type == "TECHNOLOGY"
            assert entities[1].type == "ORGANIZATION"

    @pytest.mark.asyncio
    async def test_relationship_extraction_with_generic_prompts(
        self, extraction_service, mock_llm_response
    ):
        """Test relationship extraction using generic extraction prompts."""
        entities = [
            GraphEntity(id="e1", name="TensorFlow", type="TECHNOLOGY"),
            GraphEntity(id="e2", name="Google", type="ORGANIZATION"),
        ]

        mock_relationships = [
            {
                "source": "TensorFlow",
                "target": "Google",
                "type": "DEVELOPED_BY",
                "description": "TensorFlow is developed by Google",
            }
        ]

        with patch.object(
            extraction_service.llm_proxy,
            "generate",
            new=AsyncMock(return_value=mock_llm_response(mock_relationships)),
        ):
            text = "TensorFlow is a machine learning framework developed by Google."
            relationships = await extraction_service.extract_relationships(
                text, entities, "ml_doc"
            )

            assert len(relationships) == 1
            assert relationships[0].source == "TensorFlow"
            assert relationships[0].target == "Google"


class TestExtractionServiceIntegration:
    """Integration tests for extraction service with real Ollama."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_extraction(self):
        """Test extraction with real Ollama instance.

        NOTE: This test requires Ollama to be running locally.
        Skip this test if Ollama is not available.
        """
        pytest.skip("Integration test - requires Ollama running")

        service = ExtractionService()

        text = """
        John Smith is a software engineer at Google. He previously worked at Microsoft.
        Google is a technology company based in Mountain View, California.
        """

        # Extract entities
        entities = await service.extract_entities(text, "test_doc")

        # Should extract at least: John Smith, Google, Microsoft, Mountain View
        assert len(entities) >= 3
        entity_names = [e.name for e in entities]
        assert "John Smith" in entity_names or "Google" in entity_names

        # Extract relationships
        relationships = await service.extract_relationships(text, entities, "test_doc")

        # Should extract at least: John-WORKS_AT->Google
        assert len(relationships) >= 1
