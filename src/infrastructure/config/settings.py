"""
Application Configuration using Pydantic Settings.

Sprint 56: Migrated from src/core/config.py
Original Sprint Context: Sprint 1 (2025-10-14) - Feature 1.1: Core Configuration Management

This module provides a unified configuration system for the entire AEGIS RAG application,
using Pydantic Settings for type-safe environment variable loading and validation.

Architecture:
    Environment Variables → .env File → Pydantic Validation → Settings Object

    All configuration is loaded from environment variables with .env file fallback.
    The Settings class uses Pydantic's BaseSettings for automatic validation,
    type coercion, and default values.

Configuration Categories:
    - Application: Basic app metadata (name, version, environment)
    - API Server: FastAPI server configuration with security settings
    - LLM Models: Ollama/Azure OpenAI model selection and parameters
    - Vector Database: Qdrant connection and collection settings
    - Graph Database: Neo4j connection and graph features
    - Memory: Redis cache and 3-layer memory configuration
    - Retrieval: Search, chunking, and reranking parameters
    - Security: API authentication, rate limiting, input validation

Security Design:
    - Sensitive values use Pydantic SecretStr (masked in logs)
    - API binding to 0.0.0.0 is intentional for Docker/K8s (see Bandit B104 exemption)
    - Rate limiting enforced: 10 req/min (search), 5 req/hour (ingest)
    - JWT authentication configurable via api_auth_enabled
    - Documents restricted to documents_base_path (path traversal protection)

Example:
    >>> from src.infrastructure.config import settings
    >>> print(settings.app_name)
    'aegis-rag'
    >>> print(settings.ollama_base_url)
    'http://localhost:11434'
    >>> settings.qdrant_url
    'http://localhost:6333'

Notes:
    - All settings have sensible defaults for local development
    - Production deployments should override via environment variables
    - Use @lru_cache to ensure Settings is singleton (single instance)
    - Changes to settings require application restart (no hot-reload)

See Also:
    - docs/adr/ADR-001-configuration-management.md: Configuration architecture decision
    - .env.example: Example environment file with all available settings
    - Sprint 1 Features: Core infrastructure and configuration
"""

# Re-export everything from the original location for backward compatibility
# This module is a placeholder - actual implementation remains in src/core/config.py
# to avoid code duplication during migration

from src.core.config import Settings, get_settings, settings

__all__ = [
    "Settings",
    "get_settings",
    "settings",
]
