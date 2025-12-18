"""Unit tests for Community Summarizer.

Sprint 52 - Feature 52.1: Community Summary Generation (TD-058)

Tests:
- CommunitySummarizer initialization
- Summary generation with LLM
- Neo4j storage and retrieval
- Delta-based incremental updates
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.graph_rag.community_delta_tracker import CommunityDelta
from src.components.graph_rag.community_summarizer import (
    CommunitySummarizer,
    get_community_summarizer,
)
from src.components.llm_proxy.models import LLMResponse


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client."""
    client = AsyncMock()
    client.execute_read = AsyncMock(return_value=[])
    client.execute_write = AsyncMock(return_value={})
    return client


@pytest.fixture
def mock_llm_proxy():
    """Mock LLM proxy."""
    proxy = AsyncMock()
    proxy.generate = AsyncMock(
        return_value=LLMResponse(
            content="This community focuses on machine learning and neural networks.",
            provider="local_ollama",
            model="llama3.2:8b",
            tokens_used=25,
            tokens_input=150,
            tokens_output=25,
            cost_usd=0.0,
            latency_ms=120.5,
        )
    )
    return proxy


class TestCommunitySummarizerInit:
    """Tests for CommunitySummarizer initialization."""

    def test_default_initialization(self, mock_neo4j_client):
        """Test initialization with defaults."""
        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy"
            ) as mock_get_proxy:
                mock_get_proxy.return_value = AsyncMock()

                summarizer = CommunitySummarizer()

                assert summarizer.neo4j_client is not None
                assert summarizer.llm_proxy is not None
                assert summarizer.model_name is not None
                assert summarizer.prompt_template is not None

    def test_custom_model_name(self, mock_neo4j_client):
        """Test initialization with custom model."""
        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy"
            ) as mock_get_proxy:
                mock_get_proxy.return_value = AsyncMock()

                summarizer = CommunitySummarizer(model_name="custom-model:latest")

                assert summarizer.model_name == "custom-model:latest"

    def test_custom_prompt_template(self, mock_neo4j_client):
        """Test initialization with custom prompt."""
        custom_prompt = "Custom prompt: {entities}, {relationships}"

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy"
            ) as mock_get_proxy:
                mock_get_proxy.return_value = AsyncMock()

                summarizer = CommunitySummarizer(prompt_template=custom_prompt)

                assert summarizer.prompt_template == custom_prompt


@pytest.mark.asyncio
class TestGenerateSummary:
    """Tests for generate_summary method."""

    async def test_generate_summary_success(self, mock_neo4j_client, mock_llm_proxy):
        """Test successful summary generation."""
        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy",
                return_value=mock_llm_proxy,
            ):
                summarizer = CommunitySummarizer()

                entities = [
                    {"name": "Neural Networks", "type": "CONCEPT"},
                    {"name": "Deep Learning", "type": "CONCEPT"},
                ]

                relationships = [
                    {
                        "source": "Neural Networks",
                        "target": "Deep Learning",
                        "type": "RELATES_TO",
                    }
                ]

                summary = await summarizer.generate_summary(5, entities, relationships)

                assert isinstance(summary, str)
                assert len(summary) > 0
                assert "machine learning" in summary.lower()

                # Verify LLM proxy was called
                mock_llm_proxy.generate.assert_called_once()

    async def test_generate_summary_empty_community(self, mock_neo4j_client, mock_llm_proxy):
        """Test handling of empty community."""
        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy",
                return_value=mock_llm_proxy,
            ):
                summarizer = CommunitySummarizer()

                summary = await summarizer.generate_summary(5, [], [])

                assert "Empty community" in summary
                # LLM should not be called for empty communities
                mock_llm_proxy.generate.assert_not_called()

    async def test_generate_summary_no_relationships(self, mock_neo4j_client, mock_llm_proxy):
        """Test summary generation with entities but no relationships."""
        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy",
                return_value=mock_llm_proxy,
            ):
                summarizer = CommunitySummarizer()

                entities = [
                    {"name": "Entity1", "type": "CONCEPT"},
                    {"name": "Entity2", "type": "CONCEPT"},
                ]

                summary = await summarizer.generate_summary(5, entities, [])

                assert isinstance(summary, str)
                assert len(summary) > 0

    async def test_generate_summary_llm_failure(self, mock_neo4j_client):
        """Test fallback when LLM fails."""
        failing_proxy = AsyncMock()
        failing_proxy.generate = AsyncMock(side_effect=Exception("LLM API error"))

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy",
                return_value=failing_proxy,
            ):
                summarizer = CommunitySummarizer()

                entities = [
                    {"name": "Entity1", "type": "CONCEPT"},
                    {"name": "Entity2", "type": "CONCEPT"},
                ]

                summary = await summarizer.generate_summary(5, entities, [])

                # Should fall back to simple entity listing
                assert "Community containing" in summary
                assert "Entity1" in summary


@pytest.mark.asyncio
class TestGetCommunityData:
    """Tests for _get_community_entities and _get_community_relationships."""

    async def test_get_community_entities(self, mock_neo4j_client):
        """Test retrieval of community entities."""
        mock_neo4j_client.execute_read = AsyncMock(
            return_value=[
                {"name": "Entity1", "type": "PERSON", "entity_id": "e1"},
                {"name": "Entity2", "type": "ORGANIZATION", "entity_id": "e2"},
            ]
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy"
            ) as mock_get_proxy:
                mock_get_proxy.return_value = AsyncMock()

                summarizer = CommunitySummarizer()
                entities = await summarizer._get_community_entities(5)

                assert len(entities) == 2
                assert entities[0]["name"] == "Entity1"
                assert entities[0]["type"] == "PERSON"

    async def test_get_community_relationships(self, mock_neo4j_client):
        """Test retrieval of community relationships."""
        mock_neo4j_client.execute_read = AsyncMock(
            return_value=[
                {"source": "Entity1", "target": "Entity2", "type": "RELATES_TO"},
                {"source": "Entity2", "target": "Entity3", "type": "ASSOCIATES_WITH"},
            ]
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy"
            ) as mock_get_proxy:
                mock_get_proxy.return_value = AsyncMock()

                summarizer = CommunitySummarizer()
                relationships = await summarizer._get_community_relationships(5)

                assert len(relationships) == 2
                assert relationships[0]["source"] == "Entity1"
                assert relationships[0]["target"] == "Entity2"


@pytest.mark.asyncio
class TestStoreSummary:
    """Tests for _store_summary method."""

    async def test_store_summary(self, mock_neo4j_client):
        """Test storing summary in Neo4j."""
        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy"
            ) as mock_get_proxy:
                mock_get_proxy.return_value = AsyncMock()

                summarizer = CommunitySummarizer()
                await summarizer._store_summary(5, "Test summary content")

                # Verify Neo4j write was called
                mock_neo4j_client.execute_write.assert_called_once()

                # Check parameters
                call_args = mock_neo4j_client.execute_write.call_args
                params = call_args[0][1]

                assert params["community_id"] == 5
                assert params["summary"] == "Test summary content"
                assert params["summary_length"] == len("Test summary content")


@pytest.mark.asyncio
class TestUpdateSummariesForDelta:
    """Tests for update_summaries_for_delta method."""

    async def test_update_summaries_no_changes(self, mock_neo4j_client, mock_llm_proxy):
        """Test when delta has no changes."""
        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy",
                return_value=mock_llm_proxy,
            ):
                summarizer = CommunitySummarizer()

                delta = CommunityDelta()  # Empty delta
                summaries = await summarizer.update_summaries_for_delta(delta)

                assert len(summaries) == 0
                mock_llm_proxy.generate.assert_not_called()

    async def test_update_summaries_new_communities(self, mock_neo4j_client, mock_llm_proxy):
        """Test updating summaries for new communities."""
        # Mock entity and relationship retrieval
        mock_neo4j_client.execute_read = AsyncMock(
            side_effect=[
                # First call: _get_community_entities for community 5
                [{"name": "Entity1", "type": "CONCEPT", "entity_id": "e1"}],
                # Second call: _get_community_relationships for community 5
                [{"source": "Entity1", "target": "Entity2", "type": "RELATES_TO"}],
                # Third call: _get_community_entities for community 6
                [{"name": "Entity3", "type": "CONCEPT", "entity_id": "e3"}],
                # Fourth call: _get_community_relationships for community 6
                [],
            ]
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy",
                return_value=mock_llm_proxy,
            ):
                summarizer = CommunitySummarizer()

                delta = CommunityDelta(new_communities={5, 6})
                summaries = await summarizer.update_summaries_for_delta(delta)

                assert len(summaries) == 2
                assert 5 in summaries
                assert 6 in summaries

                # Verify summaries were generated
                assert mock_llm_proxy.generate.call_count == 2

                # Verify summaries were stored
                assert mock_neo4j_client.execute_write.call_count == 2

    async def test_update_summaries_mixed_changes(self, mock_neo4j_client, mock_llm_proxy):
        """Test updating summaries for mixed delta changes."""
        # Mock entity and relationship retrieval
        mock_neo4j_client.execute_read = AsyncMock(
            side_effect=[
                # Community 5 (new)
                [{"name": "Entity1", "type": "CONCEPT", "entity_id": "e1"}],
                [],
                # Community 10 (updated)
                [{"name": "Entity2", "type": "CONCEPT", "entity_id": "e2"}],
                [],
                # Community 20 (merged target)
                [{"name": "Entity3", "type": "CONCEPT", "entity_id": "e3"}],
                [],
            ]
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy",
                return_value=mock_llm_proxy,
            ):
                summarizer = CommunitySummarizer()

                delta = CommunityDelta(
                    new_communities={5},
                    updated_communities={10},
                    merged_communities={15: 20},
                )

                summaries = await summarizer.update_summaries_for_delta(delta)

                # Should update 3 communities: 5 (new), 10 (updated), 20 (merge target)
                assert len(summaries) == 3
                assert 5 in summaries
                assert 10 in summaries
                assert 20 in summaries


@pytest.mark.asyncio
class TestRegenerateAllSummaries:
    """Tests for regenerate_all_summaries method."""

    async def test_regenerate_all_summaries(self, mock_neo4j_client, mock_llm_proxy):
        """Test regenerating all summaries."""
        # Mock community retrieval
        mock_neo4j_client.execute_read = AsyncMock(
            side_effect=[
                # First call: get all community IDs
                [
                    {"community_id": "community_5"},
                    {"community_id": "community_10"},
                ],
                # Subsequent calls: entity/relationship data for each community
                [{"name": "E1", "type": "CONCEPT", "entity_id": "e1"}],  # Comm 5 entities
                [],  # Comm 5 rels
                [{"name": "E2", "type": "CONCEPT", "entity_id": "e2"}],  # Comm 10 entities
                [],  # Comm 10 rels
            ]
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy",
                return_value=mock_llm_proxy,
            ):
                summarizer = CommunitySummarizer()

                summaries = await summarizer.regenerate_all_summaries()

                assert len(summaries) == 2
                assert 5 in summaries
                assert 10 in summaries


@pytest.mark.asyncio
class TestGetSummary:
    """Tests for get_summary method."""

    async def test_get_summary_exists(self, mock_neo4j_client):
        """Test getting existing summary."""
        mock_neo4j_client.execute_read = AsyncMock(
            return_value=[{"summary": "Existing summary text"}]
        )

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy"
            ) as mock_get_proxy:
                mock_get_proxy.return_value = AsyncMock()

                summarizer = CommunitySummarizer()
                summary = await summarizer.get_summary(5)

                assert summary == "Existing summary text"

    async def test_get_summary_not_found(self, mock_neo4j_client):
        """Test getting non-existent summary."""
        mock_neo4j_client.execute_read = AsyncMock(return_value=[])

        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ):
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy"
            ) as mock_get_proxy:
                mock_get_proxy.return_value = AsyncMock()

                summarizer = CommunitySummarizer()
                summary = await summarizer.get_summary(999)

                assert summary is None


class TestSingletonPattern:
    """Tests for singleton pattern."""

    def test_get_community_summarizer_singleton(self):
        """Test that get_community_summarizer returns singleton."""
        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client"
        ) as mock_neo4j:
            with patch(
                "src.components.graph_rag.community_summarizer.get_aegis_llm_proxy"
            ) as mock_llm:
                mock_neo4j.return_value = AsyncMock()
                mock_llm.return_value = AsyncMock()

                summarizer1 = get_community_summarizer()
                summarizer2 = get_community_summarizer()

                assert summarizer1 is summarizer2
