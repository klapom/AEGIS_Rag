"""
Structured Logging Configuration using structlog.

Sprint Context: Sprint 1 (2025-10-14) - Feature 1.2: Structured Logging Setup

This module provides a production-ready structured logging configuration using
structlog for the AEGIS RAG application. Structured logging enables better
observability, machine-parsable logs, and context-rich debugging.

Architecture:
    Python stdlib logging → structlog → Console/JSON Renderer

    All log statements use structlog's bound logger for automatic context
    injection (app name, version, log level, timestamp, etc.).

Features:
    - Structured key-value logging (e.g., logger.info("message", user_id=123))
    - Automatic context injection (app, version, timestamp, log level)
    - Dual output modes: Human-readable console (dev) or JSON (production)
    - Stack trace rendering for exceptions
    - Third-party logger silencing (httpx, qdrant_client, neo4j)

Output Formats:
    Development (json_logs=False):
        2025-10-14T10:30:45.123 [INFO] aegis-rag.v0.1.0 - Hybrid search completed
            query_length=50 vector_results=20 bm25_results=18

    Production (json_logs=True):
        {"event": "Hybrid search completed", "level": "info", "timestamp": "2025-10-14T10:30:45.123Z",
         "app": "aegis-rag", "version": "0.1.0", "query_length": 50, "vector_results": 20}

Example:
    >>> from src.core.logging import setup_logging, get_logger
    >>> setup_logging(log_level="INFO", json_logs=False)
    >>> logger = get_logger(__name__)
    >>> logger.info("user_action", user_id=123, action="search")
    2025-10-14T10:30:45.123 [INFO] my_module - user_action user_id=123 action=search

Notes:
    - Call setup_logging() once at application startup (before any logging)
    - Use get_logger(__name__) to get module-specific logger
    - Context variables persist across log calls (use contextvars for request IDs)
    - Stack traces automatically included for logger.exception() calls
    - Third-party loggers (httpx, qdrant, neo4j) set to WARNING to reduce noise

See Also:
    - structlog documentation: https://www.structlog.org/
    - docs/observability.md: Logging and monitoring guide
    - Sprint 1 Features: Core infrastructure and logging
"""

import logging
import sys

import structlog
from structlog.types import EventDict, Processor


def add_app_context(
    _logger: logging.Logger, _method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add application context to all log messages.

    This processor is called for every log statement and injects app name and version
    into the log context. This helps filter logs when multiple services log to the
    same aggregator (e.g., Elasticsearch, Loki).

    Args:
        _logger: Python stdlib logger instance (required by structlog signature)
        _method_name: Log method name (required by structlog signature)
        event_dict: Current event dictionary

    Returns:
        EventDict: Modified event dictionary with app context

    Example:
        >>> event = {"event": "test", "level": "info"}
        >>> add_app_context(None, "info", event)
        {"event": "test", "level": "info", "app": "aegis-rag", "version": "0.1.0"}

    Notes:
        - Called automatically by structlog processor chain
        - App name and version are hardcoded (could be loaded from config)
        - Useful for multi-service deployments with centralized logging
    """
    event_dict["app"] = "aegis-rag"
    event_dict["version"] = "0.1.0"
    return event_dict


def setup_logging(log_level: str = "INFO", json_logs: bool = False) -> None:
    """
    Configure structured logging for the application.

    This function sets up the structlog processor chain and configures Python's
    stdlib logging to work with structlog. It should be called ONCE at application
    startup, before any logging occurs.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, output logs in JSON format for production.
                   If False, use colored console format for development.

    Example:
        >>> # Development setup (colored console output)
        >>> setup_logging(log_level="DEBUG", json_logs=False)
        >>> logger = get_logger(__name__)
        >>> logger.info("server_started", port=8000)

        >>> # Production setup (JSON output for log aggregators)
        >>> setup_logging(log_level="INFO", json_logs=True)
        >>> logger = get_logger(__name__)
        >>> logger.error("database_error", error="Connection timeout")

    Processor Chain:
        1. merge_contextvars: Add context variables (e.g., request_id)
        2. add_log_level: Add log level to event dict
        3. add_logger_name: Add logger name (module path)
        4. TimeStamper: Add ISO timestamp
        5. StackInfoRenderer: Render stack traces
        6. add_app_context: Add app name and version
        7. dict_tracebacks/ExceptionRenderer: Format exceptions
        8. JSONRenderer/ConsoleRenderer: Final output format

    Notes:
        - Call this function BEFORE any logging occurs (typically in main.py)
        - Logs to stdout (not stderr) for Docker/K8s log aggregation
        - Third-party loggers (httpx, qdrant, neo4j) silenced to WARNING
        - Stack traces automatically included for logger.exception() calls
        - Context variables persist across async boundaries (use contextvars)

    See Also:
        - get_logger(): Get a logger instance
        - structlog.contextvars: For request-scoped context
    """
    # Shared processors for all logs
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
    ]

    if json_logs:
        # Production: JSON logs for machine parsing
        processors: list[Processor] = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Console logs for human reading
        processors = [
            *shared_processors,
            structlog.processors.ExceptionRenderer(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    This function returns a structlog BoundLogger that automatically includes
    the logger name (typically module path) in all log messages.

    Args:
        name: Logger name (typically __name__ for module path).
              If None, uses root logger.

    Returns:
        structlog.stdlib.BoundLogger: Logger instance with automatic context

    Example:
        >>> # In my_module.py
        >>> logger = get_logger(__name__)
        >>> logger.info("processing_started", doc_count=10)
        2025-10-14T10:30:45.123 [INFO] my_module - processing_started doc_count=10

        >>> # With additional context
        >>> logger = get_logger(__name__)
        >>> logger.info("user_login", user_id=123, ip="192.168.1.1")

    Usage Patterns:
        # Module-level logger (recommended)
        logger = get_logger(__name__)

        # Root logger (less useful for debugging)
        logger = get_logger()

        # Structured logging with key-value pairs
        logger.info("event_name", key1=value1, key2=value2)

        # Exception logging with automatic stack trace
        try:
            risky_operation()
        except Exception as e:
            logger.exception("operation_failed", error=str(e))

    Notes:
        - Always use __name__ for logger name to track log source
        - Use snake_case for event names (e.g., "user_login" not "User Login")
        - Add context as keyword arguments (e.g., user_id=123)
        - Use logger.exception() for errors to include stack trace
        - BoundLogger is thread-safe and can be shared across requests

    See Also:
        - setup_logging(): Must be called before get_logger()
        - structlog.stdlib.BoundLogger: Logger class documentation
    """
    return structlog.get_logger(name)  # type: ignore[no-any-return]
