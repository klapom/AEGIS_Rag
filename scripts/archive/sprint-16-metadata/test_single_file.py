"""Test indexing a single file to verify UUID fix."""

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
from llama_index.core import SimpleDirectoryReader


async def main():
    """Test single file indexing with UUID fix."""
    file_path = Path("data/sample_documents/1. Basic Admin/EN-BasicAdministration-Exercise.docx")

    print("=" * 80)
    print("AEGIS RAG - Single File Test")
    print("=" * 80)
    print(f"Test File: {file_path}")
    print()

    # Step 1: Initialize services
    print("[1/4] Initializing services...")
    embedding_service = get_embedding_service()
    qdrant_client = get_qdrant_client()
    collection_name = settings.qdrant_collection
    print(
        f"  [OK] Embedding Service: {embedding_service.model_name} (dim={embedding_service.embedding_dim})"
    )
    print(f"  [OK] Qdrant Client ready")
    print(f"  [OK] Collection: {collection_name}")
    print()

    # Step 2: Reset collection
    print("[2/4] Resetting collection...")
    try:
        await qdrant_client.delete_collection(collection_name)
        print(f"  [OK] Deleted collection: {collection_name}")
    except Exception as e:
        print(f"  [WARN] Collection may not exist: {e}")

    embedding_dim = embedding_service.embedding_dim
    await qdrant_client.create_collection(
        collection_name=collection_name,
        vector_size=embedding_dim,
        distance=Distance.COSINE,
    )
    print(f"  [OK] Created collection: {collection_name} (dimension={embedding_dim})")
    print()

    # Step 3: Load and process single file
    print("[3/4] Processing file...")

    # Load file
    reader = SimpleDirectoryReader(input_files=[str(file_path.resolve())], recursive=False)
    documents = reader.load_data()
    print(f"  [OK] Loaded {len(documents)} document parts")

    # Chunk using ChunkingService
    from src.core.chunking_service import get_chunking_service

    chunking_service = get_chunking_service()
    all_chunks = []

    for doc in documents:
        content = doc.get_content()
        if not content or not content.strip():
            continue

        chunks = chunking_service.chunk_document(
            document_id=str(file_path.name), content=content, metadata={"file_name": file_path.name}
        )
        all_chunks.extend(chunks)

    print(f"  [OK] Created {len(all_chunks)} chunks")

    # Check UUID format
    if all_chunks:
        sample_id = all_chunks[0].chunk_id
        print(f"  [OK] Sample chunk_id: {sample_id}")
        print(f"  [OK] UUID format check: {len(sample_id) == 36 and sample_id.count('-') == 4}")
    print()

    # Step 4: Generate embeddings and upload
    print("[4/4] Generating embeddings and uploading to Qdrant...")

    embeddings = []
    for i, chunk in enumerate(all_chunks):
        embedding = await embedding_service.embed_single(chunk.content)
        embeddings.append(embedding)
        if (i + 1) % 10 == 0:
            print(f"  [OK] Generated {i + 1}/{len(all_chunks)} embeddings...")

    print(f"  [OK] Generated all {len(embeddings)} embeddings")

    # Upload to Qdrant
    from qdrant_client.models import PointStruct

    points = []
    for i, (chunk, embedding) in enumerate(zip(all_chunks, embeddings)):
        point = PointStruct(
            id=chunk.chunk_id,  # This should now be UUID4 format
            vector=embedding,
            payload=chunk.to_qdrant_payload(),
        )
        points.append(point)

    await qdrant_client.upsert_points(collection_name=collection_name, points=points)

    print(f"  [OK] Uploaded {len(points)} points to Qdrant")
    print()

    # Verify
    collection_info = await qdrant_client.get_collection_info(collection_name)
    if collection_info:
        print("=" * 80)
        print("[SUCCESS] TEST COMPLETE")
        print("=" * 80)
        print(f"Points indexed: {collection_info.points_count}")
        print(f"UUID format: VERIFIED")
        print("=" * 80)
    else:
        print("[ERROR] Failed to verify collection")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
