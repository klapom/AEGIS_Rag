"""MCP Error Handler.

Provides error classification and handling for MCP tool execution.
Distinguishes between transient (retryable) and permanent errors.

Sprint 9 Feature 9.7: Tool Execution Handler
"""

from enum import Enum


class ErrorType(Enum):
    """Classification of MCP errors."""

    TRANSIENT = "transient"  # Network, timeout - retry
    PERMANENT = "permanent"  # Invalid params - no retry
    TOOL_ERROR = "tool_error"  # Tool execution failed


class MCPError(Exception):
    """Base exception for MCP-related errors.

    Attributes:
        message: Human-readable error message
        error_type: Classification of the error (transient/permanent/tool_error)
        original_error: Original exception that caused this error (if any)
    """

    def __init__(
        self,
        message: str,
        error_type: ErrorType,
        original_error: Exception | None = None,
    ):
        """Initialize MCP error.

        Args:
            message: Error message
            error_type: Type of error for retry logic
            original_error: Original exception (if any)
        """
        super().__init__(message)
        self.error_type = error_type
        self.original_error = original_error

    def is_retryable(self) -> bool:
        """Check if error should be retried.

        Returns:
            True if error is transient and should be retried
        """
        return self.error_type == ErrorType.TRANSIENT

    def __repr__(self) -> str:
        """String representation of error."""
        return (
            f"MCPError(type={self.error_type.value}, message={self.args[0]}, "
            f"original={type(self.original_error).__name__ if self.original_error else None})"
        )


class ErrorHandler:
    """Handles and classifies MCP errors."""

    @staticmethod
    def classify_error(error: Exception) -> ErrorType:
        """Classify an error as transient, permanent, or tool error.

        Args:
            error: Exception to classify

        Returns:
            ErrorType classification
        """
        import asyncio

        # Network errors, timeouts → transient (should retry)
        if isinstance(error, (asyncio.TimeoutError, ConnectionError, TimeoutError)):
            return ErrorType.TRANSIENT

        # Invalid parameters → permanent (won't succeed on retry)
        if isinstance(error, (ValueError, KeyError, TypeError)):
            return ErrorType.PERMANENT

        # MCP-specific errors
        if isinstance(error, MCPError):
            return error.error_type

        # Default → tool error (may or may not be retryable)
        return ErrorType.TOOL_ERROR

    @staticmethod
    def create_user_friendly_message(error: Exception, context: str = "") -> str:
        """Create a user-friendly error message.

        Args:
            error: Original exception
            context: Additional context about what was being attempted

        Returns:
            User-friendly error message
        """
        error_type = ErrorHandler.classify_error(error)

        if error_type == ErrorType.TRANSIENT:
            return (
                f"Temporary connection issue: {str(error)}. "
                f"The operation will be retried automatically."
            )
        elif error_type == ErrorType.PERMANENT:
            return f"Invalid request: {str(error)}. " f"Please check your parameters and try again."
        else:
            return (
                f"Tool execution failed: {str(error)}. "
                f"{context if context else 'Please try again or contact support.'}"
            )

    @staticmethod
    def wrap_error(error: Exception, context: str = "") -> MCPError:
        """Wrap a standard exception as an MCPError.

        Args:
            error: Original exception
            context: Additional context

        Returns:
            MCPError with appropriate classification
        """
        error_type = ErrorHandler.classify_error(error)
        message = ErrorHandler.create_user_friendly_message(error, context)

        return MCPError(message=message, error_type=error_type, original_error=error)
