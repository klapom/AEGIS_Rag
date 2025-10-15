"""Custom exceptions for the AEGIS RAG application."""


class AegisRAGException(Exception):  # noqa: N818
    """Base exception for all AEGIS RAG errors.

    Note: Name intentionally uses 'Exception' suffix instead of 'Error'
    to match the base Exception class naming convention.
    """

    def __init__(self, message: str, details: dict | None = None) -> None:
        """
        Initialize exception.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(AegisRAGException):
    """Raised when there is a configuration error."""

    pass


class DatabaseConnectionError(AegisRAGException):
    """Raised when database connection fails."""

    pass


class VectorSearchError(AegisRAGException):
    """Raised when vector search fails."""

    pass


class GraphQueryError(AegisRAGException):
    """Raised when graph query fails."""

    pass


class LLMError(AegisRAGException):
    """Raised when LLM operation fails."""

    pass


class MemoryError(AegisRAGException):
    """Raised when memory operation fails."""

    pass


class ValidationError(AegisRAGException):
    """Raised when input validation fails."""

    pass


class RateLimitError(AegisRAGException):
    """Raised when rate limit is exceeded."""

    pass


class AuthenticationError(AegisRAGException):
    """Raised when authentication fails."""

    pass


class AuthorizationError(AegisRAGException):
    """Raised when authorization fails."""

    pass
