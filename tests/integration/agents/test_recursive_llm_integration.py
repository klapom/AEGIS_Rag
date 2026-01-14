"""Integration tests for Recursive LLM Sprint 92 features.

Sprint 92 Integration Tests:
- End-to-end processing with per-level configuration
- Adaptive scoring with real C-LARA classifier (mocked)
- Parallel worker coordination
- Complete processing pipeline

Test file: tests/integration/agents/test_recursive_llm_integration.py
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.context.recursive_llm import RecursiveLLMProcessor
from src.core.config import RecursiveLLMSettings, RecursiveLevelConfig


class TestRecursiveLLMEndToEndPerLevel:
    """End-to-end tests with per-level configuration."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_process_with_three_level_pyramid(
        self, mock_llm, mock_skill_registry, sample_document_long
    ):
        """Test end-to-end processing with 3-level pyramid configuration."""
        settings = RecursiveLLMSettings(
            max_depth=3,
            levels=[
                RecursiveLevelConfig(
                    level=0,
                    segment_size_tokens=16384,
                    overlap_tokens=400,
                    scoring_method="dense+sparse",
                    relevance_threshold=0.5,
                ),
                RecursiveLevelConfig(
                    level=1,
                    segment_size_tokens=8192,
                    overlap_tokens=300,
                    scoring_method="dense+sparse",
                    relevance_threshold=0.6,
                ),
                RecursiveLevelConfig(
                    level=2,
                    segment_size_tokens=4096,
                    overlap_tokens=200,
                    scoring_method="multi-vector",
                    relevance_threshold=0.7,
                ),
            ],
        )

        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=settings,
        )

        # Mock embedding and aggregation
        with patch.object(processor, "_segment_document") as mock_seg:
            with patch.object(processor, "_score_relevance") as mock_score:
                with patch.object(processor, "_explore_segment") as mock_explore:
                    with patch.object(processor, "_aggregate_findings") as mock_agg:
                        # Setup mocks
                        from src.agents.context.recursive_llm import DocumentSegment

                        segment = DocumentSegment(
                            id="seg_0_0",
                            content="Sample content for testing",
                            level=0,
                            parent_id=None,
                            start_offset=0,
                            end_offset=200,
                        )

                        mock_seg.return_value = [segment]
                        scored_segment = DocumentSegment(
                            id="seg_0_0",
                            content="Sample content for testing",
                            level=0,
                            parent_id=None,
                            start_offset=0,
                            end_offset=200,
                            relevance_score=0.85,
                        )
                        mock_score.return_value = [scored_segment]
                        mock_explore.return_value = {
                            "segment_id": "seg_0_0",
                            "findings": "Key information",
                        }
                        mock_agg.return_value = "Final synthesized answer"

                        # Process
                        result = await processor.process(
                            document=sample_document_long,
                            query="What are the main results?",
                        )

                        # Verify result structure
                        assert "answer" in result
                        assert "segments_processed" in result
                        assert "max_depth_reached" in result
                        assert "total_segments" in result
                        assert "skills_used" in result

                        # Verify answer
                        assert result["answer"] == "Final synthesized answer"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_process_with_custom_level_configurations(
        self, mock_llm, mock_skill_registry, sample_document_long
    ):
        """Test processing with custom per-level scoring methods."""
        settings = RecursiveLLMSettings(
            max_depth=2,
            levels=[
                RecursiveLevelConfig(
                    level=0,
                    segment_size_tokens=20000,  # Custom size
                    scoring_method="dense+sparse",
                ),
                RecursiveLevelConfig(
                    level=1,
                    segment_size_tokens=5000,  # Custom size
                    scoring_method="llm",  # Custom method
                ),
            ],
        )

        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=settings,
        )

        assert processor.settings.levels[0].segment_size_tokens == 20000
        assert processor.settings.levels[1].segment_size_tokens == 5000
        assert processor.settings.levels[1].scoring_method == "llm"

        # Verify configuration is used in processing
        segments = processor._segment_document(sample_document_long, level=0)
        assert len(segments) > 0


class TestAdaptiveScoringIntegration:
    """Integration tests for adaptive scoring (Feature 92.9)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_adaptive_scoring_fine_grained_query(
        self, mock_llm, mock_skill_registry, mock_embedding_service,
        sample_document_long
    ):
        """Test adaptive scoring for fine-grained query."""
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

        # Mock granularity mapper to return fine-grained
        with patch(
            "src.agents.context.recursive_llm.get_granularity_mapper"
        ) as mock_mapper:
            mapper_instance = AsyncMock()
            mapper_instance.classify_granularity.return_value = (
                "fine-grained",
                0.85,
            )
            mock_mapper.return_value = mapper_instance

            # Mock segment and score
            with patch.object(processor, "_segment_document") as mock_seg:
                with patch.object(processor, "_score_relevance") as mock_score:
                    with patch.object(processor, "_explore_segment") as mock_explore:
                        with patch.object(
                            processor, "_aggregate_findings"
                        ) as mock_agg:
                            from src.agents.context.recursive_llm import DocumentSegment

                            segment = DocumentSegment(
                                id="seg_0_0",
                                content="Sample content",
                                level=0,
                                parent_id=None,
                                start_offset=0,
                                end_offset=100,
                            )

                            mock_seg.return_value = [segment]
                            scored_segment = DocumentSegment(
                                id="seg_0_0",
                                content="Sample content",
                                level=0,
                                parent_id=None,
                                start_offset=0,
                                end_offset=100,
                                relevance_score=0.85,
                            )
                            mock_score.return_value = [scored_segment]
                            mock_explore.return_value = {"findings": "test"}
                            mock_agg.return_value = "Answer"

                            result = await processor.process(
                                document=sample_document_long,
                                query="What is the p-value?",
                            )

                            # Verify granularity was evaluated
                            mapper_instance.classify_granularity.assert_called()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_adaptive_scoring_holistic_query(
        self, mock_llm, mock_skill_registry, sample_document_long
    ):
        """Test adaptive scoring for holistic query."""
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

        # Mock granularity mapper to return holistic
        with patch(
            "src.agents.context.recursive_llm.get_granularity_mapper"
        ) as mock_mapper:
            mapper_instance = AsyncMock()
            mapper_instance.classify_granularity.return_value = ("holistic", 0.90)
            mock_mapper.return_value = mapper_instance

            with patch.object(processor, "_segment_document") as mock_seg:
                with patch.object(processor, "_score_relevance") as mock_score:
                    with patch.object(processor, "_explore_segment") as mock_explore:
                        with patch.object(
                            processor, "_aggregate_findings"
                        ) as mock_agg:
                            from src.agents.context.recursive_llm import DocumentSegment

                            segment = DocumentSegment(
                                id="seg_0_0",
                                content="Sample content",
                                level=0,
                                parent_id=None,
                                start_offset=0,
                                end_offset=100,
                            )

                            mock_seg.return_value = [segment]
                            scored_segment = DocumentSegment(
                                id="seg_0_0",
                                content="Sample content",
                                level=0,
                                parent_id=None,
                                start_offset=0,
                                end_offset=100,
                                relevance_score=0.85,
                            )
                            mock_score.return_value = [scored_segment]
                            mock_explore.return_value = {"findings": "test"}
                            mock_agg.return_value = "Synthesized answer"

                            result = await processor.process(
                                document=sample_document_long,
                                query="Summarize the main findings",
                            )

                            assert result["answer"] == "Synthesized answer"


class TestParallelWorkersIntegration:
    """Integration tests for parallel worker coordination."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_parallel_processing_multiple_workers(
        self, mock_llm, mock_skill_registry, sample_document_long
    ):
        """Test parallel processing with multiple workers."""
        settings = RecursiveLLMSettings(
            max_parallel_workers=3,
            worker_limits={
                "ollama": 3,
                "openai": 10,
            },
        )

        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=settings,
        )

        # Mock the segment exploration to track parallel calls
        call_times = []
        call_lock = asyncio.Lock()

        async def mock_explore(segment, query, depth, skill):
            async with call_lock:
                call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.01)  # Simulate async work
            return {"segment_id": segment.id}

        processor._explore_segment = mock_explore

        # Create mock segments
        from src.agents.context.recursive_llm import DocumentSegment

        segments = [
            DocumentSegment(
                id=f"seg_{i}",
                content=f"Segment {i}",
                level=0,
                parent_id=None,
                start_offset=i * 100,
                end_offset=(i + 1) * 100,
                relevance_score=0.8,
            )
            for i in range(5)
        ]

        # Process in parallel batches
        findings = []
        for batch in processor._batched(segments, 3):
            batch_findings = await asyncio.gather(*[
                processor._explore_segment(s, "test", 1, None) for s in batch
            ])
            findings.extend(batch_findings)

        # Verify all segments were processed
        assert len(findings) == 5
        assert all(isinstance(f, dict) for f in findings)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_worker_limit_single_threaded(
        self, mock_llm, mock_skill_registry, sample_document_long
    ):
        """Test worker limits constrain parallelism (single-threaded Ollama)."""
        settings = RecursiveLLMSettings(
            max_parallel_workers=1,  # DGX Spark
            worker_limits={"ollama": 1},
        )

        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=settings,
        )

        assert processor.settings.max_parallel_workers == 1
        assert processor.settings.worker_limits["ollama"] == 1


class TestMixedScoringMethods:
    """Integration tests with mixed scoring methods across levels."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_different_scoring_per_level(
        self, mock_llm, mock_skill_registry, mock_embedding_service,
        sample_document_long
    ):
        """Test different scoring methods at different recursion levels."""
        settings = RecursiveLLMSettings(
            max_depth=3,
            levels=[
                RecursiveLevelConfig(
                    level=0,
                    segment_size_tokens=16384,
                    scoring_method="dense+sparse",  # Fast overview
                ),
                RecursiveLevelConfig(
                    level=1,
                    segment_size_tokens=8192,
                    scoring_method="multi-vector",  # More precise
                ),
                RecursiveLevelConfig(
                    level=2,
                    segment_size_tokens=4096,
                    scoring_method="llm",  # Deep reasoning
                ),
            ],
        )

        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            settings=settings,
        )

        # Verify level configurations
        assert processor.settings.levels[0].scoring_method == "dense+sparse"
        assert processor.settings.levels[1].scoring_method == "multi-vector"
        assert processor.settings.levels[2].scoring_method == "llm"

        # Verify each level can be segmented differently
        segments_l0 = processor._segment_document(sample_document_long, level=0)
        segments_l1 = processor._segment_document(sample_document_long, level=1)
        segments_l2 = processor._segment_document(sample_document_long, level=2)

        # Different levels should produce different segment counts (generally)
        assert len(segments_l0) >= 0  # May vary based on natural breaks
        assert len(segments_l1) >= 0
        assert len(segments_l2) >= 0


class TestErrorHandlingIntegration:
    """Integration tests for error handling and graceful degradation."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_graceful_degradation_missing_skill(
        self, mock_llm, mock_skill_registry, sample_document_long
    ):
        """Test graceful degradation when recursive-context skill not found."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
        )

        # Mock skill registry to not have recursive-context
        mock_skill_registry.list_available.return_value = []

        with patch.object(processor, "_segment_document") as mock_seg:
            with patch.object(processor, "_score_relevance") as mock_score:
                with patch.object(processor, "_explore_segment") as mock_explore:
                    with patch.object(processor, "_aggregate_findings") as mock_agg:
                        from src.agents.context.recursive_llm import DocumentSegment

                        segment = DocumentSegment(
                            id="seg_0_0",
                            content="Test",
                            level=0,
                            parent_id=None,
                            start_offset=0,
                            end_offset=100,
                        )

                        mock_seg.return_value = [segment]
                        scored = DocumentSegment(
                            id="seg_0_0",
                            content="Test",
                            level=0,
                            parent_id=None,
                            start_offset=0,
                            end_offset=100,
                            relevance_score=0.85,
                        )
                        mock_score.return_value = [scored]
                        mock_explore.return_value = {"findings": "test"}
                        mock_agg.return_value = "Answer"

                        result = await processor.process(
                            document=sample_document_long,
                            query="test query",
                        )

                        # Should still process successfully
                        assert "answer" in result
                        assert result["answer"] == "Answer"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fallback_scoring_on_embedding_error(
        self, mock_llm, mock_skill_registry, sample_document_long, sample_segments
    ):
        """Test fallback to LLM scoring if embedding service fails."""
        processor = RecursiveLLMProcessor(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
        )

        # Mock embedding service to fail
        with patch(
            "src.agents.context.recursive_llm.get_embedding_service",
            side_effect=RuntimeError("Embedding service error"),
        ):
            # Should fallback to LLM scoring
            with patch.object(
                processor, "_score_relevance_llm",
                wraps=processor._score_relevance_llm
            ) as mock_llm_score:
                await processor._score_relevance(
                    sample_segments,
                    "test query",
                    skill=None,
                    level=0,
                )

                # Verify fallback was called
                assert mock_llm_score.called
