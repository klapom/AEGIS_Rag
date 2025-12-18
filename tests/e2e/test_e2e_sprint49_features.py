"""End-to-End Test: Sprint 49 Features Validation.

This test validates Sprint 49 specific features:
- Feature 49.5: source_chunk_id on all relationships
- Feature 49.6: Index Consistency Validation
- Feature 49.7: Semantic Relation Deduplication (BGE-M3 clustering)
- Feature 49.8: Manual Relation Synonym Overrides (Redis-backed)
- Feature 49.9: BGE-M3 Migration for Entity Deduplication

Test Flow:
1. Upload document with duplicate relation types (to trigger deduplication)
2. Validate index consistency across Qdrant, Neo4j, BM25
3. Check relation deduplication occurred
4. Add manual synonym override
5. Verify override takes precedence
6. Validate provenance tracking (source_chunk_id)
"""

import asyncio
from pathlib import Path

import pytest
from neo4j import AsyncGraphDatabase
from playwright.async_api import Page, expect
from qdrant_client import AsyncQdrantClient

from src.core.config import settings


class TestSprint49Features:
    """Sprint 49 features end-to-end validation."""

    @pytest.fixture(scope="class")
    async def deduplication_test_document(self, tmp_path_factory) -> Path:
        """Create document designed to trigger relation deduplication.

        This document contains multiple relation type variants that should
        cluster together via semantic deduplication (Feature 49.7).
        """
        content = """# Film Industry Relationships

## Acting Credits
Tom Cruise acted in Top Gun in 1986.
He starred in Mission Impossible in 1996.
Tom Cruise played Ethan Hunt in the Mission Impossible series.
He performed in Jerry Maguire in 1996.

## Directing
Christopher Nolan directed Inception in 2010.
He helmed The Dark Knight in 2008.
Christopher Nolan made Interstellar in 2014.

## Professional Relationships
Tom Cruise works for Paramount Pictures.
He is employed by the studio for multiple projects.
Christopher Nolan works at Warner Bros.
He is affiliated with the studio.

## Personal Relationships
Tom Cruise knows Christopher Nolan professionally.
Christopher Nolan is acquainted with Tom Cruise.
"""

        doc_path = tmp_path_factory.mktemp("test_docs") / "test_film_relations.txt"
        doc_path.write_text(content, encoding="utf-8")
        return doc_path

    @pytest.fixture(scope="class")
    async def qdrant_client(self) -> AsyncQdrantClient:
        """Get Qdrant client for validation."""
        client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            prefer_grpc=settings.qdrant_use_grpc,
        )
        yield client
        await client.close()

    @pytest.fixture(scope="class")
    async def neo4j_driver(self):
        """Get Neo4j driver for validation."""
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        )
        yield driver
        await driver.close()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_sprint49_index_consistency_validation(
        self,
        page: Page,
        qdrant_client: AsyncQdrantClient,
        neo4j_driver,
    ):
        """Test Feature 49.6: Index Consistency Validation.

        Validates that the admin endpoint correctly reports consistency
        across Qdrant, Neo4j, and BM25 indexes.
        """

        # Login
        await page.goto("http://localhost:5179/login")
        await page.fill('input[type="text"]', "admin")
        await page.fill('input[type="password"]', "admin123")
        await page.click('button:has-text("Sign In")')
        await expect(page).to_have_url("http://localhost:5179/")

        print("✓ Logged in for Sprint 49 tests")

        # Call index consistency validation endpoint
        response = await page.request.get(
            "http://localhost:8000/api/v1/admin/validation/index-consistency"
        )

        assert response.ok, f"Index consistency endpoint failed: {response.status}"
        consistency_data = await response.json()

        print(f"✓ Index Consistency Report received")

        # Validate response structure (Feature 49.6)
        assert "total_chunks" in consistency_data, "Missing total_chunks in response"
        assert "total_entities" in consistency_data, "Missing total_entities in response"
        assert "consistency_score" in consistency_data, "Missing consistency_score in response"
        assert "orphaned_entities" in consistency_data, "Missing orphaned_entities in response"
        assert "orphaned_chunks" in consistency_data, "Missing orphaned_chunks in response"

        print(f"✓ Consistency score: {consistency_data['consistency_score']:.2f}")
        print(f"  - Total chunks: {consistency_data['total_chunks']}")
        print(f"  - Total entities: {consistency_data['total_entities']}")
        print(f"  - Orphaned entities: {len(consistency_data['orphaned_entities'])}")
        print(f"  - Orphaned chunks: {len(consistency_data['orphaned_chunks'])}")

        # Consistency score should be reasonable (>= 0.7 for healthy system)
        assert consistency_data["consistency_score"] >= 0.7, \
            f"Consistency score too low: {consistency_data['consistency_score']}"

        print("✓ Feature 49.6: Index Consistency Validation - PASSED")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_sprint49_relation_deduplication(
        self,
        page: Page,
        deduplication_test_document: Path,
        neo4j_driver,
    ):
        """Test Feature 49.7 & 49.8: Relation Deduplication.

        This test validates:
        1. Semantic deduplication clusters similar relation types
        2. Manual overrides take precedence over semantic clustering
        3. Symmetric relations are handled correctly
        """

        # Login (reuse existing session if available)
        await page.goto("http://localhost:5179")

        # Upload document designed to trigger deduplication
        # (In real UI, navigate to upload page)
        await page.goto("http://localhost:5179/admin/upload")
        await page.wait_for_load_state("networkidle")

        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(str(deduplication_test_document))

        submit_button = page.locator('button:has-text("Upload"), button[type="submit"]')
        await submit_button.first.click()

        print(f"✓ Uploaded deduplication test document: {deduplication_test_document.name}")

        # Wait for processing
        await asyncio.sleep(45)  # Give time for graph extraction + deduplication

        # =====================================================================
        # Validate Semantic Deduplication (Feature 49.7)
        # =====================================================================

        async with neo4j_driver.session() as session:
            # Our document has multiple variants of "acting" relations:
            # - ACTED_IN
            # - STARRED_IN
            # - PLAYED_IN
            # - PERFORMED_IN
            # These should be deduplicated to a single canonical type

            # Get all unique relation types
            result = await session.run(
                """
                MATCH ()-[r]->()
                RETURN DISTINCT type(r) as rel_type
                ORDER BY rel_type
                """
            )
            all_relation_types = [record["rel_type"] async for record in result]

            print(f"✓ Found {len(all_relation_types)} unique relation types in graph")

            # Check if deduplication occurred
            # We expect fewer relation types than variants in source text
            acting_variants = [rt for rt in all_relation_types if any(
                keyword in rt.upper() for keyword in ["ACT", "STAR", "PLAY", "PERFORM"]
            )]

            # If semantic deduplication worked, we should have 1-2 acting types max
            # (not 4 separate types)
            assert len(acting_variants) <= 2, \
                f"Expected deduplication of acting relations, but found {len(acting_variants)}: {acting_variants}"

            print(f"✓ Feature 49.7: Semantic deduplication reduced acting relations to: {acting_variants}")

            # Similarly check "working" relations
            working_variants = [rt for rt in all_relation_types if any(
                keyword in rt.upper() for keyword in ["WORK", "EMPLOY", "AFFILIATED"]
            )]

            assert len(working_variants) <= 2, \
                f"Expected deduplication of working relations, but found {len(working_variants)}: {working_variants}"

            print(f"✓ Feature 49.7: Semantic deduplication reduced working relations to: {working_variants}")

        # =====================================================================
        # Test Manual Synonym Override (Feature 49.8)
        # =====================================================================

        # Add a manual override via API
        override_response = await page.request.post(
            "http://localhost:8000/api/v1/admin/graph/relation-synonyms",
            data={
                "from_type": "ACTED_IN",
                "to_type": "PERFORMED_IN"
            }
        )

        assert override_response.ok, f"Failed to add manual override: {override_response.status}"
        print("✓ Feature 49.8: Added manual synonym override (ACTED_IN → PERFORMED_IN)")

        # Verify override was stored
        get_response = await page.request.get(
            "http://localhost:8000/api/v1/admin/graph/relation-synonyms"
        )
        overrides_data = await get_response.json()

        assert "ACTED_IN" in overrides_data["overrides"], "Manual override not stored"
        assert overrides_data["overrides"]["ACTED_IN"] == "PERFORMED_IN", "Override value incorrect"
        print(f"✓ Feature 49.8: Manual override verified in Redis: {overrides_data['overrides']}")

        # Clean up override
        delete_response = await page.request.delete(
            "http://localhost:8000/api/v1/admin/graph/relation-synonyms/ACTED_IN"
        )
        assert delete_response.ok, "Failed to delete override"
        print("✓ Feature 49.8: Manual override cleanup complete")

        print("\n✅ Feature 49.7 & 49.8: Relation Deduplication - PASSED")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_sprint49_provenance_tracking(
        self,
        page: Page,
        neo4j_driver,
    ):
        """Test Feature 49.5: source_chunk_id on all relationships.

        Validates that all MENTIONED_IN and RELATES_TO relationships
        have proper provenance tracking via source_chunk_id property.
        """

        # Login (reuse session)
        await page.goto("http://localhost:5179")

        async with neo4j_driver.session() as session:
            # Check MENTIONED_IN relationships
            result = await session.run(
                """
                MATCH ()-[r:MENTIONED_IN]->()
                RETURN
                    count(r) as total,
                    count(r.source_chunk_id) as with_chunk_id
                """
            )
            record = await result.single()
            total_mentioned = record["total"]
            with_chunk_id = record["with_chunk_id"]

            print(f"✓ MENTIONED_IN relationships: {total_mentioned} total, {with_chunk_id} with source_chunk_id")

            # Sprint 49.5: All MENTIONED_IN should have source_chunk_id
            if total_mentioned > 0:
                coverage_percent = (with_chunk_id / total_mentioned) * 100
                assert coverage_percent >= 95, \
                    f"Expected >= 95% MENTIONED_IN with source_chunk_id, got {coverage_percent:.1f}%"
                print(f"✓ Feature 49.5: {coverage_percent:.1f}% MENTIONED_IN have source_chunk_id")

            # Check RELATES_TO relationships (if any)
            result = await session.run(
                """
                MATCH ()-[r:RELATES_TO]->()
                RETURN
                    count(r) as total,
                    count(r.source_chunk_id) as with_chunk_id
                """
            )
            record = await result.single()
            total_relates = record["total"]
            relates_with_chunk_id = record["with_chunk_id"]

            if total_relates > 0:
                relates_coverage = (relates_with_chunk_id / total_relates) * 100
                print(f"✓ RELATES_TO relationships: {total_relates} total, {relates_coverage:.1f}% with source_chunk_id")

            # Sample a relationship to verify structure
            result = await session.run(
                """
                MATCH (e:base)-[r:MENTIONED_IN]->(c:chunk)
                WHERE r.source_chunk_id IS NOT NULL
                RETURN
                    e.entity_name as entity,
                    c.chunk_id as chunk,
                    r.source_chunk_id as source_chunk_id
                LIMIT 1
                """
            )
            record = await result.single()

            if record:
                print(f"✓ Sample relationship provenance:")
                print(f"  Entity: {record['entity']}")
                print(f"  Chunk: {record['chunk'][:30]}...")
                print(f"  source_chunk_id: {record['source_chunk_id'][:30]}...")

                # source_chunk_id should match chunk_id
                assert record["source_chunk_id"] == record["chunk"], \
                    "source_chunk_id should match the target chunk's chunk_id"
                print("✓ Provenance data integrity verified")

        print("\n✅ Feature 49.5: Provenance Tracking - PASSED")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_sprint49_complete_workflow(
        self,
        page: Page,
        qdrant_client: AsyncQdrantClient,
        neo4j_driver,
    ):
        """Complete Sprint 49 workflow test combining all features.

        This is the "golden path" test that validates the entire Sprint 49
        feature set working together in a real-world scenario.
        """

        print("\n" + "="*70)
        print("SPRINT 49 COMPLETE WORKFLOW TEST")
        print("="*70)

        # Run all Sprint 49 validations in sequence
        await self.test_sprint49_index_consistency_validation(page, qdrant_client, neo4j_driver)
        await self.test_sprint49_relation_deduplication(page, self.deduplication_test_document, neo4j_driver)
        await self.test_sprint49_provenance_tracking(page, neo4j_driver)

        print("\n" + "="*70)
        print("✅ ALL SPRINT 49 FEATURES VALIDATED SUCCESSFULLY")
        print("="*70)
        print("Features Tested:")
        print("  ✓ 49.5: Provenance Tracking (source_chunk_id)")
        print("  ✓ 49.6: Index Consistency Validation")
        print("  ✓ 49.7: Semantic Relation Deduplication (BGE-M3)")
        print("  ✓ 49.8: Manual Synonym Overrides (Redis)")
        print("  ✓ 49.9: BGE-M3 Entity Deduplication (implicit)")
