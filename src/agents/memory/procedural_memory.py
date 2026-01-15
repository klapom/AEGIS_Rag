"""Procedural Memory System - Learn from Skill Execution History.

Sprint 95 Feature 95.4: Procedural Memory System (4 SP)

This module implements a procedural memory system that learns from skill
execution history to optimize future workflows. It captures execution traces,
identifies successful patterns, and suggests optimizations.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │             Procedural Memory System                         │
    ├─────────────────────────────────────────────────────────────┤
    │                                                             │
    │  Trace Collection:                                           │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
    │  │  LangSmith   │  │  Orchestrator│  │  Manual Log  │     │
    │  │   Traces     │  │   Execution  │  │   Recording  │     │
    │  └──────────────┘  └──────────────┘  └──────────────┘     │
    │                                                             │
    │  Pattern Analysis:                                          │
    │  - Success patterns: Inputs → Outputs → Duration            │
    │  - Failure patterns: Error types + Context                  │
    │  - Optimization suggestions: Based on historical data       │
    │                                                             │
    │  Storage: Redis (TTL 30 days default)                       │
    │  - Key: procedural:{skill_name}:{trace_id}                  │
    │  - Index: procedural:skills:{skill_name}                    │
    │  - Success: procedural:success:{skill_name}                 │
    │  - Failure: procedural:failure:{skill_name}                 │
    │                                                             │
    └─────────────────────────────────────────────────────────────┘

Example:
    >>> from src.agents.memory.procedural_memory import ProceduralMemoryStore
    >>>
    >>> store = ProceduralMemoryStore()
    >>>
    >>> # Record execution
    >>> trace = SkillExecutionTrace(
    ...     trace_id="trace_123",
    ...     skill_name="web_search",
    ...     inputs={"query": "quantum computing"},
    ...     outputs={"results": 10},
    ...     duration_ms=235.0,
    ...     success=True,
    ...     context_size=1500
    ... )
    >>> await store.record_execution(trace)
    >>>
    >>> # Get successful patterns
    >>> patterns = await store.get_successful_patterns("web_search", limit=10)
    >>>
    >>> # Get optimization suggestions
    >>> suggestions = await store.get_optimization_suggestions("web_search")

Integration:
    - src/agents/orchestrator/skill_orchestrator.py: Auto-record traces
    - src/components/memory/redis_manager.py: Redis backend
    - src/core/tracing.py: LangSmith integration (optional)
    - LangGraph 1.0: Execution metadata from runs

See Also:
    - docs/sprints/SPRINT_95_PLAN.md: Feature specification
    - src/agents/memory/shared_memory.py: Shared memory protocol
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from src.components.memory.redis_manager import RedisMemoryManager
from src.core.exceptions import MemoryError

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class SkillExecutionTrace:
    """Execution trace for a single skill invocation.

    Captures all metadata needed to learn from execution history.

    Attributes:
        trace_id: Unique trace identifier
        skill_name: Name of skill executed
        inputs: Input parameters provided
        outputs: Outputs produced (if successful)
        duration_ms: Execution duration in milliseconds
        success: Whether execution succeeded
        error: Error message if failed (None if success)
        context_size: Token budget or context size
        timestamp: When execution occurred (ISO format)
        metadata: Additional metadata (parent workflow, etc.)

    Example:
        >>> trace = SkillExecutionTrace(
        ...     trace_id="trace_abc123",
        ...     skill_name="web_search",
        ...     inputs={"query": "quantum computing", "max_results": 10},
        ...     outputs={"results": 8, "sources": ["arxiv", "nature"]},
        ...     duration_ms=235.7,
        ...     success=True,
        ...     context_size=1500,
        ...     timestamp="2026-01-15T10:30:00Z"
        ... )
    """

    trace_id: str
    skill_name: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    duration_ms: float
    success: bool
    error: str | None = None
    context_size: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage.

        Returns:
            Dict representation of trace
        """
        return {
            "trace_id": self.trace_id,
            "skill_name": self.skill_name,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "context_size": self.context_size,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillExecutionTrace:
        """Create from dictionary.

        Args:
            data: Dict representation

        Returns:
            SkillExecutionTrace instance
        """
        return cls(
            trace_id=data["trace_id"],
            skill_name=data["skill_name"],
            inputs=data["inputs"],
            outputs=data["outputs"],
            duration_ms=data["duration_ms"],
            success=data["success"],
            error=data.get("error"),
            context_size=data.get("context_size", 0),
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class ExecutionPattern:
    """Identified execution pattern from traces.

    Attributes:
        pattern_id: Unique pattern identifier
        skill_name: Skill this pattern applies to
        success_rate: Success rate for this pattern (0.0-1.0)
        avg_duration_ms: Average execution duration
        sample_count: Number of traces in this pattern
        common_inputs: Common input patterns
        common_outputs: Common output patterns
        metadata: Additional pattern metadata

    Example:
        >>> pattern = ExecutionPattern(
        ...     pattern_id="pattern_123",
        ...     skill_name="web_search",
        ...     success_rate=0.95,
        ...     avg_duration_ms=220.5,
        ...     sample_count=42,
        ...     common_inputs={"query_type": "academic"},
        ...     common_outputs={"avg_results": 9}
        ... )
    """

    pattern_id: str
    skill_name: str
    success_rate: float
    avg_duration_ms: float
    sample_count: int
    common_inputs: dict[str, Any] = field(default_factory=dict)
    common_outputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Procedural Memory Store
# =============================================================================


class ProceduralMemoryStore:
    """Store and query skill execution patterns.

    Provides Redis-backed storage for execution traces with:
    - Trace recording with TTL
    - Success/failure pattern indexing
    - Pattern analysis and learning
    - Optimization suggestions

    Example:
        >>> store = ProceduralMemoryStore()
        >>>
        >>> # Record execution
        >>> trace = SkillExecutionTrace(...)
        >>> await store.record_execution(trace)
        >>>
        >>> # Query patterns
        >>> successes = await store.get_successful_patterns("web_search")
        >>> failures = await store.get_failure_patterns("web_search")
        >>>
        >>> # Get suggestions
        >>> suggestions = await store.get_optimization_suggestions("web_search")
    """

    def __init__(
        self,
        redis_manager: RedisMemoryManager | None = None,
        default_ttl_seconds: int = 2592000,  # 30 days
        namespace: str = "procedural",
    ) -> None:
        """Initialize ProceduralMemoryStore.

        Args:
            redis_manager: Redis memory manager (default: new instance)
            default_ttl_seconds: Default TTL for traces (default: 30 days)
            namespace: Redis namespace prefix (default: "procedural")
        """
        self._redis = redis_manager or RedisMemoryManager()
        self._default_ttl = default_ttl_seconds
        self._namespace = namespace

        logger.info(
            "procedural_memory_initialized",
            namespace=namespace,
            default_ttl_days=default_ttl_seconds // 86400,
        )

    def _build_trace_key(self, trace_id: str, skill_name: str) -> str:
        """Build Redis key for trace.

        Format: {namespace}:{skill_name}:{trace_id}

        Args:
            trace_id: Trace identifier
            skill_name: Skill name

        Returns:
            Redis key
        """
        return f"{self._namespace}:{skill_name}:{trace_id}"

    def _build_index_key(self, skill_name: str, success: bool) -> str:
        """Build Redis key for success/failure index.

        Format: {namespace}:success:{skill_name} or {namespace}:failure:{skill_name}

        Args:
            skill_name: Skill name
            success: Whether this is success or failure index

        Returns:
            Redis key
        """
        status = "success" if success else "failure"
        return f"{self._namespace}:{status}:{skill_name}"

    async def record_execution(
        self,
        trace: SkillExecutionTrace,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Record skill execution trace.

        Args:
            trace: Execution trace to record
            ttl_seconds: TTL in seconds (default: configured default)

        Returns:
            True if recorded successfully

        Raises:
            MemoryError: If recording fails

        Example:
            >>> trace = SkillExecutionTrace(
            ...     trace_id="trace_123",
            ...     skill_name="web_search",
            ...     inputs={"query": "quantum computing"},
            ...     outputs={"results": 10},
            ...     duration_ms=235.0,
            ...     success=True
            ... )
            >>> await store.record_execution(trace)
            True
        """
        try:
            # Build keys
            trace_key = self._build_trace_key(trace.trace_id, trace.skill_name)
            index_key = self._build_index_key(trace.skill_name, trace.success)

            # Serialize trace
            serialized = json.dumps(trace.to_dict())

            # Store trace with TTL
            ttl = ttl_seconds or self._default_ttl
            await self._redis.store(
                key=trace_key,
                value=serialized,
                ttl_seconds=ttl,
                namespace="",  # Already namespaced
            )

            # Add to index (set of trace IDs)
            redis_client = self._redis.client
            if asyncio.iscoroutine(redis_client):
                redis_client = await redis_client

            await redis_client.sadd(index_key, trace.trace_id)
            # Set TTL on index (longer than traces for safety)
            await redis_client.expire(index_key, ttl + 86400)  # +1 day

            logger.debug(
                "execution_trace_recorded",
                trace_id=trace.trace_id,
                skill=trace.skill_name,
                success=trace.success,
                duration_ms=trace.duration_ms,
            )

            return True

        except Exception as e:
            logger.error(
                "execution_trace_record_failed",
                trace_id=trace.trace_id,
                skill=trace.skill_name,
                error=str(e),
            )
            raise MemoryError(operation="Failed to record execution trace", reason=str(e)) from e

    async def get_successful_patterns(
        self,
        skill_name: str,
        limit: int = 10,
    ) -> list[SkillExecutionTrace]:
        """Get successful execution patterns for skill.

        Args:
            skill_name: Skill to get patterns for
            limit: Maximum number of patterns to return

        Returns:
            List of successful execution traces (most recent first)

        Example:
            >>> patterns = await store.get_successful_patterns("web_search", limit=5)
            >>> for pattern in patterns:
            ...     print(f"Duration: {pattern.duration_ms}ms")
        """
        try:
            index_key = self._build_index_key(skill_name, success=True)
            redis_client = self._redis.client
            if asyncio.iscoroutine(redis_client):
                redis_client = await redis_client

            # Get trace IDs from success index
            trace_ids = await redis_client.smembers(index_key)

            if not trace_ids:
                logger.debug("no_successful_patterns_found", skill=skill_name)
                return []

            # Retrieve traces
            traces = []
            for trace_id in list(trace_ids)[:limit]:
                trace_key = self._build_trace_key(trace_id, skill_name)
                serialized = await self._redis.retrieve(
                    key=trace_key,
                    namespace="",
                    track_access=False,
                )

                if serialized:
                    if isinstance(serialized, str):
                        data = json.loads(serialized)
                    else:
                        data = serialized

                    trace = SkillExecutionTrace.from_dict(data)
                    traces.append(trace)

            # Sort by timestamp (most recent first)
            traces.sort(key=lambda t: t.timestamp, reverse=True)

            logger.info(
                "successful_patterns_retrieved",
                skill=skill_name,
                count=len(traces),
            )

            return traces[:limit]

        except Exception as e:
            logger.error("failed_to_get_successful_patterns", skill=skill_name, error=str(e))
            return []

    async def get_failure_patterns(
        self,
        skill_name: str,
        limit: int = 10,
    ) -> list[SkillExecutionTrace]:
        """Get failure patterns for skill.

        Args:
            skill_name: Skill to get patterns for
            limit: Maximum number of patterns to return

        Returns:
            List of failed execution traces (most recent first)

        Example:
            >>> failures = await store.get_failure_patterns("web_search")
            >>> for failure in failures:
            ...     print(f"Error: {failure.error}")
        """
        try:
            index_key = self._build_index_key(skill_name, success=False)
            redis_client = self._redis.client
            if asyncio.iscoroutine(redis_client):
                redis_client = await redis_client

            # Get trace IDs from failure index
            trace_ids = await redis_client.smembers(index_key)

            if not trace_ids:
                logger.debug("no_failure_patterns_found", skill=skill_name)
                return []

            # Retrieve traces
            traces = []
            for trace_id in list(trace_ids)[:limit]:
                trace_key = self._build_trace_key(trace_id, skill_name)
                serialized = await self._redis.retrieve(
                    key=trace_key,
                    namespace="",
                    track_access=False,
                )

                if serialized:
                    if isinstance(serialized, str):
                        data = json.loads(serialized)
                    else:
                        data = serialized

                    trace = SkillExecutionTrace.from_dict(data)
                    traces.append(trace)

            # Sort by timestamp (most recent first)
            traces.sort(key=lambda t: t.timestamp, reverse=True)

            logger.info(
                "failure_patterns_retrieved",
                skill=skill_name,
                count=len(traces),
            )

            return traces[:limit]

        except Exception as e:
            logger.error("failed_to_get_failure_patterns", skill=skill_name, error=str(e))
            return []

    async def get_optimization_suggestions(
        self,
        skill_name: str,
    ) -> list[str]:
        """Get optimization suggestions based on execution history.

        Analyzes patterns and suggests improvements.

        Args:
            skill_name: Skill to get suggestions for

        Returns:
            List of optimization suggestions

        Example:
            >>> suggestions = await store.get_optimization_suggestions("web_search")
            >>> for suggestion in suggestions:
            ...     print(suggestion)
            "Reduce context_size from 2000 to 1500 (avg usage: 1200)"
            "Increase timeout from 10s to 15s (5% timeouts detected)"
        """
        try:
            # Get both success and failure patterns
            successes = await self.get_successful_patterns(skill_name, limit=50)
            failures = await self.get_failure_patterns(skill_name, limit=20)

            # Delegate to pattern learner
            learner = PatternLearner()
            suggestions = learner.suggest_optimizations(
                skill_name=skill_name,
                traces=successes + failures,
            )

            logger.info(
                "optimization_suggestions_generated",
                skill=skill_name,
                suggestion_count=len(suggestions),
            )

            return suggestions

        except Exception as e:
            logger.error("failed_to_generate_suggestions", skill=skill_name, error=str(e))
            return []

    async def get_metrics(self, skill_name: str) -> dict[str, Any]:
        """Get execution metrics for skill.

        Args:
            skill_name: Skill to get metrics for

        Returns:
            Dict with execution metrics

        Example:
            >>> metrics = await store.get_metrics("web_search")
            >>> print(metrics)
            {
                'total_executions': 100,
                'successful_executions': 95,
                'failed_executions': 5,
                'success_rate': 0.95,
                'avg_duration_ms': 220.5,
                'p95_duration_ms': 350.0
            }
        """
        try:
            successes = await self.get_successful_patterns(skill_name, limit=100)
            failures = await self.get_failure_patterns(skill_name, limit=100)

            total = len(successes) + len(failures)

            if total == 0:
                return {
                    "skill_name": skill_name,
                    "total_executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "success_rate": 0.0,
                    "avg_duration_ms": 0.0,
                    "p95_duration_ms": 0.0,
                }

            # Calculate metrics
            durations = [t.duration_ms for t in successes]
            durations.sort()

            avg_duration = sum(durations) / len(durations) if durations else 0.0
            p95_duration = durations[int(len(durations) * 0.95)] if durations else 0.0

            metrics = {
                "skill_name": skill_name,
                "total_executions": total,
                "successful_executions": len(successes),
                "failed_executions": len(failures),
                "success_rate": len(successes) / total if total > 0 else 0.0,
                "avg_duration_ms": avg_duration,
                "p95_duration_ms": p95_duration,
            }

            logger.info("execution_metrics_retrieved", skill=skill_name, **metrics)

            return metrics

        except Exception as e:
            logger.error("failed_to_get_metrics", skill=skill_name, error=str(e))
            return {}

    async def clear_history(self, skill_name: str) -> int:
        """Clear all execution history for skill.

        Args:
            skill_name: Skill to clear history for

        Returns:
            Number of traces deleted

        Example:
            >>> deleted = await store.clear_history("web_search")
            >>> print(f"Deleted {deleted} traces")
        """
        try:
            redis_client = self._redis.client
            if asyncio.iscoroutine(redis_client):
                redis_client = await redis_client

            # Get all trace IDs for this skill
            success_key = self._build_index_key(skill_name, success=True)
            failure_key = self._build_index_key(skill_name, success=False)

            success_ids = await redis_client.smembers(success_key)
            failure_ids = await redis_client.smembers(failure_key)

            all_trace_ids = list(success_ids) + list(failure_ids)

            # Delete traces
            deleted = 0
            for trace_id in all_trace_ids:
                trace_key = self._build_trace_key(trace_id, skill_name)
                if await self._redis.delete(key=trace_key, namespace=""):
                    deleted += 1

            # Delete indexes
            await redis_client.delete(success_key, failure_key)

            logger.info("execution_history_cleared", skill=skill_name, deleted_count=deleted)

            return deleted

        except Exception as e:
            logger.error("failed_to_clear_history", skill=skill_name, error=str(e))
            return 0

    async def aclose(self) -> None:
        """Close Redis connection (async cleanup)."""
        if self._redis:
            await self._redis.aclose()
            logger.info("procedural_memory_closed")


# =============================================================================
# Pattern Learner
# =============================================================================


class PatternLearner:
    """Analyze execution traces and identify patterns.

    Provides pattern analysis and optimization suggestions based on
    historical execution data.

    Example:
        >>> learner = PatternLearner()
        >>> patterns = learner.analyze_traces(traces)
        >>> suggestions = learner.suggest_optimizations("web_search", traces)
    """

    def analyze_traces(
        self,
        traces: list[SkillExecutionTrace],
    ) -> dict[str, Any]:
        """Analyze execution traces to identify patterns.

        Args:
            traces: List of execution traces

        Returns:
            Dict with pattern analysis

        Example:
            >>> analysis = learner.analyze_traces(traces)
            >>> print(analysis["avg_duration_ms"])
            235.7
        """
        if not traces:
            return {
                "total_traces": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
                "p95_duration_ms": 0.0,
                "common_errors": [],
            }

        # Basic metrics
        total = len(traces)
        successful = sum(1 for t in traces if t.success)
        success_rate = successful / total if total > 0 else 0.0

        # Duration metrics
        durations = [t.duration_ms for t in traces if t.success]
        durations.sort()

        avg_duration = sum(durations) / len(durations) if durations else 0.0
        p95_duration = durations[int(len(durations) * 0.95)] if durations else 0.0

        # Error analysis
        error_counts: dict[str, int] = defaultdict(int)
        for trace in traces:
            if not trace.success and trace.error:
                # Categorize error
                error_type = self._categorize_error(trace.error)
                error_counts[error_type] += 1

        common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Context size analysis
        context_sizes = [t.context_size for t in traces if t.context_size > 0]
        avg_context = sum(context_sizes) / len(context_sizes) if context_sizes else 0

        return {
            "total_traces": total,
            "success_rate": success_rate,
            "avg_duration_ms": avg_duration,
            "p95_duration_ms": p95_duration,
            "avg_context_size": avg_context,
            "common_errors": common_errors,
        }

    def suggest_optimizations(
        self,
        skill_name: str,
        traces: list[SkillExecutionTrace],
    ) -> list[str]:
        """Suggest optimizations based on trace analysis.

        Args:
            skill_name: Skill name
            traces: Execution traces to analyze

        Returns:
            List of optimization suggestions

        Example:
            >>> suggestions = learner.suggest_optimizations("web_search", traces)
            >>> for s in suggestions:
            ...     print(s)
        """
        if not traces:
            return ["No execution history available for analysis"]

        suggestions = []

        # Analyze patterns
        analysis = self.analyze_traces(traces)

        # Success rate suggestions
        if analysis["success_rate"] < 0.8:
            suggestions.append(
                f"Low success rate ({analysis['success_rate']:.1%}). "
                f"Review common errors: {', '.join(e[0] for e in analysis['common_errors'][:3])}"
            )

        # Duration suggestions
        if analysis["p95_duration_ms"] > 1000:  # >1s
            suggestions.append(
                f"High P95 latency ({analysis['p95_duration_ms']:.0f}ms). "
                "Consider adding caching or optimizing queries"
            )

        # Context size suggestions
        successful_traces = [t for t in traces if t.success]
        if successful_traces:
            avg_used = sum(t.context_size for t in successful_traces) / len(successful_traces)
            # If we have context budget info in metadata
            if successful_traces[0].metadata.get("context_budget"):
                avg_budget = sum(
                    t.metadata.get("context_budget", 0) for t in successful_traces
                ) / len(successful_traces)

                if avg_budget > 0 and avg_used < avg_budget * 0.7:
                    suggestions.append(
                        f"Overprovisioned context budget. "
                        f"Reduce from {avg_budget:.0f} to {avg_used * 1.2:.0f} tokens"
                    )

        # Error pattern suggestions
        if analysis["common_errors"]:
            top_error = analysis["common_errors"][0]
            error_type, count = top_error
            error_rate = count / analysis["total_traces"]

            if error_rate > 0.1:  # >10% error rate
                if "timeout" in error_type.lower():
                    suggestions.append("Frequent timeouts detected. Consider increasing timeout threshold")
                elif "not found" in error_type.lower():
                    suggestions.append(
                        "Frequent 'not found' errors. Improve input validation or error handling"
                    )
                elif "rate limit" in error_type.lower():
                    suggestions.append("Rate limit errors detected. Implement request throttling")

        # Input pattern suggestions
        input_patterns = self._analyze_input_patterns(successful_traces)
        if input_patterns:
            suggestions.extend(input_patterns)

        return suggestions

    def _categorize_error(self, error: str) -> str:
        """Categorize error message into error type.

        Args:
            error: Error message

        Returns:
            Error category
        """
        error_lower = error.lower()

        if "timeout" in error_lower:
            return "Timeout"
        elif "not found" in error_lower or "404" in error_lower:
            return "Not Found"
        elif "rate limit" in error_lower or "429" in error_lower:
            return "Rate Limit"
        elif "permission" in error_lower or "403" in error_lower:
            return "Permission Denied"
        elif "connection" in error_lower:
            return "Connection Error"
        elif "invalid" in error_lower or "validation" in error_lower:
            return "Validation Error"
        else:
            return "Other Error"

    def _analyze_input_patterns(
        self,
        traces: list[SkillExecutionTrace],
    ) -> list[str]:
        """Analyze input patterns for optimization suggestions.

        Args:
            traces: Execution traces

        Returns:
            List of input-based suggestions
        """
        suggestions = []

        if not traces:
            return suggestions

        # Collect input keys
        input_keys: dict[str, int] = defaultdict(int)
        for trace in traces:
            for key in trace.inputs.keys():
                input_keys[key] += 1

        # Check for unused optional parameters
        total_traces = len(traces)
        for key, count in input_keys.items():
            usage_rate = count / total_traces
            if usage_rate < 0.3:  # <30% usage
                suggestions.append(
                    f"Parameter '{key}' rarely used ({usage_rate:.0%}). "
                    "Consider making it truly optional or providing better defaults"
                )

        return suggestions


# =============================================================================
# Integration Hooks
# =============================================================================


def create_trace_from_orchestrator(
    skill_name: str,
    invocation: Any,  # SkillInvocation from orchestrator
    result: Any,
    duration_ms: float,
    success: bool,
    error: str | None = None,
) -> SkillExecutionTrace:
    """Create trace from orchestrator execution.

    Helper function to integrate with SkillOrchestrator.

    Args:
        skill_name: Skill executed
        invocation: SkillInvocation object
        result: Execution result
        duration_ms: Duration in milliseconds
        success: Whether execution succeeded
        error: Error message if failed

    Returns:
        SkillExecutionTrace

    Example:
        >>> # In SkillOrchestrator._execute_skill():
        >>> trace = create_trace_from_orchestrator(
        ...     skill_name="web_search",
        ...     invocation=invocation,
        ...     result=result,
        ...     duration_ms=duration,
        ...     success=True
        ... )
        >>> await procedural_store.record_execution(trace)
    """
    trace_id = f"trace_{uuid.uuid4().hex[:12]}"

    # Extract metadata
    metadata = {
        "action": getattr(invocation, "action", "execute"),
        "context_budget": getattr(invocation, "context_budget", 0),
        "timeout": getattr(invocation, "timeout", 30.0),
        "optional": getattr(invocation, "optional", False),
    }

    # Build trace
    return SkillExecutionTrace(
        trace_id=trace_id,
        skill_name=skill_name,
        inputs=getattr(invocation, "inputs", {}),
        outputs=result if isinstance(result, dict) else {"result": result},
        duration_ms=duration_ms,
        success=success,
        error=error,
        context_size=metadata.get("context_budget", 0),
        metadata=metadata,
    )


# =============================================================================
# Factory Functions
# =============================================================================


def create_procedural_memory(
    default_ttl_seconds: int = 2592000,
    namespace: str = "procedural",
) -> ProceduralMemoryStore:
    """Create ProceduralMemoryStore with default configuration.

    Args:
        default_ttl_seconds: Default TTL for traces (default: 30 days)
        namespace: Redis namespace prefix (default: "procedural")

    Returns:
        Configured ProceduralMemoryStore

    Example:
        >>> store = create_procedural_memory(default_ttl_seconds=86400)  # 1 day
        >>> await store.record_execution(trace)
    """
    return ProceduralMemoryStore(
        default_ttl_seconds=default_ttl_seconds,
        namespace=namespace,
    )
