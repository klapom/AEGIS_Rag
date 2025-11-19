#!/usr/bin/env python3
"""Quick model comparison for LightRAG extraction tasks."""

import json
import time
from ollama import Client

# Test document
TEST_TEXT = """
Python is a programming language created by Guido van Rossum.
It was first released in 1991 and emphasizes code readability.
"""

# Simple entity extraction prompt
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
           Quick Model Test - Entity Extraction Comparison
================================================================================
    """
    )

    client = Client()

    models = [
        "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q8_0",
        "hf.co/MaziyarPanahi/Qwen3-4B-GGUF:Q6_K",
        "qwen3:4b",
        "llama3.2:3b",
    ]

    results = []
    for model in models:
        result = test_model(model, client)
        results.append(result)
        time.sleep(1)  # Brief pause between models

    # Print comparison
    print(f"\n{'='*60}")
    print("COMPARISON TABLE")
    print(f"{'='*60}\n")
    print(f"{'Model':<35} {'Entities':<12} {'Time (s)':<12} {'Status'}")
    print(f"{'-'*35} {'-'*12} {'-'*12} {'-'*10}")

    for r in results:
        model_short = r["model"].split("/")[-1] if "/" in r["model"] else r["model"]
        status = "[OK]" if r["success"] else "[ERROR]"
        print(f"{model_short:<35} {r['entity_count']:<12} {r['time']:<12.2f} {status}")

    # Show sample entities from best model
    print(f"\n{'='*60}")
    print("SAMPLE ENTITIES (from best model)")
    print(f"{'='*60}")

    best = max([r for r in results if r["success"]], key=lambda x: x["entity_count"], default=None)
    if best and best.get("entities"):
        print(f"\nModel: {best['model'].split('/')[-1] if '/' in best['model'] else best['model']}")
        for entity in best["entities"][:5]:
            print(f"  - {entity.get('name', 'N/A')} ({entity.get('type', 'N/A')})")

    # Save results
    with open("quick_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Results saved to: quick_test_results.json")


if __name__ == "__main__":
    main()
