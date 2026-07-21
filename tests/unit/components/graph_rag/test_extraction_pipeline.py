"""Unit tests for extract_and_store_entities (ADR-064 G5-Fix 2).

Tests that aggregate_stats reports the *stored* relation count
(post-MERGE, per neo4j_client.store_relations), not the extracted count.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.graph_rag.extraction_pipeline import extract_and_store_entities


@pytest.mark.asyncio
async def test_extraction_pipeline_reports_stored_relation_count():
    """aggregate_stats['total_relations_stored'] must equal the sum of
    neo4j_client.store_relations() returns, not len(all_relations).

    Regression guard for Critic G5-Fix 2: entity-MATCH misses at MERGE time
    mean stored <= extracted, and the API must report the former.
    """
    mock_extractor = MagicMock()
    mock_extractor.extract = AsyncMock(
        return_value=(
            [{"name": "Entity1", "type": "PERSON"}, {"name": "Entity2", "type": "ORGANIZATION"}],
            [
                {
                    "source_entity": "Entity1",
                    "target_entity": "Entity2",
                    "relation_type": "WORKS_FOR",
                },
                {
                    "source_entity": "Entity2",
                    "target_entity": "Entity1",
                    "relation_type": "WORKS_FOR",
                },
            ],
        )
    )

    mock_neo4j_client = AsyncMock()
    mock_neo4j_client.store_chunks_and_provenance = AsyncMock(
        return_value={"mentioned_in_created": 2}
    )
    # Only 1 of the 2 extracted relations is actually stored (MATCH miss at MERGE).
    mock_neo4j_client.store_relations = AsyncMock(return_value=1)

    with (
        patch(
            "src.components.graph_rag.extraction_pipeline.create_extraction_pipeline_from_config",
            return_value=mock_extractor,
        ),
        patch(
            "src.components.graph_rag.extraction_pipeline.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch("src.components.graph_rag.extraction_pipeline.settings") as mock_settings,
    ):
        mock_settings.enable_multi_criteria_dedup = False
        mock_settings.enable_relation_dedup = False
        mock_settings.enable_dspy_training_collection = False
        mock_settings.extraction_llm_model = "test-model"

        result = await extract_and_store_entities(
            chunks=[{"chunk_id": "chunk_001", "text": "Some text", "chunk_index": 0}],
            document_id="doc_123",
        )

    stats = result["stats"]
    assert stats["total_relations"] == 2  # extracted count
    assert stats["total_relations_stored"] == 1  # stored count (post-MERGE)


_TWO_RELATIONS = [
    {"source_entity": "Entity1", "target_entity": "Entity2", "relation_type": "WORKS_FOR"},
    {"source_entity": "Entity2", "target_entity": "Entity1", "relation_type": "WORKS_FOR"},
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("extracted_relations", "store_return", "expected_stored"),
    [
        ([], 0, 0),  # nothing extracted -> nothing stored, store_relations not called
        (_TWO_RELATIONS, 0, 0),  # total MATCH miss at MERGE
        (_TWO_RELATIONS, 1, 1),  # partial store
        (_TWO_RELATIONS, 2, 2),  # full store (stored == extracted)
    ],
)
async def test_extraction_pipeline_stored_bounded_by_extracted(
    extracted_relations: list[dict],
    store_return: int,
    expected_stored: int,
) -> None:
    """Property guard (ADR-064 adversarial): total_relations_stored is always
    the store_relations() sum and never exceeds total_relations. The skip
    branch in graph_extraction_node reports this value to the API, so an
    over-reporting regression here would leak straight into the upload response.
    """
    mock_extractor = MagicMock()
    mock_extractor.extract = AsyncMock(
        return_value=(
            [{"name": "Entity1", "type": "PERSON"}, {"name": "Entity2", "type": "ORGANIZATION"}],
            extracted_relations,
        )
    )

    mock_neo4j_client = AsyncMock()
    mock_neo4j_client.store_chunks_and_provenance = AsyncMock(
        return_value={"mentioned_in_created": 2}
    )
    mock_neo4j_client.store_relations = AsyncMock(return_value=store_return)

    with (
        patch(
            "src.components.graph_rag.extraction_pipeline.create_extraction_pipeline_from_config",
            return_value=mock_extractor,
        ),
        patch(
            "src.components.graph_rag.extraction_pipeline.get_neo4j_client",
            return_value=mock_neo4j_client,
        ),
        patch("src.components.graph_rag.extraction_pipeline.settings") as mock_settings,
    ):
        mock_settings.enable_multi_criteria_dedup = False
        mock_settings.enable_relation_dedup = False
        mock_settings.enable_dspy_training_collection = False
        mock_settings.extraction_llm_model = "test-model"

        result = await extract_and_store_entities(
            chunks=[{"chunk_id": "chunk_001", "text": "Some text", "chunk_index": 0}],
            document_id="doc_123",
        )

    stats = result["stats"]
    assert stats["total_relations"] == len(extracted_relations)
    assert stats["total_relations_stored"] == expected_stored
    assert stats["total_relations_stored"] <= stats["total_relations"]
    if not extracted_relations:
        mock_neo4j_client.store_relations.assert_not_called()
