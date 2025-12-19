"""Memory Domain Protocols.

Sprint 57 Feature 57.5: Protocol definitions for memory operations.
Enables dependency injection and improves testability.

Usage:
    from src.domains.memory.protocols import (
        ConversationMemory,
        SessionStore,
        CacheService,
    )

These protocols define interfaces for:
- Conversation history management
- Session storage
- Caching operations
- Memory consolidation (Graphiti)
"""

from typing import Protocol, Any, runtime_checkable


@runtime_checkable
class ConversationMemory(Protocol):
    """Protocol for conversation memory.

    Implementations should manage conversation history
    for chat sessions.

    Example:
        >>> class RedisConversationMemory:
        ...     async def add_message(self, session_id: str, role: str, content: str) -> None:
        ...         # Store in Redis
        ...         pass
    """

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add message to conversation.

        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional message metadata
        """
        ...

    async def get_history(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get conversation history.

        Args:
            session_id: Session identifier
            limit: Maximum messages to return

        Returns:
            List of messages with:
            - role: str
            - content: str
            - timestamp: str
            - metadata: dict | None
        """
        ...

    async def clear_history(
        self,
        session_id: str,
    ) -> None:
        """Clear conversation history.

        Args:
            session_id: Session identifier
        """
        ...

    async def get_message_count(
        self,
        session_id: str,
    ) -> int:
        """Get number of messages in conversation.

        Args:
            session_id: Session identifier

        Returns:
            Number of messages
        """
        ...


@runtime_checkable
class SessionStore(Protocol):
    """Protocol for session storage.

    Implementations should manage user sessions
    with metadata and state.
    """

    async def create_session(
        self,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create new session.

        Args:
            user_id: Optional user identifier
            metadata: Optional session metadata

        Returns:
            New session ID
        """
        ...

    async def get_session(
        self,
        session_id: str,
    ) -> dict[str, Any] | None:
        """Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None if not found
        """
        ...

    async def update_session(
        self,
        session_id: str,
        metadata: dict[str, Any],
    ) -> bool:
        """Update session metadata.

        Args:
            session_id: Session identifier
            metadata: Metadata to update

        Returns:
            True if updated, False if not found
        """
        ...

    async def delete_session(
        self,
        session_id: str,
    ) -> bool:
        """Delete session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        ...

    async def list_sessions(
        self,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List sessions.

        Args:
            user_id: Optional filter by user
            limit: Maximum sessions to return

        Returns:
            List of session summaries
        """
        ...


@runtime_checkable
class CacheService(Protocol):
    """Protocol for caching.

    Implementations should provide key-value caching
    with optional TTL.
    """

    async def get(
        self,
        key: str,
    ) -> Any | None:
        """Get cached value.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        ...

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Set cached value.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = no expiry)
        """
        ...

    async def delete(
        self,
        key: str,
    ) -> bool:
        """Delete cached value.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        ...

    async def exists(
        self,
        key: str,
    ) -> bool:
        """Check if key exists.

        Args:
            key: Cache key

        Returns:
            True if key exists and not expired
        """
        ...

    async def clear_pattern(
        self,
        pattern: str,
    ) -> int:
        """Clear keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "session:*")

        Returns:
            Number of keys deleted
        """
        ...


@runtime_checkable
class MemoryConsolidation(Protocol):
    """Protocol for memory consolidation (Graphiti).

    Implementations should extract and store facts
    from conversations for long-term memory.
    """

    async def extract_facts(
        self,
        conversation: list[dict[str, Any]],
        session_id: str,
    ) -> list[dict[str, Any]]:
        """Extract facts from conversation.

        Args:
            conversation: Conversation messages
            session_id: Session identifier

        Returns:
            List of extracted facts with:
            - fact: str
            - confidence: float
            - entities: list[str]
        """
        ...

    async def store_facts(
        self,
        facts: list[dict[str, Any]],
        session_id: str,
    ) -> None:
        """Store facts in long-term memory.

        Args:
            facts: Facts to store
            session_id: Session identifier
        """
        ...

    async def retrieve_relevant_facts(
        self,
        query: str,
        session_id: str | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Retrieve facts relevant to query.

        Args:
            query: Query to match facts against
            session_id: Optional session filter
            top_k: Number of facts to return

        Returns:
            List of relevant facts
        """
        ...


__all__ = [
    "ConversationMemory",
    "SessionStore",
    "CacheService",
    "MemoryConsolidation",
]
