"""Tests for unified embedding service."""

import pytest

from src.components.shared.embedding_service import UnifiedEmbeddingService


@pytest.mark.asyncio
async def test_embed_single():
    """Test single text embedding."""
    service = UnifiedEmbeddingService()
    embedding = await service.embed_single("AEGIS RAG")

    assert len(embedding) == 1024  # bge-m3 dimension
    assert all(isinstance(x, float) for x in embedding)


@pytest.mark.asyncio
async def test_embed_batch():
    """Test batch embedding."""
    service = UnifiedEmbeddingService()
    texts = ["AEGIS RAG", "LangGraph", "Neo4j"]

    embeddings = await service.embed_batch(texts)

    assert len(embeddings) == 3
    assert all(len(emb) == 1024 for emb in embeddings)


@pytest.mark.asyncio
async def test_caching():
    """Test embedding cache."""
    service = UnifiedEmbeddingService()

    # First call - cache miss
    emb1 = await service.embed_single("test")
    assert service.cache.stats()["misses"] == 1

    # Second call - cache hit
    emb2 = await service.embed_single("test")
    assert service.cache.stats()["hits"] == 1
    assert emb1 == emb2


@pytest.mark.asyncio
async def test_cache_sharing():
    """Test cache sharing across components."""
    service = UnifiedEmbeddingService()

    # Simulate Qdrant embedding
    qdrant_emb = await service.embed_single("LangGraph")

    # Simulate LightRAG embedding (same text as entity)
    lightrag_emb = await service.embed_single("LangGraph")

    # Should hit cache
    assert service.cache.stats()["hits"] >= 1
    assert qdrant_emb == lightrag_emb
