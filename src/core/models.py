"""Pydantic models for API requests and responses."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "doc1_chunk1",
                "content": "This is a sample document chunk.",
                "metadata": {"source": "doc1.pdf", "page": 1},
                "score": 0.95,
            }
        }
    )

    id: str = Field(..., description="Unique chunk ID")
    content: str = Field(..., description="Chunk text content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    score: float | None = Field(None, description="Relevance score", ge=0.0, le=1.0)


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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "What are the main components of AEGIS RAG?",
                "mode": "hybrid",
                "top_k": 5,
                "score_threshold": 0.7,
                "use_memory": True,
                "conversation_id": "conv-123",
            }
        }
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate and clean query."""
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v


class QueryResponse(BaseModel):
    """Response model for RAG query."""

    model_config = ConfigDict(
        json_schema_extra={
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
    )

    answer: str = Field(..., description="Generated answer")
    sources: list[DocumentChunk] = Field(default_factory=list, description="Source documents used")
    query_intent: QueryIntent = Field(..., description="Detected query intent")
    processing_time_ms: float = Field(..., description="Query processing time in milliseconds")
    conversation_id: str | None = Field(None, description="Conversation ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


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

    model_config = ConfigDict(
        json_schema_extra={
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
    )

    status: HealthStatus = Field(..., description="Overall system health")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    services: dict[str, ServiceHealth] = Field(
        default_factory=dict, description="Individual service health"
    )


class ErrorCode:
    """Standard error codes used across the API (Sprint 22 Feature 22.2.2).

    Machine-readable error codes for programmatic error handling.
    """

    # 4xx Client Errors
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    CONFLICT = "CONFLICT"
    UNPROCESSABLE_ENTITY = "UNPROCESSABLE_ENTITY"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"

    # 5xx Server Errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    GATEWAY_TIMEOUT = "GATEWAY_TIMEOUT"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"  # Sprint 117.12

    # Business Logic Errors (Sprint 22)
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    INGESTION_FAILED = "INGESTION_FAILED"
    VECTOR_SEARCH_FAILED = "VECTOR_SEARCH_FAILED"
    GRAPH_QUERY_FAILED = "GRAPH_QUERY_FAILED"
    DATABASE_CONNECTION_FAILED = "DATABASE_CONNECTION_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Domain Management Errors (Sprint 117.8)
    DOMAIN_NOT_FOUND = "DOMAIN_NOT_FOUND"  # 404
    DOMAIN_ALREADY_EXISTS = "DOMAIN_ALREADY_EXISTS"  # 409
    TRAINING_IN_PROGRESS = "TRAINING_IN_PROGRESS"  # 409
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"  # 403


class ErrorDetail(BaseModel):
    """Detailed error information (Sprint 22 Feature 22.2.2).

    Standardized error format with request correlation support.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "INVALID_FILE_FORMAT",
                "message": "Invalid file format: document.xyz",
                "details": {
                    "filename": "document.xyz",
                    "expected_formats": [".pdf", ".docx", ".txt"],
                },
                "request_id": "a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6",
                "timestamp": "2025-11-11T14:30:00Z",
                "path": "/api/v1/retrieval/upload",
            }
        }
    )

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(None, description="Additional error context")
    request_id: str = Field(..., description="Request ID for log correlation")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    path: str = Field(..., description="API endpoint that generated error")


class ErrorResponse(BaseModel):
    """Top-level error response wrapper (Sprint 22 Feature 22.2.2).

    All API errors return this standardized format.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": "Request validation failed",
                    "details": {"field": "query", "issue": "Query cannot be empty"},
                    "request_id": "a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6",
                    "timestamp": "2025-11-11T14:30:00Z",
                    "path": "/api/v1/retrieval/search",
                }
            }
        }
    )

    error: ErrorDetail = Field(..., description="Error details")


# ============================================================================
# Graph RAG Models (Sprint 5)
# ============================================================================


class GraphEntity(BaseModel):
    """Graph entity (node) representation."""

    id: str = Field(..., description="Unique entity ID")
    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type (PERSON, ORGANIZATION, etc.)")
    sub_type: str | None = Field(
        None,
        description="Domain-specific Tier 2 sub-type (e.g., DISEASE, COMPONENT). "
        "Sprint 126: Preserved from LLM output before universal type mapping.",
    )
    description: str = Field(default="", description="Entity description")
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Additional entity properties"
    )
    source_document: str | None = Field(None, description="Source document ID")
    confidence: float = Field(
        default=1.0, description="Extraction confidence score", ge=0.0, le=1.0
    )
    # Temporal fields (Sprint 6.4: Bi-Temporal Model)
    version_id: str | None = Field(None, description="Unique version ID")
    version_number: int = Field(default=1, description="Version sequence number")
    valid_from: datetime | None = Field(None, description="Valid time start (real-world time)")
    valid_to: datetime | None = Field(None, description="Valid time end (None=current)")
    transaction_from: datetime | None = Field(
        None, description="Transaction time start (database time)"
    )
    transaction_to: datetime | None = Field(None, description="Transaction time end (None=current)")
    changed_by: str = Field(default="system", description="User/system that made the change")
    change_reason: str = Field(default="", description="Reason for the change")

    model_config = ConfigDict(
        json_schema_extra={
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
    )


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
    confidence: float = Field(
        default=1.0, description="Extraction confidence score", ge=0.0, le=1.0
    )

    model_config = ConfigDict(
        json_schema_extra={
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
    )


class Topic(BaseModel):
    """Topic/community extracted from knowledge graph."""

    id: str = Field(..., description="Unique topic ID")
    name: str = Field(..., description="Topic name")
    summary: str = Field(default="", description="Topic summary/description")
    entities: list[str] = Field(default_factory=list, description="Entity IDs in this topic")
    keywords: list[str] = Field(default_factory=list, description="Topic keywords")
    score: float = Field(default=0.0, description="Topic relevance score", ge=0.0, le=1.0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "topic_1",
                "name": "Machine Learning at Tech Companies",
                "summary": "Discussion of machine learning applications in major tech companies",
                "entities": ["entity_1", "entity_2", "entity_3"],
                "keywords": ["machine learning", "AI", "Google", "technology"],
                "score": 0.88,
            }
        }
    )


class GraphQueryResult(BaseModel):
    """Graph query result with entities, relationships, and topics."""

    query: str = Field(..., description="Original query")
    answer: str = Field(default="", description="LLM-generated answer from graph context")
    entities: list[GraphEntity] = Field(default_factory=list, description="Retrieved entities")
    relationships: list[GraphRelationship] = Field(
        default_factory=list, description="Retrieved relationships"
    )
    topics: list[Topic] = Field(
        default_factory=list, description="Retrieved topics (global search)"
    )
    context: str = Field(default="", description="Graph context used for answer generation")
    mode: str = Field(default="local", description="Search mode (local/global/hybrid)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Query metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "What companies has John Smith worked for?",
                "answer": (
                    "John Smith has worked for Google (2020-present) " "and Microsoft (2015-2020)."
                ),
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
    )


# ============================================================================
# Community Detection Models (Sprint 6.3)
# ============================================================================


class Community(BaseModel):
    """Community (cluster) in the knowledge graph."""

    id: str = Field(..., description="Unique community ID")
    label: str = Field(default="", description="Human-readable community label")
    entity_ids: list[str] = Field(default_factory=list, description="Entity IDs in this community")
    size: int = Field(..., description="Number of entities in the community", ge=0)
    density: float = Field(default=0.0, description="Community graph density", ge=0.0, le=1.0)
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Community creation timestamp"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional community metadata"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "community_1",
                "label": "Machine Learning Research",
                "entity_ids": ["entity_1", "entity_2", "entity_3"],
                "size": 3,
                "density": 0.85,
                "created_at": "2025-01-15T10:00:00Z",
                "metadata": {"algorithm": "leiden", "resolution": 1.0},
            }
        }
    )


class CommunitySearchResult(BaseModel):
    """Search result filtered by communities."""

    query: str = Field(..., description="Original query")
    communities: list[Community] = Field(default_factory=list, description="Retrieved communities")
    entities: list[GraphEntity] = Field(
        default_factory=list, description="Entities from matched communities"
    )
    answer: str = Field(default="", description="LLM-generated answer")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Search metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "What are the main research areas?",
                "communities": [
                    {
                        "id": "community_1",
                        "label": "Machine Learning Research",
                        "entity_ids": ["e1", "e2"],
                        "size": 2,
                        "density": 0.85,
                        "created_at": "2025-01-15T10:00:00Z",
                        "metadata": {},
                    }
                ],
                "entities": [
                    {
                        "id": "e1",
                        "name": "Neural Networks",
                        "type": "CONCEPT",
                        "description": "Deep learning architecture",
                        "properties": {},
                        "source_document": "doc_1",
                        "confidence": 0.95,
                    }
                ],
                "answer": "The main research areas include Machine Learning Research...",
                "metadata": {"execution_time_ms": 150, "communities_found": 1},
            }
        }
    )


# ============================================================================
# Graph Visualization & Analytics Models (Sprint 6.5 & 6.6)
# ============================================================================


class CentralityMetrics(BaseModel):
    """Centrality metrics for a graph entity."""

    entity_id: str = Field(..., description="Entity ID")
    degree: float = Field(..., description="Degree centrality (number of connections)", ge=0.0)
    betweenness: float = Field(default=0.0, description="Betweenness centrality", ge=0.0, le=1.0)
    closeness: float = Field(default=0.0, description="Closeness centrality", ge=0.0, le=1.0)
    eigenvector: float = Field(default=0.0, description="Eigenvector centrality", ge=0.0, le=1.0)
    pagerank: float = Field(default=0.0, description="PageRank score", ge=0.0, le=1.0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_id": "entity_1",
                "degree": 15.0,
                "betweenness": 0.35,
                "closeness": 0.68,
                "eigenvector": 0.42,
                "pagerank": 0.08,
            }
        }
    )


class GraphStatistics(BaseModel):
    """Overall graph statistics and metrics."""

    total_entities: int = Field(..., description="Total number of entities", ge=0)
    total_relationships: int = Field(..., description="Total number of relationships", ge=0)
    entity_types: dict[str, int] = Field(
        default_factory=dict, description="Count of entities by type"
    )
    relationship_types: dict[str, int] = Field(
        default_factory=dict, description="Count of relationships by type"
    )
    avg_degree: float = Field(..., description="Average node degree", ge=0.0)
    density: float = Field(..., description="Graph density", ge=0.0, le=1.0)
    communities: int = Field(default=0, description="Number of detected communities", ge=0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_entities": 1500,
                "total_relationships": 3200,
                "entity_types": {"PERSON": 500, "ORGANIZATION": 300, "CONCEPT": 700},
                "relationship_types": {"WORKS_AT": 450, "KNOWS": 1200, "RELATED_TO": 1550},
                "avg_degree": 4.27,
                "density": 0.0014,
                "communities": 45,
            }
        }
    )


class Recommendation(BaseModel):
    """Entity recommendation with score and reason."""

    entity: GraphEntity = Field(..., description="Recommended entity")
    score: float = Field(..., description="Recommendation score", ge=0.0, le=1.0)
    reason: str = Field(
        ...,
        description="Recommendation reason (similar_community, connected, similar_attributes)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity": {
                    "id": "entity_2",
                    "name": "Jane Doe",
                    "type": "PERSON",
                    "description": "Data scientist at Google",
                    "properties": {},
                    "source_document": "doc_2",
                    "confidence": 0.92,
                },
                "score": 0.85,
                "reason": "similar_community",
            }
        }
    )


# --- Domain Management Models (Sprint 117) ---


class DomainLLMConfig(BaseModel):
    """LLM configuration per domain.

    Sprint 117 Feature 117.1: Domain CRUD API.

    Allows different models for:
    - DSPy training (prompt optimization)
    - Production extraction (entity/relation extraction)
    - Classification (C-LARA fallback LLM verification)
    """

    training_model: str = Field(
        default="qwen3:32b",
        description="LLM model for DSPy training and prompt optimization",
    )
    training_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for training model",
    )
    extraction_model: str = Field(
        default="nemotron3",
        description="LLM model for production entity/relation extraction",
    )
    extraction_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Temperature for extraction model (lower = more deterministic)",
    )
    classification_model: str = Field(
        default="nemotron3",
        description="LLM model for C-LARA fallback classification",
    )
    provider: str = Field(
        default="ollama",
        description="LLM provider (ollama, alibaba, openai)",
        pattern="^(ollama|alibaba|openai)$",
    )


class DomainSchema(BaseModel):
    """Domain configuration schema.

    Sprint 117 Feature 117.1: Domain CRUD API.

    CRITICAL: MENTIONED_IN relation is automatically added to all domains.
    """

    id: str = Field(..., description="Unique domain ID (UUID)")
    name: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern="^[a-z][a-z0-9_-]*$",
        description="Domain name (unique, lowercase, alphanumeric + hyphens)",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Domain description for semantic matching",
    )
    training_samples: int = Field(
        default=0,
        ge=0,
        description="Count of labeled training samples",
    )
    entity_types: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Custom entity types (1-20 types, each 5-50 chars)",
    )
    relation_types: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Custom relation types (MENTIONED_IN automatically added)",
    )
    intent_classes: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Intent classes for domain-specific classification",
    )
    model_family: str = Field(
        default="general",
        pattern="^(general|medical|legal|technical|finance)$",
        description="Model family",
    )
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for auto-extraction",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp",
    )
    created_by: str = Field(
        default="system",
        description="User ID who created the domain",
    )
    status: str = Field(
        default="active",
        pattern="^(active|training|inactive)$",
        description="Domain status",
    )
    training_progress: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Training progress (0-100) when status=training",
    )
    metrics: dict[str, float] | None = Field(
        default=None,
        description="RAGAS metrics when available",
    )
    llm_config: DomainLLMConfig = Field(
        default_factory=DomainLLMConfig,
        description="LLM configuration per domain",
    )

    @field_validator("entity_types")
    @classmethod
    def validate_entity_types(cls, v: list[str]) -> list[str]:
        """Validate entity types are 5-50 characters each."""
        for entity_type in v:
            if not (5 <= len(entity_type) <= 50):
                raise ValueError(
                    f"Entity type '{entity_type}' must be 5-50 characters, got {len(entity_type)}"
                )
            if not entity_type.replace("_", "").replace(" ", "").isalnum():
                raise ValueError(
                    f"Entity type '{entity_type}' must be alphanumeric (underscores/spaces allowed)"
                )
        return v

    @field_validator("relation_types")
    @classmethod
    def validate_and_inject_mentioned_in(cls, v: list[str]) -> list[str]:
        """Validate relation types and ensure MENTIONED_IN is included.

        CRITICAL: MENTIONED_IN is required for all domains to link entities
        to their source chunks (ChunkIDs).
        """
        for relation_type in v:
            if not (5 <= len(relation_type) <= 50):
                raise ValueError(
                    f"Relation type '{relation_type}' must be 5-50 characters, got {len(relation_type)}"
                )
            if not relation_type.replace("_", "").isalnum():
                raise ValueError(
                    f"Relation type '{relation_type}' must be alphanumeric with underscores"
                )
        if "MENTIONED_IN" not in v:
            v.append("MENTIONED_IN")
        return v

    @field_validator("intent_classes")
    @classmethod
    def validate_intent_classes(cls, v: list[str]) -> list[str]:
        """Validate intent classes are 3-50 characters each."""
        for intent_class in v:
            if not (3 <= len(intent_class) <= 50):
                raise ValueError(
                    f"Intent class '{intent_class}' must be 3-50 characters, got {len(intent_class)}"
                )
        return v


class DomainCreateRequest(BaseModel):
    """Request to create a new domain configuration.

    Sprint 117 Feature 117.1: Domain CRUD API.
    """

    name: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern="^[a-z][a-z0-9_-]*$",
        description="Unique domain name (lowercase, alphanumeric + hyphens/underscores)",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Domain description for semantic matching",
    )
    entity_types: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Custom entity types (1-20 types)",
    )
    relation_types: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Custom relation types (MENTIONED_IN auto-added)",
    )
    intent_classes: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Intent classes for classification",
    )
    model_family: str = Field(
        default="general",
        pattern="^(general|medical|legal|technical|finance)$",
        description="Model family",
    )
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold",
    )
    llm_config: DomainLLMConfig = Field(
        default_factory=DomainLLMConfig,
        description="LLM configuration",
    )
    entity_sub_type_mapping: dict[str, str] | None = Field(
        default=None,
        description="Domain sub-type → universal type mapping (e.g., {DISEASE: CONCEPT}). "
        "Sprint 126: YAML factory defaults, editable via UI.",
    )
    relation_hints: list[str] | None = Field(
        default=None,
        description="Domain-specific relation examples (e.g., 'TREATS → Medication → Disease'). "
        "Sprint 126: YAML factory defaults, editable via UI.",
    )


class DomainUpdateRequest(BaseModel):
    """Request to update an existing domain configuration.

    Sprint 117 Feature 117.1: Domain CRUD API.
    """

    description: str | None = Field(
        default=None,
        min_length=10,
        max_length=500,
        description="Updated domain description",
    )
    entity_types: list[str] | None = Field(
        default=None,
        min_length=1,
        max_length=20,
        description="Updated entity types",
    )
    relation_types: list[str] | None = Field(
        default=None,
        min_length=1,
        max_length=20,
        description="Updated relation types (MENTIONED_IN auto-added)",
    )
    intent_classes: list[str] | None = Field(
        default=None,
        max_length=10,
        description="Updated intent classes",
    )
    confidence_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Updated confidence threshold",
    )
    status: str | None = Field(
        default=None,
        pattern="^(active|training|inactive)$",
        description="Updated status",
    )
    llm_config: DomainLLMConfig | None = Field(
        default=None,
        description="Updated LLM configuration",
    )
    entity_sub_type_mapping: dict[str, str] | None = Field(
        default=None,
        description="Updated domain sub-type → universal type mapping. "
        "Sprint 126: Overrides YAML factory defaults.",
    )
    relation_hints: list[str] | None = Field(
        default=None,
        description="Updated domain-specific relation examples. "
        "Sprint 126: Overrides YAML factory defaults.",
    )

    @field_validator("entity_types")
    @classmethod
    def validate_entity_types(cls, v: list[str] | None) -> list[str] | None:
        """Validate entity types are 5-50 characters each."""
        if v is None:
            return v
        for entity_type in v:
            if not (5 <= len(entity_type) <= 50):
                raise ValueError(
                    f"Entity type '{entity_type}' must be 5-50 characters, got {len(entity_type)}"
                )
        return v

    @field_validator("relation_types")
    @classmethod
    def validate_and_inject_mentioned_in(cls, v: list[str] | None) -> list[str] | None:
        """Validate relation types and ensure MENTIONED_IN is included."""
        if v is None:
            return v
        for relation_type in v:
            if not (5 <= len(relation_type) <= 50):
                raise ValueError(
                    f"Relation type '{relation_type}' must be 5-50 characters, got {len(relation_type)}"
                )
        if "MENTIONED_IN" not in v:
            v.append("MENTIONED_IN")
        return v
