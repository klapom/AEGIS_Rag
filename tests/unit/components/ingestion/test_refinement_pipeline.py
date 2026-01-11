"""Unit tests for Refinement Pipeline (Sprint 83 Feature 83.4).

Tests:
1. Load chunks from Qdrant
2. LLM entity and relation extraction
3. Neo4j graph indexing
4. Qdrant metadata update
5. Background refinement workflow
6. Error handling and retry
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.ingestion.refinement_pipeline import (
    extract_entities_and_relations_llm,
    load_chunks_from_qdrant,
    run_background_refinement,
    update_neo4j_graph,
    update_qdrant_metadata,
)
from src.core.exceptions import IngestionError


@pytest.fixture
def mock_chunks():
    """Create mock chunk payloads for testing."""
    return [
        {
            "content": "Chunk 1 content with entities",
            "chunk_id": "chunk_1",
            "document_id": "doc_123",
            "page_no": 1,
        },
        {
            "content": "Chunk 2 content with more entities",
            "chunk_id": "chunk_2",
            "document_id": "doc_123",
            "page_no": 2,
        },
    ]


@pytest.fixture
def mock_entities():
    """Create mock entities for testing."""
    return [
        {"text": "Entity1", "type": "PERSON", "chunk_id": "chunk_1"},
        {"text": "Entity2", "type": "ORG", "chunk_id": "chunk_2"},
    ]


@pytest.fixture
def mock_relations():
    """Create mock relations for testing."""
    return [
        {
            "source": "Entity1",
            "relation": "WORKS_FOR",
            "target": "Entity2",
            "chunk_id": "chunk_1",
        }
    ]


class TestLoadChunksFromQdrant:
    """Test loading chunks from Qdrant."""

    async def test_load_chunks_success(self, mock_chunks):
        """Test successful chunk loading from Qdrant."""
        with patch(
            "src.components.ingestion.refinement_pipeline.QdrantClientWrapper"
        ) as MockQdrant:
            # Mock Qdrant scroll response
            mock_qdrant = AsyncMock()
            mock_point_1 = MagicMock()
            mock_point_1.payload = mock_chunks[0]
            mock_point_2 = MagicMock()
            mock_point_2.payload = mock_chunks[1]

            # Simulate two batches
            mock_qdrant.async_client.scroll.side_effect = [
                ([mock_point_1], "offset_1"),
                ([mock_point_2], None),  # None means no more data
            ]
            MockQdrant.return_value = mock_qdrant

            chunks = await load_chunks_from_qdrant(
                document_id="doc_123",
                namespace="research",
            )

            assert len(chunks) == 2
            assert chunks[0]["chunk_id"] == "chunk_1"
            assert chunks[1]["chunk_id"] == "chunk_2"

    async def test_load_chunks_empty_result(self):
        """Test loading chunks when document has no chunks."""
        with patch(
            "src.components.ingestion.refinement_pipeline.QdrantClientWrapper"
        ) as MockQdrant:
            mock_qdrant = AsyncMock()
            mock_qdrant.async_client.scroll.return_value = ([], None)
            MockQdrant.return_value = mock_qdrant

            chunks = await load_chunks_from_qdrant(
                document_id="doc_nonexistent",
                namespace="research",
            )

            assert len(chunks) == 0

    async def test_load_chunks_error_handling(self):
        """Test error handling when Qdrant fails."""
        with patch(
            "src.components.ingestion.refinement_pipeline.QdrantClientWrapper"
        ) as MockQdrant:
            mock_qdrant = AsyncMock()
            mock_qdrant.async_client.scroll.side_effect = Exception("Qdrant error")
            MockQdrant.return_value = mock_qdrant

            with pytest.raises(IngestionError, match="Failed to load chunks from Qdrant"):
                await load_chunks_from_qdrant(
                    document_id="doc_123",
                    namespace="research",
                )


class TestLLMExtraction:
    """Test LLM entity and relation extraction."""

    async def test_extract_entities_and_relations_success(
        self, mock_chunks, mock_entities, mock_relations
    ):
        """Test successful LLM extraction."""
        with patch(
            "src.components.ingestion.refinement_pipeline.get_lightrag_wrapper_async"
        ) as mock_get_lightrag:
            # Mock LightRAG
            mock_lightrag = AsyncMock()
            mock_lightrag.extract_from_text.return_value = {
                "entities": mock_entities[:1],  # 1 entity per chunk
                "relations": mock_relations,
            }
            mock_get_lightrag.return_value = mock_lightrag

            entities, relations = await extract_entities_and_relations_llm(
                chunks=mock_chunks,
                document_id="doc_123",
                domain="ai_papers",
            )

            # Should have 2 entities (1 per chunk)
            assert len(entities) == 2
            # Relations accumulated
            assert len(relations) == 2

            # Verify LightRAG called for each chunk
            assert mock_lightrag.extract_from_text.await_count == 2

    async def test_extract_entities_continues_on_chunk_failure(self, mock_chunks):
        """Test extraction continues if one chunk fails."""
        with patch(
            "src.components.ingestion.refinement_pipeline.get_lightrag_wrapper_async"
        ) as mock_get_lightrag:
            mock_lightrag = AsyncMock()

            # First chunk fails, second succeeds
            mock_lightrag.extract_from_text.side_effect = [
                Exception("Extraction failed"),
                {"entities": [{"text": "Entity1", "type": "PERSON"}], "relations": []},
            ]
            mock_get_lightrag.return_value = mock_lightrag

            entities, relations = await extract_entities_and_relations_llm(
                chunks=mock_chunks,
                document_id="doc_123",
                domain="ai_papers",
            )

            # Should have 1 entity from successful chunk
            assert len(entities) == 1
            assert entities[0]["text"] == "Entity1"


class TestNeo4jIndexing:
    """Test Neo4j graph indexing."""

    async def test_update_neo4j_graph_success(self, mock_entities, mock_relations):
        """Test successful Neo4j indexing."""
        with patch(
            "src.components.ingestion.refinement_pipeline.get_lightrag_wrapper_async"
        ) as mock_get_lightrag:
            mock_lightrag = AsyncMock()
            mock_lightrag.store_entities_and_relations.return_value = None
            mock_get_lightrag.return_value = mock_lightrag

            await update_neo4j_graph(
                entities=mock_entities,
                relations=mock_relations,
                document_id="doc_123",
                namespace="research",
            )

            # Verify LightRAG called with correct params
            mock_lightrag.store_entities_and_relations.assert_awaited_once_with(
                entities=mock_entities,
                relations=mock_relations,
                namespace="research",
            )

    async def test_update_neo4j_graph_error(self, mock_entities, mock_relations):
        """Test Neo4j indexing error handling."""
        with patch(
            "src.components.ingestion.refinement_pipeline.get_lightrag_wrapper_async"
        ) as mock_get_lightrag:
            mock_lightrag = AsyncMock()
            mock_lightrag.store_entities_and_relations.side_effect = Exception("Neo4j error")
            mock_get_lightrag.return_value = mock_lightrag

            with pytest.raises(IngestionError, match="Neo4j indexing failed"):
                await update_neo4j_graph(
                    entities=mock_entities,
                    relations=mock_relations,
                    document_id="doc_123",
                    namespace="research",
                )


class TestQdrantMetadataUpdate:
    """Test Qdrant metadata update."""

    async def test_update_qdrant_metadata_success(self, mock_entities):
        """Test successful Qdrant metadata update."""
        with patch(
            "src.components.ingestion.refinement_pipeline.QdrantClientWrapper"
        ) as MockQdrant:
            mock_qdrant = AsyncMock()
            mock_qdrant.async_client.set_payload.return_value = None
            MockQdrant.return_value = mock_qdrant

            await update_qdrant_metadata(
                document_id="doc_123",
                namespace="research",
                entities=mock_entities,
            )

            # Verify set_payload called for each chunk
            assert mock_qdrant.async_client.set_payload.await_count == 2

            # Verify payload structure
            first_call = mock_qdrant.async_client.set_payload.await_args_list[0]
            payload = first_call[1]["payload"]
            assert "entities" in payload
            assert payload["refinement_pending"] is False
            assert "refinement_timestamp" in payload

    async def test_update_qdrant_metadata_continues_on_chunk_failure(self, mock_entities):
        """Test metadata update continues if one chunk fails."""
        with patch(
            "src.components.ingestion.refinement_pipeline.QdrantClientWrapper"
        ) as MockQdrant:
            mock_qdrant = AsyncMock()

            # First chunk fails, second succeeds
            mock_qdrant.async_client.set_payload.side_effect = [
                Exception("Update failed"),
                None,
            ]
            MockQdrant.return_value = mock_qdrant

            # Should not raise exception
            await update_qdrant_metadata(
                document_id="doc_123",
                namespace="research",
                entities=mock_entities,
            )

            # Verify both chunks attempted
            assert mock_qdrant.async_client.set_payload.await_count == 2


class TestBackgroundRefinement:
    """Test complete background refinement workflow."""

    async def test_run_background_refinement_success(
        self, mock_chunks, mock_entities, mock_relations
    ):
        """Test successful background refinement workflow."""
        with (
            patch(
                "src.components.ingestion.refinement_pipeline.load_chunks_from_qdrant"
            ) as mock_load,
            patch(
                "src.components.ingestion.refinement_pipeline.extract_entities_and_relations_llm"
            ) as mock_extract,
            patch(
                "src.components.ingestion.refinement_pipeline.update_neo4j_graph"
            ) as mock_neo4j,
            patch(
                "src.components.ingestion.refinement_pipeline.update_qdrant_metadata"
            ) as mock_qdrant,
            patch(
                "src.components.ingestion.refinement_pipeline.get_background_job_queue"
            ) as mock_queue,
        ):
            # Mock all pipeline steps
            mock_load.return_value = mock_chunks
            mock_extract.return_value = (mock_entities, mock_relations)
            mock_neo4j.return_value = None
            mock_qdrant.return_value = None

            mock_job_queue = AsyncMock()
            mock_job_queue.initialize.return_value = None
            mock_job_queue.set_status.return_value = None
            mock_queue.return_value = mock_job_queue

            # Run refinement
            await run_background_refinement(
                document_id="doc_123",
                namespace="research",
                domain="ai_papers",
            )

            # Verify all steps called
            mock_load.assert_awaited_once()
            mock_extract.assert_awaited_once()
            mock_neo4j.assert_awaited_once()
            mock_qdrant.assert_awaited_once()

            # Verify status updates
            assert mock_job_queue.set_status.await_count >= 5
            # Check final status
            final_call = mock_job_queue.set_status.await_args_list[-1]
            assert final_call[1]["status"] == "ready"
            assert final_call[1]["progress_pct"] == 100.0

    async def test_run_background_refinement_no_chunks(self):
        """Test refinement fails if no chunks found."""
        with (
            patch(
                "src.components.ingestion.refinement_pipeline.load_chunks_from_qdrant"
            ) as mock_load,
            patch(
                "src.components.ingestion.refinement_pipeline.get_background_job_queue"
            ) as mock_queue,
        ):
            mock_load.return_value = []  # No chunks

            mock_job_queue = AsyncMock()
            mock_job_queue.initialize.return_value = None
            mock_job_queue.set_status.return_value = None
            mock_queue.return_value = mock_job_queue

            with pytest.raises(IngestionError, match="No chunks found in Qdrant"):
                await run_background_refinement(
                    document_id="doc_123",
                    namespace="research",
                    domain="ai_papers",
                )

    async def test_run_background_refinement_error_handling(self, mock_chunks):
        """Test refinement error handling marks status as failed."""
        with (
            patch(
                "src.components.ingestion.refinement_pipeline.load_chunks_from_qdrant"
            ) as mock_load,
            patch(
                "src.components.ingestion.refinement_pipeline.extract_entities_and_relations_llm"
            ) as mock_extract,
            patch(
                "src.components.ingestion.refinement_pipeline.get_background_job_queue"
            ) as mock_queue,
        ):
            mock_load.return_value = mock_chunks
            mock_extract.side_effect = Exception("Extraction failed")

            mock_job_queue = AsyncMock()
            mock_job_queue.initialize.return_value = None
            mock_job_queue.set_status.return_value = None
            mock_queue.return_value = mock_job_queue

            # Should raise exception
            with pytest.raises(Exception, match="Extraction failed"):
                await run_background_refinement(
                    document_id="doc_123",
                    namespace="research",
                    domain="ai_papers",
                )

            # Verify error status was set
            final_call = mock_job_queue.set_status.await_args_list[-1]
            assert final_call[1]["status"] == "failed"
            assert "Extraction failed" in final_call[1]["error_message"]
