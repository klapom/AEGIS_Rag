"""Unit tests for VersionManager."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.components.graph_rag.version_manager import VersionManager, get_version_manager


@pytest.fixture
def mock_neo4j_client():
    """Create mock Neo4j client."""
    client = MagicMock()
    client.execute_read = AsyncMock(return_value=[])
    # Default return value for execute_write to prevent coroutine errors
    client.execute_write = AsyncMock(return_value={"nodes_created": 0, "properties_set": 0})
    return client


@pytest.fixture
def version_manager(mock_neo4j_client):
    """Create VersionManager with mock client."""
    return VersionManager(neo4j_client=mock_neo4j_client, retention_count=10)


class TestVersionManagerInit:
    """Test VersionManager initialization."""

    def test_init_with_defaults(self, mock_neo4j_client):
        """Test initialization with default settings."""
        manager = VersionManager(neo4j_client=mock_neo4j_client)
        assert manager.client == mock_neo4j_client
        assert manager.retention_count >= 0

    def test_init_with_custom_retention(self, mock_neo4j_client):
        """Test initialization with custom retention count."""
        manager = VersionManager(neo4j_client=mock_neo4j_client, retention_count=5)
        assert manager.retention_count == 5

    def test_singleton_instance(self):
        """Test singleton pattern."""
        manager1 = get_version_manager()
        manager2 = get_version_manager()
        assert manager1 is manager2


@pytest.mark.asyncio
class TestCreateVersion:
    """Test create_version method."""

    async def test_create_first_version(self, version_manager, mock_neo4j_client):
        """Test creating first version of an entity."""
        mock_neo4j_client.execute_read.return_value = []  # No existing versions
        mock_neo4j_client.execute_write.return_value = {
            "nodes_created": 1,
            "properties_set": 10,
        }

        entity = {"id": "test_entity", "name": "Test Entity", "type": "PERSON"}
        result = await version_manager.create_version(entity, changed_by="user1")

        assert result["version_number"] == 1
        assert result["version_id"] is not None
        assert result["changed_by"] == "user1"
        assert result["valid_to"] is None
        assert result["transaction_to"] is None

    async def test_create_second_version(self, version_manager, mock_neo4j_client):
        """Test creating second version of an entity."""
        # Mock existing version
        mock_neo4j_client.execute_read.return_value = [
            {"e": {"version_number": 1, "version_id": "v1"}}
        ]
        mock_neo4j_client.execute_write.return_value = {
            "nodes_created": 1,
            "properties_set": 10,
        }

        entity = {"id": "test_entity", "name": "Test Entity Updated", "type": "PERSON"}
        result = await version_manager.create_version(
            entity, changed_by="user2", change_reason="Updated name"
        )

        assert result["version_number"] == 2
        assert result["changed_by"] == "user2"
        assert result["change_reason"] == "Updated name"

    async def test_create_version_missing_id(self, version_manager):
        """Test creating version without entity ID or name raises error."""
        entity = {"type": "PERSON"}  # Missing both 'id' and 'name'
        with pytest.raises(ValueError, match="Entity must have 'id' or 'name' field"):
            await version_manager.create_version(entity)

    async def test_create_version_with_name_as_id(self, version_manager, mock_neo4j_client):
        """Test creating version using name as ID."""
        mock_neo4j_client.execute_read.return_value = []
        mock_neo4j_client.execute_write.return_value = {"nodes_created": 1}

        entity = {"name": "Test Entity", "type": "PERSON"}  # No 'id', use 'name'
        result = await version_manager.create_version(entity)

        assert result["version_number"] == 1
        assert "name" in result

    async def test_create_version_closes_old_version(self, version_manager, mock_neo4j_client):
        """Test that old version is closed when creating new version."""
        mock_neo4j_client.execute_read.return_value = [
            {"e": {"version_number": 5, "version_id": "v5"}}
        ]
        mock_neo4j_client.execute_write.return_value = {"nodes_created": 1}

        entity = {"id": "test_entity", "name": "Test"}
        await version_manager.create_version(entity)

        # Check that close query was executed
        calls = mock_neo4j_client.execute_write.call_args_list
        assert len(calls) >= 2  # Close old + create new
        close_call_query = calls[0][0][0]
        assert "valid_to" in close_call_query
        assert "transaction_to" in close_call_query


@pytest.mark.asyncio
class TestGetVersions:
    """Test get_versions method."""

    async def test_get_all_versions(self, version_manager, mock_neo4j_client):
        """Test retrieving all versions."""
        mock_versions = [
            {"e": {"id": "test", "version_number": 3, "name": "V3"}},
            {"e": {"id": "test", "version_number": 2, "name": "V2"}},
            {"e": {"id": "test", "version_number": 1, "name": "V1"}},
        ]
        mock_neo4j_client.execute_read.return_value = mock_versions

        versions = await version_manager.get_versions("test_entity")

        assert len(versions) == 3
        assert versions[0]["version_number"] == 3
        assert versions[-1]["version_number"] == 1

    async def test_get_versions_with_limit(self, version_manager, mock_neo4j_client):
        """Test retrieving limited number of versions."""
        mock_versions = [{"e": {"id": "test", "version_number": 5, "name": "V5"}}]
        mock_neo4j_client.execute_read.return_value = mock_versions

        versions = await version_manager.get_versions("test_entity", limit=1)

        assert len(versions) == 1
        # Check that LIMIT was in query
        call_args = mock_neo4j_client.execute_read.call_args
        assert "LIMIT" in call_args[0][0]

    async def test_get_versions_empty(self, version_manager, mock_neo4j_client):
        """Test retrieving versions for non-existent entity."""
        mock_neo4j_client.execute_read.return_value = []

        versions = await version_manager.get_versions("nonexistent")

        assert len(versions) == 0


@pytest.mark.asyncio
class TestGetVersionAt:
    """Test get_version_at method."""

    async def test_get_version_at_timestamp(self, version_manager, mock_neo4j_client):
        """Test retrieving version at specific timestamp."""
        mock_version = {"e": {"id": "test", "version_number": 2, "name": "V2"}}
        mock_neo4j_client.execute_read.return_value = [mock_version]

        timestamp = datetime(2025, 1, 15, 10, 0, 0)
        version = await version_manager.get_version_at("test_entity", timestamp)

        assert version is not None
        assert version["version_number"] == 2

    async def test_get_version_at_not_found(self, version_manager, mock_neo4j_client):
        """Test retrieving version when none exists at timestamp."""
        mock_neo4j_client.execute_read.return_value = []

        timestamp = datetime(2025, 1, 15, 10, 0, 0)
        version = await version_manager.get_version_at("test_entity", timestamp)

        assert version is None


@pytest.mark.asyncio
class TestCompareVersions:
    """Test compare_versions method."""

    async def test_compare_two_versions(self, version_manager, mock_neo4j_client):
        """Test comparing two versions."""
        mock_versions = [
            {
                "e": {
                    "id": "test",
                    "version_number": 1,
                    "name": "Original",
                    "description": "First version",
                }
            },
            {
                "e": {
                    "id": "test",
                    "version_number": 2,
                    "name": "Updated",
                    "description": "First version",
                }
            },
        ]
        mock_neo4j_client.execute_read.return_value = mock_versions

        result = await version_manager.compare_versions("test_entity", 1, 2)

        assert result["entity_id"] == "test_entity"
        assert result["version1"] == 1
        assert result["version2"] == 2
        assert "name" in result["changed_fields"]
        assert len(result["changed_fields"]) == 1
        assert result["differences"]["name"]["from"] == "Original"
        assert result["differences"]["name"]["to"] == "Updated"

    async def test_compare_insufficient_versions(self, version_manager, mock_neo4j_client):
        """Test comparing when versions not found."""
        mock_neo4j_client.execute_read.return_value = [
            {"e": {"id": "test", "version_number": 1}}
        ]

        result = await version_manager.compare_versions("test_entity", 1, 2)

        assert "error" in result
        assert "Insufficient versions" in result["error"]


@pytest.mark.asyncio
class TestGetEvolution:
    """Test get_evolution method."""

    async def test_get_evolution(self, version_manager, mock_neo4j_client):
        """Test retrieving evolution timeline."""
        mock_versions = [
            {
                "version_number": 3,
                "version_id": "v3",
                "valid_from": "2025-01-15T12:00:00",
                "valid_to": None,
                "changed_by": "user1",
                "change_reason": "Update 2",
                "name": "V3",
            },
            {
                "version_number": 2,
                "version_id": "v2",
                "valid_from": "2025-01-15T11:00:00",
                "valid_to": "2025-01-15T12:00:00",
                "changed_by": "user1",
                "change_reason": "Update 1",
                "name": "V2",
            },
            {
                "version_number": 1,
                "version_id": "v1",
                "valid_from": "2025-01-15T10:00:00",
                "valid_to": "2025-01-15T11:00:00",
                "changed_by": "system",
                "change_reason": "Initial",
                "name": "V1",
            },
        ]

        with patch.object(version_manager, "get_versions", return_value=mock_versions):
            evolution = await version_manager.get_evolution("test_entity")

        assert evolution["entity_id"] == "test_entity"
        assert evolution["version_count"] == 3
        assert len(evolution["timeline"]) == 3
        assert evolution["timeline"][0]["version_number"] == 1  # Oldest first

    async def test_get_evolution_empty(self, version_manager, mock_neo4j_client):
        """Test getting evolution for non-existent entity."""
        with patch.object(version_manager, "get_versions", return_value=[]):
            evolution = await version_manager.get_evolution("nonexistent")

        assert evolution["version_count"] == 0
        assert len(evolution["timeline"]) == 0
        assert evolution["first_seen"] is None


@pytest.mark.asyncio
class TestRevertToVersion:
    """Test revert_to_version method."""

    async def test_revert_to_version(self, version_manager, mock_neo4j_client):
        """Test reverting to a previous version."""
        mock_target_version = {
            "e": {
                "id": "test",
                "version_id": "v1",
                "version_number": 1,
                "name": "Original",
                "type": "PERSON",
                "valid_from": "2025-01-15T10:00:00",
            }
        }
        mock_neo4j_client.execute_read.return_value = [mock_target_version]

        with patch.object(
            version_manager,
            "create_version",
            return_value={"version_id": "v4", "version_number": 4},
        ):
            result = await version_manager.revert_to_version(
                "test_entity", "v1", changed_by="admin", change_reason="Rollback"
            )

        assert result["version_number"] == 4
        assert result["version_id"] == "v4"

    async def test_revert_to_nonexistent_version(self, version_manager, mock_neo4j_client):
        """Test reverting to non-existent version raises error."""
        mock_neo4j_client.execute_read.return_value = []

        with pytest.raises(ValueError, match="Version .* not found"):
            await version_manager.revert_to_version("test_entity", "nonexistent")


@pytest.mark.asyncio
class TestEnforceRetention:
    """Test version retention policy."""

    async def test_enforce_retention(self, version_manager, mock_neo4j_client):
        """Test enforcing retention policy."""
        mock_neo4j_client.execute_write.return_value = {"properties_set": 5}

        deleted = await version_manager._enforce_retention("test_entity")

        assert deleted == 5
        # Check that retention query was executed
        call_args = mock_neo4j_client.execute_write.call_args
        assert "SKIP" in call_args[0][0]
        assert "retention_count" in call_args[0][1]

    async def test_no_retention_limit(self):
        """Test with no retention limit (0)."""
        # Create fresh mock to ensure no prior calls
        client = MagicMock()
        client.execute_read = AsyncMock(return_value=[])
        client.execute_write = AsyncMock(return_value={"nodes_created": 0, "properties_set": 0})

        manager = VersionManager(neo4j_client=client, retention_count=0)

        deleted = await manager._enforce_retention("test_entity")

        assert deleted == 0
        # With retention_count=0, _enforce_retention returns early and never calls execute_write
        client.execute_write.assert_not_called()


@pytest.mark.asyncio
class TestVersionManagerEdgeCases:
    """Test edge cases and error handling."""

    async def test_concurrent_version_creation(self, version_manager, mock_neo4j_client):
        """Test handling concurrent version creation."""
        # Simulate sequential version increments: first call sees v5, second sees v6
        mock_neo4j_client.execute_read.side_effect = [
            [{"e": {"version_number": 5, "version_id": "v5"}}],  # First create_version call
            [{"e": {"version_number": 6, "version_id": "v6"}}],  # Second create_version call
        ]
        mock_neo4j_client.execute_write.return_value = {"nodes_created": 1}

        entity = {"id": "test", "name": "Test"}

        # Create multiple versions sequentially (simulates concurrent behavior via mocks)
        v1 = await version_manager.create_version(entity)
        v2 = await version_manager.create_version(entity)

        # Version numbers should increment
        assert v2["version_number"] > v1["version_number"]

    async def test_version_with_complex_properties(self, version_manager, mock_neo4j_client):
        """Test creating version with complex nested properties."""
        mock_neo4j_client.execute_read.return_value = []
        mock_neo4j_client.execute_write.return_value = {"nodes_created": 1}

        entity = {
            "id": "test",
            "name": "Complex Entity",
            "properties": {"nested": {"key": "value"}, "list": [1, 2, 3]},
            "metadata": {"tags": ["a", "b"]},
        }

        result = await version_manager.create_version(entity)
        assert result["version_number"] == 1
        assert "properties" in result
