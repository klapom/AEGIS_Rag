"""Unified document ingestion pipeline for all AEGIS RAG components.

============================================================================
⚠️ DEPRECATED: Sprint 21 - This module will be replaced by LangGraph pipeline
============================================================================
REASON: Parallel execution (asyncio.gather) incompatible with:
  - Memory constraints (4.4GB RAM limit, RTX 3060 6GB VRAM)
  - Container lifecycle management (Docling start/stop between batches)
  - SSE progress streaming (React UI real-time updates)
  - Sequential stage execution (memory-optimized pipeline)

REPLACEMENT: Feature 21.2 - LangGraph Ingestion State Machine
  from src.components.ingestion.langgraph_pipeline import create_ingestion_graph

  pipeline = create_ingestion_graph()
  async for event in pipeline.astream(initial_state):
      node_name = list(event.keys())[0]
      state = event[node_name]
      # Stream progress to React UI via SSE
      await send_sse({"node": node_name, "progress": state["overall_progress"]})

MIGRATION STATUS: DO NOT USE for new code
REMOVAL: Sprint 22 (after LangGraph migration complete)
============================================================================

Indexes documents to:
- Qdrant (vector search)
- BM25 (keyword search)
- Neo4j (knowledge graph via LightRAG)
"""

import asyncio
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
from src.components.vector_search.ingestion import DocumentIngestionPipeline

logger = structlog.get_logger(__name__)


class IngestionResult(BaseModel):
    """Result of unified ingestion."""

    total_documents: int = Field(description="Total documents processed")
    qdrant_indexed: int = Field(description="Documents indexed to Qdrant")
    bm25_indexed: int = Field(description="Documents indexed to BM25")
    neo4j_entities: int = Field(description="Entities extracted to Neo4j")
    neo4j_relationships: int = Field(description="Relationships extracted to Neo4j")
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
    duration_seconds: float = Field(description="Total ingestion duration")


class UnifiedIngestionPipeline:
    """Single pipeline that indexes documents to all AEGIS RAG systems.

    Features:
    - Parallel indexing to Qdrant, BM25, and Neo4j
    - Shared embedding service (no duplicate embeddings)
    - Progress tracking for all systems
    - Error handling and partial success
    """

    def __init__(
        self,
        allowed_base_path: str | None = None,
        enable_qdrant: bool = True,
        enable_neo4j: bool = True,
    ):
        """Initialize unified ingestion pipeline.

        Args:
            allowed_base_path: Base path for file security validation
            enable_qdrant: Enable Qdrant/BM25 indexing (default: True)
            enable_neo4j: Enable Neo4j graph construction (default: True)
        """
        self.allowed_base_path = Path(allowed_base_path) if allowed_base_path else None
        self.enable_qdrant = enable_qdrant
        self.enable_neo4j = enable_neo4j

        # Component pipelines
        self.qdrant_pipeline = DocumentIngestionPipeline(
            allowed_base_path=str(self.allowed_base_path) if self.allowed_base_path else None
        )

        logger.info(
            "unified_ingestion_pipeline_initialized",
            qdrant_enabled=self.enable_qdrant,
            neo4j_enabled=self.enable_neo4j,
        )

    async def ingest_directory(
        self,
        input_dir: str,
        progress_callback: Any = None,
    ) -> IngestionResult:
        """Ingest all documents from directory to all systems.

        Args:
            input_dir: Directory path with documents
            progress_callback: Optional callback for progress updates

        Returns:
            IngestionResult with statistics
        """
        import time

        start_time = time.time()

        logger.info("unified_ingestion_start", input_dir=input_dir)

        errors = []
        qdrant_result = {}
        neo4j_result = {}

        # Phase 1: Parallel indexing with error handling
        async def safe_index_qdrant():
            """Safely index to Qdrant with error handling."""
            try:
                return await self._index_to_qdrant(input_dir)
            except Exception as e:
                logger.error("qdrant_indexing_error", error=str(e), exc_info=True)
                errors.append(f"Qdrant indexing failed: {str(e)}")
                return {}

        async def safe_index_neo4j():
            """Safely index to Neo4j with error handling."""
            try:
                return await self._index_to_neo4j(input_dir)
            except Exception as e:
                logger.error("neo4j_indexing_error", error=str(e), exc_info=True)
                errors.append(f"Neo4j indexing failed: {str(e)}")
                return {}

        # Execute in parallel
        tasks = []
        if self.enable_qdrant:
            tasks.append(safe_index_qdrant())
        if self.enable_neo4j:
            tasks.append(safe_index_neo4j())

        results = await asyncio.gather(*tasks)

        # Parse results
        if self.enable_qdrant:
            qdrant_result = results[0]

        if self.enable_neo4j:
            neo4j_idx = 1 if self.enable_qdrant else 0
            neo4j_result = results[neo4j_idx]

        duration = time.time() - start_time

        result = IngestionResult(
            total_documents=qdrant_result.get("documents_loaded", 0),
            qdrant_indexed=qdrant_result.get("points_indexed", 0),
            bm25_indexed=qdrant_result.get("documents_loaded", 0),  # Same as Qdrant documents
            neo4j_entities=neo4j_result.get("entity_count", 0),
            neo4j_relationships=neo4j_result.get("relationship_count", 0),
            errors=errors,
            duration_seconds=duration,
        )

        logger.info(
            "unified_ingestion_complete",
            total_documents=result.total_documents,
            qdrant_indexed=result.qdrant_indexed,
            neo4j_entities=result.neo4j_entities,
            neo4j_relationships=result.neo4j_relationships,
            duration=duration,
            errors_count=len(errors),
        )

        return result

    async def _index_to_qdrant(self, input_dir: str) -> dict[str, Any]:
        """Index documents to Qdrant and BM25.

        Args:
            input_dir: Directory path

        Returns:
            Indexing statistics

        Raises:
            Exception: If indexing fails (caught by safe_index_qdrant wrapper)
        """
        logger.info("qdrant_indexing_start", input_dir=input_dir)

        # Use existing DocumentIngestionPipeline
        stats = await self.qdrant_pipeline.index_documents(input_dir=input_dir)

        logger.info(
            "qdrant_indexing_complete",
            documents_loaded=stats.get("documents_loaded", 0),
            points_indexed=stats.get("points_indexed", 0),
            chunks_created=stats.get("chunks_created", 0),
        )

        return stats

    async def _index_to_neo4j(self, input_dir: str) -> dict[str, Any]:
        """Index documents to Neo4j via LightRAG.

        Args:
            input_dir: Directory path

        Returns:
            Graph statistics (entity_count, relationship_count)

        Raises:
            Exception: If indexing fails (caught by safe_index_neo4j wrapper)
        """
        logger.info("neo4j_indexing_start", input_dir=input_dir)

        # Load documents first
        from llama_index.core import SimpleDirectoryReader

        reader = SimpleDirectoryReader(
            input_dir=input_dir,
            recursive=True,
            # Sprint 16 Feature 16.5: Added .pptx support
            required_exts=[".txt", ".md", ".pdf", ".docx", ".pptx"],
        )
        documents = reader.load_data()

        if not documents:
            logger.warning("no_documents_found_for_neo4j", input_dir=input_dir)
            return {"entity_count": 0, "relationship_count": 0}

        # Get LightRAG wrapper (must be done in async context, not in gather)
        lightrag = await get_lightrag_wrapper_async()

        # Convert to LightRAG format
        # Sprint 16 Feature 16.6: Add document ID for provenance tracking
        lightrag_docs = [
            {
                "text": doc.text,
                "metadata": doc.metadata,
                "id": doc.doc_id if hasattr(doc, "doc_id") else f"doc_{i}",
            }
            for i, doc in enumerate(documents)
        ]

        # Insert into LightRAG (builds graph)
        # Sprint 16 Feature 16.6: Use optimized method with ChunkingService + Three-Phase Pipeline
        await lightrag.insert_documents_optimized(lightrag_docs)

        # Get graph statistics
        stats = await lightrag.get_stats()

        logger.info(
            "neo4j_indexing_complete",
            documents=len(documents),
            entities=stats.get("entity_count", 0),
            relationships=stats.get("relationship_count", 0),
        )

        return stats


# Global instance (singleton)
_unified_pipeline: UnifiedIngestionPipeline | None = None


def get_unified_pipeline() -> UnifiedIngestionPipeline:
    """Get global UnifiedIngestionPipeline instance."""
    global _unified_pipeline
    if _unified_pipeline is None:
        _unified_pipeline = UnifiedIngestionPipeline()
    return _unified_pipeline
