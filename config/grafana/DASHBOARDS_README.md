# Grafana Dashboards - AegisRAG Monitoring Suite

## Overview

Complete monitoring dashboard suite for AegisRAG system spanning executive insights, RAG pipeline performance, LLM operations, infrastructure monitoring, and memory system analysis.

## Dashboard Catalog

### 1. Executive Overview Dashboard
**File:** `1-executive-overview.json`
**UID:** `aegis-executive-overview`
**Audience:** Executives, Product Managers, Operations

**Key Metrics:**
- **QPS (Queries Per Second):** Real-time system throughput
- **Cost (24h):** Last 24 hours LLM API costs in USD
- **System Uptime %:** Availability percentage (inverse of error rate)
- **Cost (MTD):** Month-to-date cumulative LLM costs
- **Average Response Time (P50):** Median query latency
- **Knowledge Base Size:** Total points in Qdrant + entities in Neo4j
- **Query Volume by Hour:** Historical query distribution
- **Error Rate Trend:** System reliability over time

**Refresh Rate:** 30 seconds
**Time Range:** Last 24 hours (customizable to 30 days)

---

### 2. RAG Pipeline Performance Dashboard
**File:** `2-rag-pipeline.json`
**UID:** `aegis-rag-pipeline`
**Audience:** ML Engineers, Data Scientists

**Key Metrics:**
- **Latency by Stage:** P95 latency breakdown across 5 pipeline stages:
  - Embedding: Query vectorization
  - Vector Search: Qdrant/BGE-M3 retrieval
  - Graph Search: Neo4j entity/relationship queries
  - Reranking: Cross-encoder ranking
  - LLM Generation: Model inference time
- **Intent Distribution:** Pie chart of query intents (query, analysis, synthesis, etc.)
- **Cache Hit Rate %:** Redis + memory cache effectiveness
- **Error Rate by Type:** Validation, retrieval, generation, timeout errors
- **Query Success Rate %:** Overall success percentage
- **Average Context Recall:** RAGAS metric tracking
- **Average Faithfulness:** RAGAS metric tracking
- **Avg Context Precision:** RAGAS metric tracking

**Refresh Rate:** 10 seconds
**Time Range:** Last 1 hour

**Performance Targets:**
- Embedding: < 100ms
- Vector Search: < 200ms
- Graph Search: < 200ms
- Reranking: < 100ms
- LLM Generation: < 2000ms (varies by model)

---

### 3. LLM Operations & Cost Management Dashboard
**File:** `3-llm-operations.json`
**UID:** `aegis-llm-operations`
**Audience:** Finance, DevOps, Operations

**Key Metrics:**
- **Cost by Provider ($):** Hourly cost breakdown:
  - Ollama (local, free)
  - Alibaba Cloud (DashScope)
  - OpenAI (fallback)
- **Token Usage by Type:**
  - Input tokens/minute
  - Output tokens/minute
  - Cached tokens/minute
- **Latency P50/P95/P99 by Provider (ms):** Provider performance comparison
- **Current Monthly Budget:** Gauge showing % of budget consumed
- **Budget Remaining ($):** Dollar amount remaining in monthly budget (hardcoded $1000)
- **Provider Requests/min:** Load distribution across providers

**Refresh Rate:** 30 seconds
**Time Range:** Last 7 days

**Budget Configuration:**
- Monthly Budget: $1000 USD (configurable)
- Warning Threshold: 75% usage
- Critical Threshold: 100% usage

---

### 4. Data Stores Infrastructure Dashboard
**File:** `4-data-stores.json`
**UID:** `aegis-data-stores`
**Audience:** DevOps, Infrastructure Engineers

**Key Metrics:**

**Qdrant (Vector Database):**
- Active connections (vs max pool size)
- Total points count
- Memory usage (GB)

**Neo4j (Graph Database):**
- Active connections (vs max pool size)
- Total entities count
- Total relations count

**Redis (Cache/Memory):**
- Active connections (vs max pool size)
- Memory usage (GB)
- Evictions/second

**Overall Infrastructure:**
- Connection pool saturation % (all 3 databases)
- Database query latency P95 (Qdrant, Neo4j, Redis)

**Refresh Rate:** 15 seconds
**Time Range:** Last 6 hours

**Health Thresholds:**
- Green: Pool usage < 70%
- Yellow: Pool usage 70-85%
- Orange: Pool usage 85-95%
- Red: Pool usage > 95%

---

### 5. Memory System - Graphiti 3-Layer Architecture Dashboard
**File:** `5-memory-system.json`
**UID:** `aegis-memory-system`
**Audience:** Research Engineers, Memory Specialists

**Key Metrics:**

**Layer 1: Episodic Memory**
- Fact count (short-term, latest interactions)
- Capacity: 1 million facts max

**Layer 2: Semantic Memory**
- Fact count (long-term, consolidated knowledge)
- Capacity: 500K facts max

**Layer 3: Procedural Memory**
- Fact count (skills, tools, processes)
- Capacity: 100K facts max

**Operational Metrics:**
- Facts by type: Entities, Relationships, Events, Summaries
- Layer capacity usage % (with thresholds)
- Read latency P95 by layer (ms)
- Write latency P95 by layer (ms)
- Read operations/second by layer
- Write operations/second by layer
- Memory distribution by layer (pie chart)
- Cache hit rate % by layer

**Refresh Rate:** 15 seconds
**Time Range:** Last 6 hours

**Performance Targets:**
- Read latency: < 50ms
- Write latency: < 100ms
- Cache hit rate: > 75%

---

## Prometheus Metrics Required

### Executive Overview
```
aegis_queries_total                      # Query counter
llm_cost_usd                            # Cost metric (counter)
llm_cost_usd_monthly                    # Current month total
http_requests_total{status=~"5.."}      # Error counter
aegis_query_latency_seconds_bucket      # Histogram
qdrant_points_total                     # Vector DB points
neo4j_entities_total                    # Graph DB entities
```

### RAG Pipeline
```
aegis_query_latency_seconds_bucket{stage=...}  # By stage
aegis_queries_total{intent=...}                # By intent
redis_hits, redis_misses                       # Cache
memory_cache_hits, memory_cache_misses         # Memory cache
aegis_errors_total{error_type=...}             # By type
ragas_context_recall                           # RAGAS metrics
ragas_faithfulness
ragas_context_precision
```

### LLM Operations
```
llm_cost_usd{provider=...}               # By provider
llm_tokens_total{token_type=...}         # By token type
llm_latency_seconds_bucket{provider=...} # By provider
llm_requests_total{provider=...}         # Request count
```

### Data Stores
```
qdrant_connections_active/max           # Qdrant pool
qdrant_points_total                     # Qdrant data
qdrant_memory_used_bytes                # Qdrant memory
neo4j_connections_active/max            # Neo4j pool
neo4j_entities_total                    # Neo4j entities
neo4j_relations_total                   # Neo4j relations
redis_connections_active/max            # Redis pool
redis_memory_used_bytes                 # Redis memory
redis_evictions_total                   # Evictions counter
db_query_latency_seconds_bucket{database=...}
```

### Memory System
```
graphiti_facts_total{layer=..., type=...}      # Fact counters
graphiti_read_latency_seconds_bucket{layer=...}
graphiti_write_latency_seconds_bucket{layer=...}
graphiti_read_ops_total                        # Operation counters
graphiti_write_ops_total
graphiti_memory_bytes_total{layer=...}         # Memory by layer
graphiti_cache_hits{layer=...}                 # Cache metrics
graphiti_cache_misses{layer=...}
```

---

## Grafana Provisioning Configuration

File: `dashboards.yml`

```yaml
apiVersion: 1

providers:
  - name: 'AegisRAG Dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards/aegis
      foldersFromFilesStructure: false
```

**Key Settings:**
- Auto-discovers all JSON files in directory
- Updates every 10 seconds
- Allows UI modifications
- Dashboards not deleted on config removal

---

## Docker Deployment

### docker-compose Integration

```yaml
grafana:
  image: grafana/grafana:latest
  container_name: aegis-grafana
  ports:
    - "3000:3000"
  volumes:
    - ./config/grafana/dashboards.yml:/etc/grafana/provisioning/dashboards/dashboards.yml
    - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards/aegis
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
    - GF_INSTALL_PLUGINS=grafana-piechart-panel,grafana-worldmap-panel
    - GF_PATHS_PROVISIONING=/etc/grafana/provisioning
  depends_on:
    - prometheus
  networks:
    - aegis-network
```

### Mounting Instructions

1. Ensure `config/grafana/dashboards/` contains all 5 JSON files
2. Mount `dashboards.yml` to `/etc/grafana/provisioning/dashboards/dashboards.yml`
3. Mount `dashboards/` to `/etc/grafana/provisioning/dashboards/aegis/`
4. Restart Grafana container

---

## Data Source Configuration

All dashboards use **Prometheus** data source (default name: "Prometheus")

### Prometheus Datasource Setup
```
URL: http://prometheus:9090
Access: Server (default)
Auth: None
```

---

## Customization Guide

### Adding New Panels

1. Open any dashboard in Grafana UI
2. Click "Add panel"
3. Write PromQL query
4. Save dashboard
5. Export JSON to update file:
   - Dashboard → ... → Export → Export for sharing
   - Copy JSON to respective dashboard file

### Modifying Thresholds

Edit JSON file and update `thresholds` section:
```json
"thresholds": {
  "mode": "absolute",
  "steps": [
    {"color": "green", "value": null},
    {"color": "yellow", "value": 500},
    {"color": "red", "value": 1000}
  ]
}
```

### Changing Refresh Rates

Update top-level `refresh` field:
- `5s` - very frequent (high load)
- `10s` - frequent (recommended)
- `30s` - moderate (default for cost dashboards)
- `1m` - light (business metrics)

---

## Troubleshooting

### Dashboard Not Loading
- Verify Prometheus datasource is accessible
- Check Prometheus metrics are being scraped
- Ensure JSON files are valid (validate with `python3 -m json.tool`)

### Metrics Not Showing
- Verify Prometheus is running: `curl http://prometheus:9090/api/v1/query?query=up`
- Check specific metric: `curl 'http://prometheus:9090/api/v1/query?query=aegis_queries_total'`
- Verify metric labels in PromQL queries match actual metrics

### Performance Issues
- Reduce refresh rate (increase interval)
- Reduce time range
- Add metric filters to queries
- Archive old dashboards to separate folder

---

## Performance Metrics & SLOs

### Executive Dashboard
- **Availability:** 99.5% uptime
- **P50 Latency:** < 200ms
- **Cost Tracking:** Accurate to within 1 hour

### RAG Pipeline
- **Stage Latency:** See performance targets above
- **Success Rate:** > 99%
- **Cache Hit Rate:** > 75%

### LLM Operations
- **Cost Accuracy:** Real-time tracking
- **Provider Failover:** Automatic within 5 minutes
- **Token Tracking:** Accurate to +/- 0.1%

### Data Stores
- **Connection Pool Health:** Always < 85% saturation
- **Query Latency:** P95 < 100ms per database
- **Memory Health:** Always < 80% of max

### Memory System
- **Layer Capacity:** Never exceed max limits
- **Read Performance:** P95 < 50ms
- **Write Performance:** P95 < 100ms
- **Cache Hit Rate:** > 75%

---

## Dashboard Navigation

**Suggested Workflow:**

1. **Start:** Executive Overview (high-level health check)
2. **Investigate Issues:** RAG Pipeline (if latency high) or Data Stores (if errors)
3. **Optimize Costs:** LLM Operations (if budget exceeded)
4. **Debug Memory:** Memory System (if recalls/latency degraded)

---

## Future Enhancements (Sprint 98+)

- [ ] Alerts dashboard (critical thresholds)
- [ ] Comparative analysis (A/B testing metrics)
- [ ] Historical trending (monthly/quarterly reports)
- [ ] Custom annotation markers (deployments, incidents)
- [ ] Drill-down analytics (per-namespace, per-intent)
- [ ] SLO dashboards (vs targets)
- [ ] ML model performance (by model type)

---

## Sprint History

**Sprint 97:** Initial dashboard suite created
- 5 production dashboards
- 68 panels total
- Full Prometheus integration
- All JSON validated

---

## Support & Questions

For dashboard issues or improvements, file tickets with:
- Dashboard name and UID
- Screenshot of issue
- PromQL query that's failing (if applicable)
- Time period when issue occurred
