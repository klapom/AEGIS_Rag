# Sprint 39: Bi-Temporal Knowledge Graph & Entity Versioning

**Status:** PLANNED
**Duration:** Nach Sprint 38 (Auth required)
**Story Points:** 37 SP (updated)
**Dependencies:** Sprint 38 (JWT Authentication)
**ADR:** [ADR-042: Bi-Temporal Opt-In Strategy](../adr/ADR-042_BITEMPORAL_OPT_IN_STRATEGY.md)

---

## Architecture Decision Summary (ADR-042)

| Entscheidung | Wert |
|--------------|------|
| **Strategie** | Opt-In Temporal mit Feature Flag |
| **Default** | `temporal_queries_enabled = false` |
| **Migration** | Nicht nötig (noch nicht produktiv) |
| **UI-Integration** | Isolierter "Time Travel" Tab |
| **Indexes** | Pflicht - Composite Indexes für Performance |
| **Performance-Ziel** | Temporal Queries < 500ms |

---

## Sprint Objectives

### Primary Goals
1. **Bi-Temporal Queries** - "Was wussten wir am Datum X?" (Opt-In)
2. **Entity Change Tracking** - Audit Trail mit `changed_by` User
3. **Entity Versioning** - Versionsverlauf und Rollback
4. **Temporal UI** - Isolierter Tab mit Time Travel Slider

### Why After Auth?
- `changed_by` Feld benötigt authentifizierten User
- Audit Trail für Compliance
- User-spezifische temporale Queries

---

## Feature Overview

| Feature | Story Points | Priority | Backend Ready |
|---------|--------------|----------|---------------|
| 39.1: Temporal Indexes & Feature Flag | 3 SP | P0 | New |
| 39.2: Bi-Temporal Query API (Opt-In) | 5 SP | P1 | Yes (`temporal_query_builder.py`) |
| 39.3: Entity Change Tracking | 5 SP | P1 | Yes (`evolution_tracker.py`) |
| 39.4: Entity Version Management | 5 SP | P1 | Yes (`version_manager.py`) |
| 39.5: Time Travel Tab (Isolated UI) | 8 SP | P1 | New |
| 39.6: Entity Changelog Panel | 5 SP | P2 | New |
| 39.7: Version Comparison View | 6 SP | P2 | New |
| **Total** | **37 SP** | | |

---

## Feature 39.1: Temporal Indexes & Feature Flag (3 SP) - P0

### Feature Flag Configuration

```python
# src/core/config.py
class Settings(BaseSettings):
    # Bi-Temporal Feature Flag (ADR-042)
    temporal_queries_enabled: bool = Field(
        default=False,
        description="Enable bi-temporal queries (Opt-In)"
    )
    temporal_version_retention: int = Field(
        default=10,
        description="Max versions per entity before cleanup"
    )
```

### Pflicht-Indexes (Neo4j)

```cypher
// scripts/neo4j_temporal_indexes.cypher
// MUST be created when temporal_queries_enabled = true

// Composite Index für Temporal Queries
CREATE INDEX temporal_validity_idx IF NOT EXISTS
FOR (e:base) ON (e.valid_from, e.valid_to);

CREATE INDEX temporal_transaction_idx IF NOT EXISTS
FOR (e:base) ON (e.transaction_from, e.transaction_to);

// Partial Index für "current only" Queries (Performance!)
CREATE INDEX current_version_idx IF NOT EXISTS
FOR (e:base) ON (e.valid_to)
WHERE e.valid_to IS NULL;

// Index für changed_by (Audit Trail)
CREATE INDEX changed_by_idx IF NOT EXISTS
FOR (e:base) ON (e.changed_by);
```

### Admin UI Toggle

```typescript
// frontend/src/pages/admin/SettingsPage.tsx
<SettingsCard title="Bi-Temporal Features (ADR-042)">
  <Toggle
    label="Enable Time Travel Queries"
    description="Aktiviert Point-in-Time Queries und Entity Versioning"
    checked={settings.temporalQueriesEnabled}
    onChange={handleTemporalToggle}
    data-testid="temporal-toggle"
  />
  {settings.temporalQueriesEnabled && (
    <Alert type="info">
      Temporal Indexes werden automatisch erstellt.
      Performance-Overhead: +200-300% für temporale Queries.
    </Alert>
  )}
</SettingsCard>
```

### Deliverables
- [ ] Feature Flag in Settings
- [ ] Index-Creation Script
- [ ] Admin UI Toggle
- [ ] Auto-Index Creation bei Aktivierung

---

## Feature 39.2: Bi-Temporal Query API - Opt-In (5 SP)

### Backend (Activate `temporal_query_builder.py`)

```python
# src/api/v1/temporal.py - NEW

@router.post("/temporal/point-in-time")
async def query_at_point_in_time(
    request: PointInTimeRequest,
    current_user: User = Depends(get_current_user)
) -> TemporalQueryResponse:
    """Query knowledge graph state at specific point in time.

    Requires: temporal_queries_enabled = true

    Use Cases:
    - "What did we know about Project X on launch day?"
    - "Show entity state before the last update"
    - Compliance: "What was recorded on audit date?"
    """
    if not settings.temporal_queries_enabled:
        raise HTTPException(
            status_code=400,
            detail="Temporal queries not enabled. Enable in Admin Settings."
        )

    builder = TemporalQueryBuilder()
    query, params = (
        builder
        .match("(e:base)")
        .as_of(request.timestamp)
        .return_clause("e")
        .build()
    )

    results = await neo4j_client.execute(query, params)
    return TemporalQueryResponse(entities=results, as_of=request.timestamp)


@router.post("/temporal/entity-history")
async def get_entity_history(
    entity_id: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(get_current_user)
) -> EntityHistoryResponse:
    """Get complete version history of an entity."""
```

### Request/Response Models

```python
# src/api/models/temporal.py

class PointInTimeRequest(BaseModel):
    timestamp: datetime
    entity_filter: str | None = None
    limit: int = Field(default=100, le=1000)

class TemporalQueryResponse(BaseModel):
    entities: list[EntitySnapshot]
    as_of: datetime
    total_count: int

class EntitySnapshot(BaseModel):
    id: str
    name: str
    type: str
    properties: dict[str, Any]
    valid_from: datetime
    valid_to: datetime | None
    version_number: int
```

### Deliverables
- [ ] `/temporal/point-in-time` endpoint
- [ ] `/temporal/entity-history` endpoint
- [ ] Feature Flag check in all endpoints
- [ ] Pydantic models for temporal responses

---

## Feature 39.3: Entity Change Tracking (5 SP)

### Backend (Activate `evolution_tracker.py`)

```python
# Automatic tracking on entity updates
async def update_entity(entity_id: str, new_data: dict, user: User):
    if not settings.temporal_queries_enabled:
        # Simple update without tracking
        return await neo4j_client.update_entity(entity_id, new_data)

    tracker = get_evolution_tracker()

    # Get current version
    old_version = await get_entity(entity_id)

    # Track changes with user info (requires Auth!)
    change_event = await tracker.track_changes(
        entity_id=entity_id,
        old_version=old_version,
        new_version=new_data,
        changed_by=user.username,  # From JWT Auth (Sprint 38)
        change_reason="Manual update via UI"
    )

    # Log for audit
    logger.info(
        "entity_changed",
        entity_id=entity_id,
        changed_by=user.username,
        changed_fields=change_event.changed_fields
    )

    return change_event
```

### API Endpoint

```python
@router.get("/entities/{entity_id}/changelog")
async def get_entity_changelog(
    entity_id: str,
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user)
) -> ChangelogResponse:
    """Get change history for an entity.

    Returns:
        List of changes with who/when/what
    """
    if not settings.temporal_queries_enabled:
        raise HTTPException(status_code=400, detail="Temporal queries not enabled")

    tracker = get_evolution_tracker()
    return await tracker.get_change_log(entity_id, limit=limit)
```

### Deliverables
- [ ] Change tracking integration
- [ ] `/entities/{id}/changelog` endpoint
- [ ] Audit logging with user context
- [ ] Feature Flag check

---

## Feature 39.4: Entity Version Management (5 SP)

### Backend (Activate `version_manager.py`)

```python
# Version operations
manager = get_version_manager()

# Get all versions
versions = await manager.get_versions(entity_id="kubernetes", limit=10)
# Returns: [v3 (current), v2, v1]

# Compare two versions
diff = await manager.compare_versions(
    entity_id="kubernetes",
    version_a=2,
    version_b=3
)
# Returns: {added: [...], removed: [...], changed: [...]}

# Rollback (creates new version, no history loss)
await manager.revert_to_version(
    entity_id="kubernetes",
    target_version=2,
    changed_by=current_user.username,
    change_reason="Reverting incorrect update"
)
```

### API Endpoints

```python
@router.get("/entities/{entity_id}/versions")
async def get_entity_versions(entity_id: str) -> list[EntityVersion]:
    """List all versions of an entity."""

@router.get("/entities/{entity_id}/versions/{version}/compare/{other_version}")
async def compare_versions(
    entity_id: str,
    version: int,
    other_version: int
) -> VersionDiff:
    """Compare two versions of an entity."""

@router.post("/entities/{entity_id}/versions/{version}/revert")
async def revert_to_version(
    entity_id: str,
    version: int,
    reason: str = Body(...),
    current_user: User = Depends(get_current_user)
) -> EntityVersion:
    """Revert entity to a previous version (creates new version)."""
```

### Deliverables
- [ ] Version listing endpoint
- [ ] Version comparison endpoint
- [ ] Rollback endpoint (creates new version)
- [ ] Retention policy enforcement

---

## Feature 39.5: Time Travel Tab - Isolated UI (8 SP)

### GUI Design: Isolierter Tab (ADR-042)

```
┌─────────────────────────────────────────────────────────────────┐
│  Knowledge Graph                                                 │
├─────────────────────────────────────────────────────────────────┤
│  [Graph] [Communities] [Time Travel]                            │
│           ▲ Normal Views    ▲ Isolierter Temporal Tab           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Time Travel Mode                              [Active]  │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │                                                         │   │
│  │  Timeline: ──●────────────────────────────────●──       │   │
│  │            Oct 1                              Today     │   │
│  │            2024                                         │   │
│  │                                                         │   │
│  │  Selected Date: [November 15, 2024]  [Apply]           │   │
│  │                                                         │   │
│  │  Quick Jumps: [1 Week Ago] [1 Month Ago] [Custom...]   │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │     [Graph View at Selected Point in Time]              │   │
│  │                                                         │   │
│  │     Entities shown: 127 (as of Nov 15)                  │   │
│  │     Changed since then: 23 entities                     │   │
│  │     New since then: 8 entities                          │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Compare with Today] [Export Snapshot] [Show Changes Only]    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Frontend Component

```typescript
// frontend/src/components/graph/TimeTravelTab.tsx

interface TimeTravelTabProps {
  onDateChange: (date: Date) => void;
  graphData: GraphData;
}

export function TimeTravelTab({ onDateChange, graphData }: TimeTravelTabProps) {
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [isLoading, setIsLoading] = useState(false);
  const { data: temporalData } = useTemporalQuery(selectedDate);

  // Get date range from graph data
  const { minDate, maxDate } = useMemo(() => {
    const dates = graphData.nodes
      .map(n => n.created_at)
      .filter(Boolean)
      .map(d => new Date(d));
    return {
      minDate: new Date(Math.min(...dates.map(d => d.getTime()))),
      maxDate: new Date()
    };
  }, [graphData]);

  return (
    <div className="time-travel-tab p-4" data-testid="time-travel-tab">
      {/* Time Travel Controls */}
      <div className="bg-gray-50 rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Time Travel Mode</h3>
          <span className="px-2 py-1 bg-amber-100 text-amber-800 rounded text-sm">
            Active
          </span>
        </div>

        {/* Date Slider */}
        <div className="mb-4">
          <label className="text-sm text-gray-600 mb-2 block">Timeline</label>
          <input
            type="range"
            min={minDate.getTime()}
            max={maxDate.getTime()}
            value={selectedDate.getTime()}
            onChange={(e) => setSelectedDate(new Date(Number(e.target.value)))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            data-testid="time-slider"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>{minDate.toLocaleDateString('de-DE')}</span>
            <span>Heute</span>
          </div>
        </div>

        {/* Date Picker */}
        <div className="flex items-center gap-4">
          <label className="text-sm text-gray-600">Selected Date:</label>
          <input
            type="date"
            value={selectedDate.toISOString().split('T')[0]}
            onChange={(e) => setSelectedDate(new Date(e.target.value))}
            max={new Date().toISOString().split('T')[0]}
            className="border rounded px-3 py-2"
            data-testid="date-picker"
          />
          <button
            onClick={() => onDateChange(selectedDate)}
            disabled={isLoading}
            className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark"
            data-testid="apply-date-button"
          >
            {isLoading ? 'Loading...' : 'Apply'}
          </button>
        </div>

        {/* Quick Jumps */}
        <div className="flex gap-2 mt-4">
          <button
            onClick={() => {
              const d = new Date();
              d.setDate(d.getDate() - 7);
              setSelectedDate(d);
            }}
            className="px-3 py-1 border rounded text-sm hover:bg-gray-100"
          >
            1 Week Ago
          </button>
          <button
            onClick={() => {
              const d = new Date();
              d.setMonth(d.getMonth() - 1);
              setSelectedDate(d);
            }}
            className="px-3 py-1 border rounded text-sm hover:bg-gray-100"
          >
            1 Month Ago
          </button>
        </div>
      </div>

      {/* Temporal Graph View */}
      {temporalData && (
        <div className="bg-white rounded-lg border p-4">
          <div className="mb-4 text-sm text-gray-600">
            <p>Entities shown: {temporalData.entities.length} (as of {selectedDate.toLocaleDateString('de-DE')})</p>
            <p>Changed since then: {temporalData.changedCount} entities</p>
            <p>New since then: {temporalData.newCount} entities</p>
          </div>

          <GraphView
            data={temporalData.graphData}
            temporalMode={true}
            asOf={selectedDate}
          />
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 mt-4">
        <button className="px-4 py-2 border rounded hover:bg-gray-50">
          Compare with Today
        </button>
        <button className="px-4 py-2 border rounded hover:bg-gray-50">
          Export Snapshot
        </button>
        <button className="px-4 py-2 border rounded hover:bg-gray-50">
          Show Changes Only
        </button>
      </div>
    </div>
  );
}
```

### Deliverables
- [ ] TimeTravelTab component
- [ ] Date slider with quick jumps
- [ ] Temporal graph visualization
- [ ] Compare with Today feature
- [ ] All data-testid attributes

---

## Feature 39.6: Entity Changelog Panel (5 SP)

### GUI Design

```
┌─────────────────────────────────────────────────────────────────┐
│  Entity: "Kubernetes"                              [Close]      │
├─────────────────────────────────────────────────────────────────┤
│  [Overview] [Relationships] [Documents] [Change Log]            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Change History (23 changes)                   [Filter by User] │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Dec 5, 2024 - 14:32                        by: admin    │   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │ + Added relationship: RELATES_TO -> "Docker"        │ │   │
│  │ │ ~ Updated description: "Container orchestration..." │ │   │
│  │ └─────────────────────────────────────────────────────┘ │   │
│  │ [View Version] [Revert to Previous]                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Nov 28, 2024 - 09:15                       by: system   │   │
│  │ ┌─────────────────────────────────────────────────────┐ │   │
│  │ │ + Created entity from document: "K8s_Guide.pdf"     │ │   │
│  │ └─────────────────────────────────────────────────────┘ │   │
│  │ [View Version]                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Load More...]                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Frontend Component

```typescript
// frontend/src/components/graph/EntityChangelog.tsx

interface ChangeEvent {
  id: string;
  timestamp: string;
  changedBy: string;
  changeType: 'create' | 'update' | 'delete' | 'relation_added' | 'relation_removed';
  changedFields: string[];
  oldValues: Record<string, unknown>;
  newValues: Record<string, unknown>;
  reason: string;
  version: number;
}

export function EntityChangelog({ entityId }: { entityId: string }) {
  const { data: changelog, isLoading, fetchMore } = useEntityChangelog(entityId);
  const [userFilter, setUserFilter] = useState<string | null>(null);

  if (isLoading) return <Spinner />;

  const filteredChanges = userFilter
    ? changelog?.filter(e => e.changedBy === userFilter)
    : changelog;

  return (
    <div className="changelog" data-testid="entity-changelog">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">
          Change History ({changelog?.length || 0} changes)
        </h3>
        <select
          value={userFilter || ''}
          onChange={(e) => setUserFilter(e.target.value || null)}
          className="border rounded px-3 py-1"
          data-testid="user-filter"
        >
          <option value="">All Users</option>
          {/* Unique users from changelog */}
          {[...new Set(changelog?.map(e => e.changedBy))].map(user => (
            <option key={user} value={user}>{user}</option>
          ))}
        </select>
      </div>

      <div className="space-y-4">
        {filteredChanges?.map((event) => (
          <ChangelogEntry
            key={event.id}
            event={event}
            onViewVersion={() => {/* ... */}}
            onRevert={() => {/* ... */}}
          />
        ))}
      </div>

      {changelog && changelog.length >= 50 && (
        <button
          onClick={fetchMore}
          className="w-full mt-4 py-2 text-primary hover:underline"
        >
          Load More...
        </button>
      )}
    </div>
  );
}

function ChangelogEntry({ event, onViewVersion, onRevert }: {
  event: ChangeEvent;
  onViewVersion: () => void;
  onRevert: () => void;
}) {
  const changeTypeColors = {
    create: 'bg-green-100 text-green-800',
    update: 'bg-blue-100 text-blue-800',
    delete: 'bg-red-100 text-red-800',
    relation_added: 'bg-purple-100 text-purple-800',
    relation_removed: 'bg-orange-100 text-orange-800'
  };

  return (
    <div
      className="border rounded-lg p-4 bg-gray-50"
      data-testid="changelog-entry"
    >
      <div className="flex justify-between items-start mb-2">
        <div>
          <span className="text-sm text-gray-600">
            {new Date(event.timestamp).toLocaleString('de-DE')}
          </span>
          <span className="mx-2 text-gray-400">-</span>
          <span className="text-sm font-medium">
            by: {event.changedBy}
          </span>
        </div>
        <span className={`px-2 py-1 rounded text-xs ${changeTypeColors[event.changeType]}`}>
          {event.changeType.replace('_', ' ')}
        </span>
      </div>

      <div className="bg-white rounded p-3 text-sm font-mono">
        {event.changedFields.map((field) => (
          <div key={field} className="flex items-start gap-2 mb-1">
            <span className="text-gray-500">{field}:</span>
            {event.oldValues[field] !== undefined && (
              <span className="line-through text-red-600">
                {formatValue(event.oldValues[field])}
              </span>
            )}
            {event.newValues[field] !== undefined && (
              <span className="text-green-600">
                {formatValue(event.newValues[field])}
              </span>
            )}
          </div>
        ))}
      </div>

      <div className="mt-3 flex gap-2">
        <button
          onClick={onViewVersion}
          className="text-sm text-primary hover:underline"
        >
          View Version {event.version}
        </button>
        {event.changeType !== 'create' && (
          <button
            onClick={onRevert}
            className="text-sm text-amber-600 hover:underline"
          >
            Revert to Previous
          </button>
        )}
      </div>
    </div>
  );
}
```

### Deliverables
- [ ] EntityChangelog component
- [ ] ChangelogEntry sub-component
- [ ] User filter dropdown
- [ ] Pagination (Load More)
- [ ] Revert action

---

## Feature 39.7: Version Comparison View (6 SP)

### GUI Design

```
┌─────────────────────────────────────────────────────────────────┐
│  Compare Versions: "Kubernetes"                    [Close]      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Version A: [v2 - Nov 28, by: system]              │
│  Version B: [v3 - Dec 5, by: admin  ]              │
│                                                                 │
│  ┌──────────────────────────┬──────────────────────────┐       │
│  │ Version 2 (Nov 28)       │ Version 3 (Dec 5)        │       │
│  ├──────────────────────────┼──────────────────────────┤       │
│  │ name: Kubernetes         │ name: Kubernetes         │       │
│  │ type: TECHNOLOGY         │ type: TECHNOLOGY         │       │
│  │ description:             │ description:             │       │
│  │ "Container orchestrat-   │ "Container orchestrat-   │       │
│  │  ion platform"           │  ion platform for auto-  │       │
│  │                          │  mated deployment"       │       │
│  │                          │                 [CHANGED]│       │
│  │ relationships: 5         │ relationships: 6         │       │
│  │                          │ + RELATES_TO -> Docker   │       │
│  │                          │                  [ADDED] │       │
│  └──────────────────────────┴──────────────────────────┘       │
│                                                                 │
│  Summary: 1 field changed, 1 relationship added                 │
│                                                                 │
│  [Revert to Version 2]           [Export Diff]      [Close]     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Frontend Component

```typescript
// frontend/src/components/graph/VersionCompare.tsx

interface VersionDiff {
  versionA: EntityVersion;
  versionB: EntityVersion;
  changes: {
    added: FieldChange[];
    removed: FieldChange[];
    changed: FieldChange[];
  };
  summary: string;
}

export function VersionCompare({
  entityId,
  versionA,
  versionB,
  onClose,
  onRevert
}: VersionCompareProps) {
  const { data: diff, isLoading } = useVersionDiff(entityId, versionA, versionB);

  if (isLoading) return <Spinner />;

  return (
    <div className="version-compare" data-testid="version-compare">
      {/* Version Selectors */}
      <div className="flex gap-4 mb-6">
        <div className="flex-1">
          <label className="text-sm text-gray-600">Version A:</label>
          <select
            value={versionA}
            className="w-full border rounded px-3 py-2 mt-1"
            data-testid="version-a-select"
          >
            {/* Version options */}
          </select>
        </div>
        <div className="flex-1">
          <label className="text-sm text-gray-600">Version B:</label>
          <select
            value={versionB}
            className="w-full border rounded px-3 py-2 mt-1"
            data-testid="version-b-select"
          >
            {/* Version options */}
          </select>
        </div>
      </div>

      {/* Side-by-Side Comparison */}
      <div className="grid grid-cols-2 gap-4 border rounded-lg overflow-hidden">
        <div className="bg-gray-50 p-4">
          <h4 className="font-semibold mb-3">
            Version {diff.versionA.version} ({new Date(diff.versionA.timestamp).toLocaleDateString('de-DE')})
          </h4>
          <VersionContent version={diff.versionA} changes={diff.changes} side="left" />
        </div>
        <div className="bg-gray-50 p-4">
          <h4 className="font-semibold mb-3">
            Version {diff.versionB.version} ({new Date(diff.versionB.timestamp).toLocaleDateString('de-DE')})
          </h4>
          <VersionContent version={diff.versionB} changes={diff.changes} side="right" />
        </div>
      </div>

      {/* Summary */}
      <div className="mt-4 p-3 bg-blue-50 rounded text-sm">
        <strong>Summary:</strong> {diff.summary}
      </div>

      {/* Actions */}
      <div className="flex justify-between mt-6">
        <button
          onClick={() => onRevert(versionA)}
          className="px-4 py-2 bg-amber-500 text-white rounded hover:bg-amber-600"
        >
          Revert to Version {versionA}
        </button>
        <div className="flex gap-2">
          <button className="px-4 py-2 border rounded hover:bg-gray-50">
            Export Diff
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 border rounded hover:bg-gray-50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
```

### Deliverables
- [ ] VersionCompare modal component
- [ ] Side-by-side diff view
- [ ] Version selectors
- [ ] Revert action
- [ ] Export diff feature

---

## Acceptance Criteria

### Feature 39.1: Temporal Indexes & Feature Flag
- [ ] Feature Flag in Settings (`temporal_queries_enabled`)
- [ ] Admin UI Toggle mit Warning
- [ ] Indexes automatisch erstellt bei Aktivierung
- [ ] Performance-Tests: Temporal Queries < 500ms mit Indexes

### Feature 39.2: Bi-Temporal Query API
- [ ] Point-in-time queries return correct historical state
- [ ] Range queries show all versions in date range
- [ ] Auth token required for all temporal endpoints
- [ ] Feature Flag check auf allen Endpoints

### Feature 39.3: Entity Change Tracking
- [ ] All entity updates automatically tracked
- [ ] `changed_by` populated from auth context
- [ ] Changelog API returns sorted history
- [ ] Audit log integration for compliance

### Feature 39.4: Entity Version Management
- [ ] Version comparison shows field-level diffs
- [ ] Rollback creates new version (no history loss)
- [ ] Version retention policy enforced (default: 10)

### Feature 39.5-39.7: UI Components
- [ ] Time Travel in isoliertem Tab (nicht Haupt-Graph)
- [ ] Date slider mit Quick Jumps
- [ ] Changelog panel mit User Filter
- [ ] Version comparison side-by-side
- [ ] All components have data-testid attributes
- [ ] E2E tests for temporal workflows

---

## Test Plan

### Unit Tests (20 tests)
- [ ] TemporalQueryBuilder methods
- [ ] Feature Flag behavior
- [ ] EvolutionTracker change detection
- [ ] VersionManager operations

### Integration Tests (10 tests)
- [ ] Temporal API endpoints with Auth
- [ ] Neo4j temporal queries with indexes
- [ ] Change tracking flow

### E2E Tests (10 tests)
- [ ] Time Travel Tab interaction
- [ ] Date slider and Quick Jumps
- [ ] Changelog pagination
- [ ] Version comparison modal
- [ ] Revert action flow

---

## Related Documents

- [ADR-042: Bi-Temporal Opt-In Strategy](../adr/ADR-042_BITEMPORAL_OPT_IN_STRATEGY.md)
- `src/components/graph_rag/temporal_query_builder.py` - Backend ready
- `src/components/graph_rag/evolution_tracker.py` - Backend ready
- `src/components/graph_rag/version_manager.py` - Backend ready
- Sprint 38: JWT Authentication (prerequisite)
