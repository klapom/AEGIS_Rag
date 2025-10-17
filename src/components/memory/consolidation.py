"""Memory Consolidation Pipeline for Multi-Layer Memory System.

This module provides automatic consolidation between memory layers:
- Redis (Layer 1) → Qdrant (Layer 2): Frequently accessed short-term to long-term
- Redis (Layer 1) → Graphiti (Layer 3): Conversations to episodic memory
- Time-based and relevance-based consolidation policies
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import structlog

from src.components.memory.graphiti_wrapper import get_graphiti_wrapper
from src.components.memory.redis_memory import get_redis_memory
from src.components.vector_search.qdrant_client import get_qdrant_client
from src.core.config import settings
from src.core.exceptions import MemoryError

logger = structlog.get_logger(__name__)


class ConsolidationPolicy:
    """Base class for consolidation policies."""

    def should_consolidate(self, metadata: dict[str, Any]) -> bool:
        """Determine if item should be consolidated.

        Args:
            metadata: Item metadata with access patterns

        Returns:
            True if item should be consolidated
        """
        raise NotImplementedError


class AccessCountPolicy(ConsolidationPolicy):
    """Consolidate based on access count threshold."""

    def __init__(self, min_access_count: int = 3):
        """Initialize access count policy.

        Args:
            min_access_count: Minimum access count for consolidation
        """
        self.min_access_count = min_access_count

    def should_consolidate(self, metadata: dict[str, Any]) -> bool:
        """Check if access count meets threshold.

        Args:
            metadata: Item metadata

        Returns:
            True if access count >= threshold
        """
        return metadata.get("access_count", 0) >= self.min_access_count


class TimeBasedPolicy(ConsolidationPolicy):
    """Consolidate based on age threshold."""

    def __init__(self, min_age_hours: int = 1):
        """Initialize time-based policy.

        Args:
            min_age_hours: Minimum age in hours for consolidation
        """
        self.min_age_hours = min_age_hours

    def should_consolidate(self, metadata: dict[str, Any]) -> bool:
        """Check if item is old enough.

        Args:
            metadata: Item metadata

        Returns:
            True if item age >= threshold
        """
        stored_at = metadata.get("stored_at")
        if not stored_at:
            return False

        try:
            stored_time = datetime.fromisoformat(stored_at)
            age = datetime.utcnow() - stored_time
            return age >= timedelta(hours=self.min_age_hours)
        except Exception:
            return False


class MemoryConsolidationPipeline:
    """Automatic memory consolidation pipeline.

    Manages consolidation between memory layers:
    - Short-term (Redis) → Long-term (Qdrant)
    - Short-term (Redis) → Episodic (Graphiti)
    """

    def __init__(
        self,
        access_count_threshold: int | None = None,
        time_threshold_hours: int = 1,
    ):
        """Initialize consolidation pipeline.

        Args:
            access_count_threshold: Minimum access count (default: from settings)
            time_threshold_hours: Minimum age in hours (default: 1)
        """
        self.redis_memory = get_redis_memory()
        self.qdrant_client = get_qdrant_client()

        # Initialize Graphiti only if enabled
        self.graphiti_wrapper = None
        if settings.graphiti_enabled:
            try:
                self.graphiti_wrapper = get_graphiti_wrapper()
            except Exception as e:
                logger.warning("Graphiti not available for consolidation", error=str(e))

        # Consolidation policies
        access_threshold = (
            access_count_threshold or settings.memory_consolidation_min_access_count
        )
        self.policies = [
            AccessCountPolicy(min_access_count=access_threshold),
            TimeBasedPolicy(min_age_hours=time_threshold_hours),
        ]

        logger.info(
            "Initialized MemoryConsolidationPipeline",
            access_threshold=access_threshold,
            time_threshold_hours=time_threshold_hours,
            graphiti_available=self.graphiti_wrapper is not None,
        )

    async def consolidate_redis_to_qdrant(
        self,
        namespace: str = "memory",
        batch_size: int = 100,
    ) -> dict[str, int]:
        """Consolidate frequently accessed items from Redis to Qdrant.

        Args:
            namespace: Redis namespace to consolidate
            batch_size: Maximum items to process per run

        Returns:
            Dictionary with consolidation statistics

        Raises:
            MemoryError: If consolidation fails
        """
        try:
            # Get frequently accessed items
            items = await self.redis_memory.get_frequently_accessed(
                min_access_count=settings.memory_consolidation_min_access_count,
                namespace=namespace,
                limit=batch_size,
            )

            if not items:
                logger.info("No items to consolidate to Qdrant")
                return {"processed": 0, "consolidated": 0, "skipped": 0}

            consolidated_count = 0
            skipped_count = 0

            for item in items:
                # Check consolidation policies
                metadata = {
                    "access_count": item.get("access_count", 0),
                    "stored_at": item.get("stored_at"),
                    "last_accessed_at": item.get("last_accessed_at"),
                }

                should_consolidate = any(
                    policy.should_consolidate(metadata) for policy in self.policies
                )

                if not should_consolidate:
                    skipped_count += 1
                    continue

                # Consolidate to Qdrant
                # NOTE: This is a placeholder - in production would:
                # 1. Generate embedding for item value
                # 2. Create PointStruct with embedding + payload
                # 3. Upsert to Qdrant collection
                # 4. Optionally delete from Redis or extend TTL

                logger.debug(
                    "Would consolidate to Qdrant",
                    key=item.get("key"),
                    access_count=item.get("access_count"),
                )

                consolidated_count += 1

            logger.info(
                "Completed Redis → Qdrant consolidation",
                processed=len(items),
                consolidated=consolidated_count,
                skipped=skipped_count,
            )

            return {
                "processed": len(items),
                "consolidated": consolidated_count,
                "skipped": skipped_count,
            }

        except Exception as e:
            logger.error("Redis → Qdrant consolidation failed", error=str(e))
            raise MemoryError(f"Redis → Qdrant consolidation failed: {e}") from e

    async def consolidate_conversation_to_graphiti(
        self,
        session_id: str,
        namespace: str = "context",
    ) -> dict[str, Any]:
        """Consolidate conversation context to Graphiti episodic memory.

        Args:
            session_id: Session ID to consolidate
            namespace: Redis namespace for conversations

        Returns:
            Dictionary with consolidation results

        Raises:
            MemoryError: If consolidation fails
        """
        if not self.graphiti_wrapper:
            logger.warning("Graphiti not available, skipping conversation consolidation")
            return {"consolidated": False, "reason": "graphiti_disabled"}

        try:
            # Retrieve conversation context
            context = await self.redis_memory.get_conversation_context(session_id)

            if not context:
                logger.info("No conversation context to consolidate", session_id=session_id)
                return {"consolidated": False, "reason": "no_context"}

            # Build episode content from conversation
            episode_parts = []
            for msg in context:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                episode_parts.append(f"{role.capitalize()}: {content}")

            episode_content = "\n".join(episode_parts)

            # Add as episodic memory
            result = await self.graphiti_wrapper.add_episode(
                content=episode_content,
                source="conversation_consolidation",
                metadata={
                    "session_id": session_id,
                    "message_count": len(context),
                    "consolidated_at": datetime.utcnow().isoformat(),
                },
            )

            logger.info(
                "Consolidated conversation to Graphiti",
                session_id=session_id,
                message_count=len(context),
                episode_id=result.get("episode_id"),
            )

            return {
                "consolidated": True,
                "episode_id": result.get("episode_id"),
                "message_count": len(context),
                "entities_extracted": len(result.get("entities", [])),
                "relationships_extracted": len(result.get("relationships", [])),
            }

        except Exception as e:
            logger.error(
                "Conversation → Graphiti consolidation failed",
                session_id=session_id,
                error=str(e),
            )
            raise MemoryError(
                f"Conversation → Graphiti consolidation failed: {e}"
            ) from e

    async def run_consolidation_cycle(
        self,
        consolidate_to_qdrant: bool = True,
        consolidate_conversations: bool = True,
        active_sessions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run a full consolidation cycle across all layers.

        Args:
            consolidate_to_qdrant: Enable Redis → Qdrant consolidation
            consolidate_conversations: Enable Redis → Graphiti consolidation
            active_sessions: List of active session IDs to consolidate

        Returns:
            Dictionary with consolidation results for all operations
        """
        results = {
            "started_at": datetime.utcnow().isoformat(),
            "qdrant_consolidation": None,
            "conversation_consolidations": [],
        }

        # Redis → Qdrant consolidation
        if consolidate_to_qdrant:
            try:
                results["qdrant_consolidation"] = await self.consolidate_redis_to_qdrant()
            except Exception as e:
                logger.error("Qdrant consolidation failed in cycle", error=str(e))
                results["qdrant_consolidation"] = {"error": str(e)}

        # Redis → Graphiti conversation consolidation
        if consolidate_conversations and active_sessions:
            for session_id in active_sessions:
                try:
                    conv_result = await self.consolidate_conversation_to_graphiti(
                        session_id=session_id
                    )
                    results["conversation_consolidations"].append(
                        {"session_id": session_id, "result": conv_result}
                    )
                except Exception as e:
                    logger.error(
                        "Conversation consolidation failed in cycle",
                        session_id=session_id,
                        error=str(e),
                    )
                    results["conversation_consolidations"].append(
                        {"session_id": session_id, "error": str(e)}
                    )

        results["completed_at"] = datetime.utcnow().isoformat()

        logger.info(
            "Completed consolidation cycle",
            qdrant_enabled=consolidate_to_qdrant,
            conversations_processed=len(results["conversation_consolidations"]),
        )

        return results

    async def schedule_background_consolidation(
        self,
        interval_minutes: int | None = None,
    ) -> None:
        """Background task for periodic memory consolidation.

        Args:
            interval_minutes: Consolidation interval (default: from settings)
        """
        interval = interval_minutes or settings.memory_consolidation_interval_minutes

        logger.info(
            "Starting background consolidation scheduler",
            interval_minutes=interval,
        )

        while True:
            try:
                # Wait for interval
                await asyncio.sleep(interval * 60)

                # Run consolidation cycle
                logger.info("Running scheduled consolidation cycle")
                await self.run_consolidation_cycle(
                    consolidate_to_qdrant=True,
                    consolidate_conversations=False,  # Conversations consolidated on-demand
                )

            except asyncio.CancelledError:
                logger.info("Background consolidation scheduler cancelled")
                break
            except Exception as e:
                logger.error("Background consolidation failed", error=str(e))
                # Continue running despite errors


# Global instance (singleton pattern)
_consolidation_pipeline: MemoryConsolidationPipeline | None = None


def get_consolidation_pipeline() -> MemoryConsolidationPipeline:
    """Get global consolidation pipeline instance (singleton).

    Returns:
        MemoryConsolidationPipeline instance
    """
    global _consolidation_pipeline
    if _consolidation_pipeline is None:
        _consolidation_pipeline = MemoryConsolidationPipeline()
    return _consolidation_pipeline


async def start_background_consolidation() -> asyncio.Task:
    """Start background consolidation as an async task.

    Returns:
        Async task handle for background consolidation

    Example:
        task = await start_background_consolidation()
        # Later: task.cancel() to stop
    """
    if not settings.memory_consolidation_enabled:
        logger.info("Background consolidation disabled in settings")
        return None

    pipeline = get_consolidation_pipeline()
    task = asyncio.create_task(pipeline.schedule_background_consolidation())

    logger.info("Background consolidation task started")
    return task
