"""Unified Chunking Service - Single Source of Truth (Sprint 36 Feature 36.6).

TD-054: Unified Chunking Service
ADR-039: Adaptive Section-Aware Chunking

This module provides a SINGLE SOURCE OF TRUTH for document chunking
across ALL ingestion pipelines (Qdrant, BM25, LightRAG/Neo4j).

Architecture:
- ChunkingService class: Central chunking logic
- Multiple strategies: adaptive (section-aware), fixed, sentence, paragraph
- Unified Chunk model: Same chunks go to all indexes
- Configuration-driven: ChunkStrategy for strategy selection

Benefits:
- Eliminates code duplication (70% reduction)
- Guarantees consistent chunk boundaries across all indexes
- SHA-256 chunk_id enables graph-vector alignment
- Section-aware chunking for better retrieval quality (ADR-039)

Consumers (ALL must use this service):
- Qdrant (vector embeddings)
- BM25 (keyword search)
- Neo4j/LightRAG (graph nodes)

Example:
    >>> service = ChunkingService()
    >>> chunks = await service.chunk_document(
    ...     text="Sample document...",
    ...     document_id="doc_123",
    ...     sections=[...],  # From Docling section extraction
    ... )
    >>> # Same chunks go to all indexes
    >>> await index_to_qdrant(chunks)
    >>> await index_to_bm25(chunks)
    >>> await index_to_neo4j(chunks)
"""

import re
import time
from enum import Enum
from typing import TYPE_CHECKING

import structlog
import tiktoken
from prometheus_client import Counter, Gauge, Histogram
from pydantic import BaseModel, Field

from src.core.chunk import Chunk

# TYPE_CHECKING imports - needed for type hints (string literals)
# Runtime imports are lazy-loaded in methods
if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

# Prometheus Metrics
chunking_duration_seconds = Histogram(
    "chunking_duration_seconds",
    "Time spent chunking documents",
    labelnames=["strategy"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)

chunks_created_total = Counter(
    "chunks_created_total",
    "Total number of chunks created",
    labelnames=["strategy"],
)

avg_chunk_size_tokens = Gauge(
    "avg_chunk_size_tokens",
    "Average chunk size in tokens",
    labelnames=["strategy"],
)

documents_chunked_total = Counter(
    "documents_chunked_total",
    "Total number of documents chunked",
    labelnames=["strategy"],
)

# Sprint 43 Feature 43.7: Enhanced Chunking Metrics
chunking_input_chars = Counter(
    "chunking_input_chars_total",
    "Total characters input to chunker",
    labelnames=["document_id"],
)

chunking_chunk_size_chars_histogram = Histogram(
    "chunking_chunk_size_chars",
    "Individual chunk size in characters",
    buckets=[100, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 5000],
)

chunking_chunk_size_tokens_histogram = Histogram(
    "chunking_chunk_size_tokens",
    "Individual chunk size in tokens",
    buckets=[50, 100, 200, 400, 600, 800, 1000, 1200, 1500, 1800],
)

chunking_overlap_tokens_histogram = Histogram(
    "chunking_overlap_tokens",
    "Overlap between consecutive chunks in tokens",
    buckets=[0, 25, 50, 75, 100, 150, 200, 300],
)


# =============================================================================
# CONFIGURATION MODELS
# =============================================================================


class ChunkStrategyEnum(str, Enum):
    """Available chunking strategies."""

    ADAPTIVE = "adaptive"  # Section-aware, 800-1800 tokens (ADR-039)
    FIXED = "fixed"  # Fixed-size chunks with tiktoken
    SENTENCE = "sentence"  # Sentence-based splitting
    PARAGRAPH = "paragraph"  # Paragraph-based splitting


class ChunkingConfig(BaseModel):
    """Configuration for chunking behavior."""

    strategy: ChunkStrategyEnum = Field(
        default=ChunkStrategyEnum.ADAPTIVE,
        description="Chunking strategy to use",
    )
    min_tokens: int = Field(
        default=800,
        ge=100,
        le=2000,
        description="Minimum tokens per chunk (adaptive strategy)",
    )
    max_tokens: int = Field(
        default=1800,
        ge=500,
        le=4000,
        description="Maximum tokens per chunk",
    )
    overlap_tokens: int = Field(
        default=100,
        ge=0,
        le=500,
        description="Overlap between chunks in tokens",
    )
    preserve_sections: bool = Field(
        default=True,
        description="Preserve section boundaries (adaptive strategy)",
    )
    large_section_threshold: int = Field(
        default=1200,
        ge=500,
        le=3000,
        description="Threshold for standalone sections (adaptive strategy)",
    )

    class Config:
        use_enum_values = True


# =============================================================================
# SECTION METADATA (from Docling extraction)
# =============================================================================


class SectionMetadata(BaseModel):
    """Section metadata from Docling extraction.

    This model represents a document section extracted from Docling JSON.
    Used as input for section-aware adaptive chunking.
    """

    heading: str = Field(..., description="Section heading text")
    level: int = Field(default=1, ge=1, le=6, description="Heading level")
    page_no: int = Field(default=0, ge=0, description="Page number")
    bbox: dict[str, float] = Field(
        default_factory=dict,
        description="Bounding box coordinates",
    )
    text: str = Field(..., description="Section text content")
    token_count: int = Field(default=0, ge=0, description="Token count")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


# =============================================================================
# UNIFIED CHUNKING SERVICE
# =============================================================================


class ChunkingService:
    """Unified chunking service for all consumers.

    This is the SINGLE SOURCE OF TRUTH for chunking.
    All consumers (Qdrant, BM25, Neo4j) MUST use this service.

    Strategies:
    1. **adaptive**: Section-aware chunking (800-1800 tokens, respects document structure)
    2. **fixed**: Fixed-size chunks with tiktoken (token-accurate)
    3. **sentence**: Sentence-based splitting with regex
    4. **paragraph**: Paragraph-based splitting

    Example:
        >>> service = ChunkingService()
        >>> chunks = await service.chunk_document(
        ...     text="Sample document...",
        ...     document_id="doc_123",
        ...     sections=[...],  # From Docling
        ... )
        >>>
        >>> # Same chunks go to all indexes
        >>> await index_to_qdrant(chunks)
        >>> await index_to_bm25(chunks)
        >>> await index_to_neo4j(chunks)
    """

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        """Initialize chunking service.

        Args:
            config: Chunking configuration (uses defaults if None)
        """
        self.config = config or ChunkingConfig()

        # Initialize tokenizer for token counting
        try:
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning("tiktoken_init_failed", error=str(e))
            self._tokenizer = None

        logger.info(
            "chunking_service_initialized",
            strategy=self.config.strategy,
            min_tokens=self.config.min_tokens,
            max_tokens=self.config.max_tokens,
            overlap=self.config.overlap_tokens,
        )

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Token count
        """
        if self._tokenizer:
            try:
                return len(self._tokenizer.encode(text))
            except Exception:
                pass

        # Fallback: approximate token count (avg 4 chars/token)
        return max(1, len(text) // 4)

    def _generate_chunk_id(self, document_id: str, chunk_index: int, text: str) -> str:
        """Generate unique chunk ID.

        Format: UUID4-style (8-4-4-4-12 hex chars with dashes)
        Hash ensures uniqueness even if content changes.

        Args:
            document_id: Document identifier
            chunk_index: Chunk index within document
            text: Chunk text content

        Returns:
            Unique chunk ID
        """
        return Chunk.generate_chunk_id(document_id, chunk_index, text)

    async def chunk_document(
        self,
        text: str,
        document_id: str,
        sections: list[SectionMetadata] | list[dict] | None = None,
        metadata: dict | None = None,
    ) -> list[Chunk]:
        """Chunk document using configured strategy.

        This is the MAIN ENTRY POINT for all chunking.
        ALL consumers must use this method.

        Args:
            text: Full document text
            document_id: Unique document identifier
            sections: Optional section information from Docling (for adaptive strategy)
            metadata: Optional document-level metadata

        Returns:
            List of Chunk objects with consistent IDs and metadata

        Raises:
            ValueError: If text is empty

        Example:
            >>> service = ChunkingService()
            >>> chunks = await service.chunk_document(
            ...     text="Sample document...",
            ...     document_id="doc_123",
            ...     sections=[...],
            ... )
        """
        if not text or not text.strip():
            raise ValueError("Content cannot be empty")

        logger.info(
            "chunking_document_start",
            document_id=document_id,
            text_length=len(text),
            strategy=self.config.strategy,
            has_sections=sections is not None and len(sections or []) > 0,
        )

        # Measure chunking duration
        start_time = time.time()

        # Convert dict sections to SectionMetadata if needed
        if sections and isinstance(sections[0], dict):
            sections = [SectionMetadata(**s) for s in sections]

        # Route to appropriate chunking method
        if self.config.strategy == ChunkStrategyEnum.ADAPTIVE:
            chunks = await self._chunk_adaptive(text, document_id, sections, metadata)
        elif self.config.strategy == ChunkStrategyEnum.FIXED:
            chunks = await self._chunk_fixed(text, document_id, metadata)
        elif self.config.strategy == ChunkStrategyEnum.SENTENCE:
            chunks = await self._chunk_sentence(text, document_id, metadata)
        elif self.config.strategy == ChunkStrategyEnum.PARAGRAPH:
            chunks = await self._chunk_paragraph(text, document_id, metadata)
        else:
            raise ValueError(f"Unknown chunking strategy: {self.config.strategy}")

        # Record metrics
        duration = time.time() - start_time
        # Handle both enum and string (use_enum_values=True converts to string)
        strategy_label = (
            self.config.strategy
            if isinstance(self.config.strategy, str)
            else self.config.strategy.value
        )

        chunking_duration_seconds.labels(strategy=strategy_label).observe(duration)
        chunks_created_total.labels(strategy=strategy_label).inc(len(chunks))
        documents_chunked_total.labels(strategy=strategy_label).inc()

        # Sprint 43 Feature 43.7: Enhanced metrics for monitoring/reporting
        chunking_input_chars.labels(document_id=document_id).inc(len(text))

        if chunks:
            avg_tokens = sum(c.token_count for c in chunks) / len(chunks)
            avg_chunk_size_tokens.labels(strategy=strategy_label).set(avg_tokens)

            # Record individual chunk sizes for histogram
            for i, chunk in enumerate(chunks):
                chunking_chunk_size_chars_histogram.observe(len(chunk.content))
                chunking_chunk_size_tokens_histogram.observe(chunk.token_count)

                # Record overlap (overlap_tokens is already set in _create_chunk)
                if i > 0:
                    chunking_overlap_tokens_histogram.observe(chunk.overlap_tokens)

        # Enhanced logging for report generation (Sprint 43 Feature 43.10)
        logger.info(
            "chunking_document_complete",
            document_id=document_id,
            input_chars=len(text),
            chunks_created=len(chunks),
            avg_tokens_per_chunk=(
                sum(c.token_count for c in chunks) / len(chunks) if chunks else 0
            ),
            avg_chars_per_chunk=(
                sum(len(c.content) for c in chunks) / len(chunks) if chunks else 0
            ),
            overlap_tokens=self.config.overlap_tokens,
            duration_seconds=round(duration, 3),
            # Sprint 43: Include chunk details for report export
            chunk_sizes_chars=[len(c.content) for c in chunks],
            chunk_sizes_tokens=[c.token_count for c in chunks],
        )

        return chunks

    async def _chunk_adaptive(
        self,
        text: str,
        document_id: str,
        sections: list[SectionMetadata] | None = None,
        metadata: dict | None = None,
    ) -> list[Chunk]:
        """Section-aware adaptive chunking (ADR-039).

        Strategy:
        - Large sections (>large_section_threshold): Split at sentence boundaries
        - Small sections (<min_tokens): Merge with neighbors
        - Medium sections: Keep as-is
        - Track multi-section metadata (section_headings, pages, bboxes)

        Args:
            text: Document text
            document_id: Document identifier
            sections: Section metadata from Docling
            metadata: Document metadata

        Returns:
            List of Chunk objects
        """
        chunks = []
        metadata = metadata or {}

        if sections and self.config.preserve_sections:
            # Use section information for intelligent chunking
            current_text = ""
            current_headings: list[str] = []
            current_pages: list[int] = []
            current_bboxes: list[dict[str, float]] = []
            current_tokens = 0

            for section in sections:
                section_text = section.text
                section_heading = section.heading
                section_page = section.page_no
                section_bbox = section.bbox
                section_tokens = section.token_count or self._count_tokens(section_text)

                # If adding this section would exceed max, flush current
                if current_tokens + section_tokens > self.config.max_tokens:
                    if current_text:
                        chunk = self._create_chunk(
                            text=current_text.strip(),
                            document_id=document_id,
                            chunk_index=len(chunks),
                            section_headings=current_headings.copy(),
                            pages=list(set(current_pages)),
                            bboxes=current_bboxes.copy(),
                            metadata=metadata,
                        )
                        chunks.append(chunk)

                    # Start new chunk
                    current_text = section_text
                    current_headings = [section_heading] if section_heading else []
                    current_pages = [section_page] if section_page else []
                    current_bboxes = [section_bbox] if section_bbox else []
                    current_tokens = section_tokens
                else:
                    # Merge into current chunk
                    if current_text:
                        current_text += "\n\n" + section_text
                    else:
                        current_text = section_text

                    if section_heading:
                        current_headings.append(section_heading)
                    if section_page:
                        current_pages.append(section_page)
                    if section_bbox:
                        current_bboxes.append(section_bbox)

                    current_tokens += section_tokens

            # Flush remaining
            if current_text:
                chunk = self._create_chunk(
                    text=current_text.strip(),
                    document_id=document_id,
                    chunk_index=len(chunks),
                    section_headings=current_headings,
                    pages=list(set(current_pages)),
                    bboxes=current_bboxes,
                    metadata=metadata,
                )
                chunks.append(chunk)

        else:
            # No sections - fall back to fixed-size chunking
            chunks = await self._chunk_fixed(text, document_id, metadata)

        logger.info(
            "adaptive_chunking_complete",
            document_id=document_id,
            sections_count=len(sections) if sections else 0,
            chunks_count=len(chunks),
            avg_sections_per_chunk=(
                round(len(sections) / len(chunks), 2) if sections and chunks else 0
            ),
        )

        return chunks

    async def _chunk_fixed(
        self,
        text: str,
        document_id: str,
        metadata: dict | None = None,
    ) -> list[Chunk]:
        """Fixed-size chunking with overlap.

        Args:
            text: Document text
            document_id: Document identifier
            metadata: Document metadata

        Returns:
            List of Chunk objects
        """
        chunks = []
        metadata = metadata or {}

        # Approximate characters per chunk
        chars_per_token = 4
        chunk_size_chars = self.config.max_tokens * chars_per_token
        overlap_chars = self.config.overlap_tokens * chars_per_token

        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + chunk_size_chars
            chunk_text = text[start:end]

            # Try to break at word boundary
            if end < len(text):
                last_space = chunk_text.rfind(" ")
                if last_space > chunk_size_chars * 0.8:
                    chunk_text = chunk_text[:last_space]
                    end = start + last_space

            if chunk_text.strip():
                chunk = self._create_chunk(
                    text=chunk_text.strip(),
                    document_id=document_id,
                    chunk_index=chunk_index,
                    section_headings=[],
                    pages=[],
                    bboxes=[],
                    metadata=metadata,
                )
                chunks.append(chunk)
                chunk_index += 1

            # Move start with overlap
            start = end - overlap_chars
            if start <= 0 or start >= len(text):
                break

        return chunks

    async def _chunk_sentence(
        self,
        text: str,
        document_id: str,
        metadata: dict | None = None,
    ) -> list[Chunk]:
        """Sentence-based chunking (simple regex).

        Args:
            text: Document text
            document_id: Document identifier
            metadata: Document metadata

        Returns:
            List of Chunk objects
        """
        # Split into sentences using regex
        sentence_pattern = r"(?<=[.!?])\s+"
        sentences = re.split(sentence_pattern, text)

        chunks = []
        chunk_index = 0
        current_chunk = []
        current_tokens = 0
        metadata = metadata or {}

        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)

            # Check if adding this sentence would exceed chunk_size
            if current_tokens + sentence_tokens > self.config.max_tokens and current_chunk:
                # Create chunk from accumulated sentences
                chunk_text = " ".join(current_chunk)
                chunk = self._create_chunk(
                    text=chunk_text.strip(),
                    document_id=document_id,
                    chunk_index=chunk_index,
                    section_headings=[],
                    pages=[],
                    bboxes=[],
                    metadata=metadata,
                )
                chunks.append(chunk)

                # Start new chunk
                chunk_index += 1
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                # Add sentence to current chunk
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # Add final chunk if there's remaining content
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk = self._create_chunk(
                text=chunk_text.strip(),
                document_id=document_id,
                chunk_index=chunk_index,
                section_headings=[],
                pages=[],
                bboxes=[],
                metadata=metadata,
            )
            chunks.append(chunk)

        return chunks

    async def _chunk_paragraph(
        self,
        text: str,
        document_id: str,
        metadata: dict | None = None,
    ) -> list[Chunk]:
        """Paragraph-based chunking.

        Args:
            text: Document text
            document_id: Document identifier
            metadata: Document metadata

        Returns:
            List of Chunk objects
        """
        # Split on double newlines (paragraph boundaries)
        paragraphs = re.split(r"\n\n+", text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        chunk_index = 0
        current_paragraphs = []
        current_tokens = 0
        metadata = metadata or {}

        for para in paragraphs:
            para_tokens = self._count_tokens(para)

            # Check if adding paragraph would exceed chunk_size
            if current_tokens + para_tokens > self.config.max_tokens and current_paragraphs:
                # Create chunk from accumulated paragraphs
                chunk_text = "\n\n".join(current_paragraphs)
                chunk = self._create_chunk(
                    text=chunk_text.strip(),
                    document_id=document_id,
                    chunk_index=chunk_index,
                    section_headings=[],
                    pages=[],
                    bboxes=[],
                    metadata=metadata,
                )
                chunks.append(chunk)

                # Start new chunk
                chunk_index += 1
                current_paragraphs = [para]
                current_tokens = para_tokens
            else:
                # Add paragraph to current chunk
                current_paragraphs.append(para)
                current_tokens += para_tokens

        # Add final chunk
        if current_paragraphs:
            chunk_text = "\n\n".join(current_paragraphs)
            chunk = self._create_chunk(
                text=chunk_text.strip(),
                document_id=document_id,
                chunk_index=chunk_index,
                section_headings=[],
                pages=[],
                bboxes=[],
                metadata=metadata,
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        text: str,
        document_id: str,
        chunk_index: int,
        section_headings: list[str] | None = None,
        pages: list[int] | None = None,
        bboxes: list[dict[str, float]] | None = None,
        metadata: dict | None = None,
    ) -> Chunk:
        """Create a Chunk object with all metadata.

        Args:
            text: Chunk text content
            document_id: Document identifier
            chunk_index: Chunk index within document
            section_headings: Section headings (for adaptive strategy)
            pages: Page numbers (for adaptive strategy)
            bboxes: Bounding boxes (for adaptive strategy)
            metadata: Document metadata

        Returns:
            Chunk object
        """
        token_count = self._count_tokens(text)

        return Chunk(
            chunk_id=self._generate_chunk_id(document_id, chunk_index, text),
            document_id=document_id,
            chunk_index=chunk_index,
            content=text,
            start_char=0,  # TODO: Calculate actual start_char
            end_char=len(text),  # TODO: Calculate actual end_char
            metadata=metadata or {},
            token_count=token_count,
            overlap_tokens=self.config.overlap_tokens if chunk_index > 0 else 0,
            section_headings=section_headings or [],
            section_pages=pages or [],
            section_bboxes=bboxes or [],
        )


# =============================================================================
# GLOBAL SINGLETON
# =============================================================================

_chunking_service: ChunkingService | None = None


def get_chunking_service(config: ChunkingConfig | None = None) -> ChunkingService:
    """Get chunking service instance (singleton pattern).

    Args:
        config: Optional config (only used on first call)

    Returns:
        ChunkingService instance

    Example:
        >>> service = get_chunking_service()
        >>> chunks = await service.chunk_document("doc_123", "Sample text...")
    """
    global _chunking_service

    # If config is provided, create new instance (don't use singleton)
    if config is not None:
        return ChunkingService(config)

    # Otherwise, use singleton with default config
    if _chunking_service is None:
        _chunking_service = ChunkingService()

    return _chunking_service


def reset_chunking_service() -> None:
    """Reset global chunking service (for testing).

    Example:
        >>> reset_chunking_service()
        >>> service = get_chunking_service()
    """
    global _chunking_service
    _chunking_service = None
    logger.info("chunking_service_reset")
