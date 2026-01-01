"""Training Data Extraction from Unified Tracer Logs.

Sprint 69 Feature 69.4: Learned Adaptive Reranker Weights (8 SP)

This module extracts high-quality reranking training pairs from UnifiedTracer
logs to enable learning optimal reranking weights for different query intents.

Architecture:
    The extractor filters trace events by quality score, extracts relevant
    features (semantic scores, keyword scores, recency), and labels relevance
    based on user feedback signals (click-through, dwell time, explicit ratings).

Features:
    - Quality filtering (>0.7 threshold)
    - Intent-aware pair extraction
    - Relevance label inference from signals
    - JSONL output for efficient training

Performance:
    - Extraction: <500ms for 10k traces
    - Memory efficient: Streaming JSONL parsing
    - No blocking: Async I/O

Example:
    >>> from src.adaptation import extract_rerank_pairs
    >>> from datetime import datetime, timedelta
    >>>
    >>> # Extract training pairs from last 7 days
    >>> pairs = await extract_rerank_pairs(
    ...     min_quality_score=0.7,
    ...     time_range=(datetime.now() - timedelta(days=7), datetime.now())
    ... )
    >>> print(f"Extracted {len(pairs)} training pairs")
    >>> print(f"Example pair: {pairs[0]}")
    {
        'query': 'What is hybrid search?',
        'intent': 'factual',
        'doc_id': 'doc_123',
        'semantic_score': 0.89,
        'keyword_score': 0.72,
        'recency_score': 0.85,
        'relevance_label': 1.0,  # 0.0-1.0 (graded relevance)
        'timestamp': '2026-01-01T12:00:00',
        'metadata': {...}
    }

See Also:
    - src/adaptation/trace_telemetry.py: UnifiedTracer implementation
    - src/adaptation/weight_optimizer.py: Weight optimization using pairs
    - docs/sprints/SPRINT_69_PLAN.md: Sprint plan
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiofiles
import structlog

from src.adaptation.trace_telemetry import PipelineStage

logger = structlog.get_logger(__name__)


@dataclass
class RerankTrainingPair:
    """Training pair for reranker weight optimization.

    Attributes:
        query: User query text
        intent: Query intent (factual/keyword/exploratory/summary/default)
        doc_id: Document identifier
        semantic_score: Semantic relevance score from cross-encoder (0.0-1.0)
        keyword_score: Keyword matching score from BM25 (0.0-1.0)
        recency_score: Document recency score (0.0-1.0)
        relevance_label: Ground truth relevance (0.0-1.0, graded)
        timestamp: Event timestamp
        metadata: Additional context (optional)
    """

    query: str
    intent: str
    doc_id: str
    semantic_score: float
    keyword_score: float
    recency_score: float
    relevance_label: float
    timestamp: str
    metadata: dict[str, Any] | None = None


def _infer_relevance_from_signals(event_metadata: dict[str, Any]) -> float | None:
    """Infer relevance label from user feedback signals.

    Args:
        event_metadata: Event metadata containing user signals

    Returns:
        Relevance score between 0.0 and 1.0, or None if no signals

    Signals:
        - click_through: Document was clicked (weight: 0.3)
        - dwell_time_sec: Time spent on document (weight: 0.5)
        - explicit_rating: User rating 1-5 stars (weight: 0.8)
        - citation_used: Document cited in final answer (weight: 0.6)

    Algorithm:
        1. Start with base score 0.5 (neutral)
        2. Apply weighted signal contributions
        3. Clamp to [0.0, 1.0]

    Example:
        >>> metadata = {
        ...     'click_through': True,
        ...     'dwell_time_sec': 45,
        ...     'citation_used': True
        ... }
        >>> _infer_relevance_from_signals(metadata)
        0.85
    """
    # Base score (neutral)
    score = 0.5

    # Signal: Click-through (+0.3)
    if event_metadata.get("click_through"):
        score += 0.3

    # Signal: Dwell time (normalize 0-120s → 0.0-0.5)
    dwell_time = event_metadata.get("dwell_time_sec", 0)
    if dwell_time > 0:
        # Sigmoid-like: 30s → +0.25, 60s → +0.4, 120s → +0.5
        dwell_contribution = min(0.5, dwell_time / 120.0 * 0.5)
        score += dwell_contribution

    # Signal: Explicit rating (1-5 stars → 0.0-0.8)
    explicit_rating = event_metadata.get("explicit_rating")
    if explicit_rating is not None:
        # 1 star → 0.0, 3 stars → 0.4, 5 stars → 0.8
        rating_contribution = (explicit_rating - 1) / 4.0 * 0.8
        score = score * 0.2 + rating_contribution * 0.8  # Explicit rating dominates

    # Signal: Citation used (+0.4)
    if event_metadata.get("citation_used"):
        score += 0.4

    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, score))


def _compute_quality_score(event: dict[str, Any]) -> float:
    """Compute quality score for a trace event.

    Args:
        event: Trace event dictionary

    Returns:
        Quality score between 0.0 and 1.0

    Quality factors:
        - Has all required scores (semantic, keyword, recency): +0.3
        - Has relevance signals (click, dwell, rating): +0.3
        - Latency < 500ms (fast retrieval): +0.2
        - Cache miss (fresh retrieval): +0.2

    Example:
        >>> event = {
        ...     'stage': 'reranking',
        ...     'latency_ms': 150,
        ...     'cache_hit': False,
        ...     'metadata': {
        ...         'semantic_score': 0.89,
        ...         'keyword_score': 0.72,
        ...         'recency_score': 0.85,
        ...         'click_through': True
        ...     }
        ... }
        >>> _compute_quality_score(event)
        1.0
    """
    score = 0.0
    metadata = event.get("metadata", {})

    # Factor 1: Has all required scores
    if all(
        metadata.get(field) is not None
        for field in ["semantic_score", "keyword_score", "recency_score"]
    ):
        score += 0.3

    # Factor 2: Has relevance signals
    has_signals = any(
        metadata.get(signal)
        for signal in ["click_through", "dwell_time_sec", "explicit_rating", "citation_used"]
    )
    if has_signals:
        score += 0.3

    # Factor 3: Fast retrieval (latency < 500ms)
    if event.get("latency_ms", float("inf")) < 500:
        score += 0.2

    # Factor 4: Fresh retrieval (cache miss)
    if event.get("cache_hit") is False:
        score += 0.2

    return score


async def extract_rerank_pairs(
    trace_path: str = "data/traces/traces.jsonl",
    min_quality_score: float = 0.7,
    time_range: tuple[datetime, datetime] | None = None,
    output_path: str | None = None,
) -> list[RerankTrainingPair]:
    """Extract reranking training pairs from UnifiedTracer logs.

    Args:
        trace_path: Path to JSONL trace log file
        min_quality_score: Minimum quality score threshold (0.0-1.0, default: 0.7)
        time_range: Optional time range filter (start_time, end_time)
        output_path: Optional path to save extracted pairs as JSONL

    Returns:
        list of RerankTrainingPair instances

    Raises:
        FileNotFoundError: If trace file does not exist
        ValueError: If min_quality_score not in [0.0, 1.0]

    Example:
        >>> from datetime import datetime, timedelta
        >>> pairs = await extract_rerank_pairs(
        ...     min_quality_score=0.7,
        ...     time_range=(datetime.now() - timedelta(days=7), datetime.now()),
        ...     output_path="data/rerank_training_pairs.jsonl"
        ... )
        >>> print(f"Extracted {len(pairs)} high-quality pairs")

    Algorithm:
        1. Stream trace events from JSONL file
        2. Filter by stage=RERANKING and time_range
        3. Compute quality score for each event
        4. Filter by min_quality_score threshold
        5. Extract features (semantic, keyword, recency scores)
        6. Infer relevance labels from user signals
        7. Return list of training pairs

    Performance:
        - Target: <500ms for 10k traces
        - Memory efficient: Streaming JSONL parsing
        - Async I/O: Non-blocking file reads
    """
    # Validate parameters
    if not 0.0 <= min_quality_score <= 1.0:
        raise ValueError(f"min_quality_score must be in [0.0, 1.0], got {min_quality_score}")

    trace_file = Path(trace_path)
    if not trace_file.exists():
        raise FileNotFoundError(f"Trace file not found: {trace_path}")

    logger.info(
        "extracting_rerank_pairs",
        trace_path=trace_path,
        min_quality_score=min_quality_score,
        time_range=time_range,
    )

    # Default time range: last 7 days
    if time_range is None:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        time_range = (start_time, end_time)

    start_time, end_time = time_range

    # Accumulators
    pairs: list[RerankTrainingPair] = []
    total_events = 0
    filtered_by_stage = 0
    filtered_by_quality = 0
    filtered_by_missing_labels = 0

    # Stream events from JSONL file
    async with aiofiles.open(trace_file, mode="r", encoding="utf-8") as f:
        async for line in f:
            try:
                event = json.loads(line.strip())
                total_events += 1

                # Filter 1: Stage must be RERANKING
                if event.get("stage") != PipelineStage.RERANKING.value:
                    filtered_by_stage += 1
                    continue

                # Filter 2: Time range
                event_time = datetime.fromisoformat(event["timestamp"])
                if not (start_time <= event_time <= end_time):
                    continue

                # Filter 3: Quality score
                quality_score = _compute_quality_score(event)
                if quality_score < min_quality_score:
                    filtered_by_quality += 1
                    continue

                # Extract features from metadata
                metadata = event.get("metadata", {})

                # Filter 4: Must have all required scores
                semantic_score = metadata.get("semantic_score")
                keyword_score = metadata.get("keyword_score")
                recency_score = metadata.get("recency_score")
                query = metadata.get("query")
                intent = metadata.get("intent", "default")
                doc_id = metadata.get("doc_id")

                if not all([semantic_score, keyword_score, recency_score, query, doc_id]):
                    logger.debug(
                        "skipping_event_missing_features",
                        doc_id=doc_id,
                        has_semantic=semantic_score is not None,
                        has_keyword=keyword_score is not None,
                        has_recency=recency_score is not None,
                        has_query=query is not None,
                    )
                    continue

                # Infer relevance label from signals
                relevance_label = _infer_relevance_from_signals(metadata)
                if relevance_label is None:
                    # No relevance signals available
                    filtered_by_missing_labels += 1
                    continue

                # Create training pair
                pair = RerankTrainingPair(
                    query=query,
                    intent=intent,
                    doc_id=doc_id,
                    semantic_score=float(semantic_score),
                    keyword_score=float(keyword_score),
                    recency_score=float(recency_score),
                    relevance_label=float(relevance_label),
                    timestamp=event["timestamp"],
                    metadata={
                        "quality_score": quality_score,
                        "latency_ms": event.get("latency_ms"),
                        "cache_hit": event.get("cache_hit"),
                    },
                )
                pairs.append(pair)

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning("skipping_malformed_event", error=str(e), line=line[:100])
                continue

    logger.info(
        "extraction_complete",
        total_events=total_events,
        extracted_pairs=len(pairs),
        filtered_by_stage=filtered_by_stage,
        filtered_by_quality=filtered_by_quality,
        filtered_by_missing_labels=filtered_by_missing_labels,
        quality_threshold=min_quality_score,
    )

    # Save to output file if specified
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(output_file, mode="w", encoding="utf-8") as f:
            for pair in pairs:
                pair_dict = asdict(pair)
                json_line = json.dumps(pair_dict, ensure_ascii=False) + "\n"
                await f.write(json_line)

        logger.info(
            "saved_training_pairs",
            output_path=output_path,
            num_pairs=len(pairs),
        )

    return pairs


async def load_training_pairs(input_path: str) -> list[RerankTrainingPair]:
    """Load training pairs from JSONL file.

    Args:
        input_path: Path to JSONL file with training pairs

    Returns:
        list of RerankTrainingPair instances

    Raises:
        FileNotFoundError: If input file does not exist

    Example:
        >>> pairs = await load_training_pairs("data/rerank_training_pairs.jsonl")
        >>> print(f"Loaded {len(pairs)} training pairs")
    """
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Training pairs file not found: {input_path}")

    pairs: list[RerankTrainingPair] = []

    async with aiofiles.open(input_file, mode="r", encoding="utf-8") as f:
        async for line in f:
            try:
                pair_dict = json.loads(line.strip())
                pair = RerankTrainingPair(**pair_dict)
                pairs.append(pair)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("skipping_malformed_pair", error=str(e))
                continue

    logger.info("loaded_training_pairs", input_path=input_path, num_pairs=len(pairs))
    return pairs
