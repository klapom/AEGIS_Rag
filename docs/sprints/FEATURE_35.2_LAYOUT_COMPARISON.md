# Feature 35.2: Admin Indexing Layout Comparison

## Before (Sprint 33 - Vertical Layout)

```
┌─────────────────────────────────────────────────────────────┐
│ Document Indexing                                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ [Directory Input: data/sample_documents]  [Scan Directory] │
│ ☐ Recursive                                                 │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ File List (with color coding)                               │
│ ✓ file1.pdf [Docling]                                      │
│ ✓ file2.pdf [Docling]                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ [Start Indexing (2 Files)]  [Cancel]                       │
│                                                             │
│ Status: Processing file1.pdf...                            │
│ Progress: ▓▓▓▓▓▓▓░░░ 60%                                  │
│ Documents: 1 / 2                                           │
│                                                             │
│ [Errors (0)] [Details...]  ← Opens Modal Dialog            │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ ▸ Show Progress Log (12 events)  ← Collapsed by default    │
│   (Hidden until user clicks)                                │
└─────────────────────────────────────────────────────────────┘

PROBLEMS:
❌ Log hidden in collapsible section
❌ Details require modal popup
❌ Can't see log and details simultaneously
❌ Modal interrupts workflow
```

## After (Sprint 35 - Side-by-Side Layout)

```
┌─────────────────────────────────────────────────────────────┐
│ Document Indexing                                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ [Directory Input: data/sample_documents]  [Scan Directory] │
│ ☐ Recursive                                                 │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ File List (with color coding)                               │
│ ✓ file1.pdf [Docling]                                      │
│ ✓ file2.pdf [Docling]                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ [Start Indexing (2 Files)]  [Cancel]                       │
│                                                             │
│ Status: Processing file1.pdf...                            │
│ Progress: ▓▓▓▓▓▓▓░░░ 60%                                  │
│ Documents: 1 / 2                                           │
│                                                             │
│ [Errors (0)] [Details...]  ← Still available               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ ┌───────────────────────┬───────────────────────────────┐  │
│ │ Progress Log          │ Current Status                │  │
│ │ 12 entries            │                               │  │
│ ├───────────────────────┼───────────────────────────────┤  │
│ │ [14:30:45] ℹ Starting │ File: file1.pdf              │  │
│ │ [14:30:46] ℹ Parsing  │                               │  │
│ │ [14:30:48] ℹ VLM      │ Page Progress: ▓▓▓░ 5 / 10   │  │
│ │ [14:30:50] ℹ Chunking │                               │  │
│ │ [14:30:52] ℹ Embed    │ ┌─────────┬─────────┐        │  │
│ │ [14:30:54] ℹ Graph    │ │ Chunks  │ Entities│        │  │
│ │ [14:30:56] ⚠ Warning  │ │   42    │   18    │        │  │
│ │ [14:30:58] ℹ Validate │ └─────────┴─────────┘        │  │
│ │ [14:31:00] ✓ Success  │                               │  │
│ │ [14:31:02] ℹ Next...  │ Current Page Elements:       │  │
│ │ [14:31:04] ℹ Process  │ Tables: 2  Images: 3  Words:450│  │
│ │ [14:31:06] ✓ Done     │                               │  │
│ │                       │ Pipeline Stage:               │  │
│ │ (Auto-scroll active)  │ [✓Parsing][✓VLM][▶Chunk]...  │  │
│ └───────────────────────┴───────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

IMPROVEMENTS:
✅ Log always visible (left 50%)
✅ Details always visible (right 50%)
✅ Both panels update in real-time
✅ Auto-scroll to latest log entry
✅ No modal interruption
✅ Color-coded log levels
✅ Pipeline stage visualization
```

## Mobile View (<768px)

```
┌──────────────────────────┐
│ Document Indexing        │
├──────────────────────────┤
│ [Directory: ...]  [Scan] │
│ ☐ Recursive              │
├──────────────────────────┤
│ File List                │
│ ✓ file1.pdf [Docling]    │
├──────────────────────────┤
│ [Start] [Cancel]         │
│ Progress: 60%            │
├──────────────────────────┤
│ Progress Log             │
│ 12 entries               │
├──────────────────────────┤
│ [14:30:45] ℹ Starting    │
│ [14:30:46] ℹ Parsing     │
│ [14:30:48] ℹ VLM         │
│ [14:30:50] ℹ Chunking    │
│ (scrollable)             │
├──────────────────────────┤
│ Current Status           │
├──────────────────────────┤
│ File: file1.pdf          │
│ Page: 5 / 10             │
│ Chunks: 42               │
│ Entities: 18             │
│ Pipeline: Chunking...    │
└──────────────────────────┘

Responsive: Stacks vertically
```

## Key Differences

| Aspect | Before (Sprint 33) | After (Sprint 35) |
|--------|-------------------|-------------------|
| **Layout** | Vertical, single column | Side-by-side (2 columns) |
| **Log Visibility** | Collapsed by default | Always visible |
| **Details** | Modal popup required | Always visible in panel |
| **Log Length** | Limited (collapsible) | Full height (h-96) |
| **Auto-scroll** | No | Yes (auto-scroll to latest) |
| **Color Coding** | Basic phase badges | Color-coded log levels |
| **Pipeline View** | Phase badge only | Visual stage indicators |
| **Mobile** | Same as desktop | Stacks vertically |
| **Workflow** | Interrupted by modal | Seamless, no interruption |

## Component Architecture

### Before
```
AdminIndexingPage
├── IndexingDetailDialog (Modal) ← Click required
│   ├── Page Preview
│   ├── VLM Images
│   ├── Chunk Preview
│   ├── Pipeline Status
│   └── Entities
└── <details> (Collapsible Log) ← Collapsed by default
    └── Progress chunks (inline text)
```

### After
```
AdminIndexingPage
├── IndexingDetailDialog (Modal) ← Still available for advanced view
└── Split View (50/50)
    ├── LogEntry Panel (Left) ← NEW
    │   ├── LogEntry (color-coded) × N
    │   └── Auto-scroll ref
    └── DetailPanel (Right) ← NEW
        ├── Current File
        ├── Page Progress
        ├── Chunks/Entities Count
        ├── Page Elements (if available)
        └── PipelineStages (visual) ← NEW
```

## CSS Grid Layout

```css
/* Desktop (≥768px) */
.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr)); /* 50% / 50% */
  gap: 1.5rem; /* 24px */
}

/* Mobile (<768px) */
@media (max-width: 767px) {
  .grid {
    grid-template-columns: repeat(1, minmax(0, 1fr)); /* 100% */
  }
}
```

## Color Coding

### Log Levels
- **Info** (gray): `text-gray-600` - Normal operations
- **Warning** (yellow): `text-yellow-600` - Non-critical issues
- **Error** (red): `text-red-600` - Failures
- **Success** (green): `text-green-600` - Completion messages

### Pipeline Stages
- **Completed** (green): `bg-green-100 text-green-800`
- **Current** (blue): `bg-blue-100 text-blue-800` + font-medium
- **Pending** (gray): `bg-gray-100 text-gray-500`

## Data Flow

```
SSE Progress Stream
        ↓
AdminIndexingPage State
        ↓
progressHistory (ReindexProgressChunk[])
        ↓
convertToLogEntries()
        ↓
LogEntryData[] → LogEntry Components
        +
DetailedProgress → DetailPanel Component
                        ↓
                  PipelineStages Component
```

## Performance Considerations

1. **Auto-scroll**: Uses `useRef` and `useEffect` (efficient)
2. **Log rendering**: Each entry is a simple div (no heavy computation)
3. **Responsive**: CSS Grid (no JavaScript media queries)
4. **SSE updates**: Same as before (no additional overhead)

## Accessibility

- Semantic HTML maintained
- All data-testid attributes preserved
- Color contrast ratios meet WCAG 2.1 AA
- Keyboard navigation still functional
- Screen reader friendly (no modal interruption)

---

**Visual Design:** 50/50 Split View
**Responsive:** Mobile-first with Tailwind breakpoints
**UX:** Seamless, no interruptions, always visible
