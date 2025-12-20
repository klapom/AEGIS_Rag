"""Initialize BM25 Index for Hybrid Search.

This script loads all documents from Qdrant and builds the BM25 index
required for hybrid search functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.components.vector_search.hybrid_search import HybridSearch
from src.core.config import settings


async def main():
    """Initialize BM25 index from Qdrant collection."""

    print("=" * 80)
    print("BM25 Index Initialization")
    print("=" * 80)
    print()

    # Configuration
    collection_name = settings.qdrant_collection

    print("[*] Configuration:")
    print(f"   Collection: {collection_name}")
    print(f"   Qdrant: {settings.qdrant_host}:{settings.qdrant_port}")
    print()

    try:
        # Initialize HybridSearch
        print("[1/3] Initializing HybridSearch...")
        hybrid_search = HybridSearch()
        print("   [OK] HybridSearch initialized")
        print()

        # Prepare BM25 index
        print("[2/3] Building BM25 index from Qdrant...")
        print("   (This may take a while for large collections)")

        stats = await hybrid_search.prepare_bm25_index()

        print("   [OK] BM25 index built successfully")
        print()

        # Display statistics
        print("[3/3] Index Statistics:")
        print(f"   Documents indexed: {stats.get('documents_indexed', 0)}")
        print(f"   Corpus size: {stats.get('corpus_size', 0)}")
        print(f"   BM25 fitted: {stats.get('bm25_fitted', False)}")
        print()

        # Verify index is working
        print("[*] Verifying BM25 index...")
        test_query = "test query"

        try:
            bm25_results = await hybrid_search.keyword_search(test_query, top_k=5)
            print(f"   [OK] BM25 search working ({len(bm25_results)} results)")
        except Exception as e:
            print(f"   [WARNING] BM25 search test failed: {e}")

        print()
        print("=" * 80)
        print("[SUCCESS] BM25 Index Initialization Complete!")
        print("=" * 80)
        print()
        print("You can now use hybrid search with:")
        print("  - Vector search (semantic)")
        print("  - BM25 search (keyword)")
        print("  - Hybrid search (both with RRF fusion)")
        print()

        return 0

    except Exception as e:
        print()
        print("=" * 80)
        print(f"[ERROR] BM25 initialization failed: {e}")
        print("=" * 80)
        print()
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
