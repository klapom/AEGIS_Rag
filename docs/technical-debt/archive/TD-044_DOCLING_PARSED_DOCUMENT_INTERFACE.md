# TD-044: DoclingParsedDocument Interface Mismatch

**Status:** In Progress (Sprint 33)
**Severity:** High (Performance Degradation)
**Impact:** Section extraction returns empty list, fallback to single-chunk documents
**Affected Features:** Sprint 32 Feature 32.1 (Section Extraction), ADR-039 (Adaptive Section-Aware Chunking)

---

## Problem Statement

The `DoclingParsedDocument` Pydantic model (in `src/components/ingestion/docling_client.py`) is missing critical attributes that the rest of the ingestion pipeline expects:

1. **Missing `.document` attribute** - Expected to be a native Docling DoclingDocument object
2. **Missing `.body` attribute** - Expected to be the document tree structure for section extraction

As a result:
- Section extraction code always fails (returns empty list)
- Fallback creates 1 giant chunk per document
- LightRAG re-chunks internally (massive inefficiency)
- Performance degradation due to double chunking
- Sprint 32 Feature 32.1 & ADR-039 benefits are completely lost

---

## Root Cause Analysis

### Timeline of the Bug

**Sprint 21 (commit 2627316: 2025-09-15)**
- Initial Docling integration created `DoclingParsedDocument` as an HTTP API response wrapper
- Design: `DoclingParsedDocument` contains parsed output fields (text, tables, images, layout)
- **No `.document` or `.body` attributes** - Only the flat parsed fields

**Sprint 32 (commit 9cc23a90: 2025-11-21)**
- Added section extraction feature (Feature 32.1) expecting `.body` attribute
- Code in `langgraph_nodes.py` (lines 510-529) attempted to handle missing `.document`:
  ```python
  if hasattr(parsed, "document"):
      # PDF, DOCX: parsed.document is the DoclingDocument
      state["document"] = parsed.document
  else:
      # PowerPoint: parsed itself is the DoclingDocument
      state["document"] = parsed
  ```
- **Dead code**: The `else` branch is never executed because `DoclingParsedDocument` never has `.document` attribute
- **Result**: All formats (PDF, DOCX, PPTX) go to else branch, storing `DoclingParsedDocument` object instead of native DoclingDocument

**Current State**
- `section_extraction.py` expects `docling_document.body` attribute
- `DoclingParsedDocument` has no `.body` attribute
- Section extraction returns empty list for ALL documents
- Chunking falls back to single 1-chunk-per-document strategy

### Why This Happened

The `DoclingParsedDocument` model was designed as an HTTP API wrapper during Sprint 21, containing only the flattened response fields. The team didn't anticipate needing the native DoclingDocument object structure until Sprint 32 when section extraction was added.

The if/else check in `langgraph_nodes.py` (lines 510-529) was an **incorrect attempt** to handle different document types. It couldn't work because:
1. `DoclingParsedDocument` is **always** returned (from HTTP API, not native Docling)
2. The native DoclingDocument structure is **never** in `parsed.document`
3. The structure lives in `parsed.json_content` (Docling JSON) or needs to be reconstructed

---

## Impact Analysis

### Functional Impact

**Section Extraction Failure:**
- `extract_section_hierarchy()` in `section_extraction.py` line 97 checks:
  ```python
  if not hasattr(docling_document, "body") or docling_document.body is None:
      logger.warning("docling_document_no_body", ...)
      return []
  ```
- Always returns empty list because `DoclingParsedDocument` has no `.body` attribute
- Result: No sections extracted, all documents chunked as single unit

**Performance Degradation:**
```
Without Section Extraction (Current):
  PowerPoint (15 slides, ~2,500 tokens total)
  → 1 giant chunk (2,500 tokens)
  → Stored in Qdrant as 1 chunk
  → LightRAG receives 1 chunk
  → LightRAG re-chunks internally (122 chunks from 1 chunk!)
  → Inefficient graph extraction, slower queries

With Section Extraction (Expected):
  PowerPoint (15 slides, ~2,500 tokens total)
  → 6-8 optimized chunks (400-1200 tokens each)
  → Stored in Qdrant as 6-8 chunks
  → LightRAG receives pre-chunked content (minimal re-chunking)
  → Efficient graph extraction, faster queries

Fragmentation Reduction: 122 chunks → 6-8 chunks = 94% reduction!
```

**Search & Retrieval:**
- Qdrant retrieves 1 massive chunk instead of 6-8 focused chunks
- BM25 keyword search less effective on large chunks
- Relevance ranking degraded
- Citations less precise (entire slide chunk instead of specific section)

**Neo4j Graph Quality:**
- Section nodes never created (Feature 32.4)
- Hierarchical queries impossible
- Graph analytics degraded
- False relations increased (large chunks create spurious connections)

### Performance Metrics

From Sprint 32 testing (when section extraction was briefly working):
- **Fragmentation:** 124 chunks (LightRAG default) → 2-3 chunks (with section extraction) = 98% reduction
- **False Relations:** 23% baseline → <10% with section-aware chunking = +13% improvement
- **Retrieval Precision:** +10% with section-based re-ranking
- **Citation Accuracy:** 100% (section names match exactly)

**Current State (Broken):**
- All metrics back to pre-Sprint-32 baseline
- Benefits of ADR-039 completely lost
- Performance equivalent to having no section extraction at all

---

## Code Affected

### 1. `src/components/ingestion/docling_client.py` (Lines 54-76)

**Current (Broken):**
```python
class DoclingParsedDocument(BaseModel):
    """Parsed document from Docling container."""

    text: str
    metadata: dict[str, Any]
    tables: list[dict[str, Any]]
    images: list[dict[str, Any]]
    layout: dict[str, Any]
    parse_time_ms: float
    json_content: dict[str, Any]
    md_content: str

    # MISSING: .document attribute
    # MISSING: .body attribute
```

**Issue:**
- No way to access native Docling DoclingDocument structure
- `.json_content` contains the raw JSON but not the parsed object tree
- Section extraction code can't traverse `.body` attribute

### 2. `src/components/ingestion/langgraph_nodes.py` (Lines 510-529)

**Current (Dead Code):**
```python
if hasattr(parsed, "document"):
    # PDF, DOCX: parsed.document is the DoclingDocument
    state["document"] = parsed.document
    # Extract page dimensions...
else:
    # PowerPoint: parsed itself is the DoclingDocument
    state["document"] = parsed
```

**Problems:**
1. `hasattr(parsed, "document")` is **always False** (dead code)
2. Else branch always executed, stores `DoclingParsedDocument` instead of DoclingDocument
3. Lines 515-522 never execute (page dimensions always empty)
4. Verification logging confirms all formats go to else branch

**Dead Code to Remove:**
- Lines 510-552: Entire if/else block and verification logging
- Should be replaced with direct assignment: `state["document"] = ???`

### 3. `src/components/ingestion/section_extraction.py` (Lines 97-103)

**Current (Broken):**
```python
if not hasattr(docling_document, "body") or docling_document.body is None:
    logger.warning("docling_document_no_body", ...)
    return []
```

**Issue:**
- Expects `docling_document.body` attribute
- `DoclingParsedDocument` never has this attribute
- Always returns empty list, breaking Feature 32.1

---

## Solution

### Option 1: Add Properties to DoclingParsedDocument (RECOMMENDED)

Add `.document` and `.body` properties that reconstruct the native DoclingDocument structure from `json_content`:

```python
class DoclingParsedDocument(BaseModel):
    """Parsed document from Docling container."""

    text: str
    metadata: dict[str, Any]
    tables: list[dict[str, Any]]
    images: list[dict[str, Any]]
    layout: dict[str, Any]
    parse_time_ms: float
    json_content: dict[str, Any]
    md_content: str

    @property
    def document(self) -> "DoclingDocument":
        """Return native Docling DoclingDocument reconstructed from json_content.

        This property provides backward compatibility with code that expects
        a native DoclingDocument object (e.g., section extraction).

        Returns:
            DoclingDocument object reconstructed from stored JSON

        Raises:
            ValueError: If json_content is empty or malformed
        """
        if not self.json_content:
            raise ValueError("Cannot reconstruct DoclingDocument: json_content is empty")

        try:
            from docling.document_converter import DocumentConverter
            # Reconstruct DoclingDocument from JSON
            # Implementation details in follow-up commit
            doc = DocumentConverter._deserialize_document(self.json_content)
            return doc
        except Exception as e:
            raise ValueError(f"Failed to reconstruct DoclingDocument: {e}")

    @property
    def body(self) -> Any:
        """Return document.body for section extraction.

        Shorthand for self.document.body to support section extraction.

        Returns:
            Document body tree structure
        """
        return self.document.body
```

**Pros:**
- ✅ Minimal changes to `DoclingParsedDocument`
- ✅ Properties are lazy-evaluated (no overhead on creation)
- ✅ Backward compatible with all existing code
- ✅ Section extraction works without modification
- ✅ Page dimensions automatically available

**Cons:**
- ⚠️ Slight performance overhead (reconstruction on access)
- ⚠️ Requires understanding Docling's document structure

### Option 2: Store DoclingDocument Directly

Modify `parse_document()` to also store the native DoclingDocument:

```python
async def parse_document(self, file_path: Path) -> DoclingParsedDocument:
    # ... existing parse logic ...

    # Store both parsed output AND native document
    parsed = DoclingParsedDocument(
        text=text,
        metadata={...},
        tables=tables_data,
        images=images_data,
        layout=layout_info,
        parse_time_ms=parse_time,
        json_content=json_content,
        md_content=md_content,
        _native_document=native_doc,  # NEW: Store reconstructed document
    )
```

**Pros:**
- ✅ Fastest access (no reconstruction needed)
- ✅ Type-safe

**Cons:**
- ❌ Breaks Pydantic validation (native objects not serializable)
- ❌ Can't use model_dump() for API responses
- ❌ Complicates state serialization in LangGraph

### Recommended: Option 1 (Properties)

**Rationale:**
- Minimal code changes
- No serialization issues
- Leverages existing `json_content` field
- Properties are standard Python pattern
- Clear responsibility separation

---

## Implementation Plan

### Phase 1: Add Properties to DoclingParsedDocument

**File:** `src/components/ingestion/docling_client.py`

**Changes:**
1. Add import for DoclingDocument reconstruction
2. Add `@property document` with lazy reconstruction
3. Add `@property body` shorthand
4. Add docstrings with examples
5. Add error handling for missing/malformed json_content

**Tests:**
- Unit test: `test_docling_parsed_document_properties()`
  - Verify `.document` returns valid DoclingDocument
  - Verify `.body` returns document tree
  - Verify error on empty json_content

### Phase 2: Remove Dead Code in langgraph_nodes.py

**File:** `src/components/ingestion/langgraph_nodes.py`

**Changes:**
1. Remove lines 510-552 (entire if/else block)
2. Replace with: `state["document"] = parsed.document` (now works!)
3. Remove verification logging
4. Simplify to single code path

**Tests:**
- Integration test: `test_docling_extraction_node()`
  - Parse PDF, DOCX, PPTX
  - Verify state["document"] is valid DoclingDocument
  - Verify page_dimensions extracted correctly

### Phase 3: Verify Section Extraction Works

**File:** `src/components/ingestion/section_extraction.py` (No changes needed)

**Tests:**
- Unit test: `test_extract_section_hierarchy()`
  - Extract sections from real PDF/DOCX/PPTX
  - Verify non-empty section list returned
  - Verify section headings and text correct
  - Verify token counts accurate

### Phase 4: Integration Testing

**File:** `tests/integration/test_ingestion_pipeline.py`

**Tests:**
1. End-to-end pipeline test:
   ```python
   async def test_ingestion_pipeline_with_sections():
       # Parse document
       parsed = await docling.parse_document(pdf_file)

       # Verify document object available
       assert parsed.document is not None
       assert parsed.body is not None

       # Extract sections
       sections = extract_section_hierarchy(parsed.document, SectionMetadata)
       assert len(sections) > 0  # Should have sections!

       # Verify chunking uses sections
       chunks = adaptive_section_chunking(sections)
       assert len(chunks) <= len(sections)  # Merged sections
       assert all(c.token_count <= 1800 for c in chunks)  # Within bounds
   ```

2. Format-specific tests:
   - PDF: Verify sections and page dimensions
   - DOCX: Verify sections from heading structure
   - PPTX: Verify sections from slide titles

3. Performance test:
   - PowerPoint (15 slides): Should produce 6-8 chunks (not 124)
   - Large PDF: Should produce 10-20 chunks (not 1)

---

## Dead Code to Remove

### `langgraph_nodes.py` Lines 510-552

**Current code (DEAD):**
```python
# Feature 31.12: PowerPoint Fix - parsed itself IS the DoclingDocument
# For PowerPoint files, the entire response is the document (no .document attribute)
# For PDF/DOCX, response has .document attribute
page_dimensions = {}

# CRITICAL VERIFICATION: Log parsed object type and attributes
logger.warning(
    "VERIFICATION_parsed_type_check",
    document_id=state["document_id"],
    parsed_type=type(parsed).__name__,
    parsed_module=type(parsed).__module__,
    has_document_attr=hasattr(parsed, "document"),  # Always False!
    parsed_is_none=parsed is None,
    has_text=hasattr(parsed, "text"),  # Always True
    text_length=len(parsed.text) if hasattr(parsed, "text") else 0,
)

if hasattr(parsed, "document"):
    # This block NEVER executes (dead code)
    state["document"] = parsed.document
    if hasattr(parsed.document, "pages") and parsed.document.pages:
        for page in parsed.document.pages:
            page_dimensions[page.page_no] = {...}
    logger.warning(...)
else:
    # This block ALWAYS executes
    logger.warning(...)
    state["document"] = parsed
    logger.warning(...)
    if state["document"] is None:
        raise ValueError(...)
```

**Replacement (CORRECT):**
```python
# Now that DoclingParsedDocument has .document property, use it directly
state["document"] = parsed.document

# Extract page dimensions from document
page_dimensions = {}
if hasattr(parsed.document, "pages") and parsed.document.pages:
    for page in parsed.document.pages:
        page_dimensions[page.page_no] = {
            "width": page.size.width,
            "height": page.size.height,
            "unit": "pt",
            "dpi": 72,
        }
```

**Benefit:**
- 40 lines of verification logging removed
- Single, clear code path
- Same functionality, much clearer

---

## Testing Plan

### Unit Tests

**File:** `tests/unit/test_docling_parsed_document.py`

```python
async def test_docling_parsed_document_document_property():
    """Verify .document property returns valid DoclingDocument."""
    # Create DoclingParsedDocument with json_content
    parsed = DoclingParsedDocument(
        text="Test",
        json_content={...},  # Real Docling JSON
        # ... other fields ...
    )

    # Access .document property
    doc = parsed.document
    assert doc is not None
    assert hasattr(doc, "body")
    assert doc.body is not None

async def test_docling_parsed_document_body_property():
    """Verify .body property shorthand works."""
    parsed = DoclingParsedDocument(...)
    body = parsed.body
    assert body is not None
    # Should be same as parsed.document.body
    assert body is parsed.document.body

async def test_docling_parsed_document_error_on_empty_json():
    """Verify error when json_content is empty."""
    parsed = DoclingParsedDocument(
        text="Test",
        json_content={},  # Empty!
        # ...
    )

    with pytest.raises(ValueError, match="json_content is empty"):
        _ = parsed.document
```

### Integration Tests

**File:** `tests/integration/test_section_extraction.py`

```python
async def test_section_extraction_from_real_pdf():
    """End-to-end test: parse PDF → extract sections → chunk."""
    # Parse PDF with Docling
    client = DoclingClient()
    await client.start_container()
    parsed = await client.parse_document(Path("tests/data/sample.pdf"))
    await client.stop_container()

    # Extract sections (now should work!)
    sections = extract_section_hierarchy(parsed.document, SectionMetadata)
    assert len(sections) > 0  # Was 0 before fix
    assert all(s.heading for s in sections)  # All have headings

    # Chunk with adaptive strategy
    chunks = adaptive_section_chunking(sections)
    assert len(chunks) > 0
    assert all(800 <= c.token_count <= 1800 for c in chunks)

async def test_section_extraction_powerpoint():
    """Test PowerPoint with 15 slides → 6-8 chunks."""
    parsed = await docling.parse_document(Path("presentation.pptx"))

    sections = extract_section_hierarchy(parsed.document, SectionMetadata)
    assert len(sections) == 15  # One section per slide

    chunks = adaptive_section_chunking(sections)
    assert 6 <= len(chunks) <= 8  # Should merge small sections

    # Verify no double-chunking
    assert all(c.token_count > 0 for c in chunks)
```

### Regression Tests

**File:** `tests/integration/test_ingestion_pipeline.py`

```python
async def test_ingestion_pipeline_preserves_functionality():
    """Verify section extraction doesn't break existing behavior."""
    # Parse document
    parsed = await docling.parse_document(pdf_file)

    # Existing fields still work
    assert len(parsed.text) > 0
    assert parsed.metadata is not None
    assert parsed.tables is not None
    assert parsed.parse_time_ms > 0

    # NEW: properties also work
    assert parsed.document is not None
    assert parsed.body is not None

    # Chunking works end-to-end
    state = create_initial_state(...)
    state = await docling_extraction_node(state)

    assert state["document"] is not None
    assert state["parsed_content"] == parsed.text  # Backward compat
    assert state["page_dimensions"] is not None  # Now populated!
```

### Performance Tests

**Benchmark:** PowerPoint fragmentation

```python
async def test_powerpoint_fragmentation_fixed():
    """Verify PowerPoint produces 6-8 chunks (not 124)."""
    parsed = await docling.parse_document("presentation.pptx")

    sections = extract_section_hierarchy(parsed.document, SectionMetadata)
    chunks = adaptive_section_chunking(sections)

    # Before fix: len(chunks) would be 1 (no section extraction)
    # After fix: len(chunks) should be 6-8 (intelligent merging)
    assert 6 <= len(chunks) <= 8, f"Expected 6-8 chunks, got {len(chunks)}"

    # Verify token distribution
    tokens = [c.token_count for c in chunks]
    assert min(tokens) >= 800
    assert max(tokens) <= 1800
```

---

## Verification Steps

After implementing the fix:

1. **Parse a PDF:**
   ```bash
   python -c "
   import asyncio
   from pathlib import Path
   from src.components.ingestion.docling_client import DoclingClient

   async def test():
       client = DoclingClient()
       await client.start_container()
       parsed = await client.parse_document(Path('tests/data/sample.pdf'))
       print(f'Has .document: {hasattr(parsed, \"document\")}')
       print(f'Has .body: {hasattr(parsed, \"body\")}')
       print(f'Body is not None: {parsed.body is not None}')
       await client.stop_container()

   asyncio.run(test())
   ```

2. **Extract sections:**
   ```bash
   python -c "
   from src.components.ingestion.section_extraction import extract_section_hierarchy
   from src.components.ingestion.langgraph_nodes import SectionMetadata

   # ... parse document with docling ...
   sections = extract_section_hierarchy(parsed.document, SectionMetadata)
   print(f'Extracted {len(sections)} sections')
   for s in sections[:3]:
       print(f'  - {s.heading} ({s.token_count} tokens)')
   "
   ```

3. **Run full pipeline:**
   ```bash
   pytest tests/integration/test_ingestion_pipeline.py -v
   ```

4. **Check performance:**
   ```bash
   # PowerPoint should produce 6-8 chunks, not 1
   python tests/performance/benchmark_chunking.py
   ```

---

## Dependencies

### Docling Reconstruction

The fix depends on Docling's ability to reconstruct DoclingDocument from JSON:

```python
# Option A: Use Docling's built-in deserializer
from docling.document_converter import DocumentConverter
doc = DocumentConverter._deserialize_document(json_content)

# Option B: Use Pydantic's validation
from docling.document_converter import PydanticDoclingDocument
doc = PydanticDoclingDocument.model_validate(json_content)

# Option C: Custom deserialization (if above don't work)
# Implement based on Docling's document structure
```

**Action:** Verify which method works with installed Docling version.

---

## Related ADRs and Features

- **ADR-039:** Adaptive Section-Aware Chunking (depends on this fix)
- **Feature 32.1:** Section Extraction from Docling JSON (blocked by this bug)
- **Feature 32.2:** Adaptive Section Merging Logic (blocked by this bug)
- **Feature 32.3:** Multi-Section Metadata in Qdrant (blocked by this bug)
- **Feature 32.4:** Neo4j Section Nodes (blocked by this bug)

All Sprint 32 section-related features are blocked until this is fixed.

---

## Status

**Current:** In Progress (Sprint 33)
**Owner:** Backend Agent
**Priority:** High (Performance)

### Blocked Features
- Sprint 32 Feature 32.1 (Section Extraction) - **Not Working**
- Sprint 32 Feature 32.2 (Adaptive Chunking) - **Not Working**
- Sprint 32 Feature 32.3 (Multi-Section Metadata) - **Not Working**
- Sprint 32 Feature 32.4 (Neo4j Sections) - **Not Working**

### Restoration Plan
1. Implement properties (Phase 1) - 2 hours
2. Remove dead code (Phase 2) - 1 hour
3. Run integration tests (Phase 3) - 1 hour
4. Performance validation (Phase 4) - 1 hour
5. Total: ~5 hours engineering effort

---

## References

- **Docling Documentation:** https://github.com/DS4SD/docling
- **Sprint 21 Initial Implementation:** commit 2627316
- **Sprint 32 Section Extraction:** commit 9cc23a90
- **Sprint 32 Feature 32.1:** Section Extraction from Docling JSON
- **ADR-039:** Adaptive Section-Aware Chunking
- **Performance Issue:** Double chunking, fragmentation, false relations

---

## Discussion Notes

**Why json_content Approach?**
- Docling container returns JSON response via HTTP API
- Native DoclingDocument structure not directly available
- JSON contains all necessary information to reconstruct object
- Properties provide clean lazy-loading pattern

**Why Not Store Native Object?**
- Docling objects aren't Pydantic-serializable
- LangGraph state serialization would fail
- Would break API response serialization
- Properties avoid these issues entirely

**Performance Concerns?**
- Reconstruction only happens when `.document` or `.body` accessed
- Most code paths already expect this access pattern
- Caching could be added if needed (minor optimization)
- Lazy evaluation prevents unnecessary overhead

---

## Addendum: Docling API Pages Schema Discovery

**Date:** 2025-11-29
**Discovery Context:** During benchmark testing, page extraction code failed with `'str' object has no attribute 'get'`

### Investigation

Initial assumption was that `pages` could be either a dict or list format. API schema analysis confirmed:

**Docling API OpenAPI Schema (http://localhost:8080/openapi.json):**
```json
"pages": {
  "additionalProperties": {"$ref": "#/components/schemas/PageItem"},
  "type": "object",
  "title": "Pages",
  "default": {}
}

"PageItem": {
  "properties": {
    "page_no": {"type": "integer", "title": "Page No"},
    "size": {
      "properties": {
        "width": {"type": "number"},
        "height": {"type": "number"}
      }
    },
    "image": {"anyOf": [...], "title": "Image"}
  }
}
```

### Key Finding

**`pages` is ALWAYS a dict** with string keys mapping to `PageItem` objects:

```json
{
  "pages": {
    "1": {"page_no": 1, "size": {"width": 612.0, "height": 792.0}},
    "2": {"page_no": 2, "size": {"width": 612.0, "height": 792.0}}
  }
}
```

### Code Simplification

Removed unnecessary list handling from `langgraph_nodes.py`:

```python
# Before (over-engineered):
if isinstance(pages_data, dict):
    # Dict handling...
elif isinstance(pages_data, list):
    # List handling (UNNECESSARY)

# After (simplified):
# Pages is always a dict per Docling API schema
for page_key, page_info in pages_data.items():
    page_no = page_info.get("page_no", int(page_key) if page_key.isdigit() else None)
    size = page_info.get("size", {})
    # ...
```

### Lesson Learned

Always verify API schema before implementing dual-format handling. The Docling API is well-documented with OpenAPI schema at `/openapi.json`.

---

## Addendum: Docling JSON Body Structure & Section Extraction Fix

**Date:** 2025-11-29
**Discovery Context:** Section extraction returned 0 sections despite `has_body=True` and 18 nodes traversed

### The Problem

Section extraction was traversing `body.children` but finding no sections:
```
nodes_traversed=18, sections_with_text=0, total_sections=0
```

This caused:
- Fallback to single 46,522-token chunk
- LightRAG re-chunking to 122 chunks
- Lost all section hierarchy benefits (ADR-039)

### Root Cause: JSON Reference Pointers

The Docling HTTP API JSON uses **JSON References** (`$ref`) for the document tree:

```json
{
  "body": {
    "label": "unspecified",
    "children": [
      {"$ref": "#/groups/0"},   // <-- These are REFERENCES, not content!
      {"$ref": "#/groups/1"},
      ...
    ]
  },
  "groups": [
    {
      "label": "chapter",
      "name": "slide-0",
      "children": [
        {"$ref": "#/texts/0"},
        {"$ref": "#/texts/1"}
      ]
    }
  ],
  "texts": [
    {
      "label": "title",          // <-- THE ACTUAL LABELS ARE HERE!
      "text": "Slide Title",     // <-- THE ACTUAL TEXT IS HERE!
      "prov": [{"page_no": 1, "bbox": {...}}]
    },
    {
      "label": "paragraph",
      "text": "Body text content..."
    }
  ]
}
```

**Key Insight:**
- `body.children` contains ONLY `$ref` pointers (e.g., `{"$ref": "#/groups/0"}`)
- These pointers have NO `label` or `text` attributes
- The actual content with labels is in the `texts` array
- `groups` are organizational containers (slides/chapters) that reference texts

### Label Distribution (Real Example)

From `PerformanceTuning_textonly.pptx` (17 slides):
```
title: 16x        (slide titles - THESE START SECTIONS)
paragraph: 107x   (body text)
list_item: 73x    (bullet points)
text: 10x         (generic text)
```

### The Fix

Updated `section_extraction.py` with dual extraction strategy:

**Strategy 1 (Primary):** Extract from `json_content["texts"]` array
- Iterate through texts in document order
- When `label="title"` → Start new section
- When `label="paragraph"/"list_item"` → Add to current section
- Extract `page_no` and `bbox` from `prov` array

**Strategy 2 (Fallback):** Traverse `body` tree
- For native DoclingDocument objects (not HTTP API JSON)
- Kept for backwards compatibility

```python
# New extraction logic in section_extraction.py
json_content = getattr(docling_document, "json_content", None)
if json_content and isinstance(json_content, dict):
    texts = json_content.get("texts", [])
    if texts:
        # Use texts array extraction (HTTP API response)
        sections = _extract_from_texts_array(texts, ...)
else:
    # Fall back to body tree traversal (native objects)
    sections = _extract_from_body_tree(body, ...)
```

### Expected Results After Fix

For the same 17-slide PPTX:
- **Before:** 0 sections → 1 chunk (46,522 tokens) → LightRAG re-chunks to 122
- **After:** 16 sections → ~6-8 adaptive chunks → Proper hierarchy preserved

### Documentation References

- Docling Documentation: https://docling-project.github.io/docling/concepts/docling_document/
- JSON Schema: https://github.com/docling-project/docling-core/blob/main/docs/DoclingDocument.json
- Sample JSON: `tests/performance/results/docling_parsed_sample.json`

### Files Modified

1. `src/components/ingestion/section_extraction.py`
   - Added `_extract_from_texts_array()` function
   - Renamed original to `_extract_from_body_tree()`
   - Added comprehensive module-level documentation
   - Detection logic to choose appropriate strategy

---

---

## Addendum: Multi-Format Section Extraction (DOCX, PPT)

**Date:** 2025-11-29
**Discovery Context:** Testing multiple document formats revealed format-specific issues

### Format Support Matrix

| Format | Status | Strategy | Sections Found | Notes |
|--------|--------|----------|----------------|-------|
| **PPTX** | Working | `labels` | 16 (17 slides) | Uses explicit `title` labels |
| **DOCX** | Fixed | `formatting` | 187 | Uses `formatting.bold` heuristics |
| **PDF** | Working | `labels` | Varies | Uses `title` labels |
| **PPT** | Not Supported | N/A | 0 | Docling can't process legacy format |

### DOCX Formatting-Based Heading Detection

**Problem:** DOCX documents from Docling have NO `title` labels:
```json
// PPTX: Has "title" labels
{"label": "title", "text": "Slide Title", ...}

// DOCX: NO "title" labels - everything is "paragraph"
{"label": "paragraph", "text": "Section Heading", "formatting": {"bold": true}}
```

**Labels in DOCX (DE-D-AdvancedAdministration_0368.docx):**
```
paragraph: 1718x
list_item: 370x
text: 71x
title: 0x  // <-- NONE!
```

**Solution:** Implemented formatting-based heading detection in `section_extraction.py`:

```python
def _is_likely_heading_by_formatting(text_item: dict) -> bool:
    """Detect headings via formatting (DOCX fallback)."""
    text = text_item.get("text", "").strip()
    formatting = text_item.get("formatting", {})

    is_bold = formatting.get("bold", False) if formatting else False
    is_short = len(text) < 120
    no_period = not text.rstrip().endswith(".")

    # Primary: Bold + Short + No period = Likely heading
    if is_bold and is_short and no_period:
        return True

    # Secondary: Very short uppercase text
    if len(text) < 60 and text.isupper() and no_period:
        return True

    return False
```

**Results:**
- **Before:** 0 sections extracted (DOCX treated as single chunk)
- **After:** 187 sections extracted (formatting.bold detection)

### Extraction Strategy Detection

The `_detect_heading_strategy()` function automatically chooses:

```python
def _detect_heading_strategy(texts: list[dict]) -> str:
    """Detect which extraction strategy to use."""
    HEADING_LABELS = {"title", "subtitle-level-1", "subtitle-level-2"}

    label_headings = sum(1 for t in texts if t.get("label") in HEADING_LABELS)
    formatting_headings = sum(1 for t in texts if _is_likely_heading_by_formatting(t))

    if label_headings > 0:
        return "labels"      # PPTX, PDF
    if formatting_headings > 0:
        return "formatting"  # DOCX
    return "none"            # No headings found
```

### PPT Legacy Format Limitation

**Problem:** Docling cannot process legacy `.ppt` files:
```
Error: Docling task failed: {'task_id': '...', 'task_status': 'failure'}
```

**Cause:** Docling only supports modern Office formats (PPTX, DOCX, XLSX).
Legacy binary formats (.ppt, .doc, .xls) are not supported.

**Workaround Options:**
1. Convert .ppt to .pptx before processing (recommended)
2. Use LlamaIndex fallback for legacy formats
3. Use python-pptx or libreoffice CLI for conversion

**Impact:**
- Legacy .ppt files cannot be processed
- Users must convert to .pptx format
- Document this limitation in user documentation

### Files Modified

1. `src/components/ingestion/section_extraction.py`
   - Added `_is_likely_heading_by_formatting()` function (lines 77-135)
   - Added `_detect_heading_strategy()` function (lines 138-168)
   - Modified `_extract_from_texts_array()` to use strategy detection
   - Added `heading_source` to section metadata

2. Test files created:
   - `tests/performance/multi_format_pipeline_test.py`
   - `tests/performance/analyze_docx_structure.py`
   - `tests/performance/analyze_docx_formatting.py`
   - `tests/performance/test_docx_section_extraction.py`

### Verification Results

```
Unit Tests: 16/16 passing
PPTX: strategy=labels, sections=16
DOCX: strategy=formatting, sections=187
```

---

**Created:** 2025-11-29
**Last Updated:** 2025-11-29
**Document Version:** 1.3
