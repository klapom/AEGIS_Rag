"""Ingestion Pipeline Components - Sprint 21.

This module provides the new container-based document ingestion architecture:

Feature 21.1: Docling CUDA Docker Container
  - DoclingContainerClient: HTTP client for Docling container
  - GPU-accelerated parsing with OCR, table extraction, layout analysis

Feature 21.2: LangGraph Ingestion State Machine
  - 5-node sequential pipeline (memory-optimized)
  - IngestionState: TypedDict with 15+ tracking fields
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
"""

from src.components.ingestion.docling_client import DoclingContainerClient

__all__ = [
    "DoclingContainerClient",
]
