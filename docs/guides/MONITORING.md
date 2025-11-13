# AEGIS RAG Monitoring Guide

**Sprint 24 - Feature 24.1: Prometheus Metrics Implementation (LLM metrics)**
**Sprint 25 - Feature 25.1: Extended Metrics (System metrics)**
**Related ADR:** ADR-033 (Multi-Cloud LLM Execution)
**Last Updated:** 2025-11-13

This guide covers monitoring LLM cost tracking, performance metrics, system health, and observability for the AEGIS RAG system using Prometheus and Grafana.

---

## Table of Contents

1. [Overview](#overview)
2. [Metrics Exported](#metrics-exported)
3. [Setup Instructions](#setup-instructions)
4. [Grafana Dashboard](#grafana-dashboard)
5. [Alert Configuration](#alert-configuration)
6. [Querying Metrics](#querying-metrics)
7. [Troubleshooting](#troubleshooting)

---

## Overview

AEGIS RAG exports Prometheus metrics for:
- **LLM Usage Tracking**: Requests, tokens, latency per provider
- **Cost Monitoring**: Real-time cost tracking with budget alerts
- **Performance**: Latency histograms (P50, P95, P99)
- **Error Tracking**: Error counts by provider and type

### Architecture

```
AegisLLMProxy → Prometheus Metrics → Prometheus Server → Grafana Dashboard
                     ↓
                SQLite Cost Tracker (persistent storage)
```

---

## Metrics Exported

All metrics are available at `http://localhost:8000/metrics` (Prometheus format).

### 1. Request Metrics

**`llm_requests_total`** (Counter)
- **Description**: Total number of LLM requests
- **Labels**: `provider`, `task_type`, `model`
- **Example**:
  ```
  llm_requests_total{provider="alibaba_cloud",task_type="extraction",model="qwen-plus"} 1234
  ```

### 2. Latency Metrics

**`llm_latency_seconds`** (Histogram)
- **Description**: LLM request latency distribution
- **Labels**: `provider`, `task_type`
- **Buckets**: 0.1s, 0.5s, 1s, 2s, 5s, 10s, 30s, 60s, +Inf
- **Example**:
  ```
  llm_latency_seconds_bucket{provider="local_ollama",task_type="generation",le="1.0"} 892
  ```

### 3. Cost Metrics

**`llm_cost_usd`** (Counter)
- **Description**: Total LLM cost in USD (cumulative)
- **Labels**: `provider`
- **Example**:
  ```
  llm_cost_usd{provider="alibaba_cloud"} 12.34
  llm_cost_usd{provider="openai"} 56.78
  ```

### 4. Token Metrics

**`llm_tokens_used`** (Counter)
- **Description**: Total tokens processed
- **Labels**: `provider`, `token_type` (input, output, total)
- **Example**:
  ```
  llm_tokens_used{provider="alibaba_cloud",token_type="input"} 123456
  llm_tokens_used{provider="alibaba_cloud",token_type="output"} 45678
  ```

### 5. Error Metrics

**`llm_errors_total`** (Counter)
- **Description**: Total number of LLM errors
- **Labels**: `provider`, `task_type`, `error_type`
- **Example**:
  ```
  llm_errors_total{provider="openai",task_type="generation",error_type="timeout"} 12
  ```

### 6. Budget Metrics (Gauges)

**`monthly_budget_remaining_usd`**
- **Description**: Monthly budget remaining in USD
- **Labels**: `provider`
- **Example**:
  ```
  monthly_budget_remaining_usd{provider="alibaba_cloud"} 7.65
  monthly_budget_remaining_usd{provider="openai"} 13.22
  ```

**`monthly_spend_usd`**
- **Description**: Total spend for current month in USD
- **Labels**: `provider`
- **Example**:
  ```
  monthly_spend_usd{provider="alibaba_cloud"} 2.35
  monthly_spend_usd{provider="openai"} 6.78
  ```

### 7. System Metrics (Sprint 25 - Feature 25.1)

**`qdrant_points_count`** (Gauge)
- **Description**: Number of points in Qdrant vector database collections
- **Labels**: `collection`
- **Example**:
  ```
  qdrant_points_count{collection="documents"} 15420
  ```

**`neo4j_entities_count`** (Gauge)
- **Description**: Number of entities in Neo4j knowledge graph
- **Example**:
  ```
  neo4j_entities_count 542
  ```

**`neo4j_relations_count`** (Gauge)
- **Description**: Number of relationships in Neo4j knowledge graph
- **Example**:
  ```
  neo4j_relations_count 1834
  ```

---

## Setup Instructions

### Prerequisites

- Docker Compose (for Prometheus + Grafana)
- AEGIS RAG API running on `http://localhost:8000`

### 1. Start Monitoring Stack

```bash
# From project root
docker compose up -d prometheus grafana
```

**Services:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

### 2. Configure Prometheus

Edit `config/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'aegis-rag-api'
    static_configs:
      - targets: ['host.docker.internal:8000']  # Windows/Mac Docker
    metrics_path: '/metrics'
```

**Note for Linux:** Replace `host.docker.internal` with `172.17.0.1` (Docker bridge IP).

### 3. Verify Metrics Scraping

1. Open Prometheus UI: http://localhost:9090
2. Go to **Status → Targets**
3. Verify `aegis-rag-api` target is **UP**

**Test query:**
```promql
sum(increase(llm_requests_total[1h]))
```

---

## Grafana Dashboard

### Import Dashboard

1. Open Grafana: http://localhost:3000 (admin/admin)
2. Go to **Dashboards → Import**
3. Upload `dashboards/grafana/llm_monitoring.json` (Sprint 25 - Feature 25.1)
4. Select **Prometheus** as data source
5. Click **Import**

**Note:** For Sprint 24 legacy dashboard, use `config/grafana/llm_cost_dashboard.json`

### Dashboard Panels

**Top Row - Summary Stats (24h):**
- Total Requests
- Total Cost
- Total Tokens
- P95 Latency

**Middle Row - Time Series:**
- Request Rate by Provider
- Cost by Provider (Hourly)
- Latency by Provider (P50/P95/P99)
- Token Usage by Provider

**Bottom Row - Distributions:**
- Request Distribution by Task Type (Pie Chart)
- Cost Distribution by Provider (Donut Chart)
- Monthly Budget Status (Gauge)

**Error Analysis:**
- Error Summary by Provider (Table)
- Monthly Spending Trend (Time Series)

### Template Variables

- **Provider**: Filter by provider (local_ollama, alibaba_cloud, openai)
- **Task Type**: Filter by task (extraction, generation, vision, etc.)

---

## Alert Configuration

### 1. High Cost Alert

Create alert in Grafana or Prometheus Alertmanager:

```yaml
# config/prometheus_alerts.yml
groups:
  - name: llm_cost_alerts
    interval: 1m
    rules:
      - alert: HighHourlyCost
        expr: sum(increase(llm_cost_usd[1h])) > 5.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High LLM cost detected"
          description: "Hourly cost exceeded $5.00: {{ $value | humanize }}USD"

      - alert: BudgetExceeded
        expr: monthly_budget_remaining_usd <= 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Monthly budget exceeded for {{ $labels.provider }}"
          description: "Budget remaining: {{ $value | humanize }}USD"
```

### 2. High Latency Alert

```yaml
      - alert: HighP95Latency
        expr: histogram_quantile(0.95, sum(rate(llm_latency_seconds_bucket[5m])) by (provider, le)) > 5.0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High P95 latency for {{ $labels.provider }}"
          description: "P95 latency: {{ $value | humanize }}s"
```

### 3. High Error Rate Alert

```yaml
      - alert: HighErrorRate
        expr: sum(rate(llm_errors_total[5m])) by (provider) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate for {{ $labels.provider }}"
          description: "Error rate: {{ $value | humanize }} errors/sec"
```

### Load Alerts

```bash
# Reload Prometheus config
curl -X POST http://localhost:9090/-/reload
```

---

## Querying Metrics

### Useful Prometheus Queries

**1. Request Rate by Provider (last 5 minutes)**
```promql
sum(rate(llm_requests_total[5m])) by (provider)
```

**2. Total Cost (last 24 hours)**
```promql
sum(increase(llm_cost_usd[24h]))
```

**3. P95 Latency by Provider**
```promql
histogram_quantile(0.95, sum(rate(llm_latency_seconds_bucket[5m])) by (provider, le))
```

**4. Token Usage by Task Type**
```promql
sum(rate(llm_tokens_used{token_type="total"}[5m])) by (task_type)
```

**5. Cost per Request (average)**
```promql
sum(increase(llm_cost_usd[1h])) / sum(increase(llm_requests_total[1h]))
```

**6. Error Rate by Provider**
```promql
sum(rate(llm_errors_total[5m])) by (provider, error_type)
```

**7. Budget Utilization Percentage**
```promql
100 * (1 - (monthly_budget_remaining_usd / (monthly_spend_usd + monthly_budget_remaining_usd)))
```

**8. Total Qdrant Points (Sprint 25)**
```promql
sum(qdrant_points_count)
```

**9. Knowledge Graph Size (Sprint 25)**
```promql
neo4j_entities_count + neo4j_relations_count
```

**10. Entity-to-Relationship Ratio (Sprint 25)**
```promql
neo4j_relations_count / neo4j_entities_count
```

---

## Troubleshooting

### Issue: Metrics Not Appearing

**Check 1: Verify /metrics endpoint**
```bash
curl http://localhost:8000/metrics
```

**Expected output:**
```
# HELP llm_requests_total Total number of LLM requests
# TYPE llm_requests_total counter
llm_requests_total{provider="local_ollama",task_type="generation",model="gemma-3-4b-it"} 42.0
...
```

**Check 2: Verify Prometheus target**
1. Open http://localhost:9090/targets
2. Ensure `aegis-rag-api` target is **UP**
3. If **DOWN**, check network connectivity

**Check 3: Check logs**
```bash
# API logs
docker compose logs api | grep metrics

# Prometheus logs
docker compose logs prometheus
```

### Issue: Budget Metrics Not Updating

Budget metrics (`monthly_budget_remaining_usd`, `monthly_spend_usd`) are **gauges** updated on each LLM request.

**Verify:**
1. Make an LLM request via API
2. Check SQLite database:
   ```bash
   sqlite3 data/cost_tracking.db "SELECT * FROM llm_requests ORDER BY id DESC LIMIT 5;"
   ```
3. Verify metrics:
   ```bash
   curl http://localhost:8000/metrics | grep monthly_
   ```

### Issue: Grafana Dashboard Not Loading

**Check data source:**
1. Grafana → Configuration → Data Sources
2. Verify Prometheus URL: `http://prometheus:9090` (Docker) or `http://localhost:9090` (host)
3. Click **Test** → Should show "Data source is working"

**Check query syntax:**
- Open Panel Editor → Query Inspector
- Verify PromQL syntax
- Check time range (some queries use `[24h]`)

### Issue: High Latency Alerts Triggering

**Investigate:**
```promql
# Check which provider is slow
histogram_quantile(0.95, sum(rate(llm_latency_seconds_bucket[5m])) by (provider, le))

# Check by task type
histogram_quantile(0.95, sum(rate(llm_latency_seconds_bucket[5m])) by (task_type, le))
```

**Mitigation:**
1. Check provider status (Ollama, Alibaba Cloud, OpenAI)
2. Review routing logic in `aegis_llm_proxy.py`
3. Consider adjusting task complexity thresholds

---

## Best Practices

### 1. Regular Monitoring
- Check Grafana dashboard daily
- Set up email/Slack alerts for critical issues
- Review monthly cost reports

### 2. Cost Optimization
- Monitor cost distribution by provider (pie chart)
- Identify high-cost task types
- Adjust routing logic to prefer local when possible

### 3. Performance Tuning
- Track P95 latency by provider
- Identify slow task types
- Optimize prompts to reduce token usage

### 4. Budget Management
- Set conservative monthly budgets initially
- Monitor spending trends (monthly_spend_usd)
- Adjust budgets based on usage patterns

### 5. Data Retention
- SQLite database: Automatic (persistent)
- Prometheus: Default 15 days (adjust `--storage.tsdb.retention.time`)
- Grafana: Uses Prometheus data (no additional retention)

---

## Further Reading

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [AEGIS RAG Cost Tracker](../../src/components/llm_proxy/cost_tracker.py)
- [AEGIS RAG Metrics Module](../../src/core/metrics.py)

---

## Support

**Issues:** https://github.com/aegis-rag/aegis-rag/issues
**Documentation:** https://docs.aegis-rag.com
**Community:** Discord/Slack Channel
