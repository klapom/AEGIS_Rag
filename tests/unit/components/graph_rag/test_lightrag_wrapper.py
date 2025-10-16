"""Unit tests for LightRAG wrapper.

Sprint 5: Feature 5.1 - LightRAG Core Integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.components.graph_rag.lightrag_wrapper import (
    LightRAGWrapper,
    get_lightrag_wrapper,
    get_lightrag_wrapper_async,
)


class TestLightRAGWrapper:
    """Test LightRAG wrapper initialization and core methods."""

    @pytest.fixture
    def mock_lightrag(self):
        """Mock LightRAG instance."""
        mock_instance = MagicMock()
        mock_instance.ainsert = AsyncMock(return_value={"status": "success"})
        mock_instance.aquery = AsyncMock(return_value="Mock answer from graph")
        return mock_instance

    @pytest.fixture
    async def wrapper(self, mock_lightrag):
        """LightRAG wrapper instance with mocked dependencies."""
        wrapper = LightRAGWrapper(
            working_dir="./data/test_lightrag",
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="test",
        )
        # Manually set the rag instance to avoid import errors
        # Since _ensure_initialized uses lazy imports, we bypass it
        wrapper.rag = mock_lightrag
        wrapper._initialized = True
        yield wrapper

    def test_initialization(self):
        """Test LightRAG wrapper initializes correctly."""
        wrapper = LightRAGWrapper(
            working_dir="./data/test_lightrag",
            llm_model="llama3.2:8b",
            embedding_model="nomic-embed-text",
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="test",
        )

        assert wrapper is not None
        assert wrapper.llm_model == "llama3.2:8b"
        assert wrapper.embedding_model == "nomic-embed-text"
        assert wrapper.working_dir.name == "test_lightrag"
        assert wrapper.neo4j_uri == "bolt://localhost:7687"
        assert wrapper._initialized is False

    @pytest.mark.asyncio
    async def test_insert_documents_single(self, wrapper, mock_lightrag):
        """Test document insertion with single document."""
        documents = [{"text": "Test document about machine learning."}]

        result = await wrapper.insert_documents(documents)

        assert result["total"] == 1
        assert result["success"] == 1
        assert result["failed"] == 0
        mock_lightrag.ainsert.assert_called_once_with("Test document about machine learning.")

    @pytest.mark.asyncio
    async def test_insert_documents_multiple(self, wrapper, mock_lightrag):
        """Test batch document insertion."""
        documents = [
            {"text": "Document 1 about AI"},
            {"text": "Document 2 about ML"},
            {"text": "Document 3 about Deep Learning"},
        ]

        result = await wrapper.insert_documents(documents)

        assert result["total"] == 3
        assert result["success"] == 3
        assert result["failed"] == 0
        assert mock_lightrag.ainsert.call_count == 3

    @pytest.mark.asyncio
    async def test_insert_documents_with_empty(self, wrapper, mock_lightrag):
        """Test document insertion with empty documents."""
        documents = [
            {"text": "Valid document"},
            {"text": ""},  # Empty document
            {"metadata": "no text field"},  # Missing text
        ]

        result = await wrapper.insert_documents(documents)

        assert result["total"] == 3
        assert result["success"] == 1  # Only first document
        # Only the valid document should be inserted
        mock_lightrag.ainsert.assert_called_once_with("Valid document")

    @pytest.mark.asyncio
    async def test_insert_documents_with_error(self, wrapper, mock_lightrag):
        """Test document insertion with errors."""
        mock_lightrag.ainsert = AsyncMock(side_effect=Exception("Insertion failed"))

        documents = [{"text": "Test document"}]

        result = await wrapper.insert_documents(documents)

        assert result["total"] == 1
        assert result["success"] == 0
        assert result["failed"] == 1
        assert result["results"][0]["status"] == "error"

    @pytest.mark.asyncio
    async def test_query_graph_hybrid_mode(self, wrapper, mock_lightrag):
        """Test graph query in hybrid mode."""
        # Mock the QueryParam import
        with patch.dict("sys.modules", {"lightrag": MagicMock(QueryParam=MagicMock())}):
            query = "What companies does John work for?"

            result = await wrapper.query_graph(query, mode="hybrid")

            assert result.query == query
            assert result.mode == "hybrid"
            assert result.answer == "Mock answer from graph"
            assert isinstance(result.entities, list)
            assert isinstance(result.relationships, list)
            mock_lightrag.aquery.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_graph_local_mode(self, wrapper, mock_lightrag):
        """Test graph query in local (entity-level) mode."""
        with patch.dict("sys.modules", {"lightrag": MagicMock(QueryParam=MagicMock())}):
            query = "Who is John Smith?"

            result = await wrapper.query_graph(query, mode="local")

            assert result.mode == "local"
            assert result.answer == "Mock answer from graph"

    @pytest.mark.asyncio
    async def test_query_graph_global_mode(self, wrapper, mock_lightrag):
        """Test graph query in global (topic-level) mode."""
        with patch.dict("sys.modules", {"lightrag": MagicMock(QueryParam=MagicMock())}):
            query = "What are the main themes?"

            result = await wrapper.query_graph(query, mode="global")

            assert result.mode == "global"
            assert result.answer == "Mock answer from graph"

    @pytest.mark.asyncio
    async def test_get_stats(self, wrapper):
        """Test getting graph statistics."""
        with patch("neo4j.AsyncGraphDatabase") as mock_db:
            # Mock Neo4j driver and session
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_entity_result = AsyncMock()
            mock_rel_result = AsyncMock()

            # Mock entity count
            mock_entity_record = {"count": 10}
            mock_entity_result.single = AsyncMock(return_value=mock_entity_record)

            # Mock relationship count
            mock_rel_record = {"count": 15}
            mock_rel_result.single = AsyncMock(return_value=mock_rel_record)

            # Set up session.run to return different results
            async def mock_run(query: str):
                if "Entity" in query:
                    return mock_entity_result
                else:
                    return mock_rel_result

            mock_session.run = AsyncMock(side_effect=mock_run)
            mock_driver.session = MagicMock(return_value=mock_session)
            mock_driver.close = AsyncMock()
            mock_db.driver = MagicMock(return_value=mock_driver)

            # Need to handle async context manager
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            stats = await wrapper.get_stats()

            assert stats["entity_count"] == 10
            assert stats["relationship_count"] == 15

    @pytest.mark.asyncio
    async def test_health_check_success(self, wrapper):
        """Test successful health check."""
        with patch("neo4j.AsyncGraphDatabase") as mock_db:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_result = AsyncMock()
            mock_record = {"health": 1}

            mock_result.single = AsyncMock(return_value=mock_record)
            mock_session.run = AsyncMock(return_value=mock_result)
            mock_driver.session = MagicMock(return_value=mock_session)
            mock_driver.close = AsyncMock()
            mock_db.driver = MagicMock(return_value=mock_driver)

            # Handle async context manager
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            healthy = await wrapper.health_check()

            assert healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, wrapper):
        """Test health check failure."""
        with patch("neo4j.AsyncGraphDatabase") as mock_db:
            mock_db.driver = MagicMock(side_effect=Exception("Connection failed"))

            healthy = await wrapper.health_check()

            assert healthy is False

    def test_singleton_pattern(self):
        """Test singleton pattern for global instance."""
        # Reset global instance
        import src.components.graph_rag.lightrag_wrapper as wrapper_module

        wrapper_module._lightrag_wrapper = None

        instance1 = get_lightrag_wrapper()
        instance2 = get_lightrag_wrapper()

        assert instance1 is instance2
        assert isinstance(instance1, LightRAGWrapper)

    @pytest.mark.asyncio
    async def test_async_singleton_pattern(self):
        """Test async singleton pattern."""
        import src.components.graph_rag.lightrag_wrapper as wrapper_module

        # Reset singleton
        wrapper_module._lightrag_wrapper = None

        # Mock the initialization to avoid real LightRAG import
        with patch.object(LightRAGWrapper, "_ensure_initialized", new=AsyncMock()):
            instance1 = await get_lightrag_wrapper_async()
            instance2 = await get_lightrag_wrapper_async()

            assert instance1 is instance2
            assert isinstance(instance1, LightRAGWrapper)


class TestLightRAGWrapperEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_ensure_initialized_import_error(self):
        """Test initialization with missing LightRAG package."""
        wrapper = LightRAGWrapper()

        with patch("builtins.__import__", side_effect=ImportError("lightrag not found")):
            with pytest.raises(ImportError):
                await wrapper._ensure_initialized()

    @pytest.mark.asyncio
    async def test_query_graph_with_empty_response(self):
        """Test query graph with empty response."""
        with patch.dict("sys.modules", {"lightrag": MagicMock(QueryParam=MagicMock())}):
            mock_lightrag = MagicMock()
            mock_lightrag.aquery = AsyncMock(return_value="")

            wrapper = LightRAGWrapper()
            wrapper.rag = mock_lightrag
            wrapper._initialized = True

            result = await wrapper.query_graph("test query")

            assert result.answer == ""
            assert result.query == "test query"

    @pytest.mark.asyncio
    async def test_get_stats_with_no_data(self):
        """Test get_stats with empty database."""
        wrapper = LightRAGWrapper()
        wrapper._initialized = True

        with patch("neo4j.AsyncGraphDatabase") as mock_db:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_result = AsyncMock()

            # Return None for empty database
            mock_result.single = AsyncMock(return_value=None)
            mock_session.run = AsyncMock(return_value=mock_result)
            mock_driver.session = MagicMock(return_value=mock_session)
            mock_driver.close = AsyncMock()
            mock_db.driver = MagicMock(return_value=mock_driver)

            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            stats = await wrapper.get_stats()

            assert stats["entity_count"] == 0
            assert stats["relationship_count"] == 0
