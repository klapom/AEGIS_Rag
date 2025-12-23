"""Unit tests for Prompt Extraction from DSPy Results.

Sprint 45 - Feature 45.2: DSPy Integration Service

Tests:
- Extract prompt from DSPy optimization results
- Format entity examples
- Format relation examples
- Get example format
- Format prompt for production use
- Save prompt template to file
- Error handling and validation
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.components.domain_training.prompt_extractor import (
    _format_entity_example,
    _format_relation_example,
    _get_example_format,
    extract_prompt_from_dspy_result,
    format_prompt_for_production,
    save_prompt_template,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def entity_extraction_result():
    """Sample DSPy entity extraction optimization result."""
    return {
        "instructions": "Extract key technical entities from the text. Include names of technologies, frameworks, and concepts.",
        "demos": [
            {
                "input": {"source_text": "Python is a programming language."},
                "output": {"entities": ["Python", "programming language"]},
            },
            {
                "input": {"source_text": "FastAPI is a modern web framework built on Python."},
                "output": {"entities": ["FastAPI", "web framework", "Python"]},
            },
        ],
        "metrics": {"f1": 0.85, "precision": 0.88, "recall": 0.82, "val_f1": 0.83},
    }


@pytest.fixture
def relation_extraction_result():
    """Sample DSPy relation extraction optimization result."""
    return {
        "instructions": "Extract relationships between entities. Return subject-predicate-object triples.",
        "demos": [
            {
                "input": {
                    "source_text": "FastAPI is built with Python",
                    "entities": ["FastAPI", "Python"],
                },
                "output": {
                    "relations": [
                        {"subject": "FastAPI", "predicate": "built_with", "object": "Python"}
                    ]
                },
            },
            {
                "input": {
                    "source_text": "Django is a Python web framework",
                    "entities": ["Django", "Python", "web framework"],
                },
                "output": {
                    "relations": [
                        {"subject": "Django", "predicate": "is_a", "object": "web framework"},
                        {"subject": "Django", "predicate": "built_with", "object": "Python"},
                    ]
                },
            },
        ],
        "metrics": {"f1": 0.82, "precision": 0.85, "recall": 0.79, "val_f1": 0.81},
    }


# ============================================================================
# Test: extract_prompt_from_dspy_result
# ============================================================================


class TestExtractPromptFromDspyResult:
    """Test prompt extraction from DSPy optimization results."""

    def test_extract_entity_prompt(self, entity_extraction_result):
        """Test extracting prompt from entity extraction result."""
        result = extract_prompt_from_dspy_result(entity_extraction_result)

        assert isinstance(result, dict)
        assert "prompt_template" in result
        assert "instructions" in result
        assert "demos" in result
        assert "metrics" in result
        assert "num_examples" in result

    def test_extract_prompt_template_contains_instructions(self, entity_extraction_result):
        """Test prompt template includes instructions."""
        result = extract_prompt_from_dspy_result(entity_extraction_result)
        prompt = result["prompt_template"]

        assert "Extract key technical entities" in prompt

    def test_extract_prompt_template_contains_examples(self, entity_extraction_result):
        """Test prompt template includes examples."""
        result = extract_prompt_from_dspy_result(entity_extraction_result)
        prompt = result["prompt_template"]

        assert "Example" in prompt
        assert "Input:" in prompt
        assert "Output:" in prompt

    def test_extract_prompt_contains_task_section(self, entity_extraction_result):
        """Test prompt includes task instruction section."""
        result = extract_prompt_from_dspy_result(entity_extraction_result)
        prompt = result["prompt_template"]

        assert "Task:" in prompt
        assert "instructions" in prompt.lower()

    def test_extract_relation_prompt(self, relation_extraction_result):
        """Test extracting prompt from relation extraction result."""
        result = extract_prompt_from_dspy_result(relation_extraction_result)

        assert "prompt_template" in result
        assert (
            "relations" in result["prompt_template"].lower()
            or "relationship" in result["prompt_template"].lower()
        )

    def test_extract_prompt_preserves_instructions(self, entity_extraction_result):
        """Test extracted instructions match original."""
        result = extract_prompt_from_dspy_result(entity_extraction_result)

        assert result["instructions"] == entity_extraction_result["instructions"]

    def test_extract_prompt_preserves_demos(self, entity_extraction_result):
        """Test extracted demos match original."""
        result = extract_prompt_from_dspy_result(entity_extraction_result)

        assert result["demos"] == entity_extraction_result["demos"]
        assert result["num_examples"] == len(entity_extraction_result["demos"])

    def test_extract_prompt_preserves_metrics(self, entity_extraction_result):
        """Test extracted metrics match original."""
        result = extract_prompt_from_dspy_result(entity_extraction_result)

        assert result["metrics"] == entity_extraction_result["metrics"]

    def test_extract_prompt_with_empty_demos(self):
        """Test extraction with no demos."""
        result_dict = {
            "instructions": "Extract entities",
            "demos": [],
            "metrics": {"f1": 0.5},
        }

        result = extract_prompt_from_dspy_result(result_dict)

        assert result["num_examples"] == 0
        assert "No examples" in result["prompt_template"]

    def test_extract_prompt_with_missing_keys(self):
        """Test extraction handles missing optional keys."""
        result_dict = {
            "instructions": "Extract entities",
        }

        result = extract_prompt_from_dspy_result(result_dict)

        assert result["instructions"] == "Extract entities"
        assert result["demos"] == []
        assert result["metrics"] == {}

    def test_extract_prompt_raises_on_empty_input(self):
        """Test extraction raises on empty input."""
        with pytest.raises(ValueError):
            extract_prompt_from_dspy_result({})

        with pytest.raises(ValueError):
            extract_prompt_from_dspy_result(None)

    def test_extract_prompt_detects_entity_format(self, entity_extraction_result):
        """Test example format is correctly detected as entity_extraction."""
        result = extract_prompt_from_dspy_result(entity_extraction_result)

        assert result["example_format"] == "entity_extraction"

    def test_extract_prompt_detects_relation_format(self, relation_extraction_result):
        """Test example format is correctly detected as relation_extraction."""
        result = extract_prompt_from_dspy_result(relation_extraction_result)

        assert result["example_format"] == "relation_extraction"


# ============================================================================
# Test: _format_entity_example
# ============================================================================


class TestFormatEntityExample:
    """Test entity example formatting."""

    def test_format_entity_example_basic(self):
        """Test basic entity example formatting."""
        input_data = {"source_text": "Python is a language."}
        output_data = {"entities": ["Python", "language"]}

        result = _format_entity_example(input_data, output_data, 1)

        assert "Example 1:" in result
        assert "Python is a language" in result
        assert "Python" in result
        assert "language" in result

    def test_format_entity_example_with_long_text(self):
        """Test entity example truncates long text."""
        long_text = "A" * 300
        input_data = {"source_text": long_text}
        output_data = {"entities": ["A"]}

        result = _format_entity_example(input_data, output_data, 1)

        assert len(result) < len(long_text) + 100  # Should be truncated
        assert "..." in result

    def test_format_entity_example_numbering(self):
        """Test entity example numbering."""
        input_data = {"source_text": "Text"}
        output_data = {"entities": ["Entity"]}

        result1 = _format_entity_example(input_data, output_data, 1)
        result2 = _format_entity_example(input_data, output_data, 2)
        result3 = _format_entity_example(input_data, output_data, 3)

        assert "Example 1:" in result1
        assert "Example 2:" in result2
        assert "Example 3:" in result3

    def test_format_entity_example_missing_fields(self):
        """Test entity example handles missing fields."""
        input_data = {}
        output_data = {}

        result = _format_entity_example(input_data, output_data, 1)

        assert "Example 1:" in result
        assert "Input:" in result
        assert "Output:" in result


# ============================================================================
# Test: _format_relation_example
# ============================================================================


class TestFormatRelationExample:
    """Test relation example formatting."""

    def test_format_relation_example_basic(self):
        """Test basic relation example formatting."""
        input_data = {
            "source_text": "FastAPI is built with Python",
            "entities": ["FastAPI", "Python"],
        }
        output_data = {
            "relations": [{"subject": "FastAPI", "predicate": "built_with", "object": "Python"}]
        }

        result = _format_relation_example(input_data, output_data, 1)

        assert "Example 1:" in result
        assert "FastAPI" in result
        assert "built_with" in result
        assert "Python" in result

    def test_format_relation_example_multiple_relations(self):
        """Test relation example with multiple relations."""
        input_data = {
            "source_text": "Django is a Python web framework",
            "entities": ["Django", "Python", "web framework"],
        }
        output_data = {
            "relations": [
                {"subject": "Django", "predicate": "is_a", "object": "web framework"},
                {"subject": "Django", "predicate": "built_with", "object": "Python"},
            ]
        }

        result = _format_relation_example(input_data, output_data, 1)

        assert "is_a" in result
        assert "built_with" in result
        assert "web framework" in result

    def test_format_relation_example_with_long_text(self):
        """Test relation example truncates long text."""
        long_text = "A" * 300
        input_data = {
            "source_text": long_text,
            "entities": ["A"],
        }
        output_data = {"relations": [{"subject": "A", "predicate": "is", "object": "B"}]}

        result = _format_relation_example(input_data, output_data, 1)

        assert "..." in result

    def test_format_relation_example_invalid_relations(self):
        """Test relation example with malformed relations."""
        input_data = {
            "source_text": "Text",
            "entities": ["A", "B"],
        }
        output_data = {
            "relations": [
                {"invalid": "format"},  # Missing required fields
                {"subject": "A", "predicate": "is", "object": "B"},  # Valid
            ]
        }

        result = _format_relation_example(input_data, output_data, 1)

        assert "is" in result


# ============================================================================
# Test: _get_example_format
# ============================================================================


class TestGetExampleFormat:
    """Test determining example format from demos."""

    def test_get_format_entity_extraction(self, entity_extraction_result):
        """Test detecting entity extraction format."""
        demos = entity_extraction_result["demos"]
        format_type = _get_example_format(demos)

        assert format_type == "entity_extraction"

    def test_get_format_relation_extraction(self, relation_extraction_result):
        """Test detecting relation extraction format."""
        demos = relation_extraction_result["demos"]
        format_type = _get_example_format(demos)

        assert format_type == "relation_extraction"

    def test_get_format_empty_demos(self):
        """Test format detection with empty demos."""
        format_type = _get_example_format([])

        assert format_type == "unknown"

    def test_get_format_unknown_structure(self):
        """Test format detection with unknown structure."""
        demos = [{"input": {}, "output": {"unknown_field": "value"}}]
        format_type = _get_example_format(demos)

        assert format_type == "unknown"


# ============================================================================
# Test: format_prompt_for_production
# ============================================================================


class TestFormatPromptForProduction:
    """Test formatting prompts for production use."""

    def test_format_entity_extraction_prompt(self, entity_extraction_result):
        """Test formatting entity extraction prompt for production."""
        prompt_data = extract_prompt_from_dspy_result(entity_extraction_result)
        task_text = "Tesla is building electric cars in California."

        full_prompt = format_prompt_for_production(prompt_data, task_text)

        assert "Tesla" in full_prompt
        assert "electric cars" in full_prompt
        assert "California" in full_prompt
        assert "Instructions:" in full_prompt
        assert "Examples:" in full_prompt

    def test_format_relation_extraction_prompt(self, relation_extraction_result):
        """Test formatting relation extraction prompt for production."""
        prompt_data = extract_prompt_from_dspy_result(relation_extraction_result)
        task_text = "FastAPI is built with Python"
        entities = ["FastAPI", "Python"]

        full_prompt = format_prompt_for_production(prompt_data, task_text, entities)

        assert "FastAPI" in full_prompt
        assert "Python" in full_prompt
        assert "Relations" in full_prompt or "relations" in full_prompt

    def test_format_prompt_includes_template(self, entity_extraction_result):
        """Test formatted prompt includes template."""
        prompt_data = extract_prompt_from_dspy_result(entity_extraction_result)
        task_text = "Sample text"

        full_prompt = format_prompt_for_production(prompt_data, task_text)

        # Should contain both template and task
        assert len(full_prompt) > len(prompt_data["prompt_template"])

    def test_format_prompt_requires_entities_for_relations(self, relation_extraction_result):
        """Test relation formatting requires entities parameter."""
        prompt_data = extract_prompt_from_dspy_result(relation_extraction_result)
        task_text = "Sample text"

        with pytest.raises(ValueError):
            format_prompt_for_production(prompt_data, task_text)

    def test_format_prompt_with_invalid_data(self):
        """Test format prompt raises on invalid data."""
        with pytest.raises(ValueError):
            format_prompt_for_production({}, "text")

        with pytest.raises(ValueError):
            format_prompt_for_production(None, "text")

        with pytest.raises(ValueError):
            format_prompt_for_production({"no_template": True}, "text")


# ============================================================================
# Test: save_prompt_template
# ============================================================================


class TestSavePromptTemplate:
    """Test saving prompt templates to file."""

    def test_save_prompt_template(self, entity_extraction_result):
        """Test saving prompt template to file."""
        prompt_data = extract_prompt_from_dspy_result(entity_extraction_result)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "prompts" / "entity.json")

            save_prompt_template(prompt_data, output_path)

            # Verify file exists
            assert Path(output_path).exists()

            # Verify content
            with open(output_path) as f:
                saved_data = json.load(f)

            assert saved_data["prompt_template"] == prompt_data["prompt_template"]
            assert saved_data["instructions"] == prompt_data["instructions"]

    def test_save_prompt_creates_parent_directory(self, entity_extraction_result):
        """Test saving creates parent directories."""
        prompt_data = extract_prompt_from_dspy_result(entity_extraction_result)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "a" / "b" / "c" / "prompt.json")

            save_prompt_template(prompt_data, output_path)

            assert Path(output_path).exists()

    def test_save_prompt_includes_metadata(self, entity_extraction_result):
        """Test saved prompt includes all metadata."""
        prompt_data = extract_prompt_from_dspy_result(entity_extraction_result)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "prompt.json")

            save_prompt_template(prompt_data, output_path)

            with open(output_path) as f:
                saved = json.load(f)

            assert "prompt_template" in saved
            assert "instructions" in saved
            assert "example_format" in saved
            assert "num_examples" in saved
            assert "metrics" in saved

    def test_save_prompt_with_unicode(self, entity_extraction_result):
        """Test saving prompt with Unicode characters."""
        prompt_data = extract_prompt_from_dspy_result(entity_extraction_result)
        prompt_data["instructions"] = "Extract entities from German text: Rechtesystem"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "prompt.json")

            save_prompt_template(prompt_data, output_path)

            with open(output_path, encoding="utf-8") as f:
                saved = json.load(f)

            assert "Rechtesystem" in saved["instructions"]

    def test_save_prompt_invalid_data(self):
        """Test save raises on invalid data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "prompt.json")

            with pytest.raises(ValueError):
                save_prompt_template({}, output_path)

            with pytest.raises(ValueError):
                save_prompt_template(None, output_path)

    def test_save_prompt_template_json_format(self, entity_extraction_result):
        """Test saved template is valid JSON."""
        prompt_data = extract_prompt_from_dspy_result(entity_extraction_result)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "prompt.json")

            save_prompt_template(prompt_data, output_path)

            # Should be parseable JSON
            with open(output_path) as f:
                json.load(f)  # Will raise if invalid JSON


# ============================================================================
# Integration Tests
# ============================================================================


class TestPromptExtractionIntegration:
    """Integration tests for complete prompt extraction workflow."""

    def test_complete_entity_extraction_workflow(self, entity_extraction_result):
        """Test complete entity extraction workflow."""
        # Extract prompt
        prompt_data = extract_prompt_from_dspy_result(entity_extraction_result)

        # Format for production
        full_prompt = format_prompt_for_production(
            prompt_data,
            task_text="Python is a programming language",
        )

        # Save to file
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "entity_prompt.json")
            save_prompt_template(prompt_data, output_path)

            # Verify all components work together
            assert Path(output_path).exists()
            assert len(full_prompt) > 0
            assert prompt_data["num_examples"] > 0

    def test_complete_relation_extraction_workflow(self, relation_extraction_result):
        """Test complete relation extraction workflow."""
        # Extract prompt
        prompt_data = extract_prompt_from_dspy_result(relation_extraction_result)

        # Format for production
        full_prompt = format_prompt_for_production(
            prompt_data,
            task_text="FastAPI is built with Python",
            entities=["FastAPI", "Python"],
        )

        # Verify workflow
        assert prompt_data["example_format"] == "relation_extraction"
        assert len(full_prompt) > 0
        assert "relations" in full_prompt.lower() or "relationships" in full_prompt.lower()

    def test_extraction_preserves_content_integrity(self, entity_extraction_result):
        """Test extraction preserves all content without truncation in templates."""
        prompt_data = extract_prompt_from_dspy_result(entity_extraction_result)

        # Original instructions should be fully preserved
        assert prompt_data["instructions"] == entity_extraction_result["instructions"]

        # All demos should be preserved
        assert len(prompt_data["demos"]) == len(entity_extraction_result["demos"])

        # Metrics should be preserved
        assert prompt_data["metrics"] == entity_extraction_result["metrics"]
