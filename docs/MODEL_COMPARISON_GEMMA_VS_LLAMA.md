# Model Comparison: Gemma-3-4B vs Llama3.2:3B for Answer Generation

**Date**: 2025-10-30
**Context**: Evaluating whether to use gemma-3-4b-it-Q8_0 for both extraction AND chat generation

---

## Current Architecture (Sprint 19)

| Task | Model | Size | Quantization | Purpose |
|------|-------|------|--------------|---------|
| **Embeddings** | bge-m3 | 2.2GB | - | Vector search (1024D) |
| **Extraction** | gemma-3-4b-it | 4.5GB | Q8_0 | Entity/relation extraction (LightRAG) |
| **Chat** | llama3.2:3b | 2GB | Q4_K_M | User-facing answer generation |

**GPU Context Switches**:
- When switching from extraction (gemma) to chat (llama): **76 seconds model load time** (from your Ollama logs)
- VRAM usage: ~4.4GB free (RTX 3060 has 6GB total)

---

## Proposal: Use Gemma-3-4B for Both

### Advantages ✅

1. **No GPU Context Switches**
   - Gemma stays loaded in VRAM (3.7 GB total memory from logs)
   - No 76-second model swap delays
   - Faster response times for users

2. **Consistent Quality**
   - Gemma-3-4B has proven good at structured extraction
   - Instruction-tuned (`-it`) for following prompts
   - Already validated in production (entity extraction)

3. **Simpler Architecture**
   - Only 2 models instead of 3: bge-m3 (embeddings) + gemma-3-4b (LLM tasks)
   - Easier to debug and monitor
   - Reduced model management overhead

4. **Better VRAM Utilization**
   - Current: 2.3GB (gemma weights) + 2GB (llama, when loaded) = can't fit both
   - Proposal: 2.3GB (gemma) only, leaves ~1.7GB VRAM buffer

### Disadvantages ❌

1. **Slower Inference**
   - Gemma-3-4B (Q8_0): 4.5GB, 4B parameters
   - Llama3.2:3B (Q4_K_M): 2GB, 3B parameters
   - **Expected**: 30-40% slower token generation

2. **Higher VRAM Usage**
   - Gemma: 3.7GB total (2.3GB weights + 494MB KV cache + 441MB compute)
   - Llama: ~2.5GB total (estimated)
   - **Concern**: May not fit gemma + bge-m3 embeddings in VRAM simultaneously

3. **Quantization Mismatch**
   - Gemma using Q8_0 (extraction quality)
   - Llama using Q4_K_M (faster chat)
   - **Q4_K_M gemma**: Would be faster but lower quality for extraction
   - **Q8_0 gemma**: Current choice, prioritizes extraction accuracy over speed

4. **Chat Quality Unknown**
   - Gemma-3-4B validated for structured extraction
   - NOT yet validated for conversational chat
   - Llama3.2 has better chat benchmarks (instruction following, German support)

---

## Performance Analysis

### From Your Ollama Logs

**Gemma-3-4B (Q8_0) Load Time**:
```
time=2025-10-30T06:50:10.150Z - Starting runner
time=2025-10-30T06:51:26.414Z - Llama runner started in 76.27 seconds
```
**76 seconds** to load gemma-3-4b!

**Gemma Inference Times** (entity extraction):
- First extraction: 24.4s (phase 3: relation extraction)
- Subsequent: 5-7s per chunk
- **Average**: ~6-8s per extraction call

**System Resources**:
- Total memory: 8.7 GiB
- Free memory: 5.0 GiB
- GPU VRAM: 4.4 GiB free (6GB total)
- GPU layers: 35/35 offloaded to GPU

### Estimated Chat Performance

**Llama3.2:3B (current)**:
- Load time: ~15-20s (not in logs, but typical for 2GB model)
- Tokens/sec: ~30-40 t/s (RTX 3060 Laptop)
- Response time: ~3-5s for 100 tokens

**Gemma-3-4B (Q8_0, proposed)**:
- Load time: 76s (if not already loaded)
- Tokens/sec: ~20-25 t/s (estimated, 30% slower due to Q8 + 4B params)
- Response time: ~4-7s for 100 tokens

---

## Evaluation Strategy

### How to Benchmark

1. **Create Comparison Script**: `scripts/benchmark_chat_quality.py`

2. **Test Scenarios**:
   - **German language** (DE-D-OTAutBasic content)
   - **Technical accuracy** (PLC programming questions)
   - **Conversational flow** (multi-turn chat)
   - **Response speed** (tokens/second)

3. **Metrics**:
   - **Quality**: Human evaluation (1-5 scale)
   - **Speed**: Tokens/second (measured)
   - **Latency**: Time to first token
   - **GPU memory**: VRAM usage during generation

4. **Test Set** (10 questions):
   ```
   1. "Was ist der Unterschied zwischen ST und FBD in der SPS-Programmierung?"
   2. "Erkläre mir die Funktion eines Timers in TIA Portal."
   3. "Welche Datentypen gibt es in SCL?"
   4. "Wie funktioniert ein Analogwerteingang?"
   5. "Was ist ein Interrupt in der SPS?"
   ... (5 more technical + conversational questions)
   ```

5. **Run Both Models**:
   ```bash
   # Test llama3.2:3b (baseline)
   poetry run python scripts/benchmark_chat_quality.py --model llama3.2:3b

   # Test gemma-3-4b-it-Q8_0
   poetry run python scripts/benchmark_chat_quality.py --model gemma-3-4b-it-Q8_0

   # Test gemma-3-4b-it-Q4_K_M (faster variant)
   poetry run python scripts/benchmark_chat_quality.py --model gemma-3-4b-it-Q4_K_M
   ```

---

## Recommendation

### Option A: Keep Current Architecture (llama3.2 for chat) ✅ RECOMMENDED

**Pros**:
- Proven chat quality (llama3.2 is optimized for conversations)
- Faster responses (3B vs 4B, Q4 vs Q8)
- Lower VRAM usage when generating answers

**Cons**:
- 76-second context switch when switching models
- More complex model management

**When to Use**:
- User sessions with multiple chat messages (model stays loaded)
- GPU context switches are infrequent (user waits, then asks questions)

### Option B: Use Gemma-3-4B for Both (requires testing) ⚠️ NEEDS VALIDATION

**Pros**:
- No context switches (gemma stays loaded)
- Consistent model for all LLM tasks

**Cons**:
- Slower chat responses (4B Q8 vs 3B Q4)
- Higher VRAM pressure (3.7GB gemma + embeddings)
- Chat quality unvalidated

**When to Use**:
- Frequent extraction + chat interleaving
- VRAM is sufficient (test with monitoring)
- Chat quality meets requirements (after benchmarking)

### Option C: Hybrid Strategy (OPTIMAL)

**Adaptive Model Selection**:
1. **Extraction**: Always use gemma-3-4b-it-Q8_0 (quality priority)
2. **Chat during extraction**: Use gemma-3-4b-it (already loaded)
3. **Chat after timeout**: Switch to llama3.2:3b (speed priority)

**Logic**:
```python
if last_extraction_time < 5 minutes:
    use gemma-3-4b  # Already in VRAM
else:
    use llama3.2:3b  # Lighter, faster for pure chat
```

**Pros**:
- Best of both worlds
- No unnecessary context switches
- Faster chat when possible

**Cons**:
- More complex implementation
- Requires model state tracking

---

## CPU Embeddings Consideration

You mentioned: "mit dem untendefinierten CPU embeddings wären wir sauber"

**Current**: bge-m3 via Ollama (GPU)
**Proposal**: bge-m3 via sentence-transformers (CPU)

### Analysis

**GPU Embeddings (current)**:
```
# From your second log (bge-m3 loading)
llama_model_loader: - kv   7: bert.context_length u32 = 8192
llama_model_loader: - kv   8: bert.embedding_length u32 = 1024
```
- Model: 567M parameters (BERT-based)
- Uses Ollama's GGUF backend
- **Problem**: Shares VRAM with LLMs

**CPU Embeddings (proposed)**:
- Use sentence-transformers library directly
- Runs on CPU (no VRAM usage)
- **Your CPU**: 8 cores / 16 threads - plenty for embeddings!

**Recommendation**: ✅ **YES, switch to CPU embeddings**

**Why**:
1. Frees ~1-2GB VRAM for LLMs
2. Your 8-core CPU can handle bge-m3 easily
3. Embedding speed is not critical (batch processing)
4. More VRAM for gemma-3-4b + llama3.2 if needed

**Implementation**:
```python
# src/core/unified_embedding_service.py
# Already supports sentence-transformers!
embed_model = OllamaEmbedding(
    model_name="bge-m3",
    base_url="http://localhost:11434",
)
# Change to:
from sentence_transformers import SentenceTransformer
embed_model = SentenceTransformer("BAAI/bge-m3", device="cpu")
```

---

## Action Plan

### Phase 1: CPU Embeddings (Quick Win) ✅

1. Update `src/core/unified_embedding_service.py` to use sentence-transformers on CPU
2. Test indexing performance (should be similar, CPU embeddings are fast)
3. Measure VRAM savings

### Phase 2: Benchmark Chat Quality (1-2 hours)

1. Create `scripts/benchmark_chat_quality.py`
2. Run 10-question test set:
   - llama3.2:3b (baseline)
   - gemma-3-4b-it-Q8_0
   - gemma-3-4b-it-Q4_K_M (faster variant)
3. Measure:
   - Response quality (human eval)
   - Tokens/second
   - VRAM usage
   - German language support

### Phase 3: Decide Architecture

**If gemma chat quality ≥ llama**:
   → Option B (gemma for both)

**If llama chat quality > gemma**:
   → Option C (hybrid strategy)

**If gemma is too slow**:
   → Option A (keep current)

---

## Acceleration Opportunities (Your Ollama Logs)

### Problem: 76-Second Model Load Time

**From logs**:
```
time=2025-10-30T06:50:10.150Z - starting runner
time=2025-10-30T06:51:26.414Z - llama runner started in 76.27 seconds
```

**Causes**:
1. **Model size**: 4.5GB gemma-3-4b-it-Q8_0
2. **VRAM allocation**: 35 layers being offloaded
3. **CPU→GPU transfer**: Model weights loading

**Optimizations**:

1. **Keep Model Loaded** (easiest):
   ```python
   # Set Ollama keep_alive to prevent unloading
   ollama_params = {
       "keep_alive": "30m",  # Keep model in VRAM for 30 minutes
   }
   ```

2. **Use Lighter Quantization for Chat**:
   - gemma-3-4b-it-Q4_K_M: 2.5GB (50% faster load)
   - Trade-off: Lower quality for extraction

3. **Preload Models at Startup**:
   ```python
   # In src/api/main.py startup event
   @app.on_event("startup")
   async def preload_models():
       await ollama.chat(model="gemma-3-4b-it-Q8_0", messages=[{"role": "user", "content": "ping"}])
       await ollama.chat(model="llama3.2:3b", messages=[{"role": "user", "content": "ping"}])
   ```

4. **Increase CPU Cores for Ollama**:
   ```toml
   # .wslconfig
   [wsl2]
   memory=12GB
   processors=8  # Up from 4 (you have 8 cores!)
   ```

---

## Summary

### Immediate Actions

1. ✅ **Switch to CPU embeddings** (frees 1-2GB VRAM, no quality loss)
2. ⚠️ **Benchmark gemma vs llama for chat** (data-driven decision)
3. 🔧 **Increase WSL2 CPUs to 8** (you have 8 cores, using only 4!)
4. 🔧 **Set ollama keep_alive=30m** (avoid 76s reloads)

### After Benchmarking

- **If gemma chat quality is good**: Use gemma for both (Option B)
- **If llama chat quality is better**: Hybrid strategy (Option C)
- **If speed is critical**: Keep current architecture (Option A)

### Expected Improvements

With CPU embeddings + 8 CPU cores + keep_alive:
- **VRAM savings**: +1-2GB (embeddings on CPU)
- **Faster embeddings**: 8 cores vs 4 cores
- **No model reloads**: keep_alive prevents 76s delays
- **More headroom**: Gemma + llama can coexist in VRAM

---

**Next Steps**:
1. Commit PowerShell scripts cleanup (Sprint 19)
2. Create CPU embeddings migration (Sprint 20)
3. Create benchmark_chat_quality.py script (Sprint 20)
4. Run evaluation and decide architecture

