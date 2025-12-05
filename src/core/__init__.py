"""Core module exports (Sprint 36 Feature 36.6 - TD-054)."""

from src.core.chunk import Chunk, ChunkStrategy
from src.core.chunking_service import (
    ChunkingConfig,
    ChunkingService,
    ChunkStrategyEnum,
    SectionMetadata,
    get_chunking_service,
    reset_chunking_service,
)
from src.core.config import settings
from src.core.exceptions import (
    AegisRAGException,
    ConfigurationError,
    IngestionError,
)
from src.core.logging import get_logger

__all__ = [
    # Chunk models
    "Chunk",
    "ChunkStrategy",
    # Chunking service (TD-054)
    "ChunkingService",
    "ChunkingConfig",
    "ChunkStrategyEnum",
    "SectionMetadata",
    "get_chunking_service",
    "reset_chunking_service",
    # Config
    "settings",
    # Exceptions
    "AegisRAGException",
    "ConfigurationError",
    "IngestionError",
    # Logging
    "get_logger",
]
