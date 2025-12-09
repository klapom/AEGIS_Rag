"""Neo4j Query Safety Layer for Namespace Isolation.

Sprint 41 Feature 41.1: Namespace Isolation Layer

This module provides a security wrapper around Neo4j queries that enforces
mandatory namespace filtering to prevent cross-namespace data leakage.

Every Neo4j query MUST contain a namespace filter (namespace_id property).
Queries without proper filtering are rejected at runtime.

Example:
    # REJECTED - no namespace filter
    MATCH (e:Entity) RETURN e

    # ACCEPTED - has namespace filter
    MATCH (e:Entity) WHERE e.namespace_id IN $allowed_namespaces RETURN e
"""

import re
from typing import Any

import structlog

from src.core.exceptions import AegisRAGException

logger = structlog.get_logger(__name__)


class NamespaceSecurityError(AegisRAGException):
    """Raised when a query violates namespace isolation rules."""

    def __init__(self, query: str, reason: str) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"Namespace security violation: {reason}",
            error_code=ErrorCode.FORBIDDEN,
            status_code=403,
            details={"query_preview": query[:200], "reason": reason},
        )


class Neo4jQueryValidator:
    """Validates that all Neo4j queries contain proper namespace filtering.

    This validator ensures data isolation by checking that every query
    includes a namespace_id filter before execution.

    Security Model:
    - All data nodes must have a namespace_id property
    - All queries must filter by namespace_id
    - Queries without namespace filtering are REJECTED

    Allowed Patterns:
    - WHERE n.namespace_id IN $allowed_namespaces
    - WHERE n.namespace_id = $namespace_id
    - MATCH (n {namespace_id: $ns})

    Admin Exceptions:
    - CREATE INDEX / DROP INDEX
    - SHOW INDEXES / SHOW CONSTRAINTS
    - CALL db.* procedures
    - Queries explicitly marked as admin
    """

    # Patterns that indicate valid namespace filtering
    VALID_PATTERNS = [
        # Property filter patterns
        r"namespace_id\s*IN\s*\$",              # namespace_id IN $allowed
        r"namespace_id\s*=\s*\$",               # namespace_id = $ns
        r"\.namespace_id\s*IN\s*\$",            # n.namespace_id IN $allowed
        r"\.namespace_id\s*=\s*\$",             # n.namespace_id = $ns
        # Property match patterns
        r"\{[^}]*namespace_id\s*:",             # {namespace_id: $ns}
        r"\{\s*namespace_id\s*:",               # { namespace_id: $ns}
        # SET patterns (for creating new nodes with namespace)
        r"SET\s+\w+\.namespace_id\s*=",         # SET n.namespace_id =
    ]

    # Queries that are allowed WITHOUT namespace filter (admin operations)
    ADMIN_PATTERNS = [
        r"^\s*CREATE\s+(INDEX|CONSTRAINT)",     # Index/Constraint creation
        r"^\s*DROP\s+(INDEX|CONSTRAINT)",       # Index/Constraint deletion
        r"^\s*SHOW\s+",                         # SHOW INDEXES, SHOW CONSTRAINTS, etc.
        r"^\s*CALL\s+db\.",                     # DB procedures
        r"^\s*CALL\s+apoc\.",                   # APOC procedures
        r"^\s*RETURN\s+1\s+AS\s+health",        # Health check
        r"^\s*:schema",                         # Schema info
    ]

    # Write operations that MUST have namespace
    WRITE_PATTERNS = [
        r"\bCREATE\s+\(",                       # CREATE (n)
        r"\bMERGE\s+\(",                        # MERGE (n)
        r"\bDELETE\s+",                         # DELETE
        r"\bSET\s+",                            # SET (property update)
        r"\bREMOVE\s+",                         # REMOVE
    ]

    @classmethod
    def validate(cls, query: str, skip_validation: bool = False) -> None:
        """Validate that a query contains proper namespace filtering.

        Args:
            query: The Cypher query to validate
            skip_validation: If True, skip validation (for admin operations)

        Raises:
            NamespaceSecurityError: If query lacks namespace filter
        """
        if skip_validation:
            logger.debug("namespace_validation_skipped", query_preview=query[:100])
            return

        query_upper = query.strip()

        # Check if it's an admin query (no namespace needed)
        for pattern in cls.ADMIN_PATTERNS:
            if re.match(pattern, query_upper, re.IGNORECASE | re.DOTALL):
                logger.debug(
                    "namespace_validation_admin_query",
                    query_preview=query[:100],
                )
                return

        # Check if query has valid namespace filtering
        for pattern in cls.VALID_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                logger.debug(
                    "namespace_validation_passed",
                    query_preview=query[:100],
                    matched_pattern=pattern,
                )
                return

        # No valid pattern found - REJECT the query
        logger.warning(
            "namespace_validation_rejected",
            query_preview=query[:200],
            reason="Query must contain namespace_id filter",
        )

        raise NamespaceSecurityError(
            query=query,
            reason=(
                "Query must contain namespace_id filter. "
                "Use one of these patterns:\n"
                "  - WHERE n.namespace_id IN $allowed_namespaces\n"
                "  - WHERE n.namespace_id = $namespace_id\n"
                "  - MATCH (n {namespace_id: $ns})\n"
                "  - SET n.namespace_id = $namespace_id"
            ),
        )

    @classmethod
    def is_write_query(cls, query: str) -> bool:
        """Check if query is a write operation.

        Args:
            query: The Cypher query to check

        Returns:
            True if query contains write operations
        """
        return any(re.search(pattern, query, re.IGNORECASE) for pattern in cls.WRITE_PATTERNS)


class SecureNeo4jClient:
    """Neo4j client wrapper that enforces namespace filtering on all queries.

    This wrapper ensures that every query executed through it contains
    proper namespace filtering, preventing accidental cross-namespace
    data access.

    Usage:
        from src.components.graph_rag.neo4j_client import Neo4jClient

        base_client = Neo4jClient()
        secure_client = SecureNeo4jClient(base_client)

        # This will be validated before execution
        results = await secure_client.execute_read(
            "MATCH (e:Entity) WHERE e.namespace_id IN $allowed_namespaces RETURN e",
            parameters={"allowed_namespaces": ["general", "user_project_1"]}
        )

        # This will RAISE NamespaceSecurityError
        results = await secure_client.execute_read(
            "MATCH (e:Entity) RETURN e"  # Missing namespace filter!
        )
    """

    def __init__(self, neo4j_client: Any, validate_queries: bool = True) -> None:
        """Initialize secure Neo4j client.

        Args:
            neo4j_client: Underlying Neo4jClient instance
            validate_queries: Whether to validate queries (default: True)
        """
        self._client = neo4j_client
        self._validate_queries = validate_queries

        logger.info(
            "SecureNeo4jClient initialized",
            validation_enabled=validate_queries,
        )

    async def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
        skip_validation: bool = False,
    ) -> list[dict[str, Any]]:
        """Execute a validated Cypher query.

        Args:
            query: Cypher query string (must contain namespace filter)
            parameters: Query parameters
            database: Database name
            skip_validation: Skip namespace validation (use with caution!)

        Returns:
            List of result records as dictionaries

        Raises:
            NamespaceSecurityError: If query lacks namespace filter
            DatabaseConnectionError: If query execution fails
        """
        if self._validate_queries and not skip_validation:
            Neo4jQueryValidator.validate(query)

        return await self._client.execute_query(query, parameters, database)

    async def execute_read(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
        skip_validation: bool = False,
    ) -> list[dict[str, Any]]:
        """Execute a validated read query.

        Args:
            query: Cypher read query string
            parameters: Query parameters
            database: Database name
            skip_validation: Skip namespace validation

        Returns:
            List of result records as dictionaries

        Raises:
            NamespaceSecurityError: If query lacks namespace filter
        """
        if self._validate_queries and not skip_validation:
            Neo4jQueryValidator.validate(query)

        return await self._client.execute_read(query, parameters, database)

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
        skip_validation: bool = False,
    ) -> dict[str, Any]:
        """Execute a validated write query.

        Args:
            query: Cypher write query string
            parameters: Query parameters
            database: Database name
            skip_validation: Skip namespace validation

        Returns:
            Dictionary with transaction summary

        Raises:
            NamespaceSecurityError: If query lacks namespace filter
        """
        if self._validate_queries and not skip_validation:
            Neo4jQueryValidator.validate(query)

        return await self._client.execute_write(query, parameters, database)

    async def health_check(self) -> bool:
        """Check if Neo4j server is healthy (no validation needed)."""
        return await self._client.health_check()

    async def close(self) -> None:
        """Close the underlying client connection."""
        await self._client.close()

    @property
    def driver(self):
        """Access underlying driver (for advanced operations)."""
        return self._client.driver

    # Proxy other methods to underlying client
    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to underlying client."""
        return getattr(self._client, name)


# Factory function for creating secure clients
def get_secure_neo4j_client(validate_queries: bool = True) -> SecureNeo4jClient:
    """Get a namespace-safe Neo4j client.

    Args:
        validate_queries: Whether to validate queries (default: True)

    Returns:
        SecureNeo4jClient instance wrapping the global Neo4jClient
    """
    from src.components.graph_rag.neo4j_client import get_neo4j_client

    base_client = get_neo4j_client()
    return SecureNeo4jClient(base_client, validate_queries=validate_queries)
