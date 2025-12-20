#!/usr/bin/env python3
"""Compare Gemma-3-4b Q4_K_M vs Q8_0 for LightRAG entity extraction."""

import json
import time

from ollama import Client

TEST_TEXT = """
Python is a programming language created by Guido van Rossum.
It was first released in 1991 and emphasizes code readability.
"""

ENTITY_PROMPT = """Extract all entities from this text and return ONLY a JSON array.

Text: {text}

Return format: [{{"name": "Python", "type": "TECHNOLOGY"}}, {{"name": "Guido van Rossum", "type": "PERSON"}}]

IMPORTANT: Return ONLY the JSON array, no markdown, no explanations."""


def test_model(model_name: str, client: Client) -> dict:
    """Test a single model."""
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"{'='*60}")

    start = time.perf_counter()
    try:
        response = client.chat(
            model=model_name,
            messages=[{"role": "user", "content": ENTITY_PROMPT.format(text=TEST_TEXT)}],
            options={"temperature": 0.1, "num_predict": 500, "num_ctx": 8192},
        )
        elapsed = time.perf_counter() - start

        content = response["message"]["content"]
        print(f"Response ({elapsed:.2f}s):\n{content[:200]}...")

        # Try to parse JSON
        import re

        json_match = re.search(r"\[.*\]", content, re.DOTALL)
        if json_match:
            entities = json.loads(json_match.group(0))
            entity_count = len(entities)
            success = True
        else:
            entities = []
            entity_count = 0
            success = False

        print(f"[OK] Entities: {entity_count}, Time: {elapsed:.2f}s")

        return {
            "model": model_name,
            "entity_count": entity_count,
            "time": elapsed,
            "success": success,
            "entities": entities,
            "response": content,
        }

    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"[ERROR] {e}")
        return {
            "model": model_name,
            "entity_count": 0,
            "time": elapsed,
            "success": False,
            "error": str(e),
        }


def main():
    print(
        """
================================================================================
           Gemma-3-4b Quantization Comparison - Q4_K_M vs Q8_0
================================================================================

Sprint 13 TD-31: Testing production-optimized Q4_K_M vs reference Q8_0
    """
    )

    client = Client()

    models = [
        "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q8_0",  # Reference (4.13 GB)
        "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M",  # Production (2.49 GB)
    ]

    results = []
    for model in models:
        result = test_model(model, client)
        results.append(result)
        time.sleep(1)

    # Print comparison
    print(f"\n{'='*60}")
    print("COMPARISON RESULTS")
    print(f"{'='*60}\n")
    print(f"{'Quantization':<15} {'Size':<12} {'Entities':<12} {'Time (s)':<12} {'Status'}")
    print(f"{'-'*15} {'-'*12} {'-'*12} {'-'*12} {'-'*10}")

    q8_result = results[0]
    q4_result = results[1]

    # Q8_0
    status_q8 = "[OK]" if q8_result["success"] else "[ERROR]"
    print(
        f"{'Q8_0':<15} {'4.13 GB':<12} {q8_result['entity_count']:<12} {q8_result['time']:<12.2f} {status_q8}"
    )

    # Q4_K_M
    status_q4 = "[OK]" if q4_result["success"] else "[ERROR]"
    print(
        f"{'Q4_K_M':<15} {'2.49 GB':<12} {q4_result['entity_count']:<12} {q4_result['time']:<12.2f} {status_q4}"
    )

    # Performance analysis
    if q8_result["success"] and q4_result["success"]:
        print(f"\n{'='*60}")
        print("PERFORMANCE ANALYSIS")
        print(f"{'='*60}")

        # Speed improvement
        speedup = (q8_result["time"] - q4_result["time"]) / q8_result["time"] * 100
        print("\nSpeed:")
        print(f"  Q4_K_M is {speedup:.1f}% faster than Q8_0")
        print(f"  ({q4_result['time']:.2f}s vs {q8_result['time']:.2f}s)")

        # Size saving
        size_saving = (4.13 - 2.49) / 4.13 * 100
        print("\nDisk Space:")
        print(f"  Q4_K_M saves {size_saving:.1f}% disk space")
        print("  (2.49 GB vs 4.13 GB)")

        # Quality comparison
        print("\nQuality:")
        if q8_result["entity_count"] == q4_result["entity_count"]:
            print(f"  [OK] Identical quality: {q4_result['entity_count']} entities")
        else:
            diff = q8_result["entity_count"] - q4_result["entity_count"]
            print(f"  Q8_0: {q8_result['entity_count']} entities")
            print(f"  Q4_K_M: {q4_result['entity_count']} entities (diff: {diff:+d})")

        # Recommendation
        print(f"\n{'='*60}")
        print("RECOMMENDATION")
        print(f"{'='*60}")

        if q4_result["entity_count"] >= q8_result["entity_count"]:
            print("\n[RECOMMENDED] Use Q4_K_M for production:")
            print(f"  + {speedup:.1f}% faster")
            print(f"  + {size_saving:.1f}% smaller")
            print(f"  + Same/better quality ({q4_result['entity_count']} entities)")
        else:
            print("\n[CAUTION] Q4_K_M has slightly lower quality:")
            print(f"  + {speedup:.1f}% faster")
            print(f"  + {size_saving:.1f}% smaller")
            print(f"  - Missing {abs(diff)} entity(ies)")
            print("\nDecision: Speed vs Quality tradeoff")

    # Save detailed results
    with open("gemma_quantization_comparison.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\n[OK] Detailed results saved to: gemma_quantization_comparison.json")


if __name__ == "__main__":
    main()
