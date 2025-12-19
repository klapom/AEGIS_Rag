"""Infrastructure Layer.

Sprint 56.5: Cross-cutting concerns and shared infrastructure.

Subpackages:
- config: Application configuration (settings)
- logging: Structured logging (structlog)
- exceptions: Custom exception classes
- models: Shared/base data models

Usage:
    from src.infrastructure.config import settings
    from src.infrastructure.logging import setup_logging, get_logger
    from src.infrastructure.exceptions import IngestionError
    from src.infrastructure.models import QueryRequest, QueryResponse
"""

# Config exports
from src.infrastructure.config import Settings, get_settings, settings

# Logging exports
from src.infrastructure.logging import add_app_context, get_logger, setup_logging

# Exception exports
from src.infrastructure.exceptions import (
    AegisRAGException,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    DatabaseConnectionError,
    EvaluationError,
    FileNotFoundError,
    FileTooLargeError,
    GraphQueryError,
    IngestionError,
    InvalidFileFormatError,
    LLMError,
    LLMExecutionError,
    MemoryError,
    RateLimitError,
    ValidationError,
    VectorSearchError,
)

# Model exports
from src.infrastructure.models import (
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
    # Config
    "Settings",
    "get_settings",
    "settings",
    # Logging
    "setup_logging",
    "get_logger",
    "add_app_context",
    # Exceptions
    "AegisRAGException",
    "ConfigurationError",
    "DatabaseConnectionError",
    "VectorSearchError",
    "GraphQueryError",
    "LLMError",
    "LLMExecutionError",
    "MemoryError",
    "ValidationError",
    "RateLimitError",
    "AuthenticationError",
    "AuthorizationError",
    "IngestionError",
    "FileNotFoundError",
    "InvalidFileFormatError",
    "FileTooLargeError",
    "EvaluationError",
    # Models
    "QueryIntent",
    "QueryMode",
    "QueryRequest",
    "QueryResponse",
    "DocumentChunk",
    "HealthStatus",
    "ServiceHealth",
    "HealthResponse",
    "ErrorCode",
    "ErrorDetail",
    "ErrorResponse",
    "GraphEntity",
    "GraphRelationship",
    "Topic",
    "GraphQueryResult",
    "Community",
    "CommunitySearchResult",
    "CentralityMetrics",
    "GraphStatistics",
    "Recommendation",
]
