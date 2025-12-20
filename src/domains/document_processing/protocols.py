"""Document Processing Domain Protocols.

Sprint 57 Feature 57.2: Protocol definitions for document ingestion.
Enables dependency injection and improves testability.

Usage:
    from src.domains.document_processing.protocols import (
        DocumentParser,
        ChunkingService,
        ImageEnricher,
        IngestionPipeline,
    )

These protocols define interfaces for:
- Document parsing (PDF, DOCX, etc.)
- Text chunking (section-aware, adaptive)
- Image enrichment (VLM descriptions)
- Full ingestion pipeline

IMPORTANT: These protocols are designed to be extensible for Sprint 59
Agentic Features (CodeExecutor, SandboxedRunner).
"""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DocumentParser(Protocol):
    """Protocol for document parsing.

    Implementations should parse documents and extract structured content
    including text, sections, images, and metadata.

    Example:
        >>> class DoclingParser:
        ...     async def parse(self, file_path: Path) -> dict[str, Any]:
        ...         # Use Docling to parse document
        ...         pass
    """

    async def parse(self, file_path: Path) -> dict[str, Any]:
        """Parse a document and extract content.

        Args:
            file_path: Path to document file (PDF, DOCX, etc.)

        Returns:
            Parsed document containing:
            - text: str - Full document text
            - sections: list[dict] - Document sections with headings
            - images: list[dict] - Extracted images with metadata
            - metadata: dict - Document metadata (pages, author, etc.)
        """
        ...

    async def extract_sections(
        self,
        parsed_doc: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract sections from parsed document.

        Args:
            parsed_doc: Previously parsed document

        Returns:
            List of sections with:
            - heading: str - Section heading
            - level: int - Heading level (1-6)
            - text: str - Section text content
            - page_no: int - Starting page number
        """
        ...

    def get_supported_formats(self) -> list[str]:
        """Get list of supported file formats.

        Returns:
            List of file extensions (e.g., [".pdf", ".docx"])
        """
        ...


@runtime_checkable
class ChunkingService(Protocol):
    """Protocol for text chunking.

    Implementations should split text into optimal chunks for
    embedding and retrieval, respecting section boundaries.

    ADR-039: Section-aware chunking with 800-1800 token range.
    """

    def chunk(
        self,
        text: str,
        min_tokens: int = 800,
        max_tokens: int = 1800,
        metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Chunk text into optimal segments.

        Args:
            text: Text to chunk
            min_tokens: Minimum tokens per chunk
            max_tokens: Maximum tokens per chunk
            metadata: Optional metadata to include with chunks

        Returns:
            List of chunks with:
            - text: str - Chunk text
            - token_count: int - Number of tokens
            - section_headings: list[str] - Related section headings
            - metadata: dict - Chunk metadata
        """
        ...

    def chunk_with_sections(
        self,
        sections: list[dict[str, Any]],
        min_tokens: int = 800,
        max_tokens: int = 1800,
    ) -> list[dict[str, Any]]:
        """Chunk sections while preserving structure.

        Args:
            sections: List of document sections
            min_tokens: Minimum tokens per chunk
            max_tokens: Maximum tokens per chunk

        Returns:
            List of section-aware chunks
        """
        ...


@runtime_checkable
class ImageEnricher(Protocol):
    """Protocol for image enrichment via VLM.

    Implementations should generate descriptions for images
    using vision-language models.
    """

    async def enrich_image(
        self,
        image_path: Path,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        """Generate description for a single image.

        Args:
            image_path: Path to image file
            prompt: Optional custom prompt for description

        Returns:
            Enrichment result with:
            - description: str - Generated description
            - model: str - Model used
            - tokens: int - Tokens used
            - cost_usd: float - Cost incurred
        """
        ...

    async def enrich_images(
        self,
        images: list[dict[str, Any]],
        prompt: str | None = None,
    ) -> list[dict[str, Any]]:
        """Generate descriptions for multiple images.

        Args:
            images: List of images with 'path' and optional metadata
            prompt: Optional custom prompt for descriptions

        Returns:
            List of enriched images with descriptions
        """
        ...


@runtime_checkable
class IngestionPipeline(Protocol):
    """Protocol for document ingestion pipeline.

    Implementations orchestrate the full ingestion flow from
    document to indexed vectors and graph.
    """

    async def ingest(
        self,
        file_path: Path,
        namespace: str | None = None,
        skip_existing: bool = True,
    ) -> AsyncIterator[dict[str, Any]]:
        """Ingest a document with progress events.

        Args:
            file_path: Path to document file
            namespace: Optional namespace for organization
            skip_existing: Skip if document already ingested

        Yields:
            Progress events with:
            - event: str - Event type (parsing, chunking, embedding, etc.)
            - progress: float - Progress percentage (0-100)
            - message: str - Human-readable message
            - data: dict | None - Optional event-specific data
        """
        ...

    async def ingest_batch(
        self,
        file_paths: list[Path],
        namespace: str | None = None,
        concurrency: int = 3,
    ) -> AsyncIterator[dict[str, Any]]:
        """Ingest multiple documents in batch.

        Args:
            file_paths: List of document paths
            namespace: Optional namespace
            concurrency: Number of concurrent ingestions

        Yields:
            Progress events for all documents
        """
        ...

    async def get_status(self, document_id: str) -> dict[str, Any] | None:
        """Get ingestion status for a document.

        Args:
            document_id: Document identifier

        Returns:
            Status dict or None if not found
        """
        ...


@runtime_checkable
class EmbeddingGenerator(Protocol):
    """Protocol for embedding generation.

    Implementations should generate vector embeddings for text chunks.
    ADR-024: BGE-M3 embeddings (1024-dim, multilingual).
    """

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (e.g., 1024 dimensions for BGE-M3)
        """
        ...

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors
        """
        ...

    def get_dimension(self) -> int:
        """Get embedding dimension.

        Returns:
            Dimension of embedding vectors (e.g., 1024)
        """
        ...


@runtime_checkable
class FormatRouter(Protocol):
    """Protocol for document format routing.

    Implementations should route documents to appropriate parsers
    based on file format.
    """

    def route(self, file_path: Path) -> str:
        """Route document to appropriate parser.

        Args:
            file_path: Path to document file

        Returns:
            Parser identifier (e.g., "docling", "llamaindex")
        """
        ...

    def is_supported(self, file_path: Path) -> bool:
        """Check if file format is supported.

        Args:
            file_path: Path to document file

        Returns:
            True if format is supported
        """
        ...


__all__ = [
    "DocumentParser",
    "ChunkingService",
    "ImageEnricher",
    "IngestionPipeline",
    "EmbeddingGenerator",
    "FormatRouter",
]
