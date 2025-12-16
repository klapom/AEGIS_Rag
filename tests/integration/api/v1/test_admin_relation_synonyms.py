"""Integration tests for admin relation synonym override endpoints.

Sprint 49 Feature 49.8: Manual synonym overrides for relation deduplication.
Tests the full API flow including Redis persistence.

Author: Claude Code
Date: 2025-12-16
"""

import pytest
from fastapi import status
from httpx import AsyncClient
from redis.asyncio import Redis

from src.api.main import app
from src.components.graph_rag.hybrid_relation_deduplicator import REDIS_KEY_RELATION_SYNONYMS
from src.core.config import settings


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def clean_redis():
    """Clean up Redis before and after tests."""
    # Create fresh Redis client for cleanup
    redis_client = await Redis.from_url(
        settings.redis_memory_url,
        decode_responses=True,
    )

    try:
        # Clean before test
        await redis_client.delete(REDIS_KEY_RELATION_SYNONYMS)

        yield

        # Clean after test
        await redis_client.delete(REDIS_KEY_RELATION_SYNONYMS)
    finally:
        await redis_client.aclose()


# ============================================================================
# GET /api/v1/admin/graph/relation-synonyms Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_relation_synonyms_empty(client: AsyncClient, clean_redis):
    """Test getting synonyms when none exist."""
    response = await client.get("/api/v1/admin/graph/relation-synonyms")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["overrides"] == {}
    assert data["total_overrides"] == 0


@pytest.mark.asyncio
async def test_get_relation_synonyms_with_data(client: AsyncClient, clean_redis):
    """Test getting synonyms after adding some."""
    # Add overrides via API
    await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "USES", "to_type": "USED_BY"},
    )
    await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "ACTED_IN", "to_type": "STARRED_IN"},
    )

    # Get all overrides
    response = await client.get("/api/v1/admin/graph/relation-synonyms")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_overrides"] == 2
    assert "USES" in data["overrides"]
    assert data["overrides"]["USES"] == "USED_BY"
    assert "ACTED_IN" in data["overrides"]
    assert data["overrides"]["ACTED_IN"] == "STARRED_IN"


# ============================================================================
# POST /api/v1/admin/graph/relation-synonyms Tests
# ============================================================================


@pytest.mark.asyncio
async def test_add_relation_synonym_success(client: AsyncClient, clean_redis):
    """Test successfully adding a relation synonym override."""
    response = await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "USES", "to_type": "USED_BY"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["from_type"] == "USES"
    assert data["to_type"] == "USED_BY"
    assert data["status"] == "created"

    # Verify it was stored in Redis
    redis_client = await Redis.from_url(
        settings.redis_memory_url,
        decode_responses=True,
    )
    try:
        stored_value = await redis_client.hget(REDIS_KEY_RELATION_SYNONYMS, "USES")
        assert stored_value == "USED_BY"
    finally:
        await redis_client.aclose()


@pytest.mark.asyncio
async def test_add_relation_synonym_normalizes_case(client: AsyncClient, clean_redis):
    """Test that relation types are normalized to uppercase."""
    response = await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "uses", "to_type": "used_by"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["from_type"] == "USES"
    assert data["to_type"] == "USED_BY"


@pytest.mark.asyncio
async def test_add_relation_synonym_normalizes_dashes(client: AsyncClient, clean_redis):
    """Test that dashes are normalized to underscores."""
    response = await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "WORKS-AT", "to_type": "EMPLOYED-BY"},
    )

    assert response.status_code == status.HTTP_201_CREATED

    # Verify normalization
    redis_client = await Redis.from_url(
        settings.redis_memory_url,
        decode_responses=True,
    )
    try:
        stored_value = await redis_client.hget(REDIS_KEY_RELATION_SYNONYMS, "WORKS_AT")
        assert stored_value == "EMPLOYED_BY"
    finally:
        await redis_client.aclose()


@pytest.mark.asyncio
async def test_add_relation_synonym_updates_existing(client: AsyncClient, clean_redis):
    """Test that adding an existing override updates it."""
    # Add initial override
    await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "USES", "to_type": "USED_BY"},
    )

    # Update with different value
    response = await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "USES", "to_type": "UTILIZED_BY"},
    )

    assert response.status_code == status.HTTP_201_CREATED

    # Verify updated value
    redis_client = await Redis.from_url(
        settings.redis_memory_url,
        decode_responses=True,
    )
    try:
        stored_value = await redis_client.hget(REDIS_KEY_RELATION_SYNONYMS, "USES")
        assert stored_value == "UTILIZED_BY"
    finally:
        await redis_client.aclose()


@pytest.mark.asyncio
async def test_add_relation_synonym_empty_from_type(client: AsyncClient, clean_redis):
    """Test validation for empty from_type."""
    response = await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "", "to_type": "USED_BY"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_add_relation_synonym_empty_to_type(client: AsyncClient, clean_redis):
    """Test validation for empty to_type."""
    response = await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "USES", "to_type": ""},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_add_relation_synonym_missing_fields(client: AsyncClient, clean_redis):
    """Test validation for missing required fields."""
    response = await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "USES"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# DELETE /api/v1/admin/graph/relation-synonyms/{from_type} Tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_relation_synonym_success(client: AsyncClient, clean_redis):
    """Test successfully deleting a relation synonym override."""
    # Add override first
    await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "USES", "to_type": "USED_BY"},
    )

    # Delete it
    response = await client.delete("/api/v1/admin/graph/relation-synonyms/USES")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["from_type"] == "USES"
    assert data["status"] == "deleted"

    # Verify it was removed from Redis
    redis_client = await Redis.from_url(
        settings.redis_memory_url,
        decode_responses=True,
    )
    try:
        stored_value = await redis_client.hget(REDIS_KEY_RELATION_SYNONYMS, "USES")
        assert stored_value is None
    finally:
        await redis_client.aclose()


@pytest.mark.asyncio
async def test_delete_relation_synonym_not_found(client: AsyncClient, clean_redis):
    """Test deleting a non-existent override returns 404."""
    response = await client.delete("/api/v1/admin/graph/relation-synonyms/NONEXISTENT")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "No override found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_relation_synonym_case_insensitive(client: AsyncClient, clean_redis):
    """Test that delete is case-insensitive."""
    # Add override
    await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "USES", "to_type": "USED_BY"},
    )

    # Delete with lowercase
    response = await client.delete("/api/v1/admin/graph/relation-synonyms/uses")

    assert response.status_code == status.HTTP_200_OK


# ============================================================================
# POST /api/v1/admin/graph/relation-synonyms/reset Tests
# ============================================================================


@pytest.mark.asyncio
async def test_reset_relation_synonyms_success(client: AsyncClient, clean_redis):
    """Test successfully resetting all relation synonym overrides."""
    # Add multiple overrides
    await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "USES", "to_type": "USED_BY"},
    )
    await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "ACTED_IN", "to_type": "STARRED_IN"},
    )
    await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "RELATED_TO", "to_type": "RELATES_TO"},
    )

    # Reset all
    response = await client.post("/api/v1/admin/graph/relation-synonyms/reset")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["cleared_count"] == 3
    assert data["status"] == "reset_complete"

    # Verify Redis is empty
    redis_client = await Redis.from_url(
        settings.redis_memory_url,
        decode_responses=True,
    )
    try:
        all_data = await redis_client.hgetall(REDIS_KEY_RELATION_SYNONYMS)
        assert len(all_data) == 0
    finally:
        await redis_client.aclose()


@pytest.mark.asyncio
async def test_reset_relation_synonyms_when_empty(client: AsyncClient, clean_redis):
    """Test resetting when no overrides exist."""
    response = await client.post("/api/v1/admin/graph/relation-synonyms/reset")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["cleared_count"] == 0
    assert data["status"] == "reset_complete"


# ============================================================================
# End-to-End Workflow Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_crud_workflow(client: AsyncClient, clean_redis):
    """Test complete CRUD workflow for relation synonym overrides."""
    # 1. Verify initially empty
    response = await client.get("/api/v1/admin/graph/relation-synonyms")
    assert response.json()["total_overrides"] == 0

    # 2. Add first override
    response = await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "USES", "to_type": "USED_BY"},
    )
    assert response.status_code == status.HTTP_201_CREATED

    # 3. Add second override
    response = await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "ACTED_IN", "to_type": "STARRED_IN"},
    )
    assert response.status_code == status.HTTP_201_CREATED

    # 4. Verify both exist
    response = await client.get("/api/v1/admin/graph/relation-synonyms")
    data = response.json()
    assert data["total_overrides"] == 2
    assert "USES" in data["overrides"]
    assert "ACTED_IN" in data["overrides"]

    # 5. Update one override
    response = await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "USES", "to_type": "UTILIZED_BY"},
    )
    assert response.status_code == status.HTTP_201_CREATED

    # 6. Verify update
    response = await client.get("/api/v1/admin/graph/relation-synonyms")
    data = response.json()
    assert data["overrides"]["USES"] == "UTILIZED_BY"

    # 7. Delete one override
    response = await client.delete("/api/v1/admin/graph/relation-synonyms/USES")
    assert response.status_code == status.HTTP_200_OK

    # 8. Verify deletion
    response = await client.get("/api/v1/admin/graph/relation-synonyms")
    data = response.json()
    assert data["total_overrides"] == 1
    assert "USES" not in data["overrides"]
    assert "ACTED_IN" in data["overrides"]

    # 9. Reset all
    response = await client.post("/api/v1/admin/graph/relation-synonyms/reset")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["cleared_count"] == 1

    # 10. Verify empty
    response = await client.get("/api/v1/admin/graph/relation-synonyms")
    assert response.json()["total_overrides"] == 0


@pytest.mark.asyncio
async def test_persistence_across_requests(client: AsyncClient, clean_redis):
    """Test that overrides persist across multiple requests."""
    # Add override
    await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "USES", "to_type": "USED_BY"},
    )

    # Verify persistence with multiple GET requests
    for _ in range(3):
        response = await client.get("/api/v1/admin/graph/relation-synonyms")
        data = response.json()
        assert data["total_overrides"] == 1
        assert data["overrides"]["USES"] == "USED_BY"


@pytest.mark.asyncio
async def test_special_characters_in_relation_types(client: AsyncClient, clean_redis):
    """Test handling of special characters in relation types."""
    # Add override with spaces and dashes
    response = await client.post(
        "/api/v1/admin/graph/relation-synonyms",
        json={"from_type": "WORKS AT", "to_type": "EMPLOYED-BY"},
    )

    assert response.status_code == status.HTTP_201_CREATED

    # Verify normalization
    response = await client.get("/api/v1/admin/graph/relation-synonyms")
    data = response.json()
    assert "WORKS_AT" in data["overrides"]
    assert data["overrides"]["WORKS_AT"] == "EMPLOYED_BY"


@pytest.mark.asyncio
async def test_concurrent_operations(client: AsyncClient, clean_redis):
    """Test handling of concurrent add operations."""
    import asyncio

    # Add multiple overrides concurrently
    tasks = [
        client.post(
            "/api/v1/admin/graph/relation-synonyms",
            json={"from_type": f"TYPE_{i}", "to_type": f"CANONICAL_{i}"},
        )
        for i in range(10)
    ]

    responses = await asyncio.gather(*tasks)

    # All should succeed
    for response in responses:
        assert response.status_code == status.HTTP_201_CREATED

    # Verify all were stored
    response = await client.get("/api/v1/admin/graph/relation-synonyms")
    data = response.json()
    assert data["total_overrides"] == 10
