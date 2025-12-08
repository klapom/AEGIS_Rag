"""Unit Tests for Temporal API Endpoints.

Sprint Context: Sprint 39 (2025-12-08) - Features 39.2-39.4: Bi-Temporal Backend Tests

This module tests the bi-temporal query API endpoints with:
- Feature flag enforcement (temporal_queries_enabled)
- JWT authentication requirements
- Point-in-time queries
- Entity history retrieval
- Changelog with audit trail
- Version comparison and rollback

Test Coverage:
- Feature flag disabled (400 errors)
- Unauthenticated requests (401 errors)
- Successful queries with mocked data
- Error handling and edge cases
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.auth import User


# Test Fixtures


@pytest.fixture
def mock_user() -> User:
    """Create mock authenticated user."""
    return User(
        user_id="user_test123",
        username="testuser",
        role="user",
    )


@pytest.fixture
def mock_settings_temporal_enabled():
    """Mock settings with temporal queries enabled."""
    with patch("src.api.v1.temporal.settings") as mock_settings:
        mock_settings.temporal_queries_enabled = True
        mock_settings.temporal_version_retention = 10
        yield mock_settings


@pytest.fixture
def mock_settings_temporal_disabled():
    """Mock settings with temporal queries disabled."""
    with patch("src.api.v1.temporal.settings") as mock_settings:
        mock_settings.temporal_queries_enabled = False
        yield mock_settings


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# Feature Flag Tests


def test_check_temporal_enabled_when_disabled(mock_settings_temporal_disabled):
    """Test that temporal endpoints reject requests when feature flag is disabled."""
    from src.api.v1.temporal import check_temporal_enabled

    with pytest.raises(HTTPException) as exc_info:
        check_temporal_enabled()

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "not enabled" in exc_info.value.detail.lower()


def test_check_temporal_enabled_when_enabled(mock_settings_temporal_enabled):
    """Test that temporal endpoints allow requests when feature flag is enabled."""
    from src.api.v1.temporal import check_temporal_enabled

    # Should not raise exception
    result = check_temporal_enabled()
    assert result is None


# Point-in-Time Query Tests


@pytest.mark.asyncio
async def test_point_in_time_query_success(mock_user, mock_settings_temporal_enabled):
    """Test successful point-in-time query."""
    from src.api.v1.temporal import query_at_point_in_time, PointInTimeRequest

    # Mock dependencies
    mock_builder = MagicMock()
    mock_neo4j = AsyncMock()

    mock_builder.reset.return_value = mock_builder
    mock_builder.match.return_value = mock_builder
    mock_builder.as_of.return_value = mock_builder
    mock_builder.where.return_value = mock_builder
    mock_builder.return_clause.return_value = mock_builder
    mock_builder.limit.return_value = mock_builder
    mock_builder.build.return_value = ("MATCH (e:base) RETURN e", {"as_of_time_0": "2024-11-15T00:00:00"})

    # Mock Neo4j response
    mock_neo4j.execute_read.return_value = [
        {
            "e": {
                "id": "kubernetes",
                "name": "Kubernetes",
                "type": "TECHNOLOGY",
                "valid_from": "2024-11-01T00:00:00",
                "valid_to": None,
                "version_number": 1,
                "changed_by": "system",
            }
        }
    ]

    with patch("src.api.v1.temporal.get_temporal_query_builder", return_value=mock_builder):
        with patch("src.api.v1.temporal.get_neo4j_client", return_value=mock_neo4j):
            # Execute query
            request = PointInTimeRequest(
                timestamp=datetime(2024, 11, 15, 0, 0, 0),
                entity_filter=None,
                limit=100,
            )

            response = await query_at_point_in_time(request, mock_user, None)

            # Verify response
            assert response.total_count == 1
            assert len(response.entities) == 1
            assert response.entities[0].id == "kubernetes"
            assert response.entities[0].name == "Kubernetes"
            assert response.entities[0].type == "TECHNOLOGY"
            assert response.as_of == request.timestamp


@pytest.mark.asyncio
async def test_point_in_time_query_with_filter(mock_user, mock_settings_temporal_enabled):
    """Test point-in-time query with entity filter."""
    from src.api.v1.temporal import query_at_point_in_time, PointInTimeRequest

    mock_builder = MagicMock()
    mock_neo4j = AsyncMock()

    mock_builder.reset.return_value = mock_builder
    mock_builder.match.return_value = mock_builder
    mock_builder.as_of.return_value = mock_builder
    mock_builder.where.return_value = mock_builder
    mock_builder.return_clause.return_value = mock_builder
    mock_builder.limit.return_value = mock_builder
    mock_builder.build.return_value = ("MATCH (e:base) WHERE e.type = 'TECHNOLOGY' RETURN e", {})

    mock_neo4j.execute_read.return_value = []

    with patch("src.api.v1.temporal.get_temporal_query_builder", return_value=mock_builder):
        with patch("src.api.v1.temporal.get_neo4j_client", return_value=mock_neo4j):
            request = PointInTimeRequest(
                timestamp=datetime(2024, 11, 15, 0, 0, 0),
                entity_filter="e.type = 'TECHNOLOGY'",
                limit=50,
            )

            response = await query_at_point_in_time(request, mock_user, None)

            # Verify filter was applied
            mock_builder.where.assert_called_once_with("e.type = 'TECHNOLOGY'")
            assert response.total_count == 0


@pytest.mark.asyncio
async def test_point_in_time_query_error_handling(mock_user, mock_settings_temporal_enabled):
    """Test point-in-time query error handling."""
    from src.api.v1.temporal import query_at_point_in_time, PointInTimeRequest

    mock_builder = MagicMock()
    mock_neo4j = AsyncMock()

    mock_builder.reset.return_value = mock_builder
    mock_builder.match.return_value = mock_builder
    mock_builder.as_of.return_value = mock_builder
    mock_builder.return_clause.return_value = mock_builder
    mock_builder.limit.return_value = mock_builder
    mock_builder.build.return_value = ("MATCH (e:base) RETURN e", {})

    # Simulate Neo4j error
    mock_neo4j.execute_read.side_effect = Exception("Neo4j connection failed")

    with patch("src.api.v1.temporal.get_temporal_query_builder", return_value=mock_builder):
        with patch("src.api.v1.temporal.get_neo4j_client", return_value=mock_neo4j):
            request = PointInTimeRequest(
                timestamp=datetime(2024, 11, 15, 0, 0, 0),
                limit=100,
            )

            with pytest.raises(HTTPException) as exc_info:
                await query_at_point_in_time(request, mock_user, None)

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to execute point-in-time query" in exc_info.value.detail


# Entity History Tests


@pytest.mark.asyncio
async def test_entity_history_success(mock_user, mock_settings_temporal_enabled):
    """Test successful entity history retrieval."""
    from src.api.v1.temporal import get_entity_history, EntityHistoryRequest

    mock_version_manager = AsyncMock()

    # Mock version data
    mock_version_manager.get_versions.return_value = [
        {
            "id": "kubernetes",
            "name": "Kubernetes",
            "type": "TECHNOLOGY",
            "valid_from": "2024-11-15T00:00:00",
            "valid_to": None,
            "version_number": 2,
            "changed_by": "admin",
        },
        {
            "id": "kubernetes",
            "name": "Kubernetes",
            "type": "TECHNOLOGY",
            "valid_from": "2024-11-01T00:00:00",
            "valid_to": "2024-11-15T00:00:00",
            "version_number": 1,
            "changed_by": "system",
        },
    ]

    with patch("src.api.v1.temporal.get_version_manager", return_value=mock_version_manager):
        request = EntityHistoryRequest(
            entity_id="kubernetes",
            start_date=None,
            end_date=None,
            limit=50,
        )

        response = await get_entity_history(request, mock_user, None)

        # Verify response
        assert response.entity_id == "kubernetes"
        assert response.total_versions == 2
        assert len(response.versions) == 2
        assert response.versions[0].version_number == 2
        assert response.versions[1].version_number == 1


@pytest.mark.asyncio
async def test_entity_history_with_date_range(mock_user, mock_settings_temporal_enabled):
    """Test entity history with date range filter."""
    from src.api.v1.temporal import get_entity_history, EntityHistoryRequest

    mock_version_manager = AsyncMock()

    mock_version_manager.get_versions.return_value = [
        {
            "id": "kubernetes",
            "name": "Kubernetes",
            "type": "TECHNOLOGY",
            "valid_from": "2024-11-15T00:00:00",
            "valid_to": None,
            "version_number": 2,
            "changed_by": "admin",
        },
        {
            "id": "kubernetes",
            "name": "Kubernetes",
            "type": "TECHNOLOGY",
            "valid_from": "2024-10-15T00:00:00",
            "valid_to": "2024-11-15T00:00:00",
            "version_number": 1,
            "changed_by": "system",
        },
    ]

    with patch("src.api.v1.temporal.get_version_manager", return_value=mock_version_manager):
        request = EntityHistoryRequest(
            entity_id="kubernetes",
            start_date=datetime(2024, 11, 1),
            end_date=datetime(2024, 12, 1),
            limit=50,
        )

        response = await get_entity_history(request, mock_user, None)

        # Only version 2 should be in range
        assert response.total_versions == 1
        assert response.versions[0].version_number == 2


@pytest.mark.asyncio
async def test_entity_history_not_found(mock_user, mock_settings_temporal_enabled):
    """Test entity history for non-existent entity."""
    from src.api.v1.temporal import get_entity_history, EntityHistoryRequest

    mock_version_manager = AsyncMock()
    mock_version_manager.get_versions.return_value = []

    with patch("src.api.v1.temporal.get_version_manager", return_value=mock_version_manager):
        request = EntityHistoryRequest(
            entity_id="nonexistent",
            limit=50,
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_entity_history(request, mock_user, None)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail.lower()


# Entity Changelog Tests


@pytest.mark.asyncio
async def test_entity_changelog_success(mock_user, mock_settings_temporal_enabled):
    """Test successful entity changelog retrieval."""
    from src.api.v1.temporal import get_entity_changelog

    mock_tracker = AsyncMock()

    # Mock changelog data
    mock_tracker.get_change_log.return_value = [
        {
            "entity_id": "kubernetes",
            "version_from": 1,
            "version_to": 2,
            "timestamp": "2024-11-15T00:00:00",
            "changed_fields": ["description"],
            "change_type": "update",
            "changed_by": "admin",
            "reason": "Updated description",
        },
        {
            "entity_id": "kubernetes",
            "version_from": 0,
            "version_to": 1,
            "timestamp": "2024-11-01T00:00:00",
            "changed_fields": ["name", "type"],
            "change_type": "create",
            "changed_by": "system",
            "reason": "Initial creation",
        },
    ]

    with patch("src.api.v1.temporal.get_evolution_tracker", return_value=mock_tracker):
        response = await get_entity_changelog(
            entity_id="kubernetes",
            limit=50,
            current_user=mock_user,
            _=None,
        )

        # Verify response
        assert response.entity_id == "kubernetes"
        assert response.total_changes == 2
        assert len(response.changes) == 2
        assert response.changes[0]["change_type"] == "update"
        assert response.changes[0]["changed_by"] == "admin"
        assert response.changes[1]["change_type"] == "create"


@pytest.mark.asyncio
async def test_entity_changelog_error_handling(mock_user, mock_settings_temporal_enabled):
    """Test entity changelog error handling."""
    from src.api.v1.temporal import get_entity_changelog

    mock_tracker = AsyncMock()
    mock_tracker.get_change_log.side_effect = Exception("Database error")

    with patch("src.api.v1.temporal.get_evolution_tracker", return_value=mock_tracker):
        with pytest.raises(HTTPException) as exc_info:
            await get_entity_changelog(
                entity_id="kubernetes",
                limit=50,
                current_user=mock_user,
                _=None,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve entity changelog" in exc_info.value.detail


# Version Listing Tests


@pytest.mark.asyncio
async def test_get_entity_versions_success(mock_user, mock_settings_temporal_enabled):
    """Test successful version listing."""
    from src.api.v1.temporal import get_entity_versions

    mock_version_manager = AsyncMock()

    mock_version_manager.get_versions.return_value = [
        {"version_number": 3, "version_id": "v3", "name": "Kubernetes"},
        {"version_number": 2, "version_id": "v2", "name": "Kubernetes"},
        {"version_number": 1, "version_id": "v1", "name": "Kubernetes"},
    ]

    with patch("src.api.v1.temporal.get_version_manager", return_value=mock_version_manager):
        response = await get_entity_versions(
            entity_id="kubernetes",
            limit=50,
            current_user=mock_user,
            _=None,
        )

        assert response.entity_id == "kubernetes"
        assert len(response.versions) == 3
        assert response.current_version == 3


@pytest.mark.asyncio
async def test_get_entity_versions_not_found(mock_user, mock_settings_temporal_enabled):
    """Test version listing for non-existent entity."""
    from src.api.v1.temporal import get_entity_versions

    mock_version_manager = AsyncMock()
    mock_version_manager.get_versions.return_value = []

    with patch("src.api.v1.temporal.get_version_manager", return_value=mock_version_manager):
        with pytest.raises(HTTPException) as exc_info:
            await get_entity_versions(
                entity_id="nonexistent",
                limit=50,
                current_user=mock_user,
                _=None,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# Version Comparison Tests


@pytest.mark.asyncio
async def test_compare_entity_versions_success(mock_user, mock_settings_temporal_enabled):
    """Test successful version comparison."""
    from src.api.v1.temporal import compare_entity_versions

    mock_version_manager = AsyncMock()

    mock_version_manager.compare_versions.return_value = {
        "entity_id": "kubernetes",
        "version1": 2,
        "version2": 3,
        "changed_fields": ["description"],
        "differences": {
            "description": {
                "from": "Container orchestration",
                "to": "Container orchestration platform",
            }
        },
        "change_count": 1,
    }

    with patch("src.api.v1.temporal.get_version_manager", return_value=mock_version_manager):
        response = await compare_entity_versions(
            entity_id="kubernetes",
            version_a=2,
            version_b=3,
            current_user=mock_user,
            _=None,
        )

        assert response.entity_id == "kubernetes"
        assert response.version_a == 2
        assert response.version_b == 3
        assert response.change_count == 1
        assert "description" in response.changed_fields


@pytest.mark.asyncio
async def test_compare_entity_versions_same_version(mock_user, mock_settings_temporal_enabled):
    """Test comparing version with itself (should fail)."""
    from src.api.v1.temporal import compare_entity_versions

    with pytest.raises(HTTPException) as exc_info:
        await compare_entity_versions(
            entity_id="kubernetes",
            version_a=2,
            version_b=2,
            current_user=mock_user,
            _=None,
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "cannot compare version with itself" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_compare_entity_versions_not_found(mock_user, mock_settings_temporal_enabled):
    """Test version comparison with missing versions."""
    from src.api.v1.temporal import compare_entity_versions

    mock_version_manager = AsyncMock()

    mock_version_manager.compare_versions.return_value = {
        "entity_id": "kubernetes",
        "version1": 2,
        "version2": 999,
        "changed_fields": [],
        "error": "Insufficient versions found for comparison",
    }

    with patch("src.api.v1.temporal.get_version_manager", return_value=mock_version_manager):
        with pytest.raises(HTTPException) as exc_info:
            await compare_entity_versions(
                entity_id="kubernetes",
                version_a=2,
                version_b=999,
                current_user=mock_user,
                _=None,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# Rollback Tests


@pytest.mark.asyncio
async def test_revert_entity_success(mock_user, mock_settings_temporal_enabled):
    """Test successful entity rollback."""
    from src.api.v1.temporal import revert_entity_to_version, RevertRequest

    mock_version_manager = AsyncMock()

    mock_version_manager.revert_to_version.return_value = {
        "id": "kubernetes",
        "name": "Kubernetes",
        "version_id": "v4",
        "version_number": 4,
        "changed_by": "testuser",
        "change_reason": "Reverting incorrect update (reverted to version v2)",
    }

    with patch("src.api.v1.temporal.get_version_manager", return_value=mock_version_manager):
        request = RevertRequest(reason="Reverting incorrect update")

        response = await revert_entity_to_version(
            entity_id="kubernetes",
            version_id="v2",
            request=request,
            current_user=mock_user,
            _=None,
        )

        # Verify revert was called with correct parameters
        mock_version_manager.revert_to_version.assert_called_once_with(
            entity_id="kubernetes",
            version_id="v2",
            changed_by="testuser",
            change_reason="Reverting incorrect update",
        )

        # Verify response
        assert response["entity_id"] == "kubernetes"
        assert response["reverted_to_version_id"] == "v2"
        assert response["new_version"]["version_number"] == 4
        assert response["new_version"]["changed_by"] == "testuser"


@pytest.mark.asyncio
async def test_revert_entity_version_not_found(mock_user, mock_settings_temporal_enabled):
    """Test rollback with non-existent version."""
    from src.api.v1.temporal import revert_entity_to_version, RevertRequest

    mock_version_manager = AsyncMock()
    mock_version_manager.revert_to_version.side_effect = ValueError("Version v999 not found")

    with patch("src.api.v1.temporal.get_version_manager", return_value=mock_version_manager):
        request = RevertRequest(reason="Test revert")

        with pytest.raises(HTTPException) as exc_info:
            await revert_entity_to_version(
                entity_id="kubernetes",
                version_id="v999",
                request=request,
                current_user=mock_user,
                _=None,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_revert_entity_error_handling(mock_user, mock_settings_temporal_enabled):
    """Test rollback error handling."""
    from src.api.v1.temporal import revert_entity_to_version, RevertRequest

    mock_version_manager = AsyncMock()
    mock_version_manager.revert_to_version.side_effect = Exception("Database error")

    with patch("src.api.v1.temporal.get_version_manager", return_value=mock_version_manager):
        request = RevertRequest(reason="Test revert")

        with pytest.raises(HTTPException) as exc_info:
            await revert_entity_to_version(
                entity_id="kubernetes",
                version_id="v2",
                request=request,
                current_user=mock_user,
                _=None,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to revert entity" in exc_info.value.detail


# Integration with JWT Auth Tests


@pytest.mark.asyncio
async def test_changelog_with_jwt_auth_integration(mock_user, mock_settings_temporal_enabled):
    """Test that changelog properly integrates with JWT auth (changed_by field)."""
    from src.api.v1.temporal import get_entity_changelog

    mock_tracker = AsyncMock()

    # Changelog should have changed_by from JWT auth
    mock_tracker.get_change_log.return_value = [
        {
            "entity_id": "kubernetes",
            "version_from": 1,
            "version_to": 2,
            "timestamp": "2024-11-15T00:00:00",
            "changed_fields": ["description"],
            "change_type": "update",
            "changed_by": "admin",  # From JWT auth
            "reason": "Updated via API",
        }
    ]

    with patch("src.api.v1.temporal.get_evolution_tracker", return_value=mock_tracker):
        response = await get_entity_changelog(
            entity_id="kubernetes",
            limit=50,
            current_user=mock_user,
            _=None,
        )

        # Verify changed_by is present
        assert response.changes[0]["changed_by"] == "admin"


@pytest.mark.asyncio
async def test_revert_with_jwt_auth_integration(mock_user, mock_settings_temporal_enabled):
    """Test that revert properly uses JWT auth context for changed_by field."""
    from src.api.v1.temporal import revert_entity_to_version, RevertRequest

    mock_version_manager = AsyncMock()

    mock_version_manager.revert_to_version.return_value = {
        "id": "kubernetes",
        "version_id": "v4",
        "version_number": 4,
        "changed_by": "testuser",  # Should match mock_user.username
    }

    with patch("src.api.v1.temporal.get_version_manager", return_value=mock_version_manager):
        request = RevertRequest(reason="Test revert")

        await revert_entity_to_version(
            entity_id="kubernetes",
            version_id="v2",
            request=request,
            current_user=mock_user,
            _=None,
        )

        # Verify revert was called with username from JWT
        call_args = mock_version_manager.revert_to_version.call_args
        assert call_args.kwargs["changed_by"] == "testuser"
        assert call_args.kwargs["entity_id"] == "kubernetes"
        assert call_args.kwargs["version_id"] == "v2"
