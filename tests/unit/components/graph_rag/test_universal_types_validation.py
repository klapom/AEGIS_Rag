"""Unit tests for Sprint 125 Feature 125.3: ADR-060 Universal Types validation.

Tests the entity and relation type validation, mapping, and name length enforcement.
"""

import pytest

from src.components.graph_rag.extraction_service import (
    ENTITY_TYPE_ALIASES,
    RELATION_TYPE_ALIASES,
    UNIVERSAL_ENTITY_TYPES,
    UNIVERSAL_RELATION_TYPES,
    validate_entity_name_length,
    validate_entity_type,
    validate_relation_name_length,
    validate_relation_type,
)


class TestUniversalEntityTypes:
    """Test entity type validation and mapping."""

    def test_universal_entity_types_count(self):
        """Verify exactly 15 universal entity types exist."""
        assert len(UNIVERSAL_ENTITY_TYPES) == 15

    def test_validate_known_universal_type(self):
        """Known universal types should pass through unchanged."""
        assert validate_entity_type("PERSON") == "PERSON"
        assert validate_entity_type("ORGANIZATION") == "ORGANIZATION"
        assert validate_entity_type("TECHNOLOGY") == "TECHNOLOGY"
        assert validate_entity_type("CONCEPT") == "CONCEPT"

    def test_validate_alias_mapping(self):
        """Entity type aliases should map to universal types."""
        assert validate_entity_type("COMPANY") == "ORGANIZATION"
        assert validate_entity_type("TOOL") == "TECHNOLOGY"
        assert validate_entity_type("ALGORITHM") == "PROCESS"
        assert validate_entity_type("PAPER") == "DOCUMENT"
        assert validate_entity_type("LAW") == "REGULATION"

    def test_validate_unknown_type_fallback(self):
        """Unknown entity types should fall back to CONCEPT."""
        assert validate_entity_type("UNKNOWN_TYPE") == "CONCEPT"
        assert validate_entity_type("RANDOM_ENTITY") == "CONCEPT"
        assert validate_entity_type("") == "CONCEPT"
        assert validate_entity_type(None) == "CONCEPT"

    def test_validate_case_insensitive(self):
        """Entity type validation should be case-insensitive."""
        assert validate_entity_type("person") == "PERSON"
        assert validate_entity_type("Organization") == "ORGANIZATION"
        assert validate_entity_type("company") == "ORGANIZATION"

    def test_entity_name_length_valid(self):
        """Entity names <= 4 words should pass through unchanged."""
        assert validate_entity_name_length("NVIDIA") == "NVIDIA"
        assert validate_entity_name_length("John Smith") == "John Smith"
        assert validate_entity_name_length("New York City") == "New York City"
        assert validate_entity_name_length("Google Cloud Platform") == "Google Cloud Platform"

    def test_entity_name_length_truncated(self):
        """Entity names > 4 words should be truncated."""
        long_name = "NVIDIA Corporation headquartered in Santa Clara California"
        truncated = validate_entity_name_length(long_name, max_words=4)
        assert truncated == "NVIDIA Corporation headquartered in"
        assert len(truncated.split()) == 4

    def test_entity_name_empty(self):
        """Empty entity names should return empty string."""
        assert validate_entity_name_length("") == ""
        assert validate_entity_name_length(None) == ""


class TestUniversalRelationTypes:
    """Test relation type validation and mapping."""

    def test_universal_relation_types_count(self):
        """Verify exactly 22 universal relation types exist.

        ADR-060 defines 22 types (not 21 as some docs state):
        - Structural: 4 (PART_OF, CONTAINS, INSTANCE_OF, TYPE_OF)
        - Organizational: 5 (EMPLOYS, MANAGES, FOUNDED_BY, OWNS, LOCATED_IN)
        - Causal: 4 (CAUSES, ENABLES, REQUIRES, LEADS_TO)
        - Temporal: 2 (PRECEDES, FOLLOWS)
        - Functional: 4 (USES, CREATES, IMPLEMENTS, DEPENDS_ON)
        - Semantic: 2 (SIMILAR_TO, ASSOCIATED_WITH)
        - Fallback: 1 (RELATED_TO)
        """
        assert len(UNIVERSAL_RELATION_TYPES) == 22

    def test_validate_known_universal_type(self):
        """Known universal relation types should pass through unchanged."""
        assert validate_relation_type("PART_OF") == "PART_OF"
        assert validate_relation_type("EMPLOYS") == "EMPLOYS"
        assert validate_relation_type("USES") == "USES"
        assert validate_relation_type("RELATED_TO") == "RELATED_TO"

    def test_validate_alias_mapping(self):
        """Relation type aliases should map to universal types."""
        assert validate_relation_type("RELATES_TO") == "RELATED_TO"
        assert validate_relation_type("DEVELOPED") == "CREATES"
        assert validate_relation_type("FOUNDED") == "FOUNDED_BY"
        assert validate_relation_type("BASED_ON") == "DEPENDS_ON"

    def test_validate_unknown_type_fallback(self):
        """Unknown relation types should fall back to RELATED_TO."""
        assert validate_relation_type("UNKNOWN_RELATION") == "RELATED_TO"
        assert validate_relation_type("RANDOM_TYPE") == "RELATED_TO"
        assert validate_relation_type("") == "RELATED_TO"
        assert validate_relation_type(None) == "RELATED_TO"

    def test_validate_case_insensitive(self):
        """Relation type validation should be case-insensitive."""
        assert validate_relation_type("part_of") == "PART_OF"
        assert validate_relation_type("Employs") == "EMPLOYS"
        assert validate_relation_type("relates_to") == "RELATED_TO"

    def test_relation_name_length_valid(self):
        """Relation names <= 3 words should pass through unchanged."""
        assert validate_relation_name_length("USES") == "USES"
        assert validate_relation_name_length("PART_OF") == "PART_OF"
        assert validate_relation_name_length("FOUNDED_BY") == "FOUNDED_BY"

    def test_relation_name_length_truncated(self):
        """Relation names > 3 words should be truncated."""
        long_name = "IS_A_COMPONENT_OF_THE_ENTIRE_SYSTEM"
        truncated = validate_relation_name_length(long_name, max_words=3)
        assert truncated == "IS_A_COMPONENT"
        assert len(truncated.replace("_", " ").split()) == 3

    def test_relation_name_empty(self):
        """Empty relation names should return empty string."""
        assert validate_relation_name_length("") == ""
        assert validate_relation_name_length(None) == ""


class TestEntityTypeAliases:
    """Test comprehensive entity type alias coverage."""

    def test_all_aliases_map_to_universal_types(self):
        """All entity type aliases must map to one of the 15 universal types."""
        for alias, universal_type in ENTITY_TYPE_ALIASES.items():
            assert (
                universal_type in UNIVERSAL_ENTITY_TYPES
            ), f"Alias '{alias}' maps to invalid type '{universal_type}'"

    def test_organization_aliases(self):
        """Test all organization-related aliases."""
        org_aliases = ["COMPANY", "CORPORATION", "INSTITUTION", "UNIVERSITY", "AGENCY"]
        for alias in org_aliases:
            assert ENTITY_TYPE_ALIASES[alias] == "ORGANIZATION"

    def test_location_aliases(self):
        """Test all location-related aliases."""
        loc_aliases = ["PLACE", "CITY", "COUNTRY", "GPE"]
        for alias in loc_aliases:
            assert ENTITY_TYPE_ALIASES[alias] == "LOCATION"

    def test_technology_aliases(self):
        """Test all technology-related aliases."""
        tech_aliases = ["TOOL", "SOFTWARE", "FRAMEWORK", "PROGRAMMING_LANGUAGE"]
        for alias in tech_aliases:
            assert ENTITY_TYPE_ALIASES[alias] == "TECHNOLOGY"


class TestRelationTypeAliases:
    """Test comprehensive relation type alias coverage."""

    def test_all_aliases_map_to_universal_types(self):
        """All relation type aliases must map to one of the 21 universal types."""
        for alias, universal_type in RELATION_TYPE_ALIASES.items():
            assert (
                universal_type in UNIVERSAL_RELATION_TYPES
            ), f"Alias '{alias}' maps to invalid type '{universal_type}'"

    def test_legacy_aliases(self):
        """Test legacy relation type aliases."""
        assert RELATION_TYPE_ALIASES["RELATES_TO"] == "RELATED_TO"
        assert RELATION_TYPE_ALIASES["DEVELOPED"] == "CREATES"
        assert RELATION_TYPE_ALIASES["FOUNDED"] == "FOUNDED_BY"

    def test_location_aliases(self):
        """Test location-related relation aliases."""
        loc_aliases = ["BASED_IN", "HEADQUARTERED_IN", "OPERATES_IN"]
        for alias in loc_aliases:
            assert RELATION_TYPE_ALIASES[alias] == "LOCATED_IN"


class TestKGHygieneValidation:
    """Test KG hygiene validation with universal types."""

    def test_valid_relation_types_include_universal_types(self):
        """kg_hygiene.py VALID_RELATION_TYPES must include all 21 universal types."""
        from src.components.graph_rag.kg_hygiene import VALID_RELATION_TYPES

        for rel_type in UNIVERSAL_RELATION_TYPES:
            assert (
                rel_type in VALID_RELATION_TYPES
            ), f"Universal type '{rel_type}' missing from VALID_RELATION_TYPES"

    def test_legacy_types_still_valid(self):
        """Legacy relation types should still be valid for backward compatibility."""
        from src.components.graph_rag.kg_hygiene import VALID_RELATION_TYPES

        legacy_types = ["RELATES_TO", "USED_BY", "EXTENDS"]
        for legacy_type in legacy_types:
            assert (
                legacy_type in VALID_RELATION_TYPES
            ), f"Legacy type '{legacy_type}' should remain valid"
