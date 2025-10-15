"""Document Ingestion Pipeline using LlamaIndex.

This module handles document loading, chunking, and indexing into Qdrant.
Supports PDF, TXT, MD, DOCX, and other formats via LlamaIndex loaders.
"""

import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog
from llama_index.core import Document, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from qdrant_client.models import PointStruct

from src.components.vector_search.embeddings import EmbeddingService
from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.core.config import settings
from src.core.exceptions import VectorSearchError

logger = structlog.get_logger(__name__)


class DocumentIngestionPipeline:
    """Document ingestion pipeline with LlamaIndex and Qdrant."""

    def __init__(
        self,
        qdrant_client: QdrantClientWrapper | None = None,
        embedding_service: EmbeddingService | None = None,
        collection_name: str | None = None,
        chunk_size: int = 512,
        chunk_overlap: int = 128,
        allowed_base_path: str | Path | None = None,
    ):
        """Initialize document ingestion pipeline.

        Args:
            qdrant_client: Qdrant client wrapper
            embedding_service: Embedding service
            collection_name: Target collection name (default: from settings)
            chunk_size: Maximum tokens per chunk (default: 512)
            chunk_overlap: Overlap between chunks in tokens (default: 128)
            allowed_base_path: Base directory for security validation (default: from settings)
        """
        self.qdrant_client = qdrant_client or QdrantClientWrapper()
        self.embedding_service = embedding_service or EmbeddingService()
        self.collection_name = collection_name or settings.qdrant_collection
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Security: Base path for document ingestion
        if allowed_base_path:
            self.allowed_base_path = Path(allowed_base_path).resolve()
        else:
            self.allowed_base_path = Path(settings.documents_base_path).resolve()

        # Initialize text splitter
        self.text_splitter = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        logger.info(
            "Document ingestion pipeline initialized",
            collection=self.collection_name,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
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

    async def load_documents(
        self,
        input_dir: str | Path,
        required_exts: list[str] | None = None,
        recursive: bool = True,
    ) -> list[Document]:
        """Load documents from directory using LlamaIndex.

        Args:
            input_dir: Directory containing documents
            required_exts: File extensions to load (default: [".pdf", ".txt", ".md"])
            recursive: Search subdirectories (default: True)

        Returns:
            List of LlamaIndex Document objects

        Raises:
            VectorSearchError: If document loading fails
            ValueError: If path validation fails (path traversal)
        """
        if required_exts is None:
            required_exts = [".pdf", ".txt", ".md", ".docx", ".csv"]

        try:
            # Security: Validate path to prevent directory traversal
            validated_path = self._validate_path(input_dir)

            loader = SimpleDirectoryReader(
                input_dir=str(validated_path),
                required_exts=required_exts,
                recursive=recursive,
                filename_as_id=True,
            )

            documents = loader.load_data()

            logger.info(
                "Documents loaded",
                input_dir=str(validated_path),
                documents_count=len(documents),
                extensions=required_exts,
            )

            return documents

        except ValueError:
            # Path validation error - re-raise as-is (security error)
            raise
        except Exception as e:
            logger.error(
                "Failed to load documents",
                input_dir=str(input_dir),
                error=str(e),
            )
            raise VectorSearchError(f"Failed to load documents: {e}") from e

    async def chunk_documents(
        self,
        documents: list[Document],
    ) -> list[TextNode]:
        """Split documents into chunks using sentence-based splitting.

        Args:
            documents: List of LlamaIndex documents

        Returns:
            List of text nodes (chunks)

        Raises:
            VectorSearchError: If chunking fails
        """
        try:
            nodes = self.text_splitter.get_nodes_from_documents(documents)

            logger.info(
                "Documents chunked",
                documents_count=len(documents),
                chunks_count=len(nodes),
                avg_chunks_per_doc=len(nodes) / len(documents) if documents else 0,
            )

            return nodes

        except Exception as e:
            logger.error("Failed to chunk documents", error=str(e))
            raise VectorSearchError(f"Failed to chunk documents: {e}") from e

    async def generate_embeddings(
        self,
        nodes: list[TextNode],
    ) -> list[list[float]]:
        """Generate embeddings for text nodes.

        Args:
            nodes: List of text nodes

        Returns:
            List of embedding vectors

        Raises:
            VectorSearchError: If embedding generation fails
        """
        try:
            # Extract text from nodes
            texts = [node.get_content() for node in nodes]

            # Generate embeddings in batch
            embeddings = await self.embedding_service.embed_batch(texts)

            logger.info(
                "Embeddings generated",
                nodes_count=len(nodes),
                embedding_dim=len(embeddings[0]) if embeddings else 0,
            )

            return embeddings

        except Exception as e:
            logger.error("Failed to generate embeddings", error=str(e))
            raise VectorSearchError(f"Failed to generate embeddings: {e}") from e

    async def index_documents(
        self,
        input_dir: str | Path,
        batch_size: int = 100,
        required_exts: list[str] | None = None,
    ) -> dict[str, Any]:
        """Complete ingestion pipeline: load, chunk, embed, index.

        Args:
            input_dir: Directory containing documents
            batch_size: Batch size for indexing (default: 100)
            required_exts: File extensions to load

        Returns:
            Dictionary with ingestion statistics

        Raises:
            VectorSearchError: If ingestion pipeline fails
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Step 1: Ensure collection exists
            await self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vector_size=self.embedding_service.get_embedding_dimension(),
            )

            # Step 2: Load documents
            logger.info("Step 1/4: Loading documents", input_dir=str(input_dir))
            documents = await self.load_documents(
                input_dir=input_dir,
                required_exts=required_exts,
            )

            if not documents:
                logger.warning("No documents found", input_dir=str(input_dir))
                return {
                    "documents_loaded": 0,
                    "chunks_created": 0,
                    "embeddings_generated": 0,
                    "points_indexed": 0,
                    "duration_seconds": 0,
                }

            # Step 3: Chunk documents
            logger.info("Step 2/4: Chunking documents")
            nodes = await self.chunk_documents(documents)

            # Step 4: Generate embeddings
            logger.info("Step 3/4: Generating embeddings")
            embeddings = await self.generate_embeddings(nodes)

            # Step 5: Create Qdrant points
            logger.info("Step 4/4: Indexing to Qdrant")
            points = []
            for node, embedding in zip(nodes, embeddings, strict=False):
                point_id = str(uuid4())
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": node.get_content(),
                        "document_id": node.ref_doc_id or "unknown",
                        "chunk_index": node.metadata.get("chunk_index", 0),
                        "source": node.metadata.get("file_name", "unknown"),
                        "file_path": node.metadata.get("file_path", ""),
                        "file_type": node.metadata.get("file_type", ""),
                    },
                )
                points.append(point)

            # Upload to Qdrant in batches
            await self.qdrant_client.upsert_points(
                collection_name=self.collection_name,
                points=points,
                batch_size=batch_size,
            )

            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time

            stats = {
                "documents_loaded": len(documents),
                "chunks_created": len(nodes),
                "embeddings_generated": len(embeddings),
                "points_indexed": len(points),
                "duration_seconds": round(duration, 2),
                "chunks_per_document": round(len(nodes) / len(documents), 2),
                "collection_name": self.collection_name,
            }

            logger.info(
                "Document ingestion completed",
                **stats,
            )

            return stats

        except Exception as e:
            logger.error("Document ingestion failed", error=str(e))
            raise VectorSearchError(f"Document ingestion failed: {e}") from e

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
) -> dict[str, Any]:
    """Quick document ingestion helper function.

    Args:
        input_dir: Directory containing documents
        collection_name: Target collection name
        chunk_size: Maximum tokens per chunk
        chunk_overlap: Overlap between chunks

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
    )

    return await pipeline.index_documents(input_dir=input_dir)
