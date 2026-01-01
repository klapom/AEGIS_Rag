"""Forgetting Mechanism for Episodic Memory.

Sprint 68 Feature 68.6: Memory-Write Policy + Forgetting

This module implements decay-based forgetting to prevent memory bloat:
1. Time-based decay: Exponential decay with configurable half-life
2. Importance-based filtering: Remove facts below effective importance threshold
3. Memory consolidation: Merge related/duplicate facts
4. Scheduled forgetting: Daily cron job for maintenance

Reference: Paper 2512.16301 (Tool-Level Adaptation)
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from src.core.exceptions import MemoryError

logger = structlog.get_logger(__name__)


class ForgettingMechanism:
    """Decay-based forgetting mechanism for episodic memory.

    Implements:
    - Exponential decay: score(t) = importance * 2^(-t/half_life)
    - Effective importance: Combines initial importance + time decay
    - Fact removal: Delete facts below effective importance threshold
    - Consolidation: Merge similar facts into higher-level concepts

    Example:
        forgetting = ForgettingMechanism()
        await forgetting.forget_stale_facts(min_age_days=30)
        await forgetting.consolidate_related_facts()
    """

    def __init__(
        self,
        graphiti_wrapper: Any | None = None,
        decay_half_life_days: int = 30,
        effective_importance_threshold: float = 0.3,
        consolidation_similarity_threshold: float = 0.9,
    ) -> None:
        """Initialize forgetting mechanism.

        Args:
            graphiti_wrapper: GraphitiClient instance (lazy import)
            decay_half_life_days: Half-life for time-based decay (default: 30)
            effective_importance_threshold: Min effective importance (default: 0.3)
            consolidation_similarity_threshold: Similarity for merging (default: 0.9)
        """
        # Lazy import to avoid circular dependency
        from src.components.memory.graphiti_wrapper import get_graphiti_client

        self.graphiti = graphiti_wrapper or get_graphiti_client()
        self.decay_half_life_days = decay_half_life_days
        self.effective_importance_threshold = effective_importance_threshold
        self.consolidation_similarity_threshold = consolidation_similarity_threshold

        logger.info(
            "Initialized ForgettingMechanism",
            decay_half_life_days=decay_half_life_days,
            effective_importance_threshold=effective_importance_threshold,
            consolidation_similarity_threshold=consolidation_similarity_threshold,
        )

    def compute_decay(
        self, created_at: datetime | str, reference_time: datetime | None = None
    ) -> float:
        """Compute time-based decay factor.

        Uses exponential decay: decay(t) = 2^(-t/half_life)

        Args:
            created_at: Fact creation timestamp
            reference_time: Reference time for decay calculation (default: now)

        Returns:
            Decay factor (0-1), where 1.0 = no decay
        """
        try:
            # Parse created_at
            if isinstance(created_at, str):
                created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                created_time = created_at

            # Calculate age
            ref_time = reference_time or datetime.now(UTC)
            age = ref_time - created_time
            age_days = age.total_seconds() / 86400  # Convert to days

            # Exponential decay
            decay = 2 ** (-age_days / self.decay_half_life_days)

            return max(0.0, min(1.0, decay))

        except Exception as e:
            logger.warning("Failed to compute decay", created_at=created_at, error=str(e))
            return 1.0  # No decay on error

    def compute_effective_importance(
        self, importance_score: float, created_at: datetime | str
    ) -> float:
        """Compute effective importance with time decay.

        Effective importance = importance_score * decay_factor

        Args:
            importance_score: Initial importance score (0-1)
            created_at: Fact creation timestamp

        Returns:
            Effective importance (0-1)
        """
        decay = self.compute_decay(created_at)
        effective_importance = importance_score * decay
        return max(0.0, min(1.0, effective_importance))

    def should_forget(self, fact: dict[str, Any]) -> bool:
        """Determine if fact should be forgotten.

        Args:
            fact: Fact with importance_score and created_at

        Returns:
            True if effective importance < threshold
        """
        metadata = fact.get("metadata", {})
        importance_score = metadata.get("importance_score", 1.0)  # Default: keep if missing
        created_at = fact.get("created_at")

        if not created_at:
            return False  # Keep if no timestamp

        effective_importance = self.compute_effective_importance(importance_score, created_at)

        return effective_importance < self.effective_importance_threshold

    async def forget_stale_facts(
        self, min_age_days: int = 1, batch_size: int = 1000
    ) -> dict[str, Any]:
        """Remove facts that have decayed below importance threshold.

        Args:
            min_age_days: Minimum age for forgetting (default: 1)
            batch_size: Max facts to process per run (default: 1000)

        Returns:
            Forgetting statistics

        Raises:
            MemoryError: If forgetting fails
        """
        try:
            cutoff_time = datetime.now(UTC) - timedelta(days=min_age_days)

            logger.info(
                "Starting stale fact forgetting",
                min_age_days=min_age_days,
                cutoff_time=cutoff_time.isoformat(),
                batch_size=batch_size,
            )

            # Query facts older than cutoff (placeholder)
            # TODO Sprint 69: Implement Neo4j query to fetch old episodes
            facts = await self._get_facts_older_than(cutoff_time, limit=batch_size)

            if not facts:
                logger.info("No stale facts to forget")
                return {"processed": 0, "removed": 0, "retained": 0}

            removed_facts = []
            retained_facts = []

            for fact in facts:
                if self.should_forget(fact):
                    # Remove from Neo4j
                    await self._remove_fact(fact["id"])
                    removed_facts.append(fact["id"])
                else:
                    retained_facts.append(fact["id"])

            logger.info(
                "Completed stale fact forgetting",
                processed=len(facts),
                removed=len(removed_facts),
                retained=len(retained_facts),
                removal_rate=round(len(removed_facts) / len(facts), 3) if facts else 0,
            )

            return {
                "processed": len(facts),
                "removed": len(removed_facts),
                "retained": len(retained_facts),
                "removed_fact_ids": removed_facts[:10],  # First 10 for logging
                "cutoff_time": cutoff_time.isoformat(),
            }

        except Exception as e:
            logger.error("Failed to forget stale facts", error=str(e))
            raise MemoryError(operation="forget_stale_facts", reason=str(e)) from e

    async def forget_by_importance(self, limit: int = 100) -> dict[str, Any]:
        """Remove N least important facts.

        Used when memory budget is exceeded.

        Args:
            limit: Number of facts to remove

        Returns:
            Removal statistics
        """
        try:
            logger.info("Removing least important facts", limit=limit)

            # Query facts sorted by effective importance (placeholder)
            facts = await self._get_least_important_facts(limit=limit)

            if not facts:
                logger.info("No facts to remove")
                return {"removed_count": 0, "avg_importance": 0}

            removed_ids = []
            importance_scores = []

            for fact in facts:
                await self._remove_fact(fact["id"])
                removed_ids.append(fact["id"])

                metadata = fact.get("metadata", {})
                importance = metadata.get("importance_score", 0)
                importance_scores.append(importance)

            avg_importance = sum(importance_scores) / len(importance_scores) if importance_scores else 0

            logger.info(
                "Removed least important facts",
                removed_count=len(removed_ids),
                avg_importance=round(avg_importance, 3),
            )

            return {
                "removed_count": len(removed_ids),
                "removed_fact_ids": removed_ids[:10],  # First 10
                "avg_importance": round(avg_importance, 3),
            }

        except Exception as e:
            logger.error("Failed to remove least important facts", error=str(e))
            raise MemoryError(operation="forget_by_importance", reason=str(e)) from e

    async def consolidate_related_facts(
        self, batch_size: int = 100
    ) -> dict[str, Any]:
        """Merge related facts into consolidated higher-level concepts.

        Finds fact clusters with high similarity and merges them into
        a single consolidated fact to reduce memory bloat.

        Args:
            batch_size: Max facts to process (default: 100)

        Returns:
            Consolidation statistics
        """
        try:
            logger.info(
                "Starting fact consolidation",
                batch_size=batch_size,
                similarity_threshold=self.consolidation_similarity_threshold,
            )

            # Find related fact clusters (placeholder)
            # TODO Sprint 69: Implement clustering via embeddings + cosine similarity
            fact_clusters = await self._find_related_fact_clusters(
                similarity_threshold=self.consolidation_similarity_threshold,
                limit=batch_size,
            )

            if not fact_clusters:
                logger.info("No related facts to consolidate")
                return {"processed": 0, "clusters": 0, "consolidated": 0, "removed": 0}

            consolidated_count = 0
            removed_count = 0

            for cluster in fact_clusters:
                if len(cluster) < 2:
                    continue  # Need at least 2 facts to consolidate

                # Merge facts into consolidated fact
                consolidated = await self._merge_facts(cluster)

                # Add consolidated fact
                await self.graphiti.add_episode(
                    content=consolidated["content"],
                    source="memory_consolidation",
                    metadata=consolidated["metadata"],
                )

                # Remove original facts
                for fact in cluster:
                    await self._remove_fact(fact["id"])
                    removed_count += 1

                consolidated_count += 1

            logger.info(
                "Completed fact consolidation",
                processed=sum(len(c) for c in fact_clusters),
                clusters=len(fact_clusters),
                consolidated=consolidated_count,
                removed=removed_count,
            )

            return {
                "processed": sum(len(c) for c in fact_clusters),
                "clusters": len(fact_clusters),
                "consolidated": consolidated_count,
                "removed": removed_count,
            }

        except Exception as e:
            logger.error("Failed to consolidate facts", error=str(e))
            raise MemoryError(operation="consolidate_related_facts", reason=str(e)) from e

    async def run_daily_maintenance(self) -> dict[str, Any]:
        """Run daily forgetting maintenance job.

        Performs:
        1. Forget stale facts (>30 days old, low importance)
        2. Consolidate related facts
        3. Report statistics

        Returns:
            Maintenance statistics
        """
        try:
            logger.info("Starting daily memory maintenance")

            results = {
                "started_at": datetime.now(UTC).isoformat(),
                "forgetting": None,
                "consolidation": None,
            }

            # 1. Forget stale facts
            try:
                results["forgetting"] = await self.forget_stale_facts(min_age_days=30)
            except Exception as e:
                logger.error("Forgetting failed in maintenance", error=str(e))
                results["forgetting"] = {"error": str(e)}

            # 2. Consolidate related facts
            try:
                results["consolidation"] = await self.consolidate_related_facts()
            except Exception as e:
                logger.error("Consolidation failed in maintenance", error=str(e))
                results["consolidation"] = {"error": str(e)}

            results["completed_at"] = datetime.now(UTC).isoformat()

            logger.info(
                "Completed daily memory maintenance",
                facts_removed=results.get("forgetting", {}).get("removed", 0),
                facts_consolidated=results.get("consolidation", {}).get("consolidated", 0),
            )

            return results

        except Exception as e:
            logger.error("Daily maintenance failed", error=str(e))
            raise MemoryError(operation="daily_maintenance", reason=str(e)) from e

    # =========================================================================
    # Helper Methods (Placeholders for Sprint 69 Neo4j Implementation)
    # =========================================================================

    async def _get_facts_older_than(
        self, cutoff_time: datetime, limit: int = 1000
    ) -> list[dict[str, Any]]:
        """Get facts older than cutoff time.

        TODO Sprint 69: Implement Neo4j query:
        MATCH (e:Episode)
        WHERE e.timestamp < $cutoff_timestamp
        RETURN e
        LIMIT $limit
        """
        # Placeholder: Return empty list
        logger.debug("_get_facts_older_than placeholder", cutoff_time=cutoff_time, limit=limit)
        return []

    async def _get_least_important_facts(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get N least important facts.

        TODO Sprint 69: Implement Neo4j query with effective importance calculation:
        MATCH (e:Episode)
        WHERE e.importance_score IS NOT NULL
        RETURN e ORDER BY e.importance_score ASC LIMIT $limit
        """
        # Placeholder: Return empty list
        logger.debug("_get_least_important_facts placeholder", limit=limit)
        return []

    async def _find_related_fact_clusters(
        self, similarity_threshold: float = 0.9, limit: int = 100
    ) -> list[list[dict[str, Any]]]:
        """Find clusters of related facts for consolidation.

        TODO Sprint 69: Implement clustering via embeddings + cosine similarity
        """
        # Placeholder: Return empty list
        logger.debug(
            "_find_related_fact_clusters placeholder",
            similarity_threshold=similarity_threshold,
            limit=limit,
        )
        return []

    async def _merge_facts(self, facts: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge multiple facts into consolidated fact.

        Combines content, aggregates metadata, and averages importance scores.
        """
        if not facts:
            raise ValueError("Cannot merge empty fact list")

        # Merge content
        contents = [f.get("content", "") for f in facts if f.get("content")]
        merged_content = " | ".join(contents)  # Simple concatenation

        # Aggregate metadata
        importance_scores = []
        created_times = []

        for fact in facts:
            metadata = fact.get("metadata", {})
            if "importance_score" in metadata:
                importance_scores.append(metadata["importance_score"])
            if "created_at" in fact:
                created_times.append(fact["created_at"])

        # Calculate consolidated metadata
        avg_importance = sum(importance_scores) / len(importance_scores) if importance_scores else 0.5
        earliest_time = min(created_times) if created_times else datetime.now(UTC).isoformat()

        consolidated = {
            "content": merged_content,
            "created_at": earliest_time,
            "metadata": {
                "importance_score": avg_importance,
                "consolidated_from": len(facts),
                "consolidated_at": datetime.now(UTC).isoformat(),
                "source_fact_ids": [f.get("id") for f in facts if f.get("id")],
            },
        }

        logger.debug(
            "Merged facts",
            fact_count=len(facts),
            avg_importance=round(avg_importance, 3),
            content_length=len(merged_content),
        )

        return consolidated

    async def _remove_fact(self, fact_id: str) -> None:
        """Remove fact from Neo4j.

        TODO Sprint 69: Implement Neo4j deletion:
        MATCH (e:Episode {id: $fact_id})
        DETACH DELETE e
        """
        logger.debug("_remove_fact placeholder", fact_id=fact_id)
        # Placeholder: No-op


# Global singleton instance
_forgetting_mechanism: ForgettingMechanism | None = None


def get_forgetting_mechanism() -> ForgettingMechanism:
    """Get global ForgettingMechanism instance (singleton).

    Returns:
        ForgettingMechanism instance with default configuration
    """
    global _forgetting_mechanism
    if _forgetting_mechanism is None:
        _forgetting_mechanism = ForgettingMechanism()
    return _forgetting_mechanism
