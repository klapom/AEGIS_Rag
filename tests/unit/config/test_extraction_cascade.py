"""Unit tests for Extraction Cascade Configuration.

Sprint 83 Feature 83.2: LLM Fallback & Retry Strategy

Tests:
- CascadeRankConfig validation
- Default cascade configuration
- Domain-specific cascade retrieval
- Cascade fallback logging
"""

import pytest

from src.config.extraction_cascade import (
    CascadeRankConfig,
    DEFAULT_CASCADE,
    ExtractionMethod,
    get_cascade_for_domain,
    log_cascade_fallback,
)


class TestCascadeRankConfig:
    """Test suite for CascadeRankConfig dataclass."""

    def test_valid_config(self) -> None:
        """Test valid CascadeRankConfig creation."""
        config = CascadeRankConfig(
            rank=1,
            model="nemotron3",
            method=ExtractionMethod.LLM_ONLY,
            entity_timeout_s=300,
            relation_timeout_s=300,
            max_retries=3,
            retry_backoff_multiplier=1,
        )

        assert config.rank == 1
        assert config.model == "nemotron3"
        assert config.method == ExtractionMethod.LLM_ONLY
        assert config.entity_timeout_s == 300
        assert config.relation_timeout_s == 300
        assert config.max_retries == 3
        assert config.retry_backoff_multiplier == 1

    def test_invalid_rank_too_low(self) -> None:
        """Test CascadeRankConfig validation fails with rank < 1."""
        with pytest.raises(ValueError, match="Rank must be 1-3"):
            CascadeRankConfig(
                rank=0,
                model="nemotron3",
                method=ExtractionMethod.LLM_ONLY,
                entity_timeout_s=300,
                relation_timeout_s=300,
            )

    def test_invalid_rank_too_high(self) -> None:
        """Test CascadeRankConfig validation fails with rank > 3."""
        with pytest.raises(ValueError, match="Rank must be 1-3"):
            CascadeRankConfig(
                rank=4,
                model="nemotron3",
                method=ExtractionMethod.LLM_ONLY,
                entity_timeout_s=300,
                relation_timeout_s=300,
            )

    def test_invalid_entity_timeout(self) -> None:
        """Test CascadeRankConfig validation fails with negative entity timeout."""
        with pytest.raises(ValueError, match="Entity timeout must be positive"):
            CascadeRankConfig(
                rank=1,
                model="nemotron3",
                method=ExtractionMethod.LLM_ONLY,
                entity_timeout_s=-1,
                relation_timeout_s=300,
            )

    def test_invalid_relation_timeout(self) -> None:
        """Test CascadeRankConfig validation fails with negative relation timeout."""
        with pytest.raises(ValueError, match="Relation timeout must be positive"):
            CascadeRankConfig(
                rank=1,
                model="nemotron3",
                method=ExtractionMethod.LLM_ONLY,
                entity_timeout_s=300,
                relation_timeout_s=0,
            )

    def test_invalid_max_retries(self) -> None:
        """Test CascadeRankConfig validation fails with negative max_retries."""
        with pytest.raises(ValueError, match="Max retries must be non-negative"):
            CascadeRankConfig(
                rank=1,
                model="nemotron3",
                method=ExtractionMethod.LLM_ONLY,
                entity_timeout_s=300,
                relation_timeout_s=300,
                max_retries=-1,
            )


class TestDefaultCascade:
    """Test suite for DEFAULT_CASCADE configuration."""

    def test_default_cascade_has_3_ranks(self) -> None:
        """Test DEFAULT_CASCADE contains 3 ranks."""
        assert len(DEFAULT_CASCADE) == 3

    def test_rank_1_nemotron3_llm_only(self) -> None:
        """Test Rank 1 is Nemotron3 LLM-Only."""
        rank1 = DEFAULT_CASCADE[0]

        assert rank1.rank == 1
        assert rank1.model == "nemotron3"
        assert rank1.method == ExtractionMethod.LLM_ONLY
        assert rank1.entity_timeout_s == 300
        assert rank1.relation_timeout_s == 300
        assert rank1.max_retries == 3

    def test_rank_2_gpt_oss_llm_only(self) -> None:
        """Test Rank 2 is GPT-OSS:20b LLM-Only."""
        rank2 = DEFAULT_CASCADE[1]

        assert rank2.rank == 2
        assert rank2.model == "gpt-oss:20b"
        assert rank2.method == ExtractionMethod.LLM_ONLY
        assert rank2.entity_timeout_s == 300
        assert rank2.relation_timeout_s == 300
        assert rank2.max_retries == 3

    def test_rank_3_hybrid_spacy_llm(self) -> None:
        """Test Rank 3 is Hybrid SpaCy NER + LLM."""
        rank3 = DEFAULT_CASCADE[2]

        assert rank3.rank == 3
        assert rank3.model == "gpt-oss:20b"
        assert rank3.method == ExtractionMethod.HYBRID_NER_LLM
        assert rank3.entity_timeout_s == 9999  # SpaCy NER is synchronous
        assert rank3.relation_timeout_s == 600  # Double timeout for relations
        assert rank3.max_retries == 3


class TestGetCascadeForDomain:
    """Test suite for get_cascade_for_domain function."""

    def test_get_cascade_no_domain(self) -> None:
        """Test get_cascade_for_domain returns default cascade with no domain."""
        cascade = get_cascade_for_domain(domain=None)

        assert len(cascade) == 3
        assert cascade == DEFAULT_CASCADE

    def test_get_cascade_with_domain(self) -> None:
        """Test get_cascade_for_domain returns default cascade (domain override not implemented)."""
        cascade = get_cascade_for_domain(domain="tech_docs")

        # Domain-specific cascade not yet implemented, should return default
        assert len(cascade) == 3
        assert cascade == DEFAULT_CASCADE


class TestLogCascadeFallback:
    """Test suite for log_cascade_fallback function."""

    def test_log_cascade_fallback_basic(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test log_cascade_fallback logs structured event."""
        # Capture structured logs
        import structlog

        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
        )

        log_cascade_fallback(
            from_rank=1,
            to_rank=2,
            reason="timeout",
            document_id="doc123",
        )

        # Verify log was created (caplog captures stdlib logs)
        # structlog logs to stdlib, so we can check caplog
        assert len(caplog.records) > 0

    def test_log_cascade_fallback_without_document_id(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test log_cascade_fallback works without document_id."""
        log_cascade_fallback(
            from_rank=2,
            to_rank=3,
            reason="parse_error",
            document_id=None,
        )

        # Should not raise error
        assert len(caplog.records) > 0
