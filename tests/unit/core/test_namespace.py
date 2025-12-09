"""Unit tests for Namespace Management.

Sprint 41 Feature 41.1: Namespace Isolation Layer

Tests the NamespaceManager to ensure:
1. Namespace creation and deletion work correctly
2. Qdrant filters are built properly
3. Neo4j namespace queries are correct
4. BM25 result filtering works
5. Cross-namespace queries are supported
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_client.models import FieldCondition, Filter, MatchAny

from src.core.namespace import (
    DEFAULT_NAMESPACE,
    NAMESPACE_PREFIXES,
    NamespaceInfo,
    NamespaceManager,
    get_namespace_manager,
)


class TestNamespaceInfo:
    """Tests for NamespaceInfo dataclass."""

    def test_create_namespace_info(self):
        """Test creating NamespaceInfo."""
        info = NamespaceInfo(
            namespace_id="user_alice_project1",
            namespace_type="project",
            description="Alice's project",
            document_count=100,
        )

        assert info.namespace_id == "user_alice_project1"
        assert info.namespace_type == "project"
        assert info.description == "Alice's project"
        assert info.document_count == 100

    def test_default_values(self):
        """Test NamespaceInfo with default values."""
        info = NamespaceInfo(
            namespace_id="test",
            namespace_type="test",
        )

        assert info.description == ""
        assert info.document_count == 0


class TestNamespaceManager:
    """Tests for NamespaceManager class."""

    @pytest.fixture
    def mock_qdrant_client(self):
        """Create mock Qdrant client."""
        client = MagicMock()
        client.async_client = MagicMock()
        client.async_client.create_payload_index = AsyncMock()
        client.async_client.delete = AsyncMock()
        client.async_client.scroll = AsyncMock(return_value=([], None))
        client.search = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def mock_neo4j_client(self):
        """Create mock secure Neo4j client."""
        client = MagicMock()
        client.execute_read = AsyncMock(return_value=[])
        client.execute_write = AsyncMock(return_value={})
        return client

    @pytest.fixture
    def namespace_manager(self, mock_qdrant_client, mock_neo4j_client):
        """Create NamespaceManager with mocked clients."""
        return NamespaceManager(
            qdrant_client=mock_qdrant_client,
            neo4j_client=mock_neo4j_client,
            collection_name="test_collection",
        )

    # =========================================================================
    # Test: Namespace CRUD Operations
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_namespace(self, namespace_manager, mock_qdrant_client):
        """Test namespace creation."""
        result = await namespace_manager.create_namespace(
            namespace_id="eval_hotpotqa",
            namespace_type="evaluation",
            description="HotpotQA benchmark",
        )

        assert isinstance(result, NamespaceInfo)
        assert result.namespace_id == "eval_hotpotqa"
        assert result.namespace_type == "evaluation"
        assert result.description == "HotpotQA benchmark"

        # Verify Qdrant index was created
        mock_qdrant_client.async_client.create_payload_index.assert_called()

    @pytest.mark.asyncio
    async def test_delete_namespace(self, namespace_manager, mock_qdrant_client, mock_neo4j_client):
        """Test namespace deletion."""
        mock_qdrant_client.async_client.delete = AsyncMock()
        mock_neo4j_client.execute_write = AsyncMock(
            return_value={"nodes_deleted": 10, "relationships_deleted": 5}
        )

        result = await namespace_manager.delete_namespace("test_namespace")

        assert "qdrant_points_deleted" in result
        assert "neo4j_nodes_deleted" in result

        # Verify Qdrant delete was called with correct filter
        mock_qdrant_client.async_client.delete.assert_called_once()

    # =========================================================================
    # Test: Qdrant Filter Building
    # =========================================================================

    def test_build_qdrant_filter_single_namespace(self, namespace_manager):
        """Test building Qdrant filter for single namespace."""
        filter_obj = namespace_manager.build_qdrant_filter(["general"])

        assert isinstance(filter_obj, Filter)
        assert len(filter_obj.must) == 1

        condition = filter_obj.must[0]
        assert condition.key == "namespace_id"
        assert isinstance(condition.match, MatchAny)
        assert condition.match.any == ["general"]

    def test_build_qdrant_filter_multiple_namespaces(self, namespace_manager):
        """Test building Qdrant filter for multiple namespaces."""
        filter_obj = namespace_manager.build_qdrant_filter(
            ["general", "user_alice_proj1", "eval_hotpotqa"]
        )

        condition = filter_obj.must[0]
        assert condition.match.any == ["general", "user_alice_proj1", "eval_hotpotqa"]

    def test_build_qdrant_filter_with_additional_filter(self, namespace_manager):
        """Test building Qdrant filter with additional conditions."""
        additional_filter = Filter(
            must=[
                FieldCondition(
                    key="file_type",
                    match=MatchAny(any=["pdf", "docx"]),
                )
            ]
        )

        filter_obj = namespace_manager.build_qdrant_filter(
            ["general"],
            additional_filter=additional_filter,
        )

        # Should have 2 conditions: namespace + file_type
        assert len(filter_obj.must) == 2

    # =========================================================================
    # Test: Qdrant Search
    # =========================================================================

    @pytest.mark.asyncio
    async def test_search_qdrant_empty_namespaces(self, namespace_manager):
        """Test that empty namespaces returns empty results."""
        result = await namespace_manager.search_qdrant(
            query_vector=[0.1] * 1024,
            allowed_namespaces=[],
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_search_qdrant_with_results(self, namespace_manager, mock_qdrant_client):
        """Test Qdrant search returns results with namespace info."""
        mock_qdrant_client.search = AsyncMock(
            return_value=[
                {
                    "id": "chunk_1",
                    "score": 0.95,
                    "payload": {
                        "text": "Test content",
                        "namespace_id": "general",
                    },
                }
            ]
        )

        result = await namespace_manager.search_qdrant(
            query_vector=[0.1] * 1024,
            allowed_namespaces=["general"],
            limit=10,
        )

        assert len(result) == 1
        assert result[0]["source_namespace"] == "general"
        mock_qdrant_client.search.assert_called_once()

    # =========================================================================
    # Test: Neo4j Namespace Clause Building
    # =========================================================================

    def test_build_neo4j_namespace_clause(self, namespace_manager):
        """Test building Neo4j WHERE clause for namespace."""
        clause, params = namespace_manager.build_neo4j_namespace_clause(
            allowed_namespaces=["general", "user_proj_1"],
            node_alias="e",
        )

        assert "e.namespace_id IN $allowed_namespaces" in clause
        assert params["allowed_namespaces"] == ["general", "user_proj_1"]

    def test_build_neo4j_namespace_clause_custom_alias(self, namespace_manager):
        """Test Neo4j clause with custom node alias."""
        clause, params = namespace_manager.build_neo4j_namespace_clause(
            allowed_namespaces=["test"],
            node_alias="node",
        )

        assert "node.namespace_id IN $allowed_namespaces" in clause

    # =========================================================================
    # Test: Neo4j Graph Local Search
    # =========================================================================

    @pytest.mark.asyncio
    async def test_search_neo4j_local_empty_namespaces(self, namespace_manager):
        """Test that empty namespaces returns empty results."""
        result = await namespace_manager.search_neo4j_local(
            query_terms=["test"],
            allowed_namespaces=[],
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_search_neo4j_local_with_results(self, namespace_manager, mock_neo4j_client):
        """Test Neo4j local search returns formatted results."""
        mock_neo4j_client.execute_read = AsyncMock(
            return_value=[
                {
                    "id": "chunk_1",
                    "text": "Test content",
                    "document_id": "doc_1",
                    "source": "/path/to/doc.pdf",
                    "namespace_id": "general",
                    "relevance": 3,
                    "entities": ["Entity1", "Entity2"],
                }
            ]
        )

        result = await namespace_manager.search_neo4j_local(
            query_terms=["test", "query"],
            allowed_namespaces=["general"],
            top_k=10,
        )

        assert len(result) == 1
        assert result[0]["source_channel"] == "graph_local"
        assert result[0]["source_namespace"] == "general"
        assert result[0]["matched_entities"] == ["Entity1", "Entity2"]

    # =========================================================================
    # Test: Neo4j Graph Global Search
    # =========================================================================

    @pytest.mark.asyncio
    async def test_search_neo4j_global_empty_namespaces(self, namespace_manager):
        """Test that empty namespaces returns empty results."""
        result = await namespace_manager.search_neo4j_global(
            query_terms=["test"],
            allowed_namespaces=[],
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_search_neo4j_global_with_results(self, namespace_manager, mock_neo4j_client):
        """Test Neo4j global search returns formatted results."""
        mock_neo4j_client.execute_read = AsyncMock(
            return_value=[
                {
                    "id": "chunk_1",
                    "text": "Community content",
                    "document_id": "doc_1",
                    "source": "/path/to/doc.pdf",
                    "namespace_id": "general",
                    "community_id": "community_123",
                    "relevance": 5,
                }
            ]
        )

        result = await namespace_manager.search_neo4j_global(
            query_terms=["test"],
            allowed_namespaces=["general"],
            top_k=10,
        )

        assert len(result) == 1
        assert result[0]["source_channel"] == "graph_global"
        assert result[0]["community_id"] == "community_123"

    # =========================================================================
    # Test: BM25 Result Filtering
    # =========================================================================

    def test_filter_bm25_results(self, namespace_manager):
        """Test BM25 result filtering by namespace."""
        results = [
            {"text": "Doc 1", "metadata": {"namespace_id": "general"}},
            {"text": "Doc 2", "metadata": {"namespace_id": "user_proj_1"}},
            {"text": "Doc 3", "metadata": {"namespace_id": "other_namespace"}},
            {"text": "Doc 4", "metadata": {}},  # No namespace = default
        ]

        filtered = namespace_manager.filter_bm25_results(
            results,
            allowed_namespaces=["general", DEFAULT_NAMESPACE],
        )

        assert len(filtered) == 2
        assert filtered[0]["text"] == "Doc 1"
        assert filtered[1]["text"] == "Doc 4"
        assert filtered[0]["source_namespace"] == "general"
        assert filtered[1]["source_namespace"] == DEFAULT_NAMESPACE

    def test_filter_bm25_results_empty_namespaces(self, namespace_manager):
        """Test BM25 filtering with empty namespaces."""
        results = [
            {"text": "Doc 1", "metadata": {"namespace_id": "general"}},
        ]

        filtered = namespace_manager.filter_bm25_results(results, allowed_namespaces=[])

        assert filtered == []

    # =========================================================================
    # Test: Namespace Type Inference
    # =========================================================================

    @pytest.mark.parametrize(
        "namespace_id,expected_type",
        [
            ("general", "general"),
            ("default", "general"),
            ("eval_hotpotqa", "eval"),
            ("eval_msmarco", "eval"),
            ("user_alice_proj1", "user"),
            ("proj_123", "proj"),
            ("test_unit_001", "test"),
            ("custom_namespace", "custom"),
        ],
    )
    def test_infer_namespace_type(self, namespace_manager, namespace_id, expected_type):
        """Test namespace type inference from ID."""
        result = namespace_manager._infer_namespace_type(namespace_id)
        assert result == expected_type


class TestGetNamespaceManager:
    """Tests for get_namespace_manager singleton."""

    def test_returns_namespace_manager(self):
        """Test that factory returns NamespaceManager."""
        # Reset singleton for test
        import src.core.namespace as ns_module

        ns_module._namespace_manager = None

        with patch("src.core.namespace.NamespaceManager") as MockManager:
            MockManager.return_value = MagicMock()
            result = get_namespace_manager()

            assert result is not None
            MockManager.assert_called_once()

    def test_returns_same_instance(self):
        """Test that factory returns same instance (singleton)."""
        import src.core.namespace as ns_module

        # Create a mock manager
        mock_manager = MagicMock(spec=NamespaceManager)
        ns_module._namespace_manager = mock_manager

        result1 = get_namespace_manager()
        result2 = get_namespace_manager()

        assert result1 is result2
        assert result1 is mock_manager

        # Cleanup
        ns_module._namespace_manager = None


class TestNamespaceConstants:
    """Tests for namespace constants."""

    def test_default_namespace(self):
        """Test default namespace constant."""
        assert DEFAULT_NAMESPACE == "default"

    def test_namespace_prefixes(self):
        """Test namespace prefix definitions."""
        assert "eval_" in NAMESPACE_PREFIXES
        assert "user_" in NAMESPACE_PREFIXES
        assert "proj_" in NAMESPACE_PREFIXES
        assert "test_" in NAMESPACE_PREFIXES


class TestNamespaceIsolation:
    """Integration-style tests for namespace isolation."""

    @pytest.fixture
    def manager_with_mocks(self):
        """Create manager with comprehensive mocks."""
        mock_qdrant = MagicMock()
        mock_qdrant.async_client = MagicMock()
        mock_qdrant.search = AsyncMock()

        mock_neo4j = MagicMock()
        mock_neo4j.execute_read = AsyncMock()
        mock_neo4j.execute_write = AsyncMock()

        return NamespaceManager(
            qdrant_client=mock_qdrant,
            neo4j_client=mock_neo4j,
        )

    @pytest.mark.asyncio
    async def test_search_only_returns_allowed_namespaces(self, manager_with_mocks):
        """Test that search only returns results from allowed namespaces."""
        # Mock Qdrant to return results from multiple namespaces
        manager_with_mocks._qdrant_client.search = AsyncMock(
            return_value=[
                {"id": "1", "payload": {"namespace_id": "general", "text": "General doc"}},
                {"id": "2", "payload": {"namespace_id": "user_proj_1", "text": "Project doc"}},
            ]
        )

        # Search only in "general"
        await manager_with_mocks.search_qdrant(
            query_vector=[0.1] * 1024,
            allowed_namespaces=["general"],
        )

        # Verify filter was applied (Qdrant client receives filter)
        call_args = manager_with_mocks._qdrant_client.search.call_args
        assert call_args is not None

        # The filter should restrict to "general" only
        filter_arg = call_args.kwargs.get("query_filter")
        assert filter_arg is not None
        assert filter_arg.must[0].match.any == ["general"]

    @pytest.mark.asyncio
    async def test_cross_namespace_search(self, manager_with_mocks):
        """Test search across multiple namespaces."""
        manager_with_mocks._qdrant_client.search = AsyncMock(return_value=[])

        await manager_with_mocks.search_qdrant(
            query_vector=[0.1] * 1024,
            allowed_namespaces=["general", "user_alice_proj", "eval_test"],
        )

        # Verify filter includes all namespaces
        call_args = manager_with_mocks._qdrant_client.search.call_args
        filter_arg = call_args.kwargs.get("query_filter")
        assert set(filter_arg.must[0].match.any) == {"general", "user_alice_proj", "eval_test"}
