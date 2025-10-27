"""Extended Unit Tests for Memory Models - Coverage Improvement.

Tests memory data models for validation, serialization, and transformation.

Author: Claude Code
Date: 2025-10-27
"""

from datetime import datetime

import pytest

from src.components.memory.models import MemoryEntry, MemorySearchResult


# ============================================================================
# MemoryEntry Tests
# ============================================================================


@pytest.mark.unit
def test_memory_entry_creation_valid():
    """Test MemoryEntry creation with valid data."""
    entry = MemoryEntry(
        key="test_key",
        value="test value",
        ttl_seconds=7200,
        tags=["tag1", "tag2"],
        metadata={"source": "test"},
        namespace="custom",
    )

    assert entry.key == "test_key"
    assert entry.value == "test value"
    assert entry.ttl_seconds == 7200
    assert entry.tags == ["tag1", "tag2"]
    assert entry.namespace == "custom"


@pytest.mark.unit
def test_memory_entry_defaults():
    """Test MemoryEntry uses correct defaults."""
    entry = MemoryEntry(key="test", value="value")

    assert entry.ttl_seconds == 3600  # Default 1 hour
    assert entry.tags == []
    assert entry.metadata == {}
    assert entry.namespace == "memory"
    assert isinstance(entry.created_at, datetime)


@pytest.mark.unit
def test_memory_entry_namespaced_key():
    """Test MemoryEntry generates correct namespaced key."""
    entry = MemoryEntry(key="my_key", value="value", namespace="custom")

    assert entry.namespaced_key == "custom:my_key"


@pytest.mark.unit
def test_memory_entry_namespaced_key_default():
    """Test MemoryEntry uses default namespace."""
    entry = MemoryEntry(key="my_key", value="value")

    assert entry.namespaced_key == "memory:my_key"


@pytest.mark.unit
def test_memory_entry_validates_empty_key():
    """Test MemoryEntry raises ValueError for empty key."""
    with pytest.raises(ValueError, match="key cannot be empty"):
        MemoryEntry(key="", value="value")


@pytest.mark.unit
def test_memory_entry_validates_negative_ttl():
    """Test MemoryEntry raises ValueError for negative TTL."""
    with pytest.raises(ValueError, match="TTL must be non-negative"):
        MemoryEntry(key="test", value="value", ttl_seconds=-10)


@pytest.mark.unit
def test_memory_entry_validates_tags_type():
    """Test MemoryEntry raises ValueError for non-list tags."""
    with pytest.raises(ValueError, match="Tags must be a list"):
        MemoryEntry(key="test", value="value", tags="not_a_list")  # type: ignore


@pytest.mark.unit
def test_memory_entry_to_dict():
    """Test MemoryEntry serialization to dict."""
    created_time = datetime(2025, 10, 27, 10, 0, 0)
    entry = MemoryEntry(
        key="test",
        value="value",
        ttl_seconds=3600,
        tags=["tag1"],
        created_at=created_time,
        metadata={"key": "value"},
        namespace="test_ns",
    )

    data = entry.to_dict()

    assert data["key"] == "test"
    assert data["value"] == "value"
    assert data["ttl_seconds"] == 3600
    assert data["tags"] == ["tag1"]
    assert data["created_at"] == "2025-10-27T10:00:00"
    assert data["metadata"] == {"key": "value"}
    assert data["namespace"] == "test_ns"


@pytest.mark.unit
def test_memory_entry_from_dict():
    """Test MemoryEntry deserialization from dict."""
    data = {
        "key": "test",
        "value": "value",
        "ttl_seconds": 7200,
        "tags": ["tag1", "tag2"],
        "created_at": "2025-10-27T10:00:00",
        "metadata": {"source": "test"},
        "namespace": "custom",
    }

    entry = MemoryEntry.from_dict(data)

    assert entry.key == "test"
    assert entry.value == "value"
    assert entry.ttl_seconds == 7200
    assert entry.tags == ["tag1", "tag2"]
    assert entry.metadata == {"source": "test"}
    assert entry.namespace == "custom"
    assert entry.created_at == datetime(2025, 10, 27, 10, 0, 0)


@pytest.mark.unit
def test_memory_entry_from_dict_with_defaults():
    """Test MemoryEntry deserialization uses defaults for missing fields."""
    data = {"key": "test", "value": "value"}

    entry = MemoryEntry.from_dict(data)

    assert entry.key == "test"
    assert entry.value == "value"
    assert entry.ttl_seconds == 3600  # Default
    assert entry.tags == []  # Default
    assert entry.metadata == {}  # Default
    assert entry.namespace == "memory"  # Default
    assert isinstance(entry.created_at, datetime)


@pytest.mark.unit
def test_memory_entry_roundtrip_serialization():
    """Test MemoryEntry can be serialized and deserialized without data loss."""
    original = MemoryEntry(
        key="test",
        value="test value",
        ttl_seconds=5000,
        tags=["tag1", "tag2", "tag3"],
        metadata={"key1": "value1", "key2": 123},
        namespace="roundtrip",
    )

    # Serialize
    data = original.to_dict()

    # Deserialize
    restored = MemoryEntry.from_dict(data)

    assert restored.key == original.key
    assert restored.value == original.value
    assert restored.ttl_seconds == original.ttl_seconds
    assert restored.tags == original.tags
    assert restored.metadata == original.metadata
    assert restored.namespace == original.namespace


# ============================================================================
# MemorySearchResult Tests
# ============================================================================


@pytest.mark.unit
def test_memory_search_result_creation_valid():
    """Test MemorySearchResult creation with valid data."""
    entry = MemoryEntry(key="test", value="value")
    result = MemorySearchResult(entry=entry, score=0.85, layer="redis", retrieval_time_ms=10.5)

    assert result.entry.key == "test"
    assert result.score == 0.85
    assert result.layer == "redis"
    assert result.retrieval_time_ms == 10.5


@pytest.mark.unit
def test_memory_search_result_defaults():
    """Test MemorySearchResult uses correct defaults."""
    entry = MemoryEntry(key="test", value="value")
    result = MemorySearchResult(entry=entry, score=0.5, layer="qdrant")

    assert result.retrieval_time_ms == 0.0  # Default


@pytest.mark.unit
def test_memory_search_result_validates_score_range():
    """Test MemorySearchResult validates score is between 0.0 and 1.0."""
    entry = MemoryEntry(key="test", value="value")

    # Too low
    with pytest.raises(ValueError, match="Score must be between 0.0 and 1.0"):
        MemorySearchResult(entry=entry, score=-0.1, layer="redis")

    # Too high
    with pytest.raises(ValueError, match="Score must be between 0.0 and 1.0"):
        MemorySearchResult(entry=entry, score=1.5, layer="redis")


@pytest.mark.unit
def test_memory_search_result_validates_negative_retrieval_time():
    """Test MemorySearchResult raises ValueError for negative retrieval time."""
    entry = MemoryEntry(key="test", value="value")

    with pytest.raises(ValueError, match="Retrieval time must be non-negative"):
        MemorySearchResult(entry=entry, score=0.5, layer="redis", retrieval_time_ms=-10.0)


@pytest.mark.unit
def test_memory_search_result_boundary_scores():
    """Test MemorySearchResult accepts boundary score values (0.0 and 1.0)."""
    entry = MemoryEntry(key="test", value="value")

    # Score = 0.0 should be valid
    result_min = MemorySearchResult(entry=entry, score=0.0, layer="redis")
    assert result_min.score == 0.0

    # Score = 1.0 should be valid
    result_max = MemorySearchResult(entry=entry, score=1.0, layer="redis")
    assert result_max.score == 1.0


@pytest.mark.unit
def test_memory_search_result_to_dict():
    """Test MemorySearchResult serialization to dict."""
    entry = MemoryEntry(key="test", value="value", ttl_seconds=3600, tags=["tag1"])
    result = MemorySearchResult(entry=entry, score=0.75, layer="qdrant", retrieval_time_ms=25.3)

    data = result.to_dict()

    assert data["score"] == 0.75
    assert data["layer"] == "qdrant"
    assert data["retrieval_time_ms"] == 25.3
    assert data["entry"]["key"] == "test"
    assert data["entry"]["value"] == "value"
    assert data["entry"]["tags"] == ["tag1"]


@pytest.mark.unit
def test_memory_search_result_with_different_layers():
    """Test MemorySearchResult works with different memory layers."""
    entry = MemoryEntry(key="test", value="value")

    # Redis layer
    redis_result = MemorySearchResult(entry=entry, score=0.9, layer="redis")
    assert redis_result.layer == "redis"

    # Qdrant layer
    qdrant_result = MemorySearchResult(entry=entry, score=0.7, layer="qdrant")
    assert qdrant_result.layer == "qdrant"

    # Graphiti layer
    graphiti_result = MemorySearchResult(entry=entry, score=0.8, layer="graphiti")
    assert graphiti_result.layer == "graphiti"


# ============================================================================
# Integration Tests (MemoryEntry + MemorySearchResult)
# ============================================================================


@pytest.mark.unit
def test_memory_search_result_roundtrip_with_entry():
    """Test MemorySearchResult with MemoryEntry can be serialized and deserialized."""
    # Create entry
    entry = MemoryEntry(
        key="test",
        value="test value",
        ttl_seconds=1800,
        tags=["important", "recent"],
        metadata={"priority": "high"},
        namespace="session",
    )

    # Create search result
    result = MemorySearchResult(entry=entry, score=0.95, layer="redis", retrieval_time_ms=5.2)

    # Serialize
    data = result.to_dict()

    # Deserialize entry from result
    restored_entry = MemoryEntry.from_dict(data["entry"])

    # Verify entry restored correctly
    assert restored_entry.key == entry.key
    assert restored_entry.value == entry.value
    assert restored_entry.ttl_seconds == entry.ttl_seconds
    assert restored_entry.tags == entry.tags
    assert restored_entry.metadata == entry.metadata
    assert restored_entry.namespace == entry.namespace

    # Verify result fields
    assert data["score"] == 0.95
    assert data["layer"] == "redis"
    assert data["retrieval_time_ms"] == 5.2
