"""Test script to verify cost tracking works with router.py and extraction_service.py."""

import asyncio
from src.agents.router import IntentClassifier
from src.components.graph_rag.extraction_service import ExtractionService
from src.components.llm_proxy.cost_tracker import CostTracker


async def main():
    print("Testing AegisLLMProxy Integration with Cost Tracking\n")
    print("=" * 60)

    # Initialize cost tracker
    cost_tracker = CostTracker()

    # Get initial spending
    print("\n1. Initial Spending:")
    initial_spending = cost_tracker.get_monthly_spending()
    print(f"   Monthly spending: {initial_spending}")

    # Test 1: Intent Classification (router.py)
    print("\n2. Testing Intent Classification (router.py):")
    classifier = IntentClassifier()
    intent = await classifier.classify_intent("What is Retrieval-Augmented Generation?")
    print(f"   Query: 'What is Retrieval-Augmented Generation?'")
    print(f"   Classified Intent: {intent.value}")

    # Test 2: Entity Extraction (extraction_service.py)
    print("\n3. Testing Entity Extraction (extraction_service.py):")
    extractor = ExtractionService()
    text = "John Smith works at Google as a software engineer."
    entities = await extractor.extract_entities(text, "test_doc_1")
    print(f"   Text: '{text}'")
    print(f"   Extracted {len(entities)} entities:")
    for entity in entities[:3]:  # Show first 3
        print(f"      - {entity.name} ({entity.type})")

    # Get final spending
    print("\n4. Final Spending:")
    final_spending = cost_tracker.get_monthly_spending()
    print(f"   Monthly spending: {final_spending}")

    # Calculate delta
    print("\n5. Cost Tracking Verification:")
    for provider in set(list(initial_spending.keys()) + list(final_spending.keys())):
        initial = initial_spending.get(provider, 0.0)
        final = final_spending.get(provider, 0.0)
        delta = final - initial
        if delta > 0:
            print(f"   {provider}: ${initial:.6f} -> ${final:.6f} (+${delta:.6f})")
        else:
            print(f"   {provider}: ${initial:.6f} (no change)")

    # Get recent requests
    print("\n6. Recent Requests (SQLite):")
    import sqlite3
    from pathlib import Path

    db_path = Path("data/cost_tracking.db")
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT timestamp, provider, model, task_type, tokens_input, tokens_output, cost_usd
            FROM llm_requests
            ORDER BY timestamp DESC
            LIMIT 5
        """
        )
        requests = cursor.fetchall()
        for req in requests:
            timestamp, provider, model, task_type, tokens_in, tokens_out, cost = req
            print(f"   [{timestamp}] {provider}/{model}")
            print(f"      Task: {task_type}, Tokens: {tokens_in}/{tokens_out}, Cost: ${cost:.6f}")
        conn.close()
    else:
        print("   WARNING: cost_tracking.db not found!")

    print("\n" + "=" * 60)
    print("Cost tracking verification complete!")


if __name__ == "__main__":
    asyncio.run(main())
