"""Extraction Metrics for Knowledge Graph Quality Tracking.

Sprint 85 Feature 85.6: Extraction Metrics (Log + LangGraph State)
Sprint 86 Feature 86.9: Cascade Monitoring (Prometheus-style metrics)

This module provides structured metrics tracking for entity and relationship extraction:
- Entity metrics (SpaCy vs LLM counts, types)
- Relation metrics (initial vs gleaning)
- Quality metrics (ratio, coverage, duplication)
- Performance metrics (latency per phase)
- Language detection tracking
- Cascade success rates and fallback tracking (Sprint 86.9)

Metrics are output to:
1. Structured logs (structlog)
2. LangGraph state (for pipeline aggregation)
3. Prometheus-compatible format (Sprint 86.9)
"""

from dataclasses import asdict, dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ExtractionMetrics:
    """Extraction quality and performance metrics.

    Attributes:
        entities_spacy: Entities extracted via SpaCy NER
        entities_llm: Entities extracted via LLM
        entities_total: Total unique entities after deduplication
        relations_initial: Relations from initial extraction
        relations_gleaning: Additional relations from gleaning passes
        relations_total: Total relations extracted
        relation_ratio: Relations/Entities ratio (target >= 1.0)
        typed_coverage: Percentage of relations with specific types (not RELATES_TO)
        duplication_rate: Percentage of duplicate entities removed
        spacy_latency_ms: SpaCy extraction latency
        llm_latency_ms: LLM extraction latency
        gleaning_latency_ms: Gleaning passes latency
        canonicalization_latency_ms: Entity canonicalization latency
        total_latency_ms: Total extraction pipeline latency
        languages_detected: Languages used for SpaCy models
        extraction_method: Method used (llm_only, hybrid_ner_llm, etc.)
        cascade_rank_used: Which cascade rank succeeded (1, 2, or 3)
        gleaning_rounds: Number of gleaning rounds executed
    """

    # Entity metrics
    entities_spacy: int = 0
    entities_llm: int = 0
    entities_total: int = 0

    # Relation metrics
    relations_initial: int = 0
    relations_gleaning: int = 0
    relations_total: int = 0

    # Quality metrics
    relation_ratio: float = 0.0  # relations / entities
    typed_coverage: float = 0.0  # typed / total relations (not RELATES_TO)
    duplication_rate: float = 0.0  # duplicates / total

    # Performance metrics (ms)
    spacy_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    gleaning_latency_ms: float = 0.0
    canonicalization_latency_ms: float = 0.0
    total_latency_ms: float = 0.0

    # Extraction details
    languages_detected: list[str] = field(default_factory=list)
    extraction_method: str = "unknown"
    cascade_rank_used: int = 0
    gleaning_rounds: int = 0

    # Entity type breakdown
    entity_types: dict[str, int] = field(default_factory=dict)

    # Relation type breakdown
    relation_types: dict[str, int] = field(default_factory=dict)

    def calculate_derived_metrics(self) -> None:
        """Calculate derived metrics after extraction completes."""
        # Relation ratio
        if self.entities_total > 0:
            self.relation_ratio = self.relations_total / self.entities_total
        else:
            self.relation_ratio = 0.0

        # Typed coverage (non-RELATES_TO relations)
        if self.relations_total > 0 and self.relation_types:
            relates_to_count = self.relation_types.get("RELATES_TO", 0)
            typed_count = self.relations_total - relates_to_count
            self.typed_coverage = typed_count / self.relations_total
        else:
            self.typed_coverage = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for logging/state."""
        return asdict(self)

    def to_log_dict(self) -> dict[str, Any]:
        """Convert to dict optimized for structured logging (flat, no nested dicts)."""
        result = {
            "entities_spacy": self.entities_spacy,
            "entities_llm": self.entities_llm,
            "entities_total": self.entities_total,
            "relations_initial": self.relations_initial,
            "relations_gleaning": self.relations_gleaning,
            "relations_total": self.relations_total,
            "relation_ratio": round(self.relation_ratio, 3),
            "typed_coverage": round(self.typed_coverage, 3),
            "duplication_rate": round(self.duplication_rate, 3),
            "spacy_latency_ms": round(self.spacy_latency_ms, 2),
            "llm_latency_ms": round(self.llm_latency_ms, 2),
            "gleaning_latency_ms": round(self.gleaning_latency_ms, 2),
            "canonicalization_latency_ms": round(self.canonicalization_latency_ms, 2),
            "total_latency_ms": round(self.total_latency_ms, 2),
            "languages_detected": self.languages_detected,
            "extraction_method": self.extraction_method,
            "cascade_rank_used": self.cascade_rank_used,
            "gleaning_rounds": self.gleaning_rounds,
        }

        # Add top entity types
        if self.entity_types:
            top_types = sorted(self.entity_types.items(), key=lambda x: x[1], reverse=True)[:5]
            result["top_entity_types"] = [f"{t}:{c}" for t, c in top_types]

        # Add top relation types
        if self.relation_types:
            top_types = sorted(self.relation_types.items(), key=lambda x: x[1], reverse=True)[:5]
            result["top_relation_types"] = [f"{t}:{c}" for t, c in top_types]

        return result


def log_extraction_metrics(
    metrics: ExtractionMetrics,
    document_id: str,
    chunk_id: str | None = None,
) -> None:
    """Log extraction metrics in structured format.

    Args:
        metrics: ExtractionMetrics dataclass
        document_id: Document ID for correlation
        chunk_id: Optional chunk ID for chunk-level metrics
    """
    # Calculate derived metrics before logging
    metrics.calculate_derived_metrics()

    log_data = metrics.to_log_dict()
    log_data["document_id"] = document_id
    if chunk_id:
        log_data["chunk_id"] = chunk_id

    # Use appropriate log level based on relation_ratio
    if metrics.relation_ratio >= 1.0:
        logger.info("extraction_metrics_success", **log_data)
    elif metrics.relation_ratio >= 0.5:
        logger.info("extraction_metrics_moderate", **log_data)
    else:
        logger.warning("extraction_metrics_low_ratio", **log_data)


def merge_extraction_metrics(
    existing: ExtractionMetrics | None,
    new: ExtractionMetrics,
) -> ExtractionMetrics:
    """Merge extraction metrics from multiple chunks.

    Used by LangGraph to aggregate metrics across all chunks in a document.

    Args:
        existing: Existing aggregated metrics (or None for first chunk)
        new: New metrics to merge

    Returns:
        Merged ExtractionMetrics with aggregated counts and times
    """
    if existing is None:
        return new

    # Merge entity type counts
    merged_entity_types = dict(existing.entity_types)
    for entity_type, count in new.entity_types.items():
        merged_entity_types[entity_type] = merged_entity_types.get(entity_type, 0) + count

    # Merge relation type counts
    merged_relation_types = dict(existing.relation_types)
    for relation_type, count in new.relation_types.items():
        merged_relation_types[relation_type] = merged_relation_types.get(relation_type, 0) + count

    # Merge languages (unique)
    merged_languages = list(set(existing.languages_detected + new.languages_detected))

    return ExtractionMetrics(
        # Sum counts
        entities_spacy=existing.entities_spacy + new.entities_spacy,
        entities_llm=existing.entities_llm + new.entities_llm,
        entities_total=existing.entities_total + new.entities_total,
        relations_initial=existing.relations_initial + new.relations_initial,
        relations_gleaning=existing.relations_gleaning + new.relations_gleaning,
        relations_total=existing.relations_total + new.relations_total,
        # Recalculate ratio based on totals
        relation_ratio=(existing.relations_total + new.relations_total)
        / max(1, existing.entities_total + new.entities_total),
        # Average coverage and duplication (weighted would be better but this is simpler)
        typed_coverage=(existing.typed_coverage + new.typed_coverage) / 2,
        duplication_rate=(existing.duplication_rate + new.duplication_rate) / 2,
        # Sum latencies
        spacy_latency_ms=existing.spacy_latency_ms + new.spacy_latency_ms,
        llm_latency_ms=existing.llm_latency_ms + new.llm_latency_ms,
        gleaning_latency_ms=existing.gleaning_latency_ms + new.gleaning_latency_ms,
        canonicalization_latency_ms=existing.canonicalization_latency_ms
        + new.canonicalization_latency_ms,
        total_latency_ms=existing.total_latency_ms + new.total_latency_ms,
        # Merge lists/dicts
        languages_detected=merged_languages,
        extraction_method=new.extraction_method,  # Use latest
        cascade_rank_used=new.cascade_rank_used,  # Use latest
        gleaning_rounds=max(existing.gleaning_rounds, new.gleaning_rounds),
        entity_types=merged_entity_types,
        relation_types=merged_relation_types,
    )


def create_metrics_from_extraction(
    entities: list,
    relations: list,
    spacy_count: int = 0,
    llm_count: int = 0,
    duplicates_removed: int = 0,
    spacy_latency_ms: float = 0.0,
    llm_latency_ms: float = 0.0,
    gleaning_latency_ms: float = 0.0,
    languages: list[str] | None = None,
    extraction_method: str = "unknown",
    cascade_rank: int = 0,
    gleaning_rounds: int = 0,
) -> ExtractionMetrics:
    """Create ExtractionMetrics from extraction results.

    Helper function to create metrics after extraction completes.

    Args:
        entities: List of extracted entities (GraphEntity or dict)
        relations: List of extracted relationships (GraphRelationship or dict)
        spacy_count: Entities from SpaCy
        llm_count: Entities from LLM
        duplicates_removed: Duplicates removed during deduplication
        spacy_latency_ms: SpaCy extraction time
        llm_latency_ms: LLM extraction time
        gleaning_latency_ms: Gleaning time
        languages: Languages detected
        extraction_method: Method used
        cascade_rank: Cascade rank that succeeded
        gleaning_rounds: Number of gleaning rounds

    Returns:
        ExtractionMetrics with calculated values
    """
    # Count entity types
    entity_types: dict[str, int] = {}
    for entity in entities:
        entity_type = entity.type if hasattr(entity, "type") else entity.get("type", "UNKNOWN")
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

    # Count relation types
    relation_types: dict[str, int] = {}
    for relation in relations:
        relation_type = (
            relation.type if hasattr(relation, "type") else relation.get("type", "RELATES_TO")
        )
        relation_types[relation_type] = relation_types.get(relation_type, 0) + 1

    # Calculate duplication rate
    total_before_dedup = len(entities) + duplicates_removed
    duplication_rate = duplicates_removed / total_before_dedup if total_before_dedup > 0 else 0.0

    metrics = ExtractionMetrics(
        entities_spacy=spacy_count,
        entities_llm=llm_count,
        entities_total=len(entities),
        relations_initial=len(relations),  # Will be split if gleaning used
        relations_gleaning=0,
        relations_total=len(relations),
        duplication_rate=duplication_rate,
        spacy_latency_ms=spacy_latency_ms,
        llm_latency_ms=llm_latency_ms,
        gleaning_latency_ms=gleaning_latency_ms,
        total_latency_ms=spacy_latency_ms + llm_latency_ms + gleaning_latency_ms,
        languages_detected=languages or [],
        extraction_method=extraction_method,
        cascade_rank_used=cascade_rank,
        gleaning_rounds=gleaning_rounds,
        entity_types=entity_types,
        relation_types=relation_types,
    )

    # Calculate derived metrics
    metrics.calculate_derived_metrics()

    return metrics


# ============================================================================
# Sprint 86.9: Cascade Monitoring
# ============================================================================


@dataclass
class CascadeMetrics:
    """Cascade extraction monitoring metrics.

    Sprint 86.9: Tracks success rates and fallback events per cascade rank.

    Attributes:
        rank1_attempts: Total attempts at Rank 1 (Nemotron3)
        rank1_successes: Successful extractions at Rank 1
        rank2_attempts: Total attempts at Rank 2 (GPT-OSS:20b)
        rank2_successes: Successful extractions at Rank 2
        rank3_attempts: Total attempts at Rank 3 (Hybrid SpaCy)
        rank3_successes: Successful extractions at Rank 3
        fallback_1_to_2: Fallbacks from Rank 1 to Rank 2
        fallback_2_to_3: Fallbacks from Rank 2 to Rank 3
        total_extractions: Total extraction attempts
        avg_latency_rank1_ms: Average latency for Rank 1
        avg_latency_rank2_ms: Average latency for Rank 2
        avg_latency_rank3_ms: Average latency for Rank 3
    """

    # Attempt and success counts per rank
    rank1_attempts: int = 0
    rank1_successes: int = 0
    rank2_attempts: int = 0
    rank2_successes: int = 0
    rank3_attempts: int = 0
    rank3_successes: int = 0

    # Fallback events
    fallback_1_to_2: int = 0
    fallback_2_to_3: int = 0
    total_failures: int = 0

    # Total extractions
    total_extractions: int = 0

    # Latency tracking (running average)
    avg_latency_rank1_ms: float = 0.0
    avg_latency_rank2_ms: float = 0.0
    avg_latency_rank3_ms: float = 0.0

    @property
    def rank1_success_rate(self) -> float:
        """Success rate for Rank 1."""
        return self.rank1_successes / self.rank1_attempts if self.rank1_attempts > 0 else 0.0

    @property
    def rank2_success_rate(self) -> float:
        """Success rate for Rank 2."""
        return self.rank2_successes / self.rank2_attempts if self.rank2_attempts > 0 else 0.0

    @property
    def rank3_success_rate(self) -> float:
        """Success rate for Rank 3."""
        return self.rank3_successes / self.rank3_attempts if self.rank3_attempts > 0 else 0.0

    @property
    def overall_success_rate(self) -> float:
        """Overall success rate (any rank)."""
        total_successes = self.rank1_successes + self.rank2_successes + self.rank3_successes
        return total_successes / self.total_extractions if self.total_extractions > 0 else 0.0

    @property
    def fallback_rate(self) -> float:
        """Percentage of extractions that required fallback."""
        total_fallbacks = self.fallback_1_to_2 + self.fallback_2_to_3
        return total_fallbacks / self.total_extractions if self.total_extractions > 0 else 0.0

    def to_prometheus_format(self) -> str:
        """Export metrics in Prometheus exposition format.

        Returns:
            String in Prometheus text format
        """
        lines = [
            "# HELP aegis_cascade_attempts_total Total extraction attempts per rank",
            "# TYPE aegis_cascade_attempts_total counter",
            f'aegis_cascade_attempts_total{{rank="1"}} {self.rank1_attempts}',
            f'aegis_cascade_attempts_total{{rank="2"}} {self.rank2_attempts}',
            f'aegis_cascade_attempts_total{{rank="3"}} {self.rank3_attempts}',
            "",
            "# HELP aegis_cascade_successes_total Successful extractions per rank",
            "# TYPE aegis_cascade_successes_total counter",
            f'aegis_cascade_successes_total{{rank="1"}} {self.rank1_successes}',
            f'aegis_cascade_successes_total{{rank="2"}} {self.rank2_successes}',
            f'aegis_cascade_successes_total{{rank="3"}} {self.rank3_successes}',
            "",
            "# HELP aegis_cascade_fallbacks_total Fallback events between ranks",
            "# TYPE aegis_cascade_fallbacks_total counter",
            f'aegis_cascade_fallbacks_total{{from="1",to="2"}} {self.fallback_1_to_2}',
            f'aegis_cascade_fallbacks_total{{from="2",to="3"}} {self.fallback_2_to_3}',
            "",
            "# HELP aegis_cascade_latency_ms Average extraction latency per rank",
            "# TYPE aegis_cascade_latency_ms gauge",
            f'aegis_cascade_latency_ms{{rank="1"}} {self.avg_latency_rank1_ms:.2f}',
            f'aegis_cascade_latency_ms{{rank="2"}} {self.avg_latency_rank2_ms:.2f}',
            f'aegis_cascade_latency_ms{{rank="3"}} {self.avg_latency_rank3_ms:.2f}',
            "",
            "# HELP aegis_cascade_success_rate Success rate per rank",
            "# TYPE aegis_cascade_success_rate gauge",
            f'aegis_cascade_success_rate{{rank="1"}} {self.rank1_success_rate:.4f}',
            f'aegis_cascade_success_rate{{rank="2"}} {self.rank2_success_rate:.4f}',
            f'aegis_cascade_success_rate{{rank="3"}} {self.rank3_success_rate:.4f}',
            f'aegis_cascade_success_rate{{rank="overall"}} {self.overall_success_rate:.4f}',
        ]
        return "\n".join(lines)


# Module-level cascade metrics singleton
_cascade_metrics: CascadeMetrics | None = None


def get_cascade_metrics() -> CascadeMetrics:
    """Get the global cascade metrics instance.

    Returns:
        CascadeMetrics singleton
    """
    global _cascade_metrics
    if _cascade_metrics is None:
        _cascade_metrics = CascadeMetrics()
    return _cascade_metrics


def reset_cascade_metrics() -> None:
    """Reset cascade metrics (for testing or new measurement period)."""
    global _cascade_metrics
    _cascade_metrics = CascadeMetrics()


def record_cascade_attempt(rank: int, success: bool, latency_ms: float) -> None:
    """Record a cascade extraction attempt.

    Args:
        rank: Cascade rank (1, 2, or 3)
        success: Whether extraction succeeded
        latency_ms: Extraction latency in milliseconds
    """
    metrics = get_cascade_metrics()
    metrics.total_extractions += 1

    # Running average latency update helper
    def update_avg(current_avg: float, new_value: float, count: int) -> float:
        if count == 0:
            return new_value
        return current_avg + (new_value - current_avg) / count

    if rank == 1:
        metrics.rank1_attempts += 1
        if success:
            metrics.rank1_successes += 1
        metrics.avg_latency_rank1_ms = update_avg(
            metrics.avg_latency_rank1_ms, latency_ms, metrics.rank1_attempts
        )
    elif rank == 2:
        metrics.rank2_attempts += 1
        if success:
            metrics.rank2_successes += 1
        metrics.avg_latency_rank2_ms = update_avg(
            metrics.avg_latency_rank2_ms, latency_ms, metrics.rank2_attempts
        )
    elif rank == 3:
        metrics.rank3_attempts += 1
        if success:
            metrics.rank3_successes += 1
        metrics.avg_latency_rank3_ms = update_avg(
            metrics.avg_latency_rank3_ms, latency_ms, metrics.rank3_attempts
        )

    if not success:
        metrics.total_failures += 1

    # Log the attempt
    logger.debug(
        "cascade_attempt_recorded",
        rank=rank,
        success=success,
        latency_ms=round(latency_ms, 2),
        rank_success_rate=getattr(metrics, f"rank{rank}_success_rate", 0),
    )


def record_cascade_fallback(from_rank: int, to_rank: int, reason: str) -> None:
    """Record a cascade fallback event.

    Args:
        from_rank: Source rank (1 or 2)
        to_rank: Target rank (2 or 3)
        reason: Reason for fallback (e.g., "timeout", "parse_error")
    """
    metrics = get_cascade_metrics()

    if from_rank == 1 and to_rank == 2:
        metrics.fallback_1_to_2 += 1
    elif from_rank == 2 and to_rank == 3:
        metrics.fallback_2_to_3 += 1

    logger.info(
        "cascade_fallback_recorded",
        from_rank=from_rank,
        to_rank=to_rank,
        reason=reason,
        total_fallbacks_1_to_2=metrics.fallback_1_to_2,
        total_fallbacks_2_to_3=metrics.fallback_2_to_3,
    )


def log_cascade_summary() -> None:
    """Log a summary of cascade metrics."""
    metrics = get_cascade_metrics()

    logger.info(
        "cascade_metrics_summary",
        total_extractions=metrics.total_extractions,
        rank1_success_rate=f"{metrics.rank1_success_rate:.1%}",
        rank2_success_rate=f"{metrics.rank2_success_rate:.1%}",
        rank3_success_rate=f"{metrics.rank3_success_rate:.1%}",
        overall_success_rate=f"{metrics.overall_success_rate:.1%}",
        fallback_rate=f"{metrics.fallback_rate:.1%}",
        avg_latency_rank1=f"{metrics.avg_latency_rank1_ms:.0f}ms",
        avg_latency_rank2=f"{metrics.avg_latency_rank2_ms:.0f}ms",
        avg_latency_rank3=f"{metrics.avg_latency_rank3_ms:.0f}ms",
    )
