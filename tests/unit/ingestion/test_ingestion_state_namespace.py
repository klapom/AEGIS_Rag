"""Unit tests for IngestionState namespace and domain support.

Sprint 76 Feature 76.1 (TD-084): Namespace isolation
Sprint 76 Feature 76.2 (TD-085): DSPy domain integration
"""

import pytest

from src.components.ingestion.ingestion_state import create_initial_state


class TestIngestionStateNamespace:
    """Test namespace and domain field support in IngestionState."""

    def test_create_initial_state_with_default_namespace(self):
        """Test that default namespace is 'default' when not specified."""
        state = create_initial_state(
            document_path="/data/test.pdf",
            document_id="doc_001",
            batch_id="batch_001",
            batch_index=0,
            total_documents=1,
        )

        assert state["namespace_id"] == "default"
        assert state["domain_id"] is None

    def test_create_initial_state_with_custom_namespace(self):
        """Test that custom namespace is correctly set."""
        state = create_initial_state(
            document_path="/data/test.pdf",
            document_id="doc_001",
            batch_id="batch_001",
            batch_index=0,
            total_documents=1,
            namespace_id="ragas_eval",
        )

        assert state["namespace_id"] == "ragas_eval"
        assert state["domain_id"] is None

    def test_create_initial_state_with_domain(self):
        """Test that domain_id is correctly set when provided."""
        state = create_initial_state(
            document_path="/data/test.pdf",
            document_id="doc_001",
            batch_id="batch_001",
            batch_index=0,
            total_documents=1,
            namespace_id="medical",
            domain_id="medical_reports",
        )

        assert state["namespace_id"] == "medical"
        assert state["domain_id"] == "medical_reports"

    def test_create_initial_state_with_domain_no_namespace(self):
        """Test that domain can be set with default namespace."""
        state = create_initial_state(
            document_path="/data/test.pdf",
            document_id="doc_001",
            batch_id="batch_001",
            batch_index=0,
            total_documents=1,
            domain_id="tech_docs",
        )

        assert state["namespace_id"] == "default"
        assert state["domain_id"] == "tech_docs"

    @pytest.mark.parametrize(
        "namespace_id,domain_id,expected_namespace,expected_domain",
        [
            ("default", None, "default", None),
            ("ragas_eval", None, "ragas_eval", None),
            ("medical", "medical_reports", "medical", "medical_reports"),
            ("default", "tech_docs", "default", "tech_docs"),
            ("project_a", "legal_contracts", "project_a", "legal_contracts"),
        ],
    )
    def test_namespace_domain_combinations(
        self, namespace_id, domain_id, expected_namespace, expected_domain
    ):
        """Test various combinations of namespace and domain."""
        state = create_initial_state(
            document_path="/data/test.pdf",
            document_id="doc_001",
            batch_id="batch_001",
            batch_index=0,
            total_documents=1,
            namespace_id=namespace_id,
            domain_id=domain_id,
        )

        assert state["namespace_id"] == expected_namespace
        assert state["domain_id"] == expected_domain

    def test_state_fields_are_accessible(self):
        """Test that namespace and domain fields are accessible via get()."""
        state = create_initial_state(
            document_path="/data/test.pdf",
            document_id="doc_001",
            batch_id="batch_001",
            batch_index=0,
            total_documents=1,
            namespace_id="test_ns",
            domain_id="test_domain",
        )

        # Using .get() method (common pattern in nodes)
        assert state.get("namespace_id") == "test_ns"
        assert state.get("domain_id") == "test_domain"
        assert state.get("namespace_id", "default") == "test_ns"
        assert state.get("domain_id", None) == "test_domain"

    def test_backward_compatibility_no_namespace_param(self):
        """Test backward compatibility: old code without namespace still works."""
        # This simulates old code that doesn't know about namespace parameter
        state = create_initial_state(
            document_path="/data/test.pdf",
            document_id="doc_001",
            batch_id="batch_001",
            batch_index=0,
            total_documents=1,
            # Not passing namespace_id or domain_id
        )

        # Should still work with defaults
        assert state["namespace_id"] == "default"
        assert state["document_id"] == "doc_001"
        assert state["overall_progress"] == 0.0
