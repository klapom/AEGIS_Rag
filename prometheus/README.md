# AegisRAG Prometheus Monitoring

This directory contains Prometheus alert rules for production monitoring of AegisRAG.

## Alert Rules

**File:** `alerts.yml`

### Alert Groups

1. **query_performance** (4 alerts)
   - HighQueryLatency
   - CriticalQueryLatency
   - HighRetrievalLatency
   - HighGenerationLatency

2. **error_rates** (4 alerts)
   - HighErrorRate
   - CriticalErrorRate
   - HighLLMErrorRate
   - HighDatabaseErrorRate

3. **memory_budget** (2 alerts)
   - MemoryBudgetHigh
   - MemoryBudgetCritical

4. **cache_performance** (1 alert)
   - LowCacheHitRate

5. **llm_cost** (2 alerts)
   - MonthlyBudgetWarning
   - MonthlyBudgetExceeded

6. **database_health** (2 alerts)
   - QdrantCollectionLarge
   - Neo4jGraphLarge

7. **service_availability** (3 alerts)
   - ServiceDown
   - DatabaseDown
   - LLMServiceDown

8. **query_rate** (2 alerts)
   - HighQueryRate
   - VeryLowQueryRate

**Total:** 21 alert rules

## Deployment

### Docker Compose

Alert rules are automatically mounted in the Prometheus container:

```yaml
volumes:
  - ./prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro
```

### Reload Configuration

To reload alert rules without restarting:

```bash
# Option 1: Use Prometheus API (if --web.enable-lifecycle is enabled)
curl -X POST http://localhost:9090/-/reload

# Option 2: Restart Prometheus container
docker compose -f docker-compose.dgx-spark.yml restart prometheus
```

## Verification

### Check Alert Rules Loaded

```bash
# Via Prometheus API
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].name'

# Via Prometheus UI
open http://localhost:9090/alerts
```

### Test Alert Rules

```bash
# View active alerts
curl http://localhost:9090/api/v1/alerts

# Query specific alert
curl 'http://localhost:9090/api/v1/query?query=ALERTS{alertname="HighQueryLatency"}'
```

## Alert Severity Levels

- **critical**: Immediate action required (paging recommended)
- **warning**: Investigation needed (email/Slack notification)
- **info**: Informational (logging/monitoring only)

## Customization

To customize alert thresholds:

1. Edit `alerts.yml`
2. Modify the `expr` field for the desired alert
3. Reload Prometheus configuration

Example - Change HighQueryLatency threshold from 1s to 2s:

```yaml
- alert: HighQueryLatency
  expr: |
    histogram_quantile(0.95,
      sum(rate(aegis_query_latency_seconds_bucket{stage="total"}[5m])) by (le)
    ) > 2.0  # Changed from 1.0
  for: 5m
```

## Troubleshooting

### Alert Rules Not Loading

1. Check Prometheus logs:
   ```bash
   docker compose -f docker-compose.dgx-spark.yml logs prometheus
   ```

2. Validate alert rules syntax:
   ```bash
   docker run --rm -v $(pwd)/prometheus/alerts.yml:/alerts.yml prom/prometheus:latest promtool check rules /alerts.yml
   ```

3. Verify volume mount:
   ```bash
   docker exec aegis-prometheus cat /etc/prometheus/alerts.yml
   ```

### Alerts Not Firing

1. Check metric availability:
   ```bash
   curl http://localhost:8000/metrics | grep aegis_queries_total
   ```

2. Test alert expression in Prometheus UI:
   - Go to http://localhost:9090/graph
   - Paste alert expression
   - Execute query

3. Verify alert evaluation:
   - Go to http://localhost:9090/alerts
   - Check alert state (inactive/pending/firing)

## Related Documentation

- [Sprint 69 Feature 69.7 Summary](../docs/sprints/SPRINT_69_FEATURE_69.7_SUMMARY.md)
- [Prometheus Configuration](../config/prometheus.yml)
- [Grafana Dashboard](../config/grafana/aegis_overview_sprint69.json)
- [Metrics Documentation](../src/core/metrics.py)
