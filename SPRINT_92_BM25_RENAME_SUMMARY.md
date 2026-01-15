# Sprint 92: BM25 → Sparse Label Rename Summary

## Overview
Since Sprint 87, the system uses BGE-M3 native sparse vectors (learned lexical weights) instead of traditional BM25. This task updated all UI labels to reflect this change while maintaining backward compatibility.

## Key Principle
**API values unchanged, UI labels updated**
- Backend API still sends/receives `bm25` (for backward compatibility)
- Frontend UI displays it as "Sparse" or "Lexikalisch" (German)
- Internal code handles both `sparse` and `bm25` keys

## Files Changed

### 1. Frontend Type Definitions

#### `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/types/settings.ts`
**Changes:**
- `RETRIEVAL_METHODS` labels updated:
  - `'Hybrid (Vector + BM25)'` → `'Hybrid (Vector + Sparse)'`
  - `'BM25 (Keyword)'` → `'Sparse (Lexikalisch)'`
- Descriptions updated to mention "BGE-M3 learned lexical weights"
- API value remains `'bm25'` (for backend compatibility)

**Impact:** Settings page now shows correct terminology

---

#### `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/types/reasoning.ts`
**Changes:**
- `RetrievalSource` type: Added `'sparse'` as new primary type, kept `'bm25'` for backward compatibility
- `FourWayResults` interface:
  - Added `sparse_count: number` (primary)
  - Made `bm25_count?: number` optional (legacy)
- `ChannelSamples` interface:
  - Added `sparse: ChannelSample[]` (primary)
  - Made `bm25?: ChannelSample[]` optional (legacy)
- `IntentWeights` interface:
  - Added `sparse: number` (primary)
  - Made `bm25?: number` optional (legacy)
- `ChannelSample.keywords` comment updated: "Sparse: Keywords used for the search (BGE-M3 learned lexical weights)"
- `PHASE_NAMES` updated: `'bm25_search': 'Lexikalische Suche'` (was "BM25-Suche")

**Impact:** All reasoning/retrieval UI components now support both old and new naming

---

### 2. Frontend Components

#### `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/components/chat/RetrievalStep.tsx`
**Changes:**
- `getSourceIcon()`: Handles both `'sparse'` and `'bm25'` (same icon)
- `getSourceName()`:
  - `'sparse'` → `'Sparse Lexical Search'`
  - `'bm25'` → `'Sparse Lexical Search'` (legacy)
- `getSourceColor()`: Both use amber colors (same visual style)
- `renderDetails()`: Case handles both `'sparse'` and `'bm25'`

**Impact:** Retrieval steps in reasoning panel show "Sparse Lexical Search" for both variants

---

#### `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/components/chat/ReasoningPanel.tsx`
**Changes:**
- Comments updated: "BM25" → "Sparse (BGE-M3 learned lexical weights)"
- `FourWaySection`:
  - Total calculation: `results.sparse_count ?? results.bm25_count ?? 0`
  - Channel map: `'Sparse (Lexikalisch)': channelSamples?.sparse ?? channelSamples?.bm25 ?? []`
  - Channel array:
    - Name: `'Sparse (Lexikalisch)'`
    - Count: `results?.sparse_count ?? results?.bm25_count ?? 0`
    - Weight: `weights?.sparse ?? weights?.bm25 ?? 0`
    - Visual: Same amber color (bg-amber-500)

**Impact:** 4-Way Hybrid Search panel shows "Sparse (Lexikalisch)" channel name

---

#### `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/pages/Settings.tsx`
**Changes:**
- Type cast updated to use `'bm25'` (matches API value)
- Display uses `RETRIEVAL_METHODS` labels (already updated)

**Impact:** Settings page shows "Sparse (Lexikalisch)" option

---

## Backward Compatibility Strategy

### Frontend Handles Both Formats
The frontend code uses fallback chains to handle both old and new data:

```typescript
// Count
results?.sparse_count ?? results?.bm25_count ?? 0

// Samples
channelSamples?.sparse ?? channelSamples?.bm25 ?? []

// Weights
weights?.sparse ?? weights?.bm25 ?? 0
```

### Legacy Support
- Old frontend with cached data showing `bm25`: ✅ Still works
- New frontend with old backend data: ✅ Works via fallbacks
- New frontend with new backend data: ✅ Uses `sparse` primarily

---

## Testing Impact

### Tests Requiring Updates
**None!** All existing tests continue to work because:
1. Phase names like `'bm25_search'` are still valid backend phase types
2. Frontend displays them as "Lexikalische Suche" (German translation)
3. Test assertions check phase types, not display labels
4. Example: `PhaseIndicator.test.tsx` uses `'bm25_search'` - still valid

### Test Files with BM25 References (No Changes Needed)
- `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/components/chat/PhaseIndicator.test.tsx`
- `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/components/chat/Citation.test.tsx`
- `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/src/components/admin/IndexingSection.test.tsx`
- Other E2E tests in `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/`

**Reason:** These tests use internal phase types (`'bm25_search'`), not UI labels.

---

## Backend API Compatibility

### API Endpoints (No Changes)
The backend API continues to use `'bm25'`:
- `/api/v1/retrieval/search` - `search_type` parameter accepts `'bm25'`
- `/api/v1/retrieval/prepare-bm25` - Endpoint name unchanged
- Validation pattern: `^(vector|bm25|hybrid)$` - Still valid

**Rationale:**
- Changing API parameters would break existing clients
- Frontend sends `'bm25'`, backend processes it as sparse vector search
- Only UI labels updated, not wire format

### Backend Labels to Frontend
The backend sends reasoning data with keys like:
- `bm25_count`, `bm25_results` - Frontend maps to "Sparse"
- Phase type: `'bm25_search'` - Frontend displays as "Lexikalische Suche"

No backend changes needed in this sprint.

---

## UI Changes Summary

### Before (Sprint 86)
| Location | Old Label |
|----------|-----------|
| Settings Page | "BM25 (Keyword)" |
| Hybrid Label | "Hybrid (Vector + BM25)" |
| Reasoning Panel | "BM25 (Keyword)" channel |
| Retrieval Step | "BM25 Keyword Search" |
| Phase Indicator | "BM25-Suche" |

### After (Sprint 92)
| Location | New Label |
|----------|-----------|
| Settings Page | "Sparse (Lexikalisch)" |
| Hybrid Label | "Hybrid (Vector + Sparse)" |
| Reasoning Panel | "Sparse (Lexikalisch)" channel |
| Retrieval Step | "Sparse Lexical Search" |
| Phase Indicator | "Lexikalische Suche" |

**User-Facing Text:**
- German: "Lexikalisch" or "Lexikalische Suche"
- English: "Sparse" or "Sparse Lexical Search"
- Tooltip: "BGE-M3 learned lexical weights for specific terms/numbers"

---

## Migration Path

### Phase 1 (Sprint 92 - Current)
- ✅ Frontend UI labels updated
- ✅ Frontend code handles both `sparse` and `bm25` keys
- ✅ Backend unchanged (still sends `bm25`)
- ✅ Backward compatible with cached data

### Phase 2 (Future Sprint 93+)
- Backend can optionally start sending `sparse_count` alongside `bm25_count`
- Frontend already handles both, so no code changes needed
- Gradual migration as cached data expires

### Phase 3 (Future Sprint 95+)
- Deprecate `bm25` keys in backend (make optional)
- Frontend continues to support both for 2-3 sprints
- Remove `bm25` fallback logic after transition period

---

## Technical Debt

### Completed (Sprint 92)
- ✅ UI labels updated to reflect Sprint 87 architecture change
- ✅ Backward compatibility maintained

### Remaining (Future)
- [ ] Backend API parameter rename (low priority, breaking change)
- [ ] Full migration to `sparse` keys in API responses (Sprint 93+)
- [ ] Remove `bm25` legacy keys after 3-sprint deprecation period

---

## Verification Checklist

### UI Components
- [x] Settings page shows "Sparse (Lexikalisch)"
- [x] Settings description mentions "BGE-M3 learned lexical weights"
- [x] Reasoning Panel channel shows "Sparse (Lexikalisch)"
- [x] Retrieval steps show "Sparse Lexical Search"
- [x] Phase indicator shows "Lexikalische Suche"

### Code Quality
- [x] TypeScript types support both `sparse` and `bm25`
- [x] Fallback chains handle legacy data
- [x] Comments updated with Sprint 87/92 context
- [x] No breaking changes to API contracts

### Testing
- [x] Existing tests still pass (no changes needed)
- [x] New components handle both data formats
- [x] Legacy data with `bm25` keys renders correctly

---

## Documentation Updates Needed

### Update in Next Sprint
1. **ADR-024** (BGE-M3 Embeddings): Add note about UI label updates in Sprint 92
2. **TECH_STACK.md**: Update "Sparse Search" terminology
3. **API Documentation**: Add deprecation notice for `bm25` parameter (plan for Sprint 95)

---

## Summary

**What Changed:** UI labels across frontend to reflect Sprint 87's BGE-M3 sparse vector implementation

**What Didn't Change:** Backend API, test assertions, internal phase types, data keys (backward compatible)

**Impact:** Users now see accurate terminology ("Sparse" instead of "BM25") without any breaking changes

**Next Steps:**
1. Monitor for any UI display issues in production
2. Plan backend API migration to `sparse` keys (Sprint 93+)
3. Update documentation to reflect new terminology

---

**Completed:** 2026-01-14 | Sprint 92 Feature 92.X
**Files Changed:** 5 frontend files (types + components)
**Lines Changed:** ~50 LOC
**Backward Compatibility:** ✅ Full (supports both `sparse` and `bm25`)
**Tests Impacted:** 0 (all existing tests still pass)
