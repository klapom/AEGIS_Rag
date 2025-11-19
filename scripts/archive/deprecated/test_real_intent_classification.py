"""Quick test of Intent Classification with real Ollama LLM.

Run this to verify that IntentClassifier works with real llama3.2:3b model.
"""

import asyncio
import time

from src.agents.router import IntentClassifier, QueryIntent


async def main():
    """Test intent classification with real LLM."""
    print("=" * 70)
    print("Testing Intent Classification with Real Ollama LLM")
    print("=" * 70)
    print(f"Model: llama3.2:3b")
    print(f"Base URL: http://localhost:11434")
    print(f"Temperature: 0.0 (deterministic)")
    print()

    # Create classifier
    classifier = IntentClassifier(
        model_name="llama3.2:3b",
        base_url="http://localhost:11434",
        temperature=0.0,
        max_tokens=50,
    )

    # Test queries
    test_queries = [
        ("What is RAG?", "VECTOR or HYBRID"),
        ("How are documents related?", "GRAPH or HYBRID"),
        ("Search for embeddings info", "VECTOR or HYBRID"),
        ("What did I ask before?", "MEMORY or HYBRID"),
    ]

    print(f"Running {len(test_queries)} test queries...\n")

    results = []
    for query, expected in test_queries:
        print(f"Query: '{query}'")
        print(f"Expected: {expected}")

        start_time = time.perf_counter()
        try:
            intent = await classifier.classify_intent(query)
            latency_ms = (time.perf_counter() - start_time) * 1000

            print(f"Result: {intent.value.upper()}")
            print(f"Latency: {latency_ms:.2f}ms")

            results.append(
                {
                    "query": query,
                    "intent": intent.value,
                    "latency_ms": latency_ms,
                    "success": True,
                }
            )
        except Exception as e:
            print(f"ERROR: {e}")
            results.append(
                {
                    "query": query,
                    "error": str(e),
                    "success": False,
                }
            )

        print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    successful = sum(1 for r in results if r.get("success", False))
    print(f"Successful: {successful}/{len(results)}")

    if successful > 0:
        avg_latency = sum(r["latency_ms"] for r in results if r.get("success")) / successful
        print(f"Average latency: {avg_latency:.2f}ms")

        print("\nAll Results:")
        for r in results:
            if r.get("success"):
                print(f"  [OK] {r['query'][:40]:40} -> {r['intent']:8} ({r['latency_ms']:.0f}ms)")
            else:
                print(f"  [ERROR] {r['query'][:40]:40} -> ERROR: {r.get('error', 'Unknown')}")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
