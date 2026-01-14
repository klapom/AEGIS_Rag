# Sprint 69 Feature 69.7 - Implementation Checklist

## Development Tasks

### Prometheus Metrics (2 SP)
- [x] Define `query_total` counter with intent and model labels
- [x] Define `query_latency_seconds` histogram with stage label
- [x] Define `cache_hits_total` and `cache_misses_total` counters
- [x] Define `memory_facts_count` gauge with fact_type label
- [x] Define `error_total` counter with error_type label
- [x] Implement `track_query()` helper function
- [x] Implement `track_cache_hit()` and `track_cache_miss()` helpers
- [x] Implement `update_memory_facts()` helper
- [x] Implement `track_error()` helper
- [x] Add comprehensive docstrings and examples

### Prometheus Alert Rules (1 SP)
- [x] Create `prometheus/alerts.yml` file
- [x] Define Query Performance alerts (4 alerts)
  - [x] HighQueryLatency
  - [x] CriticalQueryLatency
  - [x] HighRetrievalLatency
  - [x] HighGenerationLatency
- [x] Define Error Rate alerts (4 alerts)
  - [x] HighErrorRate
  - [x] CriticalErrorRate
  - [x] HighLLMErrorRate
  - [x] HighDatabaseErrorRate
- [x] Define Memory Budget alerts (2 alerts)
  - [x] MemoryBudgetHigh
  - [x] MemoryBudgetCritical
- [x] Define Cache Performance alerts (1 alert)
  - [x] LowCacheHitRate
- [x] Define LLM Cost alerts (2 alerts)
  - [x] MonthlyBudgetWarning
  - [x] MonthlyBudgetExceeded
- [x] Define Database Health alerts (2 alerts)
  - [x] QdrantCollectionLarge
  - [x] Neo4jGraphLarge
- [x] Define Service Availability alerts (3 alerts)
  - [x] ServiceDown
  - [x] DatabaseDown
  - [x] LLMServiceDown
- [x] Define Query Rate alerts (2 alerts)
  - [x] HighQueryRate
  - [x] VeryLowQueryRate
- [x] Add severity levels (critical, warning, info)
- [x] Add runbook annotations
- [x] Create `prometheus/README.md`

### Grafana Dashboard (2 SP)
- [x] Create `config/grafana/aegis_overview_sprint69.json`
- [x] Add Query Rate panel (timeseries by intent)
- [x] Add P95 Latency by Stage panel (timeseries)
- [x] Add Cache Hit Rate panel (gauge with thresholds)
- [x] Add Error Rate panel (gauge with thresholds)
- [x] Add Memory Facts Count panel (stat with breakdown)
- [x] Add LLM Requests & Tokens panel (stat)
- [x] Add Query Latency Heatmap panel
- [x] Add Errors by Type panel (timeseries)
- [x] Add Queries by Intent pie chart
- [x] Add Cache Performance panel (timeseries)
- [x] Add Database Metrics panel (stat)
- [x] Add LLM Cost panel (timeseries)
- [x] Add LLM Latency by Provider panel (timeseries)
- [x] Add Service Availability panel (stat with UP/DOWN mapping)
- [x] Configure auto-refresh (10s)
- [x] Create `config/grafana/dashboards.yml` provisioning config
- [x] Set default home dashboard

### Configuration Updates
- [x] Update `config/prometheus.yml` to load alert rules
- [x] Update `docker-compose.dgx-spark.yml` Prometheus volumes
- [x] Update `docker-compose.dgx-spark.yml` Grafana volumes
- [x] Add Grafana dashboard provisioning environment variable

### Documentation
- [x] Create `docs/sprints/SPRINT_69_FEATURE_69.7_SUMMARY.md`
  - [x] Overview and objectives
  - [x] Deliverables description
  - [x] Metrics specification
  - [x] Alert rules specification
  - [x] Dashboard specification
  - [x] Testing procedures
  - [x] Integration guide
  - [x] Alert response runbooks
  - [x] Performance impact analysis
  - [x] Success criteria
- [x] Create `prometheus/README.md` for alert rules
- [x] Document metric naming conventions
- [x] Document integration examples

### Testing
- [x] Create `tests/integration/test_sprint69_metrics.py`
- [x] Test metric registration (5 tests)
- [x] Test helper functions (7 tests)
- [x] Test integration scenarios (3 tests)
- [x] Test error tracking (4 parametrized tests)
- [x] Test lifecycle scenarios (3 tests)
- [x] All 22 tests passing
- [x] Create `scripts/verify_monitoring.sh` verification script

## Deployment Tasks

- [x] Verify file structure complete
- [x] Verify metrics exported at `/metrics` endpoint
- [x] Verify Prometheus scraping API metrics
- [x] Verify Grafana datasource configured
- [ ] Restart Prometheus to load alert rules
  ```bash
  docker compose -f docker-compose.dgx-spark.yml restart prometheus
  ```
- [ ] Verify alerts loaded at http://localhost:9090/alerts
- [ ] Verify dashboard accessible at http://localhost:3000
- [ ] Verify all panels rendering correctly

## Integration Tasks (Post-Implementation)

- [ ] Integrate `track_query()` into query coordinator
  - File: `src/agents/coordinator/coordinator.py`
  - Track intent classification latency
  - Track total query latency

- [ ] Integrate cache tracking into Redis cache
  - File: `src/components/memory.py`
  - Track cache hits/misses on get operations

- [ ] Integrate cache tracking into embedding cache
  - File: `src/domains/vector_search/embedding/`
  - Track embedding cache operations

- [ ] Integrate memory metrics updates
  - File: `src/agents/memory_agent/`
  - Periodically update fact counts (every 60s)

- [ ] Integrate error tracking
  - Add try/catch with `track_error()` in:
    - Query handlers
    - LLM calls
    - Database operations

- [ ] Add periodic metrics updater
  - Background task to update:
    - Memory facts count
    - Database metrics (Qdrant points, Neo4j entities)

## Verification Checklist

- [x] Metrics defined in `src/core/metrics.py`
- [x] Alert rules in `prometheus/alerts.yml` (21 alerts)
- [x] Grafana dashboard in `config/grafana/aegis_overview_sprint69.json` (14 panels)
- [x] Prometheus config updated
- [x] Docker Compose updated
- [x] Tests passing (22/22)
- [x] Documentation complete
- [x] Verification script created
- [ ] Prometheus restarted with new alerts
- [ ] Dashboard visible in Grafana
- [ ] Alerts visible in Prometheus

## Success Criteria

### Metrics
- [x] All 6 Sprint 69 metrics defined
- [x] Helper functions implemented
- [x] Metrics exported via `/metrics`
- [ ] Metrics actively tracked in application code (integration needed)

### Alerts
- [x] 21 alert rules defined
- [x] Alert severity levels set
- [x] Runbook annotations added
- [ ] Alerts loaded in Prometheus (requires restart)
- [ ] Alerts firing correctly when thresholds exceeded

### Dashboard
- [x] 14 panels created
- [x] All panels query correct metrics
- [x] Color thresholds configured
- [x] Auto-refresh enabled
- [ ] Dashboard loaded in Grafana (requires restart)
- [ ] All panels rendering without errors

### Testing
- [x] 22 integration tests written
- [x] All tests passing
- [x] Coverage for all helper functions
- [x] Integration scenarios tested

### Documentation
- [x] Feature summary created
- [x] Integration guide provided
- [x] Alert runbooks documented
- [x] Verification script provided

## Known Limitations

1. **Alert rules not loaded yet**
   - Requires Prometheus restart
   - Command: `docker compose -f docker-compose.dgx-spark.yml restart prometheus`

2. **Metrics not integrated into application**
   - Code instrumentation is defined but not yet called
   - Requires integration into query handlers, cache layers, etc.
   - See integration guide in documentation

3. **Alertmanager not configured**
   - Alerts fire but no notifications sent
   - Future enhancement for email/Slack integration

## Next Sprint Tasks

These items are out of scope for Sprint 69 but recommended for future sprints:

1. **Code Integration** (1 SP)
   - Integrate metrics tracking into all query paths
   - Add cache tracking to all cache operations
   - Implement periodic metric updaters

2. **Alertmanager Setup** (2 SP)
   - Configure Alertmanager service
   - Set up notification channels (email, Slack)
   - Define alert routing rules

3. **Distributed Tracing** (3 SP)
   - Add OpenTelemetry instrumentation
   - Trace requests across agents
   - Visualize trace spans in Grafana

4. **Custom Metrics** (1 SP)
   - Document similarity scores
   - Re-ranking effectiveness
   - Knowledge graph density metrics

## Sign-Off

- [x] Infrastructure Agent: Implementation complete
- [ ] Backend Agent: Code integration pending
- [ ] API Agent: Endpoint instrumentation pending
- [ ] Testing Agent: E2E monitoring tests pending

**Status:** Feature 69.7 implementation COMPLETE. Integration and deployment tasks remain.
