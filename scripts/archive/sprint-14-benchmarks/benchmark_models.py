#!/usr/bin/env python3
"""Benchmark script to compare LLM models for LightRAG entity/relation extraction.

Sprint 13 TD-31: Compare Gemma-3-4b-it, Qwen3-4B, and Llama3.2:3b on:
- Entity extraction quality
- Relation extraction quality
- Execution time

Uses prompts similar to LightRAG's internal extraction prompts.
"""

import asyncio
import json
import time
from typing import Any

from ollama import AsyncClient

# Test document (same as used in tests)
TEST_TEXT = """
Python is a programming language created by Guido van Rossum.
It was first released in 1991 and emphasizes code readability.
Python supports multiple programming paradigms including procedural,
object-oriented, and functional programming.
"""

# Entity extraction prompt (based on LightRAG patterns)
ENTITY_EXTRACTION_SYSTEM_PROMPT = """You are an expert entity extractor. Your task is to identify and extract named entities from text.

Extract entities of these types:
- PERSON: People, characters, historical figures
- ORGANIZATION: Companies, institutions, groups
- LOCATION: Cities, countries, places
- EVENT: Historical events, conferences, releases
- TECHNOLOGY: Programming languages, frameworks, tools
- CONCEPT: Abstract concepts, paradigms, methodologies

For each entity, provide:
- name: The entity name
- type: Entity type (PERSON, ORGANIZATION, etc.)
- description: Brief description of the entity

Return ONLY a valid JSON array with no additional text or markdown."""

ENTITY_EXTRACTION_USER_PROMPT = f"""Extract all entities from this text:

{TEST_TEXT}

Return a JSON array like this:
[
  {{"name": "Python", "type": "TECHNOLOGY", "description": "Programming language"}},
  {{"name": "Guido van Rossum", "type": "PERSON", "description": "Creator of Python"}}
]

IMPORTANT: Return ONLY the JSON array, no markdown code fences, no explanations."""


# Relation extraction prompt (based on LightRAG patterns)
RELATION_EXTRACTION_SYSTEM_PROMPT = """You are an expert relationship extractor. Your task is to identify relationships between entities.

For each relationship, provide:
- source: Source entity name
- target: Target entity name
- relation_type: Type of relationship (CREATED_BY, PART_OF, SUPPORTS, etc.)
- description: Brief description

Return ONLY a valid JSON array with no additional text or markdown."""

RELATION_EXTRACTION_USER_PROMPT = f"""Extract all relationships from this text:

{TEST_TEXT}

Return a JSON array like this:
[
  {{"source": "Python", "target": "Guido van Rossum", "relation_type": "CREATED_BY", "description": "Python was created by Guido van Rossum"}},
  {{"source": "Python", "target": "object-oriented", "relation_type": "SUPPORTS", "description": "Python supports object-oriented programming"}}
]

IMPORTANT: Return ONLY the JSON array, no markdown code fences, no explanations."""


async def extract_entities(model: str, client: AsyncClient) -> dict[str, Any]:
    """Extract entities using specified model.

    Args:
        model: Ollama model name
        client: Ollama async client

    Returns:
        Dictionary with entities list, execution time, and error info
    """
    start_time = time.perf_counter()

    try:
        response = await client.chat(
            model=model,
            messages=[
                {"role": "system", "content": ENTITY_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": ENTITY_EXTRACTION_USER_PROMPT},
            ],
            options={
                "temperature": 0.1,  # Low temperature for consistency
                "num_predict": 2048,
                "num_ctx": 32768,  # All models support this
            },
        )

        elapsed = time.perf_counter() - start_time
        content = response.get("message", {}).get("content", "")

        # Try to parse JSON
        entities = []
        parse_error = None
        try:
            # Try direct parse
            entities = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code fence
            import re

            json_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, re.DOTALL)
            if json_match:
                try:
                    entities = json.loads(json_match.group(1))
                except json.JSONDecodeError as e:
                    parse_error = f"Failed to parse JSON from code fence: {e}"
            else:
                # Try to find JSON array pattern
                json_match = re.search(r"\[.*\]", content, re.DOTALL)
                if json_match:
                    try:
                        entities = json.loads(json_match.group(0))
                    except json.JSONDecodeError as e:
                        parse_error = f"Failed to parse JSON array: {e}"
                else:
                    parse_error = "No JSON array found in response"

        return {
            "model": model,
            "task": "entity_extraction",
            "entities": entities,
            "entity_count": len(entities) if isinstance(entities, list) else 0,
            "execution_time": elapsed,
            "raw_response": content,
            "parse_error": parse_error,
            "success": parse_error is None,
        }

    except Exception as e:
        elapsed = time.perf_counter() - start_time
        return {
            "model": model,
            "task": "entity_extraction",
            "entities": [],
            "entity_count": 0,
            "execution_time": elapsed,
            "error": str(e),
            "success": False,
        }


async def extract_relations(model: str, client: AsyncClient) -> dict[str, Any]:
    """Extract relations using specified model.

    Args:
        model: Ollama model name
        client: Ollama async client

    Returns:
        Dictionary with relations list, execution time, and error info
    """
    start_time = time.perf_counter()

    try:
        response = await client.chat(
            model=model,
            messages=[
                {"role": "system", "content": RELATION_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": RELATION_EXTRACTION_USER_PROMPT},
            ],
            options={
                "temperature": 0.1,
                "num_predict": 2048,
                "num_ctx": 32768,
            },
        )

        elapsed = time.perf_counter() - start_time
        content = response.get("message", {}).get("content", "")

        # Try to parse JSON
        relations = []
        parse_error = None
        try:
            relations = json.loads(content)
        except json.JSONDecodeError:
            import re

            json_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, re.DOTALL)
            if json_match:
                try:
                    relations = json.loads(json_match.group(1))
                except json.JSONDecodeError as e:
                    parse_error = f"Failed to parse JSON from code fence: {e}"
            else:
                json_match = re.search(r"\[.*\]", content, re.DOTALL)
                if json_match:
                    try:
                        relations = json.loads(json_match.group(0))
                    except json.JSONDecodeError as e:
                        parse_error = f"Failed to parse JSON array: {e}"
                else:
                    parse_error = "No JSON array found in response"

        return {
            "model": model,
            "task": "relation_extraction",
            "relations": relations,
            "relation_count": len(relations) if isinstance(relations, list) else 0,
            "execution_time": elapsed,
            "raw_response": content,
            "parse_error": parse_error,
            "success": parse_error is None,
        }

    except Exception as e:
        elapsed = time.perf_counter() - start_time
        return {
            "model": model,
            "task": "relation_extraction",
            "relations": [],
            "relation_count": 0,
            "execution_time": elapsed,
            "error": str(e),
            "success": False,
        }


async def benchmark_model(model: str, client: AsyncClient) -> dict[str, Any]:
    """Run full benchmark on a model.

    Args:
        model: Ollama model name
        client: Ollama async client

    Returns:
        Dictionary with benchmark results
    """
    print(f"\n{'='*80}")
    print(f"Benchmarking: {model}")
    print(f"{'='*80}")

    # Entity extraction
    print("\n[1/2] Running entity extraction...")
    entity_result = await extract_entities(model, client)
    print(f"  [OK] Entities: {entity_result['entity_count']}")
    print(f"  [OK] Time: {entity_result['execution_time']:.2f}s")
    if entity_result.get("parse_error"):
        print(f"  [WARN] Parse Error: {entity_result['parse_error']}")

    # Relation extraction
    print("\n[2/2] Running relation extraction...")
    relation_result = await extract_relations(model, client)
    print(f"  [OK] Relations: {relation_result['relation_count']}")
    print(f"  [OK] Time: {relation_result['execution_time']:.2f}s")
    if relation_result.get("parse_error"):
        print(f"  [WARN] Parse Error: {relation_result['parse_error']}")

    total_time = entity_result["execution_time"] + relation_result["execution_time"]
    success = entity_result["success"] and relation_result["success"]

    return {
        "model": model,
        "entity_extraction": entity_result,
        "relation_extraction": relation_result,
        "total_execution_time": total_time,
        "success": success,
    }


async def main():
    """Run benchmark on all three models."""
    print(
        """
================================================================================
           LightRAG Model Benchmark - Entity & Relation Extraction
================================================================================

Sprint 13 TD-31: Comparing 4 models on LightRAG extraction tasks
Models: Gemma-3-4b-it, Qwen3-4B (HF GGUF), Qwen3-4B (standard), Llama3.2:3b
    """
    )

    # Model list
    models = [
        "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q8_0",
        "hf.co/MaziyarPanahi/Qwen3-4B-GGUF:Q6_K",
        "qwen3:4b",
        "llama3.2:3b",
    ]

    # Initialize Ollama client
    client = AsyncClient(host="http://localhost:11434")

    # Run benchmarks
    results = []
    for model in models:
        try:
            result = await benchmark_model(model, client)
            results.append(result)
        except Exception as e:
            print(f"\n[ERROR] Error benchmarking {model}: {e}")
            results.append(
                {
                    "model": model,
                    "error": str(e),
                    "success": False,
                }
            )

    # Print comparison table
    print(f"\n{'='*80}")
    print("BENCHMARK RESULTS - COMPARISON")
    print(f"{'='*80}\n")

    # Header
    print(f"{'Model':<40} {'Entities':<12} {'Relations':<12} {'Total Time':<15} {'Status'}")
    print(f"{'-'*40} {'-'*12} {'-'*12} {'-'*15} {'-'*10}")

    # Results
    for result in results:
        if result.get("success"):
            model_name = (
                result["model"].split("/")[-1] if "/" in result["model"] else result["model"]
            )
            entity_count = result["entity_extraction"]["entity_count"]
            relation_count = result["relation_extraction"]["relation_count"]
            total_time = result["total_execution_time"]
            status = "[OK]"

            print(
                f"{model_name:<40} {entity_count:<12} {relation_count:<12} {total_time:<14.2f}s {status}"
            )
        else:
            model_name = (
                result["model"].split("/")[-1] if "/" in result["model"] else result["model"]
            )
            print(f"{model_name:<40} {'N/A':<12} {'N/A':<12} {'N/A':<15} [ERROR]")

    # Quality analysis
    print(f"\n{'='*80}")
    print("QUALITY ANALYSIS")
    print(f"{'='*80}\n")

    for result in results:
        if result.get("success"):
            model_name = (
                result["model"].split("/")[-1] if "/" in result["model"] else result["model"]
            )
            print(f"\n{model_name}:")

            # Entity quality
            entities = result["entity_extraction"].get("entities", [])
            if entities:
                print(f"  Entities ({len(entities)}):")
                for entity in entities[:3]:  # Show first 3
                    print(f"    - {entity.get('name', 'N/A')} ({entity.get('type', 'N/A')})")
                if len(entities) > 3:
                    print(f"    ... and {len(entities) - 3} more")

            # Relation quality
            relations = result["relation_extraction"].get("relations", [])
            if relations:
                print(f"  Relations ({len(relations)}):")
                for relation in relations[:3]:  # Show first 3
                    source = relation.get("source", "N/A")
                    target = relation.get("target", "N/A")
                    rel_type = relation.get("relation_type", "N/A")
                    print(f"    - {source} --[{rel_type}]--> {target}")
                if len(relations) > 3:
                    print(f"    ... and {len(relations) - 3} more")

    # Recommendation
    print(f"\n{'='*80}")
    print("RECOMMENDATION")
    print(f"{'='*80}\n")

    successful_results = [r for r in results if r.get("success")]
    if successful_results:
        # Find best by total entities + relations
        best = max(
            successful_results,
            key=lambda r: (
                r["entity_extraction"]["entity_count"] + r["relation_extraction"]["relation_count"]
            ),
        )

        best_name = best["model"].split("/")[-1] if "/" in best["model"] else best["model"]
        print(f"Best Quality: {best_name}")
        print(f"  - Entities: {best['entity_extraction']['entity_count']}")
        print(f"  - Relations: {best['relation_extraction']['relation_count']}")
        print(f"  - Time: {best['total_execution_time']:.2f}s")

        # Find fastest
        fastest = min(successful_results, key=lambda r: r["total_execution_time"])
        fastest_name = (
            fastest["model"].split("/")[-1] if "/" in fastest["model"] else fastest["model"]
        )
        print(f"\nFastest: {fastest_name}")
        print(f"  - Time: {fastest['total_execution_time']:.2f}s")
        print(f"  - Entities: {fastest['entity_extraction']['entity_count']}")
        print(f"  - Relations: {fastest['relation_extraction']['relation_count']}")

    # Save detailed results
    output_file = "benchmark_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Detailed results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
