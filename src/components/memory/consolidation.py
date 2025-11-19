"""Memory Consolidation Pipeline for Multi-Layer Memory System.

This module provides automatic consolidation between memory layers:
- Redis (Layer 1) → Qdrant (Layer 2): Frequently accessed short-term to long-term
- Redis (Layer 1) → Graphiti (Layer 3): Conversations to episodic memory
- Time-based and relevance-based consolidation policies
- Deduplication and importance-based selection
- APScheduler support for cron-based scheduling
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.components.memory.graphiti_wrapper import get_graphiti_wrapper
from src.components.memory.redis_memory import get_redis_memory
from src.components.memory.relevance_scorer import RelevanceScorer, get_relevance_scorer
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

    def __init__(self, min_access_count: int = 3) -> None:
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
        return metadata.get("access_count", 0) >= self.min_access_count  # type: ignore[no-any-return]


class TimeBasedPolicy(ConsolidationPolicy):
    """Consolidate based on age threshold."""

    def __init__(self, min_age_hours: int = 1) -> None:
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
            age = datetime.now(UTC) - stored_time
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
        relevance_scorer: RelevanceScorer | None = None,
        deduplication_threshold: float = 0.95,
    ) -> None:
        """Initialize consolidation pipeline.

        Args:
            access_count_threshold: Minimum access count (default: from settings)
            time_threshold_hours: Minimum age in hours (default: 1)
            relevance_scorer: Custom relevance scorer (default: standard scorer)
            deduplication_threshold: Cosine similarity threshold for duplicates (0.95)
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
        access_threshold = access_count_threshold or settings.memory_consolidation_min_access_count
        self.policies = [
            AccessCountPolicy(min_access_count=access_threshold),
            TimeBasedPolicy(min_age_hours=time_threshold_hours),
        ]

        # Relevance scorer for importance calculation
        self.relevance_scorer = relevance_scorer or get_relevance_scorer()
        self.deduplication_threshold = deduplication_threshold

        # APScheduler for cron-based scheduling
        self.scheduler = AsyncIOScheduler()

        logger.info(
            "Initialized MemoryConsolidationPipeline",
            access_threshold=access_threshold,
            time_threshold_hours=time_threshold_hours,
            deduplication_threshold=deduplication_threshold,
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
            raise MemoryError(operation="Redis → Qdrant consolidation failed", reason=str(e)) from e

    def _calculate_cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0-1)
        """
        if not vec1 or not vec2:
            return 0.0

        arr1 = np.array(vec1)
        arr2 = np.array(vec2)

        # Normalize
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Cosine similarity
        similarity = np.dot(arr1, arr2) / (norm1 * norm2)

        return float(similarity)

    async def _deduplicate_memories(
        self,
        items: list[dict[str, Any]],
        embeddings: list[list[float]] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Deduplicate memories based on embedding similarity.

        Args:
            items: list of memory items
            embeddings: Precomputed embeddings (optional)

        Returns:
            Tuple of (unique_items, duplicates_removed_count)
        """
        if not items:
            return [], 0

        if len(items) == 1:
            return items, 0

        # If no embeddings provided, we can't deduplicate (placeholder)
        if not embeddings:
            logger.warning("No embeddings provided for deduplication, skipping")
            return items, 0

        if len(embeddings) != len(items):
            logger.warning(
                "Embedding count mismatch, skipping deduplication",
                items=len(items),
                embeddings=len(embeddings),
            )
            return items, 0

        unique_items = []
        unique_embeddings = []
        duplicates_removed = 0

        for _i, (item, embedding) in enumerate(zip(items, embeddings, strict=False)):
            is_duplicate = False

            # Check against all previously added unique items
            for j, unique_emb in enumerate(unique_embeddings):
                similarity = self._calculate_cosine_similarity(embedding, unique_emb)

                if similarity >= self.deduplication_threshold:
                    is_duplicate = True
                    duplicates_removed += 1
                    logger.debug(
                        "Duplicate detected",
                        item_key=item.get("key"),
                        similar_to=unique_items[j].get("key"),
                        similarity=round(similarity, 3),
                    )
                    break

            if not is_duplicate:
                unique_items.append(item)
                unique_embeddings.append(embedding)

        logger.info(
            "Deduplication complete",
            original_count=len(items),
            unique_count=len(unique_items),
            duplicates_removed=duplicates_removed,
            deduplication_rate=round(duplicates_removed / len(items), 3) if len(items) > 0 else 0,
        )

        return unique_items, duplicates_removed

    async def consolidate_with_relevance_scoring(
        self,
        namespace: str = "memory",
        batch_size: int = 100,
        top_percentile: float = 0.2,
    ) -> dict[str, Any]:
        """Enhanced consolidation with relevance scoring and deduplication.

        Selects top N% of memories based on importance score.

        Args:
            namespace: Redis namespace to consolidate
            batch_size: Maximum items to process
            top_percentile: Top percentage to migrate (0.2 = top 20%)

        Returns:
            Consolidation statistics including relevance scores

        Raises:
            MemoryError: If consolidation fails
        """
        try:
            # Get all candidate items
            items = await self.redis_memory.get_frequently_accessed(
                min_access_count=1,  # Get all items, we'll filter by score
                namespace=namespace,
                limit=batch_size,
            )

            if not items:
                logger.info("No items to consolidate")
                return {
                    "processed": 0,
                    "scored": 0,
                    "top_selected": 0,
                    "deduplicated": 0,
                    "consolidated": 0,
                }

            # Calculate relevance scores for each item
            scored_items = []
            for item in items:
                try:
                    metadata = {
                        "access_count": item.get("access_count", 0),
                        "stored_at": item.get("stored_at"),
                        "user_rating": item.get("user_rating"),
                    }

                    score = self.relevance_scorer.calculate_score_from_metadata(metadata)
                    scored_items.append(
                        {
                            **item,
                            "relevance_score": score.total_score,
                            "score_breakdown": {
                                "frequency": score.frequency_score,
                                "recency": score.recency_score,
                                "user_feedback": score.user_feedback,
                            },
                        }
                    )
                except Exception as e:
                    logger.warning("Failed to score item", key=item.get("key"), error=str(e))
                    continue

            if not scored_items:
                return {
                    "processed": len(items),
                    "scored": 0,
                    "top_selected": 0,
                    "deduplicated": 0,
                    "consolidated": 0,
                }

            # Sort by relevance score (descending)
            scored_items.sort(key=lambda x: x["relevance_score"], reverse=True)

            # Select top N%
            top_count = max(1, int(len(scored_items) * top_percentile))
            top_items = scored_items[:top_count]

            logger.info(
                "Selected top memories by relevance",
                total_items=len(scored_items),
                top_count=top_count,
                min_score=round(top_items[-1]["relevance_score"], 3),
                max_score=round(top_items[0]["relevance_score"], 3),
            )

            # Deduplicate (placeholder - would need actual embeddings)
            # In production, would generate embeddings here
            unique_items, duplicates_removed = await self._deduplicate_memories(
                top_items, embeddings=None
            )

            # TODO: Migrate unique items to Qdrant/Graphiti
            # For now, just count them
            consolidated_count = len(unique_items)

            return {
                "processed": len(items),
                "scored": len(scored_items),
                "top_selected": top_count,
                "deduplicated": duplicates_removed,
                "consolidated": consolidated_count,
                "avg_relevance_score": (
                    round(
                        sum(item["relevance_score"] for item in unique_items) / len(unique_items),
                        3,
                    )
                    if unique_items
                    else 0
                ),
            }

        except Exception as e:
            logger.error("Relevance-based consolidation failed", error=str(e))
            raise MemoryError(
                operation="Relevance-based consolidation failed", reason=str(e)
            ) from e

    def start_cron_scheduler(self, cron_schedule: str = "0 2 * * *") -> None:
        """Start cron-based consolidation scheduler using APScheduler.

        Args:
            cron_schedule: Cron schedule string (default: daily at 2 AM)
                Format: "minute hour day month day_of_week"
                Examples:
                    - "0 2 * * *" : Daily at 2 AM
                    - "0 */6 * * *" : Every 6 hours
                    - "0 0 * * 0" : Weekly on Sunday at midnight
        """
        if self.scheduler.running:
            logger.warning("Scheduler already running")
            return

        # Parse cron schedule
        parts = cron_schedule.split()
        if len(parts) != 5:
            raise ValueError(
                f"Invalid cron schedule: {cron_schedule}. "
                "Must have 5 parts: minute hour day month day_of_week"
            )

        minute, hour, day, month, day_of_week = parts

        # Add job with cron trigger
        self.scheduler.add_job(
            func=self._run_consolidation_sync_wrapper,
            trigger="cron",
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            id="memory_consolidation",
            replace_existing=True,
        )

        self.scheduler.start()

        logger.info(
            "Started cron-based consolidation scheduler",
            schedule=cron_schedule,
        )

    def _run_consolidation_sync_wrapper(self) -> None:
        """Sync wrapper for async consolidation (used by APScheduler)."""
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.consolidate_with_relevance_scoring())
        except Exception as e:
            logger.error("Scheduled consolidation failed", error=str(e))

    def stop_scheduler(self) -> None:
        """Stop the consolidation scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Stopped consolidation scheduler")

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
                    "consolidated_at": datetime.now(UTC).isoformat(),
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
                operation="Conversation → Graphiti consolidation failed", reason=str(e)
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
            active_sessions: list of active session IDs to consolidate

        Returns:
            Dictionary with consolidation results for all operations
        """
        results = {
            "started_at": datetime.now(UTC).isoformat(),
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

        results["completed_at"] = datetime.now(UTC).isoformat()

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
