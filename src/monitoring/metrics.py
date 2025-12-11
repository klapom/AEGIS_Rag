"""Prometheus Metrics for AEGIS RAG - Sprint 14 Feature 14.6.

Comprehensive metrics for extraction pipeline monitoring:
- Extraction duration by phase and pipeline type
- Entity/relation counts
- Error tracking
- GPU memory usage (if available)

Author: Claude Code
Date: 2025-10-27
"""

from typing import Any

import structlog
from prometheus_client import Counter, Gauge, Histogram, Info

logger = structlog.get_logger(__name__)

# ============================================================================
# Extraction Pipeline Metrics
# ============================================================================

extraction_duration = Histogram(
    "aegis_extraction_duration_seconds",
    "Time spent in extraction pipeline",
    ["phase", "pipeline_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0],
)

extraction_entities_total = Counter(
    "aegis_extraction_entities_total", "Total entities extracted", ["entity_type", "pipeline_type"]
)

extraction_relations_total = Counter(
    "aegis_extraction_relations_total", "Total relations extracted", ["pipeline_type"]
)

extraction_documents_total = Counter(
    "aegis_extraction_documents_total",
    "Total documents processed",
    ["pipeline_type", "status"],  # status: success, failed, skipped
)

extraction_errors_total = Counter(
    "aegis_extraction_errors_total", "Total extraction errors", ["phase", "error_type"]
)

extraction_retries_total = Counter(
    "aegis_extraction_retries_total",
    "Total retry attempts",
    ["phase", "success"],  # success: true, false
)

deduplication_reduction_ratio = Histogram(
    "aegis_deduplication_reduction_ratio",
    "Deduplication reduction percentage",
    buckets=[0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50],
)

# ============================================================================
# Sprint 43: Enhanced Chunking & Deduplication Metrics (Feature 43.x)
# ============================================================================

# Chunking input/output metrics
chunking_input_chars_total = Counter(
    "aegis_chunking_input_chars_total",
    "Total characters input to chunker",
    ["document_id"],
)

chunking_output_chunks_total = Counter(
    "aegis_chunking_output_chunks_total",
    "Total chunks output from chunker",
    ["document_id"],
)

chunking_chunk_size_chars = Histogram(
    "aegis_chunking_chunk_size_chars",
    "Individual chunk size in characters",
    buckets=[100, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 5000],
)

chunking_chunk_size_tokens = Histogram(
    "aegis_chunking_chunk_size_tokens",
    "Individual chunk size in tokens",
    buckets=[50, 100, 200, 400, 600, 800, 1000, 1200, 1500, 1800],
)

chunking_overlap_tokens = Histogram(
    "aegis_chunking_overlap_tokens",
    "Overlap between consecutive chunks in tokens",
    buckets=[0, 25, 50, 75, 100, 150, 200, 300],
)

# Deduplication detailed metrics
deduplication_entities_before = Gauge(
    "aegis_deduplication_entities_before",
    "Entity count before deduplication",
    ["document_id"],
)

deduplication_entities_after = Gauge(
    "aegis_deduplication_entities_after",
    "Entity count after deduplication",
    ["document_id"],
)

deduplication_matches_by_criterion = Counter(
    "aegis_deduplication_matches_by_criterion",
    "Deduplication matches by criterion type",
    ["criterion"],  # exact, edit_distance, substring, embedding
)

# Extraction detailed metrics
extraction_entities_by_type = Counter(
    "aegis_extraction_entities_by_type",
    "Entities extracted by type",
    ["entity_type", "model"],
)

extraction_relations_by_type = Counter(
    "aegis_extraction_relations_by_type",
    "Relations extracted by type",
    ["relation_type", "model"],
)

# ============================================================================
# GPU Memory Metrics (optional, only if GPU available)
# ============================================================================

gpu_memory_usage_bytes = Gauge(
    "aegis_gpu_memory_usage_bytes", "Current GPU memory usage", ["gpu_id"]
)

gpu_memory_allocated_bytes = Gauge(
    "aegis_gpu_memory_allocated_bytes", "GPU memory allocated by PyTorch/TensorFlow", ["gpu_id"]
)

gpu_utilization_percent = Gauge(
    "aegis_gpu_utilization_percent", "GPU utilization percentage", ["gpu_id"]
)

# ============================================================================
# Query Metrics
# ============================================================================

query_duration = Histogram(
    "aegis_query_duration_seconds",
    "Query processing time",
    ["query_type", "mode"],  # query_type: vector, graph, hybrid; mode: local, global
    buckets=[0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0],
)

query_results_count = Histogram(
    "aegis_query_results_count",
    "Number of results returned per query",
    ["query_type"],
    buckets=[1, 5, 10, 20, 50, 100],
)

# ============================================================================
# System Metrics
# ============================================================================

system_info = Info("aegis_system_info", "System information")

active_connections = Gauge(
    "aegis_active_connections",
    "Number of active connections",
    ["connection_type"],  # connection_type: neo4j, qdrant, redis, ollama
)

# ============================================================================
# Helper Functions
# ============================================================================


def record_extraction_duration(phase: str, pipeline_type: str, duration: float) -> None:
    """Record extraction phase duration."""
    extraction_duration.labels(phase=phase, pipeline_type=pipeline_type).observe(duration)


def record_extraction_entities(entity_type: str, pipeline_type: str, count: int) -> None:
    """Record extracted entities."""
    extraction_entities_total.labels(entity_type=entity_type, pipeline_type=pipeline_type).inc(
        count
    )


def record_extraction_relations(pipeline_type: str, count: int) -> None:
    """Record extracted relations."""
    extraction_relations_total.labels(pipeline_type=pipeline_type).inc(count)


def record_extraction_document(pipeline_type: str, status: str) -> None:
    """Record document processing status.

    Args:
        pipeline_type: three_phase, lightrag_default
        status: success, failed, skipped
    """
    extraction_documents_total.labels(pipeline_type=pipeline_type, status=status).inc()


def record_extraction_error(phase: str, error_type: str) -> None:
    """Record extraction error.

    Args:
        phase: phase1_spacy, phase2_dedup, phase3_gemma
        error_type: connection_error, timeout, validation_error, etc.
    """
    extraction_errors_total.labels(phase=phase, error_type=error_type).inc()


def record_extraction_retry(phase: str, success: bool) -> None:
    """Record retry attempt.

    Args:
        phase: phase3_gemma (primary phase with retries)
        success: True if retry succeeded, False if failed
    """
    extraction_retries_total.labels(phase=phase, success=str(success).lower()).inc()


def record_deduplication_reduction(reduction_ratio: float) -> None:
    """Record deduplication reduction ratio.

    Args:
        reduction_ratio: 0.0-1.0 (0.15 = 15% reduction)
    """
    deduplication_reduction_ratio.observe(reduction_ratio)


# ============================================================================
# Sprint 43: Enhanced Chunking & Deduplication Recording Functions
# ============================================================================


def record_chunking_input(document_id: str, chars: int) -> None:
    """Record characters input to chunker."""
    chunking_input_chars_total.labels(document_id=document_id).inc(chars)


def record_chunking_output(document_id: str, chunk_count: int) -> None:
    """Record number of chunks created."""
    chunking_output_chunks_total.labels(document_id=document_id).inc(chunk_count)


def record_chunk_size(chars: int, tokens: int) -> None:
    """Record individual chunk size in chars and tokens."""
    chunking_chunk_size_chars.observe(chars)
    chunking_chunk_size_tokens.observe(tokens)


def record_chunk_overlap(overlap_tokens: int) -> None:
    """Record overlap between consecutive chunks."""
    chunking_overlap_tokens.observe(overlap_tokens)


def record_deduplication_detail(
    document_id: str,
    entities_before: int,
    entities_after: int,
    criterion_matches: dict[str, int] | None = None,
) -> None:
    """Record detailed deduplication metrics.

    Args:
        document_id: Document identifier
        entities_before: Entity count before dedup
        entities_after: Entity count after dedup
        criterion_matches: Dict with match counts per criterion
            e.g. {"exact": 5, "edit_distance": 2, "substring": 1, "embedding": 3}
    """
    deduplication_entities_before.labels(document_id=document_id).set(entities_before)
    deduplication_entities_after.labels(document_id=document_id).set(entities_after)

    if criterion_matches:
        for criterion, count in criterion_matches.items():
            deduplication_matches_by_criterion.labels(criterion=criterion).inc(count)

    # Also record ratio
    if entities_before > 0:
        reduction = (entities_before - entities_after) / entities_before
        deduplication_reduction_ratio.observe(reduction)


def record_extraction_by_type(
    entity_types: dict[str, int],
    relation_types: dict[str, int],
    model: str,
) -> None:
    """Record entities and relations by type.

    Args:
        entity_types: Dict of entity_type -> count
        relation_types: Dict of relation_type -> count
        model: LLM model used for extraction
    """
    for entity_type, count in entity_types.items():
        extraction_entities_by_type.labels(entity_type=entity_type, model=model).inc(count)

    for relation_type, count in relation_types.items():
        extraction_relations_by_type.labels(relation_type=relation_type, model=model).inc(count)


def update_gpu_memory(
    gpu_id: int, used_bytes: int, allocated_bytes: int, utilization: float
) -> None:
    """Update GPU memory metrics.

    Args:
        gpu_id: GPU device ID
        used_bytes: Total memory used
        allocated_bytes: Memory allocated by framework
        utilization: GPU utilization (0.0-100.0)
    """
    gpu_memory_usage_bytes.labels(gpu_id=str(gpu_id)).set(used_bytes)
    gpu_memory_allocated_bytes.labels(gpu_id=str(gpu_id)).set(allocated_bytes)
    gpu_utilization_percent.labels(gpu_id=str(gpu_id)).set(utilization)


def record_query_duration(query_type: str, mode: str, duration: float) -> None:
    """Record query duration.

    Args:
        query_type: vector, graph, hybrid
        mode: local, global
        duration: Query duration in seconds
    """
    query_duration.labels(query_type=query_type, mode=mode).observe(duration)


def update_active_connections(connection_type: str, count: int) -> None:
    """Update active connection count.

    Args:
        connection_type: neo4j, qdrant, redis, ollama
        count: Number of active connections
    """
    active_connections.labels(connection_type=connection_type).set(count)


def initialize_system_info(config: Any) -> None:
    """Initialize system information metric.

    Args:
        config: Application configuration
    """
    system_info.info(
        {
            "version": getattr(config, "app_version", "0.1.0"),
            "environment": getattr(config, "environment", "development"),
            "extraction_pipeline": getattr(config, "extraction_pipeline", "three_phase"),
            "enable_dedup": str(getattr(config, "enable_semantic_dedup", True)),
        }
    )
    logger.info(
        "prometheus_metrics_initialized", app_version=getattr(config, "app_version", "0.1.0")
    )
