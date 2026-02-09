# Sprint 128.2: Cascade Timeout Guard Implementation

## Overview

Implemented cascade timeout guard to prevent competing vLLM requests when a timed-out request is still running server-side.

## Problem Statement

When an extraction request times out at Rank 1 (vLLM), the cascade immediately tries Rank 2. However, vLLM continues processing the timed-out request server-side. Combined with 2-worker parallelism, this resulted in 3-5 concurrent vLLM requests (34.8% of time), exceeding the optimal 2 concurrent requests.

## Solution

Added a guard that checks vLLM active requests before starting the next cascade rank after a timeout. If vLLM is at capacity, the guard waits with exponential backoff before proceeding.

## Implementation Details

### 1. vLLM Active Request Monitoring (`aegis_llm_proxy.py`)

Added `get_vllm_active_requests()` method:
- Queries vLLM's Prometheus `/metrics` endpoint
- Parses `vllm:num_requests_running` and `vllm:num_requests_waiting` metrics
- Returns total active + waiting requests (or 0 if unavailable)
- 5-second timeout for health check

**Location:** `/home/admin/projects/aegisrag/AEGIS_Rag/src/domains/llm_integration/proxy/aegis_llm_proxy.py` (lines 298-370)

**Key Features:**
- Returns 0 if vLLM is disabled
- Gracefully handles connection errors
- Parses Prometheus text format metrics
- Debug logging for monitoring

### 2. Cascade Guard Logic (`extraction_service.py`)

Added `_wait_for_vllm_capacity()` method:
- Checks if vLLM has capacity before starting next cascade rank
- Waits with exponential backoff (5s → 10s → 20s) if at capacity
- Maximum wait time: 60 seconds (configurable)
- Logs guard activation and release

**Location:** `/home/admin/projects/aegisrag/AEGIS_Rag/src/components/graph_rag/extraction_service.py` (lines 1080-1162)

**Key Features:**
- Only activates after timeout errors (not other exceptions)
- Skips if vLLM is disabled
- Exponential backoff with max wait limit
- Structured logging for monitoring

### 3. Cascade Loop Integration

Modified both entity and relationship extraction cascade loops:
- Track if previous rank timed out (`previous_rank_timed_out` flag)
- Invoke guard before starting next rank after timeout
- Reset flag after guard completes or on non-timeout errors

**Locations:**
- Entity extraction: `/home/admin/projects/aegisrag/AEGIS_Rag/src/components/graph_rag/extraction_service.py` (lines 2607-2687)
- Relationship extraction: `/home/admin/projects/aegisrag/AEGIS_Rag/src/components/graph_rag/extraction_service.py` (lines 3415-3495)

**Changes:**
```python
# Track timeout for guard
previous_rank_timed_out = False

for rank_config in cascade:
    try:
        # Guard: Wait for vLLM capacity if previous rank timed out
        if previous_rank_timed_out:
            await self._wait_for_vllm_capacity(
                rank_config=rank_config,
                max_workers=EXTRACTION_WORKERS,
                max_wait_s=60,
            )
            previous_rank_timed_out = False

        # Extraction logic...

    except (asyncio.TimeoutError, TimeoutError) as e:
        # Mark timeout for guard on next rank
        previous_rank_timed_out = True
        # Log fallback...

    except Exception as e:
        # Non-timeout error - no guard needed
        previous_rank_timed_out = False
        # Log fallback...
```

## Test Coverage

Created comprehensive unit tests:

### Cascade Guard Tests (`test_extraction_service_cascade_guard.py`)

**Location:** `/home/admin/projects/aegisrag/AEGIS_Rag/tests/unit/components/graph_rag/test_extraction_service_cascade_guard.py`

**Tests (7 total):**
1. `test_wait_for_vllm_capacity_disabled_vllm` - Guard returns immediately when vLLM disabled
2. `test_wait_for_vllm_capacity_available_immediately` - Guard returns immediately when capacity available
3. `test_wait_for_vllm_capacity_wait_then_release` - Guard waits, then releases when capacity available
4. `test_wait_for_vllm_capacity_max_wait_exceeded` - Guard proceeds after max wait time
5. `test_extract_entities_guard_invoked_on_timeout` - Guard invoked in entity extraction cascade
6. `test_extract_relationships_guard_invoked_on_timeout` - Guard invoked in relationship extraction cascade
7. `test_guard_not_invoked_on_non_timeout_error` - Guard skipped for non-timeout errors

### vLLM Active Requests Tests (`test_aegis_llm_proxy.py`)

**Location:** `/home/admin/projects/aegisrag/AEGIS_Rag/tests/unit/domains/llm_integration/test_aegis_llm_proxy.py` (lines 578-789)

**Tests (6 total):**
1. `test_get_vllm_active_requests_success` - Parse Prometheus metrics (2 running + 1 waiting = 3)
2. `test_get_vllm_active_requests_vllm_disabled` - Return 0 when vLLM disabled
3. `test_get_vllm_active_requests_metrics_unavailable` - Return 0 when /metrics returns 404
4. `test_get_vllm_active_requests_connection_error` - Return 0 when connection fails
5. `test_get_vllm_active_requests_malformed_metrics` - Handle malformed metrics gracefully
6. `test_get_vllm_active_requests_zero_active` - Correctly return 0 when no active requests

**All tests passing:** ✅ 13/13 (100%)

## Configuration

Guard uses existing `AEGIS_EXTRACTION_WORKERS` environment variable:
- Default: 1 (sequential)
- Recommended: 2 (optimal for DGX Spark)
- Location: `docker-compose.dgx-spark.yml` and `.env`

Guard parameters:
- `max_wait_s`: 60 seconds (hardcoded in cascade loops)
- Exponential backoff: 5s → 10s → 20s
- Timeout types detected: `asyncio.TimeoutError`, `TimeoutError`

## Expected Impact

**Before:**
- 34.8% of time at 3-5 concurrent vLLM requests
- Competing requests for same extraction task
- GPU memory pressure from excessive concurrent requests

**After:**
- Maximum 2 concurrent vLLM requests (respects EXTRACTION_WORKERS)
- No competing requests after timeout
- Reduced GPU memory pressure
- Improved extraction stability

## Monitoring

Key log events for monitoring:
- `cascade_guard_waiting` - Guard activated (active requests >= max_workers)
- `cascade_guard_released` - Guard released (capacity available)
- `cascade_guard_timeout` - Guard exceeded max wait time
- `vllm_active_requests_check` - Active request count (debug level)

## Files Modified

1. `/home/admin/projects/aegisrag/AEGIS_Rag/src/domains/llm_integration/proxy/aegis_llm_proxy.py`
   - Added `get_vllm_active_requests()` method (73 lines)

2. `/home/admin/projects/aegisrag/AEGIS_Rag/src/components/graph_rag/extraction_service.py`
   - Added `_wait_for_vllm_capacity()` method (83 lines)
   - Modified entity extraction cascade loop (20 lines)
   - Modified relationship extraction cascade loop (20 lines)

3. `/home/admin/projects/aegisrag/AEGIS_Rag/tests/unit/components/graph_rag/test_extraction_service_cascade_guard.py`
   - New test file (331 lines, 7 tests)

4. `/home/admin/projects/aegisrag/AEGIS_Rag/tests/unit/domains/llm_integration/test_aegis_llm_proxy.py`
   - Added `TestVLLMActiveRequests` class (212 lines, 6 tests)

**Total Changes:**
- +719 lines of code (implementation + tests)
- 4 files modified
- 13 new unit tests (100% passing)

## Testing Commands

```bash
# Run cascade guard tests
poetry run pytest tests/unit/components/graph_rag/test_extraction_service_cascade_guard.py -v

# Run vLLM active requests tests
poetry run pytest tests/unit/domains/llm_integration/test_aegis_llm_proxy.py::TestVLLMActiveRequests -v

# Run all new tests
poetry run pytest tests/unit/components/graph_rag/test_extraction_service_cascade_guard.py tests/unit/domains/llm_integration/test_aegis_llm_proxy.py::TestVLLMActiveRequests -v
```

## Next Steps

1. Deploy to production (rebuild Docker containers)
2. Monitor guard activation frequency in logs
3. Analyze reduction in concurrent vLLM requests
4. Measure impact on extraction success rate
5. Adjust `max_wait_s` if needed based on production metrics

## References

- **Sprint 127:** RAGAS Phase 1 Benchmark - Identified cascade timeout issue (34.8% at 3-5 concurrent requests)
- **Sprint 128.2:** This implementation
- **ADR-059:** vLLM dual-engine architecture
- **ADR-062:** Engine mode hot-reload
