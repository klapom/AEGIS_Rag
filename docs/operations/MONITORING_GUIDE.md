# Prometheus & Grafana Monitoring Guide

**AegisRAG Production Monitoring Stack**
**Last Updated:** 2025-11-16 (Sprint 28)

---

## Overview

AegisRAG uses **Prometheus** for metrics collection and **Grafana** for visualization. This guide covers setup, verification, and dashboard usage for production monitoring.

**Stack Components:**
- **Prometheus 2.45+**: Time-series metrics database
- **Grafana 10.0+**: Visualization and alerting
- **Node Exporter**: System metrics (CPU, memory, disk)
- **FastAPI App Metrics**: Custom application metrics via `/metrics` endpoint

---

## Quick Start (Docker Compose)

### 1. Start Monitoring Stack

```bash
# Start all services (app + monitoring)
docker-compose up -d

# Verify services are running
docker-compose ps

# Expected output:
# NAME                  STATUS              PORTS
# aegis-rag-api         Up                  0.0.0.0:8000->8000/tcp
# prometheus            Up                  0.0.0.0:9090->9090/tcp
# grafana               Up                  0.0.0.0:3000->3000/tcp
# node-exporter         Up                  0.0.0.0:9100->9100/tcp
# qdrant                Up                  0.0.0.0:6333->6333/tcp
# neo4j                 Up                  0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
# redis                 Up                  0.0.0.0:6379->6379/tcp
```

### 2. Access UIs

**Prometheus:**
- URL: http://localhost:9090
- Status: http://localhost:9090/targets (check target health)

**Grafana:**
- URL: http://localhost:3000
- Default Login: `admin` / `admin` (change on first login)
- Datasource: Prometheus (pre-configured at http://prometheus:9090)

**Application Metrics:**
- URL: http://localhost:8000/metrics (raw Prometheus metrics)
- Health: http://localhost:8000/health (API health check)

---

## Prometheus Configuration

### Configuration File

**Location:** `config/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s      # Scrape metrics every 15 seconds
  evaluation_interval: 15s  # Evaluate rules every 15 seconds
  external_labels:
    environment: 'production'
    project: 'aegis-rag'

# Scrape configurations
scrape_configs:
  # AegisRAG FastAPI application
  - job_name: 'aegis-rag-api'
    static_configs:
      - targets: ['aegis-rag-api:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node Exporter (system metrics)
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  # Qdrant (if metrics enabled)
  - job_name: 'qdrant'
    static_configs:
      - targets: ['qdrant:6333']
    metrics_path: '/metrics'

  # Neo4j (if metrics plugin enabled)
  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:2004']
```

### Verify Prometheus Targets

1. Open http://localhost:9090/targets
2. Check **all targets are UP** (green status):
   - `aegis-rag-api:8000` → FastAPI metrics
   - `prometheus:9090` → Prometheus self-metrics
   - `node-exporter:9100` → System metrics
   - `qdrant:6333` → Vector DB metrics (optional)
   - `neo4j:2004` → Graph DB metrics (optional)

**Troubleshooting:**
- **Target DOWN:** Check container is running (`docker-compose ps`)
- **Connection refused:** Check firewall/network settings
- **No metrics:** Verify endpoint responds (`curl http://localhost:8000/metrics`)

---

## Grafana Setup

### Initial Configuration

**Step 1: Login**
```
URL: http://localhost:3000
Username: admin
Password: admin (change on first login)
```

**Step 2: Add Prometheus Datasource**
1. Navigate: **Configuration** → **Data Sources** → **Add data source**
2. Select: **Prometheus**
3. Configure:
   - **Name:** Prometheus
   - **URL:** `http://prometheus:9090` (Docker network)
   - **Access:** Server (default)
4. Click **Save & Test** (should show green checkmark)

**Step 3: Import Dashboard**
```bash
# Dashboard JSON location
config/grafana/dashboards/aegis-rag-dashboard.json
```

**Import Steps:**
1. Navigate: **Dashboards** → **Import**
2. Upload JSON file OR paste JSON content
3. Select datasource: **Prometheus**
4. Click **Import**

---

## Key Metrics

### Application Metrics

**Request Metrics:**
```promql
# Request rate (queries per second)
rate(http_request_total[1m])

# Request duration (p50, p95, p99)
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# Error rate (4xx, 5xx)
rate(http_request_total{status=~"4..|5.."}[1m])
```

**LLM Metrics:**
```promql
# LLM requests per minute
rate(llm_request_total[1m]) * 60

# LLM token usage (input + output)
rate(llm_tokens_total[5m])

# LLM cost (USD per hour)
rate(llm_cost_dollars_total[1h]) * 3600

# LLM latency by provider
histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[5m]))
```

**Retrieval Metrics:**
```promql
# Retrieval operations per minute
rate(retrieval_operation_total[1m]) * 60

# Retrieval latency (p95)
histogram_quantile(0.95, rate(retrieval_duration_seconds_bucket[5m]))

# Cache hit rate
rate(memory_cache_hits_total[5m]) / (rate(memory_cache_hits_total[5m]) + rate(memory_cache_misses_total[5m]))
```

**Memory Metrics (3-Layer Architecture):**
```promql
# Redis (Short-Term Memory)
redis_memory_usage_bytes

# Qdrant (Semantic Memory)
qdrant_capacity_ratio        # 0.0 to 1.0 (0.8 = 80% full)
qdrant_total_entries

# Graphiti (Episodic Memory)
graphiti_capacity_ratio
graphiti_episode_count
```

### System Metrics

**CPU:**
```promql
# CPU usage per core
rate(node_cpu_seconds_total{mode!="idle"}[5m])

# Overall CPU usage
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

**Memory:**
```promql
# Memory usage (percentage)
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100

# Memory available (GB)
node_memory_MemAvailable_bytes / 1024 / 1024 / 1024
```

**Disk:**
```promql
# Disk usage (percentage)
(node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100

# Disk I/O rate
rate(node_disk_read_bytes_total[5m])
rate(node_disk_written_bytes_total[5m])
```

---

## Dashboard Panels

### Recommended Grafana Dashboard Layout

**Row 1: Overview (4 panels)**
- Requests/sec (Stat panel)
- Error rate % (Stat panel)
- P95 latency (Stat panel)
- Active connections (Stat panel)

**Row 2: Request Metrics (2 panels)**
- Request rate over time (Time series)
- Request duration (p50, p95, p99) (Time series)

**Row 3: LLM Metrics (3 panels)**
- LLM requests/min by provider (Time series)
- Token usage (input vs output) (Time series)
- LLM cost per hour (Stat panel with trend)

**Row 4: Retrieval Metrics (2 panels)**
- Retrieval latency by operation (Time series)
- Cache hit rate (Time series)

**Row 5: Memory Architecture (3 panels)**
- Redis memory usage (Gauge)
- Qdrant capacity (Gauge, 0-100%)
- Graphiti episode count (Stat panel)

**Row 6: System Metrics (3 panels)**
- CPU usage % (Time series)
- Memory usage % (Time series)
- Disk I/O (Time series)

---

## Alerting Rules

### Prometheus Alerts

**Location:** `config/prometheus/alerts.yml`

```yaml
groups:
  - name: aegis-rag-alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(http_request_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High 5xx error rate ({{ $value }}/sec)"
          description: "API is returning more than 5% errors"

      # High latency
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High p95 latency ({{ $value }}s)"
          description: "API p95 latency above 1 second"

      # Low cache hit rate
      - alert: LowCacheHitRate
        expr: rate(memory_cache_hits_total[5m]) / (rate(memory_cache_hits_total[5m]) + rate(memory_cache_misses_total[5m])) < 0.6
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate ({{ $value | humanizePercentage }})"
          description: "Memory cache hit rate below 60%"

      # High LLM cost
      - alert: HighLLMCost
        expr: rate(llm_cost_dollars_total[1h]) * 3600 > 5.0
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "High LLM cost ({{ $value }}/hour)"
          description: "LLM API costs exceeding $5/hour"

      # Qdrant capacity high
      - alert: QdrantCapacityHigh
        expr: qdrant_capacity_ratio > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Qdrant capacity at {{ $value | humanizePercentage }}"
          description: "Vector database nearing capacity limit"

      # Service down
      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "Service has been unavailable for 2 minutes"
```

### Grafana Alerts

**Configure in Grafana UI:**
1. Navigate: **Alerting** → **Alert rules**
2. Click **New alert rule**
3. Define query, threshold, and notification channel
4. Example: Email notification for critical alerts

---

## Health Checks

### Application Health Endpoints

**Main Health Check:**
```bash
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-11-16T10:30:00Z",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "cache": "healthy",
    "llm_proxy": "healthy"
  }
}
```

**Memory Health (3-Layer Architecture):**
```bash
curl http://localhost:8000/health/memory

# Expected response:
{
  "redis": {
    "status": "healthy",
    "used_memory_mb": 128.5,
    "capacity": 0.12
  },
  "qdrant": {
    "status": "healthy",
    "collections": 3,
    "vectors": 450000,
    "capacity": 0.045
  },
  "graphiti": {
    "status": "healthy",
    "episodes": 1250,
    "capacity": 0.0125
  }
}
```

**Component Health:**
```bash
# Neo4j health
curl http://localhost:7474/db/neo4j/tx/commit

# Qdrant health
curl http://localhost:6333/healthz

# Redis ping
redis-cli -h localhost -p 6379 PING
```

---

## Troubleshooting

### Prometheus Issues

**Problem:** Prometheus targets showing DOWN
- **Check:** `docker-compose logs prometheus`
- **Solution:** Restart Prometheus: `docker-compose restart prometheus`

**Problem:** Metrics not appearing in Prometheus
- **Check:** Query `up{job="aegis-rag-api"}` in Prometheus UI
- **Solution:** Verify `/metrics` endpoint: `curl http://localhost:8000/metrics`

### Grafana Issues

**Problem:** Datasource connection failed
- **Check:** Grafana logs: `docker-compose logs grafana`
- **Solution:** Verify Prometheus URL is `http://prometheus:9090` (not localhost)

**Problem:** Dashboard shows "No data"
- **Check:** Prometheus has data for time range
- **Solution:** Adjust time range picker (top-right) to "Last 15 minutes"

### Performance Issues

**Problem:** High memory usage in Prometheus
- **Solution:** Reduce retention period: `--storage.tsdb.retention.time=15d`

**Problem:** Slow Grafana queries
- **Solution:** Reduce scrape interval in `prometheus.yml` or add aggregation

---

## Production Best Practices

### Security

1. **Authentication:**
   - Change default Grafana password immediately
   - Enable Prometheus basic auth in production
   - Use HTTPS for external access (nginx/traefik)

2. **Network Isolation:**
   - Prometheus/Grafana on internal network only
   - Expose via reverse proxy with authentication
   - Firewall rules: Only allow internal access

### Retention

```yaml
# Prometheus retention (prometheus.yml)
global:
  storage.tsdb.retention.time: 30d   # Keep 30 days of metrics
  storage.tsdb.retention.size: 50GB  # Max 50GB storage
```

### Backup

```bash
# Backup Prometheus data
tar -czf prometheus-backup-$(date +%Y%m%d).tar.gz -C /var/lib/prometheus .

# Backup Grafana dashboards
curl -X GET http://admin:admin@localhost:3000/api/dashboards/db/aegis-rag-dashboard > dashboard-backup.json
```

### Scaling

**High Cardinality Issues:**
- Avoid labels with high variability (user IDs, request IDs)
- Use aggregation for high-frequency metrics
- Consider Thanos or Cortex for long-term storage

**Multiple Instances:**
- Use service discovery (Kubernetes, Consul)
- Configure scrape targets dynamically
- Add load balancer metrics

---

## Useful Queries

### Performance Analysis

```promql
# Top 10 slowest endpoints
topk(10, histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])))

# Error rate by endpoint
sum(rate(http_request_total{status=~"5.."}[5m])) by (path)

# LLM provider comparison (latency)
histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[5m])) by (provider)

# Cache efficiency by operation
rate(memory_cache_hits_total[5m]) / (rate(memory_cache_hits_total[5m]) + rate(memory_cache_misses_total[5m])) by (operation)
```

### Capacity Planning

```promql
# Qdrant growth rate (vectors/day)
increase(qdrant_total_entries[24h])

# Redis memory growth (MB/hour)
increase(redis_memory_usage_bytes[1h]) / 1024 / 1024

# Disk space remaining (days)
(node_filesystem_free_bytes / deriv(node_filesystem_free_bytes[1d])) / 86400
```

---

## References

- **Prometheus Documentation:** https://prometheus.io/docs/
- **Grafana Documentation:** https://grafana.com/docs/
- **FastAPI Metrics:** https://github.com/trallnag/prometheus-fastapi-instrumentator
- **AegisRAG Metrics:** `src/core/metrics.py`, `src/monitoring/metrics.py`

---

**Last Updated:** 2025-11-16 (Sprint 28)
**Maintainer:** Klaus Pommer
**Support:** See TROUBLESHOOTING.md for common issues
