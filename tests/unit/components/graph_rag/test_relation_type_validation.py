"""Unit tests for Sprint 129.10: Relation Type Validation & Suffix Stripping.

Tests validate_relation_type() improvements including suffix-stripping normalization
and expanded alias mappings.
"""

import pytest

from src.components.graph_rag.extraction_service import (
    RELATION_TYPE_ALIASES,
    UNIVERSAL_RELATION_TYPES,
    _strip_relation_suffix,
    validate_relation_type,
)


class TestUniversalRelationTypes:
    """Test that all 21+1 universal types are defined."""

    def test_universal_types_count(self):
        """Should have 22 universal types (21 + RELATED_TO fallback)."""
        assert len(UNIVERSAL_RELATION_TYPES) == 22

    def test_key_universal_types_present(self):
        """Core universal types should all be present."""
        expected = {
            "PART_OF",
            "CONTAINS",
            "INSTANCE_OF",
            "TYPE_OF",
            "EMPLOYS",
            "MANAGES",
            "FOUNDED_BY",
            "OWNS",
            "LOCATED_IN",
            "CAUSES",
            "ENABLES",
            "REQUIRES",
            "LEADS_TO",
            "PRECEDES",
            "FOLLOWS",
            "USES",
            "CREATES",
            "IMPLEMENTS",
            "DEPENDS_ON",
            "SIMILAR_TO",
            "ASSOCIATED_WITH",
            "RELATED_TO",
        }
        assert expected == UNIVERSAL_RELATION_TYPES


class TestStripRelationSuffix:
    """Test the suffix-stripping normalizer."""

    def test_strips_by_suffix(self):
        assert _strip_relation_suffix("DEVELOPED_BY") == "DEVELOPED"

    def test_strips_in_suffix(self):
        assert _strip_relation_suffix("LOCATED_IN") == "LOCATED"

    def test_strips_at_suffix(self):
        assert _strip_relation_suffix("LOCATED_AT") == "LOCATED"

    def test_strips_with_suffix(self):
        assert _strip_relation_suffix("ASSOCIATED_WITH") == "ASSOCIATED"

    def test_strips_from_suffix(self):
        assert _strip_relation_suffix("DERIVED_FROM") == "DERIVED"

    def test_strips_for_suffix(self):
        assert _strip_relation_suffix("DESIGNED_FOR") == "DESIGNED"

    def test_strips_on_suffix(self):
        assert _strip_relation_suffix("TRAINS_ON") == "TRAINS"

    def test_no_suffix_returns_none(self):
        assert _strip_relation_suffix("CREATES") is None

    def test_empty_string_returns_none(self):
        assert _strip_relation_suffix("") is None

    def test_just_suffix_returns_none(self):
        """A string that IS a suffix shouldn't produce empty root."""
        result = _strip_relation_suffix("_BY")
        assert result is None


class TestValidateRelationType:
    """Test the full validation pipeline."""

    def test_universal_type_passes_through(self):
        """Universal types should pass through unchanged."""
        assert validate_relation_type("CREATES") == "CREATES"
        assert validate_relation_type("LOCATED_IN") == "LOCATED_IN"
        assert validate_relation_type("RELATED_TO") == "RELATED_TO"

    def test_case_insensitive(self):
        """Validation should be case-insensitive."""
        assert validate_relation_type("creates") == "CREATES"
        assert validate_relation_type("Located_In") == "LOCATED_IN"

    def test_exact_alias_mapping(self):
        """Known aliases should map to correct universal types."""
        assert validate_relation_type("WORKS_AT") == "EMPLOYS"
        assert validate_relation_type("BASED_IN") == "LOCATED_IN"
        assert validate_relation_type("BUILT") == "CREATES"

    def test_suffix_stripping_recovers_known_root(self):
        """Suffix stripping should recover known roots from verb+suffix forms."""
        # DEVELOPED_BY → strip _BY → DEVELOPED → (in aliases) → CREATES
        assert validate_relation_type("DEVELOPED_BY") == "CREATES"

    def test_suffix_stripping_discovers_universal_type(self):
        """Suffix stripping might reveal a universal type directly."""
        # CAUSED_BY → strip _BY → CAUSED... not a universal type
        # but USES_ON → strip _ON → USES → universal type
        assert validate_relation_type("USES_ON") == "USES"

    def test_empty_type_returns_related_to(self):
        """Empty/None types should fallback to RELATED_TO."""
        assert validate_relation_type("") == "RELATED_TO"

    def test_truly_unknown_type_returns_related_to(self):
        """Completely unknown types should fallback to RELATED_TO."""
        assert validate_relation_type("XYZZY_FOOBAR") == "RELATED_TO"

    def test_domain_verb_mapping_from_benchmark(self):
        """Common domain-specific verbs from Sprint 128 benchmark should map correctly."""
        # These were commonly extracted by the LLM during domain prompt verification
        mappings = {
            "TREATS": "USES",
            "ENCODES": "CREATES",
            "CATALYZES": "CAUSES",
            "INHIBITS": "CAUSES",
            "PROVES": "LEADS_TO",
            "REGULATES": "MANAGES",
            "DISCOVERED": "CREATES",
            "OBSERVED": "USES",
            "ACQUIRED": "OWNS",
            "REDUCED": "CAUSES",
            "APPROVED": "MANAGES",
            "SURPASSED": "LEADS_TO",
            "LAUNCHED": "CREATES",
        }
        for verb, expected_universal in mappings.items():
            result = validate_relation_type(verb)
            assert result == expected_universal, (
                f"{verb} mapped to {result}, expected {expected_universal}"
            )

    def test_whitespace_handling(self):
        """Types with whitespace should be stripped."""
        assert validate_relation_type("  CREATES  ") == "CREATES"
        assert validate_relation_type(" WORKS_AT ") == "EMPLOYS"
