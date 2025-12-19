"""LightRAG initialization and configuration.

Sprint 55 Feature 55.3: Handles LightRAG instance creation and setup.

This module provides:
- LightRAG instance creation with Neo4j backend
- Ollama LLM function configuration via AegisLLMProxy
- BGE-M3 embedding service integration
"""

import os
from pathlib import Path
from typing import Any

import structlog

from src.components.graph_rag.lightrag.types import LightRAGConfig
from src.core.config import settings

logger = structlog.get_logger(__name__)


def get_default_config() -> LightRAGConfig:
    """Get default LightRAG configuration from settings.

    Returns:
        LightRAGConfig with default values from application settings
    """
    # Sprint 51: Read extraction model from YAML config first
    llm_model = settings.lightrag_llm_model
    try:
        from src.components.llm_proxy.config import LLMProxyConfig

        llm_config = LLMProxyConfig()
        yaml_model = llm_config.get_default_model("local_ollama", "extraction")
        if yaml_model:
            llm_model = yaml_model
    except Exception:
        pass

    return LightRAGConfig(
        working_dir=str(settings.lightrag_working_dir),
        llm_model=llm_model,
        embedding_model=settings.lightrag_embedding_model,
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password.get_secret_value(),
    )


def setup_neo4j_environment(config: LightRAGConfig) -> None:
    """Set Neo4j environment variables required by LightRAG's Neo4JStorage.

    Args:
        config: LightRAG configuration with Neo4j credentials
    """
    os.environ["NEO4J_URI"] = config.neo4j_uri
    os.environ["NEO4J_USERNAME"] = config.neo4j_user
    os.environ["NEO4J_PASSWORD"] = config.neo4j_password


def create_aegis_llm_function(llm_model: str) -> Any:
    """Create multi-cloud LLM completion function for LightRAG.

    Sprint 23: Uses AegisLLMProxy for intelligent routing.

    Args:
        llm_model: Default LLM model name

    Returns:
        Async function compatible with LightRAG's llm_model_func
    """
    from src.components.llm_proxy import get_aegis_llm_proxy
    from src.components.llm_proxy.models import (
        Complexity,
        LLMTask,
        QualityRequirement,
        TaskType,
    )

    proxy = get_aegis_llm_proxy()

    async def aegis_llm_complete(
        prompt: str,
        system_prompt: str | None = None,
        model: str = llm_model,
        **kwargs: Any,
    ) -> str:
        """Multi-cloud LLM completion function for LightRAG.

        Sprint 23: Uses AegisLLMProxy for intelligent routing.
        LightRAG sends entity extraction instructions in system_prompt
        and the actual task in prompt.
        """
        # Combine system prompt and user prompt
        combined_prompt = prompt
        if system_prompt:
            combined_prompt = f"{system_prompt}\n\n{prompt}"

        # Log prompts being sent to LLM
        logger.info(
            "lightrag_llm_request",
            model=model,
            system_prompt_length=len(system_prompt) if system_prompt else 0,
            system_prompt_preview=(system_prompt[:500] if system_prompt else ""),
            user_prompt_length=len(prompt),
            user_prompt_preview=prompt[:500],
        )

        # Sprint 23: Use AegisLLMProxy for generation
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt=combined_prompt,
            quality_requirement=QualityRequirement.MEDIUM,
            complexity=Complexity.MEDIUM,
            temperature=settings.lightrag_llm_temperature,
            max_tokens=settings.lightrag_llm_max_tokens,
            model_local=model,
        )

        response = await proxy.generate(task)
        result: str = response.content

        # Log response from LLM
        logger.info(
            "lightrag_llm_response",
            provider=response.provider,
            model=response.model,
            response_length=len(result),
            response_preview=result[:500],
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
        )

        return result

    return aegis_llm_complete


class UnifiedEmbeddingFunc:
    """Wrapper for UnifiedEmbeddingService compatible with LightRAG.

    Sprint 12: This wrapper is PICKLE-COMPATIBLE because UnifiedEmbeddingService
    uses lazy AsyncClient creation instead of storing it as instance variable.

    Sprint 16: Uses BGE-M3 (1024 dimensions) for system-wide standardization.
    """

    def __init__(self, embedding_dim: int = 1024):
        """Initialize embedding function wrapper.

        Args:
            embedding_dim: Embedding dimension (default: 1024 for BGE-M3)
        """
        self.embedding_dim = embedding_dim
        self._service = None

    @property
    def unified_service(self):
        """Lazy-load the embedding service."""
        if self._service is None:
            from src.components.shared.embedding_service import get_embedding_service

            self._service = get_embedding_service()
        return self._service

    async def __call__(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        """Generate embeddings using shared service.

        Args:
            texts: List of texts to embed
            **kwargs: Additional arguments (ignored)

        Returns:
            List of embedding vectors
        """
        return await self.unified_service.embed_batch(texts)

    @property
    def async_func(self) -> None:
        """Return self to indicate this is an async function."""
        return self


async def create_lightrag_instance(config: LightRAGConfig) -> Any:
    """Create and initialize a LightRAG instance.

    Args:
        config: LightRAG configuration

    Returns:
        Initialized LightRAG instance

    Raises:
        ImportError: If LightRAG is not installed
        Exception: If initialization fails
    """
    try:
        from lightrag import LightRAG
        from lightrag.kg.shared_storage import initialize_pipeline_status

        # Setup Neo4j environment variables
        setup_neo4j_environment(config)

        # Create working directory
        working_dir = Path(config.working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)

        # Create LLM and embedding functions
        llm_func = create_aegis_llm_function(config.llm_model)
        embedding_func = UnifiedEmbeddingFunc(embedding_dim=1024)

        # Initialize LightRAG with Neo4j backend
        # Sprint 16 Feature 16.6: Disable internal chunking (use ChunkingService instead)
        rag = LightRAG(
            working_dir=str(working_dir),
            llm_model_func=llm_func,
            embedding_func=embedding_func,
            graph_storage="Neo4JStorage",
            llm_model_max_async=2,  # Reduce from 4 to 2 workers
            # Sprint 16: Internal chunking disabled - we use ChunkingService
            chunk_token_size=99999,  # Effectively disable
            chunk_overlap_token_size=0,
            top_k=15,
            chunk_top_k=10,
            max_entity_tokens=2500,
            max_relation_tokens=2500,
            max_total_tokens=7000,
            cosine_threshold=0.05,
        )

        # Initialize storages
        await rag.initialize_storages()
        await initialize_pipeline_status()

        logger.info(
            "lightrag_instance_created",
            working_dir=str(working_dir),
            llm_model=config.llm_model,
        )

        return rag

    except ImportError as e:
        logger.error(
            "lightrag_import_failed",
            error=str(e),
            hint="Run: poetry add lightrag-hku networkx graspologic",
        )
        raise
    except Exception as e:
        logger.error("lightrag_initialization_failed", error=str(e))
        raise


__all__ = [
    "get_default_config",
    "setup_neo4j_environment",
    "create_aegis_llm_function",
    "UnifiedEmbeddingFunc",
    "create_lightrag_instance",
]
