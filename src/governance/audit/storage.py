"""Audit storage layer for append-only persistence.

Provides abstract interface and in-memory mock implementation.
Production implementations: Redis Streams, PostgreSQL append-only table.

Architecture:
    - AuditStorage: Abstract interface (query + append)
    - InMemoryAuditStorage: Mock implementation for testing
    - Future: RedisAuditStorage, PostgreSQLAuditStorage

Retention:
    - Default: 2555 days (7 years) for EU compliance
    - Automatic archival/purging after retention period
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from .trail import AuditEvent, AuditEventType


class AuditStorage(ABC):
    """Abstract interface for audit event storage.

    Requirements:
        - Append-only (no updates/deletes)
        - Time-range queries
        - Actor/event type filtering
        - Retention policy enforcement
    """

    @abstractmethod
    async def append(self, event: "AuditEvent") -> None:
        """Append audit event to storage.

        Args:
            event: Immutable audit event

        Raises:
            ValueError: If event already exists (duplicate ID)
        """
        pass

    @abstractmethod
    async def query(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        actor_id: Optional[str] = None,
        event_types: Optional[List["AuditEventType"]] = None,
        limit: int = 1000,
    ) -> List["AuditEvent"]:
        """Query audit events with filtering.

        Args:
            start_time: Query start time (inclusive)
            end_time: Query end time (inclusive)
            actor_id: Filter by actor ID
            event_types: Filter by event types
            limit: Maximum events to return

        Returns:
            List of matching audit events (chronological order)
        """
        pass

    @abstractmethod
    async def get_last_event(self) -> Optional["AuditEvent"]:
        """Get most recent audit event for chain integrity.

        Returns:
            Last audit event or None if empty
        """
        pass

    @abstractmethod
    async def purge_old_events(self, retention_days: int) -> int:
        """Purge events older than retention period.

        Args:
            retention_days: Retention period (e.g., 2555 = 7 years)

        Returns:
            Number of events purged
        """
        pass


class InMemoryAuditStorage(AuditStorage):
    """In-memory mock storage for testing.

    Production systems should use Redis Streams or PostgreSQL.

    Attributes:
        events: List of audit events (chronological)
        retention_days: Retention period (default: 7 years)
    """

    def __init__(self, retention_days: int = 365 * 7):
        """Initialize in-memory storage.

        Args:
            retention_days: Retention period (default: 2555 = 7 years)
        """
        from .trail import AuditEvent

        self.events: List["AuditEvent"] = []
        self.retention_days = retention_days

    async def append(self, event: "AuditEvent") -> None:
        """Append event to in-memory storage.

        Args:
            event: Audit event to append

        Raises:
            ValueError: If event with same ID already exists
        """
        # Check for duplicate IDs
        if any(e.id == event.id for e in self.events):
            raise ValueError(f"Duplicate audit event ID: {event.id}")

        self.events.append(event)

    async def query(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        actor_id: Optional[str] = None,
        event_types: Optional[List["AuditEventType"]] = None,
        limit: int = 1000,
    ) -> List["AuditEvent"]:
        """Query events with in-memory filtering.

        Args:
            start_time: Query start time
            end_time: Query end time
            actor_id: Filter by actor
            event_types: Filter by event types
            limit: Max results

        Returns:
            Filtered events (chronological)
        """
        results = self.events.copy()

        # Time range filter
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]

        # Actor filter
        if actor_id:
            results = [e for e in results if e.actor_id == actor_id]

        # Event type filter
        if event_types:
            results = [e for e in results if e.event_type in event_types]

        # Limit
        return results[:limit]

    async def get_last_event(self) -> Optional["AuditEvent"]:
        """Get most recent event.

        Returns:
            Last event or None
        """
        return self.events[-1] if self.events else None

    async def purge_old_events(self, retention_days: int) -> int:
        """Purge events older than retention period.

        Args:
            retention_days: Retention period

        Returns:
            Number of events purged
        """
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        original_count = len(self.events)

        self.events = [e for e in self.events if e.timestamp >= cutoff]

        return original_count - len(self.events)

    def clear(self) -> None:
        """Clear all events (test utility)."""
        self.events.clear()

    def size(self) -> int:
        """Get total event count (test utility)."""
        return len(self.events)
