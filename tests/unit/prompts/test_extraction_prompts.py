"""Unit tests for extraction prompts.

Sprint 45: Feature 45.8 - Extraction Prompts Testing
Sprint 128: Updated to test active DSPy-optimized prompts (legacy prompts removed)
"""

import pytest

from src.prompts.extraction_prompts import (
    DSPY_OPTIMIZED_ENTITY_PROMPT,
    DSPY_OPTIMIZED_RELATION_PROMPT,
    GENERIC_ENTITY_EXTRACTION_PROMPT,
    GENERIC_RELATION_EXTRACTION_PROMPT,
    get_active_extraction_prompts,
    get_domain_enriched_extraction_prompts,
)


class TestEntityPrompt:
    """Test DSPy-optimized entity extraction prompt."""

    def test_not_empty(self) -> None:
        assert DSPY_OPTIMIZED_ENTITY_PROMPT is not None
        assert len(DSPY_OPTIMIZED_ENTITY_PROMPT) > 0

    def test_contains_text_placeholder(self) -> None:
        assert "{text}" in DSPY_OPTIMIZED_ENTITY_PROMPT
        formatted = DSPY_OPTIMIZED_ENTITY_PROMPT.format(text="test text", domain="general")
        assert "test text" in formatted
        assert "{text}" not in formatted

    def test_contains_json_instructions(self) -> None:
        assert "JSON" in DSPY_OPTIMIZED_ENTITY_PROMPT
        assert "name" in DSPY_OPTIMIZED_ENTITY_PROMPT
        assert "type" in DSPY_OPTIMIZED_ENTITY_PROMPT

    def test_contains_adr060_entity_types(self) -> None:
        prompt = DSPY_OPTIMIZED_ENTITY_PROMPT.upper()
        for t in ["PERSON", "ORGANIZATION", "LOCATION", "CONCEPT", "TECHNOLOGY"]:
            assert t in prompt

    def test_contains_domain_placeholder(self) -> None:
        assert "{domain}" in DSPY_OPTIMIZED_ENTITY_PROMPT

    def test_contains_confidence_field(self) -> None:
        assert "confidence" in DSPY_OPTIMIZED_ENTITY_PROMPT

    def test_contains_output_example(self) -> None:
        assert "Output example:" in DSPY_OPTIMIZED_ENTITY_PROMPT


class TestRelationPrompt:
    """Test DSPy-optimized relation extraction prompt."""

    def test_not_empty(self) -> None:
        assert DSPY_OPTIMIZED_RELATION_PROMPT is not None
        assert len(DSPY_OPTIMIZED_RELATION_PROMPT) > 0

    def test_contains_text_placeholder(self) -> None:
        assert "{text}" in DSPY_OPTIMIZED_RELATION_PROMPT

    def test_contains_entities_placeholder(self) -> None:
        assert "{entities}" in DSPY_OPTIMIZED_RELATION_PROMPT
        formatted = DSPY_OPTIMIZED_RELATION_PROMPT.format(
            text="test text", entities="- Entity1\n- Entity2"
        )
        assert "Entity1" in formatted

    def test_contains_json_instructions(self) -> None:
        assert "JSON" in DSPY_OPTIMIZED_RELATION_PROMPT
        assert "subject" in DSPY_OPTIMIZED_RELATION_PROMPT
        assert "relation" in DSPY_OPTIMIZED_RELATION_PROMPT
        assert "object" in DSPY_OPTIMIZED_RELATION_PROMPT

    def test_contains_adr060_relation_types(self) -> None:
        prompt = DSPY_OPTIMIZED_RELATION_PROMPT.upper()
        for t in ["PART_OF", "CONTAINS", "USES", "LOCATED_IN", "RELATED_TO"]:
            assert t in prompt

    def test_contains_strength_field(self) -> None:
        assert "strength" in DSPY_OPTIMIZED_RELATION_PROMPT

    def test_no_subject_type_object_type(self) -> None:
        """Removed in Sprint 128 — parser ignores these fields."""
        assert "subject_type" not in DSPY_OPTIMIZED_RELATION_PROMPT
        assert "object_type" not in DSPY_OPTIMIZED_RELATION_PROMPT

    def test_contains_output_example(self) -> None:
        assert "Output example:" in DSPY_OPTIMIZED_RELATION_PROMPT


class TestGenericPrompts:
    """Test generic fallback prompts (used when AEGIS_USE_LEGACY_PROMPTS=1)."""

    def test_generic_entity_has_text_placeholder(self) -> None:
        assert "{text}" in GENERIC_ENTITY_EXTRACTION_PROMPT

    def test_generic_relation_has_placeholders(self) -> None:
        assert "{text}" in GENERIC_RELATION_EXTRACTION_PROMPT
        assert "{entities}" in GENERIC_RELATION_EXTRACTION_PROMPT

    def test_generic_entity_has_adr060_types(self) -> None:
        prompt = GENERIC_ENTITY_EXTRACTION_PROMPT.upper()
        assert "PERSON" in prompt
        assert "ORGANIZATION" in prompt

    def test_generic_relation_has_adr060_types(self) -> None:
        prompt = GENERIC_RELATION_EXTRACTION_PROMPT.upper()
        assert "PART_OF" in prompt
        assert "RELATED_TO" in prompt


class TestGetActiveExtractionPrompts:
    """Test get_active_extraction_prompts dispatcher."""

    def test_returns_tuple(self) -> None:
        result = get_active_extraction_prompts()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_returns_strings(self) -> None:
        entity_prompt, relation_prompt = get_active_extraction_prompts()
        assert isinstance(entity_prompt, str)
        assert isinstance(relation_prompt, str)
        assert len(entity_prompt) > 100
        assert len(relation_prompt) > 100

    def test_prompts_have_required_placeholders(self) -> None:
        entity_prompt, relation_prompt = get_active_extraction_prompts()
        assert "{text}" in entity_prompt
        assert "{text}" in relation_prompt
        assert "{entities}" in relation_prompt


class TestDomainEnrichedPrompts:
    """Test domain-enriched prompt generation from YAML metadata."""

    def test_returns_generic_for_no_subtypes(self) -> None:
        entity_p, relation_p = get_domain_enriched_extraction_prompts(domain="unknown_domain")
        # Should still return valid prompts with placeholders
        assert "{text}" in entity_p
        assert "{text}" in relation_p

    def test_with_entity_subtypes(self) -> None:
        entity_p, relation_p = get_domain_enriched_extraction_prompts(
            domain="test_domain",
            entity_sub_types=["Protein", "Gene", "Drug"],
            entity_sub_type_mapping={"Protein": "CONCEPT", "Gene": "CONCEPT", "Drug": "PRODUCT"},
        )
        assert "Protein" in entity_p
        assert "Gene" in entity_p
        assert "Drug" in entity_p
        assert "{text}" in entity_p

    def test_with_relation_hints(self) -> None:
        entity_p, relation_p = get_domain_enriched_extraction_prompts(
            domain="test_domain",
            entity_sub_types=["Protein", "Gene"],
            entity_sub_type_mapping={"Protein": "CONCEPT", "Gene": "CONCEPT"},
            relation_hints=["TARGETS → Drug → Protein", "ENCODES → Gene → Protein"],
        )
        assert "TARGETS" in relation_p
        assert "ENCODES" in relation_p
        assert "{text}" in relation_p
        assert "{entities}" in relation_p


class TestPromptsIntegration:
    """Integration tests for prompt pipeline."""

    def test_prompts_work_together_in_sequence(self) -> None:
        """Test prompts can be used in sequence for entity+relationship extraction."""
        entity_prompt, relation_prompt = get_active_extraction_prompts()
        test_text = "John Smith works at Google on machine learning."

        formatted_entity = entity_prompt.format(text=test_text, domain="general")
        assert test_text in formatted_entity

        entity_list = "- John Smith (PERSON)\n- Google (ORGANIZATION)\n- machine learning (CONCEPT)"
        formatted_rel = relation_prompt.format(text=test_text, entities=entity_list)
        assert test_text in formatted_rel
        assert "John Smith" in formatted_rel
        assert "Google" in formatted_rel

    @pytest.mark.parametrize(
        "entity_type",
        ["PERSON", "ORGANIZATION", "LOCATION", "CONCEPT", "TECHNOLOGY", "PRODUCT", "EVENT"],
    )
    def test_entity_prompt_supports_all_entity_types(self, entity_type: str) -> None:
        prompt_upper = DSPY_OPTIMIZED_ENTITY_PROMPT.upper()
        assert entity_type in prompt_upper

    def test_prompts_mention_json_format(self) -> None:
        entity_p, relation_p = get_active_extraction_prompts()
        assert "[" in entity_p and "]" in entity_p
        assert "[" in relation_p and "]" in relation_p
