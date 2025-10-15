"""Unit tests for DocumentIngestionPipeline.

Tests document ingestion including:
- Loading documents from directory
- Chunking with sentence splitter
- Embedding generation
- Complete ingestion pipeline
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.components.vector_search.ingestion import (
    DocumentIngestionPipeline,
    ingest_documents,
)
from src.core.exceptions import VectorSearchError


# ============================================================================
# Test Initialization
# ============================================================================


@pytest.mark.unit
def test_ingestion_pipeline_init_default():
    """Test DocumentIngestionPipeline initialization with defaults."""
    with patch('src.components.vector_search.ingestion.QdrantClientWrapper'), \
         patch('src.components.vector_search.ingestion.EmbeddingService'):

        pipeline = DocumentIngestionPipeline()

        assert pipeline.chunk_size == 512, "Default chunk size should be 512"
        assert pipeline.chunk_overlap == 128, "Default overlap should be 128"
        assert pipeline.collection_name is not None, "Collection name should be set"


@pytest.mark.unit
def test_ingestion_pipeline_init_custom(mock_qdrant_client, mock_embedding_service):
    """Test DocumentIngestionPipeline with custom parameters."""
    pipeline = DocumentIngestionPipeline(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        collection_name="custom_collection",
        chunk_size=1024,
        chunk_overlap=256,
    )

    assert pipeline.qdrant_client is mock_qdrant_client
    assert pipeline.embedding_service is mock_embedding_service
    assert pipeline.collection_name == "custom_collection"
    assert pipeline.chunk_size == 1024
    assert pipeline.chunk_overlap == 256


# ============================================================================
# Test Document Loading
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_documents_success(mock_qdrant_client, mock_embedding_service, mock_llama_documents, tmp_path):
    """Test successful document loading."""
    # Create a temporary directory
    test_dir = tmp_path / "test"
    test_dir.mkdir()

    with patch('src.components.vector_search.ingestion.SimpleDirectoryReader') as mock_reader:
        mock_reader.return_value.load_data.return_value = mock_llama_documents

        pipeline = DocumentIngestionPipeline(
            qdrant_client=mock_qdrant_client,
            embedding_service=mock_embedding_service,
            allowed_base_path=str(tmp_path),  # Allow tmp_path for tests
        )

        documents = await pipeline.load_documents(input_dir=str(test_dir))

        assert len(documents) == len(mock_llama_documents), "Should load all documents"
        assert documents == mock_llama_documents, "Should return LlamaIndex documents"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_documents_custom_extensions(mock_qdrant_client, mock_embedding_service, tmp_path):
    """Test loading documents with custom extensions."""
    # Create a temporary directory
    test_dir = tmp_path / "test"
    test_dir.mkdir()

    with patch('src.components.vector_search.ingestion.SimpleDirectoryReader') as mock_reader:
        mock_reader.return_value.load_data.return_value = []

        pipeline = DocumentIngestionPipeline(
            qdrant_client=mock_qdrant_client,
            embedding_service=mock_embedding_service,
            allowed_base_path=str(tmp_path),
        )

        await pipeline.load_documents(
            input_dir=str(test_dir),
            required_exts=[".txt", ".md"],
        )

        # Verify extensions were passed
        call_args = mock_reader.call_args
        assert ".txt" in call_args.kwargs["required_exts"]
        assert ".md" in call_args.kwargs["required_exts"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_documents_failure(mock_qdrant_client, mock_embedding_service, tmp_path):
    """Test document loading failure."""
    # Create a temporary directory (but will fail to read documents from it)
    test_dir = tmp_path / "test"
    test_dir.mkdir()

    with patch('src.components.vector_search.ingestion.SimpleDirectoryReader') as mock_reader:
        mock_reader.side_effect = Exception("Directory not found")

        pipeline = DocumentIngestionPipeline(
            qdrant_client=mock_qdrant_client,
            embedding_service=mock_embedding_service,
            allowed_base_path=str(tmp_path),
        )

        with pytest.raises(VectorSearchError) as exc_info:
            await pipeline.load_documents(input_dir=str(test_dir))

        assert "Failed to load documents" in str(exc_info.value)


# ============================================================================
# Test Document Chunking
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chunk_documents_success(mock_qdrant_client, mock_embedding_service, mock_llama_documents, mock_llama_nodes):
    """Test successful document chunking."""
    with patch('src.components.vector_search.ingestion.SentenceSplitter') as mock_splitter:
        mock_splitter.return_value.get_nodes_from_documents.return_value = mock_llama_nodes

        pipeline = DocumentIngestionPipeline(
            qdrant_client=mock_qdrant_client,
            embedding_service=mock_embedding_service,
        )

        nodes = await pipeline.chunk_documents(mock_llama_documents)

        assert len(nodes) == len(mock_llama_nodes), "Should return all chunks"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chunk_documents_empty_list(mock_qdrant_client, mock_embedding_service):
    """Test chunking empty document list."""
    with patch('src.components.vector_search.ingestion.SentenceSplitter') as mock_splitter:
        mock_splitter.return_value.get_nodes_from_documents.return_value = []

        pipeline = DocumentIngestionPipeline(
            qdrant_client=mock_qdrant_client,
            embedding_service=mock_embedding_service,
        )

        nodes = await pipeline.chunk_documents([])

        assert nodes == [], "Empty input should return empty list"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chunk_documents_failure(mock_qdrant_client, mock_embedding_service, mock_llama_documents):
    """Test chunking failure."""
    with patch.object(DocumentIngestionPipeline, '__init__', lambda x, **kwargs: None):
        pipeline = DocumentIngestionPipeline()
        pipeline.qdrant_client = mock_qdrant_client
        pipeline.embedding_service = mock_embedding_service

        with patch('src.components.vector_search.ingestion.SentenceSplitter') as mock_splitter:
            mock_splitter.return_value.get_nodes_from_documents.side_effect = Exception("Chunking failed")

            with pytest.raises(VectorSearchError) as exc_info:
                await pipeline.chunk_documents(mock_llama_documents)

            assert "Failed to chunk documents" in str(exc_info.value)


# ============================================================================
# Test Embedding Generation
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_embeddings_success(mock_qdrant_client, mock_embedding_service, mock_llama_nodes):
    """Test successful embedding generation."""
    pipeline = DocumentIngestionPipeline(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
    )

    embeddings = await pipeline.generate_embeddings(mock_llama_nodes)

    assert len(embeddings) > 0, "Should generate embeddings"
    mock_embedding_service.embed_batch.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_embeddings_failure(mock_qdrant_client, mock_llama_nodes):
    """Test embedding generation failure."""
    mock_service = MagicMock()
    mock_service.embed_batch = AsyncMock(side_effect=Exception("Embedding failed"))

    pipeline = DocumentIngestionPipeline(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_service,
    )

    with pytest.raises(VectorSearchError) as exc_info:
        await pipeline.generate_embeddings(mock_llama_nodes)

    assert "Failed to generate embeddings" in str(exc_info.value)


# ============================================================================
# Test Complete Ingestion Pipeline
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_index_documents_success(mock_qdrant_client, mock_embedding_service, mock_llama_documents, mock_llama_nodes, temp_test_dir):
    """Test complete document ingestion pipeline."""
    with patch('src.components.vector_search.ingestion.SimpleDirectoryReader') as mock_reader, \
         patch.object(DocumentIngestionPipeline, 'chunk_documents') as mock_chunk:

        mock_reader.return_value.load_data.return_value = mock_llama_documents
        mock_chunk.return_value = mock_llama_nodes

        pipeline = DocumentIngestionPipeline(
            qdrant_client=mock_qdrant_client,
            embedding_service=mock_embedding_service,
        )

        stats = await pipeline.index_documents(input_dir=temp_test_dir)

        assert "documents_loaded" in stats, "Should include documents_loaded"
        assert "chunks_created" in stats, "Should include chunks_created"
        assert "embeddings_generated" in stats, "Should include embeddings_generated"
        assert "points_indexed" in stats, "Should include points_indexed"
        assert "duration_seconds" in stats, "Should include duration"
        assert "collection_name" in stats, "Should include collection_name"

        # Verify all steps were called
        mock_qdrant_client.create_collection.assert_called_once()
        mock_qdrant_client.upsert_points.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_index_documents_no_documents_found(mock_qdrant_client, mock_embedding_service, temp_test_dir):
    """Test ingestion when no documents are found."""
    with patch('src.components.vector_search.ingestion.SimpleDirectoryReader') as mock_reader:
        mock_reader.return_value.load_data.return_value = []

        pipeline = DocumentIngestionPipeline(
            qdrant_client=mock_qdrant_client,
            embedding_service=mock_embedding_service,
        )

        stats = await pipeline.index_documents(input_dir=temp_test_dir)

        assert stats["documents_loaded"] == 0, "Should report 0 documents"
        assert stats["chunks_created"] == 0, "Should report 0 chunks"
        assert stats["points_indexed"] == 0, "Should report 0 points"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_index_documents_failure(mock_qdrant_client, mock_embedding_service, temp_test_dir):
    """Test ingestion pipeline failure."""
    with patch('src.components.vector_search.ingestion.SimpleDirectoryReader') as mock_reader:
        mock_reader.side_effect = Exception("Loading failed")

        pipeline = DocumentIngestionPipeline(
            qdrant_client=mock_qdrant_client,
            embedding_service=mock_embedding_service,
        )

        with pytest.raises(VectorSearchError) as exc_info:
            await pipeline.index_documents(input_dir=temp_test_dir)

        assert "Document ingestion failed" in str(exc_info.value)


# ============================================================================
# Test Collection Stats
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_collection_stats_success(mock_qdrant_client, mock_embedding_service):
    """Test getting collection statistics."""
    pipeline = DocumentIngestionPipeline(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
    )

    stats = await pipeline.get_collection_stats()

    assert stats is not None, "Should return stats"
    assert "collection_name" in stats
    assert "vectors_count" in stats
    assert "points_count" in stats


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_collection_stats_not_found(mock_embedding_service):
    """Test getting stats for non-existent collection."""
    mock_client = MagicMock()
    mock_client.get_collection_info = AsyncMock(return_value=None)

    pipeline = DocumentIngestionPipeline(
        qdrant_client=mock_client,
        embedding_service=mock_embedding_service,
    )

    stats = await pipeline.get_collection_stats()

    assert stats is None, "Should return None for non-existent collection"


# ============================================================================
# Test Convenience Function
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ingest_documents_function(temp_test_dir):
    """Test convenience ingest_documents function."""
    with patch('src.components.vector_search.ingestion.DocumentIngestionPipeline') as mock_pipeline_class:
        mock_pipeline = MagicMock()
        mock_pipeline.index_documents = AsyncMock(return_value={"documents_loaded": 3})
        mock_pipeline_class.return_value = mock_pipeline

        stats = await ingest_documents(
            input_dir=temp_test_dir,
            collection_name="test_collection",
            chunk_size=1024,
        )

        assert stats["documents_loaded"] == 3, "Should return ingestion stats"
        mock_pipeline_class.assert_called_once()


# ============================================================================
# Test Edge Cases
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_index_documents_large_batch(mock_qdrant_client, mock_embedding_service, tmp_path):
    """Test indexing with custom batch size."""
    from llama_index.core import Document
    from llama_index.core.schema import TextNode

    # Create a temporary directory
    test_dir = tmp_path / "test"
    test_dir.mkdir()

    large_doc_count = 250
    documents = [Document(text=f"Doc {i}") for i in range(large_doc_count)]
    nodes = [TextNode(text=f"Node {i}") for i in range(large_doc_count)]

    # Override mock to return correct number of embeddings
    mock_embedding_service.embed_batch = AsyncMock(
        return_value=[[0.1 + i * 0.01] * 768 for i in range(large_doc_count)]
    )

    with patch('src.components.vector_search.ingestion.SimpleDirectoryReader') as mock_reader, \
         patch.object(DocumentIngestionPipeline, 'chunk_documents') as mock_chunk:

        mock_reader.return_value.load_data.return_value = documents
        mock_chunk.return_value = nodes

        pipeline = DocumentIngestionPipeline(
            qdrant_client=mock_qdrant_client,
            embedding_service=mock_embedding_service,
            allowed_base_path=str(tmp_path),
        )

        stats = await pipeline.index_documents(
            input_dir=str(test_dir),
            batch_size=100,
        )

        assert stats["points_indexed"] == large_doc_count, "Should index all points"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_documents_recursive(mock_qdrant_client, mock_embedding_service, tmp_path):
    """Test loading documents recursively from subdirectories."""
    # Create a temporary directory
    test_dir = tmp_path / "test"
    test_dir.mkdir()

    with patch('src.components.vector_search.ingestion.SimpleDirectoryReader') as mock_reader:
        mock_reader.return_value.load_data.return_value = []

        pipeline = DocumentIngestionPipeline(
            qdrant_client=mock_qdrant_client,
            embedding_service=mock_embedding_service,
            allowed_base_path=str(tmp_path),
        )

        await pipeline.load_documents(
            input_dir=str(test_dir),
            recursive=True,
        )

        # Verify recursive flag was passed
        call_args = mock_reader.call_args
        assert call_args.kwargs["recursive"] is True
