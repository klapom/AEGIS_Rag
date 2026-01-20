"""Unit tests for batch ingestion service.

Sprint 117.5: Batch Document Ingestion Tests

Tests cover:
- Batch creation and initialization
- Parallel document processing
- Progress tracking
- Error handling and isolation
- Status polling
- Domain validation
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.domain_training.batch_ingestion_service import (
    BatchIngestionService,
    BatchProgress,
    DocumentRequest,
    DocumentResult,
    IngestionOptions,
    get_batch_ingestion_service,
    reset_service,
)


@pytest.fixture
def service():
    """Create fresh batch ingestion service for each test."""
    reset_service()
    return BatchIngestionService()


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        DocumentRequest(
            document_id="doc_001",
            content="FastAPI is a modern web framework for building APIs with Python.",
            metadata={"source": "api_docs.pdf", "page": 1},
        ),
        DocumentRequest(
            document_id="doc_002",
            content="Django is a high-level Python web framework.",
            metadata={"source": "django_guide.pdf", "page": 1},
        ),
        DocumentRequest(
            document_id="doc_003",
            content="Flask is a lightweight WSGI web application framework.",
            metadata={"source": "flask_docs.pdf", "page": 1},
        ),
    ]


@pytest.fixture
def mock_domain():
    """Mock domain configuration."""
    return {
        "name": "tech_docs",
        "entity_prompt": "Extract entities from technical documentation.",
        "relation_prompt": "Extract relations between technical entities.",
        "llm_model": "qwen3:32b",
    }


class TestBatchIngestionService:
    """Test suite for BatchIngestionService."""

    def test_service_initialization(self, service):
        """Test service initializes with empty state."""
        assert service._batches == {}
        assert service._batch_locks == {}

    def test_singleton_pattern(self):
        """Test singleton pattern returns same instance."""
        reset_service()
        service1 = get_batch_ingestion_service()
        service2 = get_batch_ingestion_service()
        assert service1 is service2

    def test_reset_singleton(self):
        """Test singleton can be reset."""
        service1 = get_batch_ingestion_service()
        reset_service()
        service2 = get_batch_ingestion_service()
        assert service1 is not service2

    @pytest.mark.asyncio
    async def test_start_batch_validates_document_count(self, service, sample_documents):
        """Test batch creation validates document count (max 100)."""
        # Too many documents
        too_many_docs = [
            DocumentRequest(
                document_id=f"doc_{i:03d}",
                content="Test content",
                metadata={},
            )
            for i in range(101)
        ]

        options = IngestionOptions()

        with patch("src.components.domain_training.get_domain_repository"):
            with pytest.raises(ValueError, match="Maximum 100 documents per batch"):
                await service.start_batch(
                    domain_name="tech_docs",
                    documents=too_many_docs,
                    options=options,
                )

    @pytest.mark.asyncio
    async def test_start_batch_validates_domain_exists(self, service, sample_documents):
        """Test batch creation validates domain exists."""
        options = IngestionOptions()

        # Mock repository that returns None (domain not found)
        mock_repo = AsyncMock()
        mock_repo.get_domain = AsyncMock(return_value=None)

        with patch(
            "src.components.domain_training.get_domain_repository",
            return_value=mock_repo,
        ):
            with pytest.raises(ValueError, match="Domain not found"):
                await service.start_batch(
                    domain_name="nonexistent_domain",
                    documents=sample_documents,
                    options=options,
                )

    @pytest.mark.asyncio
    async def test_start_batch_creates_batch_progress(
        self, service, sample_documents, mock_domain
    ):
        """Test batch creation initializes BatchProgress."""
        options = IngestionOptions()

        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_domain = AsyncMock(return_value=mock_domain)

        with patch(
            "src.components.domain_training.get_domain_repository",
            return_value=mock_repo,
        ):
            # Mock background processing to prevent actual execution
            with patch.object(service, "_process_batch_async", new_callable=AsyncMock):
                batch_id = await service.start_batch(
                    domain_name="tech_docs",
                    documents=sample_documents,
                    options=options,
                )

        # Verify batch was created
        assert batch_id.startswith("batch_")
        assert batch_id in service._batches

        batch = service._batches[batch_id]
        assert isinstance(batch, BatchProgress)
        assert batch.domain_name == "tech_docs"
        assert batch.total_documents == len(sample_documents)
        assert batch.status == "processing"

    @pytest.mark.asyncio
    async def test_get_batch_status_returns_none_for_unknown_batch(self, service):
        """Test get_batch_status returns None for unknown batch ID."""
        status = await service.get_batch_status("nonexistent_batch")
        assert status is None

    @pytest.mark.asyncio
    async def test_get_batch_status_returns_dict(self, service, sample_documents, mock_domain):
        """Test get_batch_status returns proper dict format."""
        options = IngestionOptions()

        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_domain = AsyncMock(return_value=mock_domain)

        with patch(
            "src.components.domain_training.get_domain_repository",
            return_value=mock_repo,
        ):
            with patch.object(service, "_process_batch_async", new_callable=AsyncMock):
                batch_id = await service.start_batch(
                    domain_name="tech_docs",
                    documents=sample_documents,
                    options=options,
                )

        status = await service.get_batch_status(batch_id)

        assert status is not None
        assert status["batch_id"] == batch_id
        assert status["domain_name"] == "tech_docs"
        assert status["total_documents"] == len(sample_documents)
        assert status["status"] == "processing"
        assert "progress" in status
        assert "completed" in status["progress"]
        assert "failed" in status["progress"]
        assert "pending" in status["progress"]

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="chunk_text import path needs fix - Sprint 117 implementation gap")
    async def test_process_single_document_success(self, service, mock_domain):
        """Test successful document processing."""
        batch_id = "batch_test"
        document = DocumentRequest(
            document_id="doc_001",
            content="FastAPI is a modern web framework.",
            metadata={"source": "test.pdf"},
        )
        options = IngestionOptions(
            extract_entities=True,
            extract_relations=True,
            chunk_strategy="section_aware",
            parallel_workers=4,
        )

        # Mock all external dependencies (lazy imports, patch at source)
        with patch("src.components.chunking.chunk_text") as mock_chunk:
            mock_chunk.return_value = ["FastAPI is a modern web framework."]

            mock_lightrag = AsyncMock()
            mock_lightrag.extract_entities_and_relations = AsyncMock(
                return_value={
                    "entities": [{"name": "FastAPI"}],
                    "relations": [{"subject": "FastAPI", "predicate": "IS_A", "object": "framework"}],
                }
            )
            mock_lightrag.create_mentioned_in_relation = AsyncMock()

            with patch(
                "src.components.graph_rag.lightrag_wrapper.get_lightrag_wrapper_async",
                return_value=mock_lightrag,
            ):
                mock_embedding_service = AsyncMock()
                mock_embedding_service.embed_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3]])

                with patch(
                    "src.components.shared.embedding_service.get_embedding_service",
                    return_value=mock_embedding_service,
                ):
                    mock_qdrant = AsyncMock()
                    mock_qdrant.upsert_documents = AsyncMock()

                    with patch(
                        "src.components.vector_search.qdrant_client.get_qdrant_client",
                        return_value=mock_qdrant,
                    ):
                        result = await service._process_single_document(
                            batch_id=batch_id,
                            domain_name="tech_docs",
                            domain_config=mock_domain,
                            document=document,
                            options=options,
                        )

        # Verify result
        assert isinstance(result, DocumentResult)
        assert result.document_id == "doc_001"
        assert result.status == "completed"
        assert result.entities_extracted == 1
        assert result.relations_extracted == 2  # 1 relation + 1 MENTIONED_IN
        assert result.chunks_created == 1
        assert result.processing_time_ms > 0
        assert result.error is None

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="chunk_text import path needs fix - Sprint 117 implementation gap")
    async def test_process_single_document_error_handling(self, service, mock_domain):
        """Test document processing handles errors gracefully."""
        batch_id = "batch_test"
        document = DocumentRequest(
            document_id="doc_error",
            content="Test content",
            metadata={},
        )
        options = IngestionOptions()

        # Mock chunk_text to raise exception (patch at source)
        with patch(
            "src.components.chunking.chunk_text",
            side_effect=Exception("Chunking failed"),
        ):
            result = await service._process_single_document(
                batch_id=batch_id,
                domain_name="tech_docs",
                domain_config=mock_domain,
                document=document,
                options=options,
            )

        # Verify error handling
        assert isinstance(result, DocumentResult)
        assert result.document_id == "doc_error"
        assert result.status == "error"
        assert result.error == "Chunking failed"
        assert result.error_code == "PROCESSING_FAILED"
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_batch_progress_properties(self):
        """Test BatchProgress computed properties."""
        batch = BatchProgress(
            batch_id="batch_test",
            domain_name="tech_docs",
            total_documents=10,
        )

        # Add results
        batch.results.append(
            DocumentResult(document_id="doc_001", status="completed", processing_time_ms=100)
        )
        batch.results.append(
            DocumentResult(document_id="doc_002", status="completed", processing_time_ms=200)
        )
        batch.results.append(
            DocumentResult(
                document_id="doc_003",
                status="error",
                processing_time_ms=50,
                error="Test error",
                error_code="TEST_ERROR",
            )
        )

        # Verify properties
        assert batch.completed_count == 2
        assert batch.failed_count == 1
        assert batch.pending_count == 7

    @pytest.mark.asyncio
    async def test_ingestion_options_validation(self):
        """Test IngestionOptions validates parallel_workers."""
        # Test minimum workers
        options = IngestionOptions(parallel_workers=0)
        assert options.parallel_workers == 1

        # Test maximum workers
        options = IngestionOptions(parallel_workers=20)
        assert options.parallel_workers == 10

        # Test valid range
        options = IngestionOptions(parallel_workers=4)
        assert options.parallel_workers == 4


class TestBatchProgressTracking:
    """Test suite for BatchProgress tracking."""

    def test_batch_progress_to_dict(self):
        """Test BatchProgress serialization to dict."""
        batch = BatchProgress(
            batch_id="batch_123",
            domain_name="tech_docs",
            total_documents=5,
            status="processing",
        )

        batch.results.append(
            DocumentResult(
                document_id="doc_001",
                status="completed",
                entities_extracted=10,
                relations_extracted=5,
                chunks_created=3,
                processing_time_ms=1500,
            )
        )

        batch.errors.append(
            {
                "document_id": "doc_002",
                "error": "Extraction failed",
                "error_code": "EXTRACTION_FAILED",
            }
        )

        result_dict = batch.to_dict()

        assert result_dict["batch_id"] == "batch_123"
        assert result_dict["domain_name"] == "tech_docs"
        assert result_dict["total_documents"] == 5
        assert result_dict["status"] == "processing"
        assert result_dict["progress"]["completed"] == 1
        assert result_dict["progress"]["failed"] == 0
        assert result_dict["progress"]["pending"] == 4
        assert len(result_dict["results"]) == 1
        assert len(result_dict["errors"]) == 1

    def test_batch_progress_counts(self):
        """Test BatchProgress count calculations."""
        batch = BatchProgress(
            batch_id="batch_123",
            domain_name="tech_docs",
            total_documents=10,
        )

        # Add 3 completed, 2 errors
        for i in range(3):
            batch.results.append(
                DocumentResult(document_id=f"doc_{i}", status="completed", processing_time_ms=100)
            )

        for i in range(3, 5):
            batch.results.append(
                DocumentResult(
                    document_id=f"doc_{i}",
                    status="error",
                    processing_time_ms=50,
                    error="Test",
                    error_code="TEST",
                )
            )

        assert batch.completed_count == 3
        assert batch.failed_count == 2
        assert batch.pending_count == 5


class TestParallelProcessing:
    """Test suite for parallel document processing."""

    @pytest.mark.asyncio
    async def test_parallel_processing_with_semaphore(self, service, mock_domain):
        """Test parallel processing respects worker limit."""
        options = IngestionOptions(parallel_workers=2)

        # Create 5 documents
        documents = [
            DocumentRequest(
                document_id=f"doc_{i:03d}",
                content=f"Test content {i}",
                metadata={},
            )
            for i in range(5)
        ]

        batch_id = "batch_test"
        service._batches[batch_id] = BatchProgress(
            batch_id=batch_id,
            domain_name="tech_docs",
            total_documents=len(documents),
        )
        service._batch_locks[batch_id] = asyncio.Lock()

        # Track concurrent executions
        concurrent_count = 0
        max_concurrent = 0

        async def mock_process_doc(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.01)  # Simulate processing time
            concurrent_count -= 1
            return DocumentResult(
                document_id=kwargs["document"].document_id,
                status="completed",
                processing_time_ms=10,
            )

        with patch.object(service, "_process_single_document", side_effect=mock_process_doc):
            await service._process_batch_async(
                batch_id=batch_id,
                domain_name="tech_docs",
                domain_config=mock_domain,
                documents=documents,
                options=options,
            )

        # Verify semaphore limit was respected
        assert max_concurrent <= options.parallel_workers
        assert service._batches[batch_id].status == "completed"
        assert service._batches[batch_id].completed_count == 5
        assert service._batches[batch_id].failed_count == 0
