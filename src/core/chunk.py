"""Unified Chunk Data Models.

Sprint 16 Feature 16.1 - Unified Chunking Service
ADR-022: Unified Chunking Service

This module defines Pydantic models for representing chunks
across all ingestion pipelines (Qdrant, BM25, LightRAG).
"""

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class ChunkStrategy(BaseModel):
    """Configuration for chunking strategy.

    Supports multiple chunking methods with configurable parameters.
    """

    method: Literal["fixed", "adaptive", "paragraph", "sentence"] = Field(
        default="adaptive",
        description="Chunking method to use",
    )
    chunk_size: int = Field(
        default=512,
        ge=128,
        le=2048,
        description="Target chunk size in tokens",
    )
    overlap: int = Field(
        default=128,
        ge=0,
        le=512,
        description="Overlap between chunks in tokens",
    )
    separator: str = Field(
        default="\n\n",
        description="Text separator for splitting (paragraph/sentence methods)",
    )

    @field_validator("overlap")
    @classmethod
    def validate_overlap(cls, v: int, info: ValidationInfo) -> int:
        """Ensure overlap is less than chunk_size."""
        chunk_size = info.data.get("chunk_size", 512)
        if v >= chunk_size:
            raise ValueError(f"Overlap ({v}) must be less than chunk_size ({chunk_size})")
        return v


class Chunk(BaseModel):
    """Unified chunk representation.

    This model represents a text chunk with consistent metadata
    across all ingestion pipelines (Qdrant, BM25, LightRAG).

    Attributes:
        chunk_id: Unique identifier (SHA-256 hash of content)
        document_id: Source document identifier
        chunk_index: Sequential index within document (0, 1, 2, ...)
        content: Text content of the chunk
        start_char: Starting character offset in document
        end_char: Ending character offset in document
        metadata: Additional metadata from source document
        token_count: Number of tokens in chunk
        overlap_tokens: Number of tokens overlapping with previous chunk
    """

    chunk_id: str = Field(
        ...,
        description="SHA-256 hash of content for deterministic identification",
        min_length=16,
        max_length=64,
    )
    document_id: str = Field(
        ...,
        description="Source document identifier",
        min_length=1,
    )
    chunk_index: int = Field(
        ...,
        ge=0,
        description="Sequential index within document",
    )
    content: str = Field(
        ...,
        description="Text content of the chunk",
        min_length=1,
    )
    start_char: int = Field(
        ...,
        ge=0,
        description="Starting character offset in document",
    )
    end_char: int = Field(
        ...,
        ge=0,
        description="Ending character offset in document",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from source document",
    )
    token_count: int = Field(
        default=0,
        ge=0,
        description="Number of tokens in chunk",
    )
    overlap_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of tokens overlapping with previous chunk",
    )

    # Section metadata (Sprint 36 Feature 36.6 - TD-054)
    section_headings: list[str] = Field(
        default_factory=list,
        description="Section headings for this chunk (multi-section support)",
    )
    section_pages: list[int] = Field(
        default_factory=list,
        description="Page numbers where sections appear",
    )
    section_bboxes: list[dict[str, float]] = Field(
        default_factory=list,
        description="Bounding boxes for each section",
    )
    primary_section: str | None = Field(
        default=None,
        description="Primary/dominant section heading in this chunk (for multi-section chunks)",
    )

    # Document type support (Sprint 62 Feature 62.7)
    document_type: str = Field(
        default="unknown",
        description="Document type (pdf, docx, html, md, txt, xlsx, pptx, unknown)",
    )

    @field_validator("end_char")
    @classmethod
    def validate_end_char(cls, v: int, info: ValidationInfo) -> int:
        """Ensure end_char >= start_char."""
        start_char = info.data.get("start_char", 0)
        if v < start_char:
            raise ValueError(f"end_char ({v}) must be >= start_char ({start_char})")
        return v

    @staticmethod
    def generate_chunk_id(document_id: str, chunk_index: int, content: str) -> str:
        """Generate deterministic chunk_id using SHA-256 hash in UUID4 format.

        Args:
            document_id: Source document identifier
            chunk_index: Sequential index within document
            content: Text content of the chunk

        Returns:
            UUID4-formatted string (32 hex chars with dashes: 8-4-4-4-12)

        Example:
            >>> Chunk.generate_chunk_id("doc_001", 0, "Sample text")
            'a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6'
        """
        input_str = f"{document_id}:{chunk_index}:{content}"
        hash_hex = hashlib.sha256(input_str.encode("utf-8")).hexdigest()[:32]
        # Format as UUID4: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        return f"{hash_hex[:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}-{hash_hex[20:32]}"  # noqa: E501

    def to_qdrant_payload(self) -> dict[str, Any]:
        """Convert chunk to Qdrant point payload.

        Returns:
            Dictionary suitable for Qdrant PointStruct.payload
        """
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "text": self.content,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "token_count": self.token_count,
            "section_headings": self.section_headings,
            "section_pages": self.section_pages,
            "section_bboxes": self.section_bboxes,
            "document_type": self.document_type,
            **self.metadata,
        }

    def to_bm25_document(self) -> dict[str, Any]:  # noqa: N802 (BM25 is an acronym)
        """Convert chunk to BM25 document format.

        Returns:
            Dictionary with text and metadata for BM25 indexing
        """
        return {
            "text": self.content,
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
            "document_type": self.document_type,
            **self.metadata,
        }

    def to_lightrag_format(self) -> dict[str, Any]:
        """Convert chunk to LightRAG format for Neo4j storage.

        Returns:
            Dictionary with chunk metadata for Neo4j :chunk nodes
        """
        return {
            "chunk_id": self.chunk_id,
            "text": self.content,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "tokens": self.token_count,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "document_type": self.document_type,
        }

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "chunk_id": "a1b2c3d4e5f6g7h8",
                    "document_id": "doc_001",
                    "chunk_index": 0,
                    "content": (
                        "AegisRAG is a hybrid RAG system combining vector search, "
                        "graph reasoning, and temporal memory."
                    ),
                    "start_char": 0,
                    "end_char": 92,
                    "metadata": {"source": "README.md", "section": "Overview"},
                    "token_count": 23,
                    "overlap_tokens": 0,
                }
            ]
        }
    }
