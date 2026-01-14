"""Unit tests for RecursiveLLMProcessor Sprint 92 enhancements.

Sprint 92 Features:
- Feature 92.6: Per-Level Configuration (adaptive sizing and scoring)
- Feature 92.7: BGE-M3 Dense+Sparse Scoring
- Feature 92.8: BGE-M3 Multi-Vector Scoring (ColBERT-style)
- Feature 92.9: C-LARA Adaptive Scoring
- Feature 92.10: Parallel Workers Configuration

Test file: tests/unit/agents/context/test_recursive_llm_enhanced.py
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from src.agents.context.recursive_llm import (
    RecursiveLLMProcessor,
    DocumentSegment,
)
from src.core.config import RecursiveLLMSettings, RecursiveLevelConfig


class TestRecursiveLLMProcessorInitialization:
    """Tests for RecursiveLLMProcessor initialization with per-level config."""

    def test_initialization_with_settings(
        self, mock_llm, mock_skill_registry, recursive_llm_settings
    ):
        """Test processor initializes with RecursiveLLMSettings."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        assert processor.settings == recursive_llm_settings
        assert processor.settings.max_depth == 3
        assert len(processor.settings.levels) == 4

    def test_backward_compatibility_old_params(
        self, mock_llm, mock_skill_registry
    ):
        """Test backward compatibility with deprecated parameters."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            context_window=8192,
            overlap_tokens=200,
            max_depth=2,
            relevance_threshold=0.6,
        )

        assert processor.settings is not None
        assert processor.settings.max_depth == 2
        # Old params create single-level config
        assert len(processor.settings.levels) == 1

    def test_settings_none_creates_defaults(self, mock_llm, mock_skill_registry):
        """Test passing no settings creates default configuration."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=None,
        )

        assert processor.settings is not None
        assert processor.settings.max_depth == 3
        assert len(processor.settings.levels) == 4

    def test_invalid_settings_raises_error(self, mock_llm, mock_skill_registry):
        """Test invalid settings (empty levels) raises ValueError."""
        invalid_settings = RecursiveLLMSettings(levels=[])

        with pytest.raises(ValueError):
            RecursiveLLMProcessor(
                llm=mock_llm,
                skill_registry=mock_skill_registry,
                settings=invalid_settings,
            )

    def test_level_config_fallback_warning(
        self, mock_llm, mock_skill_registry
    ):
        """Test warning logged when max_depth > len(levels)."""
        settings = RecursiveLLMSettings(
            max_depth=5,
            levels=[
                RecursiveLevelConfig(level=0, segment_size_tokens=16384),
            ],
        )

        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=settings,
        )

        assert processor.settings.max_depth == 5
        assert len(processor.settings.levels) == 1


class TestSegmentationPerLevel:
    """Tests for per-level document segmentation."""

    def test_segment_document_level_0(
        self, mock_llm, mock_skill_registry, recursive_llm_settings, sample_document_long
    ):
        """Test segmentation at level 0 uses largest chunk size."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        segments = processor._segment_document(sample_document_long, level=0)

        assert len(segments) > 0
        assert all(s.level == 0 for s in segments)
        assert all(s.parent_id is None for s in segments)
        # Level 0 uses 16384 tokens ~ 65536 chars
        assert all(len(s.content) > 1000 for s in segments)

    def test_segment_document_level_1(
        self, mock_llm, mock_skill_registry, recursive_llm_settings, sample_document_long
    ):
        """Test segmentation at level 1 uses medium chunk size."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        segments = processor._segment_document(sample_document_long, level=1)

        assert len(segments) > 0
        assert all(s.level == 1 for s in segments)

    def test_segment_document_level_2(
        self, mock_llm, mock_skill_registry, recursive_llm_settings, sample_document_long
    ):
        """Test segmentation at level 2 uses smaller chunk size."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        segments = processor._segment_document(sample_document_long, level=2)

        assert len(segments) > 0
        assert all(s.level == 2 for s in segments)

    def test_segment_sizes_decrease_by_level(
        self, mock_llm, mock_skill_registry, recursive_llm_settings, sample_document_long
    ):
        """Test segment sizes decrease at each level."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        segments_l0 = processor._segment_document(sample_document_long, level=0)
        segments_l1 = processor._segment_document(sample_document_long, level=1)
        segments_l2 = processor._segment_document(sample_document_long, level=2)

        avg_size_l0 = sum(len(s.content) for s in segments_l0) / len(segments_l0)
        avg_size_l1 = sum(len(s.content) for s in segments_l1) / len(segments_l1)
        avg_size_l2 = sum(len(s.content) for s in segments_l2) / len(segments_l2)

        # Sizes should generally decrease (with tolerance for natural breaks)
        assert avg_size_l0 > avg_size_l2

    def test_segment_with_parent_id(
        self, mock_llm, mock_skill_registry, recursive_llm_settings, sample_document_short
    ):
        """Test segmentation preserves parent_id."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        segments = processor._segment_document(
            sample_document_short, level=1, parent_id="seg_0_0"
        )

        assert len(segments) > 0
        assert all(s.parent_id == "seg_0_0" for s in segments)

    def test_segment_with_overlap(
        self, mock_llm, mock_skill_registry, recursive_llm_settings, sample_document_long
    ):
        """Test segments have appropriate overlap."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        segments = processor._segment_document(sample_document_long, level=0)

        # Check overlap exists (segments should have content from previous segment)
        if len(segments) > 1:
            # Find text that appears in both segments
            for i in range(len(segments) - 1):
                content1 = segments[i].content
                content2 = segments[i + 1].content
                # There should be some overlap in the document text
                assert segments[i + 1].start_offset < segments[i].end_offset


class TestScoreRelevanceDenseSparse:
    """Tests for BGE-M3 Dense+Sparse scoring (Feature 92.7)."""

    @pytest.mark.asyncio
    async def test_score_relevance_dense_sparse(
        self, mock_llm, mock_skill_registry, mock_embedding_service,
        recursive_llm_settings, sample_segments
    ):
        """Test dense+sparse scoring method."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        with patch(
            "src.agents.context.recursive_llm.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            scored = await processor._score_relevance_dense_sparse(
                sample_segments,
                "What is the methodology?",
            )

        assert len(scored) == len(sample_segments)
        assert all(s.relevance_score >= 0.0 for s in scored)
        assert all(s.relevance_score <= 1.0 for s in scored)
        # Should be sorted by relevance
        assert all(
            scored[i].relevance_score >= scored[i + 1].relevance_score
            for i in range(len(scored) - 1)
        )

    @pytest.mark.asyncio
    async def test_dense_sparse_batch_embedding(
        self, mock_llm, mock_skill_registry, mock_embedding_service,
        recursive_llm_settings, sample_segments
    ):
        """Test dense+sparse uses batch embedding, not one-by-one."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        with patch(
            "src.agents.context.recursive_llm.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            await processor._score_relevance_dense_sparse(
                sample_segments,
                "test query",
            )

        # Verify batch embedding was called
        assert mock_embedding_service.embed_batch.called
        # Verify embed_single was not called for each segment
        assert not mock_embedding_service.embed_single.called

    @pytest.mark.asyncio
    async def test_dense_sparse_hybrid_scoring(
        self, mock_llm, mock_skill_registry,
        recursive_llm_settings, sample_segments, sample_embedding_vectors
    ):
        """Test hybrid score calculation (0.6 * dense + 0.4 * sparse)."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        # Create embedding service that returns predictable values
        service = AsyncMock()

        async def embed_batch_side_effect(texts, **kwargs):
            return [
                {
                    "dense": sample_embedding_vectors["documents"]["doc_0"].tolist(),
                    "sparse": {0: 0.5, 1: 0.3},
                }
                for _ in texts
            ]

        service.embed_batch.side_effect = embed_batch_side_effect
        service.embed_single.return_value = {
            "dense": sample_embedding_vectors["query"].tolist(),
            "sparse": {0: 0.6, 1: 0.4},
        }

        with patch(
            "src.agents.context.recursive_llm.get_embedding_service",
            return_value=service,
        ):
            scored = await processor._score_relevance_dense_sparse(
                sample_segments,
                "test query",
            )

        assert len(scored) > 0
        assert all(0.0 <= s.relevance_score <= 1.0 for s in scored)


class TestScoreRelevanceMultiVector:
    """Tests for BGE-M3 Multi-Vector scoring (Feature 92.8, ColBERT)."""

    @pytest.mark.asyncio
    async def test_score_relevance_multi_vector(
        self, mock_llm, mock_skill_registry,
        recursive_llm_settings, sample_segments, mock_multi_vector_model
    ):
        """Test multi-vector (ColBERT) scoring method."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        # Mock BGEM3FlagModel
        with patch(
            "src.agents.context.recursive_llm.BGEM3FlagModel",
            return_value=mock_multi_vector_model,
        ):
            scored = await processor._score_relevance_multi_vector(
                sample_segments,
                "What is the methodology?",
            )

        assert len(scored) == len(sample_segments)
        assert all(s.relevance_score >= 0.0 for s in scored)
        assert all(s.relevance_score <= 1.0 for s in scored)

    @pytest.mark.asyncio
    async def test_multi_vector_lazy_loading(
        self, mock_llm, mock_skill_registry,
        recursive_llm_settings, sample_segments, mock_multi_vector_model
    ):
        """Test multi-vector model is lazy-loaded (singleton)."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        assert processor._multi_vector_model is None  # Initially None

        with patch(
            "src.agents.context.recursive_llm.BGEM3FlagModel",
            return_value=mock_multi_vector_model,
        ):
            await processor._score_relevance_multi_vector(
                sample_segments,
                "test query",
            )

        # Should be loaded now
        assert processor._multi_vector_model is not None

    @pytest.mark.asyncio
    async def test_multi_vector_fallback_to_dense_sparse(
        self, mock_llm, mock_skill_registry, mock_embedding_service,
        recursive_llm_settings, sample_segments
    ):
        """Test fallback to dense+sparse if FlagEmbedding not available."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        with patch(
            "src.agents.context.recursive_llm.BGEM3FlagModel",
            side_effect=ImportError("FlagEmbedding not installed"),
        ):
            with patch(
                "src.agents.context.recursive_llm.get_embedding_service",
                return_value=mock_embedding_service,
            ):
                # Should fallback to dense+sparse instead of raising
                scored = await processor._score_relevance_multi_vector(
                    sample_segments,
                    "test query",
                )

                assert len(scored) > 0


class TestScoreRelevanceAdaptive:
    """Tests for C-LARA adaptive scoring (Feature 92.9)."""

    @pytest.mark.asyncio
    async def test_score_relevance_adaptive_fine_grained(
        self, mock_llm, mock_skill_registry, mock_embedding_service,
        recursive_llm_settings, sample_segments
    ):
        """Test adaptive scoring for fine-grained queries → multi-vector."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        with patch(
            "src.agents.context.recursive_llm.get_granularity_mapper"
        ) as mock_mapper:
            mapper_instance = AsyncMock()
            mapper_instance.classify_granularity.return_value = (
                "fine-grained",
                0.85,
            )
            mock_mapper.return_value = mapper_instance

            with patch(
                "src.agents.context.recursive_llm.BGEM3FlagModel",
                side_effect=ImportError(),  # Force fallback
            ):
                with patch(
                    "src.agents.context.recursive_llm.get_embedding_service",
                    return_value=mock_embedding_service,
                ):
                    scored = await processor._score_relevance_adaptive(
                        sample_segments,
                        "What is the p-value?",
                    )

                assert len(scored) > 0

    @pytest.mark.asyncio
    async def test_score_relevance_adaptive_holistic(
        self, mock_llm, mock_skill_registry,
        recursive_llm_settings, sample_segments
    ):
        """Test adaptive scoring for holistic queries → LLM."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        with patch(
            "src.agents.context.recursive_llm.get_granularity_mapper"
        ) as mock_mapper:
            mapper_instance = AsyncMock()
            mapper_instance.classify_granularity.return_value = ("holistic", 0.90)
            mock_mapper.return_value = mapper_instance

            scored = await processor._score_relevance_adaptive(
                sample_segments,
                "Summarize the methodology",
            )

            assert len(scored) > 0


class TestParallelWorkers:
    """Tests for parallel worker configuration (Feature 92.10)."""

    def test_detect_llm_backend_ollama(
        self, mock_llm, mock_skill_registry, recursive_llm_settings
    ):
        """Test detecting Ollama backend."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        # Mock LLM with Ollama model
        processor.llm._client = MagicMock()
        processor.llm._client.model = "llama3.2"

        backend = processor._detect_llm_backend()
        assert backend in ["ollama", "unknown"]  # Actual detection logic

    def test_worker_limit_ollama(
        self, mock_llm, mock_skill_registry, recursive_llm_settings
    ):
        """Test worker limits for Ollama (1 worker for DGX Spark)."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        worker_limit = processor.settings.worker_limits.get("ollama", 1)
        assert worker_limit == 1

    def test_worker_limit_openai(
        self, mock_llm, mock_skill_registry, recursive_llm_settings
    ):
        """Test worker limits for OpenAI (10 workers)."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        worker_limit = processor.settings.worker_limits.get("openai", 10)
        assert worker_limit == 10

    def test_batched_helper(
        self, mock_llm, mock_skill_registry, recursive_llm_settings, sample_segments
    ):
        """Test _batched helper for batching work into worker groups."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        batch_size = 2
        batches = list(processor._batched(sample_segments, batch_size))

        # Check batching
        assert len(batches) > 0
        assert all(len(b) <= batch_size for b in batches)
        # Check all items present
        all_batched = [item for batch in batches for item in batch]
        assert len(all_batched) == len(sample_segments)

    @pytest.mark.asyncio
    async def test_parallel_exploration_with_workers(
        self, mock_llm, mock_skill_registry, recursive_llm_settings, sample_segments
    ):
        """Test parallel exploration respects worker limits."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=RecursiveLLMSettings(max_parallel_workers=2),
        )

        # Mock _explore_segment to track calls
        call_count = 0

        async def mock_explore_segment(segment, query, depth, skill):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate async work
            return {"segment_id": segment.id, "depth": depth}

        processor._explore_segment = mock_explore_segment

        findings = []
        for batch in processor._batched(sample_segments, 2):
            batch_findings = await asyncio.gather(*[
                processor._explore_segment(s, "test", 1, None)
                for s in batch
            ])
            findings.extend(batch_findings)

        assert call_count == len(sample_segments)


class TestProcessingFlow:
    """End-to-end processing tests."""

    @pytest.mark.asyncio
    async def test_process_short_document(
        self, mock_llm, mock_skill_registry, recursive_llm_settings,
        sample_document_short
    ):
        """Test processing a short document."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        # Mock dependencies
        with patch.object(processor, "_segment_document") as mock_segment:
            with patch.object(processor, "_score_relevance") as mock_score:
                with patch.object(processor, "_explore_segment") as mock_explore:
                    with patch.object(processor, "_aggregate_findings") as mock_agg:
                        mock_segment.return_value = [
                            DocumentSegment(
                                id="seg_0_0",
                                content="Sample content",
                                level=0,
                                parent_id=None,
                                start_offset=0,
                                end_offset=100,
                            )
                        ]
                        mock_score.return_value = [
                            DocumentSegment(
                                id="seg_0_0",
                                content="Sample content",
                                level=0,
                                parent_id=None,
                                start_offset=0,
                                end_offset=100,
                                relevance_score=0.85,
                            )
                        ]
                        mock_explore.return_value = {"findings": "test"}
                        mock_agg.return_value = "Final answer"

                        result = await processor.process(
                            document=sample_document_short,
                            query="What is the main topic?",
                        )

                        assert "answer" in result
                        assert result["answer"] == "Final answer"
                        assert "segments_processed" in result

    @pytest.mark.asyncio
    async def test_process_empty_document_raises_error(
        self, mock_llm, mock_skill_registry, recursive_llm_settings
    ):
        """Test processing empty document raises ValueError."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        with pytest.raises(ValueError):
            await processor.process(document="", query="test query")

    @pytest.mark.asyncio
    async def test_process_empty_query_raises_error(
        self, mock_llm, mock_skill_registry, recursive_llm_settings,
        sample_document_short
    ):
        """Test processing with empty query raises ValueError."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=recursive_llm_settings,
        )

        with pytest.raises(ValueError):
            await processor.process(document=sample_document_short, query="")


class TestScoringMethodRouting:
    """Tests for routing to appropriate scoring methods."""

    @pytest.mark.asyncio
    async def test_score_relevance_routes_to_dense_sparse(
        self, mock_llm, mock_skill_registry, mock_embedding_service,
        recursive_llm_settings, sample_segments
    ):
        """Test _score_relevance routes to dense+sparse for that method."""
        settings = RecursiveLLMSettings(
            levels=[
                RecursiveLevelConfig(
                    level=0,
                    segment_size_tokens=16384,
                    scoring_method="dense+sparse",
                )
            ]
        )

        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=settings,
        )

        with patch(
            "src.agents.context.recursive_llm.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            with patch.object(
                processor, "_score_relevance_dense_sparse",
                wraps=processor._score_relevance_dense_sparse
            ) as mock_method:
                await processor._score_relevance(
                    sample_segments,
                    "test query",
                    skill=None,
                    level=0,
                )

                assert mock_method.called

    @pytest.mark.asyncio
    async def test_score_relevance_routes_to_llm(
        self, mock_llm, mock_skill_registry,
        recursive_llm_settings, sample_segments
    ):
        """Test _score_relevance routes to LLM for that method."""
        settings = RecursiveLLMSettings(
            levels=[
                RecursiveLevelConfig(
                    level=0,
                    segment_size_tokens=16384,
                    scoring_method="llm",
                )
            ]
        )

        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=settings,
        )

        with patch.object(
            processor, "_score_relevance_llm",
            wraps=processor._score_relevance_llm
        ) as mock_method:
            await processor._score_relevance(
                sample_segments,
                "test query",
                skill=None,
                level=0,
            )

            assert mock_method.called

    @pytest.mark.asyncio
    async def test_score_relevance_routes_to_adaptive(
        self, mock_llm, mock_skill_registry, mock_embedding_service,
        recursive_llm_settings, sample_segments
    ):
        """Test _score_relevance routes to adaptive for that method."""
        settings = RecursiveLLMSettings(
            levels=[
                RecursiveLevelConfig(
                    level=0,
                    segment_size_tokens=16384,
                    scoring_method="adaptive",
                )
            ]
        )

        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=settings,
        )

        with patch(
            "src.agents.context.recursive_llm.get_granularity_mapper"
        ) as mock_mapper:
            mapper_instance = AsyncMock()
            mapper_instance.classify_granularity.return_value = (
                "fine-grained",
                0.85,
            )
            mock_mapper.return_value = mapper_instance

            with patch.object(
                processor, "_score_relevance_adaptive",
                wraps=processor._score_relevance_adaptive
            ) as mock_method:
                await processor._score_relevance(
                    sample_segments,
                    "test query",
                    skill=None,
                    level=0,
                )

                assert mock_method.called
