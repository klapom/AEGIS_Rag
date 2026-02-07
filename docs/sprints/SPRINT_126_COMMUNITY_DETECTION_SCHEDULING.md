# Sprint 126 Feature 126.1: Scheduled Community Detection

## Problem Statement

Community detection currently runs synchronously during document ingestion, taking **85-97% of total pipeline time** (~625s of 732s for a 251-byte document). The Leiden algorithm processes the **ENTIRE graph** and re-summarizes **ALL communities** after every single document upload, blocking the API for 10-20+ minutes.

## Solution

Move community detection to a nightly batch job that runs at **5:00 AM** outside the ingestion pipeline.

## Architecture

### Configuration Modes

Three execution modes controlled by `GRAPH_COMMUNITY_DETECTION_MODE`:

1. **`scheduled`** (default, recommended):
   - Skip during ingestion
   - Run via nightly batch job at 5 AM
   - API response time: <5s instead of 10-20 minutes

2. **`sync`**:
   - Run during ingestion (original behavior)
   - Blocks API for 10-20 minutes
   - Use only for testing/backward compatibility

3. **`disabled`**:
   - Never run community detection
   - Use for environments that don't need global graph retrieval

### Components

```
src/jobs/
├── __init__.py
└── community_batch_job.py          # Batch job implementation

src/api/v1/admin.py                 # Admin endpoints
├── POST /api/v1/admin/community-detection/trigger    # Manual trigger
└── GET  /api/v1/admin/community-detection/status     # Scheduler status

src/components/ingestion/nodes/
└── graph_extraction.py             # Modified to respect detection mode

src/core/config.py                  # New GRAPH_COMMUNITY_DETECTION_MODE setting
```

## API Endpoints

### Manual Trigger

```bash
POST /api/v1/admin/community-detection/trigger
```

**Response:**
```json
{
  "job_id": "comm_batch_20260207_050000",
  "started_at": "2026-02-07T05:00:00Z",
  "completed_at": "2026-02-07T05:15:23Z",
  "duration_seconds": 923.45,
  "communities_detected": 2387,
  "summaries_generated": 2387,
  "algorithm": "leiden",
  "success": true
}
```

### Scheduler Status

```bash
GET /api/v1/admin/community-detection/status
```

**Response:**
```json
{
  "running": true,
  "next_run": "2026-02-08T05:00:00Z",
  "last_run": "2026-02-07T05:00:00Z",
  "mode": "scheduled"
}
```

## Configuration

### Environment Variables

**.env:**
```bash
# Sprint 126 Feature 126.1: Community Detection Mode
GRAPH_COMMUNITY_DETECTION_MODE=scheduled  # scheduled | sync | disabled
```

**docker-compose.dgx-spark.yml:**
```yaml
services:
  api:
    environment:
      - GRAPH_COMMUNITY_DETECTION_MODE=${GRAPH_COMMUNITY_DETECTION_MODE:-scheduled}
```

### Batch Job Schedule

Default schedule: **5:00 AM daily** (cron: `0 5 * * *`)

To change schedule, modify `src/jobs/community_batch_job.py`:
```python
cron_schedule = "0 5 * * *"  # Change to your preferred time
```

## Usage Examples

### Development (Test Mode)

```bash
# Set to sync mode for immediate feedback during testing
export GRAPH_COMMUNITY_DETECTION_MODE=sync

# Restart API
docker compose -f docker-compose.dgx-spark.yml restart api
```

### Production (Scheduled Mode)

```bash
# Use default scheduled mode
export GRAPH_COMMUNITY_DETECTION_MODE=scheduled

# Start services (scheduler starts automatically)
docker compose -f docker-compose.dgx-spark.yml up -d
```

### Manual Trigger

```bash
# Trigger community detection immediately
curl -X POST http://localhost:8000/api/v1/admin/community-detection/trigger

# Check scheduler status
curl http://localhost:8000/api/v1/admin/community-detection/status
```

## Performance Impact

### Before (Sync Mode)

| Operation | Duration | % of Total |
|-----------|----------|------------|
| Community Detection | 625s | 85% |
| Entity Extraction | 50s | 7% |
| Relation Extraction | 40s | 5% |
| Other | 17s | 3% |
| **Total Ingestion** | **732s** | **100%** |

### After (Scheduled Mode)

| Operation | Duration | % of Total |
|-----------|----------|------------|
| Entity Extraction | 50s | 47% |
| Relation Extraction | 40s | 37% |
| Other | 17s | 16% |
| **Total Ingestion** | **107s** | **100%** |

**Improvement:** 625s → 0s = **85% faster** (10-20 minutes → <2 minutes)

## Testing

### Unit Tests

```bash
# Run all community detection tests
poetry run pytest tests/unit/jobs/test_community_batch_job.py -v
poetry run pytest tests/unit/core/test_config_community_mode.py -v
```

### Integration Test

```bash
# 1. Upload a document (should be fast)
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -F "file=@test.pdf" \
  -F "namespace=test"

# 2. Verify community detection was deferred (check logs)
docker logs aegis-api | grep "community_detection_deferred"

# 3. Trigger manually
curl -X POST http://localhost:8000/api/v1/admin/community-detection/trigger

# 4. Check results
curl http://localhost:8000/api/v1/admin/community-detection/status
```

## Backward Compatibility

- **Default mode:** `scheduled` (new behavior)
- **Legacy tests:** Can set `GRAPH_COMMUNITY_DETECTION_MODE=sync` to maintain old behavior
- **API contracts:** No changes to existing endpoints
- **Database schema:** No migrations required

## Limitations

- **Scheduler runs in API process:** If API is restarted, scheduled job restarts
- **No job persistence:** Missed runs are coalesced into one (APScheduler behavior)
- **No distributed scheduling:** Single instance only (use external scheduler for multi-instance)

## Future Improvements (Not Implemented)

1. **Separate Worker Process:** Run scheduler in dedicated worker container
2. **Job Persistence:** Store job history in Redis/PostgreSQL
3. **Distributed Scheduling:** Use Celery/RQ for multi-instance deployments
4. **Incremental Detection:** Only re-compute communities for changed documents

## Files Modified

| File | Changes |
|------|---------|
| `src/core/config.py` | Add `graph_community_detection_mode` setting |
| `src/components/ingestion/nodes/graph_extraction.py` | Check mode, skip if scheduled |
| `src/jobs/community_batch_job.py` | New batch job implementation |
| `src/api/v1/admin.py` | Add trigger + status endpoints |
| `.env.template` | Document new setting |
| `docker-compose.dgx-spark.yml` | Add env var to api service |
| `tests/unit/jobs/test_community_batch_job.py` | Unit tests (8 tests) |
| `tests/unit/core/test_config_community_mode.py` | Config tests (4 tests) |

## Test Coverage

**12/12 tests passing (100%)**

```bash
tests/unit/jobs/test_community_batch_job.py::test_run_community_detection_batch_success PASSED
tests/unit/jobs/test_community_batch_job.py::test_run_community_detection_batch_failure PASSED
tests/unit/jobs/test_community_batch_job.py::test_start_community_detection_scheduler_scheduled_mode PASSED
tests/unit/jobs/test_community_batch_job.py::test_start_community_detection_scheduler_sync_mode PASSED
tests/unit/jobs/test_community_batch_job.py::test_start_community_detection_scheduler_disabled_mode PASSED
tests/unit/jobs/test_community_batch_job.py::test_shutdown_community_detection_scheduler PASSED
tests/unit/jobs/test_community_batch_job.py::test_get_scheduler_status_running PASSED
tests/unit/jobs/test_community_batch_job.py::test_get_scheduler_status_not_running PASSED
tests/unit/core/test_config_community_mode.py::test_community_detection_mode_scheduled PASSED
tests/unit/core/test_config_community_mode.py::test_community_detection_mode_sync PASSED
tests/unit/core/test_config_community_mode.py::test_community_detection_mode_disabled PASSED
tests/unit/core/test_config_community_mode.py::test_community_detection_mode_invalid PASSED
```

## Related ADRs

- **ADR-057:** Community Detection for 4-Way Hybrid RRF (Sprint 42)
- **TD-058:** Community Summary Generation (Sprint 52)

## Sprint Context

**Sprint:** 126
**Feature ID:** 126.1
**Story Points:** 5
**Priority:** P1 (Blocking API performance)
