"""Integration tests for Namespace Isolation.

Sprint 41 Feature 41.1: Namespace Isolation Layer

These tests verify that namespace isolation works correctly across
all storage backends (Qdrant, Neo4j, BM25) with real services.

Prerequisites:
- Neo4j running on localhost:7687
- Qdrant running on localhost:6333
- Clean database state (run scripts/clear_all_data.py first)

Run with:
    poetry run pytest tests/integration/test_namespace_isolation.py -v --tb=short
"""

import os
import uuid

import pytest

# Override hosts for local testing
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["QDRANT_HOST"] = "localhost"
os.environ["QDRANT_PORT"] = "6333"
os.environ["QDRANT_GRPC_PORT"] = "6334"

from qdrant_client.models import Distance, PayloadSchemaType, PointStruct, VectorParams

from src.core.namespace import (
    NamespaceManager,
)
from src.core.neo4j_safety import (
    NamespaceSecurityError,
    get_secure_neo4j_client,
)


@pytest.fixture(scope="function")
def namespace_manager():
    """Create NamespaceManager for tests."""
    return NamespaceManager()


@pytest.fixture(scope="function")
def secure_neo4j():
    """Create SecureNeo4jClient for tests."""
    return get_secure_neo4j_client()


@pytest.fixture(scope="module")
def test_namespaces():
    """Generate unique test namespace IDs."""
    unique_id = str(uuid.uuid4())[:8]
    return {
        "ns_a": f"test_ns_a_{unique_id}",
        "ns_b": f"test_ns_b_{unique_id}",
        "general": "test_general",
    }


class TestNamespaceIsolationNeo4j:
    """Integration tests for Neo4j namespace isolation."""

    @pytest.mark.asyncio
    async def test_query_without_namespace_rejected(self, secure_neo4j):
        """Test that queries without namespace filter are rejected."""
        with pytest.raises(NamespaceSecurityError) as exc_info:
            await secure_neo4j.execute_read("MATCH (e:Entity) RETURN e LIMIT 10")

        assert "namespace_id filter" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_query_with_namespace_allowed(self, secure_neo4j, test_namespaces):
        """Test that queries with namespace filter are allowed."""
        # Create test node
        await secure_neo4j.execute_write(
            """
            CREATE (e:Entity {name: 'TestEntity'})
            SET e.namespace_id = $namespace_id
            RETURN e
            """,
            parameters={"namespace_id": test_namespaces["ns_a"]},
        )

        # Query with namespace filter should work
        result = await secure_neo4j.execute_read(
            """
            MATCH (e:Entity)
            WHERE e.namespace_id IN $allowed_namespaces
            RETURN e.name AS name
            """,
            parameters={"allowed_namespaces": [test_namespaces["ns_a"]]},
        )

        assert len(result) >= 1
        assert result[0]["name"] == "TestEntity"

    @pytest.mark.asyncio
    async def test_namespace_isolation_neo4j(self, secure_neo4j, test_namespaces):
        """Test that data in different namespaces is isolated."""
        # Create nodes in two different namespaces
        await secure_neo4j.execute_write(
            """
            CREATE (e:Entity {name: 'EntityInA'})
            SET e.namespace_id = $namespace_id
            """,
            parameters={"namespace_id": test_namespaces["ns_a"]},
        )

        await secure_neo4j.execute_write(
            """
            CREATE (e:Entity {name: 'EntityInB'})
            SET e.namespace_id = $namespace_id
            """,
            parameters={"namespace_id": test_namespaces["ns_b"]},
        )

        # Query namespace A - should only see EntityInA
        result_a = await secure_neo4j.execute_read(
            """
            MATCH (e:Entity)
            WHERE e.namespace_id IN $allowed_namespaces
            RETURN e.name AS name
            """,
            parameters={"allowed_namespaces": [test_namespaces["ns_a"]]},
        )

        names_a = [r["name"] for r in result_a]
        assert "EntityInA" in names_a or "TestEntity" in names_a
        assert "EntityInB" not in names_a

        # Query namespace B - should only see EntityInB
        result_b = await secure_neo4j.execute_read(
            """
            MATCH (e:Entity)
            WHERE e.namespace_id IN $allowed_namespaces
            RETURN e.name AS name
            """,
            parameters={"allowed_namespaces": [test_namespaces["ns_b"]]},
        )

        names_b = [r["name"] for r in result_b]
        assert "EntityInB" in names_b
        assert "EntityInA" not in names_b
        assert "TestEntity" not in names_b

    @pytest.mark.asyncio
    async def test_cross_namespace_query(self, secure_neo4j, test_namespaces):
        """Test querying across multiple namespaces."""
        # Query both namespaces
        result = await secure_neo4j.execute_read(
            """
            MATCH (e:Entity)
            WHERE e.namespace_id IN $allowed_namespaces
            RETURN e.name AS name, e.namespace_id AS namespace
            """,
            parameters={"allowed_namespaces": [test_namespaces["ns_a"], test_namespaces["ns_b"]]},
        )

        # Should see entities from both namespaces
        namespaces_found = {r["namespace"] for r in result}
        assert (
            test_namespaces["ns_a"] in namespaces_found
            or test_namespaces["ns_b"] in namespaces_found
        )


class TestNamespaceIsolationQdrant:
    """Integration tests for Qdrant namespace isolation."""

    @pytest.mark.asyncio
    async def test_qdrant_namespace_filter(self, namespace_manager, test_namespaces):
        """Test Qdrant search respects namespace filter."""
        collection_name = f"test_ns_{uuid.uuid4().hex[:8]}"

        # Create collection
        await namespace_manager.qdrant.async_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=4, distance=Distance.COSINE),
        )

        # Create payload index on namespace_id
        await namespace_manager.qdrant.async_client.create_payload_index(
            collection_name=collection_name,
            field_name="namespace_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )

        # Override collection name temporarily
        original_collection = namespace_manager._collection_name
        namespace_manager._collection_name = collection_name

        try:
            # Insert points in different namespaces
            points = [
                PointStruct(
                    id=1,
                    vector=[0.1, 0.2, 0.3, 0.4],
                    payload={
                        "text": "Document in namespace A",
                        "namespace_id": test_namespaces["ns_a"],
                    },
                ),
                PointStruct(
                    id=2,
                    vector=[0.2, 0.3, 0.4, 0.5],
                    payload={
                        "text": "Document in namespace B",
                        "namespace_id": test_namespaces["ns_b"],
                    },
                ),
                PointStruct(
                    id=3,
                    vector=[0.3, 0.4, 0.5, 0.6],
                    payload={
                        "text": "General document",
                        "namespace_id": test_namespaces["general"],
                    },
                ),
            ]

            await namespace_manager.qdrant.async_client.upsert(
                collection_name=collection_name,
                points=points,
            )

            # Search only in namespace A
            results_a = await namespace_manager.search_qdrant(
                query_vector=[0.1, 0.2, 0.3, 0.4],
                allowed_namespaces=[test_namespaces["ns_a"]],
                limit=10,
            )

            # Should only find document in namespace A
            assert len(results_a) == 1
            assert results_a[0]["payload"]["namespace_id"] == test_namespaces["ns_a"]
            assert "namespace A" in results_a[0]["payload"]["text"]

        finally:
            namespace_manager._collection_name = original_collection
            await namespace_manager.qdrant.async_client.delete_collection(collection_name)

    @pytest.mark.asyncio
    async def test_qdrant_cross_namespace_search(self, namespace_manager, test_namespaces):
        """Test Qdrant search across multiple namespaces."""
        collection_name = f"test_cross_{uuid.uuid4().hex[:8]}"

        await namespace_manager.qdrant.async_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=4, distance=Distance.COSINE),
        )

        await namespace_manager.qdrant.async_client.create_payload_index(
            collection_name=collection_name,
            field_name="namespace_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )

        original_collection = namespace_manager._collection_name
        namespace_manager._collection_name = collection_name

        try:
            points = [
                PointStruct(
                    id=1,
                    vector=[0.1, 0.2, 0.3, 0.4],
                    payload={"text": "Doc A", "namespace_id": test_namespaces["ns_a"]},
                ),
                PointStruct(
                    id=2,
                    vector=[0.2, 0.3, 0.4, 0.5],
                    payload={"text": "Doc B", "namespace_id": test_namespaces["ns_b"]},
                ),
                PointStruct(
                    id=3,
                    vector=[0.3, 0.4, 0.5, 0.6],
                    payload={"text": "Doc General", "namespace_id": test_namespaces["general"]},
                ),
            ]

            await namespace_manager.qdrant.async_client.upsert(
                collection_name=collection_name, points=points
            )

            # Search in both ns_a and general
            results = await namespace_manager.search_qdrant(
                query_vector=[0.1, 0.2, 0.3, 0.4],
                allowed_namespaces=[test_namespaces["ns_a"], test_namespaces["general"]],
                limit=10,
            )

            # Should find documents from both namespaces
            namespaces_found = {r["payload"]["namespace_id"] for r in results}
            assert test_namespaces["ns_a"] in namespaces_found
            assert test_namespaces["general"] in namespaces_found
            assert test_namespaces["ns_b"] not in namespaces_found

        finally:
            namespace_manager._collection_name = original_collection
            await namespace_manager.qdrant.async_client.delete_collection(collection_name)

    @pytest.mark.asyncio
    async def test_qdrant_empty_namespace_returns_empty(self, namespace_manager):
        """Test that empty namespace list returns no results."""
        results = await namespace_manager.search_qdrant(
            query_vector=[0.1, 0.2, 0.3, 0.4],
            allowed_namespaces=[],
            limit=10,
        )

        assert results == []


class TestNamespaceBM25:
    """Integration tests for BM25 namespace filtering."""

    def test_bm25_filter_results(self, namespace_manager, test_namespaces):
        """Test BM25 result filtering by namespace."""
        # Simulate BM25 results with mixed namespaces
        bm25_results = [
            {"text": "Doc 1", "score": 0.9, "metadata": {"namespace_id": test_namespaces["ns_a"]}},
            {"text": "Doc 2", "score": 0.8, "metadata": {"namespace_id": test_namespaces["ns_b"]}},
            {
                "text": "Doc 3",
                "score": 0.7,
                "metadata": {"namespace_id": test_namespaces["general"]},
            },
            {"text": "Doc 4", "score": 0.6, "metadata": {}},  # No namespace = default
        ]

        # Filter for namespace A only
        filtered = namespace_manager.filter_bm25_results(
            bm25_results,
            allowed_namespaces=[test_namespaces["ns_a"]],
        )

        assert len(filtered) == 1
        assert filtered[0]["text"] == "Doc 1"

    def test_bm25_filter_cross_namespace(self, namespace_manager, test_namespaces):
        """Test BM25 filtering across multiple namespaces."""
        bm25_results = [
            {"text": "Doc 1", "score": 0.9, "metadata": {"namespace_id": test_namespaces["ns_a"]}},
            {"text": "Doc 2", "score": 0.8, "metadata": {"namespace_id": test_namespaces["ns_b"]}},
            {
                "text": "Doc 3",
                "score": 0.7,
                "metadata": {"namespace_id": test_namespaces["general"]},
            },
        ]

        # Filter for ns_a and general
        filtered = namespace_manager.filter_bm25_results(
            bm25_results,
            allowed_namespaces=[test_namespaces["ns_a"], test_namespaces["general"]],
        )

        assert len(filtered) == 2
        texts = [r["text"] for r in filtered]
        assert "Doc 1" in texts
        assert "Doc 3" in texts
        assert "Doc 2" not in texts


class TestNamespaceManagerIntegration:
    """Integration tests for NamespaceManager operations."""

    @pytest.mark.asyncio
    async def test_create_namespace_creates_indexes(self, namespace_manager, test_namespaces):
        """Test that namespace creation ensures indexes exist."""
        result = await namespace_manager.create_namespace(
            namespace_id=test_namespaces["ns_a"],
            namespace_type="test",
            description="Test namespace",
        )

        assert result.namespace_id == test_namespaces["ns_a"]
        assert result.namespace_type == "test"

    @pytest.mark.asyncio
    async def test_delete_namespace(self, namespace_manager):
        """Test namespace deletion."""
        # Create a unique namespace for deletion test
        delete_ns = f"test_delete_{uuid.uuid4().hex[:8]}"

        # First create some data
        await namespace_manager.neo4j.execute_write(
            """
            CREATE (e:Entity {name: 'ToDelete'})
            SET e.namespace_id = $namespace_id
            """,
            parameters={"namespace_id": delete_ns},
        )

        # Delete namespace
        stats = await namespace_manager.delete_namespace(delete_ns)

        # Verify deletion stats
        assert "neo4j_nodes_deleted" in stats

        # Verify data is gone
        result = await namespace_manager.neo4j.execute_read(
            """
            MATCH (e:Entity)
            WHERE e.namespace_id IN $allowed_namespaces
            RETURN count(e) AS count
            """,
            parameters={"allowed_namespaces": [delete_ns]},
        )

        assert result[0]["count"] == 0
