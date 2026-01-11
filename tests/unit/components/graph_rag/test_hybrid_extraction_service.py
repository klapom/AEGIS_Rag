"""Unit tests for Hybrid Extraction Service.

Sprint 83 Feature 83.2: LLM Fallback & Retry Strategy (Rank 3)

Tests:
- SpaCy model loading and caching
- Multi-language NER extraction
- Language auto-detection
- Entity type mapping
- LLM relationship extraction delegation
- Full hybrid extraction flow
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.components.graph_rag.hybrid_extraction_service import (
    HybridExtractionService,
    get_hybrid_extraction_service,
)
from src.core.models import GraphEntity, GraphRelationship


class TestHybridExtractionService:
    """Test suite for HybridExtractionService."""

    @pytest.fixture
    def mock_llm_service(self) -> AsyncMock:
        """Create mock LLM extraction service."""
        mock_service = AsyncMock()
        mock_service.extract_relationships = AsyncMock(return_value=[])
        return mock_service

    @pytest.fixture
    def hybrid_service(self, mock_llm_service: AsyncMock) -> HybridExtractionService:
        """Create HybridExtractionService instance for testing."""
        return HybridExtractionService(mock_llm_service)

    def test_initialization(self, hybrid_service: HybridExtractionService) -> None:
        """Test HybridExtractionService initialization."""
        assert hybrid_service.llm_extraction_service is not None
        assert hybrid_service.supported_languages == ["de", "en", "fr", "es"]

    def test_load_spacy_model_invalid_language(
        self, hybrid_service: HybridExtractionService
    ) -> None:
        """Test _load_spacy_model raises error for invalid language."""
        with pytest.raises(ValueError, match="Unsupported language: zh"):
            hybrid_service._load_spacy_model("zh")

    def test_load_spacy_model_import_error(
        self, hybrid_service: HybridExtractionService
    ) -> None:
        """Test _load_spacy_model raises ImportError if SpaCy not installed."""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'spacy'")):
            with pytest.raises(ImportError, match="SpaCy is required"):
                hybrid_service._load_spacy_model("en")

    def test_load_spacy_model_model_not_found(
        self, hybrid_service: HybridExtractionService
    ) -> None:
        """Test _load_spacy_model raises OSError if SpaCy model not downloaded."""
        with patch("spacy.load", side_effect=OSError("Model not found")):
            with pytest.raises(OSError, match="SpaCy model"):
                hybrid_service._load_spacy_model("en")

    @patch("spacy.load")
    def test_load_spacy_model_success_and_caching(
        self, mock_spacy_load: MagicMock, hybrid_service: HybridExtractionService
    ) -> None:
        """Test _load_spacy_model loads and caches model."""
        mock_nlp = MagicMock()
        mock_nlp.pipe_names = ["tok2vec", "ner"]
        mock_spacy_load.return_value = mock_nlp

        # First load
        nlp1 = hybrid_service._load_spacy_model("en")
        assert nlp1 is mock_nlp
        assert mock_spacy_load.call_count == 1

        # Second load (should use cache)
        nlp2 = hybrid_service._load_spacy_model("en")
        assert nlp2 is mock_nlp
        assert mock_spacy_load.call_count == 1  # Not called again

    def test_detect_language_german(self, hybrid_service: HybridExtractionService) -> None:
        """Test _detect_language identifies German text."""
        text = "Der schnelle braun Fuchs springt über den faulen Hund."
        language = hybrid_service._detect_language(text)
        assert language == "de"

    def test_detect_language_french(self, hybrid_service: HybridExtractionService) -> None:
        """Test _detect_language identifies French text."""
        text = "Le renard brun rapide saute par-dessus le chien paresseux."
        language = hybrid_service._detect_language(text)
        assert language == "fr"

    def test_detect_language_spanish(self, hybrid_service: HybridExtractionService) -> None:
        """Test _detect_language identifies Spanish text."""
        text = "El rápido zorro marrón salta sobre el perro perezoso."
        language = hybrid_service._detect_language(text)
        assert language == "es"

    def test_detect_language_english_fallback(
        self, hybrid_service: HybridExtractionService
    ) -> None:
        """Test _detect_language defaults to English with no strong signal."""
        text = "This is a test sentence with no strong language markers."
        language = hybrid_service._detect_language(text)
        assert language == "en"

    @pytest.mark.asyncio
    @patch("spacy.load")
    async def test_extract_entities_with_spacy(
        self, mock_spacy_load: MagicMock, hybrid_service: HybridExtractionService
    ) -> None:
        """Test extract_entities_with_spacy extracts entities from text."""
        # Mock SpaCy NLP model
        mock_ent1 = MagicMock()
        mock_ent1.text = "Apple Inc."
        mock_ent1.label_ = "ORG"
        mock_ent1.start_char = 0
        mock_ent1.end_char = 10

        mock_ent2 = MagicMock()
        mock_ent2.text = "Cupertino"
        mock_ent2.label_ = "GPE"
        mock_ent2.start_char = 25
        mock_ent2.end_char = 34

        mock_doc = MagicMock()
        mock_doc.ents = [mock_ent1, mock_ent2]

        mock_nlp = MagicMock()
        mock_nlp.pipe_names = ["tok2vec", "ner"]
        mock_nlp.return_value = mock_doc

        mock_spacy_load.return_value = mock_nlp

        # Extract entities
        text = "Apple Inc. is located in Cupertino, California."
        entities = await hybrid_service.extract_entities_with_spacy(
            text=text,
            document_id="doc123",
            language="en",
        )

        # Assertions
        assert len(entities) == 2

        # First entity (Apple Inc.)
        assert entities[0].name == "Apple Inc."
        assert entities[0].type == "ORGANIZATION"
        assert entities[0].source_document == "doc123"
        assert entities[0].properties["spacy_label"] == "ORG"

        # Second entity (Cupertino)
        assert entities[1].name == "Cupertino"
        assert entities[1].type == "LOCATION"
        assert entities[1].properties["spacy_label"] == "GPE"

    @pytest.mark.asyncio
    @patch("spacy.load")
    async def test_extract_entities_with_spacy_auto_detect_language(
        self, mock_spacy_load: MagicMock, hybrid_service: HybridExtractionService
    ) -> None:
        """Test extract_entities_with_spacy auto-detects language."""
        # Mock SpaCy NLP model
        mock_doc = MagicMock()
        mock_doc.ents = []

        mock_nlp = MagicMock()
        mock_nlp.pipe_names = ["tok2vec", "ner"]
        mock_nlp.return_value = mock_doc

        mock_spacy_load.return_value = mock_nlp

        # Extract entities (German text, language auto-detect)
        text = "Der schnelle braun Fuchs springt über den faulen Hund."
        entities = await hybrid_service.extract_entities_with_spacy(
            text=text,
            document_id="doc456",
            language=None,  # Auto-detect
        )

        # Assertions
        assert isinstance(entities, list)
        # Language detection should have triggered (de_core_news_lg model)
        mock_spacy_load.assert_called_once_with("de_core_news_lg")

    @pytest.mark.asyncio
    async def test_extract_relationships_with_llm(
        self, hybrid_service: HybridExtractionService, mock_llm_service: AsyncMock
    ) -> None:
        """Test extract_relationships_with_llm delegates to LLM service."""
        # Mock entities
        entities = [
            GraphEntity(
                id="e1",
                name="Apple Inc.",
                type="ORGANIZATION",
                description="",
                properties={},
                source_document="doc123",
                confidence=1.0,
            ),
            GraphEntity(
                id="e2",
                name="Cupertino",
                type="LOCATION",
                description="",
                properties={},
                source_document="doc123",
                confidence=1.0,
            ),
        ]

        # Mock LLM service to return relationships
        mock_relationships = [
            GraphRelationship(
                id="r1",
                source="Apple Inc.",
                target="Cupertino",
                type="LOCATED_IN",
                description="",
                properties={},
                source_document="doc123",
                confidence=1.0,
            )
        ]
        mock_llm_service.extract_relationships = AsyncMock(return_value=mock_relationships)
        hybrid_service.llm_extraction_service = mock_llm_service

        # Extract relationships
        text = "Apple Inc. is located in Cupertino, California."
        relationships = await hybrid_service.extract_relationships_with_llm(
            text=text,
            entities=entities,
            document_id="doc123",
            domain="tech_docs",
        )

        # Assertions
        assert len(relationships) == 1
        assert relationships[0].source == "Apple Inc."
        assert relationships[0].target == "Cupertino"
        assert relationships[0].type == "LOCATED_IN"

        # Verify LLM service was called
        mock_llm_service.extract_relationships.assert_called_once_with(
            text=text,
            entities=entities,
            document_id="doc123",
            domain="tech_docs",
        )

    @pytest.mark.asyncio
    @patch("spacy.load")
    async def test_extract_hybrid_full_flow(
        self,
        mock_spacy_load: MagicMock,
        hybrid_service: HybridExtractionService,
        mock_llm_service: AsyncMock,
    ) -> None:
        """Test extract_hybrid performs full hybrid extraction flow."""
        # Mock SpaCy NLP model
        mock_ent = MagicMock()
        mock_ent.text = "Apple Inc."
        mock_ent.label_ = "ORG"
        mock_ent.start_char = 0
        mock_ent.end_char = 10

        mock_doc = MagicMock()
        mock_doc.ents = [mock_ent]

        mock_nlp = MagicMock()
        mock_nlp.pipe_names = ["tok2vec", "ner"]
        mock_nlp.return_value = mock_doc

        mock_spacy_load.return_value = mock_nlp

        # Mock LLM service
        mock_relationships = [
            GraphRelationship(
                id="r1",
                source="Apple Inc.",
                target="Cupertino",
                type="LOCATED_IN",
                description="",
                properties={},
                source_document="doc789",
                confidence=1.0,
            )
        ]
        mock_llm_service.extract_relationships = AsyncMock(return_value=mock_relationships)
        hybrid_service.llm_extraction_service = mock_llm_service

        # Extract hybrid
        text = "Apple Inc. is located in Cupertino, California."
        result = await hybrid_service.extract_hybrid(
            text=text,
            document_id="doc789",
            domain="tech_docs",
            language="en",
        )

        # Assertions
        assert result["entity_count"] == 1
        assert result["relationship_count"] == 1
        assert result["extraction_method"] == "hybrid_spacy_ner_llm"
        assert result["language"] == "en"

        assert len(result["entities"]) == 1
        assert result["entities"][0].name == "Apple Inc."

        assert len(result["relationships"]) == 1
        assert result["relationships"][0].type == "LOCATED_IN"


def test_get_hybrid_extraction_service() -> None:
    """Test get_hybrid_extraction_service factory function."""
    mock_llm_service = AsyncMock()
    hybrid_service = get_hybrid_extraction_service(mock_llm_service)

    assert isinstance(hybrid_service, HybridExtractionService)
    assert hybrid_service.llm_extraction_service is mock_llm_service
