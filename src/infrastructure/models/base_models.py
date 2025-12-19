"""Base Pydantic Models for API requests and responses.

Sprint 56: Migrated from src/core/models.py
Original Sprint Context: Sprint 1 & Sprint 22 - API Models & Error Handling

This module provides the core Pydantic models used across the AEGIS RAG application
for API requests, responses, and data transfer objects.

Model Categories:
    - Query Models: QueryRequest, QueryResponse, QueryIntent, QueryMode
    - Document Models: DocumentChunk
    - Health Models: HealthStatus, HealthResponse, ServiceHealth
    - Error Models: ErrorCode, ErrorDetail, ErrorResponse
    - Graph Models: GraphEntity, GraphRelationship, Topic, Community
    - Analytics Models: CentralityMetrics, GraphStatistics, Recommendation

Example:
    >>> from src.infrastructure.models import QueryRequest, QueryMode
    >>> request = QueryRequest(query="What is AEGIS RAG?", mode=QueryMode.HYBRID)

See Also:
    - docs/adr/ADR-001-configuration-management.md
    - Sprint 1 & Sprint 5 Features
"""

# Re-export everything from the original location for backward compatibility
# This module is a placeholder - actual implementation remains in src/core/models.py
# to avoid code duplication during migration

from src.core.models import (
    CentralityMetrics,
    Community,
    CommunitySearchResult,
    DocumentChunk,
    ErrorCode,
    ErrorDetail,
    ErrorResponse,
    GraphEntity,
    GraphQueryResult,
    GraphRelationship,
    GraphStatistics,
    HealthResponse,
    HealthStatus,
    QueryIntent,
    QueryMode,
    QueryRequest,
    QueryResponse,
    Recommendation,
    ServiceHealth,
    Topic,
)

__all__ = [
    # Query Models
    "QueryIntent",
    "QueryMode",
    "QueryRequest",
    "QueryResponse",
    "DocumentChunk",
    # Health Models
    "HealthStatus",
    "ServiceHealth",
    "HealthResponse",
    # Error Models
    "ErrorCode",
    "ErrorDetail",
    "ErrorResponse",
    # Graph Models
    "GraphEntity",
    "GraphRelationship",
    "Topic",
    "GraphQueryResult",
    "Community",
    "CommunitySearchResult",
    # Analytics Models
    "CentralityMetrics",
    "GraphStatistics",
    "Recommendation",
]
