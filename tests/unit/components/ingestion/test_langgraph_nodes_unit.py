"""Unit tests for LangGraph Ingestion Nodes - Sprint 21 Feature 21.2.

These tests use MOCKS (no real Docker services required).
Tests all 5 LangGraph nodes with comprehensive coverage:

1. memory_check_node - RAM/VRAM monitoring with psutil + nvidia-smi mocks
2. docling_parse_node - Document parsing with DoclingClient mocks
3. chunking_node - Chunking service with 1800-token chunks
4. embedding_node - Embedding generation + Qdrant upload mocks
5. graph_extraction_node - LightRAG entity/relation extraction mocks

Test Coverage:
- Happy path (all nodes succeed)
- Error handling (each node can fail independently)
- State updates (progress tracking, status fields)
- Memory management (VRAM leak detection)
- Container lifecycle (start/stop in docling_parse_node)
- Batch processing (multiple chunks)

Run tests:
    pytest tests/unit/components/ingestion/test_langgraph_nodes_unit.py -v
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Check if psutil is available for memory tests
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from src.components.ingestion.ingestion_state import create_initial_state
from src.components.ingestion.langgraph_nodes import (
    chunking_node,
    docling_parse_node,
    embedding_node,
    graph_extraction_node,
    memory_check_node,
)
from src.core.chunk import Chunk
from src.core.exceptions import IngestionError

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_state(tmp_path):
    """Create sample IngestionState for testing."""
    test_doc = tmp_path / "test.pdf"
    test_doc.write_text("Sample PDF content for testing")

    return create_initial_state(
        document_path=str(test_doc),
        document_id="test_doc_001",
        batch_id="batch_001",
        batch_index=0,
        total_documents=5,
        max_retries=3,
    )


@pytest.fixture
def sample_chunks():
    """Create sample Chunk objects for testing."""
    return [
        Chunk(
            chunk_id="0123456789abcdef",  # 16 characters (min length requirement)
            document_id="test_doc_001",
            content="This is test chunk 1 with sample content about machine learning.",
            token_count=1800,
            metadata={"page": 1, "section": "Introduction"},
            chunk_index=0,
            start_char=0,
            end_char=66,
        ),
        Chunk(
            chunk_id="0123456789abcde0",  # Different ID
            document_id="test_doc_001",
            content="This is test chunk 2 with sample content about neural networks.",
            token_count=1800,
            metadata={"page": 2, "section": "Methods"},
            chunk_index=1,
            start_char=67,
            end_char=133,
        ),
        Chunk(
            chunk_id="0123456789abcde1",  # Different ID
            document_id="test_doc_001",
            content="This is test chunk 3 with sample content about deep learning.",
            token_count=1800,
            metadata={"page": 3, "section": "Results"},
            chunk_index=2,
            start_char=134,
            end_char=197,
        ),
    ]


# =============================================================================
# NODE 1: MEMORY CHECK TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not installed - install with: poetry install --with dev")
async def test_memory_check_node_success(sample_state):
    """Test memory_check_node with sufficient RAM and VRAM."""
    with patch("psutil.virtual_memory") as mock_memory, patch("subprocess.run") as mock_nvidia_smi:
        # Mock psutil (4GB RAM used, 6GB available)
        mock_memory.return_value = MagicMock(
            used=4 * 1024 * 1024 * 1024,  # 4GB
            available=6 * 1024 * 1024 * 1024,  # 6GB
        )

        # Mock nvidia-smi (3GB VRAM used, below 5.5GB threshold)
        mock_nvidia_smi.return_value = MagicMock(stdout="3072\n")

        # Run node
        updated_state = await memory_check_node(sample_state)

        # Verify state updates
        assert updated_state["memory_check_passed"] is True
        assert updated_state["current_memory_mb"] == pytest.approx(4096, rel=1)
        assert updated_state["current_vram_mb"] == pytest.approx(3072, rel=1)
        assert updated_state["requires_container_restart"] is False
        assert updated_state["overall_progress"] > 0.0


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not installed - install with: poetry install --with dev")
async def test_memory_check_node_vram_leak_detected(sample_state):
    """Test memory_check_node detects VRAM leak (>5.5GB)."""
    with patch("psutil.virtual_memory") as mock_memory, patch("subprocess.run") as mock_nvidia_smi:
        # Mock psutil (sufficient RAM)
        mock_memory.return_value = MagicMock(
            used=3 * 1024 * 1024 * 1024,
            available=6 * 1024 * 1024 * 1024,
        )

        # Mock nvidia-smi (6GB VRAM used, above 5.5GB threshold)
        mock_nvidia_smi.return_value = MagicMock(stdout="6144\n")

        # Run node
        updated_state = await memory_check_node(sample_state)

        # Verify leak detection
        assert updated_state["memory_check_passed"] is True  # Still passed (RAM OK)
        assert updated_state["current_vram_mb"] == 6144.0
        assert updated_state["requires_container_restart"] is True  # Leak detected!
        assert len(updated_state["errors"]) == 1
        assert "VRAM leak" in updated_state["errors"][0]["message"]


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not installed - install with: poetry install --with dev")
async def test_memory_check_node_insufficient_ram(sample_state):
    """Test memory_check_node fails with insufficient RAM (<500MB)."""
    with patch("psutil.virtual_memory") as mock_memory, patch("subprocess.run") as mock_nvidia_smi:
        # Mock psutil (only 400MB RAM available - below 500MB threshold)
        # Sprint 30: Threshold lowered to 500MB for testing
        mock_memory.return_value = MagicMock(
            used=7 * 1024 * 1024 * 1024,
            available=400 * 1024 * 1024,  # Only 400MB available (< 500MB threshold)
        )

        # Mock nvidia-smi (GPU available)
        mock_nvidia_smi.return_value = MagicMock(stdout="2048\n")

        # Run node (should raise IngestionError)
        with pytest.raises(IngestionError, match="Insufficient RAM"):
            await memory_check_node(sample_state)


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not installed - install with: poetry install --with dev")
async def test_memory_check_node_no_gpu(sample_state):
    """Test memory_check_node handles missing nvidia-smi gracefully."""
    with patch("psutil.virtual_memory") as mock_memory, patch("subprocess.run") as mock_nvidia_smi:
        # Mock psutil (sufficient RAM)
        mock_memory.return_value = MagicMock(
            used=3 * 1024 * 1024 * 1024,
            available=6 * 1024 * 1024 * 1024,
        )

        # Mock nvidia-smi not available (FileNotFoundError)
        mock_nvidia_smi.side_effect = FileNotFoundError("nvidia-smi not found")

        # Run node (should succeed despite no GPU)
        updated_state = await memory_check_node(sample_state)

        # Verify graceful handling
        assert updated_state["memory_check_passed"] is True
        assert updated_state["current_vram_mb"] == 0.0  # No GPU available
        assert updated_state["requires_container_restart"] is False


# =============================================================================
# NODE 2: DOCLING PARSE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_docling_parse_node_success(sample_state):
    """Test docling_parse_node successfully parses document."""
    from src.components.ingestion.docling_client import DoclingParsedDocument

    # Create mock parsed result
    mock_parsed = DoclingParsedDocument(
        text="This is the parsed document content with OCR results.",
        metadata={"pages": 5, "mime_type": "application/pdf"},
        tables=[{"row": 1, "col": 1, "data": "Cell 1"}],
        images=[{"id": "img_001", "page": 1}],
        layout={"headings": ["Chapter 1", "Chapter 2"]},
        parse_time_ms=1234,
    )

    with patch(
        "src.components.ingestion.nodes.document_parsers.DoclingContainerClient"
    ) as mock_client_class:
        # Create mock client instance
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock parse_document
        mock_client.parse_document = AsyncMock(return_value=mock_parsed)

        # Run node
        updated_state = await docling_parse_node(sample_state)

        # Verify parsing success
        assert updated_state["docling_status"] == "completed"
        assert updated_state["parsed_content"] == mock_parsed.text
        assert updated_state["parsed_metadata"] == mock_parsed.metadata
        assert len(updated_state["parsed_tables"]) == 1
        assert len(updated_state["parsed_images"]) == 1
        assert updated_state["parsed_layout"] == mock_parsed.layout
        assert updated_state["overall_progress"] > 0.0

        # Verify container lifecycle (start → parse → stop)
        mock_client.start_container.assert_called_once()
        mock_client.parse_document.assert_called_once()
        mock_client.stop_container.assert_called_once()  # Critical: Always stop!


@pytest.mark.asyncio
async def test_docling_parse_node_with_container_restart(sample_state):
    """Test docling_parse_node restarts container if VRAM leak detected."""
    from src.components.ingestion.docling_client import DoclingParsedDocument

    # Mark VRAM leak in state
    sample_state["requires_container_restart"] = True

    mock_parsed = DoclingParsedDocument(
        text="Parsed content",
        metadata={},
        tables=[],
        images=[],
        layout={},
        parse_time_ms=1000,
    )

    with patch(
        "src.components.ingestion.nodes.document_parsers.DoclingContainerClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.parse_document = AsyncMock(return_value=mock_parsed)

        # Run node
        await docling_parse_node(sample_state)

        # Verify container restart logic
        # Should stop first (to clear leak), then start
        assert mock_client.stop_container.call_count == 2  # Initial stop + final stop
        assert mock_client.start_container.call_count == 1


@pytest.mark.asyncio
async def test_docling_parse_node_file_not_found(sample_state):
    """Test docling_parse_node fails if document doesn't exist."""
    # Point to non-existent file
    sample_state["document_path"] = "/nonexistent/file.pdf"

    # Run node (should raise IngestionError)
    with pytest.raises(IngestionError, match="Document not found"):
        await docling_parse_node(sample_state)


@pytest.mark.asyncio
async def test_docling_parse_node_parsing_error(sample_state):
    """Test docling_parse_node handles parsing errors gracefully."""
    with patch(
        "src.components.ingestion.nodes.document_parsers.DoclingContainerClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock parse_document raises exception
        mock_client.parse_document = AsyncMock(side_effect=Exception("Docling API timeout"))

        # Run node (should raise exception)
        with pytest.raises(Exception, match="Docling API timeout"):
            await docling_parse_node(sample_state)

        # Verify container is stopped even after error (critical!)
        mock_client.stop_container.assert_called_once()


# =============================================================================
# NODE 3: CHUNKING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_chunking_node_success(sample_state, sample_chunks):
    """Test chunking_node successfully chunks document."""
    # Add parsed content to state
    sample_state["parsed_content"] = "This is a long document content. " * 500
    sample_state["parsed_metadata"] = {"pages": 10}

    with patch("src.components.ingestion.nodes.adaptive_chunking.get_chunking_service") as mock_get_service:
        # Mock chunking service (async method requires AsyncMock)
        mock_service = Mock()
        mock_service.chunk_document = AsyncMock(return_value=sample_chunks)
        mock_get_service.return_value = mock_service

        # Run node
        updated_state = await chunking_node(sample_state)

        # Verify chunking success
        assert updated_state["chunking_status"] == "completed"
        assert len(updated_state["chunks"]) == 3
        # Sprint 21 Feature 21.6: chunks now have structure {"chunk": Chunk, "image_bboxes": []}
        assert all(isinstance(c, dict) and "chunk" in c and "image_bboxes" in c for c in updated_state["chunks"])
        # Verify chunk objects match
        chunk_objects = [c["chunk"] for c in updated_state["chunks"]]
        assert chunk_objects == sample_chunks
        assert updated_state["overall_progress"] > 0.0

        # Verify chunking service called with correct parameters
        mock_service.chunk_document.assert_called_once()
        call_args = mock_service.chunk_document.call_args[1]
        assert call_args["document_id"] == "test_doc_001"
        assert call_args["text"] == sample_state["parsed_content"]


@pytest.mark.asyncio
async def test_chunking_node_empty_content(sample_state):
    """Test chunking_node fails if parsed_content is empty."""
    # Set empty parsed content
    sample_state["parsed_content"] = ""

    # Run node (should raise IngestionError)
    with pytest.raises(IngestionError, match="No content to chunk"):
        await chunking_node(sample_state)


@pytest.mark.asyncio
async def test_chunking_node_uses_1800_token_chunks(sample_state):
    """Test chunking_node uses 1800-token chunks (Feature 21.4)."""
    sample_state["parsed_content"] = "Test content for chunking."

    with patch("src.components.ingestion.nodes.adaptive_chunking.get_chunking_service") as mock_get_service:
        mock_service = Mock()
        mock_service.chunk_document = AsyncMock(return_value=[])
        mock_get_service.return_value = mock_service

        # Run node
        await chunking_node(sample_state)

        # Verify ChunkingConfig parameters (800-1800 tokens, 300 overlap)
        call_args = mock_get_service.call_args
        chunk_config = call_args[1]["config"]
        assert chunk_config.max_tokens == 1800  # Feature 21.4: 3x increase
        assert chunk_config.overlap_tokens == 300  # 1/6 ratio
        assert chunk_config.strategy == "adaptive" or chunk_config.strategy.value == "adaptive"


# =============================================================================
# NODE 4: EMBEDDING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_embedding_node_success(sample_state, sample_chunks):
    """Test embedding_node generates embeddings and uploads to Qdrant."""
    # Add chunks to state
    sample_state["chunks"] = sample_chunks

    # Mock embeddings (1024D vectors for BGE-M3)
    mock_embeddings = [[0.1] * 1024, [0.2] * 1024, [0.3] * 1024]

    with (
        patch(
            "src.components.ingestion.nodes.vector_embedding.get_embedding_service"
        ) as mock_get_embedding,
        patch("src.components.ingestion.nodes.vector_embedding.QdrantClientWrapper") as mock_qdrant_class,
    ):
        # Mock embedding service
        mock_embedding_service = AsyncMock()
        mock_embedding_service.embed_batch = AsyncMock(return_value=mock_embeddings)
        mock_get_embedding.return_value = mock_embedding_service

        # Mock Qdrant client
        mock_qdrant = AsyncMock()
        mock_qdrant.create_collection = AsyncMock()
        mock_qdrant.upsert_points = AsyncMock()
        mock_qdrant_class.return_value = mock_qdrant

        # Run node
        updated_state = await embedding_node(sample_state)

        # Verify embedding success
        assert updated_state["embedding_status"] == "completed"
        assert len(updated_state["embedded_chunk_ids"]) == 3
        # Sprint 30: chunk IDs are now UUID5 generated, not from Chunk.chunk_id
        # Just verify count and UUID format, don't assert exact IDs
        assert all(isinstance(chunk_id, str) and len(chunk_id) == 36 for chunk_id in updated_state["embedded_chunk_ids"])
        assert updated_state["overall_progress"] > 0.0

        # Verify embedding service called
        mock_embedding_service.embed_batch.assert_called_once()
        texts = mock_embedding_service.embed_batch.call_args[0][0]
        assert len(texts) == 3

        # Verify Qdrant operations
        mock_qdrant.create_collection.assert_called_once()
        mock_qdrant.upsert_points.assert_called_once()


@pytest.mark.asyncio
async def test_embedding_node_no_chunks(sample_state):
    """Test embedding_node fails if no chunks available."""
    # No chunks in state
    sample_state["chunks"] = []

    # Run node (should raise IngestionError)
    with pytest.raises(IngestionError, match="No chunks to embed"):
        await embedding_node(sample_state)


@pytest.mark.asyncio
async def test_embedding_node_uses_bge_m3_1024d(sample_state, sample_chunks):
    """Test embedding_node uses BGE-M3 with 1024-dimensional vectors."""
    sample_state["chunks"] = sample_chunks

    mock_embeddings = [[0.1] * 1024, [0.2] * 1024, [0.3] * 1024]

    with (
        patch(
            "src.components.ingestion.nodes.vector_embedding.get_embedding_service"
        ) as mock_get_embedding,
        patch("src.components.ingestion.nodes.vector_embedding.QdrantClientWrapper") as mock_qdrant_class,
    ):
        mock_embedding_service = AsyncMock()
        mock_embedding_service.embed_batch = AsyncMock(return_value=mock_embeddings)
        mock_get_embedding.return_value = mock_embedding_service

        mock_qdrant = AsyncMock()
        mock_qdrant.create_collection = AsyncMock()
        mock_qdrant.upsert_points = AsyncMock()
        mock_qdrant_class.return_value = mock_qdrant

        # Run node
        await embedding_node(sample_state)

        # Verify collection created with 1024D vectors (BGE-M3)
        create_call = mock_qdrant.create_collection.call_args[1]
        assert create_call["vector_size"] == 1024  # BGE-M3 dimension


# =============================================================================
# NODE 5: GRAPH EXTRACTION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_graph_extraction_node_success(sample_state, sample_chunks):
    """Test graph_extraction_node extracts entities/relations via LightRAG."""
    # Add chunks to state (Sprint 21 Feature 21.6: enhanced format)
    sample_state["chunks"] = [{"chunk": c, "image_bboxes": []} for c in sample_chunks]

    # Mark previous nodes as completed (to reach 100% progress)
    # Progress: memory(5%) + docling(20%) + enrichment(15%) + chunking(15%) + embedding(25%) = 80%
    # graph_extraction adds 20% → 100%
    sample_state["memory_check_passed"] = True
    sample_state["docling_status"] = "completed"
    sample_state["enrichment_status"] = "completed"  # Required for progress calculation!
    sample_state["chunking_status"] = "completed"
    sample_state["embedding_status"] = "completed"

    # Mock graph statistics
    mock_graph_stats = {
        "total_entities": 42,
        "total_relations": 18,
        "total_chunks": 3,
    }

    with patch(
        "src.components.ingestion.nodes.graph_extraction.get_lightrag_wrapper_async"
    ) as mock_get_lightrag:
        # Mock LightRAG wrapper
        mock_lightrag = AsyncMock()
        # Sprint 42: Use insert_prechunked_documents instead of insert_documents_optimized
        mock_lightrag.insert_prechunked_documents = AsyncMock(return_value={"stats": mock_graph_stats})
        mock_get_lightrag.return_value = mock_lightrag

        # Run node
        updated_state = await graph_extraction_node(sample_state)

        # Verify graph extraction success
        assert updated_state["graph_status"] == "completed"
        assert updated_state["overall_progress"] == 1.0  # Final node (100%)

        # Verify LightRAG called with correct format (Sprint 42: insert_prechunked_documents)
        mock_lightrag.insert_prechunked_documents.assert_called_once()
        # Get the 'chunks' keyword argument
        lightrag_docs = mock_lightrag.insert_prechunked_documents.call_args.kwargs.get("chunks", [])
        assert len(lightrag_docs) == 3
        # Sprint 42: Prechunked format has chunk_id, text, chunk_index
        assert "chunk_id" in lightrag_docs[0]
        assert "text" in lightrag_docs[0]
        assert "chunk_index" in lightrag_docs[0]
        # Verify text contains chunk content
        assert sample_chunks[0].content in lightrag_docs[0]["text"]


@pytest.mark.asyncio
async def test_graph_extraction_node_no_chunks(sample_state):
    """Test graph_extraction_node fails if no chunks available."""
    # No chunks in state
    sample_state["chunks"] = []

    # Run node (should raise IngestionError)
    with pytest.raises(IngestionError, match="No chunks for graph extraction"):
        await graph_extraction_node(sample_state)


@pytest.mark.asyncio
async def test_graph_extraction_node_lightrag_error(sample_state, sample_chunks):
    """Test graph_extraction_node handles LightRAG errors gracefully."""
    sample_state["chunks"] = sample_chunks

    with patch(
        "src.components.ingestion.nodes.graph_extraction.get_lightrag_wrapper_async"
    ) as mock_get_lightrag:
        mock_lightrag = AsyncMock()
        # Sprint 42: Use insert_prechunked_documents instead of insert_documents_optimized
        mock_lightrag.insert_prechunked_documents = AsyncMock(
            side_effect=Exception("Neo4j connection timeout")
        )
        mock_get_lightrag.return_value = mock_lightrag

        # Run node (should raise exception)
        with pytest.raises(Exception, match="Neo4j connection timeout"):
            await graph_extraction_node(sample_state)


# =============================================================================
# INTEGRATION: FULL PIPELINE FLOW
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not installed - install with: poetry install --with dev")
async def test_full_pipeline_node_sequence(sample_state, sample_chunks):
    """Test all 5 nodes execute in sequence with state updates."""
    from src.components.ingestion.docling_client import DoclingParsedDocument

    # Mock parsed document
    mock_parsed = DoclingParsedDocument(
        text="Document content for full pipeline test.",
        metadata={"pages": 1},
        tables=[],
        images=[],
        layout={},
        parse_time_ms=500,
    )

    mock_embeddings = [[0.1] * 1024] * 3
    mock_graph_stats = {"total_entities": 10, "total_relations": 5, "total_chunks": 3}

    with (
        patch("psutil.virtual_memory") as mock_memory,
        patch("subprocess.run") as mock_nvidia_smi,
        patch(
            "src.components.ingestion.nodes.document_parsers.DoclingContainerClient"
        ) as mock_docling_class,
        patch("src.components.ingestion.nodes.adaptive_chunking.get_chunking_service") as mock_get_chunking,
        patch(
            "src.components.ingestion.nodes.vector_embedding.get_embedding_service"
        ) as mock_get_embedding,
        patch("src.components.ingestion.nodes.vector_embedding.QdrantClientWrapper") as mock_qdrant_class,
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_lightrag_wrapper_async"
        ) as mock_get_lightrag,
    ):
        # Mock all services
        mock_memory.return_value = MagicMock(
            used=3 * 1024 * 1024 * 1024, available=6 * 1024 * 1024 * 1024
        )
        mock_nvidia_smi.return_value = MagicMock(stdout="3072\n")

        mock_docling = AsyncMock()
        mock_docling.parse_document = AsyncMock(return_value=mock_parsed)
        mock_docling_class.return_value = mock_docling

        mock_chunking_service = Mock()
        mock_chunking_service.chunk_document = AsyncMock(return_value=sample_chunks)
        mock_get_chunking.return_value = mock_chunking_service

        mock_embedding_service = AsyncMock()
        mock_embedding_service.embed_batch = AsyncMock(return_value=mock_embeddings)
        mock_get_embedding.return_value = mock_embedding_service

        mock_qdrant = AsyncMock()
        mock_qdrant.create_collection = AsyncMock()
        mock_qdrant.upsert_points = AsyncMock()
        mock_qdrant_class.return_value = mock_qdrant

        mock_lightrag = AsyncMock()
        mock_lightrag.insert_documents_optimized = AsyncMock(return_value=mock_graph_stats)
        mock_get_lightrag.return_value = mock_lightrag

        # Execute all 5 nodes sequentially
        state = sample_state

        # Node 1: Memory Check
        state = await memory_check_node(state)
        assert state["memory_check_passed"] is True
        assert state["overall_progress"] == pytest.approx(0.05, rel=0.01)  # 5%

        # Node 2: Docling Parse
        state = await docling_parse_node(state)
        assert state["docling_status"] == "completed"
        assert len(state["parsed_content"]) > 0
        # Progress: memory(5%) + docling(20%) = 25% (enrichment not yet run)
        assert state["overall_progress"] == pytest.approx(0.25, rel=0.01)  # 25%

        # Node 3: Chunking
        # Sprint 32: Remove document to trigger legacy chunking path (test uses sample_chunks mock)
        state["document"] = None
        state = await chunking_node(state)
        assert state["chunking_status"] == "completed"
        assert len(state["chunks"]) == 3
        # Progress: memory(5%) + docling(20%) + chunking(15%) = 40%
        assert state["overall_progress"] == pytest.approx(0.40, rel=0.01)  # 40%

        # Node 4: Embedding
        state = await embedding_node(state)
        assert state["embedding_status"] == "completed"
        assert len(state["embedded_chunk_ids"]) == 3
        # Progress: memory(5%) + docling(20%) + chunking(15%) + embedding(25%) = 65%
        assert state["overall_progress"] == pytest.approx(0.65, rel=0.01)  # 65%

        # Node 5: Graph Extraction
        state = await graph_extraction_node(state)
        assert state["graph_status"] == "completed"
        # Progress: memory(5%) + docling(20%) + chunking(15%) + embedding(25%) + graph(20%) = 85%
        # Note: enrichment(15%) was skipped, so max is 85% not 100%
        assert state["overall_progress"] == pytest.approx(0.85, rel=0.01)  # 85%

        # Verify no errors
        assert len(state.get("errors", [])) == 0


# =============================================================================
# ERROR RECOVERY TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_node_error_accumulation(sample_state):
    """Test errors accumulate in state without aborting pipeline."""
    from src.components.ingestion.ingestion_state import add_error

    # Add multiple errors
    add_error(sample_state, "docling", "Timeout error", "error")
    add_error(sample_state, "chunking", "Empty content warning", "warning")

    # Verify errors accumulated
    assert len(sample_state["errors"]) == 2
    assert sample_state["errors"][0]["node"] == "docling"
    assert sample_state["errors"][0]["type"] == "error"
    assert sample_state["errors"][1]["node"] == "chunking"
    assert sample_state["errors"][1]["type"] == "warning"


@pytest.mark.asyncio
async def test_node_sets_failed_status_on_error(sample_state):
    """Test node sets status to 'failed' when exception occurs."""
    # Point to non-existent file
    sample_state["document_path"] = "/nonexistent/file.pdf"

    # Run docling_parse_node (should fail)
    try:
        await docling_parse_node(sample_state)
    except:
        pass  # Expected to fail

    # Verify status set to failed
    assert sample_state["docling_status"] == "failed"
    assert len(sample_state["errors"]) > 0
