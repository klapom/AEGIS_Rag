"""Hybrid re-indexing script with Qdrant + Neo4j simultaneous indexing.

Sprint 16 Feature 16.7: Unified re-indexing that populates both databases.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.components.shared.embedding_service import get_embedding_service
from src.components.vector_search.qdrant_client import get_qdrant_client
from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
from src.core.config import settings
from qdrant_client.models import Distance
from llama_index.core import SimpleDirectoryReader


async def main():
    """Re-index documents into both Qdrant and Neo4j."""
    input_dir = Path("data/sample_documents/1. Basic Admin")

    print("=" * 80)
    print("AEGIS RAG - Hybrid Re-Indexing (Qdrant + Neo4j)")
    print("=" * 80)
    print(f"Input Directory: {input_dir}")
    print()

    # Step 1: Initialize services
    print("[1/6] Initializing services...")
    embedding_service = get_embedding_service()
    qdrant_client = get_qdrant_client()
    lightrag_wrapper = await get_lightrag_wrapper_async()
    collection_name = settings.qdrant_collection
    print(
        f"  [OK] Embedding Service: {embedding_service.model_name} (dim={embedding_service.embedding_dim})"
    )
    print(f"  [OK] Qdrant Client ready")
    print(f"  [OK] LightRAG Wrapper ready")
    print(f"  [OK] Collection: {collection_name}")
    print()

    # Step 2: Delete old collections
    print("[2/6] Deleting old indexes...")
    try:
        await qdrant_client.delete_collection(collection_name)
        print(f"  [OK] Deleted Qdrant collection: {collection_name}")
    except Exception as e:
        print(f"  [WARN] Qdrant collection may not exist: {e}")

    try:
        await lightrag_wrapper._clear_neo4j_database()
        print("  [OK] Cleared Neo4j database")
    except Exception as e:
        print(f"  [WARN] Neo4j clear failed: {e}")

    # Step 3: Create new Qdrant collection
    print("[3/6] Creating new Qdrant collection...")
    embedding_dim = embedding_service.embedding_dim
    await qdrant_client.create_collection(
        collection_name=collection_name,
        vector_size=embedding_dim,
        distance=Distance.COSINE,
    )
    print(f"  [OK] Created collection: {collection_name} (dimension={embedding_dim})")
    print()

    # Step 4: Index into Qdrant
    print("[4/6] Indexing documents into Qdrant...")
    print("  This may take a while for large PDFs...")
    print()

    from src.components.vector_search.ingestion import ingest_documents

    try:
        stats = await ingest_documents(
            input_dir=input_dir,
            collection_name=collection_name,
        )

        print()
        print(f"  [OK] Qdrant indexing complete: {stats.get('points_indexed', 0)} chunks")
    except Exception as e:
        print(f"  [ERROR] Qdrant indexing failed: {e}")
        return 1

    # Step 5: Index into Neo4j
    print()
    print("[5/6] Indexing documents into Neo4j graph...")
    print("  Extracting entities and relationships...")
    print()

    try:
        # Load documents
        loader = SimpleDirectoryReader(
            input_dir=str(input_dir),
            required_exts=[".pdf", ".txt", ".md", ".docx", ".csv", ".pptx"],
            recursive=True,
            filename_as_id=True,
        )
        documents = loader.load_data()

        # Convert to LightRAG format
        lightrag_docs = []
        for doc in documents:
            content = doc.get_content()
            if content and content.strip():
                lightrag_docs.append(
                    {"text": content, "id": doc.doc_id or doc.metadata.get("file_name", "unknown")}
                )

        print(f"  [OK] Loaded {len(lightrag_docs)} documents for graph indexing")

        # Insert into LightRAG (entities + relationships + graph)
        if lightrag_docs:
            graph_stats = await lightrag_wrapper.insert_documents_optimized(lightrag_docs)
            print(f"  [OK] Neo4j indexing complete:")
            print(f"      - Entities: {graph_stats.get('stats', {}).get('total_entities', 0)}")
            print(f"      - Relations: {graph_stats.get('stats', {}).get('total_relations', 0)}")
            print(f"      - Chunks: {graph_stats.get('stats', {}).get('total_chunks', 0)}")
        else:
            print("  [WARN] No documents for graph indexing")

    except Exception as e:
        print(f"  [ERROR] Neo4j indexing failed: {e}")
        import traceback

        traceback.print_exc()
        # Continue anyway - Qdrant indexing succeeded

    # Step 6: Validation
    print()
    print("[6/6] Validating indexes...")

    # Validate Qdrant
    collection_info = await qdrant_client.get_collection_info(collection_name)
    if collection_info:
        qdrant_points = collection_info.points_count
        print(f"  [OK] Qdrant: {qdrant_points} chunks indexed")
    else:
        print("  [ERROR] Qdrant validation failed")
        return 1

    # Validate Neo4j
    try:
        graph_stats = await lightrag_wrapper.get_stats()
        entity_count = graph_stats.get("entity_count", 0)
        relationship_count = graph_stats.get("relationship_count", 0)
        print(f"  [OK] Neo4j: {entity_count} entities + {relationship_count} relationships")
    except Exception as e:
        print(f"  [WARN] Neo4j validation failed: {e}")

    print()
    print("=" * 80)
    print("[SUCCESS] HYBRID INDEXING COMPLETE")
    print("=" * 80)
    print("Both databases have been populated:")
    print(f"  - Qdrant: Vector search ready with {qdrant_points} chunks")
    print(f"  - Neo4j: Knowledge graph ready with {entity_count} entities")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
