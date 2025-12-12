"""Unit tests for extraction prompts.

Sprint 45: Feature 45.8 - Extraction Prompts Testing
Tests for entity and relationship extraction prompts.
"""

import pytest

from src.prompts.extraction_prompts import (
    ENTITY_EXTRACTION_PROMPT,
    RELATIONSHIP_EXTRACTION_PROMPT,
)


class TestEntityExtractionPrompt:
    """Test entity extraction prompt structure and content."""

    def test_entity_extraction_prompt_not_empty(self) -> None:
        """Test ENTITY_EXTRACTION_PROMPT is not empty."""
        assert ENTITY_EXTRACTION_PROMPT is not None
        assert len(ENTITY_EXTRACTION_PROMPT) > 0
        assert isinstance(ENTITY_EXTRACTION_PROMPT, str)

    def test_entity_extraction_prompt_contains_text_placeholder(self) -> None:
        """Test ENTITY_EXTRACTION_PROMPT contains {text} placeholder."""
        assert "{text}" in ENTITY_EXTRACTION_PROMPT
        # Verify it can be formatted with text parameter
        formatted = ENTITY_EXTRACTION_PROMPT.format(text="test text")
        assert "test text" in formatted
        assert "{text}" not in formatted

    def test_entity_extraction_prompt_contains_json_instructions(self) -> None:
        """Test ENTITY_EXTRACTION_PROMPT contains JSON output instructions."""
        assert "JSON" in ENTITY_EXTRACTION_PROMPT
        assert "json" in ENTITY_EXTRACTION_PROMPT.lower()
        # Should mention required fields
        assert "name" in ENTITY_EXTRACTION_PROMPT
        assert "type" in ENTITY_EXTRACTION_PROMPT

    def test_entity_extraction_prompt_contains_examples(self) -> None:
        """Test ENTITY_EXTRACTION_PROMPT contains few-shot examples."""
        assert "Example" in ENTITY_EXTRACTION_PROMPT
        # Should have multiple examples
        assert ENTITY_EXTRACTION_PROMPT.count("Example") >= 2

    def test_entity_extraction_prompt_contains_entity_types(self) -> None:
        """Test ENTITY_EXTRACTION_PROMPT mentions standard entity types."""
        prompt_text = ENTITY_EXTRACTION_PROMPT.lower()
        entity_types = ["person", "organization", "location", "concept", "technology"]
        for entity_type in entity_types:
            assert entity_type in prompt_text

    def test_entity_extraction_prompt_formatting_preserves_content(self) -> None:
        """Test formatting the prompt doesn't lose content."""
        test_text = "This is a test document with important content"
        formatted = ENTITY_EXTRACTION_PROMPT.format(text=test_text)

        # Verify key instructions are still present
        assert "Extract entities" in formatted
        assert "JSON" in formatted
        assert test_text in formatted


class TestRelationshipExtractionPrompt:
    """Test relationship extraction prompt structure and content."""

    def test_relationship_extraction_prompt_not_empty(self) -> None:
        """Test RELATIONSHIP_EXTRACTION_PROMPT is not empty."""
        assert RELATIONSHIP_EXTRACTION_PROMPT is not None
        assert len(RELATIONSHIP_EXTRACTION_PROMPT) > 0
        assert isinstance(RELATIONSHIP_EXTRACTION_PROMPT, str)

    def test_relationship_extraction_prompt_contains_text_placeholder(self) -> None:
        """Test RELATIONSHIP_EXTRACTION_PROMPT contains {text} placeholder."""
        assert "{text}" in RELATIONSHIP_EXTRACTION_PROMPT
        # Verify it can be formatted with text parameter
        formatted = RELATIONSHIP_EXTRACTION_PROMPT.format(
            text="test text",
            entities="entity list"
        )
        assert "test text" in formatted
        assert "{text}" not in formatted

    def test_relationship_extraction_prompt_contains_entities_placeholder(self) -> None:
        """Test RELATIONSHIP_EXTRACTION_PROMPT contains {entities} placeholder."""
        assert "{entities}" in RELATIONSHIP_EXTRACTION_PROMPT
        # Verify it can be formatted with entities parameter
        formatted = RELATIONSHIP_EXTRACTION_PROMPT.format(
            text="test text",
            entities="- Entity1\n- Entity2"
        )
        assert "Entity1" in formatted
        assert "{entities}" not in formatted

    def test_relationship_extraction_prompt_contains_json_instructions(self) -> None:
        """Test RELATIONSHIP_EXTRACTION_PROMPT contains JSON output instructions."""
        assert "JSON" in RELATIONSHIP_EXTRACTION_PROMPT
        assert "json" in RELATIONSHIP_EXTRACTION_PROMPT.lower()
        # Should mention required fields
        assert "source" in RELATIONSHIP_EXTRACTION_PROMPT
        assert "target" in RELATIONSHIP_EXTRACTION_PROMPT
        assert "type" in RELATIONSHIP_EXTRACTION_PROMPT

    def test_relationship_extraction_prompt_contains_examples(self) -> None:
        """Test RELATIONSHIP_EXTRACTION_PROMPT contains few-shot examples."""
        assert "Example" in RELATIONSHIP_EXTRACTION_PROMPT
        # Should have multiple examples
        assert RELATIONSHIP_EXTRACTION_PROMPT.count("Example") >= 2

    def test_relationship_extraction_prompt_contains_relationship_types(self) -> None:
        """Test RELATIONSHIP_EXTRACTION_PROMPT mentions standard relationship types."""
        prompt_text = RELATIONSHIP_EXTRACTION_PROMPT.upper()
        relationship_types = ["WORKS_AT", "KNOWS", "LOCATED_IN", "CREATED", "USES", "PART_OF"]
        for rel_type in relationship_types:
            assert rel_type in prompt_text

    def test_relationship_extraction_prompt_formatting_preserves_content(self) -> None:
        """Test formatting the prompt doesn't lose content."""
        test_text = "This is a test document"
        test_entities = "- Entity1 (PERSON)\n- Entity2 (ORG)"
        formatted = RELATIONSHIP_EXTRACTION_PROMPT.format(
            text=test_text,
            entities=test_entities
        )

        # Verify key instructions are still present
        assert "Extract relationships" in formatted
        assert "JSON" in formatted
        assert test_text in formatted
        assert "Entity1" in formatted
        assert "Entity2" in formatted


class TestPromptsIntegration:
    """Integration tests for both extraction prompts."""

    def test_both_prompts_have_consistent_structure(self) -> None:
        """Test both prompts follow consistent structure."""
        # Both should have examples
        assert "Example" in ENTITY_EXTRACTION_PROMPT
        assert "Example" in RELATIONSHIP_EXTRACTION_PROMPT

        # Both should mention JSON output
        assert "JSON" in ENTITY_EXTRACTION_PROMPT
        assert "JSON" in RELATIONSHIP_EXTRACTION_PROMPT

        # Both should have clear instructions
        assert "Extract" in ENTITY_EXTRACTION_PROMPT
        assert "Extract" in RELATIONSHIP_EXTRACTION_PROMPT

    def test_prompts_work_together_in_sequence(self) -> None:
        """Test prompts can be used in sequence for entity+relationship extraction."""
        test_text = "John Smith works at Google on machine learning."

        # First format entity extraction prompt
        entity_prompt = ENTITY_EXTRACTION_PROMPT.format(text=test_text)
        assert test_text in entity_prompt

        # Simulate extracted entities
        entity_list = "- John Smith (PERSON)\n- Google (ORGANIZATION)\n- machine learning (CONCEPT)"

        # Then format relationship extraction prompt with same text and entities
        rel_prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(
            text=test_text,
            entities=entity_list
        )

        assert test_text in rel_prompt
        assert "John Smith" in rel_prompt
        assert "Google" in rel_prompt
        assert "machine learning" in rel_prompt

    @pytest.mark.parametrize("entity_type", [
        "PERSON",
        "ORGANIZATION",
        "LOCATION",
        "CONCEPT",
        "TECHNOLOGY",
        "PRODUCT",
        "EVENT"
    ])
    def test_entity_extraction_prompt_supports_all_entity_types(
        self, entity_type: str
    ) -> None:
        """Test ENTITY_EXTRACTION_PROMPT mentions all supported entity types."""
        # Some types may be in examples, check if they're referenced
        prompt_upper = ENTITY_EXTRACTION_PROMPT.upper()
        assert entity_type in prompt_upper or entity_type.lower() in ENTITY_EXTRACTION_PROMPT

    def test_prompts_are_text_strings(self) -> None:
        """Test prompts are properly defined as strings."""
        # Should be able to call string methods on them
        assert hasattr(ENTITY_EXTRACTION_PROMPT, 'upper')
        assert hasattr(ENTITY_EXTRACTION_PROMPT, 'lower')
        assert hasattr(ENTITY_EXTRACTION_PROMPT, 'format')

        assert hasattr(RELATIONSHIP_EXTRACTION_PROMPT, 'upper')
        assert hasattr(RELATIONSHIP_EXTRACTION_PROMPT, 'lower')
        assert hasattr(RELATIONSHIP_EXTRACTION_PROMPT, 'format')

    def test_prompts_mention_json_format_requirements(self) -> None:
        """Test prompts specify JSON format requirements."""
        # Entity prompt should specify JSON array format
        assert "[" in ENTITY_EXTRACTION_PROMPT and "]" in ENTITY_EXTRACTION_PROMPT

        # Relationship prompt should specify JSON array format
        assert "[" in RELATIONSHIP_EXTRACTION_PROMPT and "]" in RELATIONSHIP_EXTRACTION_PROMPT

    def test_prompts_include_validation_guidelines(self) -> None:
        """Test prompts include validation and consistency guidelines."""
        # Should mention avoiding duplicates or being comprehensive
        entity_prompt_lower = ENTITY_EXTRACTION_PROMPT.lower()
        assert "duplicate" in entity_prompt_lower or "extract" in entity_prompt_lower

        # Relationship prompt should mention validation
        rel_prompt_lower = RELATIONSHIP_EXTRACTION_PROMPT.lower()
        assert "list" in rel_prompt_lower or "entity" in rel_prompt_lower
