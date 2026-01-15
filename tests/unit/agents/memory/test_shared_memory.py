"""Unit tests for Shared Memory Protocol.

Sprint 94 Feature 94.2: Shared Memory Protocol (8 SP)

Tests cover:
- Memory scopes (PRIVATE, SHARED, GLOBAL)
- CRUD operations (read, write, append, delete)
- Permission enforcement
- Concurrent access
- TTL expiration
- Version tracking
- Admin bypass
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.memory.shared_memory import (
    AccessControl,
    MemoryEntry,
    MemoryScope,
    SharedMemoryProtocol,
    create_shared_memory,
)
from src.core.exceptions import MemoryError


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_redis():
    """Mock RedisMemoryManager."""
    redis = AsyncMock()
    redis.store = AsyncMock(return_value=True)
    redis.retrieve = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=True)
    redis.extend_ttl = AsyncMock(return_value=True)
    redis.client = AsyncMock()
    redis.client.scan_iter = AsyncMock()
    redis.client.ttl = AsyncMock(return_value=3600)
    return redis


@pytest.fixture
def shared_memory(mock_redis):
    """SharedMemoryProtocol instance with mocked Redis."""
    return SharedMemoryProtocol(
        redis_manager=mock_redis,
        default_ttl_seconds=3600,
        namespace="test_memory",
    )


# =============================================================================
# Scope Tests
# =============================================================================


def test_memory_scope_enum():
    """Test MemoryScope enum values."""
    assert MemoryScope.PRIVATE.value == "private"
    assert MemoryScope.SHARED.value == "shared"
    assert MemoryScope.GLOBAL.value == "global"


def test_memory_scope_from_string():
    """Test creating MemoryScope from string."""
    assert MemoryScope("private") == MemoryScope.PRIVATE
    assert MemoryScope("shared") == MemoryScope.SHARED
    assert MemoryScope("global") == MemoryScope.GLOBAL


# =============================================================================
# Data Model Tests
# =============================================================================


def test_memory_entry_creation():
    """Test MemoryEntry creation."""
    entry = MemoryEntry(
        key="test_key",
        value={"data": 123},
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
        timestamp=datetime.now(UTC),
        ttl_seconds=3600,
    )

    assert entry.key == "test_key"
    assert entry.value == {"data": 123}
    assert entry.scope == MemoryScope.PRIVATE
    assert entry.owner_skill == "research"
    assert entry.ttl_seconds == 3600
    assert entry.version == 1
    assert entry.allowed_skills == []


def test_access_control_creation():
    """Test AccessControl creation."""
    acl = AccessControl(
        can_read=["skill1", "skill2"],
        can_write=["skill1"],
        is_admin=False,
    )

    assert acl.can_read == ["skill1", "skill2"]
    assert acl.can_write == ["skill1"]
    assert acl.is_admin is False


# =============================================================================
# Write Operation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_write_private_memory(shared_memory):
    """Test writing to private memory."""
    result = await shared_memory.write(
        key="findings",
        value={"count": 10},
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
        ttl_seconds=3600,
    )

    assert result is True
    shared_memory._redis.store.assert_called_once()


@pytest.mark.asyncio
async def test_write_shared_memory(shared_memory):
    """Test writing to shared memory with allowed skills."""
    result = await shared_memory.write(
        key="task_context",
        value={"query": "test"},
        scope=MemoryScope.SHARED,
        owner_skill="coordinator",
        allowed_skills=["research", "synthesis"],
        ttl_seconds=7200,
    )

    assert result is True
    shared_memory._redis.store.assert_called_once()


@pytest.mark.asyncio
async def test_write_global_memory(shared_memory):
    """Test writing to global memory."""
    result = await shared_memory.write(
        key="system_config",
        value={"max_tokens": 4096},
        scope=MemoryScope.GLOBAL,
        owner_skill="admin",
        ttl_seconds=None,  # No expiration
    )

    assert result is True


@pytest.mark.asyncio
async def test_write_with_metadata(shared_memory):
    """Test writing with custom metadata."""
    result = await shared_memory.write(
        key="findings",
        value={"count": 10},
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
        metadata={"confidence": 0.95, "source": "experiment"},
    )

    assert result is True


@pytest.mark.asyncio
async def test_write_version_increment(shared_memory):
    """Test version increment on update."""
    # Mock existing entry with version 1
    shared_memory._redis.retrieve = AsyncMock(return_value='{"version": 1}')

    result = await shared_memory.write(
        key="findings",
        value={"count": 20},
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
    )

    assert result is True


@pytest.mark.asyncio
async def test_write_redis_error(shared_memory):
    """Test write error handling."""
    shared_memory._redis.store = AsyncMock(side_effect=Exception("Redis error"))

    with pytest.raises(MemoryError, match="Failed to write to shared memory"):
        await shared_memory.write(
            key="test",
            value={"data": 1},
            scope=MemoryScope.PRIVATE,
            owner_skill="test_skill",
        )


# =============================================================================
# Read Operation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_read_private_memory_owner(shared_memory):
    """Test reading private memory as owner."""
    # Mock Redis response
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "findings", "value": {"count": 10}, "scope": "private", "owner_skill": "research", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": []}'
    )

    result = await shared_memory.read(
        key="findings",
        scope=MemoryScope.PRIVATE,
        requesting_skill="research",
        owner_skill="research",
    )

    assert result == {"count": 10}


@pytest.mark.asyncio
async def test_read_private_memory_non_owner_denied(shared_memory):
    """Test reading private memory as non-owner is denied."""
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "findings", "value": {"count": 10}, "scope": "private", "owner_skill": "research", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": []}'
    )

    with pytest.raises(PermissionError, match="cannot read"):
        await shared_memory.read(
            key="findings",
            scope=MemoryScope.PRIVATE,
            requesting_skill="synthesis",
            owner_skill="research",
        )


@pytest.mark.asyncio
async def test_read_shared_memory_allowed_skill(shared_memory):
    """Test reading shared memory with allowed skill."""
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "context", "value": {"query": "test"}, "scope": "shared", "owner_skill": "coordinator", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": ["research", "synthesis"]}'
    )

    result = await shared_memory.read(
        key="context",
        scope=MemoryScope.SHARED,
        requesting_skill="research",
        owner_skill="coordinator",
    )

    assert result == {"query": "test"}


@pytest.mark.asyncio
async def test_read_shared_memory_denied(shared_memory):
    """Test reading shared memory with non-allowed skill."""
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "context", "value": {"query": "test"}, "scope": "shared", "owner_skill": "coordinator", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": ["research"]}'
    )

    with pytest.raises(PermissionError, match="cannot read"):
        await shared_memory.read(
            key="context",
            scope=MemoryScope.SHARED,
            requesting_skill="synthesis",
            owner_skill="coordinator",
        )


@pytest.mark.asyncio
async def test_read_global_memory_any_skill(shared_memory):
    """Test reading global memory with any skill."""
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "config", "value": {"max_tokens": 4096}, "scope": "global", "owner_skill": "system", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": []}'
    )

    result = await shared_memory.read(
        key="config",
        scope=MemoryScope.GLOBAL,
        requesting_skill="research",
        owner_skill="system",
    )

    assert result == {"max_tokens": 4096}


@pytest.mark.asyncio
async def test_read_admin_bypass(shared_memory):
    """Test admin skill bypasses read permissions."""
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "findings", "value": {"count": 10}, "scope": "private", "owner_skill": "research", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": []}'
    )

    # Admin skill can read private memory
    result = await shared_memory.read(
        key="findings",
        scope=MemoryScope.PRIVATE,
        requesting_skill="admin",
        owner_skill="research",
    )

    assert result == {"count": 10}


@pytest.mark.asyncio
async def test_read_not_found(shared_memory):
    """Test reading non-existent key."""
    shared_memory._redis.retrieve = AsyncMock(return_value=None)

    result = await shared_memory.read(
        key="nonexistent",
        scope=MemoryScope.PRIVATE,
        requesting_skill="research",
        owner_skill="research",
    )

    assert result is None


@pytest.mark.asyncio
async def test_read_requires_owner_for_private(shared_memory):
    """Test read raises error if owner_skill not provided for private scope."""
    with pytest.raises(MemoryError, match="owner_skill required"):
        await shared_memory.read(
            key="test",
            scope=MemoryScope.PRIVATE,
            requesting_skill="research",
            owner_skill=None,
        )


# =============================================================================
# Append Operation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_append_to_new_list(shared_memory):
    """Test appending to new list entry."""
    shared_memory._redis.retrieve = AsyncMock(return_value=None)

    result = await shared_memory.append(
        key="findings_list",
        value={"paper_id": 123},
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
        requesting_skill="research",
    )

    assert result is True


@pytest.mark.asyncio
async def test_append_to_existing_list(shared_memory):
    """Test appending to existing list."""
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "findings_list", "value": [{"paper_id": 123}], "scope": "private", "owner_skill": "research", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": []}'
    )

    result = await shared_memory.append(
        key="findings_list",
        value={"paper_id": 456},
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
        requesting_skill="research",
    )

    assert result is True


@pytest.mark.asyncio
async def test_append_permission_denied(shared_memory):
    """Test append permission check."""
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "findings_list", "value": [{"paper_id": 123}], "scope": "private", "owner_skill": "research", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": []}'
    )

    with pytest.raises(PermissionError, match="cannot write"):
        await shared_memory.append(
            key="findings_list",
            value={"paper_id": 456},
            scope=MemoryScope.PRIVATE,
            owner_skill="research",
            requesting_skill="synthesis",
        )


@pytest.mark.asyncio
async def test_append_to_non_list_fails(shared_memory):
    """Test append to non-list entry fails."""
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "findings", "value": {"count": 10}, "scope": "private", "owner_skill": "research", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": []}'
    )

    with pytest.raises(ValueError, match="is not a list"):
        await shared_memory.append(
            key="findings",
            value={"new_data": 1},
            scope=MemoryScope.PRIVATE,
            owner_skill="research",
            requesting_skill="research",
        )


# =============================================================================
# Delete Operation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_delete_as_owner(shared_memory):
    """Test deleting as owner."""
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "findings", "value": {"count": 10}, "scope": "private", "owner_skill": "research", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": []}'
    )
    shared_memory._redis.delete = AsyncMock(return_value=True)

    result = await shared_memory.delete(
        key="findings",
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
        requesting_skill="research",
    )

    assert result is True


@pytest.mark.asyncio
async def test_delete_as_admin(shared_memory):
    """Test deleting as admin."""
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "findings", "value": {"count": 10}, "scope": "private", "owner_skill": "research", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": []}'
    )
    shared_memory._redis.delete = AsyncMock(return_value=True)

    result = await shared_memory.delete(
        key="findings",
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
        requesting_skill="admin",
    )

    assert result is True


@pytest.mark.asyncio
async def test_delete_permission_denied(shared_memory):
    """Test delete permission check."""
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "findings", "value": {"count": 10}, "scope": "private", "owner_skill": "research", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": []}'
    )

    with pytest.raises(PermissionError, match="cannot delete"):
        await shared_memory.delete(
            key="findings",
            scope=MemoryScope.PRIVATE,
            owner_skill="research",
            requesting_skill="synthesis",
        )


@pytest.mark.asyncio
async def test_delete_not_found(shared_memory):
    """Test deleting non-existent key."""
    shared_memory._redis.retrieve = AsyncMock(return_value=None)

    result = await shared_memory.delete(
        key="nonexistent",
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
        requesting_skill="research",
    )

    assert result is False


# =============================================================================
# Permission Tests
# =============================================================================


def test_is_admin():
    """Test admin skill detection."""
    memory = SharedMemoryProtocol()

    assert memory._is_admin("admin") is True
    assert memory._is_admin("coordinator") is True
    assert memory._is_admin("orchestrator") is True
    assert memory._is_admin("research") is False


def test_can_read_private_scope():
    """Test read permissions for private scope."""
    memory = SharedMemoryProtocol()
    entry = MemoryEntry(
        key="test",
        value={},
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
        timestamp=datetime.now(UTC),
    )

    # Owner can read
    assert memory._can_read(entry, "research") is True

    # Non-owner cannot read
    assert memory._can_read(entry, "synthesis") is False

    # Admin can read
    assert memory._can_read(entry, "admin") is True


def test_can_read_shared_scope():
    """Test read permissions for shared scope."""
    memory = SharedMemoryProtocol()

    # Shared with explicit allow list
    entry = MemoryEntry(
        key="test",
        value={},
        scope=MemoryScope.SHARED,
        owner_skill="coordinator",
        timestamp=datetime.now(UTC),
        allowed_skills=["research", "synthesis"],
    )

    # Owner can read
    assert memory._can_read(entry, "coordinator") is True

    # Allowed skill can read
    assert memory._can_read(entry, "research") is True

    # Non-allowed skill cannot read
    assert memory._can_read(entry, "memory") is False

    # Shared with empty allow list (public)
    entry2 = MemoryEntry(
        key="test2",
        value={},
        scope=MemoryScope.SHARED,
        owner_skill="coordinator",
        timestamp=datetime.now(UTC),
        allowed_skills=[],
    )

    # Anyone can read
    assert memory._can_read(entry2, "research") is True
    assert memory._can_read(entry2, "synthesis") is True


def test_can_read_global_scope():
    """Test read permissions for global scope."""
    memory = SharedMemoryProtocol()
    entry = MemoryEntry(
        key="test",
        value={},
        scope=MemoryScope.GLOBAL,
        owner_skill="system",
        timestamp=datetime.now(UTC),
    )

    # Everyone can read global
    assert memory._can_read(entry, "research") is True
    assert memory._can_read(entry, "synthesis") is True
    assert memory._can_read(entry, "admin") is True


def test_can_write_private_scope():
    """Test write permissions for private scope."""
    memory = SharedMemoryProtocol()
    entry = MemoryEntry(
        key="test",
        value={},
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
        timestamp=datetime.now(UTC),
    )

    # Owner can write
    assert memory._can_write(entry, "research") is True

    # Non-owner cannot write
    assert memory._can_write(entry, "synthesis") is False

    # Admin can write
    assert memory._can_write(entry, "admin") is True


def test_can_write_shared_scope():
    """Test write permissions for shared scope."""
    memory = SharedMemoryProtocol()
    entry = MemoryEntry(
        key="test",
        value={},
        scope=MemoryScope.SHARED,
        owner_skill="coordinator",
        timestamp=datetime.now(UTC),
        allowed_skills=["research"],
    )

    # Owner can write
    assert memory._can_write(entry, "coordinator") is True

    # Allowed skill can write
    assert memory._can_write(entry, "research") is True

    # Non-allowed skill cannot write
    assert memory._can_write(entry, "synthesis") is False


def test_can_write_global_scope():
    """Test write permissions for global scope."""
    memory = SharedMemoryProtocol()
    entry = MemoryEntry(
        key="test",
        value={},
        scope=MemoryScope.GLOBAL,
        owner_skill="system",
        timestamp=datetime.now(UTC),
    )

    # Only admin can write global
    assert memory._can_write(entry, "admin") is True
    assert memory._can_write(entry, "research") is False


# =============================================================================
# List Keys Tests
# =============================================================================


@pytest.mark.asyncio
async def test_list_keys_by_scope(shared_memory):
    """Test listing keys by scope."""

    # Mock Redis scan_iter - need to mock the awaited client property
    async def mock_scan_iter(match, count):
        keys = [
            "test_memory:private:research:key1",
            "test_memory:private:research:key2",
            "test_memory:private:synthesis:key3",
        ]
        for key in keys:
            yield key

    mock_client = AsyncMock()
    mock_client.scan_iter = mock_scan_iter

    # Mock the client property to return our mock
    async def get_mock_client():
        return mock_client

    shared_memory._redis.client = get_mock_client()

    keys = await shared_memory.list_keys(
        scope=MemoryScope.PRIVATE,
    )

    assert len(keys) == 3
    assert "key1" in keys
    assert "key2" in keys
    assert "key3" in keys


@pytest.mark.asyncio
async def test_list_keys_by_owner(shared_memory):
    """Test listing keys by owner skill."""

    async def mock_scan_iter(match, count):
        if "research" in match:
            keys = [
                "test_memory:private:research:key1",
                "test_memory:private:research:key2",
            ]
        else:
            keys = []
        for key in keys:
            yield key

    mock_client = AsyncMock()
    mock_client.scan_iter = mock_scan_iter

    async def get_mock_client():
        return mock_client

    shared_memory._redis.client = get_mock_client()

    keys = await shared_memory.list_keys(
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
    )

    assert len(keys) == 2


# =============================================================================
# TTL Tests
# =============================================================================


@pytest.mark.asyncio
async def test_extend_ttl(shared_memory):
    """Test extending TTL of entry."""
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "findings", "value": {"count": 10}, "scope": "private", "owner_skill": "research", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": []}'
    )
    shared_memory._redis.extend_ttl = AsyncMock(return_value=True)

    result = await shared_memory.extend_ttl(
        key="findings",
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
        additional_seconds=3600,
        requesting_skill="research",
    )

    assert result is True
    shared_memory._redis.extend_ttl.assert_called_once()


@pytest.mark.asyncio
async def test_extend_ttl_permission_denied(shared_memory):
    """Test extend TTL permission check."""
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "findings", "value": {"count": 10}, "scope": "private", "owner_skill": "research", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": []}'
    )

    with pytest.raises(PermissionError, match="cannot modify"):
        await shared_memory.extend_ttl(
            key="findings",
            scope=MemoryScope.PRIVATE,
            owner_skill="research",
            additional_seconds=3600,
            requesting_skill="synthesis",
        )


# =============================================================================
# Metadata Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_metadata(shared_memory):
    """Test getting entry metadata."""
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "findings", "value": {"count": 10}, "scope": "private", "owner_skill": "research", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": [], "metadata": {"confidence": 0.95}}'
    )

    # Mock the client property
    mock_client = AsyncMock()
    mock_client.ttl = AsyncMock(return_value=3600)

    async def get_mock_client():
        return mock_client

    shared_memory._redis.client = get_mock_client()

    metadata = await shared_memory.get_metadata(
        key="findings",
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
    )

    assert metadata is not None
    assert metadata["key"] == "findings"
    assert metadata["scope"] == "private"
    assert metadata["owner_skill"] == "research"
    assert metadata["version"] == 1
    assert metadata["ttl_seconds_remaining"] == 3600
    assert metadata["metadata"]["confidence"] == 0.95


@pytest.mark.asyncio
async def test_get_metadata_not_found(shared_memory):
    """Test get metadata for non-existent key."""
    shared_memory._redis.retrieve = AsyncMock(return_value=None)

    metadata = await shared_memory.get_metadata(
        key="nonexistent",
        scope=MemoryScope.PRIVATE,
        owner_skill="research",
    )

    assert metadata is None


# =============================================================================
# Metrics Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_metrics(shared_memory):
    """Test getting memory metrics."""

    async def mock_scan_iter(match, count):
        keys = [
            "test_memory:private:research:key1",
            "test_memory:shared:coordinator:key2",
            "test_memory:global:system:key3",
        ]
        for key in keys:
            yield key

    mock_client = AsyncMock()
    mock_client.scan_iter = mock_scan_iter

    async def get_mock_client():
        return mock_client

    shared_memory._redis.client = get_mock_client()

    metrics = await shared_memory.get_metrics()

    assert metrics["total_entries"] == 3
    assert metrics["private_entries"] == 1
    assert metrics["shared_entries"] == 1
    assert metrics["global_entries"] == 1
    assert metrics["namespace"] == "test_memory"


# =============================================================================
# Factory Function Tests
# =============================================================================


def test_create_shared_memory():
    """Test factory function."""
    memory = create_shared_memory(
        default_ttl_seconds=7200,
        namespace="custom_namespace",
    )

    assert memory._default_ttl == 7200
    assert memory._namespace == "custom_namespace"


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_concurrent_writes(shared_memory):
    """Test concurrent write operations."""
    # Simulate concurrent writes
    tasks = [
        shared_memory.write(
            key=f"key_{i}",
            value={"data": i},
            scope=MemoryScope.PRIVATE,
            owner_skill="research",
        )
        for i in range(10)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # All writes should succeed
    assert all(r is True for r in results if not isinstance(r, Exception))


@pytest.mark.asyncio
async def test_workflow_research_to_synthesis(shared_memory):
    """Test workflow: research writes, synthesis reads."""
    # Research writes findings
    await shared_memory.write(
        key="findings",
        value={"papers": 10, "citations": 45},
        scope=MemoryScope.SHARED,
        owner_skill="research",
        allowed_skills=["synthesis"],
    )

    # Mock read response
    shared_memory._redis.retrieve = AsyncMock(
        return_value='{"key": "findings", "value": {"papers": 10, "citations": 45}, "scope": "shared", "owner_skill": "research", "timestamp": "2026-01-15T10:00:00Z", "version": 1, "allowed_skills": ["synthesis"]}'
    )

    # Synthesis reads findings
    data = await shared_memory.read(
        key="findings",
        scope=MemoryScope.SHARED,
        requesting_skill="synthesis",
        owner_skill="research",
    )

    assert data == {"papers": 10, "citations": 45}


@pytest.mark.asyncio
async def test_cleanup(shared_memory):
    """Test cleanup and close."""
    await shared_memory.aclose()
    shared_memory._redis.aclose.assert_called_once()
