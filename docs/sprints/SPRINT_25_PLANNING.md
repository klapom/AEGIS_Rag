# Sprint 25: Production Readiness & Monitoring

**Status:** 📋 PLANNED
**Goal:** Production monitoring, integration tests, and deferred Sprint 24 features
**Duration:** 5 days (2025-11-15 to 2025-11-21)
**Prerequisites:** Sprint 24 complete (Dependency Optimization & CI Performance)
**Story Points:** 30 SP

---

## 🎯 Sprint Objectives

### **Primary Goals:**
1. Implement production monitoring (Prometheus metrics, Grafana dashboards)
2. Complete integration tests for LangGraph ingestion pipeline
3. Improve token tracking accuracy (no 50/50 estimation)
4. Refactor async/sync bridge for cleaner architecture
5. Complete MyPy strict mode and documentation updates

### **Success Criteria:**
- ✅ Prometheus /metrics endpoint operational
- ✅ Grafana dashboard displaying LLM cost, latency, and token metrics
- ✅ Integration tests for LangGraph pipeline (>80% coverage)
- ✅ Token tracking accuracy improved (accurate input/output split)
- ✅ Async/sync bridge refactored (no ThreadPoolExecutor)
- ✅ MyPy strict mode passing
- ✅ Architecture documentation updated

---

## 📦 Sprint Features

### Category 1: Production Monitoring (High Priority)

#### Feature 25.1: Prometheus Metrics Implementation (5 SP) ⭐
**Priority:** P1 (High) - **Production Blocker**
**Duration:** 1 day
**Source:** Deferred from Sprint 24 (Feature 24.1)

**Problem:**
Cost tracking logs structured metrics but doesn't export to Prometheus. No /metrics endpoint for monitoring dashboards.

**Solution:**
Implement `src/core/metrics.py` with prometheus_client and export metrics endpoint.

**Deliverables:**
- [ ] `src/core/metrics.py` with LLM-specific metrics
- [ ] FastAPI /metrics endpoint registration
- [ ] Grafana dashboard JSON (LLM cost, latency, requests)
- [ ] Documentation in `docs/guides/MONITORING.md`
- [ ] Integration with existing Prometheus client

**Metrics to Implement:**
```python
from prometheus_client import Counter, Gauge, Histogram

# LLM Metrics
llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["provider", "model", "task_type"]
)

llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "LLM request latency",
    ["provider", "model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

llm_cost_usd = Counter(
    "llm_cost_usd",
    "Total LLM cost in USD",
    ["provider", "model"]
)

llm_tokens_used = Counter(
    "llm_tokens_used",
    "Total tokens used",
    ["provider", "model", "token_type"]  # token_type: input, output
)

llm_errors_total = Counter(
    "llm_errors_total",
    "Total LLM errors",
    ["provider", "error_type"]
)

# Budget Metrics
monthly_budget_remaining = Gauge(
    "monthly_budget_remaining_usd",
    "Monthly budget remaining",
    ["provider"]
)

monthly_spend = Gauge(
    "monthly_spend_usd",
    "Monthly spend so far",
    ["provider"]
)

# System Metrics
qdrant_points_count = Gauge(
    "qdrant_points_count",
    "Total points in Qdrant",
    ["collection"]
)

neo4j_entities_count = Gauge(
    "neo4j_entities_count",
    "Total entities in Neo4j"
)

neo4j_relations_count = Gauge(
    "neo4j_relations_count",
    "Total relationships in Neo4j"
)
```

**Integration Points:**
```python
# src/components/llm_proxy/aegis_llm_proxy.py
from src.core.metrics import (
    llm_requests_total,
    llm_latency_seconds,
    llm_cost_usd,
    llm_tokens_used,
)

async def generate(self, task: LLMTask) -> LLMResponse:
    start_time = time.time()

    try:
        result = await self._execute_with_any_llm(...)

        # Record metrics
        latency = time.time() - start_time
        llm_requests_total.labels(
            provider=provider,
            model=model,
            task_type=task.task_type
        ).inc()

        llm_latency_seconds.labels(
            provider=provider,
            model=model
        ).observe(latency)

        llm_cost_usd.labels(
            provider=provider,
            model=model
        ).inc(result.cost_usd)

        llm_tokens_used.labels(
            provider=provider,
            model=model,
            token_type="input"
        ).inc(result.tokens_input)

        llm_tokens_used.labels(
            provider=provider,
            model=model,
            token_type="output"
        ).inc(result.tokens_output)

        return result

    except Exception as e:
        llm_errors_total.labels(
            provider=provider,
            error_type=type(e).__name__
        ).inc()
        raise
```

**Grafana Dashboard:**
```json
{
  "dashboard": {
    "title": "AEGIS RAG - LLM Monitoring",
    "panels": [
      {
        "title": "LLM Request Rate",
        "targets": [{"expr": "rate(llm_requests_total[5m])"}]
      },
      {
        "title": "LLM Latency (p95)",
        "targets": [{"expr": "histogram_quantile(0.95, llm_latency_seconds)"}]
      },
      {
        "title": "LLM Cost (Hourly)",
        "targets": [{"expr": "rate(llm_cost_usd[1h])"}]
      },
      {
        "title": "Token Usage",
        "targets": [{"expr": "rate(llm_tokens_used[5m])"}]
      },
      {
        "title": "Budget Remaining",
        "targets": [{"expr": "monthly_budget_remaining_usd"}]
      }
    ]
  }
}
```

**Acceptance Criteria:**
- ✅ /metrics endpoint returns Prometheus-formatted metrics
- ✅ Metrics update in real-time during LLM requests
- ✅ Grafana dashboard displays cost and latency trends
- ✅ Budget alerts trigger when >80% spent
- ✅ Integration tests validate metric collection
- ✅ Documentation in MONITORING.md

**Files to Create/Modify:**
- `src/core/metrics.py` (NEW)
- `src/api/main.py` (add /metrics endpoint)
- `src/components/llm_proxy/aegis_llm_proxy.py` (add metric recording)
- `src/components/llm_proxy/cost_tracker.py` (add metric export)
- `dashboards/grafana/llm_monitoring.json` (NEW)
- `docs/guides/MONITORING.md` (NEW)
- `tests/integration/test_prometheus_metrics.py` (NEW)

---

### Category 2: Testing & Quality Assurance

#### Feature 25.2: LangGraph Integration Tests (5 SP) ⭐
**Priority:** P1 (High) - **Test Coverage Gap**
**Duration:** 1 day
**Source:** Deferred from Sprint 24 (Feature 24.7)

**Problem:**
LangGraph ingestion pipeline (Sprint 21-23) missing comprehensive integration tests. Only unit tests exist for individual nodes.

**Solution:**
Create integration tests for full LangGraph ingestion pipeline (6 nodes).

**Deliverables:**
- [ ] Integration tests for LangGraph nodes (6 tests)
- [ ] E2E test for full ingestion pipeline
- [ ] Test fixtures for sample documents
- [ ] Test coverage report (target: >80%)
- [ ] CI pipeline validation

**Test Coverage:**
```python
# tests/integration/components/ingestion/test_langgraph_pipeline.py

import pytest
from pathlib import Path
from src.components.ingestion.langgraph_pipeline import IngestionPipeline
from src.components.ingestion.ingestion_state import IngestionState

@pytest.fixture
def sample_pdf():
    """Fixture for sample PDF document."""
    return Path("tests/fixtures/sample_document.pdf")

@pytest.fixture
def ingestion_pipeline():
    """Fixture for ingestion pipeline."""
    return IngestionPipeline()

# Node-level integration tests
async def test_memory_check_node_success():
    """Test memory check node with sufficient memory."""
    state = create_initial_state(document_path="test.pdf")
    result = await memory_check_node(state)

    assert result["memory_check_passed"] is True
    assert result["current_memory_mb"] > 0
    assert result["current_vram_mb"] >= 0

async def test_docling_extraction_node(sample_pdf):
    """Test Docling container integration."""
    state = create_initial_state(document_path=sample_pdf)
    state["memory_check_passed"] = True

    result = await docling_extraction_node(state)

    assert result["docling_status"] == "completed"
    assert len(result["parsed_content"]) > 0
    assert len(result["page_dimensions"]) > 0

async def test_image_enrichment_node(sample_pdf):
    """Test VLM image enrichment."""
    # Setup: Run Docling first
    state = await docling_extraction_node(...)

    result = await image_enrichment_node(state)

    assert result["enrichment_status"] == "completed"
    assert len(result["vlm_metadata"]) >= 0

async def test_chunking_node():
    """Test chunking with HybridChunker."""
    state = ...  # Setup with parsed document

    result = await chunking_node(state)

    assert result["chunking_status"] == "completed"
    assert len(result["chunks"]) > 0
    assert all("chunk" in c and "image_bboxes" in c for c in result["chunks"])

async def test_embedding_node():
    """Test Qdrant embedding and upsert."""
    state = ...  # Setup with chunks

    result = await embedding_node(state)

    assert result["embedding_status"] == "completed"
    assert len(result["embedded_chunk_ids"]) == len(state["chunks"])

async def test_graph_extraction_node():
    """Test LightRAG entity/relation extraction."""
    state = ...  # Setup with chunks

    result = await graph_extraction_node(state)

    assert result["graph_status"] == "completed"
    assert result["entities"] is not None
    assert result["relations"] is not None

# End-to-end pipeline test
@pytest.mark.slow
async def test_end_to_end_pipeline(sample_pdf, ingestion_pipeline):
    """Test complete pipeline: PDF → Qdrant + Neo4j."""
    # Run full pipeline
    result = await ingestion_pipeline.run(sample_pdf)

    # Validate all stages completed
    assert result["memory_check_passed"] is True
    assert result["docling_status"] == "completed"
    assert result["chunking_status"] == "completed"
    assert result["embedding_status"] == "completed"
    assert result["graph_status"] == "completed"

    # Validate data in Qdrant
    qdrant = get_qdrant_client()
    points = await qdrant.scroll(
        collection_name="aegis_documents",
        limit=10
    )
    assert len(points[0]) > 0

    # Validate data in Neo4j
    lightrag = await get_lightrag_wrapper_async()
    stats = await lightrag.get_stats()
    assert stats["entity_count"] > 0
    assert stats["relationship_count"] > 0

# Error handling tests
async def test_pipeline_graceful_degradation():
    """Test pipeline continues when optional steps fail."""
    # Setup: Mock VLM to fail
    with patch('src.components.ingestion.image_processor.ImageProcessor.process_image', side_effect=Exception("VLM failed")):
        result = await ingestion_pipeline.run(sample_pdf)

    # Pipeline should complete despite VLM failure
    assert result["enrichment_status"] == "failed"
    assert result["embedding_status"] == "completed"  # Should still succeed

# Performance tests
@pytest.mark.slow
async def test_pipeline_performance(sample_pdf):
    """Test pipeline completes within acceptable time."""
    import time

    start = time.time()
    result = await ingestion_pipeline.run(sample_pdf)
    duration = time.time() - start

    # Should complete within 5 minutes for small document
    assert duration < 300
    assert result["overall_progress"] == 100.0
```

**Test Fixtures:**
```python
# tests/fixtures/sample_documents.py

@pytest.fixture
def sample_pdf():
    """2-page PDF with text, image, and table."""
    return Path("tests/fixtures/sample_document.pdf")

@pytest.fixture
def sample_pptx():
    """5-slide PowerPoint presentation."""
    return Path("tests/fixtures/sample_presentation.pptx")

@pytest.fixture
def sample_docx():
    """3-page Word document."""
    return Path("tests/fixtures/sample_document.docx")
```

**Acceptance Criteria:**
- ✅ 6+ integration tests created for LangGraph nodes
- ✅ 1 E2E test for full pipeline
- ✅ All tests passing
- ✅ Coverage >80% for ingestion module
- ✅ CI pipeline includes new tests
- ✅ Performance baseline established (<5 min for small docs)

**Files to Create:**
- `tests/integration/components/ingestion/test_langgraph_pipeline.py` (NEW)
- `tests/fixtures/sample_document.pdf` (NEW)
- `tests/fixtures/sample_presentation.pptx` (NEW)
- `tests/fixtures/conftest.py` (update with fixtures)

---

### Category 3: LLM Proxy Improvements

#### Feature 25.3: Token Tracking Accuracy Fix (3 SP)
**Priority:** P2 (Medium)
**Duration:** 0.5 day
**Source:** Deferred from Sprint 24 (Feature 24.2)

**Problem:**
Token split estimation uses 50/50 split for input/output tokens because ANY-LLM response doesn't provide detailed breakdown. Alibaba Cloud charges different rates for input vs output.

**Current Code:**
```python
# src/components/llm_proxy/aegis_llm_proxy.py:495-497
# Estimate 50/50 split for input/output tokens if not available
tokens_input = result.tokens_used // 2
tokens_output = result.tokens_used - tokens_input
```

**Solution:**
Extract detailed token usage from API responses. Alibaba Cloud returns `prompt_tokens` and `completion_tokens`.

**Implementation:**
```python
# Parse response.usage properly
if hasattr(result, 'usage') and result.usage:
    tokens_input = result.usage.get('prompt_tokens', 0)
    tokens_output = result.usage.get('completion_tokens', 0)
    total_tokens = tokens_input + tokens_output
else:
    # Fallback to total tokens with 50/50 estimate
    total_tokens = getattr(result, 'tokens_used', 0)
    if total_tokens > 0:
        tokens_input = total_tokens // 2
        tokens_output = total_tokens - tokens_input
    else:
        tokens_input = 0
        tokens_output = 0

logger.info(
    "token_usage_parsed",
    provider=provider,
    model=model,
    tokens_input=tokens_input,
    tokens_output=tokens_output,
    total_tokens=total_tokens,
    estimation_used=not (hasattr(result, 'usage') and result.usage)
)
```

**Deliverables:**
- [ ] Update `aegis_llm_proxy.py` to parse `usage` field
- [ ] Add unit tests for token parsing (with/without usage field)
- [ ] Update cost tracker with accurate input/output split
- [ ] Verify with DashScope API response
- [ ] Add logging for estimation fallback

**Acceptance Criteria:**
- ✅ Token input/output split accurate when `usage` field available
- ✅ Fallback to 50/50 estimation when `usage` missing (with warning log)
- ✅ Cost calculations use correct rates (input vs output)
- ✅ Unit tests cover edge cases (missing usage field, zero tokens)
- ✅ SQLite database shows accurate token breakdown
- ✅ Prometheus metrics show input/output token split

**Files to Modify:**
- `src/components/llm_proxy/aegis_llm_proxy.py`
- `src/components/llm_proxy/cost_tracker.py`
- `tests/unit/components/llm_proxy/test_aegis_llm_proxy.py`

---

#### Feature 25.4: Async/Sync Bridge Refactoring (5 SP)
**Priority:** P2 (Medium)
**Duration:** 1 day
**Source:** Deferred from Sprint 24 (Feature 24.3)

**Problem:**
`ImageProcessor.process_image()` is synchronous but calls async `generate_vlm_description_with_dashscope()`. We use `asyncio.run()` with ThreadPoolExecutor to bridge sync/async, adding complexity.

**Current Workaround:**
```python
# src/components/ingestion/image_processor.py:414-434
try:
    asyncio.get_running_loop()
    # Already in event loop - use ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(
            asyncio.run,
            generate_vlm_description_with_dashscope(...)
        )
        description = future.result()
except RuntimeError:
    # Not in event loop - use asyncio.run
    description = asyncio.run(generate_vlm_description_with_dashscope(...))
```

**Solution:**
Make entire ingestion pipeline async. Refactor `ImageProcessor.process_image()` to be async.

**Implementation:**
```python
# src/components/ingestion/image_processor.py

class ImageProcessor:
    async def process_image(
        self,
        image: PILImage,
        picture_index: int,
        use_proxy: bool = True,
    ) -> str | None:
        """Process image and generate VLM description (ASYNC)."""
        # ... existing filter logic ...

        # Direct async call (no ThreadPoolExecutor needed!)
        if use_proxy and DASHSCOPE_VLM_AVAILABLE:
            description = await generate_vlm_description_with_dashscope(
                image_path=temp_path,
                vl_high_resolution_images=False,
            )
        else:
            # Fallback to local Ollama VLM (also async)
            description = await generate_vlm_description_with_ollama(
                image_path=temp_path
            )

        return description
```

**Callers Update:**
```python
# src/components/ingestion/langgraph_nodes.py:576

async def image_enrichment_node(state: IngestionState) -> IngestionState:
    processor = ImageProcessor()

    for idx, picture_item in enumerate(doc.pictures):
        pil_image = picture_item.get_image()

        # Now properly async!
        description = await processor.process_image(
            image=pil_image,
            picture_index=idx,
        )
```

**Deliverables:**
- [ ] Refactor `ImageProcessor.process_image()` to async
- [ ] Update all callers to use `await`
- [ ] Remove ThreadPoolExecutor complexity
- [ ] Verify LangGraph pipeline compatibility
- [ ] Update tests to use async fixtures

**Acceptance Criteria:**
- ✅ `ImageProcessor.process_image()` is async
- ✅ No ThreadPoolExecutor usage
- ✅ All callers updated (langgraph_nodes.py)
- ✅ Tests passing with async fixtures
- ✅ Performance unchanged or improved
- ✅ Code complexity reduced (simpler logic)

**Files to Modify:**
- `src/components/ingestion/image_processor.py`
- `src/components/ingestion/langgraph_nodes.py`
- `tests/unit/components/ingestion/test_image_processor.py`
- `tests/integration/components/ingestion/test_langgraph_pipeline.py`

---

### Category 4: Code Quality & Documentation

#### Feature 25.5: MyPy Strict Mode (2 SP)
**Priority:** P3 (Low)
**Duration:** 0.5 day
**Source:** Deferred from Sprint 24 (Feature 24.4 partial)

**Problem:**
MyPy type checking not enforced in CI. Potential type safety issues undetected.

**Solution:**
Enable MyPy strict mode and fix all type errors.

**Implementation:**
```bash
# Run MyPy on src/
mypy src/ --strict

# Fix errors iteratively
# Common fixes:
# 1. Add return type hints: def foo() -> int:
# 2. Add parameter type hints: def bar(x: str, y: int) -> None:
# 3. Fix Optional types: x: str | None
# 4. Add generic types: List[str], Dict[str, int]
```

**Deliverables:**
- [ ] Run MyPy strict mode on `src/`
- [ ] Fix all type errors
- [ ] Add MyPy to CI pipeline (code-quality job)
- [ ] Update `pyproject.toml` with strict MyPy config
- [ ] Document type hints best practices

**Acceptance Criteria:**
- ✅ MyPy strict mode passing (0 errors)
- ✅ CI includes MyPy check
- ✅ All public functions have type hints
- ✅ Generic types used correctly
- ✅ No `# type: ignore` comments (fix issues properly)

**Files to Modify:**
- `.github/workflows/ci.yml` (add MyPy step)
- `pyproject.toml` (enable strict mode)
- Various `src/` files (type hint fixes)

---

#### Feature 25.6: Architecture Documentation Update (2 SP)
**Priority:** P3 (Low)
**Duration:** 0.5 day
**Source:** Deferred from Sprint 24 (Feature 24.8 partial)

**Problem:**
`docs/architecture/CURRENT_ARCHITECTURE.md` and `docs/guides/PRODUCTION_DEPLOYMENT.md` not updated with Sprint 21-24 changes.

**Solution:**
Comprehensive documentation update reflecting current architecture.

**Deliverables:**
- [ ] Update `docs/architecture/CURRENT_ARCHITECTURE.md` with Sprint 21-24 changes
- [ ] Update `docs/guides/PRODUCTION_DEPLOYMENT.md` with new deployment steps
- [ ] Add Prometheus monitoring section to deployment guide
- [ ] Update dependency installation instructions
- [ ] Document lazy import pattern for optional dependencies

**CURRENT_ARCHITECTURE.md Updates:**
```markdown
# Current Architecture (Post-Sprint 24)

## System Overview
- Docling CUDA Container for ingestion (Sprint 21, ADR-027)
- LlamaIndex deprecated to optional dependency (Sprint 21, ADR-028)
- Multi-cloud LLM routing with ANY-LLM (Sprint 23, ADR-033)
- Lazy imports for optional dependencies (Sprint 24)
- Poetry dependency groups for modular installation (Sprint 24)

## Dependency Architecture
### Core Dependencies (~600MB)
- FastAPI, Qdrant, Neo4j, Redis
- Ollama client (local LLM)
- ANY-LLM SDK (multi-cloud routing)
- BGE-M3 embeddings

### Optional Dependencies (5 groups)
1. **ingestion** (~500MB): llama-index, spacy, docling
2. **reranking** (~400MB): sentence-transformers
3. **evaluation** (~600MB): ragas, datasets
4. **graph-analysis** (~150MB): graspologic
5. **ui** (~200MB): gradio

## Installation Patterns
```bash
# Minimal (core only)
poetry install

# With ingestion
poetry install --with ingestion

# Full development
poetry install --with dev,ingestion,reranking

# Production (all features)
poetry install --all-extras
```

## LLM Routing (Sprint 23)
- Tier 1 (Local): Ollama (70% of tasks, free)
- Tier 2 (Cloud): Alibaba Cloud DashScope (high quality, $10/month)
- Tier 3 (Premium): OpenAI GPT-4 (critical tasks, $20/month)

## Monitoring (Sprint 25)
- Prometheus /metrics endpoint
- Grafana dashboards for LLM cost, latency, tokens
- Budget tracking and alerts
```

**PRODUCTION_DEPLOYMENT.md Updates:**
```markdown
# Production Deployment Guide

## Prerequisites
- Docker + NVIDIA Container Toolkit (for Docling CUDA)
- Kubernetes cluster (optional, for scale)
- Prometheus + Grafana (for monitoring)

## Installation Steps
1. Clone repository
2. Install dependencies: `poetry install --all-extras`
3. Configure .env (API keys, database URLs)
4. Start services: `docker-compose up -d`
5. Run migrations
6. Verify /metrics endpoint: `curl http://localhost:8000/metrics`

## Monitoring Setup
1. Configure Prometheus to scrape /metrics
2. Import Grafana dashboard: `dashboards/grafana/llm_monitoring.json`
3. Set up budget alerts (>80% monthly spend)

## Performance Tuning
- Poetry cache for faster CI (85% speedup)
- Lazy imports for optional dependencies
- Minimal dependency installation for specific workloads
```

**Acceptance Criteria:**
- ✅ CURRENT_ARCHITECTURE.md reflects Sprint 21-24 changes
- ✅ PRODUCTION_DEPLOYMENT.md includes monitoring setup
- ✅ Dependency installation patterns documented
- ✅ Lazy import pattern explained
- ✅ All docs reviewed and accurate

**Files to Create/Modify:**
- `docs/architecture/CURRENT_ARCHITECTURE.md`
- `docs/guides/PRODUCTION_DEPLOYMENT.md`
- `docs/guides/MONITORING.md` (NEW)
- `docs/guides/DEPENDENCY_MANAGEMENT.md` (NEW)

---

## 🔧 Technical Debt Resolution Summary

### Deferred from Sprint 24

| Feature | SP | Priority | Sprint 25 Status |
|---------|----|----|---------|
| 24.1: Prometheus Metrics | 5 | P1 | ➡️ **Feature 25.1** |
| 24.2: Token Tracking | 3 | P2 | ➡️ **Feature 25.3** |
| 24.3: Async/Sync Bridge | 5 | P2 | ➡️ **Feature 25.4** |
| 24.4: MyPy Strict (partial) | 2 | P3 | ➡️ **Feature 25.5** |
| 24.7: Integration Tests | 5 | P1 | ➡️ **Feature 25.2** |
| 24.8: Documentation (partial) | 2 | P3 | ➡️ **Feature 25.6** |

**Total Deferred:** 22 SP

### Still Deferred (Future Sprints)

| ID | Description | Priority | Effort | Deferred To |
|----|-------------|----------|--------|-------------|
| TD-23.1 | ANY-LLM Full Integration | P2 | 8 SP | Sprint 26+ |
| TD-23.2 | DashScope VLM Routing | P3 | 5 SP | Sprint 26+ |
| TD-G.1 | Cross-platform Dev Env | P2 | 1 week | Sprint 27+ |

---

## 📊 Sprint 25 Timeline

### Week 1 (Days 1-3): Production Monitoring & Tests

**Day 1: Feature 25.1 - Prometheus Metrics** (5 SP)
- Morning: Implement `src/core/metrics.py`
- Afternoon: Integrate with LLM proxy + cost tracker
- Evening: Create Grafana dashboard

**Day 2: Feature 25.2 - Integration Tests** (5 SP)
- Morning: Write 6 node-level integration tests
- Afternoon: Write E2E pipeline test
- Evening: Fix test failures, validate coverage

**Day 3: Feature 25.3 - Token Tracking** (3 SP)
- Morning: Parse `usage` field from API responses
- Afternoon: Update cost tracker + Prometheus metrics
- Evening: Write unit tests

### Week 1 (Days 4-5): Code Quality & Documentation

**Day 4: Feature 25.4 - Async/Sync Bridge** (5 SP)
- Morning: Refactor `ImageProcessor` to async
- Afternoon: Update callers (langgraph_nodes.py)
- Evening: Update tests, verify no regressions

**Day 5: Features 25.5 + 25.6** (4 SP)
- Morning: MyPy strict mode fixes
- Afternoon: Architecture documentation updates
- Evening: Final review, commit all changes

---

## 🎯 Sprint 25 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Prometheus Metrics | /metrics endpoint live | curl test |
| Grafana Dashboard | Operational | Manual inspection |
| Integration Test Coverage | >80% | pytest --cov |
| Token Tracking Accuracy | 100% (no 50/50 split) | Database validation |
| Async/Sync Bridge | Removed | Code review |
| MyPy Strict Mode | 0 errors | mypy src/ --strict |
| Documentation Completeness | 100% | Manual review |

---

## 📋 Priority Matrix

```
┌───────────────┬────────────────────────┬────────────────────────┐
│               │  Low Effort (<1 day)   │ High Effort (>1 day)   │
├───────────────┼────────────────────────┼────────────────────────┤
│ High Impact   │ Feature 25.3 (Token)   │ Feature 25.1 (Metrics) │
│               │ Feature 25.6 (Docs)    │ Feature 25.2 (Tests)   │
├───────────────┼────────────────────────┼────────────────────────┤
│ Medium Impact │ Feature 25.5 (MyPy)    │ Feature 25.4 (Async)   │
└───────────────┴────────────────────────┴────────────────────────┘
```

---

## 🔄 Next Steps After Sprint 25

**Sprint 26 Candidates:**
1. ANY-LLM Full Integration (TD-23.1, 8 SP) - If ANY-LLM adds VLM support
2. DashScope VLM Routing Unification (TD-23.2, 5 SP) - Unified routing
3. Advanced Features:
   - Multi-hop query optimization
   - Profiling module completion
   - Enhanced semantic deduplication

**Sprint 27 Candidates:**
1. Cross-platform Development (TD-G.1, 1 week) - Linux CI/CD
2. Kubernetes Production Deployment
3. Multi-tenant Cost Tracking

---

## ✅ Sprint 25 Completion Criteria

- ✅ Prometheus /metrics endpoint operational with LLM-specific metrics
- ✅ Grafana dashboard displaying cost, latency, and token metrics
- ✅ Integration tests for LangGraph pipeline (>80% coverage)
- ✅ Token tracking accuracy improved (accurate input/output split)
- ✅ Async/sync bridge refactored (no ThreadPoolExecutor)
- ✅ MyPy strict mode passing (0 errors)
- ✅ Architecture documentation updated (CURRENT_ARCHITECTURE.md, PRODUCTION_DEPLOYMENT.md)
- ✅ All deferred Sprint 24 features completed
- ✅ Test coverage >80% maintained
- ✅ No regressions introduced

---

**Sprint 25 Objectives:** Production monitoring, integration tests, deferred Sprint 24 features ✅
**Next Sprint:** Sprint 26 - ANY-LLM Full Integration & Advanced Features

**Last Updated:** 2025-11-14
**Author:** Claude Code (Backend Agent)
**Prerequisites:** Sprint 24 complete (Dependency Optimization & CI Performance)
**Story Points:** 30 SP (22 SP deferred from Sprint 24 + 8 SP new work)
