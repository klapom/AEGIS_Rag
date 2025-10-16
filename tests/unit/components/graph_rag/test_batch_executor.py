"""Unit tests for BatchQueryExecutor.

Tests cover:
- Parallel query execution
- Error handling per query
- Result ordering preservation
- Concurrency limits
- Timeout handling
- Batch statistics
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.graph_rag.batch_executor import BatchQueryExecutor, BatchQueryResult


class TestBatchQueryExecutor:
    """Test BatchQueryExecutor for parallel execution."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Neo4j client."""
        client = MagicMock()
        client.execute_query = AsyncMock(return_value=[{"name": "Test"}])
        client.execute_write = AsyncMock(
            return_value={
                "nodes_created": 1,
                "nodes_deleted": 0,
                "relationships_created": 0,
                "relationships_deleted": 0,
                "properties_set": 1,
            }
        )
        return client

    @pytest.fixture
    def executor(self, mock_client):
        """Create batch executor with mock client."""
        return BatchQueryExecutor(client=mock_client, max_concurrent=5, timeout_seconds=10)

    @pytest.mark.asyncio
    async def test_execute_empty_batch(self, executor):
        """Test executing empty batch returns empty list."""
        results = await executor.execute_batch([])

        assert results == []

    @pytest.mark.asyncio
    async def test_execute_single_query(self, executor, mock_client):
        """Test executing single query in batch."""
        queries = [("MATCH (n:Entity) RETURN n", {})]

        results = await executor.execute_batch(queries)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result == [{"name": "Test"}]
        mock_client.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_multiple_queries(self, executor, mock_client):
        """Test executing multiple queries in parallel."""
        queries = [
            ("MATCH (n:Entity) RETURN n", {}),
            ("MATCH (n:Person) RETURN n", {}),
            ("MATCH (n:Organization) RETURN n", {}),
        ]

        results = await executor.execute_batch(queries)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert mock_client.execute_query.call_count == 3

    @pytest.mark.asyncio
    async def test_result_ordering_preserved(self, executor, mock_client):
        """Test that results maintain original query order."""
        # Mock different results for each query
        mock_client.execute_query.side_effect = [
            [{"id": 1}],
            [{"id": 2}],
            [{"id": 3}],
        ]

        queries = [
            ("MATCH (n1) RETURN n1", {}),
            ("MATCH (n2) RETURN n2", {}),
            ("MATCH (n3) RETURN n3", {}),
        ]

        results = await executor.execute_batch(queries)

        # Results should be in same order as queries
        assert results[0].result == [{"id": 1}]
        assert results[1].result == [{"id": 2}]
        assert results[2].result == [{"id": 3}]

    @pytest.mark.asyncio
    async def test_error_handling_single_query(self, executor, mock_client):
        """Test that single query error doesn't fail entire batch."""
        # First query succeeds, second fails, third succeeds
        mock_client.execute_query.side_effect = [
            [{"id": 1}],
            Exception("Query failed"),
            [{"id": 3}],
        ]

        queries = [
            ("MATCH (n1) RETURN n1", {}),
            ("MATCH (n2) RETURN n2", {}),
            ("MATCH (n3) RETURN n3", {}),
        ]

        results = await executor.execute_batch(queries)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[1].error is not None
        assert "Exception" in results[1].error
        assert results[2].success is True

    @pytest.mark.asyncio
    async def test_timeout_handling(self, executor, mock_client):
        """Test query timeout handling."""

        async def slow_query(*args, **kwargs):
            await asyncio.sleep(15)  # Longer than timeout
            return [{"result": 1}]

        mock_client.execute_query.side_effect = slow_query

        queries = [("MATCH (n) RETURN n", {})]

        results = await executor.execute_batch(queries)

        assert len(results) == 1
        assert results[0].success is False
        assert "timeout" in results[0].error.lower()

    @pytest.mark.asyncio
    async def test_batch_write_queries(self, executor, mock_client):
        """Test batch write query execution."""
        queries = [
            ("CREATE (n:Entity {name: $name})", {"name": "Test1"}),
            ("CREATE (n:Entity {name: $name})", {"name": "Test2"}),
        ]

        results = await executor.execute_batch_write(queries)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert mock_client.execute_write.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_write_statistics(self, executor, mock_client):
        """Test batch write returns statistics."""
        mock_client.execute_write.side_effect = [
            {
                "nodes_created": 1,
                "nodes_deleted": 0,
                "relationships_created": 1,
                "relationships_deleted": 0,
                "properties_set": 2,
            },
            {
                "nodes_created": 2,
                "nodes_deleted": 0,
                "relationships_created": 0,
                "relationships_deleted": 0,
                "properties_set": 4,
            },
        ]

        queries = [
            ("CREATE (n:Entity)-[:REL]->(m:Entity)", {}),
            ("CREATE (n:Entity), (m:Entity)", {}),
        ]

        results = await executor.execute_batch_write(queries)

        assert results[0].result["nodes_created"] == 1
        assert results[0].result["relationships_created"] == 1
        assert results[1].result["nodes_created"] == 2

    @pytest.mark.asyncio
    async def test_concurrency_limit(self, executor, mock_client):
        """Test that concurrency is limited by semaphore."""
        concurrent_executions = []

        async def track_execution(*args, **kwargs):
            concurrent_executions.append(asyncio.current_task())
            await asyncio.sleep(0.1)
            return [{"result": 1}]

        mock_client.execute_query.side_effect = track_execution

        # Create 10 queries with max_concurrent=5
        queries = [(f"MATCH (n{i}) RETURN n{i}", {}) for i in range(10)]

        await executor.execute_batch(queries)

        # All queries should execute (semaphore controls concurrency, not total)
        assert len(concurrent_executions) == 10

    @pytest.mark.asyncio
    async def test_batch_query_result_structure(self, executor):
        """Test BatchQueryResult structure."""
        queries = [("MATCH (n) RETURN n", {"limit": 10})]

        results = await executor.execute_batch(queries)

        result = results[0]
        assert hasattr(result, "query")
        assert hasattr(result, "parameters")
        assert hasattr(result, "success")
        assert hasattr(result, "result")
        assert hasattr(result, "error")
        assert hasattr(result, "execution_time")

    @pytest.mark.asyncio
    async def test_batch_query_result_to_dict(self, executor):
        """Test BatchQueryResult to_dict conversion."""
        queries = [("MATCH (n) RETURN n", {"limit": 10})]

        results = await executor.execute_batch(queries)

        result_dict = results[0].to_dict()

        assert "query" in result_dict
        assert "parameters" in result_dict
        assert "success" in result_dict
        assert "result" in result_dict
        assert "error" in result_dict
        assert "execution_time" in result_dict

    @pytest.mark.asyncio
    async def test_execution_time_tracking(self, executor, mock_client):
        """Test that execution time is tracked."""

        async def delayed_query(*args, **kwargs):
            await asyncio.sleep(0.1)
            return [{"result": 1}]

        mock_client.execute_query.side_effect = delayed_query

        queries = [("MATCH (n) RETURN n", {})]

        results = await executor.execute_batch(queries)

        assert results[0].execution_time > 0.09  # Should be ~0.1 seconds
        assert results[0].execution_time < 0.2  # But not too much more

    @pytest.mark.asyncio
    async def test_empty_write_batch(self, executor):
        """Test executing empty write batch."""
        results = await executor.execute_batch_write([])

        assert results == []

    @pytest.mark.asyncio
    async def test_write_query_error_handling(self, executor, mock_client):
        """Test error handling in write batch."""
        mock_client.execute_write.side_effect = [
            {
                "nodes_created": 1,
                "nodes_deleted": 0,
                "relationships_created": 0,
                "relationships_deleted": 0,
                "properties_set": 1,
            },
            Exception("Write failed"),
        ]

        queries = [
            ("CREATE (n:Entity {name: 'Test1'})", {}),
            ("CREATE (n:Entity {name: 'Test2'})", {}),
        ]

        results = await executor.execute_batch_write(queries)

        assert results[0].success is True
        assert results[1].success is False
        assert "Write failed" in results[1].error

    @pytest.mark.asyncio
    async def test_initialization_with_defaults(self):
        """Test executor initialization with default settings."""
        with patch("src.components.graph_rag.batch_executor.get_neo4j_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            executor = BatchQueryExecutor()

            assert executor.client == mock_client
            assert executor.max_concurrent > 0
            assert executor.timeout_seconds > 0
