"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

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

    # Ollama LLM (Primary)
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    ollama_model_generation: str = Field(
        default="llama3.1:8b", description="Ollama model for generation (128K context)"
    )
    ollama_model_query: str = Field(
        default="llama3.2:3b", description="Ollama model for query understanding"
    )
    ollama_model_embedding: str = Field(
        default="nomic-embed-text", description="Ollama embedding model"
    )
    ollama_model_router: str = Field(
        default="llama3.2:3b",
        description="Ollama model for query routing and intent classification",
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

    # Qdrant Vector Database
    qdrant_host: str = Field(default="localhost", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant HTTP port")
    qdrant_grpc_port: int = Field(default=6334, description="Qdrant gRPC port")
    qdrant_api_key: SecretStr | None = Field(default=None, description="Qdrant API key")
    qdrant_collection: str = Field(default="aegis_documents", description="Qdrant collection name")
    qdrant_use_grpc: bool = Field(default=False, description="Use gRPC for Qdrant")

    # Document Ingestion Security
    documents_base_path: str = Field(
        default="./data", description="Base directory for document ingestion (security boundary)"
    )

    # Reranker Settings (Sprint 3: Cross-Encoder Reranking)
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="HuggingFace cross-encoder model for reranking",
    )
    reranker_batch_size: int = Field(default=32, description="Batch size for reranking inference")
    reranker_cache_dir: str = Field(
        default="./data/models", description="Directory for caching HuggingFace models"
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

    # Redis Cache
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: SecretStr | None = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_ttl: int = Field(default=3600, description="Redis default TTL in seconds")

    # LangSmith Observability (Optional)
    langsmith_api_key: SecretStr | None = Field(default=None, description="LangSmith API key")
    langsmith_project: str = Field(default="aegis-rag", description="LangSmith project name")
    langsmith_tracing: bool = Field(default=False, description="Enable LangSmith tracing")

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
    lightrag_llm_model: str = Field(
        default="llama3.2:3b",
        description="Ollama LLM model for LightRAG entity extraction (requires good instruction following)"
    )
    lightrag_llm_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="LLM temperature for extraction (low for consistency)",
    )
    lightrag_llm_max_tokens: int = Field(
        default=4096, ge=100, le=32768, description="Max tokens for LLM response"
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

    # Performance
    max_concurrent_requests: int = Field(default=50, description="Maximum concurrent requests")
    request_timeout: int = Field(default=60, description="Request timeout in seconds")

    # Retrieval Configuration
    retrieval_top_k: int = Field(default=5, description="Number of documents to retrieve")
    retrieval_score_threshold: float = Field(default=0.7, description="Minimum relevance score")

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
    memory_router_enabled: bool = Field(
        default=True, description="Enable 3-layer memory routing"
    )
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

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v

    @property
    def qdrant_url(self) -> str:
        """Get Qdrant HTTP URL."""
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        password = f":{self.redis_password.get_secret_value()}@" if self.redis_password else ""
        return f"redis://{password}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Application settings
    """
    return Settings()


# Global settings instance for convenience
settings = get_settings()
