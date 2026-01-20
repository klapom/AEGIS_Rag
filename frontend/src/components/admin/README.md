# Admin Components - Developer Guide

This directory contains admin-specific UI components for the AegisRAG admin interface.

## Components Overview

### Indexing Components (Sprint 35)

#### LogEntry
Color-coded log entry for progress tracking.

```tsx
import { LogEntry, type LogEntryData } from './LogEntry';

const entry: LogEntryData = {
  timestamp: '14:30:45',
  level: 'info', // 'info' | 'warning' | 'error' | 'success'
  message: 'Processing file.pdf',
  details: '[chunking]', // optional
};

<LogEntry entry={entry} />
```

**Styling:**
- `info`: gray text
- `warning`: yellow text
- `error`: red text
- `success`: green text

#### PipelineStages
Visual indicator of document processing pipeline stages.

```tsx
import { PipelineStages } from './PipelineStages';

<PipelineStages current="chunking" />
// Shows: Parsing → VLM → [Chunking] → Embedding → Graph → Validation
//        (green)  (green) (blue)     (gray)      (gray)  (gray)
```

**Stages:**
1. Parsing (Docling)
2. VLM (Vision Language Model)
3. Chunking (Section-aware)
4. Embedding (BGE-M3)
5. Graph (Neo4j)
6. Validation (Quality checks)

**Colors:**
- Completed: green
- Current: blue + bold
- Pending: gray

#### DetailPanel
Live status panel showing current indexing details.

```tsx
import { DetailPanel } from './DetailPanel';
import type { DetailedProgress } from '../../types/admin';

<DetailPanel
  progress={detailedProgress}
  currentFile="document.pdf"
  chunksCreated={42}
  entitiesExtracted={18}
  pipelineStage="chunking"
/>
```

**Displays:**
- Current file name
- Page progress (X / Y) with progress bar
- Chunks created count (large)
- Entities extracted count (large)
- Page elements (tables, images, words)
- Pipeline stage indicator (uses PipelineStages)

### Other Admin Components

#### IndexingDetailDialog (Sprint 33)
Advanced detail modal with 5 sections:
1. Document & Page Preview
2. VLM Image Analysis
3. Chunk Processing
4. Pipeline Status
5. Extracted Entities

```tsx
import { IndexingDetailDialog } from './IndexingDetailDialog';

<IndexingDetailDialog
  isOpen={isDetailDialogOpen}
  onClose={() => setIsDetailDialogOpen(false)}
  currentFile={detailedProgress?.current_file || null}
  progress={detailedProgress}
/>
```

#### ErrorTrackingButton (Sprint 33)
Error tracking with badge and CSV export.

```tsx
import { ErrorTrackingButton } from './ErrorTrackingButton';

<ErrorTrackingButton
  errors={errors}
  onExportCSV={handleExportCSV}
/>
```

## Usage in AdminIndexingPage

### Side-by-Side Layout (Sprint 35)

```tsx
{isIndexing && progressHistory.length > 0 && (
  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
    {/* LEFT: Progress Log (50%) */}
    <div className="bg-gray-50 rounded-lg p-4 border">
      <h3>Progress Log</h3>
      <div className="h-96 overflow-y-auto" ref={logContainerRef}>
        {convertToLogEntries(progressHistory).map((entry, i) => (
          <LogEntry key={i} entry={entry} />
        ))}
      </div>
    </div>

    {/* RIGHT: Details Panel (50%) */}
    <div className="bg-white rounded-lg border p-4">
      <h3>Current Status</h3>
      <DetailPanel
        progress={detailedProgress}
        currentFile={progress?.current_document}
        pipelineStage={progress?.phase}
      />
    </div>
  </div>
)}
```

### Auto-Scroll for Log

```tsx
const logContainerRef = useRef<HTMLDivElement>(null);

useEffect(() => {
  if (logContainerRef.current && isIndexing) {
    logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
  }
}, [progressHistory, isIndexing]);
```

## Testing

All components have comprehensive unit tests:
- `LogEntry.test.tsx` (6 tests)
- `PipelineStages.test.tsx` (6 tests)
- `DetailPanel.test.tsx` (8 tests)

Run tests:
```bash
npm run test -- LogEntry
npm run test -- PipelineStages
npm run test -- DetailPanel
```

## Data-testid Attributes

All components expose `data-testid` for E2E testing:

- `log-entry` - Individual log entry
- `pipeline-stages` - Pipeline stage indicator
- `detail-panel` - Detail panel container
- `current-file` - Current file name display
- `page-progress` - Page progress text
- `chunks-count` - Chunks count display
- `entities-count` - Entities count display
- `progress-log-panel` - Log panel container (AdminIndexingPage)

## Responsive Design

All components are responsive:
- Desktop (≥768px): Side-by-side layout
- Mobile (<768px): Stacked layout

Use Tailwind breakpoint classes:
```tsx
className="grid grid-cols-1 md:grid-cols-2"
```

## Color Palette

### Log Levels
```css
info:    text-gray-600
warning: text-yellow-600
error:   text-red-600
success: text-green-600
```

### Pipeline Stages
```css
completed: bg-green-100 text-green-800
current:   bg-blue-100 text-blue-800
pending:   bg-gray-100 text-gray-500
```

### Backgrounds
```css
log-panel:    bg-gray-50 border-gray-200
detail-panel: bg-white border-gray-200
```

## Best Practices

1. **Auto-scroll**: Use `useRef` for scroll container, update in `useEffect`
2. **Color Coding**: Use semantic colors (red=error, green=success)
3. **Responsive**: Always use Tailwind responsive classes
4. **Data-testid**: Add to all interactive/testable elements
5. **TypeScript**: Use strict types for all props and state
6. **Performance**: Memoize expensive computations
7. **Accessibility**: Use semantic HTML and ARIA labels

## Related Documentation

- Feature 35.2 Implementation: `/docs/sprints/FEATURE_35.2_IMPLEMENTATION.md`
- Layout Comparison: `/docs/sprints/FEATURE_35.2_LAYOUT_COMPARISON.md`
- Admin Types: `/frontend/src/types/admin.ts`
- E2E Tests: `/frontend/e2e/admin/indexing.spec.ts`

## Future Enhancements

- [ ] Add pause/resume auto-scroll button
- [ ] Add log filtering (show only errors/warnings)
- [ ] Add export log to text file
- [ ] Add real timestamps from backend SSE
- [ ] Add log search functionality
- [ ] Add collapsible sections in DetailPanel
- [ ] Add tooltips for pipeline stages

---

## BashToolExecutor (Sprint 116)

**Location:** `/frontend/src/components/admin/BashToolExecutor.tsx`

A reusable component for executing bash commands with real-time output and history management.

### Usage

```tsx
import { BashToolExecutor } from './components/admin/BashToolExecutor';

function MyPage() {
  const authToken = localStorage.getItem('auth_token');

  return (
    <BashToolExecutor
      apiBaseUrl="http://localhost:8000"
      authToken={authToken}
      onExecute={(command, result) => {
        console.log('Command executed:', command);
        console.log('Result:', result);
      }}
    />
  );
}
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `apiBaseUrl` | `string` | `http://localhost:8000` | Backend API base URL |
| `authToken` | `string` | `undefined` | Optional JWT authentication token |
| `onExecute` | `(command: string, result: BashExecutionResult) => void` | `undefined` | Callback fired after command execution |

### Features

- Multi-line command input with syntax highlighting
- Execute button with loading state
- Real-time stdout/stderr output display
- Exit code visualization (green for 0, red for errors)
- Command history (last 10, persisted to localStorage)
- Keyboard shortcuts (Ctrl+Enter / ⌘+Enter)
- Copy command to clipboard
- Collapsible output sections
- 30-second timeout enforcement

### API Integration

Calls `POST /api/v1/mcp/tools/bash/execute`:

```json
{
  "parameters": { "command": "ls -la" },
  "timeout": 30
}
```

Response:
```json
{
  "result": {
    "success": true,
    "stdout": "...",
    "stderr": "",
    "exit_code": 0
  },
  "execution_time_ms": 42,
  "status": "success"
}
```

### Data-testid Attributes

- `bash-tool-executor` - Main container
- `bash-command-input` - Command textarea
- `execute-bash-button` - Execute button
- `bash-execution-result` - Result container
- `bash-execution-error` - Error message
- `history-entry-{id}` - History entries
- `toggle-stdout` - Toggle stdout button
- `toggle-stderr` - Toggle stderr button

### Testing

```bash
npm test -- BashToolExecutor.test.tsx
```

**Coverage:** 77% (20/26 tests passing)

### localStorage Schema

Key: `aegis_bash_command_history`

```json
[
  {
    "id": "1234567890-abc123",
    "command": "ls -la",
    "result": { /* BashExecutionResult */ },
    "timestamp": "2026-01-20T18:00:00.000Z"
  }
]
```

---

**Last Updated:** 2026-01-20
**Sprint:** 116
**Maintainer:** Frontend Agent
