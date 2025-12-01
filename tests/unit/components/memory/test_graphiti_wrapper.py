"""Unit tests for GraphitiWrapper and OllamaLLMClient.

Tests Graphiti episodic memory wrapper including:
- OllamaLLMClient initialization and methods
- GraphitiWrapper initialization with various configurations
- Episode management (add_episode)
- Search functionality with filters
- Entity and edge management
- Error handling and exceptions
- Connection cleanup and resource management
- Singleton pattern for global instance

Sprint 7 Feature 7.1: Graphiti Episodic Memory
Target Coverage: 60%+ (20+ tests)
"""

import sys
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Mock graphiti_core module if not installed
if "graphiti_core" not in sys.modules:
    sys.modules["graphiti_core"] = MagicMock()
    sys.modules["graphiti_core.cross_encoder"] = MagicMock()
    sys.modules["graphiti_core.cross_encoder.openai_reranker_client"] = MagicMock()
    sys.modules["graphiti_core.embedder"] = MagicMock()
    sys.modules["graphiti_core.embedder.openai"] = MagicMock()
    sys.modules["graphiti_core.llm_client"] = MagicMock()
    sys.modules["graphiti_core.llm_client.config"] = MagicMock()
    sys.modules["graphiti_core.llm_client.openai_client"] = MagicMock()
    sys.modules["graphiti_core.search"] = MagicMock()
    sys.modules["graphiti_core.search.search_config"] = MagicMock()

from src.core.exceptions import LLMError, MemoryError

# ============================================================================
# Test OllamaLLMClient Initialization
# ============================================================================


def test_ollama_llm_client_init_default():
    """Test OllamaLLMClient initialization with default parameters."""
    with patch("src.components.memory.graphiti_wrapper.AsyncClient") as mock_async_client_class:
        with patch("src.components.memory.graphiti_wrapper.settings") as mock_settings_module:
            from src.components.memory.graphiti_wrapper import OllamaLLMClient

            # Given: Default initialization
            mock_settings_module.graphiti_ollama_base_url = "http://localhost:11434"
            mock_settings_module.graphiti_llm_model = "llama3.2:3b"
            mock_client = AsyncMock()
            mock_async_client_class.return_value = mock_client

            # When: Initialize client
            client = OllamaLLMClient()

            # Then: Verify initialization
            assert client.base_url == "http://localhost:11434"
            assert client.model == "llama3.2:3b"
            assert client.temperature == 0.1
            assert client.client == mock_client
            mock_async_client_class.assert_called_once_with(host="http://localhost:11434")


def test_ollama_llm_client_init_custom_params():
    """Test OllamaLLMClient initialization with custom parameters."""
    with patch("src.components.memory.graphiti_wrapper.AsyncClient") as mock_async_client_class:
        from src.components.memory.graphiti_wrapper import OllamaLLMClient

        # Given: Custom parameters
        mock_client = AsyncMock()
        mock_async_client_class.return_value = mock_client

        # When: Initialize with custom params
        client = OllamaLLMClient(
            base_url="http://custom:11434",
            model="llama3.1:8b",
            temperature=0.5,
        )

        # Then: Verify custom configuration
        assert client.base_url == "http://custom:11434"
        assert client.model == "llama3.1:8b"
        assert client.temperature == 0.5
        mock_async_client_class.assert_called_once_with(host="http://custom:11434")


# ============================================================================
# Test OllamaLLMClient Response Generation
# ============================================================================


@pytest.mark.asyncio
async def test_ollama_llm_client_generate_response_success():
    """Test OllamaLLMClient generates text response successfully via AegisLLMProxy."""
    with (
        patch("src.components.memory.graphiti_wrapper.AsyncClient") as mock_async_client_class,
        patch("src.components.memory.graphiti_wrapper.get_aegis_llm_proxy") as mock_get_proxy,
    ):
        from src.components.memory.graphiti_wrapper import OllamaLLMClient

        # Given: LLM client with mocked proxy
        mock_async_client_class.return_value = AsyncMock()  # For embeddings

        # Mock AegisLLMProxy
        mock_proxy = AsyncMock()
        mock_result = MagicMock()
        mock_result.content = "Generated response"
        mock_result.provider = "local_ollama"
        mock_result.model = "llama3.2:3b"
        mock_result.tokens_used = 50
        mock_result.cost_usd = 0.0
        mock_result.latency_ms = 100
        mock_proxy.generate.return_value = mock_result
        mock_get_proxy.return_value = mock_proxy

        client = OllamaLLMClient()

        # When: Generate response
        messages = [{"role": "user", "content": "Test prompt"}]
        response = await client._generate_response(messages, max_tokens=100)

        # Then: Verify response
        assert response == "Generated response"
        mock_proxy.generate.assert_called_once()


@pytest.mark.asyncio
async def test_ollama_llm_client_generate_response_invalid_response():
    """Test OllamaLLMClient handles LLM proxy errors."""
    with (
        patch("src.components.memory.graphiti_wrapper.AsyncClient") as mock_async_client_class,
        patch("src.components.memory.graphiti_wrapper.get_aegis_llm_proxy") as mock_get_proxy,
    ):
        from src.components.memory.graphiti_wrapper import OllamaLLMClient

        # Given: LLM client with proxy error
        mock_async_client_class.return_value = AsyncMock()

        mock_proxy = AsyncMock()
        mock_proxy.generate.side_effect = Exception("LLM proxy error")
        mock_get_proxy.return_value = mock_proxy

        client = OllamaLLMClient()

        # When/Then: Should raise LLMError
        messages = [{"role": "user", "content": "Test"}]
        with pytest.raises(LLMError) as exc_info:
            await client._generate_response(messages)

        assert "graphiti_memory_generation" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_llm_client_generate_response_connection_error():
    """Test OllamaLLMClient handles connection errors."""
    with (
        patch("src.components.memory.graphiti_wrapper.AsyncClient") as mock_async_client_class,
        patch("src.components.memory.graphiti_wrapper.get_aegis_llm_proxy") as mock_get_proxy,
    ):
        from src.components.memory.graphiti_wrapper import OllamaLLMClient

        # Given: LLM client with connection error
        mock_async_client_class.return_value = AsyncMock()

        mock_proxy = AsyncMock()
        mock_proxy.generate.side_effect = ConnectionError("Provider not available")
        mock_get_proxy.return_value = mock_proxy

        client = OllamaLLMClient()

        # When/Then: Should raise LLMError
        messages = [{"role": "user", "content": "Test"}]
        with pytest.raises(LLMError) as exc_info:
            await client._generate_response(messages)

        assert "graphiti_memory_generation" in str(exc_info.value)


# ============================================================================
# Test OllamaLLMClient Embeddings
# ============================================================================


@pytest.mark.asyncio
async def test_ollama_llm_client_generate_embeddings_success():
    """Test OllamaLLMClient generates embeddings successfully."""
    with patch("src.components.memory.graphiti_wrapper.AsyncClient") as mock_async_client_class:
        with patch("src.components.memory.graphiti_wrapper.settings") as mock_settings:
            from src.components.memory.graphiti_wrapper import OllamaLLMClient

            # Given: LLM client with mocked embeddings
            mock_settings.graphiti_embedding_model = "bge-m3"
            mock_client = AsyncMock()
            mock_client.embeddings.return_value = {"embedding": [0.1] * 1024}
            mock_async_client_class.return_value = mock_client

            client = OllamaLLMClient()

            # When: Generate embeddings
            texts = ["text1", "text2"]
            embeddings = await client.generate_embeddings(texts)

            # Then: Verify embeddings
            assert len(embeddings) == 2
            assert all(len(emb) == 1024 for emb in embeddings)
            assert mock_client.embeddings.call_count == 2


@pytest.mark.asyncio
async def test_ollama_llm_client_generate_embeddings_invalid_response():
    """Test OllamaLLMClient handles invalid embedding response."""
    with patch("src.components.memory.graphiti_wrapper.AsyncClient") as mock_async_client_class:
        with patch("src.components.memory.graphiti_wrapper.settings") as mock_settings:
            from src.components.memory.graphiti_wrapper import OllamaLLMClient

            # Given: LLM client with invalid embedding response
            mock_settings.graphiti_embedding_model = "bge-m3"
            mock_client = AsyncMock()
            mock_client.embeddings.return_value = {"invalid": "structure"}  # Missing 'embedding'
            mock_async_client_class.return_value = mock_client

            client = OllamaLLMClient()

            # When/Then: Should raise LLMError
            texts = ["text1"]
            with pytest.raises(LLMError) as exc_info:
                await client.generate_embeddings(texts)

            assert "graphiti_embedding_generation" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_llm_client_generate_embeddings_connection_error():
    """Test OllamaLLMClient handles embedding connection errors."""
    with patch("src.components.memory.graphiti_wrapper.AsyncClient") as mock_async_client_class:
        with patch("src.components.memory.graphiti_wrapper.settings") as mock_settings:
            from src.components.memory.graphiti_wrapper import OllamaLLMClient

            # Given: LLM client with connection error
            mock_settings.graphiti_embedding_model = "bge-m3"
            mock_client = AsyncMock()
            mock_client.embeddings.side_effect = ConnectionError("Ollama not available")
            mock_async_client_class.return_value = mock_client

            client = OllamaLLMClient()

            # When/Then: Should raise LLMError
            texts = ["text1"]
            with pytest.raises(LLMError) as exc_info:
                await client.generate_embeddings(texts)

            assert "graphiti_embedding_generation" in str(exc_info.value)


# ============================================================================
# Test GraphitiWrapper Initialization
# ============================================================================


def test_graphiti_wrapper_init_default():
    """Test GraphitiWrapper initialization with default parameters."""
    with (
        patch("src.components.memory.graphiti_wrapper.Graphiti") as mock_graphiti_class,
        patch("src.components.memory.graphiti_wrapper.get_neo4j_client") as mock_get_neo4j,
        patch("src.components.memory.graphiti_wrapper.settings") as mock_settings,
        patch("src.components.memory.graphiti_wrapper.OllamaLLMClient") as mock_ollama,
        patch("src.components.memory.graphiti_wrapper.OpenAIClient"),
        patch("src.components.memory.graphiti_wrapper.OpenAIEmbedder"),
        patch("src.components.memory.graphiti_wrapper.OpenAIRerankerClient"),
    ):
        from src.components.memory.graphiti_wrapper import GraphitiWrapper

        # Given: Default initialization
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_password = MagicMock()
        mock_password.get_secret_value.return_value = "password"
        mock_settings.neo4j_password = mock_password

        mock_neo4j = AsyncMock()
        mock_get_neo4j.return_value = mock_neo4j

        mock_graphiti = AsyncMock()
        mock_graphiti_class.return_value = mock_graphiti

        mock_llm_client = MagicMock()
        mock_llm_client.base_url = "http://localhost:11434"
        mock_llm_client.model = "llama2"
        mock_llm_client.temperature = 0.1
        mock_ollama.return_value = mock_llm_client

        # When: Initialize wrapper
        wrapper = GraphitiWrapper()

        # Then: Verify initialization
        assert wrapper.llm_client is not None
        assert wrapper.neo4j_client == mock_neo4j
        assert wrapper.graphiti == mock_graphiti


def test_graphiti_wrapper_init_connection_error():
    """Test GraphitiWrapper handles initialization errors."""
    with (
        patch("src.components.memory.graphiti_wrapper.Graphiti") as mock_graphiti_class,
        patch("src.components.memory.graphiti_wrapper.get_neo4j_client") as mock_get_neo4j,
        patch("src.components.memory.graphiti_wrapper.settings") as mock_settings,
        patch("src.components.memory.graphiti_wrapper.OllamaLLMClient"),
    ):
        from src.components.memory.graphiti_wrapper import GraphitiWrapper

        # Given: Neo4j connection fails
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_password = MagicMock()
        mock_password.get_secret_value.return_value = "password"
        mock_settings.neo4j_password = mock_password

        mock_get_neo4j.return_value = AsyncMock()
        mock_graphiti_class.side_effect = Exception("Connection failed")

        # When/Then: Should raise MemoryError
        with pytest.raises(MemoryError) as exc_info:
            GraphitiWrapper()

        assert "graphiti_initialization" in str(exc_info.value)


# ============================================================================
# Test Episode Management
# ============================================================================


@pytest.mark.asyncio
async def test_add_episode_success():
    """Test adding episode to episodic memory successfully."""
    with (
        patch("src.components.memory.graphiti_wrapper.Graphiti") as mock_graphiti_class,
        patch("src.components.memory.graphiti_wrapper.get_neo4j_client") as mock_get_neo4j,
        patch("src.components.memory.graphiti_wrapper.settings") as mock_settings,
        patch("src.components.memory.graphiti_wrapper.OllamaLLMClient") as mock_ollama,
        patch("src.components.memory.graphiti_wrapper.OpenAIClient"),
        patch("src.components.memory.graphiti_wrapper.OpenAIEmbedder"),
        patch("src.components.memory.graphiti_wrapper.OpenAIRerankerClient"),
    ):
        from src.components.memory.graphiti_wrapper import GraphitiWrapper

        # Given: Wrapper with mocked Graphiti
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_password = MagicMock()
        mock_password.get_secret_value.return_value = "password"
        mock_settings.neo4j_password = mock_password

        mock_get_neo4j.return_value = AsyncMock()

        mock_graphiti = AsyncMock()
        mock_graphiti.add_episode.return_value = {
            "id": "episode_123",
            "entities": [{"id": "entity_1", "name": "Alice"}],
            "relationships": [{"id": "rel_1", "type": "knows"}],
        }
        mock_graphiti_class.return_value = mock_graphiti

        mock_llm_client = MagicMock()
        mock_llm_client.base_url = "http://localhost:11434"
        mock_llm_client.model = "llama2"
        mock_llm_client.temperature = 0.1
        mock_ollama.return_value = mock_llm_client

        wrapper = GraphitiWrapper()

        # When: Add episode
        result = await wrapper.add_episode(
            content="Alice met Bob at the conference.",
            source="test",
            metadata={"importance": "high"},
        )

        # Then: Verify episode added
        assert result["episode_id"] == "episode_123"
        assert "timestamp" in result
        assert len(result["entities"]) == 1
        assert len(result["relationships"]) == 1
        assert result["source"] == "test"
        assert result["metadata"]["importance"] == "high"


@pytest.mark.asyncio
async def test_add_episode_error():
    """Test add_episode handles errors gracefully."""
    with (
        patch("src.components.memory.graphiti_wrapper.Graphiti") as mock_graphiti_class,
        patch("src.components.memory.graphiti_wrapper.get_neo4j_client") as mock_get_neo4j,
        patch("src.components.memory.graphiti_wrapper.settings") as mock_settings,
        patch("src.components.memory.graphiti_wrapper.OllamaLLMClient") as mock_ollama,
        patch("src.components.memory.graphiti_wrapper.OpenAIClient"),
        patch("src.components.memory.graphiti_wrapper.OpenAIEmbedder"),
        patch("src.components.memory.graphiti_wrapper.OpenAIRerankerClient"),
    ):
        from src.components.memory.graphiti_wrapper import GraphitiWrapper

        # Given: Graphiti raises error
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_password = MagicMock()
        mock_password.get_secret_value.return_value = "password"
        mock_settings.neo4j_password = mock_password

        mock_get_neo4j.return_value = AsyncMock()

        mock_graphiti = AsyncMock()
        mock_graphiti.add_episode.side_effect = Exception("Database error")
        mock_graphiti_class.return_value = mock_graphiti

        mock_llm_client = MagicMock()
        mock_llm_client.base_url = "http://localhost:11434"
        mock_llm_client.model = "llama2"
        mock_llm_client.temperature = 0.1
        mock_ollama.return_value = mock_llm_client

        wrapper = GraphitiWrapper()

        # When/Then: Should raise MemoryError
        with pytest.raises(MemoryError) as exc_info:
            await wrapper.add_episode(content="Test", source="test")

        assert "add_episode" in str(exc_info.value)


# ============================================================================
# Test Search Functionality
# ============================================================================


@pytest.mark.asyncio
async def test_search_success():
    """Test searching episodic memory successfully."""
    with (
        patch("src.components.memory.graphiti_wrapper.Graphiti") as mock_graphiti_class,
        patch("src.components.memory.graphiti_wrapper.get_neo4j_client") as mock_get_neo4j,
        patch("src.components.memory.graphiti_wrapper.settings") as mock_settings,
        patch("src.components.memory.graphiti_wrapper.OllamaLLMClient") as mock_ollama,
        patch("src.components.memory.graphiti_wrapper.OpenAIClient"),
        patch("src.components.memory.graphiti_wrapper.OpenAIEmbedder"),
        patch("src.components.memory.graphiti_wrapper.OpenAIRerankerClient"),
    ):
        from src.components.memory.graphiti_wrapper import GraphitiWrapper

        # Given: Wrapper with search results
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_password = MagicMock()
        mock_password.get_secret_value.return_value = "password"
        mock_settings.neo4j_password = mock_password

        mock_get_neo4j.return_value = AsyncMock()

        mock_graphiti = AsyncMock()
        mock_graphiti.search.return_value = [
            {
                "id": "result_1",
                "type": "entity",
                "content": "Test result",
                "score": 0.95,
                "timestamp": "2024-01-01T12:00:00",
                "metadata": {"key": "value"},
            }
        ]
        mock_graphiti_class.return_value = mock_graphiti

        mock_llm_client = MagicMock()
        mock_llm_client.base_url = "http://localhost:11434"
        mock_llm_client.model = "llama2"
        mock_llm_client.temperature = 0.1
        mock_ollama.return_value = mock_llm_client

        wrapper = GraphitiWrapper()

        # When: Search
        results = await wrapper.search(
            query="test query",
            limit=5,
            score_threshold=0.7,
        )

        # Then: Verify results
        assert len(results) == 1
        assert results[0]["id"] == "result_1"
        assert results[0]["score"] == 0.95


@pytest.mark.asyncio
async def test_search_error():
    """Test search handles errors gracefully."""
    with (
        patch("src.components.memory.graphiti_wrapper.Graphiti") as mock_graphiti_class,
        patch("src.components.memory.graphiti_wrapper.get_neo4j_client") as mock_get_neo4j,
        patch("src.components.memory.graphiti_wrapper.settings") as mock_settings,
        patch("src.components.memory.graphiti_wrapper.OllamaLLMClient") as mock_ollama,
        patch("src.components.memory.graphiti_wrapper.OpenAIClient"),
        patch("src.components.memory.graphiti_wrapper.OpenAIEmbedder"),
        patch("src.components.memory.graphiti_wrapper.OpenAIRerankerClient"),
    ):
        from src.components.memory.graphiti_wrapper import GraphitiWrapper

        # Given: Search fails
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_password = MagicMock()
        mock_password.get_secret_value.return_value = "password"
        mock_settings.neo4j_password = mock_password

        mock_get_neo4j.return_value = AsyncMock()

        mock_graphiti = AsyncMock()
        mock_graphiti.search.side_effect = Exception("Search failed")
        mock_graphiti_class.return_value = mock_graphiti

        mock_llm_client = MagicMock()
        mock_llm_client.base_url = "http://localhost:11434"
        mock_llm_client.model = "llama2"
        mock_llm_client.temperature = 0.1
        mock_ollama.return_value = mock_llm_client

        wrapper = GraphitiWrapper()

        # When/Then: Should raise MemoryError
        with pytest.raises(MemoryError) as exc_info:
            await wrapper.search(query="test")

        assert "memory_search" in str(exc_info.value)


# ============================================================================
# Test Entity Management
# ============================================================================


@pytest.mark.asyncio
async def test_add_entity_success():
    """Test adding entity to memory graph."""
    with (
        patch("src.components.memory.graphiti_wrapper.Graphiti") as mock_graphiti_class,
        patch("src.components.memory.graphiti_wrapper.get_neo4j_client") as mock_get_neo4j,
        patch("src.components.memory.graphiti_wrapper.settings") as mock_settings,
        patch("src.components.memory.graphiti_wrapper.OllamaLLMClient") as mock_ollama,
        patch("src.components.memory.graphiti_wrapper.OpenAIClient"),
        patch("src.components.memory.graphiti_wrapper.OpenAIEmbedder"),
        patch("src.components.memory.graphiti_wrapper.OpenAIRerankerClient"),
    ):
        from src.components.memory.graphiti_wrapper import GraphitiWrapper

        # Given: Wrapper
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_password = MagicMock()
        mock_password.get_secret_value.return_value = "password"
        mock_settings.neo4j_password = mock_password

        mock_get_neo4j.return_value = AsyncMock()

        # Mock LLM client with string attributes
        mock_llm_client = MagicMock()
        mock_llm_client.base_url = "http://localhost:11434"
        mock_llm_client.model = "llama2"
        mock_llm_client.temperature = 0.1
        mock_ollama.return_value = mock_llm_client

        mock_graphiti = AsyncMock()
        mock_graphiti.add_entity.return_value = {"id": "entity_789", "name": "Alice"}
        mock_graphiti_class.return_value = mock_graphiti

        wrapper = GraphitiWrapper()

        # When: Add entity
        result = await wrapper.add_entity(
            name="Alice",
            entity_type="person",
            properties={"role": "engineer"},
        )

        # Then: Verify entity added
        assert result["entity_id"] == "entity_789"
        assert result["name"] == "Alice"
        assert result["type"] == "person"
        assert result["properties"]["role"] == "engineer"
        assert "timestamp" in result


@pytest.mark.asyncio
async def test_add_entity_error():
    """Test add_entity handles errors gracefully."""
    with (
        patch("src.components.memory.graphiti_wrapper.Graphiti") as mock_graphiti_class,
        patch("src.components.memory.graphiti_wrapper.get_neo4j_client") as mock_get_neo4j,
        patch("src.components.memory.graphiti_wrapper.settings") as mock_settings,
        patch("src.components.memory.graphiti_wrapper.OllamaLLMClient") as mock_ollama,
        patch("src.components.memory.graphiti_wrapper.OpenAIClient"),
        patch("src.components.memory.graphiti_wrapper.OpenAIEmbedder"),
        patch("src.components.memory.graphiti_wrapper.OpenAIRerankerClient"),
    ):
        from src.components.memory.graphiti_wrapper import GraphitiWrapper

        # Given: Add entity fails
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_password = MagicMock()
        mock_password.get_secret_value.return_value = "password"
        mock_settings.neo4j_password = mock_password

        mock_get_neo4j.return_value = AsyncMock()

        # Mock LLM client with string attributes
        mock_llm_client = MagicMock()
        mock_llm_client.base_url = "http://localhost:11434"
        mock_llm_client.model = "llama2"
        mock_llm_client.temperature = 0.1
        mock_ollama.return_value = mock_llm_client

        mock_graphiti = AsyncMock()
        mock_graphiti.add_entity.side_effect = Exception("Entity error")
        mock_graphiti_class.return_value = mock_graphiti

        wrapper = GraphitiWrapper()

        # When/Then: Should raise MemoryError
        with pytest.raises(MemoryError) as exc_info:
            await wrapper.add_entity(name="Alice", entity_type="person")

        assert "add_entity" in str(exc_info.value)


# ============================================================================
# Test Edge/Relationship Management
# ============================================================================


@pytest.mark.asyncio
async def test_add_edge_success():
    """Test adding edge/relationship between entities."""
    with (
        patch("src.components.memory.graphiti_wrapper.Graphiti") as mock_graphiti_class,
        patch("src.components.memory.graphiti_wrapper.get_neo4j_client") as mock_get_neo4j,
        patch("src.components.memory.graphiti_wrapper.settings") as mock_settings,
        patch("src.components.memory.graphiti_wrapper.OllamaLLMClient") as mock_ollama,
        patch("src.components.memory.graphiti_wrapper.OpenAIClient"),
        patch("src.components.memory.graphiti_wrapper.OpenAIEmbedder"),
        patch("src.components.memory.graphiti_wrapper.OpenAIRerankerClient"),
    ):
        from src.components.memory.graphiti_wrapper import GraphitiWrapper

        # Given: Wrapper
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_password = MagicMock()
        mock_password.get_secret_value.return_value = "password"
        mock_settings.neo4j_password = mock_password

        mock_get_neo4j.return_value = AsyncMock()

        # Mock LLM client with string attributes
        mock_llm_client = MagicMock()
        mock_llm_client.base_url = "http://localhost:11434"
        mock_llm_client.model = "llama2"
        mock_llm_client.temperature = 0.1
        mock_ollama.return_value = mock_llm_client

        mock_graphiti = AsyncMock()
        mock_graphiti.add_edge.return_value = {"id": "edge_123", "type": "knows"}
        mock_graphiti_class.return_value = mock_graphiti

        wrapper = GraphitiWrapper()

        # When: Add edge
        result = await wrapper.add_edge(
            source_entity_id="entity_1",
            target_entity_id="entity_2",
            relationship_type="knows",
            properties={"since": "2024"},
        )

        # Then: Verify edge added
        assert result["edge_id"] == "edge_123"
        assert result["source_id"] == "entity_1"
        assert result["target_id"] == "entity_2"
        assert result["type"] == "knows"
        assert result["properties"]["since"] == "2024"
        assert "timestamp" in result


@pytest.mark.asyncio
async def test_add_edge_error():
    """Test add_edge handles errors gracefully."""
    with (
        patch("src.components.memory.graphiti_wrapper.Graphiti") as mock_graphiti_class,
        patch("src.components.memory.graphiti_wrapper.get_neo4j_client") as mock_get_neo4j,
        patch("src.components.memory.graphiti_wrapper.settings") as mock_settings,
        patch("src.components.memory.graphiti_wrapper.OllamaLLMClient") as mock_ollama,
        patch("src.components.memory.graphiti_wrapper.OpenAIClient"),
        patch("src.components.memory.graphiti_wrapper.OpenAIEmbedder"),
        patch("src.components.memory.graphiti_wrapper.OpenAIRerankerClient"),
    ):
        from src.components.memory.graphiti_wrapper import GraphitiWrapper

        # Given: Add edge fails
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_password = MagicMock()
        mock_password.get_secret_value.return_value = "password"
        mock_settings.neo4j_password = mock_password

        mock_get_neo4j.return_value = AsyncMock()

        # Mock LLM client with string attributes
        mock_llm_client = MagicMock()
        mock_llm_client.base_url = "http://localhost:11434"
        mock_llm_client.model = "llama2"
        mock_llm_client.temperature = 0.1
        mock_ollama.return_value = mock_llm_client

        mock_graphiti = AsyncMock()
        mock_graphiti.add_edge.side_effect = Exception("Edge error")
        mock_graphiti_class.return_value = mock_graphiti

        wrapper = GraphitiWrapper()

        # When/Then: Should raise MemoryError
        with pytest.raises(MemoryError) as exc_info:
            await wrapper.add_edge(
                source_entity_id="e1",
                target_entity_id="e2",
                relationship_type="knows",
            )

        assert "add_edge" in str(exc_info.value)


# ============================================================================
# Test Connection Cleanup
# ============================================================================


@pytest.mark.asyncio
async def test_aclose_success():
    """Test async connection cleanup."""
    with (
        patch("src.components.memory.graphiti_wrapper.Graphiti") as mock_graphiti_class,
        patch("src.components.memory.graphiti_wrapper.get_neo4j_client") as mock_get_neo4j,
        patch("src.components.memory.graphiti_wrapper.settings") as mock_settings,
        patch("src.components.memory.graphiti_wrapper.OllamaLLMClient") as mock_ollama,
        patch("src.components.memory.graphiti_wrapper.OpenAIClient"),
        patch("src.components.memory.graphiti_wrapper.OpenAIEmbedder"),
        patch("src.components.memory.graphiti_wrapper.OpenAIRerankerClient"),
    ):
        from src.components.memory.graphiti_wrapper import GraphitiWrapper

        # Given: Wrapper with connections
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_password = MagicMock()
        mock_password.get_secret_value.return_value = "password"
        mock_settings.neo4j_password = mock_password

        mock_neo4j = AsyncMock()
        mock_neo4j.close = AsyncMock()
        mock_get_neo4j.return_value = mock_neo4j

        # Mock LLM client with string attributes
        mock_llm_client = MagicMock()
        mock_llm_client.base_url = "http://localhost:11434"
        mock_llm_client.model = "llama2"
        mock_llm_client.temperature = 0.1
        mock_ollama.return_value = mock_llm_client

        mock_graphiti = AsyncMock()
        mock_graphiti.close = AsyncMock()
        mock_graphiti_class.return_value = mock_graphiti

        wrapper = GraphitiWrapper()

        # When: Close connections
        await wrapper.aclose()

        # Then: Should close both connections
        mock_graphiti.close.assert_called_once()
        mock_neo4j.close.assert_called_once()


# ============================================================================
# Test Singleton Pattern
# ============================================================================


def test_get_graphiti_wrapper_disabled():
    """Test get_graphiti_wrapper raises error when disabled."""
    with patch("src.components.memory.graphiti_wrapper.settings") as mock_settings_module:
        from src.components.memory.graphiti_wrapper import get_graphiti_wrapper

        # Given: Graphiti disabled in settings
        mock_settings_module.graphiti_enabled = False

        # When/Then: Should raise MemoryError
        with pytest.raises(MemoryError) as exc_info:
            get_graphiti_wrapper()

        assert "get_graphiti_client" in str(exc_info.value)
