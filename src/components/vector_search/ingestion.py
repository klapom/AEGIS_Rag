"""Document Ingestion Pipeline using LlamaIndex.

============================================================================
⚠️ DEPRECATED: Sprint 21 ADR-028
============================================================================
This module is DEPRECATED and will be removed in Sprint 25.
Use DoclingContainerClient for new ingestion pipelines.

REASON: LlamaIndex lacks OCR, table extraction, and GPU acceleration.
REPLACEMENT: src.components.ingestion.docling_client.DoclingContainerClient

Sprint 24 Feature 24.15: Lazy imports for optional llama_index dependency
============================================================================

This module handles document loading, chunking, and indexing into Qdrant.
Supports PDF, TXT, MD, DOCX, and other formats via LlamaIndex loaders.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

# TYPE_CHECKING imports - needed for type hints in deprecated methods
# Note: llama_index is deprecated (ADR-028), use DoclingContainerClient for new pipelines
if TYPE_CHECKING:
    from llama_index.core import Document

from src.components.shared.embedding_service import UnifiedEmbeddingService
from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.core.chunk import ChunkStrategy
from src.core.chunking_service import get_chunking_service
from src.core.config import settings
from src.core.exceptions import VectorSearchError

logger = structlog.get_logger(__name__)

class DocumentIngestionPipeline:
    """Document ingestion pipeline with LlamaIndex and Qdrant."""

    def __init__(
        self,
        qdrant_client: QdrantClientWrapper | None = None,
        embedding_service: UnifiedEmbeddingService | None = None,
        collection_name: str | None = None,
        chunk_size: int = 512,
        chunk_overlap: int = 128,
        allowed_base_path: str | Path | None = None,
        use_adaptive_chunking: bool = False,
    ) -> None:
        """Initialize document ingestion pipeline.

        Args:
            qdrant_client: Qdrant client wrapper
            embedding_service: Embedding service
            collection_name: Target collection name (default: from settings)
            chunk_size: Maximum tokens per chunk (default: 512)
            chunk_overlap: Overlap between chunks in tokens (default: 128)
            allowed_base_path: Base directory for security validation (default: from settings)
            use_adaptive_chunking: Use adaptive chunking strategy (default: False)
        """
        from src.components.shared.embedding_service import get_embedding_service

        self.qdrant_client = qdrant_client or QdrantClientWrapper()
        self.embedding_service = embedding_service or get_embedding_service()
        self.collection_name = collection_name or settings.qdrant_collection
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_adaptive_chunking = use_adaptive_chunking

        # Security: Base path for document ingestion
        if allowed_base_path:
            self.allowed_base_path = Path(allowed_base_path).resolve()
        else:
            self.allowed_base_path = Path(settings.documents_base_path).resolve()

        # Sprint 16.7: Unified chunking strategy (600 tokens, adaptive, 150 overlap)
        # Aligned with Neo4j/LightRAG for maximum synergie
        chunk_strategy = ChunkStrategy(
            method="adaptive",  # Sentence-aware chunking
            chunk_size=600,  # Optimized for entity extraction (was: 512)
            overlap=150,  # 25% overlap for context bridges (was: 128)
        )
        self.chunking_service = get_chunking_service(strategy=chunk_strategy)

        logger.info(
            "Document ingestion pipeline initialized",
            collection=self.collection_name,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            use_adaptive_chunking=self.use_adaptive_chunking,
            allowed_base_path=str(self.allowed_base_path),
        )

    def _validate_path(self, input_path: str | Path) -> Path:
        """Validate path to prevent directory traversal attacks.

        Args:
            input_path: Path to validate

        Returns:
            Resolved and validated Path object

        Raises:
            ValueError: If path traversal is detected or path is outside allowed base
        """
        try:
            # Convert to Path and resolve to absolute path
            resolved_path = Path(input_path).resolve()

            # Check if path starts with allowed base path
            if not str(resolved_path).startswith(str(self.allowed_base_path)):
                logger.error(
                    "Path traversal attempt detected",
                    input_path=str(input_path),
                    resolved_path=str(resolved_path),
                    allowed_base=str(self.allowed_base_path),
                )
                raise ValueError(
                    f"Security: Path '{input_path}' is outside allowed base directory '{self.allowed_base_path}'"
                )

            # Check if path exists
            if not resolved_path.exists():
                raise ValueError(f"Path does not exist: {input_path}")

            # Check if path is a directory
            if not resolved_path.is_dir():
                raise ValueError(f"Path is not a directory: {input_path}")

            logger.debug(
                "Path validation successful",
                input_path=str(input_path),
                resolved_path=str(resolved_path),
            )

            return resolved_path

        except Exception as e:
            logger.error("Path validation failed", input_path=str(input_path), error=str(e))
            raise

    # Sprint 25 Feature 25.7: load_documents() method removed (deprecated per ADR-028)
    # Use DoclingContainerClient instead: src.components.ingestion.docling_client

    def _clean_metadata(self, metadata: dict) -> dict:
        """Clean metadata to reduce size, especially for PPTX files.

        Removes large formatting fields that are not useful for RAG:
        - text_sections (contains detailed formatting structure)
        - extraction_errors, extraction_warnings (debugging info)

        Simplifies paths to relative format from project root.

        Args:
            metadata: Original metadata dict from document loader

        Returns:
            Cleaned metadata dict with reduced size
        """
        cleaned = {}

        # Fields to keep (essential for RAG)
        keep_fields = {
            "file_name",
            "page_label",
            "title",
            "file_type",
            "file_size",
            "creation_date",
            "last_modified_date",
            "tables",
            "charts",
            "images",
            "notes",
        }

        # Fields to remove (too large or not useful)
        remove_fields = {
            "text_sections",  # Contains detailed formatting (can be 1-7 KB)
            "extraction_errors",  # Debugging info
            "extraction_warnings",  # Debugging info
        }

        for key, value in metadata.items():
            if key in remove_fields:
                continue

            if key == "file_path" and isinstance(value, str):
                # Shorten file_path to relative path from project root
                # From: C:\Users\...\AEGIS_Rag\data\sample_documents\...
                # To: data/sample_documents/...
                if "data" in value:
                    parts = value.split("data")
                    if len(parts) > 1:
                        cleaned[key] = "data" + parts[-1].replace("\\", "/")
                    else:
                        cleaned[key] = value
                else:
                    cleaned[key] = value
            elif key == "file_type" and isinstance(value, str):
                # Simplify MIME types
                # From: application/vnd.openxmlformats-officedocument.presentationml.presentation
                # To: pptx
                if "presentationml" in value:
                    cleaned[key] = "pptx"
                elif "wordprocessingml" in value:
                    cleaned[key] = "docx"
                elif "spreadsheetml" in value:
                    cleaned[key] = "xlsx"
                elif "pdf" in value:
                    cleaned[key] = "pdf"
                else:
                    cleaned[key] = value
            elif key in ["tables", "charts", "images"] and isinstance(value, list):
                # Simplify content arrays - only keep count, not full content
                # Full table/chart data should be in the chunk content, not metadata
                if value:
                    # Just keep a count and type indicator
                    cleaned[key] = len(value)  # e.g., tables: 1 instead of full table data
                else:
                    cleaned[key] = 0
            elif key in keep_fields:
                cleaned[key] = value

        return cleaned

    async def chunk_documents(
        self,
        documents: list["Document"],  # Type hint uses string literal
    ) -> list[dict]:
        """Split documents into chunks using unified ChunkingService.

        Sprint 16: Now uses ChunkingService for consistent chunking across all pipelines.
        Sprint 24 Feature 24.15: Lazy imports for optional llama_index dependency.

        Args:
            documents: list of LlamaIndex documents

        Returns:
            list of Chunk objects from ChunkingService

        Raises:
            VectorSearchError: If chunking fails
            ImportError: If llama_index not installed (deprecated method)
        """
        # Note: No lazy import needed here - documents are already loaded by load_documents()
        # which has its own lazy import. If documents are provided externally, they must
        # come from llama_index which would already be installed.
        try:
            all_chunks = []
            skipped_empty = 0

            for doc in documents:
                # Extract document metadata
                doc_id = doc.doc_id or doc.metadata.get("file_name", "unknown")
                content = doc.get_content()
                metadata = doc.metadata

                # Skip documents with empty content
                if not content or not content.strip():
                    logger.debug("Skipping document with empty content", document_id=doc_id)
                    skipped_empty += 1
                    continue

                # Clean metadata to reduce size (especially for PPTX files)
                cleaned_metadata = self._clean_metadata(metadata)

                # Use ChunkingService for unified chunking
                chunks = self.chunking_service.chunk_document(
                    document_id=doc_id,
                    content=content,
                    metadata=cleaned_metadata,
                )

                all_chunks.extend(chunks)

            logger.info(
                "Documents chunked",
                documents_count=len(documents),
                skipped_empty=skipped_empty,
                chunks_count=len(all_chunks),
                avg_chunks_per_doc=len(all_chunks) / len(documents) if documents else 0,
                strategy=self.chunking_service.strategy.method,
            )

            return all_chunks

        except Exception as e:
            logger.error("Failed to chunk documents", error=str(e))
            raise VectorSearchError(query="", reason=f"Failed to chunk documents: {e}") from e

    async def generate_embeddings(
        self,
        chunks: list,
    ) -> list[list[float]]:
        """Generate embeddings for chunks.

        Sprint 16: Now works with Chunk objects from ChunkingService.

        Args:
            chunks: list of Chunk objects

        Returns:
            list of embedding vectors

        Raises:
            VectorSearchError: If embedding generation fails
        """
        try:
            # Extract text from chunks
            texts = [chunk.content for chunk in chunks]

            # Generate embeddings in batch
            embeddings = await self.embedding_service.embed_batch(texts)

            logger.info(
                "Embeddings generated",
                chunks_count=len(chunks),
                embedding_dim=len(embeddings[0]) if embeddings else 0,
            )

            return embeddings

        except Exception as e:
            logger.error("Failed to generate embeddings", error=str(e))
            raise VectorSearchError(query="", reason=f"Failed to generate embeddings: {e}") from e

    async def index_documents(
        self,
        input_dir: str | Path,
        batch_size: int = 100,
        required_exts: list[str] | None = None,
    ) -> dict[str, Any]:
        """Complete ingestion pipeline: load, chunk, embed, index.

        ============================================================================
        ⚠️ DEPRECATED: Sprint 25 Feature 25.7 - This method is deprecated
        ============================================================================
        This method depends on load_documents() which was removed in Sprint 25.

        REPLACEMENT: Use DoclingContainerClient + LangGraph pipeline
          from src.components.ingestion.docling_client import DoclingContainerClient
          from src.components.ingestion.langgraph_pipeline import create_ingestion_graph

          # See docs/sprints/SPRINT_21_PLAN_v2.md for full migration guide
        ============================================================================

        Args:
            input_dir: Directory containing documents
            batch_size: Batch size for indexing (default: 100)
            required_exts: File extensions to load

        Returns:
            Dictionary with ingestion statistics

        Raises:
            NotImplementedError: This method was removed in Sprint 25
        """
        raise NotImplementedError(
            "index_documents() was deprecated in Sprint 25 (Feature 25.7). "
            "Use DoclingContainerClient + LangGraph pipeline instead. "
            "See src.components.ingestion.docling_client and "
            "src.components.ingestion.langgraph_pipeline for replacements."
        )

    async def get_collection_stats(self) -> dict[str, Any] | None:
        """Get statistics about the indexed collection.

        Returns:
            Dictionary with collection statistics or None
        """
        try:
            info = await self.qdrant_client.get_collection_info(self.collection_name)

            if info:
                return {
                    "collection_name": self.collection_name,
                    "vectors_count": info.vectors_count,
                    "points_count": info.points_count,
                    "indexed_vectors_count": info.indexed_vectors_count,
                    "status": info.status,
                }

            return None

        except Exception as e:
            logger.error("Failed to get collection stats", error=str(e))
            return None

# Convenience function for quick ingestion
async def ingest_documents(
    input_dir: str | Path,
    collection_name: str | None = None,
    chunk_size: int = 512,
    chunk_overlap: int = 128,
    use_adaptive_chunking: bool = False,
) -> dict[str, Any]:
    """Quick document ingestion helper function.

    Args:
        input_dir: Directory containing documents
        collection_name: Target collection name
        chunk_size: Maximum tokens per chunk
        chunk_overlap: Overlap between chunks
        use_adaptive_chunking: Use adaptive chunking strategy

    Returns:
        Ingestion statistics

    Example:
        >>> stats = await ingest_documents("./data/documents")
        >>> print(f"Indexed {stats['points_indexed']} chunks")
    """
    pipeline = DocumentIngestionPipeline(
        collection_name=collection_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        use_adaptive_chunking=use_adaptive_chunking,
    )

    return await pipeline.index_documents(input_dir=input_dir)
