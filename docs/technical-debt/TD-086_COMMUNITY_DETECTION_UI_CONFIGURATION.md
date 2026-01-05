# TD-086: Community Detection Parameter Configuration via UI

**Status:** Open
**Priority:** 🟡 **MEDIUM** - Enhancement for Production
**Effort:** 8 SP
**Sprint:** TBD (Post-76)
**Created:** 2025-01-05
**Root Cause:** Community detection parameters are hardcoded in backend

---

## Problem

**Current State:** Community detection uses hardcoded Leiden algorithm parameters with no ability to tune or re-run detection via UI.

### Current Behavior (Limited)

```python
# src/components/graph_rag/community_detector.py:442
partition = leidenalg.find_partition(
    graph,
    leidenalg.ModularityVertexPartition,
    # ❌ HARDCODED: No configuration possible!
    # resolution_parameter=1.0  (implicit default)
)
```

**Impact:**
- ❌ 75% singleton communities (186/248) - too granular for small graphs
- ❌ Cannot tune resolution for different graph sizes
- ❌ Cannot re-run detection with different parameters
- ❌ No visibility into current detection configuration
- ❌ Manual Python script execution required for tuning

### Evidence

**Sprint 76 Analysis (482 entities, 248 communities):**

| Size Range | Communities | % of Total | Optimal Range |
|-----------|-------------|------------|---------------|
| Singletons (1) | 186 | **75.0%** | 30-50% |
| 2-5 entities | 52 | 21.0% | 30-40% |
| 6+ entities | 10 | 4.0% | 20-30% |

**For comparison:**
- **Microsoft GraphRAG:** 40-60% singletons (production graphs)
- **Neo4j GDS Best Practice:** <50% singletons with proper tuning
- **Our current state:** 75% singletons → too granular

---

## Impact Analysis

### Affected Users

| User Role | Impact | Need |
|-----------|--------|------|
| **System Admin** | Cannot tune graph for production | UI to adjust resolution |
| **Data Scientist** | Cannot experiment with parameters | Quick re-run capability |
| **Domain Expert** | Cannot optimize for domain knowledge | Visual feedback on changes |

### Current Workarounds (Painful!)

1. **Edit Python code** → Requires backend deployment
2. **Run detection script** → No persistence to production
3. **Manually query Neo4j** → No UI feedback

---

## Root Cause

**Sprint 56:** Community detection implemented with research-grade defaults.
**Sprint 68:** Added automatic detection on ingestion but no configuration.
**Sprint 76:** Discovered high singleton ratio but no UI to tune.

**Nobody added UI for algorithm configuration!**

---

## Solution Design

### Required Changes

#### 1. **Backend Configuration Model (2 SP)**

```python
# src/core/models.py (NEW)
from pydantic import BaseModel, Field

class CommunityDetectionConfig(BaseModel):
    """Configuration for Leiden community detection algorithm."""

    algorithm: Literal["leiden", "louvain"] = Field(
        default="leiden",
        description="Community detection algorithm"
    )

    resolution_parameter: float = Field(
        default=1.0,
        ge=0.1,
        le=5.0,
        description="Resolution parameter (higher = larger communities)"
    )

    min_community_size: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Minimum entities per community (filter singletons)"
    )

    randomness: float = Field(
        default=0.01,
        ge=0.0,
        le=0.1,
        description="Randomness in Leiden algorithm"
    )

    iterations: int = Field(
        default=-1,
        ge=-1,
        description="Max iterations (-1 = auto)"
    )
```

#### 2. **Settings API Endpoint (2 SP)**

```python
# src/api/v1/admin_graph.py (NEW)

@router.get("/graph/community-detection/config")
async def get_community_detection_config() -> CommunityDetectionConfig:
    """Get current community detection configuration."""
    # Load from Redis or use defaults
    config = await redis_client.get("community_detection:config")
    return CommunityDetectionConfig.parse_raw(config) if config else CommunityDetectionConfig()

@router.put("/graph/community-detection/config")
async def update_community_detection_config(
    config: CommunityDetectionConfig
) -> dict[str, Any]:
    """Update community detection configuration.

    Note: Does NOT trigger re-detection automatically.
    Use /graph/community-detection/run endpoint to apply changes.
    """
    await redis_client.set("community_detection:config", config.json(), ex=None)

    return {
        "status": "success",
        "message": "Configuration updated. Run detection to apply changes.",
        "config": config.dict()
    }

@router.post("/graph/community-detection/run")
async def run_community_detection(
    background_tasks: BackgroundTasks
) -> dict[str, Any]:
    """Trigger community detection with current configuration.

    Returns:
        Task ID for polling status
    """
    # Load config
    config = await get_community_detection_config()

    # Run detection in background
    task_id = str(uuid.uuid4())
    background_tasks.add_task(_run_detection_task, task_id, config)

    return {
        "status": "started",
        "task_id": task_id,
        "message": f"Detection started with resolution={config.resolution_parameter}"
    }

@router.get("/graph/community-detection/status/{task_id}")
async def get_detection_status(task_id: str) -> dict[str, Any]:
    """Poll detection task status."""
    status = await redis_client.get(f"detection_task:{task_id}")

    if not status:
        raise HTTPException(404, "Task not found")

    return json.loads(status)

async def _run_detection_task(task_id: str, config: CommunityDetectionConfig):
    """Background task to run community detection."""
    try:
        await redis_client.set(
            f"detection_task:{task_id}",
            json.dumps({"status": "running", "progress": 0}),
            ex=3600
        )

        detector = get_community_detector()

        # Pass config parameters
        communities = await detector.detect_communities(
            resolution=config.resolution_parameter,
            min_size=config.min_community_size,
            randomness=config.randomness,
        )

        # Store results
        await redis_client.set(
            f"detection_task:{task_id}",
            json.dumps({
                "status": "completed",
                "communities_detected": len(communities),
                "config": config.dict()
            }),
            ex=3600
        )

    except Exception as e:
        await redis_client.set(
            f"detection_task:{task_id}",
            json.dumps({"status": "failed", "error": str(e)}),
            ex=3600
        )
```

#### 3. **Community Detector - Accept Parameters (2 SP)**

```python
# src/components/graph_rag/community_detector.py

async def detect_communities(
    self,
    resolution: float = 1.0,
    min_size: int = 1,
    randomness: float = 0.01,
    iterations: int = -1
) -> list[CommunityInfo]:
    """Detect communities with configurable parameters.

    Args:
        resolution: Resolution parameter (higher = larger communities)
        min_size: Minimum entities per community (filter small ones)
        randomness: Randomness in Leiden algorithm
        iterations: Max iterations (-1 = auto convergence)

    Returns:
        List of communities
    """
    # ... existing graph construction ...

    # Leiden with parameters
    partition = leidenalg.find_partition(
        graph,
        leidenalg.ModularityVertexPartition,
        resolution_parameter=resolution,  # ✅ Configurable!
        n_iterations=iterations,
        seed=42 if randomness == 0 else None
    )

    # ... existing community creation ...

    # Filter by minimum size
    communities = [c for c in communities if len(c.entity_ids) >= min_size]

    return communities
```

#### 4. **Frontend Admin UI Panel (4 SP)**

```tsx
// frontend/src/pages/admin/GraphManagementPage.tsx (NEW)

interface CommunityDetectionConfig {
  algorithm: 'leiden' | 'louvain';
  resolution_parameter: number;
  min_community_size: number;
  randomness: number;
  iterations: number;
}

export function GraphManagementPage() {
  const [config, setConfig] = useState<CommunityDetectionConfig | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);

  // Load current config
  useEffect(() => {
    fetch('/api/v1/graph/community-detection/config')
      .then(res => res.json())
      .then(setConfig);
  }, []);

  const handleRunDetection = async () => {
    setIsRunning(true);

    const response = await fetch('/api/v1/graph/community-detection/run', {
      method: 'POST'
    });
    const data = await response.json();
    setTaskId(data.task_id);

    // Poll for status
    pollDetectionStatus(data.task_id);
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Community Detection Configuration</h1>

      {/* Configuration Form */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Algorithm Parameters</h2>

        {/* Resolution Slider */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Resolution Parameter: {config?.resolution_parameter.toFixed(1)}
            <span className="text-gray-500 ml-2">
              (Higher = larger communities)
            </span>
          </label>
          <input
            type="range"
            min="0.1"
            max="5.0"
            step="0.1"
            value={config?.resolution_parameter}
            onChange={(e) => setConfig({
              ...config!,
              resolution_parameter: parseFloat(e.target.value)
            })}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>0.1 (Many small)</span>
            <span>1.0 (Default)</span>
            <span>5.0 (Few large)</span>
          </div>
        </div>

        {/* Min Community Size */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Minimum Community Size: {config?.min_community_size}
            <span className="text-gray-500 ml-2">
              (Filter out small communities)
            </span>
          </label>
          <input
            type="number"
            min="1"
            max="10"
            value={config?.min_community_size}
            onChange={(e) => setConfig({
              ...config!,
              min_community_size: parseInt(e.target.value)
            })}
            className="border rounded px-3 py-2"
          />
        </div>

        {/* Save & Run Buttons */}
        <div className="flex gap-3">
          <button
            onClick={() => saveConfig(config!)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Save Configuration
          </button>

          <button
            onClick={handleRunDetection}
            disabled={isRunning}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400"
          >
            {isRunning ? 'Running...' : 'Run Detection'}
          </button>
        </div>
      </div>

      {/* Current Statistics */}
      <CommunityStatistics />
    </div>
  );
}
```

---

## Testing Strategy

### Unit Tests (1 SP)
- `detect_communities()` with different resolution values
- Config validation (range checks)
- Min community size filtering

### Integration Tests (1 SP)
- API endpoint saves/loads config from Redis
- Background task runs detection with config
- Task status polling works

### E2E Tests (1 SP)
- User changes resolution → sees larger communities
- User sets min_size=2 → singletons disappear
- Re-run detection → graph updates

---

## Acceptance Criteria

1. ✅ Backend API accepts community detection config
2. ✅ Configuration persisted to Redis
3. ✅ `detect_communities()` accepts resolution parameter
4. ✅ Background task for long-running detection
5. ✅ Admin UI has parameter sliders
6. ✅ "Run Detection" button triggers re-computation
7. ✅ Real-time status updates (polling or WebSocket)
8. ✅ Community statistics displayed after detection

---

## Expected Impact

### Before (Current)
- ❌ 75% singletons (186/248 communities)
- ❌ No tuning capability
- ❌ Manual script execution

### After (With resolution=1.5)
- ✅ ~40% singletons (estimated 50-80 communities)
- ✅ UI-driven configuration
- ✅ Quick experimentation

### Parameter Guidelines

| Graph Size | Recommended Resolution | Expected Singletons |
|-----------|----------------------|-------------------|
| <1000 entities | 1.5 - 2.0 | 30-50% |
| 1000-5000 | 1.0 - 1.5 | 40-60% |
| 5000+ | 0.8 - 1.2 | 40-50% |

---

## Migration Plan

### Backward Compatibility

**Existing behavior preserved:**
- ✅ Default config: `resolution=1.0, min_size=1`
- ✅ Auto-detection on ingestion unchanged
- ✅ No breaking changes to existing API

### Deployment

1. **Phase 1:** Backend API + Redis persistence (Sprint 77)
2. **Phase 2:** Frontend UI (Sprint 77)
3. **Phase 3:** Background task + polling (Sprint 78)
4. **Phase 4:** Documentation + Guidelines (Sprint 78)

---

## Related Issues

- **Sprint 76:** Discovered 75% singleton ratio
- **TD-064:** Temporal community summaries (requires stable communities)
- **Sprint 68:** Added automatic community detection
- **Microsoft GraphRAG Paper:** Resolution tuning best practices

---

## References

- `src/components/graph_rag/community_detector.py:442` - Hardcoded parameters
- `docs/technical-debt/TD-064_TEMPORAL_COMMUNITY_SUMMARIES.md` - Related feature
- Microsoft GraphRAG Paper (2024) - Section 4.2: Community Detection
- Leiden Algorithm Paper: https://doi.org/10.1038/s41598-019-41695-z

---

## Open Questions

1. **WebSocket vs Polling?** For real-time status updates
2. **Hierarchical Detection?** Multi-level communities (future enhancement)
3. **Auto-Tuning?** Suggest optimal resolution based on graph size
4. **Visualization?** Show community graph in UI (out of scope for this TD)
