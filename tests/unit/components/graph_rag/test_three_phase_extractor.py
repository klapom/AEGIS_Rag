"""Unit tests for Three-Phase Entity and Relation Extraction Pipeline.

Sprint 16: Coverage improvement - 19% → 60%

Tests cover:
- Extractor initialization with/without SpaCy
- Phase 1: SpaCy NER entity extraction
- Phase 2: Semantic deduplication (enabled/disabled)
- Phase 3: Gemma relation extraction
- End-to-end extraction pipeline
- Error handling and graceful degradation
- Regex fallback when SpaCy fails
- Configuration options
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock

# Import after mocking to avoid import errors
@pytest.fixture(autouse=True)
def mock_spacy():
    """Mock spacy module before imports."""
    mock_spacy_module = MagicMock()
    mock_spacy_module.load = MagicMock()

    with patch.dict("sys.modules", {"spacy": mock_spacy_module}):
        yield mock_spacy_module


@pytest.fixture
def mock_nlp():
    """Mock SpaCy NLP model."""
    mock = MagicMock()

    # Create mock entities
    mock_ent1 = MagicMock()
    mock_ent1.text = "Klaus Pommer"
    mock_ent1.label_ = "PERSON"

    mock_ent2 = MagicMock()
    mock_ent2.text = "Pommer IT-Consulting GmbH"
    mock_ent2.label_ = "ORG"

    mock_ent3 = MagicMock()
    mock_ent3.text = "Munich"
    mock_ent3.label_ = "GPE"

    mock_doc = MagicMock()
    mock_doc.ents = [mock_ent1, mock_ent2, mock_ent3]

    mock.return_value = mock_doc
    return mock


@pytest.fixture
def mock_deduplicator():
    """Mock semantic deduplicator."""
    mock = MagicMock()
    # Deduplicator reduces 3 entities to 2
    mock.deduplicate = MagicMock(side_effect=lambda entities: entities[:2])
    return mock


@pytest.fixture
def mock_relation_extractor():
    """Mock Gemma relation extractor."""
    mock = MagicMock()
    mock.extract = AsyncMock(return_value=[
        {
            "source": "Klaus Pommer",
            "target": "Pommer IT-Consulting GmbH",
            "type": "WORKS_AT",
            "description": "Klaus Pommer works at Pommer IT-Consulting GmbH"
        }
    ])
    return mock


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return "Klaus Pommer works at Pommer IT-Consulting GmbH in Munich. He specializes in RAG systems."


class TestThreePhaseExtractorInitialization:
    """Test ThreePhaseExtractor initialization."""

    def test_initialization_without_spacy(self):
        """Test that initialization fails without spacy installed."""
        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", False):
            from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

            with pytest.raises(ImportError) as exc_info:
                ThreePhaseExtractor()

            assert "spacy required" in str(exc_info.value).lower()
            assert "pip install spacy" in str(exc_info.value)

    def test_initialization_with_spacy(self, mock_nlp, mock_spacy):
        """Test successful initialization with SpaCy."""
        # Configure the module-level mock to return our mock_nlp
        mock_spacy.load.return_value = mock_nlp

        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config"):
                with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config"):
                    from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                    extractor = ThreePhaseExtractor()

                    assert extractor.nlp is not None
                    assert extractor.config is not None
                    # Verify spacy.load was called
                    mock_spacy.load.assert_called_once()

    def test_initialization_spacy_model_not_found(self, mock_spacy):
        """Test initialization fails when SpaCy model not downloaded."""
        # Configure the module-level mock to raise OSError
        mock_spacy.load.side_effect = OSError("Model not found")

        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

            with pytest.raises(OSError) as exc_info:
                ThreePhaseExtractor()

            assert "Model not found" in str(exc_info.value)

    def test_initialization_dedup_enabled(self, mock_nlp, mock_deduplicator, mock_spacy):
        """Test initialization with deduplication enabled."""
        # Configure the module-level mock to return our mock_nlp
        mock_spacy.load.return_value = mock_nlp

        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config", return_value=mock_deduplicator):
                with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config"):
                    from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                    extractor = ThreePhaseExtractor(enable_dedup=True)

                    assert extractor.deduplicator is not None
                    # Verify spacy.load was called
                    mock_spacy.load.assert_called_once()

    def test_initialization_dedup_disabled(self, mock_nlp):
        """Test initialization with deduplication disabled."""
        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load", return_value=mock_nlp):
                with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config"):
                    from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                    extractor = ThreePhaseExtractor(enable_dedup=False)

                    assert extractor.deduplicator is None

    def test_initialization_dedup_init_failure(self, mock_nlp):
        """Test graceful handling of deduplicator initialization failure."""
        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load", return_value=mock_nlp):
                with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config", side_effect=Exception("Dedup init failed")):
                    with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config"):
                        from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                        # Should not raise, continues without deduplicator
                        extractor = ThreePhaseExtractor(enable_dedup=True)

                        assert extractor.deduplicator is None


class TestPhase1SpaCyExtraction:
    """Test Phase 1: SpaCy NER entity extraction."""

    def test_extract_entities_spacy_success(self, mock_nlp):
        """Test successful entity extraction with SpaCy."""
        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load", return_value=mock_nlp):
                with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config"):
                    with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config"):
                        from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                        extractor = ThreePhaseExtractor()
                        extractor.nlp = mock_nlp

                        entities = extractor._extract_entities_spacy("Klaus Pommer works at Pommer IT-Consulting GmbH in Munich.")

                        assert len(entities) == 3
                        assert entities[0]["name"] == "Klaus Pommer"
                        assert entities[0]["type"] == "PERSON"
                        assert entities[0]["source"] == "spacy"

                        assert entities[1]["name"] == "Pommer IT-Consulting GmbH"
                        assert entities[1]["type"] == "ORGANIZATION"

                        assert entities[2]["name"] == "Munich"
                        assert entities[2]["type"] == "LOCATION"

    def test_extract_entities_spacy_type_mapping(self, mock_nlp):
        """Test SpaCy type mapping to LightRAG types."""
        # Create entities with different SpaCy types
        mock_ent_product = MagicMock()
        mock_ent_product.text = "iPhone"
        mock_ent_product.label_ = "PRODUCT"

        mock_ent_date = MagicMock()
        mock_ent_date.text = "2024"
        mock_ent_date.label_ = "DATE"

        mock_ent_unknown = MagicMock()
        mock_ent_unknown.text = "Something"
        mock_ent_unknown.label_ = "UNKNOWN_TYPE"

        mock_doc = MagicMock()
        mock_doc.ents = [mock_ent_product, mock_ent_date, mock_ent_unknown]

        mock_nlp_custom = MagicMock(return_value=mock_doc)

        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load", return_value=mock_nlp_custom):
                with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config"):
                    with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config"):
                        from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                        extractor = ThreePhaseExtractor()
                        extractor.nlp = mock_nlp_custom

                        entities = extractor._extract_entities_spacy("iPhone released in 2024 Something")

                        assert entities[0]["type"] == "PRODUCT"
                        assert entities[1]["type"] == "DATE"
                        assert entities[2]["type"] == "OTHER"  # Unknown types map to OTHER

    def test_extract_entities_spacy_empty_text(self, mock_nlp):
        """Test entity extraction with empty text."""
        mock_doc_empty = MagicMock()
        mock_doc_empty.ents = []
        mock_nlp_empty = MagicMock(return_value=mock_doc_empty)

        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load", return_value=mock_nlp_empty):
                with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config"):
                    with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config"):
                        from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                        extractor = ThreePhaseExtractor()
                        extractor.nlp = mock_nlp_empty

                        entities = extractor._extract_entities_spacy("")

                        assert len(entities) == 0


class TestPhase1RegexFallback:
    """Test Phase 1 regex fallback when SpaCy fails."""

    def test_regex_fallback_basic_extraction(self):
        """Test regex fallback extracts capitalized words."""
        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load"):
                with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config"):
                    with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config"):
                        from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                        extractor = ThreePhaseExtractor()

                        text = "Klaus Pommer works at Pommer Consulting in Munich and Berlin."
                        entities = extractor._extract_entities_regex_fallback(text)

                        # Should extract capitalized sequences
                        entity_names = [e["name"] for e in entities]
                        assert "Klaus Pommer" in entity_names
                        assert "Munich" in entity_names
                        assert all(e["source"] == "regex_fallback" for e in entities)
                        assert all(e["type"] == "ENTITY" for e in entities)

    def test_regex_fallback_deduplication(self):
        """Test regex fallback deduplicates extracted entities."""
        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load"):
                with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config"):
                    with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config"):
                        from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                        extractor = ThreePhaseExtractor()

                        # Repeated entity
                        text = "Munich is great. Munich has good weather. Munich is in Bavaria."
                        entities = extractor._extract_entities_regex_fallback(text)

                        # Should deduplicate "Munich"
                        entity_names = [e["name"] for e in entities]
                        assert entity_names.count("Munich") == 1


class TestPhase2Deduplication:
    """Test Phase 2: Semantic deduplication."""

    @pytest.mark.asyncio
    async def test_deduplication_enabled(self, mock_nlp, mock_deduplicator, mock_relation_extractor, sample_text):
        """Test extraction with deduplication enabled."""
        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load", return_value=mock_nlp):
                with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config", return_value=mock_deduplicator):
                    with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config", return_value=mock_relation_extractor):
                        from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                        extractor = ThreePhaseExtractor(enable_dedup=True)
                        extractor.nlp = mock_nlp

                        entities, relations = await extractor.extract(sample_text)

                        # Deduplicator should reduce 3 entities to 2
                        assert len(entities) == 2
                        mock_deduplicator.deduplicate.assert_called_once()

    @pytest.mark.asyncio
    async def test_deduplication_disabled(self, mock_nlp, mock_relation_extractor, sample_text):
        """Test extraction with deduplication disabled."""
        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load", return_value=mock_nlp):
                with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config", return_value=mock_relation_extractor):
                    from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                    extractor = ThreePhaseExtractor(enable_dedup=False)
                    extractor.nlp = mock_nlp

                    entities, relations = await extractor.extract(sample_text)

                    # Should keep all 3 raw entities (no deduplication)
                    assert len(entities) == 3

    @pytest.mark.asyncio
    async def test_deduplication_failure_graceful_degradation(self, mock_nlp, mock_deduplicator, mock_relation_extractor, sample_text):
        """Test graceful handling of deduplication failure."""
        mock_deduplicator.deduplicate = MagicMock(side_effect=Exception("Dedup failed"))

        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load", return_value=mock_nlp):
                with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config", return_value=mock_deduplicator):
                    with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config", return_value=mock_relation_extractor):
                        from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                        extractor = ThreePhaseExtractor(enable_dedup=True)
                        extractor.nlp = mock_nlp

                        # Should not raise, continues with raw entities
                        entities, relations = await extractor.extract(sample_text)

                        # Should return raw entities (3) when dedup fails
                        assert len(entities) == 3
                        assert len(relations) == 1


class TestPhase3RelationExtraction:
    """Test Phase 3: Gemma relation extraction."""

    @pytest.mark.asyncio
    async def test_relation_extraction_success(self, mock_nlp, mock_relation_extractor, sample_text):
        """Test successful relation extraction."""
        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load", return_value=mock_nlp):
                with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config"):
                    with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config", return_value=mock_relation_extractor):
                        from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                        extractor = ThreePhaseExtractor()
                        extractor.nlp = mock_nlp

                        entities, relations = await extractor.extract(sample_text)

                        assert len(relations) == 1
                        assert relations[0]["source"] == "Klaus Pommer"
                        assert relations[0]["target"] == "Pommer IT-Consulting GmbH"
                        assert relations[0]["type"] == "WORKS_AT"
                        mock_relation_extractor.extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_relation_extraction_failure_graceful_degradation(self, mock_nlp, mock_relation_extractor, sample_text):
        """Test graceful handling of relation extraction failure."""
        mock_relation_extractor.extract = AsyncMock(side_effect=Exception("Relation extraction failed"))

        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load", return_value=mock_nlp):
                with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config"):
                    with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config", return_value=mock_relation_extractor):
                        from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                        extractor = ThreePhaseExtractor()
                        extractor.nlp = mock_nlp

                        # Should not raise, continues with empty relations
                        entities, relations = await extractor.extract(sample_text)

                        assert len(entities) == 3
                        assert len(relations) == 0  # Empty relations on failure


class TestEndToEndExtraction:
    """Test complete end-to-end extraction pipeline."""

    @pytest.mark.asyncio
    async def test_complete_extraction_pipeline(self, mock_nlp, mock_deduplicator, mock_relation_extractor, sample_text):
        """Test complete 3-phase extraction pipeline."""
        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load", return_value=mock_nlp):
                with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config", return_value=mock_deduplicator):
                    with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config", return_value=mock_relation_extractor):
                        from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                        extractor = ThreePhaseExtractor()
                        extractor.nlp = mock_nlp

                        entities, relations = await extractor.extract(sample_text, document_id="test_doc_001")

                        # Verify all phases executed
                        assert len(entities) == 2  # After deduplication
                        assert len(relations) == 1
                        mock_deduplicator.deduplicate.assert_called_once()
                        mock_relation_extractor.extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_extraction_with_spacy_failure_uses_regex_fallback(self, mock_relation_extractor, sample_text):
        """Test that SpaCy failure triggers regex fallback."""
        mock_nlp_failing = MagicMock(side_effect=Exception("SpaCy processing failed"))

        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load", return_value=mock_nlp_failing):
                with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config"):
                    with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config", return_value=mock_relation_extractor):
                        from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

                        extractor = ThreePhaseExtractor()
                        extractor.nlp = mock_nlp_failing

                        # Should use regex fallback
                        entities, relations = await extractor.extract(sample_text)

                        # Should have entities from regex fallback
                        assert len(entities) > 0
                        assert all(e["source"] == "regex_fallback" for e in entities)


class TestConvenienceFunction:
    """Test convenience function for extraction."""

    @pytest.mark.asyncio
    async def test_extract_with_three_phase_convenience_function(self, mock_nlp, mock_relation_extractor):
        """Test convenience function for three-phase extraction."""
        with patch("src.components.graph_rag.three_phase_extractor.SPACY_AVAILABLE", True):
            with patch("spacy.load", return_value=mock_nlp):
                with patch("src.components.graph_rag.three_phase_extractor.create_deduplicator_from_config"):
                    with patch("src.components.graph_rag.three_phase_extractor.create_relation_extractor_from_config", return_value=mock_relation_extractor):
                        from src.components.graph_rag.three_phase_extractor import extract_with_three_phase

                        text = "Klaus Pommer works at Pommer IT-Consulting GmbH."
                        entities, relations = await extract_with_three_phase(text, document_id="test_doc")

                        assert len(entities) > 0
                        assert isinstance(entities, list)
                        assert isinstance(relations, list)
