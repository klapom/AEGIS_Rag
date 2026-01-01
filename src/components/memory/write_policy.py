"""Adaptive Memory-Write Policy for Episodic Memory.

Sprint 68 Feature 68.6: Memory-Write Policy + Forgetting

This module implements an adaptive write policy that:
1. Filters facts by importance score before writing
2. Enforces memory budget (max facts)
3. Triggers forgetting when budget is exceeded
4. Provides write statistics and monitoring

Reference: Paper 2512.16301 (Tool-Level Adaptation)
"""

from datetime import UTC, datetime
from typing import Any

import structlog

from src.components.memory.forgetting import ForgettingMechanism
from src.components.memory.importance_scorer import ImportanceScore, ImportanceScorer
from src.core.config import settings
from src.core.exceptions import MemoryError

logger = structlog.get_logger(__name__)


class MemoryWritePolicy:
    """Adaptive write policy for episodic memory.

    Enforces:
    - Importance threshold: Only write facts above threshold
    - Memory budget: Maximum number of facts in memory
    - Automatic forgetting: Remove low-importance facts when full

    Example:
        policy = MemoryWritePolicy(memory_budget=10000)
        fact = {"content": "...", "created_at": "..."}
        if await policy.should_write(fact):
            await policy.write_fact(fact)
    """

    def __init__(
        self,
        graphiti_wrapper: Any | None = None,
        importance_scorer: ImportanceScorer | None = None,
        forgetting_mechanism: ForgettingMechanism | None = None,
        memory_budget: int = 10000,
        importance_threshold: float | None = None,
    ) -> None:
        """Initialize memory write policy.

        Args:
            graphiti_wrapper: GraphitiClient instance (lazy import to avoid circular deps)
            importance_scorer: ImportanceScorer instance (default: global)
            forgetting_mechanism: ForgettingMechanism instance (default: create new)
            memory_budget: Maximum number of facts (default: 10000)
            importance_threshold: Override scorer's threshold (optional)
        """
        # Lazy import to avoid circular dependency
        from src.components.memory.graphiti_wrapper import get_graphiti_client
        from src.components.memory.importance_scorer import get_importance_scorer

        self.graphiti = graphiti_wrapper or get_graphiti_client()
        self.scorer = importance_scorer or get_importance_scorer()

        # Create forgetting mechanism
        if forgetting_mechanism is None:
            from src.components.memory.forgetting import ForgettingMechanism

            forgetting_mechanism = ForgettingMechanism(graphiti_wrapper=self.graphiti)

        self.forgetting = forgetting_mechanism
        self.memory_budget = memory_budget
        self.importance_threshold = importance_threshold or self.scorer.importance_threshold

        # Write statistics
        self.stats = {
            "total_attempted": 0,
            "rejected_low_importance": 0,
            "rejected_budget_exceeded": 0,
            "written": 0,
            "forgetting_triggered": 0,
        }

        logger.info(
            "Initialized MemoryWritePolicy",
            memory_budget=memory_budget,
            importance_threshold=self.importance_threshold,
        )

    async def should_write(
        self,
        fact: dict[str, Any],
        importance_score: ImportanceScore | None = None,
        domain_context: str | None = None,
    ) -> tuple[bool, str, ImportanceScore]:
        """Determine if fact should be written to memory.

        Args:
            fact: Fact to evaluate
            importance_score: Pre-computed score (optional)
            domain_context: User's domain for relevance scoring

        Returns:
            Tuple of (should_write, rejection_reason, importance_score)
        """
        self.stats["total_attempted"] += 1

        # Calculate importance score if not provided
        if importance_score is None:
            importance_score = await self.scorer.score_fact(fact, domain_context=domain_context)

        # Check importance threshold
        if importance_score.total_score < self.importance_threshold:
            self.stats["rejected_low_importance"] += 1
            logger.debug(
                "Fact rejected: low importance",
                score=round(importance_score.total_score, 3),
                threshold=self.importance_threshold,
                content_preview=fact.get("content", "")[:50],
            )
            return (
                False,
                f"importance_score={importance_score.total_score:.3f} < threshold={self.importance_threshold}",
                importance_score,
            )

        # Check memory budget
        if await self._is_memory_full():
            self.stats["rejected_budget_exceeded"] += 1
            logger.info(
                "Memory budget exceeded, will trigger forgetting",
                current_count=await self._get_fact_count(),
                budget=self.memory_budget,
            )
            # Don't reject, but mark for forgetting
            return (
                True,
                "budget_exceeded_forgetting_triggered",
                importance_score,
            )

        return True, "accepted", importance_score

    async def write_fact(
        self,
        fact: dict[str, Any],
        importance_score: ImportanceScore | None = None,
        domain_context: str | None = None,
    ) -> dict[str, Any]:
        """Write fact to memory with importance filtering.

        Args:
            fact: Fact to write
            importance_score: Pre-computed score (optional)
            domain_context: User's domain for relevance

        Returns:
            Write result with fact_id, importance_score, and status

        Raises:
            MemoryError: If write fails
        """
        try:
            # Check if should write
            should_write, reason, score = await self.should_write(
                fact, importance_score, domain_context
            )

            if not should_write:
                logger.info(
                    "Fact rejected by write policy",
                    reason=reason,
                    score=round(score.total_score, 3),
                )
                return {
                    "written": False,
                    "reason": reason,
                    "importance_score": score.total_score,
                    "score_breakdown": score.breakdown,
                }

            # Check if forgetting needed
            if "budget_exceeded" in reason:
                logger.info("Triggering forgetting before write")
                await self._forget_least_important()
                self.stats["forgetting_triggered"] += 1

            # Add importance score to metadata
            fact_metadata = fact.get("metadata", {})
            fact_metadata["importance_score"] = score.total_score
            fact_metadata["importance_breakdown"] = score.breakdown
            fact["metadata"] = fact_metadata

            # Write to Graphiti
            result = await self.graphiti.add_episode(
                content=fact.get("content", ""),
                source=fact.get("source", "memory_write_policy"),
                metadata=fact_metadata,
                timestamp=fact.get("created_at"),
            )

            self.stats["written"] += 1

            logger.info(
                "Fact written to memory",
                episode_id=result.get("episode_id"),
                importance_score=round(score.total_score, 3),
                entities_count=len(result.get("entities", [])),
                relationships_count=len(result.get("relationships", [])),
            )

            return {
                "written": True,
                "episode_id": result.get("episode_id"),
                "importance_score": score.total_score,
                "score_breakdown": score.breakdown,
                "entities_extracted": len(result.get("entities", [])),
                "relationships_extracted": len(result.get("relationships", [])),
            }

        except Exception as e:
            logger.error("Failed to write fact", error=str(e))
            raise MemoryError(operation="write_fact", reason=str(e)) from e

    async def batch_write_facts(
        self,
        facts: list[dict[str, Any]],
        domain_context: str | None = None,
    ) -> dict[str, Any]:
        """Write multiple facts in batch with importance filtering.

        Args:
            facts: List of facts to write
            domain_context: User's domain for relevance

        Returns:
            Batch write statistics
        """
        results = {
            "total_facts": len(facts),
            "written": 0,
            "rejected": 0,
            "written_fact_ids": [],
            "rejected_reasons": [],
        }

        # Score all facts first
        scored_facts = await self.scorer.batch_score_facts(facts, domain_context)

        # Sort by importance (write most important first)
        scored_facts.sort(key=lambda x: x[1].total_score, reverse=True)

        for fact, score in scored_facts:
            result = await self.write_fact(fact, importance_score=score, domain_context=domain_context)

            if result["written"]:
                results["written"] += 1
                results["written_fact_ids"].append(result["episode_id"])
            else:
                results["rejected"] += 1
                results["rejected_reasons"].append(
                    {
                        "content_preview": fact.get("content", "")[:50],
                        "reason": result["reason"],
                        "score": result["importance_score"],
                    }
                )

        logger.info(
            "Batch write completed",
            total=results["total_facts"],
            written=results["written"],
            rejected=results["rejected"],
            write_rate=round(results["written"] / results["total_facts"], 3)
            if results["total_facts"] > 0
            else 0,
        )

        return results

    async def _is_memory_full(self) -> bool:
        """Check if memory budget is exceeded.

        Returns:
            True if fact count >= memory_budget
        """
        current_count = await self._get_fact_count()
        return current_count >= self.memory_budget

    async def _get_fact_count(self) -> int:
        """Get current number of facts in memory.

        Returns:
            Current fact count

        Note: This is a placeholder implementation.
        TODO Sprint 69: Implement actual fact counting via Graphiti/Neo4j query.
        """
        # Placeholder: Query Neo4j for episode count
        # In production, would run Cypher query: MATCH (e:Episode) RETURN count(e)
        try:
            # Access Neo4j client through Graphiti wrapper
            neo4j_client = self.graphiti.neo4j_client
            query = "MATCH (e:Episode) RETURN count(e) as count"

            result = await neo4j_client.execute_query(query)
            if result and len(result) > 0:
                return result[0].get("count", 0)  # type: ignore[return-value]

            return 0

        except Exception as e:
            logger.warning("Failed to get fact count, assuming 0", error=str(e))
            return 0

    async def _forget_least_important(self, forget_count: int = 100) -> None:
        """Remove least important facts to free up memory.

        Args:
            forget_count: Number of facts to remove (default: 100)
        """
        try:
            logger.info("Forgetting least important facts", forget_count=forget_count)

            # Use forgetting mechanism to remove low-importance facts
            results = await self.forgetting.forget_by_importance(limit=forget_count)

            logger.info(
                "Forgot least important facts",
                removed_count=results.get("removed_count", 0),
                avg_importance=results.get("avg_importance", 0),
            )

        except Exception as e:
            logger.error("Failed to forget least important facts", error=str(e))
            # Don't raise - allow write to continue even if forgetting fails

    def get_statistics(self) -> dict[str, Any]:
        """Get write policy statistics.

        Returns:
            Statistics dictionary with write/reject counts
        """
        total = self.stats["total_attempted"]
        if total == 0:
            return {**self.stats, "write_rate": 0.0, "rejection_rate": 0.0}

        write_rate = self.stats["written"] / total
        rejection_rate = (
            self.stats["rejected_low_importance"] + self.stats["rejected_budget_exceeded"]
        ) / total

        return {
            **self.stats,
            "write_rate": round(write_rate, 3),
            "rejection_rate": round(rejection_rate, 3),
            "importance_threshold": self.importance_threshold,
            "memory_budget": self.memory_budget,
            "last_updated": datetime.now(UTC).isoformat(),
        }

    def reset_statistics(self) -> None:
        """Reset write statistics."""
        self.stats = {
            "total_attempted": 0,
            "rejected_low_importance": 0,
            "rejected_budget_exceeded": 0,
            "written": 0,
            "forgetting_triggered": 0,
        }
        logger.info("Reset write policy statistics")


# Global singleton instance
_write_policy: MemoryWritePolicy | None = None


def get_write_policy() -> MemoryWritePolicy:
    """Get global MemoryWritePolicy instance (singleton).

    Returns:
        MemoryWritePolicy instance with default configuration
    """
    global _write_policy
    if _write_policy is None:
        _write_policy = MemoryWritePolicy()
    return _write_policy
