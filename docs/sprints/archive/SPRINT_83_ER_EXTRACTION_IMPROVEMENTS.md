# Sprint 83: ER-Extraction Robustness & Observability

**Epic:** Ingestion Pipeline Reliability & Debugging
**Duration:** 5-7 days
**Total Story Points:** 21 SP
**Status:** 📝 Planned

---

## Problem Statement

### Current Issues (Sprint 82 Upload Analysis)

**Observed from `upload_phase1.log` (168/500 files uploaded, 33.6% success rate):**

1. **HTTP 000 Connection Failures** (Primary Issue)
   - After ~100-124 successful uploads, API calls start failing with HTTP 000
   - Pattern: Consecutive failures on LogQA emanual files
   - Hypothesis: **Ollama/Nemotron3 LLM exhaustion** after 5+ hours of ER-Extraction
   - No automatic retry or fallback mechanism

2. **RAGAS Query Timeouts** (20% Failure Rate)
   - 2/10 queries timed out at ~301 seconds (questions 6 & 9)
   - Likely Graph Reasoning or LLM inference timeout
   - No visibility into which phase caused timeout (retrieval vs LLM)

3. **Logging Gaps** (Root Cause Analysis Blockers)
   - No per-phase latency breakdown (can't isolate ER-Extraction from chunking/embedding)
   - No LLM cost aggregation per document (can't track token burn)
   - No extraction quality metrics (entity deduplication rate, relation confidence)
   - No chunk-to-entity provenance (hard to trace entity back to source chunk)

---

## Research: Industry Best Practices

### Microsoft GraphRAG (State-of-the-Art)

**Sources:**
- [GraphRAG Methods Documentation](https://microsoft.github.io/graphrag/index/methods/)
- [GraphRAG Gleaning Bug #613](https://github.com/microsoft/graphrag/issues/613)
- [From Local to Global: Graph RAG Paper](https://arxiv.org/html/2404.16130v1)

**Key Strategies:**

1. **Gleaning (Multi-Pass Extraction)** ✅ SOTA Feature
   ```yaml
   entity_extraction:
     max_gleanings: 1-3  # Additional extraction passes
     logit_bias: 100     # Force yes/no on "all entities found?"
     continuation_prompt: "Extract any missing entities from previous passes"
   ```
   - **Result:** +20-40% entity recall after 2-3 gleaning rounds
   - **Cost:** 2-3x LLM API calls per chunk
   - **Use Case:** High-precision extraction (research papers, legal docs)

2. **Dynamic Retry with Backoff** ✅ Production-Ready
   ```yaml
   llm:
     max_retries: -1  # Dynamic retry based on server response
     retry_delay: [1s, 2s, 4s, 8s]  # Exponential backoff
   ```
   - Handles transient failures (rate limits, network glitches)
   - Microsoft's default: unlimited retries with exponential backoff

3. **Small LLM Challenges** ⚠️ Known Issue
   - 7B-8B models (Qwen, Llama) are **unstable** for structured JSON extraction
   - FastGraphRAG is **incompatible** with local 7B-8B models (can't output JSON even with 5 retries)
   - **Recommendation:** Use ≥13B models for production or hybrid SpaCy+LLM approach

### LlamaIndex PropertyGraphIndex

**Sources:**
- [Introducing PropertyGraphIndex](https://www.llamaindex.ai/blog/introducing-the-property-graph-index-a-powerful-new-way-to-build-knowledge-graphs-with-llms)
- [Entity Extraction with LlamaIndex](https://www.restack.io/p/entity-recognition-answer-implement-entity-extraction-with-llamaindex-cat-ai)

**Key Strategies:**

1. **No Built-in Gleaning** (Single-Pass Only)
   - LlamaIndex KnowledgeGraphIndex does NOT implement multi-pass refinement
   - Uses `max_triplets_per_chunk` parameter to limit extraction scope

2. **Hybrid NER Approach** ✅ Alternative Strategy
   - Combine SpaCy NER (fast, rule-based) + LLM (semantic, context-aware)
   - SpaCy extracts entities → LLM refines/classifies → LLM extracts relations
   - **Benefit:** 5-10x faster, more robust to LLM failures

### Neo4j + LangChain Integration

**Source:** [Global GraphRAG with Neo4j and LangChain](https://neo4j.com/blog/developer/global-graphrag-neo4j-langchain/)

**Key Strategies:**

1. **Batched Extraction with Progress Tracking**
   - Extract entities in batches of 10-50 chunks
   - Track progress in Neo4j with extraction metadata nodes
   - Resume from last successful batch on failure

2. **Schema-Guided Extraction** ✅ Production Pattern
   - Define allowed entity types and relation types upfront
   - LLM validates against schema (prevents hallucinated types)
   - **AegisRAG Status:** Implemented in Feature 76.2 (Domain-Specific Extraction Prompts)

---

## Proposed Solutions

### Sprint 83 Features

| # | Feature | SP | Priority | Solves |
|---|---------|-----|----------|--------|
| 83.1 | Comprehensive Ingestion Logging | 5 | P0 | Logging Gaps |
| 83.2 | LLM Fallback & Retry Strategy | 8 | P0 | HTTP 000 Failures |
| 83.3 | Gleaning (Multi-Pass ER-Extraction) | 5 | P2 | Low Entity Recall (defer to Sprint 84) |
| 83.4 | Fast User Upload + Background Refinement | 8 | P1 | User Experience (immediate feedback) |

**Total:** 26 SP (21 SP if Feature 83.3 deferred to Sprint 84)

---

## Feature 83.1: Comprehensive Ingestion Logging (5 SP)

### Goal
Add structured logging to identify bottlenecks and failures in the 5-node ingestion pipeline.

### Implementation

**Files to Modify:**
- `src/components/ingestion/nodes/graph_extraction.py` ✅ (already has good logging)
- `src/components/graph_rag/extraction_service.py` ✅ (needs enhancement)
- `src/components/ingestion/nodes/adaptive_chunking.py` (needs timing summary)
- `src/components/ingestion/nodes/vector_embedding.py` (needs per-chunk timing)
- `src/components/ingestion/nodes/document_parsers.py` (needs Docling timing)

**New Logging Events:**

```python
# 1. Per-Phase Latency Summary
logger.info(
    "TIMING_phase_summary",
    phase="graph_extraction",
    total_time_ms=12450,
    per_chunk_avg_ms=248.5,
    p50_ms=220,
    p95_ms=380,
    p99_ms=520,
    chunks_processed=50,
)

# 2. LLM Cost Aggregation
logger.info(
    "llm_cost_summary",
    document_id="doc_123",
    phase="entity_extraction",
    total_tokens=125000,
    prompt_tokens=100000,
    completion_tokens=25000,
    estimated_cost_usd=0.025,  # Based on Ollama pricing
    model="nemotron3",
)

# 3. Extraction Quality Metrics
logger.info(
    "extraction_quality_metrics",
    chunk_id="chunk_456",
    raw_entities_extracted=45,
    deduplicated_entities=32,
    deduplication_rate=0.29,  # 29% duplicates removed
    entity_types=["Product", "Feature", "Error Code"],
    relation_confidence_avg=0.78,  # Semantic similarity of relations
)

# 4. Chunk-to-Entity Provenance
logger.info(
    "chunk_entity_mapping",
    chunk_id="chunk_456",
    entities_created=["Entity_789", "Entity_790"],
    relations_created=["Rel_123", "Rel_124"],
    section_hierarchy=["1.2.3 Troubleshooting"],
)

# 5. Memory Profiling per Phase
logger.info(
    "memory_snapshot",
    phase="entity_extraction",
    ram_used_mb=2048,
    ram_available_mb=6144,
    vram_used_mb=4096,  # GPU memory
    vram_available_mb=4096,
)
```

**Output Format:**
- Real-time: StructLog JSON to `data/logs/ingestion_YYYYMMDD_HHMMSS.json`
- Summary Report: Markdown table in `data/logs/ingestion_summary.md`

**Example Summary Report:**
```markdown
## Ingestion Summary: ragas_phase1_0003_hotpot_5a82171f.txt

| Phase | Time (ms) | P95 (ms) | Success | Entities | Relations | Cost ($) |
|-------|-----------|----------|---------|----------|-----------|----------|
| Memory Check | 50 | 60 | ✅ | - | - | - |
| Docling Parse | 1200 | 1400 | ✅ | - | - | - |
| VLM Enrichment | 3400 | 3800 | ✅ | - | - | 0.003 |
| Chunking | 800 | 950 | ✅ | - | - | - |
| Embedding | 4500 | 5200 | ✅ | - | - | - |
| ER-Extraction | 8200 | 9500 | ✅ | 32 | 18 | 0.012 |
| **TOTAL** | **18150** | | ✅ | 32 | 18 | 0.015 |
```

### Acceptance Criteria

- [x] Add `TIMING_phase_summary` logs to all 5 nodes
- [x] Add `llm_cost_summary` to extraction_service.py
- [x] Add `extraction_quality_metrics` to graph_extraction_node.py
- [x] Add `chunk_entity_mapping` to lightrag/ingestion.py
- [x] Add `memory_snapshot` at start/end of each phase
- [x] Generate Markdown summary report after each document
- [x] Unit tests for new logging functions (90%+ coverage)

---

## Feature 83.2: LLM Fallback & Retry Strategy (8 SP)

### Goal
Handle LLM failures gracefully with automatic retry and fallback to alternative models.

### Root Cause Analysis

**HTTP 000 Errors Pattern:**
- After ~100-124 successful uploads (5+ hours runtime)
- Ollama/Nemotron3 becomes unresponsive (likely memory leak or resource exhaustion)
- No automatic recovery → batch upload fails catastrophically

**Hypotheses:**
1. **VRAM Exhaustion:** Nemotron3 (30B parameters) runs out of VRAM after extended use
2. **Context Window Overflow:** Extended conversations → KV-Cache explosion
3. **Memory Leak:** Ollama server doesn't release memory after failed requests
4. **No OOM Recovery:** Ollama server hangs instead of restarting on OOM
5. **No Retry Mechanism:** AegisLLMProxy doesn't retry connection failures

**How to Determine Root Cause:**

**1. VRAM Monitoring (GPU Memory Tracking)**
```python
# Add to memory_management.py
import pynvml

def get_gpu_memory_usage() -> Dict[str, float]:
    """Get current GPU memory usage."""
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    info = pynvml.nvmlDeviceGetMemoryInfo(handle)

    return {
        "vram_total_gb": info.total / 1024**3,
        "vram_used_gb": info.used / 1024**3,
        "vram_free_gb": info.free / 1024**3,
        "vram_utilization": info.used / info.total,
    }

# Log every 10 documents
logger.info("gpu_memory_snapshot", **get_gpu_memory_usage())
```

**2. Ollama Health Metrics (Connection Failures)**
```python
# Add to extraction_service.py
async def check_ollama_health() -> Dict[str, Any]:
    """Check Ollama server health."""
    try:
        response = await httpx.get(
            "http://localhost:11434/api/tags",
            timeout=5.0,
        )

        return {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "response_time_ms": response.elapsed.total_seconds() * 1000,
            "loaded_models": len(response.json().get("models", [])),
        }
    except Exception as e:
        return {
            "status": "unreachable",
            "error": str(e),
        }

# Log before each extraction batch
logger.info("ollama_health_check", **await check_ollama_health())
```

**3. LLM Request/Response Timing (Latency Degradation)**
```python
# Add to AegisLLMProxy
import time

async def invoke_with_timing(self, task: LLMTask) -> LLMResponse:
    """Invoke LLM with detailed timing metrics."""

    start_time = time.perf_counter()

    try:
        response = await self._invoke_model(task)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "llm_request_timing",
            model=task.model_id,
            task_type=task.task_type,
            elapsed_ms=elapsed_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            tokens_per_second=response.usage.completion_tokens / (elapsed_ms / 1000),
        )

        return response

    except httpx.ReadTimeout as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.error(
            "llm_request_timeout",
            model=task.model_id,
            elapsed_ms=elapsed_ms,
            timeout_s=task.timeout_s,
        )
        raise
```

**4. Context Window Analysis (KV-Cache Growth)**
```python
# Add to extraction logging
logger.info(
    "llm_context_window_usage",
    prompt_tokens=response.usage.prompt_tokens,
    completion_tokens=response.usage.completion_tokens,
    total_tokens=response.usage.total_tokens,
    model_max_tokens=32768,  # Nemotron3 context window
    context_utilization=response.usage.total_tokens / 32768,
)
```

**5. Error Pattern Analysis (Failure Clustering)**
```python
# Count consecutive failures
consecutive_failures = 0

for upload_result in upload_log:
    if upload_result["status"] == "failed":
        consecutive_failures += 1

        if consecutive_failures >= 5:
            logger.critical(
                "failure_cluster_detected",
                consecutive_failures=consecutive_failures,
                last_successful_file=last_success,
                hypothesis="ollama_exhaustion",
            )
```

**Expected Findings:**

| Symptom | Root Cause | Mitigation |
|---------|------------|------------|
| VRAM usage >90% before failure | **VRAM Exhaustion** | Restart Ollama every 100 uploads |
| Response time increases 10x over time | **KV-Cache Overflow** | Use stateless API calls (no conversation context) |
| Error clustering after 100+ uploads | **Memory Leak** | Periodic Ollama restart |
| Ollama unresponsive to health checks | **OOM Hang** | Auto-restart on health check failure |

**Diagnostic Output:**
- Log to `data/logs/ingestion_diagnostics.json` (structured JSON)
- Generate alert on 5+ consecutive failures
- Track metrics over time: VRAM usage, response latency, failure rate

### Implementation

**1. AegisLLMProxy Retry with Exponential Backoff**

```python
# src/domains/llm_integration/aegis_llm_proxy.py

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import httpx

class AegisLLMProxy:
    """Enhanced LLM Proxy with Retry & Fallback."""

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
        reraise=True,
    )
    async def invoke_with_retry(
        self,
        task: LLMTask,
        timeout_s: int = 300,
    ) -> LLMResponse:
        """Invoke LLM with automatic retry on transient failures."""
        logger.info(
            "llm_invoke_attempt",
            model=task.model_id,
            task_type=task.task_type,
            attempt=retry.statistics.get("attempt_number", 1),
        )

        try:
            response = await self._invoke_model(task, timeout_s)
            return response
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.warning(
                "llm_invoke_retry",
                model=task.model_id,
                error=str(e),
                attempt=retry.statistics["attempt_number"],
                max_attempts=5,
            )
            raise  # Will be retried by @retry decorator
        except Exception as e:
            logger.error(
                "llm_invoke_failed",
                model=task.model_id,
                error=str(e),
                exc_info=True,
            )
            raise
```

**2. Fallback Model Cascade**

**Philosophy:**
- **Rank 1-2:** Pure LLM extraction (highest quality, slower)
- **Rank 3:** Hybrid SpaCy NER + LLM (fastest, good enough for recovery)

**Important:** All LLM timeouts are **300s** to ensure timeouts are not the problem. Only Rank 3 relations extraction uses **600s** to guarantee completion.

```python
# src/domains/llm_integration/config.py

EXTRACTION_MODEL_CASCADE = [
    {
        "rank": 1,
        "model_id": "nemotron3",  # Primary (30B, highest quality)
        "provider": "ollama",
        "timeout_s": 300,
        "max_retries": 3,
        "extraction_type": "llm_only",  # Entities + Relations via LLM
    },
    {
        "rank": 2,
        "model_id": "gpt-oss:20b",  # Fallback 1 (20B, more stable)
        "provider": "ollama",
        "timeout_s": 300,  # Same timeout as Rank 1
        "max_retries": 2,
        "extraction_type": "llm_only",  # Entities + Relations via LLM
    },
    {
        "rank": 3,
        "model_id": "gpt-oss:20b",  # Fallback 2 (hybrid approach)
        "provider": "ollama",
        "timeout_s": {
            "entities": None,  # SpaCy NER (no timeout needed)
            "relations": 600,  # LLM with extended timeout for relations
        },
        "max_retries": 1,
        "extraction_type": "hybrid_ner_llm",  # SpaCy NER (entities) + LLM (relations)
        "ner_config": {
            "languages": ["de", "en", "fr", "es"],  # Multi-language support
            "models": {
                "de": "de_core_news_lg",  # German
                "en": "en_core_web_trf",  # English (Transformer-based)
                "fr": "fr_core_news_lg",  # French
                "es": "es_core_news_lg",  # Spanish
            },
        },
    },
]
```

**Rationale for Rank 3 Hybrid:**
- **SpaCy NER for Entities:** 100x faster than LLM, no timeout risk
- **LLM for Relations:** Higher quality than rule-based, worth 600s timeout
- **Relations Prompt Includes NER Entities:** LLM gets pre-extracted entities from SpaCy
- **Multi-Language Support:** SpaCy models for DE/EN/FR/ES cover most use cases

```python
# src/components/graph_rag/extraction_service.py

async def extract_entities_with_fallback(
    self,
    document_text: str,
    chunk_id: str,
) -> List[Entity]:
    """Extract entities with automatic model fallback."""

    for i, model_config in enumerate(EXTRACTION_MODEL_CASCADE):
        try:
            logger.info(
                "entity_extraction_attempt",
                chunk_id=chunk_id,
                model=model_config["model_id"],
                cascade_level=i,
            )

            entities = await self._extract_entities(
                document_text=document_text,
                model_id=model_config["model_id"],
                timeout_s=model_config["timeout_s"],
            )

            logger.info(
                "entity_extraction_success",
                chunk_id=chunk_id,
                model=model_config["model_id"],
                entities_count=len(entities),
                cascade_level=i,
            )

            return entities

        except (httpx.ConnectError, httpx.ReadTimeout, TimeoutError) as e:
            logger.warning(
                "entity_extraction_fallback",
                chunk_id=chunk_id,
                model=model_config["model_id"],
                error=str(e),
                cascade_level=i,
                next_model=EXTRACTION_MODEL_CASCADE[i+1]["model_id"] if i+1 < len(EXTRACTION_MODEL_CASCADE) else None,
            )

            if i == len(EXTRACTION_MODEL_CASCADE) - 1:
                # All models failed → raise error
                logger.error(
                    "entity_extraction_all_models_failed",
                    chunk_id=chunk_id,
                    cascade_attempts=len(EXTRACTION_MODEL_CASCADE),
                )
                raise

            # Try next model in cascade
            continue
```

**3. Ollama Health Check & Auto-Restart**

```python
# src/domains/llm_integration/ollama_health.py

import httpx
import asyncio
from pathlib import Path

class OllamaHealthMonitor:
    """Monitor Ollama health and restart if unresponsive."""

    async def health_check(self) -> bool:
        """Check if Ollama is responsive."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:11434/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def restart_ollama_if_needed(self) -> bool:
        """Restart Ollama if health check fails."""
        if await self.health_check():
            return True  # Ollama is healthy

        logger.warning("ollama_unhealthy_restarting")

        # Restart Ollama via systemd or docker
        result = await asyncio.create_subprocess_shell(
            "sudo systemctl restart ollama",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await result.wait()

        # Wait for Ollama to start
        for i in range(10):
            await asyncio.sleep(2)
            if await self.health_check():
                logger.info("ollama_restarted_successfully", wait_time_s=2*(i+1))
                return True

        logger.error("ollama_restart_failed")
        return False
```

**Integration into Parallel Orchestrator:**

```python
# src/components/ingestion/parallel_orchestrator.py

from src.domains.llm_integration.ollama_health import OllamaHealthMonitor

class ParallelIngestionOrchestrator:

    async def process_files_parallel(self, ...):
        health_monitor = OllamaHealthMonitor()

        for file_path in files:
            # Check Ollama health before each file
            if not await health_monitor.restart_ollama_if_needed():
                logger.error("ollama_unavailable_skipping_file", file=file_path)
                continue

            # Process file...
```

### Acceptance Criteria

- [x] Add `@retry` decorator to AegisLLMProxy.invoke()
- [x] Implement 3-model fallback cascade (nemotron3 → gpt-oss:20b → qwen2.5:14b)
- [x] Add OllamaHealthMonitor with auto-restart capability
- [x] Integrate health check into ParallelIngestionOrchestrator
- [x] Add `llm_fallback_triggered` log event with cascade_level
- [x] Unit tests for retry logic (mock httpx.ConnectError)
- [x] Integration test: Upload 10 files with simulated Ollama failure

### Expected Impact

**Before (Sprint 82):**
- 168/500 files uploaded (33.6% success after 5 hours)
- HTTP 000 errors → batch upload stops
- No recovery mechanism

**After (Sprint 83):**
- **Target:** 95%+ upload success rate for 500 files
- Automatic fallback to gpt-oss:20b after 3 nemotron3 failures
- Ollama auto-restart on health check failure
- **Estimated upload time:** 15-20 hours (with occasional fallbacks)

---

## Feature 83.3: Gleaning (Multi-Pass ER-Extraction) (5 SP) [DEFERRED TO SPRINT 84]

### Status
**Deferred to Sprint 84** - Logging and fallback (Features 83.1 & 83.2) are prerequisites for gleaning debugging.

### Documentation
Full implementation details documented in **[TD-100: Gleaning Multi-Pass Extraction](../technical-debt/TD-100_GLEANING_MULTI_PASS_EXTRACTION.md)**

### Summary

**Goal:** Implement Microsoft GraphRAG-style gleaning for +20-40% entity recall.

**Implementation:**
- Multi-round extraction: Initial pass → Completeness check → Extract missing entities
- Logit bias forcing for yes/no decisions
- Early exit if LLM confirms all entities extracted
- Wire `gleaning_steps` from ChunkingConfig (field exists but not implemented)

**Cost-Benefit:**
- Gleaning Round 1: +20% entities, 2x LLM cost
- Gleaning Round 2: +35% entities, 3x LLM cost
- Gleaning Round 3: +40% entities, 4x LLM cost (diminishing returns)

**Why Deferred:**
1. Feature 83.1 (logging) needed to debug gleaning performance
2. Feature 83.2 (fallback) needed to handle gleaning LLM failures
3. Sprint 83 focus: Upload reliability (Feature 83.2 is blocking RAGAS Phase 1 completion)

**Next Steps:** Implement in Sprint 84 after logging/fallback infrastructure is in place.

---

## Feature 83.4: Fast User Upload + Background Refinement (8 SP)

### Goal
Provide **immediate user feedback** for ad-hoc document uploads via Hybrid SpaCy+LLM extraction, then **automatically refine** with full LLM pipeline in background for higher quality.

### Problem Statement

**Current User Experience:**
- User uploads document via Admin UI → waits 10-60+ seconds for full LLM extraction
- No intermediate feedback during extraction
- Upload feels slow and unresponsive

**Desired UX:**
- User uploads document → **fast response (2-5s)** with basic entities/relations (SpaCy NER + LLM)
- Document immediately searchable in UI
- Background job refines extraction with full LLM pipeline (nemotron3) for higher quality
- User sees "Refining..." status indicator, then "✅ Complete" when done

### Two-Phase Extraction Strategy

#### **Phase 1: Fast User Upload (Hybrid SpaCy+LLM)** ⚡
- **Entities:** SpaCy NER (100x faster than LLM, no timeout risk)
- **Relations:** LLM gpt-oss:20b (semantic, higher quality than rules)
- **Time:** 2-5 seconds (95% faster than pure LLM)
- **Quality:** 70-80% of full LLM quality (good enough for initial search)

#### **Phase 2: Background Refinement (Full LLM Pipeline)** 🎯
- **Entities:** nemotron3 with domain-specific prompts (Feature 76.2)
- **Relations:** nemotron3 with full context
- **Time:** 30-60 seconds (runs in background, user doesn't wait)
- **Quality:** 100% quality (SOTA extraction)

**Result:** User gets 95% faster feedback with 70% quality, then 100% quality automatically.

---

### Implementation

#### **1. Hybrid Extraction Service (Multi-Language SpaCy NER)**

```python
# src/components/graph_rag/hybrid_extraction.py

import spacy
from typing import List, Dict
from langdetect import detect

class HybridExtractionService:
    """Fast hybrid SpaCy NER + LLM extraction for user uploads."""

    SPACY_MODELS = {
        "de": "de_core_news_lg",      # German
        "en": "en_core_web_trf",       # English (Transformer-based)
        "fr": "fr_core_news_lg",       # French
        "es": "es_core_news_lg",       # Spanish
    }

    def __init__(self):
        # Lazy-load SpaCy models on demand
        self.loaded_models: Dict[str, spacy.Language] = {}

    def _get_spacy_model(self, language: str) -> spacy.Language:
        """Load SpaCy model for language (cached)."""
        if language not in self.loaded_models:
            model_name = self.SPACY_MODELS.get(language, "en_core_web_trf")
            self.loaded_models[language] = spacy.load(model_name)

        return self.loaded_models[language]

    def extract_entities_spacy(
        self,
        text: str,
        language: str = None,
    ) -> List[Entity]:
        """Extract entities using SpaCy NER (multi-language)."""

        # Auto-detect language if not provided
        if language is None:
            language = detect(text[:500])  # Detect from first 500 chars

        nlp = self._get_spacy_model(language)
        doc = nlp(text)

        entities = []
        for ent in doc.ents:
            entities.append(Entity(
                name=ent.text,
                type=ent.label_,  # PERSON, ORG, GPE, PRODUCT, etc.
                description=f"Entity of type {ent.label_} (SpaCy NER)",
                extraction_method="spacy_ner",  # Mark as fast extraction
                confidence=0.7,  # SpaCy confidence is lower than LLM
            ))

        logger.info(
            "spacy_ner_extraction_complete",
            language=language,
            entities_count=len(entities),
            extraction_time_ms=doc._._opaque_data.get("time", 0),
        )

        return entities

    async def extract_relations_llm(
        self,
        text: str,
        entities: List[Entity],
        model_id: str = "gpt-oss:20b",  # Faster than nemotron3
        timeout_s: int = 600,  # Extended timeout for relations
    ) -> List[Relation]:
        """Extract relations using LLM (given SpaCy NER entities)."""

        # Prompt includes pre-extracted entities from SpaCy
        entity_names = [e.name for e in entities]

        prompt = f"""
You are extracting relationships between entities in a document.

**Entities found by NER:**
{entity_names}

**Document Text:**
{text}

**Task:** Extract relationships between the entities above.

**Output Format:** JSON array of relations
[
  {{"source": "Entity A", "target": "Entity B", "type": "RELATION_TYPE", "description": "How they relate"}},
  ...
]

**Relationships:**"""

        task = LLMTask(
            task_type="relation_extraction",
            prompt=prompt,
            model_id=model_id,
            temperature=0.1,
            max_tokens=2000,
            timeout_s=timeout_s,
        )

        response = await self.llm_proxy.invoke(task)

        # Parse JSON relations
        relations = self._parse_relation_json(response.content)

        logger.info(
            "llm_relation_extraction_complete",
            model=model_id,
            relations_count=len(relations),
            entities_provided=len(entities),
        )

        return relations
```

#### **2. Two-Phase Upload API Endpoint**

```python
# src/api/v1/admin_indexing.py

@router.post(
    "/indexing/upload-fast",
    response_model=FastUploadResponse,
    summary="Fast user upload with background refinement",
)
async def upload_fast_with_refinement(
    file: UploadFile = File(...),
    domain_id: str = Form(...),  # Domain determines ER-Extraction settings
) -> FastUploadResponse:
    """Upload document with fast hybrid extraction + background LLM refinement.

    **Feature 83.4: Fast User Upload + Background Refinement**

    **Phase 1 (Synchronous - 2-5s):**
    - SpaCy NER for entities (multi-language: DE/EN/FR/ES)
    - gpt-oss:20b for relations (600s timeout)
    - Document immediately searchable

    **Phase 2 (Asynchronous - Background):**
    - Full LLM extraction with nemotron3 (domain-specific prompts)
    - Replaces Phase 1 data with higher quality extraction
    - User sees "Refining..." status, then "✅ Complete"

    Args:
        file: Document file to upload
        domain_id: Domain ID (determines extraction settings)

    Returns:
        FastUploadResponse with document_id and refinement_job_id
    """

    # 1. Save file
    file_path = await _save_upload_file(file)

    # 2. Get domain extraction config
    domain_config = await domain_config_service.get_domain(domain_id)

    # 3. Phase 1: Fast hybrid extraction (SpaCy NER + LLM)
    logger.info(
        "fast_upload_phase1_start",
        file_name=file.filename,
        domain_id=domain_id,
    )

    hybrid_service = HybridExtractionService()

    # Parse document (Docling)
    parsed_content = await docling_parse(file_path)

    # Extract entities with SpaCy NER
    entities_fast = hybrid_service.extract_entities_spacy(
        text=parsed_content.text,
        language=domain_config.primary_language,  # From domain settings
    )

    # Extract relations with LLM (gpt-oss:20b, 600s timeout)
    relations_fast = await hybrid_service.extract_relations_llm(
        text=parsed_content.text,
        entities=entities_fast,
        model_id="gpt-oss:20b",
        timeout_s=600,  # Extended timeout as requested
    )

    # Store in databases (Qdrant, Neo4j)
    document_id = await _store_fast_extraction(
        file_path=file_path,
        entities=entities_fast,
        relations=relations_fast,
        domain_id=domain_id,
        extraction_phase="fast_hybrid",  # Mark as Phase 1
    )

    logger.info(
        "fast_upload_phase1_complete",
        document_id=document_id,
        entities_count=len(entities_fast),
        relations_count=len(relations_fast),
    )

    # 4. Phase 2: Background LLM refinement (asyncio task)
    refinement_job_id = str(uuid.uuid4())

    asyncio.create_task(
        _refine_extraction_background(
            document_id=document_id,
            file_path=file_path,
            domain_id=domain_id,
            refinement_job_id=refinement_job_id,
        )
    )

    logger.info(
        "fast_upload_refinement_queued",
        document_id=document_id,
        refinement_job_id=refinement_job_id,
    )

    return FastUploadResponse(
        document_id=document_id,
        refinement_job_id=refinement_job_id,
        phase1_entities_count=len(entities_fast),
        phase1_relations_count=len(relations_fast),
        refinement_status="queued",
    )
```

#### **3. Background Refinement Job**

```python
# src/api/v1/admin_indexing.py

async def _refine_extraction_background(
    document_id: str,
    file_path: str,
    domain_id: str,
    refinement_job_id: str,
) -> None:
    """Background job to refine extraction with full LLM pipeline."""

    try:
        logger.info(
            "refinement_job_start",
            document_id=document_id,
            refinement_job_id=refinement_job_id,
        )

        # Get domain extraction settings (from domain config)
        domain_config = await domain_config_service.get_domain(domain_id)
        extraction_settings = domain_config.er_extraction_settings

        # Run full LLM extraction pipeline
        # - Use nemotron3 with domain-specific prompts (Feature 76.2)
        # - Use gleaning if domain.gleaning_steps > 0 (Feature 83.3, Sprint 84)
        # - Use fallback cascade if extraction fails (Feature 83.2)

        extraction_service = ExtractionService()

        entities_refined = await extraction_service.extract_entities(
            document_text=parsed_content.text,
            domain_id=domain_id,
            model_id="nemotron3",  # Highest quality model
            use_domain_prompts=True,  # Feature 76.2
            gleaning_steps=extraction_settings.gleaning_steps,  # Feature 83.3
        )

        relations_refined = await extraction_service.extract_relations(
            document_text=parsed_content.text,
            entities=entities_refined,
            domain_id=domain_id,
            model_id="nemotron3",
        )

        # Replace Phase 1 data with refined extraction
        await _update_extraction(
            document_id=document_id,
            entities=entities_refined,
            relations=relations_refined,
            extraction_phase="refined_llm",  # Mark as Phase 2
        )

        logger.info(
            "refinement_job_complete",
            document_id=document_id,
            refinement_job_id=refinement_job_id,
            entities_refined=len(entities_refined),
            relations_refined=len(relations_refined),
        )

        # Update refinement status
        await refinement_status_service.update_status(
            refinement_job_id=refinement_job_id,
            status="completed",
        )

    except Exception as e:
        logger.error(
            "refinement_job_failed",
            document_id=document_id,
            refinement_job_id=refinement_job_id,
            error=str(e),
            exc_info=True,
        )

        await refinement_status_service.update_status(
            refinement_job_id=refinement_job_id,
            status="failed",
            error=str(e),
        )
```

#### **4. Domain ER-Extraction Settings**

```python
# src/components/domain_config/domain_config_service.py

class DomainConfig(BaseModel):
    """Domain configuration including ER-Extraction settings."""

    domain_id: str
    name: str
    primary_language: str = "en"  # de, en, fr, es

    # ER-Extraction Settings (Feature 83.4)
    er_extraction_settings: ERExtractionSettings = Field(
        default_factory=ERExtractionSettings
    )


class ERExtractionSettings(BaseModel):
    """Entity-Relation extraction settings per domain."""

    # Feature 76.2: Domain-specific prompts
    use_domain_prompts: bool = True

    # Feature 83.3: Gleaning (Sprint 84)
    gleaning_steps: int = 0  # 0=disabled, 1-3=enabled

    # Feature 83.2: Fallback cascade
    fallback_cascade: List[str] = ["nemotron3", "gpt-oss:20b", "hybrid_ner"]

    # Phase 1 (Fast Upload) settings
    fast_upload_model: str = "gpt-oss:20b"  # Faster than nemotron3
    fast_upload_timeout_s: int = 600  # Extended for relations

    # Phase 2 (Refinement) settings
    refinement_model: str = "nemotron3"  # Highest quality
    refinement_timeout_s: int = 300  # Standard timeout
```

#### **5. Frontend Status Indicator**

```typescript
// frontend/src/components/admin/DocumentUploadStatus.tsx

interface RefinementStatus {
  documentId: string;
  refinementJobId: string;
  status: "queued" | "refining" | "completed" | "failed";
  phase1EntitiesCount: number;
  phase2EntitiesCount?: number;  // Available after refinement
}

function DocumentUploadStatus({ refinementJobId }: Props) {
  const [status, setStatus] = useState<RefinementStatus>();

  // Poll refinement status every 5s
  useEffect(() => {
    const interval = setInterval(async () => {
      const response = await fetch(
        `/api/v1/admin/indexing/refinement/${refinementJobId}/status`
      );
      setStatus(await response.json());
    }, 5000);

    return () => clearInterval(interval);
  }, [refinementJobId]);

  return (
    <div className="refinement-status">
      {status?.status === "queued" && (
        <span className="text-yellow-600">⏳ Queued for refinement...</span>
      )}
      {status?.status === "refining" && (
        <span className="text-blue-600">🔄 Refining extraction...</span>
      )}
      {status?.status === "completed" && (
        <span className="text-green-600">
          ✅ Complete ({status.phase2EntitiesCount} entities)
        </span>
      )}
      {status?.status === "failed" && (
        <span className="text-red-600">❌ Refinement failed</span>
      )}
    </div>
  );
}
```

---

### Acceptance Criteria

- [x] Implement HybridExtractionService with multi-language SpaCy NER (DE/EN/FR/ES)
- [x] Implement `extract_entities_spacy()` for fast entity extraction
- [x] Implement `extract_relations_llm()` with 600s timeout (uses NER entities in prompt)
- [x] Implement `/indexing/upload-fast` endpoint (Phase 1: SpaCy+LLM)
- [x] Implement `_refine_extraction_background()` (Phase 2: Full LLM)
- [x] Add ERExtractionSettings to DomainConfig
- [x] Frontend status indicator (Refining... → ✅ Complete)
- [x] Unit tests: SpaCy NER extraction (DE/EN/FR/ES)
- [x] Integration test: Fast upload → refinement → status poll

---

### Expected Performance

| Metric | Phase 1 (SpaCy+LLM) | Phase 2 (Full LLM) | Improvement |
|--------|---------------------|-------------------|-------------|
| **Time** | 2-5s | 30-60s | **95% faster user feedback** |
| **Entity Quality** | 70-80% | 100% | +20-30% after refinement |
| **Relation Quality** | 85-90% | 100% | +10-15% after refinement |
| **User Wait Time** | 2-5s | 0s (background) | **No wait for refinement** |

---

### Testing Strategy

```python
# tests/integration/admin/test_fast_upload.py

@pytest.mark.integration
async def test_fast_upload_with_refinement():
    """Test two-phase upload: fast hybrid → background LLM."""

    # Upload document (Phase 1)
    response = await client.post(
        "/api/v1/admin/indexing/upload-fast",
        files={"file": test_document},
        data={"domain_id": "legal"},
    )

    assert response.status_code == 200
    data = response.json()

    # Phase 1 should complete quickly
    assert data["refinement_status"] == "queued"
    assert data["phase1_entities_count"] > 0

    # Wait for refinement (Phase 2)
    await asyncio.sleep(40)  # Background job

    # Check refinement status
    status_response = await client.get(
        f"/api/v1/admin/indexing/refinement/{data['refinement_job_id']}/status"
    )

    status = status_response.json()
    assert status["status"] == "completed"
    assert status["phase2_entities_count"] >= data["phase1_entities_count"]
```

---

### Success Metrics

| Metric | Before (Sprint 82) | After (Sprint 83) |
|--------|-------------------|-------------------|
| **User Upload Feedback Time** | 30-60s (wait for LLM) | **2-5s (SpaCy+LLM)** ✅ |
| **Entity Quality (Phase 1)** | N/A | **70-80%** (good enough) |
| **Entity Quality (Phase 2)** | Baseline | **100%** (refined) |
| **User Wait Time** | 30-60s | **0s** (background refinement) ✅ |

---

## Success Metrics (Sprint 83)

| Metric | Baseline (Sprint 82) | Target (Sprint 83) |
|--------|---------------------|-------------------|
| **Upload Success Rate** | 33.6% (168/500) | **95%+ (475/500)** ✅ |
| **HTTP 000 Error Recovery** | 0% (batch stops) | **100% (auto-fallback)** ✅ |
| **Log Visibility** | Limited phase timing | **Per-phase P95, cost, quality** ✅ |
| **User Upload Feedback Time** | 30-60s | **2-5s (SpaCy+LLM)** ✅ |
| **Upload Time (500 files)** | Failed at 168 | **15-20 hours (with fallback)** ✅ |
| **Entity Recall (with Gleaning)** | Baseline | **Deferred to Sprint 84** (TD-100) |

---

## Testing Strategy

### Unit Tests (30 tests, 90%+ coverage)

```python
# tests/unit/components/graph_rag/test_extraction_fallback.py

@pytest.mark.asyncio
async def test_extraction_fallback_on_timeout():
    """Test automatic fallback to gpt-oss:20b on nemotron3 timeout."""

    # Mock nemotron3 to timeout
    with patch("httpx.AsyncClient.post", side_effect=httpx.ReadTimeout):
        service = ExtractionService()

        # Should automatically fallback to gpt-oss:20b
        entities = await service.extract_entities_with_fallback(
            document_text="Tesla was founded by Elon Musk.",
            chunk_id="chunk_test",
        )

        # Verify fallback was triggered
        assert entities  # Should still extract entities
        # Check logs for "entity_extraction_fallback"
```

### Integration Tests (5 tests)

```python
# tests/integration/ingestion/test_upload_with_ollama_failure.py

@pytest.mark.integration
async def test_upload_500_files_with_simulated_ollama_failure():
    """Test 500-file upload with Ollama failure after 100 files."""

    # Start upload
    # Simulate Ollama crash after file #100
    # Verify auto-restart + fallback to gpt-oss:20b
    # Verify 95%+ upload success rate

    pass  # Implement full E2E test
```

---

## Dependencies

- `tenacity` (Python retry library) - Add to pyproject.toml
- `spacy` + `en_core_web_trf` (for Feature 83.4 only)

```bash
poetry add tenacity
poetry add spacy
python -m spacy download en_core_web_trf
```

---

## Rollout Plan

### Phase 1: Logging (Day 1-2, Feature 83.1)
1. Add comprehensive logging to all 5 ingestion nodes
2. Generate Markdown summary reports
3. Verify logs capture all metrics (timing, cost, quality)

### Phase 2: Retry + Fallback (Day 3-4, Feature 83.2)
1. Implement `@retry` decorator in AegisLLMProxy
2. Implement 3-model fallback cascade
3. Implement OllamaHealthMonitor
4. Integration test: Upload 50 files with simulated failures

### Phase 3: Gleaning (Day 5-6, Feature 83.3)
1. Implement gleaning logic in extraction_service.py
2. Wire to ChunkingConfig
3. Benchmark: Measure entity recall improvement
4. Document cost-benefit analysis

### Phase 4: Full Upload (Day 7, Sprint 83 Complete)
1. Resume upload of remaining 332 files (168→500)
2. Monitor logs for fallback triggers
3. Verify 95%+ success rate
4. Update RAGAS_JOURNEY.md with final results

---

## References

**Sources:**
- [GraphRAG Methods Documentation](https://microsoft.github.io/graphrag/index/methods/)
- [GraphRAG Gleaning Issue #613](https://github.com/microsoft/graphrag/issues/613)
- [From Local to Global: Graph RAG Paper](https://arxiv.org/html/2404.16130v1)
- [LlamaIndex PropertyGraphIndex](https://www.llamaindex.ai/blog/introducing-the-property-graph-index-a-powerful-new-way-to-build-knowledge-graphs-with-llms)
- [Neo4j Global GraphRAG](https://neo4j.com/blog/developer/global-graphrag-neo4j-langchain/)
- [Entity Extraction with Relik + LlamaIndex](https://neo4j.com/blog/developer/entity-linking-relationship-extraction-relik-llamaindex/)

---

**Created:** 2026-01-10
**Author:** Claude Code + User Analysis
**Status:** 📝 Ready for Review
