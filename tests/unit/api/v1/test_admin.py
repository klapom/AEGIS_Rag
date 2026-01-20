"""Unit tests for Admin API endpoints.

Sprint 17-53: Admin Statistics, Namespaces, and Relation Overrides
Sprint 58: Fixed patching strategy for module imports
Sprint 116: Dashboard Stats Cards

Tests cover:
- System statistics endpoint
- Dashboard statistics endpoint (Sprint 116.1)
- Namespace management
- Relation synonym overrides
- Error handling
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestGetSystemStatsEndpoint:
    """Tests for GET /admin/stats endpoint."""

    def test_get_system_stats_success(self, admin_test_client):
        """Test successful retrieval of system statistics.

        Uses admin_test_client fixture which applies patches BEFORE app import.
        """
        response = admin_test_client.get("/api/v1/admin/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["qdrant_total_chunks"] == 1523
        assert data["qdrant_vector_dimension"] == 1024
        assert data["bm25_corpus_size"] == 342
        assert data["neo4j_total_entities"] == 856
        assert data["neo4j_total_relations"] == 1204
        assert data["embedding_model"] == "BAAI/bge-m3"

    def test_get_system_stats_validates_structure(self, admin_test_client):
        """Test that response contains all required fields."""
        response = admin_test_client.get("/api/v1/admin/stats")

        assert response.status_code == 200
        data = response.json()

        # Validate all required fields are present
        required_fields = [
            "qdrant_total_chunks",
            "qdrant_collection_name",
            "qdrant_vector_dimension",
            "bm25_corpus_size",
            "neo4j_total_entities",
            "neo4j_total_relations",
            "last_reindex_timestamp",
            "embedding_model",
            "total_conversations",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_get_system_stats_with_partial_failures(self):
        """Test stats endpoint handles partial service failures gracefully."""
        # Mock with Neo4j failing
        mock_qdrant = AsyncMock()
        mock_qdrant.get_collection_info = AsyncMock(return_value=MagicMock(points_count=100))

        mock_embedding = MagicMock()
        mock_embedding.embedding_dim = 1024
        mock_embedding.model_name = "BAAI/bge-m3"

        mock_redis = AsyncMock()
        mock_redis_client = AsyncMock()
        mock_redis_client.scan = AsyncMock(return_value=(0, []))
        mock_redis.client = AsyncMock(return_value=mock_redis_client)

        with (
            patch("src.api.v1.admin.get_qdrant_client", return_value=mock_qdrant),
            patch("src.api.v1.admin.get_embedding_service", return_value=mock_embedding),
            patch(
                "src.components.graph_rag.neo4j_client.get_neo4j_client",
                side_effect=Exception("Neo4j unavailable"),
            ),
            patch("src.components.memory.get_redis_memory", return_value=mock_redis),
            patch(
                "src.api.v1.admin.get_last_reindex_timestamp", new_callable=AsyncMock
            ) as mock_reindex,
        ):

            mock_reindex.return_value = None

            from src.api.main import app

            client = TestClient(app)
            response = client.get("/api/v1/admin/stats")

            assert response.status_code == 200
            data = response.json()
            # Qdrant should work
            assert data["qdrant_total_chunks"] == 100
            # Neo4j should be None due to error
            assert data["neo4j_total_entities"] is None


class TestListNamespacesEndpoint:
    """Tests for GET /admin/namespaces endpoint."""

    def test_list_namespaces_success(self, namespace_test_client):
        """Test successful namespace listing."""
        response = namespace_test_client.get("/api/v1/admin/namespaces")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["namespaces"]) == 1
        assert data["namespaces"][0]["namespace_id"] == "default"
        assert data["namespaces"][0]["document_count"] == 42

    def test_list_namespaces_empty(self):
        """Test namespace listing with no namespaces."""
        mock_manager = AsyncMock()
        mock_manager.list_namespaces = AsyncMock(return_value=[])

        with patch("src.core.namespace.NamespaceManager", return_value=mock_manager):
            from src.api.main import app

            client = TestClient(app)
            response = client.get("/api/v1/admin/namespaces")

            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 0
            assert len(data["namespaces"]) == 0

    def test_list_namespaces_multiple(self):
        """Test listing multiple namespaces."""
        namespaces = []
        for i in range(3):
            ns = MagicMock()
            ns.namespace_id = f"namespace_{i}"
            ns.namespace_type = "project"
            ns.document_count = 10 * (i + 1)
            ns.description = f"Namespace {i}"
            namespaces.append(ns)

        mock_manager = AsyncMock()
        mock_manager.list_namespaces = AsyncMock(return_value=namespaces)

        with patch("src.core.namespace.NamespaceManager", return_value=mock_manager):
            from src.api.main import app

            client = TestClient(app)
            response = client.get("/api/v1/admin/namespaces")

            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 3
            assert len(data["namespaces"]) == 3

    def test_list_namespaces_error(self):
        """Test error handling for namespace listing."""
        mock_manager = AsyncMock()
        mock_manager.list_namespaces = AsyncMock(side_effect=Exception("Database error"))

        with patch("src.core.namespace.NamespaceManager", return_value=mock_manager):
            from src.api.main import app

            client = TestClient(app)
            response = client.get("/api/v1/admin/namespaces")

            assert response.status_code == 500
            data = response.json()
            # Check for error message in response (may be 'detail' or 'message')
            assert "Failed to list namespaces" in str(data)


class TestGetRelationSynonymsEndpoint:
    """Tests for GET /admin/graph/relation-synonyms endpoint."""

    @pytest.mark.asyncio
    async def test_get_relation_synonyms_success(self, test_client, monkeypatch):
        """Test successful retrieval of relation synonyms."""
        overrides = {
            "USES": "USED_BY",
            "ACTED_IN": "STARRED_IN",
            "RELATED_TO": "RELATES_TO",
        }

        mock_dedup = AsyncMock()
        mock_dedup.get_all_manual_overrides = AsyncMock(return_value=overrides)

        with patch(
            "src.components.graph_rag.hybrid_relation_deduplicator.get_hybrid_relation_deduplicator",
            return_value=mock_dedup,
        ):
            response = test_client.get("/api/v1/admin/graph/relation-synonyms")

            assert response.status_code == 200
            data = response.json()
            assert data["total_overrides"] == 3
            assert data["overrides"]["USES"] == "USED_BY"
            assert data["overrides"]["ACTED_IN"] == "STARRED_IN"

    @pytest.mark.asyncio
    async def test_get_relation_synonyms_empty(self, test_client, monkeypatch):
        """Test retrieval when no synonyms exist."""
        mock_dedup = AsyncMock()
        mock_dedup.get_all_manual_overrides = AsyncMock(return_value={})

        with patch(
            "src.components.graph_rag.hybrid_relation_deduplicator.get_hybrid_relation_deduplicator",
            return_value=mock_dedup,
        ):
            response = test_client.get("/api/v1/admin/graph/relation-synonyms")

            assert response.status_code == 200
            data = response.json()
            assert data["total_overrides"] == 0
            assert data["overrides"] == {}

    @pytest.mark.asyncio
    async def test_get_relation_synonyms_error(self, test_client, monkeypatch):
        """Test error handling."""
        with patch(
            "src.components.graph_rag.hybrid_relation_deduplicator.get_hybrid_relation_deduplicator",
            side_effect=Exception("Redis error"),
        ):
            response = test_client.get("/api/v1/admin/graph/relation-synonyms")

            assert response.status_code == 500


class TestAddRelationSynonymEndpoint:
    """Tests for POST /admin/graph/relation-synonyms endpoint."""

    @pytest.mark.asyncio
    async def test_add_relation_synonym_success(self, test_client, monkeypatch):
        """Test successful synonym addition."""
        mock_dedup = AsyncMock()
        mock_dedup.add_manual_override = AsyncMock()

        with patch(
            "src.components.graph_rag.hybrid_relation_deduplicator.get_hybrid_relation_deduplicator",
            return_value=mock_dedup,
        ):
            response = test_client.post(
                "/api/v1/admin/graph/relation-synonyms",
                json={"from_type": "USES", "to_type": "USED_BY"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["from_type"] == "USES"
            assert data["to_type"] == "USED_BY"
            assert data["status"] == "created"

    @pytest.mark.asyncio
    async def test_add_relation_synonym_empty_types(self, test_client, monkeypatch):
        """Test validation rejects empty types.

        Note: Pydantic returns 422 for validation errors, but endpoint
        may return 400 for custom validation. Accept either.
        """
        response = test_client.post(
            "/api/v1/admin/graph/relation-synonyms",
            json={"from_type": "", "to_type": "USED_BY"},
        )

        # Pydantic returns 422 for min_length validation failures
        assert response.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_add_relation_synonym_whitespace(self, test_client, monkeypatch):
        """Test validation rejects whitespace-only types."""
        response = test_client.post(
            "/api/v1/admin/graph/relation-synonyms",
            json={"from_type": "   ", "to_type": "USED_BY"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_add_relation_synonym_redis_error(self, test_client, monkeypatch):
        """Test error handling when Redis fails."""
        mock_dedup = AsyncMock()
        mock_dedup.add_manual_override = AsyncMock(side_effect=Exception("Redis write failed"))

        with patch(
            "src.components.graph_rag.hybrid_relation_deduplicator.get_hybrid_relation_deduplicator",
            return_value=mock_dedup,
        ):
            response = test_client.post(
                "/api/v1/admin/graph/relation-synonyms",
                json={"from_type": "USES", "to_type": "USED_BY"},
            )

            assert response.status_code == 500


class TestDeleteRelationSynonymEndpoint:
    """Tests for DELETE /admin/graph/relation-synonyms/{from_type} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_relation_synonym_success(self, test_client, monkeypatch):
        """Test successful synonym deletion."""
        mock_dedup = AsyncMock()
        mock_dedup.remove_manual_override = AsyncMock()

        with patch(
            "src.components.graph_rag.hybrid_relation_deduplicator.get_hybrid_relation_deduplicator",
            return_value=mock_dedup,
        ):
            response = test_client.delete("/api/v1/admin/graph/relation-synonyms/USES")

            assert response.status_code == 200
            data = response.json()
            assert data["from_type"] == "USES"
            assert data["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_delete_relation_synonym_not_found(self, test_client, monkeypatch):
        """Test deletion of non-existent synonym.

        The endpoint checks 'if not success' from remove_manual_override,
        returning 404 when the method returns False.
        """
        mock_dedup = AsyncMock()
        # Return False to indicate override was not found
        mock_dedup.remove_manual_override = AsyncMock(return_value=False)

        with patch(
            "src.components.graph_rag.hybrid_relation_deduplicator.get_hybrid_relation_deduplicator",
            return_value=mock_dedup,
        ):
            response = test_client.delete("/api/v1/admin/graph/relation-synonyms/NONEXISTENT")

            assert response.status_code == 404


class TestResetRelationSynonymsEndpoint:
    """Tests for POST /admin/graph/relation-synonyms/reset endpoint."""

    @pytest.mark.asyncio
    async def test_reset_relation_synonyms_success(self, test_client, monkeypatch):
        """Test successful reset of all synonyms."""
        mock_dedup = AsyncMock()
        mock_dedup.clear_all_manual_overrides = AsyncMock(return_value=5)

        with patch(
            "src.components.graph_rag.hybrid_relation_deduplicator.get_hybrid_relation_deduplicator",
            return_value=mock_dedup,
        ):
            response = test_client.post("/api/v1/admin/graph/relation-synonyms/reset")

            assert response.status_code == 200
            data = response.json()
            assert data["cleared_count"] == 5
            # Endpoint returns 'reset_complete' as status
            assert data["status"] == "reset_complete"

    @pytest.mark.asyncio
    async def test_reset_relation_synonyms_empty(self, test_client, monkeypatch):
        """Test reset when no synonyms exist."""
        mock_dedup = AsyncMock()
        mock_dedup.clear_all_manual_overrides = AsyncMock(return_value=0)

        with patch(
            "src.components.graph_rag.hybrid_relation_deduplicator.get_hybrid_relation_deduplicator",
            return_value=mock_dedup,
        ):
            response = test_client.post("/api/v1/admin/graph/relation-synonyms/reset")

            assert response.status_code == 200
            data = response.json()
            assert data["cleared_count"] == 0


# ============================================================================
# Sprint 116 Feature 116.1: Dashboard Stats Cards Tests
# ============================================================================


class TestGetDashboardStatsEndpoint:
    """Tests for GET /admin/dashboard/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_success(self, test_client, monkeypatch):
        """Test successful retrieval of dashboard statistics."""
        # Mock Qdrant client
        mock_qdrant = AsyncMock()
        mock_collection_info = MagicMock()
        mock_collection_info.points_count = 1523
        mock_qdrant.get_collection_info = AsyncMock(return_value=mock_collection_info)

        # Mock Neo4j client
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock()
        # First call returns entities count
        # Second call returns relations count
        mock_neo4j.execute_query.side_effect = [
            [{"count": 2842}],  # entities
            [{"count": 4103}],  # relations
        ]

        # Mock Namespace Manager
        mock_namespace = MagicMock()
        mock_namespace.namespace_id = "default"
        mock_namespace.document_count = 156
        mock_manager = AsyncMock()
        mock_manager.list_namespaces = AsyncMock(return_value=[mock_namespace])

        # Mock Domains
        mock_domains_response = MagicMock()
        mock_domains_response.domains = ["domain1", "domain2", "domain3", "domain4", "domain5", "domain6", "domain7", "domain8"]

        with (
            patch("src.components.vector_search.qdrant_client.get_qdrant_client", return_value=mock_qdrant),
            patch("src.components.graph_rag.neo4j_client.get_neo4j_client", return_value=mock_neo4j),
            patch("src.core.namespace.NamespaceManager", return_value=mock_manager),
            patch("src.api.v1.domain_training.list_domains", new_callable=AsyncMock, return_value=mock_domains_response),
        ):
            response = test_client.get("/api/v1/admin/dashboard/stats")

            assert response.status_code == 200
            data = response.json()

            assert data["total_documents"] == 156
            assert data["total_entities"] == 2842
            assert data["total_relations"] == 4103
            assert data["total_chunks"] == 1523
            assert data["active_domains"] == 8
            assert "storage_used_mb" in data
            assert isinstance(data["storage_used_mb"], (int, float))
            assert data["storage_used_mb"] > 0

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_validates_structure(self, test_client, monkeypatch):
        """Test that response contains all required fields."""
        # Mock minimal responses
        mock_qdrant = AsyncMock()
        mock_collection_info = MagicMock()
        mock_collection_info.points_count = 100
        mock_qdrant.get_collection_info = AsyncMock(return_value=mock_collection_info)

        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(side_effect=[[{"count": 50}], [{"count": 75}]])

        mock_manager = AsyncMock()
        mock_manager.list_namespaces = AsyncMock(return_value=[])

        mock_domains_response = MagicMock()
        mock_domains_response.domains = []

        with (
            patch("src.components.vector_search.qdrant_client.get_qdrant_client", return_value=mock_qdrant),
            patch("src.components.graph_rag.neo4j_client.get_neo4j_client", return_value=mock_neo4j),
            patch("src.core.namespace.NamespaceManager", return_value=mock_manager),
            patch("src.api.v1.domain_training.list_domains", new_callable=AsyncMock, return_value=mock_domains_response),
        ):
            response = test_client.get("/api/v1/admin/dashboard/stats")

            assert response.status_code == 200
            data = response.json()

            # Validate all required fields are present
            required_fields = [
                "total_documents",
                "total_entities",
                "total_relations",
                "total_chunks",
                "active_domains",
                "storage_used_mb",
            ]
            for field in required_fields:
                assert field in data, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_with_partial_failures(self, test_client, monkeypatch):
        """Test stats endpoint handles partial service failures gracefully."""
        # Mock Qdrant working
        mock_qdrant = AsyncMock()
        mock_collection_info = MagicMock()
        mock_collection_info.points_count = 500
        mock_qdrant.get_collection_info = AsyncMock(return_value=mock_collection_info)

        # Mock Neo4j failing
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(side_effect=Exception("Neo4j unavailable"))

        # Mock Namespaces working
        mock_namespace = MagicMock()
        mock_namespace.document_count = 42
        mock_manager = AsyncMock()
        mock_manager.list_namespaces = AsyncMock(return_value=[mock_namespace])

        # Mock Domains working
        mock_domains_response = MagicMock()
        mock_domains_response.domains = ["domain1", "domain2"]

        with (
            patch("src.components.vector_search.qdrant_client.get_qdrant_client", return_value=mock_qdrant),
            patch("src.components.graph_rag.neo4j_client.get_neo4j_client", return_value=mock_neo4j),
            patch("src.core.namespace.NamespaceManager", return_value=mock_manager),
            patch("src.api.v1.domain_training.list_domains", new_callable=AsyncMock, return_value=mock_domains_response),
        ):
            response = test_client.get("/api/v1/admin/dashboard/stats")

            assert response.status_code == 200
            data = response.json()

            # Qdrant should work
            assert data["total_chunks"] == 500
            # Neo4j should return 0 due to error handling
            assert data["total_entities"] == 0
            assert data["total_relations"] == 0
            # Namespaces should work
            assert data["total_documents"] == 42
            # Domains should work
            assert data["active_domains"] == 2

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_multiple_namespaces(self, test_client, monkeypatch):
        """Test aggregation of document counts across multiple namespaces."""
        # Mock minimal services
        mock_qdrant = AsyncMock()
        mock_collection_info = MagicMock()
        mock_collection_info.points_count = 100
        mock_qdrant.get_collection_info = AsyncMock(return_value=mock_collection_info)

        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(side_effect=[[{"count": 10}], [{"count": 20}]])

        # Mock 3 namespaces with different document counts
        namespaces = []
        for i, doc_count in enumerate([50, 75, 31]):
            ns = MagicMock()
            ns.namespace_id = f"namespace_{i}"
            ns.document_count = doc_count
            namespaces.append(ns)

        mock_manager = AsyncMock()
        mock_manager.list_namespaces = AsyncMock(return_value=namespaces)

        mock_domains_response = MagicMock()
        mock_domains_response.domains = []

        with (
            patch("src.components.vector_search.qdrant_client.get_qdrant_client", return_value=mock_qdrant),
            patch("src.components.graph_rag.neo4j_client.get_neo4j_client", return_value=mock_neo4j),
            patch("src.core.namespace.NamespaceManager", return_value=mock_manager),
            patch("src.api.v1.domain_training.list_domains", new_callable=AsyncMock, return_value=mock_domains_response),
        ):
            response = test_client.get("/api/v1/admin/dashboard/stats")

            assert response.status_code == 200
            data = response.json()

            # Should sum all namespace document counts
            assert data["total_documents"] == 50 + 75 + 31  # 156

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_storage_calculation(self, test_client, monkeypatch):
        """Test storage size calculation is reasonable."""
        mock_qdrant = AsyncMock()
        mock_collection_info = MagicMock()
        mock_collection_info.points_count = 1000  # 1000 chunks
        mock_qdrant.get_collection_info = AsyncMock(return_value=mock_collection_info)

        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(side_effect=[[{"count": 0}], [{"count": 0}]])

        mock_manager = AsyncMock()
        mock_manager.list_namespaces = AsyncMock(return_value=[])

        mock_domains_response = MagicMock()
        mock_domains_response.domains = []

        with (
            patch("src.components.vector_search.qdrant_client.get_qdrant_client", return_value=mock_qdrant),
            patch("src.components.graph_rag.neo4j_client.get_neo4j_client", return_value=mock_neo4j),
            patch("src.core.namespace.NamespaceManager", return_value=mock_manager),
            patch("src.api.v1.domain_training.list_domains", new_callable=AsyncMock, return_value=mock_domains_response),
        ):
            response = test_client.get("/api/v1/admin/dashboard/stats")

            assert response.status_code == 200
            data = response.json()

            # BGE-M3: 1024 dense + ~100 sparse = 1124 dims * 4 bytes * 1.5 overhead
            # 1000 chunks * 1124 * 4 * 1.5 / (1024*1024) = ~6.4 MB
            storage_mb = data["storage_used_mb"]
            assert isinstance(storage_mb, (int, float))
            assert 5.0 <= storage_mb <= 8.0  # Reasonable range for 1000 chunks
