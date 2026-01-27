"""Unit tests for Graph Entity and Relation Management API endpoints.

Sprint 121 Feature 121.5a-d: Entity/Relation Delete API + OpenAPI

Tests the following endpoints:
- POST /api/v1/admin/graph/entities/search — Entity list/search with pagination
- GET /api/v1/admin/graph/entities/{entity_id} — Entity detail with relationships
- DELETE /api/v1/admin/graph/entities/{entity_id} — Entity deletion (cascade)
- POST /api/v1/admin/graph/relations/search — Relation list/search with pagination
- DELETE /api/v1/admin/graph/relations — Relation deletion
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.v1.graph_entities import (
    DeleteResponse,
    EntityDetailResponse,
    EntityListRequest,
    EntityListResponse,
    EntityResponse,
    RelationDeleteRequest,
    RelationListRequest,
    RelationListResponse,
    RelationResponse,
    delete_entity,
    delete_relation,
    get_entity_detail,
    list_entities,
    list_relations,
)


# ============================================================================
# Fixtures: Mock Clients & Test Data
# ============================================================================


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client for graph entity tests."""
    client = MagicMock()
    client.execute_read = AsyncMock()
    client.execute_write = AsyncMock()
    return client


@pytest.fixture
def sample_entity_results():
    """Sample entity query results from Neo4j."""
    return [
        {
            "entity_id": "albert_einstein",
            "entity_name": "Albert Einstein",
            "entity_type": "PERSON",
            "description": "Theoretical physicist",
            "source_id": "doc_001",
            "file_path": "/data/physics.pdf",
            "namespace_id": "research",
            "created_at": "2026-01-15T10:00:00Z",
            "relation_count": 42,
        },
        {
            "entity_id": "relativity_theory",
            "entity_name": "Theory of Relativity",
            "entity_type": "CONCEPT",
            "description": "Fundamental physics theory",
            "source_id": "doc_001",
            "file_path": "/data/physics.pdf",
            "namespace_id": "research",
            "created_at": "2026-01-15T10:05:00Z",
            "relation_count": 18,
        },
        {
            "entity_id": "princeton_university",
            "entity_name": "Princeton University",
            "entity_type": "ORGANIZATION",
            "description": None,
            "source_id": "doc_002",
            "file_path": "/data/institutions.pdf",
            "namespace_id": "research",
            "created_at": "2026-01-15T10:10:00Z",
            "relation_count": 7,
        },
    ]


@pytest.fixture
def sample_relation_results():
    """Sample relation query results from Neo4j."""
    return [
        {
            "source_entity_id": "albert_einstein",
            "source_entity_name": "Albert Einstein",
            "target_entity_id": "relativity_theory",
            "target_entity_name": "Theory of Relativity",
            "relation_type": "DISCOVERED",
            "description": "Developed the theory",
            "weight": 0.95,
            "namespace_id": "research",
        },
        {
            "source_entity_id": "albert_einstein",
            "source_entity_name": "Albert Einstein",
            "target_entity_id": "princeton_university",
            "target_entity_name": "Princeton University",
            "relation_type": "WORKED_AT",
            "description": None,
            "weight": 0.87,
            "namespace_id": "research",
        },
        {
            "source_entity_id": "relativity_theory",
            "source_entity_name": "Theory of Relativity",
            "target_entity_id": "physics_field",
            "target_entity_name": "Physics Field",
            "relation_type": "BELONGS_TO",
            "description": None,
            "weight": 1.0,
            "namespace_id": "research",
        },
    ]


# ============================================================================
# Tests: POST /api/v1/admin/graph/entities/search
# ============================================================================


class TestListEntities:
    """Test entity listing/search endpoint."""

    @pytest.mark.asyncio
    async def test_list_entities_success(self, mock_neo4j_client, sample_entity_results):
        """Test successful entity list retrieval with pagination."""
        # Setup: Mock returns total count, then paginated results
        mock_neo4j_client.execute_read.side_effect = [
            [{"total": 100}],  # Count query
            sample_entity_results,  # Paginated results
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = EntityListRequest(page=1, page_size=50)
            response = await list_entities(request)

            assert isinstance(response, EntityListResponse)
            assert len(response.entities) == 3
            assert response.total == 100
            assert response.page == 1
            assert response.page_size == 50
            assert response.total_pages == 2

            # Verify first entity
            first_entity = response.entities[0]
            assert first_entity.entity_id == "albert_einstein"
            assert first_entity.entity_name == "Albert Einstein"
            assert first_entity.entity_type == "PERSON"
            assert first_entity.relation_count == 42

    @pytest.mark.asyncio
    async def test_list_entities_with_search_filter(self, mock_neo4j_client, sample_entity_results):
        """Test entity search with search term filter."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"total": 1}],
            [sample_entity_results[0]],
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = EntityListRequest(search="einstein", page=1, page_size=50)
            response = await list_entities(request)

            assert len(response.entities) == 1
            assert response.entities[0].entity_name == "Albert Einstein"

            # Verify that execute_read was called twice
            assert mock_neo4j_client.execute_read.call_count == 2

    @pytest.mark.asyncio
    async def test_list_entities_with_entity_type_filter(
        self, mock_neo4j_client, sample_entity_results
    ):
        """Test entity list with entity type filter."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"total": 1}],
            [sample_entity_results[0]],
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = EntityListRequest(
                entity_type="PERSON", page=1, page_size=50
            )
            response = await list_entities(request)

            assert len(response.entities) == 1
            assert response.entities[0].entity_type == "PERSON"

    @pytest.mark.asyncio
    async def test_list_entities_with_namespace_filter(
        self, mock_neo4j_client, sample_entity_results
    ):
        """Test entity list with namespace filter for multi-tenant isolation."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"total": 3}],
            sample_entity_results,
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = EntityListRequest(
                namespace_id="research", page=1, page_size=50
            )
            response = await list_entities(request)

            assert all(e.namespace_id == "research" for e in response.entities)

    @pytest.mark.asyncio
    async def test_list_entities_pagination(self, mock_neo4j_client, sample_entity_results):
        """Test pagination: page 2 with page_size=1."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"total": 3}],
            [sample_entity_results[1]],  # Page 2, size 1 = second result
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = EntityListRequest(page=2, page_size=1)
            response = await list_entities(request)

            assert response.page == 2
            assert response.page_size == 1
            assert response.total_pages == 3
            assert len(response.entities) == 1
            assert response.entities[0].entity_id == "relativity_theory"

    @pytest.mark.asyncio
    async def test_list_entities_empty_result(self, mock_neo4j_client):
        """Test entity list when no entities match filters."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"total": 0}],
            [],
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = EntityListRequest(search="nonexistent", page=1, page_size=50)
            response = await list_entities(request)

            assert response.total == 0
            assert len(response.entities) == 0
            assert response.total_pages == 0

    @pytest.mark.asyncio
    async def test_list_entities_combined_filters(self, mock_neo4j_client, sample_entity_results):
        """Test entity list with multiple filters combined."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"total": 1}],
            [sample_entity_results[0]],
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = EntityListRequest(
                search="einstein",
                entity_type="PERSON",
                namespace_id="research",
                page=1,
                page_size=50,
            )
            response = await list_entities(request)

            assert len(response.entities) == 1
            assert response.entities[0].entity_name == "Albert Einstein"

    @pytest.mark.asyncio
    async def test_list_entities_database_error(self, mock_neo4j_client):
        """Test entity list when database query fails."""
        mock_neo4j_client.execute_read.side_effect = Exception(
            "Neo4j connection failed"
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = EntityListRequest(page=1, page_size=50)

            with pytest.raises(HTTPException) as exc_info:
                await list_entities(request)

            assert exc_info.value.status_code == 500
            assert "Failed to search entities" in exc_info.value.detail


# ============================================================================
# Tests: GET /api/v1/admin/graph/entities/{entity_id}
# ============================================================================


class TestGetEntityDetail:
    """Test entity detail endpoint."""

    @pytest.mark.asyncio
    async def test_get_entity_detail_success(self, mock_neo4j_client, sample_entity_results):
        """Test successful entity detail retrieval."""
        # Mock: entity metadata query, then relationships query
        mock_neo4j_client.execute_read.side_effect = [
            [sample_entity_results[0]],  # Entity metadata
            [
                {
                    "source_id": "albert_einstein",
                    "source_name": "Albert Einstein",
                    "target_id": "relativity_theory",
                    "target_name": "Theory of Relativity",
                    "relation_type": "DISCOVERED",
                    "description": "Developed theory",
                    "weight": 0.95,
                },
                {
                    "source_id": "albert_einstein",
                    "source_name": "Albert Einstein",
                    "target_id": "princeton_university",
                    "target_name": "Princeton University",
                    "relation_type": "WORKED_AT",
                    "description": None,
                    "weight": 0.87,
                },
            ],
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            response = await get_entity_detail("albert_einstein")

            assert isinstance(response, EntityDetailResponse)
            assert response.entity.entity_id == "albert_einstein"
            assert response.entity.entity_name == "Albert Einstein"
            assert len(response.relationships) == 2

            # Verify relationship data
            rel_1 = response.relationships[0]
            assert rel_1["relation_type"] == "DISCOVERED"
            assert rel_1["target_name"] == "Theory of Relativity"
            assert rel_1["weight"] == 0.95

    @pytest.mark.asyncio
    async def test_get_entity_detail_not_found(self, mock_neo4j_client):
        """Test entity detail when entity doesn't exist."""
        mock_neo4j_client.execute_read.return_value = []

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_entity_detail("nonexistent_entity")

            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_entity_detail_no_relationships(self, mock_neo4j_client, sample_entity_results):
        """Test entity detail for entity with no relationships."""
        mock_neo4j_client.execute_read.side_effect = [
            [sample_entity_results[2]],  # Entity (has relation_count=7 in data)
            [],  # No relationships
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            response = await get_entity_detail("princeton_university")

            assert response.entity.entity_id == "princeton_university"
            assert len(response.relationships) == 0

    @pytest.mark.asyncio
    async def test_get_entity_detail_null_fields(self, mock_neo4j_client):
        """Test entity detail with null/None fields."""
        entity_result = {
            "entity_id": "test_entity",
            "entity_name": "Test Entity",
            "entity_type": None,
            "description": None,
            "source_id": None,
            "file_path": None,
            "namespace_id": None,
            "created_at": None,
            "relation_count": 0,
        }

        mock_neo4j_client.execute_read.side_effect = [
            [entity_result],
            [],
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            response = await get_entity_detail("test_entity")

            assert response.entity.entity_id == "test_entity"
            assert response.entity.entity_type == "UNKNOWN"
            assert response.entity.description is None
            assert response.entity.created_at is None

    @pytest.mark.asyncio
    async def test_get_entity_detail_database_error(self, mock_neo4j_client):
        """Test entity detail when database query fails."""
        mock_neo4j_client.execute_read.side_effect = Exception(
            "Neo4j query timeout"
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_entity_detail("einstein")

            assert exc_info.value.status_code == 500
            assert "Failed to retrieve entity details" in exc_info.value.detail


# ============================================================================
# Tests: DELETE /api/v1/admin/graph/entities/{entity_id}
# ============================================================================


class TestDeleteEntity:
    """Test entity deletion endpoint (GDPR Article 17 compliance)."""

    @pytest.mark.asyncio
    async def test_delete_entity_success(self, mock_neo4j_client):
        """Test successful entity deletion with cascade."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"entity_id": "albert_einstein"}],  # Entity exists
            [{"rel_count": 42}],  # 42 relationships to be deleted
        ]
        mock_neo4j_client.execute_write.return_value = None

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            response = await delete_entity("albert_einstein")

            assert isinstance(response, DeleteResponse)
            assert response.status == "success"
            assert response.deleted_entity_id == "albert_einstein"
            assert response.affected_relations == 42
            assert response.audit_logged is True

            # Verify write was called
            assert mock_neo4j_client.execute_write.called

    @pytest.mark.asyncio
    async def test_delete_entity_not_found(self, mock_neo4j_client):
        """Test deletion of nonexistent entity."""
        mock_neo4j_client.execute_read.return_value = []

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_entity("nonexistent_entity")

            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_delete_entity_with_namespace_filter(self, mock_neo4j_client):
        """Test entity deletion respects namespace isolation."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"entity_id": "albert_einstein"}],  # Entity exists in namespace
            [{"rel_count": 10}],
        ]
        mock_neo4j_client.execute_write.return_value = None

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            response = await delete_entity(
                "albert_einstein", namespace_id="research"
            )

            assert response.status == "success"
            assert response.affected_relations == 10

            # Verify namespace_id was used in queries
            calls = mock_neo4j_client.execute_read.call_args_list
            assert calls[0][0][1]["namespace_id"] == "research"

    @pytest.mark.asyncio
    async def test_delete_entity_wrong_namespace(self, mock_neo4j_client):
        """Test deletion fails when entity not in specified namespace."""
        mock_neo4j_client.execute_read.return_value = []

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_entity("albert_einstein", namespace_id="wrong_ns")

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_entity_cascade_relations(self, mock_neo4j_client):
        """Test that entity deletion cascades to all relationships."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"entity_id": "albert_einstein"}],
            [{"rel_count": 42}],
        ]
        mock_neo4j_client.execute_write.return_value = None

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            response = await delete_entity("albert_einstein")

            # Verify cascade count is accurate
            assert response.affected_relations == 42
            assert "cascade: 42" in response.message.lower()

    @pytest.mark.asyncio
    async def test_delete_entity_no_relations(self, mock_neo4j_client):
        """Test deletion of entity with no relationships."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"entity_id": "orphan_entity"}],
            [{"rel_count": 0}],
        ]
        mock_neo4j_client.execute_write.return_value = None

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            response = await delete_entity("orphan_entity")

            assert response.status == "success"
            assert response.affected_relations == 0

    @pytest.mark.asyncio
    async def test_delete_entity_database_error(self, mock_neo4j_client):
        """Test deletion when database query fails."""
        mock_neo4j_client.execute_read.side_effect = Exception(
            "Neo4j connection lost"
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_entity("einstein")

            assert exc_info.value.status_code == 500
            assert "Failed to delete entity" in exc_info.value.detail


# ============================================================================
# Tests: POST /api/v1/admin/graph/relations/search
# ============================================================================


class TestListRelations:
    """Test relation listing/search endpoint."""

    @pytest.mark.asyncio
    async def test_list_relations_success(self, mock_neo4j_client, sample_relation_results):
        """Test successful relation list retrieval."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"total": 150}],  # Count
            sample_relation_results,
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = RelationListRequest(page=1, page_size=50)
            response = await list_relations(request)

            assert isinstance(response, RelationListResponse)
            assert response.total == 150
            assert len(response.relations) == 3
            assert response.total_pages == 3

            # Verify first relation
            rel = response.relations[0]
            assert rel.source_entity_id == "albert_einstein"
            assert rel.target_entity_id == "relativity_theory"
            assert rel.relation_type == "DISCOVERED"

    @pytest.mark.asyncio
    async def test_list_relations_with_entity_filter(
        self, mock_neo4j_client, sample_relation_results
    ):
        """Test relation list filtered by entity."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"total": 2}],
            [sample_relation_results[0], sample_relation_results[1]],
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = RelationListRequest(
                entity_id="albert_einstein", page=1, page_size=50
            )
            response = await list_relations(request)

            assert len(response.relations) == 2
            # All relations should involve albert_einstein
            assert all(
                r.source_entity_id == "albert_einstein"
                or r.target_entity_id == "albert_einstein"
                for r in response.relations
            )

    @pytest.mark.asyncio
    async def test_list_relations_with_type_filter(
        self, mock_neo4j_client, sample_relation_results
    ):
        """Test relation list filtered by relation type."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"total": 1}],
            [sample_relation_results[0]],
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = RelationListRequest(
                relation_type="DISCOVERED", page=1, page_size=50
            )
            response = await list_relations(request)

            assert len(response.relations) == 1
            assert response.relations[0].relation_type == "DISCOVERED"

    @pytest.mark.asyncio
    async def test_list_relations_with_namespace_filter(
        self, mock_neo4j_client, sample_relation_results
    ):
        """Test relation list with namespace isolation."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"total": 3}],
            sample_relation_results,
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = RelationListRequest(namespace_id="research", page=1, page_size=50)
            response = await list_relations(request)

            assert all(r.namespace_id == "research" for r in response.relations)

    @pytest.mark.asyncio
    async def test_list_relations_pagination(self, mock_neo4j_client, sample_relation_results):
        """Test pagination for relations."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"total": 3}],
            [sample_relation_results[1]],  # Page 2, size 1
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = RelationListRequest(page=2, page_size=1)
            response = await list_relations(request)

            assert response.page == 2
            assert response.total_pages == 3
            assert len(response.relations) == 1

    @pytest.mark.asyncio
    async def test_list_relations_empty(self, mock_neo4j_client):
        """Test relation list when no relations match filters."""
        mock_neo4j_client.execute_read.side_effect = [
            [{"total": 0}],
            [],
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = RelationListRequest(entity_id="orphan", page=1, page_size=50)
            response = await list_relations(request)

            assert response.total == 0
            assert len(response.relations) == 0

    @pytest.mark.asyncio
    async def test_list_relations_database_error(self, mock_neo4j_client):
        """Test relation list when database query fails."""
        mock_neo4j_client.execute_read.side_effect = Exception(
            "Neo4j server unreachable"
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = RelationListRequest(page=1, page_size=50)

            with pytest.raises(HTTPException) as exc_info:
                await list_relations(request)

            assert exc_info.value.status_code == 500
            assert "Failed to search relations" in exc_info.value.detail


# ============================================================================
# Tests: DELETE /api/v1/admin/graph/relations
# ============================================================================


class TestDeleteRelation:
    """Test relation deletion endpoint."""

    @pytest.mark.asyncio
    async def test_delete_specific_relation_success(self, mock_neo4j_client):
        """Test successful deletion of specific relation type."""
        mock_neo4j_client.execute_read.return_value = [{"rel_count": 1}]
        mock_neo4j_client.execute_write.return_value = None

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = RelationDeleteRequest(
                source_entity_id="albert_einstein",
                target_entity_id="relativity_theory",
                relation_type="DISCOVERED",
            )
            response = await delete_relation(request)

            assert response.status == "success"
            assert response.affected_relations == 1
            assert response.audit_logged is True
            assert "DISCOVERED" in response.message

    @pytest.mark.asyncio
    async def test_delete_all_relations_between_entities(self, mock_neo4j_client):
        """Test deletion of ALL relations between two entities (relation_type=None)."""
        mock_neo4j_client.execute_read.return_value = [{"rel_count": 3}]
        mock_neo4j_client.execute_write.return_value = None

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = RelationDeleteRequest(
                source_entity_id="entity_a",
                target_entity_id="entity_b",
                relation_type=None,
            )
            response = await delete_relation(request)

            assert response.status == "success"
            assert response.affected_relations == 3
            # When relation_type is None, message doesn't specify type (meaning all types)
            assert "between" in response.message.lower()

    @pytest.mark.asyncio
    async def test_delete_relation_not_found_specific_type(self, mock_neo4j_client):
        """Test deletion fails when specific relation type doesn't exist."""
        mock_neo4j_client.execute_read.return_value = [{"rel_count": 0}]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = RelationDeleteRequest(
                source_entity_id="einstein",
                target_entity_id="darwin",
                relation_type="COLLABORATED",
            )

            with pytest.raises(HTTPException) as exc_info:
                await delete_relation(request)

            assert exc_info.value.status_code == 404
            assert "COLLABORATED" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_relation_not_found_any_type(self, mock_neo4j_client):
        """Test deletion fails when no relations exist at all."""
        mock_neo4j_client.execute_read.return_value = [{"rel_count": 0}]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = RelationDeleteRequest(
                source_entity_id="entity_a",
                target_entity_id="entity_b",
                relation_type=None,
            )

            with pytest.raises(HTTPException) as exc_info:
                await delete_relation(request)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_relation_database_error(self, mock_neo4j_client):
        """Test deletion when database query fails."""
        mock_neo4j_client.execute_read.side_effect = Exception(
            "Neo4j lock timeout"
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = RelationDeleteRequest(
                source_entity_id="a",
                target_entity_id="b",
                relation_type="RELATES_TO",
            )

            with pytest.raises(HTTPException) as exc_info:
                await delete_relation(request)

            assert exc_info.value.status_code == 500
            assert "Failed to delete relation" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_relation_multiple_same_type(self, mock_neo4j_client):
        """Test deletion when multiple relations of same type exist (edge case)."""
        mock_neo4j_client.execute_read.return_value = [{"rel_count": 2}]
        mock_neo4j_client.execute_write.return_value = None

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            request = RelationDeleteRequest(
                source_entity_id="entity_a",
                target_entity_id="entity_b",
                relation_type="RELATES_TO",
            )
            response = await delete_relation(request)

            assert response.affected_relations == 2


# ============================================================================
# Tests: Pydantic Model Validation
# ============================================================================


class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_entity_list_request_validation(self):
        """Test EntityListRequest model validation."""
        req = EntityListRequest(
            search="einstein",
            entity_type="PERSON",
            namespace_id="research",
            page=1,
            page_size=50,
        )

        assert req.search == "einstein"
        assert req.entity_type == "PERSON"
        assert req.page == 1
        assert req.page_size == 50

    def test_entity_list_request_defaults(self):
        """Test EntityListRequest default values."""
        req = EntityListRequest()

        assert req.search is None
        assert req.entity_type is None
        assert req.page == 1
        assert req.page_size == 50

    def test_entity_response_validation(self):
        """Test EntityResponse model validation."""
        entity = EntityResponse(
            entity_id="einstein",
            entity_name="Albert Einstein",
            entity_type="PERSON",
            relation_count=42,
        )

        assert entity.entity_id == "einstein"
        assert entity.entity_name == "Albert Einstein"
        assert entity.relation_count == 42

    def test_entity_list_response_validation(self):
        """Test EntityListResponse model validation."""
        entities = [
            EntityResponse(
                entity_id="e1",
                entity_name="Entity 1",
                entity_type="PERSON",
            ),
            EntityResponse(
                entity_id="e2",
                entity_name="Entity 2",
                entity_type="ORGANIZATION",
            ),
        ]

        response = EntityListResponse(
            entities=entities,
            total=100,
            page=1,
            page_size=50,
            total_pages=2,
        )

        assert len(response.entities) == 2
        assert response.total == 100
        assert response.total_pages == 2

    def test_relation_list_request_validation(self):
        """Test RelationListRequest model validation."""
        req = RelationListRequest(
            entity_id="einstein",
            relation_type="DISCOVERED",
            page=1,
            page_size=50,
        )

        assert req.entity_id == "einstein"
        assert req.relation_type == "DISCOVERED"

    def test_relation_response_validation(self):
        """Test RelationResponse model validation."""
        rel = RelationResponse(
            source_entity_id="a",
            source_entity_name="Entity A",
            target_entity_id="b",
            target_entity_name="Entity B",
            relation_type="RELATES_TO",
            weight=0.95,
        )

        assert rel.source_entity_id == "a"
        assert rel.relation_type == "RELATES_TO"
        assert rel.weight == 0.95

    def test_relation_delete_request_validation(self):
        """Test RelationDeleteRequest model validation."""
        req = RelationDeleteRequest(
            source_entity_id="a",
            target_entity_id="b",
            relation_type="RELATES_TO",
        )

        assert req.source_entity_id == "a"
        assert req.relation_type == "RELATES_TO"

    def test_relation_delete_request_no_type(self):
        """Test RelationDeleteRequest with no relation_type."""
        req = RelationDeleteRequest(
            source_entity_id="a",
            target_entity_id="b",
            relation_type=None,
        )

        assert req.relation_type is None

    def test_delete_response_validation(self):
        """Test DeleteResponse model validation."""
        resp = DeleteResponse(
            status="success",
            message="Entity deleted",
            deleted_entity_id="einstein",
            affected_relations=42,
            audit_logged=True,
        )

        assert resp.status == "success"
        assert resp.affected_relations == 42
        assert resp.audit_logged is True
