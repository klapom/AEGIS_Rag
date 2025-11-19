"""Batch Query Executor for Parallel Neo4j Query Execution.

This module provides efficient batch query execution with:
- Parallel query execution using asyncio.gather()
- Concurrency control with semaphores
- Per-query error handling (don't fail entire batch)
- Result ordering preservation
- Timeout management
"""

import asyncio
from typing import Any

import structlog

from src.components.graph_rag.neo4j_client import Neo4jClient, get_neo4j_client
from src.core.config import settings

logger = structlog.get_logger(__name__)


class BatchQueryResult:
    """Result of a single query in a batch.

    Attributes:
        query: Original query string
        parameters: Query parameters
        success: Whether query succeeded
        result: Query result (if successful)
        error: Error message (if failed)
        execution_time: Execution time in seconds
    """

    def __init__(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        success: bool = False,
        result: Any = None,
        error: str | None = None,
        execution_time: float = 0.0,
    ) -> None:
        """Initialize batch query result."""
        self.query = query
        self.parameters = parameters or {}
        self.success = success
        self.result = result
        self.error = error
        self.execution_time = execution_time

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "query": self.query[:100],  # Truncate for logging
            "parameters": self.parameters,
            "success": self.success,
            "result": self.result if self.success else None,
            "error": self.error,
            "execution_time": round(self.execution_time, 3),
        }


class BatchQueryExecutor:
    """Executor for parallel Neo4j query execution.

    Example:
        >>> executor = BatchQueryExecutor()
        >>> queries = [
        ...     ("MATCH (n:Entity) RETURN n", {}),
        ...     ("MATCH (n:Person) RETURN n", {}),
        ... ]
        >>> results = await executor.execute_batch(queries)
        >>> for result in results:
        ...     print(result.success, len(result.result))
    """

    def __init__(
        self,
        client: Neo4jClient | None = None,
        max_concurrent: int | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        """Initialize batch query executor.

        Args:
            client: Neo4j client instance (default: global client)
            max_concurrent: Maximum concurrent queries (default: from settings)
            timeout_seconds: Query timeout in seconds (default: from settings)
        """
        self.client = client or get_neo4j_client()
        self.max_concurrent = max_concurrent or settings.graph_batch_query_max_concurrent
        self.timeout_seconds = timeout_seconds or settings.graph_query_timeout_seconds

        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

        logger.info(
            "BatchQueryExecutor initialized",
            max_concurrent=self.max_concurrent,
            timeout_seconds=self.timeout_seconds,
        )

    async def _execute_single_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        index: int = 0,
    ) -> tuple[int, BatchQueryResult]:
        """Execute a single query with error handling.

        Args:
            query: Cypher query string
            parameters: Query parameters
            index: Query index in batch (for ordering)

        Returns:
            Tuple of (index, BatchQueryResult)
        """
        start_time = asyncio.get_event_loop().time()
        params = parameters or {}

        try:
            # Acquire semaphore for concurrency control
            async with self._semaphore:
                # Execute with timeout
                result = await asyncio.wait_for(
                    self.client.execute_query(query, params), timeout=self.timeout_seconds
                )

                execution_time = asyncio.get_event_loop().time() - start_time

                logger.debug(
                    "Query executed successfully",
                    index=index,
                    query=query[:50],
                    execution_time=round(execution_time, 3),
                )

                return (
                    index,
                    BatchQueryResult(
                        query=query,
                        parameters=params,
                        success=True,
                        result=result,
                        execution_time=execution_time,
                    ),
                )

        except TimeoutError:
            execution_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"Query timeout after {self.timeout_seconds}s"
            logger.warning(
                "Query timeout", index=index, query=query[:50], timeout=self.timeout_seconds
            )

            return (
                index,
                BatchQueryResult(
                    query=query,
                    parameters=params,
                    success=False,
                    error=error_msg,
                    execution_time=execution_time,
                ),
            )

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error("Query execution failed", index=index, query=query[:50], error=error_msg)

            return (
                index,
                BatchQueryResult(
                    query=query,
                    parameters=params,
                    success=False,
                    error=error_msg,
                    execution_time=execution_time,
                ),
            )

    async def execute_batch(
        self, queries: list[tuple[str, dict[str, Any] | None]]
    ) -> list[BatchQueryResult]:
        """Execute multiple queries in parallel.

        Args:
            queries: list of (query, parameters) tuples

        Returns:
            list of BatchQueryResult in original order

        Example:
            >>> queries = [
            ...     ("MATCH (n:Entity) RETURN n LIMIT 10", {}),
            ...     ("MATCH (n:Person) RETURN n LIMIT 10", {}),
            ... ]
            >>> results = await executor.execute_batch(queries)
        """
        if not queries:
            logger.warning("Empty query batch provided")
            return []

        logger.info(
            "Executing batch queries", batch_size=len(queries), max_concurrent=self.max_concurrent
        )

        # Create tasks for all queries with their indices
        tasks = [
            self._execute_single_query(query, params, index)
            for index, (query, params) in enumerate(queries)
        ]

        # Execute all queries in parallel
        results_with_indices = await asyncio.gather(*tasks, return_exceptions=False)

        # Sort by index to preserve original order
        results_with_indices.sort(key=lambda x: x[0])

        # Extract results without indices
        results = [result for _, result in results_with_indices]

        # Calculate statistics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_time = sum(r.execution_time for r in results)
        avg_time = total_time / len(results) if results else 0

        logger.info(
            "Batch execution completed",
            total=len(results),
            successful=successful,
            failed=failed,
            avg_execution_time=round(avg_time, 3),
        )

        return results

    async def _execute_single_write_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        index: int = 0,
    ) -> tuple[int, BatchQueryResult]:
        """Execute a single write query with error handling.

        Args:
            query: Cypher write query string
            parameters: Query parameters
            index: Query index in batch (for ordering)

        Returns:
            Tuple of (index, BatchQueryResult)
        """
        start_time = asyncio.get_event_loop().time()
        params = parameters or {}

        try:
            # Acquire semaphore for concurrency control
            async with self._semaphore:
                # Execute with timeout
                result = await asyncio.wait_for(
                    self.client.execute_write(query, params), timeout=self.timeout_seconds
                )

                execution_time = asyncio.get_event_loop().time() - start_time

                logger.debug(
                    "Write query executed successfully",
                    index=index,
                    query=query[:50],
                    nodes_created=result.get("nodes_created", 0),
                    relationships_created=result.get("relationships_created", 0),
                    execution_time=round(execution_time, 3),
                )

                return (
                    index,
                    BatchQueryResult(
                        query=query,
                        parameters=params,
                        success=True,
                        result=result,
                        execution_time=execution_time,
                    ),
                )

        except TimeoutError:
            execution_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"Write query timeout after {self.timeout_seconds}s"
            logger.warning(
                "Write query timeout", index=index, query=query[:50], timeout=self.timeout_seconds
            )

            return (
                index,
                BatchQueryResult(
                    query=query,
                    parameters=params,
                    success=False,
                    error=error_msg,
                    execution_time=execution_time,
                ),
            )

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(
                "Write query execution failed", index=index, query=query[:50], error=error_msg
            )

            return (
                index,
                BatchQueryResult(
                    query=query,
                    parameters=params,
                    success=False,
                    error=error_msg,
                    execution_time=execution_time,
                ),
            )

    async def execute_batch_write(
        self, queries: list[tuple[str, dict[str, Any] | None]]
    ) -> list[BatchQueryResult]:
        """Execute multiple write queries in parallel.

        Args:
            queries: list of (query, parameters) tuples for write operations

        Returns:
            list of BatchQueryResult in original order

        Example:
            >>> queries = [
            ...     ("CREATE (n:Entity {name: $name})", {"name": "Test1"}),
            ...     ("CREATE (n:Entity {name: $name})", {"name": "Test2"}),
            ... ]
            >>> results = await executor.execute_batch_write(queries)
        """
        if not queries:
            logger.warning("Empty write query batch provided")
            return []

        logger.info(
            "Executing batch write queries",
            batch_size=len(queries),
            max_concurrent=self.max_concurrent,
        )

        # Create tasks for all queries with their indices
        tasks = [
            self._execute_single_write_query(query, params, index)
            for index, (query, params) in enumerate(queries)
        ]

        # Execute all queries in parallel
        results_with_indices = await asyncio.gather(*tasks, return_exceptions=False)

        # Sort by index to preserve original order
        results_with_indices.sort(key=lambda x: x[0])

        # Extract results without indices
        results = [result for _, result in results_with_indices]

        # Calculate statistics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_nodes_created = sum(
            r.result.get("nodes_created", 0) for r in results if r.success and r.result
        )
        total_relationships_created = sum(
            r.result.get("relationships_created", 0) for r in results if r.success and r.result
        )

        logger.info(
            "Batch write execution completed",
            total=len(results),
            successful=successful,
            failed=failed,
            nodes_created=total_nodes_created,
            relationships_created=total_relationships_created,
        )

        return results
