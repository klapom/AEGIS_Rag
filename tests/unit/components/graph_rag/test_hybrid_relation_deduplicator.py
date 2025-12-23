"""Unit tests for HybridRelationDeduplicator.

Sprint 49 Feature 49.8: Manual synonym overrides for relation deduplication.
Tests Redis-backed manual overrides and hybrid deduplication logic.

Author: Claude Code
Date: 2025-12-16
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.graph_rag.hybrid_relation_deduplicator import (
    REDIS_KEY_RELATION_SYNONYMS,
    HybridRelationDeduplicator,
    get_hybrid_relation_deduplicator,
)


@pytest.fixture
def mock_redis_memory():
    """Mock Redis memory manager."""
    redis_client = AsyncMock()
    redis_memory = MagicMock()

    # Create an async function that returns the client
    async def get_redis_client():
        return redis_client

    # Mock the client property to return our async function when accessed
    type(redis_memory).client = property(lambda self: get_redis_client())

    return redis_memory, redis_client


@pytest.fixture
def hybrid_dedup():
    """Create HybridRelationDeduplicator instance."""
    return HybridRelationDeduplicator()


# ============================================================================
# Factory Function Tests
# ============================================================================


def test_get_hybrid_relation_deduplicator():
    """Test factory function creates instance."""
    dedup = get_hybrid_relation_deduplicator()
    assert isinstance(dedup, HybridRelationDeduplicator)
    assert dedup.preserve_original_type is False


def test_get_hybrid_relation_deduplicator_with_preserve():
    """Test factory function with preserve_original_type flag."""
    dedup = get_hybrid_relation_deduplicator(preserve_original_type=True)
    assert isinstance(dedup, HybridRelationDeduplicator)
    assert dedup.preserve_original_type is True


# ============================================================================
# Initialization Tests
# ============================================================================


def test_initialization_default():
    """Test initialization with default parameters."""
    dedup = HybridRelationDeduplicator()
    assert dedup.base_deduplicator is not None
    assert dedup.preserve_original_type is False


def test_initialization_with_base_deduplicator():
    """Test initialization with custom base deduplicator."""
    from src.components.graph_rag.relation_deduplicator import RelationDeduplicator

    base = RelationDeduplicator(preserve_original_type=True)
    dedup = HybridRelationDeduplicator(base_deduplicator=base)
    assert dedup.base_deduplicator == base


# ============================================================================
# Manual Override Management Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_add_manual_override(mock_get_redis, mock_redis_memory):
    """Test adding a manual synonym override."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory

    dedup = HybridRelationDeduplicator()
    await dedup.add_manual_override("USES", "USED_BY")

    # Verify Redis hset was called with correct parameters
    redis_client.hset.assert_called_once_with(
        REDIS_KEY_RELATION_SYNONYMS,
        "USES",
        "USED_BY",
    )


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_add_manual_override_normalizes_types(mock_get_redis, mock_redis_memory):
    """Test that add_manual_override normalizes type names."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory

    dedup = HybridRelationDeduplicator()
    await dedup.add_manual_override("uses", "used-by")

    # Should normalize to uppercase and replace dashes
    redis_client.hset.assert_called_once_with(
        REDIS_KEY_RELATION_SYNONYMS,
        "USES",
        "USED_BY",
    )


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_remove_manual_override_success(mock_get_redis, mock_redis_memory):
    """Test removing an existing manual override."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory
    redis_client.hdel.return_value = 1  # 1 field deleted

    dedup = HybridRelationDeduplicator()
    success = await dedup.remove_manual_override("USES")

    assert success is True
    redis_client.hdel.assert_called_once_with(
        REDIS_KEY_RELATION_SYNONYMS,
        "USES",
    )


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_remove_manual_override_not_found(mock_get_redis, mock_redis_memory):
    """Test removing a non-existent override."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory
    redis_client.hdel.return_value = 0  # No fields deleted

    dedup = HybridRelationDeduplicator()
    success = await dedup.remove_manual_override("NONEXISTENT")

    assert success is False


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_get_all_manual_overrides(mock_get_redis, mock_redis_memory):
    """Test retrieving all manual overrides."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory

    # Mock Redis hgetall to return byte strings
    redis_client.hgetall.return_value = {
        b"USES": b"USED_BY",
        b"ACTED_IN": b"STARRED_IN",
    }

    dedup = HybridRelationDeduplicator()
    overrides = await dedup.get_all_manual_overrides()

    assert overrides == {
        "USES": "USED_BY",
        "ACTED_IN": "STARRED_IN",
    }


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_get_all_manual_overrides_empty(mock_get_redis, mock_redis_memory):
    """Test retrieving overrides when none exist."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory
    redis_client.hgetall.return_value = {}

    dedup = HybridRelationDeduplicator()
    overrides = await dedup.get_all_manual_overrides()

    assert overrides == {}


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_clear_all_manual_overrides(mock_get_redis):
    """Test clearing all manual overrides."""
    # Create mock Redis client
    redis_client = AsyncMock()

    # Mock existing overrides in hgetall
    redis_client.hgetall.return_value = {
        b"USES": b"USED_BY",
        b"ACTED_IN": b"STARRED_IN",
        b"RELATED_TO": b"RELATES_TO",
    }

    # Create mock Redis memory with async client property
    redis_memory = MagicMock()

    # Create an async function that returns the client
    async def get_redis_client():
        return redis_client

    # Mock the client property
    type(redis_memory).client = property(lambda self: get_redis_client())

    # Mock get_redis_memory to return our mock
    mock_get_redis.return_value = redis_memory

    dedup = HybridRelationDeduplicator()
    cleared_count = await dedup.clear_all_manual_overrides()

    assert cleared_count == 3
    redis_client.delete.assert_called_once_with(REDIS_KEY_RELATION_SYNONYMS)


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_clear_all_manual_overrides_empty(mock_get_redis, mock_redis_memory):
    """Test clearing when no overrides exist."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory
    redis_client.hgetall.return_value = {}

    dedup = HybridRelationDeduplicator()
    cleared_count = await dedup.clear_all_manual_overrides()

    assert cleared_count == 0
    redis_client.delete.assert_not_called()


# ============================================================================
# Type Deduplication Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_deduplicate_types_with_manual_overrides(mock_get_redis, mock_redis_memory):
    """Test type deduplication with manual overrides."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory

    # Mock manual overrides
    redis_client.hgetall.return_value = {
        b"USES": b"USED_BY",
    }

    dedup = HybridRelationDeduplicator()
    result = await dedup.deduplicate_types(["USES", "ACTED_IN"])

    # USES should be overridden, ACTED_IN should use automatic normalization
    assert result["USES"] == "USED_BY"
    assert "ACTED_IN" in result


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_deduplicate_types_manual_overrides_take_precedence(
    mock_get_redis, mock_redis_memory
):
    """Test that manual overrides take precedence over automatic normalization."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory

    # Manual override that differs from automatic normalization
    redis_client.hgetall.return_value = {
        b"STARRED_IN": b"PERFORMED_IN",  # Override the automatic ACTED_IN mapping
    }

    dedup = HybridRelationDeduplicator()
    result = await dedup.deduplicate_types(["STARRED_IN"])

    # Manual override should win
    assert result["STARRED_IN"] == "PERFORMED_IN"


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_deduplicate_types_without_manual_overrides(mock_get_redis, mock_redis_memory):
    """Test type deduplication without manual overrides."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory
    redis_client.hgetall.return_value = {}

    dedup = HybridRelationDeduplicator()
    result = await dedup.deduplicate_types(["STARRED_IN", "ACTED_IN"])

    # Both should be normalized to ACTED_IN (automatic normalization)
    assert result["STARRED_IN"] == "ACTED_IN"
    assert result["ACTED_IN"] == "ACTED_IN"


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_deduplicate_types_empty_list(mock_get_redis, mock_redis_memory):
    """Test type deduplication with empty list."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory

    dedup = HybridRelationDeduplicator()
    result = await dedup.deduplicate_types([])

    assert result == {}


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_deduplicate_types_redis_failure_graceful(mock_get_redis, mock_redis_memory):
    """Test graceful handling of Redis failures."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory
    redis_client.hgetall.side_effect = Exception("Redis connection failed")

    dedup = HybridRelationDeduplicator()
    # Should not raise, should fall back to automatic normalization
    result = await dedup.deduplicate_types(["STARRED_IN"])

    assert "STARRED_IN" in result


# ============================================================================
# Full Deduplication Tests
# ============================================================================


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_deduplicate_relations_with_manual_overrides(mock_get_redis, mock_redis_memory):
    """Test full relation deduplication with manual overrides."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory

    # Mock manual overrides
    redis_client.hgetall.return_value = {
        b"USES": b"USED_BY",
    }

    dedup = HybridRelationDeduplicator()
    relations = [
        {"source": "A", "target": "B", "relationship_type": "USES"},
        {"source": "C", "target": "D", "relationship_type": "ACTED_IN"},
    ]

    result = await dedup.deduplicate(relations)

    # Check that USES was overridden
    uses_rel = next((r for r in result if r["source"] == "A"), None)
    assert uses_rel is not None
    assert uses_rel["relationship_type"] == "USED_BY"


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_deduplicate_relations_preserves_original_type(mock_get_redis, mock_redis_memory):
    """Test that original type is preserved when requested."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory
    redis_client.hgetall.return_value = {
        b"USES": b"USED_BY",
    }

    dedup = HybridRelationDeduplicator(preserve_original_type=True)
    relations = [
        {"source": "A", "target": "B", "relationship_type": "USES"},
    ]

    result = await dedup.deduplicate(relations)

    assert result[0]["relationship_type"] == "USED_BY"
    assert result[0]["original_type"] == "USES"


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_deduplicate_relations_with_entity_mapping(mock_get_redis, mock_redis_memory):
    """Test deduplication with entity name remapping."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory
    redis_client.hgetall.return_value = {}

    dedup = HybridRelationDeduplicator()
    relations = [
        {"source": "nicolas cage", "target": "Movie A", "relationship_type": "ACTED_IN"},
        {"source": "Nicolas Cage", "target": "Movie A", "relationship_type": "ACTED_IN"},
    ]
    entity_mapping = {"nicolas cage": "Nicolas Cage"}

    result = await dedup.deduplicate(relations, entity_mapping=entity_mapping)

    # Should merge into one relation after entity remapping
    assert len(result) == 1
    assert result[0]["source"] == "Nicolas Cage"


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_deduplicate_relations_empty_list(mock_get_redis, mock_redis_memory):
    """Test deduplication with empty list."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory

    dedup = HybridRelationDeduplicator()
    result = await dedup.deduplicate([])

    assert result == []


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_deduplicate_relations_disable_manual_overrides(mock_get_redis, mock_redis_memory):
    """Test disabling manual overrides."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory
    redis_client.hgetall.return_value = {
        b"USES": b"USED_BY",
    }

    dedup = HybridRelationDeduplicator()
    relations = [
        {"source": "A", "target": "B", "relationship_type": "USES"},
    ]

    result = await dedup.deduplicate(relations, use_manual_overrides=False)

    # Manual override should not be applied
    assert result[0]["relationship_type"] == "USES"


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_add_manual_override_with_spaces_and_dashes(mock_get_redis, mock_redis_memory):
    """Test that spaces and dashes are normalized."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory

    dedup = HybridRelationDeduplicator()
    await dedup.add_manual_override("WORKS AT", "EMPLOYED-BY")

    redis_client.hset.assert_called_once_with(
        REDIS_KEY_RELATION_SYNONYMS,
        "WORKS_AT",
        "EMPLOYED_BY",
    )


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_get_manual_overrides_handles_string_values(mock_get_redis, mock_redis_memory):
    """Test that string values (not bytes) are handled correctly."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory

    # Mock Redis returning strings instead of bytes
    redis_client.hgetall.return_value = {
        "USES": "USED_BY",
        "ACTED_IN": "STARRED_IN",
    }

    dedup = HybridRelationDeduplicator()
    overrides = await dedup.get_all_manual_overrides()

    assert overrides == {
        "USES": "USED_BY",
        "ACTED_IN": "STARRED_IN",
    }


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_add_manual_override_redis_error(mock_get_redis, mock_redis_memory):
    """Test error handling when Redis fails."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory
    redis_client.hset.side_effect = Exception("Redis connection failed")

    dedup = HybridRelationDeduplicator()

    with pytest.raises(Exception, match="Redis connection failed"):
        await dedup.add_manual_override("USES", "USED_BY")


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_remove_manual_override_redis_error(mock_get_redis, mock_redis_memory):
    """Test error handling when Redis delete fails."""
    redis_memory, redis_client = mock_redis_memory
    mock_get_redis.return_value = redis_memory
    redis_client.hdel.side_effect = Exception("Redis connection failed")

    dedup = HybridRelationDeduplicator()

    with pytest.raises(Exception, match="Redis connection failed"):
        await dedup.remove_manual_override("USES")


@pytest.mark.asyncio
@patch("src.components.memory.get_redis_memory")
async def test_clear_manual_overrides_redis_error(mock_get_redis):
    """Test graceful error handling when Redis hgetall fails."""
    redis_client = AsyncMock()
    redis_memory = MagicMock()

    # Create an async function that returns the client
    async def get_redis_client():
        return redis_client

    type(redis_memory).client = property(lambda self: get_redis_client())
    mock_get_redis.return_value = redis_memory

    # Make hgetall fail (used by _get_manual_overrides)
    # _get_manual_overrides catches this and returns {}
    redis_client.hgetall.side_effect = Exception("Redis connection failed")

    dedup = HybridRelationDeduplicator()

    # Should gracefully handle the error and return 0
    # (because _get_manual_overrides returns {} on error)
    cleared_count = await dedup.clear_all_manual_overrides()
    assert cleared_count == 0
