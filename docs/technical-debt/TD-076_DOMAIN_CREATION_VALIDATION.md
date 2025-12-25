# TD-076: Domain Creation UX & Validation Issues

**Created:** 2025-12-24
**Priority:** P1 (High - UX/Data Integrity)
**Effort:** 5 SP
**Sprint:** 64

## Problem Statement

The Domain Training feature (Feature 60.1) has **6 critical UX and validation bugs** that create a poor user experience and allow invalid states in the database. DSPy training appears to run successfully but is actually a non-functional mock.

## Discovered Bugs

### Bug #1: No Frontend Validation for Minimum Samples

**Severity:** P1 (High)
**Impact:** User submits form → backend rejects with 422 → user confused

**Current Behavior:**
- UI shows "Dataset Preview (3 samples)" with no warnings
- "Start Training" button is enabled
- User clicks → Backend returns 422 error
- Error message: `"List should have at least 5 items after validation, not 3"`

**Root Cause:**
- Backend validates `min_items=5` in Pydantic model
- Frontend has no matching validation

**Expected Behavior:**
- UI shows warning: "⚠️ Minimum 5 samples required (currently: 3)"
- "Start Training" button disabled until `samples.length >= 5`
- Helpful message: "Add 2 more samples to meet the minimum requirement"

**File:** `frontend/src/pages/admin/DomainTrainingPage.tsx`

---

### Bug #2: Domain Persists Before Successful Training

**Severity:** P0 (Critical - Data Integrity)
**Impact:** Database polluted with incomplete/failed domains

**Current Behavior:**
1. User creates domain (Step 1)
2. Uploads dataset (Step 2)
3. Clicks "Start Training" → Validation fails (422)
4. **Domain already exists in Neo4j with status="pending"**
5. User stuck with orphaned domain

**Evidence:**
```bash
# After failed training
curl http://localhost:7474 | grep test_vlm_domain
# Result: Domain exists with status="pending"
```

**Root Cause:**
- Domain is created in Step 1 (`POST /admin/domains`)
- Training validation happens in Step 3
- No transactional rollback on validation failure

**Expected Behavior:**
- Domain should only be persisted **after successful training completion**
- Or: Domain marked as "draft" until training completes
- Failed training should delete incomplete domain

**File:** `src/api/v1/domain_training.py` (create domain endpoint)

---

### Bug #3: Error Message Not Cleared After New Upload

**Severity:** P2 (Medium - UX)
**Impact:** User sees stale error message, thinks new upload also failed

**Current Behavior:**
1. Upload 3 samples → Error: "List should have at least 5 items"
2. Upload 6 samples → Error message **still visible** from previous attempt
3. User confused whether new upload succeeded

**Root Cause:**
- Error state not cleared when new file is uploaded
- Frontend doesn't reset error on file selection

**Expected Behavior:**
- Clear error message when user uploads new file
- Or: Show success message "6 samples loaded (requirement met ✓)"

**File:** `frontend/src/pages/admin/DomainTrainingPage.tsx`

---

### Bug #4: F1-Scores Show 0.000 During Training, Then Jump to 0.850

**Severity:** P1 (High - Indicates Mock/Fake Training)
**Impact:** F1 scores appear fabricated, not from real DSPy optimization

**Current Behavior:**
```
08:52:07.326  entity_optimization complete - F1: 0.000
08:52:07.326  relation_optimization complete - F1: 0.000
...
08:52:07.327  Final metrics validated - Entity F1: 0.850, Relation F1: 0.800
```

**Evidence:**
- During optimization phases: F1 = 0.000
- After validation: F1 suddenly becomes 0.850/0.800
- No gradual improvement shown

**Root Cause Analysis:**
- F1 scores are **hardcoded or mocked**
- Real DSPy optimization would show:
  - Initial baseline (e.g., 0.45)
  - Incremental improvements (0.50 → 0.65 → 0.78)
  - Final optimized score

**Expected Behavior:**
- Show actual DSPy optimization metrics
- Display iteration-by-iteration improvements
- If mock: clearly label as "Simulated Training" for demo purposes

**File:** `src/components/domain_training/dspy_trainer.py`

---

### Bug #5: Training Completes in 35ms (Physically Impossible)

**Severity:** P0 (Critical - Training is Fake)
**Impact:** DSPy training doesn't actually run

**Current Behavior:**
```
08:52:07.323  Training started
08:52:07.358  Training completed (35ms)
```

**Evidence:**
- Timestamps show **35 milliseconds** total duration
- With 6 training samples + LLM calls, real DSPy would take **10-30 seconds minimum**
- Training completes ~1000x faster than physically possible

**Root Cause:**
- DSPy training is a **mock/stub implementation**
- No actual LLM optimization happening
- SSE events are pre-generated

**Backend Logs Confirm:**
```bash
# grep for "dspy\|optimization\|llm.*call" in logs
# Result: ZERO logs about actual training
# Only: status_retrieved, training_log_retrieved (polling)
```

**Expected Behavior:**
- Real DSPy optimization with LLM calls
- Duration: 10-30 seconds for 6 samples
- Progress updates showing actual optimization steps

**File:** `src/components/domain_training/dspy_trainer.py`

---

### Bug #6: Training Claims "Saved to Neo4j" But Domain Doesn't Exist

**Severity:** P0 (Critical - Data Loss)
**Impact:** Training appears successful but no data is persisted

**Current Behavior:**
- UI shows: "Saving optimized prompts and metrics to Neo4j..."
- Status: "completed" (green checkmark)
- Final message: "Training completed successfully - Entity F1: 0.850, Relation F1: 0.800"

**Neo4j Verification:**
```bash
curl -X POST http://localhost:7474/db/neo4j/tx/commit \
  -d '{"statements":[{"statement":"MATCH (d:Domain {name: \"test_vlm_domain\"}) RETURN d"}]}'
# Result: null  (domain does NOT exist!)
```

**Root Cause:**
- Training completes with mock data
- No actual persistence to Neo4j happens
- Or: Persistence fails silently

**Expected Behavior:**
- Domain with training metrics persisted to Neo4j
- Verify persistence before showing "completed"
- If persistence fails, show error and rollback

**File:** `src/components/domain_training/domain_repository.py`

---

## Impact Summary

| Bug | Severity | User Impact | Data Impact |
|-----|----------|-------------|-------------|
| #1: No min sample validation | P1 | Confusing error messages | None |
| #2: Domain persists on failure | P0 | Orphaned domains | Database pollution |
| #3: Stale error messages | P2 | User confusion | None |
| #4: Fake F1 scores | P1 | Misleading metrics | Trust issues |
| #5: 35ms training | P0 | **Feature non-functional** | Complete failure |
| #6: No Neo4j persistence | P0 | **Data loss** | Complete failure |

**Overall Assessment:** Domain Training feature is **0% functional**. It's a UI-only demo with no backend implementation.

## Proposed Solutions

### Priority 1: Make DSPy Training Real (Bug #5, #6)

**Option A: Implement Real DSPy Training (13 SP)**
- Integrate actual DSPy library
- Implement entity/relation optimization
- Persist results to Neo4j
- **Effort:** High (new feature implementation)

**Option B: Remove Mock UI Until Ready (2 SP)**
- Hide Domain Training page
- Show "Coming Soon" placeholder
- **Effort:** Low (honest about feature status)

**Recommendation:** Option B for Sprint 64, Option A for Sprint 65

### Priority 2: Frontend Validation (Bug #1, #3)

**Implementation (2 SP):**
```typescript
// frontend/src/pages/admin/DomainTrainingPage.tsx
const MIN_SAMPLES = 5;

// Add validation
const canStartTraining = samples.length >= MIN_SAMPLES;

// Clear errors on new upload
const handleFileUpload = (file: File) => {
  setError(null);  // Clear previous errors
  parseSamples(file);
};

// Show helpful message
{samples.length < MIN_SAMPLES && (
  <Alert variant="warning">
    ⚠️ Minimum {MIN_SAMPLES} samples required.
    Currently: {samples.length} ({MIN_SAMPLES - samples.length} more needed)
  </Alert>
)}
```

### Priority 3: Transactional Domain Creation (Bug #2)

**Implementation (3 SP):**
```python
# src/api/v1/domain_training.py
@router.post("/{domain_name}/train")
async def train_domain(domain_name: str, request: TrainRequest):
    # Start transaction
    async with neo4j_session.begin_transaction() as tx:
        try:
            # 1. Validate samples
            if len(request.samples) < 5:
                raise ValidationError("Minimum 5 samples required")

            # 2. Run DSPy training
            results = await dspy_trainer.train(request.samples)

            # 3. Persist domain with results
            await domain_repo.save_domain(domain_name, results, tx)

            # 4. Commit transaction
            await tx.commit()

        except Exception as e:
            # Rollback on any failure
            await tx.rollback()
            raise
```

## Testing Strategy

### Test 1: Frontend Validation
```typescript
test("should disable Start Training with <5 samples", () => {
  render(<DomainTrainingPage />);
  uploadFile("3_samples.jsonl");

  expect(screen.getByText("Start Training")).toBeDisabled();
  expect(screen.getByText(/Minimum 5 samples/)).toBeInTheDocument();
});
```

### Test 2: Transactional Rollback
```python
def test_domain_not_persisted_on_training_failure():
    # Create domain with invalid training data
    response = client.post("/admin/domains/test/train", json={
        "samples": [{"text": "invalid"}]  # Missing entities/relations
    })

    assert response.status_code == 422

    # Verify domain doesn't exist in Neo4j
    domain = domain_repo.get_domain("test")
    assert domain is None, "Domain should not exist after failed training"
```

### Test 3: Error Message Clearing
```typescript
test("should clear error on new file upload", () => {
  render(<DomainTrainingPage />);

  // Upload invalid file
  uploadFile("3_samples.jsonl");
  expect(screen.getByText(/List should have at least 5/)).toBeInTheDocument();

  // Upload valid file
  uploadFile("6_samples.jsonl");
  expect(screen.queryByText(/List should have at least 5/)).not.toBeInTheDocument();
});
```

## Acceptance Criteria

### Must Have (Sprint 64)
1. ✅ Frontend validates minimum 5 samples before enabling "Start Training"
2. ✅ Error messages cleared when new file uploaded
3. ✅ Domain only persisted after successful training (transactional)
4. ✅ "Feature Under Development" banner if DSPy not implemented

### Should Have (Sprint 65)
5. ✅ Real DSPy training with actual LLM optimization
6. ✅ F1 scores reflect real training metrics
7. ✅ Domain persisted to Neo4j with training results
8. ✅ Training duration 10-30s (realistic for 6 samples)

## Dependencies

- **Blocks:** Production use of Domain Training feature
- **Requires:** DSPy library integration (for real implementation)

## References

- **Feature:** Feature 60.1 (DSPy Domain Training)
- **Test Evidence:**
  - Frontend validation: HTTP 422 error in browser console
  - Training mock: Logs show 35ms duration, no DSPy calls
  - No persistence: Neo4j query returns `null` for trained domain
- **Files:**
  - Frontend: `frontend/src/pages/admin/DomainTrainingPage.tsx`
  - Backend: `src/api/v1/domain_training.py`
  - Training: `src/components/domain_training/dspy_trainer.py`
  - Persistence: `src/components/domain_training/domain_repository.py`

## Estimated Effort

- **Frontend Validation (Bug #1, #3):** 2 SP
- **Transactional Creation (Bug #2):** 3 SP
- **"Under Development" Banner:** 0.5 SP (if DSPy not implemented)
- **Total Sprint 64:** 5 SP (UX fixes only)

**Note:** Real DSPy implementation (Bug #4, #5, #6) is 13 SP and should be Sprint 65.
