"""Unit tests for research synthesizer.

Sprint 70 Feature 70.3: Test synthesizer with AnswerGenerator reuse.
"""

import pytest

from src.agents.research.synthesizer import (
    evaluate_synthesis_quality,
    synthesize_research_findings,
)


class TestSynthesizeResearchFindings:
    """Test research findings synthesis."""

    @pytest.mark.asyncio
    async def test_synthesize_success(self, mocker):
        """Test successful synthesis."""
        # Mock AnswerGenerator
        mock_generator = mocker.MagicMock()
        mock_generator.generate_with_citations = mocker.AsyncMock(
            return_value={
                "answer": "OMNITRACKER is a workflow management system that integrates with SAP.",
                "sources": [
                    {"index": 1, "text": "OMNITRACKER context", "score": 0.9},
                ],
            }
        )

        mocker.patch(
            "src.agents.answer_generator.AnswerGenerator",
            return_value=mock_generator,
        )

        # Execute
        contexts = [
            {"text": "OMNITRACKER is a workflow system", "score": 0.9, "source_channel": "vector"},
            {"text": "OMNITRACKER integrates with SAP", "score": 0.8, "source_channel": "graph_global"},
        ]

        result = await synthesize_research_findings(
            query="What is OMNITRACKER?",
            contexts=contexts,
            namespace="omnitracker",
        )

        # Verify
        assert "answer" in result
        assert "sources" in result
        assert "metadata" in result
        assert "OMNITRACKER" in result["answer"]
        assert len(result["sources"]) == 1
        assert result["metadata"]["synthesis_method"] == "AnswerGenerator"

        # Verify AnswerGenerator was called correctly
        mock_generator.generate_with_citations.assert_called_once()
        call_args = mock_generator.generate_with_citations.call_args
        assert call_args[1]["query"] == "What is OMNITRACKER?"
        assert len(call_args[1]["contexts"]) == 2
        assert call_args[1]["intent"] == "hybrid"

    @pytest.mark.asyncio
    async def test_synthesize_no_contexts(self, mocker):
        """Test synthesis with no contexts."""
        # Execute
        result = await synthesize_research_findings(
            query="What is AI?",
            contexts=[],
            namespace="default",
        )

        # Should return no information message
        assert result["answer"] == "No information found to answer the query."
        assert len(result["sources"]) == 0
        assert result["metadata"]["num_contexts"] == 0

    @pytest.mark.asyncio
    async def test_synthesize_generator_error(self, mocker):
        """Test fallback when AnswerGenerator fails."""
        # Mock AnswerGenerator to fail
        mock_generator = mocker.MagicMock()
        mock_generator.generate_with_citations = mocker.AsyncMock(
            side_effect=Exception("Generator error")
        )

        mocker.patch(
            "src.agents.answer_generator.AnswerGenerator",
            return_value=mock_generator,
        )

        # Execute
        contexts = [
            {"text": "Context 1", "score": 0.9, "source_channel": "vector"},
            {"text": "Context 2", "score": 0.8, "source_channel": "bm25"},
        ]

        result = await synthesize_research_findings(
            query="What is AI?",
            contexts=contexts,
        )

        # Should use fallback synthesis
        assert "answer" in result
        assert "sources" in result
        assert result["metadata"]["fallback"] is True
        assert "Research findings for:" in result["answer"]

    @pytest.mark.asyncio
    async def test_synthesize_temperature(self, mocker):
        """Test that synthesizer uses lower temperature for research."""
        mock_generator_class = mocker.MagicMock()
        mock_generator = mocker.MagicMock()
        mock_generator.generate_with_citations = mocker.AsyncMock(
            return_value={"answer": "Test answer", "sources": []}
        )
        mock_generator_class.return_value = mock_generator

        mocker.patch(
            "src.agents.answer_generator.AnswerGenerator",
            mock_generator_class,
        )

        # Execute
        contexts = [{"text": "Context", "score": 0.9, "source_channel": "vector"}]
        await synthesize_research_findings(
            query="Test query",
            contexts=contexts,
        )

        # Verify AnswerGenerator was created with temperature=0.2
        mock_generator_class.assert_called_once_with(temperature=0.2)


class TestEvaluateSynthesisQuality:
    """Test synthesis quality evaluation."""

    def test_evaluate_excellent_synthesis(self):
        """Test evaluation of excellent synthesis."""
        result = {
            "answer": "A" * 600,  # Long answer
            "sources": [
                {"index": 1},
                {"index": 2},
                {"index": 3},
                {"index": 4},
            ],  # Many citations
            "metadata": {"num_contexts": 10},
        }

        metrics = evaluate_synthesis_quality(result)

        assert metrics["answer_length"] == 600
        assert metrics["num_contexts"] == 10
        assert metrics["num_sources_cited"] == 4
        assert metrics["citation_rate"] == 0.4
        assert metrics["quality_score"] > 0.8
        assert metrics["has_fallback"] is False

    def test_evaluate_good_synthesis(self):
        """Test evaluation of good synthesis."""
        result = {
            "answer": "A" * 300,  # Medium answer
            "sources": [{"index": 1}, {"index": 2}],  # Some citations
            "metadata": {"num_contexts": 5},
        }

        metrics = evaluate_synthesis_quality(result)

        assert metrics["answer_length"] == 300
        assert 0.5 < metrics["quality_score"] < 0.8

    def test_evaluate_poor_synthesis(self):
        """Test evaluation of poor synthesis."""
        result = {
            "answer": "Short",  # Short answer
            "sources": [],  # No citations
            "metadata": {"num_contexts": 2},
        }

        metrics = evaluate_synthesis_quality(result)

        assert metrics["answer_length"] == 5
        assert metrics["num_sources_cited"] == 0
        assert metrics["quality_score"] < 0.5
        assert metrics["has_citations"] is False

    def test_evaluate_fallback_synthesis(self):
        """Test evaluation of fallback synthesis."""
        result = {
            "answer": "Fallback answer",
            "sources": [],
            "metadata": {"fallback": True, "num_contexts": 0},
        }

        metrics = evaluate_synthesis_quality(result)

        assert metrics["has_fallback"] is True
        assert metrics["quality_score"] == 0.0

    def test_evaluate_empty_synthesis(self):
        """Test evaluation of empty synthesis."""
        result = {
            "answer": "",
            "sources": [],
            "metadata": {},
        }

        metrics = evaluate_synthesis_quality(result)

        assert metrics["answer_length"] == 0
        assert metrics["num_contexts"] == 0
        assert metrics["quality_score"] == 0.0
