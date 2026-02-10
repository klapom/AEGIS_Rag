"""Unit tests for Sprint 129.2: Metadata Artifact Filtering.

Tests the filter_metadata_artifacts() function in extraction_pipeline.py.
"""

import pytest

from src.components.graph_rag.extraction_pipeline import (
    ENTITY_BLOCKLIST,
    filter_metadata_artifacts,
)


class TestEntityBlocklist:
    """Test the default blocklist configuration."""

    def test_blocklist_contains_known_artifacts(self):
        """Known document structure tokens should be in the blocklist."""
        expected = {"clean_text", "doc type", "document", "chunk", "text", "content", "file"}
        assert expected.issubset(ENTITY_BLOCKLIST)

    def test_blocklist_is_lowercase(self):
        """All entries in the blocklist should be lowercase."""
        for entry in ENTITY_BLOCKLIST:
            assert entry == entry.lower(), f"Blocklist entry '{entry}' is not lowercase"


class TestFilterMetadataArtifacts:
    """Test the filter_metadata_artifacts function."""

    def test_filters_blocklisted_entities(self):
        """Entities with blocklisted names should be removed."""
        entities = [
            {"name": "clean_text", "type": "CONCEPT"},
            {"name": "Albert Einstein", "type": "PERSON"},
            {"name": "Document", "type": "CONCEPT"},
        ]
        relations = []

        filtered_entities, filtered_relations, ent_removed, rel_removed = filter_metadata_artifacts(
            entities, relations
        )

        assert len(filtered_entities) == 1
        assert filtered_entities[0]["name"] == "Albert Einstein"
        assert ent_removed == 2

    def test_case_insensitive_matching(self):
        """Filtering should be case-insensitive."""
        entities = [
            {"name": "CLEAN_TEXT", "type": "CONCEPT"},
            {"name": "Doc Type", "type": "CONCEPT"},
            {"name": "DOCUMENT", "type": "CONCEPT"},
            {"name": "Python", "type": "PROGRAMMING_LANGUAGE"},
        ]
        relations = []

        filtered_entities, _, ent_removed, _ = filter_metadata_artifacts(entities, relations)

        assert len(filtered_entities) == 1
        assert filtered_entities[0]["name"] == "Python"
        assert ent_removed == 3

    def test_preserves_domain_entities(self):
        """Domain-specific entities should NOT be filtered."""
        entities = [
            {"name": "TensorFlow", "type": "SOFTWARE"},
            {"name": "Google Brain", "type": "ORGANIZATION"},
            {"name": "CUDA", "type": "TECHNOLOGY"},
        ]
        relations = []

        filtered_entities, _, ent_removed, _ = filter_metadata_artifacts(entities, relations)

        assert len(filtered_entities) == 3
        assert ent_removed == 0

    def test_filters_relations_with_both_artifact_endpoints(self):
        """Relations where BOTH subject and object are artifacts should be removed."""
        entities = []
        relations = [
            {"subject": "clean_text", "object": "Document", "predicate": "PART_OF"},
            {"subject": "Albert Einstein", "object": "Physics", "predicate": "STUDIES"},
            {"subject": "clean_text", "object": "Physics", "predicate": "MENTIONS"},
        ]

        _, filtered_relations, _, rel_removed = filter_metadata_artifacts(entities, relations)

        # Only the first relation (both endpoints are artifacts) should be removed
        assert len(filtered_relations) == 2
        assert rel_removed == 1

    def test_preserves_relations_with_one_real_endpoint(self):
        """Relations with at least one non-artifact endpoint should be preserved."""
        entities = []
        relations = [
            {"subject": "clean_text", "object": "Einstein", "predicate": "MENTIONS"},
            {"source": "Einstein", "target": "Physics", "type": "STUDIES"},
        ]

        _, filtered_relations, _, rel_removed = filter_metadata_artifacts(entities, relations)

        assert len(filtered_relations) == 2
        assert rel_removed == 0

    def test_handles_entity_name_key_variants(self):
        """Should handle both 'name' and 'entity_name' keys."""
        entities = [
            {"entity_name": "clean_text", "entity_type": "CONCEPT"},
            {"entity_name": "Einstein", "entity_type": "PERSON"},
        ]
        relations = []

        filtered_entities, _, ent_removed, _ = filter_metadata_artifacts(entities, relations)

        assert len(filtered_entities) == 1
        assert filtered_entities[0]["entity_name"] == "Einstein"

    def test_handles_relation_key_variants(self):
        """Should handle both subject/object and source/target keys."""
        entities = []
        relations = [
            {"source": "Document", "target": "chunk", "type": "CONTAINS"},
            {"source": "Einstein", "target": "Physics", "type": "STUDIES"},
        ]

        _, filtered_relations, _, rel_removed = filter_metadata_artifacts(entities, relations)

        assert len(filtered_relations) == 1
        assert rel_removed == 1

    def test_empty_inputs(self):
        """Empty entity and relation lists should be handled gracefully."""
        filtered_entities, filtered_relations, ent_removed, rel_removed = filter_metadata_artifacts(
            [], []
        )

        assert filtered_entities == []
        assert filtered_relations == []
        assert ent_removed == 0
        assert rel_removed == 0

    def test_custom_blocklist(self):
        """Custom blocklist should override the default."""
        entities = [
            {"name": "RAGAS Phase 1 Benchmark", "type": "CONCEPT"},
            {"name": "Einstein", "type": "PERSON"},
        ]
        relations = []
        custom_blocklist = {"ragas phase 1 benchmark"}

        filtered_entities, _, ent_removed, _ = filter_metadata_artifacts(
            entities, relations, blocklist=custom_blocklist
        )

        assert len(filtered_entities) == 1
        assert filtered_entities[0]["name"] == "Einstein"

    def test_empty_blocklist_passes_everything(self):
        """An empty blocklist should not filter anything."""
        entities = [
            {"name": "clean_text", "type": "CONCEPT"},
            {"name": "Document", "type": "CONCEPT"},
        ]
        relations = []

        filtered_entities, _, ent_removed, _ = filter_metadata_artifacts(
            entities, relations, blocklist=set()
        )

        assert len(filtered_entities) == 2
        assert ent_removed == 0

    def test_whitespace_handling(self):
        """Entity names with whitespace should be stripped before matching."""
        entities = [
            {"name": "  clean_text  ", "type": "CONCEPT"},
            {"name": " Document ", "type": "CONCEPT"},
            {"name": "  Einstein  ", "type": "PERSON"},
        ]
        relations = []

        filtered_entities, _, ent_removed, _ = filter_metadata_artifacts(entities, relations)

        assert len(filtered_entities) == 1
        assert ent_removed == 2
