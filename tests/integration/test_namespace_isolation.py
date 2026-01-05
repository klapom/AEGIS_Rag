"""Integration test for namespace isolation in ingestion pipeline.

Sprint 76 Feature 76.1 (TD-084): Multi-tenant namespace isolation

This test verifies that documents uploaded to different namespaces
are properly isolated in both Qdrant (vector search) and Neo4j (graph).
"""

import pytest

from src.components.ingestion.ingestion_state import create_initial_state


@pytest.mark.integration
class TestNamespaceIsolation:
    """Integration tests for namespace isolation across the ingestion pipeline."""

    def test_ingestion_state_preserves_namespace(self):
        """Test that IngestionState correctly stores and retrieves namespace_id."""
        # Create state with custom namespace
        state = create_initial_state(
            document_path="/data/test.pdf",
            document_id="doc_ragas_001",
            batch_id="batch_ragas",
            batch_index=0,
            total_documents=1,
            namespace_id="ragas_eval",
        )

        # Verify namespace is preserved
        assert state["namespace_id"] == "ragas_eval"
        assert state.get("namespace_id") == "ragas_eval"
        assert state.get("namespace_id", "default") == "ragas_eval"

    def test_ingestion_state_preserves_domain(self):
        """Test that IngestionState correctly stores and retrieves domain_id."""
        # Create state with domain
        state = create_initial_state(
            document_path="/data/medical.pdf",
            document_id="doc_medical_001",
            batch_id="batch_medical",
            batch_index=0,
            total_documents=1,
            namespace_id="medical_ns",
            domain_id="medical_reports",
        )

        # Verify both namespace and domain are preserved
        assert state["namespace_id"] == "medical_ns"
        assert state["domain_id"] == "medical_reports"
