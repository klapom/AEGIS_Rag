"""Unit tests for domain classification in graph_extraction_node.

Sprint 125 Feature 125.7: Domain-Aware Extraction Pipeline

Tests:
- Auto-classification when domain_id not set
- Skip classification when domain_id provided
- Fallback to generic prompts when classification fails
- Active domains filter
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.components.ingestion.ingestion_state import create_initial_state
from src.components.ingestion.nodes.graph_extraction import graph_extraction_node
from src.core.chunk import Chunk


@pytest.fixture
def sample_state():
    """Create sample ingestion state with chunks."""
    state = create_initial_state(
        document_path="/tmp/test.pdf",
        document_id="doc_123",
        batch_id="batch_1",
        batch_index=0,
        total_documents=1,
        namespace_id="default",
        domain_id=None,  # No domain set
    )

    # Add sample chunks with all required Pydantic fields
    chunk = Chunk(
        chunk_id="a" * 64,
        document_id="doc_123",
        chunk_index=0,
        start_char=0,
        end_char=75,
        content="This is a computer science research paper about machine learning algorithms.",
        metadata={"source": "test.pdf"},
    )
    state["chunks"] = [{"chunk": chunk}]
    state["chunking_status"] = "completed"
    state["embedding_status"] = "completed"
    state["embedded_chunk_ids"] = ["chunk_1"]

    return state


@pytest.mark.asyncio
async def test_domain_classification_auto_when_not_set(sample_state):
    """Test that domain is auto-classified when not set in state."""
    # Mock dependencies
    with patch(
        "src.components.domain_training.domain_classifier.get_domain_classifier"
    ) as mock_get_classifier, patch(
        "src.components.domain_training.domain_seeder.get_active_domains"
    ) as mock_get_active, patch(
        "src.components.ingestion.nodes.graph_extraction.get_lightrag_wrapper_async"
    ) as mock_lightrag:

        # Setup classifier mock
        mock_classifier = MagicMock()
        mock_classifier.is_loaded.return_value = False
        mock_classifier.load_domains = AsyncMock()
        mock_classifier.classify_document.return_value = [
            {"domain": "computer_science_it", "score": 0.85}
        ]
        mock_get_classifier.return_value = mock_classifier

        # Setup active domains mock
        mock_get_active.return_value = [
            "computer_science_it",
            "medicine_health",
            "entertainment",
        ]

        # Setup LightRAG mock
        mock_lightrag_instance = AsyncMock()
        mock_lightrag_instance.insert_prechunked_documents = AsyncMock(
            return_value={"stats": {"total_entities": 5, "total_relations": 3}}
        )
        mock_lightrag_instance._store_relations_to_neo4j = AsyncMock(return_value=2)
        mock_lightrag.return_value = mock_lightrag_instance

        # Mock Neo4j client for chunk queries
        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client"
        ) as mock_neo4j:
            mock_neo4j_client = AsyncMock()
            mock_neo4j_client.execute_read = AsyncMock(return_value=[])
            mock_neo4j_client.create_section_nodes = AsyncMock(
                return_value={
                    "sections_created": 0,
                    "has_section_rels": 0,
                    "contains_chunk_rels": 0,
                    "defines_entity_rels": 0,
                }
            )
            mock_neo4j.return_value = mock_neo4j_client

            # Mock community detector
            with patch(
                "src.components.ingestion.nodes.graph_extraction.get_community_detector"
            ) as mock_community:
                mock_detector = AsyncMock()
                mock_detector.detect_communities = AsyncMock(return_value=[])
                mock_community.return_value = mock_detector

                # Execute node
                result_state = await graph_extraction_node(sample_state)

                # Assertions
                assert result_state["domain_id"] == "computer_science_it"
                assert result_state["graph_status"] == "completed"

                # Verify classifier was called
                mock_classifier.load_domains.assert_called_once()
                mock_classifier.classify_document.assert_called_once()

                # Verify classification was logged
                assert mock_get_active.called


@pytest.mark.asyncio
async def test_domain_classification_skip_when_provided(sample_state):
    """Test that classification is skipped when domain_id already set."""
    # Set domain in state
    sample_state["domain_id"] = "entertainment"

    with patch(
        "src.components.domain_training.domain_classifier.get_domain_classifier"
    ) as mock_get_classifier, patch(
        "src.components.ingestion.nodes.graph_extraction.get_lightrag_wrapper_async"
    ) as mock_lightrag:

        mock_lightrag_instance = AsyncMock()
        mock_lightrag_instance.insert_prechunked_documents = AsyncMock(
            return_value={"stats": {"total_entities": 5, "total_relations": 3}}
        )
        mock_lightrag.return_value = mock_lightrag_instance

        # Mock Neo4j client
        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client"
        ) as mock_neo4j:
            mock_neo4j_client = AsyncMock()
            mock_neo4j_client.execute_read = AsyncMock(return_value=[])
            mock_neo4j_client.create_section_nodes = AsyncMock(
                return_value={
                    "sections_created": 0,
                    "has_section_rels": 0,
                    "contains_chunk_rels": 0,
                    "defines_entity_rels": 0,
                }
            )
            mock_neo4j.return_value = mock_neo4j_client

            # Mock community detector
            with patch(
                "src.components.ingestion.nodes.graph_extraction.get_community_detector"
            ) as mock_community:
                mock_detector = AsyncMock()
                mock_detector.detect_communities = AsyncMock(return_value=[])
                mock_community.return_value = mock_detector

                # Execute node
                result_state = await graph_extraction_node(sample_state)

                # Assertions
                assert result_state["domain_id"] == "entertainment"
                assert result_state["graph_status"] == "completed"

                # Verify classifier was NOT called
                mock_get_classifier.assert_not_called()


@pytest.mark.asyncio
async def test_domain_classification_fallback_on_error(sample_state):
    """Test that extraction continues when classification fails."""
    with patch(
        "src.components.domain_training.domain_classifier.get_domain_classifier"
    ) as mock_get_classifier, patch(
        "src.components.ingestion.nodes.graph_extraction.get_lightrag_wrapper_async"
    ) as mock_lightrag:

        # Setup classifier to raise error
        mock_classifier = MagicMock()
        mock_classifier.is_loaded.return_value = False
        mock_classifier.load_domains = AsyncMock(side_effect=Exception("Classifier error"))
        mock_get_classifier.return_value = mock_classifier

        # Setup LightRAG mock
        mock_lightrag_instance = AsyncMock()
        mock_lightrag_instance.insert_prechunked_documents = AsyncMock(
            return_value={"stats": {"total_entities": 5, "total_relations": 3}}
        )
        mock_lightrag.return_value = mock_lightrag_instance

        # Mock Neo4j client
        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client"
        ) as mock_neo4j:
            mock_neo4j_client = AsyncMock()
            mock_neo4j_client.execute_read = AsyncMock(return_value=[])
            mock_neo4j_client.create_section_nodes = AsyncMock(
                return_value={
                    "sections_created": 0,
                    "has_section_rels": 0,
                    "contains_chunk_rels": 0,
                    "defines_entity_rels": 0,
                }
            )
            mock_neo4j.return_value = mock_neo4j_client

            # Mock community detector
            with patch(
                "src.components.ingestion.nodes.graph_extraction.get_community_detector"
            ) as mock_community:
                mock_detector = AsyncMock()
                mock_detector.detect_communities = AsyncMock(return_value=[])
                mock_community.return_value = mock_detector

                # Execute node (should not raise)
                result_state = await graph_extraction_node(sample_state)

                # Assertions
                assert result_state["domain_id"] is None  # Not set due to error
                assert result_state["graph_status"] == "completed"  # Still completes


@pytest.mark.asyncio
async def test_domain_classification_inactive_domain_skipped(sample_state):
    """Test that inactive domains are not used."""
    with patch(
        "src.components.domain_training.domain_classifier.get_domain_classifier"
    ) as mock_get_classifier, patch(
        "src.components.domain_training.domain_seeder.get_active_domains"
    ) as mock_get_active, patch(
        "src.components.ingestion.nodes.graph_extraction.get_lightrag_wrapper_async"
    ) as mock_lightrag:

        # Setup classifier to return inactive domain
        mock_classifier = MagicMock()
        mock_classifier.is_loaded.return_value = False
        mock_classifier.load_domains = AsyncMock()
        mock_classifier.classify_document.return_value = [
            {"domain": "chemistry", "score": 0.85}  # Not in active domains
        ]
        mock_get_classifier.return_value = mock_classifier

        # Setup active domains (chemistry NOT included)
        mock_get_active.return_value = ["computer_science_it", "medicine_health"]

        # Setup LightRAG mock
        mock_lightrag_instance = AsyncMock()
        mock_lightrag_instance.insert_prechunked_documents = AsyncMock(
            return_value={"stats": {"total_entities": 5, "total_relations": 3}}
        )
        mock_lightrag.return_value = mock_lightrag_instance

        # Mock Neo4j client
        with patch(
            "src.components.graph_rag.neo4j_client.get_neo4j_client"
        ) as mock_neo4j:
            mock_neo4j_client = AsyncMock()
            mock_neo4j_client.execute_read = AsyncMock(return_value=[])
            mock_neo4j_client.create_section_nodes = AsyncMock(
                return_value={
                    "sections_created": 0,
                    "has_section_rels": 0,
                    "contains_chunk_rels": 0,
                    "defines_entity_rels": 0,
                }
            )
            mock_neo4j.return_value = mock_neo4j_client

            # Mock community detector
            with patch(
                "src.components.ingestion.nodes.graph_extraction.get_community_detector"
            ) as mock_community:
                mock_detector = AsyncMock()
                mock_detector.detect_communities = AsyncMock(return_value=[])
                mock_community.return_value = mock_detector

                # Execute node
                result_state = await graph_extraction_node(sample_state)

                # Assertions
                assert result_state["domain_id"] is None  # Not set because inactive
                assert result_state["graph_status"] == "completed"
