"""Custom Exceptions.

Sprint 56.5: Application-specific exception classes.

Usage:
    from src.infrastructure.exceptions import IngestionError, ValidationError
    raise IngestionError(document_id="doc123", reason="File too large")
"""

from src.infrastructure.exceptions.aegis_exceptions import (
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

__all__ = [
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
]
