"""Performance tests for Phase Event creation and serialization.

Sprint 48 Feature 48.1: Phase Event Models & Types (5 SP)
Sprint 48 Feature 48.7: ReasoningData Builder (3 SP)

These tests verify:
- Phase event creation is fast (<1ms)
- Serialization overhead is minimal (<2ms)
- Reasoning data accumulation is efficient
- No memory leaks during streaming
"""

import sys
import time
from datetime import datetime

import pytest

from src.agents.reasoning_data import ReasoningData
from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType


# ============================================================================
# Creation Performance Tests
# ============================================================================


@pytest.mark.performance
def test_phase_event_creation_performance():
    """Test PhaseEvent creation is fast (<1ms per event)."""
    iterations = 1000
    target_ms_per_event = 1.0

    start = time.perf_counter()
    for _ in range(iterations):
        event = PhaseEvent(
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.IN_PROGRESS,
            start_time=datetime.utcnow(),
        )
    end = time.perf_counter()

    total_time_ms = (end - start) * 1000
    avg_time_ms = total_time_ms / iterations

    print(f"\nPhaseEvent creation performance:")
    print(f"  Total time: {total_time_ms:.2f}ms for {iterations} events")
    print(f"  Average: {avg_time_ms:.4f}ms per event")

    # Should be fast
    assert avg_time_ms < target_ms_per_event, (
        f"PhaseEvent creation too slow: {avg_time_ms:.4f}ms "
        f"(target: <{target_ms_per_event}ms)"
    )


@pytest.mark.performance
def test_phase_event_with_metadata_creation():
    """Test PhaseEvent creation with metadata is still fast."""
    iterations = 500
    target_ms_per_event = 1.5

    start = time.perf_counter()
    for i in range(iterations):
        event = PhaseEvent(
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=150.0,
            metadata={
                "docs_retrieved": 10,
                "collection": "documents_v1",
                "top_k": 5,
                "query_embedding_dim": 1024,
                "threshold": 0.8,
                "iteration": i,
            },
        )
    end = time.perf_counter()

    total_time_ms = (end - start) * 1000
    avg_time_ms = total_time_ms / iterations

    print(f"\nPhaseEvent with metadata creation:")
    print(f"  Total time: {total_time_ms:.2f}ms for {iterations} events")
    print(f"  Average: {avg_time_ms:.4f}ms per event")

    assert avg_time_ms < target_ms_per_event


# ============================================================================
# Serialization Performance Tests
# ============================================================================


@pytest.mark.performance
def test_phase_event_serialization_performance():
    """Test PhaseEvent serialization is fast (<2ms)."""
    event = PhaseEvent(
        phase_type=PhaseType.VECTOR_SEARCH,
        status=PhaseStatus.COMPLETED,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        duration_ms=150.0,
        metadata={"results": 100, "collection": "docs"},
    )

    iterations = 1000
    target_ms_per_serialization = 2.0

    start = time.perf_counter()
    for _ in range(iterations):
        _ = event.model_dump()
    end = time.perf_counter()

    total_time_ms = (end - start) * 1000
    avg_time_ms = total_time_ms / iterations

    print(f"\nPhaseEvent serialization performance:")
    print(f"  Total time: {total_time_ms:.2f}ms for {iterations} serializations")
    print(f"  Average: {avg_time_ms:.4f}ms per serialization")

    assert avg_time_ms < target_ms_per_serialization, (
        f"Serialization too slow: {avg_time_ms:.4f}ms "
        f"(target: <{target_ms_per_serialization}ms)"
    )


@pytest.mark.performance
def test_phase_event_json_serialization_performance():
    """Test PhaseEvent JSON serialization performance."""
    import json

    event = PhaseEvent(
        phase_type=PhaseType.LLM_GENERATION,
        status=PhaseStatus.COMPLETED,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        duration_ms=250.0,
        metadata={
            "tokens_generated": 150,
            "model": "ollama:llama3.2",
            "temperature": 0.7,
        },
    )

    iterations = 500
    target_ms_per_json = 3.0

    # Custom JSON encoder that handles datetime
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return super().default(obj)

    start = time.perf_counter()
    for _ in range(iterations):
        data = event.model_dump()
        # Convert datetime to ISO string for JSON serialization
        data["start_time"] = data["start_time"].isoformat() if isinstance(data["start_time"], datetime) else data["start_time"]
        data["end_time"] = data["end_time"].isoformat() if isinstance(data["end_time"], datetime) else data["end_time"]
        _ = json.dumps(data)
    end = time.perf_counter()

    total_time_ms = (end - start) * 1000
    avg_time_ms = total_time_ms / iterations

    print(f"\nPhaseEvent JSON serialization performance:")
    print(f"  Total time: {total_time_ms:.2f}ms for {iterations} JSON conversions")
    print(f"  Average: {avg_time_ms:.4f}ms per JSON conversion")

    assert avg_time_ms < target_ms_per_json


# ============================================================================
# Reasoning Data Accumulation Tests
# ============================================================================


@pytest.mark.performance
def test_reasoning_data_phase_accumulation():
    """Test ReasoningData efficiently accumulates phase events."""
    reasoning = ReasoningData()
    num_events = 100

    start = time.perf_counter()
    for i in range(num_events):
        phase_type = list(PhaseType)[i % len(PhaseType)]
        event = PhaseEvent(
            phase_type=phase_type,
            status=PhaseStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=100.0 * (i + 1) / num_events,
            metadata={"index": i},
        )
        reasoning.add_phase_event(event)
    end = time.perf_counter()

    total_time_ms = (end - start) * 1000
    avg_time_ms = total_time_ms / num_events

    print(f"\nReasoningData phase accumulation:")
    print(f"  Total time: {total_time_ms:.2f}ms for {num_events} events")
    print(f"  Average: {avg_time_ms:.4f}ms per event")

    # Should be very fast (just appending to list)
    assert avg_time_ms < 0.5, f"Accumulation too slow: {avg_time_ms:.4f}ms"
    assert len(reasoning.phase_events) == num_events


@pytest.mark.performance
def test_reasoning_data_to_dict_performance():
    """Test ReasoningData.to_dict() serialization is fast."""
    reasoning = ReasoningData()

    # Populate with events
    for i in range(50):
        phase_type = list(PhaseType)[i % len(PhaseType)]
        reasoning.add_phase_event(
            PhaseEvent(
                phase_type=phase_type,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=100.0,
                metadata={"iteration": i},
            )
        )

    # Add supporting data
    for i in range(10):
        reasoning.retrieved_docs.append({"doc_id": f"doc_{i}", "score": 0.9 - i * 0.05})
        reasoning.graph_entities.append({"entity": f"entity_{i}"})
        reasoning.memories.append({"memory": f"mem_{i}"})

    iterations = 1000
    target_ms_per_to_dict = 1.0

    start = time.perf_counter()
    for _ in range(iterations):
        _ = reasoning.to_dict()
    end = time.perf_counter()

    total_time_ms = (end - start) * 1000
    avg_time_ms = total_time_ms / iterations

    print(f"\nReasoningData.to_dict() performance:")
    print(f"  Total time: {total_time_ms:.2f}ms for {iterations} calls")
    print(f"  Average: {avg_time_ms:.4f}ms per call")

    assert avg_time_ms < target_ms_per_to_dict


# ============================================================================
# Memory Usage Tests
# ============================================================================


@pytest.mark.performance
def test_phase_event_memory_footprint():
    """Test PhaseEvent memory footprint is reasonable."""
    import sys

    event = PhaseEvent(
        phase_type=PhaseType.VECTOR_SEARCH,
        status=PhaseStatus.COMPLETED,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        duration_ms=150.0,
        metadata={
            "docs_retrieved": 10,
            "collection": "documents_v1",
            "top_k": 5,
        },
    )

    # Estimate size
    size_bytes = sys.getsizeof(event)
    metadata_size = sys.getsizeof(event.metadata)
    total_size = size_bytes + metadata_size

    print(f"\nPhaseEvent memory footprint:")
    print(f"  Event object: {size_bytes} bytes")
    print(f"  Metadata dict: {metadata_size} bytes")
    print(f"  Total estimate: {total_size} bytes")

    # Should be reasonably small
    assert total_size < 2000, f"Event too large: {total_size} bytes"


@pytest.mark.performance
def test_reasoning_data_memory_growth():
    """Test ReasoningData memory usage grows linearly with events."""
    import sys

    reasoning_empty = ReasoningData()
    empty_size = sys.getsizeof(reasoning_empty)

    reasoning_full = ReasoningData()
    num_events = 100

    for i in range(num_events):
        reasoning_full.add_phase_event(
            PhaseEvent(
                phase_type=list(PhaseType)[i % len(PhaseType)],
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=100.0,
                metadata={"index": i},
            )
        )

    # Add supporting data
    for i in range(10):
        reasoning_full.retrieved_docs.append({"doc_id": f"doc_{i}", "score": 0.9})

    full_size = sys.getsizeof(reasoning_full)

    print(f"\nReasoningData memory growth:")
    print(f"  Empty: {empty_size} bytes")
    print(f"  With 100 events: {full_size} bytes")
    print(f"  Growth: {full_size - empty_size} bytes")

    # Growth should be reasonable
    max_expected_bytes = empty_size + (num_events * 200)  # ~200 bytes per event
    assert full_size < max_expected_bytes, (
        f"Memory growth too large: {full_size} bytes "
        f"(expected <{max_expected_bytes})"
    )


# ============================================================================
# Stream Throughput Tests
# ============================================================================


@pytest.mark.performance
def test_phase_event_stream_throughput():
    """Test how many events can be created and serialized per second."""
    iterations = 5000
    events = []

    start = time.perf_counter()
    for i in range(iterations):
        event = PhaseEvent(
            phase_type=list(PhaseType)[i % len(PhaseType)],
            status=PhaseStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=100.0,
            metadata={"index": i},
        )
        events.append(event.model_dump())
    end = time.perf_counter()

    elapsed_seconds = end - start
    throughput = iterations / elapsed_seconds

    print(f"\nPhaseEvent stream throughput:")
    print(f"  Events created and serialized: {iterations}")
    print(f"  Time: {elapsed_seconds:.2f}s")
    print(f"  Throughput: {throughput:.0f} events/second")

    # Should achieve at least 1000 events/second
    assert throughput > 1000, f"Throughput too low: {throughput:.0f} events/s"


# ============================================================================
# Batch Operation Tests
# ============================================================================


@pytest.mark.performance
def test_reasoning_data_batch_operations():
    """Test batch operations on ReasoningData."""
    reasoning = ReasoningData()

    # Create batch of events
    batch_size = 50
    events = [
        PhaseEvent(
            phase_type=list(PhaseType)[i % len(PhaseType)],
            status=PhaseStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=100.0,
            metadata={"batch": 0, "index": i},
        )
        for i in range(batch_size)
    ]

    start = time.perf_counter()
    # Add batch 10 times
    for batch_num in range(10):
        for event in events:
            reasoning.add_phase_event(event)
    end = time.perf_counter()

    total_events = len(reasoning.phase_events)
    total_time_ms = (end - start) * 1000

    print(f"\nReasoningData batch operations:")
    print(f"  Total events: {total_events}")
    print(f"  Total time: {total_time_ms:.2f}ms")
    print(f"  Average per batch: {total_time_ms / 10:.2f}ms")

    assert total_events == batch_size * 10
    # Should be very fast
    assert total_time_ms < 50  # 50ms for 500 events


# ============================================================================
# Comparison Tests
# ============================================================================


@pytest.mark.performance
def test_phase_event_vs_dict():
    """Compare PhaseEvent performance vs plain dict."""
    iterations = 1000

    # Test PhaseEvent
    start = time.perf_counter()
    for _ in range(iterations):
        event = PhaseEvent(
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=150.0,
            metadata={"count": 10},
        )
        _ = event.model_dump()
    pydantic_time = time.perf_counter() - start

    # Test plain dict
    start = time.perf_counter()
    for _ in range(iterations):
        event_dict = {
            "phase_type": "vector_search",
            "status": "completed",
            "start_time": datetime.utcnow().isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "duration_ms": 150.0,
            "metadata": {"count": 10},
            "error": None,
        }
    dict_time = time.perf_counter() - start

    print(f"\nPhaseEvent vs dict comparison:")
    print(f"  Pydantic: {pydantic_time * 1000:.2f}ms for {iterations} operations")
    print(f"  Plain dict: {dict_time * 1000:.2f}ms for {iterations} operations")
    print(f"  Overhead: {(pydantic_time / dict_time - 1) * 100:.1f}%")

    # Pydantic overhead should be reasonable (< 5x)
    assert pydantic_time < dict_time * 5


# ============================================================================
# Stress Tests
# ============================================================================


@pytest.mark.performance
def test_high_volume_event_creation():
    """Test creating high volume of events doesn't cause slowdown."""
    # Create 10,000 events in batches and measure if throughput is consistent
    batch_size = 1000
    batches = 10

    batch_times = []

    for batch_num in range(batches):
        start = time.perf_counter()
        events = []
        for i in range(batch_size):
            event = PhaseEvent(
                phase_type=list(PhaseType)[i % len(PhaseType)],
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=100.0,
                metadata={"batch": batch_num, "index": i},
            )
            events.append(event.model_dump())
        batch_time = (time.perf_counter() - start) * 1000
        batch_times.append(batch_time)

    print(f"\nHigh volume event creation (10,000 events):")
    print(f"  Batches: {batches} x {batch_size} events")
    print(f"  Batch times (ms): {[f'{t:.2f}' for t in batch_times]}")
    print(f"  Average: {sum(batch_times) / len(batch_times):.2f}ms per batch")

    # Check for performance degradation (later batches shouldn't be much slower)
    first_batch_avg = sum(batch_times[:2]) / 2
    last_batch_avg = sum(batch_times[-2:]) / 2
    degradation = (last_batch_avg / first_batch_avg - 1) * 100

    print(f"  Degradation: {degradation:.1f}%")

    # Should not degrade more than 20%
    assert degradation < 20, f"Performance degradation too high: {degradation:.1f}%"


# ============================================================================
# Profiling Utilities
# ============================================================================


@pytest.mark.performance
def test_generate_performance_report():
    """Generate comprehensive performance report."""
    print("\n" + "=" * 80)
    print("PHASE EVENT PERFORMANCE REPORT")
    print("=" * 80)

    # Quick benchmarks
    benchmarks = {}

    # 1. Event creation
    start = time.perf_counter()
    for _ in range(1000):
        PhaseEvent(
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=150.0,
        )
    benchmarks["event_creation"] = (time.perf_counter() - start) * 1000 / 1000

    # 2. Event serialization
    event = PhaseEvent(
        phase_type=PhaseType.LLM_GENERATION,
        status=PhaseStatus.COMPLETED,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        duration_ms=250.0,
    )
    start = time.perf_counter()
    for _ in range(1000):
        _ = event.model_dump()
    benchmarks["serialization"] = (time.perf_counter() - start) * 1000 / 1000

    # 3. Reasoning accumulation
    reasoning = ReasoningData()
    start = time.perf_counter()
    for i in range(100):
        reasoning.add_phase_event(
            PhaseEvent(
                phase_type=list(PhaseType)[i % len(PhaseType)],
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                duration_ms=100.0,
            )
        )
    benchmarks["reasoning_accumulation"] = (time.perf_counter() - start) * 1000

    print("\nBenchmark Results:")
    for name, time_ms in benchmarks.items():
        print(f"  {name}: {time_ms:.4f}ms")

    print("=" * 80)

    # All should be fast
    assert all(t < 10 for t in benchmarks.values()), "Some benchmarks too slow"
