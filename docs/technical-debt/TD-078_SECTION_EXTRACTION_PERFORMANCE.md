# TD-078: Section Extraction Performance Optimization

**Status:** OPEN
**Priority:** HIGH
**Story Points:** 18 SP (7 SP Sprint 67 + 11 SP Sprint 68)
**Created:** 2025-12-29 (Sprint 66 Analysis)
**Target:** Sprint 67-68
**Analysis:** [PERF-001](../analysis/PERF-001_Section_Extraction_Performance.md)

---

## Problem Statement

Section extraction is the **slowest component** in the ingestion pipeline, taking 2-15 minutes for medium-sized PDFs. This creates a poor user experience and limits throughput.

### Real-World Performance Data

| Document | Text Blocks | Duration | Throughput | Severity |
|----------|-------------|----------|------------|----------|
| Doc 1 | 146 texts | 112s (1.9min) | 0.31 sections/sec | ⚠️ Acceptable |
| Doc 2 | 146 texts | 122s (2.0min) | 0.34 sections/sec | ⚠️ Acceptable |
| Doc 3 | 794 texts | 920s (15.3min) | 0.02 sections/sec | 🔴 **CRITICAL** |
| Doc 4 (GenericAPI) | 550 texts | 545s (9.1min) | 0.99 sections/sec | 🔴 **CRITICAL** |

**Key Observation:** Non-linear scaling! 794 texts took 7.5x longer than 146 texts, despite being only 5.4x more text blocks.

---

## Root Cause Analysis

**File:** `src/components/ingestion/section_extraction.py`

### Identified Bottlenecks

1. **Sequential Processing** - All text blocks processed one-by-one (no parallelization)
2. **Repeated Tokenization** - Each text block tokenized individually without batching
3. **Heading Detection** - Regex patterns recompiled on every block
4. **No Caching** - Same heading patterns checked repeatedly
5. **Inefficient Data Structures** - O(n) linear search for section tree traversal

### Performance Characteristics

```
146 texts → 112s = 0.77s per text  ✅ OK
794 texts → 920s = 1.16s per text  ⚠️  Degrading (+51% slower)
550 texts → 545s = 0.99s per text  ⚠️  Degrading (+29% slower)
```

**Why does per-text time increase?**
- Larger section trees require more traversal
- More heading hierarchy levels → more comparisons
- No algorithmic optimization for large documents

---

## Optimization Strategy

### Sprint 67: Profiling + Quick Wins (7 SP)

**Target:** 2-3x speedup (146 texts: 112s → 40-50s)

#### Tasks

1. **Add Profiling Instrumentation (2 SP)**
   - Detailed timing logs per operation
   - Memory usage tracking
   - Export profiling data to CSV

2. **Run Benchmark Suite (1 SP)**
   - Test with 3 document sizes (small/medium/large)
   - Generate performance report
   - Identify top 3 bottlenecks

3. **Implement Quick Wins (3 SP)**
   - **Batch Tokenization** (30-50% faster)
     ```python
     # BEFORE: 550 individual calls
     for text in texts:
         tokens = tokenizer.encode(text)

     # AFTER: Single batch call
     all_tokens = tokenizer.encode_batch([t["text"] for t in texts])
     ```

   - **Compile Regex Patterns** (10-20% faster)
     ```python
     # BEFORE: Recompiled every call
     def _is_heading(text):
         if re.match(r'^[A-Z].*:', text):
             return True

     # AFTER: Module-level compilation
     HEADING_PATTERNS = [
         re.compile(r'^[A-Z].*:'),
         re.compile(r'^\d+\.'),
     ]

     def _is_heading(text):
         return any(p.match(text) for p in HEADING_PATTERNS)
     ```

   - **Early Exit Conditions** (5-10% faster)
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

4. **Verify Improvements (1 SP)**
   - Re-run benchmarks
   - Compare before/after metrics
   - Document actual speedup achieved

---

### Sprint 68: Parallelization + Caching (11 SP)

**Target:** 5-10x total speedup (146 texts: 112s → 12-15s)

#### Tasks

1. **Design Parallel Algorithm (2 SP)**
   - Thread-safe section tree
   - Merge strategy for chunks
   - Handle edge cases (single-section docs)

2. **Implement Parallel Processing (5 SP)**
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

3. **Add Caching Layer (2 SP)**
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=1000)
   def is_heading_style(font_size, font_weight, text_prefix):
       """Cache heading decisions based on style."""
       return font_size > 14 or font_weight > 700
   ```

4. **Integration Testing (2 SP)**
   - E2E tests with large PDFs (794+ texts)
   - Performance regression tests
   - Verify section hierarchy correctness

---

## Success Metrics

| Metric | Current | Sprint 67 Target | Sprint 68 Target |
|--------|---------|------------------|------------------|
| 146 texts | 112s (1.9min) | 40-50s (2.5x) | 12-15s (8x) |
| 550 texts | 545s (9.1min) | 200-250s (2.5x) | 60-80s (8x) |
| 794 texts | 920s (15.3min) | 300-400s (2.5x) | 90-120s (8x) |
| Throughput | 0.02-0.34 sec/text | 0.5-1.0 sec/text | 2-5 sec/text |

**Business Impact:**
- User experience: 15min → 2min (8x faster)
- Throughput: 0.02 docs/sec → 0.5 docs/sec (25x improvement)
- Scalability: Handle 10x larger documents

---

## Risk Assessment

### Low Risk ✅
- Batch tokenization (well-tested in transformers)
- Regex compilation (standard Python optimization)
- Profiling instrumentation (read-only changes)

### Medium Risk ⚠️
- Parallel processing (requires careful testing for correctness)
- Caching (must invalidate correctly)

### High Risk 🔴
- Changing section hierarchy algorithm (could break downstream)
  - **Mitigation:** Comprehensive E2E tests before deployment
- Rust extensions (adds dependency complexity)
  - **Deferred to Sprint 69+**

---

## Implementation Plan

### Sprint 67: Analysis & Quick Wins (7 SP)

**Duration:** 3-5 days

| Task | SP | Description |
|------|-----|-------------|
| Profiling | 2 | Add timing instrumentation + export |
| Benchmarks | 1 | Run 3-document test suite |
| Quick Wins | 3 | Batch tokenization + regex + early exits |
| Verification | 1 | Re-run benchmarks, document results |

**Deliverables:**
- Profiling data (CSV export)
- Performance report comparing before/after
- Code changes in `section_extraction.py`
- Updated benchmarks in `tests/performance/`

---

### Sprint 68: Parallelization (11 SP)

**Duration:** 5-7 days

| Task | SP | Description |
|------|-----|-------------|
| Design | 2 | Thread-safe algorithm design |
| Implementation | 5 | ThreadPoolExecutor integration |
| Caching | 2 | LRU cache for heading patterns |
| Testing | 2 | E2E tests + regression tests |

**Deliverables:**
- Parallel section extraction implementation
- Caching layer with invalidation
- 95% test coverage
- Performance regression test suite

---

## Acceptance Criteria

### Sprint 67
- [ ] Profiling instrumentation added to `section_extraction.py`
- [ ] Benchmark suite runs successfully (3 documents)
- [ ] Batch tokenization implemented
- [ ] Regex patterns compiled at module level
- [ ] Early exit conditions added
- [ ] Performance improvement: 2-3x speedup achieved
- [ ] Documentation updated with performance data

### Sprint 68
- [ ] Parallel processing implemented with ThreadPoolExecutor
- [ ] LRU caching added for heading patterns
- [ ] Section hierarchy correctness verified (E2E tests)
- [ ] Performance improvement: 5-10x total speedup achieved
- [ ] No regressions in chunking quality
- [ ] Backward compatibility maintained

---

## Dependencies

- **Upstream:** None (self-contained optimization)
- **Downstream:**
  - Chunking quality must remain identical
  - Section hierarchy structure unchanged
  - E2E tests must pass (no breaking changes)

---

## Long-Term Roadmap (Sprint 69+)

### Future Optimizations (10-15x speedup potential)

1. **Rust Extension for Tokenization**
   ```python
   from tokenizers import Tokenizer
   # 10-100x faster than pure Python
   tokenizer = Tokenizer.from_pretrained("bert-base-uncased")
   ```

2. **Streaming Processing**
   ```python
   async def extract_sections_streaming(text_stream):
       async for text_block in text_stream:
           section = process_block(text_block)
           yield section  # Start chunking immediately
   ```

3. **GPU Acceleration**
   - Use CUDA for regex matching (cuDF)
   - GPU-based tokenization (RAPIDS cuML)

---

## Related Items

- **TD-070:** Ingestion Performance Tuning (broader pipeline optimization)
- **ADR-039:** Adaptive Section-Aware Chunking (current implementation)
- **PERF-001:** Section Extraction Performance Analysis (detailed investigation)

---

## Monitoring & Alerts

Post-deployment monitoring:

```python
# Prometheus metrics
section_extraction_duration_seconds.histogram()
section_extraction_texts_per_second.gauge()
section_extraction_errors_total.counter()
```

**Alerts:**
- Section extraction >120s for 146 texts (regression)
- Throughput <0.5 sections/sec (performance degradation)
- Error rate >1% (quality issue)

---

**Created by:** Claude Code
**Analysis Date:** 2025-12-29
**Last Updated:** 2025-12-29
**Document Version:** 1.0
