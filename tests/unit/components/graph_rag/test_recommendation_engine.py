"""Tests for Graph Recommendation Engine."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.components.graph_rag.recommendation_engine import (
    RecommendationEngine,
    get_recommendation_engine,
)
from src.core.exceptions import DatabaseConnectionError
from src.core.models import Recommendation


@pytest.fixture
def mock_neo4j_client():
    """Create mock Neo4j client."""
    client = MagicMock()
    client.execute_query = AsyncMock()
    return client


@pytest.fixture
def engine(mock_neo4j_client):
    """Create RecommendationEngine instance."""
    return RecommendationEngine(neo4j_client=mock_neo4j_client)


@pytest.fixture
def sample_recommendation_data():
    """Sample recommendation query result."""
    return [
        {
            "id": "entity_2",
            "name": "Jane Doe",
            "type": "PERSON",
            "description": "Data scientist",
            "properties": {"age": 28},
            "common_neighbors": 5,
            "score": 0.5,
        },
        {
            "id": "entity_3",
            "name": "Alice Brown",
            "type": "PERSON",
            "description": "ML engineer",
            "properties": {"age": 32},
            "common_neighbors": 3,
            "score": 0.3,
        },
    ]


class TestRecommendationEngine:
    """Test RecommendationEngine class."""

    def test_initialization(self, engine):
        """Test engine initialization."""
        assert engine is not None
        assert engine.top_k == 5
        assert engine.default_method == "collaborative"

    @pytest.mark.asyncio
    async def test_recommend_by_collaborative(
        self, engine, mock_neo4j_client, sample_recommendation_data
    ):
        """Test collaborative filtering recommendations."""
        mock_neo4j_client.execute_query.return_value = sample_recommendation_data

        recommendations = await engine.recommend_by_collaborative("entity_1", top_k=5)

        assert isinstance(recommendations, list)
        assert len(recommendations) == 2
        assert all(isinstance(r, Recommendation) for r in recommendations)
        assert recommendations[0].entity.id == "entity_2"
        assert recommendations[0].reason == "similar_community"

    @pytest.mark.asyncio
    async def test_recommend_by_community(
        self, engine, mock_neo4j_client, sample_recommendation_data
    ):
        """Test community-based recommendations."""
        mock_neo4j_client.execute_query.return_value = sample_recommendation_data

        recommendations = await engine.recommend_by_community("entity_1", top_k=5)

        assert isinstance(recommendations, list)
        assert len(recommendations) == 2
        assert recommendations[0].reason == "similar_community"

    @pytest.mark.asyncio
    async def test_recommend_by_community_no_community_id(self, engine, mock_neo4j_client):
        """Test community-based recommendations when community_id doesn't exist."""
        mock_neo4j_client.execute_query.side_effect = Exception("Property community_id not found")

        recommendations = await engine.recommend_by_community("entity_1", top_k=5)

        assert recommendations == []

    @pytest.mark.asyncio
    async def test_recommend_by_relationships(self, engine, mock_neo4j_client):
        """Test relationship-based recommendations."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "id": "entity_2",
                "name": "Google",
                "type": "ORGANIZATION",
                "description": "Tech company",
                "properties": {},
                "rel_type": "WORKS_AT",
                "rel_count": 3,
                "score": 0.6,
            }
        ]

        recommendations = await engine.recommend_by_relationships("entity_1", top_k=5)

        assert len(recommendations) == 1
        assert "connected" in recommendations[0].reason
        assert "WORKS_AT" in recommendations[0].reason

    @pytest.mark.asyncio
    async def test_recommend_by_attributes(
        self, engine, mock_neo4j_client, sample_recommendation_data
    ):
        """Test attribute-based recommendations."""
        mock_neo4j_client.execute_query.return_value = sample_recommendation_data

        recommendations = await engine.recommend_by_attributes("entity_1", top_k=5)

        assert len(recommendations) == 2
        assert recommendations[0].reason == "similar_attributes"

    @pytest.mark.asyncio
    async def test_recommend_similar_entities_collaborative(
        self, engine, mock_neo4j_client, sample_recommendation_data
    ):
        """Test recommend_similar_entities with collaborative method."""
        mock_neo4j_client.execute_query.return_value = sample_recommendation_data

        recommendations = await engine.recommend_similar_entities(
            "entity_1", method="collaborative"
        )

        assert len(recommendations) == 2
        mock_neo4j_client.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_recommend_similar_entities_community(
        self, engine, mock_neo4j_client, sample_recommendation_data
    ):
        """Test recommend_similar_entities with community method."""
        mock_neo4j_client.execute_query.return_value = sample_recommendation_data

        recommendations = await engine.recommend_similar_entities("entity_1", method="community")

        assert len(recommendations) == 2

    @pytest.mark.asyncio
    async def test_recommend_similar_entities_relationships(self, engine, mock_neo4j_client):
        """Test recommend_similar_entities with relationships method."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "id": "entity_2",
                "name": "Test",
                "type": "TEST",
                "description": "",
                "properties": {},
                "rel_type": "KNOWS",
                "rel_count": 1,
                "score": 0.2,
            }
        ]

        recommendations = await engine.recommend_similar_entities(
            "entity_1", method="relationships"
        )

        assert len(recommendations) == 1

    @pytest.mark.asyncio
    async def test_recommend_similar_entities_attributes(
        self, engine, mock_neo4j_client, sample_recommendation_data
    ):
        """Test recommend_similar_entities with attributes method."""
        mock_neo4j_client.execute_query.return_value = sample_recommendation_data

        recommendations = await engine.recommend_similar_entities("entity_1", method="attributes")

        assert len(recommendations) == 2

    @pytest.mark.asyncio
    async def test_recommend_similar_entities_invalid_method(self, engine):
        """Test recommend_similar_entities with invalid method."""
        with pytest.raises(ValueError, match="Unsupported recommendation method"):
            await engine.recommend_similar_entities("entity_1", method="invalid")

    @pytest.mark.asyncio
    async def test_recommend_similar_entities_custom_top_k(
        self, engine, mock_neo4j_client, sample_recommendation_data
    ):
        """Test recommend_similar_entities with custom top_k."""
        mock_neo4j_client.execute_query.return_value = sample_recommendation_data

        await engine.recommend_similar_entities("entity_1", top_k=1)

        mock_neo4j_client.execute_query.assert_called_once()
        call_args = mock_neo4j_client.execute_query.call_args
        assert call_args[0][1]["top_k"] == 1

    @pytest.mark.asyncio
    async def test_recommend_similar_entities_database_error(self, engine, mock_neo4j_client):
        """Test recommend_similar_entities with database error."""
        mock_neo4j_client.execute_query.side_effect = Exception("Connection failed")

        with pytest.raises(DatabaseConnectionError):
            await engine.recommend_similar_entities("entity_1")

    def test_get_recommendation_engine_singleton(self):
        """Test singleton pattern for get_recommendation_engine."""
        engine1 = get_recommendation_engine()
        engine2 = get_recommendation_engine()
        assert engine1 is engine2

    @pytest.mark.asyncio
    async def test_score_normalization(self, engine, mock_neo4j_client):
        """Test that recommendation scores are normalized to [0, 1]."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "id": "entity_2",
                "name": "Test",
                "type": "TEST",
                "description": "",
                "properties": {},
                "common_neighbors": 15,
                "score": 1.5,  # Score > 1.0
            }
        ]

        recommendations = await engine.recommend_by_collaborative("entity_1", top_k=5)

        assert recommendations[0].score <= 1.0
