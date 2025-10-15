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
    api_host: str = Field(default="0.0.0.0", description="API server host")  # noqa: S104
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

    # Neo4j Graph Database
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: SecretStr = Field(
        default=SecretStr("aegis-rag-neo4j-password"), description="Neo4j password"
    )
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")

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

    # MCP Server
    mcp_server_port: int = Field(default=3000, description="MCP server port")
    mcp_auth_enabled: bool = Field(default=False, description="Enable MCP authentication")

    # Performance
    max_concurrent_requests: int = Field(default=50, description="Maximum concurrent requests")
    request_timeout: int = Field(default=60, description="Request timeout in seconds")

    # Retrieval Configuration
    retrieval_top_k: int = Field(default=5, description="Number of documents to retrieve")
    retrieval_score_threshold: float = Field(default=0.7, description="Minimum relevance score")

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
