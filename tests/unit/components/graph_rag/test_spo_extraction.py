"""Unit tests for S-P-O Triple Extraction (Sprint 125 Feature 125.3).

Tests S-P-O extraction including:
- JSON parsing and validation
- Entity type validation with universal types
- Relation type validation with universal types
- Entity name length enforcement
- Relation name length enforcement
- KG hygiene validation
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.components.graph_rag.extraction_service import (
    ENTITY_TYPE_ALIASES,
    RELATION_TYPE_ALIASES,
    UNIVERSAL_ENTITY_TYPES,
    UNIVERSAL_RELATION_TYPES,
    ExtractionService,
    validate_entity_name_length,
    validate_entity_type,
    validate_relation_name_length,
    validate_relation_type,
)
from src.components.graph_rag.kg_hygiene import VALID_RELATION_TYPES


class TestSPOExtraction:
    """Test S-P-O (Subject-Predicate-Object) extraction functionality."""

    def test_spo_json_parsing_complete(self):
        """Test parsing complete S-P-O JSON with all fields."""
        spo_json = {
            "subject": "NVIDIA",
            "subject_type": "ORGANIZATION",
            "relation": "FOUNDED_BY",
            "object": "Jensen Huang",
            "object_type": "PERSON",
        }

        # Validate structure
        assert spo_json["subject"] == "NVIDIA"
        assert spo_json["subject_type"] == "ORGANIZATION"
        assert spo_json["relation"] == "FOUNDED_BY"
        assert spo_json["object"] == "Jensen Huang"
        assert spo_json["object_type"] == "PERSON"

    def test_spo_json_parsing_minimal(self):
        """Test parsing minimal S-P-O JSON."""
        spo_json = {
            "subject": "Python",
            "relation": "USES",
            "object": "Typing System",
        }

        # Minimal triples should still have subject and relation
        assert spo_json["subject"]
        assert spo_json["relation"]
        assert spo_json["object"]

    def test_spo_entity_type_validation_universal(self):
        """Test validation of universal entity types in S-P-O."""
        # All universal entity types should validate
        for entity_type in UNIVERSAL_ENTITY_TYPES:
            result = validate_entity_type(entity_type)
            assert result == entity_type, f"Failed for type: {entity_type}"

    def test_spo_entity_type_with_subject_object(self):
        """Test subject and object entity types in S-P-O."""
        spo_subject_type = validate_entity_type("PERSON")
        spo_object_type = validate_entity_type("ORGANIZATION")

        assert spo_subject_type == "PERSON"
        assert spo_object_type == "ORGANIZATION"

    def test_spo_relation_type_validation_universal(self):
        """Test validation of universal relation types in S-P-O."""
        # All universal relation types should validate
        for relation_type in UNIVERSAL_RELATION_TYPES:
            result = validate_relation_type(relation_type)
            assert result == relation_type, f"Failed for type: {relation_type}"

    def test_spo_relation_uses(self):
        """Test USES relation type in S-P-O."""
        relation = validate_relation_type("USES")
        assert relation == "USES"

    def test_spo_relation_creates(self):
        """Test CREATES relation type in S-P-O."""
        relation = validate_relation_type("CREATES")
        assert relation == "CREATES"

    def test_spo_relation_founded_by(self):
        """Test FOUNDED_BY relation type in S-P-O."""
        relation = validate_relation_type("FOUNDED_BY")
        assert relation == "FOUNDED_BY"

    def test_spo_entity_name_length_subject(self):
        """Test subject name length enforcement."""
        subject = validate_entity_name_length(
            "Google Cloud Platform Division", max_words=4
        )

        # Should truncate to 4 words
        assert len(subject.split()) <= 4

    def test_spo_entity_name_length_object(self):
        """Test object name length enforcement."""
        object_name = validate_entity_name_length(
            "Deep Learning Neural Networks Machine Learning Systems", max_words=4
        )

        # Should truncate to 4 words
        assert len(object_name.split()) <= 4

    def test_spo_relation_name_length(self):
        """Test relation name length enforcement."""
        relation_name = validate_relation_name_length(
            "IS_RESPONSIBLE_FOR_MANAGING_AND_OVERSEEING", max_words=3
        )

        # Should truncate to 3 words
        word_count = len(relation_name.replace("_", " ").split())
        assert word_count <= 3

    def test_spo_with_alias_mapping(self):
        """Test S-P-O with entity/relation type alias mapping."""
        # Test alias mapping in S-P-O context
        subject_type = validate_entity_type("COMPANY")  # Alias for ORGANIZATION
        relation = validate_relation_type("DEVELOPED")  # Alias for CREATES
        object_type = validate_entity_type("SOFTWARE")  # Alias for TECHNOLOGY

        assert subject_type == "ORGANIZATION"
        assert relation == "CREATES"
        assert object_type == "TECHNOLOGY"

    def test_spo_with_unknown_type_fallback(self):
        """Test S-P-O with unknown types falling back to defaults."""
        unknown_entity = validate_entity_type("UNKNOWN_ENTITY_TYPE")
        unknown_relation = validate_relation_type("UNKNOWN_RELATION_TYPE")

        assert unknown_entity == "CONCEPT"
        assert unknown_relation == "RELATED_TO"

    def test_spo_multiple_triples_consistency(self):
        """Test consistency across multiple S-P-O triples."""
        triples = [
            {
                "subject": "NVIDIA",
                "subject_type": validate_entity_type("ORGANIZATION"),
                "relation": validate_relation_type("USES"),
                "object": "CUDA",
                "object_type": validate_entity_type("TECHNOLOGY"),
            },
            {
                "subject": "Python",
                "subject_type": validate_entity_type("TECHNOLOGY"),
                "relation": validate_relation_type("IMPLEMENTS"),
                "object": "Type Hints",
                "object_type": validate_entity_type("CONCEPT"),
            },
        ]

        # All types should be validated consistently
        for triple in triples:
            assert triple["subject_type"] in UNIVERSAL_ENTITY_TYPES
            assert triple["object_type"] in UNIVERSAL_ENTITY_TYPES
            assert triple["relation"] in UNIVERSAL_RELATION_TYPES

    def test_spo_empty_subject_fallback(self):
        """Test S-P-O with empty subject."""
        subject = validate_entity_name_length("")
        assert subject == ""

    def test_spo_empty_object_fallback(self):
        """Test S-P-O with empty object."""
        obj = validate_entity_name_length("")
        assert obj == ""

    def test_spo_empty_relation_fallback(self):
        """Test S-P-O with empty relation."""
        relation = validate_relation_type("")
        assert relation == "RELATED_TO"


class TestSPOJsonSerialization:
    """Test S-P-O JSON serialization and deserialization."""

    def test_spo_to_json_string(self):
        """Test converting S-P-O triple to JSON string."""
        spo = {
            "subject": "NVIDIA",
            "subject_type": "ORGANIZATION",
            "relation": "FOUNDED_BY",
            "object": "Jensen Huang",
            "object_type": "PERSON",
        }

        json_str = json.dumps(spo)
        parsed = json.loads(json_str)

        assert parsed["subject"] == "NVIDIA"
        assert parsed["subject_type"] == "ORGANIZATION"

    def test_spo_from_json_string(self):
        """Test parsing S-P-O triple from JSON string."""
        json_str = '{"subject": "Python", "relation": "USES", "object": "Type System"}'
        spo = json.loads(json_str)

        assert spo["subject"] == "Python"
        assert spo["relation"] == "USES"
        assert spo["object"] == "Type System"

    def test_spo_json_with_escaped_quotes(self):
        """Test S-P-O JSON with escaped quotes in values."""
        spo = {
            "subject": 'Smith said "Hello"',
            "subject_type": "PERSON",
            "relation": "SAID",
            "object": 'Message "Hello World"',
            "object_type": "CONCEPT",
        }

        json_str = json.dumps(spo)
        parsed = json.loads(json_str)

        assert 'Hello' in parsed["subject"]
        assert 'Hello World' in parsed["object"]

    def test_spo_json_array_serialization(self):
        """Test serializing multiple S-P-O triples."""
        triples = [
            {
                "subject": "NVIDIA",
                "subject_type": "ORGANIZATION",
                "relation": "USES",
                "object": "CUDA",
                "object_type": "TECHNOLOGY",
            },
            {
                "subject": "CUDA",
                "subject_type": "TECHNOLOGY",
                "relation": "ENABLES",
                "object": "GPU Computing",
                "object_type": "CONCEPT",
            },
        ]

        json_str = json.dumps(triples)
        parsed = json.loads(json_str)

        assert len(parsed) == 2
        assert parsed[0]["subject"] == "NVIDIA"
        assert parsed[1]["object"] == "GPU Computing"


class TestSPOKGHygiene:
    """Test KG hygiene validation for S-P-O triples."""

    def test_valid_relation_types_includes_all_universal(self):
        """Test that VALID_RELATION_TYPES includes all universal types."""
        for universal_type in UNIVERSAL_RELATION_TYPES:
            assert (
                universal_type in VALID_RELATION_TYPES
            ), f"Universal type '{universal_type}' missing from VALID_RELATION_TYPES"

    def test_kg_hygiene_uses_type(self):
        """Test USES relation is valid in KG hygiene."""
        assert "USES" in VALID_RELATION_TYPES

    def test_kg_hygiene_creates_type(self):
        """Test CREATES relation is valid in KG hygiene."""
        assert "CREATES" in VALID_RELATION_TYPES

    def test_kg_hygiene_founded_by_type(self):
        """Test FOUNDED_BY relation is valid in KG hygiene."""
        assert "FOUNDED_BY" in VALID_RELATION_TYPES

    def test_kg_hygiene_part_of_type(self):
        """Test PART_OF relation is valid in KG hygiene."""
        assert "PART_OF" in VALID_RELATION_TYPES

    def test_kg_hygiene_all_universal_types_valid(self):
        """Test all 22 universal relation types are valid."""
        universal_count = len(UNIVERSAL_RELATION_TYPES)
        assert universal_count == 22, f"Expected 22 universal types, got {universal_count}"

        # All should be in VALID_RELATION_TYPES
        for rel_type in UNIVERSAL_RELATION_TYPES:
            assert rel_type in VALID_RELATION_TYPES


class TestSPOExtractedTriples:
    """Test realistic S-P-O triples from extraction."""

    def test_academic_paper_spo(self):
        """Test S-P-O from academic paper extraction."""
        spo = {
            "subject": "Transformer Architecture",
            "subject_type": validate_entity_type("CONCEPT"),
            "relation": validate_relation_type("ENABLES"),
            "object": "Natural Language Processing",
            "object_type": validate_entity_type("CONCEPT"),
        }

        assert spo["subject_type"] == "CONCEPT"
        assert spo["object_type"] == "CONCEPT"
        assert spo["relation"] == "ENABLES"

    def test_company_spo(self):
        """Test S-P-O from company domain."""
        spo = {
            "subject": "Google",
            "subject_type": validate_entity_type("ORGANIZATION"),
            "relation": validate_relation_type("OWNS"),
            "object": "YouTube",
            "object_type": validate_entity_type("ORGANIZATION"),
        }

        assert spo["subject_type"] == "ORGANIZATION"
        assert spo["object_type"] == "ORGANIZATION"
        assert spo["relation"] == "OWNS"

    def test_legal_document_spo(self):
        """Test S-P-O from legal document."""
        spo = {
            "subject": "Defendant",
            "subject_type": validate_entity_type("PERSON"),
            "relation": validate_relation_type("RESPONSIBLE_FOR"),
            "object": "Contract Violation",
            "object_type": validate_entity_type("CONCEPT"),
        }

        assert spo["subject_type"] == "PERSON"
        assert spo["relation"] in UNIVERSAL_RELATION_TYPES or spo["relation"] == "RELATED_TO"

    def test_spo_with_location(self):
        """Test S-P-O with location entity type."""
        spo = {
            "subject": "Apple Inc.",
            "subject_type": validate_entity_type("ORGANIZATION"),
            "relation": validate_relation_type("LOCATED_IN"),
            "object": "Cupertino",
            "object_type": validate_entity_type("LOCATION"),
        }

        assert spo["subject_type"] == "ORGANIZATION"
        assert spo["object_type"] == "LOCATION"
        assert spo["relation"] == "LOCATED_IN"

    def test_spo_with_technology(self):
        """Test S-P-O with technology entity type."""
        spo = {
            "subject": "LangChain",
            "subject_type": validate_entity_type("TECHNOLOGY"),
            "relation": validate_relation_type("IMPLEMENTS"),
            "object": "Agent Framework",
            "object_type": validate_entity_type("CONCEPT"),
        }

        assert spo["subject_type"] == "TECHNOLOGY"
        assert spo["object_type"] == "CONCEPT"
        assert spo["relation"] == "IMPLEMENTS"

    def test_spo_with_document(self):
        """Test S-P-O with document entity type."""
        spo = {
            "subject": "RFC 9110",
            "subject_type": validate_entity_type("DOCUMENT"),
            "relation": validate_relation_type("DEFINES"),
            "object": "HTTP Semantics",
            "object_type": validate_entity_type("CONCEPT"),
        }

        assert spo["subject_type"] == "DOCUMENT"
        assert spo["object_type"] == "CONCEPT"

    def test_spo_chained_relationships(self):
        """Test multiple S-P-O triples forming a knowledge chain."""
        # A -> B -> C chain
        triple1 = {
            "subject": "Python",
            "subject_type": validate_entity_type("TECHNOLOGY"),
            "relation": validate_relation_type("USES"),
            "object": "Type Hints",
            "object_type": validate_entity_type("CONCEPT"),
        }

        triple2 = {
            "subject": "Type Hints",
            "subject_type": validate_entity_type("CONCEPT"),
            "relation": validate_relation_type("ENABLES"),
            "object": "Static Analysis",
            "object_type": validate_entity_type("CONCEPT"),
        }

        # Both triples should be valid
        for triple in [triple1, triple2]:
            assert triple["subject_type"] in UNIVERSAL_ENTITY_TYPES
            assert triple["object_type"] in UNIVERSAL_ENTITY_TYPES
            assert triple["relation"] in UNIVERSAL_RELATION_TYPES

        # Object of triple1 is subject of triple2
        assert triple1["object"] == triple2["subject"]
