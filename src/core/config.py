"""
Application Configuration using Pydantic Settings.

Sprint Context: Sprint 1 (2025-10-14) - Feature 1.1: Core Configuration Management

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
    >>> from src.core.config import settings
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

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RecursiveLevelConfig(BaseModel):
    """Configuration for a specific recursion level in Recursive LLM processing.

    Sprint 92 Feature 92.6: Per-Level Configuration

    Each level can have different segment sizes, overlap, scoring methods, and
    relevance thresholds optimized for that level of detail.

    Attributes:
        level: Recursion depth (0=top level, 1=first recursion, etc.)
        segment_size_tokens: Target segment size in tokens (1000-32000)
        overlap_tokens: Overlap between segments to prevent information loss
        top_k_subsegments: Number of sub-segments to explore at this level
        scoring_method: Relevance scoring method for this level
        relevance_threshold: Minimum relevance score to explore (0.0-1.0)

    Example:
        >>> level_0 = RecursiveLevelConfig(
        ...     level=0,
        ...     segment_size_tokens=16384,  # Large chunks for overview
        ...     scoring_method="dense+sparse",  # Fast document-level
        ...     relevance_threshold=0.5
        ... )
    """

    level: int = Field(description="Recursion depth (0=top level)")

    segment_size_tokens: int = Field(description="Target segment size in tokens", ge=1000, le=32000)

    overlap_tokens: int = Field(
        default=200, description="Overlap between segments to prevent information loss"
    )

    top_k_subsegments: int = Field(default=3, description="Number of sub-segments to explore")

    scoring_method: Literal["dense+sparse", "multi-vector", "llm", "adaptive"] = Field(
        default="dense+sparse",
        description="BGE-M3 scoring method: dense+sparse (fast), multi-vector (precise), llm (reasoning), adaptive (query-based)",
    )

    relevance_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum relevance score to explore"
    )


class RecursiveLLMSettings(BaseModel):
    """Recursive LLM processing configuration.

    Sprint 92 Features:
    - 92.6: Per-level configuration with adaptive sizing
    - 92.10: Parallel worker configuration by LLM backend

    Attributes:
        max_depth: Maximum recursion depth (1-5 levels)
        levels: Per-level configuration (adaptive sizing and scoring)
        max_parallel_workers: Max parallel segment processing workers
        worker_limits: Worker limits per LLM backend

    Example:
        >>> settings = RecursiveLLMSettings(
        ...     max_depth=3,
        ...     max_parallel_workers=1,  # DGX Spark (Ollama)
        ...     levels=[
        ...         RecursiveLevelConfig(level=0, segment_size_tokens=16384),
        ...         RecursiveLevelConfig(level=1, segment_size_tokens=8192),
        ...         RecursiveLevelConfig(level=2, segment_size_tokens=4096),
        ...     ]
        ... )
    """

    max_depth: int = Field(
        default=3, ge=1, le=5, description="Maximum recursion depth (1-5 levels)"
    )

    levels: list[RecursiveLevelConfig] = Field(
        default_factory=lambda: [
            # Level 0: Overview (large chunks, fast dense+sparse)
            RecursiveLevelConfig(
                level=0,
                segment_size_tokens=16384,  # 16K tokens
                overlap_tokens=400,
                top_k_subsegments=5,
                scoring_method="dense+sparse",
                relevance_threshold=0.5,
            ),
            # Level 1: Details (medium chunks, fast dense+sparse)
            RecursiveLevelConfig(
                level=1,
                segment_size_tokens=8192,  # 8K tokens
                overlap_tokens=300,
                top_k_subsegments=4,
                scoring_method="dense+sparse",
                relevance_threshold=0.6,
            ),
            # Level 2: Fine-grained (small chunks, adaptive scoring)
            RecursiveLevelConfig(
                level=2,
                segment_size_tokens=4096,  # 4K tokens
                overlap_tokens=200,
                top_k_subsegments=3,
                scoring_method="adaptive",  # Query-adaptive (multi-vector or LLM)
                relevance_threshold=0.7,
            ),
            # Level 3: Ultra-fine (tiny chunks, adaptive scoring)
            RecursiveLevelConfig(
                level=3,
                segment_size_tokens=2048,  # 2K tokens
                overlap_tokens=100,
                top_k_subsegments=2,
                scoring_method="adaptive",
                relevance_threshold=0.8,
            ),
        ]
    )

    # Feature 92.10: Parallel worker configuration
    max_parallel_workers: int = Field(
        default=1,
        description="Max parallel segment processing workers (1 for DGX Spark, 5-10 for cloud)",
    )

    worker_limits: dict[str, int] = Field(
        default_factory=lambda: {
            "ollama": 1,  # DGX Spark Ollama: single-threaded
            "openai": 10,  # OpenAI: high parallelism
            "alibaba": 5,  # Alibaba DashScope: moderate
        },
        description="Worker limits per LLM backend",
    )


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    This class uses Pydantic BaseSettings to automatically load configuration
    from environment variables with .env file fallback. All fields have type
    hints for validation and default values for local development.

    Attributes:
        app_name (str): Application name (default: "aegis-rag")
        app_version (str): Application version (default: "0.1.0")
        environment (Literal): Deployment environment (development/staging/production)
        debug (bool): Enable debug mode (default: False)
        log_level (str): Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        json_logs (bool): Output logs in JSON format for production (default: False)

        api_host (str): API server host (default: "0.0.0.0" for Docker/K8s)
        api_port (int): API server port (default: 8000)
        api_workers (int): Number of Uvicorn workers (default: 1)
        api_reload (bool): Enable auto-reload for development (default: False)

        api_auth_enabled (bool): Enable JWT authentication (default: True)
        api_secret_key (SecretStr): JWT secret key (min 32 chars for production)
        api_admin_password (SecretStr): Admin password for token endpoint

        ollama_base_url (str): Ollama server URL (default: http://localhost:11434)
        ollama_model_generation (str): LLM for text generation (default: llama3.1:8b)
        ollama_model_query (str): LLM for query understanding (default: llama3.2:3b)
        ollama_model_embedding (str): Embedding model (default: bge-m3, Sprint 16)
        ollama_model_router (str): LLM for query routing (default: llama3.2:3b)

        qdrant_host (str): Qdrant server host (default: localhost)
        qdrant_port (int): Qdrant HTTP port (default: 6333)
        qdrant_grpc_port (int): Qdrant gRPC port (default: 6334)
        qdrant_collection (str): Qdrant collection name (default: documents_v1)

        neo4j_uri (str): Neo4j connection URI (default: bolt://localhost:7687)
        neo4j_user (str): Neo4j username (default: neo4j)
        neo4j_password (SecretStr): Neo4j password
        neo4j_database (str): Neo4j database name (default: neo4j)

        redis_host (str): Redis server host (default: localhost)
        redis_port (int): Redis server port (default: 6379)
        redis_db (int): Redis database number (default: 0)
        redis_ttl (int): Redis default TTL in seconds (default: 3600)

        extraction_pipeline (Literal): Entity/relation extraction pipeline
            - 'llm_extraction': Pure LLM (NO SpaCy, high quality) - DEFAULT (ADR-026, ADR-037)
            - 'lightrag_default': Legacy LightRAG baseline
            Note: 'three_phase' removed in Sprint 25 (deprecated per ADR-026)

        retrieval_top_k (int): Number of documents to retrieve (default: 5)
        retrieval_score_threshold (float): Minimum relevance score (default: 0.7)

    Example:
        >>> settings = Settings()
        >>> print(settings.app_name)
        'aegis-rag'
        >>> settings.qdrant_url  # Computed property
        'http://localhost:6333'
        >>> settings.redis_url  # Computed property with password
        'redis://localhost:6379/0'

    Notes:
        - Environment variables are case-insensitive (e.g., API_HOST or api_host)
        - SecretStr fields are masked in logs and repr() output
        - Extra environment variables are ignored (extra="ignore")
        - Validators ensure log_level is valid (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        - Sprint 16: Migrated from nomic-embed-text to bge-m3 (1024-dim embeddings)
        - Sprint 21: Pure LLM extraction is default for high-quality entity/relation extraction

    See Also:
        - get_settings(): Factory function with @lru_cache for singleton pattern
        - .env.example: Example environment file
        - docs/configuration.md: Detailed configuration guide
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="aegis-rag", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Deployment environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    json_logs: bool = Field(default=False, description="Output logs in JSON format")

    # API Server
    # Security Note: Binding to 0.0.0.0 is intentional for Docker/Kubernetes deployments.
    # This allows the container to accept connections from any interface.
    # Security is enforced via:
    #   - Rate limiting (slowapi): 10 req/min (search), 5 req/hour (ingest)
    #   - JWT authentication (optional, configurable)
    #   - Input validation (Pydantic schemas)
    # Bandit B104 finding accepted by design. See BACKLOG_SPRINT_3.md:27-48
    api_host: str = Field(
        default="0.0.0.0", description="API server host"  # noqa: S104  # nosec B104
    )
    api_port: int = Field(default=8000, description="API server port")
    api_workers: int = Field(default=1, description="Number of Uvicorn workers")
    api_reload: bool = Field(default=False, description="Enable auto-reload")

    # API Security
    api_auth_enabled: bool = Field(
        default=True, description="Enable JWT authentication (disable for testing)"
    )
    api_secret_key: SecretStr = Field(
        default=SecretStr("CHANGE-ME-IN-PRODUCTION-MIN-32-CHARS"),
        description="JWT secret key (min 32 chars for production)",
    )
    api_admin_password: SecretStr = Field(
        default=SecretStr("admin123"),
        description="Admin password for token endpoint (CHANGE IN PRODUCTION)",
    )

    # JWT Configuration (Sprint 38 Feature 38.1a: JWT Authentication Backend)
    jwt_secret_key: SecretStr | None = Field(
        default=None,
        description="JWT secret key (auto-generated if not set, min 32 chars for production)",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(
        default=30, ge=1, le=1440, description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, ge=1, le=30, description="Refresh token expiration in days"
    )

    # Ollama LLM (Primary)
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    ollama_model_generation: str = Field(
        default="nemotron-no-think:latest",
        description="Ollama model for generation (Sprint 48: nemotron-no-think for better RAG)",
    )
    ollama_model_query: str = Field(
        default="llama3.2:3b", description="Ollama model for query understanding"
    )
    ollama_model_embedding: str = Field(
        default="bge-m3",
        description="Ollama embedding model (Sprint 16: migrated to bge-m3 1024-dim)",
    )
    ollama_model_router: str = Field(
        default="llama3.2:3b",
        description="Ollama model for query routing and intent classification",
    )

    # Sprint 87 Feature 87.4: Multi-Vector Embedding Configuration
    embedding_backend: Literal["ollama", "sentence-transformers", "flag-embedding"] = Field(
        default="ollama",
        description="Embedding backend: 'ollama' (default), 'sentence-transformers' (dense-only), 'flag-embedding' (multi-vector)",
    )
    st_model_name: str = Field(
        default="BAAI/bge-m3",
        description="SentenceTransformers/FlagEmbedding model name (Sprint 87)",
    )
    st_device: Literal["auto", "cuda", "cpu"] = Field(
        default="auto",
        description="Device for SentenceTransformers/FlagEmbedding: 'auto' (CUDA if available), 'cuda', 'cpu'",
    )
    st_batch_size: int = Field(
        default=32,
        ge=1,
        le=256,
        description="Batch size for SentenceTransformers/FlagEmbedding embedding",
    )
    st_use_fp16: bool = Field(
        default=True,
        description="Use FP16 half-precision for faster inference (requires CUDA)",
    )
    st_sparse_min_weight: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="FlagEmbedding: Minimum weight for sparse tokens (0.0 = keep all)",
    )
    st_sparse_top_k: int | None = Field(
        default=None,
        description="FlagEmbedding: Keep only top-k sparse tokens (None = keep all, 100 = typical)",
    )

    # Router Configuration (Sprint 4 Feature 4.2)
    router_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Temperature for router LLM (0.0 for deterministic)",
    )
    router_max_tokens: int = Field(
        default=50, ge=1, le=500, description="Max tokens for router response"
    )
    router_max_retries: int = Field(
        default=3, ge=1, le=10, description="Max retries for router LLM calls"
    )
    router_default_intent: str = Field(
        default="hybrid", description="Default intent if LLM classification fails"
    )

    # Azure OpenAI (Optional)
    use_azure_llm: bool = Field(default=False, description="Use Azure OpenAI instead of Ollama")
    azure_openai_endpoint: str | None = Field(default=None, description="Azure OpenAI endpoint URL")
    azure_openai_api_key: SecretStr | None = Field(default=None, description="Azure OpenAI API key")
    azure_openai_model: str = Field(default="gpt-4o", description="Azure OpenAI model name")
    azure_openai_deployment: str | None = Field(
        default=None, description="Azure OpenAI deployment name"
    )

    # Anthropic (Optional Fallback)
    anthropic_api_key: SecretStr | None = Field(default=None, description="Anthropic API key")

    # Budget Limits (Sprint 31 Feature 31.10a: Cost Dashboard)
    monthly_budget_alibaba_cloud: float | None = Field(
        default=10.0,
        description="Monthly budget limit for Alibaba Cloud in USD (null = unlimited)",
    )
    monthly_budget_openai: float | None = Field(
        default=20.0,
        description="Monthly budget limit for OpenAI in USD (null = unlimited)",
    )

    # Feature 21.6: Qwen3-VL Image Processing
    qwen3vl_model: str = Field(
        default="qwen3-vl:4b-instruct",
        description="Qwen3-VL model for image description (via Ollama)",
    )
    qwen3vl_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for Qwen3-VL (0.7 = model default)",
    )
    qwen3vl_top_p: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Top-p sampling for Qwen3-VL"
    )
    qwen3vl_top_k: int = Field(default=20, ge=1, le=100, description="Top-k sampling for Qwen3-VL")
    qwen3vl_num_ctx: int = Field(
        default=4096, ge=512, le=8192, description="Context window for Qwen3-VL"
    )

    # Feature 21.6: Image Filtering
    image_min_size: int = Field(
        default=100, ge=10, le=1000, description="Minimum image size (width or height) in pixels"
    )
    image_min_aspect_ratio: float = Field(
        default=0.1,
        ge=0.01,
        le=1.0,
        description="Minimum aspect ratio (width/height) for images",
    )
    image_max_aspect_ratio: float = Field(
        default=10.0,
        ge=1.0,
        le=100.0,
        description="Maximum aspect ratio (width/height) for images",
    )

    # Feature 21.6: Chunking (HybridChunker with BGE-M3)
    chunking_tokenizer_model: str = Field(
        default="BAAI/bge-m3",
        description="HuggingFace tokenizer model for HybridChunker",
    )
    chunking_max_tokens: int = Field(
        default=8192, ge=512, le=32768, description="Max tokens for BGE-M3 chunker"
    )
    chunking_merge_peers: bool = Field(
        default=True,
        description="Merge adjacent chunks in HybridChunker for better context",
    )

    # Qdrant Vector Database
    qdrant_host: str = Field(default="localhost", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant HTTP port")
    qdrant_grpc_port: int = Field(default=6334, description="Qdrant gRPC port")
    qdrant_api_key: SecretStr | None = Field(default=None, description="Qdrant API key")
    qdrant_collection: str = Field(default="documents_v1", description="Qdrant collection name")
    qdrant_use_grpc: bool = Field(default=False, description="Use gRPC for Qdrant")

    # Sprint 77 Feature 77.3 (TD-093): Qdrant Index Optimization
    qdrant_optimize_after_ingestion: bool = Field(
        default=True,
        description="Trigger Qdrant index rebuild after ingestion (Sprint 77 TD-093)",
    )
    qdrant_indexing_threshold: int = Field(
        default=0,
        description="HNSW indexing threshold (0=immediate, 20000=default). User request: index after every ingestion",
    )

    # Document Ingestion Security
    documents_base_path: str = Field(
        default="./data", description="Base directory for document ingestion (security boundary)"
    )

    # Reranker Settings (Sprint 3: Cross-Encoder Reranking)
    # Sprint 80 Feature 80.3: Updated to BAAI reranker (same family as BGE-M3 embeddings)
    reranker_model: str = Field(
        default="BAAI/bge-reranker-v2-m3",
        description="HuggingFace cross-encoder model for reranking. BAAI/bge-reranker-v2-m3 is multilingual and pairs with BGE-M3 embeddings.",
    )
    reranker_batch_size: int = Field(default=32, description="Batch size for reranking inference")
    reranker_cache_dir: str = Field(
        default="./data/models", description="Directory for caching HuggingFace models"
    )

    # Sprint 48 Feature 48.8: Ollama Reranker (TD-059)
    reranker_enabled: bool = Field(
        default=True,
        description="Enable reranking after RRF fusion",
    )
    reranker_backend: str = Field(
        default="sentence-transformers",
        description="Reranking backend: 'sentence-transformers' (BGE-Reranker-v2-m3, Sprint 76) or 'ollama' (TD-059, requires qllama/bge-reranker-v2-m3 model)",
    )
    reranker_ollama_model: str = Field(
        default="qllama/bge-reranker-v2-m3:q8_0",
        description="Ollama model for reranking (qllama/bge-reranker-v2-m3: multilingual, compatible with BGE-M3)",
    )
    reranker_top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of documents to return after reranking",
    )

    # Sprint 67 Feature 67.8: Adaptive Reranking with Intent-Aware Weights
    adaptive_reranking_enabled: bool = Field(
        default=True,
        description="Enable intent-aware adaptive reranking with weighted scores (Sprint 67.8)",
    )
    adaptive_reranking_semantic_weight_factual: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Semantic weight for factual queries (high precision)",
    )
    adaptive_reranking_keyword_weight_factual: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Keyword weight for factual queries"
    )
    adaptive_reranking_recency_weight_factual: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Recency weight for factual queries"
    )

    # Semantic Entity Deduplication (Sprint 13: ADR-017)
    enable_semantic_dedup: bool = Field(
        default=True, description="Enable semantic entity deduplication using sentence-transformers"
    )
    semantic_dedup_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence transformer model for entity deduplication (90MB, 384-dim)",
    )
    semantic_dedup_threshold: float = Field(
        default=0.93,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for duplicate detection (0.90-0.95 recommended)",
    )
    semantic_dedup_device: str = Field(
        default="auto", description="Device for semantic dedup ('auto', 'cuda', 'cpu')"
    )

    # Multi-Criteria Entity Deduplication (Sprint 43: ADR-044)
    enable_multi_criteria_dedup: bool = Field(
        default=True,
        description="Use multi-criteria dedup (edit distance + substring + semantic). "
        "If False, falls back to semantic-only (ADR-017).",
    )
    dedup_edit_distance_threshold: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max Levenshtein edit distance to consider as duplicate (1-2 char typos)",
    )
    dedup_min_length_for_edit: int = Field(
        default=5,
        ge=2,
        le=20,
        description="Min entity name length for edit distance check (prevents 'AI' ~ 'UI')",
    )
    dedup_min_length_for_substring: int = Field(
        default=6,
        ge=3,
        le=20,
        description="Min entity name length for substring check (prevents 'AI' in 'NVIDIA')",
    )

    # Relation Deduplication (Sprint 44: TD-063)
    enable_relation_dedup: bool = Field(
        default=True,
        description="Enable relation deduplication (type synonyms + bidirectional handling). "
        "Requires entity deduplication to be enabled for entity name normalization.",
    )
    relation_preserve_original_type: bool = Field(
        default=False,
        description="If True, store original relation type in 'original_type' field "
        "when normalizing to canonical type (e.g., STARRED_IN → ACTED_IN).",
    )

    # DSPy Training Data Collection (Sprint 85: Feature 85.7)
    enable_dspy_training_collection: bool = Field(
        default=True,
        description="Enable collection of high-quality training data for DSPy optimization. "
        "Samples are collected when extraction quality thresholds are met.",
    )

    # Gemma Relation Extraction (Sprint 13: ADR-018)
    # Sprint 51: Updated default to nemotron-3-nano (fast MoE model on DGX Spark)
    gemma_model: str = Field(
        default="nemotron-3-nano",
        description="LLM model for relation extraction (Ollama) - use GEMMA_MODEL env var to override",
    )
    gemma_temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="Temperature for Gemma relation extraction"
    )
    gemma_num_predict: int = Field(
        default=2000, ge=100, le=4096, description="Max tokens for Gemma relation extraction"
    )
    gemma_num_ctx: int = Field(
        default=16384, ge=2048, le=32768, description="Context window for Gemma model"
    )

    # Entity/Relation Extraction Pipeline Selection (Sprint 14: Feature 14.2, Sprint 20+21)
    # Sprint 25 Feature 25.7: Removed "three_phase" option (deprecated per ADR-026)
    extraction_pipeline: Literal["lightrag_default", "llm_extraction"] = Field(
        default="llm_extraction",
        description=(
            "Entity/relation extraction pipeline to use:\n"
            "- 'llm_extraction': Pure LLM (NO SpaCy, high quality, ~200-300s/doc) - DEFAULT Sprint 21+\n"
            "- 'lightrag_default': Legacy LightRAG baseline (for comparison only)\n"
            "Note: 'three_phase' removed in Sprint 25 (deprecated per ADR-026)"
        ),
    )
    enable_legacy_extraction: bool = Field(
        default=False, description="Enable legacy LightRAG extraction for A/B comparison"
    )
    extraction_batch_size: int = Field(
        default=10, ge=1, le=100, description="Batch size for extraction operations"
    )
    extraction_max_workers: int = Field(
        default=4, ge=1, le=16, description="Max worker threads for parallel extraction"
    )

    # Error Handling & Retry Logic (Sprint 14: Feature 14.5)
    extraction_max_retries: int = Field(
        default=3, ge=1, le=10, description="Max retry attempts for transient extraction failures"
    )
    extraction_retry_min_wait: float = Field(
        default=2.0, ge=0.1, le=10.0, description="Minimum wait time between retries (seconds)"
    )
    extraction_retry_max_wait: float = Field(
        default=10.0, ge=1.0, le=60.0, description="Maximum wait time between retries (seconds)"
    )
    extraction_enable_graceful_degradation: bool = Field(
        default=True, description="Continue with degraded features on non-critical failures"
    )

    # Sprint 37 Feature 37.2: Worker Pool Configuration
    graph_extraction_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Number of parallel workers for graph extraction (Sprint 37)",
    )
    extraction_worker_timeout: int = Field(
        default=120,
        ge=30,
        le=600,
        description="Timeout per chunk extraction in seconds (Sprint 37)",
    )

    # Neo4j Graph Database
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: SecretStr = Field(
        default=SecretStr("aegis-rag-neo4j-password"), description="Neo4j password"
    )
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")

    # Graph Query Configuration (Sprint 6: Advanced Query Operations)
    graph_query_cache_enabled: bool = Field(default=True, description="Enable query result caching")
    graph_query_cache_max_size: int = Field(
        default=1000, ge=10, le=10000, description="Maximum cache entries (LRU eviction)"
    )
    graph_query_cache_ttl_seconds: int = Field(
        default=300, ge=10, le=3600, description="Cache TTL in seconds (default: 5 minutes)"
    )
    graph_batch_query_max_concurrent: int = Field(
        default=10, ge=1, le=50, description="Maximum concurrent batch queries"
    )
    graph_query_timeout_seconds: int = Field(
        default=30, ge=5, le=300, description="Query execution timeout in seconds"
    )

    # Community Detection Configuration (Sprint 6.3: Community Detection & Clustering)
    graph_community_algorithm: str = Field(
        default="leiden", description="Community detection algorithm (leiden or louvain)"
    )
    graph_community_resolution: float = Field(
        default=1.0, ge=0.1, le=5.0, description="Resolution parameter for community detection"
    )
    graph_community_min_size: int = Field(
        default=3, ge=1, le=100, description="Minimum community size to include"
    )
    graph_community_use_gds: bool = Field(
        default=True, description="Try Neo4j GDS first, fallback to NetworkX"
    )
    graph_community_labeling_enabled: bool = Field(
        default=True, description="Enable automatic community labeling with LLM"
    )
    graph_community_labeling_model: str = Field(
        default="llama3.2:3b", description="Ollama model for community labeling"
    )

    # Graph Visualization Settings (Sprint 6: Feature 6.5)
    graph_visualization_max_nodes: int = Field(
        default=100, ge=1, le=1000, description="Maximum nodes to return in visualization"
    )
    graph_visualization_default_depth: int = Field(
        default=1, ge=1, le=5, description="Default depth for subgraph traversal"
    )
    graph_visualization_default_format: str = Field(
        default="d3", description="Default visualization format (d3, cytoscape, visjs)"
    )

    # Graph Analytics Settings (Sprint 6: Feature 6.6)
    graph_analytics_use_gds: bool = Field(
        default=True, description="Use Neo4j GDS plugin if available, fallback to NetworkX"
    )
    graph_analytics_pagerank_iterations: int = Field(
        default=20, ge=1, le=100, description="PageRank algorithm iterations"
    )
    graph_analytics_cache_ttl_seconds: int = Field(
        default=600, ge=0, le=3600, description="Cache TTL for analytics results (10 min default)"
    )
    graph_recommendations_top_k: int = Field(
        default=5, ge=1, le=50, description="Number of recommendations to return"
    )
    graph_recommendations_method: str = Field(
        default="collaborative",
        description="Default recommendation method (collaborative, community, relationships, attributes)",
    )

    # Sprint 78: Semantic Graph Search Configuration
    # Sprint 80 Quick Win: Increased from 1→2 for better multi-hop reasoning (RAGAS Context Recall)
    # Higher values find more related entities for complex questions. Use 3 for HotpotQA-style queries.
    graph_expansion_hops: int = Field(
        default=2,
        ge=1,
        le=3,
        description="Number of hops for graph entity expansion (1-3). "
        "2+ recommended for multi-hop reasoning questions like HotpotQA.",
    )
    graph_min_entities_threshold: int = Field(
        default=10, ge=5, le=20, description="Minimum entities before LLM synonym fallback (5-20)"
    )
    graph_max_synonyms_per_entity: int = Field(
        default=3, ge=1, le=5, description="Maximum synonyms to generate per entity (1-5)"
    )
    graph_semantic_reranking_enabled: bool = Field(
        default=True, description="Enable semantic reranking of graph entities (BGE-M3)"
    )

    # Sprint 80 Feature 80.1: Faithfulness Optimization
    # Activated 2026-01-09 for RAGAS Faithfulness testing (Sprint 80.3+)
    strict_faithfulness_enabled: bool = Field(
        default=True,
        description="Enable strict citation mode requiring citations for EVERY sentence. "
        "When True, uses FAITHFULNESS_STRICT_PROMPT which forbids general knowledge. "
        "Designed to maximize RAGAS Faithfulness score (F=0.55→0.85+). Default: True.",
    )

    # Sprint 81 Feature 81.8: No-Hedging Faithfulness Optimization
    # Eliminates LLM meta-commentary like "This information is not available"
    # that causes RAGAS Faithfulness penalties even when info IS in context.
    no_hedging_enabled: bool = Field(
        default=True,
        description="Enable no-hedging prompt mode that forbids LLM meta-commentary about "
        "document contents (e.g., 'This information is not available'). "
        "Eliminates false Faithfulness penalties. Expected: F=0.63→0.80 (+27%). Default: True.",
    )

    # Sprint 80 Feature 80.2: Graph→Vector Fallback
    graph_vector_fallback_enabled: bool = Field(
        default=True,
        description="Enable automatic fallback to vector search when graph search returns "
        "empty results. Improves Context Recall by ensuring contexts are always retrieved. "
        "Default: True.",
    )

    # Temporal Graph Features (Sprint 6.4: Bi-Temporal Model)
    graph_temporal_enabled: bool = Field(
        default=True, description="Enable temporal features (bi-temporal model)"
    )
    graph_version_retention_count: int = Field(
        default=10, ge=0, le=100, description="Max versions to retain per entity (0=unlimited)"
    )
    graph_temporal_index_enabled: bool = Field(
        default=True, description="Create indexes on temporal properties"
    )
    graph_evolution_tracking_enabled: bool = Field(
        default=True, description="Track entity changes and evolution"
    )
    graph_temporal_precision: str = Field(
        default="second", description="Temporal precision (second or millisecond)"
    )

    # Sprint 39 Feature 39.1: Bi-Temporal Queries Feature Flag (ADR-042)
    temporal_queries_enabled: bool = Field(
        default=False,
        description="Enable bi-temporal queries (Opt-In per ADR-042) - requires temporal indexes",
    )
    temporal_version_retention: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Max versions per entity before cleanup (Sprint 39)",
    )

    # Redis Cache
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: SecretStr | None = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_ttl: int = Field(default=3600, description="Redis default TTL in seconds")
    use_redis_checkpointer: bool = Field(
        default=True, description="Use Redis for LangGraph checkpointing (Sprint 11 Feature 11.5)"
    )

    # LangSmith Observability (Optional - Sprint 115 Feature 115.6)
    langsmith_api_key: SecretStr | None = Field(
        default=None,
        description="LangSmith API key (get from https://smith.langchain.com/settings)",
    )
    langsmith_project: str = Field(
        default="aegis-rag-sprint115", description="LangSmith project name for organizing traces"
    )
    langsmith_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        description="LangSmith API endpoint (default: https://api.smith.langchain.com)",
    )
    langsmith_tracing: bool = Field(
        default=False,
        description=(
            "Enable LangSmith tracing for LangGraph agents. "
            "Provides instant LLM call visibility, token counts, and latency breakdown. "
            "No code changes required - just set LANGSMITH_TRACING=true and LANGSMITH_API_KEY."
        ),
    )

    # LangGraph Configuration (Sprint 4: Multi-Agent Orchestration)
    langgraph_checkpointer: str = Field(
        default="memory",
        description="LangGraph checkpointer type (memory, sqlite, postgres)",
    )
    langgraph_recursion_limit: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Maximum recursion depth for LangGraph execution",
    )

    # LightRAG Settings (Sprint 5: Graph RAG)
    lightrag_enabled: bool = Field(default=True, description="Enable LightRAG graph retrieval")
    lightrag_working_dir: str = Field(
        default="./data/lightrag", description="LightRAG working directory for graph storage"
    )

    # LightRAG LLM Configuration
    # Sprint 51: Updated default to nemotron-3-nano (fast MoE model on DGX Spark)
    lightrag_llm_model: str = Field(
        default="nemotron-3-nano",
        description="Ollama LLM model for LightRAG entity extraction - use LIGHTRAG_LLM_MODEL env var to override",
    )
    lightrag_llm_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="LLM temperature for extraction (low for consistency)",
    )
    lightrag_llm_max_tokens: int = Field(
        default=8192, ge=100, le=32768, description="Max tokens for LLM response (Nemotron 32k context)"
    )

    # LightRAG Embedding Configuration
    lightrag_embedding_model: str = Field(
        default="nomic-embed-text", description="Ollama embedding model"
    )
    lightrag_embedding_dim: int = Field(
        default=768, ge=128, le=4096, description="Embedding dimension (nomic-embed-text=768)"
    )

    # Graph Construction Settings
    lightrag_entity_extraction_batch_size: int = Field(
        default=5, ge=1, le=50, description="Batch size for entity extraction"
    )
    lightrag_max_tokens_per_chunk: int = Field(
        default=1200, ge=500, le=4000, description="Max tokens per chunk for extraction"
    )
    lightrag_max_entities_per_doc: int = Field(
        default=50, ge=10, le=200, description="Maximum entities to extract per document"
    )

    # MCP Server
    mcp_server_port: int = Field(default=3000, description="MCP server port")
    mcp_auth_enabled: bool = Field(default=False, description="Enable MCP authentication")

    # Rate Limiting (Sprint 22 Feature 22.2.3)
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(
        default=100, ge=1, le=1000, description="Global requests per minute per IP (development)"
    )
    rate_limit_upload: int = Field(
        default=10, ge=1, le=100, description="Upload requests per minute per IP"
    )
    rate_limit_search: int = Field(
        default=100, ge=1, le=500, description="Search requests per minute per IP"
    )
    rate_limit_storage_uri: str = Field(
        default="memory://", description="Rate limit storage (memory:// or redis://host:port)"
    )

    # CORS Configuration (Sprint 22 Feature 22.2.3)
    # Sprint 31: Extended port range 5170-5180 for frontend dev server flexibility
    # Sprint 92: Added port 80 for Docker frontend deployment
    cors_origins: list[str] = Field(
        default=[
            "http://localhost",  # Sprint 92: Port 80 (default HTTP)
            "http://localhost:80",  # Sprint 92: Explicit port 80
            "http://localhost:3000",
            "http://localhost:5170",
            "http://localhost:5171",
            "http://localhost:5172",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://localhost:5176",
            "http://localhost:5177",
            "http://localhost:5178",
            "http://localhost:5179",
            "http://localhost:5180",
        ],
        description="Allowed CORS origins. Override with CORS_ORIGINS env var (comma-separated). "
        "Sprint 92: Include external IP for Docker deployment, e.g., http://192.168.178.10",
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials in CORS")
    cors_allow_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods for CORS",
    )
    cors_allow_headers: list[str] = Field(default=["*"], description="Allowed headers for CORS")

    # Performance
    max_concurrent_requests: int = Field(default=50, description="Maximum concurrent requests")
    request_timeout: int = Field(default=60, description="Request timeout in seconds")

    # Retrieval Configuration
    # Sprint 80 Feature 80.4: Increased from 5→10 to improve Context Recall (RAGAS optimization)
    # SOTA systems use 10-20 contexts. More contexts = higher Context Recall, but diminishing returns.
    retrieval_top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of documents to retrieve. Increased to 10 for better Context Recall "
        "(RAGAS metric). SOTA systems use 10-20. Higher values improve recall but add latency.",
    )
    retrieval_score_threshold: float = Field(default=0.7, description="Minimum relevance score")

    # Sprint 51: Relevance Threshold for Hybrid Search
    # Filters out irrelevant results when no document meets quality threshold
    hybrid_search_min_relevance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum vector similarity score for hybrid search results. "
        "If no result exceeds this threshold, return empty results. "
        "0.3 = weak match, 0.5 = moderate, 0.7 = strong.",
    )
    hybrid_search_require_relevant: bool = Field(
        default=True,
        description="If True, return empty results when no document meets min_relevance threshold. "
        "If False, always return top-k results regardless of quality.",
    )

    # Vector Search Agent Configuration (Sprint 4.3)
    vector_agent_timeout: int = Field(
        default=30, description="Vector search agent timeout in seconds"
    )
    vector_agent_max_retries: int = Field(default=3, description="Max retries for vector search")
    vector_agent_use_reranking: bool = Field(
        default=True, description="Enable reranking in vector search agent"
    )

    # Chunking Configuration (Sprint 3: Adaptive Chunking)
    pdf_chunk_size: int = Field(default=1024, description="Token limit for PDF/DOCX chunks")
    code_chunk_size: int = Field(default=512, description="Token limit for code file chunks")
    markdown_chunk_size: int = Field(default=768, description="Token limit for Markdown chunks")
    text_chunk_size: int = Field(default=512, description="Token limit for plain text chunks")
    chunk_overlap: int = Field(default=50, description="Overlap between chunks in tokens")

    # Docling Container Configuration (Sprint 21: GPU-Accelerated OCR, Sprint 30: Port Config)
    docling_base_url: str = Field(
        default="http://localhost:8080",
        description="Docling container HTTP endpoint (Docker maps 8080 -> 5001)",
    )
    docling_timeout_seconds: int = Field(
        default=900,
        description="HTTP timeout for Docling requests (900s = 15min for complex PDFs, Sprint 30)",
    )
    docling_max_retries: int = Field(
        default=3, description="Max retry count for Docling transient failures"
    )

    # Embedding Backend Configuration (Sprint 35 Feature 35.8: Sentence-Transformers Migration)
    # Sprint 61 Feature 61.1: Default switched to native sentence-transformers (5x faster)
    # Sprint 87 Feature 87.4: Added flag-embedding for multi-vector (dense + sparse)
    embedding_backend: Literal["ollama", "sentence-transformers", "flag-embedding"] = Field(
        default="sentence-transformers",
        description=(
            "Embedding service backend selection:\n"
            "- 'flag-embedding': BGE-M3 multi-vector (Sprint 87, dense + sparse for native hybrid)\n"
            "- 'sentence-transformers': Native BGE-M3 (default, 5x faster, Sprint 61, dense-only)\n"
            "- 'ollama': Ollama HTTP API (backward compatible, slower)"
        ),
    )
    st_model_name: str = Field(
        default="BAAI/bge-m3",
        description="HuggingFace model for sentence-transformers backend (1024-dim)",
    )
    st_device: str = Field(
        default="auto",
        description="Device for sentence-transformers ('auto', 'cuda', 'cpu')",
    )
    st_batch_size: int = Field(
        default=64,
        ge=1,
        le=512,
        description="Batch size for sentence-transformers GPU processing",
    )

    # Reranking Backend Configuration (Sprint 61 Feature 61.2)
    reranking_backend: Literal["cross_encoder", "llm"] = Field(
        default="cross_encoder",
        description=(
            "Reranking service backend selection:\n"
            "- 'cross_encoder': MS MARCO MiniLM (default, 17x faster, Sprint 61)\n"
            "- 'llm': LLM-based reranking (backward compatible, slower)"
        ),
    )
    ce_model_name: str = Field(
        default="BAAI/bge-reranker-v2-m3",
        description="HuggingFace model for cross-encoder reranking (multilingual, ~560MB)",
    )
    ce_device: str = Field(
        default="auto",
        description="Device for cross-encoder ('auto', 'cuda', 'cpu')",
    )
    ce_max_length: int = Field(
        default=512,
        ge=128,
        le=2048,
        description="Maximum token length for query-document pairs",
    )

    # Sprint 125 Feature 125.2: vLLM Provider Configuration
    vllm_enabled: bool = Field(
        default=False,
        description="Enable vLLM provider for extraction tasks (Sprint 125.2, 256+ concurrent requests)",
    )
    vllm_base_url: str = Field(
        default="http://localhost:8001",
        description="vLLM OpenAI-compatible API endpoint (Sprint 125.2)",
    )
    vllm_model: str = Field(
        default="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4",
        description="vLLM model name for extraction tasks (Sprint 125.2)",
    )

    # Sprint 33 Performance: Parallel Ingestion Settings
    ingestion_parallel_files: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Maximum concurrent files to process during ingestion (default 3, increase if RAM allows)",
    )
    ingestion_parallel_chunks: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum concurrent chunk embeddings to generate (default 10)",
    )
    embedding_max_concurrent: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum concurrent embedding requests in batch operations (default 20). "
        "DGX Spark with 128GB unified memory can handle 50+. Smaller GPUs use 10.",
    )
    ingestion_max_concurrent_vlm: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum concurrent VLM image processing calls (default 5)",
    )

    # Graphiti Memory Configuration (Sprint 7: Episodic Memory)
    graphiti_enabled: bool = Field(default=True, description="Enable Graphiti episodic memory")
    graphiti_llm_model: str = Field(
        default="llama3.2:8b", description="Ollama model for Graphiti entity extraction"
    )
    graphiti_embedding_model: str = Field(
        default="nomic-embed-text", description="Ollama model for Graphiti embeddings"
    )
    graphiti_ollama_base_url: str = Field(
        default="http://localhost:11434", description="Ollama base URL for Graphiti"
    )

    # Memory Router Configuration (Sprint 7: 3-Layer Memory)
    memory_router_enabled: bool = Field(default=True, description="Enable 3-layer memory routing")
    redis_memory_url: str = Field(
        default="redis://localhost:6379/0", description="Redis URL for working memory"
    )
    redis_memory_ttl_seconds: int = Field(
        default=3600, description="Redis memory TTL in seconds (1 hour)"
    )

    # Memory Consolidation (Sprint 7: Background Consolidation)
    memory_consolidation_enabled: bool = Field(
        default=True, description="Enable automatic memory consolidation"
    )
    memory_consolidation_interval_minutes: int = Field(
        default=30, description="Consolidation interval in minutes"
    )
    memory_consolidation_min_access_count: int = Field(
        default=3, description="Minimum access count for consolidation"
    )

    # Temporal Memory Retention Policy (Sprint 11: Feature 11.8)
    # Configurable retention for Graphiti temporal memory versions
    # Set temporal_retention_days=0 for infinite retention (no auto-purge)
    temporal_retention_days: int = Field(
        default=365, ge=0, description="Days to retain temporal versions (0 = infinite retention)"
    )

    temporal_auto_purge: bool = Field(
        default=True, description="Automatically purge old temporal versions on schedule"
    )

    temporal_purge_schedule: str = Field(
        default="0 2 * * *", description="Cron schedule for temporal purge job"  # 2 AM daily
    )

    # Web Search Configuration (Sprint 63 Feature 63.9)
    web_search_enabled: bool = Field(
        default=False,
        description="Enable web search with DuckDuckGo (default: disabled for privacy)",
    )
    web_search_max_results: int = Field(
        default=5, ge=1, le=20, description="Maximum web search results per query"
    )
    web_search_timeout: int = Field(
        default=10, ge=1, le=30, description="Web search timeout in seconds"
    )
    web_search_region: str = Field(
        default="de-DE", description="Region code for web search (e.g., de-DE, en-US)"
    )
    web_search_safesearch: Literal["strict", "moderate", "off"] = Field(
        default="moderate", description="SafeSearch setting for web results"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """
        Validate log level is one of the standard Python logging levels.

        Args:
            v: Log level string (case-insensitive)

        Returns:
            Uppercase log level string

        Raises:
            ValueError: If log level is not valid

        Example:
            >>> Settings(log_level="info").log_level
            'INFO'
            >>> Settings(log_level="DEBUG").log_level
            'DEBUG'
        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """
        Parse CORS origins from comma-separated string or list.

        Args:
            v: CORS origins as string (comma-separated) or list

        Returns:
            List of origin URLs

        Example:
            >>> Settings(cors_origins="http://localhost:3000,http://localhost:5173").cors_origins
            ['http://localhost:3000', 'http://localhost:5173']
            >>> Settings(cors_origins=["http://localhost:3000"]).cors_origins
            ['http://localhost:3000']
        """
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def qdrant_url(self) -> str:
        """
        Get Qdrant HTTP URL from host and port.

        Returns:
            Formatted HTTP URL (e.g., "http://localhost:6333")

        Example:
            >>> settings.qdrant_url
            'http://localhost:6333'

        Notes:
            - Always returns HTTP URL (not HTTPS)
            - For production, use reverse proxy with TLS termination
        """
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @property
    def redis_url(self) -> str:
        """
        Get Redis connection URL with optional password.

        Returns:
            Formatted Redis URL (e.g., "redis://localhost:6379/0" or "redis://:password@localhost:6379/0")

        Example:
            >>> # Without password
            >>> settings.redis_url
            'redis://localhost:6379/0'
            >>> # With password
            >>> settings_with_pw = Settings(redis_password="secret123")
            >>> settings_with_pw.redis_url
            'redis://:secret123@localhost:6379/0'

        Notes:
            - Password is included in URL if redis_password is set
            - Format follows Redis connection string spec: redis://[:password@]host:port/db
            - For production, always use password-protected Redis
        """
        password = f":{self.redis_password.get_secret_value()}@" if self.redis_password else ""
        return f"redis://{password}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def jwt_secret(self) -> str:
        """
        Get JWT secret key, using api_secret_key as fallback.

        Returns:
            JWT secret key string

        Notes:
            - Uses jwt_secret_key if set
            - Falls back to api_secret_key for backward compatibility
            - For production, ALWAYS set JWT_SECRET_KEY environment variable

        Example:
            >>> settings.jwt_secret
            'your-secret-key-here'
        """
        if self.jwt_secret_key:
            return self.jwt_secret_key.get_secret_value()
        # Fallback to api_secret_key for backward compatibility
        return self.api_secret_key.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance (singleton pattern).

    This function uses @lru_cache to ensure only one Settings instance is created
    throughout the application lifecycle. This is important for:
    - Performance: Avoid re-parsing environment variables on every access
    - Consistency: All modules use the same configuration
    - Memory efficiency: Single instance instead of multiple copies

    Returns:
        Settings: Cached application settings instance

    Example:
        >>> from src.core.config import get_settings
        >>> settings1 = get_settings()
        >>> settings2 = get_settings()
        >>> settings1 is settings2  # Same instance
        True
        >>> settings1.app_name
        'aegis-rag'

    Notes:
        - First call loads from environment and caches the instance
        - Subsequent calls return cached instance (O(1) lookup)
        - To reload settings, restart the application (no hot-reload)
        - For testing, consider using Settings() directly instead of singleton

    See Also:
        - Settings: The settings class definition
        - functools.lru_cache: Python's LRU cache decorator
    """
    return Settings()


# Global settings instance for convenience
settings = get_settings()
