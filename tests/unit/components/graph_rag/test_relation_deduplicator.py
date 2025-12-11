"""Unit tests for RelationDeduplicator.

Sprint 44 Feature 44.6: TD-063
Tests for relation deduplication including:
- Type synonym resolution
- Entity name normalization
- Bidirectional/symmetric relation handling
- Edge cases

Author: Claude Code
Date: 2025-12-12
"""

import pytest

from src.components.graph_rag.relation_deduplicator import (
    RELATION_TYPE_SYNONYMS,
    SYMMETRIC_RELATIONS,
    RelationDeduplicator,
    create_relation_deduplicator_from_config,
)


class TestRelationDeduplicator:
    """Test suite for RelationDeduplicator class."""

    def test_init_default(self):
        """Test default initialization."""
        dedup = RelationDeduplicator()

        assert dedup.type_synonyms == RELATION_TYPE_SYNONYMS
        assert dedup.symmetric_relations == SYMMETRIC_RELATIONS
        assert dedup.preserve_original_type is False

    def test_init_custom_synonyms(self):
        """Test initialization with custom synonyms."""
        custom_synonyms = {"WORKS_AT": ["EMPLOYED_BY", "STAFF_OF"]}
        dedup = RelationDeduplicator(type_synonyms=custom_synonyms)

        assert dedup.type_synonyms == custom_synonyms
        assert dedup.normalize_relation_type("EMPLOYED_BY") == "WORKS_AT"

    def test_init_custom_symmetric(self):
        """Test initialization with custom symmetric relations."""
        custom_symmetric = {"LOVES", "HATES"}
        dedup = RelationDeduplicator(symmetric_relations=custom_symmetric)

        assert dedup.symmetric_relations == custom_symmetric


class TestNormalizeRelationType:
    """Tests for relation type normalization."""

    @pytest.fixture
    def dedup(self):
        return RelationDeduplicator()

    def test_canonical_type_unchanged(self, dedup):
        """Canonical types should be returned as-is."""
        assert dedup.normalize_relation_type("ACTED_IN") == "ACTED_IN"
        assert dedup.normalize_relation_type("DIRECTED") == "DIRECTED"
        assert dedup.normalize_relation_type("MARRIED_TO") == "MARRIED_TO"

    def test_synonym_normalized(self, dedup):
        """Synonyms should be normalized to canonical form."""
        # Acting synonyms
        assert dedup.normalize_relation_type("STARRED_IN") == "ACTED_IN"
        assert dedup.normalize_relation_type("PLAYED_IN") == "ACTED_IN"
        assert dedup.normalize_relation_type("APPEARED_IN") == "ACTED_IN"
        assert dedup.normalize_relation_type("PERFORMED_IN") == "ACTED_IN"

        # Writing synonyms
        assert dedup.normalize_relation_type("WROTE") == "WRITTEN_BY"
        assert dedup.normalize_relation_type("AUTHORED") == "WRITTEN_BY"

        # Marriage synonyms
        assert dedup.normalize_relation_type("SPOUSE_OF") == "MARRIED_TO"
        assert dedup.normalize_relation_type("HUSBAND_OF") == "MARRIED_TO"
        assert dedup.normalize_relation_type("WIFE_OF") == "MARRIED_TO"

    def test_case_insensitive(self, dedup):
        """Type normalization should be case-insensitive."""
        assert dedup.normalize_relation_type("starred_in") == "ACTED_IN"
        assert dedup.normalize_relation_type("Starred_In") == "ACTED_IN"
        assert dedup.normalize_relation_type("STARRED_IN") == "ACTED_IN"

    def test_space_to_underscore(self, dedup):
        """Spaces should be converted to underscores."""
        assert dedup.normalize_relation_type("STARRED IN") == "ACTED_IN"
        assert dedup.normalize_relation_type("married to") == "MARRIED_TO"

    def test_unknown_type_unchanged(self, dedup):
        """Unknown types should be returned uppercased."""
        assert dedup.normalize_relation_type("INVENTED") == "INVENTED"
        assert dedup.normalize_relation_type("custom_relation") == "CUSTOM_RELATION"


class TestNormalizeEntityReferences:
    """Tests for entity name normalization in relations."""

    @pytest.fixture
    def dedup(self):
        return RelationDeduplicator()

    def test_no_mapping(self, dedup):
        """Without mapping, relations should be unchanged."""
        relations = [
            {"source": "Alice", "target": "Bob", "relationship_type": "KNOWS"},
        ]
        result = dedup.normalize_entity_references(relations, {})
        assert result[0]["source"] == "Alice"
        assert result[0]["target"] == "Bob"

    def test_source_normalized(self, dedup):
        """Source entity should be remapped to canonical name."""
        relations = [
            {"source": "nicolas cage", "target": "Movie", "relationship_type": "ACTED_IN"},
        ]
        mapping = {"nicolas cage": "Nicolas Cage"}
        result = dedup.normalize_entity_references(relations, mapping)

        assert result[0]["source"] == "Nicolas Cage"
        assert result[0]["target"] == "Movie"

    def test_target_normalized(self, dedup):
        """Target entity should be remapped to canonical name."""
        relations = [
            {"source": "Director", "target": "leaving las vegas", "relationship_type": "DIRECTED"},
        ]
        mapping = {"leaving las vegas": "Leaving Las Vegas"}
        result = dedup.normalize_entity_references(relations, mapping)

        assert result[0]["source"] == "Director"
        assert result[0]["target"] == "Leaving Las Vegas"

    def test_both_normalized(self, dedup):
        """Both source and target should be normalized."""
        relations = [
            {"source": "nicolas cage", "target": "leaving las vegas", "relationship_type": "ACTED_IN"},
        ]
        mapping = {
            "nicolas cage": "Nicolas Cage",
            "leaving las vegas": "Leaving Las Vegas",
        }
        result = dedup.normalize_entity_references(relations, mapping)

        assert result[0]["source"] == "Nicolas Cage"
        assert result[0]["target"] == "Leaving Las Vegas"


class TestBidirectionalDeduplication:
    """Tests for symmetric/bidirectional relation handling."""

    @pytest.fixture
    def dedup(self):
        return RelationDeduplicator()

    def test_symmetric_deduplicated(self, dedup):
        """Symmetric relations should be deduplicated bidirectionally."""
        relations = [
            {"source": "Alice", "target": "Bob", "relationship_type": "KNOWS"},
            {"source": "Bob", "target": "Alice", "relationship_type": "KNOWS"},
        ]
        result = dedup.deduplicate(relations)

        assert len(result) == 1
        # Should keep alphabetically first
        assert result[0]["source"] in ["Alice", "Bob"]
        assert result[0]["target"] in ["Alice", "Bob"]

    def test_asymmetric_not_deduplicated(self, dedup):
        """Asymmetric relations should NOT be deduplicated bidirectionally."""
        relations = [
            {"source": "Alice", "target": "Bob", "relationship_type": "PARENT_OF"},
            {"source": "Bob", "target": "Alice", "relationship_type": "PARENT_OF"},
        ]
        result = dedup.deduplicate(relations)

        # Both should be kept (parent-child is not symmetric)
        assert len(result) == 2

    def test_married_to_symmetric(self, dedup):
        """MARRIED_TO should be treated as symmetric."""
        relations = [
            {"source": "John", "target": "Jane", "relationship_type": "MARRIED_TO"},
            {"source": "Jane", "target": "John", "relationship_type": "MARRIED_TO"},
        ]
        result = dedup.deduplicate(relations)

        assert len(result) == 1

    def test_sibling_of_symmetric(self, dedup):
        """SIBLING_OF should be treated as symmetric."""
        relations = [
            {"source": "Anna", "target": "Elsa", "relationship_type": "SIBLING_OF"},
            {"source": "Elsa", "target": "Anna", "relationship_type": "SIBLING_OF"},
        ]
        result = dedup.deduplicate(relations)

        assert len(result) == 1


class TestTypeSynonymDeduplication:
    """Tests for type synonym-based deduplication."""

    @pytest.fixture
    def dedup(self):
        return RelationDeduplicator()

    def test_same_relation_different_types(self, dedup):
        """Same relation with synonym types should be deduplicated."""
        relations = [
            {"source": "Nicolas Cage", "target": "Leaving Las Vegas", "relationship_type": "STARRED_IN"},
            {"source": "Nicolas Cage", "target": "Leaving Las Vegas", "relationship_type": "ACTED_IN"},
        ]
        result = dedup.deduplicate(relations)

        assert len(result) == 1
        assert result[0]["relationship_type"] == "ACTED_IN"  # Canonical form

    def test_different_relations_same_type_synonym(self, dedup):
        """Different relations shouldn't be merged just because of type synonym."""
        relations = [
            {"source": "Nicolas Cage", "target": "Leaving Las Vegas", "relationship_type": "STARRED_IN"},
            {"source": "Nicolas Cage", "target": "The Rock", "relationship_type": "ACTED_IN"},
        ]
        result = dedup.deduplicate(relations)

        # Different targets, should not be merged
        assert len(result) == 2


class TestFullDeduplication:
    """Tests for complete deduplication pipeline."""

    @pytest.fixture
    def dedup(self):
        return RelationDeduplicator()

    def test_empty_relations(self, dedup):
        """Empty input should return empty output."""
        result = dedup.deduplicate([])
        assert result == []

    def test_single_relation(self, dedup):
        """Single relation should be returned normalized."""
        relations = [
            {"source": "Alice", "target": "Bob", "relationship_type": "starred_in"},
        ]
        result = dedup.deduplicate(relations)

        assert len(result) == 1
        assert result[0]["relationship_type"] == "ACTED_IN"

    def test_complex_scenario(self, dedup):
        """Test complex scenario with multiple dedup opportunities."""
        relations = [
            # Duplicate: same entities, synonym types
            {"source": "Nicolas Cage", "target": "Leaving Las Vegas", "relationship_type": "STARRED_IN"},
            {"source": "Nicolas Cage", "target": "Leaving Las Vegas", "relationship_type": "ACTED_IN"},
            # Symmetric duplicate
            {"source": "Alice", "target": "Bob", "relationship_type": "KNOWS"},
            {"source": "Bob", "target": "Alice", "relationship_type": "KNOWS"},
            # Unique relation
            {"source": "Mike Figgis", "target": "Leaving Las Vegas", "relationship_type": "DIRECTED"},
        ]
        entity_mapping = {"nicolas cage": "Nicolas Cage"}

        result = dedup.deduplicate(relations, entity_mapping=entity_mapping)

        # Should have: 1 ACTED_IN, 1 KNOWS, 1 DIRECTED = 3
        assert len(result) == 3

        types = {r["relationship_type"] for r in result}
        assert "ACTED_IN" in types
        assert "KNOWS" in types
        assert "DIRECTED" in types

    def test_description_merged(self, dedup):
        """Descriptions should be merged for duplicates."""
        relations = [
            {"source": "A", "target": "B", "relationship_type": "KNOWS", "description": "Met in 2020"},
            {"source": "A", "target": "B", "relationship_type": "KNOWS", "description": "Work together"},
        ]
        result = dedup.deduplicate(relations)

        assert len(result) == 1
        assert "Met in 2020" in result[0]["description"]
        assert "Work together" in result[0]["description"]

    def test_weight_merged_max(self, dedup):
        """Weights should be merged using max."""
        relations = [
            {"source": "A", "target": "B", "relationship_type": "KNOWS", "weight": 0.5},
            {"source": "A", "target": "B", "relationship_type": "KNOWS", "weight": 0.8},
        ]
        result = dedup.deduplicate(relations)

        assert len(result) == 1
        assert result[0]["weight"] == 0.8

    def test_invalid_relations_skipped(self, dedup):
        """Relations with empty source/target should be skipped."""
        relations = [
            {"source": "", "target": "B", "relationship_type": "KNOWS"},
            {"source": "A", "target": "", "relationship_type": "KNOWS"},
            {"source": "A", "target": "B", "relationship_type": "KNOWS"},
        ]
        result = dedup.deduplicate(relations)

        assert len(result) == 1
        assert result[0]["source"] == "A"
        assert result[0]["target"] == "B"


class TestPreserveOriginalType:
    """Tests for preserve_original_type option."""

    def test_original_type_preserved(self):
        """Original type should be stored when preserve_original_type=True."""
        dedup = RelationDeduplicator(preserve_original_type=True)
        relations = [
            {"source": "A", "target": "B", "relationship_type": "STARRED_IN"},
        ]
        result = dedup.deduplicate(relations)

        assert result[0]["relationship_type"] == "ACTED_IN"
        assert result[0]["original_type"] == "STARRED_IN"

    def test_original_type_not_preserved_default(self):
        """Original type should NOT be stored by default."""
        dedup = RelationDeduplicator()
        relations = [
            {"source": "A", "target": "B", "relationship_type": "STARRED_IN"},
        ]
        result = dedup.deduplicate(relations)

        assert result[0]["relationship_type"] == "ACTED_IN"
        assert "original_type" not in result[0]


class TestGetStats:
    """Tests for get_stats method."""

    @pytest.fixture
    def dedup(self):
        return RelationDeduplicator()

    def test_stats_basic(self, dedup):
        """Test basic statistics calculation."""
        relations = [
            {"source": "A", "target": "B", "relationship_type": "STARRED_IN"},
            {"source": "A", "target": "C", "relationship_type": "ACTED_IN"},
            {"source": "D", "target": "E", "relationship_type": "DIRECTED"},
        ]
        stats = dedup.get_stats(relations)

        assert stats["total_relations"] == 3
        assert stats["unique_types"] == 3  # STARRED_IN, ACTED_IN, DIRECTED
        assert "STARRED_IN" in stats["type_distribution"]
        assert "ACTED_IN" in stats["canonical_type_distribution"]

    def test_stats_symmetric_duplicates(self, dedup):
        """Test detection of potential symmetric duplicates."""
        relations = [
            {"source": "A", "target": "B", "relationship_type": "KNOWS"},
            {"source": "B", "target": "A", "relationship_type": "KNOWS"},
        ]
        stats = dedup.get_stats(relations)

        assert stats["potential_symmetric_duplicates"] == 1


class TestFactoryFunction:
    """Tests for create_relation_deduplicator_from_config."""

    def test_enabled_by_default(self):
        """Factory should create deduplicator when enabled."""
        class MockConfig:
            enable_relation_dedup = True
            relation_preserve_original_type = False

        dedup = create_relation_deduplicator_from_config(MockConfig())
        assert dedup is not None
        assert isinstance(dedup, RelationDeduplicator)

    def test_disabled(self):
        """Factory should return None when disabled."""
        class MockConfig:
            enable_relation_dedup = False

        dedup = create_relation_deduplicator_from_config(MockConfig())
        assert dedup is None

    def test_preserve_original_type(self):
        """Factory should pass preserve_original_type option."""
        class MockConfig:
            enable_relation_dedup = True
            relation_preserve_original_type = True

        dedup = create_relation_deduplicator_from_config(MockConfig())
        assert dedup.preserve_original_type is True
