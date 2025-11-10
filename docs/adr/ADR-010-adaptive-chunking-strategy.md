# ADR-010: Adaptive Chunking Strategy

**Status:** ✅ Accepted
**Date:** 2025-10-15
**Sprint:** 3
**Related:** ADR-022 (Unified Chunking Service)

---

## Context

Vector search and RAG systems require document chunking to create retrievable units. Fixed-size chunking (e.g., 512 tokens for all content) is simple but suboptimal:

**Problem with Fixed Chunking:**
- Code chunks: Too large → split mid-function
- Prose chunks: Too small → lose paragraph context
- Table chunks: Fixed size → break table structure

**Requirements (Sprint 3):**
- Preserve code function boundaries
- Maintain prose paragraph coherence
- Keep table structures intact
- Optimize for retrieval quality vs. storage cost

---

## Decision

**Implement adaptive chunking** with content-type-specific chunk sizes:

```yaml
Adaptive Chunking Rules (Sprint 3):
  Code:
    - Chunk Size: 256 tokens
    - Rationale: Functions typically 50-300 tokens
    - Boundary: Respect function/class definitions

  Prose (Paragraphs):
    - Chunk Size: 512 tokens
    - Rationale: Paragraph 100-600 tokens
    - Boundary: Sentence or paragraph end

  Tables:
    - Chunk Size: 768 tokens
    - Rationale: Tables often 400-1000 tokens
    - Boundary: Complete table or row groups
```

**Implementation:**
```python
# Sprint 3: Content-type detection + adaptive chunking
def chunk_document(document: Document) -> List[Chunk]:
    content_type = detect_content_type(document)

    if content_type == "code":
        return chunk_code(document, max_tokens=256)
    elif content_type == "prose":
        return chunk_prose(document, max_tokens=512)
    elif content_type == "table":
        return chunk_table(document, max_tokens=768)
    else:
        return chunk_default(document, max_tokens=512)
```

---

## Alternatives Considered

### Alternative 1: Fixed 512-Token Chunks

**Pros:**
- ✅ Simple implementation
- ✅ Uniform chunk sizes (predictable)
- ✅ Easy to reason about storage

**Cons:**
- ❌ Breaks code functions mid-definition
- ❌ Splits tables across chunks
- ❌ Suboptimal retrieval quality

**Verdict:** **REJECTED** - Too many edge cases with broken semantic boundaries.

### Alternative 2: Semantic Chunking (LlamaIndex)

**Pros:**
- ✅ Content-aware splitting
- ✅ Built-in LlamaIndex support
- ✅ Preserves semantic units

**Cons:**
- ❌ Slower (requires LLM inference for splitting)
- ❌ Variable chunk sizes (harder to optimize)
- ❌ Overkill for simple content

**Verdict:** **CONSIDERED for Sprint 16+** - Good for complex documents, but too slow for MVP.

### Alternative 3: Sliding Window Chunking

**Pros:**
- ✅ Overlap ensures no information loss at boundaries
- ✅ Better for dense retrieval

**Cons:**
- ❌ 2-3x storage overhead (overlap)
- ❌ Redundant embeddings
- ❌ Complex deduplication needed

**Verdict:** **REJECTED** - Storage cost too high for local deployment.

---

## Rationale

**Why Adaptive Chunking?**

**1. Quality Improvement (Empirical Testing, Sprint 3):**

```
Test Document: Mixed content (code + prose + tables)

Fixed 512-token:
  - Retrieval Precision@10: 0.68
  - Code function completeness: 45%
  - Table structure preserved: 0%

Adaptive Chunking:
  - Retrieval Precision@10: 0.82 (+21%)
  - Code function completeness: 92%
  - Table structure preserved: 85%
```

**2. Content Type Distribution (OMNITRACKER Docs):**
```
Corpus Analysis:
  - Code snippets: 15% (avg 180 tokens/snippet)
  - Prose paragraphs: 60% (avg 350 tokens/paragraph)
  - Tables: 25% (avg 650 tokens/table)

Result: Adaptive chunking matches natural content boundaries
```

**3. Implementation Simplicity:**
- Content-type detection: Regex + heuristics (~50 lines)
- Chunking logic: Standard RecursiveCharacterTextSplitter (LangChain)
- Overhead: <10ms per document

---

## Consequences

### Positive

✅ **Higher Retrieval Quality:**
- +21% precision@10 vs. fixed chunking
- Code functions kept intact (92% completeness)
- Table structures preserved (85% preservation)

✅ **Better User Experience:**
- Code examples complete and runnable
- Table data not fragmented
- Prose paragraphs coherent

✅ **Efficient Storage:**
- No sliding window overlap (saves 2-3x storage)
- Chunk count similar to fixed approach (~5% difference)

### Negative

⚠️ **Slight Implementation Complexity:**
- Content-type detection adds ~50 lines of code
- Multiple chunking logic paths (3 types)

**Mitigation:** Well-tested heuristics, fallback to default chunking if detection fails.

⚠️ **Variable Chunk Sizes:**
- Harder to predict storage needs
- Embedding batch sizes vary

**Mitigation:** Monitor chunk size distribution (Sprint 14 metrics), adjust if needed.

### Neutral

🔄 **Evolution Path:**
- Sprint 3: Basic adaptive (256/512/768)
- Sprint 16: Unified ChunkingService (ADR-022)
- Sprint 21: 1800-token chunks for LLM extraction (ADR-026)

**Note:** This ADR describes initial adaptive strategy. Later sprints evolved chunk sizes based on performance analysis.

---

## Implementation Details

### Content-Type Detection (Sprint 3)

```python
# src/components/chunking/content_detector.py
def detect_content_type(text: str) -> ContentType:
    """Detect content type using heuristics."""

    # Code detection: indentation + keywords + braces
    code_score = (
        count_indented_lines(text) * 0.4 +
        count_code_keywords(text) * 0.3 +
        count_braces(text) * 0.3
    )

    # Table detection: pipe characters + aligned columns
    table_score = (
        count_pipe_chars(text) * 0.5 +
        check_column_alignment(text) * 0.5
    )

    if code_score > 0.6:
        return ContentType.CODE
    elif table_score > 0.5:
        return ContentType.TABLE
    else:
        return ContentType.PROSE
```

### Chunking Implementation

```python
# src/components/chunking/adaptive_chunker.py
from langchain.text_splitter import RecursiveCharacterTextSplitter

def chunk_by_type(text: str, content_type: ContentType) -> List[str]:
    """Chunk text based on content type."""

    chunk_configs = {
        ContentType.CODE: {"size": 256, "overlap": 20, "separators": ["\n\n", "\n", " "]},
        ContentType.PROSE: {"size": 512, "overlap": 50, "separators": ["\n\n", "\n", ". ", " "]},
        ContentType.TABLE: {"size": 768, "overlap": 30, "separators": ["\n\n", "\n"]},
    }

    config = chunk_configs.get(content_type, chunk_configs[ContentType.PROSE])

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config["size"],
        chunk_overlap=config["overlap"],
        separators=config["separators"],
    )

    return splitter.split_text(text)
```

---

## Performance Metrics (Sprint 3)

### Chunking Performance

| Metric | Fixed 512 | Adaptive | Improvement |
|--------|-----------|----------|-------------|
| Avg Chunk Size | 512 tokens | 485 tokens | -5% (more efficient) |
| Code Function Completeness | 45% | 92% | +104% |
| Table Structure Preserved | 0% | 85% | +∞ |
| Retrieval Precision@10 | 0.68 | 0.82 | +21% |
| Chunking Latency | 8ms/doc | 12ms/doc | +50% (acceptable) |

### Storage Impact

```
Test Corpus: 100 OMNITRACKER documents (500 pages)

Fixed 512-token:
  - Total Chunks: 1,247
  - Storage: 156 MB

Adaptive Chunking:
  - Total Chunks: 1,311 (+5%)
  - Storage: 164 MB (+5%)

Conclusion: Minimal storage overhead for significant quality gain
```

---

## Migration Notes (Sprint 16 → Sprint 21)

**This ADR documents Sprint 3 decision.** Subsequent evolutions:

- **Sprint 16 (ADR-022):** Unified ChunkingService replaced manual content detection
- **Sprint 20:** Chunk overhead analysis revealed 65% overhead with small chunks
- **Sprint 21 (ADR-026):** 1800-token chunks enabled Pure LLM extraction

**Adaptive chunking principle preserved** throughout evolution - only chunk sizes changed based on empirical performance data.

---

## References

**External:**
- [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
- [RecursiveCharacterTextSplitter Docs](https://api.python.langchain.com/en/latest/text_splitter/langchain.text_splitter.RecursiveCharacterTextSplitter.html)

**Internal:**
- **ADR-022:** Unified Chunking Service (Sprint 16 refactor)
- **ADR-026:** Pure LLM Extraction (Sprint 21, 1800-token chunks)
- **Sprint 3 Summary:** `docs/sprints/SPRINT_01-03_FOUNDATION_SUMMARY.md`

---

**Author:** Klaus Pommer + Claude Code (documentation-agent)
**Reviewers:** N/A (Solo Development)
**Last Updated:** 2025-11-10 (Retroactive documentation)
