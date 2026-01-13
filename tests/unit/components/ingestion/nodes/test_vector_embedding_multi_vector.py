"""Unit tests for embedding_node multi-vector integration (Sprint 87 Feature 87.4).

Tests:
1. Multi-vector backend detection (FlagEmbedding returns dict)
2. Multi-vector collection creation
3. Multi-vector point creation (named vectors)
4. Backward compatibility (multi-vector backend, dense-only collection)
5. Dense-only fallback (sentence-transformers/ollama backends)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from qdrant_client.models import SparseVector

from src.components.ingestion.ingestion_state import create_initial_state
from src.components.ingestion.nodes.vector_embedding import embedding_node


@pytest.fixture
def mock_multi_vector_embeddings():
    """Mock embeddings from FlagEmbedding (multi-vector format)."""
    return [
        {
            "dense": [0.1] * 1024,
            "sparse": {1: 0.5, 2: 0.3, 3: 0.2},
            "sparse_vector": SparseVector(indices=[1, 2, 3], values=[0.5, 0.3, 0.2]),
        },
        {
            "dense": [0.2] * 1024,
            "sparse": {4: 0.6, 5: 0.4},
            "sparse_vector": SparseVector(indices=[4, 5], values=[0.6, 0.4]),
        },
    ]


@pytest.fixture
def mock_dense_embeddings():
    """Mock embeddings from sentence-transformers/ollama (dense-only format)."""
    return [
        [0.1] * 1024,
        [0.2] * 1024,
    ]


@pytest.fixture
def base_state():
    """Base ingestion state with 2 chunks."""
    state = create_initial_state(
        document_path="/test/doc.pdf",
        document_id="test_doc",
        batch_id="batch_001",
        batch_index=0,
        total_documents=1,
        namespace_id="test_namespace",
    )

    # Add mock chunks
    state["chunks"] = [
        {
            "chunk": MagicMock(
                content="Test chunk 1",
                meta=MagicMock(page_no=1, headings=["Section 1"]),
                contextualize=lambda: "Context: Test chunk 1",
            ),
            "image_bboxes": [],
        },
        {
            "chunk": MagicMock(
                content="Test chunk 2",
                meta=MagicMock(page_no=2, headings=["Section 2"]),
                contextualize=lambda: "Context: Test chunk 2",
            ),
            "image_bboxes": [],
        },
    ]

    return state


@pytest.mark.asyncio
async def test_embedding_node_multi_vector_backend(base_state, mock_multi_vector_embeddings):
    """Test embedding_node with FlagEmbedding multi-vector backend."""
    # Mock embedding service (returns multi-vector format)
    mock_service = AsyncMock()
    mock_service.embed_batch = AsyncMock(return_value=mock_multi_vector_embeddings)

    # Mock multi-vector manager
    mock_manager = AsyncMock()
    mock_manager.create_multi_vector_collection = AsyncMock(return_value=True)
    mock_manager.collection_has_sparse = AsyncMock(return_value=True)

    # Mock Qdrant client
    mock_qdrant = AsyncMock()
    mock_qdrant.upsert_points = AsyncMock()
    mock_qdrant.async_client = AsyncMock()
    mock_qdrant.async_client.update_collection = AsyncMock()

    with (
        patch(
            "src.components.ingestion.nodes.vector_embedding.get_embedding_service",
            return_value=mock_service,
        ),
        patch(
            "src.components.ingestion.nodes.vector_embedding.get_multi_vector_manager",
            return_value=mock_manager,
        ),
        patch(
            "src.components.ingestion.nodes.vector_embedding.QdrantClientWrapper",
            return_value=mock_qdrant,
        ),
    ):
        result = await embedding_node(base_state)

        # Verify multi-vector collection was created
        mock_manager.create_multi_vector_collection.assert_called_once()
        call_args = mock_manager.create_multi_vector_collection.call_args
        assert call_args.kwargs["collection_name"] == "documents_v1"
        assert call_args.kwargs["dense_dim"] == 1024

        # Verify collection capabilities were checked
        mock_manager.collection_has_sparse.assert_called_once_with("documents_v1")

        # Verify points were uploaded
        mock_qdrant.upsert_points.assert_called_once()
        points = mock_qdrant.upsert_points.call_args.kwargs["points"]

        # Verify multi-vector point structure
        assert len(points) == 2
        first_point = points[0]

        # Check named vectors format
        assert isinstance(first_point.vector, dict)
        assert "dense" in first_point.vector
        assert "sparse" in first_point.vector
        assert len(first_point.vector["dense"]) == 1024
        assert isinstance(first_point.vector["sparse"], SparseVector)

        # Verify state was updated
        assert result["embedding_status"] == "completed"
        assert len(result["embedded_chunk_ids"]) == 2


@pytest.mark.asyncio
async def test_embedding_node_dense_only_backend(base_state, mock_dense_embeddings):
    """Test embedding_node with dense-only backend (sentence-transformers/ollama)."""
    # Mock embedding service (returns dense-only format)
    mock_service = AsyncMock()
    mock_service.embed_batch = AsyncMock(return_value=mock_dense_embeddings)

    # Mock multi-vector manager
    mock_manager = AsyncMock()
    mock_manager.collection_has_sparse = AsyncMock(return_value=False)

    # Mock Qdrant client
    mock_qdrant = AsyncMock()
    mock_qdrant.create_collection = AsyncMock()
    mock_qdrant.upsert_points = AsyncMock()
    mock_qdrant.async_client = AsyncMock()
    mock_qdrant.async_client.update_collection = AsyncMock()

    with (
        patch(
            "src.components.ingestion.nodes.vector_embedding.get_embedding_service",
            return_value=mock_service,
        ),
        patch(
            "src.components.ingestion.nodes.vector_embedding.get_multi_vector_manager",
            return_value=mock_manager,
        ),
        patch(
            "src.components.ingestion.nodes.vector_embedding.QdrantClientWrapper",
            return_value=mock_qdrant,
        ),
    ):
        result = await embedding_node(base_state)

        # Verify dense-only collection was created
        mock_qdrant.create_collection.assert_called_once()
        call_args = mock_qdrant.create_collection.call_args
        assert call_args.kwargs["collection_name"] == "documents_v1"
        assert call_args.kwargs["vector_size"] == 1024

        # Verify points were uploaded
        mock_qdrant.upsert_points.assert_called_once()
        points = mock_qdrant.upsert_points.call_args.kwargs["points"]

        # Verify dense-only point structure
        assert len(points) == 2
        first_point = points[0]

        # Check legacy format (vector is list, not dict)
        assert isinstance(first_point.vector, list)
        assert len(first_point.vector) == 1024

        # Verify state was updated
        assert result["embedding_status"] == "completed"
        assert len(result["embedded_chunk_ids"]) == 2


@pytest.mark.asyncio
async def test_embedding_node_backward_compatibility_fallback(
    base_state, mock_multi_vector_embeddings
):
    """Test backward compatibility: multi-vector backend but dense-only collection."""
    # Mock embedding service (returns multi-vector format)
    mock_service = AsyncMock()
    mock_service.embed_batch = AsyncMock(return_value=mock_multi_vector_embeddings)

    # Mock multi-vector manager (collection does NOT have sparse)
    mock_manager = AsyncMock()
    mock_manager.create_multi_vector_collection = AsyncMock(return_value=True)
    mock_manager.collection_has_sparse = AsyncMock(return_value=False)

    # Mock Qdrant client
    mock_qdrant = AsyncMock()
    mock_qdrant.upsert_points = AsyncMock()
    mock_qdrant.async_client = AsyncMock()
    mock_qdrant.async_client.update_collection = AsyncMock()

    with (
        patch(
            "src.components.ingestion.nodes.vector_embedding.get_embedding_service",
            return_value=mock_service,
        ),
        patch(
            "src.components.ingestion.nodes.vector_embedding.get_multi_vector_manager",
            return_value=mock_manager,
        ),
        patch(
            "src.components.ingestion.nodes.vector_embedding.QdrantClientWrapper",
            return_value=mock_qdrant,
        ),
    ):
        result = await embedding_node(base_state)

        # Verify multi-vector collection creation was attempted
        mock_manager.create_multi_vector_collection.assert_called_once()

        # Verify points were uploaded
        mock_qdrant.upsert_points.assert_called_once()
        points = mock_qdrant.upsert_points.call_args.kwargs["points"]

        # Verify fallback to dense-only format
        assert len(points) == 2
        first_point = points[0]

        # Check that dense vector was extracted (not multi-vector dict)
        assert isinstance(first_point.vector, list)
        assert len(first_point.vector) == 1024

        # Verify state was updated
        assert result["embedding_status"] == "completed"
        assert len(result["embedded_chunk_ids"]) == 2


@pytest.mark.asyncio
async def test_embedding_node_multi_vector_metadata_logging(
    base_state, mock_multi_vector_embeddings
):
    """Test that multi-vector metadata is properly logged."""
    # Mock embedding service
    mock_service = AsyncMock()
    mock_service.embed_batch = AsyncMock(return_value=mock_multi_vector_embeddings)

    # Mock multi-vector manager
    mock_manager = AsyncMock()
    mock_manager.create_multi_vector_collection = AsyncMock(return_value=True)
    mock_manager.collection_has_sparse = AsyncMock(return_value=True)

    # Mock Qdrant client
    mock_qdrant = AsyncMock()
    mock_qdrant.upsert_points = AsyncMock()
    mock_qdrant.async_client = AsyncMock()
    mock_qdrant.async_client.update_collection = AsyncMock()

    with (
        patch(
            "src.components.ingestion.nodes.vector_embedding.get_embedding_service",
            return_value=mock_service,
        ),
        patch(
            "src.components.ingestion.nodes.vector_embedding.get_multi_vector_manager",
            return_value=mock_manager,
        ),
        patch(
            "src.components.ingestion.nodes.vector_embedding.QdrantClientWrapper",
            return_value=mock_qdrant,
        ),
        patch("src.components.ingestion.nodes.vector_embedding.logger") as mock_logger,
    ):
        await embedding_node(base_state)

        # Find the embedding generation complete log
        generation_logs = [
            call
            for call in mock_logger.info.call_args_list
            if "TIMING_embedding_generation_complete" in str(call)
        ]

        assert len(generation_logs) > 0

        # Verify multi-vector metadata was logged
        log_call = generation_logs[0]
        log_kwargs = log_call.kwargs

        assert log_kwargs["is_multi_vector"] is True
        assert log_kwargs["avg_sparse_tokens"] == 2  # First: 3 tokens, second: 2 tokens, avg=2.5→2


@pytest.mark.asyncio
async def test_embedding_node_empty_chunks_error(base_state):
    """Test that embedding_node raises error when no chunks are provided."""
    # Remove chunks
    base_state["chunks"] = []

    with pytest.raises(Exception) as exc_info:
        await embedding_node(base_state)

    assert "No chunks to embed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_embedding_node_preserves_payload_metadata(
    base_state, mock_multi_vector_embeddings
):
    """Test that all payload metadata is preserved in multi-vector mode."""
    # Mock embedding service
    mock_service = AsyncMock()
    mock_service.embed_batch = AsyncMock(return_value=mock_multi_vector_embeddings)

    # Mock multi-vector manager
    mock_manager = AsyncMock()
    mock_manager.create_multi_vector_collection = AsyncMock(return_value=True)
    mock_manager.collection_has_sparse = AsyncMock(return_value=True)

    # Mock Qdrant client
    mock_qdrant = AsyncMock()
    mock_qdrant.upsert_points = AsyncMock()
    mock_qdrant.async_client = AsyncMock()
    mock_qdrant.async_client.update_collection = AsyncMock()

    with (
        patch(
            "src.components.ingestion.nodes.vector_embedding.get_embedding_service",
            return_value=mock_service,
        ),
        patch(
            "src.components.ingestion.nodes.vector_embedding.get_multi_vector_manager",
            return_value=mock_manager,
        ),
        patch(
            "src.components.ingestion.nodes.vector_embedding.QdrantClientWrapper",
            return_value=mock_qdrant,
        ),
    ):
        await embedding_node(base_state)

        # Verify points were uploaded
        points = mock_qdrant.upsert_points.call_args.kwargs["points"]
        first_point = points[0]

        # Verify all expected payload fields
        assert first_point.payload["content"] == "Test chunk 1"
        assert first_point.payload["contextualized_content"] == "Context: Test chunk 1"
        assert first_point.payload["document_id"] == "test_doc"
        assert first_point.payload["page_no"] == 1
        assert first_point.payload["headings"] == ["Section 1"]
        assert first_point.payload["namespace_id"] == "test_namespace"
        assert "ingestion_timestamp" in first_point.payload
