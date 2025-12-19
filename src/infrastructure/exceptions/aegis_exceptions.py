"""Custom exceptions for the AEGIS RAG application.

Sprint 56: Migrated from src/core/exceptions.py
Original Sprint 22 Feature 22.2.2: Standardized error responses with error codes.

This module provides a hierarchy of custom exceptions for the AEGIS RAG application,
each with:
- HTTP status code
- Machine-readable error code
- Human-readable message
- Optional details dictionary

Example:
    >>> from src.infrastructure.exceptions import IngestionError
    >>> raise IngestionError(document_id="doc123", reason="File too large")
"""

# Re-export everything from the original location for backward compatibility
# This module is a placeholder - actual implementation remains in src/core/exceptions.py
# to avoid code duplication during migration

from src.core.exceptions import (
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
