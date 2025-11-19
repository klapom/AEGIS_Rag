"""Neo4j Client Wrapper with Connection Pooling and Error Handling.

This module provides a production-ready wrapper around the Neo4j driver with:
- Connection pooling
- Automatic retry logic
- Health checks
- Async context manager support
- Query execution methods
"""

from contextlib import asynccontextmanager
from typing import Any

import structlog
from neo4j import AsyncDriver, AsyncGraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import settings
from src.core.exceptions import DatabaseConnectionError

logger = structlog.get_logger(__name__)

# Constants
DEFAULT_POOL_SIZE = 10
DEFAULT_CONNECTION_TIMEOUT = 30
DEFAULT_MAX_RETRY_ATTEMPTS = 3

class Neo4jClient:
    """Production-ready Neo4j client with connection pooling and error handling."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        max_connection_pool_size: int = DEFAULT_POOL_SIZE,
        connection_timeout: int = DEFAULT_CONNECTION_TIMEOUT,
    ) -> None:
        """Initialize Neo4j client wrapper.

        Args:
            uri: Neo4j connection URI (default: from settings)
            user: Neo4j username (default: from settings)
            password: Neo4j password (default: from settings)
            database: Neo4j database name (default: from settings)
            max_connection_pool_size: Maximum connection pool size (default: 10)
            connection_timeout: Connection timeout in seconds (default: 30)
        """
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password.get_secret_value()
        self.database = database or settings.neo4j_database
        self.max_connection_pool_size = max_connection_pool_size
        self.connection_timeout = connection_timeout

        self._driver: AsyncDriver | None = None

        logger.info(
            "Initializing Neo4j client",
            uri=self.uri,
            user=self.user,
            database=self.database,
            max_pool_size=self.max_connection_pool_size,
        )

    @property
    def driver(self) -> AsyncDriver:
        """Get Neo4j driver (lazy initialization).

        Returns:
            AsyncDriver instance

        Raises:
            DatabaseConnectionError: If driver initialization fails
        """
        if self._driver is None:
            try:
                self._driver = AsyncGraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    max_connection_pool_size=self.max_connection_pool_size,
                    connection_timeout=self.connection_timeout,
                )
                logger.info("Neo4j driver initialized")
            except Exception as e:
                logger.error("Failed to initialize Neo4j driver", error=str(e))
                raise DatabaseConnectionError(
                    "Neo4j", f"Failed to initialize Neo4j driver: {e}"
                ) from e
        return self._driver

    @retry(
        stop=stop_after_attempt(DEFAULT_MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ServiceUnavailable),
    )
    async def health_check(self) -> bool:
        """Check if Neo4j server is healthy.

        Returns:
            True if server is healthy

        Raises:
            DatabaseConnectionError: If connection fails after retries
        """
        try:
            async with self.driver.session(database=self.database) as session:
                result = await session.run("RETURN 1 AS health")
                record = await result.single()
                if record and record["health"] == 1:
                    logger.info("Neo4j health check passed")
                    return True
                return False
        except ServiceUnavailable:
            # Let tenacity retry on ServiceUnavailable
            raise
        except Exception as e:
            logger.error("Neo4j health check failed", error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Neo4j health check failed: {e}") from e

    @retry(
        stop=stop_after_attempt(DEFAULT_MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ServiceUnavailable, Neo4jError)),
    )
    async def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters (default: None)
            database: Database name (default: from settings)

        Returns:
            list of result records as dictionaries

        Raises:
            DatabaseConnectionError: If query execution fails
        """
        db = database or self.database
        params = parameters or {}

        try:
            async with self.driver.session(database=db) as session:
                result = await session.run(query, params)
                records = await result.data()
                logger.debug(
                    "Query executed successfully",
                    query=query[:100],  # Log first 100 chars
                    record_count=len(records),
                )
                return records
        except (ServiceUnavailable, Neo4jError):
            # Let tenacity retry on these exceptions
            raise
        except Exception as e:
            logger.error("Query execution failed", query=query[:100], error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Query execution failed: {e}") from e

    async def execute_read(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a read-only Cypher query and return results.

        Alias for execute_query for consistency with Neo4j terminology.

        Args:
            query: Cypher query string
            parameters: Query parameters (default: None)
            database: Database name (default: from settings)

        Returns:
            list of result records as dictionaries

        Raises:
            DatabaseConnectionError: If query execution fails
        """
        return await self.execute_query(query, parameters, database)

    @retry(
        stop=stop_after_attempt(DEFAULT_MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ServiceUnavailable, Neo4jError)),
    )
    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> dict[str, Any]:
        """Execute a write transaction.

        Args:
            query: Cypher write query string
            parameters: Query parameters (default: None)
            database: Database name (default: from settings)

        Returns:
            Dictionary with transaction summary

        Raises:
            DatabaseConnectionError: If write transaction fails
        """
        db = database or self.database
        params = parameters or {}

        try:
            async with self.driver.session(database=db) as session:
                result = await session.run(query, params)
                summary = await result.consume()

                return {
                    "nodes_created": summary.counters.nodes_created,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_created": summary.counters.relationships_created,
                    "relationships_deleted": summary.counters.relationships_deleted,
                    "properties_set": summary.counters.properties_set,
                }
        except (ServiceUnavailable, Neo4jError):
            # Let tenacity retry on these exceptions
            raise
        except Exception as e:
            logger.error("Write transaction failed", query=query[:100], error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Write transaction failed: {e}") from e

    async def create_temporal_indexes(self) -> dict[str, bool]:
        """Create indexes on temporal properties for performance.

        Returns:
            Dictionary with index creation status

        Raises:
            DatabaseConnectionError: If index creation fails
        """
        indexes = {
            "entity_valid_from": "CREATE INDEX entity_valid_from IF NOT EXISTS FOR (e:Entity) ON (e.valid_from)",
            "entity_valid_to": "CREATE INDEX entity_valid_to IF NOT EXISTS FOR (e:Entity) ON (e.valid_to)",
            "entity_transaction_from": "CREATE INDEX entity_transaction_from IF NOT EXISTS FOR (e:Entity) ON (e.transaction_from)",
            "entity_transaction_to": "CREATE INDEX entity_transaction_to IF NOT EXISTS FOR (e:Entity) ON (e.transaction_to)",
            "entity_version_id": "CREATE INDEX entity_version_id IF NOT EXISTS FOR (e:Entity) ON (e.version_id)",
            "entity_version_number": "CREATE INDEX entity_version_number IF NOT EXISTS FOR (e:Entity) ON (e.version_number)",
        }

        results = {}
        for index_name, query in indexes.items():
            try:
                await self.execute_write(query)
                results[index_name] = True
                logger.info("Created temporal index", index_name=index_name)
            except Exception as e:
                logger.warning("Failed to create index", index_name=index_name, error=str(e))
                results[index_name] = False

        return results

    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed")

    async def __aenter__(self) -> "Neo4jClient":
        """Async context manager entry.

        Returns:
            Neo4jClient instance
        """
        # Driver is initialized lazily on first use
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        await self.close()

# Global client instance (singleton pattern)
_neo4j_client: Neo4jClient | None = None

def get_neo4j_client() -> Neo4jClient:
    """Get global Neo4j client instance (singleton).

    Returns:
        Neo4jClient instance
    """
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
    return _neo4j_client

@asynccontextmanager
async def get_neo4j_client_async() -> None:
    """Async context manager for Neo4j client.

    Usage:
        async with get_neo4j_client_async() as client:
            await client.health_check()

    Yields:
        Neo4jClient instance
    """
    client = get_neo4j_client()
    try:
        yield client
    finally:
        # Connection is pooled, no need to close here
        pass
