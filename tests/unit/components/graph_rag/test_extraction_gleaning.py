"""Unit tests for gleaning multi-pass entity extraction.

Sprint 83: Feature 83.3 - Gleaning Multi-Pass Extraction (TD-100)

Tests cover:
- Gleaning disabled (gleaning_steps=0)
- Gleaning enabled with early termination
- Gleaning with multiple rounds
- Completeness check (YES/NO logit bias)
- Continuation prompt extraction
- Entity deduplication (exact match + substring match)
- Entity merge with confidence preservation
- Error handling in gleaning rounds
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.components.graph_rag.extraction_service import ExtractionService
from src.components.llm_proxy.models import LLMResponse
from src.config.extraction_cascade import CascadeRankConfig, ExtractionMethod
from src.core.models import GraphEntity


@pytest.fixture
def extraction_service():
    """Create extraction service for testing."""
    return ExtractionService()


@pytest.fixture
def sample_rank_config():
    """Create sample cascade rank configuration."""
    return CascadeRankConfig(
        rank=1,
        model="nemotron3",
        method=ExtractionMethod.LLM_ONLY,
        entity_timeout_s=300,
        relation_timeout_s=300,
        max_retries=3,
        retry_backoff_multiplier=1,
    )


@pytest.fixture
def sample_entities():
    """Create sample entities for testing."""
    return [
        GraphEntity(
            id="e1",
            name="Tesla",
            type="ORGANIZATION",
            description="Electric vehicle company",
            properties={},
            source_document="doc_1",
            confidence=1.0,
        ),
        GraphEntity(
            id="e2",
            name="Elon Musk",
            type="PERSON",
            description="CEO of Tesla",
            properties={},
            source_document="doc_1",
            confidence=1.0,
        ),
    ]


class TestGleaningDisabled:
    """Test gleaning when disabled (gleaning_steps=0)."""

    @pytest.mark.asyncio
    async def test_gleaning_disabled_returns_initial_entities(
        self, extraction_service, sample_entities
    ):
        """Test that gleaning_steps=0 returns only initial entities."""
        # Mock initial extraction
        with patch.object(
            extraction_service,
            "_extract_entities_with_rank",
            return_value=sample_entities,
        ):
            entities = await extraction_service.extract_entities_with_gleaning(
                text="Tesla was founded by Elon Musk.",
                document_id="doc_1",
                gleaning_steps=0,
            )

        # Should return initial entities without gleaning
        assert len(entities) == 2
        assert entities[0].name == "Tesla"
        assert entities[1].name == "Elon Musk"

    @pytest.mark.asyncio
    async def test_gleaning_disabled_no_completeness_check(self, extraction_service, sample_entities):
        """Test that completeness check is NOT called when gleaning disabled."""
        with patch.object(
            extraction_service,
            "_extract_entities_with_rank",
            return_value=sample_entities,
        ), patch.object(
            extraction_service,
            "_check_extraction_completeness",
            side_effect=AssertionError("Should not be called"),
        ):
            entities = await extraction_service.extract_entities_with_gleaning(
                text="Tesla was founded by Elon Musk.",
                gleaning_steps=0,
            )

        # Should not raise AssertionError (completeness check not called)
        assert len(entities) == 2


class TestCompletenessCheck:
    """Test completeness check logic."""

    @pytest.mark.asyncio
    async def test_completeness_check_returns_true_on_no(
        self, extraction_service, sample_entities, sample_rank_config
    ):
        """Test that completeness check returns True when LLM says 'NO'."""
        # Mock LLM response: "NO"
        mock_response = LLMResponse(
            content="NO",
            provider="ollama",
            model="nemotron3",
            tokens_used=101,
            tokens_input=100,
            tokens_output=1,
            cost_usd=0.001,
            latency_ms=50.0,
        )

        with patch.object(extraction_service.llm_proxy, "generate", return_value=mock_response):
            is_complete = await extraction_service._check_extraction_completeness(
                text="Tesla was founded by Elon Musk.",
                entities=sample_entities,
                rank_config=sample_rank_config,
            )

        assert is_complete is True

    @pytest.mark.asyncio
    async def test_completeness_check_returns_false_on_yes(
        self, extraction_service, sample_entities, sample_rank_config
    ):
        """Test that completeness check returns False when LLM says 'YES'."""
        # Mock LLM response: "YES"
        mock_response = LLMResponse(
            content="YES",
            provider="ollama",
            model="nemotron3",
            tokens_used=101,
            tokens_input=100,
            tokens_output=1,
            cost_usd=0.001,
            latency_ms=50.0,
        )

        with patch.object(extraction_service.llm_proxy, "generate", return_value=mock_response):
            is_complete = await extraction_service._check_extraction_completeness(
                text="Tesla was founded by Elon Musk in 2003.",
                entities=sample_entities,
                rank_config=sample_rank_config,
            )

        assert is_complete is False

    @pytest.mark.asyncio
    async def test_completeness_check_handles_error_gracefully(
        self, extraction_service, sample_entities, sample_rank_config
    ):
        """Test that completeness check returns False on error (assume incomplete)."""
        # Mock LLM error
        with patch.object(
            extraction_service.llm_proxy, "generate", side_effect=Exception("LLM timeout")
        ):
            is_complete = await extraction_service._check_extraction_completeness(
                text="Tesla was founded by Elon Musk.",
                entities=sample_entities,
                rank_config=sample_rank_config,
            )

        # Should assume incomplete on error
        assert is_complete is False


class TestGleaningEarlyTermination:
    """Test gleaning with early termination."""

    @pytest.mark.asyncio
    async def test_gleaning_stops_early_on_complete(self, extraction_service, sample_entities):
        """Test that gleaning stops early if LLM says extraction is complete."""
        # Mock initial extraction
        with patch.object(
            extraction_service, "_extract_entities_with_rank", return_value=sample_entities
        ), patch.object(
            extraction_service, "_check_extraction_completeness", return_value=True
        ), patch.object(
            extraction_service,
            "_extract_missing_entities",
            side_effect=AssertionError("Should not be called"),
        ):
            entities = await extraction_service.extract_entities_with_gleaning(
                text="Tesla was founded by Elon Musk.",
                gleaning_steps=3,  # Could run 3 rounds, but stops at 1
            )

        # Should return initial entities (no gleaning rounds executed)
        assert len(entities) == 2


class TestGleaningMultipleRounds:
    """Test gleaning with multiple rounds."""

    @pytest.mark.asyncio
    async def test_gleaning_incremental_improvement(self, extraction_service, sample_entities):
        """Test that gleaning adds entities over multiple rounds."""
        # Round 1: 2 entities
        # Round 2: +1 entity (2003)
        # Round 3: +1 entity (Palo Alto)

        round_2_entity = GraphEntity(
            id="e3",
            name="2003",
            type="EVENT",
            description="Year Tesla was founded",
            properties={},
            source_document="doc_1",
            confidence=1.0,
        )

        round_3_entity = GraphEntity(
            id="e4",
            name="Palo Alto",
            type="LOCATION",
            description="City where Tesla was founded",
            properties={},
            source_document="doc_1",
            confidence=1.0,
        )

        # Mock multiple rounds
        with patch.object(
            extraction_service, "_extract_entities_with_rank", return_value=sample_entities
        ), patch.object(
            extraction_service, "_check_extraction_completeness", return_value=False
        ), patch.object(
            extraction_service,
            "_extract_missing_entities",
            side_effect=[[round_2_entity], [round_3_entity]],
        ):
            entities = await extraction_service.extract_entities_with_gleaning(
                text="Tesla was founded by Elon Musk in 2003 in Palo Alto.",
                gleaning_steps=2,
            )

        # Should have 4 entities total (2 initial + 1 from round 2 + 1 from round 3)
        assert len(entities) == 4

    @pytest.mark.asyncio
    async def test_gleaning_respects_max_rounds(self, extraction_service, sample_entities):
        """Test that gleaning respects max_gleanings limit."""
        # Mock completeness check to always return False (never complete)
        with patch.object(
            extraction_service, "_extract_entities_with_rank", return_value=sample_entities
        ), patch.object(
            extraction_service, "_check_extraction_completeness", return_value=False
        ), patch.object(
            extraction_service, "_extract_missing_entities", return_value=[]
        ) as mock_extract_missing:
            await extraction_service.extract_entities_with_gleaning(
                text="Tesla was founded by Elon Musk.",
                gleaning_steps=2,
            )

        # Should call _extract_missing_entities exactly 2 times (for rounds 2 and 3)
        assert mock_extract_missing.call_count == 2


class TestEntityDeduplication:
    """Test entity deduplication logic."""

    def test_deduplication_removes_exact_duplicates(self, extraction_service):
        """Test that deduplication removes exact name matches (case-insensitive)."""
        entities = [
            GraphEntity(id="e1", name="Tesla", type="ORGANIZATION", description="Company 1", properties={}, source_document=None, confidence=1.0),
            GraphEntity(id="e2", name="tesla", type="ORGANIZATION", description="Company 2", properties={}, source_document=None, confidence=0.9),
            GraphEntity(id="e3", name="TESLA", type="ORGANIZATION", description="Company 3", properties={}, source_document=None, confidence=0.8),
        ]

        deduplicated = extraction_service._merge_and_deduplicate_entities(entities)

        # Should keep only 1 entity (highest confidence)
        assert len(deduplicated) == 1
        assert deduplicated[0].name == "Tesla"  # Original case preserved
        assert deduplicated[0].confidence == 1.0

    def test_deduplication_removes_substring_duplicates(self, extraction_service):
        """Test that deduplication removes substring matches."""
        entities = [
            GraphEntity(id="e1", name="Tesla Inc", type="ORGANIZATION", description="Full name", properties={}, source_document=None, confidence=1.0),
            GraphEntity(id="e2", name="Tesla", type="ORGANIZATION", description="Short name", properties={}, source_document=None, confidence=0.9),
        ]

        deduplicated = extraction_service._merge_and_deduplicate_entities(entities)

        # Should keep longer entity name
        assert len(deduplicated) == 1
        assert deduplicated[0].name == "Tesla Inc"

    def test_deduplication_preserves_unique_entities(self, extraction_service):
        """Test that deduplication preserves unique entities."""
        entities = [
            GraphEntity(id="e1", name="Tesla", type="ORGANIZATION", description="Company", properties={}, source_document=None, confidence=1.0),
            GraphEntity(id="e2", name="Elon Musk", type="PERSON", description="CEO", properties={}, source_document=None, confidence=1.0),
            GraphEntity(id="e3", name="SpaceX", type="ORGANIZATION", description="Space company", properties={}, source_document=None, confidence=1.0),
        ]

        deduplicated = extraction_service._merge_and_deduplicate_entities(entities)

        # Should keep all 3 unique entities
        assert len(deduplicated) == 3

    def test_deduplication_handles_empty_list(self, extraction_service):
        """Test that deduplication handles empty entity list."""
        entities = []

        deduplicated = extraction_service._merge_and_deduplicate_entities(entities)

        assert len(deduplicated) == 0


class TestContinuationExtraction:
    """Test continuation extraction for missing entities."""

    @pytest.mark.asyncio
    async def test_continuation_extraction_returns_new_entities(
        self, extraction_service, sample_entities, sample_rank_config
    ):
        """Test that continuation extraction returns new entities."""
        # Mock LLM response with new entity
        mock_response = LLMResponse(
            content='[{"name": "2003", "type": "EVENT", "description": "Year Tesla was founded"}]',
            provider="ollama",
            model="nemotron3",
            tokens_used=230,
            tokens_input=200,
            tokens_output=30,
            cost_usd=0.002,
            latency_ms=150.0,
        )

        with patch.object(extraction_service.llm_proxy, "generate", return_value=mock_response):
            new_entities = await extraction_service._extract_missing_entities(
                text="Tesla was founded by Elon Musk in 2003.",
                existing_entities=sample_entities,
                rank_config=sample_rank_config,
                document_id="doc_1",
            )

        # Should return 1 new entity
        assert len(new_entities) == 1
        assert new_entities[0].name == "2003"
        assert new_entities[0].type == "EVENT"

    @pytest.mark.asyncio
    async def test_continuation_extraction_handles_empty_response(
        self, extraction_service, sample_entities, sample_rank_config
    ):
        """Test that continuation extraction handles empty JSON array."""
        # Mock LLM response with empty array
        mock_response = LLMResponse(
            content="[]",
            provider="ollama",
            model="nemotron3",
            tokens_used=202,
            tokens_input=200,
            tokens_output=2,
            cost_usd=0.001,
            latency_ms=80.0,
        )

        with patch.object(extraction_service.llm_proxy, "generate", return_value=mock_response):
            new_entities = await extraction_service._extract_missing_entities(
                text="Tesla was founded by Elon Musk.",
                existing_entities=sample_entities,
                rank_config=sample_rank_config,
            )

        # Should return empty list
        assert len(new_entities) == 0


class TestGleaningErrorHandling:
    """Test error handling in gleaning rounds."""

    @pytest.mark.asyncio
    async def test_gleaning_continues_on_round_failure(self, extraction_service, sample_entities):
        """Test that gleaning continues even if a round fails."""
        round_2_entity = GraphEntity(
            id="e3",
            name="2003",
            type="EVENT",
            description="Year Tesla was founded",
            properties={},
            source_document="doc_1",
            confidence=1.0,
        )

        # Mock: Round 2 fails, Round 3 succeeds
        with patch.object(
            extraction_service, "_extract_entities_with_rank", return_value=sample_entities
        ), patch.object(
            extraction_service, "_check_extraction_completeness", return_value=False
        ), patch.object(
            extraction_service,
            "_extract_missing_entities",
            side_effect=[Exception("Round 2 failed"), [round_2_entity]],
        ):
            entities = await extraction_service.extract_entities_with_gleaning(
                text="Tesla was founded by Elon Musk in 2003.",
                gleaning_steps=2,
            )

        # Should still return entities (Round 1 + Round 3)
        # Round 2 failed but didn't stop process
        assert len(entities) == 3  # 2 initial + 1 from round 3

    @pytest.mark.asyncio
    async def test_gleaning_deduplication_always_runs(self, extraction_service, sample_entities):
        """Test that deduplication always runs even if all gleaning rounds fail."""
        with patch.object(
            extraction_service, "_extract_entities_with_rank", return_value=sample_entities
        ), patch.object(
            extraction_service, "_check_extraction_completeness", return_value=False
        ), patch.object(
            extraction_service,
            "_extract_missing_entities",
            side_effect=Exception("All rounds failed"),
        ), patch.object(
            extraction_service,
            "_merge_and_deduplicate_entities",
            return_value=sample_entities,
        ) as mock_dedup:
            entities = await extraction_service.extract_entities_with_gleaning(
                text="Tesla was founded by Elon Musk.",
                gleaning_steps=1,
            )

        # Deduplication should still be called
        mock_dedup.assert_called_once()
        assert len(entities) == 2
