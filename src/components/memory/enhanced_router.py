"""Enhanced Memory Router with Strategy Pattern and Parallel Querying (Sprint 9 Feature 9.2).

This module implements intelligent memory routing across three layers:
- Layer 1 (Redis): Short-term working memory for recent context
- Layer 2 (Qdrant): Long-term semantic memory for facts
- Layer 3 (Graphiti): Episodic temporal memory for events

Features:
- Pluggable routing strategies (Recency, QueryType, Hybrid)
- Parallel multi-layer retrieval using asyncio
- Result merging and ranking
- Performance monitoring (<5ms routing decision, <100ms parallel retrieval)
"""

import asyncio
import time
from typing import Any

import structlog

from src.components.memory.graphiti_wrapper import get_graphiti_wrapper
from src.components.memory.models import MemoryEntry, MemorySearchResult
from src.components.memory.redis_manager import get_redis_manager
from src.components.memory.routing_strategy import (
    HybridStrategy,
    MemoryLayer,
    RoutingStrategy,
)
from src.components.vector_search.qdrant_client import get_qdrant_client
from src.core.config import settings
from src.core.exceptions import MemoryError

logger = structlog.get_logger(__name__)


class EnhancedMemoryRouter:
    """Enhanced memory router with strategy-based layer selection and parallel querying.

    Performance Targets:
    - Routing Decision: <5ms
    - Multi-Layer Retrieval: <100ms (parallel)
    - Correctness: 90%+ correct layer selection
    """

    def __init__(
        self,
        strategy: RoutingStrategy | None = None,
        session_id: str | None = None,
        enable_graphiti: bool = True,
    ):
        """Initialize enhanced memory router.

        Args:
            strategy: Routing strategy (default: HybridStrategy)
            session_id: Session ID for context tracking
            enable_graphiti: Enable Graphiti episodic memory layer
        """
        self.strategy = strategy or HybridStrategy()
        self.session_id = session_id
        self.enable_graphiti = enable_graphiti and settings.graphiti_enabled

        # Initialize memory layer clients
        self.redis_manager = get_redis_manager()
        self.qdrant_client = get_qdrant_client()

        # Initialize Graphiti if enabled
        self.graphiti_wrapper = None
        if self.enable_graphiti:
            try:
                self.graphiti_wrapper = get_graphiti_wrapper()
            except Exception as e:
                logger.warning("Graphiti not available", error=str(e))
                self.enable_graphiti = False

        logger.info(
            "Initialized EnhancedMemoryRouter",
            strategy=self.strategy.__class__.__name__,
            session_id=session_id,
            graphiti_enabled=self.enable_graphiti,
        )

    async def route_query(
        self,
        query: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[MemoryLayer]:
        """Determine which memory layers to query (routing decision).

        Args:
            query: User query text
            metadata: Additional metadata for routing decision

        Returns:
            Ordered list of memory layers to search

        Performance: <5ms
        """
        start_time = time.time()

        metadata = metadata or {}

        # Add session context to metadata
        if self.session_id:
            metadata["session_id"] = self.session_id

        # Use strategy to select layers
        selected_layers = self.strategy.select_layers(query, metadata)

        # Filter out unavailable layers
        available_layers = []
        for layer in selected_layers:
            if layer == MemoryLayer.GRAPHITI and not self.enable_graphiti:
                continue
            available_layers.append(layer)

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            "Routed query to memory layers",
            query=query[:100],
            strategy=self.strategy.__class__.__name__,
            selected_layers=[layer.value for layer in available_layers],
            routing_time_ms=round(elapsed_ms, 2),
        )

        return available_layers

    async def search_memory(
        self,
        query: str,
        metadata: dict[str, Any] | None = None,
        limit_per_layer: int = 10,
    ) -> dict[str, list[MemorySearchResult]]:
        """Search across multiple memory layers in parallel.

        Args:
            query: Search query
            metadata: Additional metadata for routing
            limit_per_layer: Maximum results per layer

        Returns:
            Dictionary mapping layer names to search results

        Raises:
            MemoryError: If all layer searches fail

        Performance: <100ms (parallel execution)
        """
        start_time = time.time()

        # Route query to appropriate layers
        layers = await self.route_query(query, metadata)

        # Build parallel search tasks
        tasks = []
        layer_names = []

        for layer in layers:
            if layer == MemoryLayer.REDIS:
                tasks.append(self._search_redis(query, limit_per_layer))
                layer_names.append("redis")

            elif layer == MemoryLayer.QDRANT:
                tasks.append(self._search_qdrant(query, limit_per_layer))
                layer_names.append("qdrant")

            elif layer == MemoryLayer.GRAPHITI:
                tasks.append(self._search_graphiti(query, limit_per_layer))
                layer_names.append("graphiti")

        # Execute searches in parallel
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge results
        results = {}
        for layer_name, layer_results in zip(layer_names, results_list, strict=False):
            if isinstance(layer_results, Exception):
                logger.error(
                    "Layer search failed",
                    layer=layer_name,
                    error=str(layer_results),
                )
                results[layer_name] = []
            else:
                results[layer_name] = layer_results

        elapsed_ms = (time.time() - start_time) * 1000
        total_results = sum(len(r) for r in results.values())

        logger.info(
            "Completed multi-layer memory search",
            query=query[:100],
            layers_searched=list(results.keys()),
            total_results=total_results,
            search_time_ms=round(elapsed_ms, 2),
        )

        # Check if all searches failed
        if all(isinstance(r, Exception) for r in results_list):
            raise MemoryError("All memory layer searches failed")

        return results

    async def _search_redis(
        self, query: str, limit: int
    ) -> list[MemorySearchResult]:
        """Search Redis short-term memory.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of search results from Redis
        """
        start_time = time.time()

        try:
            results = []

            # Extract tags from query (simple keyword extraction)
            tags = self._extract_tags(query)

            if tags:
                # Search by tags
                entries = await self.redis_manager.search(tags, limit=limit)

                for entry in entries:
                    # Simple keyword matching score
                    score = self._calculate_relevance_score(query, entry.value)

                    results.append(
                        MemorySearchResult(
                            entry=entry,
                            score=score,
                            layer="redis",
                            retrieval_time_ms=(time.time() - start_time) * 1000,
                        )
                    )

            # Sort by score descending
            results.sort(key=lambda x: x.score, reverse=True)

            logger.debug(
                "Searched Redis layer",
                query=query[:50],
                tags=tags,
                results_count=len(results),
            )

            return results[:limit]

        except Exception as e:
            logger.error("Redis search failed", error=str(e))
            return []

    async def _search_qdrant(
        self, query: str, limit: int
    ) -> list[MemorySearchResult]:
        """Search Qdrant long-term semantic memory.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of search results from Qdrant
        """
        time.time()

        try:
            # NOTE: This is a placeholder implementation
            # In production, this would:
            # 1. Generate query embedding
            # 2. Search Qdrant collection
            # 3. Convert results to MemorySearchResult format

            logger.info("Qdrant search requires embedding service (placeholder)")

            # Placeholder return
            return []

        except Exception as e:
            logger.error("Qdrant search failed", error=str(e))
            return []

    async def _search_graphiti(
        self, query: str, limit: int
    ) -> list[MemorySearchResult]:
        """Search Graphiti episodic temporal memory.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of search results from Graphiti
        """
        start_time = time.time()

        if not self.graphiti_wrapper:
            return []

        try:
            # Search Graphiti episodic memory
            results_raw = await self.graphiti_wrapper.search(
                query=query,
                limit=limit,
            )

            # Convert to MemorySearchResult format
            results = []
            for item in results_raw:
                # Create MemoryEntry from Graphiti result
                entry = MemoryEntry(
                    key=f"graphiti_{item.get('id', '')}",
                    value=item.get("content", ""),
                    ttl_seconds=0,  # Graphiti entries don't expire
                    tags=item.get("tags", []),
                    metadata=item.get("metadata", {}),
                    namespace="graphiti",
                )

                results.append(
                    MemorySearchResult(
                        entry=entry,
                        score=item.get("score", 0.5),
                        layer="graphiti",
                        retrieval_time_ms=(time.time() - start_time) * 1000,
                    )
                )

            logger.debug(
                "Searched Graphiti layer",
                query=query[:50],
                results_count=len(results),
            )

            return results

        except Exception as e:
            logger.error("Graphiti search failed", error=str(e))
            return []

    def _extract_tags(self, query: str) -> list[str]:
        """Extract potential tags from query for Redis search.

        Args:
            query: Query text

        Returns:
            List of extracted tags (keywords)
        """
        # Simple implementation: extract significant words
        # In production, could use NLP/NER
        import re

        # Remove common words
        stopwords = {
            "a",
            "an",
            "the",
            "is",
            "are",
            "was",
            "were",
            "what",
            "when",
            "where",
            "who",
            "how",
            "can",
            "could",
            "would",
            "should",
        }

        words = re.findall(r"\b\w+\b", query.lower())
        tags = [w for w in words if len(w) > 3 and w not in stopwords]

        return tags[:5]  # Limit to 5 tags

    def _calculate_relevance_score(self, query: str, content: str) -> float:
        """Calculate simple relevance score for keyword matching.

        Args:
            query: Query text
            content: Content to score

        Returns:
            Relevance score (0.0-1.0)
        """
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())

        if not query_words:
            return 0.0

        # Simple Jaccard similarity
        intersection = query_words.intersection(content_words)
        union = query_words.union(content_words)

        return len(intersection) / len(union) if union else 0.0

    async def store_memory(
        self,
        entry: MemoryEntry,
        target_layers: list[MemoryLayer] | None = None,
    ) -> dict[str, bool]:
        """Store memory entry in specified layers.

        Args:
            entry: MemoryEntry to store
            target_layers: Layers to store in (default: Redis only)

        Returns:
            Dictionary indicating success for each layer
        """
        target_layers = target_layers or [MemoryLayer.REDIS]
        results = {}

        for layer in target_layers:
            try:
                if layer == MemoryLayer.REDIS:
                    success = await self.redis_manager.store(entry)
                    results["redis"] = success

                elif layer == MemoryLayer.QDRANT:
                    # Placeholder for Qdrant storage
                    logger.info("Qdrant storage requires embedding service (placeholder)")
                    results["qdrant"] = False

                elif layer == MemoryLayer.GRAPHITI:
                    if self.graphiti_wrapper:
                        await self.graphiti_wrapper.add_episode(
                            content=entry.value,
                            source="memory_router",
                            metadata=entry.metadata,
                        )
                        results["graphiti"] = True
                    else:
                        results["graphiti"] = False

            except Exception as e:
                logger.error(
                    "Failed to store in layer",
                    layer=layer.value,
                    error=str(e),
                )
                results[layer.value] = False

        logger.info(
            "Stored memory entry",
            key=entry.key,
            layers=list(results.keys()),
            success_count=sum(1 for v in results.values() if v),
        )

        return results

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics for all memory layers.

        Returns:
            Dictionary with statistics for each layer
        """
        stats = {
            "router": {
                "strategy": self.strategy.__class__.__name__,
                "session_id": self.session_id,
            }
        }

        # Redis stats
        try:
            redis_stats = await self.redis_manager.get_stats()
            stats["redis"] = redis_stats
        except Exception as e:
            logger.error("Failed to get Redis stats", error=str(e))
            stats["redis"] = {"error": str(e)}

        # Qdrant stats (placeholder)
        stats["qdrant"] = {"note": "Statistics require implementation"}

        # Graphiti stats (placeholder)
        if self.graphiti_wrapper:
            stats["graphiti"] = {"enabled": True}
        else:
            stats["graphiti"] = {"enabled": False}

        return stats


# Global instance (singleton pattern)
_enhanced_router: EnhancedMemoryRouter | None = None


def get_enhanced_router(
    strategy: RoutingStrategy | None = None,
    session_id: str | None = None,
) -> EnhancedMemoryRouter:
    """Get enhanced memory router instance.

    Args:
        strategy: Routing strategy (default: HybridStrategy)
        session_id: Session ID for context tracking

    Returns:
        EnhancedMemoryRouter instance
    """
    if session_id or strategy:
        # Create new instance for specific session/strategy
        return EnhancedMemoryRouter(strategy=strategy, session_id=session_id)

    # Return global singleton
    global _enhanced_router
    if _enhanced_router is None:
        _enhanced_router = EnhancedMemoryRouter()
    return _enhanced_router
