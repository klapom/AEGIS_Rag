"""Integration tests for domain batch ingestion endpoints.

Sprint 117.5: Batch Document Ingestion Integration Tests

Tests cover:
- POST /admin/domains/{name}/ingest-batch
- GET /admin/domains/{name}/ingest-batch/{batch_id}/status
- End-to-end batch processing workflow
- Error handling and validation
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
class TestDomainBatchIngestionEndpoint:
    """Integration tests for batch ingestion endpoint."""

    async def test_ingest_batch_success(self, async_client: AsyncClient):
        """Test successful batch ingestion initiation."""
        # Mock domain repository
        mock_domain = {
            "name": "tech_docs",
            "entity_prompt": "Extract entities",
            "relation_prompt": "Extract relations",
            "llm_model": "qwen3:32b",
        }

        mock_repo = AsyncMock()
        mock_repo.get_domain = AsyncMock(return_value=mock_domain)

        with patch(
            "src.api.v1.domain_training.get_domain_repository",
            return_value=mock_repo,
        ):
            # Mock batch service to prevent actual processing
            from src.components.domain_training import BatchIngestionService, reset_batch_ingestion_service

            reset_batch_ingestion_service()
            service = BatchIngestionService()

            async def mock_start_batch(*args, **kwargs):
                batch_id = "batch_test123"
                service._batches[batch_id] = type(
                    "BatchProgress",
                    (),
                    {
                        "to_dict": lambda: {
                            "batch_id": batch_id,
                            "domain_name": "tech_docs",
                            "total_documents": 2,
                            "status": "processing",
                            "progress": {"completed": 0, "failed": 0, "pending": 2},
                            "results": [],
                            "errors": [],
                        }
                    },
                )()
                return batch_id

            with patch.object(service, "start_batch", side_effect=mock_start_batch):
                with patch.object(service, "get_batch_status") as mock_status:
                    mock_status.return_value = {
                        "batch_id": "batch_test123",
                        "domain_name": "tech_docs",
                        "total_documents": 2,
                        "status": "processing",
                        "progress": {"completed": 0, "failed": 0, "pending": 2},
                        "results": [],
                        "errors": [],
                    }

                    with patch(
                        "src.api.v1.domain_training.get_batch_ingestion_service",
                        return_value=service,
                    ):
                        response = await async_client.post(
                            "/api/v1/admin/domains/tech_docs/ingest-batch",
                            json={
                                "documents": [
                                    {
                                        "document_id": "doc_001",
                                        "content": "FastAPI is a modern web framework.",
                                        "metadata": {"source": "test.pdf"},
                                    },
                                    {
                                        "document_id": "doc_002",
                                        "content": "Django is a high-level framework.",
                                        "metadata": {"source": "test2.pdf"},
                                    },
                                ],
                                "options": {
                                    "extract_entities": True,
                                    "extract_relations": True,
                                    "parallel_workers": 2,
                                },
                            },
                        )

        # Verify response
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "batch_id" in data
        assert data["domain_name"] == "tech_docs"
        assert data["total_documents"] == 2
        assert data["status"] == "processing"
        assert "progress" in data

    async def test_ingest_batch_domain_not_found(self, async_client: AsyncClient):
        """Test batch ingestion fails when domain doesn't exist."""
        mock_repo = AsyncMock()
        mock_repo.get_domain = AsyncMock(return_value=None)

        with patch(
            "src.api.v1.domain_training.get_domain_repository",
            return_value=mock_repo,
        ):
            response = await async_client.post(
                "/api/v1/admin/domains/nonexistent/ingest-batch",
                json={
                    "documents": [
                        {
                            "document_id": "doc_001",
                            "content": "Test content",
                            "metadata": {},
                        }
                    ],
                    "options": {},
                },
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not found" in response.json()["detail"].lower()

    async def test_ingest_batch_too_many_documents(self, async_client: AsyncClient):
        """Test batch ingestion validates document count."""
        # Create 101 documents (exceeds limit)
        documents = [
            {
                "document_id": f"doc_{i:03d}",
                "content": "Test content",
                "metadata": {},
            }
            for i in range(101)
        ]

        mock_domain = {"name": "tech_docs"}
        mock_repo = AsyncMock()
        mock_repo.get_domain = AsyncMock(return_value=mock_domain)

        with patch(
            "src.api.v1.domain_training.get_domain_repository",
            return_value=mock_repo,
        ):
            response = await async_client.post(
                "/api/v1/admin/domains/tech_docs/ingest-batch",
                json={
                    "documents": documents,
                    "options": {},
                },
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "100 documents" in response.json()["detail"]

    async def test_ingest_batch_invalid_document_id(self, async_client: AsyncClient):
        """Test batch ingestion validates document IDs."""
        response = await async_client.post(
            "/api/v1/admin/domains/tech_docs/ingest-batch",
            json={
                "documents": [
                    {
                        "document_id": "",  # Empty document ID
                        "content": "Test content",
                        "metadata": {},
                    }
                ],
                "options": {},
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_ingest_batch_missing_content(self, async_client: AsyncClient):
        """Test batch ingestion validates content."""
        response = await async_client.post(
            "/api/v1/admin/domains/tech_docs/ingest-batch",
            json={
                "documents": [
                    {
                        "document_id": "doc_001",
                        "content": "short",  # Too short
                        "metadata": {},
                    }
                ],
                "options": {},
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
class TestBatchStatusEndpoint:
    """Integration tests for batch status endpoint."""

    async def test_get_batch_status_success(self, async_client: AsyncClient):
        """Test successful batch status retrieval."""
        from src.components.domain_training import BatchIngestionService, reset_batch_ingestion_service

        reset_batch_ingestion_service()
        service = BatchIngestionService()

        # Create mock batch
        batch_id = "batch_test123"
        service._batches[batch_id] = type(
            "BatchProgress",
            (),
            {
                "to_dict": lambda: {
                    "batch_id": batch_id,
                    "domain_name": "tech_docs",
                    "total_documents": 5,
                    "status": "processing",
                    "progress": {"completed": 2, "failed": 1, "pending": 2},
                    "results": [
                        {
                            "document_id": "doc_001",
                            "status": "completed",
                            "entities_extracted": 10,
                            "relations_extracted": 5,
                            "chunks_created": 3,
                            "processing_time_ms": 1500,
                        },
                        {
                            "document_id": "doc_002",
                            "status": "completed",
                            "entities_extracted": 8,
                            "relations_extracted": 4,
                            "chunks_created": 2,
                            "processing_time_ms": 1200,
                        },
                    ],
                    "errors": [
                        {
                            "document_id": "doc_003",
                            "error": "Extraction failed",
                            "error_code": "EXTRACTION_FAILED",
                        }
                    ],
                }
            },
        )()

        with patch.object(service, "get_batch_status") as mock_status:
            mock_status.return_value = {
                "batch_id": batch_id,
                "domain_name": "tech_docs",
                "total_documents": 5,
                "status": "processing",
                "progress": {"completed": 2, "failed": 1, "pending": 2},
                "results": [
                    {
                        "document_id": "doc_001",
                        "status": "completed",
                        "entities_extracted": 10,
                        "relations_extracted": 5,
                        "chunks_created": 3,
                        "processing_time_ms": 1500,
                    },
                    {
                        "document_id": "doc_002",
                        "status": "completed",
                        "entities_extracted": 8,
                        "relations_extracted": 4,
                        "chunks_created": 2,
                        "processing_time_ms": 1200,
                    },
                ],
                "errors": [
                    {
                        "document_id": "doc_003",
                        "error": "Extraction failed",
                        "error_code": "EXTRACTION_FAILED",
                    }
                ],
            }

            with patch(
                "src.api.v1.domain_training.get_batch_ingestion_service",
                return_value=service,
            ):
                response = await async_client.get(
                    f"/api/v1/admin/domains/tech_docs/ingest-batch/{batch_id}/status"
                )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["batch_id"] == batch_id
        assert data["domain_name"] == "tech_docs"
        assert data["total_documents"] == 5
        assert data["status"] == "processing"
        assert data["progress"]["completed"] == 2
        assert data["progress"]["failed"] == 1
        assert data["progress"]["pending"] == 2
        assert len(data["results"]) == 2
        assert len(data["errors"]) == 1

    async def test_get_batch_status_not_found(self, async_client: AsyncClient):
        """Test batch status returns 404 for unknown batch."""
        from src.components.domain_training import BatchIngestionService, reset_batch_ingestion_service

        reset_batch_ingestion_service()
        service = BatchIngestionService()

        with patch.object(service, "get_batch_status", return_value=None):
            with patch(
                "src.api.v1.domain_training.get_batch_ingestion_service",
                return_value=service,
            ):
                response = await async_client.get(
                    "/api/v1/admin/domains/tech_docs/ingest-batch/nonexistent_batch/status"
                )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    async def test_get_batch_status_domain_mismatch(self, async_client: AsyncClient):
        """Test batch status validates domain name."""
        from src.components.domain_training import BatchIngestionService, reset_batch_ingestion_service

        reset_batch_ingestion_service()
        service = BatchIngestionService()

        with patch.object(service, "get_batch_status") as mock_status:
            mock_status.return_value = {
                "batch_id": "batch_123",
                "domain_name": "other_domain",  # Different domain
                "total_documents": 1,
                "status": "processing",
                "progress": {"completed": 0, "failed": 0, "pending": 1},
                "results": [],
                "errors": [],
            }

            with patch(
                "src.api.v1.domain_training.get_batch_ingestion_service",
                return_value=service,
            ):
                response = await async_client.get(
                    "/api/v1/admin/domains/tech_docs/ingest-batch/batch_123/status"
                )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "domain" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestBatchIngestionWorkflow:
    """End-to-end workflow tests."""

    async def test_complete_batch_workflow(self, async_client: AsyncClient):
        """Test complete batch ingestion workflow from start to completion."""
        # 1. Create domain
        mock_domain = {
            "name": "test_domain",
            "entity_prompt": "Extract entities",
            "relation_prompt": "Extract relations",
        }

        mock_repo = AsyncMock()
        mock_repo.get_domain = AsyncMock(return_value=mock_domain)

        with patch(
            "src.api.v1.domain_training.get_domain_repository",
            return_value=mock_repo,
        ):
            from src.components.domain_training import BatchIngestionService, reset_batch_ingestion_service

            reset_batch_ingestion_service()
            service = BatchIngestionService()

            # Mock service to simulate processing
            batch_id = "batch_workflow"

            async def mock_start(*args, **kwargs):
                service._batches[batch_id] = type(
                    "BatchProgress",
                    (),
                    {
                        "to_dict": lambda: {
                            "batch_id": batch_id,
                            "domain_name": "test_domain",
                            "total_documents": 2,
                            "status": "processing",
                            "progress": {"completed": 0, "failed": 0, "pending": 2},
                            "results": [],
                            "errors": [],
                        }
                    },
                )()
                return batch_id

            with patch.object(service, "start_batch", side_effect=mock_start):
                with patch.object(service, "get_batch_status") as mock_status:
                    # Initial status
                    mock_status.return_value = {
                        "batch_id": batch_id,
                        "domain_name": "test_domain",
                        "total_documents": 2,
                        "status": "processing",
                        "progress": {"completed": 0, "failed": 0, "pending": 2},
                        "results": [],
                        "errors": [],
                    }

                    with patch(
                        "src.api.v1.domain_training.get_batch_ingestion_service",
                        return_value=service,
                    ):
                        # 2. Start batch ingestion
                        response = await async_client.post(
                            "/api/v1/admin/domains/test_domain/ingest-batch",
                            json={
                                "documents": [
                                    {
                                        "document_id": "doc_001",
                                        "content": "Test document 1",
                                        "metadata": {},
                                    },
                                    {
                                        "document_id": "doc_002",
                                        "content": "Test document 2",
                                        "metadata": {},
                                    },
                                ],
                                "options": {"parallel_workers": 2},
                            },
                        )

                        assert response.status_code == status.HTTP_202_ACCEPTED
                        data = response.json()
                        returned_batch_id = data["batch_id"]

                        # 3. Poll for status (simulate completion)
                        mock_status.return_value = {
                            "batch_id": returned_batch_id,
                            "domain_name": "test_domain",
                            "total_documents": 2,
                            "status": "completed",
                            "progress": {"completed": 2, "failed": 0, "pending": 0},
                            "results": [
                                {
                                    "document_id": "doc_001",
                                    "status": "completed",
                                    "entities_extracted": 5,
                                    "relations_extracted": 3,
                                    "chunks_created": 2,
                                    "processing_time_ms": 1000,
                                },
                                {
                                    "document_id": "doc_002",
                                    "status": "completed",
                                    "entities_extracted": 7,
                                    "relations_extracted": 4,
                                    "chunks_created": 3,
                                    "processing_time_ms": 1200,
                                },
                            ],
                            "errors": [],
                        }

                        response = await async_client.get(
                            f"/api/v1/admin/domains/test_domain/ingest-batch/{returned_batch_id}/status"
                        )

                        assert response.status_code == status.HTTP_200_OK
                        data = response.json()
                        assert data["status"] == "completed"
                        assert data["progress"]["completed"] == 2
                        assert data["progress"]["failed"] == 0
                        assert len(data["results"]) == 2
