"""Unified Chunking Service.

Sprint 16 Feature 16.1 - Unified Chunking Service
ADR-022: Unified Chunking Service
Sprint 24 Feature 24.15 - Lazy imports for optional llama_index dependency

This module provides a single source of truth for document chunking
across all ingestion pipelines (Qdrant, BM25, LightRAG).

Benefits:
- Eliminates code duplication (70% reduction)
- Guarantees consistent chunk boundaries
- SHA-256 chunk_id enables graph-vector alignment
- Configuration-driven strategies
- Prometheus metrics for observability

Dependencies:
- fixed strategy: tiktoken only (always available)
- adaptive/paragraph strategies: llama_index (optional "ingestion" group)
- sentence strategy: no dependencies (regex only)
"""

import re
import time
from typing import TYPE_CHECKING

import structlog
import tiktoken
from prometheus_client import Counter, Gauge, Histogram

from src.core.chunk import Chunk, ChunkStrategy

# TYPE_CHECKING imports - needed for type hints (string literals)
# Runtime imports are lazy-loaded in methods
if TYPE_CHECKING:
    from llama_index.core.node_parser import SentenceSplitter

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


class ChunkingService:
    """Unified chunking service for all ingestion pipelines.

    Provides three chunking strategies:
    1. **fixed**: Fixed-size chunks using tiktoken (token-based, used by LightRAG)
    2. **adaptive**: Adaptive chunks using LlamaIndex SentenceSplitter (sentence-aware)
    3. **paragraph**: Paragraph-based chunks with separator (semantic boundaries)

    Example:
        >>> service = ChunkingService(ChunkStrategy(method="adaptive", chunk_size=512))
        >>> chunks = service.chunk_document("doc_001", "Sample text...", metadata={"source": "test.md"})
        >>> len(chunks)
        3
    """

    def __init__(self, strategy: ChunkStrategy | None = None) -> None:
        """Initialize chunking service with strategy.

        Args:
            strategy: Chunking strategy configuration (default: adaptive with 512 tokens, 128 overlap)
        """
        self.strategy = strategy or ChunkStrategy()
        self._chunker = self._init_chunker()

        logger.info(
            "chunking_service_initialized",
            method=self.strategy.method,
            chunk_size=self.strategy.chunk_size,
            overlap=self.strategy.overlap,
        )

    def _init_chunker(
        self,
    ) -> "SentenceSplitter | tiktoken.Encoding | None":  # String literal for type hint
        """Initialize chunker based on strategy.

        Sprint 24 Feature 24.15: Lazy import for adaptive/paragraph strategies.

        Returns:
            Chunker instance (SentenceSplitter for adaptive/paragraph, tiktoken for fixed, None for sentence)

        Raises:
            ImportError: If llama_index not installed for adaptive/paragraph strategies
        """
        if self.strategy.method == "fixed":
            # Fixed-size chunking with tiktoken (token-accurate, used by LightRAG)
            # NO llama_index needed!
            try:
                return tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.error("tiktoken_init_failed", error=str(e))
                raise

        elif self.strategy.method in ("adaptive", "paragraph"):
            # ================================================================
            # LAZY IMPORT: llama_index (Sprint 24 Feature 24.15)
            # ================================================================
            # Adaptive/paragraph chunking requires SentenceSplitter from llama_index.
            # Load it lazily only when these strategies are used.
            # ================================================================
            try:
                from llama_index.core.node_parser import SentenceSplitter
            except ImportError as e:
                error_msg = (
                    f"llama_index is required for '{self.strategy.method}' chunking strategy but is not installed.\n\n"
                    "INSTALLATION OPTIONS:\n"
                    "1. poetry install --with ingestion\n"
                    "2. poetry install --all-extras\n\n"
                    "ALTERNATIVE STRATEGIES (no llama_index needed):\n"
                    "- 'fixed': Token-based chunking with tiktoken\n"
                    "- 'sentence': Regex-based sentence chunking\n"
                )
                logger.error(
                    "llamaindex_import_failed",
                    strategy=self.strategy.method,
                    error=str(e),
                    install_command="poetry install --with ingestion",
                )
                raise ImportError(error_msg) from e

            return SentenceSplitter(
                chunk_size=self.strategy.chunk_size,
                chunk_overlap=self.strategy.overlap,
                separator=self.strategy.separator if self.strategy.method == "paragraph" else " ",
            )

        elif self.strategy.method == "sentence":
            # Sentence-based chunking (simple regex, no external chunker needed)
            # NO llama_index needed!
            return None

        else:
            raise ValueError(f"Unknown chunking method: {self.strategy.method}")

    def chunk_document(
        self,
        document_id: str,
        content: str,
        metadata: dict | None = None,
    ) -> list[Chunk]:
        """Chunk a document into uniform chunks.

        Args:
            document_id: Unique document identifier
            content: Document text content
            metadata: Additional metadata to attach to chunks

        Returns:
            List of Chunk objects with consistent IDs, boundaries, metadata

        Raises:
            ValueError: If content is empty or chunking fails

        Example:
            >>> service = ChunkingService()
            >>> chunks = service.chunk_document("doc_001", "Sample text...", {"source": "test.md"})
            >>> chunks[0].chunk_id
            'a1b2c3d4e5f6g7h8'
        """
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")

        logger.info(
            "chunking_document_start",
            document_id=document_id,
            content_length=len(content),
            method=self.strategy.method,
        )

        # Measure chunking duration
        start_time = time.time()

        # Route to appropriate chunking method
        if self.strategy.method == "fixed":
            chunks = self._chunk_fixed(document_id, content, metadata)
        elif self.strategy.method == "adaptive":
            chunks = self._chunk_adaptive(document_id, content, metadata)
        elif self.strategy.method == "paragraph":
            chunks = self._chunk_paragraph(document_id, content, metadata)
        elif self.strategy.method == "sentence":
            chunks = self._chunk_sentence(document_id, content, metadata)
        else:
            raise ValueError(f"Unknown chunking method: {self.strategy.method}")

        # Record metrics
        duration = time.time() - start_time
        strategy_label = self.strategy.method

        chunking_duration_seconds.labels(strategy=strategy_label).observe(duration)
        chunks_created_total.labels(strategy=strategy_label).inc(len(chunks))
        documents_chunked_total.labels(strategy=strategy_label).inc()

        if chunks:
            avg_tokens = sum(c.token_count for c in chunks) / len(chunks)
            avg_chunk_size_tokens.labels(strategy=strategy_label).set(avg_tokens)

        logger.info(
            "chunking_document_complete",
            document_id=document_id,
            chunks_created=len(chunks),
            avg_tokens_per_chunk=sum(c.token_count for c in chunks) / len(chunks) if chunks else 0,
            duration_seconds=duration,
        )

        return chunks

    def _chunk_fixed(
        self,
        document_id: str,
        content: str,
        metadata: dict | None,
    ) -> list[Chunk]:
        """Fixed-size chunking using tiktoken (token-based).

        This method provides token-accurate chunking using tiktoken,
        matching the behavior of LightRAG for consistency.

        Args:
            document_id: Document identifier
            content: Document text
            metadata: Additional metadata

        Returns:
            List of fixed-size chunks
        """
        if not isinstance(self._chunker, tiktoken.Encoding):
            raise RuntimeError("Fixed chunking requires tiktoken encoder")

        encoder = self._chunker
        tokens = encoder.encode(content)
        total_tokens = len(tokens)

        chunks = []
        chunk_index = 0
        start_token = 0

        while start_token < total_tokens:
            # Calculate end token for this chunk
            end_token = min(start_token + self.strategy.chunk_size, total_tokens)

            # Extract chunk tokens
            chunk_tokens = tokens[start_token:end_token]
            chunk_text = encoder.decode(chunk_tokens)

            # Calculate character offsets (approximate, since tiktoken is token-based)
            # We use the start of the decoded text in the original content
            start_char = content.find(chunk_text[:50])  # Find first 50 chars
            if start_char == -1:
                start_char = 0
            end_char = start_char + len(chunk_text)

            # Generate chunk_id
            chunk_id = Chunk.generate_chunk_id(document_id, chunk_index, chunk_text)

            # Calculate overlap tokens
            overlap_tokens = self.strategy.overlap if chunk_index > 0 else 0

            # Create chunk
            chunk = Chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                chunk_index=chunk_index,
                content=chunk_text,
                start_char=start_char,
                end_char=end_char,
                metadata=metadata or {},
                token_count=len(chunk_tokens),
                overlap_tokens=overlap_tokens,
            )

            chunks.append(chunk)

            # Move to next chunk with overlap
            chunk_index += 1
            start_token = end_token - self.strategy.overlap

            # Prevent infinite loop on last small chunk
            if start_token >= total_tokens - self.strategy.overlap:
                break

        return chunks

    def _chunk_adaptive(
        self,
        document_id: str,
        content: str,
        metadata: dict | None,
    ) -> list[Chunk]:
        """Adaptive chunking using LlamaIndex SentenceSplitter (sentence-aware).

        Sprint 24 Feature 24.15: Lazy import for llama_index types.

        This method provides sentence-aware chunking that respects
        sentence boundaries for better semantic coherence.

        Args:
            document_id: Document identifier
            content: Document text
            metadata: Additional metadata

        Returns:
            List of adaptive chunks

        Raises:
            ImportError: If llama_index not installed
        """
        # ====================================================================
        # LAZY IMPORT: llama_index (Sprint 24 Feature 24.15)
        # ====================================================================
        # Document and TextNode are needed for adaptive chunking.
        # SentenceSplitter is already lazy-loaded in _init_chunker().
        # ====================================================================
        try:
            from llama_index.core import Document
            from llama_index.core.node_parser import SentenceSplitter
            from llama_index.core.schema import TextNode
        except ImportError as e:
            error_msg = (
                "llama_index is required for adaptive chunking but is not installed.\n\n"
                "INSTALLATION OPTIONS:\n"
                "1. poetry install --with ingestion\n"
                "2. poetry install --all-extras\n"
            )
            logger.error(
                "llamaindex_import_failed",
                method="_chunk_adaptive",
                error=str(e),
            )
            raise ImportError(error_msg) from e

        if not isinstance(self._chunker, SentenceSplitter):
            raise RuntimeError("Adaptive chunking requires SentenceSplitter")

        # Create LlamaIndex Document
        doc = Document(text=content, metadata=metadata or {})

        # Get nodes from SentenceSplitter
        nodes: list[TextNode] = self._chunker.get_nodes_from_documents([doc])

        chunks = []
        for idx, node in enumerate(nodes):
            chunk_text = node.get_content()

            # Generate chunk_id
            chunk_id = Chunk.generate_chunk_id(document_id, idx, chunk_text)

            # Calculate overlap tokens (approximate from previous chunk)
            overlap_tokens = self.strategy.overlap if idx > 0 else 0

            # Estimate token count (simple whitespace split approximation)
            token_count = len(chunk_text.split())

            # Create chunk
            chunk = Chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                chunk_index=idx,
                content=chunk_text,
                start_char=node.start_char_idx or 0,
                end_char=node.end_char_idx or len(chunk_text),
                metadata={**(metadata or {}), **node.metadata},
                token_count=token_count,
                overlap_tokens=overlap_tokens,
            )

            chunks.append(chunk)

        return chunks

    def _chunk_paragraph(
        self,
        document_id: str,
        content: str,
        metadata: dict | None,
    ) -> list[Chunk]:
        """Paragraph-based chunking with separator (semantic boundaries).

        Sprint 24 Feature 24.15: Lazy import for llama_index types.

        This method splits on paragraph boundaries (default: \\n\\n)
        and groups paragraphs to meet target chunk size.

        Args:
            document_id: Document identifier
            content: Document text
            metadata: Additional metadata

        Returns:
            List of paragraph-based chunks

        Raises:
            ImportError: If llama_index not installed
        """
        # ====================================================================
        # LAZY IMPORT: llama_index (Sprint 24 Feature 24.15)
        # ====================================================================
        # Document and TextNode are needed for paragraph chunking.
        # SentenceSplitter is already lazy-loaded in _init_chunker().
        # ====================================================================
        try:
            from llama_index.core import Document
            from llama_index.core.node_parser import SentenceSplitter
            from llama_index.core.schema import TextNode
        except ImportError as e:
            error_msg = (
                "llama_index is required for paragraph chunking but is not installed.\n\n"
                "INSTALLATION OPTIONS:\n"
                "1. poetry install --with ingestion\n"
                "2. poetry install --all-extras\n"
            )
            logger.error(
                "llamaindex_import_failed",
                method="_chunk_paragraph",
                error=str(e),
            )
            raise ImportError(error_msg) from e

        if not isinstance(self._chunker, SentenceSplitter):
            raise RuntimeError("Paragraph chunking requires SentenceSplitter")

        # SentenceSplitter with separator already configured in _init_chunker
        doc = Document(text=content, metadata=metadata or {})
        nodes: list[TextNode] = self._chunker.get_nodes_from_documents([doc])

        chunks = []
        for idx, node in enumerate(nodes):
            chunk_text = node.get_content()

            # Generate chunk_id
            chunk_id = Chunk.generate_chunk_id(document_id, idx, chunk_text)

            # Calculate overlap tokens
            overlap_tokens = self.strategy.overlap if idx > 0 else 0

            # Estimate token count
            token_count = len(chunk_text.split())

            # Create chunk
            chunk = Chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                chunk_index=idx,
                content=chunk_text,
                start_char=node.start_char_idx or 0,
                end_char=node.end_char_idx or len(chunk_text),
                metadata={**(metadata or {}), **node.metadata},
                token_count=token_count,
                overlap_tokens=overlap_tokens,
            )

            chunks.append(chunk)

        return chunks

    def _chunk_sentence(
        self,
        document_id: str,
        content: str,
        metadata: dict | None,
    ) -> list[Chunk]:
        """Sentence-based chunking (simple regex).

        This method splits on sentence boundaries (. ! ?)
        and groups sentences to meet target chunk size.

        Args:
            document_id: Document identifier
            content: Document text
            metadata: Additional metadata

        Returns:
            List of sentence-based chunks
        """
        # Split into sentences using regex
        sentence_pattern = r"(?<=[.!?])\s+"
        sentences = re.split(sentence_pattern, content)

        chunks = []
        chunk_index = 0
        current_chunk = []
        current_tokens = 0
        start_char = 0

        for sentence in sentences:
            sentence_tokens = len(sentence.split())

            # Check if adding this sentence would exceed chunk_size
            if current_tokens + sentence_tokens > self.strategy.chunk_size and current_chunk:
                # Create chunk from accumulated sentences
                chunk_text = " ".join(current_chunk)
                chunk_id = Chunk.generate_chunk_id(document_id, chunk_index, chunk_text)

                chunk = Chunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    chunk_index=chunk_index,
                    content=chunk_text,
                    start_char=start_char,
                    end_char=start_char + len(chunk_text),
                    metadata=metadata or {},
                    token_count=current_tokens,
                    overlap_tokens=self.strategy.overlap if chunk_index > 0 else 0,
                )

                chunks.append(chunk)

                # Start new chunk (with overlap if configured)
                chunk_index += 1
                start_char += len(chunk_text)

                # Keep last few sentences for overlap (approximate)
                overlap_sentences = []
                overlap_tokens_count = 0
                for s in reversed(current_chunk):
                    s_tokens = len(s.split())
                    if overlap_tokens_count + s_tokens <= self.strategy.overlap:
                        overlap_sentences.insert(0, s)
                        overlap_tokens_count += s_tokens
                    else:
                        break

                current_chunk = overlap_sentences
                current_tokens = overlap_tokens_count

            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # Add final chunk if there's remaining content
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk_id = Chunk.generate_chunk_id(document_id, chunk_index, chunk_text)

            chunk = Chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                chunk_index=chunk_index,
                content=chunk_text,
                start_char=start_char,
                end_char=start_char + len(chunk_text),
                metadata=metadata or {},
                token_count=current_tokens,
                overlap_tokens=self.strategy.overlap if chunk_index > 0 else 0,
            )

            chunks.append(chunk)

        return chunks


# Global singleton
_chunking_service: ChunkingService | None = None


def get_chunking_service(strategy: ChunkStrategy | None = None) -> ChunkingService:
    """Get global chunking service instance.

    Args:
        strategy: Optional strategy to use (default: adaptive with 512 tokens, 128 overlap)

    Returns:
        ChunkingService instance

    Example:
        >>> service = get_chunking_service()
        >>> chunks = service.chunk_document("doc_001", "Sample text...")
    """
    global _chunking_service

    # If strategy is provided, create new instance (don't use singleton)
    if strategy is not None:
        return ChunkingService(strategy)

    # Otherwise, use singleton with default strategy
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
