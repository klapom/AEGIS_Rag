"""Memory data models for AEGIS RAG Sprint 9.

This module provides data models for the 3-layer memory architecture:
- MemoryEntry: Core memory entry with TTL, tags, and metadata
- MemorySearchResult: Result from memory search operations
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

@dataclass
class MemoryEntry:
    """Memory entry for Redis working memory storage.

    Attributes:
        key: Unique key for this memory entry
        value: The actual value/content to store
        ttl_seconds: Time-to-live in seconds (default: 3600 = 1 hour)
        tags: list of tags for searchability and categorization
        created_at: Timestamp when entry was created
        metadata: Additional metadata dictionary
        namespace: Key namespace prefix for organization
    """

    key: str
    value: str
    ttl_seconds: int = 3600  # Default 1 hour
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    namespace: str = "memory"

    def __post_init__(self) -> None:
        """Validate memory entry after initialization."""
        if not self.key:
            raise ValueError("Memory entry key cannot be empty")
        if self.ttl_seconds < 0:
            raise ValueError("TTL must be non-negative")
        if not isinstance(self.tags, list):
            raise ValueError("Tags must be a list")

    @property
    def namespaced_key(self) -> str:
        """Get the namespaced key for Redis storage.

        Returns:
            Namespaced key in format "namespace:key"
        """
        return f"{self.namespace}:{self.key}"

    def to_dict(self) -> dict[str, Any]:
        """Convert MemoryEntry to dictionary for serialization.

        Returns:
            Dictionary representation of the memory entry
        """
        return {
            "key": self.key,
            "value": self.value,
            "ttl_seconds": self.ttl_seconds,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
            "namespace": self.namespace,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        """Create MemoryEntry from dictionary.

        Args:
            data: Dictionary with memory entry data

        Returns:
            MemoryEntry instance
        """
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            key=data["key"],
            value=data["value"],
            ttl_seconds=data.get("ttl_seconds", 3600),
            tags=data.get("tags", []),
            created_at=created_at or datetime.now(UTC),
            metadata=data.get("metadata", {}),
            namespace=data.get("namespace", "memory"),
        )

@dataclass
class MemorySearchResult:
    """Result from memory search operation.

    Attributes:
        entry: The memory entry that was found
        score: Relevance score (0.0-1.0)
        layer: Which memory layer this came from
        retrieval_time_ms: Time taken to retrieve in milliseconds
    """

    entry: MemoryEntry
    score: float
    layer: str
    retrieval_time_ms: float = 0.0

    def __post_init__(self) -> None:
        """Validate search result after initialization."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("Score must be between 0.0 and 1.0")
        if self.retrieval_time_ms < 0:
            raise ValueError("Retrieval time must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "entry": self.entry.to_dict(),
            "score": self.score,
            "layer": self.layer,
            "retrieval_time_ms": self.retrieval_time_ms,
        }
