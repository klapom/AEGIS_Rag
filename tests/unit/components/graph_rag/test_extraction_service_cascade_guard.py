"""Unit tests for ExtractionService Cascade Timeout Guard.

Sprint 128 Feature 128.2: Cascade timeout guard to prevent competing vLLM requests.

Tests:
- Guard waits when vLLM is overloaded after timeout
- Guard releases when capacity becomes available
- Guard skips when vLLM is not enabled
- Guard timeout after max wait
- Guard applies to both entity and relationship extraction
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.graph_rag.extraction_service import EXTRACTION_WORKERS, ExtractionService
from src.config.extraction_cascade import CascadeRankConfig, ExtractionMethod
from src.core.models import GraphEntity, GraphRelationship


class TestExtractionServiceCascadeGuard:
    """Test suite for cascade timeout guard functionality."""

    @pytest.fixture
    def extraction_service(self) -> ExtractionService:
        """Create ExtractionService instance for testing."""
        return ExtractionService(
            llm_model="nemotron3",
            temperature=0.1,
            max_tokens=2000,
        )

    @pytest.fixture
    def rank_config(self) -> CascadeRankConfig:
        """Create test rank configuration."""
        return CascadeRankConfig(
            rank=1,
            model="nemotron3",
            method=ExtractionMethod.LLM_ONLY,
            entity_timeout_s=300,
            relation_timeout_s=300,
        )

    @pytest.mark.asyncio
    async def test_wait_for_vllm_capacity_disabled_vllm(
        self, extraction_service: ExtractionService, rank_config: CascadeRankConfig
    ) -> None:
        """Test guard returns immediately when vLLM is not enabled."""
        # Mock vLLM as disabled
        extraction_service.llm_proxy._vllm_enabled = False

        # Guard should return immediately without checking active requests
        await extraction_service._wait_for_vllm_capacity(
            rank_config=rank_config,
            max_workers=2,
            max_wait_s=60,
        )

        # No assertions needed - test passes if it returns immediately

    @pytest.mark.asyncio
    async def test_wait_for_vllm_capacity_available_immediately(
        self, extraction_service: ExtractionService, rank_config: CascadeRankConfig
    ) -> None:
        """Test guard returns immediately when capacity is available."""
        # Mock vLLM as enabled
        extraction_service.llm_proxy._vllm_enabled = True

        # Mock get_vllm_active_requests to return 1 (below max_workers=2)
        extraction_service.llm_proxy.get_vllm_active_requests = AsyncMock(return_value=1)

        # Guard should return immediately
        await extraction_service._wait_for_vllm_capacity(
            rank_config=rank_config,
            max_workers=2,
            max_wait_s=60,
        )

        # Verify active requests were checked
        extraction_service.llm_proxy.get_vllm_active_requests.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_for_vllm_capacity_wait_then_release(
        self, extraction_service: ExtractionService, rank_config: CascadeRankConfig
    ) -> None:
        """Test guard waits when overloaded, then releases when capacity available."""
        # Mock vLLM as enabled
        extraction_service.llm_proxy._vllm_enabled = True

        # Mock get_vllm_active_requests to return:
        # - First call: 2 (at capacity)
        # - Second call: 1 (capacity available)
        extraction_service.llm_proxy.get_vllm_active_requests = AsyncMock(side_effect=[2, 1])

        # Guard should wait once, then release
        start_time = asyncio.get_event_loop().time()
        await extraction_service._wait_for_vllm_capacity(
            rank_config=rank_config,
            max_workers=2,
            max_wait_s=60,
        )
        elapsed = asyncio.get_event_loop().time() - start_time

        # Verify active requests were checked twice (initial + after wait)
        assert extraction_service.llm_proxy.get_vllm_active_requests.call_count == 2

        # Verify guard waited at least 5 seconds (initial wait)
        assert elapsed >= 5.0

    @pytest.mark.asyncio
    async def test_wait_for_vllm_capacity_max_wait_exceeded(
        self, extraction_service: ExtractionService, rank_config: CascadeRankConfig
    ) -> None:
        """Test guard proceeds after max wait time even if still overloaded."""
        # Mock vLLM as enabled
        extraction_service.llm_proxy._vllm_enabled = True

        # Mock get_vllm_active_requests to always return 2 (overloaded)
        extraction_service.llm_proxy.get_vllm_active_requests = AsyncMock(return_value=2)

        # Guard should wait up to max_wait_s (10s for test), then proceed
        start_time = asyncio.get_event_loop().time()
        await extraction_service._wait_for_vllm_capacity(
            rank_config=rank_config,
            max_workers=2,
            max_wait_s=10,  # Short timeout for test
        )
        elapsed = asyncio.get_event_loop().time() - start_time

        # Verify guard waited approximately max_wait_s (with some tolerance for exponential backoff)
        assert 10.0 <= elapsed < 20.0

        # Verify active requests were checked multiple times
        assert extraction_service.llm_proxy.get_vllm_active_requests.call_count >= 2

    @pytest.mark.asyncio
    @patch("src.components.graph_rag.extraction_service.get_cascade_for_domain")
    async def test_extract_entities_guard_invoked_on_timeout(
        self,
        mock_get_cascade: MagicMock,
        extraction_service: ExtractionService,
    ) -> None:
        """Test guard is invoked when Rank 1 times out."""
        from src.config.extraction_cascade import DEFAULT_CASCADE

        # Mock cascade configuration
        mock_get_cascade.return_value = DEFAULT_CASCADE

        # Mock vLLM as enabled
        extraction_service.llm_proxy._vllm_enabled = True

        # Mock get_vllm_active_requests to return 0 (capacity available)
        extraction_service.llm_proxy.get_vllm_active_requests = AsyncMock(return_value=0)

        # Mock _extract_entities_with_rank:
        # - Rank 1: TimeoutError (should trigger guard)
        # - Rank 2: Success
        mock_entities = [
            GraphEntity(
                id="e1",
                name="Test Entity",
                type="CONCEPT",
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
        entities = await extraction_service.extract_entities(
            text="Test text",
            document_id="doc123",
            domain="test_domain",
        )

        # Assertions
        assert len(entities) == 1
        assert entities[0].name == "Test Entity"

        # Verify guard was invoked (checked active requests)
        extraction_service.llm_proxy.get_vllm_active_requests.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.components.graph_rag.extraction_service.get_cascade_for_domain")
    async def test_extract_relationships_guard_invoked_on_timeout(
        self,
        mock_get_cascade: MagicMock,
        extraction_service: ExtractionService,
    ) -> None:
        """Test guard is invoked when relationship extraction Rank 1 times out."""
        from src.config.extraction_cascade import DEFAULT_CASCADE

        # Mock cascade configuration
        mock_get_cascade.return_value = DEFAULT_CASCADE

        # Mock vLLM as enabled
        extraction_service.llm_proxy._vllm_enabled = True

        # Mock get_vllm_active_requests to return 0 (capacity available)
        extraction_service.llm_proxy.get_vllm_active_requests = AsyncMock(return_value=0)

        # Mock entities
        mock_entities = [
            GraphEntity(
                id="e1",
                name="Entity A",
                type="CONCEPT",
                description="",
                properties={},
                source_document="doc123",
                confidence=1.0,
            ),
            GraphEntity(
                id="e2",
                name="Entity B",
                type="CONCEPT",
                description="",
                properties={},
                source_document="doc123",
                confidence=1.0,
            ),
        ]

        # Mock _extract_relationships_with_rank:
        # - Rank 1: TimeoutError (should trigger guard)
        # - Rank 2: Success
        mock_relationships = [
            GraphRelationship(
                id="r1",
                source="Entity A",
                target="Entity B",
                type="RELATES_TO",
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
        relationships = await extraction_service.extract_relationships(
            text="Entity A relates to Entity B.",
            entities=mock_entities,
            document_id="doc123",
            domain="test_domain",
        )

        # Assertions
        assert len(relationships) == 1
        assert relationships[0].type == "RELATES_TO"

        # Verify guard was invoked (checked active requests)
        extraction_service.llm_proxy.get_vllm_active_requests.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.components.graph_rag.extraction_service.get_cascade_for_domain")
    async def test_guard_not_invoked_on_non_timeout_error(
        self,
        mock_get_cascade: MagicMock,
        extraction_service: ExtractionService,
    ) -> None:
        """Test guard is NOT invoked when Rank 1 fails with non-timeout error."""
        from src.config.extraction_cascade import DEFAULT_CASCADE

        # Mock cascade configuration
        mock_get_cascade.return_value = DEFAULT_CASCADE

        # Mock vLLM as enabled
        extraction_service.llm_proxy._vllm_enabled = True

        # Mock get_vllm_active_requests (should NOT be called)
        extraction_service.llm_proxy.get_vllm_active_requests = AsyncMock(return_value=0)

        # Mock _extract_entities_with_rank:
        # - Rank 1: ValueError (parse error - NOT timeout)
        # - Rank 2: Success
        mock_entities = [
            GraphEntity(
                id="e1",
                name="Test Entity",
                type="CONCEPT",
                description="",
                properties={},
                source_document="doc123",
                confidence=1.0,
            )
        ]

        extraction_service._extract_entities_with_rank = AsyncMock(
            side_effect=[ValueError("Parse error"), mock_entities]
        )

        # Extract entities
        entities = await extraction_service.extract_entities(
            text="Test text",
            document_id="doc123",
            domain="test_domain",
        )

        # Assertions
        assert len(entities) == 1

        # Verify guard was NOT invoked (active requests NOT checked)
        extraction_service.llm_proxy.get_vllm_active_requests.assert_not_called()
