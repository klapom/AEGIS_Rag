"""Graphiti Wrapper with Ollama Integration for Episodic Memory.

This module provides a wrapper around Graphiti episodic memory system with:
- Custom Ollama LLM client implementation
- Entity and relationship extraction using Ollama
- Temporal graph storage in Neo4j
- Episode management and search capabilities
"""

from datetime import UTC, datetime
from typing import Any

import structlog
from graphiti_core import Graphiti
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.llm_client import LLMClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.search.search_config import SearchConfig
from ollama import AsyncClient

from src.components.graph_rag.neo4j_client import get_neo4j_client
from src.components.llm_proxy import get_aegis_llm_proxy
from src.components.llm_proxy.models import (
    Complexity,
    LLMTask,
    QualityRequirement,
    TaskType,
)
from src.core.config import settings
from src.core.exceptions import LLMError, MemoryError

logger = structlog.get_logger(__name__)


class OllamaLLMClient(LLMClient):
    """Custom LLM client for Graphiti using AegisLLMProxy.

    Sprint 25 Feature 25.10: Migrated from direct Ollama to multi-cloud routing.

    Implements Graphiti's LLMClient interface to use AegisLLMProxy for:
    - Entity and relationship extraction (memory consolidation)
    - Text generation for memory operations
    - Multi-cloud routing: Local Ollama → Alibaba Cloud → OpenAI
    - Cost tracking and observability
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.1,
    ) -> None:
        """Initialize LLM client with AegisLLMProxy.

        Args:
            base_url: Ollama server URL (deprecated, kept for compatibility)
            model: Preferred model name (default: from settings)
            temperature: Generation temperature (default: 0.1 for consistency)
        """
        self.base_url = base_url or settings.graphiti_ollama_base_url
        self.model = model or settings.graphiti_llm_model
        self.temperature = temperature

        # Sprint 25: Use AegisLLMProxy for multi-cloud routing
        self.proxy = get_aegis_llm_proxy()

        # Keep AsyncClient for embeddings (embeddings always local)
        self.client = AsyncClient(host=self.base_url)

        logger.info(
            "Initialized OllamaLLMClient with AegisLLMProxy",
            preferred_model=self.model,
            temperature=self.temperature,
        )

    async def _generate_response(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        """Generate text response via AegisLLMProxy.

        Sprint 12: Renamed from generate_response() to _generate_response()
        to match updated Graphiti LLMClient abstract method.
        Sprint 25: Migrated to AegisLLMProxy for multi-cloud routing.

        Args:
            messages: list of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response

        Raises:
            LLMError: If generation fails
        """
        try:
            # Convert messages to prompt (Graphiti uses chat format)
            prompt_parts = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prompt_parts.append(f"{role}: {content}")
            prompt = "\n\n".join(prompt_parts)

            # Create LLM task for memory consolidation
            task = LLMTask(
                task_type=TaskType.MEMORY_CONSOLIDATION,
                prompt=prompt,
                quality_requirement=QualityRequirement.HIGH,
                complexity=Complexity.MEDIUM,
                max_tokens=max_tokens,
                temperature=self.temperature,
                model_local=self.model,  # Preferred local model
            )

            # Execute via proxy
            result = await self.proxy.generate(task)

            logger.debug(
                "Generated response via AegisLLMProxy",
                provider=result.provider,
                model=result.model,
                tokens_used=result.tokens_used,
                cost_usd=result.cost_usd,
                latency_ms=result.latency_ms,
                output_length=len(result.content),
            )

            return result.content

        except Exception as e:
            logger.error("LLM generation failed", error=str(e))
            raise LLMError(operation="graphiti_memory_generation", reason=str(e)) from e

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Ollama.

        Args:
            texts: list of texts to embed

        Returns:
            list of embedding vectors

        Raises:
            LLMError: If embedding generation fails
        """
        try:
            embeddings = []
            for text in texts:
                response = await self.client.embeddings(
                    model=settings.graphiti_embedding_model,
                    prompt=text,
                )

                if not response or "embedding" not in response:
                    raise LLMError(
                        operation="graphiti_embedding_generation",
                        reason=f"Invalid embedding response for text: {text[:50]}",
                    )

                embeddings.append(response["embedding"])

            logger.debug(
                "Generated embeddings",
                model=settings.graphiti_embedding_model,
                count=len(embeddings),
                dimension=len(embeddings[0]) if embeddings else 0,
            )

            return embeddings

        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise LLMError(operation="graphiti_embedding_generation", reason=str(e)) from e


class GraphitiClient:
    """Wrapper for Graphiti episodic memory with Ollama and Neo4j backend.

    Sprint 25 Feature 25.9: Renamed from GraphitiWrapper to GraphitiClient for consistency.

    Provides high-level interface for:
    - Adding episodes (conversations, events)
    - Searching episodic memory
    - Managing entities and relationships
    - Temporal graph queries
    """

    def __init__(
        self,
        llm_client: OllamaLLMClient | None = None,
        neo4j_uri: str | None = None,
        neo4j_user: str | None = None,
        neo4j_password: str | None = None,
    ) -> None:
        """Initialize Graphiti wrapper.

        Args:
            llm_client: Custom Ollama LLM client (default: auto-create)
            neo4j_uri: Neo4j connection URI (default: from settings)
            neo4j_user: Neo4j username (default: from settings)
            neo4j_password: Neo4j password (default: from settings)
        """
        self.llm_client = llm_client or OllamaLLMClient()
        self.neo4j_client = get_neo4j_client()

        # Initialize Graphiti with Neo4j backend
        neo4j_config = {
            "uri": neo4j_uri or settings.neo4j_uri,
            "user": neo4j_user or settings.neo4j_user,
            "password": neo4j_password or settings.neo4j_password.get_secret_value(),
        }

        try:
            # Sprint 13: Updated constructor signature for Graphiti 0.3.21+
            # Changed from neo4j_uri/neo4j_user/neo4j_password to uri/user/password
            # Added embedder and cross_encoder configuration for Ollama

            logger.info(
                "graphiti_wrapper_init_start",
                llm_model=self.llm_client.model,
                base_url=self.llm_client.base_url,
                neo4j_uri=neo4j_config["uri"],
            )

            # Configure LLM client for Graphiti (OpenAI-compatible interface)
            llm_config = LLMConfig(
                api_key="abc",  # Ollama doesn't require a real API key
                model=self.llm_client.model,
                base_url=self.llm_client.base_url,
                temperature=self.llm_client.temperature,
            )
            logger.debug("graphiti_wrapper_llm_config_created")
            openai_client = OpenAIClient(config=llm_config)
            logger.debug("graphiti_wrapper_openai_client_created")

            # Configure embedder for Ollama
            # Note: Graphiti 0.3.21+ requires embedding_dim=1024 (Pydantic Literal validation)
            # Using bge-m3 which supports 1024 dimensions (nomic-embed-text only supports 768)
            embedder = OpenAIEmbedder(
                config=OpenAIEmbedderConfig(
                    api_key="abc",  # Ollama doesn't require a real API key
                    embedding_model="bge-m3",  # BGE-M3 supports 1024 dimensions
                    embedding_dim=1024,  # Required by Graphiti 0.3.21+ validation
                    base_url=self.llm_client.base_url,
                )
            )
            logger.debug("graphiti_wrapper_embedder_created", model="bge-m3", dim=1024)

            # Configure cross-encoder reranker
            cross_encoder = OpenAIRerankerClient(
                config=llm_config,
            )
            logger.debug("graphiti_wrapper_cross_encoder_created")

            self.graphiti = Graphiti(
                uri=neo4j_config["uri"],
                user=neo4j_config["user"],
                password=neo4j_config["password"],
                llm_client=openai_client,
                embedder=embedder,
                cross_encoder=cross_encoder,
            )
            logger.debug("graphiti_wrapper_graphiti_client_created")
            logger.info(
                "Initialized Graphiti wrapper with Ollama",
                neo4j_uri=neo4j_config["uri"],
                llm_model=self.llm_client.model,
                embedding_model="bge-m3",  # Using BGE-M3 for 1024-dim embeddings
                embedding_dim=1024,
            )
        except Exception as e:
            logger.error("Failed to initialize Graphiti", error=str(e))
            raise MemoryError(operation="graphiti_initialization", reason=str(e)) from e

    async def add_episode(
        self,
        content: str,
        source: str = "user_conversation",
        metadata: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> dict[str, Any]:
        """Add an episode to episodic memory.

        Extracts entities and relationships from content and stores them
        in the temporal graph with timestamps.

        Args:
            content: Episode content (conversation turn, event description)
            source: Source of the episode (default: "user_conversation")
            metadata: Additional metadata (default: None)
            timestamp: Episode timestamp (default: now)

        Returns:
            Dictionary with episode_id, entities, and relationships

        Raises:
            MemoryError: If episode addition fails
        """
        try:
            timestamp = timestamp or datetime.now(UTC)
            metadata = metadata or {}

            # Add episode to Graphiti
            episode = await self.graphiti.add_episode(
                content=content,
                timestamp=timestamp,
                source=source,
                metadata=metadata,
            )

            logger.info(
                "Added episode to memory",
                episode_id=episode.get("id"),
                source=source,
                content_length=len(content),
                entities_count=len(episode.get("entities", [])),
                relationships_count=len(episode.get("relationships", [])),
            )

            return {
                "episode_id": episode.get("id"),
                "timestamp": timestamp.isoformat(),
                "entities": episode.get("entities", []),
                "relationships": episode.get("relationships", []),
                "source": source,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error("Failed to add episode", error=str(e), source=source)
            raise MemoryError(operation="add_episode", reason=str(e)) from e

    async def search(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.7,
        time_window_hours: int | None = None,
    ) -> list[dict[str, Any]]:
        """Search episodic memory.

        Args:
            query: Search query text
            limit: Maximum number of results (default: 10)
            score_threshold: Minimum similarity score (default: 0.7)
            time_window_hours: Limit to recent N hours (default: None)

        Returns:
            list of search results with entities, relationships, and episodes

        Raises:
            MemoryError: If search fails
        """
        try:
            search_config = SearchConfig(
                limit=limit,
                score_threshold=score_threshold,
            )

            # Apply time window filter if specified
            if time_window_hours:
                cutoff_time = datetime.now(UTC).timestamp() - (time_window_hours * 3600)
                search_config.time_filter = {"after": cutoff_time}

            results = await self.graphiti.search(
                query=query,
                config=search_config,
            )

            logger.info(
                "Searched episodic memory",
                query=query[:100],
                results_count=len(results),
                time_window_hours=time_window_hours,
            )

            return [
                {
                    "id": r.get("id"),
                    "type": r.get("type"),  # entity, relationship, episode
                    "content": r.get("content"),
                    "score": r.get("score"),
                    "timestamp": r.get("timestamp"),
                    "metadata": r.get("metadata", {}),
                }
                for r in results
            ]

        except Exception as e:
            logger.error("Memory search failed", query=query[:100], error=str(e))
            raise MemoryError(operation="memory_search", reason=str(e)) from e

    async def add_entity(
        self,
        name: str,
        entity_type: str,
        properties: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> dict[str, Any]:
        """Add entity to episodic memory graph.

        Args:
            name: Entity name
            entity_type: Entity type (person, organization, concept, etc.)
            properties: Entity properties (default: None)
            timestamp: Creation timestamp (default: now)

        Returns:
            Dictionary with entity details

        Raises:
            MemoryError: If entity addition fails
        """
        try:
            timestamp = timestamp or datetime.now(UTC)
            properties = properties or {}

            entity = await self.graphiti.add_entity(
                name=name,
                entity_type=entity_type,
                properties=properties,
                timestamp=timestamp,
            )

            logger.info(
                "Added entity to memory",
                entity_id=entity.get("id"),
                name=name,
                type=entity_type,
            )

            return {
                "entity_id": entity.get("id"),
                "name": name,
                "type": entity_type,
                "properties": properties,
                "timestamp": timestamp.isoformat(),
            }

        except Exception as e:
            logger.error("Failed to add entity", name=name, error=str(e))
            raise MemoryError(operation="add_entity", reason=str(e)) from e

    async def add_edge(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        properties: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> dict[str, Any]:
        """Add relationship edge between entities.

        Args:
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID
            relationship_type: Type of relationship
            properties: Edge properties (default: None)
            timestamp: Creation timestamp (default: now)

        Returns:
            Dictionary with edge details

        Raises:
            MemoryError: If edge addition fails
        """
        try:
            timestamp = timestamp or datetime.now(UTC)
            properties = properties or {}

            edge = await self.graphiti.add_edge(
                source_id=source_entity_id,
                target_id=target_entity_id,
                edge_type=relationship_type,
                properties=properties,
                timestamp=timestamp,
            )

            logger.info(
                "Added edge to memory",
                edge_id=edge.get("id"),
                type=relationship_type,
                source=source_entity_id,
                target=target_entity_id,
            )

            return {
                "edge_id": edge.get("id"),
                "source_id": source_entity_id,
                "target_id": target_entity_id,
                "type": relationship_type,
                "properties": properties,
                "timestamp": timestamp.isoformat(),
            }

        except Exception as e:
            logger.error(
                "Failed to add edge",
                type=relationship_type,
                error=str(e),
            )
            raise MemoryError(operation="add_edge", reason=str(e)) from e

    async def close(self) -> None:
        """Close Graphiti and Neo4j connections.

        Deprecated: Use aclose() instead for proper async cleanup.
        """
        await self.aclose()

    async def aclose(self) -> None:
        """Close Graphiti and Neo4j connections (async cleanup).

        Sprint 13: Proper async cleanup to prevent event loop errors.
        This method should be called in pytest fixture teardown.
        """
        try:
            if hasattr(self.graphiti, "close"):
                await self.graphiti.close()
            if hasattr(self.neo4j_client, "close"):
                await self.neo4j_client.close()
            logger.info("Closed Graphiti connections")
        except Exception as e:
            logger.warning("Error closing Graphiti", error=str(e))


# Global instance (singleton pattern)
_graphiti_client: GraphitiClient | None = None


def get_graphiti_client() -> GraphitiClient:
    """Get global Graphiti client instance (singleton).

    Returns:
        GraphitiClient instance (renamed from GraphitiWrapper in Sprint 25)
    """
    global _graphiti_client
    if _graphiti_client is None:
        if not settings.graphiti_enabled:
            raise MemoryError(
                operation="get_graphiti_client", reason="Graphiti is disabled in settings"
            )
        _graphiti_client = GraphitiClient()
    return _graphiti_client


# ============================================================================
# Backward Compatibility Aliases (Sprint 25 Feature 25.9)
# ============================================================================
# Deprecation period: Sprint 25-26
GraphitiWrapper = GraphitiClient
get_graphiti_wrapper = get_graphiti_client
