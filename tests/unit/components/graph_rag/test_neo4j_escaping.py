"""Unit tests for Neo4j Cypher escaping (Sprint 84 Feature 84.7).

Tests the _sanitize_cypher_label() function that prevents Cypher syntax errors
when entity types contain special characters (spaces, colons, slashes, etc.).
"""

import pytest

from src.components.graph_rag.lightrag.neo4j_storage import _sanitize_cypher_label


class TestCypherLabelEscaping:
    """Test Cypher label sanitization for special characters."""

    def test_entity_type_with_spaces(self):
        """Entity types with spaces should be wrapped in backticks."""
        entity_type = "Dataset Processing"
        result = _sanitize_cypher_label(entity_type)

        assert result == "`Dataset Processing`"
        # Verify it can be used in Cypher query
        assert f"MERGE (e:base:{result} {{id: $id}})" == "MERGE (e:base:`Dataset Processing` {id: $id})"

    def test_entity_type_with_colon(self):
        """Entity types with colons should be wrapped in backticks."""
        entity_type = "Work: Title"
        result = _sanitize_cypher_label(entity_type)

        assert result == "`Work: Title`"

    def test_entity_type_with_slash(self):
        """Entity types with slashes should be wrapped in backticks."""
        entity_type = "Path/To/Resource"
        result = _sanitize_cypher_label(entity_type)

        assert result == "`Path/To/Resource`"

    def test_entity_type_with_special_chars(self):
        """Entity types with various special characters should be sanitized."""
        entity_type = "Test: Entity / With <Special> Chars & Symbols"
        result = _sanitize_cypher_label(entity_type)

        # Should wrap in backticks
        assert result.startswith("`") and result.endswith("`")
        # Should contain the original content
        assert "Test: Entity / With <Special> Chars & Symbols" in result

    def test_simple_entity_type_still_escaped(self):
        """Simple entity types without special chars should also be wrapped for consistency."""
        entity_type = "Person"
        result = _sanitize_cypher_label(entity_type)

        # Always wrap for safety
        assert result == "`Person`"

    def test_entity_type_with_backticks_escaped(self):
        """Existing backticks in entity types should be escaped to prevent injection."""
        entity_type = "Label`With`Backticks"
        result = _sanitize_cypher_label(entity_type)

        # Backticks should be escaped
        assert result == "`Label\\`With\\`Backticks`"

    def test_empty_string(self):
        """Empty string should return empty backticks."""
        result = _sanitize_cypher_label("")
        assert result == "``"

    def test_unicode_characters(self):
        """Unicode characters should be preserved."""
        entity_type = "Datensatz Verarbeitung 数据处理"
        result = _sanitize_cypher_label(entity_type)

        assert result == "`Datensatz Verarbeitung 数据处理`"

    def test_real_world_examples_from_iteration1(self):
        """Test actual entity types that caused failures in Iteration 1."""
        # From error logs:
        problematic_types = [
            "Dataset Processing",
            "Work",  # "Moloch: or, This Gentile World"
            "Event",  # "Launceston by-election, 1874"
            "Benchmark Dataset",  # "RAGAS Phase 1 Benchmark"
        ]

        for entity_type in problematic_types:
            result = _sanitize_cypher_label(entity_type)

            # All should be wrapped in backticks
            assert result.startswith("`") and result.endswith("`")

            # Should contain original content
            assert entity_type in result

            # Should not raise SyntaxError when used in Cypher
            # (This would need integration test with Neo4j driver)


@pytest.mark.parametrize(
    "entity_type,expected",
    [
        ("Person", "`Person`"),
        ("Dataset Processing", "`Dataset Processing`"),
        ("Work: Title", "`Work: Title`"),
        ("Path/To/File", "`Path/To/File`"),
        ("Label`With`Backticks", "`Label\\`With\\`Backticks`"),
        ("数据处理", "`数据处理`"),
        ("", "``"),
    ],
)
def test_sanitize_cypher_label_parameterized(entity_type, expected):
    """Parameterized tests for various entity types."""
    assert _sanitize_cypher_label(entity_type) == expected
