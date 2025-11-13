# Metrics and Monitoring API Endpoints

**Version:** 1.0.0 (Sprint 24)
**Status:** Planned (implementation in progress)
**Base URL:** `http://localhost:8000/api/v1`

---

## Table of Contents

1. [Overview](#overview)
2. [Health Check Endpoint](#health-check-endpoint)
3. [Cost Tracking Endpoints](#cost-tracking-endpoints)
4. [Prometheus Metrics Endpoint](#prometheus-metrics-endpoint)
5. [System Metrics](#system-metrics)
6. [Error Responses](#error-responses)

---

## Overview

AegisRAG provides comprehensive monitoring and metrics endpoints for production observability:

- **Health Checks:** Service health and readiness
- **Cost Tracking:** Multi-cloud LLM usage and budget monitoring
- **Prometheus Metrics:** Time-series metrics for alerting and dashboards
- **System Metrics:** GPU, memory, and database statistics

---

## Health Check Endpoint

### GET /health

**Description:** Returns overall system health status.

**Authentication:** None

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2025-11-13T14:30:00Z",
  "version": "0.23.0",
  "services": {
    "ollama": {
      "status": "ok",
      "latency_ms": 45,
      "models_loaded": ["gemma-3-4b-it-Q8_0", "llama3.2:8b"]
    },
    "qdrant": {
      "status": "ok",
      "latency_ms": 12,
      "collections": 1,
      "vectors_count": 150000
    },
    "neo4j": {
      "status": "ok",
      "latency_ms": 23,
      "nodes_count": 5432,
      "relationships_count": 12876
    },
    "redis": {
      "status": "ok",
      "latency_ms": 3,
      "memory_used_mb": 256
    },
    "alibaba_cloud": {
      "status": "ok",
      "latency_ms": 340
    }
  },
  "gpu": {
    "available": true,
    "utilization_pct": 52.7,
    "memory_used_gb": 6.4,
    "memory_total_gb": 12.0,
    "temperature_c": 57
  }
}
```

**Status Codes:**
- `200 OK` - All services healthy
- `503 Service Unavailable` - One or more critical services down

**Example Request:**

```bash
curl http://localhost:8000/health
```

**Example Response (Degraded):**

```json
{
  "status": "degraded",
  "timestamp": "2025-11-13T14:30:00Z",
  "version": "0.23.0",
  "services": {
    "ollama": {
      "status": "error",
      "error": "Connection refused",
      "latency_ms": null
    },
    "qdrant": {
      "status": "ok",
      "latency_ms": 12
    },
    "neo4j": {
      "status": "ok",
      "latency_ms": 23
    },
    "redis": {
      "status": "ok",
      "latency_ms": 3
    }
  }
}
```

---

## Cost Tracking Endpoints

### GET /api/v1/cost/budget-status

**Description:** Get current budget utilization for all providers.

**Authentication:** Required (JWT token)

**Query Parameters:** None

**Response:**

```json
{
  "providers": {
    "alibaba_cloud": {
      "monthly_limit_usd": 120.0,
      "current_spend_usd": 3.47,
      "utilization_pct": 2.89,
      "remaining_usd": 116.53,
      "requests_count": 147,
      "status": "ok"
    },
    "openai": {
      "monthly_limit_usd": 80.0,
      "current_spend_usd": 0.0,
      "utilization_pct": 0.0,
      "remaining_usd": 80.0,
      "requests_count": 0,
      "status": "ok"
    },
    "local_ollama": {
      "monthly_limit_usd": null,
      "current_spend_usd": 0.0,
      "utilization_pct": 0.0,
      "remaining_usd": null,
      "requests_count": 8523,
      "status": "ok"
    }
  },
  "total": {
    "monthly_limit_usd": 200.0,
    "current_spend_usd": 3.47,
    "utilization_pct": 1.74,
    "remaining_usd": 196.53,
    "requests_count": 8670
  },
  "period": {
    "month": "2025-11",
    "days_elapsed": 13,
    "days_remaining": 17,
    "projected_spend_usd": 8.03
  }
}
```

**Status Codes:**
- `200 OK` - Budget status returned
- `401 Unauthorized` - Missing or invalid authentication
- `500 Internal Server Error` - Database error

**Example Request:**

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/api/v1/cost/budget-status
```

---

### GET /api/v1/cost/usage

**Description:** Get detailed LLM usage statistics.

**Authentication:** Required (JWT token)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `period` | string | No | "month" | Time period: "day", "week", "month", "year" |
| `provider` | string | No | null | Filter by provider: "alibaba_cloud", "openai", "local_ollama" |
| `task_type` | string | No | null | Filter by task type: "extraction", "generation", "embedding", "vlm" |
| `start_date` | string | No | null | Start date (ISO 8601): "2025-11-01" |
| `end_date` | string | No | null | End date (ISO 8601): "2025-11-30" |

**Response:**

```json
{
  "usage_summary": {
    "total_requests": 147,
    "total_cost_usd": 3.47,
    "total_tokens": 1250000,
    "total_tokens_input": 625000,
    "total_tokens_output": 625000,
    "average_latency_ms": 845,
    "average_cost_per_request": 0.024
  },
  "by_provider": [
    {
      "provider": "alibaba_cloud",
      "requests": 147,
      "cost_usd": 3.47,
      "tokens": 1250000,
      "average_latency_ms": 845,
      "cost_per_1k_tokens": 0.003
    }
  ],
  "by_task_type": [
    {
      "task_type": "vlm",
      "requests": 47,
      "cost_usd": 2.15,
      "tokens": 750000,
      "average_latency_ms": 1820
    },
    {
      "task_type": "generation",
      "requests": 100,
      "cost_usd": 1.32,
      "tokens": 500000,
      "average_latency_ms": 450
    }
  ],
  "by_model": [
    {
      "model": "qwen3-vl-30b-a3b-instruct",
      "requests": 47,
      "cost_usd": 2.15,
      "tokens": 750000
    },
    {
      "model": "qwen-turbo",
      "requests": 100,
      "cost_usd": 1.32,
      "tokens": 500000
    }
  ],
  "period": {
    "start_date": "2025-11-01",
    "end_date": "2025-11-13",
    "days": 13
  }
}
```

**Status Codes:**
- `200 OK` - Usage data returned
- `400 Bad Request` - Invalid query parameters
- `401 Unauthorized` - Missing or invalid authentication
- `500 Internal Server Error` - Database error

**Example Request:**

```bash
# Get monthly usage
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/cost/usage?period=month"

# Get usage for specific provider
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/cost/usage?provider=alibaba_cloud"

# Get usage for date range
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/cost/usage?start_date=2025-11-01&end_date=2025-11-13"
```

---

### GET /api/v1/cost/export

**Description:** Export cost data to CSV or JSON format.

**Authentication:** Required (JWT token)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `format` | string | No | "csv" | Export format: "csv", "json" |
| `start_date` | string | No | null | Start date (ISO 8601) |
| `end_date` | string | No | null | End date (ISO 8601) |

**Response (CSV):**

```csv
timestamp,provider,model,task_type,tokens_input,tokens_output,cost_usd,latency_ms
2025-11-13T10:30:00Z,alibaba_cloud,qwen3-vl-30b-a3b-instruct,vlm,15000,8000,0.069,1820
2025-11-13T10:31:00Z,alibaba_cloud,qwen-turbo,generation,500,800,0.013,450
```

**Response (JSON):**

```json
{
  "export_date": "2025-11-13T14:30:00Z",
  "period": {
    "start_date": "2025-11-01",
    "end_date": "2025-11-13"
  },
  "records": [
    {
      "timestamp": "2025-11-13T10:30:00Z",
      "provider": "alibaba_cloud",
      "model": "qwen3-vl-30b-a3b-instruct",
      "task_type": "vlm",
      "tokens_input": 15000,
      "tokens_output": 8000,
      "cost_usd": 0.069,
      "latency_ms": 1820
    },
    {
      "timestamp": "2025-11-13T10:31:00Z",
      "provider": "alibaba_cloud",
      "model": "qwen-turbo",
      "task_type": "generation",
      "tokens_input": 500,
      "tokens_output": 800,
      "cost_usd": 0.013,
      "latency_ms": 450
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Export data returned
- `400 Bad Request` - Invalid query parameters
- `401 Unauthorized` - Missing or invalid authentication
- `500 Internal Server Error` - Database error

**Example Request:**

```bash
# Export to CSV
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/cost/export?format=csv" \
  > monthly_costs.csv

# Export to JSON
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/v1/cost/export?format=json" \
  > monthly_costs.json
```

---

## Prometheus Metrics Endpoint

### GET /metrics

**Description:** Prometheus-compatible metrics endpoint for scraping.

**Authentication:** None (internal network only)

**Response Format:** Prometheus text exposition format

**Response Example:**

```prometheus
# HELP aegis_rag_requests_total Total number of RAG requests
# TYPE aegis_rag_requests_total counter
aegis_rag_requests_total{strategy="simple"} 5234
aegis_rag_requests_total{strategy="advanced"} 1823
aegis_rag_requests_total{strategy="hybrid"} 3245

# HELP aegis_rag_request_latency_seconds Request latency in seconds
# TYPE aegis_rag_request_latency_seconds histogram
aegis_rag_request_latency_seconds_bucket{strategy="simple",le="0.1"} 3420
aegis_rag_request_latency_seconds_bucket{strategy="simple",le="0.5"} 5120
aegis_rag_request_latency_seconds_bucket{strategy="simple",le="1.0"} 5230
aegis_rag_request_latency_seconds_bucket{strategy="simple",le="+Inf"} 5234
aegis_rag_request_latency_seconds_sum{strategy="simple"} 892.5
aegis_rag_request_latency_seconds_count{strategy="simple"} 5234

# HELP aegis_llm_requests_total Total LLM requests by provider
# TYPE aegis_llm_requests_total counter
aegis_llm_requests_total{provider="local_ollama",model="gemma-3-4b-it-Q8_0"} 8523
aegis_llm_requests_total{provider="alibaba_cloud",model="qwen-turbo"} 100
aegis_llm_requests_total{provider="alibaba_cloud",model="qwen3-vl-30b-a3b-instruct"} 47

# HELP aegis_llm_cost_usd_total Total LLM cost in USD
# TYPE aegis_llm_cost_usd_total counter
aegis_llm_cost_usd_total{provider="local_ollama"} 0.0
aegis_llm_cost_usd_total{provider="alibaba_cloud"} 3.47

# HELP aegis_llm_latency_seconds LLM request latency in seconds
# TYPE aegis_llm_latency_seconds histogram
aegis_llm_latency_seconds_bucket{provider="alibaba_cloud",le="0.5"} 23
aegis_llm_latency_seconds_bucket{provider="alibaba_cloud",le="1.0"} 98
aegis_llm_latency_seconds_bucket{provider="alibaba_cloud",le="2.0"} 145
aegis_llm_latency_seconds_bucket{provider="alibaba_cloud",le="+Inf"} 147

# HELP aegis_gpu_utilization_pct GPU utilization percentage
# TYPE aegis_gpu_utilization_pct gauge
aegis_gpu_utilization_pct 52.7

# HELP aegis_gpu_memory_used_bytes GPU memory used in bytes
# TYPE aegis_gpu_memory_used_bytes gauge
aegis_gpu_memory_used_bytes 6871947673

# HELP aegis_qdrant_vectors_count Total vectors in Qdrant
# TYPE aegis_qdrant_vectors_count gauge
aegis_qdrant_vectors_count{collection="aegis_documents"} 150000

# HELP aegis_neo4j_nodes_count Total nodes in Neo4j
# TYPE aegis_neo4j_nodes_count gauge
aegis_neo4j_nodes_count 5432

# HELP aegis_neo4j_relationships_count Total relationships in Neo4j
# TYPE aegis_neo4j_relationships_count gauge
aegis_neo4j_relationships_count 12876
```

**Prometheus Scrape Configuration:**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'aegis-rag'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

**Example Request:**

```bash
curl http://localhost:8000/metrics
```

---

## System Metrics

### GET /api/v1/metrics/system

**Description:** Get detailed system resource metrics.

**Authentication:** Required (JWT token)

**Response:**

```json
{
  "timestamp": "2025-11-13T14:30:00Z",
  "cpu": {
    "cores": 12,
    "usage_pct": 45.3,
    "load_average": [2.1, 2.3, 2.5]
  },
  "memory": {
    "total_gb": 64.0,
    "used_gb": 32.5,
    "available_gb": 31.5,
    "usage_pct": 50.8
  },
  "gpu": {
    "available": true,
    "device_name": "NVIDIA GeForce RTX 3060",
    "utilization_pct": 52.7,
    "memory_used_gb": 6.4,
    "memory_total_gb": 12.0,
    "memory_usage_pct": 53.3,
    "temperature_c": 57,
    "power_draw_w": 115,
    "power_limit_w": 170
  },
  "disk": {
    "total_gb": 500.0,
    "used_gb": 245.3,
    "available_gb": 254.7,
    "usage_pct": 49.1,
    "iops_read": 1234,
    "iops_write": 567
  },
  "network": {
    "throughput_mbps_in": 45.2,
    "throughput_mbps_out": 12.8,
    "connections_active": 127
  }
}
```

**Status Codes:**
- `200 OK` - Metrics returned
- `401 Unauthorized` - Missing or invalid authentication
- `500 Internal Server Error` - System error

**Example Request:**

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8000/api/v1/metrics/system
```

---

## Error Responses

### Error Format

All error responses follow this format:

```json
{
  "error": "Error Title",
  "detail": "Detailed error message",
  "status_code": 400,
  "timestamp": "2025-11-13T14:30:00Z",
  "request_id": "req_abc123xyz"
}
```

### Common Error Codes

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | Bad Request | Invalid query parameters or request body |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Endpoint or resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Service temporarily unavailable |

**Example Error Response:**

```json
{
  "error": "Budget Exceeded",
  "detail": "Monthly budget for alibaba_cloud exceeded (120.0 USD). Fallback to local_ollama.",
  "status_code": 429,
  "timestamp": "2025-11-13T14:30:00Z",
  "request_id": "req_abc123xyz",
  "context": {
    "provider": "alibaba_cloud",
    "current_spend_usd": 120.5,
    "monthly_limit_usd": 120.0
  }
}
```

---

## Grafana Dashboard Integration

### Importing Metrics to Grafana

**Step 1: Configure Prometheus Data Source**

```yaml
# grafana-datasources.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true
```

**Step 2: Create Dashboard Panels**

**Panel 1: LLM Cost Over Time**

```promql
# Query
sum by (provider) (rate(aegis_llm_cost_usd_total[5m]))

# Panel Type: Graph (Time Series)
# Y-axis: USD per minute
# Legend: {{provider}}
```

**Panel 2: Request Latency (p95)**

```promql
# Query
histogram_quantile(0.95, sum(rate(aegis_rag_request_latency_seconds_bucket[5m])) by (le, strategy))

# Panel Type: Graph (Time Series)
# Y-axis: Seconds
# Legend: {{strategy}} (p95)
```

**Panel 3: Budget Utilization**

```promql
# Query
(aegis_llm_cost_usd_total / 120) * 100

# Panel Type: Gauge
# Unit: percent (0-100)
# Thresholds: 80 (yellow), 100 (red)
```

**Panel 4: GPU Utilization**

```promql
# Query
aegis_gpu_utilization_pct

# Panel Type: Gauge
# Unit: percent (0-100)
# Thresholds: 80 (yellow), 95 (red)
```

---

## Rate Limiting

**Current Limits:**
- `/health`: Unlimited (no authentication)
- `/metrics`: Unlimited (internal network only)
- `/api/v1/cost/*`: 60 requests per minute per user

**Rate Limit Headers:**

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1700000000
```

**Rate Limit Exceeded Response:**

```json
{
  "error": "Rate Limit Exceeded",
  "detail": "Maximum 60 requests per minute exceeded. Try again in 30 seconds.",
  "status_code": 429,
  "timestamp": "2025-11-13T14:30:00Z",
  "retry_after": 30
}
```

---

## Security Considerations

### Authentication

**JWT Token Format:**

```bash
# Header
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token Expiration:** 24 hours

**Token Refresh:** Use `/api/v1/auth/refresh` endpoint

### Network Security

**Production Recommendations:**
- `/health` - Public (load balancer health checks)
- `/metrics` - Internal network only (Prometheus scraping)
- `/api/v1/cost/*` - Authenticated users only
- `/api/v1/metrics/system` - Admin users only

**Firewall Rules:**

```bash
# Allow Prometheus scraping from monitoring subnet
iptables -A INPUT -s 10.0.1.0/24 -p tcp --dport 8000 -j ACCEPT

# Block external access to /metrics
iptables -A INPUT -p tcp --dport 8000 -m string --string "GET /metrics" --algo bm -j DROP
```

---

## References

### Documentation

- [Current Architecture](../architecture/CURRENT_ARCHITECTURE.md)
- [Production Deployment Guide](../guides/PRODUCTION_DEPLOYMENT_GUIDE.md)
- [ADR-033: ANY-LLM Integration](../adr/ADR-033-any-llm-integration.md)

### External Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
- [OpenAPI Specification](https://swagger.io/specification/)

---

**Document Metadata:**
- **Created:** 2025-11-13
- **Author:** Documentation Agent (Claude Code)
- **Sprint:** Sprint 24, Feature 24.8
- **Status:** Planned (implementation in progress)

Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
