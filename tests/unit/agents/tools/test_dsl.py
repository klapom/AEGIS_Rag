"""Unit tests for Tool Chain DSL.

Tests ChainBuilder fluent API, YAML/JSON parsing, and chain serialization.

Sprint 93 Feature 93.5: Tool Chain DSL (3 SP)
"""

import json

import pytest
import yaml

from src.agents.tools.composition import ToolChain, ToolStep, ToolStatus
from src.agents.tools.dsl import (
    ChainBuilder,
    DSLParseError,
    DSLValidationError,
    chain_to_json,
    chain_to_yaml,
    create_chain,
    parse_chain_json,
    parse_chain_yaml,
)


# =============================================================================
# ChainBuilder Tests
# =============================================================================


def test_chain_builder_basic():
    """Test basic ChainBuilder usage."""
    builder = ChainBuilder("test_chain", skill="research")

    assert builder.chain_id == "test_chain"
    assert builder.skill_name == "research"
    assert builder.steps == []
    assert builder.parallel_groups == []


def test_chain_builder_add_step():
    """Test adding steps to chain."""
    builder = ChainBuilder("test_chain")
    builder.add_step("search", "web_search", inputs={"query": "$user_query"})

    assert len(builder.steps) == 1
    assert builder.steps[0].name == "search"
    assert builder.steps[0].tool == "web_search"
    assert builder.steps[0].inputs == {"query": "$user_query"}
    assert builder.steps[0].output_key == "search"


def test_chain_builder_method_chaining():
    """Test fluent API method chaining."""
    builder = (
        ChainBuilder("test_chain", skill="research")
        .add_step("search", "web_search", inputs={"query": "$query"})
        .add_step("summarize", "llm_summarize", inputs={"text": "$search.result"})
        .set_output("summarize")
    )

    assert len(builder.steps) == 2
    assert builder._final_output == "summarize"


def test_chain_builder_parallel():
    """Test adding parallel execution groups."""
    builder = (
        ChainBuilder("test_chain")
        .add_step("search", "web_search", inputs={})
        .add_step("fetch", "http_get", inputs={})
        .run_parallel(["search", "fetch"])
    )

    assert len(builder.parallel_groups) == 1
    assert builder.parallel_groups[0] == ["search", "fetch"]


def test_chain_builder_with_condition():
    """Test adding conditional execution."""
    builder = ChainBuilder("test_chain")
    builder.add_step("search", "web_search", inputs={})
    builder.with_condition("search", lambda ctx: len(ctx.get("query", "")) > 0)

    assert "search" in builder._conditions
    assert callable(builder._conditions["search"])


def test_chain_builder_build():
    """Test building ToolChain from builder."""
    chain = (
        ChainBuilder("test_chain", skill="research")
        .add_step("search", "web_search", inputs={"query": "$query"})
        .add_step("summarize", "llm_summarize", inputs={"text": "$search"})
        .set_output("summarize")
        .build()
    )

    assert isinstance(chain, ToolChain)
    assert chain.id == "test_chain"
    assert chain.skill_name == "research"
    assert len(chain.steps) == 2
    assert chain.final_output_key == "summarize"


def test_chain_builder_step_options():
    """Test step with custom options."""
    builder = ChainBuilder("test_chain")
    builder.add_step(
        "search",
        "web_search",
        inputs={"query": "$query"},
        optional=True,
        max_retries=5,
        timeout_seconds=60.0,
    )

    step = builder.steps[0]
    assert step.optional is True
    assert step.max_retries == 5
    assert step.timeout_seconds == 60.0


# =============================================================================
# Validation Tests
# =============================================================================


def test_chain_builder_validation_empty():
    """Test validation fails for empty chain."""
    builder = ChainBuilder("test_chain")

    with pytest.raises(DSLValidationError, match="at least one step"):
        builder.build()


def test_chain_builder_validation_duplicate_names():
    """Test validation fails for duplicate step names."""
    builder = (
        ChainBuilder("test_chain")
        .add_step("search", "web_search", inputs={})
        .add_step("search", "another_tool", inputs={})
    )

    with pytest.raises(DSLValidationError, match="Duplicate step names"):
        builder.build()


def test_chain_builder_validation_parallel_unknown_step():
    """Test validation fails for parallel group with unknown step."""
    builder = (
        ChainBuilder("test_chain")
        .add_step("search", "web_search", inputs={})
        .run_parallel(["search", "unknown_step"])
    )

    with pytest.raises(DSLValidationError, match="unknown step"):
        builder.build()


def test_chain_builder_validation_invalid_output_key():
    """Test validation fails for invalid output key."""
    builder = (
        ChainBuilder("test_chain")
        .add_step("search", "web_search", inputs={})
        .set_output("nonexistent_step")
    )

    with pytest.raises(DSLValidationError, match="does not match any step"):
        builder.build()


# =============================================================================
# YAML Parser Tests
# =============================================================================


def test_parse_chain_yaml_basic():
    """Test parsing basic YAML chain."""
    yaml_str = """
id: research_chain
skill: research
steps:
  - name: search
    tool: web_search
    inputs:
      query: $user_query
  - name: summarize
    tool: llm_summarize
    inputs:
      text: $search.result
"""

    chain = parse_chain_yaml(yaml_str)

    assert chain.id == "research_chain"
    assert chain.skill_name == "research"
    assert len(chain.steps) == 2
    assert chain.steps[0].name == "search"
    assert chain.steps[0].tool == "web_search"
    assert chain.steps[0].inputs == {"query": "$user_query"}
    assert chain.steps[1].name == "summarize"
    assert chain.steps[1].inputs == {"text": "$search.result"}


def test_parse_chain_yaml_with_output():
    """Test parsing YAML with custom output key."""
    yaml_str = """
id: test_chain
steps:
  - name: step1
    tool: tool1
    inputs: {}
output: $step1
"""

    chain = parse_chain_yaml(yaml_str)
    assert chain.final_output_key == "step1"


def test_parse_chain_yaml_with_parallel():
    """Test parsing YAML with parallel groups."""
    yaml_str = """
id: test_chain
steps:
  - name: search
    tool: web_search
    inputs: {}
  - name: fetch
    tool: http_get
    inputs: {}
parallel:
  - [search, fetch]
"""

    chain = parse_chain_yaml(yaml_str)
    assert len(chain.parallel_groups) == 1
    assert chain.parallel_groups[0] == ["search", "fetch"]


def test_parse_chain_yaml_with_step_options():
    """Test parsing YAML with step options."""
    yaml_str = """
id: test_chain
steps:
  - name: search
    tool: web_search
    inputs: {}
    optional: true
    max_retries: 5
    timeout_seconds: 60.0
"""

    chain = parse_chain_yaml(yaml_str)
    step = chain.steps[0]
    assert step.optional is True
    assert step.max_retries == 5
    assert step.timeout_seconds == 60.0


def test_parse_chain_yaml_with_condition():
    """Test parsing YAML with conditional step."""
    yaml_str = """
id: test_chain
steps:
  - name: search
    tool: web_search
    inputs: {}
    condition: len($query) > 0
"""

    # Should parse without error (condition compilation deferred)
    chain = parse_chain_yaml(yaml_str)
    assert len(chain.steps) == 1


def test_parse_chain_yaml_invalid():
    """Test parsing invalid YAML."""
    yaml_str = """
    invalid: yaml: content
    :::
    """

    with pytest.raises(DSLParseError, match="Invalid YAML"):
        parse_chain_yaml(yaml_str)


def test_parse_chain_yaml_missing_id():
    """Test parsing YAML missing required 'id' field."""
    yaml_str = """
steps:
  - name: step1
    tool: tool1
    inputs: {}
"""

    with pytest.raises(DSLParseError, match="missing required 'id'"):
        parse_chain_yaml(yaml_str)


def test_parse_chain_yaml_missing_steps():
    """Test parsing YAML missing required 'steps' field."""
    yaml_str = """
id: test_chain
"""

    with pytest.raises(DSLParseError, match="missing required 'steps'"):
        parse_chain_yaml(yaml_str)


def test_parse_chain_yaml_invalid_step():
    """Test parsing YAML with invalid step structure."""
    yaml_str = """
id: test_chain
steps:
  - name: step1
    # Missing 'tool' field
    inputs: {}
"""

    with pytest.raises(DSLParseError, match="missing required"):
        parse_chain_yaml(yaml_str)


# =============================================================================
# JSON Parser Tests
# =============================================================================


def test_parse_chain_json_basic():
    """Test parsing basic JSON chain."""
    json_str = """
{
  "id": "research_chain",
  "skill": "research",
  "steps": [
    {
      "name": "search",
      "tool": "web_search",
      "inputs": {
        "query": "$user_query"
      }
    },
    {
      "name": "summarize",
      "tool": "llm_summarize",
      "inputs": {
        "text": "$search.result"
      }
    }
  ]
}
"""

    chain = parse_chain_json(json_str)

    assert chain.id == "research_chain"
    assert chain.skill_name == "research"
    assert len(chain.steps) == 2
    assert chain.steps[0].name == "search"
    assert chain.steps[1].name == "summarize"


def test_parse_chain_json_with_parallel():
    """Test parsing JSON with parallel groups."""
    json_str = """
{
  "id": "test_chain",
  "steps": [
    {"name": "search", "tool": "web_search", "inputs": {}},
    {"name": "fetch", "tool": "http_get", "inputs": {}}
  ],
  "parallel": [
    ["search", "fetch"]
  ]
}
"""

    chain = parse_chain_json(json_str)
    assert len(chain.parallel_groups) == 1
    assert chain.parallel_groups[0] == ["search", "fetch"]


def test_parse_chain_json_invalid():
    """Test parsing invalid JSON."""
    json_str = """
{
  "id": "test_chain"
  "missing_comma": true
}
"""

    with pytest.raises(DSLParseError, match="Invalid JSON"):
        parse_chain_json(json_str)


# =============================================================================
# Serialization Tests
# =============================================================================


def test_chain_to_yaml():
    """Test serializing ToolChain to YAML."""
    chain = (
        ChainBuilder("test_chain", skill="research")
        .add_step("search", "web_search", inputs={"query": "$query"})
        .add_step("summarize", "llm_summarize", inputs={"text": "$search"})
        .set_output("summarize")
        .build()
    )

    yaml_str = chain_to_yaml(chain)

    # Parse back and verify
    parsed_chain = parse_chain_yaml(yaml_str)
    assert parsed_chain.id == chain.id
    assert parsed_chain.skill_name == chain.skill_name
    assert len(parsed_chain.steps) == len(chain.steps)


def test_chain_to_json():
    """Test serializing ToolChain to JSON."""
    chain = (
        ChainBuilder("test_chain", skill="research")
        .add_step("search", "web_search", inputs={"query": "$query"})
        .set_output("search")
        .build()
    )

    json_str = chain_to_json(chain)

    # Parse back and verify
    parsed_chain = parse_chain_json(json_str)
    assert parsed_chain.id == chain.id
    assert parsed_chain.skill_name == chain.skill_name
    assert len(parsed_chain.steps) == len(chain.steps)


def test_chain_to_yaml_with_parallel():
    """Test serializing chain with parallel groups to YAML."""
    chain = (
        ChainBuilder("test_chain")
        .add_step("search", "web_search", inputs={})
        .add_step("fetch", "http_get", inputs={})
        .run_parallel(["search", "fetch"])
        .build()
    )

    yaml_str = chain_to_yaml(chain)
    parsed = parse_chain_yaml(yaml_str)

    assert len(parsed.parallel_groups) == 1
    assert parsed.parallel_groups[0] == ["search", "fetch"]


# =============================================================================
# Factory Function Tests
# =============================================================================


def test_create_chain_factory():
    """Test create_chain factory function."""
    builder = create_chain("test_chain", skill="research")

    assert isinstance(builder, ChainBuilder)
    assert builder.chain_id == "test_chain"
    assert builder.skill_name == "research"


def test_create_chain_with_steps():
    """Test factory function with method chaining."""
    chain = (
        create_chain("test_chain")
        .add_step("search", "web_search", inputs={"query": "$query"})
        .build()
    )

    assert isinstance(chain, ToolChain)
    assert chain.id == "test_chain"
    assert len(chain.steps) == 1


# =============================================================================
# Integration Tests
# =============================================================================


def test_yaml_roundtrip():
    """Test YAML serialization roundtrip."""
    original = (
        ChainBuilder("test_chain", skill="research")
        .add_step("search", "web_search", inputs={"query": "$query"})
        .add_step("summarize", "llm_summarize", inputs={"text": "$search"})
        .run_parallel(["search", "summarize"])
        .set_output("summarize")
        .build()
    )

    yaml_str = chain_to_yaml(original)
    parsed = parse_chain_yaml(yaml_str)

    assert parsed.id == original.id
    assert parsed.skill_name == original.skill_name
    assert len(parsed.steps) == len(original.steps)
    assert parsed.final_output_key == original.final_output_key
    assert parsed.parallel_groups == original.parallel_groups


def test_json_roundtrip():
    """Test JSON serialization roundtrip."""
    original = (
        ChainBuilder("test_chain", skill="research")
        .add_step("search", "web_search", inputs={"query": "$query"})
        .set_output("search")
        .build()
    )

    json_str = chain_to_json(original)
    parsed = parse_chain_json(json_str)

    assert parsed.id == original.id
    assert parsed.skill_name == original.skill_name
    assert len(parsed.steps) == len(original.steps)
    assert parsed.final_output_key == original.final_output_key


def test_complex_chain_example():
    """Test complex chain with all features."""
    yaml_str = """
id: deep_research
skill: research
steps:
  - name: search
    tool: web_search
    inputs:
      query: $user_query
    optional: false
    max_retries: 3
    timeout_seconds: 30.0
  - name: fetch_top
    tool: browser
    inputs:
      action: navigate
      url: $search.results[0].url
    optional: true
  - name: extract
    tool: parse_html
    inputs:
      html: $fetch_top.content
  - name: summarize
    tool: llm_summarize
    inputs:
      text: $extract.text
parallel:
  - [search, fetch_top]
output: $summarize
"""

    chain = parse_chain_yaml(yaml_str)

    assert chain.id == "deep_research"
    assert chain.skill_name == "research"
    assert len(chain.steps) == 4
    assert chain.steps[0].name == "search"
    assert chain.steps[0].max_retries == 3
    assert chain.steps[1].optional is True
    assert len(chain.parallel_groups) == 1
    assert chain.final_output_key == "summarize"


def test_builder_matches_yaml():
    """Test that builder API produces same result as YAML parser."""
    yaml_str = """
id: test_chain
skill: research
steps:
  - name: search
    tool: web_search
    inputs:
      query: $query
  - name: summarize
    tool: llm_summarize
    inputs:
      text: $search
output: $summarize
"""

    yaml_chain = parse_chain_yaml(yaml_str)

    builder_chain = (
        ChainBuilder("test_chain", skill="research")
        .add_step("search", "web_search", inputs={"query": "$query"})
        .add_step("summarize", "llm_summarize", inputs={"text": "$search"})
        .set_output("summarize")
        .build()
    )

    # Compare key attributes
    assert yaml_chain.id == builder_chain.id
    assert yaml_chain.skill_name == builder_chain.skill_name
    assert len(yaml_chain.steps) == len(builder_chain.steps)
    assert yaml_chain.final_output_key == builder_chain.final_output_key

    for yaml_step, builder_step in zip(yaml_chain.steps, builder_chain.steps):
        assert yaml_step.name == builder_step.name
        assert yaml_step.tool == builder_step.tool
        assert yaml_step.inputs == builder_step.inputs
