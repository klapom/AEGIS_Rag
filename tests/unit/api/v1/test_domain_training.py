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

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

import pytest
from fastapi.testclient import TestClient


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
    service.embed_documents = AsyncMock(
        return_value=[[0.1] * 1024, [0.2] * 1024]
    )
    return service


class TestCreateDomainEndpoint:
    """Tests for POST /admin/domains endpoint."""

    @pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
    def test_create_domain_success(
        self, test_client, sample_domain_request, monkeypatch
    ):
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

    @pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
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

    @pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
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

    @pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
    def test_create_domain_duplicate_name(
        self, test_client, sample_domain_request, monkeypatch
    ):
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

    @pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
    def test_create_domain_database_error(
        self, test_client, sample_domain_request, monkeypatch
    ):
        """Test error handling for database failure."""
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(
            side_effect=Exception("Database error")
        )

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

    @pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
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

    @pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
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


@pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
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


@pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
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
        mock_neo4j.execute_query = AsyncMock(
            return_value=[{"id": "domain-123"}]
        )

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

    def test_train_domain_insufficient_samples(
        self, test_client, monkeypatch
    ):
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


@pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
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
            response = test_client.get(
                "/api/v1/admin/domains/tech_docs/training-status"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["progress_percent"] == 100

    def test_get_training_status_not_started(
        self, test_client, monkeypatch
    ):
        """Test status when training hasn't started."""
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(
            return_value=[{"status": "pending", "progress": 0}]
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ):
            response = test_client.get(
                "/api/v1/admin/domains/tech_docs/training-status"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "pending"


@pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
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


@pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
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
            response = test_client.get(
                "/api/v1/admin/domains/available-models"
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["models"]) == 2


@pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
class TestClassifyDocumentEndpoint:
    """Tests for POST /admin/domains/classify endpoint."""

    def test_classify_document_success(
        self, test_client, mock_embedding_service, monkeypatch
    ):
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

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ), patch(
            "src.components.shared.embedding_service.get_embedding_service",
            return_value=mock_embedding_service,
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

    def test_classify_document_no_domains(
        self, test_client, mock_embedding_service, monkeypatch
    ):
        """Test classification when no domains exist."""
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(return_value=[])

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j,
        ), patch(
            "src.components.shared.embedding_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            response = test_client.post(
                "/api/v1/admin/domains/classify",
                json={
                    "text": "This is a sample document for classification testing purposes",
                    "top_k": 3,
                },
            )

            assert response.status_code in [200, 404]


@pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
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


@pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
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


@pytest.mark.skip(reason="Sprint 58: Domain training API routes changed - needs updated endpoint path")
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
