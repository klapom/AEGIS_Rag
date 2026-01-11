"""Extraction Cascade Configuration for LLM Fallback Strategy.

Sprint 83 Feature 83.2: LLM Fallback & Retry Strategy

This module defines the 3-rank cascade for entity/relationship extraction:
- Rank 1: Nemotron3 (LLM-Only) - Fast, local
- Rank 2: GPT-OSS:20b (LLM-Only) - Larger model, more accurate
- Rank 3: Hybrid SpaCy NER + LLM - Maximum recall with NER + LLM relations

Configuration includes timeouts, retry settings, and extraction methods for each rank.
"""

from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class ExtractionMethod(str, Enum):
    """Extraction method for each cascade rank."""

    LLM_ONLY = "llm_only"  # Pure LLM extraction (entities + relations)
    HYBRID_NER_LLM = "hybrid_ner_llm"  # SpaCy NER entities + LLM relations


@dataclass
class CascadeRankConfig:
    """Configuration for a single cascade rank.

    Attributes:
        rank: Rank number (1-3, lower is preferred)
        model: LLM model name (e.g., "nemotron3", "gpt-oss:20b")
        method: Extraction method (LLM_ONLY or HYBRID_NER_LLM)
        entity_timeout_s: Timeout for entity extraction in seconds
        relation_timeout_s: Timeout for relation extraction in seconds
        max_retries: Maximum retry attempts on failure
        retry_backoff_multiplier: Exponential backoff multiplier (seconds)
    """

    rank: int
    model: str
    method: ExtractionMethod
    entity_timeout_s: int
    relation_timeout_s: int
    max_retries: int = 3
    retry_backoff_multiplier: int = 1

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.rank < 1 or self.rank > 3:
            raise ValueError(f"Rank must be 1-3, got {self.rank}")
        if self.entity_timeout_s <= 0:
            raise ValueError(f"Entity timeout must be positive, got {self.entity_timeout_s}")
        if self.relation_timeout_s <= 0:
            raise ValueError(f"Relation timeout must be positive, got {self.relation_timeout_s}")
        if self.max_retries < 0:
            raise ValueError(f"Max retries must be non-negative, got {self.max_retries}")


# Default 3-Rank Cascade Configuration
DEFAULT_CASCADE: list[CascadeRankConfig] = [
    # Rank 1: Nemotron3 (LLM-Only) - Fast, local, 300s timeout
    CascadeRankConfig(
        rank=1,
        model="nemotron3",
        method=ExtractionMethod.LLM_ONLY,
        entity_timeout_s=300,
        relation_timeout_s=300,
        max_retries=3,
        retry_backoff_multiplier=1,  # 1s, 2s, 4s backoff
    ),
    # Rank 2: GPT-OSS:20b (LLM-Only) - Larger model, 300s timeout
    CascadeRankConfig(
        rank=2,
        model="gpt-oss:20b",
        method=ExtractionMethod.LLM_ONLY,
        entity_timeout_s=300,
        relation_timeout_s=300,
        max_retries=3,
        retry_backoff_multiplier=1,
    ),
    # Rank 3: Hybrid SpaCy NER + LLM - Maximum recall, no entity timeout, 600s relation timeout
    CascadeRankConfig(
        rank=3,
        model="gpt-oss:20b",  # Used only for relation extraction
        method=ExtractionMethod.HYBRID_NER_LLM,
        entity_timeout_s=9999,  # SpaCy NER is synchronous, no timeout needed
        relation_timeout_s=600,  # Double timeout for relation extraction
        max_retries=3,
        retry_backoff_multiplier=1,
    ),
]


def get_cascade_for_domain(domain: str | None = None) -> list[CascadeRankConfig]:
    """Get extraction cascade configuration for a domain.

    Args:
        domain: Domain name (e.g., "tech_docs", "legal_contracts")
                If None or domain has no custom cascade, returns default cascade.

    Returns:
        List of CascadeRankConfig objects (sorted by rank)

    Example:
        >>> cascade = get_cascade_for_domain("tech_docs")
        >>> for rank_config in cascade:
        ...     logger.info("rank", rank=rank_config.rank, model=rank_config.model)
    """
    # TODO: Implement domain-specific cascade override in Sprint 83+
    # For now, always return default cascade
    # Future: Fetch from DomainRepository if domain has custom extraction_model_cascade

    if domain:
        logger.debug(
            "domain_cascade_not_implemented_using_default",
            domain=domain,
            reason="feature_pending_sprint83+",
        )

    return DEFAULT_CASCADE


def log_cascade_fallback(
    from_rank: int, to_rank: int, reason: str, document_id: str | None = None
) -> None:
    """Log structured event when falling back to next cascade rank.

    Args:
        from_rank: Failed rank number (1-3)
        to_rank: Next rank to try (2-3)
        reason: Failure reason (e.g., "timeout", "llm_error", "parse_error")
        document_id: Document ID (optional, for correlation)

    Example:
        >>> log_cascade_fallback(from_rank=1, to_rank=2, reason="timeout", document_id="doc123")
        # Logs: {"event": "cascade_fallback", "from_rank": 1, "to_rank": 2, ...}
    """
    logger.warning(
        "cascade_fallback",
        from_rank=from_rank,
        to_rank=to_rank,
        reason=reason,
        document_id=document_id,
        cascade_transition=f"rank{from_rank}_failed_trying_rank{to_rank}",
    )
