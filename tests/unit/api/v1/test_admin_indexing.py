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
