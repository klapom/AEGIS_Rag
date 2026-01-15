"""Unit tests for audit trail system.

Test Coverage:
    - AuditEventType: All 16 event types
    - AuditEvent: Hash computation, verification, serialization
    - AuditTrailManager: Logging, chain integrity, compliance reports
    - SkillAuditDecorator: Auto-audit skill executions
    - AuditStorage: Query, append, retention
"""

import pytest
from datetime import datetime, timedelta
from typing import List
from unittest.mock import AsyncMock, patch

from src.governance.audit import (
    AuditEvent,
    AuditEventType,
    AuditTrailManager,
    InMemoryAuditStorage,
    audit_skill,
)


class TestAuditEventType:
    """Test AuditEventType enum."""

    def test_all_event_types_exist(self):
        """Test all 16 event types are defined."""
        expected_types = {
            # Skill lifecycle (5)
            "skill.loaded",
            "skill.executed",
            "skill.failed",
            "skill.updated",
            "skill.deleted",
            # Data access (4)
            "data.read",
            "data.write",
            "data.delete",
            "data.exported",
            # Decisions (3)
            "decision.routed",
            "decision.rejected",
            "decision.approved",
            # Security (3)
            "auth.success",
            "auth.failure",
            "policy.violation",
            # System (1)
            "config.changed",
        }

        actual_types = {e.value for e in AuditEventType}
        assert actual_types == expected_types

    def test_skill_lifecycle_events(self):
        """Test skill lifecycle event types."""
        assert AuditEventType.SKILL_LOADED.value == "skill.loaded"
        assert AuditEventType.SKILL_EXECUTED.value == "skill.executed"
        assert AuditEventType.SKILL_FAILED.value == "skill.failed"
        assert AuditEventType.SKILL_UPDATED.value == "skill.updated"
        assert AuditEventType.SKILL_DELETED.value == "skill.deleted"

    def test_data_access_events(self):
        """Test data access event types."""
        assert AuditEventType.DATA_READ.value == "data.read"
        assert AuditEventType.DATA_WRITE.value == "data.write"
        assert AuditEventType.DATA_DELETE.value == "data.delete"
        assert AuditEventType.DATA_EXPORTED.value == "data.exported"

    def test_decision_events(self):
        """Test decision event types."""
        assert AuditEventType.DECISION_ROUTED.value == "decision.routed"
        assert AuditEventType.DECISION_REJECTED.value == "decision.rejected"
        assert AuditEventType.DECISION_APPROVED.value == "decision.approved"

    def test_security_events(self):
        """Test security event types."""
        assert AuditEventType.AUTH_SUCCESS.value == "auth.success"
        assert AuditEventType.AUTH_FAILURE.value == "auth.failure"
        assert AuditEventType.POLICY_VIOLATION.value == "policy.violation"

    def test_system_events(self):
        """Test system event types."""
        assert AuditEventType.CONFIG_CHANGED.value == "config.changed"


class TestAuditEvent:
    """Test AuditEvent immutable dataclass."""

    def test_event_creation(self):
        """Test basic event creation."""
        event = AuditEvent(
            id="evt-001",
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
            metadata={"skill_id": "rag-001"},
        )

        assert event.id == "evt-001"
        assert event.event_type == AuditEventType.SKILL_EXECUTED
        assert event.actor_id == "claude"
        assert event.outcome == "success"
        assert event.metadata["skill_id"] == "rag-001"

    def test_event_hash_computed_on_init(self):
        """Test event hash is auto-computed on initialization."""
        event = AuditEvent(
            id="evt-001",
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
        )

        assert event.event_hash is not None
        assert len(event.event_hash) == 64  # SHA-256 hex = 64 chars

    def test_compute_hash_deterministic(self):
        """Test hash computation is deterministic."""
        timestamp = datetime.utcnow()

        event1 = AuditEvent(
            id="evt-001",
            timestamp=timestamp,
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
        )

        event2 = AuditEvent(
            id="evt-001",
            timestamp=timestamp,
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
        )

        # Same data = same hash
        assert event1.compute_hash() == event2.compute_hash()

    def test_compute_hash_changes_with_data(self):
        """Test hash changes when event data changes."""
        timestamp = datetime.utcnow()

        event1 = AuditEvent(
            id="evt-001",
            timestamp=timestamp,
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
        )

        event2 = AuditEvent(
            id="evt-002",  # Different ID
            timestamp=timestamp,
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
        )

        # Different data = different hash
        assert event1.compute_hash() != event2.compute_hash()

    def test_verify_hash_success(self):
        """Test hash verification succeeds for valid event."""
        event = AuditEvent(
            id="evt-001",
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
        )

        assert event.verify_hash() is True

    def test_verify_hash_failure(self):
        """Test hash verification fails for tampered event."""
        event = AuditEvent(
            id="evt-001",
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
        )

        # Tamper with event hash
        object.__setattr__(event, "event_hash", "tampered_hash_12345")

        assert event.verify_hash() is False

    def test_event_with_context_hash(self):
        """Test event with context hash."""
        event = AuditEvent(
            id="evt-001",
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
            context_hash="abc123",
        )

        assert event.context_hash == "abc123"

    def test_event_with_output_hash(self):
        """Test event with output hash."""
        event = AuditEvent(
            id="evt-001",
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
            output_hash="def456",
        )

        assert event.output_hash == "def456"

    def test_event_with_previous_hash(self):
        """Test event with previous hash for chain."""
        event = AuditEvent(
            id="evt-002",
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
            previous_hash="prev_hash_123",
        )

        assert event.previous_hash == "prev_hash_123"

    def test_to_dict_serialization(self):
        """Test event serialization to dict."""
        timestamp = datetime.utcnow()

        event = AuditEvent(
            id="evt-001",
            timestamp=timestamp,
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
            metadata={"skill_id": "rag-001"},
        )

        data = event.to_dict()

        assert data["id"] == "evt-001"
        assert data["timestamp"] == timestamp.isoformat()
        assert data["event_type"] == "skill.executed"
        assert data["actor_id"] == "claude"
        assert data["metadata"]["skill_id"] == "rag-001"

    def test_from_dict_deserialization(self):
        """Test event deserialization from dict."""
        timestamp = datetime.utcnow()

        data = {
            "id": "evt-001",
            "timestamp": timestamp.isoformat(),
            "event_type": "skill.executed",
            "actor_id": "claude",
            "actor_type": "agent",
            "action": "retrieve_documents",
            "outcome": "success",
            "metadata": {"skill_id": "rag-001"},
            "context_hash": None,
            "output_hash": None,
            "previous_hash": None,
            "event_hash": "",
        }

        event = AuditEvent.from_dict(data)

        assert event.id == "evt-001"
        assert event.event_type == AuditEventType.SKILL_EXECUTED
        assert event.actor_id == "claude"
        assert event.metadata["skill_id"] == "rag-001"

    def test_event_is_frozen(self):
        """Test event is immutable (frozen dataclass)."""
        event = AuditEvent(
            id="evt-001",
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            event.outcome = "failure"


class TestInMemoryAuditStorage:
    """Test InMemoryAuditStorage."""

    @pytest.fixture
    def storage(self):
        """Create in-memory storage."""
        return InMemoryAuditStorage()

    @pytest.mark.asyncio
    async def test_append_event(self, storage):
        """Test appending event to storage."""
        event = AuditEvent(
            id="evt-001",
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
        )

        await storage.append(event)

        assert storage.size() == 1
        assert storage.events[0] == event

    @pytest.mark.asyncio
    async def test_append_duplicate_id_raises_error(self, storage):
        """Test appending duplicate ID raises error."""
        event1 = AuditEvent(
            id="evt-001",
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            actor_type="agent",
            action="retrieve_documents",
            outcome="success",
        )

        await storage.append(event1)

        # Try to append same ID again
        event2 = AuditEvent(
            id="evt-001",  # Same ID
            timestamp=datetime.utcnow(),
            event_type=AuditEventType.DATA_READ,
            actor_id="user",
            actor_type="human",
            action="read_data",
            outcome="success",
        )

        with pytest.raises(ValueError, match="Duplicate audit event ID"):
            await storage.append(event2)

    @pytest.mark.asyncio
    async def test_query_all_events(self, storage):
        """Test querying all events."""
        events = [
            AuditEvent(
                id=f"evt-{i}",
                timestamp=datetime.utcnow(),
                event_type=AuditEventType.SKILL_EXECUTED,
                actor_id="claude",
                actor_type="agent",
                action="action",
                outcome="success",
            )
            for i in range(5)
        ]

        for event in events:
            await storage.append(event)

        results = await storage.query()

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_query_with_time_range(self, storage):
        """Test querying with time range."""
        now = datetime.utcnow()

        events = [
            AuditEvent(
                id=f"evt-{i}",
                timestamp=now + timedelta(hours=i),
                event_type=AuditEventType.SKILL_EXECUTED,
                actor_id="claude",
                actor_type="agent",
                action="action",
                outcome="success",
            )
            for i in range(5)
        ]

        for event in events:
            await storage.append(event)

        # Query events from hour 1 to hour 3
        results = await storage.query(
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=3),
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_query_with_actor_filter(self, storage):
        """Test querying with actor filter."""
        events = [
            AuditEvent(
                id=f"evt-{i}",
                timestamp=datetime.utcnow(),
                event_type=AuditEventType.SKILL_EXECUTED,
                actor_id="claude" if i % 2 == 0 else "user",
                actor_type="agent",
                action="action",
                outcome="success",
            )
            for i in range(10)
        ]

        for event in events:
            await storage.append(event)

        results = await storage.query(actor_id="claude")

        assert len(results) == 5
        assert all(e.actor_id == "claude" for e in results)

    @pytest.mark.asyncio
    async def test_query_with_event_type_filter(self, storage):
        """Test querying with event type filter."""
        events = [
            AuditEvent(
                id=f"evt-{i}",
                timestamp=datetime.utcnow(),
                event_type=(
                    AuditEventType.SKILL_EXECUTED if i % 2 == 0
                    else AuditEventType.DATA_READ
                ),
                actor_id="claude",
                actor_type="agent",
                action="action",
                outcome="success",
            )
            for i in range(10)
        ]

        for event in events:
            await storage.append(event)

        results = await storage.query(
            event_types=[AuditEventType.SKILL_EXECUTED]
        )

        assert len(results) == 5
        assert all(e.event_type == AuditEventType.SKILL_EXECUTED for e in results)

    @pytest.mark.asyncio
    async def test_query_with_limit(self, storage):
        """Test querying with limit."""
        events = [
            AuditEvent(
                id=f"evt-{i}",
                timestamp=datetime.utcnow(),
                event_type=AuditEventType.SKILL_EXECUTED,
                actor_id="claude",
                actor_type="agent",
                action="action",
                outcome="success",
            )
            for i in range(100)
        ]

        for event in events:
            await storage.append(event)

        results = await storage.query(limit=10)

        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_get_last_event(self, storage):
        """Test getting last event."""
        events = [
            AuditEvent(
                id=f"evt-{i}",
                timestamp=datetime.utcnow(),
                event_type=AuditEventType.SKILL_EXECUTED,
                actor_id="claude",
                actor_type="agent",
                action="action",
                outcome="success",
            )
            for i in range(5)
        ]

        for event in events:
            await storage.append(event)

        last = await storage.get_last_event()

        assert last is not None
        assert last.id == "evt-4"

    @pytest.mark.asyncio
    async def test_get_last_event_empty(self, storage):
        """Test getting last event from empty storage."""
        last = await storage.get_last_event()

        assert last is None

    @pytest.mark.asyncio
    async def test_purge_old_events(self, storage):
        """Test purging old events."""
        now = datetime.utcnow()

        events = [
            AuditEvent(
                id=f"evt-{i}",
                timestamp=now - timedelta(days=i * 365),
                event_type=AuditEventType.SKILL_EXECUTED,
                actor_id="claude",
                actor_type="agent",
                action="action",
                outcome="success",
            )
            for i in range(10)
        ]

        for event in events:
            await storage.append(event)

        # Purge events older than 3 years
        purged = await storage.purge_old_events(retention_days=365 * 3)

        assert purged == 7  # Events 3+ years old
        assert storage.size() == 3  # 0, 1, 2 years old remain


class TestAuditTrailManager:
    """Test AuditTrailManager."""

    @pytest.fixture
    def storage(self):
        """Create in-memory storage."""
        return InMemoryAuditStorage()

    @pytest.fixture
    def manager(self, storage):
        """Create audit trail manager."""
        return AuditTrailManager(storage)

    @pytest.mark.asyncio
    async def test_log_event(self, manager, storage):
        """Test logging audit event."""
        event = await manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            action="retrieve_documents",
            outcome="success",
            metadata={"skill_id": "rag-001"},
        )

        assert event.event_type == AuditEventType.SKILL_EXECUTED
        assert event.actor_id == "claude"
        assert event.outcome == "success"
        assert storage.size() == 1

    @pytest.mark.asyncio
    async def test_log_event_with_context(self, manager):
        """Test logging event with context."""
        context = {"query": "What is RAG?"}

        event = await manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            action="retrieve_documents",
            outcome="success",
            context=context,
        )

        assert event.context_hash is not None
        assert len(event.context_hash) == 64  # SHA-256

    @pytest.mark.asyncio
    async def test_log_event_with_output(self, manager):
        """Test logging event with output."""
        output = {"documents": ["doc1", "doc2"]}

        event = await manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            action="retrieve_documents",
            outcome="success",
            output=output,
        )

        assert event.output_hash is not None
        assert len(event.output_hash) == 64  # SHA-256

    @pytest.mark.asyncio
    async def test_log_creates_hash_chain(self, manager):
        """Test logging creates hash chain."""
        event1 = await manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            action="action1",
            outcome="success",
        )

        event2 = await manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="claude",
            action="action2",
            outcome="success",
        )

        # Event2 should link to event1
        assert event1.previous_hash is None  # First event
        assert event2.previous_hash == event1.event_hash

    @pytest.mark.asyncio
    async def test_verify_integrity_success(self, manager):
        """Test integrity verification succeeds for valid chain."""
        # Log multiple events
        for i in range(5):
            await manager.log(
                event_type=AuditEventType.SKILL_EXECUTED,
                actor_id="claude",
                action=f"action{i}",
                outcome="success",
            )

        is_valid, errors = await manager.verify_integrity()

        assert is_valid is True
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_verify_integrity_detects_tampered_hash(self, manager, storage):
        """Test integrity verification detects tampered event hash."""
        # Log events
        for i in range(3):
            await manager.log(
                event_type=AuditEventType.SKILL_EXECUTED,
                actor_id="claude",
                action=f"action{i}",
                outcome="success",
            )

        # Tamper with middle event
        tampered_event = storage.events[1]
        object.__setattr__(tampered_event, "event_hash", "tampered_hash")

        is_valid, errors = await manager.verify_integrity()

        assert is_valid is False
        assert len(errors) > 0
        assert "invalid hash" in errors[0]

    @pytest.mark.asyncio
    async def test_verify_integrity_detects_broken_chain(self, manager, storage):
        """Test integrity verification detects broken chain."""
        # Log events
        for i in range(3):
            await manager.log(
                event_type=AuditEventType.SKILL_EXECUTED,
                actor_id="claude",
                action=f"action{i}",
                outcome="success",
            )

        # Break chain by changing previous_hash
        event = storage.events[2]
        object.__setattr__(event, "previous_hash", "broken_chain")
        # Recompute hash to pass individual hash check
        object.__setattr__(event, "event_hash", event.compute_hash())

        is_valid, errors = await manager.verify_integrity()

        assert is_valid is False
        assert len(errors) > 0
        assert "Chain break" in errors[0]

    @pytest.mark.asyncio
    async def test_verify_integrity_empty_trail(self, manager):
        """Test integrity verification on empty trail."""
        is_valid, errors = await manager.verify_integrity()

        assert is_valid is True
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_generate_gdpr_art30_report(self, manager):
        """Test generating GDPR Article 30 compliance report."""
        # Log data processing events
        for i in range(5):
            await manager.log(
                event_type=AuditEventType.DATA_READ,
                actor_id=f"user{i}",
                action="read_documents",
                outcome="success",
            )

        for i in range(3):
            await manager.log(
                event_type=AuditEventType.DATA_WRITE,
                actor_id=f"user{i}",
                action="write_documents",
                outcome="success",
            )

        report = await manager.generate_compliance_report(
            report_type="gdpr_art30",
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow(),
        )

        assert report["report_type"] == "gdpr_art30"
        assert report["processing_activities"]["total"] == 8
        assert report["processing_activities"]["by_type"]["data.read"] == 5
        assert report["processing_activities"]["by_type"]["data.write"] == 3

    @pytest.mark.asyncio
    async def test_generate_security_report(self, manager):
        """Test generating security compliance report."""
        # Log security events
        await manager.log(
            event_type=AuditEventType.AUTH_SUCCESS,
            actor_id="user1",
            action="login",
            outcome="success",
        )

        await manager.log(
            event_type=AuditEventType.AUTH_FAILURE,
            actor_id="user2",
            action="login",
            outcome="failure",
        )

        await manager.log(
            event_type=AuditEventType.POLICY_VIOLATION,
            actor_id="user3",
            action="unauthorized_access",
            outcome="blocked",
        )

        report = await manager.generate_compliance_report(
            report_type="security",
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow(),
        )

        assert report["report_type"] == "security"
        assert report["security_summary"]["total"] == 3
        assert report["security_summary"]["failed_auth"] == 1
        assert report["security_summary"]["violations"] == 1

    @pytest.mark.asyncio
    async def test_generate_skill_usage_report(self, manager):
        """Test generating skill usage report."""
        # Log skill events
        for i in range(10):
            await manager.log(
                event_type=AuditEventType.SKILL_EXECUTED,
                actor_id="claude",
                action="execute_skill",
                outcome="success",
                metadata={"skill_id": f"skill-{i % 3}"},
            )

        for i in range(2):
            await manager.log(
                event_type=AuditEventType.SKILL_FAILED,
                actor_id="claude",
                action="execute_skill",
                outcome="failure",
                metadata={"skill_id": "skill-0"},
            )

        report = await manager.generate_compliance_report(
            report_type="skill_usage",
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow(),
        )

        assert report["report_type"] == "skill_usage"
        assert report["skill_usage"]["total_executions"] == 10
        assert report["skill_usage"]["failures"] == 2

    @pytest.mark.asyncio
    async def test_generate_data_access_report(self, manager):
        """Test generating data access report."""
        # Log data access events
        await manager.log(
            event_type=AuditEventType.DATA_READ,
            actor_id="user1",
            action="read",
            outcome="success",
        )

        await manager.log(
            event_type=AuditEventType.DATA_WRITE,
            actor_id="user2",
            action="write",
            outcome="success",
        )

        await manager.log(
            event_type=AuditEventType.DATA_DELETE,
            actor_id="admin",
            action="delete",
            outcome="success",
        )

        report = await manager.generate_compliance_report(
            report_type="data_access",
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow(),
        )

        assert report["report_type"] == "data_access"
        assert report["data_access"]["total"] == 3
        assert report["data_access"]["reads"] == 1
        assert report["data_access"]["writes"] == 1
        assert report["data_access"]["deletes"] == 1

    @pytest.mark.asyncio
    async def test_purge_old_events(self, manager, storage):
        """Test purging old events."""
        now = datetime.utcnow()

        # Log old events (0, 2, 4, 6, 8, 10 years old)
        for i in range(6):
            event = AuditEvent(
                id=f"evt-{i}",
                timestamp=now - timedelta(days=i * 365 * 2),
                event_type=AuditEventType.SKILL_EXECUTED,
                actor_id="claude",
                actor_type="agent",
                action="action",
                outcome="success",
            )
            await storage.append(event)

        purged = await manager.purge_old_events()

        # Default retention: 7 years, so 8+ years old should be purged (2 events)
        assert purged >= 2
        assert storage.size() <= 4  # 0, 2, 4, 6 years remain


class TestSkillAuditDecorator:
    """Test SkillAuditDecorator."""

    @pytest.fixture
    def storage(self):
        """Create in-memory storage."""
        return InMemoryAuditStorage()

    @pytest.fixture
    def manager(self, storage):
        """Create audit trail manager."""
        return AuditTrailManager(storage)

    @pytest.mark.asyncio
    async def test_decorator_logs_skill_loaded(self, manager, storage):
        """Test decorator logs skill loaded on first call."""
        @audit_skill(manager, skill_id="test-skill")
        async def test_function():
            return "result"

        await test_function()

        # Should have SKILL_LOADED event
        events = await storage.query(event_types=[AuditEventType.SKILL_LOADED])
        assert len(events) == 1
        assert events[0].metadata["skill_id"] == "test-skill"

    @pytest.mark.asyncio
    async def test_decorator_logs_skill_executed(self, manager, storage):
        """Test decorator logs skill executed on each call."""
        @audit_skill(manager, skill_id="test-skill")
        async def test_function():
            return "result"

        await test_function()
        await test_function()

        # Should have 2 SKILL_EXECUTED events
        events = await storage.query(event_types=[AuditEventType.SKILL_EXECUTED])
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_decorator_logs_skill_failed(self, manager, storage):
        """Test decorator logs skill failed on exception."""
        @audit_skill(manager, skill_id="test-skill")
        async def test_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await test_function()

        # Should have SKILL_FAILED event
        events = await storage.query(event_types=[AuditEventType.SKILL_FAILED])
        assert len(events) == 1
        assert events[0].outcome == "failure"
        assert "Test error" in events[0].metadata["error"]

    @pytest.mark.asyncio
    async def test_decorator_captures_duration(self, manager, storage):
        """Test decorator captures execution duration."""
        @audit_skill(manager, skill_id="test-skill")
        async def test_function():
            return "result"

        await test_function()

        events = await storage.query(event_types=[AuditEventType.SKILL_EXECUTED])
        assert "duration_ms" in events[0].metadata
        assert events[0].metadata["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_decorator_with_custom_actor(self, manager, storage):
        """Test decorator with custom actor ID."""
        @audit_skill(manager, skill_id="test-skill", actor_id="custom_actor")
        async def test_function():
            return "result"

        await test_function()

        events = await storage.query()
        assert all(e.actor_id == "custom_actor" for e in events)

    @pytest.mark.asyncio
    async def test_decorator_returns_result(self, manager):
        """Test decorator returns function result."""
        @audit_skill(manager, skill_id="test-skill")
        async def test_function():
            return "expected_result"

        result = await test_function()

        assert result == "expected_result"

    @pytest.mark.asyncio
    async def test_decorator_logs_loaded_once(self, manager, storage):
        """Test decorator logs SKILL_LOADED only once."""
        @audit_skill(manager, skill_id="test-skill")
        async def test_function():
            return "result"

        await test_function()
        await test_function()
        await test_function()

        # Should have only 1 SKILL_LOADED event
        events = await storage.query(event_types=[AuditEventType.SKILL_LOADED])
        assert len(events) == 1


class TestIntegration:
    """Integration tests for audit trail system."""

    @pytest.mark.asyncio
    async def test_full_audit_workflow(self):
        """Test complete audit workflow."""
        # Setup
        storage = InMemoryAuditStorage()
        manager = AuditTrailManager(storage)

        # Create decorated function
        @audit_skill(manager, skill_id="integration-test")
        async def retrieve_documents(query: str):
            return [f"doc{i}" for i in range(3)]

        # Execute skill multiple times
        await retrieve_documents("test1")
        await retrieve_documents("test2")

        # Log additional events
        await manager.log(
            event_type=AuditEventType.DATA_READ,
            actor_id="user",
            action="read_documents",
            outcome="success",
        )

        # Verify integrity
        is_valid, errors = await manager.verify_integrity()
        assert is_valid is True

        # Generate report
        report = await manager.generate_compliance_report(
            report_type="skill_usage",
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
        )

        assert report["skill_usage"]["total_executions"] == 2

    @pytest.mark.asyncio
    async def test_compliance_report_with_integrity_check(self):
        """Test compliance report includes integrity verification."""
        storage = InMemoryAuditStorage()
        manager = AuditTrailManager(storage)

        # Log events
        for i in range(10):
            await manager.log(
                event_type=AuditEventType.DATA_READ,
                actor_id="user",
                action="read",
                outcome="success",
            )

        report = await manager.generate_compliance_report(
            report_type="gdpr_art30",
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow(),
        )

        assert report["integrity_verified"] is True
        assert len(report["integrity_errors"]) == 0

    @pytest.mark.asyncio
    async def test_audit_trail_with_7_year_retention(self):
        """Test 7-year retention policy."""
        storage = InMemoryAuditStorage(retention_days=365 * 7)
        manager = AuditTrailManager(storage, retention_days=365 * 7)

        now = datetime.utcnow()

        # Log events spanning 10 years
        for year in range(10):
            event = AuditEvent(
                id=f"evt-year-{year}",
                timestamp=now - timedelta(days=365 * year),
                event_type=AuditEventType.DATA_READ,
                actor_id="user",
                actor_type="human",
                action="read",
                outcome="success",
            )
            await storage.append(event)

        # Purge old events
        purged = await storage.purge_old_events(retention_days=365 * 7)

        # Should retain 0-6 years (7 events), purge 7-9 years (3 events)
        assert purged == 3
        assert storage.size() == 7
