"""Simple re-indexing script with detailed progress logging."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.components.shared.embedding_service import get_embedding_service
from src.components.vector_search.qdrant_client import get_qdrant_client
from src.core.config import settings
from qdrant_client.models import Distance


async def main():
    """Re-index documents with detailed progress."""
    input_dir = Path("data/sample_documents/1. Basic Admin")

    print("=" * 80)
    print("AEGIS RAG - Document Re-Indexing")
    print("=" * 80)
    print(f"Input Directory: {input_dir}")
    print()

    # Step 1: Initialize services
    print("[1/5] Initializing services...")
    embedding_service = get_embedding_service()
    qdrant_client = get_qdrant_client()
    collection_name = settings.qdrant_collection
    print(f"  [OK] Embedding Service: {embedding_service.model_name} (dim={embedding_service.embedding_dim})")
    print(f"  [OK] Qdrant Client ready")
    print(f"  [OK] Collection: {collection_name}")
    print()

    # Step 2: Discover documents
    print("[2/5] Discovering documents...")
    pdf_files = list(input_dir.glob("*.pdf"))
    txt_files = list(input_dir.glob("*.txt"))
    docx_files = list(input_dir.glob("*.docx"))
    all_files = pdf_files + txt_files + docx_files
    print(f"  [OK] Found {len(pdf_files)} PDF files")
    print(f"  [OK] Found {len(txt_files)} TXT files")
    print(f"  [OK] Found {len(docx_files)} DOCX files")
    print(f"  [OK] Total: {len(all_files)} documents")
    for i, file in enumerate(all_files, 1):
        print(f"    {i}. {file.name}")
    print()

    # Step 3: Delete old collection
    print("[3/5] Deleting old collection...")
    try:
        await qdrant_client.delete_collection(collection_name)
        print(f"  [OK] Deleted collection: {collection_name}")
    except Exception as e:
        print(f"  [WARN] Collection may not exist: {e}")

    # Step 4: Create new collection
    print("[4/5] Creating new collection...")
    embedding_dim = embedding_service.embedding_dim
    await qdrant_client.create_collection(
        collection_name=collection_name,
        vector_size=embedding_dim,
        distance=Distance.COSINE,
    )
    print(f"  [OK] Created collection: {collection_name} (dimension={embedding_dim})")
    print()

    # Step 5: Index documents
    print("[5/5] Indexing documents...")
    print("  This may take a while for large PDFs...")
    print()

    from src.components.vector_search.ingestion import ingest_documents

    try:
        stats = await ingest_documents(
            input_dir=input_dir,
            collection_name=collection_name,
        )

        print()
        print("=" * 80)
        print("[SUCCESS] INDEXING COMPLETE")
        print("=" * 80)
        print(f"Documents processed: {stats.get('documents_processed', 0)}")
        print(f"Chunks indexed: {stats.get('points_indexed', 0)}")
        print(f"Time taken: {stats.get('total_time_seconds', 0):.1f}s")
        print("=" * 80)

    except Exception as e:
        print()
        print("=" * 80)
        print("[ERROR] INDEXING FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
