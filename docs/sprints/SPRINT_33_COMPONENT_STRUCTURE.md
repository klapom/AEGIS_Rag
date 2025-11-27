# Sprint 33 Component Structure - Visual Reference

## Component Hierarchy

```
AdminIndexingPage
├── Directory Selection Section
├── File List Section
└── Indexing Section
    ├── Start/Cancel Buttons
    ├── Progress Display
    │   ├── Status Message
    │   ├── ErrorTrackingButton ⭐ NEW (Feature 33.5)
    │   ├── Details Button ⭐ NEW (Feature 33.4)
    │   ├── Progress Bar
    │   ├── Document Count
    │   ├── Phase Badge
    │   ├── Success Message
    │   ├── Error Message
    │   └── Progress History
    └── IndexingDetailDialog ⭐ NEW (Feature 33.4)
        ├── Dialog Header
        ├── Section 1: Document & Page Preview
        ├── Section 2: VLM Image Analysis
        ├── Section 3: Chunk Processing
        ├── Section 4: Pipeline Status
        ├── Section 5: Extracted Entities
        └── Dialog Footer
```

---

## IndexingDetailDialog Component Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ Indexing Details                                         [X]    │ ← Header
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ╔═══════════════════════════════════════════════════════════╗ │
│ ║ SECTION 1: Document & Page Preview                       ║ │
│ ╠═══════════════════════════════════════════════════════════╣ │
│ ║  ┌─────────────────┐  ┌─────────────────────────────┐   ║ │
│ ║  │ [Page Thumbnail]│  │ File: document.pdf           │   ║ │
│ ║  │                 │  │ Parser: DOCLING              │   ║ │
│ ║  │                 │  │ Size: 2.5 MB                 │   ║ │
│ ║  │                 │  ├─────────────────────────────┤   ║ │
│ ║  │  Page 5 of 20   │  │ ┌──────┬──────┬──────┐     │   ║ │
│ ║  └─────────────────┘  │ │Tables│Images│Words │     │   ║ │
│ ║                       │ │  3   │  5   │ 1,234│     │   ║ │
│ ║                       │ └──────┴──────┴──────┘     │   ║ │
│ ║                       └─────────────────────────────┘   ║ │
│ ╚═══════════════════════════════════════════════════════════╝ │
│                                                                 │
│ ╔═══════════════════════════════════════════════════════════╗ │
│ ║ SECTION 2: VLM Image Analysis                            ║ │
│ ╠═══════════════════════════════════════════════════════════╣ │
│ ║  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐      ║ │
│ ║  │[IMG] │  │[IMG] │  │[IMG] │  │[IMG] │  │[IMG] │      ║ │
│ ║  │ ✅   │  │ ⚙️   │  │ ⏳   │  │ ❌   │  │ ✅   │      ║ │
│ ║  │Done  │  │Proc. │  │Pend. │  │Fail  │  │Done  │      ║ │
│ ║  │"A bar│  │      │  │      │  │      │  │"Graph│      ║ │
│ ║  │chart"│  │      │  │      │  │      │  │ show"│      ║ │
│ ║  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘      ║ │
│ ╚═══════════════════════════════════════════════════════════╝ │
│                                                                 │
│ ╔═══════════════════════════════════════════════════════════╗ │
│ ║ SECTION 3: Chunk Processing                              ║ │
│ ╠═══════════════════════════════════════════════════════════╣ │
│ ║  Current Chunk              Tokens: 1,234  [Has Image]   ║ │
│ ║  Section: "Load Balancing Strategies"                    ║ │
│ ║  ┌───────────────────────────────────────────────────┐   ║ │
│ ║  │ This section discusses various load balancing... │   ║ │
│ ║  │ techniques including round-robin, least-connec... │   ║ │
│ ║  │ and consistent hashing. Each method has trade... │   ║ │
│ ║  └───────────────────────────────────────────────────┘   ║ │
│ ╚═══════════════════════════════════════════════════════════╝ │
│                                                                 │
│ ╔═══════════════════════════════════════════════════════════╗ │
│ ║ SECTION 4: Pipeline Status                               ║ │
│ ╠═══════════════════════════════════════════════════════════╣ │
│ ║  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        ║ │
│ ║  │Parsing ✅   │ │VLM Anal ⚙️  │ │Chunking ⏳  │        ║ │
│ ║  │COMPLETED    │ │IN_PROGRESS  │ │PENDING      │        ║ │
│ ║  │2.3s         │ │1.1s         │ │             │        ║ │
│ ║  └─────────────┘ └─────────────┘ └─────────────┘        ║ │
│ ║  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        ║ │
│ ║  │Embeddings ⏳│ │BM25 Index ⏳│ │Graph ⏳      │        ║ │
│ ║  │PENDING      │ │PENDING      │ │PENDING      │        ║ │
│ ║  │             │ │             │ │             │        ║ │
│ ║  └─────────────┘ └─────────────┘ └─────────────┘        ║ │
│ ╚═══════════════════════════════════════════════════════════╝ │
│                                                                 │
│ ╔═══════════════════════════════════════════════════════════╗ │
│ ║ SECTION 5: Extracted Entities (Live)                     ║ │
│ ╠═══════════════════════════════════════════════════════════╣ │
│ ║  New Entities (from current page)                        ║ │
│ ║  ┌────────────────────────────────────────────────────┐  ║ │
│ ║  │ [Load Balancer] [API Gateway] [Redis] [MongoDB]   │  ║ │
│ ║  │ [Kubernetes] [Docker]                              │  ║ │
│ ║  └────────────────────────────────────────────────────┘  ║ │
│ ║                                                           ║ │
│ ║  New Relations (from current page)                       ║ │
│ ║  ┌────────────────────────────────────────────────────┐  ║ │
│ ║  │ [uses] [routes_to] [stores_in] [deployed_on]      │  ║ │
│ ║  └────────────────────────────────────────────────────┘  ║ │
│ ║                                                           ║ │
│ ║  ┌───────────────────┐  ┌───────────────────┐           ║ │
│ ║  │ Total Entities    │  │ Total Relations   │           ║ │
│ ║  │      1,234        │  │       2,456       │           ║ │
│ ║  └───────────────────┘  └───────────────────┘           ║ │
│ ╚═══════════════════════════════════════════════════════════╝ │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                     [Close]     │ ← Footer
└─────────────────────────────────────────────────────────────────┘
```

---

## ErrorTrackingButton Component Structure

### Button States

```
┌─────────────────────────┐    ┌─────────────────────────┐
│  Errors                 │    │  Errors            [5]  │
│  (Gray - No Errors)     │    │  (Red - Has Errors)     │
└─────────────────────────┘    └─────────────────────────┘
         ↓ Click                        ↓ Click
```

### Error Dialog

```
┌─────────────────────────────────────────────────────────────────┐
│ Indexing Errors                    [Export CSV] [X]             │
│ 3 Errors  |  2 Warnings  |  1 Info                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ ❌ [ERROR]                               10:30:45       │   │
│ │ document.pdf (Page 5)                                   │   │
│ │ Parser failed: Unsupported table format                 │   │
│ │ ▼ Show details                                          │   │
│ │   ValueError: Cannot parse nested table at line 234... │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ ⚠️ [WARNING]                             10:31:12       │   │
│ │ presentation.pptx (Page 8)                              │   │
│ │ Low resolution image detected, using fallback OCR       │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ ℹ️ [INFO]                                10:32:05       │   │
│ │ report.pdf (Page 12)                                    │   │
│ │ Using LlamaIndex fallback parser (Docling unavailable)  │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│                           ⋮                                     │
│                     (scroll for more)                           │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                     [Close]     │
└─────────────────────────────────────────────────────────────────┘
```

### CSV Export Format

```csv
Type,Timestamp,File Name,Page,Message,Details
"error","2025-11-27T10:30:45Z","document.pdf","5","Parser failed: Unsupported table format","ValueError: Cannot parse nested table at line 234..."
"warning","2025-11-27T10:31:12Z","presentation.pptx","8","Low resolution image detected, using fallback OCR",""
"info","2025-11-27T10:32:05Z","report.pdf","12","Using LlamaIndex fallback parser (Docling unavailable)",""
```

---

## Integration in AdminIndexingPage

### Before (Sprint 31)

```
┌─────────────────────────────────────────────────┐
│ Step 3: Start Indexing                         │
├─────────────────────────────────────────────────┤
│ [Start Indexing (15 files)]  [Cancel]          │
│                                                 │
│ Status: Processing document.pdf...             │
│ Progress: ████████░░░░░░░░░░ 42%              │
│ Documents: 5 / 12                               │
│ Phase: [EMBEDDING]                              │
│                                                 │
│ ✓ Indexing complete! 12 documents processed    │
└─────────────────────────────────────────────────┘
```

### After (Sprint 33 - Features 33.4 & 33.5)

```
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Start Indexing                                     │
├─────────────────────────────────────────────────────────────┤
│ [Start Indexing (15 files)]  [Cancel]                      │
│                                                             │
│ Processing document.pdf...     [Errors 3] [Details...]  ⭐ │
│ Progress: ████████░░░░░░░░░░ 42%                          │
│ Documents: 5 / 12                                           │
│ Phase: [EMBEDDING]                                          │
│                                                             │
│ ✓ Indexing complete! 12 documents processed                │
└─────────────────────────────────────────────────────────────┘
         ↓ Click [Errors]            ↓ Click [Details...]
    ┌─────────────┐              ┌─────────────────┐
    │ Error Dialog│              │ Detail Dialog   │
    │ (Feature 5) │              │ (Feature 4)     │
    └─────────────┘              └─────────────────┘
```

---

## State Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    AdminIndexingPage State                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │ directory   │    │ scanResult  │    │ selectedFiles│    │
│  │ recursive   │    │ scanError   │    │              │    │
│  └─────────────┘    └─────────────┘    └─────────────┘    │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │ isIndexing  │    │ progress    │    │ progressHist│    │
│  │ abortCtrl   │    │ error       │    │              │    │
│  └─────────────┘    └─────────────┘    └─────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │  Sprint 33 NEW State                             │      │
│  ├──────────────────────────────────────────────────┤      │
│  │  ┌─────────────┐    ┌─────────────────────┐     │      │
│  │  │isDetailDlg  │    │ detailedProgress    │     │      │
│  │  │             │    │ (DetailedProgress)  │     │      │
│  │  └─────────────┘    └─────────────────────┘     │      │
│  │                                                   │      │
│  │  ┌─────────────────────────────────────────┐    │      │
│  │  │ errors: IngestionError[]                │    │      │
│  │  └─────────────────────────────────────────┘    │      │
│  └──────────────────────────────────────────────────┘      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                           ↓
        ┌──────────────────────────────────────────┐
        │         SSE Stream (Future)              │
        ├──────────────────────────────────────────┤
        │  ReindexProgressChunk {                  │
        │    status, phase, progress_percent,      │
        │    detailed_progress?: {                 │ ⭐ NEW
        │      current_file, current_page,         │
        │      page_thumbnail_url, vlm_images,     │
        │      pipeline_status, entities, ...      │
        │    },                                     │
        │    errors?: IngestionError[]             │ ⭐ NEW
        │  }                                        │
        └──────────────────────────────────────────┘
                           ↓
        ┌──────────────────────────────────────────┐
        │    Frontend Update (Feature 33.6)        │
        ├──────────────────────────────────────────┤
        │  setProgress(chunk)                      │
        │  if (chunk.detailed_progress)            │
        │    setDetailedProgress(chunk.detailed_progress)
        │  if (chunk.errors)                       │
        │    setErrors(prev => [...prev, ...chunk.errors])
        └──────────────────────────────────────────┘
```

---

## Data-TestID Map

### IndexingDetailDialog

| Element | data-testid | Location |
|---------|-------------|----------|
| Dialog Container | `detail-dialog` | Root div |
| Page Preview Section | `detail-page-preview` | Section 1 |
| VLM Images Section | `detail-vlm-images` | Section 2 |
| Chunk Preview Section | `detail-chunk-preview` | Section 3 |
| Pipeline Status Section | `detail-pipeline-status` | Section 4 |
| Entities Section | `detail-entities` | Section 5 |

### ErrorTrackingButton

| Element | data-testid | Location |
|---------|-------------|----------|
| Error Button | `error-button` | Main button |
| Error Count Badge | `error-count-badge` | Badge on button |
| Error Dialog | `error-dialog` | Dialog container |
| Error List | `error-list` | Scrollable list |
| CSV Export Button | `error-export-csv` | Dialog header |

---

## File Structure

```
frontend/src/
├── components/
│   └── admin/
│       ├── IndexingDetailDialog.tsx       ⭐ NEW (490 LOC)
│       └── ErrorTrackingButton.tsx        ⭐ NEW (295 LOC)
├── pages/
│   └── admin/
│       └── AdminIndexingPage.tsx          ✏️  MODIFIED (+40 LOC)
├── types/
│   └── admin.ts                           ✏️  MODIFIED (+58 LOC)
└── api/
    └── admin.ts                           (No changes)

docs/sprints/
├── SPRINT_33_FEATURES_4_5_SUMMARY.md      ⭐ NEW (documentation)
└── SPRINT_33_COMPONENT_STRUCTURE.md       ⭐ NEW (this file)
```

---

## Color Palette Reference

### Error Types

| Type | Primary Color | Background | Border | Text | Symbol |
|------|---------------|------------|--------|------|--------|
| ERROR | `bg-red-500` | `bg-red-50` | `border-red-300` | `text-red-800` | ❌ |
| WARNING | `bg-orange-500` | `bg-orange-50` | `border-orange-300` | `text-orange-800` | ⚠️ |
| INFO | `bg-blue-500` | `bg-blue-50` | `border-blue-300` | `text-blue-800` | ℹ️ |

### Pipeline Phases

| Status | Background | Text | Border | Symbol |
|--------|------------|------|--------|--------|
| Pending | `bg-gray-100` | `text-gray-700` | `border-gray-300` | ⏳ |
| In Progress | `bg-yellow-100` | `text-yellow-700` | `border-yellow-300` | ⚙️ |
| Completed | `bg-green-100` | `text-green-700` | `border-green-300` | ✅ |
| Failed | `bg-red-100` | `text-red-700` | `border-red-300` | ❌ |

### VLM Image Status

| Status | Badge Color | Symbol |
|--------|-------------|--------|
| Pending | `bg-gray-100 text-gray-700` | ⏳ |
| Processing | `bg-yellow-100 text-yellow-700` | ⚙️ |
| Completed | `bg-green-100 text-green-700` | ✅ |
| Failed | `bg-red-100 text-red-700` | ❌ |

### Entity Sections

| Section | Background | Border | Text |
|---------|------------|--------|------|
| New Entities | `bg-blue-50` | `border-blue-200` | `text-blue-800` |
| New Relations | `bg-green-50` | `border-green-200` | `text-green-800` |
| Total Entities | `bg-indigo-50` | `border-indigo-200` | `text-indigo-900` |
| Total Relations | `bg-purple-50` | `border-purple-200` | `text-purple-900` |

---

## Mobile Responsiveness Breakpoints

| Breakpoint | Width | Grid Columns | Dialog Width |
|------------|-------|--------------|--------------|
| Mobile | <768px | 1 column | Full width |
| Tablet | 768px-1024px | 2 columns | 90% width |
| Desktop | >1024px | 3 columns | max-w-6xl |

**Responsive Classes Used:**
- `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` (VLM images, pipeline)
- `grid-cols-1 md:grid-cols-2` (page preview, entities)
- `max-w-6xl` (detail dialog)
- `max-w-4xl` (error dialog)
- `max-h-[90vh]` (detail dialog)
- `max-h-[80vh]` (error dialog)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-27
**Author:** Frontend Agent (Claude Code)
