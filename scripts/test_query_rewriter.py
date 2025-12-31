#!/usr/bin/env python3
"""Test script for QueryRewriter (Sprint 67 Feature 67.9).

This script demonstrates the query rewriting functionality with examples
of expansion and refinement strategies.

Usage:
    poetry run python scripts/test_query_rewriter.py
"""

import asyncio

from src.adaptation.query_rewriter import get_query_rewriter


async def main() -> None:
    """Run query rewriter tests."""
    print("=" * 80)
    print("QueryRewriter Test Script - Sprint 67 Feature 67.9")
    print("=" * 80)

    # Initialize rewriter
    rewriter = get_query_rewriter()

    # Test cases
    test_queries = [
        # Short queries (expansion)
        "API",
        "API docs",
        "JWT token",
        # Vague queries (refinement)
        "How auth?",
        "What is API?",
        "Explain this",
        # Well-formed queries (no rewriting)
        "How to configure JWT authentication in the REST API?",
        "Summarize the project architecture",
        # Technical queries
        "database schema",
        "authentication flow",
    ]

    print("\nTest Queries:")
    print("-" * 80)

    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Original: \"{query}\"")

        # Rewrite
        result = await rewriter.rewrite(query)

        # Display result
        print(f"   Strategy: {result.strategy}")
        print(f"   Rewritten: \"{result.rewritten_query}\"")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Latency: {result.latency_ms:.2f}ms")

        if result.intent:
            print(f"   Intent: {result.intent}")

    print("\n" + "=" * 80)
    print("Test complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
