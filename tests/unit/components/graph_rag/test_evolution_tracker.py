"""Unit tests for EvolutionTracker."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.components.graph_rag.evolution_tracker import (
    ChangeEvent,
    EvolutionTracker,
    get_evolution_tracker,
)


@pytest.fixture
def mock_neo4j_client():
    """Create mock Neo4j client."""
    client = MagicMock()
    client.execute_read = AsyncMock()
    client.execute_write = AsyncMock()
    return client


@pytest.fixture
def evolution_tracker(mock_neo4j_client):
    """Create EvolutionTracker with mock client."""
    return EvolutionTracker(neo4j_client=mock_neo4j_client)


class TestChangeEvent:
    """Test ChangeEvent model."""

    def test_create_change_event(self):
        """Test creating a ChangeEvent."""
        event = ChangeEvent(
            entity_id="test_entity",
            version_from=1,
            version_to=2,
            timestamp=datetime.utcnow(),
            changed_fields=["name", "description"],
            change_type="update",
            changed_by="user1",
            reason="Updated entity",
        )

        assert event.entity_id == "test_entity"
        assert event.version_from == 1
        assert event.version_to == 2
        assert len(event.changed_fields) == 2
        assert event.change_type == "update"

    def test_change_event_minimal(self):
        """Test creating ChangeEvent with minimal fields."""
        event = ChangeEvent(
            entity_id="test",
            version_from=0,
            version_to=1,
            timestamp=datetime.utcnow(),
            changed_fields=[],
            change_type="create",
            changed_by="system",
        )

        assert event.reason == ""  # Default value


class TestEvolutionTrackerInit:
    """Test EvolutionTracker initialization."""

    def test_init_with_client(self, mock_neo4j_client):
        """Test initialization with provided client."""
        tracker = EvolutionTracker(neo4j_client=mock_neo4j_client)
        assert tracker.client == mock_neo4j_client

    def test_singleton_instance(self):
        """Test singleton pattern."""
        tracker1 = get_evolution_tracker()
        tracker2 = get_evolution_tracker()
        assert tracker1 is tracker2


@pytest.mark.asyncio
class TestTrackChanges:
    """Test track_changes method."""

    async def test_track_create(self, evolution_tracker, mock_neo4j_client):
        """Test tracking entity creation."""
        mock_neo4j_client.execute_write.return_value = {}

        new_version = {
            "id": "test_entity",
            "version_number": 1,
            "name": "New Entity",
            "changed_by": "user1",
            "change_reason": "Initial creation",
        }

        event = await evolution_tracker.track_changes("test_entity", None, new_version)

        assert event.change_type == "create"
        assert event.version_from == 0
        assert event.version_to == 1
        assert event.changed_by == "user1"
        assert len(event.changed_fields) > 0

    async def test_track_update(self, evolution_tracker, mock_neo4j_client):
        """Test tracking entity update."""
        mock_neo4j_client.execute_write.return_value = {}

        old_version = {
            "id": "test_entity",
            "version_number": 1,
            "name": "Old Name",
            "description": "Old description",
        }

        new_version = {
            "id": "test_entity",
            "version_number": 2,
            "name": "New Name",
            "description": "Old description",
            "changed_by": "user2",
            "change_reason": "Updated name",
        }

        event = await evolution_tracker.track_changes("test_entity", old_version, new_version)

        assert event.change_type == "update"
        assert event.version_from == 1
        assert event.version_to == 2
        assert "name" in event.changed_fields
        assert "description" not in event.changed_fields

    async def test_track_no_changes(self, evolution_tracker, mock_neo4j_client):
        """Test tracking when no fields changed."""
        mock_neo4j_client.execute_write.return_value = {}

        old_version = {"id": "test", "version_number": 1, "name": "Same"}
        new_version = {"id": "test", "version_number": 2, "name": "Same"}

        event = await evolution_tracker.track_changes("test", old_version, new_version)

        assert event.change_type == "update"
        assert len(event.changed_fields) == 0


@pytest.mark.asyncio
class TestGetChangeLog:
    """Test get_change_log method."""

    async def test_get_change_log(self, evolution_tracker, mock_neo4j_client):
        """Test retrieving change log."""
        now = datetime.utcnow()
        mock_changes = [
            {
                "c": {
                    "entity_id": "test",
                    "version_from": 2,
                    "version_to": 3,
                    "timestamp": now,
                    "changed_fields": ["name"],
                    "change_type": "update",
                }
            },
            {
                "c": {
                    "entity_id": "test",
                    "version_from": 1,
                    "version_to": 2,
                    "timestamp": now - timedelta(hours=1),
                    "changed_fields": ["description"],
                    "change_type": "update",
                }
            },
        ]
        mock_neo4j_client.execute_read.return_value = mock_changes

        changes = await evolution_tracker.get_change_log("test_entity", limit=50)

        assert len(changes) == 2
        assert changes[0]["version_to"] == 3
        assert changes[1]["version_to"] == 2

    async def test_get_change_log_empty(self, evolution_tracker, mock_neo4j_client):
        """Test retrieving change log for entity with no changes."""
        mock_neo4j_client.execute_read.return_value = []

        changes = await evolution_tracker.get_change_log("nonexistent")

        assert len(changes) == 0


@pytest.mark.asyncio
class TestGetChangeStatistics:
    """Test get_change_statistics method."""

    async def test_get_statistics(self, evolution_tracker, mock_neo4j_client):
        """Test retrieving change statistics."""
        first_change = datetime(2025, 1, 1, 0, 0, 0)
        last_change = datetime(2025, 1, 31, 0, 0, 0)

        mock_result = [
            {
                "total_changes": 15,
                "first_change": first_change,
                "last_change": last_change,
                "changes": [
                    {"changed_fields": ["name", "description"]},
                    {"changed_fields": ["name"]},
                    {"changed_fields": ["description", "type"]},
                ],
            }
        ]
        mock_neo4j_client.execute_read.return_value = mock_result

        stats = await evolution_tracker.get_change_statistics("test_entity")

        assert stats["entity_id"] == "test_entity"
        assert stats["total_changes"] == 15
        assert stats["change_frequency"] > 0
        assert len(stats["most_changed_fields"]) > 0

    async def test_get_statistics_no_changes(self, evolution_tracker, mock_neo4j_client):
        """Test statistics for entity with no changes."""
        mock_neo4j_client.execute_read.return_value = [{"total_changes": 0}]

        stats = await evolution_tracker.get_change_statistics("test_entity")

        assert stats["total_changes"] == 0
        assert stats["change_frequency"] == 0.0
        assert len(stats["most_changed_fields"]) == 0


@pytest.mark.asyncio
class TestDetectDrift:
    """Test detect_drift method."""

    async def test_detect_high_drift(self, evolution_tracker, mock_neo4j_client):
        """Test detecting high drift (>1 change/day)."""
        mock_result = [
            {
                "recent_changes": 35,  # 35 changes in 30 days = 1.17/day
                "all_changed_fields": [["name"], ["description"], ["type"]],
            }
        ]
        mock_neo4j_client.execute_read.return_value = mock_result

        drift = await evolution_tracker.detect_drift("test_entity", days=30)

        assert drift["entity_id"] == "test_entity"
        assert drift["recent_changes"] == 35
        assert drift["change_rate"] > 1.0
        assert drift["drift_detected"] is True
        assert drift["alert_level"] == "high"

    async def test_detect_medium_drift(self, evolution_tracker, mock_neo4j_client):
        """Test detecting medium drift (>0.5 change/day)."""
        mock_result = [
            {
                "recent_changes": 20,  # 20 changes in 30 days = 0.67/day
                "all_changed_fields": [["name"], ["description"]],
            }
        ]
        mock_neo4j_client.execute_read.return_value = mock_result

        drift = await evolution_tracker.detect_drift("test_entity", days=30)

        assert drift["change_rate"] > 0.5
        assert drift["drift_detected"] is True
        assert drift["alert_level"] == "medium"

    async def test_detect_no_drift(self, evolution_tracker, mock_neo4j_client):
        """Test detecting no drift (<=0.5 change/day)."""
        mock_result = [
            {
                "recent_changes": 10,  # 10 changes in 30 days = 0.33/day
                "all_changed_fields": [["name"]],
            }
        ]
        mock_neo4j_client.execute_read.return_value = mock_result

        drift = await evolution_tracker.detect_drift("test_entity", days=30)

        assert drift["change_rate"] <= 0.5
        assert drift["drift_detected"] is False
        assert drift["alert_level"] == "normal"

    async def test_detect_drift_no_changes(self, evolution_tracker, mock_neo4j_client):
        """Test drift detection with no recent changes."""
        mock_neo4j_client.execute_read.return_value = []

        drift = await evolution_tracker.detect_drift("test_entity", days=30)

        assert drift["recent_changes"] == 0
        assert drift["change_rate"] == 0.0
        assert drift["drift_detected"] is False


@pytest.mark.asyncio
class TestGetStableEntities:
    """Test get_stable_entities method."""

    async def test_get_stable_entities(self, evolution_tracker, mock_neo4j_client):
        """Test retrieving stable entities."""
        mock_entities = [
            {
                "entity_id": "stable1",
                "name": "Stable Entity 1",
                "type": "PERSON",
                "created_at": datetime(2024, 1, 1),
                "version": 1,
            },
            {
                "entity_id": "stable2",
                "name": "Stable Entity 2",
                "type": "ORGANIZATION",
                "created_at": datetime(2024, 2, 1),
                "version": 1,
            },
        ]
        mock_neo4j_client.execute_read.return_value = mock_entities

        stable = await evolution_tracker.get_stable_entities(min_age_days=30, limit=100)

        assert len(stable) == 2
        assert stable[0]["entity_id"] == "stable1"
        assert stable[1]["entity_id"] == "stable2"

    async def test_get_stable_entities_empty(self, evolution_tracker, mock_neo4j_client):
        """Test when no stable entities found."""
        mock_neo4j_client.execute_read.return_value = []

        stable = await evolution_tracker.get_stable_entities(min_age_days=30)

        assert len(stable) == 0


@pytest.mark.asyncio
class TestGetActiveEntities:
    """Test get_active_entities method."""

    async def test_get_active_entities(self, evolution_tracker, mock_neo4j_client):
        """Test retrieving active entities."""
        mock_entities = [
            {
                "entity_id": "active1",
                "name": "Active Entity 1",
                "type": "PERSON",
                "change_count": 10,
            },
            {
                "entity_id": "active2",
                "name": "Active Entity 2",
                "type": "ORGANIZATION",
                "change_count": 5,
            },
        ]
        mock_neo4j_client.execute_read.return_value = mock_entities

        active = await evolution_tracker.get_active_entities(days=7, min_changes=3, limit=100)

        assert len(active) == 2
        assert active[0]["change_count"] == 10
        assert active[1]["change_count"] == 5
        assert active[0]["days_analyzed"] == 7

    async def test_get_active_entities_empty(self, evolution_tracker, mock_neo4j_client):
        """Test when no active entities found."""
        mock_neo4j_client.execute_read.return_value = []

        active = await evolution_tracker.get_active_entities(days=7, min_changes=5)

        assert len(active) == 0


@pytest.mark.asyncio
class TestEvolutionTrackerEdgeCases:
    """Test edge cases and error handling."""

    async def test_track_changes_with_null_fields(self, evolution_tracker, mock_neo4j_client):
        """Test tracking changes with None/null values."""
        mock_neo4j_client.execute_write.return_value = {}

        old_version = {"id": "test", "version_number": 1, "name": "Test", "description": None}
        new_version = {
            "id": "test",
            "version_number": 2,
            "name": "Test",
            "description": "New description",
        }

        event = await evolution_tracker.track_changes("test", old_version, new_version)

        assert "description" in event.changed_fields

    async def test_drift_detection_edge_window(self, evolution_tracker, mock_neo4j_client):
        """Test drift detection with very small time window."""
        mock_result = [{"recent_changes": 5, "all_changed_fields": [["name"]]}]
        mock_neo4j_client.execute_read.return_value = mock_result

        drift = await evolution_tracker.detect_drift("test_entity", days=1)

        assert drift["days_analyzed"] == 1
        assert drift["change_rate"] == 5.0  # 5 changes per day
        assert drift["alert_level"] == "high"

    async def test_statistics_single_change(self, evolution_tracker, mock_neo4j_client):
        """Test statistics with only one change."""
        single_change = datetime.utcnow()
        mock_result = [
            {
                "total_changes": 1,
                "first_change": single_change,
                "last_change": single_change,
                "changes": [{"changed_fields": ["name"]}],
            }
        ]
        mock_neo4j_client.execute_read.return_value = mock_result

        stats = await evolution_tracker.get_change_statistics("test_entity")

        assert stats["total_changes"] == 1
        # Single change should have minimal frequency calculation
        assert stats["change_frequency"] >= 0
