# Grafana Dashboards - Quick Reference

## Dashboard Overview Table

| Dashboard | Purpose | Audience | Key Metrics | Access |
|-----------|---------|----------|-------------|--------|
| **1. Executive Overview** | Business health snapshot | Executives, PMs | QPS, Cost, Uptime | `/d/aegis-executive-overview` |
| **2. RAG Pipeline** | Performance by stage | ML Engineers | Latency stages, RAGAS scores | `/d/aegis-rag-pipeline` |
| **3. LLM Operations** | Cost & provider performance | Finance, DevOps | Cost by provider, tokens, budget | `/d/aegis-llm-operations` |
| **4. Data Stores** | Infrastructure health | DevOps | Pool usage, connections, memory | `/d/aegis-data-stores` |
| **5. Memory System** | Graphiti 3-layer health | Research Eng | Facts by layer, latency, cache | `/d/aegis-memory-system` |

---

## Key Metrics at a Glance

### Executive Dashboard (8 panels)
```
Panel 1: QPS (Queries/sec)           → sum(rate(aegis_queries_total[5m]))
Panel 2: Cost 24h                    → increase(llm_cost_usd[24h])
Panel 3: System Uptime %             → (1 - error_rate) * 100
Panel 4: Monthly Cost (MTD)          → llm_cost_usd_monthly
Panel 5: Response Time P50           → histogram_quantile(0.50, latency)
Panel 6: Knowledge Base Size         → qdrant_points_total + neo4j_entities_total
Panel 7: Query Volume/Hour           → increase(aegis_queries_total[1h])
Panel 8: Error Rate %                → error_rate * 100
```

### RAG Pipeline Dashboard (8 panels)
```
Panel 1: Latency by Stage            → 5 stages (embedding, vector, graph, reranking, llm)
Panel 2: Intent Distribution         → pie chart by intent type
Panel 3: Cache Hit Rate %            → (redis_hits / total) * 100
Panel 4: Error Rate by Type          → validation, retrieval, generation, timeout
Panel 5: Query Success Rate %        → (success / total) * 100
Panel 6: Context Recall (RAGAS)      → avg(ragas_context_recall)
Panel 7: Faithfulness (RAGAS)        → avg(ragas_faithfulness)
Panel 8: Context Precision (RAGAS)   → avg(ragas_context_precision)
```

### LLM Operations Dashboard (8 panels)
```
Panel 1: Cost by Provider            → ollama, alibaba, openai
Panel 2: Token Usage                 → input, output, cached tokens
Panel 3-5: Latency P50/P95/P99       → per provider comparison
Panel 6: Budget Gauge                → % of $1000 monthly budget used
Panel 7: Budget Remaining            → $ remaining
Panel 8: Provider Requests/min       → load distribution
```

### Data Stores Dashboard (11 panels)
```
Panels 1-3:   Qdrant metrics (connections, points, memory)
Panels 4-6:   Neo4j metrics (connections, entities, relations)
Panels 7-9:   Redis metrics (connections, memory, evictions)
Panel 10:     Pool saturation % (all 3 databases)
Panel 11:     Query latency P95 (all 3 databases)
```

### Memory System Dashboard (11 panels)
```
Panels 1-3:   Layer fact counts (episodic, semantic, procedural)
Panel 4:      Facts by type (entity, relationship, event, summary)
Panel 5:      Layer capacity % (vs max limits)
Panels 6-7:   Read/write latency P95 (by layer)
Panels 8-9:   Operations/sec (read/write by layer)
Panel 10:     Memory distribution (pie chart)
Panel 11:     Cache hit rate % (by layer)
```

---

## Quick Access URLs

From Grafana home:
```
Dashboard 1: http://localhost:3000/d/aegis-executive-overview
Dashboard 2: http://localhost:3000/d/aegis-rag-pipeline
Dashboard 3: http://localhost:3000/d/aegis-llm-operations
Dashboard 4: http://localhost:3000/d/aegis-data-stores
Dashboard 5: http://localhost:3000/d/aegis-memory-system
```

---

## Refresh Rates & Time Ranges

| Dashboard | Refresh | Default Range | Typical Analysis |
|-----------|---------|---|---|
| Executive Overview | 30s | Last 24h | Executive daily standup |
| RAG Pipeline | 10s | Last 1h | Real-time tuning |
| LLM Operations | 30s | Last 7d | Weekly cost review |
| Data Stores | 15s | Last 6h | Capacity planning |
| Memory System | 15s | Last 6h | Memory optimization |

---

## Performance Thresholds

### Green (Healthy)
- QPS: < 40 req/s
- Uptime: > 99%
- P50 Latency: < 200ms
- Error Rate: < 0.5%
- Cost/day: < $100
- Pool Saturation: < 70%
- Cache Hit Rate: > 75%
- RAGAS Faithfulness: > 0.85
- RAGAS Context Recall: > 0.80

### Yellow (Warning)
- QPS: 40-50 req/s
- Uptime: 95-99%
- P50 Latency: 200-500ms
- Error Rate: 0.5-2%
- Cost/day: $100-200
- Pool Saturation: 70-85%
- Cache Hit Rate: 50-75%
- RAGAS Faithfulness: 0.7-0.85
- RAGAS Context Recall: 0.6-0.80

### Red (Critical)
- QPS: > 50 req/s
- Uptime: < 95%
- P50 Latency: > 500ms
- Error Rate: > 2%
- Cost/day: > $200
- Pool Saturation: > 85%
- Cache Hit Rate: < 50%
- RAGAS Faithfulness: < 0.7
- RAGAS Context Recall: < 0.6

---

## Common Troubleshooting

### "No data" in panel
1. Check time range (adjust dashboard time picker)
2. Verify Prometheus datasource: Configuration → Data Sources
3. Query metric directly: Prometheus UI → Graph

### Dashboard not loading
1. Check Grafana logs: `docker logs aegis-grafana`
2. Verify dashboard file exists: `ls config/grafana/dashboards/`
3. Restart Grafana: `docker restart aegis-grafana`

### Missing metrics
1. Check Prometheus targets: http://localhost:9090/targets
2. Verify scrape config: `config/prometheus.yml`
3. Check API metrics endpoint: `curl http://localhost:8000/metrics`

### Performance issues
1. Reduce refresh rate (edit dashboard)
2. Reduce time range
3. Add metric filters to PromQL queries
4. Check Prometheus disk usage

---

## Common PromQL Patterns

### Rate/second
```promql
rate(metric_total[5m])          # per 5-minute window
sum(rate(metric_total[1m])) * 60  # convert to per-second
```

### Percentiles
```promql
histogram_quantile(0.50, metric_bucket)  # P50 (median)
histogram_quantile(0.95, metric_bucket)  # P95
histogram_quantile(0.99, metric_bucket)  # P99
```

### By label
```promql
sum(metric) by (label1, label2)  # sum grouped by labels
rate(metric[5m]) by (instance)   # rate per instance
```

### Calculate percentage
```promql
(success / total) * 100
(active / max) * 100
(hits / (hits + misses)) * 100
```

---

## File Locations

**Dashboard JSON files:**
```
/home/admin/projects/aegisrag/AEGIS_Rag/config/grafana/dashboards/
  1-executive-overview.json
  2-rag-pipeline.json
  3-llm-operations.json
  4-data-stores.json
  5-memory-system.json
```

**Documentation:**
```
/home/admin/projects/aegisrag/AEGIS_Rag/config/grafana/
  DASHBOARDS_README.md      (Complete reference)
  SETUP_GUIDE.md            (Setup & troubleshooting)
  DASHBOARD_MANIFEST.md     (Specifications & inventory)
  QUICK_REFERENCE.md        (This file)
```

**Validation script:**
```
/home/admin/projects/aegisrag/AEGIS_Rag/scripts/
  validate_dashboards.py    (Dashboard validator)
```

---

## Validation Commands

```bash
# Validate all dashboards
python3 scripts/validate_dashboards.py

# Validate with verbose output
python3 scripts/validate_dashboards.py --verbose

# Validate specific dashboard
python3 scripts/validate_dashboards.py --dashboard 1-executive-overview.json
```

---

## Docker Commands

```bash
# Start Grafana
docker compose up -d grafana

# View logs
docker logs -f aegis-grafana

# Restart
docker restart aegis-grafana

# Enter container
docker exec -it aegis-grafana /bin/bash

# Check volume mounts
docker inspect aegis-grafana | grep -A 10 Mounts
```

---

## Provisioning Configuration

**File:** `config/grafana/dashboards.yml`

Key features:
- Auto-discovers all `.json` files in `dashboards/` directory
- Reloads every 10 seconds if files change
- Allows UI modifications
- Dashboards not deleted on config removal

---

## Panel Types Used

| Type | Used For | Count |
|------|----------|-------|
| Timeseries | Metrics over time | 42 |
| Stat | Single metric value | 12 |
| Gauge | Percentage/threshold | 1 |
| Piechart | Distribution | 2 |
| Table | Structured data | 0 |

---

## Prometheus Jobs Required

Ensure these scrape jobs in `config/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'aegis-rag-api'      # Application metrics
  - job_name: 'qdrant'             # Vector DB
  - job_name: 'neo4j'              # Graph DB
  - job_name: 'redis'              # Cache
  - job_name: 'prometheus'         # Prometheus itself
```

---

## Next Steps

1. **Deploy:** Follow SETUP_GUIDE.md
2. **Verify:** Run `validate_dashboards.py`
3. **Monitor:** Access Grafana UI
4. **Configure:** Create alerts and notifications
5. **Optimize:** Adjust thresholds based on baselines

---

## Support

For detailed information, see:
- **Setup:** `SETUP_GUIDE.md`
- **Reference:** `DASHBOARDS_README.md`
- **Specs:** `DASHBOARD_MANIFEST.md`

For issues:
1. Check logs: `docker logs aegis-grafana`
2. Validate dashboards: `python3 scripts/validate_dashboards.py --verbose`
3. Verify Prometheus: http://localhost:9090

---

**Last Updated:** Sprint 97
**Status:** Production Ready ✓
