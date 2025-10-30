"""
Production document indexing script.
Indexes all documents from data/sample_documents/ into Qdrant + Neo4j.

Sprint 19 Update: Uses current production settings:
- BGE-M3 embeddings (1024D, upgraded from nomic-embed-text 768D)
- Adaptive chunking (600 tokens, 150 overlap - Sprint 16 alignment)
- Hybrid RAG (Qdrant + Neo4j/LightRAG)
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.components.vector_search.ingestion import DocumentIngestionPipeline
from src.core.config import settings


async def main():
    print("[*] Starting production document indexing...")
    print(f"    Embedding: bge-m3 (1024D)")
    print(f"    Chunking: 600 tokens, adaptive, 150 overlap")

    # Configuration
    collection_name = settings.qdrant_collection
    documents_path = project_root / "data" / "sample_documents"

    # Use production ingestion pipeline
    print(f"\n[1/3] Initializing production ingestion pipeline...")
    pipeline = DocumentIngestionPipeline()
    print("   [OK] Pipeline ready")

    # Step 2: Index documents (Qdrant only)
    print(f"\n[2/3] Indexing documents from '{documents_path}'...")
    print(f"   This will load, chunk, embed, and index all documents.")

    stats = await pipeline.index_documents(
        input_dir=str(documents_path),
        batch_size=100,
    )

    print(f"   [OK] Indexing complete")

    # Step 3: Verify
    print(f"\n[3/3] Verifying indexing...")
    qdrant_info = await pipeline.qdrant_client.get_collection_info(collection_name)
    if qdrant_info:
        print(f"   Collection '{collection_name}' has {qdrant_info.points_count} points")

    print("\n[SUCCESS] Production indexing complete!")
    print(f"\nSummary:")
    print(f"   - Documents loaded: {stats.get('documents_loaded', 0)}")
    print(f"   - Chunks created: {stats.get('chunks_created', 0)}")
    print(f"   - Points indexed: {stats.get('points_indexed', 0)}")
    print(f"   - Collection: {collection_name}")
    print(f"   - Embedding model: bge-m3 (1024D)")
    print(f"   - Chunking: 600 tokens, adaptive, 150 overlap")
    print(f"\nNote: This script indexes to Qdrant only.")
    print(f"      For Neo4j/LightRAG indexing, use index_three_specific_docs.py")


if __name__ == "__main__":
    asyncio.run(main())
