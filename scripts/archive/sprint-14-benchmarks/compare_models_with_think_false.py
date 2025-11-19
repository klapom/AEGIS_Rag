#!/usr/bin/env python3
"""Compare models WITH and WITHOUT think=False parameter.

Sprint 13 TD-31: Test which models support thinking mode and compare performance.
"""

import json
import time
from ollama import Client

TEST_TEXT = """
Python is a programming language created by Guido van Rossum.
It was first released in 1991 and emphasizes code readability.
Python supports multiple programming paradigms including procedural,
object-oriented, and functional programming.
"""

ENTITY_PROMPT = """Extract all entities from this text and return ONLY a JSON array.

Text: {text}

Return format: [{{"name": "Python", "type": "TECHNOLOGY"}}, {{"name": "Guido van Rossum", "type": "PERSON"}}]

IMPORTANT: Return ONLY the JSON array, no markdown, no explanations."""


def test_model(model_name: str, client: Client, use_think_false: bool = False) -> dict:
    """Test a single model with or without think=False."""
    mode = "think=False" if use_think_false else "default"
    print(f"\nTesting: {model_name} [{mode}]", end=" ... ", flush=True)

    start = time.perf_counter()
    try:
        kwargs = {
            "model": model_name,
            "messages": [{"role": "user", "content": ENTITY_PROMPT.format(text=TEST_TEXT)}],
            "options": {"temperature": 0.1, "num_predict": 500, "num_ctx": 8192},
        }

        if use_think_false:
            kwargs["think"] = False

        response = client.chat(**kwargs)
        elapsed = time.perf_counter() - start

        content = response["message"]["content"]

        # Check for <think> tags
        has_think_tags = "<think>" in content or "</think>" in content

        # Try to parse JSON
        import re

        entities = []
        success = False
        json_match = re.search(r"\[.*\]", content, re.DOTALL)
        if json_match:
            try:
                entities = json.loads(json_match.group(0))
                success = True
            except:
                pass

        print(f"{len(entities)} entities in {elapsed:.1f}s [{'OK' if success else 'FAIL'}]")

        return {
            "model": model_name,
            "mode": mode,
            "entity_count": len(entities),
            "time": elapsed,
            "success": success,
            "has_think_tags": has_think_tags,
            "supports_think_param": True,
            "entities": entities,
            "response_preview": content[:200],
        }

    except Exception as e:
        elapsed = time.perf_counter() - start
        error_msg = str(e)

        # Check if error is "does not support thinking"
        supports_think = "does not support thinking" not in error_msg

        print(f"[ERROR] {error_msg[:60]}")

        return {
            "model": model_name,
            "mode": mode,
            "entity_count": 0,
            "time": elapsed,
            "success": False,
            "supports_think_param": supports_think,
            "error": error_msg,
        }


def main():
    print(
        """
================================================================================
        Model Comparison WITH and WITHOUT think=False
================================================================================

Sprint 13 TD-31: Testing which models support thinking mode
"""
    )

    client = Client()

    # Models to test
    models = [
        "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q8_0",
        "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M",
        "hf.co/MaziyarPanahi/Qwen3-4B-GGUF:Q6_K",
        "qwen3:4b",
        "llama3.2:3b",
    ]

    results = []

    for model in models:
        print(f"\n{'='*80}")
        print(f"MODEL: {model.split('/')[-1] if '/' in model else model}")
        print(f"{'='*80}")

        # Test 1: Default mode (no think parameter)
        result_default = test_model(model, client, use_think_false=False)
        results.append(result_default)

        # Test 2: With think=False (if supported)
        if result_default.get("supports_think_param", False):
            time.sleep(0.5)
            result_no_think = test_model(model, client, use_think_false=True)
            results.append(result_no_think)
        else:
            print(f"  --> Skipping think=False test (not supported)")

    # COMPARISON TABLE
    print(f"\n{'='*80}")
    print("COMPARISON RESULTS")
    print(f"{'='*80}\n")

    print(
        f"{'Model':<40} {'Mode':<15} {'Entities':<12} {'Time (s)':<12} {'Think Tags':<12} {'Status'}"
    )
    print(f"{'-'*40} {'-'*15} {'-'*12} {'-'*12} {'-'*12} {'-'*10}")

    for r in results:
        model_short = r["model"].split("/")[-1] if "/" in r["model"] else r["model"]
        think_tags = "YES" if r.get("has_think_tags") else "NO" if r.get("success") else "N/A"
        status = "[OK]" if r["success"] else "[ERROR]"

        print(
            f"{model_short:<40} {r['mode']:<15} {r['entity_count']:<12} {r['time']:<12.2f} {think_tags:<12} {status}"
        )

    # ANALYSIS
    print(f"\n{'='*80}")
    print("ANALYSIS: Thinking Mode Support")
    print(f"{'='*80}\n")

    for model in models:
        model_short = model.split("/")[-1] if "/" in model else model
        model_results = [r for r in results if r["model"] == model]

        if not model_results:
            continue

        default_result = [r for r in model_results if r["mode"] == "default"][0]

        print(f"\n{model_short}:")

        if not default_result.get("supports_think_param", True):
            print(f"  [INFO] Does NOT support think parameter")
            print(f"  Entities: {default_result['entity_count']}")
            print(f"  Time: {default_result['time']:.2f}s")
        else:
            no_think_results = [r for r in model_results if r["mode"] == "think=False"]

            if no_think_results:
                no_think_result = no_think_results[0]

                # Compare performance
                if default_result["success"] and no_think_result["success"]:
                    time_diff = default_result["time"] - no_think_result["time"]
                    time_pct = (time_diff / default_result["time"]) * 100

                    entity_diff = default_result["entity_count"] - no_think_result["entity_count"]

                    print(f"  [INFO] Supports think parameter")
                    print(
                        f"  Default mode:  {default_result['entity_count']} entities in {default_result['time']:.2f}s"
                    )
                    print(
                        f"  think=False:   {no_think_result['entity_count']} entities in {no_think_result['time']:.2f}s"
                    )
                    print(
                        f"  Speed improvement: {time_pct:+.1f}% ({'faster' if time_diff > 0 else 'slower'} with think=False)"
                    )

                    if entity_diff != 0:
                        print(f"  Quality change: {entity_diff:+d} entities")

    # RECOMMENDATION
    print(f"\n{'='*80}")
    print("RECOMMENDATION")
    print(f"{'='*80}\n")

    # Find best overall
    successful_results = [r for r in results if r["success"]]
    if successful_results:
        # Best quality
        best_quality = max(successful_results, key=lambda r: r["entity_count"])
        print(
            f"Best Quality: {best_quality['model'].split('/')[-1] if '/' in best_quality['model'] else best_quality['model']}"
        )
        print(f"  Mode: {best_quality['mode']}")
        print(f"  Entities: {best_quality['entity_count']}")
        print(f"  Time: {best_quality['time']:.2f}s")

        # Fastest
        fastest = min(successful_results, key=lambda r: r["time"])
        print(
            f"\nFastest: {fastest['model'].split('/')[-1] if '/' in fastest['model'] else fastest['model']}"
        )
        print(f"  Mode: {fastest['mode']}")
        print(f"  Time: {fastest['time']:.2f}s")
        print(f"  Entities: {fastest['entity_count']}")

        # Best balance
        # Score = entities / time (higher is better)
        balanced = max(
            successful_results, key=lambda r: r["entity_count"] / r["time"] if r["time"] > 0 else 0
        )
        print(
            f"\nBest Balance (entities/sec): {balanced['model'].split('/')[-1] if '/' in balanced['model'] else balanced['model']}"
        )
        print(f"  Mode: {balanced['mode']}")
        print(f"  Entities: {balanced['entity_count']}")
        print(f"  Time: {balanced['time']:.2f}s")
        print(f"  Score: {balanced['entity_count'] / balanced['time']:.2f} entities/sec")

    # Save results
    output_file = "model_comparison_think_false.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Detailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
