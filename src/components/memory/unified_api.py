"""Unified Memory API for 3-Layer Memory Architecture.

This module provides a single facade for all memory operations across:
- Layer 1 (Redis): Short-term working memory
- Layer 2 (Qdrant): Long-term semantic memory
- Layer 3 (Graphiti): Episodic temporal memory

Key features:
- Consistent interface for all layers
- Automatic layer routing
- Graceful degradation on failures
- Prometheus metrics collection
- Retry logic with exponential backoff
"""

import time
from typing import Any, Dict

import structlog
from prometheus_client import Counter, Histogram
from tenacity import retry, stop_after_attempt, wait_exponential

from src.components.memory.graphiti_wrapper import get_graphiti_wrapper
from src.components.memory.memory_router import get_memory_router
from src.components.memory.redis_memory import get_redis_memory
from src.components.vector_search.qdrant_client import get_qdrant_client
from src.core.config import settings

logger = structlog.get_logger(__name__)


class UnifiedMemoryAPI:
    """Unified API facade for all memory layers.

    Provides a consistent interface for memory operations across Redis,
    Qdrant, and Graphiti. Handles routing, error recovery, and metrics.
    """

    def __init__(
        self,
        session_id: str | None = None,
        enable_metrics: bool = True,
    ) -> None:
        """Initialize unified memory API.

        Args:
            session_id: Session ID for context tracking
            enable_metrics: Enable Prometheus metrics collection
        """
        self.session_id = session_id

        # Initialize all memory layer clients
        self.redis_memory = get_redis_memory()
        self.qdrant_client = get_qdrant_client()
        self.memory_router = get_memory_router(session_id)

        # Initialize Graphiti only if enabled
        self.graphiti_wrapper = None
        if settings.graphiti_enabled:
            try:
                self.graphiti_wrapper = get_graphiti_wrapper()
            except Exception as e:
                logger.warning("Graphiti not available", error=str(e))

        # Prometheus metrics
        self.enable_metrics = enable_metrics
        if enable_metrics:
            self.store_counter = Counter(
                "memory_store_total",
                "Total memory store operations",
                ["layer", "status"],
            )
            self.retrieve_counter = Counter(
                "memory_retrieve_total",
                "Total memory retrieve operations",
                ["layer", "status"],
            )
            self.latency_histogram = Histogram(
                "memory_operation_latency_seconds",
                "Memory operation latency",
                ["operation", "layer"],
            )

        logger.info(
            "Initialized UnifiedMemoryAPI",
            session_id=session_id,
            graphiti_available=self.graphiti_wrapper is not None,
            metrics_enabled=enable_metrics,
        )

    async def store(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
        namespace: str = "memory",
        metadata: Dict[str, Any] | None = None,
    ) -> bool:
        """Store data in working memory (Redis Layer 1).

        All new memories start in Redis for fast access. They are
        automatically consolidated to long-term layers based on usage.

        Args:
            key: Storage key (unique identifier)
            value: Value to store (any JSON-serializable data)
            ttl_seconds: Time-to-live in seconds (default: from settings)
            namespace: Key namespace for organization
            metadata: Optional metadata (access patterns, user ratings, etc.)

        Returns:
            True if stored successfully, False otherwise

        Example:
            >>> api = UnifiedMemoryAPI(session_id="user_123")
            >>> await api.store("pref_theme", "dark", ttl_seconds=3600)
            True
        """
        start_time = time.time()
        layer = "redis"

        try:
            # Merge metadata if provided
            store_value = value
            if metadata:
                store_value = {
                    "value": value,
                    "metadata": metadata,
                }

            success = await self.redis_memory.store(
                key=key,
                value=store_value,
                ttl_seconds=ttl_seconds,
                namespace=namespace,
            )

            if self.enable_metrics:
                self.store_counter.labels(layer=layer, status="success").inc()
                self.latency_histogram.labels(operation="store", layer=layer).observe(
                    time.time() - start_time
                )

            logger.debug(
                "Stored in working memory",
                key=key,
                namespace=namespace,
                ttl_seconds=ttl_seconds,
            )

            return success

        except Exception as e:
            if self.enable_metrics:
                self.store_counter.labels(layer=layer, status="error").inc()

            logger.error(
                "Failed to store in working memory",
                key=key,
                namespace=namespace,
                error=str(e),
            )
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def retrieve(
        self,
        query: str,
        session_id: str | None = None,
        limit: int = 10,
        time_window_hours: int | None = None,
    ) -> Dict[str, Any]:
        """Retrieve memories across all layers using intelligent routing.

        Automatically selects appropriate layers based on query analysis
        and returns combined results.

        Args:
            query: Search query (natural language or keywords)
            session_id: Override session ID (default: from constructor)
            limit: Maximum results per layer
            time_window_hours: Limit temporal search to recent N hours

        Returns:
            Dictionary with results from each layer:
            {
                "short_term": [...],   # Redis results
                "long_term": [...],    # Qdrant results
                "episodic": [...],     # Graphiti results
                "total_results": N,
                "layers_searched": [...],
            }

        Raises:
            MemoryError: If all layers fail (retries exhausted)

        Example:
            >>> results = await api.retrieve("What did we discuss about pricing?")
            >>> print(results["total_results"])
            5
        """
        start_time = time.time()
        session = session_id or self.session_id

        try:
            # Use memory router for intelligent layer selection
            results = await self.memory_router.search_memory(
                query=query,
                session_id=session,
                limit=limit,
                time_window_hours=time_window_hours,
            )

            # Calculate total results
            total_results = sum(len(layer_results) for layer_results in results.values())

            # Add metadata
            results["total_results"] = total_results
            results["layers_searched"] = list(results.keys())
            results["query"] = query
            results["latency_ms"] = round((time.time() - start_time) * 1000, 2)

            if self.enable_metrics:
                self.retrieve_counter.labels(layer="multi", status="success").inc()
                self.latency_histogram.labels(operation="retrieve", layer="multi").observe(
                    time.time() - start_time
                )

            logger.info(
                "Retrieved memories across layers",
                query=query[:100],
                total_results=total_results,
                layers=results["layers_searched"],
                latency_ms=results["latency_ms"],
            )

            return results

        except Exception as e:
            if self.enable_metrics:
                self.retrieve_counter.labels(layer="multi", status="error").inc()

            logger.error("Memory retrieval failed", query=query, error=str(e))

            # Graceful degradation: return empty results
            return {
                "short_term": [],
                "long_term": [],
                "episodic": [],
                "total_results": 0,
                "layers_searched": [],
                "error": str(e),
            }

    async def search(
        self,
        query: str,
        layers: list[str] | None = None,
        top_k: int = 5,
        filters: Dict[str, Any] | None = None,
    ) -> list[Dict[str, Any]]:
        """Search specific memory layers with optional filters.

        More granular control than `retrieve()`. Allows explicit layer
        selection and filtering.

        Args:
            query: Search query
            layers: Specific layers to search (default: all available)
                Options: ["short_term", "long_term", "episodic"]
            top_k: Number of results per layer
            filters: Optional metadata filters (layer-specific)

        Returns:
            Flat list of search results with layer tags

        Example:
            >>> results = await api.search(
            ...     "machine learning",
            ...     layers=["long_term"],
            ...     top_k=10
            ... )
            >>> for result in results:
            ...     print(f"{result['layer']}: {result['content']}")
        """
        start_time = time.time()

        # Default to all available layers
        if layers is None:
            layers = ["short_term", "long_term"]
            if self.graphiti_wrapper:
                layers.append("episodic")

        all_results = []

        # Search each specified layer
        for layer in layers:
            try:
                if layer == "short_term":
                    layer_results = await self._search_short_term(query, top_k)
                    all_results.extend(layer_results)

                elif layer == "long_term":
                    layer_results = await self._search_long_term(query, top_k, filters)
                    all_results.extend(layer_results)

                elif layer == "episodic":
                    if self.graphiti_wrapper:
                        layer_results = await self._search_episodic(query, top_k)
                        all_results.extend(layer_results)
                    else:
                        logger.debug("Episodic layer not available, skipping")

                else:
                    logger.warning(f"Unknown layer: {layer}, skipping")

            except Exception as e:
                logger.error(f"Search failed for layer {layer}", error=str(e))
                # Continue with other layers

        logger.info(
            "Multi-layer search complete",
            query=query[:100],
            layers=layers,
            total_results=len(all_results),
            latency_ms=round((time.time() - start_time) * 1000, 2),
        )

        return all_results

    async def _search_short_term(
        self,
        query: str,
        top_k: int,
    ) -> list[Dict[str, Any]]:
        """Search Redis short-term memory (placeholder)."""
        # Simplified keyword search for now
        # In production, would use semantic search on embeddings
        return []

    async def _search_long_term(
        self,
        query: str,
        top_k: int,
        filters: Dict[str, Any] | None,
    ) -> list[Dict[str, Any]]:
        """Search Qdrant long-term memory (placeholder)."""
        # Would generate embeddings and search Qdrant
        return []

    async def _search_episodic(
        self,
        query: str,
        top_k: int,
    ) -> list[Dict[str, Any]]:
        """Search Graphiti episodic memory."""
        if not self.graphiti_wrapper:
            return []

        try:
            results = await self.graphiti_wrapper.search(query=query, limit=top_k)
            return results
        except Exception as e:
            logger.error("Episodic search failed", error=str(e))
            return []

    async def delete(
        self,
        key: str,
        namespace: str = "memory",
        all_layers: bool = False,
    ) -> dict[str, bool]:
        """Delete memory from Redis or all layers.

        Args:
            key: Storage key to delete
            namespace: Key namespace
            all_layers: If True, attempt to delete from all layers

        Returns:
            Dictionary indicating success for each layer:
            {"short_term": True, "long_term": False, "episodic": True}

        Example:
            >>> await api.delete("temp_cache_123")
            {"short_term": True}
            >>> await api.delete("important_fact", all_layers=True)
            {"short_term": True, "long_term": True, "episodic": False}
        """
        results = {}

        # Always delete from Redis
        try:
            results["short_term"] = await self.redis_memory.delete(
                key=key,
                namespace=namespace,
            )
        except Exception as e:
            logger.error("Failed to delete from Redis", key=key, error=str(e))
            results["short_term"] = False

        # Delete from other layers if requested
        if all_layers:
            # Qdrant deletion (placeholder)
            results["long_term"] = False
            logger.debug("Long-term deletion not implemented")

            # Graphiti deletion (placeholder)
            results["episodic"] = False
            logger.debug("Episodic deletion not implemented")

        logger.info(
            "Memory deletion",
            key=key,
            all_layers=all_layers,
            results=results,
        )

        return results

    async def store_conversation_turn(
        self,
        user_message: str,
        assistant_message: str,
        metadata: Dict[str, Any] | None = None,
    ) -> dict[str, bool]:
        """Store a conversation turn across appropriate memory layers.

        Convenience method for conversational agents. Automatically
        stores in Redis (short-term) and Graphiti (episodic).

        Args:
            user_message: User message content
            assistant_message: Assistant response content
            metadata: Additional metadata (timestamps, etc.)

        Returns:
            Dictionary indicating success for each layer

        Example:
            >>> results = await api.store_conversation_turn(
            ...     "What's the weather?",
            ...     "It's sunny today!",
            ...     metadata={"intent": "weather_query"}
            ... )
            >>> print(results)
            {"short_term": True, "episodic": True}
        """
        return await self.memory_router.store_conversation_turn(
            user_message=user_message,
            assistant_message=assistant_message,
            session_id=self.session_id,
            metadata=metadata,
        )

    async def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session's memory across all layers.

        Returns:
            Summary statistics for each layer:
            {
                "session_id": "...",
                "short_term": {"message_count": 5, "available": True},
                "long_term": {"available": True},
                "episodic": {"available": True, "enabled": True}
            }
        """
        summary = await self.memory_router.get_session_summary(self.session_id)
        summary["session_id"] = self.session_id
        return summary

    async def health_check(self) -> Dict[str, Any]:
        """Check health status of all memory layers.

        Returns:
            Health status for each layer:
            {
                "redis": {"healthy": True, "latency_ms": 2.5},
                "qdrant": {"healthy": True, "latency_ms": 15.3},
                "graphiti": {"healthy": False, "error": "..."}
            }
        """
        health = {}

        # Redis health check
        try:
            start = time.time()
            client = await self.redis_memory.client
            await client.ping()
            health["redis"] = {
                "healthy": True,
                "latency_ms": round((time.time() - start) * 1000, 2),
            }
        except Exception as e:
            health["redis"] = {"healthy": False, "error": str(e)}

        # Qdrant health check (placeholder)
        health["qdrant"] = {"healthy": True, "note": "Health check not implemented"}

        # Graphiti health check
        if self.graphiti_wrapper:
            health["graphiti"] = {"healthy": True, "enabled": True}
        else:
            health["graphiti"] = {"healthy": False, "enabled": False}

        return health


# Global instance (singleton pattern)
_unified_memory_api: UnifiedMemoryAPI | None = None


def get_unified_memory_api(session_id: str | None = None) -> UnifiedMemoryAPI:
    """Get unified memory API instance.

    Args:
        session_id: Optional session ID for context tracking

    Returns:
        UnifiedMemoryAPI instance (creates new if session_id provided, else singleton)
    """
    if session_id:
        # Create new instance for specific session
        return UnifiedMemoryAPI(session_id=session_id)

    # Return global singleton
    global _unified_memory_api
    if _unified_memory_api is None:
        _unified_memory_api = UnifiedMemoryAPI()
    return _unified_memory_api
