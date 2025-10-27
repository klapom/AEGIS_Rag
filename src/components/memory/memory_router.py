"""Memory Router with 3-Layer Selection Logic.

This module implements intelligent memory routing across three layers:
- Layer 1 (SHORT_TERM): Redis working memory for recent context
- Layer 2 (LONG_TERM): Qdrant vector store for semantic facts
- Layer 3 (EPISODIC): Graphiti temporal graph for episodic memory
"""

import re
from enum import Enum
from typing import Any

import structlog

from src.components.memory.graphiti_wrapper import get_graphiti_wrapper
from src.components.memory.redis_memory import get_redis_memory
from src.components.vector_search.qdrant_client import get_qdrant_client
from src.core.config import settings

logger = structlog.get_logger(__name__)


class MemoryLayer(str, Enum):
    """Memory layer enumeration."""

    SHORT_TERM = "short_term"  # Redis: Recent context, session state
    LONG_TERM = "long_term"  # Qdrant: Semantic facts, document chunks
    EPISODIC = "episodic"  # Graphiti: Temporal events, entity relationships


class MemoryRouter:
    """Intelligent memory router with 3-layer selection logic.

    Routes queries to appropriate memory layers based on:
    - Temporal signals (recent vs. historical)
    - Query intent (factual vs. episodic vs. contextual)
    - Session awareness
    """

    def __init__(
        self,
        session_id: str | None = None,
    ):
        """Initialize memory router.

        Args:
            session_id: Optional session ID for context tracking
        """
        self.session_id = session_id
        self.redis_memory = get_redis_memory()
        self.qdrant_client = get_qdrant_client()

        # Initialize Graphiti only if enabled
        self.graphiti_wrapper = None
        if settings.graphiti_enabled:
            try:
                self.graphiti_wrapper = get_graphiti_wrapper()
            except Exception as e:
                logger.warning("Graphiti not available", error=str(e))

        logger.info(
            "Initialized MemoryRouter",
            session_id=session_id,
            graphiti_enabled=self.graphiti_wrapper is not None,
        )

    async def route_query(
        self,
        query: str,
        session_id: str | None = None,
    ) -> list[MemoryLayer]:
        """Determine which memory layers to query based on query analysis.

        Args:
            query: User query text
            session_id: Session ID (overrides instance session_id if provided)

        Returns:
            Ordered list of memory layers to search
        """
        session = session_id or self.session_id
        layers = []

        # Layer 1: Check for recent context needs
        if self._is_recent_context_query(query) and session:
            layers.append(MemoryLayer.SHORT_TERM)
            logger.debug("Selected SHORT_TERM layer", reason="recent_context_query")

        # Layer 3: Check for temporal/episodic needs
        if self._is_temporal_query(query) and self.graphiti_wrapper:
            layers.append(MemoryLayer.EPISODIC)
            logger.debug("Selected EPISODIC layer", reason="temporal_query")

        # Layer 2: Always include long-term for semantic search
        layers.append(MemoryLayer.LONG_TERM)
        logger.debug("Selected LONG_TERM layer", reason="semantic_search")

        logger.info(
            "Routed query to memory layers",
            query=query[:100],
            layers=[layer.value for layer in layers],
        )

        return layers

    def _is_recent_context_query(self, query: str) -> bool:
        """Detect if query requires recent conversation context.

        Args:
            query: Query text

        Returns:
            True if query needs recent context
        """
        # Patterns indicating recent context needs
        recent_patterns = [
            r"\b(just|earlier|previous|last|recent)\b",
            r"\b(we|our|my)\s+(discussed|talked|mentioned)\b",
            r"\bwhat\s+(did\s+)?[iI]\s+(say|ask|mention)\b",
            r"\bremember\s+(when|what|that)\b",
            r"\bcontext\b",
        ]

        for pattern in recent_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                logger.debug("Detected recent context pattern", pattern=pattern)
                return True

        return False

    def _is_temporal_query(self, query: str) -> bool:
        """Detect if query requires temporal/episodic memory.

        Args:
            query: Query text

        Returns:
            True if query needs temporal reasoning
        """
        # Patterns indicating temporal needs
        temporal_patterns = [
            r"\b(when|timeline|history|evolution|changed|became)\b",
            r"\b(before|after|during|while|since)\b",
            r"\b(first|last|initially|originally|currently)\b",
            r"\b(year|month|day|date|time)\b",
            r"\b(happened|occurred|started|ended)\b",
            r"\bhow\s+.+\s+(changed|evolved|developed)\b",
        ]

        for pattern in temporal_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                logger.debug("Detected temporal pattern", pattern=pattern)
                return True

        return False

    async def search_memory(
        self,
        query: str,
        session_id: str | None = None,
        limit: int = 10,
        time_window_hours: int | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Search across multiple memory layers.

        Args:
            query: Search query
            session_id: Session ID for context retrieval
            limit: Maximum results per layer
            time_window_hours: Limit temporal search to recent N hours

        Returns:
            Dictionary mapping layer names to search results

        Raises:
            MemoryError: If search fails
        """
        session = session_id or self.session_id
        layers = await self.route_query(query, session)

        results = {}

        # Search each selected layer
        for layer in layers:
            try:
                if layer == MemoryLayer.SHORT_TERM:
                    results["short_term"] = await self._search_short_term(query, session)

                elif layer == MemoryLayer.LONG_TERM:
                    results["long_term"] = await self._search_long_term(query, limit)

                elif layer == MemoryLayer.EPISODIC:
                    results["episodic"] = await self._search_episodic(
                        query, limit, time_window_hours
                    )

            except Exception as e:
                logger.error(
                    "Layer search failed",
                    layer=layer.value,
                    error=str(e),
                )
                # Continue with other layers on failure
                results[layer.value] = []

        logger.info(
            "Completed multi-layer memory search",
            query=query[:100],
            layers_searched=list(results.keys()),
            total_results=sum(len(r) for r in results.values()),
        )

        return results

    async def _search_short_term(
        self,
        query: str,
        session_id: str | None,
    ) -> list[dict[str, Any]]:
        """Search Redis working memory.

        Args:
            query: Search query
            session_id: Session ID

        Returns:
            List of results from short-term memory
        """
        if not session_id:
            return []

        try:
            # Retrieve conversation context
            context = await self.redis_memory.get_conversation_context(session_id)

            if not context:
                return []

            # Simple keyword matching (can be enhanced with semantic search)
            query_lower = query.lower()
            relevant_messages = [
                {
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "layer": "short_term",
                }
                for msg in context
                if query_lower in msg.get("content", "").lower()
            ]

            logger.debug(
                "Searched short-term memory",
                session_id=session_id,
                results_count=len(relevant_messages),
            )

            return relevant_messages

        except Exception as e:
            logger.error("Short-term search failed", error=str(e))
            return []

    async def _search_long_term(
        self,
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Search Qdrant vector store.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of results from long-term memory
        """
        try:
            # For this implementation, we assume embeddings are generated elsewhere
            # In production, would call embedding service here
            logger.info("Long-term search requires embedding service (placeholder)")

            # Placeholder - in real implementation:
            # 1. Generate query embedding
            # 2. Search Qdrant collection
            # 3. Return formatted results

            return []

        except Exception as e:
            logger.error("Long-term search failed", error=str(e))
            return []

    async def _search_episodic(
        self,
        query: str,
        limit: int,
        time_window_hours: int | None,
    ) -> list[dict[str, Any]]:
        """Search Graphiti episodic memory.

        Args:
            query: Search query
            limit: Maximum results
            time_window_hours: Time window for temporal filtering

        Returns:
            List of results from episodic memory
        """
        if not self.graphiti_wrapper:
            return []

        try:
            results = await self.graphiti_wrapper.search(
                query=query,
                limit=limit,
                time_window_hours=time_window_hours,
            )

            # Add layer tag
            for result in results:
                result["layer"] = "episodic"

            logger.debug(
                "Searched episodic memory",
                results_count=len(results),
            )

            return results

        except Exception as e:
            logger.error("Episodic search failed", error=str(e))
            return []

    async def store_conversation_turn(
        self,
        user_message: str,
        assistant_message: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, bool]:
        """Store a conversation turn across appropriate memory layers.

        Args:
            user_message: User message content
            assistant_message: Assistant response content
            session_id: Session ID for context tracking
            metadata: Additional metadata

        Returns:
            Dictionary indicating success for each layer
        """
        session = session_id or self.session_id
        metadata = metadata or {}
        results = {}

        # Layer 1: Store in Redis for immediate context
        if session:
            try:
                context = await self.redis_memory.get_conversation_context(session) or []
                context.extend(
                    [
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": assistant_message},
                    ]
                )

                results["short_term"] = await self.redis_memory.store_conversation_context(
                    session_id=session,
                    messages=context,
                )
            except Exception as e:
                logger.error("Failed to store in short-term memory", error=str(e))
                results["short_term"] = False

        # Layer 3: Store in Graphiti as episodic memory
        if self.graphiti_wrapper:
            try:
                episode_content = f"User: {user_message}\nAssistant: {assistant_message}"
                await self.graphiti_wrapper.add_episode(
                    content=episode_content,
                    source="conversation",
                    metadata={"session_id": session, **metadata},
                )
                results["episodic"] = True
            except Exception as e:
                logger.error("Failed to store in episodic memory", error=str(e))
                results["episodic"] = False

        logger.info(
            "Stored conversation turn",
            session_id=session,
            layers_stored=list(results.keys()),
        )

        return results

    async def get_session_summary(
        self,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Get summary of session memory across all layers.

        Args:
            session_id: Session ID

        Returns:
            Summary statistics for each memory layer
        """
        session = session_id or self.session_id
        if not session:
            return {}

        summary = {}

        # Short-term summary
        try:
            context = await self.redis_memory.get_conversation_context(session)
            summary["short_term"] = {
                "message_count": len(context) if context else 0,
                "available": context is not None,
            }
        except Exception as e:
            logger.error("Failed to get short-term summary", error=str(e))
            summary["short_term"] = {"message_count": 0, "available": False}

        # Long-term summary (placeholder)
        summary["long_term"] = {
            "available": True,
            "note": "Vector store access requires embedding service",
        }

        # Episodic summary
        if self.graphiti_wrapper:
            summary["episodic"] = {
                "available": True,
                "enabled": settings.graphiti_enabled,
            }
        else:
            summary["episodic"] = {"available": False, "enabled": False}

        logger.info("Generated session summary", session_id=session)

        return summary


# Global instance (singleton pattern for default session)
_memory_router: MemoryRouter | None = None


def get_memory_router(session_id: str | None = None) -> MemoryRouter:
    """Get memory router instance.

    Args:
        session_id: Optional session ID

    Returns:
        MemoryRouter instance
    """
    if session_id:
        # Create new instance for specific session
        return MemoryRouter(session_id=session_id)

    # Return global singleton for default session
    global _memory_router
    if _memory_router is None:
        _memory_router = MemoryRouter()
    return _memory_router
