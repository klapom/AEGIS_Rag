# LightRAG Model Testing Results

**Date:** 2025-10-18
**Sprint:** Sprint 8 E2E Testing Preparation
**Objective:** Find compatible LLM model for LightRAG within Docker Desktop memory constraints

---

## Executive Summary

**WORKING MODEL FOUND:** `qwen3:0.6b`

- ✅ Produces correct LightRAG delimiter format (`<|#|>`)
- ✅ Successfully extracts entities and relationships
- ✅ Fits within Docker Desktop memory constraints (7.63GB limit)
- ✅ 32K context window (LightRAG requirement)
- ✅ Generation time acceptable (~51 seconds for test document)

---

## Critical Discovery: Delimiter Format

### The Problem
Previous tests were failing because we were using **incorrect delimiter format**.

### Investigation Results
| Source | Delimiter Format | Status |
|--------|------------------|--------|
| Neo4j Blog Article | `<\|>` | ❌ Outdated/Simplified |
| Our Test Scripts | `\|` | ❌ Wrong |
| **LightRAG Source Code** | **`<\|#\|>`** | ✅ **CORRECT** |

**Source Code Location:** `lightrag/prompt.py`
```python
PROMPTS["DEFAULT_TUPLE_DELIMITER"] = "<|#|>"
PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"
```

### Correct Format Examples
```
entity<|#|>Apple Inc<|#|>organization<|#|>Apple Inc. is a technology company
entity<|#|>Steve Jobs<|#|>person<|#|>Steve Jobs was CEO of Apple
relation<|#|>Steve Jobs<|#|>Apple Inc<|#|>employment<|#|>Steve Jobs was CEO of Apple Inc
<|COMPLETE|>
```

---

## Model Testing Results

### Test Environment
- **System RAM:** 16.5 GB total
- **Docker Desktop Limit:** 7.63 GB ← **BOTTLENECK**
- **Ollama Available Memory:** ~5.6 GB (after Docker overhead)
- **Test Document:** Apple Inc. founding story (4 entities, 3 relationships expected)

### Model Compatibility Matrix

| Model | Download Size | Runtime RAM | Context Window | Test Result | Issue |
|-------|--------------|-------------|----------------|-------------|-------|
| **qwen3:0.6b** | 522 MB | ~2 GB | 32K | ✅ **SUCCESS** | **WORKING** |
| qwen3:4b | 2.5 GB | 10 GB | 256K | ❌ OUT OF MEMORY | Needs 10GB, only 5.6GB available |
| qwen2.5:7b | 4.7 GB | 8.3 GB | 128K | ❌ OUT OF MEMORY | Needs 8.3GB, only 5.6GB available |
| llama3.2:3b | 2.0 GB | 7.3 GB | 128K | ❌ OUT OF MEMORY | Needs 7.3GB, only 5.6GB available |
| smollm | 990 MB | ~3 GB | 32K | ❌ FAIL | Produces Python code instead of entities |

### qwen3:0.6b Test Results (WORKING MODEL)
```
================================================================================
MODEL OUTPUT:
================================================================================
entity<|#|>Apple Inc<|#|>organization<|#|>Apple Inc. is a technology company founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976.
entity<|#|>Steve Jobs<|#|>person<|#|>Steve Jobs is the co-founder of Apple Inc. who served as CEO and led product development.
entity<|#|>Steve Wozniak<|#|>person<|#|>Steve Wozniak is one of the founders of Apple Inc.
entity<|#|>Ronald Wayne<|#|>person<|#|>Ronald Wayne was a co-founder of Apple Inc. along with Steve Jobs and Steve Wozniak in 1976.
relation<|#|>Steve Jobs<|#|>Apple Inc<|#|>employment<|#|>Steve Jobs served as CEO of Apple Inc. and led product development.
relation<|#|>Apple Inc<|#|>Cupertino<|#|>location<|#|>The company's headquarters is located in Cupertino, California.
relation<|#|>Steve Wozniak<|#|>Apple Inc<|#|>co-founder<|#|>Steve Wozniak was one of the co-founders of Apple Inc.
<|COMPLETE|>

================================================================================
ANALYSIS:
================================================================================
Entities found: 4
Relationships found: 3
Uses correct delimiter (<|#|>): True
Has completion marker: True

[OK] qwen3:0.6b WORKS with LightRAG format!
Generation time: 51.28s
```

---

## Memory Constraint Analysis

### Root Cause: Docker Desktop Memory Limit

```powershell
# System Check Results
Total Visible Memory: 16,916,884 KB (~16.5 GB)
Docker Desktop Limit: 7.63 GB (configured in Docker Desktop settings)
Ollama Available: ~5.6 GB (after Docker overhead ~2GB)
```

### Why Models Fail

**Download size ≠ Runtime memory requirement**

Example: qwen3:4b
- Download size: 2.5 GB (seems OK)
- Runtime memory: **10 GB** (FAILS - exceeds 5.6GB available)

Ollama error message:
```
model requires more system memory (10.0 GiB) than is available (5.6 GiB) (status code: 500)
```

### Solution Options

**Option 1: Use qwen3:0.6b (RECOMMENDED)**
- ✅ Works within current constraints
- ✅ Produces correct format
- ✅ No configuration changes needed
- ⚠️ Smaller model (lower quality responses)

**Option 2: Increase Docker Desktop Memory**
1. Open Docker Desktop
2. Settings → Resources → Memory
3. Increase from 7.63GB to **12-14GB**
4. Restart Docker Desktop
5. Test qwen3:4b or qwen2.5:7b

---

## SmolLM Test Results (FAILED)

**Model:** `smollm` (990MB, HuggingFace SmolLM3)

**Problem:** Model completely misunderstood the task and produced Python code instead of entities:

```python
Here is a Python function that implements this approach:

```python
import re
from typing import List

def extract_entities_and_relationships(text: str) -> List[str]:
    """
    Extracts entities and relationships from the input text.
    """
    entities = []
    ...
```

**Conclusion:** SmolLM is NOT suitable for LightRAG entity extraction tasks.

---

## Files Updated

### Test Scripts Created
1. **scripts/test_lightrag_prompts.py**
   - Updated delimiter from `|` to `<|#|>`
   - Tests qwen3:0.6b with correct format
   - ✅ Working

2. **scripts/test_all_models_lightrag.py**
   - Comprehensive model testing script
   - Tests all available Ollama models
   - Memory usage analysis

3. **scripts/test_smollm3.py**
   - Dedicated SmolLM test
   - Results: Model fails to follow instructions

### Integration Tests Updated
**tests/integration/test_sprint5_critical_e2e.py**

All LightRAG tests updated to use `qwen3:0.6b`:
- Line 307: Test 5.3 (Graph Construction)
- Line 363: Test 5.4 (Local Search)
- Line 412: Test 5.5 (Global Search)
- Line 460: Test 5.6 (Hybrid Search)
- Line 532: Test 5.8 (Incremental Updates)

**Previous model:** `qwen2.5:7b` (OUT OF MEMORY)
**New model:** `qwen3:0.6b` (WORKING)

---

## LightRAG Configuration Requirements

### Minimum Requirements
- **Context Window:** 32K tokens minimum
- **Delimiter Format:** `<|#|>` (NOT `|` or `<|>`)
- **Completion Marker:** `<|COMPLETE|>`
- **Temperature:** 0.0-0.1 (for consistency)
- **Max Tokens:** 2000+ (for entity extraction)

### Ollama Configuration
```python
response = await client.generate(
    model="qwen3:0.6b",
    prompt=lightrag_prompt,
    options={
        "temperature": 0.0,
        "num_predict": 2000,
        "num_ctx": 32768,  # 32K context window
    },
)
```

---

## Recommendations

### Immediate Action (DONE)
✅ **Use qwen3:0.6b for all Sprint 5 LightRAG tests**
- All test files updated
- Model works within memory constraints
- Correct delimiter format confirmed

### Future Improvements (Optional)

**If Better Quality Needed:**
1. Increase Docker Desktop memory to 12-14GB
2. Test qwen3:4b (256K context, better quality)
3. Test qwen2.5:7b (7B parameters, higher quality)

**Model Upgrade Path:**
- Current: `qwen3:0.6b` (600M parameters, 32K context)
- Next: `qwen3:4b` (4B parameters, 256K context) - requires 10GB RAM
- Best: `qwen2.5:7b` (7B parameters, 128K context) - requires 8.3GB RAM

---

## Next Steps

1. ✅ **Sprint 5 tests ready** - All using qwen3:0.6b
2. ⏭️ **Run Sprint 5 E2E tests** - Verify model works in integration tests
3. ⏭️ **Monitor test results** - Check entity extraction quality
4. 🔄 **Optional:** Increase Docker memory if higher quality needed

---

## References

- **LightRAG Source:** `lightrag/prompt.py` (delimiter definitions)
- **Neo4j Article:** https://neo4j.com/blog/developer/under-the-covers-with-lightrag-extraction/ (outdated delimiter)
- **HuggingFace SmolLM:** https://huggingface.co/HuggingFaceTB/SmolLM3-3B (tested, failed)
- **Qwen Models:** Alibaba Cloud Qwen family (qwen3:0.6b, qwen3:4b, qwen2.5:7b)
