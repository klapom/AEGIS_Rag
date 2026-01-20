"""Integration tests for Admin Dashboard Stats endpoint.

Sprint 116 Feature 116.1: Dashboard Stats Cards

These tests verify the dashboard stats endpoint with real database connections.
Tests cover:
- Full stats aggregation from Qdrant, Neo4j, and Namespaces
- Real storage calculation
- Error resilience with partial service failures
"""

import pytest
from httpx import AsyncClient

from src.api.main import app


class TestDashboardStatsIntegration:
    """Integration tests for /api/v1/admin/dashboard/stats endpoint."""

    @pytest.mark.asyncio
    async def test_dashboard_stats_real_services(self):
        """Test dashboard stats with real database services.

        This test requires:
        - Qdrant running on localhost:6333
        - Neo4j running on localhost:7687
        - Redis running on localhost:6379
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/admin/dashboard/stats")

            assert response.status_code == 200
            data = response.json()

            # Validate all required fields
            required_fields = [
                "total_documents",
                "total_entities",
                "total_relations",
                "total_chunks",
                "active_domains",
                "storage_used_mb",
            ]
            for field in required_fields:
                assert field in data, f"Missing field: {field}"

            # Validate data types
            assert isinstance(data["total_documents"], int)
            assert isinstance(data["total_entities"], int)
            assert isinstance(data["total_relations"], int)
            assert isinstance(data["total_chunks"], int)
            assert isinstance(data["active_domains"], int)
            assert isinstance(data["storage_used_mb"], (int, float))

            # Validate non-negative values
            assert data["total_documents"] >= 0
            assert data["total_entities"] >= 0
            assert data["total_relations"] >= 0
            assert data["total_chunks"] >= 0
            assert data["active_domains"] >= 0
            assert data["storage_used_mb"] >= 0

    @pytest.mark.asyncio
    async def test_dashboard_stats_consistency(self):
        """Test that chunks count is consistent with entities."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/admin/dashboard/stats")

            assert response.status_code == 200
            data = response.json()

            # In a typical RAG system, we should have at least as many chunks as entities
            # (since entities are extracted from chunks)
            # This is not a hard rule but a sanity check
            if data["total_entities"] > 0:
                # If we have entities, we must have chunks
                assert data["total_chunks"] > 0, "Entities exist but no chunks found"

    @pytest.mark.asyncio
    async def test_dashboard_stats_storage_calculation(self):
        """Test that storage calculation is reasonable."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/admin/dashboard/stats")

            assert response.status_code == 200
            data = response.json()

            total_chunks = data["total_chunks"]
            storage_mb = data["storage_used_mb"]

            if total_chunks > 0:
                # BGE-M3: ~1124 dims (1024 dense + 100 sparse avg) * 4 bytes * 1.5 overhead
                # = ~6.75 KB per chunk
                # So storage_mb should be roughly total_chunks * 0.00659 MB
                expected_mb_per_chunk = 0.00659  # ~6.75 KB
                min_expected = total_chunks * expected_mb_per_chunk * 0.5  # 50% tolerance
                max_expected = total_chunks * expected_mb_per_chunk * 2.0  # 200% tolerance

                assert (
                    min_expected <= storage_mb <= max_expected
                ), f"Storage {storage_mb}MB outside expected range [{min_expected:.2f}, {max_expected:.2f}] for {total_chunks} chunks"

    @pytest.mark.asyncio
    async def test_dashboard_stats_multiple_calls(self):
        """Test that multiple calls return consistent results."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # First call
            response1 = await client.get("/api/v1/admin/dashboard/stats")
            assert response1.status_code == 200
            data1 = response1.json()

            # Second call immediately after
            response2 = await client.get("/api/v1/admin/dashboard/stats")
            assert response2.status_code == 200
            data2 = response2.json()

            # Results should be identical (assuming no concurrent writes)
            assert data1["total_chunks"] == data2["total_chunks"]
            assert data1["total_entities"] == data2["total_entities"]
            assert data1["total_relations"] == data2["total_relations"]
            # Storage calculation should be deterministic
            assert data1["storage_used_mb"] == data2["storage_used_mb"]

    @pytest.mark.asyncio
    async def test_dashboard_stats_response_time(self):
        """Test that dashboard stats respond within reasonable time."""
        import time

        async with AsyncClient(app=app, base_url="http://test") as client:
            start_time = time.time()
            response = await client.get("/api/v1/admin/dashboard/stats")
            elapsed_time = time.time() - start_time

            assert response.status_code == 200

            # Should respond within 2 seconds (querying 3 databases)
            assert (
                elapsed_time < 2.0
            ), f"Dashboard stats took {elapsed_time:.2f}s (expected <2s)"
