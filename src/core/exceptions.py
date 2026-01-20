"""Custom exceptions for the AEGIS RAG application.

Sprint 22 Feature 22.2.2: Standardized error responses with error codes.
"""

from typing import Any


class AegisRAGException(Exception):  # noqa: N818
    """Base exception for all AEGIS RAG errors.

    Sprint 22 Feature 22.2.2: Extended with error codes and HTTP status codes.

    Note: Name intentionally uses 'Exception' suffix instead of 'Error'
    to match the base Exception class naming convention.
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code (from ErrorCode enum)
            status_code: HTTP status code (default: 500)
            details: Additional error details for debugging
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class ConfigurationError(AegisRAGException):
    """Raised when there is a configuration error."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=message,
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            status_code=500,
            details=details,
        )


class DatabaseConnectionError(AegisRAGException):
    """Raised when database connection fails."""

    def __init__(self, database: str, reason: str) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"Failed to connect to {database}: {reason}",
            error_code=ErrorCode.DATABASE_CONNECTION_FAILED,
            status_code=503,
            details={"database": database, "reason": reason},
        )


class VectorSearchError(AegisRAGException):
    """Raised when vector search fails."""

    def __init__(self, query: str, reason: str) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"Vector search failed: {reason}",
            error_code=ErrorCode.VECTOR_SEARCH_FAILED,
            status_code=500,
            details={"query": query, "reason": reason},
        )


class GraphQueryError(AegisRAGException):
    """Raised when graph query fails."""

    def __init__(self, query: str, reason: str) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"Graph query failed: {reason}",
            error_code=ErrorCode.GRAPH_QUERY_FAILED,
            status_code=500,
            details={"query": query, "reason": reason},
        )


class LLMError(AegisRAGException):
    """Raised when LLM operation fails."""

    def __init__(self, operation: str, reason: str) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"LLM operation '{operation}' failed: {reason}",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            status_code=500,
            details={"operation": operation, "reason": reason},
        )


class LLMExecutionError(AegisRAGException):
    """Raised when LLM execution fails across all providers.

    Sprint 23: Used by AegisLLMProxy when all providers (OpenAI, Ollama Cloud, Local) fail.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=message,
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            status_code=503,  # Service Unavailable
            details=details or {},
        )


class MemoryError(AegisRAGException):
    """Raised when memory operation fails."""

    def __init__(self, operation: str, reason: str) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"Memory operation '{operation}' failed: {reason}",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            status_code=500,
            details={"operation": operation, "reason": reason},
        )


class ValidationError(AegisRAGException):
    """Raised when input validation fails."""

    def __init__(self, field: str, issue: str) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"Validation failed for field '{field}': {issue}",
            error_code=ErrorCode.VALIDATION_FAILED,
            status_code=400,
            details={"field": field, "issue": issue},
        )


class RateLimitError(AegisRAGException):
    """Raised when rate limit is exceeded."""

    def __init__(self, limit: int, window: str) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window}",
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=429,
            details={"limit": limit, "window": window},
        )


class AuthenticationError(AegisRAGException):
    """Raised when authentication fails."""

    def __init__(self, reason: str = "Invalid credentials") -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"Authentication failed: {reason}",
            error_code=ErrorCode.UNAUTHORIZED,
            status_code=401,
            details={"reason": reason},
        )


class AuthorizationError(AegisRAGException):
    """Raised when authorization fails."""

    def __init__(self, resource: str, action: str) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"Not authorized to {action} {resource}",
            error_code=ErrorCode.FORBIDDEN,
            status_code=403,
            details={"resource": resource, "action": action},
        )


class IngestionError(AegisRAGException):
    """Raised when document ingestion fails.

    Sprint 21: Used by DoclingContainerClient and LangGraph ingestion pipeline.
    """

    def __init__(self, document_id: str, reason: str) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"Document ingestion failed: {reason}",
            error_code=ErrorCode.INGESTION_FAILED,
            status_code=500,
            details={"document_id": document_id, "reason": reason},
        )


# ============================================================================
# Sprint 22 Feature 22.2.2: Business-specific exceptions
# ============================================================================


class FileNotFoundError(AegisRAGException):  # noqa: A001
    """Raised when a requested file does not exist."""

    def __init__(self, file_id: str) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"File not found: {file_id}",
            error_code=ErrorCode.FILE_NOT_FOUND,
            status_code=404,
            details={"file_id": file_id},
        )


class InvalidFileFormatError(AegisRAGException):
    """Raised when file format is not supported."""

    def __init__(self, filename: str, expected_formats: list[str]) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"Invalid file format: {filename}",
            error_code=ErrorCode.INVALID_FILE_FORMAT,
            status_code=400,
            details={"filename": filename, "expected_formats": expected_formats},
        )


class FileTooLargeError(AegisRAGException):
    """Raised when file size exceeds maximum allowed."""

    def __init__(self, filename: str, size_mb: float, max_size_mb: float) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"File too large: {filename} ({size_mb:.2f}MB > {max_size_mb}MB)",
            error_code=ErrorCode.FILE_TOO_LARGE,
            status_code=413,
            details={"filename": filename, "size_mb": size_mb, "max_size_mb": max_size_mb},
        )


class ExternalServiceError(AegisRAGException):
    """Raised when an external service (Ollama, Neo4j, Qdrant) is unavailable or returns an error.

    Sprint 117.12: Added for ModelService error handling.
    """

    def __init__(
        self, service_name: str, message: str, details: dict[str, Any] | None = None
    ) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=f"{service_name} service error: {message}",
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            status_code=503,
            details=details or {},
        )
        self.service_name = service_name


class EvaluationError(AegisRAGException):
    """Raised when evaluation operation fails.

    Sprint 41 Feature 41.7: Used by RAGAS evaluator when evaluation fails.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        from src.core.models import ErrorCode

        super().__init__(
            message=message,
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            status_code=500,
            details=details or {},
        )
