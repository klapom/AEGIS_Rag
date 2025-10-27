"""Monitoring and Observability Module - Sprint 14 Feature 14.6.

Provides Prometheus metrics, structured logging, and health checks
for production monitoring of AEGIS RAG extraction pipeline.
"""

from src.monitoring.metrics import (
    active_connections,
    deduplication_reduction_ratio,
    extraction_documents_total,
    extraction_duration,
    extraction_entities_total,
    extraction_errors_total,
    extraction_relations_total,
    extraction_retries_total,
    gpu_memory_usage_bytes,
    gpu_utilization_percent,
    initialize_system_info,
    query_duration,
    record_deduplication_reduction,
    record_extraction_document,
    record_extraction_duration,
    record_extraction_entities,
    record_extraction_error,
    record_extraction_relations,
    record_extraction_retry,
    record_query_duration,
    update_active_connections,
    update_gpu_memory,
)

__all__ = [
    "extraction_duration",
    "extraction_entities_total",
    "extraction_relations_total",
    "extraction_documents_total",
    "extraction_errors_total",
    "extraction_retries_total",
    "deduplication_reduction_ratio",
    "gpu_memory_usage_bytes",
    "gpu_utilization_percent",
    "query_duration",
    "active_connections",
    "record_extraction_duration",
    "record_extraction_entities",
    "record_extraction_relations",
    "record_extraction_document",
    "record_extraction_error",
    "record_extraction_retry",
    "record_deduplication_reduction",
    "update_gpu_memory",
    "record_query_duration",
    "update_active_connections",
    "initialize_system_info",
]
