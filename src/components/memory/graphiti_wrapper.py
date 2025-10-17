"""Graphiti Wrapper with Ollama Integration for Episodic Memory.

This module provides a wrapper around Graphiti episodic memory system with:
- Custom Ollama LLM client implementation
- Entity and relationship extraction using Ollama
- Temporal graph storage in Neo4j
- Episode management and search capabilities
"""

from datetime import datetime
from typing import Any

import structlog
from graphiti_core import Graphiti
from graphiti_core.llm_client import LLMClient
from graphiti_core.search import SearchConfig
from ollama import AsyncClient

from src.components.graph_rag.neo4j_client import get_neo4j_client
from src.core.config import settings
from src.core.exceptions import LLMError, MemoryError

logger = structlog.get_logger(__name__)


class OllamaLLMClient(LLMClient):
    """Custom LLM client for Graphiti using Ollama.

    Implements Graphiti's LLMClient interface to use Ollama for:
    - Entity and relationship extraction
    - Text generation for memory operations
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.1,
    ):
        """Initialize Ollama LLM client.

        Args:
            base_url: Ollama server URL (default: from settings)
            model: Ollama model name (default: from settings)
            temperature: Generation temperature (default: 0.1 for consistency)
        """
        self.base_url = base_url or settings.graphiti_ollama_base_url
        self.model = model or settings.graphiti_llm_model
        self.temperature = temperature
        self.client = AsyncClient(host=self.base_url)

        logger.info(
            "Initialized OllamaLLMClient",
            base_url=self.base_url,
            model=self.model,
            temperature=self.temperature,
        )

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        """Generate text response from Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response

        Raises:
            LLMError: If generation fails
        """
        try:
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": self.temperature,
                    "num_predict": max_tokens,
                },
            )

            if not response or "message" not in response:
                raise LLMError("Invalid response from Ollama")

            content = response["message"]["content"]
            logger.debug(
                "Generated response",
                model=self.model,
                input_tokens=len(str(messages)),
                output_length=len(content),
            )

            return content

        except Exception as e:
            logger.error("Ollama generation failed", error=str(e))
            raise LLMError(f"Ollama generation failed: {e}") from e

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Ollama.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

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
                    raise LLMError(f"Invalid embedding response for text: {text[:50]}")

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
            raise LLMError(f"Embedding generation failed: {e}") from e


class GraphitiWrapper:
    """Wrapper for Graphiti episodic memory with Ollama and Neo4j backend.

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
    ):
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
            self.graphiti = Graphiti(
                llm_client=self.llm_client,
                neo4j_uri=neo4j_config["uri"],
                neo4j_user=neo4j_config["user"],
                neo4j_password=neo4j_config["password"],
            )
            logger.info(
                "Initialized Graphiti wrapper",
                neo4j_uri=neo4j_config["uri"],
                llm_model=self.llm_client.model,
            )
        except Exception as e:
            logger.error("Failed to initialize Graphiti", error=str(e))
            raise MemoryError(f"Failed to initialize Graphiti: {e}") from e

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
            timestamp = timestamp or datetime.utcnow()
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
            raise MemoryError(f"Failed to add episode: {e}") from e

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
            List of search results with entities, relationships, and episodes

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
                cutoff_time = datetime.utcnow().timestamp() - (time_window_hours * 3600)
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
            raise MemoryError(f"Memory search failed: {e}") from e

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
            timestamp = timestamp or datetime.utcnow()
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
            raise MemoryError(f"Failed to add entity: {e}") from e

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
            timestamp = timestamp or datetime.utcnow()
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
            raise MemoryError(f"Failed to add edge: {e}") from e

    async def close(self) -> None:
        """Close Graphiti and Neo4j connections."""
        try:
            if hasattr(self.graphiti, "close"):
                await self.graphiti.close()
            logger.info("Closed Graphiti connections")
        except Exception as e:
            logger.warning("Error closing Graphiti", error=str(e))


# Global instance (singleton pattern)
_graphiti_wrapper: GraphitiWrapper | None = None


def get_graphiti_wrapper() -> GraphitiWrapper:
    """Get global Graphiti wrapper instance (singleton).

    Returns:
        GraphitiWrapper instance
    """
    global _graphiti_wrapper
    if _graphiti_wrapper is None:
        if not settings.graphiti_enabled:
            raise MemoryError("Graphiti is disabled in settings")
        _graphiti_wrapper = GraphitiWrapper()
    return _graphiti_wrapper
