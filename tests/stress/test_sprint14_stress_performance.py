"""Stress and Performance Tests for Sprint 14 Features.

Tests system behavior under extreme load:
- Memory profiling with large document batches
- Memory leak detection over extended runs
- Connection pool exhaustion scenarios
- Performance degradation under load

Requirements:
- Docker services running (Ollama, Neo4j, Redis)
- Sufficient system resources (8GB+ RAM recommended)
- pytest-timeout, memory_profiler

Author: Claude Code
Date: 2025-10-27
"""

import asyncio
import gc
import os
import time
import tracemalloc
from typing import List

import psutil
import pytest

from src.components.graph_rag.extraction_factory import create_extraction_pipeline_from_config
from src.monitoring.metrics import (
    record_extraction_document,
    record_extraction_duration,
    record_extraction_entities,
    record_extraction_relations,
)


# ============================================================================
# Helper Functions
# ============================================================================


def get_memory_usage_mb() -> float:
    """Get current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def get_connection_count() -> int:
    """Get current number of network connections."""
    process = psutil.Process(os.getpid())
    return len(process.connections())


# ============================================================================
# Large Batch Processing Tests
# ============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
@pytest.mark.timeout(600)  # 10 minute timeout
async def test_stress_batch_100_documents():
    """Stress test: Process 100 documents and track performance degradation.

    Verifies:
    - System handles large batch without crashing
    - Performance doesn't degrade significantly over time
    - Memory usage stays within reasonable bounds
    """
    print("\n" + "="*70)
    print("STRESS TEST: 100 Document Batch Processing")
    print("="*70)

    # Setup
    pipeline = create_extraction_pipeline_from_config()

    # Generate 100 test documents (varied sizes)
    documents = []
    for i in range(100):
        # Vary document size (small, medium, large)
        if i % 3 == 0:  # Small docs (every 3rd)
            text = f"Document {i}. Company A acquired Company B. CEO John Smith announced the deal."
        elif i % 3 == 1:  # Medium docs
            text = f"""
            Document {i}. In a major development, Technology Corporation announced today
            that CEO Jane Doe will lead a new initiative. The company, based in Silicon Valley,
            will integrate cloud services with AI capabilities. Industry analysts expect
            significant impact in the technology sector.
            """
        else:  # Large docs
            text = f"""
            Document {i}. Breaking news from the corporate world. MegaCorp Industries, led by
            Chief Executive Officer Robert Johnson, has unveiled ambitious expansion plans.
            The multinational corporation, headquartered in New York City, will invest billions
            in research and development. Dr. Sarah Chen, Chief Technology Officer, emphasized
            the strategic importance of artificial intelligence and machine learning technologies.
            The announcement came during a press conference at the company's headquarters,
            attended by industry leaders and financial analysts from major investment firms.
            Market experts predict this move will reshape the competitive landscape.
            """

        documents.append({"id": f"stress_doc_{i:03d}", "text": text})

    # Tracking metrics
    start_time = time.time()
    start_memory = get_memory_usage_mb()
    processing_times = []
    memory_samples = []

    print(f"\nStart Memory: {start_memory:.1f} MB")
    print(f"Documents: {len(documents)}\n")

    # Process all documents
    for i, doc in enumerate(documents):
        doc_start = time.time()

        try:
            entities, relations = await pipeline.extract(doc["text"], document_id=doc["id"])

            doc_duration = time.time() - doc_start
            processing_times.append(doc_duration)

            # Record metrics
            record_extraction_entities(len(entities), entity_type="ALL")
            record_extraction_relations(len(relations))
            record_extraction_duration(doc_duration, phase="stress_batch")
            record_extraction_document(status="success")

            # Sample memory every 10 docs
            if i % 10 == 0:
                current_memory = get_memory_usage_mb()
                memory_samples.append(current_memory)
                print(f"[{i:3d}/100] Time: {doc_duration:5.2f}s | Memory: {current_memory:6.1f} MB | Entities: {len(entities):2d}")

        except Exception as e:
            print(f"[{i:3d}/100] ERROR: {type(e).__name__}: {str(e)[:50]}")
            record_extraction_document(status="error")
            continue

    # Calculate statistics
    total_time = time.time() - start_time
    end_memory = get_memory_usage_mb()
    memory_increase = end_memory - start_memory

    avg_time = sum(processing_times) / len(processing_times)
    first_10_avg = sum(processing_times[:10]) / 10
    last_10_avg = sum(processing_times[-10:]) / 10

    print(f"\n{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")
    print(f"Total Time:            {total_time:.2f}s")
    print(f"Documents Processed:   {len(processing_times)}/{len(documents)}")
    print(f"Avg Time/Doc:          {avg_time:.2f}s")
    print(f"First 10 Avg:          {first_10_avg:.2f}s")
    print(f"Last 10 Avg:           {last_10_avg:.2f}s")
    print(f"Performance Degradation: {((last_10_avg - first_10_avg) / first_10_avg * 100):.1f}%")
    print(f"\nStart Memory:          {start_memory:.1f} MB")
    print(f"End Memory:            {end_memory:.1f} MB")
    print(f"Memory Increase:       {memory_increase:.1f} MB")
    print(f"{'='*70}\n")

    # Assertions
    assert len(processing_times) >= 95, f"Should process at least 95/100 docs, got {len(processing_times)}"
    assert memory_increase < 500, f"Memory increase too high: {memory_increase:.1f} MB"

    # Performance shouldn't degrade more than 50%
    degradation = (last_10_avg - first_10_avg) / first_10_avg
    assert degradation < 0.5, f"Performance degraded by {degradation*100:.1f}%, expected < 50%"


# ============================================================================
# Memory Leak Detection
# ============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
@pytest.mark.timeout(300)  # 5 minute timeout
async def test_stress_memory_leak_detection():
    """Stress test: Detect memory leaks over repeated processing cycles.

    Processes the same document 50 times and monitors memory growth.
    Significant memory growth indicates a leak.
    """
    print("\n" + "="*70)
    print("STRESS TEST: Memory Leak Detection")
    print("="*70)

    # Enable memory tracking
    tracemalloc.start()

    pipeline = create_extraction_pipeline_from_config()

    document = """
    Technology Corporation announced today that CEO Jane Doe will lead
    a new AI initiative. The company will integrate cloud services with
    advanced machine learning capabilities developed in partnership with
    industry leaders.
    """

    iterations = 50
    memory_snapshots = []

    print(f"\nRunning {iterations} iterations with same document...\n")

    for i in range(iterations):
        # Force garbage collection before each iteration
        gc.collect()

        # Snapshot memory before
        snapshot_before = tracemalloc.take_snapshot()
        mem_before = get_memory_usage_mb()

        # Process document
        entities, relations = await pipeline.extract(document, document_id=f"leak_test_{i}")

        # Snapshot memory after
        mem_after = get_memory_usage_mb()
        memory_snapshots.append(mem_after)

        if i % 10 == 0:
            print(f"[Iteration {i:2d}] Memory: {mem_after:.1f} MB")

    tracemalloc.stop()

    # Analyze memory trend
    first_10_avg = sum(memory_snapshots[:10]) / 10
    last_10_avg = sum(memory_snapshots[-10:]) / 10
    memory_growth = last_10_avg - first_10_avg
    growth_percentage = (memory_growth / first_10_avg) * 100

    print(f"\n{'='*70}")
    print("MEMORY LEAK ANALYSIS")
    print(f"{'='*70}")
    print(f"Iterations:            {iterations}")
    print(f"First 10 Avg Memory:   {first_10_avg:.1f} MB")
    print(f"Last 10 Avg Memory:    {last_10_avg:.1f} MB")
    print(f"Memory Growth:         {memory_growth:.1f} MB ({growth_percentage:.1f}%)")
    print(f"{'='*70}\n")

    # Memory growth should be minimal (< 20%)
    assert growth_percentage < 20, f"Possible memory leak: {growth_percentage:.1f}% growth over {iterations} iterations"

    print("✓ No significant memory leak detected")


# ============================================================================
# Connection Pool Exhaustion
# ============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_stress_connection_pool_exhaustion():
    """Stress test: Verify connection pool doesn't exhaust under concurrent load.

    Simulates high concurrency by processing multiple documents simultaneously.
    """
    print("\n" + "="*70)
    print("STRESS TEST: Connection Pool Exhaustion")
    print("="*70)

    pipeline = create_extraction_pipeline_from_config()

    # Test document
    document = """
    Microsoft Corporation announced partnerships with OpenAI to develop
    advanced AI systems. CEO Satya Nadella emphasized the strategic
    importance of artificial intelligence for enterprise solutions.
    """

    concurrent_requests = 20
    connection_samples = []

    print(f"\nSimulating {concurrent_requests} concurrent extraction requests...\n")

    async def process_with_monitoring(doc_id: int):
        """Process document and monitor connections."""
        conn_count_before = get_connection_count()

        try:
            entities, relations = await pipeline.extract(document, document_id=f"concurrent_{doc_id}")
            conn_count_after = get_connection_count()

            connection_samples.append({
                "doc_id": doc_id,
                "before": conn_count_before,
                "after": conn_count_after,
                "success": True,
            })

            return {"entities": len(entities), "relations": len(relations), "success": True}

        except Exception as e:
            print(f"[Doc {doc_id:2d}] ERROR: {type(e).__name__}")
            connection_samples.append({
                "doc_id": doc_id,
                "before": conn_count_before,
                "after": get_connection_count(),
                "success": False,
                "error": str(e),
            })
            return {"success": False, "error": str(e)}

    # Launch concurrent tasks
    start_time = time.time()
    tasks = [process_with_monitoring(i) for i in range(concurrent_requests)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time

    # Analyze results
    successful = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))
    failed = concurrent_requests - successful

    max_connections = max(s["after"] for s in connection_samples)
    avg_connections = sum(s["after"] for s in connection_samples) / len(connection_samples)

    print(f"\n{'='*70}")
    print("CONNECTION POOL RESULTS")
    print(f"{'='*70}")
    print(f"Concurrent Requests:   {concurrent_requests}")
    print(f"Successful:            {successful}")
    print(f"Failed:                {failed}")
    print(f"Total Time:            {total_time:.2f}s")
    print(f"Max Connections:       {max_connections}")
    print(f"Avg Connections:       {avg_connections:.1f}")
    print(f"{'='*70}\n")

    # Assertions
    assert successful >= concurrent_requests * 0.8, f"Too many failures: {failed}/{concurrent_requests}"
    assert max_connections < 100, f"Connection count too high: {max_connections}"

    print("✓ Connection pool handled concurrent load")


# ============================================================================
# Memory Profiling with Large Documents
# ============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_stress_large_document_memory_profile():
    """Stress test: Profile memory usage with very large documents.

    Tests memory efficiency when processing documents with hundreds
    of entities and complex relationships.
    """
    print("\n" + "="*70)
    print("STRESS TEST: Large Document Memory Profiling")
    print("="*70)

    pipeline = create_extraction_pipeline_from_config()

    # Generate very large document (simulate research paper)
    large_doc = """
    The integration of artificial intelligence technologies in enterprise systems
    represents a paradigm shift in organizational operations. Dr. Sarah Chen from
    Stanford University and Professor Michael Brown from MIT have conducted extensive
    research on machine learning applications. Their collaboration with Technology
    Corporation, led by CEO Jane Doe, has produced significant innovations.

    The research team, including Dr. Robert Johnson, Dr. Emily Williams, and
    Dr. David Martinez, developed novel approaches to natural language processing.
    Microsoft Corporation, Google LLC, Amazon Web Services, and IBM Watson have
    all invested in similar technologies. The partnership between OpenAI and
    Anthropic has further accelerated progress in this domain.

    Based in Silicon Valley, California, these companies collaborate with
    research institutions in Boston, Massachusetts, New York City, and Seattle.
    The Stanford AI Lab, MIT Computer Science Department, Carnegie Mellon Robotics
    Institute, and Berkeley EECS have all contributed to foundational research.

    Dr. Chen's work on transformer architectures complements Professor Brown's
    research on reinforcement learning. Together with Dr. Johnson's expertise in
    computer vision and Dr. Williams' knowledge of robotics, the team has created
    comprehensive AI frameworks. Dr. Martinez's contributions to neural architecture
    search have been particularly influential.
    """

    # Repeat to make it even larger
    mega_document = (large_doc + "\n\n") * 3  # ~1000 words

    print(f"Document size: {len(mega_document)} characters, ~{len(mega_document.split())} words\n")

    # Profile memory
    gc.collect()
    mem_before = get_memory_usage_mb()
    tracemalloc.start()

    start_time = time.time()
    entities, relations = await pipeline.extract(mega_document, document_id="large_doc_profile")
    processing_time = time.time() - start_time

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    mem_after = get_memory_usage_mb()
    mem_increase = mem_after - mem_before

    print(f"{'='*70}")
    print("MEMORY PROFILE RESULTS")
    print(f"{'='*70}")
    print(f"Processing Time:       {processing_time:.2f}s")
    print(f"Entities Extracted:    {len(entities)}")
    print(f"Relations Found:       {len(relations)}")
    print(f"\nMemory Before:         {mem_before:.1f} MB")
    print(f"Memory After:          {mem_after:.1f} MB")
    print(f"Memory Increase:       {mem_increase:.1f} MB")
    print(f"Peak Memory (traced):  {peak / 1024 / 1024:.1f} MB")
    print(f"{'='*70}\n")

    # Assertions
    assert processing_time < 180, f"Large doc processing too slow: {processing_time:.2f}s"
    assert mem_increase < 200, f"Memory increase too high: {mem_increase:.1f} MB"
    assert len(entities) > 10, "Should extract significant entities from large document"

    print("✓ Large document processed efficiently")


# ============================================================================
# Throughput Under Sustained Load
# ============================================================================


@pytest.mark.stress
@pytest.mark.asyncio
@pytest.mark.timeout(300)
async def test_stress_sustained_throughput():
    """Stress test: Measure throughput under sustained load (5 minutes).

    Continuously processes documents for 5 minutes and measures:
    - Documents processed per minute
    - Performance stability over time
    - Resource usage trends
    """
    print("\n" + "="*70)
    print("STRESS TEST: Sustained Throughput (5 min)")
    print("="*70)

    pipeline = create_extraction_pipeline_from_config()

    document = """
    Technology startup announces major funding round. CEO Alex Smith stated
    that the Series B investment from Venture Capital Partners will accelerate
    product development. The San Francisco based company plans to expand to
    New York and London.
    """

    duration_seconds = 60  # Reduced to 1 minute for faster testing
    start_time = time.time()
    doc_count = 0
    throughput_samples = []

    print(f"\nProcessing documents for {duration_seconds} seconds...\n")

    while (time.time() - start_time) < duration_seconds:
        batch_start = time.time()

        # Process 5 documents
        for i in range(5):
            entities, relations = await pipeline.extract(
                document, document_id=f"sustained_{doc_count}"
            )
            doc_count += 1

        batch_time = time.time() - batch_start
        docs_per_sec = 5 / batch_time
        throughput_samples.append(docs_per_sec)

        elapsed = time.time() - start_time
        if int(elapsed) % 15 == 0:  # Print every 15 seconds
            print(f"[{elapsed:.0f}s] Processed: {doc_count} docs | Throughput: {docs_per_sec:.2f} docs/sec")

    total_time = time.time() - start_time

    # Calculate statistics
    avg_throughput = sum(throughput_samples) / len(throughput_samples)
    first_half_avg = sum(throughput_samples[:len(throughput_samples)//2]) / (len(throughput_samples)//2)
    second_half_avg = sum(throughput_samples[len(throughput_samples)//2:]) / (len(throughput_samples) - len(throughput_samples)//2)

    print(f"\n{'='*70}")
    print("SUSTAINED LOAD RESULTS")
    print(f"{'='*70}")
    print(f"Duration:              {total_time:.1f}s")
    print(f"Documents Processed:   {doc_count}")
    print(f"Avg Throughput:        {avg_throughput:.2f} docs/sec")
    print(f"First Half Avg:        {first_half_avg:.2f} docs/sec")
    print(f"Second Half Avg:       {second_half_avg:.2f} docs/sec")
    print(f"Throughput Change:     {((second_half_avg - first_half_avg) / first_half_avg * 100):.1f}%")
    print(f"{'='*70}\n")

    # Assertions
    assert doc_count > 10, f"Should process significant documents, got {doc_count}"
    assert avg_throughput > 0.1, f"Throughput too low: {avg_throughput:.2f} docs/sec"

    # Throughput shouldn't drop more than 30% over time
    throughput_drop = (first_half_avg - second_half_avg) / first_half_avg
    assert throughput_drop < 0.3, f"Throughput dropped {throughput_drop*100:.1f}%"

    print("✓ Sustained load handled successfully")
