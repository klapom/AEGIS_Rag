# Sprint 20: Performance Optimization

**Status:** 📋 PLANNED
**Goal:** Optimize performance bottlenecks discovered during Sprint 19 indexing
**Duration:** 4 days (estimated)
**Prerequisites:** Sprint 19 complete (Scripts cleanup + Indexing validation)
**Story Points:** 21 SP

---

## 🎯 Sprint Objectives

### **Primary Goals:**
1. Evaluate Gemma vs Llama for chat generation (benchmark quality + performance)
2. Optimize SentenceTransformer initialization (singleton pattern for deduplicator)
3. Implement Ollama performance improvements (keep_alive, WSL2 CPU increase, preloading)
4. Migrate embeddings to CPU (free VRAM for LLMs)
5. Benchmark and document all improvements

### **Success Criteria:**
- ✅ Data-driven decision: Gemma vs Llama for chat (quality + speed measured)
- ✅ SentenceTransformer loaded once (not 200+ times per indexing)
- ✅ Ollama models stay in VRAM (no 76-second reloads)
- ✅ WSL2 uses 8 CPU cores (up from 4)
- ✅ Embeddings run on CPU (frees 1-2GB VRAM)
- ✅ Comprehensive performance report with before/after metrics

---

## 📦 Sprint Features

### Feature 20.1: Chat Model Evaluation (Gemma vs Llama) (8 SP)
**Priority:** HIGH - Foundational decision for architecture
**Duration:** 2 days

#### **Problem:**
**Context from Sprint 19 indexing logs:**
- Ollama takes **76 seconds** to load gemma-3-4b-it-Q8_0 (used for entity extraction)
- When switching from extraction (gemma) to chat (llama3.2:3b), we pay the 76s context switch penalty
- Current architecture: Gemma (extraction) + Llama (chat) = 2 models = frequent GPU swaps

**Two competing approaches:**
1. **Keep Current (Llama for chat)**: Proven chat quality, but 76s context switches
2. **Use Gemma for both**: No context switches, but unknown chat quality + slower inference (4B Q8 vs 3B Q4)

**We need data to decide!**

#### **Solution:**
Create comprehensive benchmark comparing llama3.2:3b vs gemma-3-4b-it-Q8_0 for German technical chat on PLC documentation.

#### **Benchmark Dimensions:**

**1. Chat Quality (Human Evaluation):**
- German language fluency
- Technical accuracy (PLC programming)
- Instruction following
- Conversational coherence
- Source citation quality

**2. Performance Metrics:**
- Tokens/second (inference speed)
- Time to first token (latency)
- VRAM usage during generation
- CPU usage

**3. Test Dataset:**
10 diverse questions covering:
- Simple factual (Tier 1): "Was ist der Unterschied zwischen ST und FBD?"
- Medium technical (Tier 2): "Erkläre die Funktion eines Timers in TIA Portal."
- Complex multi-hop (Tier 3): "Wie implementiere ich eine Zustandsmaschine mit SCL?"
- Conversational follow-ups

#### **Tasks:**
- [ ] **Create benchmark script** (`scripts/benchmark_chat_quality.py`)
  - Load test questions from YAML
  - Query both models with same prompts
  - Measure tokens/sec, TTFT, VRAM
  - Save results to JSON

- [ ] **Test both models:**
  - llama3.2:3b (baseline)
  - gemma-3-4b-it-Q8_0 (current extraction model)
  - Optional: gemma-3-4b-it-Q4_K_M (faster variant)

- [ ] **Human evaluation rubric:**
  - Scale: 1-5 for each dimension
  - Dimensions: Fluency, Accuracy, Completeness, Coherence
  - Document evaluation criteria

- [ ] **Statistical analysis:**
  - Mean scores per model
  - Win rate (head-to-head)
  - Speed vs quality trade-off chart

- [ ] **Decision matrix:**
  ```
  | Criterion            | Weight | Llama | Gemma | Winner |
  |---------------------|--------|-------|-------|--------|
  | Chat Quality        | 40%    | ?     | ?     | ?      |
  | Response Speed      | 20%    | ?     | ?     | ?      |
  | Context Switch Time | 20%    | ?     | ?     | ?      |
  | VRAM Usage          | 10%    | ?     | ?     | ?      |
  | Ease of Maintenance | 10%    | ?     | ?     | ?      |
  | **Total Score**     | 100%   | ?     | ?     | ?      |
  ```

#### **Implementation:**

```python
# scripts/benchmark_chat_quality.py
"""
Sprint 20: Benchmark Gemma vs Llama for chat generation.

Evaluates:
- German language quality
- Technical accuracy on PLC docs
- Response speed (tokens/sec)
- VRAM usage
"""
import asyncio
import time
from pathlib import Path
import yaml
import json
from typing import List, Dict

from src.core.config import settings
from src.components.llm.ollama_client import OllamaClient

# Test questions (German PLC domain)
TEST_QUESTIONS = [
    {
        "tier": 1,
        "question": "Was ist der Unterschied zwischen ST und FBD in der SPS-Programmierung?",
        "expected_topics": ["Structured Text", "Function Block Diagram", "Textsprache", "Grafisch"],
    },
    {
        "tier": 2,
        "question": "Erkläre mir die Funktion eines Timers in TIA Portal. Welche Typen gibt es?",
        "expected_topics": ["TON", "TOF", "TP", "Zeitgeber", "Zeitverzögerung"],
    },
    {
        "tier": 3,
        "question": "Wie implementiere ich eine Zustandsmaschine in SCL? Zeige ein Beispiel.",
        "expected_topics": ["CASE", "Zustand", "Transition", "Enumeration"],
    },
    # Add 7 more questions...
]

async def benchmark_model(model_name: str, questions: List[Dict]) -> Dict:
    """Benchmark a single model."""
    client = OllamaClient(model=model_name)

    results = []

    for q in questions:
        start = time.perf_counter()

        # Generate response
        response = await client.generate(
            prompt=q["question"],
            temperature=0.7,
            max_tokens=500,
        )

        elapsed = time.perf_counter() - start

        # Calculate metrics
        tokens = len(response.split())  # Rough estimate
        tokens_per_sec = tokens / elapsed if elapsed > 0 else 0

        results.append({
            "question": q["question"],
            "tier": q["tier"],
            "response": response,
            "time_seconds": elapsed,
            "tokens": tokens,
            "tokens_per_sec": tokens_per_sec,
            "expected_topics": q["expected_topics"],
        })

        print(f"✓ {model_name}: {q['tier']} - {elapsed:.2f}s, {tokens_per_sec:.1f} t/s")

    return {
        "model": model_name,
        "results": results,
        "avg_tokens_per_sec": sum(r["tokens_per_sec"] for r in results) / len(results),
        "avg_time_seconds": sum(r["time_seconds"] for r in results) / len(results),
    }

async def main():
    print("=" * 60)
    print("Sprint 20: Chat Model Benchmark (Gemma vs Llama)")
    print("=" * 60)

    # Benchmark both models
    llama_results = await benchmark_model("llama3.2:3b", TEST_QUESTIONS)
    gemma_results = await benchmark_model("gemma-3-4b-it-Q8_0", TEST_QUESTIONS)

    # Save results
    output = {
        "llama3.2:3b": llama_results,
        "gemma-3-4b-it-Q8_0": gemma_results,
        "timestamp": time.time(),
    }

    output_file = Path("docs/sprints/SPRINT_20_CHAT_BENCHMARK_RESULTS.json")
    output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"Llama3.2:3b   - Avg: {llama_results['avg_tokens_per_sec']:.1f} t/s, {llama_results['avg_time_seconds']:.2f}s")
    print(f"Gemma-3-4b-Q8 - Avg: {gemma_results['avg_tokens_per_sec']:.1f} t/s, {gemma_results['avg_time_seconds']:.2f}s")
    print(f"\nResults saved to: {output_file}")
    print("\n⚠️  NEXT STEP: Human evaluation of quality (see SPRINT_20_CHAT_EVALUATION.md)")

if __name__ == "__main__":
    asyncio.run(main())
```

#### **Deliverables:**
```bash
scripts/benchmark_chat_quality.py
docs/sprints/SPRINT_20_CHAT_BENCHMARK_RESULTS.json
docs/sprints/SPRINT_20_CHAT_EVALUATION.md  # Human evaluation template
docs/MODEL_COMPARISON_GEMMA_VS_LLAMA.md    # Updated with decision
```

#### **Acceptance Criteria:**
- ✅ Benchmark script runs successfully for both models
- ✅ 10+ test questions across difficulty tiers
- ✅ Quantitative metrics collected (tokens/sec, TTFT, VRAM)
- ✅ Human evaluation completed with rubric
- ✅ Decision matrix filled with scores
- ✅ Final recommendation documented (Gemma vs Llama)

---

### Feature 20.2: SentenceTransformer Singleton Optimization (5 SP)
**Priority:** HIGH - Major indexing bottleneck
**Duration:** 1 day

#### **Problem:**
**From Sprint 19 indexing logs:**
```
INFO:sentence_transformers.SentenceTransformer:Load pretrained SentenceTransformer: sentence-transformers/all-MiniLM-L6-v2
[... repeated 200+ times during indexing of 223 chunks ...]
```

**Root cause:**
- `SemanticEntityDeduplicator` creates a NEW `SentenceTransformer` instance **for every chunk**
- Each initialization loads the model weights from disk (~90MB)
- 223 chunks × ~500ms load time = **111 seconds wasted** on redundant loading!

**Current code** (`src/components/graph_rag/semantic_deduplicator.py`):
```python
class SemanticEntityDeduplicator:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        # ❌ This is called for EVERY chunk!
        self.model = SentenceTransformer(model_name, device="cpu")
```

**Called from** (`src/components/graph_rag/lightrag_wrapper.py` line ~650):
```python
# Inside per-chunk extraction loop
deduplicator = SemanticEntityDeduplicator()  # ❌ Creates new model each time!
deduplicated_entities = deduplicator.deduplicate(entities)
```

#### **Solution:**
Implement singleton pattern to load SentenceTransformer **once** and reuse across all chunks.

#### **Tasks:**
- [ ] **Refactor SemanticEntityDeduplicator:**
  - Create module-level singleton instance
  - Lazy-load on first use
  - Thread-safe initialization

- [ ] **Update LightRAGWrapper:**
  - Initialize deduplicator once in `__init__`
  - Reuse same instance for all chunks

- [ ] **Add performance logging:**
  - Log model initialization time
  - Log deduplication time per chunk
  - Compare before/after total time

- [ ] **Validate functionality:**
  - Ensure deduplication results identical
  - Test with multiple concurrent indexing jobs

#### **Implementation:**

```python
# src/components/graph_rag/semantic_deduplicator.py
"""
Sprint 20: Singleton pattern for SentenceTransformer.

Before: ~200+ model loads (111 seconds wasted)
After: 1 model load (~500ms)
Speedup: ~220x faster initialization
"""
from typing import Optional
import threading
from sentence_transformers import SentenceTransformer
import structlog

logger = structlog.get_logger(__name__)

# Module-level singleton
_deduplicator_instance: Optional["SemanticEntityDeduplicator"] = None
_init_lock = threading.Lock()

class SemanticEntityDeduplicator:
    """Semantic entity deduplicator with singleton SentenceTransformer."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        similarity_threshold: float = 0.93,
        device: str = "cpu",
    ):
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.device = device

        # Lazy-load model (only on first use)
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load SentenceTransformer (singleton pattern)."""
        if self._model is None:
            import time
            start = time.perf_counter()

            self._model = SentenceTransformer(self.model_name, device=self.device)

            elapsed = time.perf_counter() - start
            logger.info(
                "sentence_transformer_loaded",
                model=self.model_name,
                device=self.device,
                load_time_ms=int(elapsed * 1000),
            )

        return self._model

    def deduplicate(self, entities: list) -> list:
        """Deduplicate entities using semantic similarity."""
        # Use lazy-loaded model
        embeddings = self.model.encode([e["entity_name"] for e in entities])

        # ... existing deduplication logic ...
        return deduplicated


def get_semantic_deduplicator() -> SemanticEntityDeduplicator:
    """Get singleton deduplicator instance."""
    global _deduplicator_instance

    if _deduplicator_instance is None:
        with _init_lock:
            # Double-check locking
            if _deduplicator_instance is None:
                _deduplicator_instance = SemanticEntityDeduplicator()
                logger.info("semantic_deduplicator_singleton_created")

    return _deduplicator_instance
```

```python
# src/components/graph_rag/lightrag_wrapper.py (UPDATED)
from src.components.graph_rag.semantic_deduplicator import get_semantic_deduplicator

class LightRAGWrapper:
    def __init__(self, ...):
        # Initialize deduplicator ONCE (singleton)
        self.deduplicator = get_semantic_deduplicator()
        logger.info("lightrag_wrapper_initialized_with_singleton_deduplicator")

    async def _extract_entities_per_chunk(self, chunks: List[Dict]) -> Dict:
        """Extract entities for all chunks (reusing same deduplicator)."""
        for chunk in chunks:
            # Phase 1: SpaCy extraction
            entities = self._extract_with_spacy(chunk)

            # Phase 2: Semantic deduplication (reuses loaded model!)
            deduplicated = self.deduplicator.deduplicate(entities)

            # Phase 3: Gemma relation extraction
            relations = await self._extract_relations_with_gemma(deduplicated, chunk)
```

#### **Performance Testing:**

```python
# tests/performance/test_deduplicator_singleton.py
"""Test deduplicator singleton performance."""
import time
from src.components.graph_rag.semantic_deduplicator import get_semantic_deduplicator

def test_singleton_performance():
    """Verify singleton loads model only once."""

    # First call: Should load model
    start = time.perf_counter()
    dedup1 = get_semantic_deduplicator()
    first_call_time = time.perf_counter() - start

    # Subsequent calls: Should reuse instance
    start = time.perf_counter()
    dedup2 = get_semantic_deduplicator()
    second_call_time = time.perf_counter() - start

    # Verify same instance
    assert dedup1 is dedup2, "Should return same instance"

    # Verify speedup
    assert second_call_time < first_call_time * 0.01, "Second call should be 100x faster"

    print(f"First call:  {first_call_time*1000:.1f}ms")
    print(f"Second call: {second_call_time*1000:.1f}ms")
    print(f"Speedup:     {first_call_time/second_call_time:.0f}x")
```

#### **Deliverables:**
```bash
src/components/graph_rag/semantic_deduplicator.py (updated)
src/components/graph_rag/lightrag_wrapper.py (updated)
tests/performance/test_deduplicator_singleton.py
docs/sprints/SPRINT_20_DEDUPLICATOR_PERFORMANCE.md
```

#### **Acceptance Criteria:**
- ✅ SentenceTransformer loaded only once per Python process
- ✅ All chunk deduplication reuses same model instance
- ✅ No "Load pretrained SentenceTransformer" spam in logs
- ✅ Indexing speed improved by ~100+ seconds (for 223 chunks)
- ✅ Deduplication results identical to before (no regression)
- ✅ Thread-safe for concurrent indexing

---

### Feature 20.3: Ollama Performance Improvements (5 SP)
**Priority:** MEDIUM - Reduces latency
**Duration:** 1 day

#### **Problem:**
**From Sprint 19 analysis:**
1. **76-second model load time** when Ollama loads gemma-3-4b-it-Q8_0
2. **Frequent model unloading** (no keep_alive set, defaults to 5 minutes)
3. **Underutilized CPU** (WSL2 using 4 cores, but system has 8 cores / 16 threads)

#### **Solution:**
Three optimizations:
1. Set `keep_alive=30m` (prevent model unloading during sessions)
2. Increase WSL2 CPUs to 8 (faster embeddings, better parallelism)
3. Preload models at API startup (avoid first-request cold start)

#### **Tasks:**

**Task 1: Set keep_alive parameter**
```python
# src/components/llm/ollama_client.py
class OllamaClient:
    async def generate(self, prompt: str, **kwargs):
        response = await self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options={
                "keep_alive": "30m",  # ✅ Keep model in VRAM for 30 minutes
                **kwargs,
            },
        )
```

**Task 2: Create .wslconfig with 8 CPUs**
```ini
# C:\Users\Klaus Pommer\.wslconfig
[wsl2]
memory=12GB        # Keep current
processors=8       # ✅ Increase from 4 to 8
swap=2GB           # Keep current
localhostForwarding=true
```

**Task 3: Preload models at startup**
```python
# src/api/main.py
from src.components.llm.ollama_client import OllamaClient

@app.on_event("startup")
async def preload_ollama_models():
    """Preload models to avoid cold start."""
    logger.info("preloading_ollama_models")

    models = [
        "gemma-3-4b-it-Q8_0",  # Extraction
        "llama3.2:3b",         # Chat (if still used after benchmark)
    ]

    for model in models:
        try:
            client = OllamaClient(model=model)
            # Ping model (loads into VRAM)
            await client.generate("ping", max_tokens=1)
            logger.info("model_preloaded", model=model)
        except Exception as e:
            logger.error("model_preload_failed", model=model, error=str(e))
```

#### **Deliverables:**
```bash
.wslconfig (new file in user home directory)
src/components/llm/ollama_client.py (updated with keep_alive)
src/api/main.py (updated with preload)
docs/sprints/SPRINT_20_OLLAMA_OPTIMIZATIONS.md
```

#### **Acceptance Criteria:**
- ✅ `.wslconfig` created with 8 CPUs
- ✅ WSL2 restart completed, CPU count verified (`grep -c processor /proc/cpuinfo` = 8)
- ✅ `keep_alive=30m` set in all Ollama calls
- ✅ Models preloaded at API startup (no 76s delay on first request)
- ✅ Models stay in VRAM during active use (check with `ollama ps`)

---

### Feature 20.4: CPU Embeddings Migration (3 SP)
**Priority:** LOW - Nice-to-have (frees VRAM)
**Duration:** 0.5 days

#### **Problem:**
**From MODEL_COMPARISON analysis:**
- bge-m3 via Ollama uses **GPU VRAM** (~1-2GB)
- Your 8-core CPU can handle embeddings easily
- Freeing VRAM allows gemma + llama to coexist without swapping

#### **Solution:**
Migrate from Ollama embeddings to sentence-transformers (CPU).

#### **Tasks:**
- [ ] **Update UnifiedEmbeddingService:**
  ```python
  # src/core/unified_embedding_service.py
  from sentence_transformers import SentenceTransformer

  class UnifiedEmbeddingService:
      def __init__(self, model_name: str = "BAAI/bge-m3", device: str = "cpu"):
          self.model = SentenceTransformer(model_name, device=device)
          self.dimension = 1024
  ```

- [ ] **Test embedding quality:**
  - Verify embeddings identical to Ollama bge-m3
  - Measure embedding speed (should be similar on 8-core CPU)

- [ ] **Update config:**
  ```python
  # src/core/config.py
  EMBEDDING_PROVIDER = "sentence-transformers"  # Was: "ollama"
  EMBEDDING_MODEL = "BAAI/bge-m3"
  EMBEDDING_DEVICE = "cpu"
  ```

#### **Deliverables:**
```bash
src/core/unified_embedding_service.py (updated)
src/core/config.py (updated)
tests/embeddings/test_cpu_embeddings.py
docs/sprints/SPRINT_20_CPU_EMBEDDINGS.md
```

#### **Acceptance Criteria:**
- ✅ Embeddings run on CPU (verified in logs)
- ✅ Embedding quality identical (cosine similarity test)
- ✅ VRAM freed for LLMs (check nvidia-smi or Task Manager)
- ✅ Indexing speed not significantly slower

---

## Testing Strategy

### Performance Benchmarks
```python
# tests/performance/test_sprint_20_improvements.py
"""
Benchmark Sprint 20 improvements.

Measures:
- Indexing speed (before/after deduplicator singleton)
- Chat response latency (gemma vs llama)
- Model load times (with keep_alive)
- VRAM usage (with CPU embeddings)
"""
import pytest
import time

@pytest.mark.performance
async def test_indexing_speed_improvement():
    """Verify indexing faster after deduplicator singleton."""
    # Baseline: ~350s for 223 chunks (Sprint 19)
    # Target: <250s (at least 100s improvement from deduplicator)

    start = time.perf_counter()
    await index_documents(["DE-D-OTAutBasic.pdf"])
    elapsed = time.perf_counter() - start

    assert elapsed < 250, f"Indexing took {elapsed}s, expected <250s"

@pytest.mark.performance
async def test_chat_latency():
    """Verify chat responses fast (no 76s cold start)."""
    # With preloading + keep_alive, should be <5s

    start = time.perf_counter()
    response = await chat("Was ist ein Timer in TIA Portal?")
    elapsed = time.perf_counter() - start

    assert elapsed < 5, f"Chat took {elapsed}s, expected <5s"
```

---

## Documentation

### Performance Report Template
```markdown
# Sprint 20: Performance Improvements Report

## 1. Chat Model Evaluation

| Model           | Avg Quality | Avg Tokens/sec | Decision |
|-----------------|-------------|----------------|----------|
| llama3.2:3b     | 4.2/5       | 35 t/s         | ?        |
| gemma-3-4b-Q8   | ?/5         | ? t/s          | ?        |

**Winner:** TBD after benchmarking

## 2. Deduplicator Singleton

| Metric                 | Before    | After    | Improvement |
|------------------------|-----------|----------|-------------|
| Model loads            | 223       | 1        | 223x        |
| Initialization time    | 111s      | 0.5s     | 222x        |
| Total indexing time    | 350s      | <250s    | 30%+        |

## 3. Ollama Optimizations

| Metric                 | Before    | After    | Improvement |
|------------------------|-----------|----------|-------------|
| First request latency  | 76s       | <5s      | 15x         |
| WSL2 CPUs              | 4         | 8        | 2x          |
| Model reload frequency | High      | Low      | keep_alive  |

## 4. CPU Embeddings

| Metric                 | Before    | After    | Improvement |
|------------------------|-----------|----------|-------------|
| VRAM usage             | 5-6GB     | 3-4GB    | +2GB free   |
| Embedding speed        | ~same     | ~same    | No regression |
```

---

## Sprint 20 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Indexing speed | <250s (223 chunks) | Benchmark script |
| Chat quality | ≥4/5 (chosen model) | Human evaluation |
| Chat latency | <5s (no cold start) | API response time |
| VRAM savings | +1-2GB free | nvidia-smi |
| Model reload frequency | <1 per hour | Ollama logs |

---

**Sprint 20 Completion:** Performance optimized, architecture decision made
**Next Sprint:** Sprint 21 - Foundation (Auth & Multi-Tenancy)
