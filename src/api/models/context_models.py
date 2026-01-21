"""Pydantic models for Long Context API.

Sprint 112 Feature 112.1: Long Context Backend APIs

This module defines request/response models for the context management API,
providing structured data for document metadata, chunk exploration,
compression strategies, and export functionality.

Models:
    - ContextDocument: Document with token counts and status
    - ContextDocumentListResponse: List of documents
    - ContextMetricsResponse: Aggregated context statistics
    - DocumentChunk: Individual chunk with relevance score
    - ChunkListResponse: List of chunks for a document
    - CompressionRequest: Compression strategy request
    - CompressionResponse: Compression result
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Metadata for a document chunk.

    Attributes:
        section: Section header from document
        source: Source filename
        page_number: Page number (for PDFs)
    """

    section: str | None = Field(None, description="Section header from document")
    source: str | None = Field(None, description="Source filename")
    page_number: int | None = Field(None, description="Page number (for PDFs)")


class DocumentChunk(BaseModel):
    """Individual chunk from a document with relevance scoring.

    Attributes:
        id: Unique chunk identifier
        content: Text content of the chunk
        relevance_score: Relevance score (0.0-1.0)
        token_count: Number of tokens in this chunk
        chunk_index: Position in document (0-indexed)
        metadata: Additional chunk metadata
    """

    id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Text content of the chunk")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")
    token_count: int = Field(..., description="Number of tokens in this chunk")
    chunk_index: int = Field(..., ge=0, description="Position in document (0-indexed)")
    metadata: ChunkMetadata | None = Field(None, description="Additional metadata")


class ContextDocument(BaseModel):
    """Document with context metadata.

    Attributes:
        id: Unique document identifier
        name: Original filename
        token_count: Total tokens in document
        chunk_count: Number of chunks
        uploaded_at: Upload timestamp
        status: Processing status (ready/processing/error)
        namespace: Document namespace
        metadata: Additional document metadata
    """

    id: str = Field(..., description="Unique document identifier")
    name: str = Field(..., description="Original filename")
    token_count: int = Field(..., description="Total tokens in document")
    chunk_count: int = Field(..., description="Number of chunks")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    status: Literal["ready", "processing", "error"] = Field(..., description="Processing status")
    namespace: str | None = Field(None, description="Document namespace")
    metadata: dict | None = Field(None, description="Additional metadata")


class ContextDocumentListResponse(BaseModel):
    """Response for listing context documents.

    Attributes:
        documents: List of documents
        total: Total number of documents
    """

    documents: list[ContextDocument] = Field(..., description="List of documents")
    total: int = Field(..., description="Total number of documents")


class ContextMetricsResponse(BaseModel):
    """Aggregated context window metrics.

    Attributes:
        total_tokens: Total tokens across all documents
        max_tokens: Maximum context window size (default 128K)
        document_count: Number of documents
        average_relevance: Average relevance score across chunks
        chunks_total: Total number of chunks
        utilization_percent: Context window utilization percentage
    """

    total_tokens: int = Field(..., description="Total tokens across all documents")
    max_tokens: int = Field(default=128000, description="Maximum context window size")
    document_count: int = Field(..., description="Number of documents")
    average_relevance: float = Field(..., ge=0.0, le=1.0, description="Average relevance score")
    chunks_total: int = Field(default=0, description="Total number of chunks")
    utilization_percent: float = Field(
        default=0.0, description="Context window utilization percentage"
    )


class ChunkListResponse(BaseModel):
    """Response for listing document chunks.

    Attributes:
        chunks: List of chunks
        total: Total number of chunks
        document_id: Parent document ID
    """

    chunks: list[DocumentChunk] = Field(..., description="List of chunks")
    total: int = Field(..., description="Total number of chunks")
    document_id: str | None = Field(None, description="Parent document ID")


class CompressionRequest(BaseModel):
    """Request for context compression.

    Attributes:
        document_id: Specific document to compress (optional)
        strategy: Compression strategy to apply
        target_reduction: Target reduction percentage (10-90)
        min_relevance_threshold: Minimum relevance score to keep
        max_chunks: Maximum chunks to keep (for truncation)
    """

    document_id: str | None = Field(None, description="Specific document to compress (optional)")
    strategy: Literal["summarization", "filtering", "truncation", "hybrid"] = Field(
        ..., description="Compression strategy"
    )
    target_reduction: int = Field(
        default=50, ge=10, le=90, description="Target reduction percentage"
    )
    min_relevance_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum relevance score to keep"
    )
    max_chunks: int | None = Field(
        None, ge=1, description="Maximum chunks to keep (for truncation)"
    )


class CompressionResponse(BaseModel):
    """Response from context compression.

    Attributes:
        original_tokens: Token count before compression
        compressed_tokens: Token count after compression
        reduction_percent: Actual reduction achieved
        chunks_removed: Number of chunks removed
        strategy_applied: Strategy that was applied
        document_id: Document that was compressed (if specific)
    """

    original_tokens: int = Field(..., description="Token count before compression")
    compressed_tokens: int = Field(..., description="Token count after compression")
    reduction_percent: float = Field(..., description="Actual reduction achieved")
    chunks_removed: int = Field(default=0, description="Number of chunks removed")
    strategy_applied: str = Field(..., description="Strategy that was applied")
    document_id: str | None = Field(None, description="Document that was compressed")
