#!/usr/bin/env python3
"""Ingest Sprint Plan documents into Qdrant for Long Context testing.

Sprint 112 Feature 112.3: Real Test Data Integration

This script indexes all Sprint Plan markdown files from docs/sprints/
into Qdrant, creating a "sprint_docs" namespace that can be used for:
- Long Context UI testing
- E2E test assertions on real data
- Context window management demos

Usage:
    python scripts/ingest_sprint_docs.py --namespace sprint_docs
    python scripts/ingest_sprint_docs.py --dry-run  # Preview without indexing
"""

import argparse
import hashlib
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.components.shared.flag_embedding_service import FlagEmbeddingService
from src.core.config import settings

logger = structlog.get_logger(__name__)

# Constants
DOCS_DIR = Path(__file__).parent.parent / "docs" / "sprints"
CHUNK_SIZE = 800  # tokens (approximate, using chars/4)
CHUNK_OVERLAP = 100  # tokens overlap between chunks
VECTOR_DIM = 1024  # BGE-M3 dimension


def get_sprint_number(filename: str) -> int | None:
    """Extract sprint number from filename."""
    match = re.search(r"SPRINT_(\d+)", filename)
    return int(match.group(1)) if match else None


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Split text into overlapping chunks with metadata.

    Args:
        text: Full document text
        chunk_size: Target chunk size in tokens (approx 4 chars per token)
        overlap: Token overlap between chunks

    Returns:
        List of chunk dicts with content, start, end positions
    """
    # Approximate tokens as chars/4
    char_chunk_size = chunk_size * 4
    char_overlap = overlap * 4

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + char_chunk_size

        # Try to break at paragraph or sentence boundary
        if end < len(text):
            # Look for paragraph break first
            para_break = text.rfind("\n\n", start, end)
            if para_break > start + char_chunk_size // 2:
                end = para_break
            else:
                # Look for sentence break
                sentence_break = text.rfind(". ", start, end)
                if sentence_break > start + char_chunk_size // 2:
                    end = sentence_break + 1

        chunk_text = text[start:end].strip()

        if chunk_text:
            # Extract section header if present
            section = None
            header_match = re.search(r"^#+\s+(.+)$", chunk_text, re.MULTILINE)
            if header_match:
                section = header_match.group(1)[:50]  # Limit length

            chunks.append({
                "content": chunk_text,
                "chunk_index": chunk_index,
                "section": section,
                "char_start": start,
                "char_end": end,
            })
            chunk_index += 1

        # Move forward with overlap
        start = end - char_overlap if end < len(text) else len(text)

    return chunks


def generate_point_id(source: str, chunk_index: int) -> str:
    """Generate deterministic point ID from source and chunk index."""
    key = f"{source}:{chunk_index}"
    return hashlib.md5(key.encode()).hexdigest()


def estimate_tokens(text: str) -> int:
    """Estimate token count (approx 4 chars per token)."""
    return len(text) // 4


def main():
    parser = argparse.ArgumentParser(description="Ingest Sprint Plan documents")
    parser.add_argument(
        "--namespace",
        default="sprint_docs",
        help="Qdrant collection namespace (default: sprint_docs)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without indexing",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and recreate collection",
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("Sprint Documents Ingestion")
    print(f"{'='*60}")
    print(f"Source: {DOCS_DIR}")
    print(f"Namespace: {args.namespace}")
    print(f"Dry run: {args.dry_run}")
    print(f"{'='*60}\n")

    # Find all Sprint Plan files
    sprint_files = sorted(DOCS_DIR.glob("SPRINT_*.md"))

    if not sprint_files:
        print(f"❌ No Sprint Plan files found in {DOCS_DIR}")
        return 1

    print(f"Found {len(sprint_files)} Sprint Plan files:\n")

    # Collect all chunks
    all_chunks: list[dict[str, Any]] = []

    for file_path in sprint_files:
        content = file_path.read_text(encoding="utf-8")
        sprint_num = get_sprint_number(file_path.name)

        # Chunk the document
        chunks = chunk_text(content)

        file_tokens = estimate_tokens(content)

        print(f"  📄 {file_path.name}")
        print(f"     Sprint: {sprint_num or 'N/A'} | Chunks: {len(chunks)} | Tokens: ~{file_tokens:,}")

        for chunk in chunks:
            chunk.update({
                "source": file_path.name,
                "sprint_number": sprint_num,
                "document_type": "sprint_plan",
                "namespace": args.namespace,
                "uploaded_at": datetime.now().isoformat(),
                "token_count": estimate_tokens(chunk["content"]),
            })
            all_chunks.append(chunk)

    total_tokens = sum(c["token_count"] for c in all_chunks)

    print(f"\n{'='*60}")
    print(f"Total: {len(sprint_files)} files | {len(all_chunks)} chunks | ~{total_tokens:,} tokens")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("✓ Dry run complete. Use without --dry-run to index.")
        return 0

    # Initialize clients
    print("Connecting to Qdrant...")
    qdrant = QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )

    collection_name = f"aegis_{args.namespace}"

    # Check/create collection
    try:
        if args.recreate:
            print(f"Deleting existing collection: {collection_name}")
            qdrant.delete_collection(collection_name)
    except Exception:
        pass  # Collection may not exist

    try:
        qdrant.get_collection(collection_name)
        print(f"Using existing collection: {collection_name}")
    except Exception:
        print(f"Creating collection: {collection_name}")
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            },
        )

    # Initialize embedding service
    print("Initializing BGE-M3 embedding service...")
    embedding_service = FlagEmbeddingService()

    # Index chunks in batches
    batch_size = 10
    total_indexed = 0

    print(f"\nIndexing {len(all_chunks)} chunks...")

    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]

        # Generate embeddings using internal sync method (embed_batch is async)
        texts = [c["content"] for c in batch]
        results = embedding_service._embed_batch_sync(texts)
        embeddings = [r["dense"] for r in results]

        # Create points
        points = []
        for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
            point_id = generate_point_id(chunk["source"], chunk["chunk_index"])

            # embed_batch_dense returns list[list[float]] directly
            vector = embedding

            points.append(
                PointStruct(
                    id=point_id,
                    vector={"dense": vector},
                    payload={
                        "text": chunk["content"],
                        "source": chunk["source"],
                        "section": chunk["section"],
                        "chunk_index": chunk["chunk_index"],
                        "sprint_number": chunk["sprint_number"],
                        "document_type": chunk["document_type"],
                        "namespace": chunk["namespace"],
                        "token_count": chunk["token_count"],
                        "uploaded_at": chunk["uploaded_at"],
                        "relevance_score": 0.7,  # Default score
                    },
                )
            )

        # Upsert to Qdrant
        qdrant.upsert(collection_name=collection_name, points=points)
        total_indexed += len(points)

        # Progress
        progress = (i + len(batch)) / len(all_chunks) * 100
        print(f"  Progress: {progress:.1f}% ({total_indexed}/{len(all_chunks)} chunks)")

    print(f"\n{'='*60}")
    print(f"✅ Successfully indexed {total_indexed} chunks into {collection_name}")
    print(f"{'='*60}\n")

    # Verify
    collection_info = qdrant.get_collection(collection_name)
    print(f"Collection info:")
    print(f"  Points: {collection_info.points_count}")
    print(f"  Vectors: {collection_info.vectors_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
