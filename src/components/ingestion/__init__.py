"""Ingestion Pipeline Components - Sprint 21.

This module provides the new container-based document ingestion architecture:

Feature 21.1: Docling CUDA Docker Container
  - DoclingContainerClient: HTTP client for Docling container
  - GPU-accelerated parsing with OCR, table extraction, layout analysis

Feature 21.2: LangGraph Ingestion State Machine
  - 5-node sequential pipeline (memory-optimized)
  - IngestionState: TypedDict with 30+ tracking fields
  - Nodes: memory_check, docling, chunking, embedding, graph_extraction

Feature 21.3: Batch Processing + Progress Monitoring
  - BatchOrchestrator: Process 10 docs/batch with container lifecycle
  - SSE streaming for React UI real-time progress
  - Error handling with partial success

Architecture:
  Docling Container → DoclingClient → LangGraph Pipeline → Qdrant + Neo4j
                                              ↓
                                      ChunkingService (1800 tokens)
                                              ↓
                                      EmbeddingService (BGE-M3)
                                              ↓
                                      ThreePhaseExtractor (SpaCy + Gemma)

Usage:
    >>> from src.components.ingestion import run_ingestion_pipeline
    >>>
    >>> # Single document (blocking)
    >>> final_state = await run_ingestion_pipeline(
    ...     document_path="/data/doc.pdf",
    ...     document_id="doc_001",
    ...     batch_id="batch_001",
    ... )
    >>>
    >>> # Streaming (SSE for React UI)
    >>> async for update in run_ingestion_pipeline_streaming(...):
    ...     print(f"[{update['node']}] {update['progress']:.0%}")
    >>>
    >>> # Batch processing
    >>> async for result in run_batch_ingestion(doc_paths, "batch_001"):
    ...     print(f"Document {result['document_id']}: {result['batch_progress']:.0%}")
"""

from src.components.ingestion.docling_client import (
    DoclingContainerClient,
    DoclingParsedDocument,
)
from src.components.ingestion.ingestion_state import (
    IngestionState,
    add_error,
    calculate_progress,
    create_initial_state,
    increment_retry,
    should_retry,
)
from src.components.ingestion.langgraph_pipeline import (
    create_ingestion_graph,
    run_batch_ingestion,
    run_ingestion_pipeline,
    run_ingestion_pipeline_streaming,
)

__all__ = [
    # Docling Client (Feature 21.1)
    "DoclingContainerClient",
    "DoclingParsedDocument",
    # State Management (Feature 21.2)
    "IngestionState",
    "create_initial_state",
    "calculate_progress",
    "add_error",
    "should_retry",
    "increment_retry",
    # LangGraph Pipeline (Feature 21.2)
    "create_ingestion_graph",
    "run_ingestion_pipeline",
    "run_ingestion_pipeline_streaming",
    # Batch Processing (Feature 21.3 preview)
    "run_batch_ingestion",
]
