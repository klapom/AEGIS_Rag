"""Unit tests for EvalHarness (Feature 67.6).

Sprint 67 Feature 67.6: Automated quality gates for RAG responses.

Test Coverage:
- QualityCheck enum and EvalResult dataclass
- EvalHarness initialization with custom thresholds
- Format compliance check (markdown validation)
- Citation coverage check (citation parsing)
- Grounding check (LLM-based validation)
- Error handling and edge cases

Target: >80% code coverage
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adaptation.eval_harness import EvalHarness, EvalResult, QualityCheck
from src.core.exceptions import EvaluationError
from src.domains.llm_integration.models import LLMResponse


class TestQualityCheckEnum:
    """Test QualityCheck enum."""

    def test_quality_check_values(self):
        """Test QualityCheck enum has correct values."""
        assert QualityCheck.GROUNDING.value == "grounding"
        assert QualityCheck.CITATION_COVERAGE.value == "citation_coverage"
        assert QualityCheck.FORMAT_COMPLIANCE.value == "format_compliance"

    def test_quality_check_is_string_enum(self):
        """Test QualityCheck is a string enum."""
        assert isinstance(QualityCheck.GROUNDING, str)
        assert QualityCheck.GROUNDING == "grounding"


class TestEvalResult:
    """Test EvalResult dataclass."""

    def test_eval_result_creation(self):
        """Test creating EvalResult."""
        result = EvalResult(
            check=QualityCheck.GROUNDING,
            passed=True,
            score=0.85,
            details={"claims": 10},
            latency_ms=250.5,
        )

        assert result.check == QualityCheck.GROUNDING
        assert result.passed is True
        assert result.score == 0.85
        assert result.details == {"claims": 10}
        assert result.latency_ms == 250.5

    def test_eval_result_repr(self):
        """Test EvalResult string representation."""
        result = EvalResult(
            check=QualityCheck.FORMAT_COMPLIANCE,
            passed=False,
            score=0.60,
            latency_ms=50.2,
        )

        repr_str = repr(result)
        assert "EvalResult" in repr_str
        assert "format_compliance" in repr_str
        assert "FAIL" in repr_str
        assert "0.600" in repr_str
        assert "50.2ms" in repr_str

    def test_eval_result_default_values(self):
        """Test EvalResult default values."""
        result = EvalResult(
            check=QualityCheck.CITATION_COVERAGE,
            passed=True,
            score=0.9,
        )

        assert result.details == {}
        assert result.latency_ms == 0.0


class TestEvalHarnessInitialization:
    """Test EvalHarness initialization."""

    def test_init_with_default_thresholds(self):
        """Test initialization with default thresholds."""
        harness = EvalHarness()

        assert harness.thresholds[QualityCheck.GROUNDING] == 0.8
        assert harness.thresholds[QualityCheck.CITATION_COVERAGE] == 0.7
        assert harness.thresholds[QualityCheck.FORMAT_COMPLIANCE] == 0.95

    def test_init_with_custom_thresholds(self):
        """Test initialization with custom thresholds."""
        custom_thresholds = {
            QualityCheck.GROUNDING: 0.9,
            QualityCheck.CITATION_COVERAGE: 0.6,
            QualityCheck.FORMAT_COMPLIANCE: 1.0,
        }
        harness = EvalHarness(thresholds=custom_thresholds)

        assert harness.thresholds[QualityCheck.GROUNDING] == 0.9
        assert harness.thresholds[QualityCheck.CITATION_COVERAGE] == 0.6
        assert harness.thresholds[QualityCheck.FORMAT_COMPLIANCE] == 1.0

    def test_init_with_invalid_threshold_high(self):
        """Test initialization with threshold > 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            EvalHarness(thresholds={QualityCheck.GROUNDING: 1.5})

    def test_init_with_invalid_threshold_low(self):
        """Test initialization with threshold < 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            EvalHarness(thresholds={QualityCheck.CITATION_COVERAGE: -0.1})

    def test_init_with_llm_proxy(self):
        """Test initialization with pre-configured LLM proxy."""
        mock_proxy = MagicMock()
        harness = EvalHarness(llm_proxy=mock_proxy)

        assert harness._llm_proxy is mock_proxy


class TestFormatCheck:
    """Test _check_format() method."""

    @pytest.mark.asyncio
    async def test_check_format_valid_markdown(self):
        """Test format check with valid markdown."""
        harness = EvalHarness()
        answer = """
# Valid Answer

This is a well-formatted answer with citations [1][2].

- List item 1
- List item 2

[Link text](https://example.com)
"""
        result = await harness._check_format(answer)

        assert result.check == QualityCheck.FORMAT_COMPLIANCE
        assert result.passed is True
        assert result.score == 1.0
        assert result.details["issue_count"] == 0
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_check_format_empty_heading(self):
        """Test format check detects empty headings."""
        harness = EvalHarness()
        answer = """
##

Some content [1].
"""
        result = await harness._check_format(answer)

        assert result.check == QualityCheck.FORMAT_COMPLIANCE
        assert result.score < 1.0
        assert result.details["issue_count"] > 0
        assert any("Empty heading" in str(issue) for issue in result.details["issues"])

    @pytest.mark.asyncio
    async def test_check_format_empty_list_item(self):
        """Test format check detects empty list items."""
        harness = EvalHarness()
        answer = """
-

Content [1].
"""
        result = await harness._check_format(answer)

        assert result.score < 1.0
        assert any("Empty list item" in str(issue) for issue in result.details["issues"])

    @pytest.mark.asyncio
    async def test_check_format_empty_link(self):
        """Test format check detects empty links."""
        harness = EvalHarness()
        answer = "[Click here]() for more information [1]."

        result = await harness._check_format(answer)

        assert result.score < 1.0
        assert any("Empty link" in str(issue) for issue in result.details["issues"])

    @pytest.mark.asyncio
    async def test_check_format_non_sequential_citations(self):
        """Test format check detects non-sequential citations."""
        harness = EvalHarness()
        answer = "This is supported by sources [1][3][5]."

        result = await harness._check_format(answer)

        assert result.score < 1.0
        issues = result.details["issues"]
        assert any("Non-sequential" in str(issue) for issue in issues)

    @pytest.mark.asyncio
    async def test_check_format_multiple_issues(self):
        """Test format check with multiple issues."""
        harness = EvalHarness()
        answer = """
##

-

[Link]()

Citations [1][5].
"""
        result = await harness._check_format(answer)

        # Each issue type reduces score by 0.1
        assert result.score < 0.7
        assert result.details["issue_count"] >= 3

    @pytest.mark.asyncio
    async def test_check_format_latency(self):
        """Test format check completes within 100ms."""
        harness = EvalHarness()
        answer = "Valid markdown with citations [1][2][3]." * 100

        result = await harness._check_format(answer)

        # Should be well under 100ms for regex-based check
        assert result.latency_ms < 100


class TestCitationCoverageCheck:
    """Test _check_citation_coverage() method."""

    @pytest.mark.asyncio
    async def test_check_citation_coverage_full_coverage(self):
        """Test citation coverage with all sentences cited."""
        harness = EvalHarness()
        answer = "First claim [1]. Second claim [2]. Third claim [3]."
        sources = [
            {"chunk_id": "c1", "text": "Source 1"},
            {"chunk_id": "c2", "text": "Source 2"},
            {"chunk_id": "c3", "text": "Source 3"},
        ]

        result = await harness._check_citation_coverage(answer, sources)

        assert result.check == QualityCheck.CITATION_COVERAGE
        assert result.score == 1.0  # 100% coverage
        assert result.passed is True
        assert result.details["total_sentences"] == 3
        assert result.details["sentences_with_citations"] == 3

    @pytest.mark.asyncio
    async def test_check_citation_coverage_partial_coverage(self):
        """Test citation coverage with some uncited sentences."""
        harness = EvalHarness()
        answer = "Cited claim [1]. Uncited claim. Another cited claim [2]."
        sources = [{"chunk_id": "c1", "text": "Source 1"}, {"chunk_id": "c2", "text": "Source 2"}]

        result = await harness._check_citation_coverage(answer, sources)

        assert result.score < 1.0
        assert result.details["citation_coverage"] < 1.0
        # 2 out of 3 sentences cited = ~0.67
        assert abs(result.details["citation_coverage"] - 0.67) < 0.01

    @pytest.mark.asyncio
    async def test_check_citation_coverage_no_citations(self):
        """Test citation coverage with no citations."""
        harness = EvalHarness()
        answer = "Uncited claim. Another uncited claim."
        sources = [{"chunk_id": "c1", "text": "Source"}]

        result = await harness._check_citation_coverage(answer, sources)

        assert result.score == 0.0
        assert result.passed is False
        assert "No citations found" in str(result.details["warnings"])

    @pytest.mark.asyncio
    async def test_check_citation_coverage_invalid_citations(self):
        """Test citation coverage with invalid citation numbers."""
        harness = EvalHarness()
        answer = "Claim with invalid citation [5]."
        sources = [{"chunk_id": "c1", "text": "Source 1"}]  # Only 1 source

        result = await harness._check_citation_coverage(answer, sources)

        # Score is halved due to invalid citations (1.0 * 0.5 = 0.5)
        assert result.score <= 0.5
        assert 5 in result.details["invalid_citations"]
        assert "Invalid citation numbers" in str(result.details["warnings"])

    @pytest.mark.asyncio
    async def test_check_citation_coverage_multiple_citations_per_sentence(self):
        """Test citation coverage with multiple citations per sentence."""
        harness = EvalHarness()
        answer = "Multi-cited claim [1][2][3]."
        sources = [
            {"chunk_id": "c1", "text": "S1"},
            {"chunk_id": "c2", "text": "S2"},
            {"chunk_id": "c3", "text": "S3"},
        ]

        result = await harness._check_citation_coverage(answer, sources)

        assert result.score == 1.0
        assert set(result.details["cited_numbers"]) == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_check_citation_coverage_latency(self):
        """Test citation coverage check completes within 100ms."""
        harness = EvalHarness()
        answer = "Claim [1]. " * 50  # 50 sentences
        sources = [{"chunk_id": f"c{i}", "text": f"Source {i}"} for i in range(1, 51)]

        result = await harness._check_citation_coverage(answer, sources)

        # Should be well under 100ms for parsing-based check
        assert result.latency_ms < 100


class TestGroundingCheck:
    """Test _check_grounding() method."""

    @pytest.mark.asyncio
    async def test_check_grounding_success(self):
        """Test grounding check with successful LLM validation."""
        harness = EvalHarness()

        # Mock LLM response (all required fields for Pydantic validation)
        mock_response = LLMResponse(
            content='{"grounding_score": 0.9, "total_claims": 5, "grounded_claims": 5, "ungrounded_claims": [], "reasoning": "All claims supported"}',
            provider="local_ollama",
            model="qwen2.5:7b",
            tokens_used=100,
            cost_usd=0.0,
            latency_ms=300,
        )

        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        harness._llm_proxy = mock_proxy

        answer = "RAG is Retrieval Augmented Generation [1]."
        sources = [{"chunk_id": "c1", "text": "RAG definition..."}]

        result = await harness._check_grounding(answer, sources)

        assert result.check == QualityCheck.GROUNDING
        assert result.score == 0.9
        assert result.passed is True  # 0.9 >= 0.8 threshold
        assert result.details["total_claims"] == 5
        assert result.details["grounded_claims"] == 5
        assert result.details["reasoning"] == "All claims supported"

    @pytest.mark.asyncio
    async def test_check_grounding_json_in_markdown(self):
        """Test grounding check handles JSON in markdown code block."""
        harness = EvalHarness()

        # Mock LLM response with markdown code block
        mock_response = LLMResponse(
            content='```json\n{"grounding_score": 0.85, "total_claims": 4, "grounded_claims": 3, "ungrounded_claims": ["Claim X"], "reasoning": "Mostly grounded"}\n```',
            provider="local_ollama",
            model="qwen2.5:7b",
            tokens_used=100,
            cost_usd=0.0,
            latency_ms=250,
        )

        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        harness._llm_proxy = mock_proxy

        answer = "Answer [1]."
        sources = [{"chunk_id": "c1", "text": "Source"}]

        result = await harness._check_grounding(answer, sources)

        assert result.score == 0.85
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_check_grounding_low_score(self):
        """Test grounding check with low grounding score."""
        harness = EvalHarness()

        mock_response = LLMResponse(
            content='{"grounding_score": 0.5, "total_claims": 4, "grounded_claims": 2, "ungrounded_claims": ["Claim A", "Claim B"], "reasoning": "Half grounded"}',
            provider="local_ollama",
            model="qwen2.5:7b",
            tokens_used=100,
            cost_usd=0.0,
            latency_ms=280,
        )

        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        harness._llm_proxy = mock_proxy

        answer = "Answer [1]."
        sources = [{"chunk_id": "c1", "text": "Source"}]

        result = await harness._check_grounding(answer, sources)

        assert result.score == 0.5
        assert result.passed is False  # 0.5 < 0.8 threshold
        assert len(result.details["ungrounded_claims"]) == 2

    @pytest.mark.asyncio
    async def test_check_grounding_llm_error(self):
        """Test grounding check handles LLM errors gracefully."""
        from src.core.exceptions import LLMExecutionError

        harness = EvalHarness()

        # Patch the _llm_proxy attribute directly instead of the property
        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(side_effect=LLMExecutionError("LLM failed"))
        harness._llm_proxy = mock_proxy

        answer = "Answer [1]."
        sources = [{"chunk_id": "c1", "text": "Source"}]

        result = await harness._check_grounding(answer, sources)

        # Should return failed result, not raise exception
        assert result.passed is False
        assert result.score == 0.0
        assert "error" in result.details

    @pytest.mark.asyncio
    async def test_check_grounding_invalid_json(self):
        """Test grounding check handles invalid JSON response."""
        harness = EvalHarness()

        mock_response = LLMResponse(
            content="Invalid JSON response",
            provider="local_ollama",
            model="qwen2.5:7b",
            tokens_used=50,
            cost_usd=0.0,
            latency_ms=200,
        )

        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        harness._llm_proxy = mock_proxy

        answer = "Answer [1]."
        sources = [{"chunk_id": "c1", "text": "Source"}]

        result = await harness._check_grounding(answer, sources)

        # Should fail gracefully
        assert result.passed is False
        assert result.score == 0.0
        assert "error" in result.details

    @pytest.mark.asyncio
    async def test_check_grounding_source_truncation(self):
        """Test grounding check truncates long sources."""
        harness = EvalHarness()

        mock_response = LLMResponse(
            content='{"grounding_score": 0.9, "total_claims": 1, "grounded_claims": 1, "ungrounded_claims": [], "reasoning": "OK"}',
            provider="local_ollama",
            model="qwen2.5:7b",
            tokens_used=100,
            cost_usd=0.0,
            latency_ms=250,
        )

        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        harness._llm_proxy = mock_proxy

        answer = "Answer [1]."
        sources = [{"chunk_id": "c1", "text": "x" * 1000}]  # Long source

        result = await harness._check_grounding(answer, sources)

        # Verify source was truncated in prompt (check mock call)
        call_args = mock_proxy.generate.call_args
        task = call_args[0][0]
        # Source should be truncated to 500 chars
        assert len(sources[0]["text"]) == 1000
        assert "[1] " + "x" * 500 in task.prompt


class TestEvaluateResponse:
    """Test evaluate_response() method."""

    @pytest.mark.asyncio
    async def test_evaluate_response_all_checks(self):
        """Test evaluate_response runs all three checks."""
        harness = EvalHarness()

        # Mock grounding check LLM call
        mock_response = LLMResponse(
            content='{"grounding_score": 0.9, "total_claims": 2, "grounded_claims": 2, "ungrounded_claims": [], "reasoning": "OK"}',
            provider="local_ollama",
            model="qwen2.5:7b",
            tokens_used=100,
            cost_usd=0.0,
            latency_ms=250,
        )

        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        harness._llm_proxy = mock_proxy

        query = "What is RAG?"
        answer = "RAG is Retrieval Augmented Generation [1]. It combines retrieval and generation [2]."
        sources = [
            {"chunk_id": "c1", "text": "RAG definition"},
            {"chunk_id": "c2", "text": "RAG architecture"},
        ]

        results = await harness.evaluate_response(query, answer, sources)

        # Should return 3 results
        assert len(results) == 3
        check_types = {r.check for r in results}
        assert QualityCheck.FORMAT_COMPLIANCE in check_types
        assert QualityCheck.CITATION_COVERAGE in check_types
        assert QualityCheck.GROUNDING in check_types

        # All should pass
        assert all(r.passed for r in results)

    @pytest.mark.asyncio
    async def test_evaluate_response_handles_exception(self):
        """Test evaluate_response raises EvaluationError on failure."""
        harness = EvalHarness()

        # Mock format check to raise exception
        with patch.object(harness, "_check_format", side_effect=Exception("Test error")):
            query = "What is RAG?"
            answer = "RAG [1]."
            sources = [{"chunk_id": "c1", "text": "Source"}]

            with pytest.raises(EvaluationError, match="Evaluation failed"):
                await harness.evaluate_response(query, answer, sources)

    @pytest.mark.asyncio
    async def test_evaluate_response_logs_metrics(self):
        """Test evaluate_response logs completion metrics."""
        harness = EvalHarness()

        # Mock grounding check
        mock_response = LLMResponse(
            content='{"grounding_score": 0.9, "total_claims": 1, "grounded_claims": 1, "ungrounded_claims": [], "reasoning": "OK"}',
            provider="local_ollama",
            model="qwen2.5:7b",
            tokens_used=100,
            cost_usd=0.0,
            latency_ms=200,
        )

        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        harness._llm_proxy = mock_proxy

        with patch.object(harness.logger, "info") as mock_log:
            query = "Test"
            answer = "Answer [1]."
            sources = [{"chunk_id": "c1", "text": "Source"}]

            await harness.evaluate_response(query, answer, sources)

            # Verify logging
            log_calls = [call[0][0] for call in mock_log.call_args_list]
            assert "eval_response_completed" in log_calls


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_answer(self):
        """Test evaluation with empty answer."""
        harness = EvalHarness()
        answer = ""
        sources = [{"chunk_id": "c1", "text": "Source"}]

        # Should not crash
        result = await harness._check_format(answer)
        assert result.score >= 0.0

    @pytest.mark.asyncio
    async def test_empty_sources(self):
        """Test evaluation with no sources."""
        harness = EvalHarness()
        answer = "Answer [1]."
        sources = []

        result = await harness._check_citation_coverage(answer, sources)
        # Citation [1] is invalid (no sources)
        assert 1 in result.details["invalid_citations"]

    @pytest.mark.asyncio
    async def test_source_without_text_field(self):
        """Test grounding check with sources missing 'text' field."""
        harness = EvalHarness()

        mock_response = LLMResponse(
            content='{"grounding_score": 0.9, "total_claims": 1, "grounded_claims": 1, "ungrounded_claims": [], "reasoning": "OK"}',
            provider="local_ollama",
            model="qwen2.5:7b",
            tokens_used=100,
            cost_usd=0.0,
            latency_ms=200,
        )

        mock_proxy = MagicMock()
        mock_proxy.generate = AsyncMock(return_value=mock_response)
        harness._llm_proxy = mock_proxy

        answer = "Answer [1]."
        sources = [{"chunk_id": "c1", "content": "Source content"}]  # 'content' instead of 'text'

        # Should handle gracefully
        result = await harness._check_grounding(answer, sources)
        assert result.score >= 0.0
