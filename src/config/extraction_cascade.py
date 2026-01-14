"""Extraction Cascade Configuration for LLM Fallback Strategy.

Sprint 83 Feature 83.2: LLM Fallback & Retry Strategy
Sprint 89 Feature 89.1: SpaCy-First Pipeline (TD-102 Iteration 1)

This module defines extraction strategies:

**Legacy Cascade (Sprint 83):**
- Rank 1: Nemotron3 (LLM-Only) - Fast, local
- Rank 2: GPT-OSS:20b (LLM-Only) - Larger model, more accurate
- Rank 3: Hybrid SpaCy NER + LLM - Maximum recall with NER + LLM relations

**SpaCy-First Pipeline (Sprint 89 - DEFAULT):**
- Stage 1: SpaCy NER - Deterministic entity baseline (~50ms)
- Stage 2: LLM Entity Enrichment - Additional entities (optional, ~5-15s)
- Stage 3: LLM Relation Extraction - All relations (~10-30s)

Configuration includes timeouts, retry settings, and extraction methods for each stage.
"""

import os
from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)

# Sprint 89: SpaCy-First Pipeline Feature Flag
# Default: enabled (1) - Use SpaCy-first pipeline for faster extraction
# Disable: AEGIS_USE_LEGACY_CASCADE=1 to revert to old LLM-first cascade
USE_SPACY_FIRST_PIPELINE = os.environ.get("AEGIS_USE_LEGACY_CASCADE", "0") != "1"

# Sprint 89: Entity Enrichment is MANDATORY in SpaCy-First Pipeline
# Stage 2 always runs to ensure CONCEPT, TECHNOLOGY entities are captured
# (SpaCy NER only finds PERSON, ORG, LOC - misses domain-specific entities)


class ExtractionMethod(str, Enum):
    """Extraction method for each cascade rank or pipeline stage."""

    LLM_ONLY = "llm_only"  # Pure LLM extraction (entities + relations)
    HYBRID_NER_LLM = "hybrid_ner_llm"  # SpaCy NER entities + LLM relations
    # Sprint 89: New methods for SpaCy-First Pipeline
    SPACY_NER_ONLY = "spacy_ner_only"  # Stage 1: SpaCy NER entities only
    LLM_ENTITY_ENRICHMENT = "llm_entity_enrichment"  # Stage 2: LLM adds missing entities
    LLM_RELATION_ONLY = "llm_relation_only"  # Stage 3: LLM extracts relations from known entities


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
    # Rank 1: Nemotron-3-Nano (LLM-Only) - Fast, local, 300s timeout
    # Sprint 85 Fix: Correct model name from "nemotron3" to "nemotron-3-nano:latest"
    CascadeRankConfig(
        rank=1,
        model="nemotron-3-nano:latest",
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


@dataclass
class PipelineStageConfig:
    """Configuration for a single pipeline stage (Sprint 89).

    Attributes:
        stage: Stage number (1-3)
        name: Human-readable stage name
        method: Extraction method for this stage
        model: LLM model name (None for SpaCy stages)
        timeout_s: Timeout in seconds
        max_retries: Maximum retry attempts on failure
        fallback_to_llm: If True, fall back to LLM-only on SpaCy failure
    """

    stage: int
    name: str
    method: ExtractionMethod
    model: str | None
    timeout_s: int
    max_retries: int = 2
    fallback_to_llm: bool = False


# Sprint 89: SpaCy-First Pipeline Configuration (TD-102 Iteration 1)
# This is the NEW DEFAULT - 10-20x faster than legacy cascade
SPACY_FIRST_PIPELINE: list[PipelineStageConfig] = [
    # Stage 1: SpaCy NER - Deterministic Entity Baseline (~50ms)
    # Extracts: PERSON, ORG, LOC, DATE, etc.
    PipelineStageConfig(
        stage=1,
        name="SpaCy NER Entities",
        method=ExtractionMethod.SPACY_NER_ONLY,
        model=None,  # SpaCy uses language-specific models (de_core_news_lg, en_core_web_lg)
        timeout_s=60,  # SpaCy is fast, but allow time for model loading
        max_retries=1,
        fallback_to_llm=True,  # If SpaCy fails, fall back to LLM entity extraction
    ),
    # Stage 2: LLM Entity Enrichment (~5-15s) - MANDATORY
    # Adds: CONCEPT, TECHNOLOGY, PRODUCT entities that SpaCy misses
    # Prompt: "Given these SpaCy entities, find ONLY additional entities"
    PipelineStageConfig(
        stage=2,
        name="LLM Entity Enrichment",
        method=ExtractionMethod.LLM_ENTITY_ENRICHMENT,
        model="nemotron-3-nano:latest",
        timeout_s=120,  # Shorter timeout since SpaCy already provides baseline
        max_retries=2,
        fallback_to_llm=False,  # Already LLM, no fallback
    ),
    # Stage 3: LLM Relation Extraction (~10-30s)
    # Uses ALL entities from Stage 1+2 as input
    # Prompt: "Given these entities, extract ALL relations between them"
    PipelineStageConfig(
        stage=3,
        name="LLM Relation Extraction",
        method=ExtractionMethod.LLM_RELATION_ONLY,
        model="nemotron-3-nano:latest",
        timeout_s=180,  # Relations take longer
        max_retries=3,
        fallback_to_llm=False,
    ),
]


def get_pipeline_config() -> list[PipelineStageConfig]:
    """Get SpaCy-First Pipeline configuration.

    Returns:
        List of PipelineStageConfig objects for the 3-stage pipeline.

    Example:
        >>> pipeline = get_pipeline_config()
        >>> for stage in pipeline:
        ...     logger.info("stage", stage=stage.stage, name=stage.name)
    """
    return SPACY_FIRST_PIPELINE


def get_cascade_for_domain(domain: str | None = None) -> list[CascadeRankConfig]:
    """Get extraction cascade configuration for a domain (LEGACY).

    Note: This is the LEGACY cascade. Use get_pipeline_config() for Sprint 89+.

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


def should_use_spacy_first_pipeline() -> bool:
    """Check if SpaCy-First Pipeline should be used.

    Returns:
        True if SpaCy-First Pipeline is enabled (default),
        False if legacy cascade is forced via AEGIS_USE_LEGACY_CASCADE=1.
    """
    return USE_SPACY_FIRST_PIPELINE


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
