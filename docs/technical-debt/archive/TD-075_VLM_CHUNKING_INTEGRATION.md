# TD-075: VLM Image Descriptions Not Integrated into Chunks

**Created:** 2025-12-24
**Priority:** P0 (Critical - Feature 62.3 Non-Functional)
**Effort:** 8 SP
**Sprint:** 64

## Problem Statement

VLM (Vision Language Model) successfully generates image descriptions during ingestion, but **these descriptions are never integrated into the final chunks** stored in Qdrant. This makes VLM-generated descriptions completely unsearchable, rendering Feature 62.3 (VLM Image Integration) non-functional.

## Evidence

### Test: PDF Indexing with 9 Images

**File:** `data/sample_documents/small_test.pdf` (722.7 KB, 5 pages)

**Expected Flow:**
1. ✅ Docling parses PDF → Extracts 9 images as base64 in markdown
2. ✅ VLM processes images → Generates 1205-1291 char descriptions (2 of 9 successful)
3. ✅ VLM descriptions stored in `DoclingDocument.pictures[].text` (line 244 in `image_enrichment.py`)
4. ❌ **FAIL:** Adaptive chunking ignores picture descriptions
5. ❌ **FAIL:** Final chunks have `chunks_with_images=0`, `total_image_annotations=0`

### Logs Confirming Bug

```
09:05:23 chunking_complete
  chunks_with_images=0
  total_image_annotations=0

09:05:27 embedding_complete
  points_with_images=0

09:06:20 graph_extraction_complete
  chunks_with_images=0
```

### Qdrant Verification

```bash
curl -X POST http://localhost:6333/collections/documents_v1/points/scroll \
  -d '{"limit": 50, "filter": {"must": [{"key": "document_id", "match": {"value": "79f05c8e3acb6b32"}}]}}' \
  | jq '.result.points[].payload.image_annotations'
# Result: [] (empty)
```

## Root Cause Analysis

### File: `src/components/ingestion/nodes/adaptive_chunking.py`

**Lines 482-484:**
```python
# Map VLM metadata to chunks (currently unused as section-aware chunking doesn't have picture refs)
# vlm_metadata = state.get("vlm_metadata", [])
# Note: VLM metadata mapping can be added here when needed
```

**Problem:** The code explicitly states VLM metadata mapping is **"currently unused"** and **commented out**.

### Why This Happens

1. **VLM Enrichment (Sprint 62)** inserts descriptions into `DoclingDocument.pictures[].text`
2. **Section Extraction (Sprint 62)** uses the **new `texts` array approach** instead of parsing markdown
3. **Missing Bridge:** There's no code to:
   - Extract descriptions from `DoclingDocument.pictures[]`
   - Match pictures to sections via BBox coordinates
   - Append descriptions to section text

### Image Filter is Working (Not the Issue)

**File:** `src/components/ingestion/image_processor.py:176-224`

Image filtering correctly skips:
- Small images (< 200px)
- Logos/icons (aspect ratio < 0.2 or > 5.0)
- Single-color placeholders (< 16 unique colors)

**This is NOT causing the bug** - VLM descriptions ARE generated, just not integrated into chunks.

## Impact Assessment

### Feature Functionality
- **Feature 62.3 (VLM Image Integration):** 0% functional
- **Image Content Searchability:** 0% - users cannot find documents by image content
- **VLM Cost/Time Waste:** 75-95s per image processing with zero value

### Business Impact
- **Silent Failure:** Pipeline completes successfully but feature doesn't work
- **User Experience:** Queries like "show me diagrams of architecture" return nothing
- **Resource Waste:** VLM processing costs (local: time, cloud: $$$) with no benefit

## VLM Performance Issues (Secondary)

### Issue 1: Only 2/9 Images Processed

**Logs:**
```
09:04:59 Local Ollama VLM failed, falling back to cloud
  error_type=ReadTimeout
09:04:59 VLM description failed on all backends
  error=DashScope API key not configured
```

**Causes:**
1. **Qwen3-VL 32B too slow:** 75-95 seconds per image → timeouts
2. **No cloud fallback:** DashScope API key missing
3. **Success rate:** 22% (2/9)

### Issue 2: Model Selection

**Current:** `qwen3-vl:32b` (slow but accurate)
**Alternative:** `qwen3-vl:4b` (faster, slightly less accurate)

## Proposed Solution

### Phase 1: VLM-to-Chunk Integration (Sprint 64 - 8 SP)

**File:** `src/components/ingestion/nodes/adaptive_chunking.py`

```python
def _integrate_vlm_descriptions(
    sections: list[Section],
    vlm_metadata: list[dict],
    page_dimensions: dict,
) -> list[Section]:
    """Integrate VLM descriptions into sections based on BBox overlap.

    Algorithm:
    1. For each VLM description with BBox:
       a. Calculate overlap with each section's BBox
       b. If overlap > 50%, append description to section text
       c. Store image annotation in section metadata
    2. For VLM descriptions without BBox:
       a. Append to the first section (fallback)
    """
    for vlm_item in vlm_metadata:
        bbox = vlm_item.get("bbox_full")
        description = vlm_item["description"]

        if bbox:
            # Find best matching section by BBox overlap
            best_section = find_section_by_bbox_overlap(sections, bbox, threshold=0.5)
            if best_section:
                best_section.text += f"\n\n[Image Description]: {description}"
                best_section.image_annotations.append({
                    "picture_ref": vlm_item["picture_ref"],
                    "bbox": bbox,
                })
        else:
            # Fallback: append to first section
            sections[0].text += f"\n\n[Image Description]: {description}"

    return sections
```

**Integration Point:**
- Call after section extraction (line ~485)
- Before adaptive merging

### Phase 2: VLM Performance Optimization (Sprint 64 - 3 SP)

1. **Switch to Qwen3-VL 4B:**
   - Expected speed: 15-30s per image (vs 75-95s)
   - Accuracy trade-off: ~5-10% (acceptable for most use cases)

2. **Configure DashScope Fallback:**
   - Set `ALIBABA_CLOUD_API_KEY` environment variable
   - Fallback triggers on local timeout (>60s)

3. **Increase Timeout Settings:**
   - Current: implicit httpx default (~30s)
   - New: 120s for VLM requests

## Testing Strategy

### Test 1: VLM Description Integration

```python
def test_vlm_descriptions_in_chunks():
    # Index PDF with images
    result = index_document("small_test.pdf")

    # Query Qdrant for chunks with images
    points = qdrant.scroll(
        collection="documents_v1",
        filter={"document_id": result.document_id},
    )

    # Assertions
    chunks_with_images = [p for p in points if p.payload.get("image_annotations")]
    assert len(chunks_with_images) > 0, "No chunks contain image annotations"

    # Check VLM description is in chunk text
    for chunk in chunks_with_images:
        assert "[Image Description]:" in chunk.payload.content
        assert len(chunk.payload.image_annotations) > 0
```

### Test 2: Image Content Search

```python
def test_image_content_searchable():
    # Index PDF with images
    index_document("small_test.pdf")

    # Search for content that only appears in VLM descriptions
    results = hybrid_search("OMNITRACKER logo blue white")

    assert len(results) > 0, "VLM-described image not found"
    assert "OMNITRACKER" in results[0].content
```

## Acceptance Criteria

1. ✅ VLM descriptions appear in chunk `content` field
2. ✅ Chunks have `image_annotations` array with BBox data
3. ✅ `chunks_with_images` > 0 in chunking logs
4. ✅ `points_with_images` > 0 in embedding logs
5. ✅ Image content is searchable via hybrid search
6. ✅ E2E test: PDF with images → query returns VLM-described content

## Dependencies

- **Upstream:** Feature 62.3 (VLM Image Integration) implementation
- **Downstream:** Feature 62.4 (Image-Aware Retrieval) - currently blocked

## References

- **Feature:** Feature 62.3 (VLM Image Integration with Sections)
- **Files:**
  - `src/components/ingestion/nodes/adaptive_chunking.py:482-484` (root cause)
  - `src/components/ingestion/nodes/image_enrichment.py:240-245` (VLM insertion)
  - `src/components/ingestion/image_processor.py:176-224` (image filtering - working)
- **ADR:** ADR-039 (Adaptive Section-Aware Chunking)
- **Test Logs:** `/tmp/docling_live.log` (lines 14-15 show VLM errors)

## Estimated Effort

- **Investigation:** 1 SP (completed)
- **Implementation:** 5 SP (BBox matching, text integration, metadata)
- **Testing:** 2 SP (unit tests, E2E tests, verification)
- **Total:** 8 SP

---

## ✅ RESOLUTION

**Status:** RESOLVED
**Resolution Sprint:** Sprint 64+ (Feature 62.3)
**Resolution Date:** 2026-01-10 (Sprint 84 Technical Debt Review)
**Resolved By:** Code Analysis (feature was implemented but not archived)

**Implementation Evidence:**
- `src/components/ingestion/nodes/adaptive_chunking.py:82-204` - `_integrate_vlm_descriptions()` function
- `src/components/ingestion/nodes/adaptive_chunking.py:769-771` - VLM integration active
- `src/components/ingestion/nodes/adaptive_chunking.py:340-341, 377-378, 473-474` - image_annotations copied to chunks

**Verification:** Grep shows VLM metadata integration fully implemented with BBox matching and section-level image annotations.

**Root Cause of Documentation Drift:** Feature implemented in Sprint 64 but TD not archived due to missing TD-archiving automation (see CLAUDE.md Sprint-Abschluss Checkliste I).
