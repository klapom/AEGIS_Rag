"""Unit tests for ExtractionService Cascade Fallback Logic.

Sprint 83 Feature 83.2: LLM Fallback & Retry Strategy

Tests:
- Cascade fallback on timeout
- Cascade fallback on LLM error
- Cascade fallback on parsing error
- Successful extraction on Rank 1
- Successful extraction on Rank 2 (after Rank 1 failure)
- Successful extraction on Rank 3 (after Rank 1 & 2 failures)
- All ranks fail
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.graph_rag.extraction_service import ExtractionService
from src.config.extraction_cascade import DEFAULT_CASCADE, ExtractionMethod
from src.core.models import GraphEntity, GraphRelationship


class TestExtractionServiceCascadeFallback:
    """Test suite for ExtractionService cascade fallback logic."""

    @pytest.fixture
    def extraction_service(self) -> ExtractionService:
        """Create ExtractionService instance for testing."""
        return ExtractionService(
            llm_model="nemotron3",  # Explicit model for testing
            temperature=0.1,
            max_tokens=2000,
        )

    @pytest.mark.asyncio
    @patch("src.components.graph_rag.extraction_service.get_cascade_for_domain")
    async def test_extract_entities_rank1_success(
        self,
        mock_get_cascade: MagicMock,
        extraction_service: ExtractionService,
    ) -> None:
        """Test extract_entities succeeds on Rank 1 (no fallback)."""
        # Mock cascade configuration
        mock_get_cascade.return_value = DEFAULT_CASCADE

        # Mock _extract_entities_with_rank to succeed on first call
        mock_entities = [
            GraphEntity(
                id="e1",
                name="Apple Inc.",
                type="ORGANIZATION",
                description="",
                properties={},
                source_document="doc123",
                confidence=1.0,
            )
        ]

        extraction_service._extract_entities_with_rank = AsyncMock(return_value=mock_entities)

        # Extract entities
        text = "Apple Inc. is a technology company."
        entities = await extraction_service.extract_entities(
            text=text,
            document_id="doc123",
            domain="tech_docs",
        )

        # Assertions
        assert len(entities) == 1
        assert entities[0].name == "Apple Inc."

        # Verify only Rank 1 was tried
        assert extraction_service._extract_entities_with_rank.call_count == 1
        call_args = extraction_service._extract_entities_with_rank.call_args
        assert call_args.kwargs["rank_config"].rank == 1

    @pytest.mark.asyncio
    @patch("src.components.graph_rag.extraction_service.get_cascade_for_domain")
    @patch("src.components.graph_rag.extraction_service.log_cascade_fallback")
    async def test_extract_entities_rank2_success_after_rank1_failure(
        self,
        mock_log_fallback: MagicMock,
        mock_get_cascade: MagicMock,
        extraction_service: ExtractionService,
    ) -> None:
        """Test extract_entities falls back to Rank 2 after Rank 1 timeout."""
        # Mock cascade configuration
        mock_get_cascade.return_value = DEFAULT_CASCADE

        # Mock _extract_entities_with_rank:
        # - Rank 1: TimeoutError
        # - Rank 2: Success
        mock_entities = [
            GraphEntity(
                id="e1",
                name="Apple Inc.",
                type="ORGANIZATION",
                description="",
                properties={},
                source_document="doc123",
                confidence=1.0,
            )
        ]

        extraction_service._extract_entities_with_rank = AsyncMock(
            side_effect=[asyncio.TimeoutError("Rank 1 timeout"), mock_entities]
        )

        # Extract entities
        text = "Apple Inc. is a technology company."
        entities = await extraction_service.extract_entities(
            text=text,
            document_id="doc123",
            domain="tech_docs",
        )

        # Assertions
        assert len(entities) == 1
        assert entities[0].name == "Apple Inc."

        # Verify Rank 1 and Rank 2 were tried
        assert extraction_service._extract_entities_with_rank.call_count == 2

        # Verify fallback was logged
        mock_log_fallback.assert_called_once()
        call_args = mock_log_fallback.call_args
        assert call_args.kwargs["from_rank"] == 1
        assert call_args.kwargs["to_rank"] == 2
        assert call_args.kwargs["document_id"] == "doc123"

    @pytest.mark.asyncio
    @patch("src.components.graph_rag.extraction_service.get_cascade_for_domain")
    @patch("src.components.graph_rag.extraction_service.log_cascade_fallback")
    async def test_extract_entities_rank3_success_after_rank1_rank2_failure(
        self,
        mock_log_fallback: MagicMock,
        mock_get_cascade: MagicMock,
        extraction_service: ExtractionService,
    ) -> None:
        """Test extract_entities falls back to Rank 3 after Rank 1 & 2 failures."""
        # Mock cascade configuration
        mock_get_cascade.return_value = DEFAULT_CASCADE

        # Mock _extract_entities_with_rank:
        # - Rank 1: TimeoutError
        # - Rank 2: ValueError (parse error)
        # - Rank 3: Success
        mock_entities = [
            GraphEntity(
                id="e1",
                name="Apple Inc.",
                type="ORGANIZATION",
                description="",
                properties={},
                source_document="doc123",
                confidence=1.0,
            )
        ]

        extraction_service._extract_entities_with_rank = AsyncMock(
            side_effect=[
                asyncio.TimeoutError("Rank 1 timeout"),
                ValueError("Rank 2 parse error"),
                mock_entities,
            ]
        )

        # Extract entities
        text = "Apple Inc. is a technology company."
        entities = await extraction_service.extract_entities(
            text=text,
            document_id="doc123",
            domain="tech_docs",
        )

        # Assertions
        assert len(entities) == 1
        assert entities[0].name == "Apple Inc."

        # Verify all 3 ranks were tried
        assert extraction_service._extract_entities_with_rank.call_count == 3

        # Verify fallback was logged twice (1→2, 2→3)
        assert mock_log_fallback.call_count == 2

    @pytest.mark.asyncio
    @patch("src.components.graph_rag.extraction_service.get_cascade_for_domain")
    async def test_extract_entities_all_ranks_fail(
        self,
        mock_get_cascade: MagicMock,
        extraction_service: ExtractionService,
    ) -> None:
        """Test extract_entities raises exception when all ranks fail."""
        # Mock cascade configuration
        mock_get_cascade.return_value = DEFAULT_CASCADE

        # Mock _extract_entities_with_rank to fail on all ranks
        extraction_service._extract_entities_with_rank = AsyncMock(
            side_effect=[
                asyncio.TimeoutError("Rank 1 timeout"),
                asyncio.TimeoutError("Rank 2 timeout"),
                ValueError("Rank 3 parse error"),
            ]
        )

        # Extract entities (should raise exception)
        text = "Apple Inc. is a technology company."
        with pytest.raises(ValueError, match="Rank 3 parse error"):
            await extraction_service.extract_entities(
                text=text,
                document_id="doc123",
                domain="tech_docs",
            )

        # Verify all 3 ranks were tried
        assert extraction_service._extract_entities_with_rank.call_count == 3

    @pytest.mark.asyncio
    @patch("src.components.graph_rag.extraction_service.get_cascade_for_domain")
    async def test_extract_relationships_cascade_fallback(
        self,
        mock_get_cascade: MagicMock,
        extraction_service: ExtractionService,
    ) -> None:
        """Test extract_relationships uses cascade fallback."""
        # Mock cascade configuration
        mock_get_cascade.return_value = DEFAULT_CASCADE

        # Mock entities
        mock_entities = [
            GraphEntity(
                id="e1",
                name="Apple Inc.",
                type="ORGANIZATION",
                description="",
                properties={},
                source_document="doc123",
                confidence=1.0,
            )
        ]

        # Mock _extract_relationships_with_rank:
        # - Rank 1: TimeoutError
        # - Rank 2: Success
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

        extraction_service._extract_relationships_with_rank = AsyncMock(
            side_effect=[asyncio.TimeoutError("Rank 1 timeout"), mock_relationships]
        )

        # Extract relationships
        text = "Apple Inc. is located in Cupertino."
        relationships = await extraction_service.extract_relationships(
            text=text,
            entities=mock_entities,
            document_id="doc123",
            domain="tech_docs",
        )

        # Assertions
        assert len(relationships) == 1
        assert relationships[0].type == "LOCATED_IN"

        # Verify Rank 1 and Rank 2 were tried
        assert extraction_service._extract_relationships_with_rank.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_with_timeout_success(
        self, extraction_service: ExtractionService
    ) -> None:
        """Test _extract_with_timeout completes within timeout."""
        async def fast_extraction() -> list[GraphEntity]:
            await asyncio.sleep(0.1)
            return [
                GraphEntity(
                    id="e1",
                    name="Test",
                    type="ENTITY",
                    description="",
                    properties={},
                    source_document="doc",
                    confidence=1.0,
                )
            ]

        from src.config.extraction_cascade import CascadeRankConfig, ExtractionMethod

        rank_config = CascadeRankConfig(
            rank=1,
            model="nemotron3",
            method=ExtractionMethod.LLM_ONLY,
            entity_timeout_s=1,
            relation_timeout_s=1,
        )

        result = await extraction_service._extract_with_timeout(
            fast_extraction,
            timeout_s=1,
            rank_config=rank_config,
        )

        assert len(result) == 1
        assert result[0].name == "Test"

    @pytest.mark.asyncio
    async def test_extract_with_timeout_timeout_error(
        self, extraction_service: ExtractionService
    ) -> None:
        """Test _extract_with_timeout raises TimeoutError on timeout."""
        async def slow_extraction() -> list[GraphEntity]:
            await asyncio.sleep(2)  # Longer than timeout
            return []

        from src.config.extraction_cascade import CascadeRankConfig, ExtractionMethod

        rank_config = CascadeRankConfig(
            rank=1,
            model="nemotron3",
            method=ExtractionMethod.LLM_ONLY,
            entity_timeout_s=1,
            relation_timeout_s=1,
        )

        with pytest.raises(asyncio.TimeoutError):
            await extraction_service._extract_with_timeout(
                slow_extraction,
                timeout_s=1,
                rank_config=rank_config,
            )
