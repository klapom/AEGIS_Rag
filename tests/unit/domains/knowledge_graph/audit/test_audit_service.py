"""Unit tests for AuditService.

Sprint 63 Feature 63.2: Tests for audit logging and query methods.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exceptions import GraphQueryError
from src.domains.knowledge_graph.audit.audit_service import AuditService, reset_audit_service


@pytest.fixture
def mock_neo4j_client() -> MagicMock:
    """Create mock Neo4j client."""
    client = MagicMock()
    client.execute_write = AsyncMock()
    client.execute_read = AsyncMock()
    return client


@pytest.fixture
def audit_service(mock_neo4j_client: MagicMock) -> AuditService:
    """Create AuditService instance with mocked Neo4j client."""
    reset_audit_service()  # Reset singleton
    return AuditService(neo4j_client=mock_neo4j_client)


class TestAuditServiceEntityLogging:
    """Test entity change logging methods."""

    @pytest.mark.asyncio
    async def test_log_entity_created(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test logging entity creation event."""
        mock_neo4j_client.execute_write.return_value = {"event_id": "evt-123"}

        event = await audit_service.log_entity_change(
            event_type="entity_created",
            entity_id="entity-123",
            entity_type="PERSON",
            new_properties={"name": "John Doe"},
            namespace="default",
            document_id="doc-456",
        )

        assert event.event_type == "entity_created"
        assert event.entity_id == "entity-123"
        assert event.entity_type == "PERSON"
        assert event.new_properties == {"name": "John Doe"}
        assert event.namespace == "default"
        assert event.document_id == "doc-456"

        # Verify Neo4j write was called
        mock_neo4j_client.execute_write.assert_called_once()
        call_args = mock_neo4j_client.execute_write.call_args
        assert "CREATE (e:AuditEvent" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_log_entity_updated(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test logging entity update event."""
        mock_neo4j_client.execute_write.return_value = {"event_id": "evt-123"}

        event = await audit_service.log_entity_change(
            event_type="entity_updated",
            entity_id="entity-123",
            entity_type="PERSON",
            old_properties={"name": "John"},
            new_properties={"name": "John Doe"},
            namespace="default",
            document_id="doc-456",
            user_id="user-789",
        )

        assert event.event_type == "entity_updated"
        assert event.old_properties == {"name": "John"}
        assert event.new_properties == {"name": "John Doe"}
        assert event.user_id == "user-789"

    @pytest.mark.asyncio
    async def test_log_entity_deleted(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test logging entity deletion event."""
        mock_neo4j_client.execute_write.return_value = {"event_id": "evt-123"}

        event = await audit_service.log_entity_change(
            event_type="entity_deleted",
            entity_id="entity-123",
            entity_type="PERSON",
            old_properties={"name": "John Doe"},
            namespace="default",
            document_id="doc-456",
        )

        assert event.event_type == "entity_deleted"
        assert event.old_properties == {"name": "John Doe"}
        assert event.new_properties is None

    @pytest.mark.asyncio
    async def test_log_entity_change_failure(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test handling of Neo4j write failure."""
        mock_neo4j_client.execute_write.side_effect = Exception("Neo4j error")

        with pytest.raises(GraphQueryError) as exc_info:
            await audit_service.log_entity_change(
                event_type="entity_created",
                entity_id="entity-123",
                entity_type="PERSON",
                new_properties={"name": "John Doe"},
                namespace="default",
                document_id="doc-456",
            )

        assert "Neo4j error" in str(exc_info.value)


class TestAuditServiceRelationshipLogging:
    """Test relationship change logging methods."""

    @pytest.mark.asyncio
    async def test_log_relationship_created(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test logging relationship creation event."""
        mock_neo4j_client.execute_write.return_value = {"event_id": "evt-123"}

        event = await audit_service.log_relationship_change(
            event_type="relationship_created",
            relationship_id="rel-789",
            relationship_type="WORKS_FOR",
            source_entity_id="entity-123",
            target_entity_id="entity-456",
            new_properties={"since": "2024-01-01"},
            namespace="default",
            document_id="doc-456",
        )

        assert event.event_type == "relationship_created"
        assert event.relationship_id == "rel-789"
        assert event.relationship_type == "WORKS_FOR"
        assert event.new_properties["since"] == "2024-01-01"
        assert event.new_properties["_source_entity_id"] == "entity-123"
        assert event.new_properties["_target_entity_id"] == "entity-456"

    @pytest.mark.asyncio
    async def test_log_relationship_deleted(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test logging relationship deletion event."""
        mock_neo4j_client.execute_write.return_value = {"event_id": "evt-123"}

        event = await audit_service.log_relationship_change(
            event_type="relationship_deleted",
            relationship_id="rel-789",
            relationship_type="WORKS_FOR",
            old_properties={"since": "2024-01-01"},
            namespace="default",
            document_id="doc-456",
        )

        assert event.event_type == "relationship_deleted"
        assert event.old_properties == {"since": "2024-01-01"}

    @pytest.mark.asyncio
    async def test_log_relationship_change_failure(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test handling of Neo4j write failure for relationships."""
        mock_neo4j_client.execute_write.side_effect = Exception("Neo4j error")

        with pytest.raises(GraphQueryError):
            await audit_service.log_relationship_change(
                event_type="relationship_created",
                relationship_id="rel-789",
                relationship_type="WORKS_FOR",
                namespace="default",
                document_id="doc-456",
            )


class TestAuditServiceQueries:
    """Test audit query methods."""

    @pytest.mark.asyncio
    async def test_get_entity_history(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test querying entity change history."""
        mock_records = [
            {
                "event_id": "evt-1",
                "timestamp": "2024-01-01T12:00:00",
                "event_type": "entity_created",
                "entity_id": "entity-123",
                "entity_type": "PERSON",
                "relationship_id": None,
                "relationship_type": None,
                "old_properties": None,
                "new_properties": "{'name': 'John Doe'}",
                "namespace": "default",
                "document_id": "doc-456",
                "user_id": "system",
            },
            {
                "event_id": "evt-2",
                "timestamp": "2024-01-02T12:00:00",
                "event_type": "entity_updated",
                "entity_id": "entity-123",
                "entity_type": "PERSON",
                "relationship_id": None,
                "relationship_type": None,
                "old_properties": "{'name': 'John Doe'}",
                "new_properties": "{'name': 'John Smith'}",
                "namespace": "default",
                "document_id": "doc-456",
                "user_id": "user-789",
            },
        ]
        mock_neo4j_client.execute_read.return_value = mock_records

        events = await audit_service.get_entity_history("entity-123", "default")

        assert len(events) == 2
        assert events[0].event_type == "entity_created"
        assert events[1].event_type == "entity_updated"
        assert all(e.entity_id == "entity-123" for e in events)

        # Verify query
        mock_neo4j_client.execute_read.assert_called_once()
        call_args = mock_neo4j_client.execute_read.call_args
        assert "MATCH (e:AuditEvent)" in call_args[0][0]
        assert call_args[0][1]["entity_id"] == "entity-123"

    @pytest.mark.asyncio
    async def test_get_entity_history_empty(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test querying entity history with no results."""
        mock_neo4j_client.execute_read.return_value = []

        events = await audit_service.get_entity_history("entity-999", "default")

        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_get_recent_changes(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test querying recent changes."""
        mock_records = [
            {
                "event_id": "evt-1",
                "timestamp": "2024-01-01T12:00:00",
                "event_type": "entity_created",
                "entity_id": "entity-123",
                "entity_type": "PERSON",
                "relationship_id": None,
                "relationship_type": None,
                "old_properties": None,
                "new_properties": "{'name': 'John'}",
                "namespace": "default",
                "document_id": "doc-456",
                "user_id": "system",
            },
            {
                "event_id": "evt-2",
                "timestamp": "2024-01-02T12:00:00",
                "event_type": "relationship_created",
                "entity_id": None,
                "entity_type": None,
                "relationship_id": "rel-789",
                "relationship_type": "WORKS_FOR",
                "old_properties": None,
                "new_properties": "{'since': '2024-01-01'}",
                "namespace": "default",
                "document_id": "doc-456",
                "user_id": "system",
            },
        ]
        mock_neo4j_client.execute_read.return_value = mock_records

        events = await audit_service.get_recent_changes("default", limit=50)

        assert len(events) == 2
        assert events[0].event_type == "entity_created"
        assert events[1].event_type == "relationship_created"

    @pytest.mark.asyncio
    async def test_get_recent_changes_filtered(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test querying recent changes with event type filter."""
        mock_records = [
            {
                "event_id": "evt-1",
                "timestamp": "2024-01-01T12:00:00",
                "event_type": "entity_created",
                "entity_id": "entity-123",
                "entity_type": "PERSON",
                "relationship_id": None,
                "relationship_type": None,
                "old_properties": None,
                "new_properties": "{'name': 'John'}",
                "namespace": "default",
                "document_id": "doc-456",
                "user_id": "system",
            },
        ]
        mock_neo4j_client.execute_read.return_value = mock_records

        events = await audit_service.get_recent_changes(
            "default",
            event_type="entity_created",
        )

        assert len(events) == 1
        assert events[0].event_type == "entity_created"

        # Verify filter was applied
        call_args = mock_neo4j_client.execute_read.call_args
        assert call_args[0][1]["event_type"] == "entity_created"

    @pytest.mark.asyncio
    async def test_get_changes_by_timerange(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test querying changes within time range."""
        mock_records = [
            {
                "event_id": "evt-1",
                "timestamp": "2024-01-01T12:00:00",
                "event_type": "entity_created",
                "entity_id": "entity-123",
                "entity_type": "PERSON",
                "relationship_id": None,
                "relationship_type": None,
                "old_properties": None,
                "new_properties": "{'name': 'John'}",
                "namespace": "default",
                "document_id": "doc-456",
                "user_id": "system",
            },
        ]
        mock_neo4j_client.execute_read.return_value = mock_records

        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 2, 0, 0, 0)

        events = await audit_service.get_changes_by_timerange(
            "default",
            start_time=start_time,
            end_time=end_time,
        )

        assert len(events) == 1
        assert events[0].event_type == "entity_created"

        # Verify time range was applied
        call_args = mock_neo4j_client.execute_read.call_args
        assert "datetime(e.timestamp) >=" in call_args[0][0]
        assert call_args[0][1]["start_time"] == start_time.isoformat()
        assert call_args[0][1]["end_time"] == end_time.isoformat()

    @pytest.mark.asyncio
    async def test_get_changes_by_timerange_with_filter(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test querying changes by time range with event type filter."""
        mock_neo4j_client.execute_read.return_value = []

        start_time = datetime(2024, 1, 1, 0, 0, 0)
        end_time = datetime(2024, 1, 2, 0, 0, 0)

        events = await audit_service.get_changes_by_timerange(
            "default",
            start_time=start_time,
            end_time=end_time,
            event_type="entity_updated",
        )

        assert len(events) == 0

        # Verify filter was applied
        call_args = mock_neo4j_client.execute_read.call_args
        assert call_args[0][1]["event_type"] == "entity_updated"

    @pytest.mark.asyncio
    async def test_query_failure(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test handling of Neo4j query failure."""
        mock_neo4j_client.execute_read.side_effect = Exception("Neo4j error")

        with pytest.raises(GraphQueryError):
            await audit_service.get_entity_history("entity-123", "default")


class TestAuditServiceIndexes:
    """Test index creation methods."""

    @pytest.mark.asyncio
    async def test_create_indexes_success(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test successful index creation."""
        mock_neo4j_client.execute_write.return_value = {}

        results = await audit_service.create_indexes()

        assert results["audit_event_id"] is True
        assert results["audit_event_timestamp"] is True
        assert results["audit_event_entity_id"] is True
        assert results["audit_event_namespace"] is True
        assert results["audit_event_type"] is True

        # Verify all indexes were created
        assert mock_neo4j_client.execute_write.call_count == 5

    @pytest.mark.asyncio
    async def test_create_indexes_partial_failure(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test handling of partial index creation failure."""

        # First call succeeds, second fails, rest succeed
        mock_neo4j_client.execute_write.side_effect = [
            {},  # Success
            Exception("Index error"),  # Failure
            {},  # Success
            {},  # Success
            {},  # Success
        ]

        results = await audit_service.create_indexes()

        # Should have mixed results
        assert results["audit_event_id"] is True
        assert results["audit_event_timestamp"] is False
        assert results["audit_event_entity_id"] is True


class TestAuditServiceSingleton:
    """Test singleton pattern."""

    def test_get_audit_service_singleton(self) -> None:
        """Test that get_audit_service returns singleton."""
        from src.domains.knowledge_graph.audit.audit_service import get_audit_service

        reset_audit_service()

        service1 = get_audit_service()
        service2 = get_audit_service()

        assert service1 is service2

    def test_reset_audit_service(self) -> None:
        """Test resetting singleton."""
        from src.domains.knowledge_graph.audit.audit_service import get_audit_service

        service1 = get_audit_service()
        reset_audit_service()
        service2 = get_audit_service()

        assert service1 is not service2


class TestAuditServicePerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_log_entity_change_overhead(
        self,
        audit_service: AuditService,
        mock_neo4j_client: MagicMock,
    ) -> None:
        """Test that audit logging completes within 10ms (excluding Neo4j time)."""
        import time

        mock_neo4j_client.execute_write.return_value = {"event_id": "evt-123"}

        start = time.perf_counter()
        await audit_service.log_entity_change(
            event_type="entity_created",
            entity_id="entity-123",
            entity_type="PERSON",
            new_properties={"name": "John Doe"},
            namespace="default",
            document_id="doc-456",
        )
        duration_ms = (time.perf_counter() - start) * 1000

        # Overhead should be < 10ms (excluding actual Neo4j write)
        # Since Neo4j is mocked, this tests our code overhead
        assert duration_ms < 10.0
