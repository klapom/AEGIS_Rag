# Sprint 64: Critical Bugfixes & DSPy Implementation (Combined Sprint 64+65)

**Sprint Duration:** 2 weeks
**Total Story Points:** 26 SP
**Priority:** P0 (Critical - Fix Non-Functional Features)
**Dependencies:** Sprint 62+63 Complete

---

## Executive Summary

Sprint 64 is a **comprehensive bugfix + implementation sprint** addressing two critical issues discovered during E2E testing of Sprint 62+63 features:

1. **VLM Image Descriptions Not Searchable** (TD-075) - Feature 62.3 is 0% functional
2. **Domain Training is a Mock** (TD-076) - Feature 60.1 creates invalid database state

**Scope Change:** Originally Sprint 64 (13 SP) + Sprint 65 (13 SP) → Combined into single 2-week sprint (26 SP)

**Impact:**
- **VLM Integration:** $0 value from 75-95s image processing → descriptions discarded
- **Domain Training:** Database polluted with incomplete domains, fake metrics

**Expected Outcome:**
- VLM descriptions integrated into chunks → searchable via hybrid search
- Domain Training UX fixed → no orphaned domains, clear validation messages
- **Real DSPy implementation** with actual LLM optimization and Neo4j persistence

---

## Feature 64.1: VLM-Chunking Integration Fix (8 SP)

**Priority:** P0 (Critical)
**Technical Debt:** TD-075
**Root Cause:** Adaptive chunking ignores `DoclingDocument.pictures[]` descriptions

### Problem Statement

VLM successfully generates image descriptions and stores them in `DoclingDocument.pictures[].text`, but the new section-aware chunking (Sprint 62) **never extracts these descriptions**. Result: VLM-generated content is completely unsearchable.

**Evidence:**
```
# Logs after indexing PDF with 9 images
chunks_with_images=0
total_image_annotations=0
points_with_images=0 (in Qdrant)
```

### Implementation Tasks

#### Task 64.1.1: VLM-to-Section Mapping Algorithm (3 SP)

**File:** `src/components/ingestion/nodes/adaptive_chunking.py`

**New Function:**
```python
def _integrate_vlm_descriptions(
    sections: list[Section],
    vlm_metadata: list[dict],
    page_dimensions: dict,
) -> list[Section]:
    """Integrate VLM descriptions into sections via BBox matching.

    Algorithm:
    1. For each VLM description with BBox:
       - Calculate IoU (Intersection over Union) with each section
       - If IoU > 0.5, append description to section.text
       - Store image annotation in section metadata
    2. For descriptions without BBox:
       - Append to first section on same page (fallback)
    """
    for vlm_item in vlm_metadata:
        bbox = vlm_item.get("bbox_full", {})
        description = vlm_item["description"]
        page_no = bbox.get("page_context", {}).get("page_no", 0)

        if bbox:
            best_section = find_section_by_bbox_iou(sections, bbox, threshold=0.5)
            if best_section:
                best_section.text += f"\n\n[Image Description]: {description}"
                best_section.image_annotations.append({
                    "picture_ref": vlm_item["picture_ref"],
                    "bbox": bbox,
                })
            else:
                # Fallback: append to first section on page
                page_sections = [s for s in sections if s.page_no == page_no]
                if page_sections:
                    page_sections[0].text += f"\n\n[Image Description]: {description}"
        else:
            # No BBox: append to first section
            sections[0].text += f"\n\n[Image Description]: {description}"

    return sections
```

**BBox IoU Helper:**
```python
def calculate_bbox_iou(bbox1: dict, bbox2: dict) -> float:
    """Calculate Intersection over Union for two BBoxes."""
    # Extract coordinates
    x1_min, y1_min = bbox1["bbox_normalized"]["left"], bbox1["bbox_normalized"]["top"]
    x1_max, y1_max = bbox1["bbox_normalized"]["right"], bbox1["bbox_normalized"]["bottom"]

    x2_min, y2_min = bbox2["left"], bbox2["top"]
    x2_max, y2_max = bbox2["right"], bbox2["bottom"]

    # Calculate intersection
    xi_min = max(x1_min, x2_min)
    yi_min = max(y1_min, y2_min)
    xi_max = min(x1_max, x2_max)
    yi_max = min(y1_max, y2_max)

    if xi_max < xi_min or yi_max < yi_min:
        return 0.0  # No overlap

    intersection = (xi_max - xi_min) * (yi_max - yi_min)

    # Calculate union
    area1 = (x1_max - x1_min) * (y1_max - y1_min)
    area2 = (x2_max - x2_min) * (y2_max - y2_min)
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0
```

**Integration Point (line ~485):**
```python
# After section extraction, before adaptive merging
if vlm_metadata:
    sections = _integrate_vlm_descriptions(sections, vlm_metadata, page_dimensions)
```

#### Task 64.1.2: Update Chunk Metadata Schema (1 SP)

**File:** `src/components/ingestion/nodes/adaptive_chunking.py`

Ensure chunks include:
```python
chunk_dict = {
    "content": merged_text,
    "image_annotations": chunk_image_annotations,  # List[dict] with BBox
    "contains_images": len(chunk_image_annotations) > 0,  # Boolean flag
    # ... existing fields
}
```

#### Task 64.1.3: Unit Tests (2 SP)

**File:** `tests/unit/components/ingestion/test_vlm_chunking.py`

```python
def test_vlm_descriptions_integrated_into_chunks():
    """Test that VLM descriptions appear in chunk text."""
    vlm_metadata = [{
        "description": "The OMNITRACKER logo with blue and white colors",
        "picture_ref": "#/pictures/0",
        "bbox_full": {...},  # BBox matching section_0
    }]

    sections = [Section(text="Header section", page_no=0, bbox={...})]
    result = _integrate_vlm_descriptions(sections, vlm_metadata, {})

    assert "[Image Description]:" in result[0].text
    assert "OMNITRACKER logo" in result[0].text
    assert len(result[0].image_annotations) == 1
```

```python
def test_bbox_iou_calculation():
    """Test BBox IoU matching."""
    bbox1 = {"bbox_normalized": {"left": 0.1, "top": 0.1, "right": 0.5, "bottom": 0.5}}
    bbox2 = {"left": 0.2, "top": 0.2, "right": 0.6, "bottom": 0.6}

    iou = calculate_bbox_iou(bbox1, bbox2)
    assert 0.1 < iou < 0.5  # Partial overlap
```

#### Task 64.1.4: E2E Test (2 SP)

**File:** `tests/e2e/test_vlm_search.py`

```python
@pytest.mark.e2e
def test_vlm_image_content_searchable():
    """Test that VLM-described images are searchable."""
    # Index PDF with images
    response = client.post("/admin/add-documents", json={
        "server_directory": "data/sample_documents",
        "files": ["small_test.pdf"],
    })

    assert response.json()["success_count"] == 1

    # Query for content only in VLM description
    search_response = client.post("/query", json={
        "query": "OMNITRACKER logo blue white colors",
        "retrieval_mode": "hybrid",
    })

    results = search_response.json()["results"]
    assert len(results) > 0, "VLM-described image not found"
    assert "OMNITRACKER" in results[0]["content"]
```

### Acceptance Criteria

1. ✅ VLM descriptions appear in chunk `content` field with `[Image Description]:` prefix
2. ✅ Chunks have `image_annotations` array with BBox and picture_ref
3. ✅ `chunks_with_images` > 0 in chunking completion logs
4. ✅ `points_with_images` > 0 in embedding completion logs
5. ✅ Hybrid search returns chunks containing VLM descriptions
6. ✅ E2E test passes: PDF with images → query matches VLM content

---

## Feature 64.2: Domain Training UX & Validation Fixes (5 SP)

**Priority:** P1 (High)
**Technical Debt:** TD-076
**Scope:** Fix UX issues, defer real DSPy implementation to Sprint 65

### Problem Statement

Domain Training feature has 6 critical bugs:
1. No frontend validation for minimum 5 samples
2. Domain persists before successful training
3. Stale error messages after new upload
4. F1 scores are mocked (0.000 → 0.850 jump)
5. Training completes in 35ms (physically impossible)
6. Domain claims "saved to Neo4j" but doesn't exist

**Decision:** Fix UX issues (#1-3) in Sprint 64, implement real DSPy (#4-6) in Sprint 65.

### Implementation Tasks

#### Task 64.2.1: Frontend Sample Validation (1 SP)

**File:** `frontend/src/pages/admin/DomainTrainingPage.tsx`

```typescript
const MIN_SAMPLES = 5;

// Add validation state
const [samples, setSamples] = useState<TrainingSample[]>([]);
const canStartTraining = samples.length >= MIN_SAMPLES;

// Show validation message
{samples.length > 0 && samples.length < MIN_SAMPLES && (
  <Alert variant="warning" className="mt-4">
    <AlertTriangle className="h-4 w-4" />
    <AlertTitle>Minimum Samples Required</AlertTitle>
    <AlertDescription>
      At least {MIN_SAMPLES} training samples are required.
      Currently: {samples.length} ({MIN_SAMPLES - samples.length} more needed)
    </AlertDescription>
  </Alert>
)}

// Disable button
<Button
  onClick={handleStartTraining}
  disabled={!canStartTraining || isTraining}
>
  Start Training ({samples.length} samples)
</Button>
```

#### Task 64.2.2: Clear Errors on New Upload (0.5 SP)

**File:** `frontend/src/pages/admin/DomainTrainingPage.tsx`

```typescript
const handleFileUpload = async (file: File) => {
  // Clear previous errors
  setError(null);
  setValidationError(null);

  try {
    const parsed = await parseJSONL(file);
    setSamples(parsed);

    // Show success message
    if (parsed.length >= MIN_SAMPLES) {
      setSuccess(`✓ ${parsed.length} samples loaded (requirement met)`);
    }
  } catch (err) {
    setError(err.message);
  }
};
```

#### Task 64.2.3: Transactional Domain Creation (2 SP)

**File:** `src/api/v1/domain_training.py`

```python
@router.post("/{domain_name}/train")
async def train_domain(
    domain_name: str,
    request: TrainRequest,
    domain_repo: DomainRepository = Depends(get_domain_repo),
):
    """Train domain with transactional rollback on failure."""

    # Validate samples before creating domain
    if len(request.samples) < 5:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "VALIDATION_FAILED",
                "message": f"Minimum 5 samples required, got {len(request.samples)}",
            },
        )

    # Start Neo4j transaction
    async with domain_repo.transaction() as tx:
        try:
            # 1. Check if domain already exists (idempotency)
            existing = await domain_repo.get_domain(domain_name, tx)
            if existing and existing.status == "completed":
                raise HTTPException(409, "Domain already trained")

            # 2. Create domain with status="training"
            domain = await domain_repo.create_domain(
                name=domain_name,
                description=request.description,
                status="training",
                tx=tx,
            )

            # 3. Run training (mock for now, real DSPy in Sprint 65)
            training_results = await dspy_trainer.train(request.samples)

            # 4. Update domain with results
            await domain_repo.update_training_results(
                domain_name=domain_name,
                results=training_results,
                status="completed",
                tx=tx,
            )

            # 5. Commit transaction
            await tx.commit()

            return {"status": "completed", "domain": domain_name}

        except Exception as e:
            # Rollback on any failure
            await tx.rollback()
            logger.error("training_failed", domain=domain_name, error=str(e))
            raise
```

#### Task 64.2.4: "Under Development" Banner (0.5 SP)

**File:** `frontend/src/pages/admin/DomainTrainingPage.tsx`

```typescript
{/* Show banner if DSPy not implemented */}
<Alert variant="info" className="mb-6">
  <Info className="h-4 w-4" />
  <AlertTitle>Feature Under Development</AlertTitle>
  <AlertDescription>
    DSPy training is currently a demonstration. Real optimization coming in Sprint 65.
    Metrics shown are simulated for UI testing purposes.
  </AlertDescription>
</Alert>
```

#### Task 64.2.5: Unit & E2E Tests (1 SP)

**Frontend Test:**
```typescript
test("disables Start Training with <5 samples", () => {
  render(<DomainTrainingPage />);
  uploadFile("3_samples.jsonl");

  expect(screen.getByText("Start Training")).toBeDisabled();
  expect(screen.getByText(/Minimum 5 samples/)).toBeInTheDocument();
});
```

**Backend Test:**
```python
def test_domain_not_created_on_validation_failure():
    """Domain should not exist in Neo4j after validation failure."""
    response = client.post("/admin/domains/test/train", json={
        "samples": [{"text": "sample1"}, {"text": "sample2"}],  # Only 2
    })

    assert response.status_code == 422
    domain = domain_repo.get_domain("test")
    assert domain is None
```

### Acceptance Criteria

1. ✅ Frontend validates minimum 5 samples before enabling "Start Training"
2. ✅ Helpful message shows how many more samples needed
3. ✅ Error messages cleared when new file uploaded
4. ✅ Domain only persisted after training starts (transactional)
5. ✅ Failed training rolls back domain creation
6. ✅ "Under Development" banner visible if DSPy mocked
7. ✅ Unit tests cover validation edge cases
8. ✅ E2E test verifies no orphaned domains

---

## Testing Strategy

### Automated Tests

**Unit Tests:**
- VLM-to-chunk integration: BBox matching, text appending
- Domain validation: min samples, transactional rollback
- Error message clearing: state management

**E2E Tests:**
- VLM search: Index PDF with images → query for VLM-described content
- Domain creation: Upload invalid samples → verify no domain created

### Manual Testing

1. **VLM Integration:**
   - Index `small_test.pdf` (9 images)
   - Verify chunking logs: `chunks_with_images=9`
   - Query "OMNITRACKER logo blue white"
   - Confirm results contain VLM descriptions

2. **Domain Validation:**
   - Upload 3 samples → verify warning message
   - Upload 6 samples → verify success message
   - Start training → verify domain persisted only after completion

### Acceptance Testing

- [ ] VLM descriptions searchable via hybrid search
- [ ] Chunking logs show `chunks_with_images > 0`
- [ ] Domain creation validates samples before persisting
- [ ] No orphaned domains in Neo4j after failed training
- [ ] Clear error messages guide users

---

## Dependencies

### Upstream (Required)
- Sprint 62+63 complete (VLM integration, section-aware chunking)

### Downstream (Blocked)
- Feature 62.4 (Image-Aware Retrieval) - currently blocked by TD-075

### Future Work (Sprint 65)
- Real DSPy implementation (13 SP)
- F1 score calculation from actual optimization
- Domain persistence to Neo4j with training artifacts

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| BBox matching fails for rotated images | Low | Medium | Use IoU threshold 0.3 as fallback |
| VLM descriptions too long for chunk limit | Medium | Low | Truncate to 500 chars with "..." |
| Transaction rollback leaves partial state | Low | High | Add cleanup job for orphaned domains |
| DSPy implementation takes >1 sprint | High | Medium | Defer to Sprint 65, show "Under Development" |

---

## Rollout Plan

### Phase 1: Deploy VLM Fix (Day 1-2)
1. Merge VLM-chunking integration PR
2. Run E2E tests on staging
3. Re-index sample documents
4. Verify image search works

### Phase 2: Deploy Domain UX Fixes (Day 3)
1. Deploy frontend validation
2. Deploy transactional backend
3. Add "Under Development" banner
4. Test domain creation flow

### Phase 3: Validation (Day 4-5)
1. Manual testing of both features
2. Performance testing (VLM processing time)
3. Database state verification (no orphans)
4. Documentation updates

---

## Success Metrics

### VLM Integration (Feature 64.1)
- **Image Description Integration:** 100% of VLM descriptions appear in chunks
- **Search Recall:** Image content queries return relevant chunks
- **Processing Efficiency:** 0% waste (descriptions no longer discarded)

### Domain Training UX (Feature 64.2)
- **Validation Coverage:** 100% of invalid inputs blocked at frontend
- **Database Integrity:** 0 orphaned domains after failed training
- **User Confusion:** Error messages clear in 100% of test cases

---

## Timeline

**Sprint Duration:** 5 working days
**Story Points:** 13 SP (team velocity: ~15 SP/sprint)

| Day | Tasks | SP |
|-----|-------|-----|
| Day 1 | VLM-to-section mapping algorithm | 3 |
| Day 2 | VLM metadata schema, unit tests | 3 |
| Day 3 | Frontend validation, error clearing | 1.5 |
| Day 4 | Transactional domain creation | 2 |
| Day 5 | E2E tests, "Under Development" banner | 3.5 |

---

## Documentation Updates

### ADRs
- None (bugfixes don't change architecture)

### User Guides
- Update "Image Search" section: explain VLM-described images are searchable
- Add "Domain Training" disclaimer: feature under development

### Technical Docs
- Update chunking pipeline diagram: show VLM integration step
- Document BBox IoU matching algorithm

---

## References

- **Technical Debt:** TD-075 (VLM Chunking), TD-076 (Domain Creation)
- **Related Features:** Feature 62.3 (VLM Integration), Feature 60.1 (Domain Training)
- **Test Evidence:**
  - VLM bug: `/tmp/docling_live.log` lines 14-15
  - Domain bug: Playwright test screenshots in `.playwright-mcp/`
- **Code Files:**
  - `src/components/ingestion/nodes/adaptive_chunking.py` (VLM fix)
  - `src/api/v1/domain_training.py` (domain validation)
  - `frontend/src/pages/admin/DomainTrainingPage.tsx` (UX fixes)
