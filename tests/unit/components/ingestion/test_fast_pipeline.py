"""Unit tests for Fast Upload Pipeline (Sprint 83 Feature 83.4).

Tests:
1. SpaCy NER entity extraction (fast, no LLM)
2. Fast upload pipeline workflow (Docling -> Chunking -> Embedding -> Qdrant)
3. Status updates during fast upload
4. Error handling and status marking
5. Performance targets (<5s)
"""

import hashlib
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.ingestion.fast_pipeline import (
    extract_entities_fast,
    get_spacy_nlp,
    run_fast_upload,
)
from src.core.exceptions import IngestionError


@pytest.fixture
def mock_chunks():
    """Create mock chunks for testing."""
    chunks = []
    for i in range(3):
        chunk = MagicMock()
        chunk.content = f"This is chunk {i} with entities like New York and Apple Inc."
        chunk.id = f"chunk_{i}"
        chunk.meta = MagicMock()
        chunk.meta.page_no = i + 1
        chunk.meta.headings = [f"Section {i}"]
        chunks.append(chunk)
    return chunks


@pytest.fixture
def mock_file_path(tmp_path):
    """Create mock file path for testing."""
    file_path = tmp_path / "test_document.pdf"
    file_path.write_text("Test document content")
    return file_path


class TestSpaCyNER:
    """Test SpaCy NER entity extraction."""

    def test_get_spacy_nlp_loads_model(self):
        """Test SpaCy NLP model loading."""
        with patch("spacy.load") as mock_load:
            mock_nlp = MagicMock()
            mock_load.return_value = mock_nlp

            nlp = get_spacy_nlp()

            assert nlp is not None
            mock_load.assert_called_once_with("en_core_web_sm")

    async def test_extract_entities_fast_success(self, mock_chunks):
        """Test fast entity extraction with SpaCy."""
        with patch("src.components.ingestion.fast_pipeline.get_spacy_nlp") as mock_get_nlp:
            # Mock SpaCy NLP
            mock_nlp = MagicMock()
            mock_doc = MagicMock()

            # Mock entities
            mock_ent_1 = MagicMock()
            mock_ent_1.text = "New York"
            mock_ent_1.label_ = "GPE"
            mock_ent_2 = MagicMock()
            mock_ent_2.text = "Apple Inc."
            mock_ent_2.label_ = "ORG"

            mock_doc.ents = [mock_ent_1, mock_ent_2]
            mock_nlp.return_value = mock_doc
            mock_get_nlp.return_value = mock_nlp

            entities = await extract_entities_fast(mock_chunks)

            # Verify entities extracted from all chunks
            assert len(entities) == 6  # 2 entities per chunk * 3 chunks
            assert all(isinstance(e, dict) for e in entities)
            assert all("text" in e and "type" in e for e in entities)

    async def test_extract_entities_fast_performance(self, mock_chunks):
        """Test entity extraction completes in <500ms for 10 chunks."""
        with patch("src.components.ingestion.fast_pipeline.get_spacy_nlp") as mock_get_nlp:
            mock_nlp = MagicMock()
            mock_doc = MagicMock()
            mock_doc.ents = []  # No entities for speed test
            mock_nlp.return_value = mock_doc
            mock_get_nlp.return_value = mock_nlp

            # Create 10 chunks
            chunks = mock_chunks * 4  # 12 chunks (>10)

            start_time = time.perf_counter()
            await extract_entities_fast(chunks)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Should complete in <500ms (actually much faster with mocks)
            assert duration_ms < 500


class TestFastUploadPipeline:
    """Test fast upload pipeline workflow."""

    async def test_run_fast_upload_file_not_found(self):
        """Test fast upload fails if file doesn't exist."""
        with pytest.raises(IngestionError, match="File not found"):
            await run_fast_upload(
                file_path="/nonexistent/file.pdf",
                namespace="research",
                domain="ai_papers",
            )

    async def test_run_fast_upload_success(self, mock_file_path):
        """Test successful fast upload workflow."""
        with (
            patch("src.components.ingestion.fast_pipeline.DoclingClient") as MockDocling,
            patch(
                "src.components.ingestion.fast_pipeline.adaptive_section_chunking"
            ) as mock_chunking,
            patch(
                "src.components.ingestion.fast_pipeline.get_embedding_service"
            ) as mock_embedding_service,
            patch("src.components.ingestion.fast_pipeline.QdrantClientWrapper") as MockQdrant,
            patch(
                "src.components.ingestion.fast_pipeline.extract_entities_fast"
            ) as mock_extract,
            patch(
                "src.components.ingestion.fast_pipeline.get_background_job_queue"
            ) as mock_queue,
        ):
            # Mock Docling
            mock_docling = AsyncMock()
            mock_docling.parse_document.return_value = {"content": "test"}
            MockDocling.return_value = mock_docling

            # Mock chunking
            mock_chunks = []
            for i in range(3):
                chunk = MagicMock()
                chunk.content = f"Chunk {i}"
                chunk.meta = MagicMock()
                chunk.meta.page_no = i + 1
                chunk.meta.headings = []
                mock_chunks.append(chunk)
            mock_chunking.return_value = mock_chunks

            # Mock embeddings
            mock_service = AsyncMock()
            mock_service.embed_batch.return_value = [[0.1] * 1024] * 3
            mock_embedding_service.return_value = mock_service

            # Mock Qdrant
            mock_qdrant = AsyncMock()
            mock_qdrant.create_collection.return_value = None
            mock_qdrant.upsert_points.return_value = None
            MockQdrant.return_value = mock_qdrant

            # Mock entity extraction
            mock_extract.return_value = [
                {"text": "Entity1", "type": "PERSON"},
                {"text": "Entity2", "type": "ORG"},
            ]

            # Mock job queue
            mock_job_queue = AsyncMock()
            mock_job_queue.initialize.return_value = None
            mock_job_queue.set_status.return_value = None
            mock_queue.return_value = mock_job_queue

            # Run fast upload
            document_id = await run_fast_upload(
                file_path=mock_file_path,
                namespace="research",
                domain="ai_papers",
                original_filename="test.pdf",
            )

            # Verify document_id format
            assert document_id.startswith("doc_")
            assert len(document_id) == 20  # "doc_" + 16 hex chars

            # Verify pipeline steps called
            mock_docling.parse_document.assert_awaited_once()
            mock_chunking.assert_awaited_once()
            mock_service.embed_batch.assert_awaited_once()
            mock_qdrant.upsert_points.assert_awaited_once()
            mock_extract.assert_awaited_once()

            # Verify status updates
            assert mock_job_queue.set_status.await_count >= 5
            # Check final status
            final_call = mock_job_queue.set_status.await_args_list[-1]
            assert final_call[1]["status"] == "processing_background"
            assert final_call[1]["progress_pct"] == 100.0

    async def test_run_fast_upload_error_handling(self, mock_file_path):
        """Test fast upload error handling marks status as failed."""
        with (
            patch("src.components.ingestion.fast_pipeline.DoclingClient") as MockDocling,
            patch(
                "src.components.ingestion.fast_pipeline.get_background_job_queue"
            ) as mock_queue,
        ):
            # Mock Docling to raise error
            mock_docling = AsyncMock()
            mock_docling.parse_document.side_effect = Exception("Parsing failed")
            MockDocling.return_value = mock_docling

            # Mock job queue
            mock_job_queue = AsyncMock()
            mock_job_queue.initialize.return_value = None
            mock_job_queue.set_status.return_value = None
            mock_queue.return_value = mock_job_queue

            # Run fast upload (should raise)
            with pytest.raises(IngestionError, match="Fast upload failed"):
                await run_fast_upload(
                    file_path=mock_file_path,
                    namespace="research",
                    domain="ai_papers",
                )

            # Verify error status was set
            final_call = mock_job_queue.set_status.await_args_list[-1]
            assert final_call[1]["status"] == "failed"
            assert "Parsing failed" in final_call[1]["error_message"]

    async def test_run_fast_upload_qdrant_payload(self, mock_file_path):
        """Test Qdrant payload includes fast_upload and refinement_pending flags."""
        with (
            patch("src.components.ingestion.fast_pipeline.DoclingClient") as MockDocling,
            patch(
                "src.components.ingestion.fast_pipeline.adaptive_section_chunking"
            ) as mock_chunking,
            patch(
                "src.components.ingestion.fast_pipeline.get_embedding_service"
            ) as mock_embedding_service,
            patch("src.components.ingestion.fast_pipeline.QdrantClientWrapper") as MockQdrant,
            patch(
                "src.components.ingestion.fast_pipeline.extract_entities_fast"
            ) as mock_extract,
            patch(
                "src.components.ingestion.fast_pipeline.get_background_job_queue"
            ) as mock_queue,
        ):
            # Mock setup (simplified)
            mock_docling = AsyncMock()
            mock_docling.parse_document.return_value = {"content": "test"}
            MockDocling.return_value = mock_docling

            chunk = MagicMock()
            chunk.content = "Test chunk"
            chunk.meta = MagicMock()
            chunk.meta.page_no = 1
            chunk.meta.headings = []
            mock_chunking.return_value = [chunk]

            mock_service = AsyncMock()
            mock_service.embed_batch.return_value = [[0.1] * 1024]
            mock_embedding_service.return_value = mock_service

            mock_qdrant = AsyncMock()
            MockQdrant.return_value = mock_qdrant

            mock_extract.return_value = []

            mock_job_queue = AsyncMock()
            mock_queue.return_value = mock_job_queue

            # Run fast upload
            await run_fast_upload(
                file_path=mock_file_path,
                namespace="research",
                domain="ai_papers",
            )

            # Verify Qdrant payload flags
            upsert_call = mock_qdrant.upsert_points.await_args
            points = upsert_call[1]["points"]
            assert len(points) == 1
            payload = points[0].payload
            assert payload["fast_upload"] is True
            assert payload["refinement_pending"] is True
            assert payload["namespace_id"] == "research"
