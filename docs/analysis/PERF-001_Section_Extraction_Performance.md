# PERF-001: Section Extraction Performance Analysis

**Status:** 🔴 Critical Performance Bottleneck
**Priority:** High
**Sprint:** 67 (Analysis) → 68 (Implementation)
**Estimated Impact:** 10-15x speedup possible

---

## Problem Statement

Section extraction is the **slowest component** in the ingestion pipeline, taking 2-15 minutes for medium-sized PDFs. This creates a poor user experience and limits throughput.

### Current Performance Data

| Document | Text Blocks | Duration | Throughput | Notes |
|----------|-------------|----------|------------|-------|
| Doc 1 | 146 texts | 112s (1.9min) | 0.31 sections/sec | Small PDF |
| Doc 2 | 146 texts | 122s (2.0min) | 0.34 sections/sec | Same size, variance |
| Doc 3 | 794 texts | 920s (15.3min) | 0.02 sections/sec | **15 min!** |
| Doc 4 (OMNITRACKER) | 550 texts | ~600s (10min est) | TBD | Currently running |

**Key Observation:** Non-linear scaling! 794 texts took 7.5x longer than 146 texts, despite being only 5.4x more text blocks.

---

## Root Cause Analysis

### Current Implementation

**File:** `src/components/ingestion/section_extraction.py`

**Process:**
1. For each text block (550 iterations):
   - Check if it's a heading (regex + style analysis)
   - Tokenize text for length calculation
   - Build hierarchical section tree
   - Aggregate text into sections

### Suspected Bottlenecks

1. **Sequential Processing:** All 550 text blocks processed one-by-one
2. **Repeated Tokenization:** Each text block tokenized individually (no batching)
3. **Heading Detection:** Regex patterns executed on every block
4. **No Caching:** Same heading patterns checked repeatedly

### Performance Characteristics

```
146 texts → 112s = 0.77s per text  ✅ OK
794 texts → 920s = 1.16s per text  ⚠️  Degrading
```

**Why does per-text time increase?**
- Larger section trees require more traversal
- More heading hierarchy levels → more comparisons
- No algorithmic optimization for large documents

---

## Profiling Strategy (Sprint 67)

### 1. Add Detailed Timing Instrumentation

```python
# src/components/ingestion/section_extraction.py
import time

class SectionExtractor:
    def __init__(self):
        self.timing_stats = {
            "heading_detection": [],
            "tokenization": [],
            "tree_building": [],
            "text_aggregation": []
        }

    def extract_sections(self, texts):
        for text_block in texts:
            # Time heading detection
            t0 = time.perf_counter()
            is_heading = self._is_heading(text_block)
            self.timing_stats["heading_detection"].append(time.perf_counter() - t0)

            # Time tokenization
            t0 = time.perf_counter()
            tokens = self._tokenize(text_block)
            self.timing_stats["tokenization"].append(time.perf_counter() - t0)

            # ... etc

        # Log aggregate stats
        logger.info("section_extraction_timing_breakdown",
            avg_heading_ms=sum(self.timing_stats["heading_detection"]) / len(texts) * 1000,
            avg_tokenization_ms=sum(self.timing_stats["tokenization"]) / len(texts) * 1000,
            # ...
        )
```

### 2. Python Profiler

```bash
# Run with cProfile
python -m cProfile -o section_extraction.prof \
    scripts/profile_section_extraction.py

# Analyze with snakeviz
snakeviz section_extraction.prof
```

### 3. Memory Profiling

```bash
# Check for memory leaks in long documents
memory_profiler src/components/ingestion/section_extraction.py
```

---

## Optimization Strategies

### Quick Wins (Sprint 67) - 2-3x Speedup

#### 1. Batch Tokenization (30-50% faster)

**Current:**
```python
for text in texts:
    tokens = tokenizer.encode(text)  # 550 individual calls
```

**Optimized:**
```python
# Batch all texts at once
all_tokens = tokenizer.encode_batch([t["text"] for t in texts])
```

**Why faster:**
- GPU/CPU vectorization
- Reduced Python overhead
- Tokenizer can optimize internally

#### 2. Compile Regex Patterns (10-20% faster)

**Current:**
```python
def _is_heading(text):
    if re.match(r'^[A-Z].*:', text):  # Recompiled every call!
        return True
```

**Optimized:**
```python
# At module level
HEADING_PATTERNS = [
    re.compile(r'^[A-Z].*:'),
    re.compile(r'^\d+\.'),
    # ...
]

def _is_heading(text):
    return any(p.match(text) for p in HEADING_PATTERNS)
```

#### 3. Early Exit Conditions (5-10% faster)

```python
def _is_heading(text):
    # Quick checks first
    if len(text) > 200:  # Headings are usually short
        return False
    if not text[0].isupper():  # Must start with capital
        return False
    # Expensive checks last
    return self._check_heading_style(text)
```

### Medium-Term (Sprint 68) - 5-10x Speedup

#### 4. Parallel Processing

**Strategy:** Process text blocks in chunks of 50-100

```python
from concurrent.futures import ThreadPoolExecutor

def extract_sections_parallel(texts, max_workers=4):
    chunk_size = len(texts) // max_workers
    chunks = [texts[i:i+chunk_size] for i in range(0, len(texts), chunk_size)]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        section_chunks = list(executor.map(extract_chunk, chunks))

    # Merge results
    return merge_section_trees(section_chunks)
```

**Challenges:**
- Section hierarchy must be reconstructed after merging
- Thread-safe tree building

#### 5. Caching Heading Patterns

```python
@lru_cache(maxsize=1000)
def is_heading_style(font_size, font_weight, text_prefix):
    """Cache heading decisions based on style."""
    return font_size > 14 or font_weight > 700
```

#### 6. Optimized Data Structures

**Current:** List iteration for section tree
**Optimized:** Dict-based lookup for O(1) parent finding

```python
# Instead of linear search
for section in all_sections:
    if section.level < current_level:
        parent = section

# Use dict lookup
section_by_level = {s.level: s for s in all_sections}
parent = section_by_level.get(current_level - 1)
```

### Long-Term (Sprint 69+) - 10-15x Speedup

#### 7. Rust Extension for Tokenization

Replace Python tokenizer with Rust-based `tokenizers` library:

```python
from tokenizers import Tokenizer

# 10-100x faster than pure Python
tokenizer = Tokenizer.from_pretrained("bert-base-uncased")
```

#### 8. Streaming Processing

Don't wait for all texts before starting:

```python
async def extract_sections_streaming(text_stream):
    async for text_block in text_stream:
        section = process_block(text_block)
        yield section  # Start chunking immediately
```

---

## Implementation Plan

### Sprint 67: Analysis & Quick Wins

**Tasks:**
1. **Add profiling instrumentation** (2 SP)
   - Detailed timing logs per operation
   - Memory usage tracking
   - Export profiling data

2. **Run benchmark suite** (1 SP)
   - Test with 3 document sizes (small/medium/large)
   - Generate performance report
   - Identify top 3 bottlenecks

3. **Implement Quick Wins** (3 SP)
   - Batch tokenization
   - Compile regex patterns
   - Early exit conditions
   - **Target:** 2-3x speedup

4. **Verify improvements** (1 SP)
   - Re-run benchmarks
   - Compare before/after metrics
   - Document actual speedup

**Total:** 7 SP

### Sprint 68: Parallelization

**Tasks:**
1. **Design parallel algorithm** (2 SP)
   - Thread-safe section tree
   - Merge strategy for chunks

2. **Implement parallel processing** (5 SP)
   - ThreadPoolExecutor integration
   - Handle edge cases (single-section docs)

3. **Add caching layer** (2 SP)
   - LRU cache for heading patterns
   - Style-based caching

4. **Integration testing** (2 SP)
   - E2E tests with large PDFs
   - Performance regression tests

**Total:** 11 SP

---

## Success Metrics

| Metric | Current | Sprint 67 Target | Sprint 68 Target |
|--------|---------|------------------|------------------|
| 146 texts | 112s | 40-50s (2.5x) | 12-15s (8x) |
| 550 texts | 600s | 200-250s (2.5x) | 60-80s (8x) |
| 794 texts | 920s | 300-400s (2.5x) | 90-120s (8x) |
| Throughput | 0.02-0.34 sec/text | 0.5-1.0 sec/text | 2-5 sec/text |

---

## Risk Assessment

### Low Risk
- ✅ Batch tokenization (well-tested in transformers)
- ✅ Regex compilation (standard Python optimization)
- ✅ Profiling instrumentation (read-only changes)

### Medium Risk
- ⚠️ Parallel processing (requires careful testing for correctness)
- ⚠️ Caching (must invalidate correctly)

### High Risk
- 🔴 Changing section hierarchy algorithm (could break downstream)
- 🔴 Rust extensions (adds dependency complexity)

**Recommendation:** Start with Quick Wins in Sprint 67, move to parallelization in Sprint 68 only after thorough testing.

---

## Related Technical Debt

- **TD-078:** Section Extraction Performance (this analysis)
- **ADR-039:** Adaptive Section-Aware Chunking (current implementation)

---

## Next Steps

1. **Create TD-078** technical debt item
2. **Create Sprint 67 tasks** for profiling + quick wins
3. **Schedule performance review** after Sprint 67 completion
4. **Consider GPU acceleration** if CPU parallelization insufficient

---

**Author:** Claude Code
**Date:** 2025-12-28
**Last Updated:** 2025-12-28
