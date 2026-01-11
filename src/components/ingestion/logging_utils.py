"""Ingestion Pipeline Logging Utilities.

Sprint 83 Feature 83.1: Comprehensive ingestion logging
Provides utilities for performance metrics, LLM cost tracking, and memory profiling.
"""

import statistics
import time
from typing import Any

import structlog

try:
    import pynvml

    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False

logger = structlog.get_logger(__name__)


# ============================================================================
# STATISTICS CALCULATION (P50/P95/P99 Percentiles)
# ============================================================================


def calculate_percentiles(values: list[float | int]) -> dict[str, float]:
    """Calculate P50/P95/P99 percentiles for latency analysis.

    Args:
        values: List of numeric values (latencies, durations, etc.)

    Returns:
        Dictionary with p50, p95, p99 keys (0.0 if empty list)

    Example:
        >>> latencies = [100, 150, 200, 250, 300, 400, 500, 600, 700, 1000]
        >>> percentiles = calculate_percentiles(latencies)
        >>> percentiles
        {'p50_ms': 300.0, 'p95_ms': 900.0, 'p99_ms': 980.0}
    """
    if not values:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}

    # Sort values for accurate percentile calculation
    sorted_values = sorted(values)

    # Handle single value case
    if len(sorted_values) == 1:
        single_val = round(sorted_values[0], 2)
        return {"p50_ms": single_val, "p95_ms": single_val, "p99_ms": single_val}

    return {
        "p50_ms": round(statistics.quantiles(sorted_values, n=2)[0], 2),
        "p95_ms": round(statistics.quantiles(sorted_values, n=100)[94], 2),
        "p99_ms": round(statistics.quantiles(sorted_values, n=100)[98], 2),
    }


# ============================================================================
# PER-PHASE LATENCY SUMMARY
# ============================================================================


def log_phase_summary(
    phase: str,
    total_time_ms: float,
    items_processed: int,
    per_item_latencies_ms: list[float] | None = None,
    **extra_metrics: Any,
) -> None:
    """Log comprehensive latency summary for an ingestion phase.

    Args:
        phase: Phase name (e.g., "graph_extraction", "chunking", "embedding")
        total_time_ms: Total phase duration in milliseconds
        items_processed: Number of items processed (chunks, entities, etc.)
        per_item_latencies_ms: Optional list of per-item latencies for percentile calculation
        **extra_metrics: Additional metrics to include in log

    Example:
        >>> latencies = [120, 150, 200, 250, 300]
        >>> log_phase_summary(
        ...     phase="graph_extraction",
        ...     total_time_ms=1200,
        ...     items_processed=5,
        ...     per_item_latencies_ms=latencies,
        ...     entities_extracted=150,
        ... )
        # Logs:
        # {
        #   "event": "TIMING_phase_summary",
        #   "phase": "graph_extraction",
        #   "total_time_ms": 1200,
        #   "items_processed": 5,
        #   "per_item_avg_ms": 240.0,
        #   "p50_ms": 200.0,
        #   "p95_ms": 290.0,
        #   "p99_ms": 298.0,
        #   "entities_extracted": 150
        # }
    """
    log_data = {
        "phase": phase,
        "total_time_ms": round(total_time_ms, 2),
        "items_processed": items_processed,
        "per_item_avg_ms": (
            round(total_time_ms / items_processed, 2) if items_processed > 0 else 0.0
        ),
    }

    # Add percentiles if per-item latencies provided
    if per_item_latencies_ms:
        percentiles = calculate_percentiles(per_item_latencies_ms)
        log_data.update(percentiles)

    # Add extra metrics
    log_data.update(extra_metrics)

    logger.info("TIMING_phase_summary", **log_data)


# ============================================================================
# LLM COST AGGREGATION
# ============================================================================


def log_llm_cost_summary(
    document_id: str,
    phase: str,
    total_tokens: int,
    prompt_tokens: int,
    completion_tokens: int,
    model: str,
    estimated_cost_usd: float | None = None,
) -> None:
    """Log LLM usage and cost summary for a document ingestion phase.

    Args:
        document_id: Document being processed
        phase: Phase name (e.g., "entity_extraction", "relation_extraction")
        total_tokens: Total tokens consumed
        prompt_tokens: Prompt tokens consumed
        completion_tokens: Completion tokens consumed
        model: LLM model used (e.g., "nemotron3", "qwen3:32b")
        estimated_cost_usd: Optional cost estimate (if using paid cloud provider)

    Example:
        >>> log_llm_cost_summary(
        ...     document_id="doc_123",
        ...     phase="entity_extraction",
        ...     total_tokens=125000,
        ...     prompt_tokens=100000,
        ...     completion_tokens=25000,
        ...     model="qwen3:32b",
        ...     estimated_cost_usd=0.025,
        ... )
        # Logs:
        # {
        #   "event": "llm_cost_summary",
        #   "document_id": "doc_123",
        #   "phase": "entity_extraction",
        #   "total_tokens": 125000,
        #   "prompt_tokens": 100000,
        #   "completion_tokens": 25000,
        #   "estimated_cost_usd": 0.025,
        #   "model": "qwen3:32b"
        # }
    """
    log_data = {
        "document_id": document_id,
        "phase": phase,
        "total_tokens": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "model": model,
    }

    if estimated_cost_usd is not None:
        log_data["estimated_cost_usd"] = round(estimated_cost_usd, 6)

    logger.info("llm_cost_summary", **log_data)


# ============================================================================
# EXTRACTION QUALITY METRICS
# ============================================================================


def log_extraction_quality_metrics(
    chunk_id: str,
    raw_entities_extracted: int,
    deduplicated_entities: int,
    entity_types: list[str],
    relation_confidence_avg: float | None = None,
    **extra_metrics: Any,
) -> None:
    """Log entity extraction quality metrics for a chunk.

    Args:
        chunk_id: Chunk being processed
        raw_entities_extracted: Number of entities before deduplication
        deduplicated_entities: Number of entities after deduplication
        entity_types: List of unique entity types found
        relation_confidence_avg: Average confidence score for extracted relations
        **extra_metrics: Additional quality metrics (e.g., entity_name_lengths, type_distribution)

    Example:
        >>> log_extraction_quality_metrics(
        ...     chunk_id="chunk_456",
        ...     raw_entities_extracted=45,
        ...     deduplicated_entities=32,
        ...     entity_types=["Product", "Feature", "Error Code"],
        ...     relation_confidence_avg=0.78,
        ... )
        # Logs:
        # {
        #   "event": "extraction_quality_metrics",
        #   "chunk_id": "chunk_456",
        #   "raw_entities_extracted": 45,
        #   "deduplicated_entities": 32,
        #   "deduplication_rate": 0.29,
        #   "entity_types": ["Product", "Feature", "Error Code"],
        #   "relation_confidence_avg": 0.78
        # }
    """
    deduplication_rate = (
        round((raw_entities_extracted - deduplicated_entities) / raw_entities_extracted, 2)
        if raw_entities_extracted > 0
        else 0.0
    )

    log_data = {
        "chunk_id": chunk_id,
        "raw_entities_extracted": raw_entities_extracted,
        "deduplicated_entities": deduplicated_entities,
        "deduplication_rate": deduplication_rate,
        "entity_types": entity_types,
    }

    if relation_confidence_avg is not None:
        log_data["relation_confidence_avg"] = round(relation_confidence_avg, 2)

    log_data.update(extra_metrics)

    logger.info("extraction_quality_metrics", **log_data)


# ============================================================================
# CHUNK-TO-ENTITY PROVENANCE
# ============================================================================


def log_chunk_entity_mapping(
    chunk_id: str,
    entities_created: list[str],
    relations_created: list[str],
    section_hierarchy: list[str],
    **extra_provenance: Any,
) -> None:
    """Log chunk-to-entity provenance for graph debugging.

    Args:
        chunk_id: Chunk being processed
        entities_created: List of entity IDs created from this chunk
        relations_created: List of relation IDs created from this chunk
        section_hierarchy: List of section headings for this chunk
        **extra_provenance: Additional provenance data (e.g., page_no, bbox)

    Example:
        >>> log_chunk_entity_mapping(
        ...     chunk_id="chunk_456",
        ...     entities_created=["Entity_789", "Entity_790"],
        ...     relations_created=["Rel_123", "Rel_124"],
        ...     section_hierarchy=["1.2.3 Troubleshooting", "1.2.3.1 Common Issues"],
        ... )
        # Logs:
        # {
        #   "event": "chunk_entity_mapping",
        #   "chunk_id": "chunk_456",
        #   "entities_created": ["Entity_789", "Entity_790"],
        #   "relations_created": ["Rel_123", "Rel_124"],
        #   "section_hierarchy": ["1.2.3 Troubleshooting", "1.2.3.1 Common Issues"]
        # }
    """
    log_data = {
        "chunk_id": chunk_id,
        "entities_created": entities_created,
        "relations_created": relations_created,
        "section_hierarchy": section_hierarchy,
    }

    log_data.update(extra_provenance)

    logger.info("chunk_entity_mapping", **log_data)


# ============================================================================
# MEMORY PROFILING (RAM + GPU VRAM)
# ============================================================================


def get_gpu_memory_info() -> dict[str, int] | None:
    """Get current GPU memory usage via pynvml.

    Returns:
        Dictionary with vram_used_mb and vram_available_mb, or None if pynvml unavailable

    Example:
        >>> info = get_gpu_memory_info()
        >>> info
        {'vram_used_mb': 4096, 'vram_available_mb': 4096}
    """
    if not PYNVML_AVAILABLE:
        return None

    try:
        # Initialize NVML if not already initialized
        try:
            pynvml.nvmlInit()
        except pynvml.NVMLError_AlreadyInitialized:
            pass  # Already initialized

        # Get first GPU (index 0)
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

        return {
            "vram_used_mb": mem_info.used // (1024**2),
            "vram_available_mb": mem_info.free // (1024**2),
        }

    except Exception as e:
        logger.warning("failed_to_get_gpu_memory", error=str(e))
        return None


def log_memory_snapshot(
    phase: str,
    ram_used_mb: int,
    ram_available_mb: int,
) -> None:
    """Log memory usage snapshot for a phase (RAM + optional GPU VRAM).

    Args:
        phase: Phase name (e.g., "entity_extraction", "chunking")
        ram_used_mb: RAM used in MB
        ram_available_mb: RAM available in MB

    Example:
        >>> log_memory_snapshot(
        ...     phase="entity_extraction",
        ...     ram_used_mb=2048,
        ...     ram_available_mb=6144,
        ... )
        # Logs:
        # {
        #   "event": "memory_snapshot",
        #   "phase": "entity_extraction",
        #   "ram_used_mb": 2048,
        #   "ram_available_mb": 6144,
        #   "vram_used_mb": 4096,  # If GPU available
        #   "vram_available_mb": 4096  # If GPU available
        # }
    """
    log_data = {
        "phase": phase,
        "ram_used_mb": ram_used_mb,
        "ram_available_mb": ram_available_mb,
    }

    # Add GPU memory if available
    gpu_mem = get_gpu_memory_info()
    if gpu_mem:
        log_data.update(gpu_mem)

    logger.info("memory_snapshot", **log_data)


# ============================================================================
# LATENCY TRACKER (Context Manager)
# ============================================================================


class PhaseLatencyTracker:
    """Context manager for tracking per-item latencies in a phase.

    Usage:
        >>> tracker = PhaseLatencyTracker()
        >>> for chunk in chunks:
        ...     with tracker.track():
        ...         process_chunk(chunk)  # Latency auto-tracked
        >>> tracker.log_summary(phase="graph_extraction", items_processed=len(chunks))
    """

    def __init__(self) -> None:
        """Initialize latency tracker."""
        self.latencies_ms: list[float] = []
        self.current_start: float | None = None

    def track(self) -> "PhaseLatencyTracker":
        """Start tracking an item (returns self for context manager)."""
        self.current_start = time.perf_counter()
        return self

    def __enter__(self) -> None:
        """Context manager entry."""
        self.current_start = time.perf_counter()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - record latency."""
        if self.current_start is not None:
            latency_ms = (time.perf_counter() - self.current_start) * 1000
            self.latencies_ms.append(latency_ms)
            self.current_start = None

    def log_summary(
        self,
        phase: str,
        items_processed: int,
        **extra_metrics: Any,
    ) -> None:
        """Log phase summary with tracked latencies.

        Args:
            phase: Phase name
            items_processed: Number of items processed
            **extra_metrics: Additional metrics to include
        """
        total_time_ms = sum(self.latencies_ms)
        log_phase_summary(
            phase=phase,
            total_time_ms=total_time_ms,
            items_processed=items_processed,
            per_item_latencies_ms=self.latencies_ms,
            **extra_metrics,
        )
