"""Structured Logging.

Sprint 56.5: Structlog-based logging configuration.

Usage:
    from src.infrastructure.logging import setup_logging, get_logger
    setup_logging(log_level="INFO", json_logs=False)
    logger = get_logger(__name__)
"""

from src.infrastructure.logging.structlog_config import (
    add_app_context,
    get_logger,
    setup_logging,
)

__all__ = [
    "add_app_context",
    "get_logger",
    "setup_logging",
]
