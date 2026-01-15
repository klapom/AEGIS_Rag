"""Unit tests for built-in tools.

Sprint 93 Feature 93.1: Tool Composition Framework
"""

import json
import pytest

from src.agents.tools.builtin import (
    echo_tool,
    format_tool,
    from_json_tool,
    get_builtin_tools,
    join_tool,
    json_extract_tool,
    replace_tool,
    split_tool,
    template_tool,
    to_json_tool,
    truncate_tool,
    _parse_path,
    _extract_path,
)


class TestEchoTool:
    """Test echo_tool functionality."""

    def test_echo_simple_string(self):
        """Test echoing a simple string."""
        result = echo_tool.invoke("Hello, World!")
        assert result == "Hello, World!"

    def test_echo_empty_string(self):
        """Test echoing an empty string."""
        result = echo_tool.invoke("")
        assert result == ""

    def test_echo_unicode(self):
        """Test echoing unicode characters."""
        result = echo_tool.invoke("日本語 🎉")
        assert result == "日本語 🎉"


class TestFormatTool:
    """Test format_tool functionality."""

    def test_format_simple(self):
        """Test simple template formatting."""
        result = format_tool.invoke({
            "template": "Hello, {name}!",
            "values": {"name": "World"}
        })
        assert result == "Hello, World!"

    def test_format_multiple_values(self):
        """Test formatting with multiple values."""
        result = format_tool.invoke({
            "template": "{item}: {count} units",
            "values": {"item": "Apple", "count": 5}
        })
        assert result == "Apple: 5 units"

    def test_format_missing_key(self):
        """Test formatting with missing key returns original."""
        result = format_tool.invoke({
            "template": "Hello, {name}!",
            "values": {}
        })
        # Should return unformatted on missing key
        assert result == "Hello, {name}!"

    def test_format_empty_template(self):
        """Test formatting empty template."""
        result = format_tool.invoke({
            "template": "",
            "values": {"name": "test"}
        })
        assert result == ""


class TestJsonExtractTool:
    """Test json_extract_tool functionality."""

    def test_extract_simple_path(self):
        """Test extracting simple path."""
        json_str = '{"name": "Alice"}'
        result = json_extract_tool.invoke({"json_str": json_str, "path": "name"})
        assert result == "Alice"

    def test_extract_nested_path(self):
        """Test extracting nested path."""
        json_str = '{"user": {"name": "Alice", "age": 30}}'
        result = json_extract_tool.invoke({"json_str": json_str, "path": "user.name"})
        assert result == "Alice"

    def test_extract_array_index(self):
        """Test extracting array index."""
        json_str = '{"items": ["a", "b", "c"]}'
        result = json_extract_tool.invoke({"json_str": json_str, "path": "items[1]"})
        assert result == "b"

    def test_extract_complex_path(self):
        """Test extracting complex path with nested array."""
        json_str = '{"data": {"users": [{"name": "Alice"}, {"name": "Bob"}]}}'
        result = json_extract_tool.invoke({"json_str": json_str, "path": "data.users[0].name"})
        assert result == "Alice"

    def test_extract_invalid_json(self):
        """Test extracting from invalid JSON."""
        result = json_extract_tool.invoke({"json_str": "not json", "path": "name"})
        assert result is None

    def test_extract_missing_path(self):
        """Test extracting missing path."""
        json_str = '{"name": "Alice"}'
        result = json_extract_tool.invoke({"json_str": json_str, "path": "missing"})
        assert result is None


class TestParsePath:
    """Test _parse_path helper."""

    def test_parse_simple_path(self):
        """Test parsing simple path."""
        parts = _parse_path("name")
        assert parts == ["name"]

    def test_parse_nested_path(self):
        """Test parsing nested path."""
        parts = _parse_path("user.name")
        assert parts == ["user", "name"]

    def test_parse_array_path(self):
        """Test parsing path with array index."""
        parts = _parse_path("items[0]")
        assert parts == ["items", 0]

    def test_parse_complex_path(self):
        """Test parsing complex path."""
        parts = _parse_path("data.items[2].name")
        assert parts == ["data", "items", 2, "name"]


class TestExtractPath:
    """Test _extract_path helper."""

    def test_extract_from_dict(self):
        """Test extracting from dict."""
        data = {"name": "test"}
        result = _extract_path(data, "name")
        assert result == "test"

    def test_extract_from_nested(self):
        """Test extracting from nested structure."""
        data = {"user": {"name": "Alice"}}
        result = _extract_path(data, "user.name")
        assert result == "Alice"

    def test_extract_from_list(self):
        """Test extracting from list."""
        data = {"items": [1, 2, 3]}
        result = _extract_path(data, "items[1]")
        assert result == 2

    def test_extract_missing_returns_none(self):
        """Test extracting missing path returns None."""
        data = {"name": "test"}
        result = _extract_path(data, "missing")
        assert result is None


class TestTemplateTool:
    """Test template_tool functionality."""

    def test_template_simple(self):
        """Test simple template rendering."""
        result = template_tool.invoke({
            "template": "Hello, {{ name }}!",
            "context": {"name": "World"}
        })
        assert result == "Hello, World!"

    def test_template_multiple_vars(self):
        """Test template with multiple variables."""
        result = template_tool.invoke({
            "template": "{{ greeting }}, {{ name }}!",
            "context": {"greeting": "Hi", "name": "Alice"}
        })
        assert result == "Hi, Alice!"

    def test_template_missing_var(self):
        """Test template with missing variable keeps placeholder."""
        result = template_tool.invoke({
            "template": "Hello, {{ name }}!",
            "context": {}
        })
        assert "{{ name }}" in result


class TestSplitTool:
    """Test split_tool functionality."""

    def test_split_newline(self):
        """Test splitting on newlines."""
        result = split_tool.invoke({"text": "a\nb\nc"})
        assert result == ["a", "b", "c"]

    def test_split_comma(self):
        """Test splitting on comma."""
        result = split_tool.invoke({"text": "a,b,c", "separator": ","})
        assert result == ["a", "b", "c"]

    def test_split_no_separator(self):
        """Test splitting with no matches."""
        result = split_tool.invoke({"text": "abc", "separator": ","})
        assert result == ["abc"]


class TestJoinTool:
    """Test join_tool functionality."""

    def test_join_default(self):
        """Test joining with default separator."""
        result = join_tool.invoke({"items": ["a", "b", "c"]})
        assert result == "a, b, c"

    def test_join_custom_separator(self):
        """Test joining with custom separator."""
        result = join_tool.invoke({"items": ["a", "b", "c"], "separator": " - "})
        assert result == "a - b - c"

    def test_join_empty_list(self):
        """Test joining empty list."""
        result = join_tool.invoke({"items": []})
        assert result == ""


class TestToJsonTool:
    """Test to_json_tool functionality."""

    def test_to_json_dict(self):
        """Test converting dict to JSON."""
        result = to_json_tool.invoke({"data": {"name": "test"}})
        parsed = json.loads(result)
        assert parsed == {"name": "test"}

    def test_to_json_list(self):
        """Test converting list to JSON."""
        result = to_json_tool.invoke({"data": [1, 2, 3]})
        parsed = json.loads(result)
        assert parsed == [1, 2, 3]

    def test_to_json_with_indent(self):
        """Test JSON with custom indent."""
        result = to_json_tool.invoke({"data": {"a": 1}, "indent": 4})
        assert "    " in result


class TestFromJsonTool:
    """Test from_json_tool functionality."""

    def test_from_json_dict(self):
        """Test parsing JSON dict."""
        result = from_json_tool.invoke({"json_str": '{"name": "test"}'})
        assert result == {"name": "test"}

    def test_from_json_list(self):
        """Test parsing JSON list."""
        result = from_json_tool.invoke({"json_str": '[1, 2, 3]'})
        assert result == [1, 2, 3]

    def test_from_json_invalid(self):
        """Test parsing invalid JSON."""
        result = from_json_tool.invoke({"json_str": "not json"})
        assert result is None


class TestTruncateTool:
    """Test truncate_tool functionality."""

    def test_truncate_short_text(self):
        """Test truncating short text (no change)."""
        result = truncate_tool.invoke({"text": "Hello", "max_length": 10})
        assert result == "Hello"

    def test_truncate_long_text(self):
        """Test truncating long text."""
        result = truncate_tool.invoke({"text": "Hello World", "max_length": 5})
        assert result == "Hello..."

    def test_truncate_custom_suffix(self):
        """Test truncating with custom suffix."""
        result = truncate_tool.invoke({
            "text": "Hello World",
            "max_length": 5,
            "suffix": "[...]"
        })
        assert result == "Hello[...]"


class TestReplaceTool:
    """Test replace_tool functionality."""

    def test_replace_all(self):
        """Test replacing all occurrences."""
        result = replace_tool.invoke({
            "text": "hello world world",
            "old": "world",
            "new": "earth"
        })
        assert result == "hello earth earth"

    def test_replace_limited(self):
        """Test replacing limited occurrences."""
        result = replace_tool.invoke({
            "text": "hello world world",
            "old": "world",
            "new": "earth",
            "count": 1
        })
        assert result == "hello earth world"

    def test_replace_no_match(self):
        """Test replacing with no matches."""
        result = replace_tool.invoke({
            "text": "hello",
            "old": "world",
            "new": "earth"
        })
        assert result == "hello"


class TestGetBuiltinTools:
    """Test get_builtin_tools registry."""

    def test_returns_dict(self):
        """Test that get_builtin_tools returns a dict."""
        tools = get_builtin_tools()
        assert isinstance(tools, dict)

    def test_contains_required_tools(self):
        """Test that registry contains required tools."""
        tools = get_builtin_tools()
        required = ["echo", "format", "json_extract", "split", "join"]
        for name in required:
            assert name in tools, f"Missing tool: {name}"

    def test_all_tools_callable(self):
        """Test that all tools are callable or StructuredTool."""
        from langchain_core.tools import BaseTool
        tools = get_builtin_tools()
        for name, tool in tools.items():
            # Tools are either callables or BaseTool instances (which are callable)
            is_tool = isinstance(tool, BaseTool)
            is_callable = callable(tool)
            assert is_callable or is_tool, f"Tool {name} is neither callable nor a BaseTool"
