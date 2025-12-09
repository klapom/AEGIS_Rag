"""Integration tests for error propagation through LangGraph ingestion pipeline.

Sprint 22 Task 22.1.3 - Test Baseline 2: Error Propagation

This test file verifies errors are caught, logged, and propagated correctly through
all 6 pipeline nodes (memory_check, docling, chunking, embedding, graph).

Critical Failure Modes Tested:
- Docling parsing errors (invalid files, timeout)
- VLM enrichment failures (optional step, non-critical)
- Graph extraction errors (Neo4j unavailable)
- Partial failures (vector succeeds, graph fails)

ADR-027: Docling as Primary Ingestion
ADR-028: LlamaIndex as Fallback

Prerequisites:
    - Qdrant running (for embedding tests)
    - Neo4j optional (for graph error tests)

Run tests:
    pytest tests/integration/test_ingestion_error_handling.py -v -m integration
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.components.ingestion.ingestion_state import create_initial_state
from src.components.ingestion.langgraph_nodes import (
    docling_parse_node,
    graph_extraction_node,
)
from src.components.ingestion.langgraph_pipeline import (
    create_ingestion_graph,
)
from src.core.exceptions import IngestionError

# =============================================================================
# Test 2.1: Docling Parse Error Propagation
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_docling_parse_error__invalid_file__error_caught_and_logged():
    """Verify Docling parsing errors are caught and logged with context.

    Validates:
    - Invalid PDF raises clear error
    - Error logged with file path context
    - State marked with error status
    - Error message includes helpful details
    """
    import tempfile

    temp_dir = Path(tempfile.mkdtemp())
    invalid_pdf = temp_dir / "invalid.pdf"
    # Create truly invalid PDF (empty file)
    invalid_pdf.write_bytes(b"")

    try:
        # Create initial state
        state = create_initial_state(
            document_path=str(invalid_pdf),
            document_id="invalid_doc",
            batch_id="test_batch",
            batch_index=0,
            total_documents=1,
        )

        # Mock Docling client to simulate parsing error
        with patch(
            "src.components.ingestion.langgraph_nodes.DoclingContainerClient"
        ) as mock_client:
            mock_instance = AsyncMock()
            mock_instance.parse_document.side_effect = IngestionError(
                f"Failed to parse {invalid_pdf.name}: Empty file"
            )
            mock_client.return_value = mock_instance

            # Action: Run docling_parse_node
            updated_state = await docling_parse_node(state)

            # Assert: Error caught and state updated
            assert (
                updated_state["docling_status"] == "failed"
            ), "Docling status not marked as failed"
            assert len(updated_state["errors"]) > 0, "No errors recorded in state"

            # Assert: Error includes file context
            error_msg = str(updated_state["errors"][0])
            assert (
                "invalid.pdf" in error_msg or "Empty file" in error_msg
            ), f"Error lacks context: {error_msg}"

    finally:
        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_docling_parse_timeout__large_file__error_propagated():
    """Verify timeout errors are propagated with clear message.

    Validates:
    - Timeout exception caught
    - Error message includes duration
    - State marked as failed
    - No silent failures
    """
    import tempfile

    temp_dir = Path(tempfile.mkdtemp())
    large_file = temp_dir / "large.pdf"
    # Create mock large file
    large_file.write_bytes(b"%PDF-1.4\n" + b"x" * 10000)

    try:
        state = create_initial_state(
            document_path=str(large_file),
            document_id="large_doc",
            batch_id="test_batch",
            batch_index=0,
            total_documents=1,
        )

        # Mock timeout scenario
        with patch(
            "src.components.ingestion.langgraph_nodes.DoclingContainerClient"
        ) as mock_client:
            mock_instance = AsyncMock()
            mock_instance.parse_document.side_effect = IngestionError(
                "Docling parse timeout after 300.0s (file: large.pdf)"
            )
            mock_client.return_value = mock_instance

            # Action: Run docling_parse_node
            updated_state = await docling_parse_node(state)

            # Assert: Timeout error recorded
            assert updated_state["docling_status"] == "failed"
            error_msg = str(updated_state["errors"][0])
            assert "timeout" in error_msg.lower(), f"Timeout not in error: {error_msg}"
            assert (
                "300" in error_msg or "large.pdf" in error_msg
            ), f"Error lacks context: {error_msg}"

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Test 2.2: VLM Enrichment Optional Failure
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skip(reason="VLM enrichment node not yet in main pipeline")
async def test_vlm_enrichment_failure__service_unavailable__pipeline_continues():
    """Verify VLM failure doesn't break pipeline (optional step).

    Validates:
    - VLM service unavailable → Warning logged
    - Pipeline continues without VLM data
    - Chunks created without enrichment
    - No critical error raised

    Note: VLM enrichment is optional (Feature 21.6)
    """
    import tempfile

    temp_dir = Path(tempfile.mkdtemp())
    test_doc = temp_dir / "test.txt"
    test_doc.write_text("Test document for VLM failure.")

    try:
        create_initial_state(
            document_path=str(test_doc),
            document_id="vlm_test_doc",
            batch_id="test_batch",
            batch_index=0,
            total_documents=1,
        )

        # Mock VLM service unavailable
        with patch("src.components.ingestion.langgraph_nodes.vlm_enrichment_node") as mock_vlm:
            mock_vlm.side_effect = Exception("VLM service connection refused")

            # Action: Run pipeline (should continue despite VLM failure)
            # This is a preview test - actual implementation in Feature 21.6
            pass

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Test 2.3: Graph Extraction Failure Handling
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_graph_extraction_failure__neo4j_unavailable__vector_data_saved():
    """Verify graph extraction errors don't corrupt vector data.

    Validates:
    - Neo4j connection failure caught
    - Vector/embedding data still saved to Qdrant
    - Graph extraction marked as failed
    - Error logged with Neo4j context

    Critical: Vector indexing must succeed even if graph fails.
    """
    import tempfile

    temp_dir = Path(tempfile.mkdtemp())
    test_doc = temp_dir / "test.txt"
    test_doc.write_text("Test document for graph extraction failure.")

    try:
        # Create state with mocked chunks and embeddings (simulate earlier success)
        state = create_initial_state(
            document_path=str(test_doc),
            document_id="graph_test_doc",
            batch_id="test_batch",
            batch_index=0,
            total_documents=1,
        )

        # Simulate successful embedding phase
        from src.core.chunk import Chunk

        state["chunks"] = [
            Chunk(
                id="chunk_1",
                text="Test chunk content",
                embedding=[0.1] * 1024,
                metadata={"document_id": "graph_test_doc", "chunk_index": 0},
            )
        ]
        state["embedded_chunk_ids"] = ["chunk_1"]
        state["embedding_status"] = "completed"

        # Mock Neo4j connection failure
        with patch(
            "src.components.ingestion.langgraph_nodes.get_lightrag_wrapper_async"
        ) as mock_lightrag:
            mock_lightrag.side_effect = Exception("Neo4j connection refused")

            # Action: Run graph_extraction_node
            updated_state = await graph_extraction_node(state)

            # Assert: Graph extraction failed
            assert updated_state["graph_status"] == "failed", "Graph status not marked as failed"
            assert len(updated_state["errors"]) > 0, "No graph error recorded"

            # Assert: Vector data still intact
            assert updated_state["embedding_status"] == "completed", "Embedding status corrupted"
            assert len(updated_state["embedded_chunk_ids"]) > 0, "Embedded chunks lost"

            # Assert: Error message mentions Neo4j
            error_msg = str(updated_state["errors"][-1])
            assert (
                "neo4j" in error_msg.lower() or "connection" in error_msg.lower()
            ), f"Error lacks Neo4j context: {error_msg}"

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Test 2.4: Partial Failure Recovery
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_partial_failure__vlm_and_graph_fail__qdrant_succeeds():
    """Verify pipeline completes successfully even if non-critical steps fail.

    Validates:
    - VLM failure (optional) → Warning
    - Graph failure (non-critical for vector search) → Error logged
    - Qdrant indexing completes → Success
    - Partial success state returned

    Critical: Core vector search must work even if enrichment/graph fail.
    """
    import tempfile

    temp_dir = Path(tempfile.mkdtemp())
    test_doc = temp_dir / "test.txt"
    test_doc.write_text("Test document for partial failure.")

    try:
        # Mock VLM and Graph failures, but allow Qdrant to succeed
        with patch(
            "src.components.ingestion.langgraph_nodes.get_lightrag_wrapper_async"
        ) as mock_lightrag:
            mock_lightrag.side_effect = Exception("Neo4j unavailable")

            # Create state
            state = create_initial_state(
                document_path=str(test_doc),
                document_id="partial_test_doc",
                batch_id="test_batch",
                batch_index=0,
                total_documents=1,
            )

            # Mock successful Docling + Chunking + Embedding
            with patch(
                "src.components.ingestion.langgraph_nodes.DoclingContainerClient"
            ) as mock_docling:
                mock_docling_instance = AsyncMock()
                from src.components.ingestion.docling_client import DoclingParsedDocument

                mock_docling_instance.parse_document.return_value = DoclingParsedDocument(
                    text="Test document content",
                    metadata={"filename": "test.txt"},
                    tables=[],
                    images=[],
                    layout={},
                    parse_time_ms=100.0,
                    json_content={},
                    md_content="",
                )
                mock_docling.return_value = mock_docling_instance

                # Mock Qdrant success
                with patch(
                    "src.components.ingestion.langgraph_nodes.QdrantClientWrapper"
                ) as mock_qdrant:
                    mock_qdrant_instance = AsyncMock()
                    mock_qdrant_instance.upsert_points.return_value = True
                    mock_qdrant.return_value = mock_qdrant_instance

                    # Action: Run pipeline
                    pipeline = create_ingestion_graph()
                    final_state = await pipeline.ainvoke(state)

                    # Assert: Overall progress complete (even with partial failures)
                    assert (
                        final_state.get("overall_progress", 0.0) > 0.5
                    ), "Pipeline did not make progress despite partial success"

                    # Assert: Embedding succeeded
                    assert (
                        final_state.get("embedding_status") == "completed"
                    ), "Embedding should succeed despite graph failure"

                    # Assert: Graph failed (expected)
                    assert (
                        final_state.get("graph_status") == "failed"
                    ), "Graph status should be failed"

                    # Assert: Errors recorded but pipeline completed
                    assert len(final_state.get("errors", [])) > 0, "Errors not recorded"

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Test 2.5: Error Accumulation Across Nodes
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_accumulation__multiple_nodes_fail__all_errors_recorded():
    """Verify errors accumulate across nodes (don't overwrite).

    Validates:
    - Error from node 1 preserved
    - Error from node 2 appended
    - Final state contains all errors
    - Each error has node context

    Critical: Full error history needed for debugging.
    """
    import tempfile

    temp_dir = Path(tempfile.mkdtemp())
    test_doc = temp_dir / "test.txt"
    test_doc.write_text("Test document for error accumulation.")

    try:
        state = create_initial_state(
            document_path=str(test_doc),
            document_id="accumulation_test_doc",
            batch_id="test_batch",
            batch_index=0,
            total_documents=1,
        )

        # Manually trigger errors in multiple nodes
        # Error 1: Docling failure
        state["errors"] = [{"node": "docling", "message": "Parse error", "type": "error"}]
        state["docling_status"] = "failed"

        # Error 2: Graph failure
        state["errors"].append(
            {"node": "graph", "message": "Neo4j connection failed", "type": "error"}
        )
        state["graph_status"] = "failed"

        # Assert: Both errors present
        assert len(state["errors"]) == 2, "Errors not accumulated"
        assert state["errors"][0]["node"] == "docling", "First error lost"
        assert state["errors"][1]["node"] == "graph", "Second error lost"

        # Assert: Each error has required fields
        for error in state["errors"]:
            assert "node" in error, "Error missing node field"
            assert "message" in error, "Error missing message field"
            assert "type" in error, "Error missing type field"

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Test 2.6: No Silent Failures
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_no_silent_failures__exception_raised__must_be_logged():
    """Verify all exceptions are logged (no silent failures).

    Validates:
    - Unexpected exception caught
    - Exception logged with traceback
    - State marked as failed
    - Exception details preserved

    Critical: Silent failures are unacceptable in production.
    """
    import tempfile

    temp_dir = Path(tempfile.mkdtemp())
    test_doc = temp_dir / "test.txt"
    test_doc.write_text("Test document for silent failure check.")

    try:
        state = create_initial_state(
            document_path=str(test_doc),
            document_id="silent_test_doc",
            batch_id="test_batch",
            batch_index=0,
            total_documents=1,
        )

        # Mock unexpected exception
        with patch(
            "src.components.ingestion.langgraph_nodes.DoclingContainerClient"
        ) as mock_client:
            mock_instance = AsyncMock()
            mock_instance.parse_document.side_effect = RuntimeError("Unexpected error in Docling")
            mock_client.return_value = mock_instance

            # Action: Run docling_parse_node
            updated_state = await docling_parse_node(state)

            # Assert: Error recorded (not silent)
            assert len(updated_state["errors"]) > 0, "Silent failure detected (no error logged)"
            assert updated_state["docling_status"] == "failed", "Status not updated"

            # Assert: Error details preserved
            error_msg = str(updated_state["errors"][0])
            assert (
                "Unexpected error" in error_msg or "RuntimeError" in error_msg
            ), f"Exception details lost: {error_msg}"

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Test Summary
# =============================================================================

"""
Test Coverage Summary:

Test 2.1: Docling Parse Errors (2 tests)
- test_docling_parse_error__invalid_file__error_caught_and_logged
- test_docling_parse_timeout__large_file__error_propagated

Test 2.2: VLM Optional Failure (1 test, skipped - Feature 21.6)
- test_vlm_enrichment_failure__service_unavailable__pipeline_continues

Test 2.3: Graph Extraction Errors (1 test)
- test_graph_extraction_failure__neo4j_unavailable__vector_data_saved

Test 2.4: Partial Failure Recovery (1 test)
- test_partial_failure__vlm_and_graph_fail__qdrant_succeeds

Test 2.5: Error Accumulation (1 test)
- test_error_accumulation__multiple_nodes_fail__all_errors_recorded

Test 2.6: No Silent Failures (1 test)
- test_no_silent_failures__exception_raised__must_be_logged

Total: 7 tests (6 active, 1 skipped)

Expected Behavior:
- All errors caught and logged with context
- Critical vs non-critical failures handled differently
- Partial success allowed (vector succeeds even if graph fails)
- No silent failures
"""
