"""Skill Activation Metrics and Analytics.

Sprint Context:
    - Sprint 91 (2026-01-14): Feature 91.4 - Skill Activation Metrics (5 SP)

Tracks and analyzes skill activation patterns:
- Per-skill activation counts
- Context usage per skill
- Activation latency
- Token savings vs always-on baseline

Metrics provide insights for:
- Optimization opportunities (which skills are underused?)
- Performance tuning (which skills are slow?)
- Cost reduction (token savings from selective activation)

Architecture:
    Skill Activation → Record Metrics → Aggregated Statistics → Analytics

Based on: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

Example:
    >>> from src.agents.routing.metrics import SkillMetricsCollector
    >>> collector = SkillMetricsCollector()
    >>>
    >>> # Record activation
    >>> collector.record_activation(
    ...     skill_name="retrieval",
    ...     context_used=800,
    ...     duration_ms=45.2
    ... )
    >>>
    >>> # Get statistics
    >>> stats = collector.get_usage_stats()
    >>> stats["retrieval"]["activation_count"]
    142
    >>> stats["retrieval"]["avg_context_tokens"]
    785
    >>>
    >>> # Calculate token savings
    >>> savings = collector.get_context_efficiency()
    >>> savings["total_tokens_saved"]
    124800  # vs always-on baseline
    >>> savings["savings_percentage"]
    31.2
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SkillActivationMetric:
    """Single skill activation record.

    Attributes:
        skill_name: Skill identifier
        timestamp: Unix timestamp (seconds)
        context_used: Tokens consumed by skill instructions
        duration_ms: Activation latency in milliseconds

    Example:
        >>> metric = SkillActivationMetric(
        ...     skill_name="retrieval",
        ...     timestamp=1705234567.89,
        ...     context_used=800,
        ...     duration_ms=45.2
        ... )
    """

    skill_name: str
    timestamp: float
    context_used: int  # Tokens
    duration_ms: float


@dataclass
class SkillUsageStats:
    """Aggregated usage statistics for a skill.

    Attributes:
        skill_name: Skill identifier
        activation_count: Total number of activations
        total_context_tokens: Sum of all context tokens used
        avg_context_tokens: Average tokens per activation
        total_duration_ms: Sum of all activation durations
        avg_duration_ms: Average duration per activation
        min_duration_ms: Fastest activation
        max_duration_ms: Slowest activation

    Example:
        >>> stats = SkillUsageStats(
        ...     skill_name="retrieval",
        ...     activation_count=142,
        ...     total_context_tokens=111570,
        ...     avg_context_tokens=785,
        ...     total_duration_ms=6428.4,
        ...     avg_duration_ms=45.3,
        ...     min_duration_ms=32.1,
        ...     max_duration_ms=89.7
        ... )
    """

    skill_name: str
    activation_count: int = 0
    total_context_tokens: int = 0
    avg_context_tokens: float = 0.0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    max_duration_ms: float = 0.0


class SkillMetricsCollector:
    """Collect and analyze skill activation metrics.

    Tracks:
    - Activation frequency per skill
    - Context usage per skill (token efficiency)
    - Activation latency (performance)
    - Token savings vs always-on baseline

    Attributes:
        _metrics: List of recorded activation metrics
        _always_on_baseline: Assumed context tokens if all skills always active
        _max_metrics: Maximum metrics to keep (LRU)

    Example:
        >>> collector = SkillMetricsCollector()
        >>> collector.record_activation("retrieval", 800, 45.2)
        >>> collector.record_activation("reflection", 1200, 67.8)
        >>> stats = collector.get_usage_stats()
    """

    def __init__(
        self,
        always_on_baseline: int = 10000,
        max_metrics: int = 10000,
    ):
        """Initialize metrics collector.

        Args:
            always_on_baseline: Assumed tokens if all skills always active
            max_metrics: Maximum metrics to keep in memory (oldest evicted)
        """
        self._metrics: List[SkillActivationMetric] = []
        self._always_on_baseline = always_on_baseline
        self._max_metrics = max_metrics

        logger.info(
            "skill_metrics_collector_initialized",
            always_on_baseline=always_on_baseline,
            max_metrics=max_metrics,
        )

    def record_activation(
        self,
        skill_name: str,
        context_used: int,
        duration_ms: float,
    ) -> None:
        """Record a skill activation.

        Args:
            skill_name: Skill identifier
            context_used: Tokens consumed by skill instructions
            duration_ms: Activation latency in milliseconds

        Example:
            >>> collector = SkillMetricsCollector()
            >>> collector.record_activation("retrieval", 800, 45.2)
            >>> collector.record_activation("reflection", 1200, 67.8)
        """
        metric = SkillActivationMetric(
            skill_name=skill_name,
            timestamp=time.time(),
            context_used=context_used,
            duration_ms=duration_ms,
        )

        self._metrics.append(metric)

        # Evict oldest metrics if limit exceeded (LRU)
        if len(self._metrics) > self._max_metrics:
            self._metrics = self._metrics[-self._max_metrics :]
            logger.debug(
                "metrics_evicted",
                evicted_count=len(self._metrics) - self._max_metrics,
                remaining=len(self._metrics),
            )

        logger.debug(
            "activation_recorded",
            skill=skill_name,
            context_tokens=context_used,
            duration_ms=round(duration_ms, 2),
            total_metrics=len(self._metrics),
        )

    def get_usage_stats(
        self,
        skill_name: Optional[str] = None,
    ) -> Dict[str, SkillUsageStats]:
        """Get aggregated usage statistics.

        Args:
            skill_name: Optional skill to filter by (None = all skills)

        Returns:
            Dict mapping skill names to SkillUsageStats

        Example:
            >>> collector = SkillMetricsCollector()
            >>> # ... record activations ...
            >>> stats = collector.get_usage_stats()
            >>> stats["retrieval"].activation_count
            142
            >>> stats["retrieval"].avg_context_tokens
            785
            >>>
            >>> # Get stats for specific skill
            >>> retrieval_stats = collector.get_usage_stats("retrieval")
        """
        # Filter metrics
        if skill_name:
            metrics = [m for m in self._metrics if m.skill_name == skill_name]
        else:
            metrics = self._metrics

        # Aggregate by skill
        stats_dict: Dict[str, SkillUsageStats] = defaultdict(lambda: SkillUsageStats(skill_name=""))

        for metric in metrics:
            stats = stats_dict[metric.skill_name]
            if not stats.skill_name:
                stats.skill_name = metric.skill_name

            stats.activation_count += 1
            stats.total_context_tokens += metric.context_used
            stats.total_duration_ms += metric.duration_ms
            stats.min_duration_ms = min(stats.min_duration_ms, metric.duration_ms)
            stats.max_duration_ms = max(stats.max_duration_ms, metric.duration_ms)

        # Calculate averages
        for skill, stats in stats_dict.items():
            if stats.activation_count > 0:
                stats.avg_context_tokens = stats.total_context_tokens / stats.activation_count
                stats.avg_duration_ms = stats.total_duration_ms / stats.activation_count

        logger.debug(
            "usage_stats_calculated",
            skill_filter=skill_name,
            skills_count=len(stats_dict),
            total_activations=sum(s.activation_count for s in stats_dict.values()),
        )

        return dict(stats_dict)

    def get_context_efficiency(self) -> Dict[str, float | int]:
        """Calculate token savings vs always-on baseline.

        Compares actual token usage (selective activation) with
        assumed baseline (all skills always active).

        Returns:
            Dict with:
            - total_tokens_used: Actual tokens used
            - baseline_tokens: Tokens if always-on
            - total_tokens_saved: Difference
            - savings_percentage: Savings as percentage
            - activations_count: Total activations

        Example:
            >>> collector = SkillMetricsCollector(always_on_baseline=10000)
            >>> # ... record activations ...
            >>> efficiency = collector.get_context_efficiency()
            >>> efficiency
            {
                'total_tokens_used': 275200,
                'baseline_tokens': 400000,
                'total_tokens_saved': 124800,
                'savings_percentage': 31.2,
                'activations_count': 40
            }
        """
        if not self._metrics:
            return {
                "total_tokens_used": 0,
                "baseline_tokens": 0,
                "total_tokens_saved": 0,
                "savings_percentage": 0.0,
                "activations_count": 0,
            }

        # Calculate actual token usage
        total_tokens_used = sum(m.context_used for m in self._metrics)

        # Calculate baseline (all skills always active for each query)
        activations_count = len(self._metrics)
        baseline_tokens = self._always_on_baseline * activations_count

        # Calculate savings
        total_tokens_saved = baseline_tokens - total_tokens_used
        savings_percentage = (
            (total_tokens_saved / baseline_tokens) * 100 if baseline_tokens > 0 else 0.0
        )

        result = {
            "total_tokens_used": total_tokens_used,
            "baseline_tokens": baseline_tokens,
            "total_tokens_saved": total_tokens_saved,
            "savings_percentage": round(savings_percentage, 2),
            "activations_count": activations_count,
        }

        logger.info(
            "context_efficiency_calculated",
            **result,
        )

        return result

    def get_performance_summary(self) -> Dict[str, float | int]:
        """Get overall performance summary.

        Returns:
            Dict with:
            - total_activations: Total skill activations
            - unique_skills: Number of unique skills activated
            - avg_context_per_activation: Average tokens per activation
            - avg_duration_per_activation: Average latency per activation
            - total_context_tokens: Sum of all context tokens
            - token_savings_pct: Token savings percentage

        Example:
            >>> collector = SkillMetricsCollector()
            >>> # ... record activations ...
            >>> summary = collector.get_performance_summary()
            >>> summary
            {
                'total_activations': 142,
                'unique_skills': 5,
                'avg_context_per_activation': 785.2,
                'avg_duration_per_activation': 52.3,
                'total_context_tokens': 111570,
                'token_savings_pct': 31.2
            }
        """
        if not self._metrics:
            return {
                "total_activations": 0,
                "unique_skills": 0,
                "avg_context_per_activation": 0.0,
                "avg_duration_per_activation": 0.0,
                "total_context_tokens": 0,
                "token_savings_pct": 0.0,
            }

        total_activations = len(self._metrics)
        unique_skills = len(set(m.skill_name for m in self._metrics))
        total_context = sum(m.context_used for m in self._metrics)
        total_duration = sum(m.duration_ms for m in self._metrics)

        avg_context = total_context / total_activations
        avg_duration = total_duration / total_activations

        efficiency = self.get_context_efficiency()
        token_savings_pct = efficiency["savings_percentage"]

        summary = {
            "total_activations": total_activations,
            "unique_skills": unique_skills,
            "avg_context_per_activation": round(avg_context, 2),
            "avg_duration_per_activation": round(avg_duration, 2),
            "total_context_tokens": total_context,
            "token_savings_pct": token_savings_pct,
        }

        logger.info("performance_summary_generated", **summary)

        return summary

    def clear_metrics(self) -> None:
        """Clear all recorded metrics.

        Example:
            >>> collector = SkillMetricsCollector()
            >>> # ... record activations ...
            >>> collector.clear_metrics()
            >>> len(collector._metrics)
            0
        """
        metrics_count = len(self._metrics)
        self._metrics = []

        logger.info("metrics_cleared", cleared_count=metrics_count)

    def export_metrics(self) -> List[Dict]:
        """Export metrics as list of dicts (for JSON serialization).

        Returns:
            List of metric dicts

        Example:
            >>> collector = SkillMetricsCollector()
            >>> # ... record activations ...
            >>> metrics = collector.export_metrics()
            >>> metrics[0]
            {
                'skill_name': 'retrieval',
                'timestamp': 1705234567.89,
                'context_used': 800,
                'duration_ms': 45.2
            }
        """
        return [
            {
                "skill_name": m.skill_name,
                "timestamp": m.timestamp,
                "context_used": m.context_used,
                "duration_ms": m.duration_ms,
            }
            for m in self._metrics
        ]


# Global collector instance
_metrics_collector: Optional["SkillMetricsCollector"] = None


def get_metrics_collector() -> SkillMetricsCollector:
    """Get or create the global metrics collector.

    Returns singleton instance for centralized metrics collection.

    Returns:
        Global SkillMetricsCollector instance

    Example:
        >>> from src.agents.routing.metrics import get_metrics_collector
        >>> collector = get_metrics_collector()
        >>> collector.record_activation("retrieval", 800, 45.2)
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = SkillMetricsCollector()
        logger.info("global_metrics_collector_initialized")
    return _metrics_collector
