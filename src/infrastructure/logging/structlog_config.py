"""
Structured Logging Configuration using structlog.

Sprint 56: Migrated from src/core/logging.py
Original Sprint Context: Sprint 1 (2025-10-14) - Feature 1.2: Structured Logging Setup

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

Example:
    >>> from src.infrastructure.logging import setup_logging, get_logger
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

# Re-export everything from the original location for backward compatibility
# This module is a placeholder - actual implementation remains in src/core/logging.py
# to avoid code duplication during migration

from src.core.logging import add_app_context, get_logger, setup_logging

__all__ = [
    "add_app_context",
    "get_logger",
    "setup_logging",
]
