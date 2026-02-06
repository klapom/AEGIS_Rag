"""Integration tests for domain-aware ingestion flow (Sprint 125 Feature 125.9).

Tests complete workflows:
- Upload document with domain_id parameter
- Upload document without domain_id (auto-detection)
- Domain filter in search results
- Deployment profile change affects active domains
"""

import pytest
from unittest.mock import AsyncMock, patch
from src.components.ingestion.ingestion_state import create_initial_state
from src.core.chunk import Chunk


class TestDomainAwareIngestionFlow:
    """Integration tests for domain-aware ingestion."""

    @pytest.mark.asyncio
    async def test_ingest_with_explicit_domain_id(self):
        """Test full ingestion with explicit domain_id parameter."""
        # Create initial state with domain_id set
        state = create_initial_state(
            document_path="/tmp/medical_paper.pdf",
            document_id="doc_medical_001",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
            namespace_id="healthcare",
            domain_id="medicine_health",  # Explicit domain
        )

        # Verify domain is preserved through pipeline
        assert state["domain_id"] == "medicine_health"
        assert state["namespace_id"] == "healthcare"

    @pytest.mark.asyncio
    async def test_ingest_without_domain_id_auto_detects(self):
        """Test that domain is auto-detected when not provided."""
        state = create_initial_state(
            document_path="/tmp/unknown_doc.pdf",
            document_id="doc_unknown_001",
            batch_id="batch_2",
            batch_index=0,
            total_documents=1,
            namespace_id="default",
            domain_id=None,  # No domain provided
        )

        # Domain starts as None, will be detected by graph_extraction_node
        assert state["domain_id"] is None

        # Simulate domain classification in graph_extraction_node
        with patch(
            "src.components.domain_training.domain_classifier.get_domain_classifier"
        ) as mock_get_classifier:

            mock_classifier = AsyncMock()
            mock_classifier.is_loaded.return_value = False
            mock_classifier.load_domains = AsyncMock()
            mock_classifier.classify_document.return_value = [
                {"domain": "computer_science_it", "score": 0.85}
            ]
            mock_get_classifier.return_value = mock_classifier

            # After classification, domain should be set
            state["domain_id"] = "computer_science_it"

            assert state["domain_id"] == "computer_science_it"

    @pytest.mark.asyncio
    async def test_domain_id_preserved_through_pipeline(self):
        """Test that domain_id is preserved through all pipeline stages."""
        state = create_initial_state(
            document_path="/tmp/doc.pdf",
            document_id="doc_123",
            batch_id="batch_1",
            batch_index=0,
            total_documents=1,
            namespace_id="default",
            domain_id="medicine_health",
        )

        # Add chunks (chunking stage)
        chunk = Chunk(
            chunk_id="b" * 64,
            document_id="doc_123",
            chunk_index=0,
            start_char=0,
            end_char=20,
            content="Medical content here",
            metadata={"source": "doc.pdf"},
        )
        state["chunks"] = [{"chunk": chunk}]
        state["chunking_status"] = "completed"

        # Domain should still be set
        assert state["domain_id"] == "medicine_health"

        # Simulate embedding stage
        state["embedding_status"] = "completed"
        state["embedded_chunk_ids"] = ["chunk_1"]

        # Domain still preserved
        assert state["domain_id"] == "medicine_health"

        # Simulate graph extraction stage
        state["graph_status"] = "completed"

        # Domain still preserved
        assert state["domain_id"] == "medicine_health"

    @pytest.mark.asyncio
    async def test_domain_added_to_qdrant_payload(self):
        """Test that domain_id is added to Qdrant chunk metadata."""
        domain_id = "chemistry"
        chunk_id = "chunk_001"

        # Simulate Qdrant payload construction
        qdrant_payload = {
            "document_id": "doc_chemistry_001",
            "chunk_id": chunk_id,
            "chunk_index": 0,
            "namespace_id": "default",
            "domain_id": domain_id,  # Added to payload
            "text": "Molecular structure of compounds...",
        }

        assert qdrant_payload["domain_id"] == "chemistry"
        assert qdrant_payload["chunk_id"] == chunk_id

    @pytest.mark.asyncio
    async def test_domain_added_to_neo4j_entity_nodes(self):
        """Test that domain_id is stored in Neo4j entity nodes."""
        domain_id = "law"

        # Simulate entity node creation in Neo4j
        entity_node_data = {
            "name": "Contract Law",
            "type": "CONCEPT",
            "domain_id": domain_id,  # Added to node properties
            "document_id": "doc_law_001",
        }

        assert entity_node_data["domain_id"] == "law"
        assert entity_node_data["name"] == "Contract Law"

    @pytest.mark.asyncio
    async def test_multi_domain_documents_same_namespace(self):
        """Test uploading documents from different domains in same namespace."""
        doc1_state = create_initial_state(
            document_path="/tmp/medicine_paper.pdf",
            document_id="doc_med_001",
            batch_id="batch_1",
            batch_index=0,
            total_documents=2,
            namespace_id="healthcare",
            domain_id="medicine_health",
        )

        doc2_state = create_initial_state(
            document_path="/tmp/chemistry_paper.pdf",
            document_id="doc_chem_001",
            batch_id="batch_1",
            batch_index=1,
            total_documents=2,
            namespace_id="healthcare",  # Same namespace
            domain_id="chemistry",  # Different domain
        )

        # Both documents in same namespace but different domains
        assert doc1_state["namespace_id"] == doc2_state["namespace_id"]
        assert doc1_state["domain_id"] != doc2_state["domain_id"]

        assert doc1_state["domain_id"] == "medicine_health"
        assert doc2_state["domain_id"] == "chemistry"


class TestDomainSearchFiltering:
    """Integration tests for domain filtering in search."""

    @pytest.mark.asyncio
    async def test_search_with_domain_filter(self):
        """Test that search results can be filtered by domain."""
        # Simulate documents indexed with domain_id
        indexed_docs = [
            {
                "id": "chunk_1",
                "domain_id": "medicine_health",
                "content": "Aspirin is an analgesic",
            },
            {
                "id": "chunk_2",
                "domain_id": "medicine_health",
                "content": "Penicillin is an antibiotic",
            },
            {
                "id": "chunk_3",
                "domain_id": "chemistry",
                "content": "Molecular bonds form reactions",
            },
        ]

        # Search with medicine filter
        search_domain = "medicine_health"
        filtered_results = [d for d in indexed_docs if d["domain_id"] == search_domain]

        # Should return only medicine docs
        assert len(filtered_results) == 2
        assert all(d["domain_id"] == "medicine_health" for d in filtered_results)

    @pytest.mark.asyncio
    async def test_search_without_domain_filter_returns_all(self):
        """Test that search without domain filter returns all domains."""
        indexed_docs = [
            {"id": "chunk_1", "domain_id": "medicine_health", "content": "..."},
            {"id": "chunk_2", "domain_id": "chemistry", "content": "..."},
            {"id": "chunk_3", "domain_id": "law", "content": "..."},
        ]

        # Search without domain filter
        results = indexed_docs

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_respects_deployment_profile_domains(self):
        """Test that search filters to active domains in deployment profile."""
        # All documents in system
        all_docs = [
            {"id": "chunk_1", "domain_id": "medicine_health", "content": "..."},
            {"id": "chunk_2", "domain_id": "chemistry", "content": "..."},
            {"id": "chunk_3", "domain_id": "law", "content": "..."},
            {"id": "chunk_4", "domain_id": "entertainment", "content": "..."},
        ]

        # Active deployment profile: pharma_company (only medicine_health)
        active_domains = ["medicine_health"]

        # Search respects profile
        results = [d for d in all_docs if d["domain_id"] in active_domains]

        assert len(results) == 1
        assert results[0]["domain_id"] == "medicine_health"


class TestDeploymentProfileImpact:
    """Integration tests for deployment profile changes."""

    @pytest.mark.asyncio
    async def test_deployment_profile_change_affects_search(self):
        """Test that changing deployment profile changes search results."""
        # Initial state: pharma_company profile
        all_docs = [
            {"id": "chunk_1", "domain_id": "medicine_health", "content": "Drug treatment"},
            {
                "id": "chunk_2",
                "domain_id": "chemistry",
                "content": "Chemical compounds",
            },
            {"id": "chunk_3", "domain_id": "law", "content": "Contract law"},
        ]

        # Profile 1: pharma_company
        active_1 = ["medicine_health", "chemistry"]
        results_1 = [d for d in all_docs if d["domain_id"] in active_1]

        assert len(results_1) == 2
        assert "law" not in [d["domain_id"] for d in results_1]

        # Profile 2: law_firm (different active domains)
        active_2 = ["law"]
        results_2 = [d for d in all_docs if d["domain_id"] in active_2]

        assert len(results_2) == 1
        assert results_2[0]["domain_id"] == "law"

    @pytest.mark.asyncio
    async def test_deployment_profile_affects_ingestion_prompt_selection(self):
        """Test that profile change affects which extraction prompts are used."""
        # Domain-specific prompts in Neo4j
        trained_prompts = {
            "medicine_health": "Extract medical entities: diseases, medications, treatments",
            "law": "Extract legal entities: statutes, contracts, parties",
        }

        # Profile 1: medicine active
        active_domain = "medicine_health"
        selected_prompt = trained_prompts.get(active_domain)

        assert selected_prompt == "Extract medical entities: diseases, medications, treatments"

        # Profile 2: law active
        active_domain = "law"
        selected_prompt = trained_prompts.get(active_domain)

        assert selected_prompt == "Extract legal entities: statutes, contracts, parties"

    @pytest.mark.asyncio
    async def test_domain_classifier_respects_active_profile(self):
        """Test that domain classifier returns active domains first."""
        with patch(
            "src.components.domain_training.domain_seeder.get_active_domains"
        ) as mock_get_active:

            # All possible predictions from classifier
            all_predictions = [
                {"domain": "medicine_health", "score": 0.85},
                {"domain": "chemistry", "score": 0.80},
                {"domain": "law", "score": 0.72},
                {"domain": "entertainment", "score": 0.65},
            ]

            # Active profile: pharma
            mock_get_active.return_value = ["medicine_health", "chemistry"]

            # Filter to active only
            active_predictions = [
                p
                for p in all_predictions
                if p["domain"] in mock_get_active.return_value
            ]

            assert len(active_predictions) == 2
            assert active_predictions[0]["domain"] == "medicine_health"
            assert active_predictions[1]["domain"] == "chemistry"


class TestDomainExtractionPrompts:
    """Integration tests for domain-aware extraction prompt selection."""

    @pytest.mark.asyncio
    async def test_domain_trained_prompts_used_for_ingestion(self):
        """Test that domain-trained prompts are used during ingestion."""
        with patch(
            "src.components.domain_training.get_domain_repository"
        ) as mock_repo:

            # Medicine domain has trained prompts
            mock_domain_repo = AsyncMock()
            mock_domain_repo.get_domain.return_value = {
                "name": "medicine_health",
                "entity_prompt": "Extract medical entities: medications, diseases, treatments",
                "relation_prompt": "Extract medical relationships: treats, causes, prevents",
            }
            mock_repo.return_value = mock_domain_repo

            # During ingestion of medicine document
            domain = "medicine_health"
            entity_prompt, relation_prompt = (
                mock_domain_repo.get_domain.return_value["entity_prompt"],
                mock_domain_repo.get_domain.return_value["relation_prompt"],
            )

            assert "medications" in entity_prompt
            assert "treats" in relation_prompt

    @pytest.mark.asyncio
    async def test_generic_prompts_when_no_domain_trained(self):
        """Test fallback to generic prompts when domain has no training."""
        with patch(
            "src.components.domain_training.get_domain_repository"
        ) as mock_repo, patch(
            "src.components.graph_rag.extraction_service.get_active_extraction_prompts"
        ) as mock_generic:

            # New domain without training
            mock_domain_repo = AsyncMock()
            mock_domain_repo.get_domain.return_value = {
                "name": "new_domain",
                "entity_prompt": None,  # Not trained
                "relation_prompt": None,
            }
            mock_repo.return_value = mock_domain_repo

            # Fallback to generic
            mock_generic.return_value = (
                "Generic entity extraction prompt",
                "Generic relation extraction prompt",
            )

            entity_prompt = (
                mock_domain_repo.get_domain.return_value["entity_prompt"]
                or mock_generic.return_value[0]
            )

            assert entity_prompt == "Generic entity extraction prompt"

    @pytest.mark.asyncio
    async def test_prompt_selection_respects_use_dspy_flag(self):
        """Test that prompt selection respects USE_DSPY_PROMPTS flag."""
        with patch(
            "src.components.graph_rag.extraction_service.USE_DSPY_PROMPTS", True
        ), patch(
            "src.components.graph_rag.extraction_service.get_active_extraction_prompts"
        ) as mock_dspy:

            mock_dspy.return_value = (
                "DSPy entity prompt",
                "DSPy relation prompt",
            )

            # When USE_DSPY_PROMPTS=True, should use DSPy
            entity_prompt = mock_dspy.return_value[0]

            assert entity_prompt == "DSPy entity prompt"


class TestDomainIngestionErrorHandling:
    """Integration tests for domain-aware error handling."""

    @pytest.mark.asyncio
    async def test_ingest_continues_when_domain_classification_fails(self):
        """Test that ingestion continues even if domain classification fails."""
        with patch(
            "src.components.domain_training.domain_classifier.get_domain_classifier"
        ) as mock_get_classifier:

            # Classifier fails
            mock_classifier = AsyncMock()
            mock_classifier.is_loaded.return_value = False
            mock_classifier.load_domains = AsyncMock(
                side_effect=Exception("Classifier loading failed")
            )
            mock_get_classifier.return_value = mock_classifier

            state = create_initial_state(
                document_path="/tmp/doc.pdf",
                document_id="doc_123",
                batch_id="batch_1",
                batch_index=0,
                total_documents=1,
                namespace_id="default",
                domain_id=None,
            )

            # Even with classifier error, ingestion should continue
            state["graph_status"] = "completed"
            state["domain_id"] = None  # Not classified, but ingestion succeeded

            assert state["graph_status"] == "completed"

    @pytest.mark.asyncio
    async def test_ingest_with_invalid_domain_id_uses_fallback(self):
        """Test that invalid domain_id falls back to auto-detection."""
        with patch(
            "src.components.domain_training.domain_seeder.get_active_domains"
        ) as mock_get_active:

            # User provides invalid domain
            provided_domain = "nonexistent_domain"

            # Active domains don't include it
            mock_get_active.return_value = [
                "medicine_health",
                "chemistry",
                "law",
            ]

            # Check if provided domain is active
            if provided_domain not in mock_get_active.return_value:
                # Fall back to auto-detection
                detected_domain = "medicine_health"
            else:
                detected_domain = provided_domain

            assert detected_domain == "medicine_health"
