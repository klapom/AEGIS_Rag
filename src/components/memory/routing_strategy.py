"""Memory Routing Strategies for Sprint 9 Feature 9.2.

This module provides routing strategies for intelligent memory layer selection:
- RecencyBasedStrategy: Route based on temporal recency
- QueryTypeStrategy: Route based on query type (factual vs episodic)
- HybridStrategy: Combine multiple strategies
"""

import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict

import structlog

logger = structlog.get_logger(__name__)


class MemoryLayer(Enum):
    """Memory layer enumeration for routing decisions."""

    REDIS = "redis"  # Short-term, <1 hour, session-scoped
    QDRANT = "qdrant"  # Long-term, semantic facts, documents
    GRAPHITI = "graphiti"  # Episodic, temporal events, relationships


class RoutingStrategy(ABC):
    """Abstract base class for memory routing strategies."""

    @abstractmethod
    def select_layers(self, query: str, metadata: Dict[str, Any]) -> list[MemoryLayer]:
        """Select appropriate memory layers for a query.

        Args:
            query: User query text
            metadata: Additional metadata (session_id, timestamp, context, etc.)

        Returns:
            Ordered list of memory layers to query
        """
        pass


class RecencyBasedStrategy(RoutingStrategy):
    """Routing strategy based on temporal recency.

    Rules:
    - Recent (< 1 hour): Redis only
    - Medium (1-24 hours): Redis + Qdrant
    - Old (> 24 hours): Qdrant + Graphiti
    """

    def __init__(
        self,
        recent_threshold_hours: float = 1.0,
        medium_threshold_hours: float = 24.0,
    ) -> None:
        """Initialize recency-based strategy.

        Args:
            recent_threshold_hours: Threshold for "recent" queries (default: 1 hour)
            medium_threshold_hours: Threshold for "medium" queries (default: 24 hours)
        """
        self.recent_threshold = timedelta(hours=recent_threshold_hours)
        self.medium_threshold = timedelta(hours=medium_threshold_hours)

        logger.info(
            "Initialized RecencyBasedStrategy",
            recent_threshold_hours=recent_threshold_hours,
            medium_threshold_hours=medium_threshold_hours,
        )

    def select_layers(self, query: str, metadata: Dict[str, Any]) -> list[MemoryLayer]:
        """Select layers based on query recency.

        Args:
            query: User query text
            metadata: Must contain 'timestamp' or 'session_start_time'

        Returns:
            Ordered list of memory layers
        """
        # Extract temporal information from metadata
        query_time = metadata.get("timestamp")
        if isinstance(query_time, str):
            query_time = datetime.fromisoformat(query_time)
        elif not isinstance(query_time, datetime):
            query_time = datetime.now(timezone.utc)

        session_start = metadata.get("session_start_time")
        if isinstance(session_start, str):
            session_start = datetime.fromisoformat(session_start)

        # Calculate time delta
        now = datetime.now(timezone.utc)
        reference_time = session_start if session_start else query_time
        time_delta = now - reference_time

        # Route based on recency
        if time_delta < self.recent_threshold:
            # Very recent: Redis only
            layers = [MemoryLayer.REDIS]
            logger.debug(
                "Selected REDIS layer",
                reason="recent_query",
                time_delta_minutes=time_delta.total_seconds() / 60,
            )

        elif time_delta < self.medium_threshold:
            # Medium recency: Redis + Qdrant
            layers = [MemoryLayer.REDIS, MemoryLayer.QDRANT]
            logger.debug(
                "Selected REDIS + QDRANT layers",
                reason="medium_recency",
                time_delta_hours=time_delta.total_seconds() / 3600,
            )

        else:
            # Old query: Qdrant + Graphiti
            layers = [MemoryLayer.QDRANT, MemoryLayer.GRAPHITI]
            logger.debug(
                "Selected QDRANT + GRAPHITI layers",
                reason="old_query",
                time_delta_hours=time_delta.total_seconds() / 3600,
            )

        return layers


class QueryTypeStrategy(RoutingStrategy):
    """Routing strategy based on query type classification.

    Rules:
    - Factual query → Qdrant (semantic search over documents)
    - Episodic query → Graphiti (temporal events, relationships)
    - Session/context query → Redis (recent conversation)
    - Ambiguous → All layers
    """

    def __init__(self) -> None:
        """Initialize query-type-based strategy."""
        # Patterns for query type classification
        self.factual_patterns = [
            r"\bwhat\s+is\b",
            r"\bdefine\b",
            r"\bexplain\b",
            r"\bhow\s+(does|do|to)\b",
            r"\blist\b",
            r"\bdescribe\b",
            r"\bcompare\b",
        ]

        self.episodic_patterns = [
            r"\bwhen\s+(did|was|were)\b",
            r"\btimeline\b",
            r"\bhistory\b",
            r"\bevolution\b",
            r"\b(changed|became|started|ended)\b",
            r"\b(before|after|during)\s+",
            r"\bfirst\s+time\b",
            r"\blast\s+time\b",
        ]

        self.session_patterns = [
            r"\b(just|earlier|previous|recent)\b",
            r"\b(we|our)\s+(discussed|talked|mentioned)\b",
            r"\bwhat\s+did\s+[iI]\s+(say|ask)\b",
            r"\bcontext\b",
            r"\bremember\s+(when|what|that)\b",
        ]

        logger.info("Initialized QueryTypeStrategy")

    def select_layers(self, query: str, metadata: Dict[str, Any]) -> list[MemoryLayer]:
        """Select layers based on query type.

        Args:
            query: User query text
            metadata: Additional context (session_id, etc.)

        Returns:
            Ordered list of memory layers
        """
        query_lower = query.lower()

        # Check for session/context patterns first
        if self._matches_patterns(query_lower, self.session_patterns):
            layers = [MemoryLayer.REDIS]
            logger.debug("Selected REDIS layer", reason="session_query")
            return layers

        # Check for episodic patterns
        is_episodic = self._matches_patterns(query_lower, self.episodic_patterns)

        # Check for factual patterns
        is_factual = self._matches_patterns(query_lower, self.factual_patterns)

        # Route based on classification
        if is_episodic and not is_factual:
            # Pure episodic query
            layers = [MemoryLayer.GRAPHITI, MemoryLayer.QDRANT]
            logger.debug("Selected GRAPHITI + QDRANT layers", reason="episodic_query")

        elif is_factual and not is_episodic:
            # Pure factual query
            layers = [MemoryLayer.QDRANT]
            logger.debug("Selected QDRANT layer", reason="factual_query")

        else:
            # Ambiguous or hybrid query - query all layers
            layers = [MemoryLayer.QDRANT, MemoryLayer.GRAPHITI, MemoryLayer.REDIS]
            logger.debug(
                "Selected all layers",
                reason="ambiguous_query",
                is_factual=is_factual,
                is_episodic=is_episodic,
            )

        return layers

    def _matches_patterns(self, text: str, patterns: list[str]) -> bool:
        """Check if text matches any of the given patterns.

        Args:
            text: Text to check
            patterns: List of regex patterns

        Returns:
            True if any pattern matches
        """
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


class HybridStrategy(RoutingStrategy):
    """Hybrid routing strategy combining recency and query type.

    This strategy uses both temporal recency and query type to make
    more intelligent routing decisions.
    """

    def __init__(
        self,
        recent_threshold_hours: float = 1.0,
        medium_threshold_hours: float = 24.0,
    ) -> None:
        """Initialize hybrid strategy.

        Args:
            recent_threshold_hours: Threshold for "recent" queries
            medium_threshold_hours: Threshold for "medium" queries
        """
        self.recency_strategy = RecencyBasedStrategy(recent_threshold_hours, medium_threshold_hours)
        self.query_type_strategy = QueryTypeStrategy()

        logger.info("Initialized HybridStrategy")

    def select_layers(self, query: str, metadata: Dict[str, Any]) -> list[MemoryLayer]:
        """Select layers using both recency and query type.

        Args:
            query: User query text
            metadata: Additional context

        Returns:
            Ordered list of memory layers (merged from both strategies)
        """
        # Get recommendations from both strategies
        recency_layers = self.recency_strategy.select_layers(query, metadata)
        query_type_layers = self.query_type_strategy.select_layers(query, metadata)

        # Merge and deduplicate (preserving order)
        seen = set()
        merged_layers = []

        # Priority to query_type layers (more specific)
        for layer in query_type_layers:
            if layer not in seen:
                merged_layers.append(layer)
                seen.add(layer)

        # Add recency layers
        for layer in recency_layers:
            if layer not in seen:
                merged_layers.append(layer)
                seen.add(layer)

        logger.debug(
            "Hybrid strategy selected layers",
            query=query[:50],
            recency_layers=[layer.value for layer in recency_layers],
            query_type_layers=[layer.value for layer in query_type_layers],
            final_layers=[layer.value for layer in merged_layers],
        )

        return merged_layers


class FallbackAllStrategy(RoutingStrategy):
    """Fallback strategy that always queries all layers.

    Used when uncertain about the best routing decision.
    Guarantees comprehensive results at the cost of performance.
    """

    def select_layers(self, query: str, metadata: Dict[str, Any]) -> list[MemoryLayer]:
        """Always return all layers.

        Args:
            query: User query text (ignored)
            metadata: Additional context (ignored)

        Returns:
            All memory layers
        """
        return [MemoryLayer.REDIS, MemoryLayer.QDRANT, MemoryLayer.GRAPHITI]
