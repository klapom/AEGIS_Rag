"""Simple test script for VectorSearchAgent.

Tests basic functionality without pytest to verify integration.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.state import create_initial_state
from src.agents.vector_search_agent import VectorSearchAgent
from src.components.vector_search.hybrid_search import HybridSearch


async def main():
    """Test VectorSearchAgent with real components."""
    print("=" * 80)
    print("Vector Search Agent Integration Test")
    print("=" * 80)

    try:
        # Create components
        print("\n1. Initializing components...")
        hybrid_search = HybridSearch()
        print("   ✓ HybridSearch initialized")

        # Prepare BM25 index
        print("\n2. Preparing BM25 index...")
        try:
            stats = await hybrid_search.prepare_bm25_index()
            print(f"   ✓ BM25 index prepared: {stats['documents_indexed']} documents")
        except Exception as e:
            print(f"   ⚠ Could not prepare BM25 index: {e}")
            print("   (This is OK if no documents are indexed yet)")

        # Create agent
        print("\n3. Creating VectorSearchAgent...")
        agent = VectorSearchAgent(hybrid_search=hybrid_search, top_k=5, use_reranking=True)
        print(f"   ✓ Agent created: {agent.name}")

        # Test query
        query = "What is retrieval augmented generation?"
        print(f"\n4. Testing query: '{query}'")

        # Create initial state
        state = create_initial_state(query, intent="hybrid")
        print("   ✓ Initial state created")

        # Process
        print("\n5. Processing query...")
        start_time = time.perf_counter()
        result_state = await agent.process(state)
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Display results
        print(f"\n6. Results (latency: {latency_ms:.2f}ms):")

        contexts = result_state.get("retrieved_contexts", [])
        print(f"   Retrieved {len(contexts)} documents:")

        for i, ctx in enumerate(contexts[:3], 1):  # Show top 3
            print(f"\n   [{i}] Score: {ctx.get('score', 0):.4f}")
            print(f"       Source: {ctx.get('source', 'unknown')}")
            text = ctx.get("text", "")
            preview = text[:100] + "..." if len(text) > 100 else text
            print(f"       Text: {preview}")

        # Display metadata
        if "metadata" in result_state:
            print(f"\n7. Metadata:")
            metadata = result_state["metadata"]

            if "search" in metadata:
                search_meta = metadata["search"]
                print(f"   Search mode: {search_meta.get('search_mode', 'unknown')}")
                print(f"   Vector results: {search_meta.get('vector_results_count', 0)}")
                print(f"   BM25 results: {search_meta.get('bm25_results_count', 0)}")
                print(f"   Reranking applied: {search_meta.get('reranking_applied', False)}")
                print(f"   Latency: {search_meta.get('latency_ms', 0):.2f}ms")

            if "agent_path" in metadata:
                print(f"\n   Agent path:")
                for step in metadata["agent_path"]:
                    print(f"     - {step}")

        print("\n" + "=" * 80)
        print("✅ Test completed successfully!")
        print("=" * 80)

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ Test failed: {type(e).__name__}: {e}")
        print("=" * 80)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
