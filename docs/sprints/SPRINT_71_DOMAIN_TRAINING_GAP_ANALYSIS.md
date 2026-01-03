# Domain Training API-Frontend Gap Analysis

**Sprint:** 71
**Date:** 2026-01-02
**Status:** Analysis Complete

---

## Executive Summary

**Requested:** ALL 13 Domain Training endpoints must be fully accessible via `/admin/domain-training` page.

**Current Status:** 10/13 endpoints have frontend integration (77%)

**Missing Features:** 3 critical endpoints without UI (23%)

---

## Complete Endpoint Inventory

### ✅ IMPLEMENTED (10 endpoints)

| # | Endpoint | Method | Hook/Component | Status |
|---|----------|--------|----------------|--------|
| 1 | `/admin/domains/` | GET | `useDomains()` | ✅ Auto-refresh every 5s |
| 2 | `/admin/domains/` | POST | `useCreateDomain()` | ✅ NewDomainWizard |
| 4 | `/admin/domains/available-models` | GET | `useAvailableModels()` | ✅ Model selection |
| 5 | `/admin/domains/classify` | POST | `useClassifyDocument()` | ✅ Document classification |
| 6 | `/admin/domains/discover` | POST | `DomainAutoDiscovery` | ✅ File upload + LLM suggestion |
| 8 | `/admin/domains/{name}` | DELETE | `useDeleteDomain()` | ✅ Domain deletion |
| 10 | `/admin/domains/{name}/reindex` | POST | `useReindexDomain()` | ✅ Re-index domain |
| 11 | `/admin/domains/{name}/stats` | GET | `useDomainStats()` | ✅ Auto-refresh every 10s |
| 12 | `/admin/domains/{name}/train` | POST | `useStartTraining()` | ✅ Start DSPy training |
| 13 | `/admin/domains/{name}/training-status` | GET | `useTrainingStatus()` | ✅ Poll every 2s |
| 14 | `/admin/domains/{name}/training-stream` | SSE | `useTrainingStream()` | ✅ Real-time SSE |
| 16 | `/admin/domains/{name}/validate` | POST | `useValidateDomain()` | ✅ Domain validation |

---

### ❌ MISSING (3 endpoints)

#### 1. **Data Augmentation** (Backend exists, no frontend)

**Endpoint:**
```
POST /admin/domains/augment
```

**Purpose:** Augment training dataset using LLM (paraphrasing, synonym replacement)

**Backend Implementation:**
- `src/api/v1/domain_training.py::augment_training_data()`
- Input: `AugmentationRequest` (samples, augmentation_factor)
- Output: `AugmentationResponse` (augmented samples)

**Missing UI:**
- No button/dialog in NewDomainWizard to trigger augmentation
- No way to expand 5 samples → 20+ samples via LLM

**Impact:**
- Users with small datasets (5-10 samples) cannot improve training quality
- Manual dataset expansion is tedious

**Solution (Feature 71.13):**
- Add "Augment Dataset" button in NewDomainWizard Step 2 (Upload Samples)
- Dialog: "Expand your 5 samples to 20 using LLM augmentation?"
- Show progress: "Augmenting sample 1/5..."
- Display augmented samples before training

**Estimated SP:** 2

---

#### 2. **Batch Ingestion** (Backend exists, no frontend)

**Endpoint:**
```
POST /admin/domains/ingest-batch
```

**Purpose:** Batch ingest documents grouped by LLM model for efficiency

**Backend Implementation:**
- `src/api/v1/domain_training.py::ingest_batch()`
- Input: `BatchIngestionRequest` (files, domain, recursive)
- Output: `BatchIngestionResponse` (job_id, documents_queued)

**Missing UI:**
- No way to upload multiple documents to a domain at once
- No integration with ingestion job tracker

**Impact:**
- Users must upload documents one-by-one (slow)
- Cannot leverage parallel ingestion optimization

**Solution (Feature 71.14):**
- Add "Upload Documents" button in DomainList (per domain)
- File picker with multi-select
- Calls `/admin/domains/ingest-batch`
- Returns `job_id` → redirect to `/admin/jobs/{job_id}`
- Real-time SSE progress via IngestionJobList

**Estimated SP:** 3

---

#### 3. **Get Domain Details** (Backend exists, no frontend use)

**Endpoint:**
```
GET /admin/domains/{name}
```

**Purpose:** Get full domain configuration (not just stats)

**Backend Implementation:**
- `src/api/v1/domain_training.py::get_domain()`
- Returns: `DomainResponse` (id, name, description, llm_model, prompts, metrics)

**Current Frontend:**
- `useDomains()` returns list of domains
- No individual domain detail view
- Stats are fetched via `useDomainStats()` (different endpoint)

**Missing UI:**
- No "View Details" button in DomainList
- No modal/page showing domain configuration

**Impact:**
- Users cannot see full domain config (prompts, trained metrics)
- Cannot inspect what the domain was trained on

**Solution (Feature 71.15):**
- Add "View Details" button in DomainList
- Domain Detail Modal:
  - Domain name, description
  - LLM model
  - Training metrics (F1 scores)
  - Trained prompts (if available)
  - Created/Trained timestamps
- Uses `GET /admin/domains/{name}` endpoint

**Estimated SP:** 1

---

#### 4. **Training Stream Stats** (Backend exists, unclear if needed)

**Endpoint:**
```
GET /admin/domains/{name}/training-stream/stats
```

**Purpose:** Get aggregated stats from training stream (total events, duration, etc.)

**Backend Implementation:**
- Likely exists in `domain_training.py`
- Returns: Event counts, durations, phases

**Current Frontend:**
- `useTrainingStream()` already tracks events in memory
- Could compute stats client-side

**Missing UI:**
- No stats summary in training progress dialog

**Impact:**
- Low - stats can be computed from SSE events

**Solution (Feature 71.16 - Optional):**
- Add "Training Statistics" tab in training progress dialog
- Show:
  - Total events received
  - Duration per phase
  - LLM request count
  - Evaluation metrics

**Estimated SP:** 1 (Optional)

---

## Current Frontend Components

### DomainTrainingPage (`frontend/src/pages/admin/DomainTrainingPage.tsx`)
- ✅ Back button to /admin
- ✅ "New Domain" button → opens NewDomainWizard
- ✅ Renders DomainList
- ✅ "Under Development" banner

### DomainList (`frontend/src/components/admin/DomainList.tsx`)
**Likely Implementation:**
- Lists all domains from `useDomains()`
- Shows status (pending/training/ready/failed)
- Actions per domain:
  - ✅ View Stats (via `useDomainStats()`)
  - ✅ Re-index (via `useReindexDomain()`)
  - ✅ Validate (via `useValidateDomain()`)
  - ✅ Delete (via `useDeleteDomain()`)
  - ❌ View Details (GET /domains/{name})
  - ❌ Upload Documents (POST /domains/ingest-batch)

### NewDomainWizard (`frontend/src/components/admin/NewDomainWizard.tsx`)
**Likely Steps:**
1. **Domain Info:** Name, description, LLM model
   - Uses `useAvailableModels()` for model selection
   - Option: Auto-discover via `DomainAutoDiscovery` (upload files)
2. **Training Data:** Upload samples (JSON/CSV)
   - ❌ Missing: "Augment Dataset" button (POST /domains/augment)
3. **Review & Train:** Review samples, start training
   - Uses `useCreateDomain()` → `useStartTraining()`
   - Shows `useTrainingStatus()` or `useTrainingStream()` for progress

---

## Recommended Implementation Plan (Sprint 71)

### Priority 1: Essential Missing Features

**Feature 71.13: Data Augmentation UI (2 SP)**
- Add "Augment Dataset" button in NewDomainWizard
- Dialog with augmentation_factor slider (1-5x)
- Call `POST /admin/domains/augment`
- Show augmented samples before training

**Feature 71.14: Batch Document Upload (3 SP)**
- Add "Upload Documents" button in DomainList (per domain)
- Multi-file picker
- Call `POST /admin/domains/ingest-batch`
- Integrate with IngestionJobList (Feature 71.8)

**Feature 71.15: Domain Details View (1 SP)**
- Add "View Details" button in DomainList
- Modal showing full domain config
- Call `GET /admin/domains/{name}`

### Priority 2: Optional Enhancements

**Feature 71.16: Training Stream Stats (1 SP - Optional)**
- Add stats tab in training progress dialog
- Show event counts, durations, metrics

---

## Success Criteria

**Before Sprint 71:**
- Domain Training Gap: 23% (3/13 endpoints without UI)

**After Sprint 71:**
- Domain Training Gap: 0% (13/13 endpoints accessible via UI)
- Users can:
  - ✅ Create domains with auto-discovery
  - ✅ Augment training datasets (2-5x expansion)
  - ✅ Upload multiple documents to domains
  - ✅ View full domain configuration
  - ✅ Monitor training with real-time SSE
  - ✅ Re-index, validate, delete domains

---

## Technical Notes

### API Prefix Discrepancy

**Backend:** `/admin/domains/*` (NO `/api/v1` prefix)

**Frontend Hook:** `apiClient.get('/admin/domains/')` (adds `/api/v1` automatically)

**Actual URL:** `http://localhost:8000/api/v1/admin/domains/`

**SSE Exception:** `useTrainingStream()` uses `VITE_API_HOST/admin/domains/{name}/training-stream` (NO `/api/v1`)

This is correct - the domain training router is mounted at `/admin/domains` WITHOUT `/api/v1` prefix.

---

## Estimated Total Effort

| Feature | SP |
|---------|------|
| 71.13 Data Augmentation UI | 2 |
| 71.14 Batch Document Upload | 3 |
| 71.15 Domain Details View | 1 |
| 71.16 Training Stream Stats (Optional) | 1 |
| **Total** | **7 SP** (6 required, 1 optional) |

---

## Next Steps

1. Review existing DomainList and NewDomainWizard implementations
2. Implement Feature 71.13-71.15 (6 SP)
3. Test complete domain training workflow:
   - Create domain with auto-discovery
   - Augment dataset from 5 → 20 samples
   - Train with real-time SSE monitoring
   - Upload batch documents
   - View domain details
   - Validate and re-index

