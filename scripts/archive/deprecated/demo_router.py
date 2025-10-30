"""Demo script for Query Router and Intent Classification.

This script demonstrates the router's ability to classify different types of queries.
It uses mock responses to avoid requiring Ollama to be running.

Sprint 4 Feature 4.2: Query Router Demo
"""

import asyncio
from unittest.mock import AsyncMock, patch

from src.agents.router import IntentClassifier, QueryIntent


async def demo_classification():
    """Demonstrate query classification with various examples."""
    # Test queries
    test_queries = [
        ("What is Retrieval-Augmented Generation?", "VECTOR"),
        ("How are RAG and knowledge graphs related?", "GRAPH"),
        ("Find documents about RAG and explain how it integrates with vector databases", "HYBRID"),
        ("What did we discuss yesterday about embeddings?", "MEMORY"),
        ("Define machine learning", "VECTOR"),
        ("What is the relationship between transformers and attention mechanisms?", "GRAPH"),
    ]

    print("=" * 80)
    print("Query Router Intent Classification Demo")
    print("=" * 80)
    print()

    # Create classifier with mocked responses
    classifier = IntentClassifier(
        model_name="llama3.2:3b",
        base_url="http://localhost:11434",
        temperature=0.0,
        max_tokens=50,
    )

    results = []
    for query, expected_intent in test_queries:
        # Mock the Ollama response based on expected intent
        mock_response = {"response": expected_intent}

        with patch.object(classifier.client, "generate", new=AsyncMock(return_value=mock_response)):
            intent = await classifier.classify_intent(query)

            success = "" if intent.value.upper() == expected_intent else ""
            results.append((query, expected_intent, intent.value, success))

            print(f"{success} Query: {query[:60]}...")
            print(f"  Expected: {expected_intent}, Got: {intent.value.upper()}")
            print()

    # Summary
    print("=" * 80)
    correct = sum(1 for _, expected, actual, _ in results if expected == actual.upper())
    total = len(results)
    accuracy = (correct / total) * 100
    print(f"Classification Accuracy: {accuracy:.1f}% ({correct}/{total})")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(demo_classification())
