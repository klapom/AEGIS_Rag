# Sprint 30: System Stability & VLM Directory Indexing

**Sprint Goal:** Stabilize system and enable VLM-enhanced directory indexing for PDF/PPTX with embedded images.

**Duration:** 2025-11-18 (1 day)
**Status:** ✅ READY FOR TESTING
**Branch:** `main`

---

## Features Implemented

### Feature 30.1: VLM-Enhanced Re-Indexing API ✅

**Endpoint:** `POST /api/v1/admin/reindex_with_vlm`

**Full LangGraph Pipeline:**
1. Docling CUDA Container → Parse PDF/PPTX + extract images
2. Qwen3-VL Image Enrichment → Generate descriptions for all images
3. Chunking → 1800-token chunks with image context
4. BGE-M3 Embeddings → Index to Qdrant
5. Graph Extraction → Entities + Relations to Neo4j

**Features:**
- ✅ Real-time progress via SSE (Server-Sent Events)
- ✅ Per-document progress tracking (6 nodes each)
- ✅ VLM image count tracking
- ✅ Cost tracking via AegisLLMProxy
- ✅ Safety: `confirm=true` required (prevents accidental deletion)
- ✅ Batch processing (one document at a time for memory optimization)

**Supported Formats:**
- PDF (with embedded images)
- PPTX (PowerPoint with images)
- DOCX, TXT, MD, CSV

**VLM Configuration:**
- Local: Qwen3-VL via Ollama (5-6GB VRAM)
- Cloud Fallback: Alibaba DashScope qwen3-vl models
- Image Filtering: Min size 100px, aspect ratio 0.1-10.0

**Files Modified:**
- `src/api/v1/admin.py` (+293 lines, new endpoint)

---

### Feature 30.2: Test Script for Directory Indexing ✅

**Script:** `scripts/test_vlm_indexing.py`

**Purpose:** Test VLM indexing for the Performance Schulung directory.

**Features:**
- ✅ Discovers documents in target directory
- ✅ Shows detailed progress for each document
- ✅ Tracks VLM images processed
- ✅ Shows chunk statistics
- ✅ Reports errors (non-fatal)
- ✅ Final summary with duration and stats

**Usage:**
```powershell
poetry run python scripts/test_vlm_indexing.py
```

**Target Directory:** `data/sample_documents/10. Performance Schulung`

---

### Feature 30.3: Startup Script (Backend + Frontend) ✅

**Script:** `scripts/start_aegis_rag.ps1`

**Purpose:** Start all AegisRAG services in one command.

**What it does:**
1. Checks prerequisites (Poetry, Docker, Node.js)
2. Starts Docker Compose services (Qdrant, Neo4j, Redis, Ollama)
3. Starts Backend API (port 8000) in new terminal
4. Starts Frontend UI (port 5173) in new terminal
5. Performs health checks
6. Shows service URLs and next steps

**Usage:**
```powershell
.\scripts\start_aegis_rag.ps1
```

**Services Started:**
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend UI: http://localhost:5173
- Qdrant UI: http://localhost:6333/dashboard
- Neo4j Browser: http://localhost:7474
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

---

### Feature 30.4: Monitoring & Cost Tracking Documentation ✅

**Document:** `docs/MONITORING_GUIDE.md`

**Comprehensive Guide:**

**1. Progress Tracking**
- Real-time SSE progress streams
- Per-document VLM image counts
- Chunk statistics
- Error tracking

**2. Cost Tracking (3 Layers)**
- **SQLite Database** (`data/cost_tracking.db`) - Persistent storage
- **Prometheus Metrics** (`/metrics`) - Real-time counters
- **Grafana Dashboard** (http://localhost:3000) - Visual analytics

**3. System Metrics**
- Indexing throughput
- Memory usage (RAM + VRAM)
- API latency
- Database sizes

**4. Application Logs**
- Structured JSON logging (structlog)
- Docker Compose logs
- VLM enrichment events
- Cost tracking events

---

### Feature 30.5: Alibaba Cloud (Qwen3-32B) for Entity Extraction ✅

**ADR:** ADR-037 (Alibaba Cloud Extraction)
**Date:** 2025-11-19

**Problem:**
Entity/relation extraction was marked as `Complexity.MEDIUM`, causing all extraction to route to local Gemma 2 4B (4 billion parameters) instead of Alibaba Cloud Qwen3-32B (32 billion parameters).

**Solution:**
Changed extraction complexity from MEDIUM → HIGH to enable Alibaba Cloud routing.

**Changes:**
- `src/components/graph_rag/extraction_service.py:269` - Entity extraction complexity: MEDIUM → HIGH
- `src/components/graph_rag/extraction_service.py:392` - Relationship extraction complexity: MEDIUM → HIGH

**Routing Logic:**
```python
# Before (MEDIUM complexity):
# → Routes to local_ollama (Gemma 2 4B)

# After (HIGH complexity):
# → Routes to alibaba_cloud (Qwen3-32B) when:
#    - Quality: HIGH
#    - Complexity: HIGH
#    - Budget not exceeded
```

**Model Used:**
- **Provider:** Alibaba Cloud DashScope
- **Model:** `qwen3-32b` (32 billion parameters)
- **Quality:** 8x larger than local Gemma 2 4B
- **Cost:** ~$0.001-0.003 per 1,000 tokens
- **Monthly Budget:** $120 (covers ~40,000-120,000 chunks)

**Expected Benefits:**
- **Entity Accuracy:** 85% → 95% (+10%)
- **Relation Accuracy:** 75% → 90% (+15%)
- **Better Disambiguation:** Advanced context understanding
- **Cost-Effective:** $120/month covers 1,000-3,000 documents

**Automatic Fallback:**
- Falls back to local Gemma 2 4B if budget exceeded
- Graceful degradation (no downtime)
- Budget alerts at 80% utilization

**Cost Monitoring:**
```powershell
# Check extraction costs
sqlite3 data/cost_tracking.db "SELECT provider, model, SUM(cost_usd) FROM costs WHERE task_type='extraction' GROUP BY provider, model;"

# Today's extraction costs
sqlite3 data/cost_tracking.db "SELECT SUM(cost_usd) FROM costs WHERE task_type='extraction' AND date(timestamp) = date('now');"
```

**Verification:**
Look for these log events during indexing:
```json
{
  "event": "routing_decision",
  "provider": "alibaba_cloud",
  "routing_reason": "high_quality_high_complexity",
  "task_type": "extraction",
  "quality": "high",
  "complexity": "high"
}

{
  "event": "llm_entity_extraction_response",
  "provider": "alibaba_cloud",
  "model": "qwen3-32b",
  "cost_usd": 0.0023,
  "tokens_input": 512,
  "tokens_output": 1024
}
```

**LightRAG Research:**
No recent Qwen-specific entity extraction improvements in LightRAG GitHub (checked 2025-11-19). Recent changes were for RAG response prompts (anti-hallucination), NOT entity extraction. Quality improvement comes from model parameter count (32B vs 4B), not prompt optimization.

**Files Modified:**
- `src/components/graph_rag/extraction_service.py` (2 lines changed)
- `docs/adr/ADR-037-alibaba-cloud-extraction.md` (new ADR)

---

### Feature 30.6: DashScope extra_body Parameter Fix ✅

**ADR:** ADR-038 (DashScope Custom Parameters via OpenAI SDK extra_body)
**Date:** 2025-11-19

**Problem:**
After implementing Feature 30.5 (Complexity.HIGH routing), Alibaba Cloud API calls failed with:
```json
{
  "error": {
    "code": "invalid_parameter_error",
    "message": "parameter.enable_thinking must be set to false for non-streaming calls"
  }
}
```

**Root Cause:**
Deep code analysis revealed:
1. ✅ ANY-LLM correctly forwards `**kwargs` (no filtering)
2. ❌ OpenAI Python SDK only accepts custom parameters via `extra_body`
3. ❌ `enable_thinking` was passed as direct kwarg → rejected by SDK

**Solution:**
Use OpenAI SDK's `extra_body` mechanism for DashScope custom parameters:

```python
# Before (failed):
await acompletion(
    model="qwen3-32b",
    enable_thinking=False,  # ❌ Unknown parameter → TypeError
    **kwargs
)

# After (works):
await acompletion(
    model="qwen3-32b",
    extra_body={"enable_thinking": False},  # ✅ Via extra_body
    **kwargs
)
```

**Implementation:**
```python
# In aegis_llm_proxy.py
if provider == "alibaba_cloud" and not stream:
    extra_body = {}
    if "thinking" in model:
        extra_body["enable_thinking"] = True  # Thinking models
    else:
        extra_body["enable_thinking"] = False  # Non-thinking models

    completion_kwargs["extra_body"] = extra_body
```

**Test Results:**
```json
{
  "routing_decision": "complexity=high provider=alibaba_cloud",
  "token_usage": "model=qwen3-32b tokens=899",
  "cost_usd": 0.00007585,
  "fallback_used": false,
  "entities_extracted": 7
}
```

**Quality Improvement:**
- 7 entities extracted vs 5 with local model (+40%)
- New entities detected:
  - "World War II" (EVENT)
  - "international peace and security" (CONCEPT)

**Why This Matters:**
- Generalizable pattern for other OpenAI-compatible APIs (Groq, Perplexity, etc.)
- No changes needed to ANY-LLM framework (preserves benefits)
- Clean solution using official OpenAI SDK mechanism

**Code Path Verified:**
1. `any_llm/api.py:190` → `**kwargs` forwarded ✅
2. `any_llm/providers/openai/base.py:138` → kwargs merged ✅
3. `openai/resources/chat/completions.py:279` → `extra_body` accepted ✅
4. DashScope API receives `enable_thinking` in request body ✅

**Files Modified:**
- `src/components/llm_proxy/aegis_llm_proxy.py` (+28 lines documentation, logic fix)
- `docs/adr/ADR-038-dashscope-extra-body-parameters.md` (new ADR, 250+ lines)

**Learning:**
This debugging session highlighted the importance of tracing code through all layers (ANY-LLM → OpenAI SDK → HTTP) to find root causes. The initial assumption (ANY-LLM filtering) was incorrect; the actual bottleneck was OpenAI SDK's parameter validation.

---

## Testing Guide for Tomorrow

### Step 1: Start the System

```powershell
# Navigate to project root
cd "C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag"

# Start all services
.\scripts\start_aegis_rag.ps1
```

**Expected Output:**
- 3 new PowerShell windows open (Backend, Frontend, Docker Logs)
- Service URLs displayed
- Health checks pass

**Verify Services:**
1. Backend: http://localhost:8000/health
2. Frontend: http://localhost:5173
3. Qdrant: http://localhost:6333/dashboard
4. Neo4j: http://localhost:7474
5. Grafana: http://localhost:3000 (admin/admin)

---

### Step 2: Test VLM Indexing (Option A: Test Script)

```powershell
# Run test script for Performance Schulung directory
poetry run python scripts/test_vlm_indexing.py
```

**What to Expect:**
1. **Discovery Phase:** Shows found PDFs, PPTX, DOCX files
2. **Per-Document Progress:**
   - Document name
   - Chunks created
   - VLM images processed
   - Errors (if any)
3. **Final Summary:**
   - Total documents processed
   - Total chunks created
   - Total VLM images processed
   - Duration

**Example Output:**
```
[50%] Document 1/2: Performance_Optimierung.pdf
----------------------------------------------------------------
STATUS: SUCCESS
  - Document ID: abc123
  - Chunks created: 42
  - VLM images processed: 8
  - Errors (non-fatal): 0

  VLM Image Details:
    1. image_page3_bbox1: A diagram showing CPU utilization...
    2. image_page5_bbox2: Performance graph with latency metrics...
    ...
```

---

### Step 3: Test VLM Indexing (Option B: API via curl)

```powershell
# Via API with SSE progress stream
$dir = "C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\data\sample_documents\10. Performance Schulung"

curl -N "http://localhost:8000/api/v1/admin/reindex_with_vlm?input_dir=$([Uri]::EscapeDataString($dir))&confirm=true" `
  -H "Accept: text/event-stream"
```

**What to Expect:**
```
data: {"status":"discovery","progress":0.05,"message":"Found 2 documents"}

data: {"status":"deletion","progress":0.15,"message":"Old indexes deleted"}

data: {"status":"ingestion","progress":0.42,"message":"Processed Performance_Optimierung.pdf","chunks":42,"vlm_images":8}

data: {"status":"completed","progress":1.0,"total_chunks":85,"total_vlm_images":16}
```

---

### Step 4: Monitor Progress

**Terminal 1: SSE Progress Stream (from Step 3)**
- Shows real-time document processing
- VLM image counts
- Chunk statistics

**Terminal 2: Docker Logs**
```powershell
docker compose logs -f backend
```
**What to Look For:**
- `node_vlm_enrichment_start` - VLM processing started
- `vlm_document_indexed` - Document completed
- `llm_call_completed` - VLM API calls with costs

**Terminal 3: System Metrics**
```powershell
# Watch GPU usage (if NVIDIA GPU available)
nvidia-smi -l 1

# Watch RAM usage
Get-Counter '\Memory\Available MBytes' -SampleInterval 1 -Continuous
```

**Browser Tabs:**
1. **Grafana Dashboard:** http://localhost:3000
   - Monitor VLM costs in real-time
   - Check budget utilization
   - View cost trends

2. **Qdrant UI:** http://localhost:6333/dashboard
   - Verify chunks are being indexed
   - Check vector collection size

3. **Neo4j Browser:** http://localhost:7474
   - Login: neo4j/neo4j
   - Query: `MATCH (e:Entity) RETURN COUNT(e)`
   - Verify entities are being created

---

### Step 5: Verify Results

#### Check Qdrant Indexing

```powershell
# Get admin stats
curl http://localhost:8000/api/v1/admin/stats | ConvertFrom-Json
```

**Expected Output:**
```json
{
  "qdrant_total_chunks": 142,
  "qdrant_vector_dimension": 1024,
  "neo4j_total_entities": 56,
  "neo4j_total_relations": 82,
  "embedding_model": "BAAI/bge-m3"
}
```

#### Check VLM Costs

```powershell
# Open SQLite database
sqlite3 data/cost_tracking.db

# Query VLM costs
SELECT
  model,
  COUNT(*) as calls,
  SUM(cost_usd) as total_cost,
  AVG(cost_usd) as avg_cost
FROM llm_calls
WHERE task_type = 'vlm'
GROUP BY model;
```

**Expected Output:**
```
qwen3-vl-30b-a3b-instruct|16|0.0234|0.0014625
```

#### Test Retrieval

```powershell
# Query indexed content
curl -X POST http://localhost:8000/api/v1/retrieval/query `
  -H "Content-Type: application/json" `
  -d '{
    "query": "Welche Performance-Optimierungen werden im Dokument beschrieben?",
    "top_k": 5,
    "search_type": "hybrid"
  }' | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

**Expected:** Relevant chunks with VLM image descriptions included!

---

## Monitoring Kosten (Where to Check)

### Option 1: SQLite Database (Most Detailed)

```powershell
sqlite3 data/cost_tracking.db

# Total costs by provider
SELECT provider, SUM(cost_usd) FROM llm_calls GROUP BY provider;

# VLM costs today
SELECT SUM(cost_usd) FROM llm_calls
WHERE task_type = 'vlm' AND DATE(timestamp) = DATE('now');

# Most expensive VLM calls
SELECT timestamp, model, total_tokens, cost_usd
FROM llm_calls
WHERE task_type = 'vlm'
ORDER BY cost_usd DESC
LIMIT 10;
```

### Option 2: Grafana Dashboard (Visual)

**URL:** http://localhost:3000 (admin/admin)

**Dashboards:**
1. **LLM Cost Overview**
   - Total cost gauge
   - Cost by provider pie chart
   - Cost trend line chart
   - Budget utilization progress bars

2. **VLM Image Processing Costs**
   - VLM calls counter
   - Images processed counter
   - Cost comparison: qwen3-vl vs qwen3-vl-thinking

**To Access:**
```powershell
Start-Process "http://localhost:3000"
```

### Option 3: Prometheus Metrics (Real-Time)

**URL:** http://localhost:9090

**Key Metrics:**
```
llm_api_cost_total{provider="alibaba_cloud"}
llm_api_calls_total{provider="alibaba_cloud",model="qwen3-vl-30b"}
llm_api_tokens_total{type="input"}
llm_api_budget_remaining_usd{provider="alibaba_cloud"}
```

**Query Examples:**
```promql
# Total VLM cost (Alibaba Cloud)
sum(llm_api_cost_total{provider="alibaba_cloud"})

# VLM calls in last hour
increase(llm_api_calls_total{task_type="vlm"}[1h])

# Budget remaining percentage
(llm_api_budget_remaining_usd / 10) * 100
```

### Option 4: Admin UI (Future)

**URL:** http://localhost:5173/admin (when frontend supports it)

Currently shows:
- Qdrant chunks
- Neo4j entities
- Total conversations

**Future Sprint:** Add cost summary cards

---

## Troubleshooting

### Issue: Script fails with "Directory not found"

**Solution:**
```powershell
# Verify directory exists
Test-Path "C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\data\sample_documents\10. Performance Schulung"

# List files in directory
Get-ChildItem "C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\data\sample_documents\10. Performance Schulung"
```

### Issue: VLM images not being processed

**Symptoms:** `vlm_images: 0` in output

**Possible Causes:**
1. **Images too small:** Min size is 100px
2. **Extreme aspect ratio:** Outside 0.1-10.0 range
3. **VLM service unavailable:** Check Ollama/DashScope

**Solution:**
```powershell
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check Qwen3-VL model installed
docker exec ollama ollama list | Select-String "qwen"

# Test VLM directly
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3-vl:4b-instruct",
  "prompt": "Test",
  "stream": false
}'
```

### Issue: High VLM costs

**Symptoms:** Costs higher than expected

**Analysis:**
```powershell
# Check average cost per image
sqlite3 data/cost_tracking.db "
SELECT
  COUNT(*) as images,
  SUM(cost_usd) as total_cost,
  AVG(cost_usd) as avg_cost_per_image,
  SUM(total_tokens) / COUNT(*) as avg_tokens_per_image
FROM llm_calls
WHERE task_type = 'vlm'
"
```

**Optimization:**
1. **Use local Ollama** (free): Set `USE_LOCAL_VLM=true`
2. **Increase image filtering:** Min size 200px instead of 100px
3. **Use cheaper model:** `qwen3-vl-30b-a3b-instruct` (cheaper output tokens)
4. **Set budget limits:** `MONTHLY_BUDGET_ALIBABA_CLOUD=10.0`

---

## Next Steps (Future Sprints)

**Sprint 31: Frontend Directory Picker**
- Add directory selection UI to admin dashboard
- Stream progress with visual progress bars
- Display VLM image previews
- Show cost estimates before indexing

**Sprint 32: Advanced Cost Controls**
- Per-provider budget limits
- Cost prediction before indexing
- Automatic fallback to local VLM when budget exceeded
- Email alerts for budget warnings

**Sprint 33: Production Hardening**
- Horizontal scaling (multi-worker deployment)
- Kubernetes manifests with auto-scaling
- Advanced error recovery
- Comprehensive E2E tests

---

## Summary

**Sprint 30 Deliverables:** ✅ ALL COMPLETE

1. ✅ VLM-Enhanced Re-Indexing API (`/admin/reindex_with_vlm`)
2. ✅ Test Script (`scripts/test_vlm_indexing.py`)
3. ✅ Startup Script (`scripts/start_aegis_rag.ps1`)
4. ✅ Monitoring Guide (`docs/MONITORING_GUIDE.md`)

**Ready for Testing:** YES ✅

**Testing Tomorrow:**
1. Run `.\scripts\start_aegis_rag.ps1`
2. Run `poetry run python scripts/test_vlm_indexing.py`
3. Monitor progress via logs, Grafana, and SSE stream
4. Verify costs in SQLite database
5. Test retrieval with indexed content

**Kosten Tracking:**
- SQLite: `data/cost_tracking.db` (detailed queries)
- Grafana: http://localhost:3000 (visual dashboards)
- Prometheus: http://localhost:9090 (real-time metrics)

**Estimated VLM Costs:**
- Local Ollama: $0.00 (free!)
- Alibaba Cloud (qwen3-vl): ~$0.002 per image (~$0.20 for 100 images)

---

**Happy Testing! 🚀**
