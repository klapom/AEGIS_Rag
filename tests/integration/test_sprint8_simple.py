"""Sprint 8 Simple E2E Test - Verify basic service connectivity.

This is a minimal test to verify all services are running correctly
before implementing the full Sprint 8 critical path tests.

NO IMPORTS from src.api.main to avoid graphiti dependency conflict.
See docs/SPRINT_8_BLOCKER.md for details.
"""

import pytest


@pytest.mark.integration
@pytest.mark.sprint8
def test_qdrant_connection():
    """E2E: Verify Qdrant is accessible and responsive."""
    from qdrant_client import QdrantClient

    client = QdrantClient(host="localhost", port=6333)

    # Verify connection
    collections = client.get_collections()
    assert collections is not None

    # Verify API version
    # Qdrant v1.11.0 should be running
    print(f"✅ Qdrant connected: {len(collections.collections)} collections")


@pytest.mark.integration
@pytest.mark.sprint8
def test_neo4j_connection():
    """E2E: Verify Neo4j is accessible and responsive."""
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "aegis_secure_2024"),
    )

    # Verify connection
    driver.verify_connectivity()

    # Execute simple query
    with driver.session() as session:
        result = session.run("RETURN 1 AS test")
        value = result.single()["test"]
        assert value == 1

    driver.close()

    print("✅ Neo4j connected and responsive")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.sprint8
async def test_ollama_embedding():
    """E2E: Verify Ollama embedding service is working."""
    from ollama import AsyncClient

    client = AsyncClient(host="http://localhost:11434")

    # Generate embedding
    response = await client.embeddings(
        model="nomic-embed-text",
        prompt="This is a test sentence for embedding generation.",
    )

    # Verify embedding
    embedding = response["embedding"]
    assert len(embedding) == 768, f"Expected 768-dim embedding, got {len(embedding)}"
    assert all(isinstance(v, float) for v in embedding), "Embedding values must be floats"

    print(f"✅ Ollama embedding: {len(embedding)}-dim vector generated")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.sprint8
@pytest.mark.slow
async def test_ollama_llm_generation():
    """E2E: Verify Ollama LLM generation is working."""
    from ollama import AsyncClient

    client = AsyncClient(host="http://localhost:11434")

    # Generate text
    response = await client.generate(
        model="llama3.2:3b",
        prompt="What is 2+2? Answer in one word.",
        options={
            "temperature": 0.0,
            "num_predict": 10,
        },
    )

    # Verify response
    generated_text = response["response"]
    assert len(generated_text) > 0, "Expected non-empty response"
    assert (
        "4" in generated_text or "four" in generated_text.lower()
    ), f"Expected '4', got: {generated_text}"

    print(f"✅ Ollama LLM generated: {generated_text.strip()}")
