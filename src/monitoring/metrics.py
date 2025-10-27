"""Prometheus Metrics for AEGIS RAG - Sprint 14 Feature 14.6.

Comprehensive metrics for extraction pipeline monitoring:
- Extraction duration by phase and pipeline type
- Entity/relation counts
- Error tracking
- GPU memory usage (if available)

Author: Claude Code
Date: 2025-10-27
"""

import structlog
from prometheus_client import Counter, Gauge, Histogram, Info

logger = structlog.get_logger(__name__)

# ============================================================================
# Extraction Pipeline Metrics
# ============================================================================

extraction_duration = Histogram(
    'aegis_extraction_duration_seconds',
    'Time spent in extraction pipeline',
    ['phase', 'pipeline_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0]
)

extraction_entities_total = Counter(
    'aegis_extraction_entities_total',
    'Total entities extracted',
    ['entity_type', 'pipeline_type']
)

extraction_relations_total = Counter(
    'aegis_extraction_relations_total',
    'Total relations extracted',
    ['pipeline_type']
)

extraction_documents_total = Counter(
    'aegis_extraction_documents_total',
    'Total documents processed',
    ['pipeline_type', 'status']  # status: success, failed, skipped
)

extraction_errors_total = Counter(
    'aegis_extraction_errors_total',
    'Total extraction errors',
    ['phase', 'error_type']
)

extraction_retries_total = Counter(
    'aegis_extraction_retries_total',
    'Total retry attempts',
    ['phase', 'success']  # success: true, false
)

deduplication_reduction_ratio = Histogram(
    'aegis_deduplication_reduction_ratio',
    'Deduplication reduction percentage',
    buckets=[0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
)

# ============================================================================
# GPU Memory Metrics (optional, only if GPU available)
# ============================================================================

gpu_memory_usage_bytes = Gauge(
    'aegis_gpu_memory_usage_bytes',
    'Current GPU memory usage',
    ['gpu_id']
)

gpu_memory_allocated_bytes = Gauge(
    'aegis_gpu_memory_allocated_bytes',
    'GPU memory allocated by PyTorch/TensorFlow',
    ['gpu_id']
)

gpu_utilization_percent = Gauge(
    'aegis_gpu_utilization_percent',
    'GPU utilization percentage',
    ['gpu_id']
)

# ============================================================================
# Query Metrics
# ============================================================================

query_duration = Histogram(
    'aegis_query_duration_seconds',
    'Query processing time',
    ['query_type', 'mode'],  # query_type: vector, graph, hybrid; mode: local, global
    buckets=[0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]
)

query_results_count = Histogram(
    'aegis_query_results_count',
    'Number of results returned per query',
    ['query_type'],
    buckets=[1, 5, 10, 20, 50, 100]
)

# ============================================================================
# System Metrics
# ============================================================================

system_info = Info(
    'aegis_system_info',
    'System information'
)

active_connections = Gauge(
    'aegis_active_connections',
    'Number of active connections',
    ['connection_type']  # connection_type: neo4j, qdrant, redis, ollama
)

# ============================================================================
# Helper Functions
# ============================================================================

def record_extraction_duration(phase: str, pipeline_type: str, duration: float):
    """Record extraction phase duration."""
    extraction_duration.labels(phase=phase, pipeline_type=pipeline_type).observe(duration)


def record_extraction_entities(entity_type: str, pipeline_type: str, count: int):
    """Record extracted entities."""
    extraction_entities_total.labels(
        entity_type=entity_type,
        pipeline_type=pipeline_type
    ).inc(count)


def record_extraction_relations(pipeline_type: str, count: int):
    """Record extracted relations."""
    extraction_relations_total.labels(pipeline_type=pipeline_type).inc(count)


def record_extraction_document(pipeline_type: str, status: str):
    """Record document processing status.

    Args:
        pipeline_type: three_phase, lightrag_default
        status: success, failed, skipped
    """
    extraction_documents_total.labels(
        pipeline_type=pipeline_type,
        status=status
    ).inc()


def record_extraction_error(phase: str, error_type: str):
    """Record extraction error.

    Args:
        phase: phase1_spacy, phase2_dedup, phase3_gemma
        error_type: connection_error, timeout, validation_error, etc.
    """
    extraction_errors_total.labels(phase=phase, error_type=error_type).inc()


def record_extraction_retry(phase: str, success: bool):
    """Record retry attempt.

    Args:
        phase: phase3_gemma (primary phase with retries)
        success: True if retry succeeded, False if failed
    """
    extraction_retries_total.labels(
        phase=phase,
        success=str(success).lower()
    ).inc()


def record_deduplication_reduction(reduction_ratio: float):
    """Record deduplication reduction ratio.

    Args:
        reduction_ratio: 0.0-1.0 (0.15 = 15% reduction)
    """
    deduplication_reduction_ratio.observe(reduction_ratio)


def update_gpu_memory(gpu_id: int, used_bytes: int, allocated_bytes: int, utilization: float):
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


def record_query_duration(query_type: str, mode: str, duration: float):
    """Record query duration.

    Args:
        query_type: vector, graph, hybrid
        mode: local, global
        duration: Query duration in seconds
    """
    query_duration.labels(query_type=query_type, mode=mode).observe(duration)


def update_active_connections(connection_type: str, count: int):
    """Update active connection count.

    Args:
        connection_type: neo4j, qdrant, redis, ollama
        count: Number of active connections
    """
    active_connections.labels(connection_type=connection_type).set(count)


def initialize_system_info(config):
    """Initialize system information metric.

    Args:
        config: Application configuration
    """
    system_info.info({
        'version': getattr(config, 'app_version', '0.1.0'),
        'environment': getattr(config, 'environment', 'development'),
        'extraction_pipeline': getattr(config, 'extraction_pipeline', 'three_phase'),
        'enable_dedup': str(getattr(config, 'enable_semantic_dedup', True)),
    })
    logger.info("prometheus_metrics_initialized", app_version=getattr(config, 'app_version', '0.1.0'))
