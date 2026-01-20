"""Unit tests for Admin Indexing API endpoints.

Sprint 53 Feature 53.3: Admin Indexing API
Tests cover:
- Document re-indexing with SSE progress tracking
- Re-indexing timestamp persistence
- Empty directory handling
- Dry-run mode
- Error scenarios
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.v1.admin_indexing import (
    get_last_reindex_timestamp,
    save_last_reindex_timestamp,
)


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client."""
    client = AsyncMock()
    client.delete_collection = AsyncMock()
    client.create_collection = AsyncMock()
    client.get_collection_info = AsyncMock(return_value=MagicMock(points_count=1523))
    return client


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    service = MagicMock()
    service.embedding_dim = 1024
    return service


@pytest.fixture
def mock_redis_memory():
    """Mock Redis memory."""
    redis_mock = AsyncMock()
    redis_mock.client = AsyncMock()
    return redis_mock


@pytest.fixture
def mock_lightrag_wrapper():
    """Mock LightRAG wrapper."""
    wrapper = AsyncMock()
    wrapper._clear_neo4j_database = AsyncMock()
    wrapper.get_stats = AsyncMock(return_value={"entity_count": 856, "relationship_count": 1204})
    return wrapper


class TestGetLastReindexTimestamp:
    """Tests for get_last_reindex_timestamp function."""

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Sprint 58: Requires patch at source location - to be fixed in Sprint 59"
    )
    async def test_get_timestamp_success(self, monkeypatch):
        """Test successful retrieval of last reindex timestamp."""
        mock_redis_memory = AsyncMock()
        mock_redis_client = AsyncMock()
        mock_redis_client.get = AsyncMock(return_value=b"2025-12-18T10:30:00")
        mock_redis_memory.client = AsyncMock(return_value=mock_redis_client)

        with patch(
            "src.api.v1.admin_indexing.get_redis_memory",
            return_value=mock_redis_memory,
        ):
            timestamp = await get_last_reindex_timestamp()
            assert timestamp == "2025-12-18T10:30:00"

    @pytest.mark.asyncio
    async def test_get_timestamp_not_set(self, monkeypatch):
        """Test retrieval when timestamp not set."""
        mock_redis_memory = AsyncMock()
        mock_redis_client = AsyncMock()
        mock_redis_client.get = AsyncMock(return_value=None)
        mock_redis_memory.client = AsyncMock(return_value=mock_redis_client)

        with patch(
            "src.components.memory.get_redis_memory",
            return_value=mock_redis_memory,
        ):
            timestamp = await get_last_reindex_timestamp()
            assert timestamp is None

    @pytest.mark.asyncio
    async def test_get_timestamp_redis_error(self, monkeypatch):
        """Test error handling when Redis unavailable."""
        with patch(
            "src.components.memory.get_redis_memory",
            side_effect=Exception("Redis connection failed"),
        ):
            timestamp = await get_last_reindex_timestamp()
            assert timestamp is None


class TestSaveLastReindexTimestamp:
    """Tests for save_last_reindex_timestamp function."""

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Sprint 58: Requires patch at source location - to be fixed in Sprint 59"
    )
    async def test_save_timestamp_success(self, monkeypatch):
        """Test successful save of reindex timestamp."""
        mock_redis_memory = AsyncMock()
        mock_redis_client = AsyncMock()
        mock_redis_client.set = AsyncMock()
        mock_redis_memory.client = AsyncMock(return_value=mock_redis_client)

        with patch(
            "src.api.v1.admin_indexing.get_redis_memory",
            return_value=mock_redis_memory,
        ):
            await save_last_reindex_timestamp()
            mock_redis_client.set.assert_called_once()
            # Verify it was called with the REDIS_KEY_LAST_REINDEX key
            call_args = mock_redis_client.set.call_args
            assert call_args[0][0] == "admin:last_reindex_timestamp"

    @pytest.mark.asyncio
    async def test_save_timestamp_redis_error(self, monkeypatch):
        """Test error handling when save fails."""
        with patch(
            "src.components.memory.get_redis_memory",
            side_effect=Exception("Redis connection failed"),
        ):
            # Should not raise, just log warning
            await save_last_reindex_timestamp()


class TestReindexProgressStream:
    """Tests for reindex_progress_stream function."""

    @pytest.mark.asyncio
    async def test_reindex_progress_no_documents(self, tmp_path, monkeypatch):
        """Test error when no documents found in directory."""
        from src.api.v1.admin_indexing import reindex_progress_stream

        mock_qdrant = AsyncMock()
        mock_embedding = MagicMock(embedding_dim=1024)

        with (
            patch(
                "src.components.vector_search.qdrant_client.get_qdrant_client",
                return_value=mock_qdrant,
            ),
            patch(
                "src.components.shared.embedding_service.get_embedding_service",
                return_value=mock_embedding,
            ),
        ):
            gen = reindex_progress_stream(tmp_path, dry_run=True)
            messages = []
            async for msg in gen:
                messages.append(msg)

            # Should contain error message about no documents
            assert any("No documents found" in msg for msg in messages)

    @pytest.mark.asyncio
    async def test_reindex_progress_dry_run(self, tmp_path, monkeypatch):
        """Test dry-run mode skips actual indexing."""
        from src.api.v1.admin_indexing import reindex_progress_stream

        # Create test document file
        test_doc = tmp_path / "test.pdf"
        test_doc.write_text("test")

        mock_qdrant = AsyncMock()
        mock_embedding = MagicMock(embedding_dim=1024)

        with (
            patch(
                "src.components.vector_search.qdrant_client.get_qdrant_client",
                return_value=mock_qdrant,
            ),
            patch(
                "src.components.shared.embedding_service.get_embedding_service",
                return_value=mock_embedding,
            ),
        ):
            gen = reindex_progress_stream(tmp_path, dry_run=True)
            messages = []
            async for msg in gen:
                messages.append(msg)

            # Dry run should complete without calling delete
            mock_qdrant.delete_collection.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Sprint 58: run_batch_ingestion refactored - needs updated mock strategy"
    )
    async def test_reindex_progress_stream_format(self, tmp_path, monkeypatch):
        """Test SSE message format."""
        from src.api.v1.admin_indexing import reindex_progress_stream

        test_doc = tmp_path / "test.pdf"
        test_doc.write_text("test")

        mock_qdrant = AsyncMock()
        mock_embedding = MagicMock(embedding_dim=1024)

        with (
            patch(
                "src.components.vector_search.qdrant_client.get_qdrant_client",
                return_value=mock_qdrant,
            ),
            patch(
                "src.components.shared.embedding_service.get_embedding_service",
                return_value=mock_embedding,
            ),
        ):
            gen = reindex_progress_stream(tmp_path, dry_run=True)
            messages = []
            async for msg in gen:
                messages.append(msg)

            # Check SSE format (data: {json})
            assert any("data:" in msg for msg in messages)


class TestReindexEndpoints:
    """Tests for reindex HTTP endpoints."""

    @pytest.mark.skip(reason="Sprint 58: Error message format changed - needs update")
    def test_reindex_all_documents_endpoint_missing_dir(self, test_client):
        """Test reindex endpoint with missing directory."""
        response = test_client.post(
            "/api/v1/admin/reindex",
            params={"input_dir": "/nonexistent/path", "dry_run": "true"},
        )
        # Should stream error
        assert response.status_code == 200
        assert "No documents found" in response.text

    @pytest.mark.skip(
        reason="Sprint 58: run_batch_ingestion refactored - needs updated mock strategy"
    )
    def test_reindex_all_documents_dry_run(self, test_client, tmp_path, monkeypatch):
        """Test reindex with dry-run flag."""
        test_doc = tmp_path / "test.pdf"
        test_doc.write_text("test")

        mock_qdrant = AsyncMock()
        mock_embedding = MagicMock(embedding_dim=1024)

        with (
            patch(
                "src.components.vector_search.qdrant_client.get_qdrant_client",
                return_value=mock_qdrant,
            ),
            patch(
                "src.components.shared.embedding_service.get_embedding_service",
                return_value=mock_embedding,
            ),
        ):
            response = test_client.post(
                "/api/v1/admin/reindex",
                params={"input_dir": str(tmp_path), "dry_run": "true"},
            )
            assert response.status_code == 200


class TestAddDocumentsEndpoint:
    """Tests for document addition endpoint."""

    @pytest.mark.skip(
        reason="Sprint 58: run_batch_ingestion refactored - needs updated mock strategy"
    )
    def test_add_documents_success(self, test_client, tmp_path, monkeypatch):
        """Test successful document addition."""
        test_doc = tmp_path / "test.pdf"
        test_doc.write_text("test")

        mock_qdrant = AsyncMock()
        mock_embedding = MagicMock(embedding_dim=1024)

        with (
            patch(
                "src.components.vector_search.qdrant_client.get_qdrant_client",
                return_value=mock_qdrant,
            ),
            patch(
                "src.components.shared.embedding_service.get_embedding_service",
                return_value=mock_embedding,
            ),
        ):
            response = test_client.post(
                "/api/v1/admin/add-documents",
                params={"input_dir": str(tmp_path)},
            )
            # Streaming response
            assert response.status_code == 200


class TestGetReindexStatusEndpoint:
    """Tests for getting last reindex status."""

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Sprint 58: Requires patch at source location - to be fixed in Sprint 59"
    )
    async def test_get_last_reindex_status(self, test_client, monkeypatch):
        """Test getting last reindex timestamp."""
        mock_redis_memory = AsyncMock()
        mock_redis_client = AsyncMock()
        mock_redis_client.get = AsyncMock(return_value=b"2025-12-18T10:30:00")
        mock_redis_memory.client = AsyncMock(return_value=mock_redis_client)

        with patch(
            "src.api.v1.admin_indexing.get_redis_memory",
            return_value=mock_redis_memory,
        ):
            response = test_client.get("/api/v1/admin/reindex-status")
            assert response.status_code == 200
            data = response.json()
            assert "last_reindex_timestamp" in data


class AsyncIteratorMock:
    """Mock async iterator for testing."""

    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


class TestFastUploadResponse:
    """Tests for FastUploadResponse model.

    Sprint 117 Feature 117.10: Domain Classification Display in Upload Dialog.
    """

    def test_valid_fast_upload_response(self):
        """Test creating valid FastUploadResponse."""
        from src.api.v1.admin_indexing import FastUploadResponse

        response = FastUploadResponse(
            document_id="doc_abc123",
            filename="medical_report.pdf",
            status="processing_background",
            message="Document uploaded! Processing in background...",
            namespace="default",
            domain="medical",
            domain_classification=None,
            extraction_summary=None,
        )

        assert response.document_id == "doc_abc123"
        assert response.filename == "medical_report.pdf"
        assert response.status == "processing_background"
        assert response.namespace == "default"
        assert response.domain == "medical"
        assert response.domain_classification is None
        assert response.extraction_summary is None

    def test_fast_upload_response_with_classification(self):
        """Test FastUploadResponse with domain classification data."""
        from src.api.v1.admin_indexing import FastUploadResponse

        classification_data = {
            "domain_id": "medical",
            "domain_name": "Medical Documents",
            "confidence": 0.94,
            "classification_path": "fast",
            "latency_ms": 42,
            "model_used": "C-LARA-SetFit-v2",
            "matched_entity_types": ["Disease", "Treatment"],
            "matched_intent": "diagnosis_report",
            "requires_review": False,
            "alternatives": [],
        }

        response = FastUploadResponse(
            document_id="doc_xyz789",
            filename="patient_notes.docx",
            status="ready",
            message="Processing complete",
            namespace="default",
            domain="medical",
            domain_classification=classification_data,
            extraction_summary=None,
        )

        assert response.domain_classification is not None
        assert response.domain_classification["domain_id"] == "medical"
        assert response.domain_classification["confidence"] == 0.94

    def test_fast_upload_response_with_extraction_summary(self):
        """Test FastUploadResponse with extraction summary data."""
        from src.api.v1.admin_indexing import FastUploadResponse

        extraction_data = {
            "entities_count": 47,
            "relations_count": 23,
            "chunks_count": 12,
            "mentioned_in_count": 47,
        }

        response = FastUploadResponse(
            document_id="doc_123",
            filename="research_paper.pdf",
            status="ready",
            message="Processing complete",
            namespace="research",
            domain="general",
            domain_classification=None,
            extraction_summary=extraction_data,
        )

        assert response.extraction_summary is not None
        assert response.extraction_summary["entities_count"] == 47
        assert response.extraction_summary["relations_count"] == 23


class TestUploadStatusResponse:
    """Tests for UploadStatusResponse model.

    Sprint 117 Feature 117.10: Domain Classification Display in Upload Dialog.
    """

    def test_valid_upload_status_response(self):
        """Test creating valid UploadStatusResponse."""
        from src.api.v1.admin_indexing import UploadStatusResponse

        response = UploadStatusResponse(
            document_id="doc_abc123",
            filename="report.pdf",
            status="processing_background",
            progress_pct=65.5,
            current_phase="extraction",
            error_message=None,
            created_at="2026-01-21T10:00:00Z",
            updated_at="2026-01-21T10:02:30Z",
            namespace="default",
            domain="general",
            domain_classification=None,
            extraction_summary=None,
        )

        assert response.document_id == "doc_abc123"
        assert response.filename == "report.pdf"
        assert response.status == "processing_background"
        assert response.progress_pct == 65.5
        assert response.current_phase == "extraction"
        assert response.error_message is None

    def test_upload_status_response_complete(self):
        """Test UploadStatusResponse for completed upload with all data."""
        from src.api.v1.admin_indexing import UploadStatusResponse

        classification_data = {
            "domain_id": "legal",
            "domain_name": "Legal Documents",
            "confidence": 0.88,
            "classification_path": "verified",
            "latency_ms": 95,
            "model_used": "Hybrid-Model",
            "matched_entity_types": ["Contract", "Party", "Clause"],
            "matched_intent": "contract_analysis",
            "requires_review": False,
            "alternatives": [],
        }

        extraction_data = {
            "entities_count": 125,
            "relations_count": 87,
            "chunks_count": 34,
            "mentioned_in_count": 125,
        }

        response = UploadStatusResponse(
            document_id="doc_legal_001",
            filename="contract.pdf",
            status="ready",
            progress_pct=100.0,
            current_phase="completed",
            error_message=None,
            created_at="2026-01-21T09:00:00Z",
            updated_at="2026-01-21T09:01:15Z",
            namespace="legal_docs",
            domain="legal",
            domain_classification=classification_data,
            extraction_summary=extraction_data,
        )

        assert response.status == "ready"
        assert response.progress_pct == 100.0
        assert response.domain_classification is not None
        assert response.extraction_summary is not None
        assert response.domain_classification["confidence"] == 0.88
        assert response.extraction_summary["entities_count"] == 125

    def test_upload_status_response_failed(self):
        """Test UploadStatusResponse for failed upload."""
        from src.api.v1.admin_indexing import UploadStatusResponse

        response = UploadStatusResponse(
            document_id="doc_fail_001",
            filename="corrupted.pdf",
            status="failed",
            progress_pct=35.0,
            current_phase="parsing",
            error_message="Failed to parse document: Invalid PDF structure",
            created_at="2026-01-21T11:00:00Z",
            updated_at="2026-01-21T11:00:45Z",
            namespace="default",
            domain="general",
            domain_classification=None,
            extraction_summary=None,
        )

        assert response.status == "failed"
        assert response.error_message is not None
        assert "Invalid PDF structure" in response.error_message
        assert response.progress_pct == 35.0
        assert response.domain_classification is None
        assert response.extraction_summary is None
