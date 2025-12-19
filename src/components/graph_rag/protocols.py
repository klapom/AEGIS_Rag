"""Protocol definitions for Graph RAG components.

Sprint 53 Feature 53.1: Define protocols for dependency injection
to break circular dependencies and improve testability.

These protocols define the interfaces that components depend on,
allowing for loose coupling and easier mocking in tests.

Author: Claude Code
Date: 2025-12-19
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMConfigProvider(Protocol):
    """Protocol for LLM configuration providers.

    Components that need LLM configuration should depend on this protocol
    rather than importing directly from admin or other high-level modules.

    Example:
        >>> class MyComponent:
        ...     def __init__(self, config_provider: LLMConfigProvider):
        ...         self.config = config_provider
        ...
        ...     async def do_work(self):
        ...         model = await self.config.get_community_summary_model()
    """

    async def get_community_summary_model(self) -> str:
        """Get the configured model for community summary generation.

        Returns:
            Model name string (e.g., "llama3.2:8b")
        """
        ...

    async def get_extraction_model(self) -> str:
        """Get the configured model for entity extraction.

        Returns:
            Model name string
        """
        ...


@runtime_checkable
class GraphStorage(Protocol):
    """Protocol for graph storage backends.

    Sprint 53: Placeholder for Sprint 56 DDD migration.
    Will be used to abstract Neo4j operations.
    """

    async def store_entity(self, entity: dict) -> str:
        """Store an entity and return its ID."""
        ...

    async def store_relationship(self, relationship: dict) -> str:
        """Store a relationship and return its ID."""
        ...

    async def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        """Execute a Cypher query and return results."""
        ...


@runtime_checkable
class CommunityDetector(Protocol):
    """Protocol for community detection algorithms.

    Sprint 53: Placeholder for Sprint 56 DDD migration.
    """

    async def detect_communities(self) -> list[dict]:
        """Detect communities in the graph.

        Returns:
            List of community dictionaries with 'id' and 'members'
        """
        ...

    async def get_community(self, community_id: int) -> dict | None:
        """Get a specific community by ID."""
        ...
