#!/usr/bin/env python3
"""Comprehensive benchmark: Q4_K_M vs Q8_0 with 10 prompts of varying complexity.

Sprint 13 TD-31: Test Gemma-3-4b quantizations across diverse extraction tasks.
"""

import json
import time
from typing import Any

from ollama import Client

# ============================================================================
# TEST CASES - 10 Prompts of Increasing Complexity
# ============================================================================

TEST_CASES = [
    # COMPLEXITY 1: Simple, short text, few entities
    {
        "id": 1,
        "complexity": "SIMPLE",
        "text": "Berlin is the capital of Germany.",
        "expected_entities": 2,
        "description": "Basic entity extraction - city and country",
    },
    # COMPLEXITY 2: Multiple entities, clear types
    {
        "id": 2,
        "complexity": "SIMPLE",
        "text": "Apple CEO Tim Cook announced the iPhone 15 in September 2023 in Cupertino, California.",
        "expected_entities": 6,
        "description": "Multiple entity types - company, person, product, date, location",
    },
    # COMPLEXITY 3: Technical terms, acronyms
    {
        "id": 3,
        "complexity": "MEDIUM",
        "text": "NASA's James Webb Space Telescope (JWST) was launched on December 25, 2021, from the Guiana Space Centre using an Ariane 5 rocket.",
        "expected_entities": 5,
        "description": "Technical entities with acronyms and specific equipment",
    },
    # COMPLEXITY 4: Scientific content with relations
    {
        "id": 4,
        "complexity": "MEDIUM",
        "text": "Albert Einstein developed the theory of relativity in 1905. His work revolutionized physics and earned him the Nobel Prize in Physics in 1921.",
        "expected_entities": 4,
        "description": "Scientific achievements with temporal relations",
    },
    # COMPLEXITY 5: Business context with multiple relations
    {
        "id": 5,
        "complexity": "MEDIUM",
        "text": "Microsoft acquired GitHub for $7.5 billion in 2018. The deal was led by CEO Satya Nadella and aimed to strengthen Microsoft's developer ecosystem.",
        "expected_entities": 5,
        "description": "Business transaction with monetary values and leadership",
    },
    # COMPLEXITY 6: Technical architecture description
    {
        "id": 6,
        "complexity": "COMPLEX",
        "text": "LangGraph is a Python library built on LangChain that enables creation of stateful, multi-agent workflows. It uses a graph-based approach where nodes represent computational steps and edges define the flow.",
        "expected_entities": 4,
        "description": "Technical architecture with abstract concepts",
    },
    # COMPLEXITY 7: Medical/Scientific with specialized terms
    {
        "id": 7,
        "complexity": "COMPLEX",
        "text": "CRISPR-Cas9, developed by Jennifer Doudna and Emmanuelle Charpentier, is a gene-editing technology that allows precise modifications to DNA. Their work earned them the 2020 Nobel Prize in Chemistry.",
        "expected_entities": 5,
        "description": "Scientific discovery with specialized terminology",
    },
    # COMPLEXITY 8: Historical context with implicit relations
    {
        "id": 8,
        "complexity": "COMPLEX",
        "text": "The Apollo 11 mission, commanded by Neil Armstrong with crew members Buzz Aldrin and Michael Collins, successfully landed on the Moon on July 20, 1969. Armstrong became the first person to walk on the lunar surface.",
        "expected_entities": 6,
        "description": "Historical event with multiple participants and roles",
    },
    # COMPLEXITY 9: Software engineering with nested concepts
    {
        "id": 9,
        "complexity": "VERY COMPLEX",
        "text": "Docker containers leverage Linux kernel features like namespaces and cgroups for isolation. Kubernetes, originally developed by Google, orchestrates these containers across distributed systems. The Cloud Native Computing Foundation (CNCF) now maintains Kubernetes.",
        "expected_entities": 6,
        "description": "Technical stack with organizational relationships",
    },
    # COMPLEXITY 10: Multi-domain with implicit knowledge
    {
        "id": 10,
        "complexity": "VERY COMPLEX",
        "text": "Transformer architecture, introduced in the 'Attention is All You Need' paper by Vaswani et al. at Google Brain, revolutionized NLP. This led to models like BERT (2018) and GPT-3 (2020), which use self-attention mechanisms for language understanding. OpenAI's GPT-4, released in 2023, demonstrates emergent capabilities.",
        "expected_entities": 8,
        "description": "AI research timeline with technical concepts and papers",
    },
]

ENTITY_SYSTEM_PROMPT = """You are an expert entity extractor for knowledge graphs.

Extract ALL named entities from the text. Include:
- PERSON: People, authors, leaders
- ORGANIZATION: Companies, institutions, teams
- LOCATION: Cities, countries, places
- TECHNOLOGY: Products, frameworks, tools, methods
- CONCEPT: Abstract ideas, theories, paradigms
- EVENT: Historical events, missions, releases
- DATE: Specific dates, years, time periods
- OTHER: Anything else important

Return ONLY a JSON array. No markdown, no explanations."""

ENTITY_USER_PROMPT_TEMPLATE = """Extract entities from this text:

{text}

Return format: [{{"name": "Einstein", "type": "PERSON"}}, {{"name": "relativity", "type": "CONCEPT"}}]

Return ONLY the JSON array:"""


def extract_entities(model: str, test_case: dict[str, Any], client: Client) -> dict[str, Any]:
    """Extract entities for a single test case."""
    start = time.perf_counter()

    try:
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": ENTITY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": ENTITY_USER_PROMPT_TEMPLATE.format(text=test_case["text"]),
                },
            ],
            options={"temperature": 0.1, "num_predict": 1000, "num_ctx": 8192},
        )

        elapsed = time.perf_counter() - start
        content = response["message"]["content"]

        # Parse JSON
        import re

        entities = []
        parse_error = None

        try:
            # Try direct parse
            entities = json.loads(content)
        except json.JSONDecodeError:
            # Extract from markdown
            json_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, re.DOTALL)
            if json_match:
                try:
                    entities = json.loads(json_match.group(1))
                except:
                    pass
            else:
                # Find array pattern
                json_match = re.search(r"\[.*\]", content, re.DOTALL)
                if json_match:
                    try:
                        entities = json.loads(json_match.group(0))
                    except:
                        parse_error = "JSON parse failed"

        return {
            "test_id": test_case["id"],
            "complexity": test_case["complexity"],
            "entities": entities if isinstance(entities, list) else [],
            "entity_count": len(entities) if isinstance(entities, list) else 0,
            "expected_count": test_case["expected_entities"],
            "time": elapsed,
            "success": parse_error is None and isinstance(entities, list),
            "parse_error": parse_error,
        }

    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "test_id": test_case["id"],
            "complexity": test_case["complexity"],
            "entities": [],
            "entity_count": 0,
            "expected_count": test_case["expected_entities"],
            "time": elapsed,
            "success": False,
            "error": str(e),
        }


def benchmark_model(model_name: str, client: Client) -> dict[str, Any]:
    """Run comprehensive benchmark on a model."""
    model_short = model_name.split(":")[-1] if ":" in model_name else model_name
    print(f"\n{'='*80}")
    print(f"BENCHMARKING: {model_short}")
    print(f"{'='*80}\n")

    results = []
    total_time = 0
    total_entities = 0
    success_count = 0

    for i, test_case in enumerate(TEST_CASES, 1):
        print(
            f"[{i}/10] Test {test_case['id']} ({test_case['complexity']})... ", end="", flush=True
        )

        result = extract_entities(model_name, test_case, client)
        results.append(result)

        total_time += result["time"]
        total_entities += result["entity_count"]
        if result["success"]:
            success_count += 1

        status = "[OK]" if result["success"] else "[ERROR]"
        print(f"{result['entity_count']} entities in {result['time']:.1f}s {status}")

    return {
        "model": model_name,
        "model_short": model_short,
        "test_results": results,
        "total_time": total_time,
        "total_entities": total_entities,
        "avg_time_per_test": total_time / len(TEST_CASES),
        "success_rate": (success_count / len(TEST_CASES)) * 100,
        "success_count": success_count,
    }


def main():
    print(
        """
================================================================================
        COMPREHENSIVE MODEL BENCHMARK - Q4_K_M vs Q8_0
================================================================================

Sprint 13 TD-31: Testing Gemma-3-4b quantizations across 10 prompts
Complexity levels: SIMPLE, MEDIUM, COMPLEX, VERY COMPLEX
    """
    )

    client = Client()

    models = [
        "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q8_0",
        "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M",
    ]

    benchmark_results = []
    for model in models:
        result = benchmark_model(model, client)
        benchmark_results.append(result)

    # COMPARISON TABLE
    print(f"\n{'='*80}")
    print("OVERALL COMPARISON")
    print(f"{'='*80}\n")

    q8_result = benchmark_results[0]
    q4_result = benchmark_results[1]

    print(f"{'Metric':<30} {'Q8_0':<20} {'Q4_K_M':<20} {'Difference'}")
    print(f"{'-'*30} {'-'*20} {'-'*20} {'-'*15}")

    # Total entities
    q8_ent = q8_result["total_entities"]
    q4_ent = q4_result["total_entities"]
    ent_diff = ((q4_ent - q8_ent) / q8_ent * 100) if q8_ent > 0 else 0
    print(f"{'Total Entities Extracted':<30} {q8_ent:<20} {q4_ent:<20} {ent_diff:+.1f}%")

    # Total time
    q8_time = q8_result["total_time"]
    q4_time = q4_result["total_time"]
    time_diff = ((q8_time - q4_time) / q8_time * 100) if q8_time > 0 else 0
    print(f"{'Total Time (s)':<30} {q8_time:<20.1f} {q4_time:<20.1f} {time_diff:+.1f}%")

    # Avg time per test
    print(
        f"{'Avg Time per Test (s)':<30} {q8_result['avg_time_per_test']:<20.1f} {q4_result['avg_time_per_test']:<20.1f}"
    )

    # Success rate
    print(
        f"{'Success Rate (%)':<30} {q8_result['success_rate']:<20.1f} {q4_result['success_rate']:<20.1f}"
    )

    # PER-TEST COMPARISON
    print(f"\n{'='*80}")
    print("PER-TEST RESULTS")
    print(f"{'='*80}\n")

    print(
        f"{'Test':<8} {'Complexity':<15} {'Q8_0 Ent':<12} {'Q4_K_M Ent':<12} {'Q8_0 Time':<12} {'Q4_K_M Time'}"
    )
    print(f"{'-'*8} {'-'*15} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")

    for i in range(len(TEST_CASES)):
        q8_test = q8_result["test_results"][i]
        q4_test = q4_result["test_results"][i]

        print(
            f"{q8_test['test_id']:<8} {q8_test['complexity']:<15} "
            f"{q8_test['entity_count']:<12} {q4_test['entity_count']:<12} "
            f"{q8_test['time']:<11.1f}s {q4_test['time']:<11.1f}s"
        )

    # ANALYSIS BY COMPLEXITY
    print(f"\n{'='*80}")
    print("ANALYSIS BY COMPLEXITY LEVEL")
    print(f"{'='*80}\n")

    complexity_levels = ["SIMPLE", "MEDIUM", "COMPLEX", "VERY COMPLEX"]

    for complexity in complexity_levels:
        q8_tests = [t for t in q8_result["test_results"] if t["complexity"] == complexity]
        q4_tests = [t for t in q4_result["test_results"] if t["complexity"] == complexity]

        if not q8_tests:
            continue

        q8_avg_ent = sum(t["entity_count"] for t in q8_tests) / len(q8_tests)
        q4_avg_ent = sum(t["entity_count"] for t in q4_tests) / len(q4_tests)
        q8_avg_time = sum(t["time"] for t in q8_tests) / len(q8_tests)
        q4_avg_time = sum(t["time"] for t in q4_tests) / len(q4_tests)

        print(f"{complexity}:")
        print(f"  Avg Entities:  Q8_0={q8_avg_ent:.1f}, Q4_K_M={q4_avg_ent:.1f}")
        print(f"  Avg Time:      Q8_0={q8_avg_time:.1f}s, Q4_K_M={q4_avg_time:.1f}s")
        print()

    # FINAL RECOMMENDATION
    print(f"{'='*80}")
    print("RECOMMENDATION")
    print(f"{'='*80}\n")

    speed_improvement = time_diff
    quality_diff_pct = ent_diff

    print(
        f"Speed:     Q4_K_M is {abs(speed_improvement):.1f}% {'FASTER' if speed_improvement > 0 else 'SLOWER'}"
    )
    print(
        f"Quality:   Q4_K_M extracts {abs(quality_diff_pct):.1f}% {'MORE' if quality_diff_pct > 0 else 'FEWER'} entities"
    )
    print(
        f"Success:   Q8_0={q8_result['success_count']}/10, Q4_K_M={q4_result['success_count']}/10"
    )

    if abs(quality_diff_pct) < 10 and speed_improvement > 30:
        print("\n[RECOMMENDED] Q4_K_M for Production")
        print("  + Significantly faster")
        print("  + Minimal quality loss")
        print("  + 40% smaller disk footprint")
    elif abs(quality_diff_pct) > 15:
        print("\n[RECOMMENDED] Q8_0 for Quality-Critical Tasks")
        print("  + Better entity extraction")
        print("  - Slower inference")
    else:
        print("\n[DECISION NEEDED] Tradeoff between speed and quality")

    # Save results
    output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "models_tested": models,
        "test_cases": TEST_CASES,
        "benchmark_results": benchmark_results,
    }

    with open("comprehensive_benchmark_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n[OK] Detailed results saved to: comprehensive_benchmark_results.json")


if __name__ == "__main__":
    main()
