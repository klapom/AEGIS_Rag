# AegisRAG Monitoring & Cost Tracking Guide - Sprint 30

**Last Updated:** 2025-11-18
**Sprint:** 30 (System Stability & VLM Integration)

---

## Overview

AegisRAG provides comprehensive monitoring and observability across 4 layers:

1. **Progress Tracking** - Real-time indexing progress via SSE
2. **Cost Tracking** - LLM API cost monitoring (SQLite + Prometheus + Grafana)
3. **System Metrics** - Performance metrics (Prometheus + Grafana)
4. **Application Logs** - Structured logging (structlog JSON)

---

## 1. Progress Tracking (VLM Indexing)

### 1.1 Real-Time Progress via SSE (Server-Sent Events)

When you trigger VLM re-indexing via the API or frontend, progress is streamed in real-time.

**API Endpoint:**
```bash
POST /api/v1/admin/reindex_with_vlm?input_dir=<path>&confirm=true
```

**Progress Events (JSON):**
```json
// Event 1: Discovery
{
  "status": "discovery",
  "progress": 0.05,
  "message": "Found 10 documents",
  "total_documents": 10
}

// Event 2: Deletion
{
  "status": "deletion",
  "progress": 0.15,
  "message": "Old indexes deleted"
}

// Event 3: Ingestion (per document)
{
  "status": "ingestion",
  "progress": 0.42,
  "message": "Processed document.pdf",
  "document_id": "abc123",
  "completed_documents": 5,
  "total_documents": 10,
  "batch_progress": 0.5,
  "chunks": 42,
  "vlm_images": 8,
  "errors": 0,
  "success": true
}

// Event 4: Validation
{
  "status": "validation",
  "progress": 0.98,
  "message": "Validating indexes..."
}

// Event 5: Completion
{
  "status": "completed",
  "progress": 1.0,
  "message": "VLM re-indexing completed in 420.5s",
  "total_documents": 10,
  "completed_documents": 10,
  "total_chunks": 420,
  "total_vlm_images": 85,
  "total_errors": 2,
  "qdrant_points": 420,
  "neo4j_entities": 156,
  "neo4j_relations": 234,
  "duration_seconds": 420.5
}
```

### 1.2 Monitoring Progress via curl

**PowerShell:**
```powershell
# Stream progress to console
$dir = "C:\path\to\documents"
curl -N "http://localhost:8000/api/v1/admin/reindex_with_vlm?input_dir=$([Uri]::EscapeDataString($dir))&confirm=true" `
  -H "Accept: text/event-stream"
```

**Output:**
```
data: {"status":"discovery","progress":0.05,"message":"Found 3 documents"}

data: {"status":"ingestion","progress":0.3,"chunks":25,"vlm_images":5}

data: {"status":"completed","progress":1.0,"total_chunks":142}
```

### 1.3 Frontend Progress UI (Admin Dashboard)

**Location:** `http://localhost:5173/admin/indexing`

**Features:**
- Real-time progress bar (0-100%)
- Document-by-document status
- VLM image count
- Chunk statistics
- Error notifications
- Final summary

---

## 2. Cost Tracking (LLM API Costs)

AegisRAG tracks **all** LLM API costs via the `AegisLLMProxy` (Sprint 23-25).

### 2.1 Cost Tracking Architecture

**Components:**
1. **SQLite Database** (`data/cost_tracking.db`)
   - Persistent storage for all LLM calls
   - Tracks: Provider, Model, Tokens, Cost, Timestamp
   - Accessible via SQL queries

2. **Prometheus Metrics** (exposed at `/metrics`)
   - Real-time cost counters
   - Aggregated by provider (Ollama, Alibaba, OpenAI)
   - Budget tracking

3. **Grafana Dashboard** (`http://localhost:3000`)
   - Visual cost analytics
   - Budget alerts
   - Cost trends over time

### 2.2 SQLite Cost Database

**Location:** `data/cost_tracking.db`

**Schema:**
```sql
CREATE TABLE llm_calls (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    provider TEXT,       -- 'ollama', 'alibaba_cloud', 'openai'
    model TEXT,          -- 'llama3.2:3b', 'qwen3-vl-30b-a3b-instruct', etc.
    task_type TEXT,      -- 'query', 'generation', 'extraction', 'vlm'
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd REAL,
    metadata TEXT        -- JSON with additional context
);
```

**Query Examples:**

```powershell
# Install SQLite CLI (if needed)
# winget install SQLite.SQLite

# Open database
sqlite3 data/cost_tracking.db

# Total costs by provider
SELECT provider, SUM(cost_usd) as total_cost
FROM llm_calls
GROUP BY provider;

# VLM costs (Qwen3-VL)
SELECT model, COUNT(*) as calls, SUM(cost_usd) as total_cost
FROM llm_calls
WHERE task_type = 'vlm'
GROUP BY model;

# Costs in last 24 hours
SELECT
  provider,
  model,
  COUNT(*) as calls,
  SUM(total_tokens) as tokens,
  SUM(cost_usd) as cost
FROM llm_calls
WHERE timestamp > datetime('now', '-1 day')
GROUP BY provider, model;

# Top 10 most expensive calls
SELECT
  timestamp,
  provider,
  model,
  task_type,
  total_tokens,
  cost_usd
FROM llm_calls
ORDER BY cost_usd DESC
LIMIT 10;
```

### 2.3 Prometheus Metrics

**Metrics Endpoint:** `http://localhost:8000/metrics`

**Key Metrics:**

```prometheus
# Total LLM API cost (USD)
llm_api_cost_total{provider="ollama"} 0.0
llm_api_cost_total{provider="alibaba_cloud"} 2.45
llm_api_cost_total{provider="openai"} 5.67

# Total API calls
llm_api_calls_total{provider="alibaba_cloud",model="qwen3-vl-30b"} 142

# Total tokens consumed
llm_api_tokens_total{provider="alibaba_cloud",type="input"} 125430
llm_api_tokens_total{provider="alibaba_cloud",type="output"} 23456

# Budget remaining (if configured)
llm_api_budget_remaining_usd{provider="alibaba_cloud"} 7.55
```

**Configuration (`.env`):**
```bash
# Monthly budgets (USD)
MONTHLY_BUDGET_ALIBABA_CLOUD=10.0
MONTHLY_BUDGET_OPENAI=20.0

# Budget alerts (triggers warning when <20% remaining)
BUDGET_ALERT_THRESHOLD=0.2
```

### 2.4 Grafana Dashboards

**Access:** `http://localhost:3000`
**Credentials:** `admin / admin`

**Pre-configured Dashboards:**

#### Dashboard 1: LLM Cost Overview

**Panels:**
1. **Total Cost (Current Month)** - Gauge showing total spend
2. **Cost by Provider** - Pie chart (Ollama vs Alibaba vs OpenAI)
3. **Cost Trend** - Line chart over time
4. **Budget Utilization** - Progress bar showing % of monthly budget used
5. **Cost per Request** - Average cost per API call
6. **Top 10 Models by Cost** - Bar chart

**Alerts:**
- ⚠️ Warning: Budget > 80% utilized
- 🚨 Critical: Budget > 95% utilized

#### Dashboard 2: VLM Image Processing Costs

**Panels:**
1. **VLM Calls Today** - Counter
2. **Images Processed** - Counter
3. **VLM Cost (Current Month)** - Gauge
4. **qwen3-vl vs qwen3-vl-thinking** - Cost comparison
5. **Token Distribution** - Input vs Output tokens

#### Dashboard 3: System Performance

**Panels:**
1. **Indexing Throughput** - Documents/hour
2. **Memory Usage** - RAM + VRAM
3. **Qdrant Points** - Total indexed chunks
4. **Neo4j Entities** - Graph size
5. **API Latency** - p50, p95, p99

### 2.5 Admin UI Cost Display

**Endpoint:** `GET /api/v1/admin/stats`

**Response (includes cost data):**
```json
{
  "qdrant_total_chunks": 1523,
  "neo4j_total_entities": 856,
  "total_conversations": 15,

  // Sprint 30: Add cost stats (future enhancement)
  "llm_costs": {
    "total_monthly_cost": 8.12,
    "ollama_cost": 0.0,
    "alibaba_cloud_cost": 2.45,
    "openai_cost": 5.67,
    "budget_remaining": {
      "alibaba_cloud": 7.55,
      "openai": 14.33
    }
  }
}
```

**Frontend Display:**
- **Admin Dashboard** (`/admin/overview`)
  - Cost summary card
  - Budget utilization progress bars
  - Cost trend mini-chart
  - Link to Grafana for details

---

## 3. Application Logs

### 3.1 Structured Logging (structlog)

All logs are JSON-formatted for easy parsing and filtering.

**Log Levels:**
- `DEBUG` - Detailed execution traces
- `INFO` - Normal operations (default)
- `WARNING` - Non-critical issues
- `ERROR` - Critical failures

**Configuration (`.env`):**
```bash
LOG_LEVEL=INFO
LOG_FORMAT=json  # or 'console' for human-readable
```

### 3.2 VLM Indexing Logs

**Key Log Events:**

```json
// VLM indexing started
{
  "event": "vlm_reindex_started",
  "input_dir": "C:\\path\\to\\docs",
  "confirm": true,
  "feature": "sprint_30_vlm_enrichment",
  "timestamp": "2025-11-18T10:30:00Z"
}

// Document indexed successfully
{
  "event": "vlm_document_indexed",
  "document_id": "abc123",
  "chunks": 42,
  "vlm_images": 8,
  "batch_progress": 0.5,
  "timestamp": "2025-11-18T10:32:15Z"
}

// VLM enrichment node processing
{
  "event": "node_vlm_enrichment_start",
  "document_id": "abc123",
  "timestamp": "2025-11-18T10:32:10Z"
}

// VLM API call with cost
{
  "event": "llm_call_completed",
  "provider": "alibaba_cloud",
  "model": "qwen3-vl-30b-a3b-instruct",
  "task_type": "vlm",
  "input_tokens": 1024,
  "output_tokens": 256,
  "cost_usd": 0.0023,
  "duration_ms": 1250,
  "timestamp": "2025-11-18T10:32:12Z"
}

// Batch completion
{
  "event": "vlm_reindex_completed",
  "total_docs": 10,
  "total_chunks": 420,
  "total_vlm_images": 85,
  "total_errors": 2,
  "duration_seconds": 420.5,
  "timestamp": "2025-11-18T10:37:30Z"
}
```

### 3.3 Log Viewing

**PowerShell:**
```powershell
# Backend logs (if running via uvicorn directly)
poetry run uvicorn src.api.main:app --reload --log-level info

# Docker Compose logs
docker compose logs -f

# Specific service logs
docker compose logs -f backend
docker compose logs -f qdrant
docker compose logs -f neo4j

# Filter logs by event
docker compose logs backend | Select-String "vlm_document_indexed"
```

**Log Files (if configured):**
- `logs/aegis_rag.log` - Application logs
- `logs/error.log` - Error logs only
- `logs/cost_tracking.log` - Cost-related events

---

## 4. Monitoring Checklist (Before & During Indexing)

### Pre-Indexing Checks

```powershell
# 1. Check Docker services
docker compose ps

# 2. Check Qdrant
curl http://localhost:6333/collections

# 3. Check Neo4j
curl -u neo4j:neo4j http://localhost:7474

# 4. Check Backend API health
curl http://localhost:8000/health

# 5. Check Prometheus
curl http://localhost:9090/-/healthy

# 6. Check Grafana
curl http://localhost:3000/api/health
```

### During Indexing

**Terminal 1: SSE Progress Stream**
```powershell
curl -N "http://localhost:8000/api/v1/admin/reindex_with_vlm?confirm=true" `
  -H "Accept: text/event-stream"
```

**Terminal 2: Docker Logs**
```powershell
docker compose logs -f backend
```

**Terminal 3: System Metrics**
```powershell
# Watch GPU usage
nvidia-smi -l 1

# Watch RAM usage
Get-Counter '\Memory\Available MBytes' -SampleInterval 1 -Continuous
```

**Browser:**
- **Grafana Dashboard:** http://localhost:3000
- **Qdrant UI:** http://localhost:6333/dashboard
- **Prometheus:** http://localhost:9090

### Post-Indexing Verification

```powershell
# 1. Check Qdrant points
curl http://localhost:8000/api/v1/admin/stats | jq '.qdrant_total_chunks'

# 2. Check Neo4j entities
curl http://localhost:8000/api/v1/admin/stats | jq '.neo4j_total_entities'

# 3. Check VLM costs
sqlite3 data/cost_tracking.db "SELECT SUM(cost_usd) FROM llm_calls WHERE task_type='vlm';"

# 4. Test retrieval
curl -X POST http://localhost:8000/api/v1/retrieval/query `
  -H "Content-Type: application/json" `
  -d '{"query":"performance optimization","top_k":5}'
```

---

## 5. Cost Optimization Tips

### 5.1 Reduce VLM Costs

**Image Filtering:**
```python
# src/components/ingestion/image_processor.py
# Increase minimum image size (skip small icons)
min_size = 200  # Default: 100

# Filter extreme aspect ratios (skip narrow banners)
min_aspect_ratio = 0.5  # Default: 0.1
max_aspect_ratio = 2.0  # Default: 10.0
```

**Use Local Ollama:**
```bash
# .env
# Prefer local Qwen3-VL over cloud (free!)
USE_LOCAL_VLM=true
QWEN3VL_MODEL=qwen3-vl:4b-instruct

# Only use cloud as fallback
CLOUD_VLM_FALLBACK=true
```

### 5.2 Budget Alerts

**Configure Alerts:**
```bash
# .env
MONTHLY_BUDGET_ALIBABA_CLOUD=10.0
BUDGET_ALERT_THRESHOLD=0.2  # Alert when <20% remaining

# Email notifications (future feature)
BUDGET_ALERT_EMAIL=your.email@example.com
```

**Grafana Alert Rules:**
1. Alert when `llm_api_budget_remaining_usd < 2.0`
2. Send email/Slack notification
3. Optionally pause VLM enrichment

### 5.3 Cost Analysis Queries

```sql
-- Average cost per document
SELECT
  AVG(doc_cost) as avg_cost_per_doc
FROM (
  SELECT
    metadata->>'$.document_id' as doc_id,
    SUM(cost_usd) as doc_cost
  FROM llm_calls
  WHERE task_type = 'vlm'
  GROUP BY doc_id
);

-- Most expensive VLM model
SELECT
  model,
  COUNT(*) as calls,
  SUM(cost_usd) / COUNT(*) as avg_cost_per_call
FROM llm_calls
WHERE task_type = 'vlm'
GROUP BY model
ORDER BY avg_cost_per_call DESC;

-- Daily cost trend (last 7 days)
SELECT
  DATE(timestamp) as date,
  SUM(cost_usd) as daily_cost
FROM llm_calls
WHERE timestamp > datetime('now', '-7 days')
GROUP BY DATE(timestamp)
ORDER BY date;
```

---

## 6. Troubleshooting

### Issue: Progress stream stops

**Symptoms:** SSE stream freezes, no updates

**Solution:**
```powershell
# Check backend logs for errors
docker compose logs backend | Select-String "ERROR"

# Check if pipeline is stuck
docker compose logs backend | Select-String "node_.*_start"

# Restart backend if frozen
docker compose restart backend
```

### Issue: Costs not tracking

**Symptoms:** SQLite database empty, Prometheus shows 0.0

**Solution:**
```powershell
# 1. Verify database exists
Test-Path data/cost_tracking.db

# 2. Check AegisLLMProxy is used (not direct LLM calls)
Get-Content src/components/ingestion/image_processor.py | Select-String "AegisLLMProxy"

# 3. Check logs for cost_tracker events
docker compose logs backend | Select-String "cost_tracker"

# 4. Manually trigger cost tracking test
poetry run python -c "
from src.components.llm_proxy.cost_tracker import get_cost_tracker
tracker = get_cost_tracker()
tracker.track_call('test', 'test-model', 100, 50, 'test')
print('Test call tracked!')
"
```

### Issue: Grafana not showing data

**Symptoms:** Empty dashboards, no data sources

**Solution:**
```powershell
# 1. Verify Prometheus is scraping metrics
curl http://localhost:9090/api/v1/targets

# 2. Check if Backend exposes /metrics
curl http://localhost:8000/metrics | Select-String "llm_api_cost"

# 3. Import Grafana dashboard manually
# - Login: http://localhost:3000 (admin/admin)
# - Dashboards → Import → Upload JSON from config/grafana/dashboards/

# 4. Verify Prometheus data source
curl -u admin:admin http://localhost:3000/api/datasources
```

---

## 7. Summary

**Where to Monitor:**

| What to Monitor | Where | URL |
|-----------------|-------|-----|
| **Indexing Progress** | SSE Stream | `curl -N http://localhost:8000/api/v1/admin/reindex_with_vlm?confirm=true` |
| **LLM Costs (Database)** | SQLite | `sqlite3 data/cost_tracking.db` |
| **LLM Costs (Visual)** | Grafana | http://localhost:3000 |
| **System Metrics** | Prometheus | http://localhost:9090 |
| **Vector DB** | Qdrant UI | http://localhost:6333/dashboard |
| **Graph DB** | Neo4j Browser | http://localhost:7474 |
| **Application Logs** | Docker Logs | `docker compose logs -f backend` |
| **Admin Stats** | Admin UI | http://localhost:5173/admin |

**Quick Start Commands:**
```powershell
# Start all services
.\scripts\start_aegis_rag.ps1

# Index with VLM
poetry run python scripts/test_vlm_indexing.py

# Check costs
sqlite3 data/cost_tracking.db "SELECT provider, SUM(cost_usd) FROM llm_calls GROUP BY provider;"

# View Grafana
Start-Process "http://localhost:3000"
```

---

**End of Monitoring Guide**
