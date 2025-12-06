# Pipeline Progress Visualization Components

**Sprint 37 Feature 37.4: Visual Pipeline Progress Component**

## Overview

This feature provides a comprehensive visual representation of the document indexing pipeline progress, designed for the Admin Indexing page. It displays real-time progress updates via Server-Sent Events (SSE), showing stage completion, worker pool status, and live metrics.

## Components

### 1. PipelineProgressVisualization.tsx

**Main container component** that orchestrates the entire visualization.

**Props:**
- `progress: PipelineProgressData | null` - Pipeline progress data from SSE
- `isProcessing: boolean` - Whether pipeline is currently active

**Features:**
- Document metadata display (name, chunks, images)
- Pipeline stage flow diagram (desktop: horizontal, mobile: vertical)
- Worker pool status
- Live metrics (entities, relations, Qdrant/Neo4j writes)
- Timing information (elapsed, ETA)
- Overall progress bar

**Data-testid attributes:**
- `pipeline-progress-container` - Main container
- `document-name` - Document name display
- `overall-progress` - Overall progress percentage
- `total-chunks` - Total chunks count
- `total-images` - Total images count
- `timing-elapsed` - Elapsed time display
- `timing-remaining` - Estimated remaining time
- `metrics-entities` - Entities count
- `metrics-relations` - Relations count
- `metrics-qdrant` - Qdrant writes count
- `metrics-neo4j` - Neo4j writes count

**Usage:**
```tsx
import { PipelineProgressVisualization } from './components/admin/PipelineProgressVisualization';
import { usePipelineProgress } from './hooks/usePipelineProgress';

function AdminIndexingPage() {
  const jobId = "current-job-id"; // From backend
  const { progress, isConnected } = usePipelineProgress(jobId);

  return (
    <PipelineProgressVisualization
      progress={progress}
      isProcessing={isConnected}
    />
  );
}
```

### 2. StageProgressBar.tsx

**Individual stage progress component** with animated progress bar and status indicators.

**Props:**
- `stage: StageProgress` - Stage data (name, status, processed, total, etc.)
- `showArrow?: boolean` - Whether to show arrow to next stage (default: false)

**Features:**
- Color-coded status indicators (pending: gray, in_progress: blue, completed: green, error: red)
- Animated progress bar
- Processed/total counter
- In-flight indicator (items currently processing)
- Completion checkmark
- Duration display

**Data-testid attributes (per stage):**
- `stage-{stageName}` - Stage container (e.g., `stage-parsing`)
- `stage-progress-bar-{stageName}` - Progress bar element
- `stage-counter-{stageName}` - Counter display

**Stages:**
- Parsing
- VLM (Vision Language Model)
- Chunking
- Embedding
- Extraction

**Status Colors:**
```typescript
pending:     gray   (bg-gray-200, border-gray-300)
in_progress: blue   (bg-blue-500, border-blue-600, ring effect)
completed:   green  (bg-green-500, border-green-600)
error:       red    (bg-red-500, border-red-600)
```

### 3. WorkerPoolDisplay.tsx

**Worker pool status component** showing individual worker states and queue depth.

**Props:**
- `workers: WorkerInfo[]` - Array of worker status objects
- `queueDepth: number` - Number of chunks in queue
- `maxWorkers: number` - Maximum worker pool size

**Features:**
- Individual worker indicators with progress bars
- Worker status (idle: gray, processing: blue, error: red)
- Processing animations (pulsing dot)
- Queue depth with color coding (yellow: >10, blue: >0, gray: 0)
- Active/idle/error summary

**Data-testid attributes:**
- `worker-pool-container` - Main container
- `queue-depth` - Queue depth display
- `worker-{id}` - Individual worker container (e.g., `worker-1`)
- `worker-status-{id}` - Worker status bar (e.g., `worker-status-1`)

### 4. usePipelineProgress.ts

**Custom React hook** for managing SSE connection to pipeline progress stream.

**Signature:**
```typescript
function usePipelineProgress(jobId: string | null): {
  progress: PipelineProgressData | null;
  isConnected: boolean;
  error: string | null;
  reconnect: () => void;
}
```

**Features:**
- Automatic SSE connection management
- Connection status tracking
- Error handling with reconnect capability
- Automatic cleanup on unmount
- Null-safe (handles jobId being null)

**SSE Endpoint:**
```
GET /api/v1/admin/indexing/progress/{jobId}
```

**Event Format:**
```json
{
  "type": "pipeline_progress",
  "data": {
    "document_id": "doc-123",
    "document_name": "example.pdf",
    "total_chunks": 32,
    "total_images": 48,
    "stages": {
      "parsing": { "status": "completed", "processed": 1, "total": 1, ... },
      "vlm": { "status": "in_progress", "processed": 38, "total": 48, ... },
      ...
    },
    "worker_pool": {
      "active": 4,
      "max": 4,
      "queue_depth": 6,
      "workers": [
        { "id": 1, "status": "processing", "progress_percent": 75 },
        ...
      ]
    },
    "metrics": {
      "entities_total": 127,
      "relations_total": 89,
      "neo4j_writes": 216,
      "qdrant_writes": 28
    },
    "timing": {
      "started_at": 1234567890,
      "elapsed_ms": 154000,
      "estimated_remaining_ms": 105000
    },
    "overall_progress_percent": 68.5
  }
}
```

## Type Definitions

All types are defined in `/frontend/src/types/admin.ts`:

```typescript
export interface PipelineProgressData {
  document_id: string;
  document_name: string;
  total_chunks: number;
  total_images: number;
  stages: {
    parsing: StageProgress;
    vlm: StageProgress;
    chunking: StageProgress;
    embedding: StageProgress;
    extraction: StageProgress;
  };
  worker_pool: {
    active: number;
    max: number;
    queue_depth: number;
    workers: WorkerInfo[];
  };
  metrics: {
    entities_total: number;
    relations_total: number;
    neo4j_writes: number;
    qdrant_writes: number;
  };
  timing: {
    started_at: number;
    elapsed_ms: number;
    estimated_remaining_ms: number;
  };
  overall_progress_percent: number;
}

export interface StageProgress {
  name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
  processed: number;
  total: number;
  in_flight: number;
  progress_percent: number;
  duration_ms: number;
  is_complete: boolean;
}

export interface WorkerInfo {
  id: number;
  status: 'idle' | 'processing' | 'error';
  current_chunk: string | null;
  progress_percent: number;
}
```

## Design Mockup Reference

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Document: DE-D-BasicAdministration.pdf (8.2 MB)                      68%   │
│  Total Chunks: 32 | Images: 48 | Elapsed: 2:34 | Est. Remaining: 1:45       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─ Pipeline Stages ──────────────────────────────────────────────────────┐ │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐            │ │
│  │  │ Parsing  │──►│   VLM    │──►│ Chunking │──►│Embedding │            │ │
│  │  │ ████████ │   │ ██████░░ │   │ ████████ │   │ ██████░░ │            │ │
│  │  │  1/1 ✓   │   │ 38/48    │   │ 32/32 ✓  │   │  28/32   │            │ │
│  │  └──────────┘   └──────────┘   └──────────┘   └──────────┘            │ │
│  │                                                     ▼                  │ │
│  │                                              ┌──────────┐              │ │
│  │                                              │Extraction│              │ │
│  │                                              │ ████░░░░ │              │ │
│  │                                              │  18/32   │              │ │
│  │                                              └──────────┘              │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│  ┌─ Worker Pool ─────────────────────────────────────────────────────────┐ │
│  │  Extract Workers (4): [W1: ██] [W2: ██] [W3: ░░] [W4: ░░]  Queue: 6   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│  ┌─ Live Metrics ─────────────────────────────────────────────────────────┐ │
│  │  Entities: 127 | Relations: 89 | Qdrant: 28 | Neo4j: 216              │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Responsive Design

- **Desktop (≥768px):** Horizontal pipeline flow with arrows
- **Mobile (<768px):** Vertical stack of stage cards

## Dark Mode Support

Components use Tailwind's dark mode variants:
- Background: `bg-white dark:bg-gray-800`
- Text: `text-gray-900 dark:text-gray-100`
- Borders: `border-gray-200 dark:border-gray-700`

## Testing

### Data-testid Coverage

Total: **26+ static testids + dynamic worker testids**

**Static (11):** pipeline-progress-container, document-name, overall-progress, total-chunks, total-images, timing-elapsed, timing-remaining, metrics-entities, metrics-relations, metrics-qdrant, metrics-neo4j, worker-pool-container, queue-depth

**Per Stage (15 = 3 × 5 stages):** stage-{name}, stage-progress-bar-{name}, stage-counter-{name}

**Dynamic (per worker):** worker-{id}, worker-status-{id}

### E2E Test Example

```typescript
test('displays pipeline progress visualization', async ({ page }) => {
  // Navigate to admin indexing
  await page.goto('/admin/indexing');

  // Start indexing
  await page.click('[data-testid="start-indexing"]');

  // Verify pipeline progress appears
  await expect(page.locator('[data-testid="pipeline-progress-container"]')).toBeVisible();

  // Check document name
  await expect(page.locator('[data-testid="document-name"]')).toContainText('example.pdf');

  // Verify all stages are present
  await expect(page.locator('[data-testid="stage-parsing"]')).toBeVisible();
  await expect(page.locator('[data-testid="stage-vlm"]')).toBeVisible();
  await expect(page.locator('[data-testid="stage-chunking"]')).toBeVisible();
  await expect(page.locator('[data-testid="stage-embedding"]')).toBeVisible();
  await expect(page.locator('[data-testid="stage-extraction"]')).toBeVisible();

  // Verify worker pool
  await expect(page.locator('[data-testid="worker-pool-container"]')).toBeVisible();
  await expect(page.locator('[data-testid="worker-1"]')).toBeVisible();

  // Verify metrics
  await expect(page.locator('[data-testid="metrics-entities"]')).toBeVisible();
  await expect(page.locator('[data-testid="metrics-relations"]')).toBeVisible();
});
```

## Performance Considerations

- **SSE Connection:** Single connection per active job, auto-cleanup on unmount
- **Progress Bar Animations:** CSS transitions (300ms duration)
- **Re-renders:** Optimized with React.memo where appropriate
- **Mobile Performance:** Simplified vertical layout reduces DOM complexity

## Accessibility

- Semantic HTML structure
- ARIA labels for icons and status indicators
- Keyboard navigation support
- Color-blind friendly status colors (combined with icons)
- Screen reader announcements for progress updates

## Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Note:** Requires EventSource API support (all modern browsers)

## Future Enhancements

- [ ] Real-time log streaming in detail view
- [ ] Pause/resume pipeline capability
- [ ] Historical pipeline runs comparison
- [ ] Export progress reports
- [ ] WebSocket fallback for SSE
- [ ] Configurable worker pool size

## Files

```
frontend/src/
├── types/admin.ts                                      (Pipeline types added)
├── hooks/
│   ├── usePipelineProgress.ts                         (NEW - SSE hook)
│   └── index.ts                                        (Updated exports)
└── components/admin/
    ├── PipelineProgressVisualization.tsx              (NEW - Main component)
    ├── PipelineProgressVisualization.md               (NEW - This documentation)
    ├── StageProgressBar.tsx                           (NEW - Stage component)
    └── WorkerPoolDisplay.tsx                          (NEW - Worker pool component)
```

## Integration Example

```tsx
// AdminIndexingPage.tsx
import { useState } from 'react';
import { PipelineProgressVisualization } from '../../components/admin/PipelineProgressVisualization';
import { usePipelineProgress } from '../../hooks/usePipelineProgress';

export function AdminIndexingPage() {
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const { progress, isConnected, error } = usePipelineProgress(currentJobId);

  const handleStartIndexing = async () => {
    // Start indexing and get job ID from backend
    const response = await fetch('/api/v1/admin/indexing/add', {
      method: 'POST',
      body: JSON.stringify({ file_paths: [...] })
    });
    const { job_id } = await response.json();
    setCurrentJobId(job_id);
  };

  return (
    <div className="space-y-6">
      {/* Indexing controls */}
      <button onClick={handleStartIndexing}>Start Indexing</button>

      {/* Pipeline progress visualization */}
      {currentJobId && (
        <PipelineProgressVisualization
          progress={progress}
          isProcessing={isConnected}
        />
      )}

      {/* Error display */}
      {error && <div className="text-red-600">{error}</div>}
    </div>
  );
}
```

## License

Part of the AEGIS RAG project. See main project LICENSE.
