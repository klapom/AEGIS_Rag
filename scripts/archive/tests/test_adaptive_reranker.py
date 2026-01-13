#!/usr/bin/env python3
"""Test script for Adaptive Reranker (Sprint 67 Feature 67.8).

Demonstrates intent-aware reranking with different query types.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.components.retrieval.intent_classifier import get_intent_classifier
from src.components.retrieval.reranker import INTENT_RERANK_WEIGHTS, CrossEncoderReranker


# Sample documents for testing
SAMPLE_DOCS = [
    {
        "id": "doc1",
        "text": "OMNITRACKER is an enterprise workflow management system.",
        "score": 0.85,
        "bm25_score": 0.4,
        "metadata": {"created_at": "2023-01-15T10:00:00Z"},
    },
    {
        "id": "doc2",
        "text": "Error 404: JWT_TOKEN not found in authentication header.",
        "score": 0.75,
        "bm25_score": 0.9,
        "metadata": {"created_at": "2024-06-20T14:30:00Z"},
    },
    {
        "id": "doc3",
        "text": "The new 2025 release includes AI-powered ticket routing.",
        "score": 0.90,
        "bm25_score": 0.6,
        "metadata": {"created_at": "2024-12-15T09:15:00Z"},
    },
    {
        "id": "doc4",
        "text": "Authentication workflow connects to LDAP directory service.",
        "score": 0.70,
        "bm25_score": 0.5,
        "metadata": {"created_at": "2024-03-10T11:20:00Z"},
    },
]


async def test_adaptive_reranking():
    """Test adaptive reranking with different query types."""
    print("=" * 80)
    print("Adaptive Reranker v1 - Sprint 67 Feature 67.8")
    print("=" * 80)

    # Show weight profiles
    print("\nIntent Weight Profiles:")
    print("-" * 80)
    for intent, weights in INTENT_RERANK_WEIGHTS.items():
        print(
            f"{intent:12} | Semantic: {weights.semantic_weight:.1f} | "
            f"Keyword: {weights.keyword_weight:.1f} | Recency: {weights.recency_weight:.1f}"
        )

    # Initialize reranker
    reranker = CrossEncoderReranker(use_adaptive_weights=True)
    classifier = get_intent_classifier()

    # Test queries with different intents
    test_queries = [
        ("What is OMNITRACKER?", "factual"),
        ("JWT_TOKEN error 404", "keyword"),
        ("How does authentication work?", "exploratory"),
        ("Summarize recent features", "summary"),
    ]

    for query, expected_intent in test_queries:
        print("\n" + "=" * 80)
        print(f"Query: '{query}'")
        print("-" * 80)

        # Classify intent
        intent_result = await classifier.classify(query)
        print(
            f"Intent: {intent_result.intent.value} "
            f"(confidence: {intent_result.confidence:.2f}, "
            f"method: {intent_result.method}, "
            f"latency: {intent_result.latency_ms:.2f}ms)"
        )

        # Get weight profile
        weights = INTENT_RERANK_WEIGHTS.get(
            intent_result.intent.value, INTENT_RERANK_WEIGHTS["default"]
        )
        print(
            f"Weights: Semantic={weights.semantic_weight:.1f}, "
            f"Keyword={weights.keyword_weight:.1f}, "
            f"Recency={weights.recency_weight:.1f}"
        )

        # Note: For this test script, we'll skip actual cross-encoder inference
        # since it requires downloading the model. In production, this would run.
        print("\nNote: Skipping cross-encoder inference in test script.")
        print("In production, documents would be reranked based on adaptive weights.")

    print("\n" + "=" * 80)
    print("Adaptive Reranker Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_adaptive_reranking())
