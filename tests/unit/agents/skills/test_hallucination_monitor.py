"""Unit tests for Hallucination Monitor.

Sprint Context:
    - Sprint 90 (2026-01-14): Feature 90.3 - Hallucination Monitoring & Logging (8 SP)

Tests:
    - Claim extraction from answers
    - Claim verification against contexts
    - Hallucination score calculation
    - Metrics tracking
    - Comprehensive logging
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
import structlog

from src.agents.skills.hallucination_monitor import (
    Claim,
    ClaimVerification,
    HallucinationMonitor,
    HallucinationReport,
)


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def mock_logger():
    """Mock structured logger."""
    return structlog.get_logger(__name__)


@pytest.fixture
def hallucination_monitor(mock_llm, mock_logger):
    """Create HallucinationMonitor instance."""
    return HallucinationMonitor(llm=mock_llm, logger=mock_logger)


@pytest.fixture
def sample_contexts():
    """Sample contexts for testing."""
    return [
        "The Earth is a sphere that orbits the Sun.",
        "The Moon orbits the Earth and causes tides through gravitational pull.",
        "The Earth's rotation period is approximately 24 hours.",
    ]


class TestClaimExtraction:
    """Test claim extraction from answers."""

    @pytest.mark.asyncio
    async def test_extract_claims_multiple(
        self, hallucination_monitor, mock_llm
    ):
        """Test extracting multiple claims from answer."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = """1. The Earth is a sphere
2. The Earth orbits the Sun
3. The Moon orbits the Earth"""
        mock_llm.ainvoke.return_value = mock_response

        answer = "The Earth is a sphere that orbits the Sun. The Moon orbits the Earth."
        claims = await hallucination_monitor._extract_claims(answer)

        assert len(claims) == 3
        assert all(isinstance(c, Claim) for c in claims)
        assert claims[0].text == "The Earth is a sphere"
        assert claims[1].text == "The Earth orbits the Sun"
        assert claims[2].text == "The Moon orbits the Earth"

    @pytest.mark.asyncio
    async def test_extract_claims_single(
        self, hallucination_monitor, mock_llm
    ):
        """Test extracting single claim."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = "1. Water freezes at 0°C"
        mock_llm.ainvoke.return_value = mock_response

        answer = "Water freezes at 0°C."
        claims = await hallucination_monitor._extract_claims(answer)

        assert len(claims) == 1
        assert claims[0].text == "Water freezes at 0°C"

    @pytest.mark.asyncio
    async def test_extract_claims_bullet_format(
        self, hallucination_monitor, mock_llm
    ):
        """Test extracting claims with bullet points."""
        # Mock LLM response with bullets
        mock_response = MagicMock()
        mock_response.content = """- First claim
- Second claim
- Third claim"""
        mock_llm.ainvoke.return_value = mock_response

        answer = "Multiple claims here."
        claims = await hallucination_monitor._extract_claims(answer)

        assert len(claims) == 3
        assert claims[0].text == "First claim"
        assert claims[1].text == "Second claim"

    @pytest.mark.asyncio
    async def test_extract_claims_handles_dict_response(
        self, hallucination_monitor, mock_llm
    ):
        """Test claim extraction handles dict response."""
        # Mock dict response (AegisLLMProxy format)
        mock_llm.ainvoke.return_value = {
            "content": "1. Claim one\n2. Claim two"
        }

        answer = "Test answer."
        claims = await hallucination_monitor._extract_claims(answer)

        assert len(claims) == 2


class TestClaimVerification:
    """Test claim verification against contexts."""

    @pytest.mark.asyncio
    async def test_verify_supported_claim(
        self, hallucination_monitor, mock_llm, sample_contexts
    ):
        """Test verifying supported claim."""
        # Mock LLM response (claim is supported)
        mock_response = MagicMock()
        mock_response.content = """SUPPORTED: yes
EVIDENCE: The Earth is a sphere that orbits the Sun.
REASONING: The claim directly matches the context statement."""
        mock_llm.ainvoke.return_value = mock_response

        claim = Claim(text="The Earth is a sphere", index=0)
        verification = await hallucination_monitor._verify_claim(
            claim, sample_contexts
        )

        assert isinstance(verification, ClaimVerification)
        assert verification.claim == claim
        assert verification.is_supported is True
        assert "Earth is a sphere" in verification.evidence
        assert len(verification.reasoning) > 0

    @pytest.mark.asyncio
    async def test_verify_unsupported_claim(
        self, hallucination_monitor, mock_llm, sample_contexts
    ):
        """Test verifying unsupported claim."""
        # Mock LLM response (claim is NOT supported)
        mock_response = MagicMock()
        mock_response.content = """SUPPORTED: no
EVIDENCE: none
REASONING: The contexts state Earth is a sphere, not flat."""
        mock_llm.ainvoke.return_value = mock_response

        claim = Claim(text="The Earth is flat", index=0)
        verification = await hallucination_monitor._verify_claim(
            claim, sample_contexts
        )

        assert verification.is_supported is False
        assert "none" in verification.evidence.lower()

    @pytest.mark.asyncio
    async def test_verify_claim_handles_dict_response(
        self, hallucination_monitor, mock_llm, sample_contexts
    ):
        """Test claim verification handles dict response."""
        # Mock dict response
        mock_llm.ainvoke.return_value = {
            "content": "SUPPORTED: yes\nEVIDENCE: Test evidence\nREASONING: Test reasoning"
        }

        claim = Claim(text="Test claim", index=0)
        verification = await hallucination_monitor._verify_claim(
            claim, sample_contexts
        )

        assert verification.is_supported is True


class TestHallucinationCheck:
    """Test full hallucination check."""

    @pytest.mark.asyncio
    async def test_check_no_hallucinations(
        self, hallucination_monitor, mock_llm, sample_contexts
    ):
        """Test checking answer with no hallucinations."""
        # Mock claim extraction
        extract_response = MagicMock()
        extract_response.content = "1. Earth is a sphere\n2. Moon orbits Earth"

        # Mock verification (all supported)
        verify_response = MagicMock()
        verify_response.content = (
            "SUPPORTED: yes\nEVIDENCE: Test\nREASONING: Test"
        )

        mock_llm.ainvoke.side_effect = [
            extract_response,
            verify_response,
            verify_response,
        ]

        answer = "Earth is a sphere and the Moon orbits Earth."
        report = await hallucination_monitor.check(answer, sample_contexts)

        assert isinstance(report, HallucinationReport)
        assert report.hallucination_score == 0.0
        assert len(report.unsupported_claims) == 0
        assert len(report.claims) == 2
        assert len(report.verifications) == 2

    @pytest.mark.asyncio
    async def test_check_partial_hallucinations(
        self, hallucination_monitor, mock_llm, sample_contexts
    ):
        """Test checking answer with partial hallucinations."""
        # Mock claim extraction
        extract_response = MagicMock()
        extract_response.content = "1. Earth is a sphere\n2. Earth is flat"

        # Mock verification (one supported, one not)
        verify_supported = MagicMock()
        verify_supported.content = (
            "SUPPORTED: yes\nEVIDENCE: Test\nREASONING: Test"
        )

        verify_unsupported = MagicMock()
        verify_unsupported.content = (
            "SUPPORTED: no\nEVIDENCE: none\nREASONING: Contradicts context"
        )

        mock_llm.ainvoke.side_effect = [
            extract_response,
            verify_supported,
            verify_unsupported,
        ]

        answer = "Earth is a sphere but also flat."
        report = await hallucination_monitor.check(answer, sample_contexts)

        assert report.hallucination_score == 0.5  # 1 out of 2 unsupported
        assert len(report.unsupported_claims) == 1
        assert "Earth is flat" in report.unsupported_claims

    @pytest.mark.asyncio
    async def test_check_all_hallucinations(
        self, hallucination_monitor, mock_llm, sample_contexts
    ):
        """Test checking answer with all hallucinations."""
        # Mock claim extraction
        extract_response = MagicMock()
        extract_response.content = "1. Earth is flat\n2. Moon is made of cheese"

        # Mock verification (all unsupported)
        verify_unsupported = MagicMock()
        verify_unsupported.content = (
            "SUPPORTED: no\nEVIDENCE: none\nREASONING: Not in contexts"
        )

        mock_llm.ainvoke.side_effect = [
            extract_response,
            verify_unsupported,
            verify_unsupported,
        ]

        answer = "Earth is flat and the Moon is made of cheese."
        report = await hallucination_monitor.check(answer, sample_contexts)

        assert report.hallucination_score == 1.0  # All claims unsupported
        assert len(report.unsupported_claims) == 2

    @pytest.mark.asyncio
    async def test_check_empty_answer(
        self, hallucination_monitor, mock_llm, sample_contexts
    ):
        """Test checking empty answer."""
        # Mock empty claim extraction
        extract_response = MagicMock()
        extract_response.content = ""

        mock_llm.ainvoke.return_value = extract_response

        answer = ""
        report = await hallucination_monitor.check(answer, sample_contexts)

        assert report.hallucination_score == 0.0
        assert len(report.claims) == 0


class TestMetricsTracking:
    """Test metrics tracking."""

    @pytest.mark.asyncio
    async def test_metrics_initialization(self, hallucination_monitor):
        """Test metrics are initialized correctly."""
        metrics = hallucination_monitor.get_metrics()
        assert metrics["total_checks"] == 0
        assert metrics["hallucinations_detected"] == 0
        assert metrics["claims_verified"] == 0
        assert metrics["claims_unsupported"] == 0

    @pytest.mark.asyncio
    async def test_metrics_after_check(
        self, hallucination_monitor, mock_llm, sample_contexts
    ):
        """Test metrics updated after check."""
        # Mock claim extraction
        extract_response = MagicMock()
        extract_response.content = "1. Claim one\n2. Claim two"

        # Mock verification (one supported, one not)
        verify_supported = MagicMock()
        verify_supported.content = (
            "SUPPORTED: yes\nEVIDENCE: Test\nREASONING: Test"
        )

        verify_unsupported = MagicMock()
        verify_unsupported.content = (
            "SUPPORTED: no\nEVIDENCE: none\nREASONING: Not supported"
        )

        mock_llm.ainvoke.side_effect = [
            extract_response,
            verify_supported,
            verify_unsupported,
        ]

        await hallucination_monitor.check("Test answer", sample_contexts)

        metrics = hallucination_monitor.get_metrics()
        assert metrics["total_checks"] == 1
        assert metrics["hallucinations_detected"] == 1  # Score > 0.1
        assert metrics["claims_verified"] == 1
        assert metrics["claims_unsupported"] == 1

    @pytest.mark.asyncio
    async def test_metrics_multiple_checks(
        self, hallucination_monitor, mock_llm, sample_contexts
    ):
        """Test metrics accumulate over multiple checks."""
        # First check
        extract_response1 = MagicMock()
        extract_response1.content = "1. Claim one"

        verify_supported = MagicMock()
        verify_supported.content = (
            "SUPPORTED: yes\nEVIDENCE: Test\nREASONING: Test"
        )

        # Second check
        extract_response2 = MagicMock()
        extract_response2.content = "1. Claim two\n2. Claim three"

        verify_unsupported = MagicMock()
        verify_unsupported.content = (
            "SUPPORTED: no\nEVIDENCE: none\nREASONING: Not supported"
        )

        mock_llm.ainvoke.side_effect = [
            extract_response1,
            verify_supported,
            extract_response2,
            verify_unsupported,
            verify_unsupported,
        ]

        await hallucination_monitor.check("First answer", sample_contexts)
        await hallucination_monitor.check("Second answer", sample_contexts)

        metrics = hallucination_monitor.get_metrics()
        assert metrics["total_checks"] == 2
        assert metrics["hallucinations_detected"] == 1  # Only second check
        assert metrics["claims_verified"] == 1
        assert metrics["claims_unsupported"] == 2


class TestFormatContexts:
    """Test context formatting."""

    def test_format_contexts(self, hallucination_monitor, sample_contexts):
        """Test formatting contexts with numbered list."""
        formatted = hallucination_monitor._format_contexts(sample_contexts)
        assert "[1]" in formatted
        assert "[2]" in formatted
        assert "[3]" in formatted
        assert sample_contexts[0] in formatted

    def test_format_empty_contexts(self, hallucination_monitor):
        """Test formatting empty contexts."""
        formatted = hallucination_monitor._format_contexts([])
        assert formatted == ""


class TestLogging:
    """Test comprehensive logging."""

    @pytest.mark.asyncio
    async def test_log_check_pass(
        self, hallucination_monitor, mock_llm, sample_contexts
    ):
        """Test logging for PASS verdict (score < 0.1)."""
        # Mock all supported claims
        extract_response = MagicMock()
        extract_response.content = "1. Claim one"

        verify_supported = MagicMock()
        verify_supported.content = (
            "SUPPORTED: yes\nEVIDENCE: Test\nREASONING: Test"
        )

        mock_llm.ainvoke.side_effect = [extract_response, verify_supported]

        report = await hallucination_monitor.check(
            "Test answer", sample_contexts
        )

        # Verify verdict is PASS
        assert report.hallucination_score < 0.1

    @pytest.mark.asyncio
    async def test_log_check_warn(
        self, hallucination_monitor, mock_llm, sample_contexts
    ):
        """Test logging for WARN verdict (0.1 <= score < 0.3)."""
        # Mock 2 claims, 1 unsupported (score = 0.5, but we need 0.1-0.3)
        extract_response = MagicMock()
        extract_response.content = "1. Claim one\n2. Claim two\n3. Claim three\n4. Claim four\n5. Claim five"

        # 1 unsupported out of 5 = 0.2 (WARN)
        verify_supported = MagicMock()
        verify_supported.content = (
            "SUPPORTED: yes\nEVIDENCE: Test\nREASONING: Test"
        )

        verify_unsupported = MagicMock()
        verify_unsupported.content = (
            "SUPPORTED: no\nEVIDENCE: none\nREASONING: Not supported"
        )

        mock_llm.ainvoke.side_effect = [
            extract_response,
            verify_supported,
            verify_supported,
            verify_supported,
            verify_supported,
            verify_unsupported,
        ]

        report = await hallucination_monitor.check(
            "Test answer", sample_contexts
        )

        # Verify verdict is WARN
        assert 0.1 <= report.hallucination_score < 0.3

    @pytest.mark.asyncio
    async def test_log_check_fail(
        self, hallucination_monitor, mock_llm, sample_contexts
    ):
        """Test logging for FAIL verdict (score >= 0.3)."""
        # Mock majority unsupported
        extract_response = MagicMock()
        extract_response.content = "1. Claim one\n2. Claim two"

        verify_unsupported = MagicMock()
        verify_unsupported.content = (
            "SUPPORTED: no\nEVIDENCE: none\nREASONING: Not supported"
        )

        mock_llm.ainvoke.side_effect = [
            extract_response,
            verify_unsupported,
            verify_unsupported,
        ]

        report = await hallucination_monitor.check(
            "Test answer", sample_contexts
        )

        # Verify verdict is FAIL
        assert report.hallucination_score >= 0.3
