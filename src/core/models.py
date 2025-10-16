"""Pydantic models for API requests and responses."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class QueryIntent(str, Enum):
    """Query intent classification."""

    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"
    MEMORY = "memory"


class QueryMode(str, Enum):
    """Query mode for retrieval."""

    NAIVE = "naive"
    LOCAL = "local"
    GLOBAL = "global"
    HYBRID = "hybrid"


class DocumentChunk(BaseModel):
    """Document chunk with metadata."""

    id: str = Field(..., description="Unique chunk ID")
    content: str = Field(..., description="Chunk text content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    score: float | None = Field(None, description="Relevance score", ge=0.0, le=1.0)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "id": "doc1_chunk1",
                "content": "This is a sample document chunk.",
                "metadata": {"source": "doc1.pdf", "page": 1},
                "score": 0.95,
            }
        }


class QueryRequest(BaseModel):
    """Request model for RAG query."""

    query: str = Field(..., description="User query", min_length=1, max_length=2000)
    mode: QueryMode = Field(default=QueryMode.HYBRID, description="Query mode for retrieval")
    top_k: int = Field(default=5, description="Number of results to retrieve", ge=1, le=50)
    score_threshold: float = Field(
        default=0.7, description="Minimum relevance score", ge=0.0, le=1.0
    )
    use_memory: bool = Field(default=True, description="Include memory in context")
    conversation_id: str | None = Field(None, description="Conversation ID for memory")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate and clean query."""
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "query": "What are the main components of AEGIS RAG?",
                "mode": "hybrid",
                "top_k": 5,
                "score_threshold": 0.7,
                "use_memory": True,
                "conversation_id": "conv-123",
            }
        }


class QueryResponse(BaseModel):
    """Response model for RAG query."""

    answer: str = Field(..., description="Generated answer")
    sources: list[DocumentChunk] = Field(default_factory=list, description="Source documents used")
    query_intent: QueryIntent = Field(..., description="Detected query intent")
    processing_time_ms: float = Field(..., description="Query processing time in milliseconds")
    conversation_id: str | None = Field(None, description="Conversation ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "answer": "AEGIS RAG consists of four main components...",
                "sources": [
                    {
                        "id": "doc1_chunk1",
                        "content": "Component 1: Vector Search...",
                        "metadata": {"source": "architecture.md"},
                        "score": 0.95,
                    }
                ],
                "query_intent": "hybrid",
                "processing_time_ms": 450.5,
                "conversation_id": "conv-123",
                "metadata": {"agent_steps": 3},
            }
        }


class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseModel):
    """Health status for a single service."""

    status: HealthStatus = Field(..., description="Service health status")
    latency_ms: float | None = Field(None, description="Service response latency")
    error: str | None = Field(None, description="Error message if unhealthy")


class HealthResponse(BaseModel):
    """Health check response."""

    status: HealthStatus = Field(..., description="Overall system health")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    services: dict[str, ServiceHealth] = Field(
        default_factory=dict, description="Individual service health"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "timestamp": "2025-01-15T10:00:00Z",
                "services": {
                    "qdrant": {"status": "healthy", "latency_ms": 5.2, "error": None},
                    "neo4j": {"status": "healthy", "latency_ms": 12.8, "error": None},
                    "redis": {"status": "healthy", "latency_ms": 1.5, "error": None},
                    "ollama": {"status": "healthy", "latency_ms": 50.0, "error": None},
                },
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Query cannot be empty",
                "details": {"field": "query"},
                "timestamp": "2025-01-15T10:00:00Z",
            }
        }


# ============================================================================
# Graph RAG Models (Sprint 5)
# ============================================================================


class GraphEntity(BaseModel):
    """Graph entity (node) representation."""

    id: str = Field(..., description="Unique entity ID")
    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type (PERSON, ORGANIZATION, etc.)")
    description: str = Field(default="", description="Entity description")
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Additional entity properties"
    )
    source_document: str | None = Field(None, description="Source document ID")
    confidence: float = Field(default=1.0, description="Extraction confidence score", ge=0.0, le=1.0)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "id": "entity_1",
                "name": "John Smith",
                "type": "PERSON",
                "description": "Software engineer at Google",
                "properties": {"aliases": ["J. Smith", "Johnny"]},
                "source_document": "doc_123",
                "confidence": 0.95,
            }
        }


class GraphRelationship(BaseModel):
    """Graph relationship (edge) representation."""

    id: str = Field(..., description="Unique relationship ID")
    source: str = Field(..., description="Source entity name or ID")
    target: str = Field(..., description="Target entity name or ID")
    type: str = Field(..., description="Relationship type (WORKS_AT, KNOWS, etc.)")
    description: str = Field(default="", description="Relationship description")
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Additional relationship properties"
    )
    source_document: str | None = Field(None, description="Source document ID")
    confidence: float = Field(default=1.0, description="Extraction confidence score", ge=0.0, le=1.0)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "id": "rel_1",
                "source": "John Smith",
                "target": "Google",
                "type": "WORKS_AT",
                "description": "John Smith works at Google",
                "properties": {"since": "2020-01-01"},
                "source_document": "doc_123",
                "confidence": 0.92,
            }
        }


class Topic(BaseModel):
    """Topic/community extracted from knowledge graph."""

    id: str = Field(..., description="Unique topic ID")
    name: str = Field(..., description="Topic name")
    summary: str = Field(default="", description="Topic summary/description")
    entities: list[str] = Field(default_factory=list, description="Entity IDs in this topic")
    keywords: list[str] = Field(default_factory=list, description="Topic keywords")
    score: float = Field(default=0.0, description="Topic relevance score", ge=0.0, le=1.0)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "id": "topic_1",
                "name": "Machine Learning at Tech Companies",
                "summary": "Discussion of machine learning applications in major tech companies",
                "entities": ["entity_1", "entity_2", "entity_3"],
                "keywords": ["machine learning", "AI", "Google", "technology"],
                "score": 0.88,
            }
        }


class GraphQueryResult(BaseModel):
    """Graph query result with entities, relationships, and topics."""

    query: str = Field(..., description="Original query")
    answer: str = Field(default="", description="LLM-generated answer from graph context")
    entities: list[GraphEntity] = Field(default_factory=list, description="Retrieved entities")
    relationships: list[GraphRelationship] = Field(
        default_factory=list, description="Retrieved relationships"
    )
    topics: list[Topic] = Field(default_factory=list, description="Retrieved topics (global search)")
    context: str = Field(default="", description="Graph context used for answer generation")
    mode: str = Field(default="local", description="Search mode (local/global/hybrid)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Query metadata")

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "query": "What companies has John Smith worked for?",
                "answer": "John Smith has worked for Google (2020-present) and Microsoft (2015-2020).",
                "entities": [
                    {
                        "id": "e1",
                        "name": "John Smith",
                        "type": "PERSON",
                        "description": "Software engineer",
                        "properties": {},
                        "source_document": "doc_1",
                        "confidence": 0.95,
                    }
                ],
                "relationships": [
                    {
                        "id": "r1",
                        "source": "John Smith",
                        "target": "Google",
                        "type": "WORKS_AT",
                        "description": "Employment relationship",
                        "properties": {},
                        "source_document": "doc_1",
                        "confidence": 0.92,
                    }
                ],
                "topics": [],
                "context": "John Smith-WORKS_AT->Google...",
                "mode": "local",
                "metadata": {"execution_time_ms": 250, "entities_found": 2},
            }
        }
