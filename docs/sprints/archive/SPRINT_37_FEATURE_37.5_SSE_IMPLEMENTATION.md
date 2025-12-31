# Sprint 37 Feature 37.5: Backend SSE Streaming Updates

**Status:** COMPLETED ✅
**Date:** 2025-12-06
**Story Points:** 5 SP
**Agent:** API Agent

---

## Overview

Implemented backend Server-Sent Events (SSE) endpoint for real-time pipeline progress visualization. The endpoint streams progress updates from the `PipelineProgressManager` to the frontend, enabling live monitoring of document ingestion with stage-level granularity, worker pool status, and extraction metrics.

---

## Implementation Details

### 1. Pydantic Schema: `src/api/models/pipeline_progress.py`

Created comprehensive Pydantic v2 models for SSE event serialization:

```python
PipelineProgressEvent
├── type: str = "pipeline_progress"
└── data: PipelineProgressEventData
    ├── document_id: str
    ├── document_name: str
    ├── total_chunks: int
    ├── total_images: int
    ├── stages: Dict[str, StageProgressSchema]
    │   └── StageProgressSchema
    │       ├── name: str
    │       ├── status: str  # pending, in_progress, completed, error
    │       ├── processed: int
    │       ├── total: int
    │       ├── in_flight: int
    │       ├── progress_percent: float
    │       ├── duration_ms: int
    │       └── is_complete: bool
    ├── worker_pool: WorkerPoolSchema
    │   ├── active: int
    │   ├── max: int
    │   ├── queue_depth: int
    │   └── workers: List[WorkerInfoSchema]
    │       ├── id: int
    │       ├── status: str  # idle, processing, error
    │       ├── current_chunk: str | None
    │       └── progress_percent: float
    ├── metrics: MetricsSchema
    │   ├── entities_total: int
    │   ├── relations_total: int
    │   ├── neo4j_writes: int
    │   └── qdrant_writes: int
    ├── timing: TimingSchema
    │   ├── started_at: float
    │   ├── elapsed_ms: int
    │   └── estimated_remaining_ms: int
    └── overall_progress_percent: float
```

**Key Design Decisions:**

- **Pydantic v2:** Uses `BaseModel` with `Field()` for comprehensive validation and OpenAPI generation
- **Frontend Alignment:** Schema exactly matches TypeScript `PipelineProgressData` interface
- **Comprehensive Documentation:** Each model has detailed docstrings with examples
- **Type Safety:** Strict typing with `str | None` for optional fields

**File Size:** 352 lines (including documentation)

---

### 2. Admin API Endpoint: `src/api/v1/admin.py`

Added new SSE streaming endpoint:

#### Endpoint Specification

```python
@router.get("/ingestion/jobs/{job_id}/progress")
async def stream_pipeline_progress(
    job_id: str,
    request: Request,
) -> StreamingResponse
```

**URL:** `GET /api/v1/admin/ingestion/jobs/{job_id}/progress`
**Response Type:** `text/event-stream` (SSE)
**Authentication:** Not required (admin endpoints)

#### SSE Event Format

```
event: pipeline_progress
data: {"document_id": "...", "stages": {...}, ...}

event: pipeline_progress
data: {"document_id": "...", "stages": {...}, ...}

event: complete
data: {}
```

#### Features

1. **Real-time Progress Streaming:**
   - Fetches progress from `PipelineProgressManager` singleton
   - Throttled at ~500ms intervals (prevents excessive updates)
   - Streams until 100% completion or client disconnect

2. **Error Handling:**
   - Job not found: Returns `event: error` with message
   - Client disconnect: Clean shutdown with logging
   - Stream errors: Sends error event before terminating

3. **SSE Headers:**
   - `Cache-Control: no-cache` - Prevents caching
   - `Connection: keep-alive` - Maintains persistent connection
   - `X-Accel-Buffering: no` - Disables nginx buffering
   - `Access-Control-Allow-Origin: *` - CORS support for SSE

4. **Logging:**
   - Stream start: Logs job_id and client IP
   - Stream complete: Logs final progress percentage
   - Client disconnect: Logs disconnection
   - Errors: Full traceback with structured logging

#### Example cURL Request

```bash
curl -N "http://localhost:8000/api/v1/admin/ingestion/jobs/job_123/progress" \
  -H "Accept: text/event-stream"
```

#### Example Frontend Integration

```typescript
const eventSource = new EventSource(
  `/api/v1/admin/ingestion/jobs/${jobId}/progress`
);

eventSource.addEventListener('pipeline_progress', (event) => {
  const data: PipelineProgressData = JSON.parse(event.data);

  // Update UI with stage progress
  data.stages.extraction.progress_percent // 46.9

  // Update worker pool visualization
  data.worker_pool.active // 4
  data.worker_pool.queue_depth // 13

  // Update metrics counters
  data.metrics.entities_total // 42
  data.metrics.relations_total // 28

  // Update timing
  data.timing.elapsed_ms // 12500
  data.timing.estimated_remaining_ms // 14200

  // Update overall progress
  data.overall_progress_percent // 46.9
});

eventSource.addEventListener('complete', () => {
  console.log('Pipeline processing complete!');
  eventSource.close();
});

eventSource.addEventListener('error', (event) => {
  const data = JSON.parse(event.data);
  console.error('Stream error:', data.message);
  eventSource.close();
});
```

---

### 3. Updated Files

#### Modified Files

1. **`src/api/v1/admin.py`** (+142 lines)
   - Added `Request` to FastAPI imports
   - Added `PipelineProgressEvent` import
   - Added `stream_pipeline_progress` endpoint (142 lines with docstring)

2. **`src/api/models/__init__.py`** (+18 lines)
   - Exported all pipeline progress models
   - Updated docstring to reference Sprint 37

#### New Files

1. **`src/api/models/pipeline_progress.py`** (352 lines)
   - Complete Pydantic schema for SSE events
   - 7 model classes with comprehensive documentation
   - Example JSON in module docstring

---

## Integration with Existing Components

### Progress Manager (`src/components/ingestion/progress_manager.py`)

The SSE endpoint consumes the existing `PipelineProgressManager` singleton:

```python
from src.components.ingestion.progress_manager import get_progress_manager

progress_manager = get_progress_manager()
event = progress_manager.get_sse_event(job_id)  # Returns dict
```

**Key Methods Used:**

- `get_sse_event(job_id)` - Get current progress as SSE-compatible dict
- `_throttle_ms = 500` - Built-in throttling at 500ms intervals

**No modifications required to `progress_manager.py`** - it already provides the exact format needed for SSE streaming.

---

## Testing

### Manual Testing Script

```python
"""Test SSE endpoint with real progress manager."""
from src.components.ingestion.progress_manager import get_progress_manager, StageStatus
import asyncio

async def test_sse_endpoint():
    # Setup progress manager
    manager = get_progress_manager()

    # Start document tracking
    manager.start_document(
        document_id="test-job-123",
        document_name="test.pdf",
        total_chunks=32,
        total_images=5,
    )

    # Simulate progress updates
    await manager.update_stage(
        document_id="test-job-123",
        stage_name="parsing",
        processed=1,
        total=1,
        status=StageStatus.COMPLETED,
    )

    await manager.update_stage(
        document_id="test-job-123",
        stage_name="extraction",
        processed=15,
        total=32,
        in_flight=4,
        status=StageStatus.IN_PROGRESS,
    )

    # Get SSE event
    event = manager.get_sse_event("test-job-123")

    print("SSE Event:")
    print(json.dumps(event, indent=2))

    # Verify structure
    assert event["type"] == "pipeline_progress"
    assert event["data"]["document_id"] == "test-job-123"
    assert event["data"]["stages"]["parsing"]["status"] == "completed"
    assert event["data"]["stages"]["extraction"]["status"] == "in_progress"
    assert event["data"]["overall_progress_percent"] > 0

    print("✅ All assertions passed!")

asyncio.run(test_sse_endpoint())
```

### Integration Test Verification

```bash
# Start FastAPI server
poetry run uvicorn src.api.main:app --reload

# In another terminal, test SSE endpoint
curl -N "http://localhost:8000/api/v1/admin/ingestion/jobs/test-job-123/progress" \
  -H "Accept: text/event-stream"
```

**Expected Output:**
```
event: pipeline_progress
data: {"document_id": "test-job-123", "stages": {...}, ...}

event: pipeline_progress
data: {"document_id": "test-job-123", "stages": {...}, ...}

event: complete
data: {}
```

---

## Performance Characteristics

### Throttling Strategy

1. **Progress Manager Throttling:**
   - Minimum 500ms between SSE event emissions
   - Implemented in `PipelineProgressManager._emit_sse_event()`
   - Prevents excessive updates during rapid progress changes

2. **Endpoint Throttling:**
   - `asyncio.sleep(0.5)` in event loop
   - Prevents tight loop when no updates available
   - Combined with manager throttling = consistent 500ms intervals

### Resource Usage

- **Memory:** Minimal (reads existing progress state, no buffering)
- **CPU:** Low (simple dict serialization + JSON encoding)
- **Network:** ~1-2 KB per event, ~2 events/second = ~4 KB/s per client

### Scalability

- **Concurrent Clients:** Supports multiple clients streaming different job_ids
- **Client Disconnect Handling:** Automatic cleanup with `request.is_disconnected()`
- **Error Recovery:** Stream terminates on error (client can reconnect)

---

## API Documentation (OpenAPI)

The endpoint is fully documented with:

- **Summary:** "Stream pipeline progress via SSE"
- **Description:** Comprehensive SSE format, event types, frontend integration example
- **Parameters:** `job_id` (path parameter)
- **Response Model:** `StreamingResponse` with `text/event-stream`
- **Example cURL Request:** Complete curl command
- **Example Frontend Code:** TypeScript EventSource integration

---

## Frontend Integration Points

### Expected Frontend Components

1. **AdminIndexingPage.tsx** (Sprint 37 Feature 37.3):
   - Opens EventSource on job start
   - Listens for `pipeline_progress` events
   - Updates state with `PipelineProgressData`
   - Closes EventSource on `complete` event

2. **PipelineProgressData Interface** (TypeScript):
   ```typescript
   interface PipelineProgressData {
     document_id: string;
     document_name: string;
     total_chunks: number;
     total_images: number;
     stages: {
       [key: string]: {
         name: string;
         status: "pending" | "in_progress" | "completed" | "error";
         processed: number;
         total: number;
         in_flight: number;
         progress_percent: number;
         duration_ms: number;
         is_complete: boolean;
       };
     };
     worker_pool: {
       active: number;
       max: number;
       queue_depth: number;
       workers: Array<{
         id: number;
         status: "idle" | "processing" | "error";
         current_chunk: string | null;
         progress_percent: number;
       }>;
     };
     metrics: {
       entities_total: number;
       relations_total: number;
       neo4j_writes: number;
       qdrant_writes: number;
     };
     timing: {
       started_at: number;
       elapsed_ms: number;
       estimated_remaining_ms: number;
     };
     overall_progress_percent: number;
   }
   ```

**The Pydantic schema exactly matches this TypeScript interface!**

---

## Error Handling

### Job Not Found

```
event: error
data: {"message": "Job not found: job_123", "job_id": "job_123"}
```

Frontend should:
- Display error message
- Close EventSource
- Optionally retry with backoff

### Client Disconnect

- Server detects via `await request.is_disconnected()`
- Logs disconnection
- Cleans up event generator
- No client action needed

### Stream Error

```
event: error
data: {"message": "Stream error: ...", "job_id": "job_123"}
```

Frontend should:
- Display error message
- Close EventSource
- Allow user to retry

---

## Acceptance Criteria

- [x] SSE endpoint streams progress events
- [x] Events match frontend `PipelineProgressData` interface
- [x] Throttling at ~500ms intervals
- [x] Clean disconnect handling
- [x] Complete event sent when done (100% progress)
- [x] Error events for job not found / stream errors
- [x] CORS headers for SSE
- [x] Comprehensive OpenAPI documentation
- [x] Structured logging for debugging

---

## Future Enhancements

### Potential Improvements

1. **Authentication:**
   - Add JWT token validation for SSE endpoint
   - Use query parameter token (EventSource doesn't support custom headers)

2. **Reconnection Support:**
   - Add `Last-Event-ID` header support
   - Resume streaming from last received event

3. **Multiple Job Streaming:**
   - Stream progress for all active jobs
   - Client filters by job_id

4. **Compression:**
   - gzip compression for SSE payload (if supported by nginx)

5. **Metrics:**
   - Track active SSE connections with Prometheus
   - Alert on high connection count

---

## Related Documentation

- [Progress Manager Implementation](../../src/components/ingestion/progress_manager.py)
- [Admin API Documentation](../../src/api/v1/admin.py)
- [Pipeline Progress Schema](../../src/api/models/pipeline_progress.py)
- [Frontend Integration (Sprint 37.3)](./SPRINT_37_FEATURE_37.3_FRONTEND_PROGRESS.md)

---

## Lessons Learned

### What Went Well

1. **Schema Design:** Pydantic v2 models with comprehensive documentation made frontend integration trivial
2. **Existing Infrastructure:** `PipelineProgressManager` already provided perfect SSE format
3. **Error Handling:** Comprehensive error events prevent silent failures

### What Could Be Improved

1. **Authentication:** SSE with EventSource doesn't support custom headers (limitation of browser API)
2. **Testing:** Should add E2E test with real SSE client (not just curl)

### Technical Debt

- **TD-048:** Add integration test for SSE endpoint with real progress updates
- **TD-049:** Add authentication support for SSE endpoint (query param JWT)

---

## Conclusion

Feature 37.5 successfully implements backend SSE streaming for pipeline progress visualization. The endpoint provides real-time updates with comprehensive error handling, clean disconnect detection, and full frontend compatibility. The Pydantic schema ensures type safety and API documentation, while the existing `PipelineProgressManager` provides efficient throttled updates.

**Status:** READY FOR FRONTEND INTEGRATION ✅

---

**Next Steps:**

1. Frontend team implements EventSource integration (Sprint 37.3)
2. Add integration tests for SSE endpoint (TD-048)
3. Consider adding authentication (TD-049)
