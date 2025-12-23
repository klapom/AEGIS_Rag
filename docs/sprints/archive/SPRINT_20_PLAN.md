# Sprint 20: Performance Optimization (Updated with LM Studio)

**Status:** 📋 PLANNED
**Goal:** Optimize performance bottlenecks discovered during Sprint 19 + evaluate LM Studio
**Duration:** 5 days (estimated - extended for LM Studio evaluation)
**Prerequisites:** Sprint 19 complete (Scripts cleanup + Indexing validation)
**Story Points:** 26 SP (increased from 21 SP)

---

## 🎯 Sprint Objectives

### **Primary Goals:**
1. Evaluate Gemma vs Llama for chat generation (benchmark quality + performance) **with indexed documents**
2. **NEW**: Evaluate LM Studio advanced parameters vs Ollama
3. Optimize SentenceTransformer initialization (singleton pattern for deduplicator)
4. Implement Ollama performance improvements (keep_alive, WSL2 CPU increase, preloading)
5. Migrate embeddings to CPU (free VRAM for LLMs)
6. Benchmark and document all improvements

### **Success Criteria:**
- ✅ Data-driven decision: Gemma vs Llama for chat (quality + speed measured on **indexed documents**)
- ✅ LM Studio evaluation completed (parameter tuning opportunities identified)
- ✅ SentenceTransformer loaded once (not 200+ times per indexing)
- ✅ Ollama models stay in VRAM (no 76-second reloads)
- ✅ WSL2 uses 8 CPU cores (up from 4)
- ✅ Embeddings run on CPU (frees 1-2GB VRAM)
- ✅ Comprehensive performance report with before/after metrics

---

## 📦 Sprint Features

### Feature 20.1: Chat Model Evaluation (Gemma vs Llama) - UPDATED (8 SP)
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
Create comprehensive benchmark comparing llama3.2:3b vs gemma-3-4b-it-Q8_0 for **German + English technical chat on INDEXED DOCUMENTS**.

#### **IMPORTANT CHANGES:**
✅ **Questions MUST be based on indexed documents:**
   - `DE-D-OTAutBasic.pdf` (Basic Scripting with VBS/Automation)
   - `DE-D-OTAutAdvanced.pdf` (Advanced Scripting)

✅ **Mixed language testing:**
   - 5 questions in **German** (native language of docs)
   - 5 questions in **English** (multilingual capability)

✅ **Test pyramid:**
   - **Tier 1**: Simple factual questions (directly in document)
   - **Tier 2**: Medium technical (requires context understanding)
   - **Tier 3**: Complex multi-hop (connecting multiple sections)

#### **Benchmark Dimensions:**

**1. Chat Quality (Human Evaluation):**
- German language fluency
- English language fluency
- Technical accuracy (VBScript/Automation content)
- Instruction following
- Conversational coherence
- Source citation quality

**2. Performance Metrics:**
- Tokens/second (inference speed)
- Time to first token (latency)
- VRAM usage during generation
- CPU usage

**3. Test Dataset (10 Questions - DOCUMENT-BASED):**

```yaml
# German questions (Tier 1 - Simple factual)
- tier: 1
  language: de
  question: "Was ist VBScript laut dem Dokument?"
  expected_topics: ["VBScript", "Scripting-Sprache", "Visual Basic"]
  document: "DE-D-OTAutBasic.pdf"

- tier: 1
  language: de
  question: "Welches Automation Interface wird im Dokument beschrieben?"
  expected_topics: ["Automation Interface", "COM", "OLE"]
  document: "DE-D-OTAutBasic.pdf"

# English questions (Tier 1)
- tier: 1
  language: en
  question: "What is VBScript according to the document?"
  expected_topics: ["VBScript", "scripting language", "Visual Basic"]
  document: "DE-D-OTAutBasic.pdf"

- tier: 1
  language: en
  question: "Which Automation Interface is described in the document?"
  expected_topics: ["Automation Interface", "COM", "OLE"]
  document: "DE-D-OTAutBasic.pdf"

# German questions (Tier 2 - Medium technical)
- tier: 2
  language: de
  question: "Welche Vorteile bietet serverseitiges Scripting gegenüber clientseitigem laut Dokument?"
  expected_topics: ["Server-Side", "Client-Side", "Vorteile", "Unterschiede"]
  document: "DE-D-OTAutBasic.pdf"

# English questions (Tier 2)
- tier: 2
  language: en
  question: "What advantages does server-side scripting offer compared to client-side according to the document?"
  expected_topics: ["server-side", "client-side", "advantages", "comparison"]
  document: "DE-D-OTAutBasic.pdf"

# German questions (Tier 3 - Complex multi-hop)
- tier: 3
  language: de
  question: "Erkläre den Unterschied zwischen Client-Side und Server-Side Scripting mit konkreten Beispielen aus dem Dokument."
  expected_topics: ["Client-Side", "Server-Side", "Unterschiede", "Beispiele", "Anwendungsfälle"]
  document: "DE-D-OTAutBasic.pdf"

- tier: 3
  language: de
  question: "Welche Schritte sind nötig, um ein VBScript für die Automation zu erstellen? Fasse den Prozess aus dem Dokument zusammen."
  expected_topics: ["VBScript", "Automation", "Schritte", "Prozess", "Anleitung"]
  document: "DE-D-OTAutBasic.pdf"

# English questions (Tier 3)
- tier: 3
  language: en
  question: "Explain the difference between client-side and server-side scripting with specific examples from the document."
  expected_topics: ["client-side", "server-side", "differences", "examples", "use cases"]
  document: "DE-D-OTAutBasic.pdf"

- tier: 3
  language: en
  question: "What steps are necessary to create a VBScript for automation? Summarize the process from the document."
  expected_topics: ["VBScript", "automation", "steps", "process", "guide"]
  document: "DE-D-OTAutBasic.pdf"
```

#### **Tasks:**
- [ ] **Verify documents indexed:**
  - Run `scripts/index_three_specific_docs.py` if not already indexed
  - Verify both documents in Qdrant collection
  - Verify entities in Neo4j from both documents

- [ ] **Create benchmark script** (`scripts/benchmark_chat_quality.py`)
  - Load test questions from YAML (document-based!)
  - Query both models with RAG context (retrieve from Qdrant first!)
  - Measure tokens/sec, TTFT, VRAM
  - Save results to JSON
  - **Mixed language**: 5 German + 5 English questions

- [ ] **Test both models:**
  - llama3.2:3b (baseline via Ollama)
  - gemma-3-4b-it-Q8_0 (current extraction model via Ollama)

- [ ] **Human evaluation rubric:**
  - Scale: 1-5 for each dimension
  - Dimensions: Fluency (DE), Fluency (EN), Accuracy, Completeness, Coherence
  - Document evaluation criteria

- [ ] **Decision matrix:**
  ```
  | Criterion            | Weight | Llama | Gemma | Winner |
  |---------------------|--------|-------|-------|--------|
  | Chat Quality (DE)   | 20%    | ?     | ?     | ?      |
  | Chat Quality (EN)   | 20%    | ?     | ?     | ?      |
  | Response Speed      | 20%    | ?     | ?     | ?      |
  | Context Switch Time | 20%    | ?     | ?     | ?      |
  | VRAM Usage          | 10%    | ?     | ?     | ?      |
  | Ease of Maintenance | 10%    | ?     | ?     | ?      |
  | **Total Score**     | 100%   | ?     | ?     | ?      |
  ```

#### **Deliverables:**
```bash
scripts/benchmark_chat_quality.py
scripts/test_questions.yaml  # Document-based questions (DE + EN)
docs/sprints/SPRINT_20_CHAT_BENCHMARK_RESULTS.json
docs/sprints/SPRINT_20_CHAT_EVALUATION.md  # Human evaluation
docs/MODEL_COMPARISON_GEMMA_VS_LLAMA.md    # Updated with decision
```

#### **Acceptance Criteria:**
- ✅ Benchmark script runs successfully for both models
- ✅ 10 test questions (5 DE, 5 EN) across difficulty tiers **based on indexed documents**
- ✅ Quantitative metrics collected (tokens/sec, TTFT, VRAM)
- ✅ Human evaluation completed with rubric
- ✅ Decision matrix filled with scores
- ✅ Final recommendation documented (Gemma vs Llama)

---

### Feature 20.2: LM Studio Advanced Parameters Evaluation - NEW (5 SP)
**Priority:** MEDIUM - Could significantly improve performance
**Duration:** 1.5 days

#### **Problem:**
**From Sprint 19 analysis (LMSTUDIO_VS_OLLAMA_ANALYSIS.md):**
- LM Studio uses same backend (llama.cpp) as Ollama → **same performance baseline**
- BUT: LM Studio offers **many more tuning options** for inference optimization:
  - Advanced sampling parameters (top_k, top_p, min_p, typical_p, mirostat)
  - Context management (KV cache, RoPE scaling, context shift)
  - Performance tuning (batch size, thread count, GPU layers)
  - Model-specific presets

**Could these advanced parameters improve:**
1. **Chat quality** (better sampling strategies)
2. **Response speed** (optimized batch processing)
3. **VRAM efficiency** (smart KV cache management)

#### **Solution:**
Systematic evaluation of LM Studio's advanced parameters to find optimal settings for Gemma/Llama chat generation.

#### **LM Studio Parameters to Evaluate:**

**1. Sampling Parameters** (Quality Focus):
```python
# Baseline (Ollama defaults)
temperature = 0.7
top_p = 0.9
top_k = 40

# LM Studio advanced options
min_p = 0.05          # Minimum probability threshold
typical_p = 1.0       # Typical sampling (alternative to top-p)
mirostat = 0          # 0=disabled, 1=Mirostat 1.0, 2=Mirostat 2.0
mirostat_tau = 5.0    # Target entropy
mirostat_eta = 0.1    # Learning rate
```

**2. Context Management** (Memory Focus):
```python
# Context window
n_ctx = 8192          # Context size (larger = more memory)
n_batch = 512         # Batch size for prompt processing
rope_freq_base = 10000  # RoPE frequency base (for long contexts)
rope_freq_scale = 1.0   # RoPE frequency scaling
```

**3. Performance Tuning** (Speed Focus):
```python
# Threading
n_threads = 8         # CPU threads (match your 8 cores)
n_threads_batch = 8   # Batch processing threads

# GPU offloading
n_gpu_layers = 35     # Layers offloaded to GPU (all for gemma)
main_gpu = 0          # Primary GPU index

# KV cache
use_mlock = False     # Lock model in RAM
use_mmap = True       # Memory-map model file
```

#### **Evaluation Methodology:**

**Phase 1: Parameter Grid Search**
Test combinations systematically:
```python
# Test matrix
SAMPLING_CONFIGS = [
    {"name": "ollama_default", "temp": 0.7, "top_p": 0.9, "top_k": 40},
    {"name": "low_temperature", "temp": 0.3, "top_p": 0.95, "top_k": 20},
    {"name": "mirostat_v2", "temp": 0.7, "mirostat": 2, "mirostat_tau": 5.0},
    {"name": "typical_sampling", "temp": 0.7, "typical_p": 0.9},
]

PERFORMANCE_CONFIGS = [
    {"name": "default", "n_threads": 4, "n_batch": 512},
    {"name": "optimized", "n_threads": 8, "n_batch": 1024},
]
```

**Phase 2: A/B Testing**
Compare best LM Studio config vs Ollama default on same 10 questions from Feature 20.1.

#### **Tasks:**
- [ ] **Setup LM Studio:**
  - Install LM Studio (already done per analysis)
  - Load gemma-3-4b-it-Q8_0 model
  - Configure OpenAI-compatible API endpoint

- [ ] **Create parameter evaluation script** (`scripts/evaluate_lm_studio_params.py`)
  - Test sampling parameter combinations
  - Test performance parameter combinations
  - Measure quality (same rubric as Feature 20.1)
  - Measure speed (tokens/sec, TTFT)

- [ ] **Identify optimal parameters:**
  - Best sampling config for quality
  - Best performance config for speed
  - Best balanced config

- [ ] **A/B test best config:**
  - LM Studio (optimized params) vs Ollama (default params)
  - Same 10 questions from Feature 20.1
  - Compare quality + speed

#### **Implementation:**

```python
# scripts/evaluate_lm_studio_params.py
"""
Sprint 20 Feature 20.2: LM Studio Parameter Evaluation

Tests advanced parameters unavailable in Ollama:
- Sampling strategies (mirostat, typical_p, min_p)
- Context management (RoPE scaling, KV cache)
- Performance tuning (thread count, batch size)
"""
import asyncio
import time
from typing import Dict, List
import httpx

LM_STUDIO_API = "http://localhost:1234/v1"  # OpenAI-compatible

SAMPLING_CONFIGS = [
    {
        "name": "ollama_baseline",
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
    },
    {
        "name": "mirostat_v2",
        "temperature": 0.7,
        "mirostat_mode": 2,
        "mirostat_tau": 5.0,
        "mirostat_eta": 0.1,
    },
    {
        "name": "typical_sampling",
        "temperature": 0.7,
        "typical_p": 0.9,
        "min_p": 0.05,
    },
    {
        "name": "low_temp_precise",
        "temperature": 0.3,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.1,
    },
]

async def test_sampling_config(config: Dict, question: str) -> Dict:
    """Test single sampling configuration."""
    async with httpx.AsyncClient() as client:
        start = time.perf_counter()

        response = await client.post(
            f"{LM_STUDIO_API}/chat/completions",
            json={
                "model": "gemma-3-4b-it-Q8_0",
                "messages": [{"role": "user", "content": question}],
                **config,  # Sampling parameters
                "max_tokens": 500,
                "stream": False,
            },
            timeout=60.0,
        )

        elapsed = time.perf_counter() - start

        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        tokens = data["usage"]["completion_tokens"]

        return {
            "config_name": config["name"],
            "answer": answer,
            "time_seconds": elapsed,
            "tokens": tokens,
            "tokens_per_sec": tokens / elapsed if elapsed > 0 else 0,
        }

async def main():
    print("=" * 60)
    print("Sprint 20 Feature 20.2: LM Studio Parameter Evaluation")
    print("=" * 60)

    # Use first question from Feature 20.1 for quick test
    test_question = "Was ist VBScript laut dem Dokument?"

    results = []

    for config in SAMPLING_CONFIGS:
        print(f"\n[Testing] {config['name']}...")
        result = await test_sampling_config(config, test_question)
        results.append(result)

        print(f"  → {result['tokens_per_sec']:.1f} t/s, {result['time_seconds']:.2f}s")
        print(f"  → Answer preview: {result['answer'][:100]}...")

    # Save results
    import json
    with open("docs/sprints/SPRINT_20_LM_STUDIO_PARAMS.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("RESULTS SAVED")
    print("=" * 60)
    print("Next: Human evaluation of answer quality")
    print("Then: A/B test best config vs Ollama")

if __name__ == "__main__":
    asyncio.run(main())
```

#### **Deliverables:**
```bash
scripts/evaluate_lm_studio_params.py
docs/sprints/SPRINT_20_LM_STUDIO_PARAMS.json
docs/sprints/SPRINT_20_LM_STUDIO_EVALUATION.md
docs/LMSTUDIO_VS_OLLAMA_ANALYSIS.md  # Updated with parameter findings
```

#### **Acceptance Criteria:**
- ✅ LM Studio installed and running
- ✅ 4+ sampling configurations tested
- ✅ Performance metrics collected for each config
- ✅ Best config identified (quality + speed balance)
- ✅ A/B test completed (LM Studio optimized vs Ollama)
- ✅ Recommendation documented (use LM Studio params or stick with Ollama)

---

### Feature 20.3: SentenceTransformer Singleton Optimization (5 SP)
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

_(Implementation details remain the same as original plan...)_

---

### Feature 20.4: Ollama Performance Improvements (5 SP)
_(Same as original plan - keep_alive, WSL2 8 CPUs, preloading)_

---

### Feature 20.5: CPU Embeddings Migration (3 SP)
_(Same as original plan - migrate to sentence-transformers on CPU)_

---

## Testing Strategy

_(Same as original plan)_

---

## Sprint 20 Success Metrics - UPDATED

| Metric | Target | Measurement |
|--------|--------|-------------|
| Indexing speed | <250s (223 chunks) | Benchmark script |
| Chat quality (DE) | ≥4/5 (chosen model) | Human evaluation on indexed docs |
| Chat quality (EN) | ≥4/5 (chosen model) | Human evaluation on indexed docs |
| **LM Studio params** | **Identify 1-2 improvements** | **Parameter grid search** |
| Chat latency | <5s (no cold start) | API response time |
| VRAM savings | +1-2GB free | nvidia-smi |
| Model reload frequency | <1 per hour | Ollama logs |

---

**Sprint 20 Completion:** Performance optimized, architecture decision made, LM Studio evaluated
**Next Sprint:** Sprint 21 - Foundation (Auth & Multi-Tenancy)
