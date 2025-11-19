"""
Test hybrid search with real queries on indexed documents.

This script validates that the end-to-end search pipeline works correctly
after documents have been indexed.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.components.vector_search.hybrid_search import HybridSearch
from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.components.vector_search.embeddings import EmbeddingService


async def test_search_queries():
    """Test hybrid search with various query types."""

    print("[*] Initializing HybridSearch...")

    # Initialize components
    qdrant_client = QdrantClientWrapper(host="localhost", port=6333)

    embedding_service = EmbeddingService(model_name="nomic-embed-text", enable_cache=True)

    hybrid_search = HybridSearch(
        qdrant_client=qdrant_client,
        embedding_service=embedding_service,
        collection_name="aegis_documents",
    )

    print("   [OK] HybridSearch initialized\n")

    # Test queries based on user's documents (building renovation documents)
    test_queries = [
        {"query": "Sanierung Fenster", "description": "Search for window renovation information"},
        {"query": "Heizung Installation", "description": "Search for heating installation details"},
        {"query": "Elektro Raumbuch", "description": "Search for electrical room book"},
        {"query": "Finanzierung", "description": "Search for financing information"},
        {"query": "Vertrag", "description": "Search for contract documents"},
    ]

    for idx, test_case in enumerate(test_queries, start=1):
        query = test_case["query"]
        description = test_case["description"]

        print(f"[{idx}/{len(test_queries)}] Testing: {description}")
        print(f"   Query: '{query}'")

        try:
            # Test vector search
            print("   Running vector search...")
            vector_results = await hybrid_search.vector_search(
                query=query, top_k=3, score_threshold=0.3
            )
            print(f"      Found {len(vector_results)} vector results")

            # Test hybrid search
            print("   Running hybrid search...")
            hybrid_results = await hybrid_search.hybrid_search(
                query=query, top_k=5, vector_top_k=10, bm25_top_k=10
            )

            print(f"      Found {len(hybrid_results['results'])} hybrid results")
            print(
                f"      Diversity score: {hybrid_results['search_metadata']['diversity']['overlap_ratio']:.2%}"
            )

            # Show top result
            if hybrid_results["results"]:
                top_result = hybrid_results["results"][0]
                text_preview = top_result.get("text", "")[:150]
                score = top_result.get("rrf_score", 0.0)
                print(f"      Top result (RRF={score:.4f}): {text_preview}...")

            print("   [OK] Search successful\n")

        except Exception as e:
            print(f"   [ERROR] Search failed: {e}\n")
            import traceback

            traceback.print_exc()

    print("[SUCCESS] All search queries completed!")
    print(f"\nSummary:")
    print(f"   - Tested {len(test_queries)} different queries")
    print(f"   - Collection: aegis_documents")
    print(f"   - Embedding model: nomic-embed-text")


if __name__ == "__main__":
    asyncio.run(test_search_queries())
