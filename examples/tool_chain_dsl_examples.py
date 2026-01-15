"""Tool Chain DSL Usage Examples.

Sprint 93 Feature 93.5: Tool Chain DSL (3 SP)

This file demonstrates how to use the Tool Chain DSL for defining
and executing tool chains declaratively and programmatically.

Examples:
    1. YAML-based chain definition
    2. JSON-based chain definition
    3. Python ChainBuilder fluent API
    4. Variable interpolation
    5. Conditional execution
    6. Parallel execution groups
    7. Chain serialization
"""

import asyncio

from src.agents.tools.composition import ToolComposer
from src.agents.tools.dsl import (
    ChainBuilder,
    chain_to_json,
    chain_to_yaml,
    create_chain,
    parse_chain_json,
    parse_chain_yaml,
)


# =============================================================================
# Example 1: YAML-based Chain Definition
# =============================================================================


def example_yaml_chain():
    """Example: Define a research chain using YAML."""
    yaml_config = """
id: deep_research_chain
skill: research
steps:
  - name: web_search
    tool: web_search
    inputs:
      query: $user_query
    max_retries: 3
    timeout_seconds: 30.0

  - name: browse_top_result
    tool: browser
    inputs:
      action: navigate
      url: $web_search.results[0].url
    optional: true  # Continue if browsing fails

  - name: extract_content
    tool: parse_html
    inputs:
      html: $browse_top_result.content

  - name: summarize
    tool: llm_summarize
    inputs:
      text: $extract_content.text
      max_length: 500

parallel:
  - [web_search, browse_top_result]  # Run search and browsing in parallel

output: $summarize
"""

    chain = parse_chain_yaml(yaml_config)

    print("YAML Chain Definition:")
    print(f"  Chain ID: {chain.id}")
    print(f"  Skill: {chain.skill_name}")
    print(f"  Steps: {len(chain.steps)}")
    print(f"  Parallel Groups: {len(chain.parallel_groups)}")
    print(f"  Final Output: {chain.final_output_key}")
    print()

    return chain


# =============================================================================
# Example 2: JSON-based Chain Definition
# =============================================================================


def example_json_chain():
    """Example: Define a data processing chain using JSON."""
    json_config = """
{
  "id": "data_pipeline",
  "skill": "data_processing",
  "steps": [
    {
      "name": "fetch",
      "tool": "http_get",
      "inputs": {
        "url": "$data_url"
      }
    },
    {
      "name": "parse",
      "tool": "json_parse",
      "inputs": {
        "json_str": "$fetch.body"
      }
    },
    {
      "name": "transform",
      "tool": "data_transform",
      "inputs": {
        "data": "$parse.result",
        "schema": "$target_schema"
      }
    }
  ],
  "output": "$transform"
}
"""

    chain = parse_chain_json(json_config)

    print("JSON Chain Definition:")
    print(f"  Chain ID: {chain.id}")
    print(f"  Skill: {chain.skill_name}")
    print(f"  Steps: {[s.name for s in chain.steps]}")
    print()

    return chain


# =============================================================================
# Example 3: Python ChainBuilder Fluent API
# =============================================================================


def example_builder_api():
    """Example: Build a chain using the fluent Python API."""
    chain = (
        ChainBuilder("automation_chain", skill="web_automation")
        # Step 1: Search for information
        .add_step(
            "search",
            "web_search",
            inputs={"query": "$search_query"},
            max_retries=3,
        )
        # Step 2: Extract links
        .add_step(
            "extract_links",
            "parse_links",
            inputs={"html": "$search.results[0].content"},
        )
        # Step 3: Visit each link (optional)
        .add_step(
            "visit_links",
            "browser_batch",
            inputs={"urls": "$extract_links.urls"},
            optional=True,  # Continue even if some links fail
        )
        # Step 4: Aggregate results
        .add_step(
            "aggregate",
            "data_merge",
            inputs={"sources": ["$search", "$visit_links"]},
        )
        # Configure parallel execution
        .run_parallel(["search", "extract_links"])
        # Set final output
        .set_output("aggregate")
        # Build the chain
        .build()
    )

    print("ChainBuilder Fluent API:")
    print(f"  Chain ID: {chain.id}")
    print(f"  Skill: {chain.skill_name}")
    print(f"  Steps:")
    for step in chain.steps:
        print(f"    - {step.name} ({step.tool})")
        if step.optional:
            print(f"      [OPTIONAL]")
    print()

    return chain


# =============================================================================
# Example 4: Variable Interpolation
# =============================================================================


def example_variable_interpolation():
    """Example: Demonstrate variable interpolation patterns."""
    chain = (
        create_chain("variable_demo", skill="demo")
        # Direct variable reference
        .add_step("step1", "tool1", inputs={"param": "$user_input"})
        # Nested object reference
        .add_step("step2", "tool2", inputs={"data": "$step1.result.data"})
        # Array indexing
        .add_step("step3", "tool3", inputs={"first": "$step2.items[0]"})
        # Multiple references
        .add_step(
            "step4",
            "tool4",
            inputs={
                "a": "$step1.output",
                "b": "$step2.output",
                "c": "$step3.output",
            },
        )
        .build()
    )

    print("Variable Interpolation Examples:")
    for step in chain.steps:
        print(f"  Step: {step.name}")
        for key, value in step.inputs.items():
            print(f"    {key}: {value}")
    print()

    return chain


# =============================================================================
# Example 5: Conditional Execution
# =============================================================================


def example_conditional_execution():
    """Example: Add conditional logic to chains."""
    chain = (
        ChainBuilder("conditional_chain", skill="research")
        .add_step("search", "web_search", inputs={"query": "$query"})
        # Add condition: only summarize if search returned results
        .add_step("summarize", "llm_summarize", inputs={"text": "$search.results"})
        # Conditions are stored in the builder
        .with_condition(
            "summarize",
            lambda ctx: len(ctx.get("search", {}).get("results", [])) > 0,
        )
        .build()
    )

    print("Conditional Execution:")
    print(f"  Chain: {chain.id}")
    print(f"  Steps with conditions: {list(chain.context.get('_conditions', {}).keys())}")
    print()

    return chain


# =============================================================================
# Example 6: Parallel Execution Groups
# =============================================================================


def example_parallel_execution():
    """Example: Configure parallel execution for independent steps."""
    chain = (
        ChainBuilder("parallel_chain", skill="research")
        # These steps can run in parallel
        .add_step("search_google", "web_search", inputs={"engine": "google", "query": "$query"})
        .add_step("search_bing", "web_search", inputs={"engine": "bing", "query": "$query"})
        .add_step("search_wiki", "wiki_search", inputs={"query": "$query"})
        # Mark for parallel execution
        .run_parallel(["search_google", "search_bing", "search_wiki"])
        # Merge results after parallel execution
        .add_step(
            "merge",
            "merge_results",
            inputs={
                "sources": ["$search_google", "$search_bing", "$search_wiki"]
            },
        )
        .set_output("merge")
        .build()
    )

    print("Parallel Execution:")
    print(f"  Chain: {chain.id}")
    print(f"  Parallel Groups:")
    for i, group in enumerate(chain.parallel_groups):
        print(f"    Group {i+1}: {group}")
    print()

    return chain


# =============================================================================
# Example 7: Chain Serialization
# =============================================================================


def example_serialization():
    """Example: Serialize chains to YAML/JSON."""
    # Build a chain
    chain = (
        create_chain("serialization_demo", skill="demo")
        .add_step("step1", "tool1", inputs={"input": "$data"})
        .add_step("step2", "tool2", inputs={"result": "$step1"})
        .build()
    )

    # Serialize to YAML
    yaml_str = chain_to_yaml(chain)
    print("Serialized to YAML:")
    print(yaml_str)

    # Serialize to JSON
    json_str = chain_to_json(chain)
    print("Serialized to JSON:")
    print(json_str)
    print()

    # Round-trip: parse YAML back to chain
    parsed_chain = parse_chain_yaml(yaml_str)
    print(f"Round-trip successful: {parsed_chain.id == chain.id}")
    print()


# =============================================================================
# Example 8: Complete Research Pipeline
# =============================================================================


def example_complete_research_pipeline():
    """Example: Complete research automation pipeline."""
    yaml_config = """
id: complete_research
skill: research
steps:
  # Stage 1: Multi-source search
  - name: web_search
    tool: web_search
    inputs:
      query: $research_topic
      max_results: 10
    max_retries: 3

  - name: academic_search
    tool: arxiv_search
    inputs:
      query: $research_topic
      max_results: 5
    optional: true

  # Stage 2: Content extraction
  - name: browse_top_results
    tool: browser_batch
    inputs:
      urls: $web_search.top_urls
      max_pages: 5

  # Stage 3: Analysis
  - name: extract_entities
    tool: ner_extract
    inputs:
      texts: $browse_top_results.contents

  - name: extract_relations
    tool: relation_extract
    inputs:
      texts: $browse_top_results.contents
      entities: $extract_entities.entities

  # Stage 4: Synthesis
  - name: summarize_findings
    tool: llm_summarize
    inputs:
      texts: $browse_top_results.contents
      max_length: 1000

  - name: generate_report
    tool: report_generator
    inputs:
      summary: $summarize_findings.result
      entities: $extract_entities.entities
      relations: $extract_relations.relations
      sources: $web_search.sources

# Parallel execution configuration
parallel:
  - [web_search, academic_search]  # Search in parallel
  - [extract_entities, extract_relations]  # Extract in parallel

output: $generate_report
"""

    chain = parse_chain_yaml(yaml_config)

    print("Complete Research Pipeline:")
    print(f"  Chain ID: {chain.id}")
    print(f"  Total Steps: {len(chain.steps)}")
    print(f"  Parallel Stages: {len(chain.parallel_groups)}")
    print()
    print("  Execution Flow:")
    for i, step in enumerate(chain.steps, 1):
        optional = " [OPTIONAL]" if step.optional else ""
        print(f"    {i}. {step.name} ({step.tool}){optional}")
    print()


# =============================================================================
# Main Execution
# =============================================================================


def main():
    """Run all examples."""
    print("=" * 70)
    print("Tool Chain DSL Examples")
    print("=" * 70)
    print()

    example_yaml_chain()
    example_json_chain()
    example_builder_api()
    example_variable_interpolation()
    example_conditional_execution()
    example_parallel_execution()
    example_serialization()
    example_complete_research_pipeline()

    print("=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
