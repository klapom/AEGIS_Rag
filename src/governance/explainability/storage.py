"""
Storage layer for decision traces.

Provides in-memory storage (for testing/MVP) with Redis-backed implementation
planned for production use.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from src.governance.explainability.engine import DecisionTrace


class TraceStorage(ABC):
    """Abstract storage interface for decision traces."""

    @abstractmethod
    async def save(self, trace: DecisionTrace) -> None:
        """
        Save a decision trace.

        Args:
            trace: Decision trace to save
        """
        pass

    @abstractmethod
    async def get(self, trace_id: str) -> Optional[DecisionTrace]:
        """
        Retrieve a decision trace by ID.

        Args:
            trace_id: Trace identifier

        Returns:
            Decision trace if found, None otherwise
        """
        pass

    @abstractmethod
    async def query(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skill_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[DecisionTrace]:
        """
        Query decision traces.

        Args:
            start_time: Filter traces after this time
            end_time: Filter traces before this time
            skill_name: Filter by skill name
            limit: Maximum number of traces to return

        Returns:
            List of matching decision traces
        """
        pass

    @abstractmethod
    async def delete(self, trace_id: str) -> bool:
        """
        Delete a decision trace.

        Args:
            trace_id: Trace identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def count(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """
        Count decision traces.

        Args:
            start_time: Count traces after this time
            end_time: Count traces before this time

        Returns:
            Number of matching traces
        """
        pass


class InMemoryTraceStorage(TraceStorage):
    """
    In-memory storage for decision traces.

    Suitable for testing and MVP deployment. For production, use Redis-backed
    implementation with persistence and expiration policies.
    """

    def __init__(self):
        """Initialize empty in-memory storage."""
        self._traces: Dict[str, DecisionTrace] = {}

    async def save(self, trace: DecisionTrace) -> None:
        """
        Save a decision trace to memory.

        Args:
            trace: Decision trace to save
        """
        self._traces[trace.id] = trace

    async def get(self, trace_id: str) -> Optional[DecisionTrace]:
        """
        Retrieve a decision trace by ID.

        Args:
            trace_id: Trace identifier

        Returns:
            Decision trace if found, None otherwise
        """
        return self._traces.get(trace_id)

    async def query(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skill_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[DecisionTrace]:
        """
        Query decision traces from memory.

        Args:
            start_time: Filter traces after this time
            end_time: Filter traces before this time
            skill_name: Filter by skill name
            limit: Maximum number of traces to return

        Returns:
            List of matching decision traces
        """
        results = []

        for trace in self._traces.values():
            # Time filtering
            if start_time and trace.timestamp < start_time:
                continue
            if end_time and trace.timestamp > end_time:
                continue

            # Skill filtering
            if skill_name and skill_name not in trace.skills_activated:
                continue

            results.append(trace)

            # Apply limit
            if len(results) >= limit:
                break

        # Sort by timestamp (newest first)
        results.sort(key=lambda t: t.timestamp, reverse=True)
        return results

    async def delete(self, trace_id: str) -> bool:
        """
        Delete a decision trace from memory.

        Args:
            trace_id: Trace identifier

        Returns:
            True if deleted, False if not found
        """
        if trace_id in self._traces:
            del self._traces[trace_id]
            return True
        return False

    async def count(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """
        Count decision traces in memory.

        Args:
            start_time: Count traces after this time
            end_time: Count traces before this time

        Returns:
            Number of matching traces
        """
        count = 0
        for trace in self._traces.values():
            if start_time and trace.timestamp < start_time:
                continue
            if end_time and trace.timestamp > end_time:
                continue
            count += 1
        return count

    def clear(self) -> None:
        """Clear all traces from memory (for testing)."""
        self._traces.clear()


class RedisTraceStorage(TraceStorage):
    """
    Redis-backed storage for decision traces.

    Production-ready implementation with:
    - Persistence across restarts
    - TTL-based expiration (7 years for GDPR compliance)
    - Efficient indexing for queries
    - Horizontal scalability

    TODO: Implement in future sprint when Redis integration is needed.
    """

    def __init__(self, redis_client, ttl_days: int = 365 * 7):
        """
        Initialize Redis storage.

        Args:
            redis_client: Redis client instance
            ttl_days: Time-to-live for traces in days (default: 7 years for GDPR)
        """
        self.redis = redis_client
        self.ttl_seconds = ttl_days * 24 * 60 * 60

    async def save(self, trace: DecisionTrace) -> None:
        """Save trace to Redis (not implemented)."""
        raise NotImplementedError("Redis storage implementation pending")

    async def get(self, trace_id: str) -> Optional[DecisionTrace]:
        """Get trace from Redis (not implemented)."""
        raise NotImplementedError("Redis storage implementation pending")

    async def query(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skill_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[DecisionTrace]:
        """Query traces from Redis (not implemented)."""
        raise NotImplementedError("Redis storage implementation pending")

    async def delete(self, trace_id: str) -> bool:
        """Delete trace from Redis (not implemented)."""
        raise NotImplementedError("Redis storage implementation pending")

    async def count(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Count traces in Redis (not implemented)."""
        raise NotImplementedError("Redis storage implementation pending")
