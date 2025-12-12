"""Prompt Extraction from DSPy Optimized Modules.

Sprint 45 - Feature 45.2: DSPy Integration Service

This module provides utilities for extracting static prompts from DSPy optimized modules.
The extracted prompts can be used in production WITHOUT requiring DSPy, reducing dependencies
and improving inference performance.

Key Features:
- Extract instructions and examples from DSPy modules
- Format as production-ready prompt templates
- Support for both entity and relation extraction
- Few-shot example formatting
- Lightweight and dependency-free (only uses DSPy results)

Architecture:
    DSPy Optimized Module → Prompt Extractor → Static Prompt Template
    ├── Extract instructions
    ├── Extract few-shot demos
    └── Format as production template

Usage:
    >>> from src.components.domain_training import DSPyOptimizer, extract_prompt_from_dspy
    >>> optimizer = DSPyOptimizer()
    >>> result = await optimizer.optimize_entity_extraction(training_data)
    >>> prompt = extract_prompt_from_dspy_result(result)
    >>> print(prompt["prompt_template"])
"""

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def extract_prompt_from_dspy_result(optimized_result: dict[str, Any]) -> dict[str, Any]:
    """Extract static prompt from DSPy optimization result.

    This function converts DSPy optimization results into a production-ready prompt
    template that can be used without DSPy. The template includes instructions and
    few-shot examples formatted for direct use with LLMs.

    Args:
        optimized_result: Result dictionary from DSPyOptimizer with keys:
            - instructions: str (optimized instructions)
            - demos: list[dict] (few-shot examples with input/output)
            - metrics: dict (evaluation metrics)

    Returns:
        Dictionary with prompt components:
        {
            "prompt_template": str,      # Full prompt with instructions and examples
            "instructions": str,         # Standalone instructions
            "demos": list[dict],         # Few-shot examples
            "example_format": str,       # Format string for examples
            "metrics": dict              # Copy of optimization metrics
        }

    Example:
        >>> result = await optimizer.optimize_entity_extraction(data)
        >>> prompt = extract_prompt_from_dspy_result(result)
        >>> print(prompt["prompt_template"])
        # Instructions:
        # Extract a THOROUGH list of key entities from the source text.
        #
        # Examples:
        # Input: "Apple acquired Siri in 2010."
        # Output: ["Apple", "Siri", "2010"]
        # ...
    """
    if not optimized_result:
        raise ValueError("optimized_result cannot be empty")

    instructions = optimized_result.get("instructions", "")
    demos = optimized_result.get("demos", [])
    metrics = optimized_result.get("metrics", {})

    logger.info(
        "extracting_prompt_from_dspy",
        num_demos=len(demos),
        instructions_length=len(instructions),
    )

    # Format few-shot examples
    formatted_examples = []
    for i, demo in enumerate(demos):
        input_data = demo.get("input", {})
        output_data = demo.get("output", {})

        # Determine extraction type based on output structure
        if "entities" in output_data:
            # Entity extraction example
            formatted_example = _format_entity_example(input_data, output_data, i + 1)
        elif "relations" in output_data:
            # Relation extraction example
            formatted_example = _format_relation_example(input_data, output_data, i + 1)
        else:
            logger.warning("unknown_demo_format", demo=demo)
            continue

        formatted_examples.append(formatted_example)

    # Build full prompt template
    example_section = "\n\n".join(formatted_examples) if formatted_examples else "No examples."

    prompt_template = f"""# Instructions:
{instructions}

# Examples:
{example_section}

# Task:
Now apply these instructions to extract information from the following text.
"""

    result = {
        "prompt_template": prompt_template,
        "instructions": instructions,
        "demos": demos,
        "example_format": _get_example_format(demos),
        "metrics": metrics,
        "num_examples": len(demos),
    }

    logger.info(
        "prompt_extracted",
        template_length=len(prompt_template),
        num_examples=len(demos),
        metrics=metrics,
    )

    return result


def _format_entity_example(
    input_data: dict[str, Any], output_data: dict[str, Any], example_num: int
) -> str:
    """Format entity extraction example.

    Args:
        input_data: Input fields (source_text)
        output_data: Output fields (entities)
        example_num: Example number for labeling

    Returns:
        Formatted example string
    """
    source_text = input_data.get("source_text", "")
    entities = output_data.get("entities", [])

    # Truncate long text for readability
    if len(source_text) > 200:
        source_text = source_text[:200] + "..."

    return f"""Example {example_num}:
Input: "{source_text}"
Output: {entities}"""


def _format_relation_example(
    input_data: dict[str, Any], output_data: dict[str, Any], example_num: int
) -> str:
    """Format relation extraction example.

    Args:
        input_data: Input fields (source_text, entities)
        output_data: Output fields (relations)
        example_num: Example number for labeling

    Returns:
        Formatted example string
    """
    source_text = input_data.get("source_text", "")
    entities = input_data.get("entities", [])
    relations = output_data.get("relations", [])

    # Truncate long text for readability
    if len(source_text) > 200:
        source_text = source_text[:200] + "..."

    # Format relations as readable triples
    formatted_relations = []
    for rel in relations:
        if isinstance(rel, dict) and all(k in rel for k in ["subject", "predicate", "object"]):
            formatted_relations.append(
                f"  - ({rel['subject']}) --[{rel['predicate']}]--> ({rel['object']})"
            )

    relations_str = "\n".join(formatted_relations) if formatted_relations else "  No relations"

    return f"""Example {example_num}:
Input Text: "{source_text}"
Known Entities: {entities}
Output Relations:
{relations_str}"""


def _get_example_format(demos: list[dict[str, Any]]) -> str:
    """Determine example format type from demos.

    Args:
        demos: List of demonstration examples

    Returns:
        Format type string: "entity_extraction" or "relation_extraction"
    """
    if not demos:
        return "unknown"

    first_demo = demos[0]
    output_data = first_demo.get("output", {})

    if "entities" in output_data:
        return "entity_extraction"
    elif "relations" in output_data:
        return "relation_extraction"
    else:
        return "unknown"


def format_prompt_for_production(
    prompt_data: dict[str, Any], task_text: str, entities: list[str] | None = None
) -> str:
    """Format a production-ready prompt with task-specific data.

    This function takes the extracted prompt template and fills it with
    task-specific data (text to extract from, optional entities).

    Args:
        prompt_data: Dictionary from extract_prompt_from_dspy_result
        task_text: Text to extract information from
        entities: Optional list of entities (for relation extraction)

    Returns:
        Complete formatted prompt ready for LLM inference

    Example:
        >>> prompt_data = extract_prompt_from_dspy_result(result)
        >>> full_prompt = format_prompt_for_production(
        ...     prompt_data,
        ...     task_text="Tesla builds electric cars in California.",
        ...     entities=["Tesla", "electric cars", "California"]
        ... )
    """
    if not prompt_data or "prompt_template" not in prompt_data:
        raise ValueError("Invalid prompt_data: missing prompt_template")

    prompt_template = prompt_data["prompt_template"]
    example_format = prompt_data.get("example_format", "unknown")

    # Build task section based on format type
    if example_format == "entity_extraction":
        task_section = f"""
Source Text: "{task_text}"

Please extract all key entities from the above text."""
    elif example_format == "relation_extraction":
        if entities is None:
            raise ValueError("entities parameter required for relation extraction")
        task_section = f"""
Source Text: "{task_text}"
Known Entities: {entities}

Please extract all relations (subject-predicate-object triples) from the above text."""
    else:
        task_section = f"""
Text: "{task_text}"

Please extract the requested information from the above text."""

    # Combine template with task
    full_prompt = f"""{prompt_template}

{task_section}
"""

    logger.info(
        "production_prompt_formatted",
        format_type=example_format,
        text_length=len(task_text),
        prompt_length=len(full_prompt),
    )

    return full_prompt


def save_prompt_template(prompt_data: dict[str, Any], output_path: str) -> None:
    """Save extracted prompt template to file.

    Args:
        prompt_data: Dictionary from extract_prompt_from_dspy_result
        output_path: Path to save prompt template (e.g., "prompts/entity_extraction.txt")

    Raises:
        ValueError: If prompt_data is invalid
        IOError: If file cannot be written
    """
    import json
    from pathlib import Path

    if not prompt_data or "prompt_template" not in prompt_data:
        raise ValueError("Invalid prompt_data: missing prompt_template")

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Save as JSON for structured storage
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "prompt_template": prompt_data["prompt_template"],
                "instructions": prompt_data["instructions"],
                "example_format": prompt_data.get("example_format", "unknown"),
                "num_examples": prompt_data.get("num_examples", 0),
                "metrics": prompt_data.get("metrics", {}),
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    logger.info("prompt_template_saved", output_path=str(output_file))
