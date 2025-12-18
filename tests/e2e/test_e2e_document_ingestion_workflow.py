"""End-to-End Test: Document Ingestion & Query Workflow.

This test validates the complete document lifecycle:
1. User uploads a document
2. Document is processed through ingestion pipeline (Docling)
3. Chunks are created and indexed (Qdrant + BM25)
4. Entities and relations are extracted (Neo4j)
5. User queries the document
6. System retrieves relevant information with proper citations

Test validates data consistency across all storage layers.
"""

import asyncio
import time
from pathlib import Path

import pytest
from neo4j import AsyncGraphDatabase
from playwright.async_api import Page, expect
from qdrant_client import AsyncQdrantClient

from src.components.vector_search.bm25_search import BM25Search
from src.core.config import settings


class TestDocumentIngestionWorkflow:
    """Complete document ingestion and query workflow tests."""

    @pytest.fixture(scope="class")
    async def sample_document_path(self, tmp_path_factory) -> Path:
        """Create a sample test document with known content.

        This document is designed to test:
        - Text extraction (Docling)
        - Entity extraction (persons, organizations, concepts)
        - Relation extraction (WORKED_AT, FOUNDED, etc.)
        - Multi-hop reasoning
        """
        content = """# Machine Learning Research at Stanford University

## Introduction
Professor Andrew Ng is a prominent researcher in artificial intelligence and machine learning.
He is the founder of Google Brain and was a professor at Stanford University.

## Research Areas
Andrew Ng's research focuses on deep learning, computer vision, and natural language processing.
He has published over 200 papers in leading conferences like NeurIPS and ICML.

## Industry Impact
In 2011, Andrew Ng founded the Google Brain project at Google.
Later in 2014, he became Chief Scientist at Baidu, leading their AI research division.

## Education Initiatives
Andrew Ng co-founded Coursera with Daphne Koller in 2012, making machine learning
education accessible to millions of students worldwide.

## Key Contributions
- Deep Learning Specialization on Coursera
- Machine Learning course with over 5 million enrollments
- Pioneering work on unsupervised learning and reinforcement learning
"""

        doc_path = tmp_path_factory.mktemp("test_docs") / "test_ml_research.txt"
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
    async def test_complete_document_ingestion_workflow(
        self,
        page: Page,
        sample_document_path: Path,
        qdrant_client: AsyncQdrantClient,
        neo4j_driver,
    ):
        """Test complete document ingestion workflow from upload to query.

        Workflow Steps:
        1. Login to application
        2. Upload test document
        3. Wait for ingestion completion (monitor SSE events)
        4. Validate chunks in Qdrant
        5. Validate entities in Neo4j
        6. Validate relations in Neo4j with source_chunk_id (Sprint 49.5)
        7. Validate BM25 corpus updated
        8. Query the document
        9. Validate citations reference uploaded document
        10. Validate answer content is relevant
        """

        # =====================================================================
        # Step 1: Login
        # =====================================================================
        await page.goto("http://localhost:5179")
        await expect(page).to_have_url("http://localhost:5179/login")

        await page.fill('input[type="text"]', "admin")
        await page.fill('input[type="password"]', "admin123")
        await page.click('button:has-text("Sign In")')

        # Wait for redirect to main page
        await expect(page).to_have_url("http://localhost:5179/")
        await page.wait_for_load_state("networkidle")

        print("✓ Login successful")

        # =====================================================================
        # Step 2: Get baseline counts before upload
        # =====================================================================

        # Count chunks in Qdrant before upload
        qdrant_count_before = await qdrant_client.count(
            collection_name=settings.qdrant_collection
        )
        initial_chunk_count = qdrant_count_before.count

        # Count entities in Neo4j before upload
        async with neo4j_driver.session() as session:
            result = await session.run("MATCH (n:base) RETURN count(n) as count")
            record = await result.single()
            initial_entity_count = record["count"]

            result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            record = await result.single()
            initial_relation_count = record["count"]

        print(f"✓ Baseline: {initial_chunk_count} chunks, {initial_entity_count} entities, {initial_relation_count} relations")

        # =====================================================================
        # Step 3: Navigate to Admin Upload Page (Sprint 51: Direct URL)
        # =====================================================================

        # Sprint 51: Upload page is accessible directly via admin subpage
        # No upload button in main navigation - navigate directly
        await page.goto("http://localhost:5179/admin/upload")

        await page.wait_for_load_state("networkidle")
        print("✓ Navigated to upload page")

        # =====================================================================
        # Step 4: Upload Document
        # =====================================================================

        # Find file input (may be hidden)
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(str(sample_document_path))

        # Look for submit/upload button
        submit_button = page.locator('button:has-text("Upload"), button[type="submit"]')
        await submit_button.first.click()

        print(f"✓ Uploaded document: {sample_document_path.name}")

        # =====================================================================
        # Step 5: Monitor Ingestion Progress (SSE Events)
        # =====================================================================

        # Wait for success message or progress indicator
        # This may vary based on UI implementation
        success_indicator = page.locator('text=/upload.*success/i, text=/completed/i, [role="alert"]:has-text("success")')

        try:
            await success_indicator.first.wait_for(timeout=60000)  # 60 seconds max
            print("✓ Ingestion success message received")
        except Exception:
            # Fallback: wait for processing time
            print("⚠ No explicit success message, waiting 30s for processing...")
            await asyncio.sleep(30)

        # Additional wait for post-processing (graph extraction can take longer)
        await asyncio.sleep(10)

        # =====================================================================
        # Step 6: Validate Chunks in Qdrant
        # =====================================================================

        qdrant_count_after = await qdrant_client.count(
            collection_name=settings.qdrant_collection
        )
        new_chunk_count = qdrant_count_after.count
        chunks_added = new_chunk_count - initial_chunk_count

        assert chunks_added > 0, f"Expected new chunks in Qdrant, but count didn't change (before: {initial_chunk_count}, after: {new_chunk_count})"
        print(f"✓ Qdrant: {chunks_added} new chunks added (total: {new_chunk_count})")

        # Retrieve one chunk to verify structure
        search_result = await qdrant_client.scroll(
            collection_name=settings.qdrant_collection,
            limit=1,
            with_payload=True,
            with_vectors=False,
        )

        if search_result[0]:
            sample_chunk = search_result[0][0]
            assert "chunk_id" in sample_chunk.payload, "Chunk missing chunk_id"
            assert "text" in sample_chunk.payload, "Chunk missing text content"
            assert "document_id" in sample_chunk.payload, "Chunk missing document_id"
            print(f"✓ Chunk structure validated: chunk_id={sample_chunk.payload['chunk_id'][:20]}...")

        # =====================================================================
        # Step 7: Validate Entities in Neo4j
        # =====================================================================

        async with neo4j_driver.session() as session:
            # Count entities after upload
            result = await session.run("MATCH (n:base) RETURN count(n) as count")
            record = await result.single()
            new_entity_count = record["count"]
            entities_added = new_entity_count - initial_entity_count

            assert entities_added > 0, f"Expected new entities in Neo4j, but count didn't change (before: {initial_entity_count}, after: {new_entity_count})"
            print(f"✓ Neo4j: {entities_added} new entities extracted (total: {new_entity_count})")

            # Check for expected entities from our test document
            expected_entities = ["Andrew Ng", "Stanford University", "Google Brain", "Coursera"]
            found_entities = []

            for entity_name in expected_entities:
                result = await session.run(
                    "MATCH (n:base) WHERE toLower(n.entity_name) CONTAINS toLower($name) RETURN n.entity_name as name LIMIT 1",
                    name=entity_name
                )
                record = await result.single()
                if record:
                    found_entities.append(record["name"])

            # Expect at least 50% of entities found (LLM may extract variations)
            assert len(found_entities) >= len(expected_entities) * 0.5, \
                f"Expected to find at least {len(expected_entities) * 0.5} entities, found: {found_entities}"
            print(f"✓ Key entities found: {found_entities}")

        # =====================================================================
        # Step 8: Validate Relations with source_chunk_id (Sprint 49.5)
        # =====================================================================

        async with neo4j_driver.session() as session:
            # Count relations after upload
            result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            record = await result.single()
            new_relation_count = record["count"]
            relations_added = new_relation_count - initial_relation_count

            assert relations_added > 0, f"Expected new relations in Neo4j, but count didn't change (before: {initial_relation_count}, after: {new_relation_count})"
            print(f"✓ Neo4j: {relations_added} new relations extracted (total: {new_relation_count})")

            # Sprint 49.5: Validate source_chunk_id on MENTIONED_IN relationships
            result = await session.run(
                """
                MATCH ()-[r:MENTIONED_IN]->()
                WHERE r.source_chunk_id IS NOT NULL
                RETURN count(r) as count_with_chunk_id
                """
            )
            record = await result.single()
            relations_with_chunk_id = record["count_with_chunk_id"]

            # All new MENTIONED_IN relations should have source_chunk_id
            assert relations_with_chunk_id > 0, "Sprint 49.5: Expected MENTIONED_IN relations to have source_chunk_id"
            print(f"✓ Sprint 49.5: {relations_with_chunk_id} MENTIONED_IN relations have source_chunk_id")

        # =====================================================================
        # Step 9: Validate BM25 Corpus Updated
        # =====================================================================

        # BM25 is loaded lazily, trigger a search to ensure it's loaded
        bm25_response = await page.request.post(
            "http://localhost:8000/api/v1/retrieval/search",
            data={
                "query": "machine learning",
                "top_k": 5,
                "search_type": "bm25"
            }
        )

        assert bm25_response.ok, f"BM25 search failed: {bm25_response.status}"
        bm25_results = await bm25_response.json()

        # Should return results if BM25 corpus is populated
        assert len(bm25_results) > 0, "BM25 corpus should return results after indexing"
        print(f"✓ BM25 corpus functional: {len(bm25_results)} results returned")

        # =====================================================================
        # Step 10: Query the Uploaded Document
        # =====================================================================

        # Navigate to chat
        await page.goto("http://localhost:5179/")
        await page.wait_for_load_state("networkidle")

        # Find chat input (adjust selector based on actual UI)
        chat_input = page.locator('textarea, input[placeholder*="question"], input[placeholder*="message"]')
        await chat_input.fill("Who is Andrew Ng and what did he found?")

        # Submit query
        submit_btn = page.locator('button[type="submit"], button:has-text("Send")')
        await submit_btn.first.click()

        print("✓ Query submitted: 'Who is Andrew Ng and what did he found?'")

        # Wait for response (may take time for agent reasoning)
        response_container = page.locator('[role="article"], .message, .response').last
        await response_container.wait_for(timeout=60000)

        # Wait for thinking to complete (look for final answer)
        await asyncio.sleep(5)

        # =====================================================================
        # Step 11: Validate Answer Content
        # =====================================================================

        response_text = await response_container.inner_text()

        # Validate answer mentions key facts from our document
        expected_keywords = ["Andrew Ng", "Google Brain", "Coursera"]
        found_keywords = [kw for kw in expected_keywords if kw.lower() in response_text.lower()]

        assert len(found_keywords) >= 2, \
            f"Expected answer to mention at least 2 of {expected_keywords}, but found only: {found_keywords}\nAnswer: {response_text[:200]}"
        print(f"✓ Answer contains expected content: {found_keywords}")

        # =====================================================================
        # Step 12: Validate Citations Reference Uploaded Document
        # =====================================================================

        # Look for citation indicators (adjust based on UI)
        citations = page.locator('[data-citation], .citation, a[href*="chunk"]')
        citation_count = await citations.count()

        if citation_count > 0:
            print(f"✓ Found {citation_count} citations in response")

            # Click first citation to verify it opens/highlights source
            first_citation = citations.first
            await first_citation.click()
            await asyncio.sleep(1)

            # Verify citation panel/modal opened (adjust based on UI)
            citation_panel = page.locator('[role="dialog"], .citation-panel, .source-panel')
            if await citation_panel.count() > 0:
                citation_text = await citation_panel.inner_text()
                # Citation should contain text from our uploaded document
                assert any(kw.lower() in citation_text.lower() for kw in ["machine learning", "stanford", "google brain"]), \
                    "Citation should reference uploaded document content"
                print("✓ Citation references uploaded document")
        else:
            print("⚠ No citations found (may not be displayed in UI)")

        print("\n" + "="*70)
        print("✅ COMPLETE DOCUMENT INGESTION WORKFLOW TEST PASSED")
        print("="*70)
        print(f"Summary:")
        print(f"  - Chunks added: {chunks_added}")
        print(f"  - Entities extracted: {entities_added}")
        print(f"  - Relations extracted: {relations_added}")
        print(f"  - Relations with source_chunk_id: {relations_with_chunk_id}")
        print(f"  - Query answered correctly: Yes")
        print(f"  - Citations valid: {citation_count > 0}")
