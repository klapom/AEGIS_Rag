"""Unit tests for Domain Training API endpoints.

Sprint 45-51: Domain Training and Classification
Tests cover:
- Domain creation and management
- Training status monitoring
- Document classification
- Batch ingestion
- Auto-discovery and augmentation
- Error handling
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def sample_domain_request():
    """Sample domain creation request."""
    return {
        "name": "tech_docs",
        "description": "Technical documentation for software development projects including API docs, guides, and READMEs",
        "llm_model": "qwen3:32b",
    }


@pytest.fixture
def sample_domain_response(sample_domain_request):
    """Sample domain response."""
    return {
        "id": str(uuid.uuid4()),
        "name": sample_domain_request["name"],
        "description": sample_domain_request["description"],
        "status": "pending",
        "llm_model": sample_domain_request["llm_model"],
        "training_metrics": None,
        "created_at": "2025-12-18T10:30:00",
        "trained_at": None,
    }


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client."""
    client = AsyncMock()
    client.execute_query = AsyncMock(return_value=[{"count": 0}])
    return client


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    service = MagicMock()
    service.embed_query = AsyncMock(return_value=[0.1] * 1024)
    service.embed_documents = AsyncMock(return_value=[[0.1] * 1024, [0.2] * 1024])
    return service


class TestCreateDomainEndpoint:
    """Tests for POST /admin/domains endpoint."""

    @pytest.mark.skip(
        reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
    )
    def test_create_domain_success(self, test_client, sample_domain_request, monkeypatch):
        """Test successful domain creation."""
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(
            side_effect=[
                [],  # Check existing
                [{"id": "domain-123"}],  # Create response
            ]
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.post(
                "/api/v1/admin/domains/",
                json=sample_domain_request,
            )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == sample_domain_request["name"]
            assert data["status"] == "pending"
            assert data["llm_model"] == sample_domain_request["llm_model"]

    @pytest.mark.skip(
        reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
    )
    def test_create_domain_invalid_name(self, test_client, monkeypatch):
        """Test validation of domain name."""
        response = test_client.post(
            "/api/v1/admin/domains/",
            json={
                "name": "Invalid Name",  # Invalid: spaces
                "description": "A valid description for testing",
                "llm_model": "qwen3:32b",
            },
        )

        assert response.status_code == 422

    @pytest.mark.skip(
        reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
    )
    def test_create_domain_short_description(self, test_client, monkeypatch):
        """Test validation of description length."""
        response = test_client.post(
            "/api/v1/admin/domains/",
            json={
                "name": "test_domain",
                "description": "Too short",  # < 10 chars
                "llm_model": "qwen3:32b",
            },
        )

        assert response.status_code == 422

    @pytest.mark.skip(
        reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
    )
    def test_create_domain_duplicate_name(self, test_client, sample_domain_request, monkeypatch):
        """Test error when domain name already exists."""
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(
            side_effect=[
                [{"id": "existing-domain"}],  # Domain exists
            ]
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.post(
                "/api/v1/admin/domains/",
                json=sample_domain_request,
            )

            assert response.status_code == 400

    @pytest.mark.skip(
        reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
    )
    def test_create_domain_database_error(self, test_client, sample_domain_request, monkeypatch):
        """Test error handling for database failure."""
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(side_effect=Exception("Database error"))

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.post(
                "/api/v1/admin/domains/",
                json=sample_domain_request,
            )

            assert response.status_code == 500


class TestGetDomainEndpoint:
    """Tests for GET /admin/domains/{name} endpoint."""

    @pytest.mark.skip(
        reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
    )
    def test_get_domain_success(self, test_client, monkeypatch):
        """Test successful domain retrieval."""
        domain_data = {
            "id": "domain-123",
            "name": "tech_docs",
            "description": "Technical documentation",
            "status": "ready",
            "llm_model": "qwen3:32b",
            "created_at": "2025-12-18T10:30:00",
            "trained_at": "2025-12-18T11:00:00",
        }

        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(return_value=[domain_data])

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.get("/api/v1/admin/domains/tech_docs")

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "tech_docs"
            assert data["status"] == "ready"

    @pytest.mark.skip(
        reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
    )
    def test_get_domain_not_found(self, test_client, monkeypatch):
        """Test error when domain not found."""
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(return_value=[])

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.get("/api/v1/admin/domains/nonexistent")

            assert response.status_code == 404


@pytest.mark.skip(
    reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
)
class TestListDomainsEndpoint:
    """Tests for GET /admin/domains endpoint."""

    def test_list_domains_success(self, test_client, monkeypatch):
        """Test successful domain listing."""
        domains = [
            {
                "id": "domain-1",
                "name": "tech_docs",
                "status": "ready",
                "document_count": 10,
            },
            {
                "id": "domain-2",
                "name": "legal_docs",
                "status": "training",
                "document_count": 5,
            },
        ]

        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(return_value=domains)

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.get("/api/v1/admin/domains/")

            assert response.status_code == 200
            data = response.json()
            assert len(data["domains"]) == 2

    def test_list_domains_empty(self, test_client, monkeypatch):
        """Test listing when no domains exist."""
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(return_value=[])

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.get("/api/v1/admin/domains/")

            assert response.status_code == 200
            data = response.json()
            assert len(data["domains"]) == 0


@pytest.mark.skip(
    reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
)
class TestTrainDomainEndpoint:
    """Tests for POST /admin/domains/{name}/train endpoint."""

    def test_train_domain_success(self, test_client, monkeypatch):
        """Test successful domain training."""
        training_data = {
            "samples": [
                {
                    "text": "FastAPI is a modern web framework",
                    "entities": ["FastAPI", "web framework"],
                    "relations": [],
                }
            ]
        }

        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(return_value=[{"id": "domain-123"}])

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.post(
                "/api/v1/admin/domains/tech_docs/train",
                json=training_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert "training_id" in data

    def test_train_domain_insufficient_samples(self, test_client, monkeypatch):
        """Test validation rejects insufficient samples."""
        training_data = {
            "samples": [
                {
                    "text": "Sample text",
                    "entities": ["entity"],
                    "relations": [],
                }
            ]
        }

        response = test_client.post(
            "/api/v1/admin/domains/tech_docs/train",
            json=training_data,
        )

        assert response.status_code == 422

    def test_train_domain_not_found(self, test_client, monkeypatch):
        """Test error when domain not found."""
        training_data = {
            "samples": [
                {
                    "text": "Sample text for training",
                    "entities": ["entity"],
                    "relations": [],
                }
                for _ in range(5)
            ]
        }

        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(return_value=[])

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.post(
                "/api/v1/admin/domains/nonexistent/train",
                json=training_data,
            )

            assert response.status_code == 404


@pytest.mark.skip(
    reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
)
class TestGetTrainingStatusEndpoint:
    """Tests for GET /admin/domains/{name}/training-status endpoint."""

    def test_get_training_status_success(self, test_client, monkeypatch):
        """Test successful training status retrieval."""
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(
            return_value=[
                {
                    "status": "completed",
                    "progress": 100,
                    "metrics": {"f1_score": 0.92},
                }
            ]
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.get("/api/v1/admin/domains/tech_docs/training-status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["progress_percent"] == 100

    def test_get_training_status_not_started(self, test_client, monkeypatch):
        """Test status when training hasn't started."""
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(return_value=[{"status": "pending", "progress": 0}])

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.get("/api/v1/admin/domains/tech_docs/training-status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "pending"


@pytest.mark.skip(
    reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
)
class TestDeleteDomainEndpoint:
    """Tests for DELETE /admin/domains/{name} endpoint."""

    def test_delete_domain_success(self, test_client, monkeypatch):
        """Test successful domain deletion."""
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(
            side_effect=[
                [{"id": "domain-123"}],  # Get domain
                [],  # Delete
            ]
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.delete("/api/v1/admin/domains/tech_docs")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "deleted"

    def test_delete_domain_not_found(self, test_client, monkeypatch):
        """Test error when domain not found."""
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(return_value=[])

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.delete("/api/v1/admin/domains/nonexistent")

            assert response.status_code == 404


@pytest.mark.skip(
    reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
)
class TestGetAvailableModelsEndpoint:
    """Tests for GET /admin/domains/available-models endpoint."""

    def test_get_available_models_success(self, test_client, monkeypatch):
        """Test successful retrieval of available models."""
        models = [
            {"name": "qwen3:32b", "size": 19922944768},
            {"name": "llama3.2:8b", "size": 4844318627},
        ]

        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(return_value=models)

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.get("/api/v1/admin/domains/available-models")

            assert response.status_code == 200
            data = response.json()
            assert len(data["models"]) == 2


@pytest.mark.skip(
    reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
)
class TestClassifyDocumentEndpoint:
    """Tests for POST /admin/domains/classify endpoint."""

    def test_classify_document_success(self, test_client, mock_embedding_service, monkeypatch):
        """Test successful document classification."""
        classification_request = {
            "text": "FastAPI is a modern Python web framework for building APIs",
            "top_k": 3,
        }

        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(
            return_value=[
                {
                    "name": "tech_docs",
                    "description": "Technical documentation",
                    "score": 0.95,
                }
            ]
        )

        with (
            patch(
                "src.components.graph_rag.neo4j_client.get_neo4j_client",
                return_value=mock_neo4j,
            ),
            patch(
                "src.components.shared.embedding_service.get_embedding_service",
                return_value=mock_embedding_service,
            ),
        ):
            response = test_client.post(
                "/api/v1/admin/domains/classify",
                json=classification_request,
            )

            assert response.status_code == 200
            data = response.json()
            assert "recommended" in data
            assert "confidence" in data
            assert len(data["classifications"]) > 0

    def test_classify_document_text_too_short(self, test_client, monkeypatch):
        """Test validation rejects short text."""
        response = test_client.post(
            "/api/v1/admin/domains/classify",
            json={"text": "Too short", "top_k": 3},
        )

        assert response.status_code == 422

    def test_classify_document_no_domains(self, test_client, mock_embedding_service, monkeypatch):
        """Test classification when no domains exist."""
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(return_value=[])

        with (
            patch(
                "src.components.graph_rag.neo4j_client.get_neo4j_client",
                return_value=mock_neo4j,
            ),
            patch(
                "src.components.shared.embedding_service.get_embedding_service",
                return_value=mock_embedding_service,
            ),
        ):
            response = test_client.post(
                "/api/v1/admin/domains/classify",
                json={
                    "text": "This is a sample document for classification testing purposes",
                    "top_k": 3,
                },
            )

            assert response.status_code in [200, 404]


@pytest.mark.skip(
    reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
)
class TestBatchIngestionEndpoint:
    """Tests for POST /admin/domains/ingest-batch endpoint."""

    def test_batch_ingestion_success(self, test_client, monkeypatch):
        """Test successful batch ingestion."""
        batch_request = {
            "items": [
                {
                    "file_path": "/docs/api.md",
                    "text": "API documentation for our service",
                    "domain": "tech_docs",
                },
                {
                    "file_path": "/docs/guide.md",
                    "text": "Getting started guide for developers",
                    "domain": "tech_docs",
                },
            ]
        }

        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(return_value=[{"model": "qwen3:32b", "count": 2}])

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.post(
                "/api/v1/admin/domains/ingest-batch",
                json=batch_request,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_items"] == 2

    def test_batch_ingestion_empty(self, test_client, monkeypatch):
        """Test validation rejects empty batch."""
        response = test_client.post(
            "/api/v1/admin/domains/ingest-batch",
            json={"items": []},
        )

        assert response.status_code == 422


@pytest.mark.skip(
    reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
)
class TestAutoDiscoveryEndpoint:
    """Tests for POST /admin/domains/auto-discover endpoint."""

    def test_auto_discovery_success(self, test_client, monkeypatch):
        """Test successful domain auto-discovery."""
        discovery_request = {
            "sample_texts": [
                "Sample API documentation text",
                "Another API reference guide",
                "REST endpoint specification",
            ]
        }

        with patch("src.api.v1.domain_training.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(
                return_value={
                    "name": "api_docs",
                    "title": "API Documentation",
                    "description": "REST API and technical documentation",
                    "confidence": 0.95,
                    "reasoning": "Documents contain API specifications",
                    "entity_types": ["API", "Endpoint"],
                    "relation_types": ["DOCUMENTS", "REFERENCES"],
                }
            )
            mock_response.raise_for_status = MagicMock()

            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)

            mock_client_cls.return_value = mock_client

            response = test_client.post(
                "/api/v1/admin/domains/auto-discover",
                json=discovery_request,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "api_docs"
            assert data["confidence"] >= 0.9

    def test_auto_discovery_insufficient_samples(self, test_client, monkeypatch):
        """Test validation rejects insufficient samples."""
        response = test_client.post(
            "/api/v1/admin/domains/auto-discover",
            json={"sample_texts": ["Text 1", "Text 2"]},  # Only 2, need 3+
        )

        assert response.status_code == 422


@pytest.mark.skip(
    reason="Sprint 58: Domain training API routes changed - needs updated endpoint path"
)
class TestDataAugmentationEndpoint:
    """Tests for POST /admin/domains/augment endpoint."""

    def test_augmentation_success(self, test_client, monkeypatch):
        """Test successful data augmentation."""
        augmentation_request = {
            "seed_samples": [
                {
                    "text": "FastAPI is a web framework",
                    "entities": ["FastAPI"],
                    "relations": [],
                }
                for _ in range(5)
            ],
            "target_count": 20,
        }

        with patch("src.api.v1.domain_training.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(
                return_value={
                    "generated_samples": [
                        {"text": "Generated sample", "entities": [], "relations": []}
                        for _ in range(15)
                    ],
                    "validation_rate": 0.75,
                }
            )
            mock_response.raise_for_status = MagicMock()

            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)

            mock_client_cls.return_value = mock_client

            response = test_client.post(
                "/api/v1/admin/domains/augment",
                json=augmentation_request,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["generated_samples"]) > 0

    def test_augmentation_insufficient_seeds(self, test_client, monkeypatch):
        """Test validation rejects insufficient seed samples."""
        response = test_client.post(
            "/api/v1/admin/domains/augment",
            json={
                "seed_samples": [{"text": "Sample", "entities": [], "relations": []}],
                "target_count": 20,
            },
        )

        assert response.status_code == 422


# ============================================================================
# Sprint 77 Feature 77.5 (TD-095): Connectivity Evaluation Tests
# ============================================================================


@pytest.mark.skip(
    reason="Sprint 58: Domain training API routes changed - needs /api/v1 prefix update"
)
class TestConnectivityEvaluationEndpoint:
    """Tests for POST /admin/domains/connectivity/evaluate endpoint."""

    def test_evaluate_connectivity_success(self, test_client):
        """Test successful connectivity evaluation within benchmark."""
        request_data = {
            "namespace_id": "hotpotqa_large",
            "domain_type": "factual",
        }

        # Mock Neo4j response (Sprint 76 HotpotQA data)
        mock_result = [
            {
                "total_entities": 146,
                "total_relationships": 65,
                "total_communities": 92,
            }
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client"
        ) as mock_get_neo4j:
            # Setup mock
            mock_neo4j = AsyncMock()
            mock_neo4j.execute_read = AsyncMock(return_value=mock_result)
            mock_get_neo4j.return_value = mock_neo4j

            response = test_client.post(
                "/api/v1/admin/domains/connectivity/evaluate",
                json=request_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["namespace_id"] == "hotpotqa_large"
            assert data["domain_type"] == "factual"
            assert data["total_entities"] == 146
            assert data["total_relationships"] == 65
            assert data["total_communities"] == 92
            assert "relations_per_entity" in data
            assert "entities_per_community" in data
            assert "benchmark_min" in data
            assert "benchmark_max" in data
            assert "within_benchmark" in data
            assert "benchmark_status" in data
            assert "recommendations" in data
            assert len(data["recommendations"]) > 0

    def test_evaluate_connectivity_empty_namespace(self, test_client):
        """Test connectivity evaluation for empty namespace."""
        request_data = {
            "namespace_id": "empty_namespace",
            "domain_type": "factual",
        }

        # Mock Neo4j response (empty namespace)
        mock_result = []

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client"
        ) as mock_get_neo4j:
            # Setup mock
            mock_neo4j = AsyncMock()
            mock_neo4j.execute_read = AsyncMock(return_value=mock_result)
            mock_get_neo4j.return_value = mock_neo4j

            response = test_client.post(
                "/api/v1/admin/domains/connectivity/evaluate",
                json=request_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["namespace_id"] == "empty_namespace"
            assert data["total_entities"] == 0
            assert data["total_relationships"] == 0
            assert data["relations_per_entity"] == 0.0
            assert data["within_benchmark"] is False
            assert data["benchmark_status"] == "below"
            assert any("No entities found" in rec for rec in data["recommendations"])

    def test_evaluate_connectivity_below_benchmark(self, test_client):
        """Test connectivity evaluation below benchmark (sparse graph)."""
        request_data = {
            "namespace_id": "sparse_namespace",
            "domain_type": "factual",
        }

        # Mock Neo4j response (below benchmark: 0.1 relations/entity)
        mock_result = [
            {
                "total_entities": 100,
                "total_relationships": 10,  # 0.1 relations/entity (below 0.3)
                "total_communities": 50,
            }
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client"
        ) as mock_get_neo4j:
            # Setup mock
            mock_neo4j = AsyncMock()
            mock_neo4j.execute_read = AsyncMock(return_value=mock_result)
            mock_get_neo4j.return_value = mock_neo4j

            response = test_client.post(
                "/api/v1/admin/domains/connectivity/evaluate",
                json=request_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["relations_per_entity"] == 0.1
            assert data["within_benchmark"] is False
            assert data["benchmark_status"] == "below"
            assert any("below benchmark" in rec.lower() for rec in data["recommendations"])

    def test_evaluate_connectivity_above_benchmark(self, test_client):
        """Test connectivity evaluation above benchmark (over-extraction)."""
        request_data = {
            "namespace_id": "dense_namespace",
            "domain_type": "factual",
        }

        # Mock Neo4j response (above benchmark: 3.5 relations/entity)
        mock_result = [
            {
                "total_entities": 100,
                "total_relationships": 350,  # 3.5 relations/entity (above 0.8)
                "total_communities": 20,
            }
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client"
        ) as mock_get_neo4j:
            # Setup mock
            mock_neo4j = AsyncMock()
            mock_neo4j.execute_read = AsyncMock(return_value=mock_result)
            mock_get_neo4j.return_value = mock_neo4j

            response = test_client.post(
                "/api/v1/admin/domains/connectivity/evaluate",
                json=request_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["relations_per_entity"] == 3.5
            assert data["within_benchmark"] is False
            assert data["benchmark_status"] == "above"
            assert any("above benchmark" in rec.lower() for rec in data["recommendations"])

    def test_evaluate_connectivity_invalid_domain_type(self, test_client):
        """Test validation rejects invalid domain type."""
        request_data = {
            "namespace_id": "test_namespace",
            "domain_type": "invalid_type",
        }

        response = test_client.post(
            "/api/v1/admin/domains/connectivity/evaluate",
            json=request_data,
        )

        assert response.status_code == 422

    def test_evaluate_connectivity_narrative_domain(self, test_client):
        """Test connectivity evaluation for narrative domain (higher benchmark)."""
        request_data = {
            "namespace_id": "narrative_namespace",
            "domain_type": "narrative",
        }

        # Mock Neo4j response (narrative domain: higher connectivity expected)
        mock_result = [
            {
                "total_entities": 100,
                "total_relationships": 200,  # 2.0 relations/entity (within [1.5, 3.0])
                "total_communities": 15,
            }
        ]

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client"
        ) as mock_get_neo4j:
            # Setup mock
            mock_neo4j = AsyncMock()
            mock_neo4j.execute_read = AsyncMock(return_value=mock_result)
            mock_get_neo4j.return_value = mock_neo4j

            response = test_client.post(
                "/api/v1/admin/domains/connectivity/evaluate",
                json=request_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["domain_type"] == "narrative"
            assert data["relations_per_entity"] == 2.0
            assert data["within_benchmark"] is True
            assert data["benchmark_status"] == "within"
            # Narrative benchmark should be different from factual
            assert data["benchmark_min"] == 1.5
            assert data["benchmark_max"] == 3.0

    def test_evaluate_connectivity_neo4j_error(self, test_client):
        """Test error handling for Neo4j failures."""
        request_data = {
            "namespace_id": "test_namespace",
            "domain_type": "factual",
        }

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client"
        ) as mock_get_neo4j:
            # Setup mock to raise error
            mock_neo4j = AsyncMock()
            mock_neo4j.execute_read = AsyncMock(
                side_effect=Exception("Neo4j connection failed")
            )
            mock_get_neo4j.return_value = mock_neo4j

            response = test_client.post(
                "/api/v1/admin/domains/connectivity/evaluate",
                json=request_data,
            )

            assert response.status_code == 500


class TestEnhancedTrainingStatus:
    """Tests for enhanced GET /admin/domains/{name}/training-status endpoint.

    Sprint 117.6: Step-by-step progress tracking with ETA calculation.
    """

    @pytest.fixture
    def mock_training_log_in_progress(self):
        """Mock training log for in-progress training."""
        return {
            "id": "log-123",
            "started_at": "2026-01-20T15:00:00Z",
            "completed_at": None,
            "status": "running",
            "current_step": "Optimizing entity extraction prompts",
            "progress_percent": 25.0,
            "log_messages": "[]",
            "metrics": '{"entity_f1": 0.82}',
            "error_message": None,
        }

    @pytest.fixture
    def mock_training_log_completed(self):
        """Mock training log for completed training."""
        return {
            "id": "log-456",
            "started_at": "2026-01-20T14:00:00Z",
            "completed_at": "2026-01-20T14:15:00Z",
            "status": "completed",
            "current_step": "Training completed successfully",
            "progress_percent": 100.0,
            "log_messages": "[]",
            "metrics": '{"entity_f1": 0.87, "relation_f1": 0.82}',
            "error_message": None,
        }

    def test_get_training_status_with_steps(
        self, test_client, mock_training_log_in_progress
    ):
        """Test training status includes step-by-step progress."""
        with patch(
            "src.components.domain_training.get_domain_repository"
        ) as mock_get_repo:
            mock_repo = AsyncMock()
            mock_repo.get_latest_training_log = AsyncMock(
                return_value=mock_training_log_in_progress
            )
            mock_get_repo.return_value = mock_repo

            response = test_client.get("/api/v1/admin/domains/medical/training-status")

            assert response.status_code == 200
            data = response.json()

            # Basic fields
            assert data["domain_name"] == "medical"
            assert data["status"] == "training"
            assert data["progress"] == 25
            assert data["current_step"] == "Optimizing entity extraction prompts"

            # Step-by-step progress
            assert "steps" in data
            assert len(data["steps"]) == 7
            steps = data["steps"]

            # Check initialization step (completed, 0-5%)
            init_step = steps[0]
            assert init_step["name"] == "initialization"
            assert init_step["status"] == "completed"
            assert init_step["progress"] == 100

            # Check loading_data step (completed, 5-10%)
            loading_step = steps[1]
            assert loading_step["name"] == "loading_data"
            assert loading_step["status"] == "completed"
            assert loading_step["progress"] == 100

            # Check entity_extraction_optimization step (in_progress, 10-45%)
            # Progress 25% → within 10-45% range → (25-10)/(45-10) = 42.8% step progress
            entity_step = steps[2]
            assert entity_step["name"] == "entity_extraction_optimization"
            assert entity_step["status"] == "in_progress"
            assert 40 <= entity_step["progress"] <= 45  # ~43%

            # Check relation_extraction_optimization step (pending, 45-80%)
            relation_step = steps[3]
            assert relation_step["name"] == "relation_extraction_optimization"
            assert relation_step["status"] == "pending"
            assert relation_step["progress"] == 0

            # Metrics
            assert data["metrics"]["entity_f1"] == 0.82

            # Time fields
            assert data["started_at"] == "2026-01-20T15:00:00Z"
            assert data["elapsed_time_ms"] is not None
            assert data["estimated_completion"] is not None

    def test_get_training_status_completed(
        self, test_client, mock_training_log_completed
    ):
        """Test training status for completed training."""
        with patch(
            "src.components.domain_training.get_domain_repository"
        ) as mock_get_repo:
            mock_repo = AsyncMock()
            mock_repo.get_latest_training_log = AsyncMock(
                return_value=mock_training_log_completed
            )
            mock_get_repo.return_value = mock_repo

            response = test_client.get("/api/v1/admin/domains/medical/training-status")

            assert response.status_code == 200
            data = response.json()

            # Status should be completed
            assert data["status"] == "completed"
            assert data["progress"] == 100

            # All steps should be completed
            assert len(data["steps"]) == 7
            for step in data["steps"]:
                assert step["status"] == "completed"
                assert step["progress"] == 100

            # Metrics should include both entity and relation F1
            assert data["metrics"]["entity_f1"] == 0.87
            assert data["metrics"]["relation_f1"] == 0.82

            # No estimated completion for finished training
            assert data["estimated_completion"] is None

    def test_get_training_status_not_found(self, test_client):
        """Test 404 when no training log exists."""
        with patch(
            "src.components.domain_training.get_domain_repository"
        ) as mock_get_repo:
            mock_repo = AsyncMock()
            mock_repo.get_latest_training_log = AsyncMock(return_value=None)
            mock_get_repo.return_value = mock_repo

            response = test_client.get("/api/v1/admin/domains/nonexistent/training-status")

            assert response.status_code == 404
            assert "No training log found" in response.json()["detail"]

    def test_get_training_status_db_error(self, test_client):
        """Test 500 when database connection fails."""
        from src.core.exceptions import DatabaseConnectionError

        with patch(
            "src.components.domain_training.get_domain_repository"
        ) as mock_get_repo:
            mock_repo = AsyncMock()
            mock_repo.get_latest_training_log = AsyncMock(
                side_effect=DatabaseConnectionError("Neo4j", "Connection failed")
            )
            mock_get_repo.return_value = mock_repo

            response = test_client.get("/api/v1/admin/domains/medical/training-status")

            assert response.status_code == 500
            assert "Database operation failed" in response.json()["detail"]


class TestTrainingLogsEndpoint:
    """Tests for GET /admin/domains/{name}/training-logs endpoint.

    Sprint 117.6: Paginated training logs retrieval.
    """

    @pytest.fixture
    def mock_training_logs_result(self):
        """Mock training logs from repository."""
        return {
            "logs": [
                {
                    "timestamp": "2026-01-20T15:05:00Z",
                    "level": "INFO",
                    "message": "Entity extraction F1: 0.87",
                    "step": "entity_extraction_optimization",
                    "metrics": {"f1": 0.87},
                },
                {
                    "timestamp": "2026-01-20T15:03:00Z",
                    "level": "INFO",
                    "message": "Starting entity extraction optimization",
                    "step": "entity_extraction_optimization",
                    "metrics": None,
                },
                {
                    "timestamp": "2026-01-20T15:00:00Z",
                    "level": "INFO",
                    "message": "Starting DSPy optimization for medical domain",
                    "step": "initialization",
                    "metrics": None,
                },
            ],
            "total_logs": 45,
            "page": 1,
            "page_size": 20,
        }

    def test_get_training_logs_success(self, test_client, mock_training_logs_result):
        """Test successful retrieval of training logs."""
        with patch(
            "src.components.domain_training.get_domain_repository"
        ) as mock_get_repo:
            mock_repo = AsyncMock()
            mock_repo.get_training_log_messages = AsyncMock(
                return_value=mock_training_logs_result
            )
            mock_get_repo.return_value = mock_repo

            response = test_client.get("/api/v1/admin/domains/medical/training-logs")

            assert response.status_code == 200
            data = response.json()

            # Pagination fields
            assert data["domain_name"] == "medical"
            assert data["total_logs"] == 45
            assert data["page"] == 1
            assert data["page_size"] == 20

            # Log entries
            assert len(data["logs"]) == 3
            first_log = data["logs"][0]
            assert first_log["timestamp"] == "2026-01-20T15:05:00Z"
            assert first_log["level"] == "INFO"
            assert first_log["message"] == "Entity extraction F1: 0.87"
            assert first_log["step"] == "entity_extraction_optimization"
            assert first_log["metrics"]["f1"] == 0.87

    def test_get_training_logs_with_pagination(self, test_client):
        """Test pagination parameters."""
        mock_result = {
            "logs": [{"timestamp": "2026-01-20T15:00:00Z", "level": "INFO", "message": "Log 1"}],
            "total_logs": 100,
            "page": 2,
            "page_size": 50,
        }

        with patch(
            "src.components.domain_training.get_domain_repository"
        ) as mock_get_repo:
            mock_repo = AsyncMock()
            mock_repo.get_training_log_messages = AsyncMock(return_value=mock_result)
            mock_get_repo.return_value = mock_repo

            response = test_client.get(
                "/api/v1/admin/domains/medical/training-logs?page=2&page_size=50"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 2
            assert data["page_size"] == 50
            assert data["total_logs"] == 100

            # Verify repository called with correct params
            mock_repo.get_training_log_messages.assert_called_once_with(
                domain_name="medical",
                page=2,
                page_size=50,
            )

    def test_get_training_logs_invalid_page(self, test_client):
        """Test validation of page parameter."""
        response = test_client.get(
            "/api/v1/admin/domains/medical/training-logs?page=0"
        )

        assert response.status_code == 422
        assert "page must be >= 1" in response.json()["detail"]

    def test_get_training_logs_invalid_page_size(self, test_client):
        """Test validation of page_size parameter."""
        response = test_client.get(
            "/api/v1/admin/domains/medical/training-logs?page_size=200"
        )

        assert response.status_code == 422
        assert "page_size must be 1-100" in response.json()["detail"]

    def test_get_training_logs_empty_result(self, test_client):
        """Test response when no logs exist."""
        mock_result = {
            "logs": [],
            "total_logs": 0,
            "page": 1,
            "page_size": 20,
        }

        with patch(
            "src.components.domain_training.get_domain_repository"
        ) as mock_get_repo:
            mock_repo = AsyncMock()
            mock_repo.get_training_log_messages = AsyncMock(return_value=mock_result)
            mock_get_repo.return_value = mock_repo

            response = test_client.get("/api/v1/admin/domains/medical/training-logs")

            assert response.status_code == 200
            data = response.json()
            assert data["logs"] == []
            assert data["total_logs"] == 0

    def test_get_training_logs_db_error(self, test_client):
        """Test 500 when database connection fails."""
        from src.core.exceptions import DatabaseConnectionError

        with patch(
            "src.components.domain_training.get_domain_repository"
        ) as mock_get_repo:
            mock_repo = AsyncMock()
            mock_repo.get_training_log_messages = AsyncMock(
                side_effect=DatabaseConnectionError("Neo4j", "Connection failed")
            )
            mock_get_repo.return_value = mock_repo

            response = test_client.get("/api/v1/admin/domains/medical/training-logs")

            assert response.status_code == 500
            assert "Database operation failed" in response.json()["detail"]
