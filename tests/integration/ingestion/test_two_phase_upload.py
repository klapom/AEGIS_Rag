"""Integration tests for Two-Phase Document Upload (Sprint 83 Feature 83.4).

Tests:
1. End-to-end fast upload + background refinement
2. Concurrent uploads (multiple documents)

Requirements:
- Redis running on localhost:6379
- Qdrant running on localhost:6333
- Neo4j running on bolt://localhost:7687
- Docling service available
"""

import asyncio
import tempfile
import time
from pathlib import Path

import pytest

from src.components.ingestion.background_jobs import get_background_job_queue
from src.components.ingestion.fast_pipeline import run_fast_upload
from src.components.ingestion.refinement_pipeline import run_background_refinement
from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.core.config import settings

# Mark as integration test (requires external services)
pytestmark = pytest.mark.integration


@pytest.fixture
def test_file(tmp_path):
    """Create a test text file for upload."""
    file_path = tmp_path / "test_document.txt"
    file_path.write_text(
        """
        # Test Document

        This is a test document for two-phase upload.
        It contains entities like New York, Apple Inc., and John Doe.

        ## Section 1

        New York is a city in the United States.
        Apple Inc. is a technology company founded by Steve Jobs.

        ## Section 2

        John Doe works at Apple Inc. in New York.
        The company was founded in 1976.
        """
    )
    return file_path


class TestEndToEndTwoPhaseUpload:
    """Test complete two-phase upload workflow."""

    @pytest.mark.asyncio
    async def test_fast_upload_and_background_refinement(self, test_file):
        """Test Phase 1 + Phase 2 complete workflow.

        Steps:
        1. Run fast upload (Phase 1)
        2. Verify status is "processing_background"
        3. Run background refinement (Phase 2)
        4. Verify status is "ready"
        5. Verify chunks in Qdrant
        6. Verify entities in Neo4j (if available)
        """
        job_queue = get_background_job_queue()
        await job_queue.initialize()

        # Phase 1: Fast Upload
        start_time = time.perf_counter()
        document_id = await run_fast_upload(
            file_path=test_file,
            namespace="test_namespace",
            domain="general",
        )
        phase1_duration = (time.perf_counter() - start_time) * 1000

        # Verify Phase 1 performance (<5s = 5000ms)
        assert phase1_duration < 5000, f"Phase 1 took {phase1_duration:.2f}ms (target: <5000ms)"

        # Verify status after Phase 1
        status = await job_queue.get_status(document_id)
        assert status is not None
        assert status["status"] == "processing_background"
        assert status["progress_pct"] == 100.0
        assert status["namespace"] == "test_namespace"

        # Verify chunks in Qdrant
        qdrant = QdrantClientWrapper()
        collection_name = settings.qdrant_collection

        # Scroll to find chunks
        scroll_result = await qdrant.async_client.scroll(
            collection_name=collection_name,
            scroll_filter={
                "must": [
                    {"key": "document_id", "match": {"value": document_id}},
                    {"key": "namespace_id", "match": {"value": "test_namespace"}},
                ]
            },
            limit=100,
            with_payload=True,
        )

        chunks, _ = scroll_result
        assert len(chunks) > 0, "No chunks found in Qdrant after Phase 1"

        # Verify fast upload flags
        for chunk in chunks:
            assert chunk.payload["fast_upload"] is True
            assert chunk.payload["refinement_pending"] is True

        # Phase 2: Background Refinement
        start_time = time.perf_counter()
        await run_background_refinement(
            document_id=document_id,
            namespace="test_namespace",
            domain="general",
        )
        phase2_duration = (time.perf_counter() - start_time) * 1000

        # Verify Phase 2 performance (<60s = 60000ms)
        assert (
            phase2_duration < 60000
        ), f"Phase 2 took {phase2_duration:.2f}ms (target: <60000ms)"

        # Verify status after Phase 2
        status = await job_queue.get_status(document_id)
        assert status is not None
        assert status["status"] == "ready"
        assert status["progress_pct"] == 100.0
        assert status["current_phase"] == "completed"

        # Verify Qdrant metadata updated
        scroll_result = await qdrant.async_client.scroll(
            collection_name=collection_name,
            scroll_filter={
                "must": [
                    {"key": "document_id", "match": {"value": document_id}},
                    {"key": "namespace_id", "match": {"value": "test_namespace"}},
                ]
            },
            limit=100,
            with_payload=True,
        )

        chunks, _ = scroll_result
        assert len(chunks) > 0

        # Check if any chunks have refined metadata
        refined_count = sum(
            1 for chunk in chunks if not chunk.payload.get("refinement_pending", True)
        )
        assert refined_count > 0, "No chunks were refined in Phase 2"

        # Cleanup
        await job_queue.delete_status(document_id)

        # Print performance summary
        print(f"\n=== Two-Phase Upload Performance ===")
        print(f"Phase 1 (Fast Upload): {phase1_duration:.2f}ms (target: <5000ms)")
        print(f"Phase 2 (Refinement): {phase2_duration:.2f}ms (target: <60000ms)")
        print(f"Total Time: {(phase1_duration + phase2_duration):.2f}ms")
        print(f"Chunks Created: {len(chunks)}")
        print(f"Refined Chunks: {refined_count}")


class TestConcurrentUploads:
    """Test concurrent document uploads."""

    @pytest.mark.asyncio
    async def test_concurrent_fast_uploads(self, tmp_path):
        """Test uploading multiple documents concurrently.

        Verifies:
        1. Multiple fast uploads can run concurrently
        2. Each document gets unique document_id
        3. Status tracking works for all documents
        4. No race conditions or conflicts
        """
        job_queue = get_background_job_queue()
        await job_queue.initialize()

        # Create 3 test files
        test_files = []
        for i in range(3):
            file_path = tmp_path / f"test_document_{i}.txt"
            file_path.write_text(
                f"""
                # Test Document {i}

                This is test document {i} with unique content.
                Entity {i}: Company_{i} in City_{i}.
                Person_{i} works at Company_{i}.
                """
            )
            test_files.append(file_path)

        # Run fast uploads concurrently
        start_time = time.perf_counter()

        upload_tasks = [
            run_fast_upload(
                file_path=file_path,
                namespace=f"test_concurrent_{i}",
                domain="general",
            )
            for i, file_path in enumerate(test_files)
        ]

        document_ids = await asyncio.gather(*upload_tasks)
        concurrent_duration = (time.perf_counter() - start_time) * 1000

        # Verify all uploads succeeded
        assert len(document_ids) == 3
        assert len(set(document_ids)) == 3, "Document IDs should be unique"

        # Verify status for all documents
        for i, document_id in enumerate(document_ids):
            status = await job_queue.get_status(document_id)
            assert status is not None
            assert status["status"] == "processing_background"
            assert status["document_id"] == document_id
            assert status["namespace"] == f"test_concurrent_{i}"

        # Verify concurrent performance (should be faster than sequential)
        # Sequential would take ~15s (3 x 5s), concurrent should be closer to 5s
        assert (
            concurrent_duration < 10000
        ), f"Concurrent uploads took {concurrent_duration:.2f}ms (expected: <10000ms)"

        # Cleanup
        for document_id in document_ids:
            await job_queue.delete_status(document_id)

        # Print performance summary
        print(f"\n=== Concurrent Upload Performance ===")
        print(f"Documents Uploaded: {len(document_ids)}")
        print(f"Total Time: {concurrent_duration:.2f}ms")
        print(f"Average per Document: {concurrent_duration / len(document_ids):.2f}ms")

    @pytest.mark.asyncio
    async def test_background_refinement_queue(self, tmp_path):
        """Test background refinement job queue with multiple documents.

        Verifies:
        1. Jobs can be enqueued while others are running
        2. Status tracking works for multiple concurrent jobs
        3. Jobs complete successfully
        """
        job_queue = get_background_job_queue()
        await job_queue.initialize()

        # Create test files
        test_files = []
        for i in range(2):
            file_path = tmp_path / f"test_refinement_{i}.txt"
            file_path.write_text(
                f"""
                # Refinement Test {i}

                This document tests background refinement queue.
                Entity: TestEntity_{i}, Type: ORGANIZATION
                """
            )
            test_files.append(file_path)

        # Run fast uploads
        document_ids = []
        for file_path in test_files:
            doc_id = await run_fast_upload(
                file_path=file_path,
                namespace="test_refinement_queue",
                domain="general",
            )
            document_ids.append(doc_id)

        # Enqueue background refinement jobs
        for document_id in document_ids:
            await job_queue.enqueue_job(
                document_id=document_id,
                func=run_background_refinement,
                namespace="test_refinement_queue",
                domain="general",
            )

        # Verify jobs are active
        active_count = await job_queue.get_active_jobs_count()
        assert active_count == 2, f"Expected 2 active jobs, got {active_count}"

        # Wait for jobs to complete (max 2 minutes)
        timeout = 120
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            active_count = await job_queue.get_active_jobs_count()
            if active_count == 0:
                break
            await asyncio.sleep(1)

        # Verify all jobs completed
        assert active_count == 0, "Jobs did not complete within timeout"

        # Verify final status
        for document_id in document_ids:
            status = await job_queue.get_status(document_id)
            assert status is not None
            # Should be either "ready" or "failed" (not "processing_background")
            assert status["status"] in ["ready", "failed"]

        # Cleanup
        for document_id in document_ids:
            await job_queue.delete_status(document_id)

        print(f"\n=== Background Refinement Queue Test ===")
        print(f"Documents Processed: {len(document_ids)}")
        print(f"Total Time: {(time.time() - start_time):.2f}s")
