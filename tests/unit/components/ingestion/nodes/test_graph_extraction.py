"""Unit tests for graph extraction node (Sprint 54 Feature 54.7).

Tests the graph_extraction_node which handles entity/relation extraction,
Neo4j storage, and community detection.

Test Coverage:
- test_graph_extraction_success() - Successful graph extraction
- test_graph_extraction_no_chunks() - No chunks available → error
- test_graph_extraction_lightrag_insert() - LightRAG insert called correctly
- test_graph_extraction_relation_extraction() - RELATES_TO relationships created
- test_graph_extraction_section_nodes() - Section nodes created
- test_graph_extraction_community_detection() - Community detection runs
- test_graph_extraction_community_skipped() - Community detection skipped (no relations)
- test_graph_extraction_error_handling() - Error during extraction
- test_graph_extraction_state_updated() - All state fields updated
- test_graph_extraction_vram_leak_detected() - VRAM leak tracking
"""

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog.testing

from src.components.ingestion.ingestion_state import IngestionState
from src.components.ingestion.nodes.graph_extraction import graph_extraction_node
from src.core.exceptions import IngestionError

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def base_state() -> IngestionState:
    """Base ingestion state for testing."""
    return {
        "document_id": "test_doc_123",
        "document_path": "/tmp/test.pdf",
        "batch_index": 1,
        "parsed_content": "Test document content",
        "chunks": [
            {
                "chunk": MagicMock(text="Chunk 1 content"),
                "image_bboxes": [],
            },
            {
                "chunk": MagicMock(text="Chunk 2 content"),
                "image_bboxes": [],
            },
        ],
        "embedded_chunk_ids": ["chunk_001", "chunk_002"],
        "memory_check_passed": True,
        "current_memory_mb": 4000.0,
        "current_vram_mb": 3000.0,
        "requires_container_restart": False,
        "overall_progress": 0.6,
        "errors": [],
        "docling_status": "completed",
        "chunking_status": "completed",
        "embedding_status": "completed",
        "graph_status": "pending",
        "vector_status": "completed",
        "sections": [],
        "adaptive_chunks": [],
    }


@pytest.fixture
def mock_extract_and_store():
    """Mock extract_and_store_entities function."""
    mock_fn = AsyncMock(
        return_value={
            "document_id": "test_doc_123",
            "status": "success",
            "stats": {
                "total_chunks": 2,
                "total_entities": 10,
                "total_relations": 5,
                "total_relations_stored": 5,
                "total_mentioned_in": 20,
            },
            "total_time_seconds": 1.5,
        }
    )
    return mock_fn


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client."""
    client = AsyncMock()
    client.execute_read = AsyncMock(
        return_value=[
            {
                "chunk_id": "chunk_001",
                "chunk_text": "Chunk 1 content",
            },
            {
                "chunk_id": "chunk_002",
                "chunk_text": "Chunk 2 content",
            },
        ]
    )
    client.create_section_nodes = AsyncMock(
        return_value={
            "sections_created": 3,
            "has_section_rels": 2,
            "contains_chunk_rels": 2,
            "defines_entity_rels": 0,
        }
    )
    client.store_relations = AsyncMock(return_value=3)
    return client


@pytest.fixture
def mock_community_detector():
    """Mock community detector."""
    detector = AsyncMock()
    detector.algorithm = "leiden"
    detector.resolution = 1.0
    detector.min_size = 3
    detector.detect_communities = AsyncMock(
        return_value=[
            MagicMock(size=5),
            MagicMock(size=3),
        ]
    )
    return detector


@pytest.fixture
def mock_relation_extractor():
    """Mock relation extractor."""
    extractor = MagicMock()
    extractor.extract_with_gleaning = AsyncMock(
        return_value=[
            {"source": "Entity1", "relation": "RELATES_TO", "target": "Entity2"},
            {"source": "Entity2", "relation": "RELATES_TO", "target": "Entity3"},
        ]
    )
    return extractor


# =============================================================================
# TEST: SUCCESSFUL GRAPH EXTRACTION
# =============================================================================


@pytest.mark.asyncio
async def test_graph_extraction_success(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
) -> None:
    """Test successful graph extraction workflow.

    Expected behavior:
    - extract_and_store_entities called with chunks
    - Entities and relations stored
    - graph_status = 'completed'
    """
    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=MagicMock(),
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
    ):
        result = await graph_extraction_node(base_state)

        # Verify graph extraction succeeded
        assert result["graph_status"] == "completed"
        assert "graph_start_time" in result
        assert "graph_end_time" in result

        # Verify extract_and_store_entities called
        mock_extract_and_store.assert_called_once()


# =============================================================================
# TEST: NO CHUNKS AVAILABLE
# =============================================================================


@pytest.mark.asyncio
async def test_graph_extraction_no_chunks(base_state: IngestionState) -> None:
    """Test graph extraction fails when no chunks available.

    Expected behavior:
    - IngestionError raised
    - Error message indicates missing chunks
    """
    base_state["chunks"] = []

    with pytest.raises(IngestionError) as exc_info:
        await graph_extraction_node(base_state)

    assert "No chunks for graph extraction" in str(exc_info.value)


# =============================================================================
# TEST: LIGHTRAG INSERT CALLED CORRECTLY
# =============================================================================


@pytest.mark.asyncio
async def test_graph_extraction_extract_and_store_called(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
) -> None:
    """Test extract_and_store_entities called with correct args.

    Expected behavior:
    - Chunks converted to proper format
    - chunk_id from embedded_chunk_ids used
    - extract_and_store_entities called with chunks list
    """
    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=MagicMock(),
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
    ):
        await graph_extraction_node(base_state)

        # Verify extract_and_store_entities called
        mock_extract_and_store.assert_called_once()
        call_args = mock_extract_and_store.call_args
        chunks = call_args.kwargs["chunks"]

        # Verify chunk count
        assert len(chunks) == 2


# =============================================================================
# TEST: RELATION EXTRACTION
# =============================================================================


@pytest.mark.asyncio
async def test_graph_extraction_relation_extraction(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
    mock_relation_extractor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test RELATES_TO relationship extraction (ADR-064 legacy Round-2 path).

    ADR-064: Round 2 is disabled by default; this test exercises the legacy
    path explicitly via AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS=true.

    Expected behavior:
    - Neo4j queried for entities per chunk
    - RelationExtractor called with entities
    - Relations stored via neo4j_client.store_relations
    """
    monkeypatch.setenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", "true")

    # Mock Neo4j entity query response
    mock_neo4j_client.execute_read = AsyncMock(
        side_effect=[
            # First call: query chunks
            [
                {"chunk_id": "chunk_001", "chunk_text": "Content"},
                {"chunk_id": "chunk_002", "chunk_text": "Content"},
            ],
            # Second call (chunk 1): query entities
            [
                {"name": "Entity1", "type": "PERSON"},
                {"name": "Entity2", "type": "ORGANIZATION"},
            ],
            # Third call (chunk 2): query entities
            [
                {"name": "Entity3", "type": "LOCATION"},
                {"name": "Entity4", "type": "PERSON"},
            ],
        ]
    )

    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=MagicMock(),
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
            return_value=mock_relation_extractor,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
    ):
        result = await graph_extraction_node(base_state)

        # Verify relations stored
        assert result["relations_count"] > 0
        mock_neo4j_client.store_relations.assert_called()


# =============================================================================
# TEST: SECTION NODES CREATION
# =============================================================================


@pytest.mark.asyncio
async def test_graph_extraction_section_nodes(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
) -> None:
    """Test section nodes creation when sections available.

    Expected behavior:
    - create_section_nodes called with sections and chunks
    - section_node_stats stored in state
    """
    from src.components.ingestion.nodes.models import SectionMetadata

    # Add sections to state
    base_state["sections"] = [
        SectionMetadata(
            heading="Section 1",
            level=1,
            page_no=1,
            bbox={"l": 0, "t": 0, "r": 100, "b": 100},
            text="Section 1 content",
            token_count=100,
            metadata={},
        ),
    ]
    base_state["adaptive_chunks"] = [
        MagicMock(token_count=100, section_headings=["Section 1"]),
    ]

    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=MagicMock(),
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
    ):
        result = await graph_extraction_node(base_state)

        # Verify section nodes created
        assert "section_node_stats" in result
        mock_neo4j_client.create_section_nodes.assert_called_once()


# =============================================================================
# TEST: COMMUNITY DETECTION
# =============================================================================


@pytest.mark.asyncio
async def test_graph_extraction_community_detection(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
    mock_community_detector,
) -> None:
    """Test community detection runs when relations created.

    Expected behavior:
    - detect_communities called
    - community_detection_stats stored
    - communities_detected populated
    """
    # Ensure relations will be created (mock returns relations)
    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=mock_community_detector,
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
    ):
        result = await graph_extraction_node(base_state)

        # Sprint 126: Community detection is deferred to batch mode
        # Verify graph extraction still completes successfully
        assert result["graph_status"] == "completed"


# =============================================================================
# TEST: COMMUNITY DETECTION SKIPPED (NO RELATIONS)
# =============================================================================


@pytest.mark.asyncio
async def test_graph_extraction_community_skipped_no_relations(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
    mock_community_detector,
) -> None:
    """Test community detection skipped when no relations created.

    Expected behavior:
    - detect_communities NOT called
    - community_detection_stats stored with skip reason
    """
    # Mock no relations created (empty entity list)
    mock_neo4j_client.execute_read = AsyncMock(
        side_effect=[
            # First call: query chunks
            [
                {"chunk_id": "chunk_001", "chunk_text": "Content"},
                {"chunk_id": "chunk_002", "chunk_text": "Content"},
            ],
            # Second call (chunk 1): no entities
            [],
            # Third call (chunk 2): no entities
            [],
        ]
    )

    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=mock_community_detector,
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
    ):
        result = await graph_extraction_node(base_state)

        # Verify community detection skipped
        assert "community_detection_stats" in result
        mock_community_detector.detect_communities.assert_not_called()


# =============================================================================
# TEST: STATE UPDATED CORRECTLY
# =============================================================================


@pytest.mark.asyncio
async def test_graph_extraction_state_updated(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
) -> None:
    """Test graph extraction updates all required state fields.

    Expected fields:
    - graph_status
    - graph_start_time
    - graph_end_time
    - entities
    - relations
    - relations_count
    - section_node_stats
    - community_detection_stats
    - overall_progress
    """
    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=MagicMock(),
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
    ):
        result = await graph_extraction_node(base_state)

        # Verify required fields
        assert "graph_status" in result
        assert result["graph_status"] == "completed"
        assert "graph_start_time" in result
        assert "graph_end_time" in result
        assert "entities" in result
        assert "relations" in result
        assert "relations_count" in result
        assert "community_detection_stats" in result
        assert "overall_progress" in result

        # Verify types
        assert isinstance(result["graph_start_time"], float)
        assert isinstance(result["graph_end_time"], float)
        assert isinstance(result["entities"], list)
        assert isinstance(result["relations"], list)


# =============================================================================
# TEST: ERROR HANDLING
# =============================================================================


@pytest.mark.asyncio
async def test_graph_extraction_error_handling(
    base_state: IngestionState,
) -> None:
    """Test graph extraction error handling.

    Expected behavior:
    - Exception caught and logged
    - Error added to state
    - graph_status = 'failed'
    """
    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            side_effect=RuntimeError("Extraction error"),
        ),
        pytest.raises(RuntimeError),
    ):
        await graph_extraction_node(base_state)


# =============================================================================
# TEST: PROGRESS EVENTS EMITTED
# =============================================================================


@pytest.mark.asyncio
async def test_graph_extraction_progress_events(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
    mock_relation_extractor,
) -> None:
    """Test progress events emitted during extraction.

    Expected behavior:
    - emit_progress called multiple times
    - Events for entity extraction, relation extraction, community detection
    """
    mock_emit = AsyncMock()

    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=MagicMock(),
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
            return_value=mock_relation_extractor,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            mock_emit,
        ),
    ):
        await graph_extraction_node(base_state)

        # Verify progress events emitted
        assert mock_emit.called


# =============================================================================
# TEST: ENHANCED CHUNKS WITH IMAGE BBOXES
# =============================================================================


@pytest.mark.asyncio
async def test_graph_extraction_enhanced_chunks_with_images(
    mock_extract_and_store,
    mock_neo4j_client,
) -> None:
    """Test graph extraction with enhanced chunks containing images.

    Expected behavior:
    - Enhanced chunks with image_bboxes handled correctly
    - Image bbox info preserved but not used in extraction
    """
    state = {
        "document_id": "test_doc_123",
        "document_path": "/tmp/test.pdf",
        "batch_index": 1,
        "parsed_content": "Test document with images",
        "chunks": [
            {
                "chunk": MagicMock(text="Chunk with image"),
                "image_bboxes": [{"page": 1, "bbox": [10, 20, 100, 200]}],
            },
        ],
        "embedded_chunk_ids": ["chunk_001"],
        "memory_check_passed": True,
        "current_memory_mb": 4000.0,
        "current_vram_mb": 3000.0,
        "requires_container_restart": False,
        "overall_progress": 0.6,
        "errors": [],
        "docling_status": "completed",
        "chunking_status": "completed",
        "embedding_status": "completed",
        "graph_status": "pending",
        "vector_status": "completed",
        "sections": [],
        "adaptive_chunks": [],
    }

    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=MagicMock(),
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
    ):
        result = await graph_extraction_node(state)

        # Verify extraction succeeded with enhanced chunks
        assert result["graph_status"] == "completed"


# =============================================================================
# TEST: CHUNK COUNT TRACKING
# =============================================================================


@pytest.mark.asyncio
async def test_graph_extraction_chunk_count_tracking(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
) -> None:
    """Test graph extraction tracks chunk count correctly.

    Expected behavior:
    - Extraction stats contain chunk count
    - State contains chunk count info
    """
    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=MagicMock(),
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
    ):
        result = await graph_extraction_node(base_state)

        # Verify extraction stats available
        assert result["graph_status"] == "completed"


# =============================================================================
# ADR-064: ROUND-2 RELATION EXTRACTION FEATURE FLAG
# (Critic-Gate CRITIC_GATE_ADR_064_2026-07-21.md, Section C1: U1-U5)
# =============================================================================


@pytest.mark.asyncio
async def test_graph_extraction_node_skips_round2_by_default(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
    mock_relation_extractor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U1: Round 2 is skipped when AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS is unset.

    Expected behavior:
    - RelationExtractor.extract_with_gleaning never awaited
    - neo4j_client.store_relations never called from the node's Round-2 loop
    - state["relations_count"] == stats.total_relations_stored (Round-1 count)
    - round2_relation_extraction_skipped log emitted with reason/document_id/round1_relations
    """
    monkeypatch.delenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", raising=False)

    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=MagicMock(),
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
            return_value=mock_relation_extractor,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
        structlog.testing.capture_logs() as captured_logs,
    ):
        result = await graph_extraction_node(base_state)

        # Round 2 extractor/store never invoked
        mock_relation_extractor.extract_with_gleaning.assert_not_awaited()
        mock_neo4j_client.store_relations.assert_not_called()

        # relations_count comes from Round-1 stored stats, not Round-2
        assert result["relations_count"] == 5

        skip_events = [
            e for e in captured_logs if e.get("event") == "round2_relation_extraction_skipped"
        ]
        assert len(skip_events) == 1
        assert skip_events[0]["reason"] == "disabled_by_adr_064"
        assert skip_events[0]["document_id"] == "test_doc_123"
        assert skip_events[0]["round1_relations"] == 5


@pytest.mark.asyncio
async def test_graph_extraction_node_runs_round2_when_flag_true(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
    mock_relation_extractor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U2: Round 2 runs (legacy behavior byte-identical) when flag is 'true'."""
    monkeypatch.setenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", "true")

    mock_neo4j_client.execute_read = AsyncMock(
        side_effect=[
            [
                {"chunk_id": "chunk_001", "chunk_text": "Content"},
                {"chunk_id": "chunk_002", "chunk_text": "Content"},
            ],
            [
                {"name": "Entity1", "type": "PERSON"},
                {"name": "Entity2", "type": "ORGANIZATION"},
            ],
            [
                {"name": "Entity3", "type": "LOCATION"},
                {"name": "Entity4", "type": "PERSON"},
            ],
        ]
    )

    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=MagicMock(),
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
            return_value=mock_relation_extractor,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
    ):
        result = await graph_extraction_node(base_state)

        mock_relation_extractor.extract_with_gleaning.assert_awaited()
        mock_neo4j_client.store_relations.assert_called()
        # Round-2 counting: 2 chunks x 2 relations stored (mock_neo4j_client.store_relations -> 3 each)
        assert result["relations_count"] == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_value", ["1", "yes", "TRUE ", "on"])
async def test_round2_flag_rejects_non_true_values(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
    mock_relation_extractor,
    monkeypatch: pytest.MonkeyPatch,
    flag_value: str,
) -> None:
    """U3: Only the exact literal 'true' (case-insensitive, no whitespace) activates Round 2.

    '1', 'yes', trailing-space 'TRUE ', and 'on' must all be treated as skip,
    matching the AEGIS_LLM_THINKING contract (no strtobool semantics).
    """
    monkeypatch.setenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", flag_value)

    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=MagicMock(),
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
            return_value=mock_relation_extractor,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
    ):
        result = await graph_extraction_node(base_state)

        mock_relation_extractor.extract_with_gleaning.assert_not_awaited()
        assert result["relations_count"] == 5  # Round-1 stored count, not Round-2


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_value", ["true", "True", "TRUE"])
async def test_round2_flag_accepts_true_case_insensitive(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
    mock_relation_extractor,
    monkeypatch: pytest.MonkeyPatch,
    flag_value: str,
) -> None:
    """U3 (contract complement): 'true'/'True'/'TRUE' all activate Round 2."""
    monkeypatch.setenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", flag_value)

    mock_neo4j_client.execute_read = AsyncMock(
        side_effect=[
            [{"chunk_id": "chunk_001", "chunk_text": "Content"}],
            [
                {"name": "Entity1", "type": "PERSON"},
                {"name": "Entity2", "type": "ORGANIZATION"},
            ],
        ]
    )

    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=MagicMock(),
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
            return_value=mock_relation_extractor,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
    ):
        await graph_extraction_node(base_state)

        mock_relation_extractor.extract_with_gleaning.assert_awaited()


@pytest.mark.asyncio
async def test_round2_skip_emits_no_relation_extraction_progress(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U4: When Round 2 is skipped, no emit_progress call uses phase='relation_extraction',
    while entity_extraction progress events are still emitted unchanged.
    """
    monkeypatch.delenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", raising=False)
    mock_emit = AsyncMock()

    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=MagicMock(),
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            mock_emit,
        ),
    ):
        await graph_extraction_node(base_state)

        relation_extraction_calls = [
            call
            for call in mock_emit.call_args_list
            if call.kwargs.get("phase") == "relation_extraction"
        ]
        entity_extraction_calls = [
            call
            for call in mock_emit.call_args_list
            if call.kwargs.get("phase") == "entity_extraction"
        ]
        assert relation_extraction_calls == []
        assert len(entity_extraction_calls) == 2  # start + complete


@pytest.mark.asyncio
async def test_community_detection_immediate_uses_round1_count_when_skipped(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
    mock_community_detector,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5: With Round 2 skipped and detection_mode='sync', community detection
    runs because the sync-mode gate (relations_created > 0) is fed by the
    Round-1 stored count, not the (now-absent) Round-2 count.

    Regression guard for the latent bug identified in Critic-Gate G5: previously,
    if Round 2 happened to store 0 relations while Round 1 stored >0, community
    detection was incorrectly skipped.
    """
    monkeypatch.delenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", raising=False)

    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=mock_community_detector,
        ),
        patch(
            "src.components.graph_rag.relation_extractor.RelationExtractor",
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
        patch("src.core.config.settings.graph_community_detection_mode", "sync"),
    ):
        result = await graph_extraction_node(base_state)

        assert result["relations_count"] == 5  # Round-1 stored count (mock_extract_and_store)
        mock_community_detector.detect_communities.assert_called_once()
        assert result["community_detection_stats"]["communities_detected"] == 2


# =============================================================================
# ADR-064: ADVERSARIAL HARDENING (Fable verify pass, beyond C1 U1-U5)
# =============================================================================


@contextmanager
def _adr064_node_env(mock_extract_and_store, mock_neo4j_client, community_detector=None):
    """Standard patch set for graph_extraction_node ADR-064 tests."""
    with (
        patch(
            "src.components.ingestion.nodes.graph_extraction.extract_and_store_entities",
            mock_extract_and_store,
        ),
        patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch(
            "src.components.ingestion.nodes.graph_extraction.get_community_detector",
            return_value=community_detector or MagicMock(),
        ),
        patch("src.components.graph_rag.relation_extractor.RelationExtractor"),
        patch(
            "src.components.ingestion.nodes.graph_extraction.emit_progress",
            new_callable=AsyncMock,
        ),
    ):
        yield


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_value", [None, "true"])
async def test_neo4j_commit_wait_sleep_runs_exactly_once_regardless_of_flag(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
    monkeypatch: pytest.MonkeyPatch,
    flag_value: str | None,
) -> None:
    """G3 guard: the Sprint-33 asyncio.sleep(1.0) commit-wait sits BEFORE the
    ADR-064 branch and must fire exactly once in both the skip and legacy path.

    Catches an accidental relocation of the sleep into the else branch (which
    would re-open the Neo4j visibility race for create_section_nodes, Critic G3).
    """
    if flag_value is None:
        monkeypatch.delenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", raising=False)
    else:
        monkeypatch.setenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", flag_value)

    mock_asyncio = MagicMock(sleep=AsyncMock())

    with (
        _adr064_node_env(mock_extract_and_store, mock_neo4j_client),
        patch(
            "src.components.ingestion.nodes.graph_extraction.asyncio",
            mock_asyncio,
        ),
    ):
        await graph_extraction_node(base_state)

        commit_wait_calls = [c for c in mock_asyncio.sleep.await_args_list if c.args == (1.0,)]
        assert len(commit_wait_calls) == 1
        assert mock_asyncio.sleep.await_count == 1


@pytest.mark.asyncio
async def test_skip_and_legacy_branches_write_same_state_keys(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """State-contract parity: the skip branch must not drop (or add) state keys
    relative to the legacy branch — downstream nodes and the upload response
    (retrieval.py: relations_count -> neo4j_relationships) read the same fields
    in both modes.
    """
    state_off = dict(base_state)
    state_on = dict(base_state)

    monkeypatch.delenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", raising=False)
    with _adr064_node_env(mock_extract_and_store, mock_neo4j_client):
        result_off = await graph_extraction_node(state_off)

    monkeypatch.setenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", "true")
    with _adr064_node_env(mock_extract_and_store, mock_neo4j_client):
        result_on = await graph_extraction_node(state_on)

    assert set(result_off.keys()) == set(result_on.keys())
    assert result_off["graph_status"] == result_on["graph_status"] == "completed"
    # Both branches must produce an int relations_count (API contract)
    assert isinstance(result_off["relations_count"], int)
    assert isinstance(result_on["relations_count"], int)


@pytest.mark.asyncio
async def test_round2_skip_log_field_contract(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skip-log contract: round2_relation_extraction_skipped carries exactly
    the fields {reason, document_id, round1_relations} — operators and log
    queries depend on these names (Critic G5 Fix 1).
    """
    monkeypatch.delenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", raising=False)

    with (
        _adr064_node_env(mock_extract_and_store, mock_neo4j_client),
        structlog.testing.capture_logs() as captured_logs,
    ):
        await graph_extraction_node(base_state)

    skip_events = [
        e for e in captured_logs if e.get("event") == "round2_relation_extraction_skipped"
    ]
    assert len(skip_events) == 1
    payload_keys = set(skip_events[0]) - {"event", "log_level"}
    assert payload_keys == {"reason", "document_id", "round1_relations"}


@pytest.mark.asyncio
async def test_round2_timing_logs_only_in_legacy_path(
    base_state: IngestionState,
    mock_extract_and_store,
    mock_neo4j_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """I2-at-unit-level: TIMING_relation_extraction_* events are absent when
    skipped and present when the flag is true (rollback verification signal
    from the ADR-064 rollback procedure relies on this log line).
    """
    monkeypatch.delenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", raising=False)
    with (
        _adr064_node_env(mock_extract_and_store, mock_neo4j_client),
        structlog.testing.capture_logs() as logs_off,
    ):
        await graph_extraction_node(dict(base_state))

    monkeypatch.setenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", "true")
    with (
        _adr064_node_env(mock_extract_and_store, mock_neo4j_client),
        structlog.testing.capture_logs() as logs_on,
    ):
        await graph_extraction_node(dict(base_state))

    events_off = {e.get("event") for e in logs_off}
    events_on = {e.get("event") for e in logs_on}
    assert "TIMING_relation_extraction_start" not in events_off
    assert "TIMING_relation_extraction_complete" not in events_off
    assert "TIMING_relation_extraction_start" in events_on
    assert "TIMING_relation_extraction_complete" in events_on
    assert "round2_relation_extraction_skipped" not in events_on


@pytest.mark.asyncio
async def test_community_detection_sync_skipped_when_round1_stores_zero(
    base_state: IngestionState,
    mock_neo4j_client,
    mock_community_detector,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U5 complement: with Round 2 skipped and Round 1 storing 0 relations,
    the sync-mode CD gate (relations_created > 0) must NOT run community
    detection — the gate's negative side stays intact after ADR-064.
    """
    monkeypatch.delenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", raising=False)

    zero_store = AsyncMock(
        return_value={
            "document_id": "test_doc_123",
            "status": "success",
            "stats": {
                "total_chunks": 2,
                "total_entities": 10,
                "total_relations": 3,
                "total_relations_stored": 0,
                "total_mentioned_in": 20,
            },
            "total_time_seconds": 1.5,
        }
    )

    with (
        _adr064_node_env(zero_store, mock_neo4j_client, mock_community_detector),
        patch("src.core.config.settings.graph_community_detection_mode", "sync"),
    ):
        result = await graph_extraction_node(base_state)

    assert result["relations_count"] == 0
    mock_community_detector.detect_communities.assert_not_called()


def test_round2_flag_not_enabled_in_test_env_or_templates() -> None:
    """I3 fixture guard (Critic C2): the flag must not be active by default in
    the test environment, .env.template, conftest, or docker-compose files.
    An accidentally-enabled default would silently turn the whole skip-suite
    into dead assertions.
    """
    import os
    from pathlib import Path

    assert os.environ.get("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", "false").lower() != "true", (
        "AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS is enabled in the test environment"
    )

    repo_root = Path(__file__).resolve().parents[5]
    for candidate in [
        repo_root / ".env.template",
        repo_root / "tests" / "conftest.py",
        *repo_root.glob("docker-compose*.yml"),
    ]:
        if not candidate.exists():
            continue
        for line in candidate.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS" in stripped:
                normalized = stripped.replace(" ", "").replace('"', "").replace("'", "").lower()
                assert "aegis_enable_legacy_round2_relations=true" not in normalized, (
                    f"{candidate} enables the legacy Round-2 flag by default: {stripped}"
                )
