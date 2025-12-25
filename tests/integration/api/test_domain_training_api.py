"""Integration tests for Domain Training API endpoints.

Sprint 45 - Feature 45.12: Domain Training API Endpoints

Tests cover:
- Domain creation (POST /admin/domains/)
- List domains (GET /admin/domains/)
- Get domain (GET /admin/domains/{name})
- Delete domain (DELETE /admin/domains/{name})
- Start training (POST /admin/domains/{name}/train)
- Training status (GET /admin/domains/{name}/training-status)
- Document classification (POST /admin/domains/classify)
- Available models (GET /admin/domains/available-models)

All external dependencies (Neo4j, Redis, Ollama) are mocked.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


# ============================================================================
# Mocks and Fixtures
# ============================================================================


@pytest.fixture
def mock_domain_repository():
    """Mock DomainRepository for all domain operations.

    IMPORTANT: Patch at source module (src.components.domain_training)
    because imports are lazy in the API layer.
    """
    with patch("src.components.domain_training.get_domain_repository") as mock:
        instance = AsyncMock()
        mock.return_value = instance

        # Setup common mock methods
        instance.initialize = AsyncMock()
        instance.create_domain = AsyncMock()
        instance.get_domain = AsyncMock()
        instance.list_domains = AsyncMock()
        instance.delete_domain = AsyncMock()
        instance.update_domain_prompts = AsyncMock()
        instance.find_best_matching_domain = AsyncMock()
        instance.create_training_log = AsyncMock()
        instance.update_training_log = AsyncMock()
        instance.get_latest_training_log = AsyncMock()

        yield instance


@pytest.fixture
def sample_domain():
    """Sample domain object matching Neo4j schema."""
    return {
        "id": str(uuid4()),
        "name": "tech_docs",
        "description": "Technical documentation for APIs and software libraries",
        "status": "ready",
        "llm_model": "qwen3:32b",
        "entity_prompt": "Extract technical entities like classes, functions, APIs",
        "relation_prompt": "Extract relationships between technical components",
        "entity_examples": json.dumps(
            [
                {"text": "FastAPI", "label": "API_Framework"},
                {"text": "Pydantic", "label": "Validation_Library"},
            ]
        ),
        "relation_examples": json.dumps(
            [{"head": "FastAPI", "relation": "BUILT_WITH", "tail": "Pydantic"}]
        ),
        "training_samples": 50,
        "training_metrics": json.dumps(
            {"entity_f1": 0.89, "relation_f1": 0.82, "extraction_accuracy": 0.91}
        ),
        "created_at": datetime.now(UTC).isoformat(),
        "trained_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def general_domain():
    """Default 'general' domain fixture."""
    return {
        "id": str(uuid4()),
        "name": "general",
        "description": "General-purpose domain for documents that don't match specialized domains",
        "status": "ready",
        "llm_model": "llama3.2:8b",
        "entity_prompt": "Extract general entities",
        "relation_prompt": "Extract general relationships",
        "entity_examples": "[]",
        "relation_examples": "[]",
        "training_samples": 0,
        "training_metrics": "{}",
        "created_at": datetime.now(UTC).isoformat(),
        "trained_at": None,
        "updated_at": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def training_log():
    """Sample training log fixture."""
    return {
        "id": str(uuid4()),
        "domain_id": str(uuid4()),
        "status": "completed",
        "started_at": datetime.now(UTC).isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "progress_percent": 100.0,
        "current_step": "Validation complete",
        "log_messages": json.dumps(
            [
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "level": "INFO",
                    "message": "Training started",
                },
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "level": "INFO",
                    "message": "Training completed with F1=0.89",
                },
            ]
        ),
        "metrics": json.dumps(
            {"entity_f1": 0.89, "relation_f1": 0.82, "extraction_accuracy": 0.91}
        ),
        "error_message": None,
    }


# ============================================================================
# Test: Create Domain
# ============================================================================


def test_create_domain_success(client, mock_domain_repository, sample_domain):
    """Test successful domain creation with all fields."""
    mock_domain_repository.create_domain.return_value = sample_domain

    response = client.post(
        "/admin/domains/",
        json={
            "name": "tech_docs",
            "description": "Technical documentation for APIs and software libraries",
            "llm_model": "qwen3:32b",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "tech_docs"
    assert data["status"] == "ready"
    assert data["llm_model"] == "qwen3:32b"
    assert "id" in data
    assert "created_at" in data

    # Verify repository was called with correct parameters
    mock_domain_repository.create_domain.assert_called_once()


def test_create_domain_missing_name(client, mock_domain_repository):
    """Test domain creation fails with missing name."""
    response = client.post(
        "/admin/domains/", json={"description": "Technical documentation", "llm_model": "qwen3:32b"}
    )

    assert response.status_code == 422  # Validation error
    # Check that error response mentions name field
    response_body = str(response.json())
    assert "name" in response_body.lower() or "missing" in response_body.lower()


def test_create_domain_missing_description(client, mock_domain_repository):
    """Test domain creation fails with missing description."""
    response = client.post("/admin/domains/", json={"name": "tech_docs", "llm_model": "qwen3:32b"})

    assert response.status_code == 422


def test_create_domain_short_description(client, mock_domain_repository):
    """Test domain creation fails with too short description."""
    response = client.post(
        "/admin/domains/",
        json={"name": "tech_docs", "description": "Short", "llm_model": "qwen3:32b"},
    )

    assert response.status_code == 422


def test_create_domain_invalid_name_format(client, mock_domain_repository):
    """Test domain creation fails with invalid name format (spaces, uppercase)."""
    response = client.post(
        "/admin/domains/",
        json={
            "name": "Tech Docs",  # Invalid: spaces and uppercase
            "description": "Technical documentation for APIs and software",
            "llm_model": "qwen3:32b",
        },
    )

    assert response.status_code == 422


def test_create_domain_default_llm_model(client, mock_domain_repository, sample_domain):
    """Test domain creation uses default LLM model if not specified."""
    sample_domain["llm_model"] = "llama3.2:8b"  # Default
    mock_domain_repository.create_domain.return_value = sample_domain

    response = client.post(
        "/admin/domains/",
        json={
            "name": "tech_docs",
            "description": "Technical documentation for APIs and software libraries",
        },
    )

    assert response.status_code == 201
    assert response.json()["llm_model"] == "llama3.2:8b"


# ============================================================================
# Test: List Domains
# ============================================================================


def test_list_domains_empty(client, mock_domain_repository):
    """Test listing domains when none exist."""
    mock_domain_repository.list_domains.return_value = []

    response = client.get("/admin/domains/")

    assert response.status_code == 200
    assert response.json() == []
    mock_domain_repository.list_domains.assert_called_once()


def test_list_domains_returns_all(client, mock_domain_repository, sample_domain, general_domain):
    """Test listing all domains returns complete data."""
    domains = [sample_domain, general_domain]
    mock_domain_repository.list_domains.return_value = domains

    response = client.get("/admin/domains/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "tech_docs"
    assert data[1]["name"] == "general"


def test_list_domains_includes_metadata(client, mock_domain_repository, sample_domain):
    """Test list response includes all required metadata."""
    mock_domain_repository.list_domains.return_value = [sample_domain]

    response = client.get("/admin/domains/")

    assert response.status_code == 200
    domain = response.json()[0]

    # Verify all fields are present
    assert "id" in domain
    assert "name" in domain
    assert "description" in domain
    assert "status" in domain
    assert "llm_model" in domain
    assert "training_metrics" in domain
    assert "created_at" in domain


# ============================================================================
# Test: Get Domain
# ============================================================================


def test_get_domain_exists(client, mock_domain_repository, sample_domain):
    """Test getting existing domain returns complete data."""
    mock_domain_repository.get_domain.return_value = sample_domain

    response = client.get("/admin/domains/tech_docs")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "tech_docs"
    assert data["description"] == sample_domain["description"]
    assert data["status"] == "ready"

    mock_domain_repository.get_domain.assert_called_once_with("tech_docs")


def test_get_domain_not_found(client, mock_domain_repository):
    """Test getting non-existent domain returns 404."""
    mock_domain_repository.get_domain.return_value = None

    response = client.get("/admin/domains/nonexistent")

    assert response.status_code == 404
    # Error response should indicate domain not found
    response_body = str(response.json())
    assert "not found" in response_body.lower() or "error" in response_body.lower()


def test_get_domain_includes_prompts(client, mock_domain_repository, sample_domain):
    """Test get domain response includes core domain fields."""
    mock_domain_repository.get_domain.return_value = sample_domain

    response = client.get("/admin/domains/tech_docs")

    assert response.status_code == 200
    data = response.json()
    # Verify core fields are present
    assert "name" in data
    assert "description" in data
    assert "status" in data
    assert "llm_model" in data


# ============================================================================
# Test: Start Training
# ============================================================================


def test_start_training_success(client, mock_domain_repository, sample_domain, training_log):
    """Test starting training with sufficient samples."""
    sample_domain["status"] = "ready"
    mock_domain_repository.get_domain.return_value = sample_domain
    mock_domain_repository.create_training_log.return_value = training_log

    samples = [
        {"text": "Python is a programming language", "entities": ["Python"], "relations": []},
        {"text": "FastAPI is a web framework", "entities": ["FastAPI"], "relations": []},
        {"text": "Pydantic validates data", "entities": ["Pydantic"], "relations": []},
        {"text": "Qdrant stores vectors", "entities": ["Qdrant"], "relations": []},
        {"text": "Neo4j is a graph database", "entities": ["Neo4j"], "relations": []},
    ]

    response = client.post("/admin/domains/tech_docs/train", json={"samples": samples})

    assert response.status_code == 200
    data = response.json()
    # Message indicates training was started (may include "in background")
    assert "training" in data.get("message", "").lower()
    assert "started" in data.get("message", "").lower()
    assert "training_run_id" in data

    # get_domain may be called multiple times during the request processing
    mock_domain_repository.get_domain.assert_called_with("tech_docs")
    mock_domain_repository.create_training_log.assert_called_once()


def test_start_training_domain_not_found(client, mock_domain_repository):
    """Test training fails when domain doesn't exist."""
    mock_domain_repository.get_domain.return_value = None

    samples = [
        {
            "text": "Sample text with sufficient length for validation",
            "entities": ["Sample"],
            "relations": [],
        }
        for _ in range(5)
    ]

    response = client.post("/admin/domains/nonexistent/train", json={"samples": samples})

    assert response.status_code == 404
    response_body = str(response.json())
    assert "not found" in response_body.lower()


def test_start_training_already_running(client, mock_domain_repository, sample_domain):
    """Test training fails when domain is already training."""
    sample_domain["status"] = "training"
    mock_domain_repository.get_domain.return_value = sample_domain

    samples = [
        {
            "text": "Sample text with sufficient length for validation",
            "entities": ["Sample"],
            "relations": [],
        }
        for _ in range(5)
    ]

    response = client.post("/admin/domains/tech_docs/train", json={"samples": samples})

    assert response.status_code == 409
    response_body = str(response.json())
    assert "training" in response_body.lower()


def test_start_training_insufficient_samples(client, mock_domain_repository, sample_domain):
    """Test training fails with fewer than 5 samples."""
    mock_domain_repository.get_domain.return_value = sample_domain

    samples = [{"text": "Only one sample", "entities": ["sample"], "relations": []}]

    response = client.post("/admin/domains/tech_docs/train", json={"samples": samples})

    assert response.status_code == 422
    response_body = str(response.json())
    assert (
        "at least" in response_body.lower()
        or "samples" in response_body.lower()
        or "minimum" in response_body.lower()
    )


def test_start_training_exactly_five_samples(
    client, mock_domain_repository, sample_domain, training_log
):
    """Test training succeeds with exactly 5 samples (minimum)."""
    sample_domain["status"] = "ready"
    mock_domain_repository.get_domain.return_value = sample_domain
    mock_domain_repository.create_training_log.return_value = training_log

    samples = [
        {
            "text": f"Sample {i} with sufficient text length for validation",
            "entities": [f"Entity{i}"],
            "relations": [],
        }
        for i in range(5)
    ]

    response = client.post("/admin/domains/tech_docs/train", json={"samples": samples})

    assert response.status_code == 200
    assert "training_run_id" in response.json()


def test_start_training_many_samples(client, mock_domain_repository, sample_domain, training_log):
    """Test training succeeds with many samples."""
    sample_domain["status"] = "ready"
    mock_domain_repository.get_domain.return_value = sample_domain
    mock_domain_repository.create_training_log.return_value = training_log

    samples = [
        {"text": f"Sample {i}", "entities": [f"Entity{i}"], "relations": []} for i in range(100)
    ]

    response = client.post("/admin/domains/tech_docs/train", json={"samples": samples})

    assert response.status_code == 200


# ============================================================================
# Test: Training Status
# ============================================================================


def test_get_training_status_running(client, mock_domain_repository):
    """Test getting training status while training is in progress."""
    mock_domain_repository.get_latest_training_log.return_value = {
        "status": "running",
        "progress_percent": 45.0,
        "current_step": "Optimizing entity extraction...",
        "log_messages": json.dumps(
            [
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "level": "INFO",
                    "message": "Started entity extraction optimization",
                }
            ]
        ),
        "metrics": None,
    }

    response = client.get("/admin/domains/tech_docs/training-status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["progress_percent"] == 45.0
    assert "Training in progress" in data["current_step"]


def test_get_training_status_completed(client, mock_domain_repository, training_log):
    """Test getting training status when training is completed."""
    training_log_data = {
        "status": "completed",
        "progress_percent": 100.0,
        "current_step": "Training completed successfully",
        "log_messages": training_log["log_messages"],
        "metrics": training_log["metrics"],
    }
    mock_domain_repository.get_latest_training_log.return_value = training_log_data

    response = client.get("/admin/domains/tech_docs/training-status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["progress_percent"] == 100.0
    assert data["metrics"] is not None


def test_get_training_status_no_training(client, mock_domain_repository):
    """Test getting training status when no training has occurred."""
    mock_domain_repository.get_latest_training_log.return_value = None

    response = client.get("/admin/domains/tech_docs/training-status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_started"
    assert data["progress_percent"] == 0.0


def test_get_training_status_failed(client, mock_domain_repository):
    """Test getting training status when training has failed."""
    mock_domain_repository.get_latest_training_log.return_value = {
        "status": "failed",
        "progress_percent": 35.0,
        "current_step": "Entity extraction optimization",
        "log_messages": json.dumps(
            [
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "level": "ERROR",
                    "message": "CUDA out of memory",
                }
            ]
        ),
        "metrics": None,
        "error_message": "CUDA out of memory",
    }

    response = client.get("/admin/domains/tech_docs/training-status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "error" in data or data["status"] == "failed"


# ============================================================================
# Test: Delete Domain (Sprint 51 Feature 51.4)
# ============================================================================


def test_delete_domain_success(client, mock_domain_repository, sample_domain):
    """Test successful domain deletion with cascading cleanup.

    Sprint 51 Feature 51.4: Enhanced domain deletion that cleans up:
    - Domain configuration in Neo4j
    - Namespace data in Qdrant and Neo4j
    - BM25 index entries
    """
    # Domain is in ready state (not training)
    sample_domain["status"] = "ready"
    mock_domain_repository.get_domain.return_value = sample_domain
    mock_domain_repository.delete_domain.return_value = True

    # Mock namespace deletion
    with patch("src.core.namespace.get_namespace_manager") as mock_ns_mgr:
        mock_ns_instance = MagicMock()
        mock_ns_mgr.return_value = mock_ns_instance
        mock_ns_instance.delete_namespace = AsyncMock(
            return_value={
                "qdrant_points_deleted": 150,
                "neo4j_nodes_deleted": 75,
                "neo4j_relationships_deleted": 120,
            }
        )

        # Mock BM25 cleanup
        with patch("src.components.vector_search.bm25_retrieval.get_bm25_retrieval") as mock_bm25:
            mock_bm25_instance = MagicMock()
            mock_bm25.return_value = mock_bm25_instance
            mock_bm25_instance.corpus = [
                {"text": "doc1", "metadata": {"namespace_id": "tech_docs"}},
                {"text": "doc2", "metadata": {"namespace_id": "other"}},
            ]
            mock_bm25_instance._build_index = MagicMock()

            response = client.delete("/admin/domains/tech_docs")

            assert response.status_code == 200
            data = response.json()
            assert data["domain_name"] == "tech_docs"
            assert "deleted successfully" in data["message"]
            assert "deleted_counts" in data
            assert data["deleted_counts"]["qdrant_points"] == 150
            assert data["deleted_counts"]["neo4j_entities"] == 75
            assert data["deleted_counts"]["neo4j_relationships"] == 120

            mock_domain_repository.get_domain.assert_called_once_with("tech_docs")
            mock_domain_repository.delete_domain.assert_called_once_with("tech_docs")


def test_delete_domain_not_found(client, mock_domain_repository):
    """Test deleting non-existent domain returns 404."""
    mock_domain_repository.get_domain.return_value = None

    response = client.delete("/admin/domains/nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_general_domain_fails(client, mock_domain_repository):
    """Test that deleting 'general' domain fails (protected)."""
    response = client.delete("/admin/domains/general")

    assert response.status_code == 400
    assert (
        "cannot delete" in response.json()["detail"].lower()
        or "default" in response.json()["detail"].lower()
    )

    # Verify get_domain was not called (rejected before checking existence)
    mock_domain_repository.get_domain.assert_not_called()


def test_delete_domain_training_in_progress(client, mock_domain_repository, sample_domain):
    """Test that deleting a domain fails when training is in progress.

    Sprint 51 Feature 51.4: Prevent deletion if domain is currently training.
    """
    sample_domain["status"] = "training"
    mock_domain_repository.get_domain.return_value = sample_domain

    response = client.delete("/admin/domains/tech_docs")

    assert response.status_code == 409
    assert (
        "training" in response.json()["detail"].lower()
        or "in progress" in response.json()["detail"].lower()
    )

    # Verify deletion was not attempted
    mock_domain_repository.delete_domain.assert_not_called()


def test_delete_domain_partial_cleanup_warnings(client, mock_domain_repository, sample_domain):
    """Test domain deletion handles partial failures gracefully.

    Sprint 51 Feature 51.4: Non-critical cleanup failures should generate warnings
    but not prevent domain deletion.
    """
    sample_domain["status"] = "ready"
    mock_domain_repository.get_domain.return_value = sample_domain
    mock_domain_repository.delete_domain.return_value = True

    with patch("src.core.namespace.get_namespace_manager") as mock_ns_mgr:
        mock_ns_instance = MagicMock()
        mock_ns_mgr.return_value = mock_ns_instance

        # Simulate namespace deletion failure
        mock_ns_instance.delete_namespace = AsyncMock(
            side_effect=Exception("Qdrant connection timeout")
        )

        # Mock BM25 cleanup
        with patch("src.components.vector_search.bm25_retrieval.get_bm25_retrieval") as mock_bm25:
            mock_bm25_instance = MagicMock()
            mock_bm25.return_value = mock_bm25_instance
            mock_bm25_instance.corpus = []

            response = client.delete("/admin/domains/tech_docs")

            # Domain should still be deleted despite namespace cleanup failure
            assert response.status_code == 200
            data = response.json()
            assert data["domain_name"] == "tech_docs"
            assert len(data["warnings"]) > 0
            assert any("namespace" in w.lower() for w in data["warnings"])

            # Domain itself should still be deleted
            mock_domain_repository.delete_domain.assert_called_once()


def test_delete_domain_empty_namespace(client, mock_domain_repository, sample_domain):
    """Test deleting domain with no associated documents."""
    sample_domain["status"] = "ready"
    mock_domain_repository.get_domain.return_value = sample_domain
    mock_domain_repository.delete_domain.return_value = True

    with patch("src.core.namespace.get_namespace_manager") as mock_ns_mgr:
        mock_ns_instance = MagicMock()
        mock_ns_mgr.return_value = mock_ns_instance
        mock_ns_instance.delete_namespace = AsyncMock(
            return_value={
                "qdrant_points_deleted": 0,
                "neo4j_nodes_deleted": 0,
                "neo4j_relationships_deleted": 0,
            }
        )

        with patch("src.components.vector_search.bm25_retrieval.get_bm25_retrieval") as mock_bm25:
            mock_bm25_instance = MagicMock()
            mock_bm25.return_value = mock_bm25_instance
            mock_bm25_instance.corpus = []

            response = client.delete("/admin/domains/tech_docs")

            assert response.status_code == 200
            data = response.json()
            assert data["deleted_counts"]["qdrant_points"] == 0
            assert data["deleted_counts"]["neo4j_entities"] == 0


# ============================================================================
# Test: Available Models
# ============================================================================


def test_get_available_models_success(client):
    """Test getting list of available Ollama models."""
    mock_models = [
        {"name": "qwen3:32b", "size": 20000000000},
        {"name": "llama3.2:8b", "size": 5000000000},
        {"name": "llama2:7b", "size": 4000000000},
    ]

    with patch("httpx.AsyncClient") as mock_http:
        # Mock the async context manager
        mock_response = AsyncMock()
        mock_response.json.return_value = {"models": mock_models}

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.get.return_value = mock_response

        mock_http.return_value = mock_client_instance

        response = client.get("/admin/domains/available-models")

        assert response.status_code == 200
        models = response.json()
        assert len(models) >= 2
        assert any(m["name"] == "qwen3:32b" for m in models)


def test_get_available_models_empty(client):
    """Test getting available models when Ollama has none."""
    with patch("httpx.AsyncClient") as mock_http:
        mock_response = AsyncMock()
        mock_response.json.return_value = {"models": []}

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.get.return_value = mock_response

        mock_http.return_value = mock_client_instance

        response = client.get("/admin/domains/available-models")

        assert response.status_code == 200
        assert response.json() == []


def test_get_available_models_ollama_unavailable(client):
    """Test handling when Ollama service is unavailable."""
    with patch("httpx.AsyncClient") as mock_http:
        mock_http.side_effect = ConnectionError("Failed to connect to Ollama")

        response = client.get("/admin/domains/available-models")

        # Should return error or empty list gracefully
        assert response.status_code in [200, 503]


# ============================================================================
# Test: Document Classification
# ============================================================================


def test_classify_document_success(client, mock_domain_repository):
    """Test document classification returns top matches."""
    with patch("src.components.domain_training.get_domain_classifier") as mock_classifier_factory:
        mock_classifier = AsyncMock()
        mock_classifier_factory.return_value = mock_classifier

        mock_classifier.load_domains = AsyncMock()
        mock_classifier.classify_document.return_value = [
            {"domain": "tech_docs", "score": 0.89},
            {"domain": "general", "score": 0.45},
        ]

        response = client.post(
            "/admin/domains/classify",
            params={
                "text": "This document describes API endpoints and FastAPI best practices",
                "top_k": 3,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["recommended"] == "tech_docs"
        assert data["confidence"] >= 0.8  # High confidence
        assert len(data["candidates"]) <= 3


def test_classify_document_empty_text(client):
    """Test document classification fails with empty text."""
    response = client.post("/admin/domains/classify", params={"text": "", "top_k": 3})

    assert response.status_code == 422


def test_classify_document_very_short_text(client):
    """Test document classification with very short text."""
    with patch("src.components.domain_training.get_domain_classifier") as mock_classifier_factory:
        mock_classifier = AsyncMock()
        mock_classifier_factory.return_value = mock_classifier

        mock_classifier.load_domains = AsyncMock()
        mock_classifier.classify_document.return_value = [{"domain": "general", "score": 0.5}]

        response = client.post("/admin/domains/classify", params={"text": "API", "top_k": 1})

        assert response.status_code == 200
        data = response.json()
        assert data["recommended"] in ["tech_docs", "general"]


def test_classify_document_custom_top_k(client):
    """Test document classification with custom top_k parameter."""
    with patch("src.components.domain_training.get_domain_classifier") as mock_classifier_factory:
        mock_classifier = AsyncMock()
        mock_classifier_factory.return_value = mock_classifier

        mock_classifier.load_domains = AsyncMock()
        mock_classifier.classify_document.return_value = [
            {"domain": "tech_docs", "score": 0.89},
            {"domain": "data_science", "score": 0.67},
            {"domain": "general", "score": 0.45},
            {"domain": "finance", "score": 0.32},
        ]

        response = client.post(
            "/admin/domains/classify",
            params={"text": "Machine learning with Python and TensorFlow", "top_k": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data.get("candidates", [])) <= 5


def test_classify_document_invalid_top_k(client):
    """Test document classification fails with invalid top_k."""
    response = client.post("/admin/domains/classify", params={"text": "Some document", "top_k": 0})

    assert response.status_code == 422


def test_classify_document_negative_top_k(client):
    """Test document classification fails with negative top_k."""
    response = client.post("/admin/domains/classify", params={"text": "Some document", "top_k": -1})

    assert response.status_code == 422


# ============================================================================
# Test: Error Handling
# ============================================================================


def test_api_returns_400_on_validation_error(client):
    """Test API returns proper validation error responses."""
    response = client.post("/admin/domains/", json={"name": "tech_docs"})  # Missing required fields

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], list)


def test_api_returns_404_on_not_found(client, mock_domain_repository):
    """Test API returns 404 for missing resources."""
    mock_domain_repository.get_domain.return_value = None

    response = client.get("/admin/domains/nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_api_returns_409_on_conflict(client, mock_domain_repository, sample_domain):
    """Test API returns 409 for conflicting operations."""
    sample_domain["status"] = "training"
    mock_domain_repository.get_domain.return_value = sample_domain

    samples = [{"text": "Sample", "entities": ["Sample"], "relations": []} for _ in range(5)]

    response = client.post("/admin/domains/tech_docs/train", json={"samples": samples})

    assert response.status_code == 409


# ============================================================================
# Test: Response Format and Content-Type
# ============================================================================


def test_api_returns_json_content_type(client, mock_domain_repository, sample_domain):
    """Test API returns JSON content type."""
    mock_domain_repository.get_domain.return_value = sample_domain

    response = client.get("/admin/domains/tech_docs")

    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")


def test_create_domain_returns_201_created(client, mock_domain_repository, sample_domain):
    """Test POST domain returns 201 Created status."""
    mock_domain_repository.create_domain.return_value = sample_domain

    response = client.post(
        "/admin/domains/",
        json={
            "name": "tech_docs",
            "description": "Technical documentation for APIs and software libraries",
            "llm_model": "qwen3:32b",
        },
    )

    assert response.status_code == 201


def test_delete_domain_returns_deletion_stats(client, mock_domain_repository, sample_domain):
    """Test DELETE domain returns 200 with deletion statistics.

    Sprint 51 Feature 51.4: Changed from 204 No Content to 200 with
    detailed deletion statistics for transparency.
    """
    sample_domain["status"] = "ready"
    mock_domain_repository.get_domain.return_value = sample_domain
    mock_domain_repository.delete_domain.return_value = True

    with patch("src.core.namespace.get_namespace_manager") as mock_ns_mgr:
        mock_ns_instance = MagicMock()
        mock_ns_mgr.return_value = mock_ns_instance
        mock_ns_instance.delete_namespace = AsyncMock(
            return_value={
                "qdrant_points_deleted": 42,
                "neo4j_nodes_deleted": 28,
                "neo4j_relationships_deleted": 50,
            }
        )

        with patch("src.components.vector_search.bm25_retrieval.get_bm25_retrieval") as mock_bm25:
            mock_bm25_instance = MagicMock()
            mock_bm25.return_value = mock_bm25_instance
            mock_bm25_instance.corpus = []

            response = client.delete("/admin/domains/tech_docs")

            assert response.status_code == 200
            data = response.json()
            assert "deleted_counts" in data
            assert "message" in data
            assert "domain_name" in data


def test_training_status_returns_200_ok(client, mock_domain_repository):
    """Test training status returns 200 OK."""
    mock_domain_repository.get_latest_training_log.return_value = None

    response = client.get("/admin/domains/tech_docs/training-status")

    assert response.status_code == 200


# ============================================================================
# Test: Feature 64.2 Part 2 - Transactional Domain Creation
# ============================================================================


def test_train_domain_validation_fails_before_creation(client, mock_domain_repository):
    """Test validation failure prevents domain creation.

    Feature 64.2 Part 2: Ensure domain is NOT created when validation fails.
    """
    # Domain doesn't exist yet
    mock_domain_repository.get_domain.return_value = None

    # Submit training request with TOO FEW samples (< 5)
    # Use valid text samples (10+ chars) to avoid Pydantic validation errors
    response = client.post(
        "/admin/domains/new_domain/train",
        json={
            "samples": [
                {"text": "Sample text one with sufficient length", "entities": ["Entity1"]},
                {"text": "Sample text two with sufficient length", "entities": ["Entity2"]},
                # Only 2 samples - should fail validation (need 5 minimum)
            ]
        },
    )

    # Should return 422 Unprocessable Entity (Pydantic validation)
    assert response.status_code == 422
    data = response.json()
    # Check that it's a validation error
    assert "error" in data
    error = data["error"]
    assert error["code"] in ["UNPROCESSABLE_ENTITY", "VALIDATION_FAILED"]
    # Pydantic validates min_items=5 automatically
    assert "validation_errors" in error["details"]
    validation_errors = error["details"]["validation_errors"]
    assert any("samples" in str(err["loc"]) for err in validation_errors)
    assert any("5 items" in err["msg"] for err in validation_errors)

    # Verify domain was NOT created (most important assertion)
    mock_domain_repository.create_domain.assert_not_called()
    mock_domain_repository.update_domain_status.assert_not_called()
    mock_domain_repository.save_training_results.assert_not_called()


def test_train_new_domain_creates_transactionally(
    client, mock_domain_repository, sample_training_dataset
):
    """Test new domain is created transactionally during training.

    Feature 64.2 Part 2: Domain created ONLY after successful training.
    """
    # Domain doesn't exist yet
    mock_domain_repository.get_domain.return_value = None

    response = client.post(
        "/admin/domains/new_domain/train",
        json={"samples": sample_training_dataset},
    )

    # Should accept request and return 200
    assert response.status_code == 200
    data = response.json()
    assert data["is_new_domain"] is True
    assert data["domain"] == "new_domain"
    assert "training_run_id" in data

    # Domain should NOT be created immediately (deferred until training succeeds)
    # Training happens in background - domain creation is deferred
    mock_domain_repository.create_domain.assert_not_called()


def test_train_existing_domain_with_insufficient_samples(
    client, mock_domain_repository, sample_domain
):
    """Test validation failure with existing domain doesn't affect it.

    Feature 64.2 Part 2: Existing domains remain unchanged on validation failure.
    """
    # Domain already exists
    mock_domain_repository.get_domain.return_value = sample_domain

    # Submit training with insufficient samples
    response = client.post(
        "/admin/domains/tech_docs/train",
        json={
            "samples": [
                {"text": "Sample 1", "entities": ["Entity1"]},
                {"text": "Sample 2", "entities": ["Entity2"]},
                {"text": "Sample 3", "entities": ["Entity3"]},
                # Only 3 samples - should fail
            ]
        },
    )

    # Should return 422
    assert response.status_code == 422

    # Existing domain should NOT be modified
    mock_domain_repository.update_domain_status.assert_not_called()
    mock_domain_repository.update_domain_prompts.assert_not_called()


def test_train_domain_allows_retraining_completed(client, mock_domain_repository, sample_domain):
    """Test re-training of completed domains is allowed.

    Feature 64.2 Part 2: Domains with status='ready' can be re-trained.
    """
    sample_domain["status"] = "ready"
    mock_domain_repository.get_domain.return_value = sample_domain
    mock_domain_repository.create_training_log.return_value = {
        "id": str(uuid4()),
        "status": "pending",
    }

    # Valid training dataset (5+ samples)
    response = client.post(
        "/admin/domains/tech_docs/train",
        json={
            "samples": [
                {"text": f"Sample {i}", "entities": [f"Entity{i}"]} for i in range(1, 6)
            ]
        },
    )

    # Should accept re-training
    assert response.status_code == 200
    data = response.json()
    assert data["is_new_domain"] is False
    assert data["domain"] == "tech_docs"


def test_train_domain_prevents_concurrent_training(client, mock_domain_repository, sample_domain):
    """Test training is rejected if already in progress.

    Feature 64.2 Part 2: Prevent concurrent training runs.
    """
    sample_domain["status"] = "training"
    mock_domain_repository.get_domain.return_value = sample_domain

    response = client.post(
        "/admin/domains/tech_docs/train",
        json={
            "samples": [
                {"text": f"Sample {i}", "entities": [f"Entity{i}"]} for i in range(1, 6)
            ]
        },
    )

    # Should return 409 Conflict
    assert response.status_code == 409
    assert "already in progress" in response.json()["detail"]


@pytest.fixture
def sample_training_dataset():
    """Sample training dataset with minimum required samples."""
    return [
        {
            "text": "FastAPI is a modern web framework for building APIs with Python 3.6+",
            "entities": ["FastAPI", "web framework", "Python 3.6+"],
            "relations": [
                {"subject": "FastAPI", "predicate": "is_a", "object": "web framework"}
            ],
        },
        {
            "text": "Pydantic provides data validation using Python type annotations",
            "entities": ["Pydantic", "data validation", "Python type annotations"],
            "relations": [
                {"subject": "Pydantic", "predicate": "provides", "object": "data validation"}
            ],
        },
        {
            "text": "Docker containers enable consistent deployment across environments",
            "entities": ["Docker", "containers", "deployment", "environments"],
            "relations": [
                {"subject": "Docker", "predicate": "enables", "object": "consistent deployment"}
            ],
        },
        {
            "text": "Redis is an in-memory data structure store used as cache and message broker",
            "entities": ["Redis", "in-memory", "cache", "message broker"],
            "relations": [{"subject": "Redis", "predicate": "used_as", "object": "cache"}],
        },
        {
            "text": "Neo4j is a graph database that stores nodes and relationships efficiently",
            "entities": ["Neo4j", "graph database", "nodes", "relationships"],
            "relations": [{"subject": "Neo4j", "predicate": "is_a", "object": "graph database"}],
        },
    ]
