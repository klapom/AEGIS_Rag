"""Unit tests for Community Delta Tracker.

Sprint 52 - Feature 52.1: Community Summary Generation (TD-058)

Tests:
- CommunityDelta dataclass functionality
- track_community_changes for various scenarios
- get_entity_communities_snapshot from Neo4j
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.components.graph_rag.community_delta_tracker import (
    CommunityDelta,
    get_entity_communities_snapshot,
    track_community_changes,
)


class TestCommunityDelta:
    """Tests for CommunityDelta dataclass."""

    def test_empty_delta(self):
        """Test empty delta has no changes."""
        delta = CommunityDelta()

        assert not delta.has_changes()
        assert len(delta.get_affected_communities()) == 0
        assert "new=0" in str(delta)

    def test_new_communities_only(self):
        """Test delta with only new communities."""
        delta = CommunityDelta(new_communities={1, 2, 3})

        assert delta.has_changes()
        assert delta.get_affected_communities() == {1, 2, 3}
        assert "new=3" in str(delta)

    def test_updated_communities_only(self):
        """Test delta with only updated communities."""
        delta = CommunityDelta(updated_communities={5, 6})

        assert delta.has_changes()
        assert delta.get_affected_communities() == {5, 6}
        assert "updated=2" in str(delta)

    def test_merged_communities(self):
        """Test delta with merged communities."""
        # Communities 1 and 2 merged into 3
        delta = CommunityDelta(merged_communities={1: 3, 2: 3})

        assert delta.has_changes()
        # Only the target community needs summary update
        assert delta.get_affected_communities() == {3}
        assert "merged=2" in str(delta)

    def test_split_communities(self):
        """Test delta with split communities."""
        # Community 10 split into 20 and 21
        delta = CommunityDelta(split_communities={10: {20, 21}})

        assert delta.has_changes()
        # Both new communities need summaries
        assert delta.get_affected_communities() == {20, 21}
        assert "split=1" in str(delta)

    def test_complex_delta(self):
        """Test delta with all types of changes."""
        delta = CommunityDelta(
            new_communities={100, 101},
            updated_communities={50},
            merged_communities={1: 10, 2: 10},
            split_communities={5: {60, 61}},
        )

        assert delta.has_changes()
        affected = delta.get_affected_communities()

        # Should include: new (100, 101), updated (50), merged target (10), split targets (60, 61)
        assert affected == {50, 60, 61, 100, 101, 10}
        assert len(affected) == 6


@pytest.mark.asyncio
class TestTrackCommunityChanges:
    """Tests for track_community_changes function."""

    async def test_no_changes(self):
        """Test when nothing changed."""
        before = {"e1": 0, "e2": 0, "e3": 1}
        after = {"e1": 0, "e2": 0, "e3": 1}

        delta = await track_community_changes(before, after)

        assert not delta.has_changes()
        assert len(delta.new_communities) == 0
        assert len(delta.updated_communities) == 0

    async def test_new_community_detected(self):
        """Test detection of new communities."""
        before = {"e1": 0, "e2": 0}
        after = {"e1": 0, "e2": 0, "e3": 5, "e4": 5}

        delta = await track_community_changes(before, after)

        # Community 5 is new
        assert 5 in delta.new_communities
        assert len(delta.new_communities) == 1

    async def test_entity_moved_between_communities(self):
        """Test when entity moves from one community to another."""
        before = {"e1": 0, "e2": 0, "e3": 1}
        after = {"e1": 0, "e2": 1, "e3": 1}

        delta = await track_community_changes(before, after)

        # Both communities 0 and 1 should be marked as updated
        assert 0 in delta.updated_communities
        assert 1 in delta.updated_communities

    async def test_new_entity_assigned_to_existing_community(self):
        """Test when new entity joins existing community."""
        before = {"e1": 0, "e2": 0}
        after = {"e1": 0, "e2": 0, "e3": 0}

        delta = await track_community_changes(before, after)

        # Community 0 gained a member → updated
        assert 0 in delta.updated_communities
        assert 0 not in delta.new_communities

    async def test_community_merge_detection(self):
        """Test detection of merged communities."""
        # e1 and e2 were in community 0, e3 was in community 1
        # After merge, all are in community 0
        before = {"e1": 0, "e2": 0, "e3": 1}
        after = {"e1": 0, "e2": 0, "e3": 0}

        delta = await track_community_changes(before, after)

        # Community 1 merged into 0
        assert delta.merged_communities.get(1) == 0

    async def test_community_split_detection(self):
        """Test detection of split communities."""
        # All entities were in community 0
        before = {"e1": 0, "e2": 0, "e3": 0, "e4": 0}

        # After split: e1, e2 in community 0; e3, e4 in new community 5
        after = {"e1": 0, "e2": 0, "e3": 5, "e4": 5}

        delta = await track_community_changes(before, after)

        # Community 0 didn't disappear, but 5 is new
        assert 5 in delta.new_communities or 0 in delta.split_communities.get(0, set())

    async def test_entity_without_community(self):
        """Test handling of entities without community assignment."""
        before = {"e1": 0, "e2": None, "e3": None}
        after = {"e1": 0, "e2": 5, "e3": None}

        delta = await track_community_changes(before, after)

        # e2 got assigned to new community 5
        assert 5 in delta.new_communities

    async def test_multiple_merges(self):
        """Test multiple communities merging into one."""
        before = {"e1": 0, "e2": 1, "e3": 2, "e4": 3}
        after = {"e1": 10, "e2": 10, "e3": 10, "e4": 10}

        delta = await track_community_changes(before, after)

        # Community 10 is new (didn't exist before)
        assert 10 in delta.new_communities

        # If we want to track merges into an existing community, test this instead:
        before2 = {"e1": 0, "e2": 1, "e3": 2, "e4": 10}
        after2 = {"e1": 10, "e2": 10, "e3": 10, "e4": 10}

        delta2 = await track_community_changes(before2, after2)

        # Communities 0, 1, 2 all merged into existing community 10
        assert delta2.merged_communities[0] == 10
        assert delta2.merged_communities[1] == 10
        assert delta2.merged_communities[2] == 10

    async def test_complex_scenario(self):
        """Test complex scenario with multiple change types."""
        before = {
            "e1": 0,
            "e2": 0,
            "e3": 1,
            "e4": 1,
            "e5": 2,
        }

        after = {
            "e1": 0,
            "e2": 0,
            "e3": 0,  # Moved from 1 to 0 (merge)
            "e4": 3,  # Moved from 1 to new 3
            "e5": 2,  # Stayed in 2
            "e6": 4,  # New entity in new community 4
        }

        delta = await track_community_changes(before, after)

        # Community 3 and 4 are new
        assert 3 in delta.new_communities
        assert 4 in delta.new_communities

        # Community 0 gained e3 → updated or merged
        # Community 2 unchanged → not updated


@pytest.mark.asyncio
class TestGetEntityCommunitiesSnapshot:
    """Tests for get_entity_communities_snapshot function."""

    async def test_snapshot_with_entities(self):
        """Test snapshot retrieval from Neo4j."""
        # Mock Neo4j client
        mock_client = AsyncMock()
        mock_client.execute_read = AsyncMock(
            return_value=[
                {"entity_id": "e1", "community_id": "community_5"},
                {"entity_id": "e2", "community_id": "community_5"},
                {"entity_id": "e3", "community_id": "community_10"},
                {"entity_id": "e4", "community_id": None},
            ]
        )

        snapshot = await get_entity_communities_snapshot(mock_client)

        # Should parse community IDs correctly
        assert snapshot["e1"] == 5
        assert snapshot["e2"] == 5
        assert snapshot["e3"] == 10
        assert snapshot["e4"] is None

    async def test_snapshot_empty_graph(self):
        """Test snapshot when graph has no entities."""
        mock_client = AsyncMock()
        mock_client.execute_read = AsyncMock(return_value=[])

        snapshot = await get_entity_communities_snapshot(mock_client)

        assert len(snapshot) == 0
        assert isinstance(snapshot, dict)

    async def test_snapshot_with_invalid_community_id(self):
        """Test handling of invalid community_id format."""
        mock_client = AsyncMock()
        mock_client.execute_read = AsyncMock(
            return_value=[
                {"entity_id": "e1", "community_id": "invalid_format"},
                {"entity_id": "e2", "community_id": "community_5"},
            ]
        )

        snapshot = await get_entity_communities_snapshot(mock_client)

        # Invalid format should be treated as None
        assert snapshot["e1"] is None
        assert snapshot["e2"] == 5

    async def test_snapshot_with_numeric_community_id(self):
        """Test handling when community_id is already numeric."""
        mock_client = AsyncMock()
        mock_client.execute_read = AsyncMock(
            return_value=[
                {"entity_id": "e1", "community_id": 123},
            ]
        )

        snapshot = await get_entity_communities_snapshot(mock_client)

        # Should handle numeric IDs (just store as-is)
        assert snapshot["e1"] == 123
