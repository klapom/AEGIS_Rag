"""LangGraph Ingestion Pipeline Compiler - Sprint 21 Feature 21.2.

This module creates the LangGraph StateGraph that connects the 5 ingestion nodes
into a sequential pipeline with error handling and progress tracking.

Pipeline Flow:
  START
    ↓
  memory_check_node (5% progress)
    ↓
  docling_parse_node (30% progress)
    ↓
  chunking_node (45% progress)
    ↓
  embedding_node (75% progress)
    ↓
  graph_extraction_node (100% progress)
    ↓
  END

Architecture:
- Sequential execution (one node at a time for memory optimization)
- State passed through all nodes (IngestionState TypedDict)
- Error accumulation (continue on non-fatal errors)
- Progress tracking (0.0 to 1.0)
- Container lifecycle management (start/stop between stages)

Memory Management:
- 4.4GB RAM constraint → Sequential execution (no parallel stages)
- 6GB VRAM constraint → Container start/stop to free memory
- VRAM leak detection → Auto-restart if >5.5GB

Usage:
    >>> from src.components.ingestion.langgraph_pipeline import create_ingestion_graph
    >>> from src.components.ingestion.ingestion_state import create_initial_state
    >>>
    >>> # Create pipeline
    >>> pipeline = create_ingestion_graph()
    >>>
    >>> # Create initial state
    >>> state = create_initial_state(
    ...     document_path="/data/doc.pdf",
    ...     document_id="doc_001",
    ...     batch_id="batch_001",
    ...     batch_index=0,
    ...     total_documents=10,
    ... )
    >>>
    >>> # Execute pipeline (streaming)
    >>> async for event in pipeline.astream(state):
    ...     node_name = list(event.keys())[0]
    ...     updated_state = event[node_name]
    ...     print(f"Node: {node_name}, Progress: {updated_state['overall_progress']:.0%}")
    >>>
    >>> # Execute pipeline (blocking)
    >>> final_state = await pipeline.ainvoke(state)
    >>> print(f"Status: {final_state['graph_status']}")
    >>> print(f"Chunks: {len(final_state['chunks'])}")

Error Handling:
- Errors accumulate in state["errors"] (don't abort pipeline)
- Each node sets its status to "failed" on error
- Retry logic via state["retry_count"] and state["max_retries"]
- Final state includes all errors for diagnostics

Example with Error Handling:
    >>> state = create_initial_state(...)
    >>> final_state = await pipeline.ainvoke(state)
    >>>
    >>> # Check for errors
    >>> if final_state["errors"]:
    ...     for error in final_state["errors"]:
    ...         print(f"[{error['type']}] {error['node']}: {error['message']}")
    >>>
    >>> # Check node status
    >>> if final_state["docling_status"] == "failed":
    ...     print("Docling parsing failed!")
    >>> if final_state["graph_status"] == "completed":
    ...     print(f"Graph extraction succeeded: {len(final_state['entities'])} entities")
"""

import structlog
from langgraph.graph import END, StateGraph

from src.components.ingestion.ingestion_state import IngestionState
from src.components.ingestion.langgraph_nodes import (
    chunking_node,
    docling_parse_node,
    embedding_node,
    graph_extraction_node,
    memory_check_node,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# GRAPH COMPILER
# =============================================================================


def create_ingestion_graph() -> StateGraph:
    """Create LangGraph StateGraph for document ingestion pipeline.

    Creates a sequential pipeline with 5 nodes:
    1. memory_check → Verify RAM/VRAM available
    2. docling → Parse document with Docling container
    3. chunking → Split into 1800-token chunks
    4. embedding → Generate BGE-M3 vectors → Qdrant
    5. graph → Extract entities/relations → Neo4j

    Returns:
        Compiled StateGraph ready for execution

    Example:
        >>> pipeline = create_ingestion_graph()
        >>> state = create_initial_state(...)
        >>> final_state = await pipeline.ainvoke(state)

    Note:
        - Sequential execution (memory-optimized)
        - State passed through all nodes
        - Error handling in each node
        - Progress tracking automatic
    """
    logger.info("ingestion_graph_create_start")

    # Create graph with IngestionState schema
    graph = StateGraph(IngestionState)

    # Add nodes (5 stages)
    graph.add_node("memory_check", memory_check_node)
    graph.add_node("docling", docling_parse_node)
    graph.add_node("chunking", chunking_node)
    graph.add_node("embedding", embedding_node)
    graph.add_node("graph", graph_extraction_node)

    # Define edges (sequential flow)
    # START → memory_check → docling → chunking → embedding → graph → END
    graph.set_entry_point("memory_check")
    graph.add_edge("memory_check", "docling")
    graph.add_edge("docling", "chunking")
    graph.add_edge("chunking", "embedding")
    graph.add_edge("embedding", "graph")
    graph.add_edge("graph", END)

    # Compile graph
    compiled_graph = graph.compile()

    logger.info(
        "ingestion_graph_created",
        nodes=["memory_check", "docling", "chunking", "embedding", "graph"],
        flow="sequential",
    )

    return compiled_graph


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


async def run_ingestion_pipeline(
    document_path: str,
    document_id: str,
    batch_id: str,
    batch_index: int = 0,
    total_documents: int = 1,
    max_retries: int = 3,
) -> IngestionState:
    """Run ingestion pipeline for a single document (convenience function).

    This is a high-level convenience function that:
    1. Creates initial state
    2. Creates pipeline graph
    3. Executes pipeline (blocking)
    4. Returns final state

    Args:
        document_path: Absolute path to document file
        document_id: Unique document identifier (SHA-256 hash)
        batch_id: Batch identifier for grouping
        batch_index: Index in batch (0-based)
        total_documents: Total documents in batch
        max_retries: Maximum retries before skipping (default: 3)

    Returns:
        Final IngestionState with all results and errors

    Raises:
        IngestionError: If any critical error occurs (propagated from nodes)

    Example:
        >>> final_state = await run_ingestion_pipeline(
        ...     document_path="/data/doc.pdf",
        ...     document_id="doc_001",
        ...     batch_id="batch_001",
        ...     batch_index=0,
        ...     total_documents=10,
        ... )
        >>> print(f"Progress: {final_state['overall_progress']:.0%}")
        >>> print(f"Chunks: {len(final_state['chunks'])}")
        >>> print(f"Errors: {len(final_state['errors'])}")

    Note:
        - This is a blocking call (use run_ingestion_pipeline_streaming for SSE)
        - Errors accumulate in state["errors"]
        - Check node status fields to identify failures
        - Container lifecycle managed automatically
    """
    from src.components.ingestion.ingestion_state import create_initial_state

    logger.info(
        "run_ingestion_pipeline_start",
        document_id=document_id,
        batch_id=batch_id,
        batch_index=batch_index,
    )

    # Create initial state
    state = create_initial_state(
        document_path=document_path,
        document_id=document_id,
        batch_id=batch_id,
        batch_index=batch_index,
        total_documents=total_documents,
        max_retries=max_retries,
    )

    # Create and execute pipeline
    pipeline = create_ingestion_graph()
    final_state = await pipeline.ainvoke(state)

    logger.info(
        "run_ingestion_pipeline_complete",
        document_id=document_id,
        overall_progress=final_state.get("overall_progress", 0.0),
        error_count=len(final_state.get("errors", [])),
        chunks_created=len(final_state.get("chunks", [])),
    )

    return final_state


async def run_ingestion_pipeline_streaming(
    document_path: str,
    document_id: str,
    batch_id: str,
    batch_index: int = 0,
    total_documents: int = 1,
    max_retries: int = 3,
):
    """Run ingestion pipeline with streaming progress updates (for SSE).

    This generator yields state updates after each node completes,
    allowing real-time progress monitoring via Server-Sent Events (SSE).

    Args:
        document_path: Absolute path to document file
        document_id: Unique document identifier
        batch_id: Batch identifier
        batch_index: Index in batch (0-based)
        total_documents: Total documents in batch
        max_retries: Maximum retries (default: 3)

    Yields:
        dict: {"node": str, "state": IngestionState, "progress": float}
              after each node completion

    Example:
        >>> async for update in run_ingestion_pipeline_streaming(...):
        ...     node = update["node"]
        ...     progress = update["progress"]
        ...     state = update["state"]
        ...     print(f"[{node}] Progress: {progress:.0%}")
        ...
        ...     # Send SSE to React UI
        ...     await send_sse({
        ...         "event": "ingestion_progress",
        ...         "data": {
        ...             "node": node,
        ...             "progress": progress,
        ...             "document_id": state["document_id"],
        ...         }
        ...     })

    Integration with FastAPI SSE:
        ```python
        @app.get("/api/ingestion/{document_id}/stream")
        async def stream_ingestion_progress(document_id: str):
            async def event_generator():
                async for update in run_ingestion_pipeline_streaming(...):
                    yield {
                        "event": "progress",
                        "data": json.dumps({
                            "node": update["node"],
                            "progress": update["progress"],
                            "status": update["state"].get(f"{update['node']}_status"),
                        })
                    }
            return EventSourceResponse(event_generator())
        ```

    Note:
        - Yields after EACH node (5 yields total)
        - Final yield contains complete state
        - Errors still accumulate (don't stop streaming)
        - Perfect for React UI progress bars
    """
    from src.components.ingestion.ingestion_state import create_initial_state

    logger.info(
        "run_ingestion_pipeline_streaming_start",
        document_id=document_id,
        batch_id=batch_id,
    )

    # Create initial state
    state = create_initial_state(
        document_path=document_path,
        document_id=document_id,
        batch_id=batch_id,
        batch_index=batch_index,
        total_documents=total_documents,
        max_retries=max_retries,
    )

    # Create pipeline
    pipeline = create_ingestion_graph()

    # Stream state updates (astream yields after each node)
    async for event in pipeline.astream(state):
        # Extract node name and updated state
        node_name = list(event.keys())[0]
        updated_state = event[node_name]

        # Yield progress update
        yield {
            "node": node_name,
            "state": updated_state,
            "progress": updated_state.get("overall_progress", 0.0),
            "timestamp": updated_state.get("end_time", 0.0),
        }

        logger.debug(
            "ingestion_pipeline_node_complete",
            document_id=document_id,
            node=node_name,
            progress=updated_state.get("overall_progress", 0.0),
        )

    logger.info(
        "run_ingestion_pipeline_streaming_complete",
        document_id=document_id,
    )


# =============================================================================
# BATCH PROCESSING (Preview for Feature 21.3)
# =============================================================================


async def run_batch_ingestion(
    document_paths: list[str],
    batch_id: str,
    max_retries: int = 3,
):
    """Run ingestion pipeline for multiple documents (batch processing).

    This is a PREVIEW for Feature 21.3 (Batch Processing).
    Full implementation with SSE streaming and error recovery will be added in 21.3.

    Args:
        document_paths: List of absolute paths to documents
        batch_id: Batch identifier for grouping
        max_retries: Maximum retries per document (default: 3)

    Yields:
        dict: {"document_id": str, "state": IngestionState, "batch_progress": float}

    Example:
        >>> doc_paths = ["/data/doc1.pdf", "/data/doc2.pdf", "/data/doc3.pdf"]
        >>> async for result in run_batch_ingestion(doc_paths, "batch_001"):
        ...     print(f"Document {result['document_id']}: {result['state']['overall_progress']:.0%}")
        ...     print(f"Batch progress: {result['batch_progress']:.0%}")

    Note:
        - Sequential processing (one document at a time for memory optimization)
        - Container restarted between documents (memory leak mitigation)
        - Batch progress = (completed_docs / total_docs)
        - Full Feature 21.3 adds: error recovery, partial success handling, React UI
    """
    import hashlib
    from pathlib import Path

    total_documents = len(document_paths)

    logger.info(
        "run_batch_ingestion_start",
        batch_id=batch_id,
        total_documents=total_documents,
    )

    for batch_index, doc_path in enumerate(document_paths):
        # Generate document ID (SHA-256 hash of path)
        document_id = hashlib.sha256(doc_path.encode()).hexdigest()[:16]

        logger.info(
            "batch_document_start",
            batch_id=batch_id,
            document_id=document_id,
            batch_index=batch_index,
            document_path=doc_path,
        )

        try:
            # Run pipeline for single document
            final_state = await run_ingestion_pipeline(
                document_path=doc_path,
                document_id=document_id,
                batch_id=batch_id,
                batch_index=batch_index,
                total_documents=total_documents,
                max_retries=max_retries,
            )

            # Calculate batch progress
            batch_progress = (batch_index + 1) / total_documents

            # Yield result
            yield {
                "document_id": document_id,
                "document_path": doc_path,
                "state": final_state,
                "batch_index": batch_index,
                "batch_progress": batch_progress,
                "success": final_state.get("graph_status") == "completed",
            }

            logger.info(
                "batch_document_complete",
                batch_id=batch_id,
                document_id=document_id,
                batch_progress=batch_progress,
                errors=len(final_state.get("errors", [])),
            )

        except Exception as e:
            logger.error(
                "batch_document_failed",
                batch_id=batch_id,
                document_id=document_id,
                error=str(e),
            )

            # Yield error result (continue with next document)
            yield {
                "document_id": document_id,
                "document_path": doc_path,
                "state": None,
                "batch_index": batch_index,
                "batch_progress": (batch_index + 1) / total_documents,
                "success": False,
                "error": str(e),
            }

    logger.info("run_batch_ingestion_complete", batch_id=batch_id)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "create_ingestion_graph",
    "run_ingestion_pipeline",
    "run_ingestion_pipeline_streaming",
    "run_batch_ingestion",
]
