# Sprint 49: Admin UX Improvements & Reasoning History

**Sprint Duration:** TBD
**Story Points:** 39 SP
**Status:** 🟡 PLANNED

---

## Sprint Goals

1. **Dynamic LLM Configuration**: Auto-populate LLM models from Ollama (no hardcoded lists)
2. **Graph Relationship Filtering**: Add multiselect for all available relationship types
3. **Reasoning History View**: Display phase events from past conversations

---

## Features

### Feature 49.1: Dynamic LLM Selection from Ollama (8 SP)

**Problem:**
- `/admin/llm-config` uses hardcoded model list (`defaultModelOptions`)
- New Ollama models require code changes to appear in dropdown
- No automatic discovery of available models

**Solution:**
Fetch available Ollama models via API and filter out embedding models.

**Implementation:**

#### Backend: New API Endpoint
```python
# src/api/v1/admin.py

@router.get("/ollama/models", response_model=OllamaModelsResponse)
async def list_ollama_models() -> OllamaModelsResponse:
    """List all Ollama models (excluding embeddings).

    Returns:
        OllamaModelsResponse with text and vision models
    """
    try:
        ollama_url = settings.ollama_base_url
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ollama_url}/api/tags") as resp:
                data = await resp.json()

        # Filter out embedding models
        text_models = []
        vision_models = []

        for model in data.get("models", []):
            name = model["name"]

            # Skip embedding models
            if any(emb in name.lower() for emb in ["embed", "nomic", "bge-m3", "mxbai"]):
                continue

            # Detect vision models
            is_vision = any(vision in name.lower() for vision in ["vl", "vision", "llava"])

            model_info = {
                "id": f"ollama/{name}",
                "name": name,
                "size": model.get("size", 0),
                "modified_at": model.get("modified_at"),
                "capabilities": ["text", "vision"] if is_vision else ["text"]
            }

            if is_vision:
                vision_models.append(model_info)
            else:
                text_models.append(model_info)

        return OllamaModelsResponse(
            text_models=text_models,
            vision_models=vision_models,
            total_count=len(text_models) + len(vision_models)
        )

    except Exception as e:
        logger.error("failed_to_fetch_ollama_models", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Ollama models: {str(e)}"
        )
```

#### Frontend: Fetch Models on Page Load
```tsx
// frontend/src/pages/admin/AdminLLMConfigPage.tsx

const [ollamaModels, setOllamaModels] = useState<ModelOption[]>([]);
const [loading, setLoading] = useState(true);

useEffect(() => {
  async function fetchOllamaModels() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/ollama/models`);
      const data = await response.json();

      // Convert to ModelOption format
      const models: ModelOption[] = [
        ...data.text_models.map(m => ({
          id: m.id,
          provider: 'ollama' as const,
          name: m.name,
          description: `Local model (${formatBytes(m.size)})`,
          capabilities: m.capabilities
        })),
        ...data.vision_models.map(m => ({
          id: m.id,
          provider: 'ollama' as const,
          name: m.name,
          description: `Vision model (${formatBytes(m.size)})`,
          capabilities: m.capabilities
        }))
      ];

      setOllamaModels(models);
    } catch (error) {
      console.error('Failed to fetch Ollama models:', error);
    } finally {
      setLoading(false);
    }
  }

  fetchOllamaModels();
}, []);

// Combine with cloud providers
const allModelOptions = [...ollamaModels, ...cloudProviderModels];
```

**Acceptance Criteria:**
- ✅ New Ollama models appear automatically in dropdown
- ✅ Embedding models are excluded
- ✅ Vision models are correctly identified
- ✅ Error handling for Ollama connectivity issues
- ✅ Loading state while fetching models

**Files to Modify:**
- `src/api/v1/admin.py` (new endpoint)
- `src/models/admin.py` (Pydantic models)
- `frontend/src/pages/admin/AdminLLMConfigPage.tsx` (fetch logic)
- `frontend/src/api/admin.ts` (API function)

**Related TD:** TD-053 (Admin Dashboard Full Implementation)

---

### Feature 49.2: Graph Relationship Type Multiselect (8 SP)

**Problem:**
- `/admin/graph` has hardcoded EdgeFilters (`showRelatesTo`, `showCoOccurs`, `showMentionedIn`)
- Cannot filter by custom relationship types (e.g., `WORKS_AT`, `LOCATED_IN`)
- New relationship types require code changes

**Solution:**
Fetch available relationship types from Neo4j and provide multiselect filter.

**Implementation:**

#### Backend: Relationship Types Endpoint
```python
# src/api/v1/admin.py

@router.get("/graph/relationship-types", response_model=RelationshipTypesResponse)
async def get_relationship_types() -> RelationshipTypesResponse:
    """Get all relationship types from Neo4j graph.

    Returns:
        RelationshipTypesResponse with types and counts
    """
    from src.components.graph_rag.neo4j_client import get_neo4j_client

    neo4j_client = get_neo4j_client()

    # Query all relationship types with counts
    query = """
    MATCH ()-[r]->()
    RETURN
        type(r) as relationship_type,
        count(r) as count
    ORDER BY count DESC
    """

    result = neo4j_client.query(query)

    relationship_types = [
        RelationshipTypeInfo(
            type=record["relationship_type"],
            count=record["count"],
            label=format_relationship_label(record["relationship_type"])
        )
        for record in result
    ]

    return RelationshipTypesResponse(
        relationship_types=relationship_types,
        total_types=len(relationship_types)
    )
```

#### Frontend: Multiselect Component
```tsx
// frontend/src/components/graph/GraphFilters.tsx

interface RelationshipTypeFilter {
  type: string;
  label: string;
  count: number;
  enabled: boolean;
}

export function GraphFilters({ ... }) {
  const [relationshipTypes, setRelationshipTypes] = useState<RelationshipTypeFilter[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchRelationshipTypes() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/admin/graph/relationship-types`);
        const data = await response.json();

        const types: RelationshipTypeFilter[] = data.relationship_types.map(rt => ({
          type: rt.type,
          label: rt.label,
          count: rt.count,
          enabled: true // All enabled by default
        }));

        setRelationshipTypes(types);
      } catch (error) {
        console.error('Failed to fetch relationship types:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchRelationshipTypes();
  }, []);

  const handleToggleRelationshipType = (type: string) => {
    setRelationshipTypes(prev =>
      prev.map(rt =>
        rt.type === type ? { ...rt, enabled: !rt.enabled } : rt
      )
    );

    // Update parent filter state
    const enabledTypes = relationshipTypes
      .filter(rt => rt.enabled)
      .map(rt => rt.type);
    onFiltersChange({ ...filters, relationshipTypes: enabledTypes });
  };

  return (
    <div className="space-y-4">
      {/* ... existing filters ... */}

      {/* Relationship Types Filter */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-2">
          Relationship Types
        </h4>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {relationshipTypes.map(rt => (
            <label
              key={rt.type}
              className="flex items-center justify-between px-3 py-2 hover:bg-gray-50 rounded cursor-pointer"
            >
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={rt.enabled}
                  onChange={() => handleToggleRelationshipType(rt.type)}
                  className="rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-sm text-gray-700">{rt.label}</span>
              </div>
              <span className="text-xs text-gray-500">{rt.count.toLocaleString()}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
```

**Acceptance Criteria:**
- ✅ All relationship types from Neo4j displayed in multiselect
- ✅ Show count for each relationship type
- ✅ Graph updates when relationship type filter changes
- ✅ "Select All" / "Deselect All" buttons
- ✅ Relationship types sorted by count (descending)

**Files to Modify:**
- `src/api/v1/admin.py` (new endpoint)
- `src/models/admin.py` (Pydantic models)
- `frontend/src/components/graph/GraphFilters.tsx` (multiselect UI)
- `frontend/src/api/admin.ts` (API function)
- `frontend/src/types/graph.ts` (TypeScript types)

**Related TDs:**
- TD-046 (RELATES_TO Relationship Extraction)
- TD-048 (Graph Extraction with Unified Chunks)
- TD-063 (Relation Deduplication)

---

### Feature 49.3: Historical Phase Events Display (13 SP)

**Problem:**
- Phase events only visible during live streaming (Sprint 48)
- Cannot view reasoning process for past conversations
- No way to debug or understand historical query processing

**Solution:**
Add collapsible reasoning panel to conversation history messages.

**Implementation:**

#### Backend: Extend Conversation API
```python
# src/api/v1/chat.py

@router.get("/history/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(session_id: str, include_phase_events: bool = False):
    """Retrieve conversation history with optional phase events.

    Args:
        session_id: Session ID
        include_phase_events: If True, include phase events for each message

    Returns:
        ConversationHistoryResponse with messages and optional phase events
    """
    # ... existing logic ...

    if include_phase_events:
        # Fetch phase events for this session
        phase_events_key = f"phase_events:{session_id}"
        phase_events_data = await redis_memory.retrieve(key=phase_events_key)

        if phase_events_data and "value" in phase_events_data:
            messages_with_events = []
            for msg in messages:
                # Match phase events to message by timestamp
                msg_phase_events = [
                    e for e in phase_events_data["value"]
                    if e.get("message_index") == messages.index(msg)
                ]
                messages_with_events.append({
                    **msg,
                    "phase_events": msg_phase_events
                })
            messages = messages_with_events

    return ConversationHistoryResponse(
        session_id=session_id,
        messages=messages,
        message_count=len(messages)
    )
```

#### Frontend: Historical Reasoning Panel
```tsx
// frontend/src/components/chat/MessageBubble.tsx

interface MessageBubbleProps {
  message: MessageData;
  onCitationClick?: (sourceId: string) => void;
  showHistoricalReasoning?: boolean; // New prop
}

export function MessageBubble({ message, onCitationClick, showHistoricalReasoning = true }: MessageBubbleProps) {
  const [showReasoning, setShowReasoning] = useState(false);
  const [phaseEvents, setPhaseEvents] = useState<PhaseEvent[]>([]);
  const [loading, setLoading] = useState(false);

  const loadPhaseEvents = async () => {
    if (!message.session_id || phaseEvents.length > 0) return;

    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/chat/conversations/${message.session_id}/phase-events`
      );
      const events = await response.json();
      setPhaseEvents(events);
    } catch (error) {
      console.error('Failed to load phase events:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleReasoning = () => {
    if (!showReasoning && phaseEvents.length === 0) {
      loadPhaseEvents();
    }
    setShowReasoning(!showReasoning);
  };

  return (
    <div className="message-bubble">
      {/* ... existing message content ... */}

      {/* Historical Reasoning Panel (Assistant messages only) */}
      {message.role === 'assistant' && showHistoricalReasoning && (
        <div className="mt-3 border-t border-gray-200 pt-3">
          <button
            onClick={handleToggleReasoning}
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
          >
            <Brain className="w-4 h-4" />
            <span>
              {showReasoning ? 'Reasoning ausblenden' : 'Reasoning anzeigen'}
            </span>
            {loading && <Loader className="w-4 h-4 animate-spin" />}
          </button>

          {showReasoning && (
            <div className="mt-3 space-y-2">
              {phaseEvents.length === 0 && !loading && (
                <p className="text-xs text-gray-500 italic">
                  Keine Phase Events verfügbar (Pre-Sprint 48 Conversation)
                </p>
              )}

              {phaseEvents.map((event, idx) => (
                <PhaseEventCard key={idx} event={event} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

#### New Component: PhaseEventCard
```tsx
// frontend/src/components/chat/PhaseEventCard.tsx

interface PhaseEventCardProps {
  event: PhaseEvent;
}

export function PhaseEventCard({ event }: PhaseEventCardProps) {
  const getPhaseIcon = (type: PhaseType) => {
    switch (type) {
      case 'intent_classification': return <Target className="w-4 h-4" />;
      case 'vector_search': return <Search className="w-4 h-4" />;
      case 'graph_query': return <Network className="w-4 h-4" />;
      case 'rrf_fusion': return <Layers className="w-4 h-4" />;
      case 'reranking': return <ArrowUpDown className="w-4 h-4" />;
      case 'llm_generation': return <Sparkles className="w-4 h-4" />;
      default: return <Circle className="w-4 h-4" />;
    }
  };

  const getStatusColor = (status: PhaseStatus) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-50';
      case 'failed': return 'text-red-600 bg-red-50';
      case 'in_progress': return 'text-blue-600 bg-blue-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
      <div className={`p-2 rounded ${getStatusColor(event.status)}`}>
        {getPhaseIcon(event.phase_type)}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <h5 className="text-sm font-medium text-gray-900">
            {formatPhaseType(event.phase_type)}
          </h5>
          <span className="text-xs text-gray-500">
            {event.duration_ms ? `${event.duration_ms.toFixed(0)}ms` : '-'}
          </span>
        </div>

        {event.metadata && Object.keys(event.metadata).length > 0 && (
          <div className="mt-1 text-xs text-gray-600">
            {Object.entries(event.metadata).map(([key, value]) => (
              <div key={key}>
                <span className="font-medium">{key}:</span> {JSON.stringify(value)}
              </div>
            ))}
          </div>
        )}

        {event.error && (
          <div className="mt-1 text-xs text-red-600">
            Error: {event.error}
          </div>
        )}
      </div>
    </div>
  );
}
```

**Acceptance Criteria:**
- ✅ "Reasoning anzeigen" button on assistant messages
- ✅ Phase events loaded on-demand (lazy loading)
- ✅ Phase events displayed with icons, duration, metadata
- ✅ Graceful handling for pre-Sprint 48 conversations (no phase events)
- ✅ Collapsible panel (default: closed)
- ✅ Visual distinction between phase types (colors, icons)

**Files to Create:**
- `frontend/src/components/chat/PhaseEventCard.tsx` (new component)

**Files to Modify:**
- `frontend/src/components/chat/MessageBubble.tsx` (add reasoning toggle)
- `src/api/v1/chat.py` (extend history endpoint)
- `frontend/src/api/chat.ts` (API function)
- `frontend/src/types/reasoning.ts` (TypeScript types)

**Related:** Sprint 48 Feature 48.5 (Phase Events Redis Persistence)

---

### Feature 49.4: Fix Indexing Progress Inconsistency Bug (3 SP)

**Problem:**
Document indexing shows contradictory messages:
- "Successfully added **-3** document(s)" (negative count!)
- "3 failed" but status says "Successfully"
- User feedback is confusing and misleading

**Root Cause:**
Progress calculation error when all documents fail - `successful_count - failed_count` = `0 - 3` = `-3`

**Solution:**
Fix progress messages and success determination logic.

**Implementation:**

#### Backend: Fix Progress Calculation
```python
# src/api/v1/admin.py - Index documents endpoint

async def send_progress(message: str, progress: int, status: str = "info"):
    """Send SSE progress update with consistent messaging."""
    event_data = {
        "message": message,
        "progress": progress,
        "status": status,
        "timestamp": datetime.now(UTC).isoformat()
    }
    await queue.put(f"data: {json.dumps(event_data)}\n\n")

# In the indexing logic:
successful_count = len([d for d in results if d["status"] == "success"])
failed_count = len([d for d in results if d["status"] == "failed"])
total_processed = successful_count + failed_count  # Always positive

# Determine overall status
if failed_count == 0:
    final_status = "Successfully"
    status_type = "success"
elif successful_count == 0:
    final_status = "Failed to add"
    status_type = "error"
else:
    final_status = "Partially completed"
    status_type = "warning"

final_message = (
    f"{final_status}: {successful_count} document(s) indexed, "
    f"{failed_count} failed"
    if failed_count > 0
    else f"{final_status}: {successful_count} document(s) indexed"
)

await send_progress(final_message, 100, status_type)
```

#### Frontend: Status Display
```tsx
// frontend/src/pages/admin/AdminIndexingPage.tsx

function getStatusColor(status: string): string {
  switch (status) {
    case 'success': return 'text-green-600';
    case 'warning': return 'text-yellow-600';
    case 'error': return 'text-red-600';
    default: return 'text-gray-600';
  }
}

function getStatusIcon(status: string): React.ReactNode {
  switch (status) {
    case 'success': return <CheckCircle className="w-5 h-5" />;
    case 'warning': return <AlertTriangle className="w-5 h-5" />;
    case 'error': return <XCircle className="w-5 h-5" />;
    default: return <Info className="w-5 h-5" />;
  }
}
```

**Acceptance Criteria:**
- ✅ No negative document counts ever shown
- ✅ "Failed" status when all documents fail (not "Successfully")
- ✅ "Partially completed" when some succeed, some fail
- ✅ Clear visual distinction (colors, icons) for success/warning/error
- ✅ Consistent messaging across all SSE events

**Files to Modify:**
- `src/api/v1/admin.py` (indexing progress logic)
- `frontend/src/pages/admin/AdminIndexingPage.tsx` (status display)

**Related:** Sprint 13 Feature 13.1 (SSE Progress Streaming)

---

### Feature 49.5: Add source_chunk_id to Relationships (13 SP)

**Problem (TD-048):**
- `MENTIONED_IN` relationships lack provenance tracking
- Cannot trace which chunk an entity was extracted from
- Debugging extraction issues is difficult
- No validation that entities come from indexed chunks

**Solution:**
Add `source_chunk_id` property to all `MENTIONED_IN` relationships in Neo4j.

**Implementation:**

#### Step 1: Update LightRAG Entity Extraction
```python
# src/components/graph_rag/lightrag_wrapper.py

async def insert_entity(self, entity_data: dict, chunk_id: str) -> None:
    """Insert entity with chunk provenance tracking.

    Args:
        entity_data: Entity information (name, type, description)
        chunk_id: Qdrant chunk ID for provenance
    """
    query = """
    MERGE (e:base {entity_id: $entity_id})
    ON CREATE SET
        e.entity_name = $entity_name,
        e.entity_type = $entity_type,
        e.description = $description,
        e.created_at = datetime()
    ON MATCH SET
        e.updated_at = datetime()

    MERGE (c:chunk {chunk_id: $chunk_id})

    MERGE (e)-[r:MENTIONED_IN]->(c)
    ON CREATE SET
        r.source_chunk_id = $chunk_id,
        r.confidence = $confidence,
        r.extraction_timestamp = datetime()
    ON MATCH SET
        r.updated_at = datetime()

    RETURN e.entity_id as entity_id
    """

    await self.neo4j_client.execute(query, {
        "entity_id": entity_data["entity_id"],
        "entity_name": entity_data["entity_name"],
        "entity_type": entity_data["entity_type"],
        "description": entity_data.get("description", ""),
        "chunk_id": chunk_id,
        "confidence": entity_data.get("confidence", 1.0)
    })
```

#### Step 2: Migration Script for Existing Data
```python
# scripts/migrate_add_chunk_provenance.py

async def migrate_add_chunk_provenance():
    """Add source_chunk_id to existing MENTIONED_IN relationships."""
    neo4j_client = get_neo4j_client()

    # Query to update existing relationships
    query = """
    MATCH (e:base)-[r:MENTIONED_IN]->(c:chunk)
    WHERE r.source_chunk_id IS NULL
    SET r.source_chunk_id = c.chunk_id,
        r.migrated_at = datetime()
    RETURN count(r) as updated_count
    """

    result = await neo4j_client.execute(query)
    logger.info(f"Migration complete: {result[0]['updated_count']} relationships updated")
```

#### Step 3: Validation Endpoint
```python
# src/api/v1/admin.py

@router.get("/graph/provenance-validation", response_model=ProvenanceValidationResponse)
async def validate_graph_provenance():
    """Validate that all MENTIONED_IN relationships have source_chunk_id."""
    neo4j_client = get_neo4j_client()

    # Count total relationships
    total_query = """
    MATCH ()-[r:MENTIONED_IN]->()
    RETURN count(r) as total
    """
    total = neo4j_client.query(total_query)[0]["total"]

    # Count relationships with provenance
    valid_query = """
    MATCH ()-[r:MENTIONED_IN]->()
    WHERE r.source_chunk_id IS NOT NULL
    RETURN count(r) as valid
    """
    valid = neo4j_client.query(valid_query)[0]["valid"]

    # Find missing provenance
    missing_query = """
    MATCH (e:base)-[r:MENTIONED_IN]->(c:chunk)
    WHERE r.source_chunk_id IS NULL
    RETURN e.entity_name, c.chunk_id
    LIMIT 10
    """
    missing_examples = neo4j_client.query(missing_query)

    return ProvenanceValidationResponse(
        total_relationships=total,
        valid_relationships=valid,
        missing_provenance=total - valid,
        validation_percentage=(valid / total * 100) if total > 0 else 0,
        missing_examples=missing_examples
    )
```

**Acceptance Criteria:**
- ✅ All new `MENTIONED_IN` relationships have `source_chunk_id`
- ✅ Migration script updates existing relationships
- ✅ Validation endpoint confirms 100% provenance coverage
- ✅ Entity extraction includes chunk_id parameter
- ✅ Admin UI shows provenance validation status

**Files to Create:**
- `scripts/migrate_add_chunk_provenance.py` (migration script)

**Files to Modify:**
- `src/components/graph_rag/lightrag_wrapper.py` (entity insertion)
- `src/components/graph_rag/parallel_extractor.py` (pass chunk_id)
- `src/api/v1/admin.py` (validation endpoint)
- `frontend/src/pages/admin/GraphAnalyticsPage.tsx` (display validation)

**Related TD:** TD-048 (Graph Extraction with Unified Chunks) - RESOLVED by this feature

---

### Feature 49.6: Index Consistency Validation (8 SP)

**Problem (TD-048):**
- No way to verify that Qdrant, Neo4j, and BM25 are synchronized
- Chunk counts may diverge after failed indexing
- Re-indexing validation is unreliable
- No admin visibility into cross-layer consistency

**Solution:**
Admin endpoint and UI to validate consistency across all indexes.

**Implementation:**

#### Backend: Consistency Check Endpoint
```python
# src/api/v1/admin.py

@router.get("/validation/index-consistency", response_model=IndexConsistencyResponse)
async def validate_index_consistency(namespace: str = "default"):
    """Validate consistency across Qdrant, Neo4j, and BM25 indexes.

    Checks:
    1. Qdrant chunk count vs BM25 corpus size
    2. Neo4j chunk nodes vs Qdrant chunks
    3. Entity provenance (all entities linked to valid chunks)
    4. Orphaned chunks (no entities extracted)

    Args:
        namespace: Namespace to validate

    Returns:
        IndexConsistencyResponse with validation results
    """
    from src.components.vector_search.qdrant_client import get_qdrant_client
    from src.components.vector_search.bm25_retriever import get_bm25_retriever
    from src.components.graph_rag.neo4j_client import get_neo4j_client

    qdrant_client = get_qdrant_client()
    bm25_retriever = get_bm25_retriever()
    neo4j_client = get_neo4j_client()

    # 1. Count Qdrant chunks
    qdrant_count = await qdrant_client.count_points(
        collection_name=settings.qdrant_collection_name,
        namespace=namespace
    )

    # 2. Count BM25 corpus
    bm25_count = len(bm25_retriever.get_corpus(namespace))

    # 3. Count Neo4j chunk nodes
    neo4j_query = """
    MATCH (c:chunk)
    WHERE c.namespace = $namespace
    RETURN count(c) as count
    """
    neo4j_count = neo4j_client.query(neo4j_query, {"namespace": namespace})[0]["count"]

    # 4. Check entity provenance
    provenance_query = """
    MATCH (e:base)-[r:MENTIONED_IN]->(c:chunk)
    WHERE c.namespace = $namespace AND r.source_chunk_id IS NULL
    RETURN count(r) as missing_provenance
    """
    missing_provenance = neo4j_client.query(provenance_query, {"namespace": namespace})[0]["missing_provenance"]

    # 5. Check orphaned chunks (no entities)
    orphaned_query = """
    MATCH (c:chunk)
    WHERE c.namespace = $namespace AND NOT (c)<-[:MENTIONED_IN]-()
    RETURN count(c) as orphaned_chunks
    """
    orphaned_chunks = neo4j_client.query(orphaned_query, {"namespace": namespace})[0]["orphaned_chunks"]

    # Determine consistency status
    qdrant_bm25_consistent = abs(qdrant_count - bm25_count) <= 1  # Allow 1 difference (timing)
    qdrant_neo4j_consistent = abs(qdrant_count - neo4j_count) <= 5  # Allow 5 difference (extraction lag)
    provenance_consistent = missing_provenance == 0

    overall_consistent = (
        qdrant_bm25_consistent and
        qdrant_neo4j_consistent and
        provenance_consistent
    )

    return IndexConsistencyResponse(
        namespace=namespace,
        qdrant_count=qdrant_count,
        bm25_count=bm25_count,
        neo4j_count=neo4j_count,
        qdrant_bm25_consistent=qdrant_bm25_consistent,
        qdrant_neo4j_consistent=qdrant_neo4j_consistent,
        provenance_consistent=provenance_consistent,
        missing_provenance=missing_provenance,
        orphaned_chunks=orphaned_chunks,
        overall_consistent=overall_consistent,
        checked_at=datetime.now(UTC)
    )
```

#### Frontend: Validation Dashboard
```tsx
// frontend/src/pages/admin/IndexValidationPage.tsx

export function IndexValidationPage() {
  const [validation, setValidation] = useState<IndexConsistencyResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const runValidation = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/validation/index-consistency`);
      const data = await response.json();
      setValidation(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Index Consistency Validation</h1>
        <button onClick={runValidation} disabled={loading}>
          {loading ? 'Validating...' : 'Run Validation'}
        </button>
      </div>

      {validation && (
        <div className="space-y-4">
          {/* Overall Status */}
          <div className={`p-4 rounded-lg ${validation.overall_consistent ? 'bg-green-50' : 'bg-red-50'}`}>
            <h2 className="font-semibold">
              {validation.overall_consistent ? '✅ Indexes Consistent' : '❌ Consistency Issues Found'}
            </h2>
          </div>

          {/* Counts */}
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-white rounded-lg shadow">
              <h3 className="text-sm text-gray-500">Qdrant Chunks</h3>
              <p className="text-2xl font-bold">{validation.qdrant_count.toLocaleString()}</p>
            </div>
            <div className="p-4 bg-white rounded-lg shadow">
              <h3 className="text-sm text-gray-500">BM25 Corpus</h3>
              <p className="text-2xl font-bold">{validation.bm25_count.toLocaleString()}</p>
            </div>
            <div className="p-4 bg-white rounded-lg shadow">
              <h3 className="text-sm text-gray-500">Neo4j Chunks</h3>
              <p className="text-2xl font-bold">{validation.neo4j_count.toLocaleString()}</p>
            </div>
          </div>

          {/* Issues */}
          {!validation.provenance_consistent && (
            <div className="p-4 bg-yellow-50 rounded-lg">
              <h3 className="font-semibold">⚠️ Missing Provenance</h3>
              <p>{validation.missing_provenance} entities without source_chunk_id</p>
            </div>
          )}

          {validation.orphaned_chunks > 0 && (
            <div className="p-4 bg-blue-50 rounded-lg">
              <h3 className="font-semibold">ℹ️ Orphaned Chunks</h3>
              <p>{validation.orphaned_chunks} chunks with no extracted entities</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

**Acceptance Criteria:**
- ✅ Admin endpoint validates consistency across all 3 indexes
- ✅ Visual dashboard shows consistency status
- ✅ Identifies specific inconsistencies (missing provenance, orphaned chunks)
- ✅ Namespace-specific validation
- ✅ Tolerance thresholds for timing differences

**Files to Create:**
- `frontend/src/pages/admin/IndexValidationPage.tsx` (validation UI)

**Files to Modify:**
- `src/api/v1/admin.py` (validation endpoint)
- `src/models/admin.py` (response models)
- `frontend/src/api/admin.ts` (API function)

**Related TD:** TD-048 (Graph Extraction with Unified Chunks) - RESOLVED by this feature

---

### Feature 49.7: Automated Relation Deduplication (13 SP)

**Problem (TD-063):**
- Duplicate relationships in knowledge graph
- Synonym relationship types not merged (`STARRED_IN` vs `ACTED_IN`)
- Entity name variants not remapped after deduplication
- Bidirectional symmetric relationships duplicated

**Solution:**
Multi-criteria relation deduplicator similar to entity deduplication (TD-062).

**Implementation:**

#### Step 1: Relation Deduplicator Class
```python
# src/components/graph_rag/relation_deduplicator.py

class RelationDeduplicator:
    """Multi-criteria relation deduplication.

    Deduplication criteria:
    1. Type synonyms: STARRED_IN = ACTED_IN = PLAYED_IN
    2. Entity remapping: After entity dedup, update relation endpoints
    3. Bidirectional symmetric: KNOWS is symmetric, deduplicate
    4. Confidence-based: Keep highest confidence relation
    """

    def __init__(self, synonym_map: dict[str, str] | None = None):
        """Initialize relation deduplicator.

        Args:
            synonym_map: Mapping of relation types to canonical form
                Example: {"ACTED_IN": "STARRED_IN", "PLAYED_IN": "STARRED_IN"}
        """
        self.synonym_map = synonym_map or self._default_synonym_map()
        self.symmetric_types = {"KNOWS", "RELATED_TO", "CO_OCCURS", "SIMILAR_TO"}

    def _default_synonym_map(self) -> dict[str, str]:
        """Default relationship type synonyms."""
        return {
            # Acting
            "ACTED_IN": "STARRED_IN",
            "PLAYED_IN": "STARRED_IN",
            "PERFORMED_IN": "STARRED_IN",
            # Location
            "LOCATED_IN": "BASED_IN",
            "RESIDES_IN": "BASED_IN",
            # Employment
            "EMPLOYED_BY": "WORKS_FOR",
            "WORKS_AT": "WORKS_FOR",
            # Ownership
            "OWNS": "OWNS",
            "POSSESSES": "OWNS",
        }

    def deduplicate(
        self,
        relations: list[dict],
        entity_id_map: dict[str, str] | None = None
    ) -> list[dict]:
        """Deduplicate relations using multi-criteria approach.

        Args:
            relations: List of relation dicts with source, target, type, weight
            entity_id_map: Entity dedup mapping (old_id -> canonical_id)

        Returns:
            Deduplicated relation list
        """
        # Step 1: Normalize relation types using synonym map
        normalized_relations = []
        for rel in relations:
            normalized_type = self.synonym_map.get(
                rel["relationship_type"].upper(),
                rel["relationship_type"]
            )

            normalized_relations.append({
                **rel,
                "relationship_type": normalized_type,
                "original_type": rel["relationship_type"]
            })

        # Step 2: Remap entity IDs after entity deduplication
        if entity_id_map:
            for rel in normalized_relations:
                rel["source"] = entity_id_map.get(rel["source"], rel["source"])
                rel["target"] = entity_id_map.get(rel["target"], rel["target"])

        # Step 3: Deduplicate by (source, target, type) key
        deduplicated = {}
        for rel in normalized_relations:
            # For symmetric relations, use sorted tuple to avoid duplicates
            if rel["relationship_type"] in self.symmetric_types:
                key = tuple(sorted([rel["source"], rel["target"]])) + (rel["relationship_type"],)
            else:
                key = (rel["source"], rel["target"], rel["relationship_type"])

            # Keep relation with highest weight/confidence
            if key not in deduplicated or rel.get("weight", 0) > deduplicated[key].get("weight", 0):
                deduplicated[key] = rel

        return list(deduplicated.values())
```

#### Step 2: Integration in Extraction Pipeline
```python
# src/components/graph_rag/parallel_extractor.py

from src.components.graph_rag.relation_deduplicator import RelationDeduplicator

class ParallelExtractor:
    def __init__(self):
        self.entity_deduplicator = MultiCriteriaDeduplicator()
        self.relation_deduplicator = RelationDeduplicator()  # NEW

    async def extract_parallel(self, chunk_text: str, chunk_id: str):
        # ... existing entity extraction ...

        # Deduplicate entities
        deduplicated_entities, entity_id_map = self.entity_deduplicator.deduplicate(all_entities)

        # Deduplicate relations with entity remapping
        deduplicated_relations = self.relation_deduplicator.deduplicate(
            all_relationships,
            entity_id_map=entity_id_map
        )

        return deduplicated_entities, deduplicated_relations
```

#### Step 3: Migration Script for Existing Data
```python
# scripts/migrate_deduplicate_relations.py

async def migrate_deduplicate_relations():
    """Deduplicate existing relations in Neo4j."""
    neo4j_client = get_neo4j_client()
    deduplicator = RelationDeduplicator()

    # Fetch all relations
    query = """
    MATCH (source:base)-[r:RELATES_TO]->(target:base)
    RETURN source.entity_id as source, target.entity_id as target,
           type(r) as relationship_type, r.weight as weight,
           id(r) as rel_id
    """
    relations = neo4j_client.query(query)

    # Deduplicate
    logger.info(f"Deduplicating {len(relations)} relations...")
    deduplicated = deduplicator.deduplicate(relations)

    # Delete duplicates
    relations_to_keep = {r["rel_id"] for r in deduplicated}
    delete_query = """
    MATCH ()-[r:RELATES_TO]->()
    WHERE NOT id(r) IN $keep_ids
    DELETE r
    """
    result = neo4j_client.execute(delete_query, {"keep_ids": list(relations_to_keep)})

    logger.info(f"Migration complete: Removed {len(relations) - len(deduplicated)} duplicate relations")
```

**Acceptance Criteria:**
- ✅ Synonym relation types merged (ACTED_IN → STARRED_IN)
- ✅ Entity name variants remapped in relations
- ✅ Bidirectional symmetric relations deduplicated
- ✅ Highest confidence relation kept when duplicates found
- ✅ Migration script cleans existing graph
- ✅ Unit tests for all deduplication criteria

**Files to Create:**
- `src/components/graph_rag/relation_deduplicator.py` (deduplicator class)
- `scripts/migrate_deduplicate_relations.py` (migration script)
- `tests/unit/test_relation_deduplicator.py` (unit tests)

**Files to Modify:**
- `src/components/graph_rag/parallel_extractor.py` (integration)
- `src/components/graph_rag/lightrag_wrapper.py` (integration)

**Related TD:** TD-063 (Relation Deduplication) - RESOLVED by this feature

---

### Feature 49.8: Relationship Type Synonym Mapping (8 SP)

**Problem (TD-063):**
- Hardcoded synonym mappings in deduplicator
- No admin UI to configure synonyms
- Cannot adapt to new relationship types
- No way to fix LLM extraction inconsistencies without code changes

**Solution:**
Configurable synonym mappings with admin UI for editing.

**Implementation:**

#### Step 1: Backend Configuration Management
```python
# src/core/relationship_synonyms.py

class RelationshipSynonymConfig:
    """Manage relationship type synonym mappings.

    Stored in Redis for easy updates without code changes.
    """

    def __init__(self):
        self.redis_key = "config:relationship_synonyms"
        self.redis_client = get_redis_client()

    async def get_synonym_map(self) -> dict[str, str]:
        """Get current synonym mappings from Redis."""
        data = await self.redis_client.get(self.redis_key)
        if not data:
            return self._default_synonyms()
        return json.loads(data)

    async def update_synonym_map(self, synonym_map: dict[str, str]) -> None:
        """Update synonym mappings in Redis."""
        await self.redis_client.set(
            self.redis_key,
            json.dumps(synonym_map),
            ex=None  # No expiration
        )
        logger.info("relationship_synonyms_updated", count=len(synonym_map))

    def _default_synonyms(self) -> dict[str, str]:
        """Default synonym mappings."""
        return {
            "ACTED_IN": "STARRED_IN",
            "PLAYED_IN": "STARRED_IN",
            "PERFORMED_IN": "STARRED_IN",
            "LOCATED_IN": "BASED_IN",
            "RESIDES_IN": "BASED_IN",
            "EMPLOYED_BY": "WORKS_FOR",
            "WORKS_AT": "WORKS_FOR",
            "POSSESSES": "OWNS",
        }

# src/api/v1/admin.py

@router.get("/graph/relationship-synonyms", response_model=RelationshipSynonymsResponse)
async def get_relationship_synonyms():
    """Get current relationship type synonym mappings."""
    config = RelationshipSynonymConfig()
    synonym_map = await config.get_synonym_map()

    return RelationshipSynonymsResponse(
        synonyms=synonym_map,
        total_mappings=len(synonym_map)
    )

@router.put("/graph/relationship-synonyms", response_model=RelationshipSynonymsResponse)
async def update_relationship_synonyms(request: UpdateRelationshipSynonymsRequest):
    """Update relationship type synonym mappings."""
    config = RelationshipSynonymConfig()
    await config.update_synonym_map(request.synonyms)

    return RelationshipSynonymsResponse(
        synonyms=request.synonyms,
        total_mappings=len(request.synonyms)
    )
```

#### Step 2: Admin UI for Synonym Configuration
```tsx
// frontend/src/pages/admin/RelationshipSynonymsPage.tsx

export function RelationshipSynonymsPage() {
  const [synonyms, setSynonyms] = useState<Record<string, string>>({});
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    fetchSynonyms();
  }, []);

  const fetchSynonyms = async () => {
    const response = await fetch(`${API_BASE_URL}/api/v1/admin/graph/relationship-synonyms`);
    const data = await response.json();
    setSynonyms(data.synonyms);
  };

  const saveSynonyms = async () => {
    await fetch(`${API_BASE_URL}/api/v1/admin/graph/relationship-synonyms`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ synonyms })
    });
    setEditing(false);
  };

  const addSynonym = () => {
    setSynonyms(prev => ({ ...prev, '': '' }));
  };

  const removeSynonym = (key: string) => {
    const { [key]: _, ...rest } = synonyms;
    setSynonyms(rest);
  };

  const updateSynonym = (oldKey: string, newKey: string, newValue: string) => {
    const { [oldKey]: _, ...rest } = synonyms;
    setSynonyms({ ...rest, [newKey]: newValue });
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Relationship Type Synonyms</h1>
        <div className="flex gap-2">
          {editing ? (
            <>
              <button onClick={saveSynonyms} className="btn-primary">Save</button>
              <button onClick={() => setEditing(false)} className="btn-secondary">Cancel</button>
            </>
          ) : (
            <button onClick={() => setEditing(true)} className="btn-primary">Edit</button>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <table className="w-full">
          <thead>
            <tr className="text-left border-b">
              <th className="pb-2">Synonym Type</th>
              <th className="pb-2">→</th>
              <th className="pb-2">Canonical Type</th>
              {editing && <th className="pb-2">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {Object.entries(synonyms).map(([key, value]) => (
              <tr key={key} className="border-b">
                <td className="py-2">
                  {editing ? (
                    <input
                      value={key}
                      onChange={(e) => updateSynonym(key, e.target.value, value)}
                      className="border rounded px-2 py-1 w-full"
                    />
                  ) : (
                    <code className="bg-gray-100 px-2 py-1 rounded">{key}</code>
                  )}
                </td>
                <td className="py-2 text-gray-400">→</td>
                <td className="py-2">
                  {editing ? (
                    <input
                      value={value}
                      onChange={(e) => updateSynonym(key, key, e.target.value)}
                      className="border rounded px-2 py-1 w-full"
                    />
                  ) : (
                    <code className="bg-blue-100 px-2 py-1 rounded font-semibold">{value}</code>
                  )}
                </td>
                {editing && (
                  <td className="py-2">
                    <button
                      onClick={() => removeSynonym(key)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Remove
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>

        {editing && (
          <button onClick={addSynonym} className="mt-4 text-primary hover:underline">
            + Add Synonym Mapping
          </button>
        )}
      </div>

      <div className="mt-6 bg-blue-50 p-4 rounded-lg">
        <h3 className="font-semibold mb-2">ℹ️ How Synonyms Work</h3>
        <p className="text-sm text-gray-700">
          When the LLM extracts relationships with variant types (e.g., ACTED_IN, PLAYED_IN),
          they will be automatically merged into the canonical type (STARRED_IN).
          This reduces duplicate relationships and improves graph consistency.
        </p>
      </div>
    </div>
  );
}
```

**Acceptance Criteria:**
- ✅ Admin UI to view/edit synonym mappings
- ✅ Mappings stored in Redis (no code changes needed)
- ✅ Add/Remove synonym mappings dynamically
- ✅ Deduplicator uses live synonym config from Redis
- ✅ Changes apply to new extractions immediately
- ✅ Migration script can re-apply to existing graph

**Files to Create:**
- `src/core/relationship_synonyms.py` (config management)
- `frontend/src/pages/admin/RelationshipSynonymsPage.tsx` (admin UI)

**Files to Modify:**
- `src/components/graph_rag/relation_deduplicator.py` (load from Redis)
- `src/api/v1/admin.py` (synonym endpoints)
- `frontend/src/App.tsx` (add route)

**Related TD:** TD-063 (Relation Deduplication) - RESOLVED by this feature

---

## Technical Debt Resolution

### TD-053: Admin Dashboard Full Implementation (Partial)
**Addressed in Feature 49.1:**
- Dynamic LLM model configuration UI
- No more hardcoded model lists
- Foundation for A/B testing and performance comparison

**Remaining:**
- User & Permission Management (Future Sprint)
- Budget limits per provider (Future Sprint)
- System configuration UI (Future Sprint)

### TD-046: RELATES_TO Relationship Extraction (Preparatory)
**Addressed in Feature 49.2:**
- UI foundation for filtering relationship types
- Supports future `RELATES_TO` relationships
- Dynamic discovery of all relationship types

**Remaining:**
- LLM extraction of Entity-Entity relationships (Backend work)
- Weight and description properties (Backend work)

### TD-048: Graph Extraction with Unified Chunks (Preparatory)
**Addressed in Feature 49.2:**
- Admin visibility into relationship types
- Helps debug extraction issues
- Foundation for provenance tracking

**Remaining:**
- `source_chunk_id` property on relationships (Backend work)
- Consistency validation (Backend work)

### TD-063: Relation Deduplication (Preparatory)
**Addressed in Feature 49.2:**
- Visibility into duplicate relationships
- Count display helps identify deduplication issues
- Admin can manually verify relationship quality

**Remaining:**
- Automated relation deduplication (Backend work)
- Synonym mapping for relationship types (Backend work)

---

## Story Point Breakdown

| Feature | SP | Complexity |
|---------|----|----|
| 49.1: Dynamic LLM Selection | 8 SP | Backend API (3) + Frontend Integration (3) + Testing (2) |
| 49.2: Relationship Type Multiselect | 8 SP | Backend Query (3) + Frontend Multiselect (3) + Graph Integration (2) |
| 49.3: Historical Phase Events Display | 13 SP | Backend Extension (4) + Frontend Components (5) + Testing (4) |
| **Total** | **39 SP** | |

---

## Implementation Order

### Phase 1: Backend APIs (1 day)
1. ✅ Feature 49.1 Backend: `/admin/ollama/models` endpoint
2. ✅ Feature 49.2 Backend: `/admin/graph/relationship-types` endpoint
3. ✅ Feature 49.3 Backend: Extend `/history/{session_id}` with phase events

### Phase 2: Frontend Components (2 days)
4. ✅ Feature 49.1 Frontend: Dynamic model loading in AdminLLMConfigPage
5. ✅ Feature 49.2 Frontend: Multiselect in GraphFilters component
6. ✅ Feature 49.3 Frontend: PhaseEventCard + MessageBubble reasoning toggle

### Phase 3: Integration & Testing (1 day)
7. ✅ E2E tests for all three features
8. ✅ Manual testing in Playwright
9. ✅ Documentation updates

---

## Testing Strategy

### Feature 49.1: Dynamic LLM Selection
```python
# tests/integration/test_admin_ollama_models.py

async def test_list_ollama_models():
    """Test Ollama model listing endpoint."""
    response = await client.get("/api/v1/admin/ollama/models")
    assert response.status_code == 200

    data = response.json()
    assert "text_models" in data
    assert "vision_models" in data

    # Verify no embedding models
    all_models = data["text_models"] + data["vision_models"]
    for model in all_models:
        assert "embed" not in model["name"].lower()
        assert "nomic" not in model["name"].lower()
```

### Feature 49.2: Relationship Types
```python
# tests/integration/test_admin_graph_relationship_types.py

async def test_get_relationship_types():
    """Test relationship types endpoint."""
    response = await client.get("/api/v1/admin/graph/relationship-types")
    assert response.status_code == 200

    data = response.json()
    assert "relationship_types" in data
    assert len(data["relationship_types"]) > 0

    # Verify sorted by count
    counts = [rt["count"] for rt in data["relationship_types"]]
    assert counts == sorted(counts, reverse=True)
```

### Feature 49.3: Historical Phase Events
```typescript
// tests/e2e/phase-events-history.spec.ts

test('should display phase events for historical conversations', async ({ page }) => {
  await page.goto('http://localhost:5179');
  await page.fill('[data-testid="username-input"]', 'admin');
  await page.fill('[data-testid="password-input"]', 'admin123');
  await page.click('[data-testid="login-button"]');

  // Click on a conversation
  await page.click('[data-testid="session-item"]');

  // Wait for conversation to load
  await page.waitForSelector('[data-testid="message-bubble"]');

  // Click "Reasoning anzeigen" on assistant message
  await page.click('text=Reasoning anzeigen');

  // Verify phase events displayed
  await expect(page.locator('[data-testid="phase-event-card"]')).toBeVisible();
  await expect(page.locator('text=intent_classification')).toBeVisible();
});
```

---

## Dependencies

### External Dependencies
- **Ollama API**: `/api/tags` endpoint for model listing
- **Neo4j**: Cypher query for relationship types
- **Redis**: Phase events storage from Sprint 48

### Internal Dependencies
- Sprint 48 Phase Events infrastructure
- Sprint 36 AdminLLMConfigPage foundation
- Sprint 29 GraphAnalyticsPage foundation

---

## Risks & Mitigation

### Risk 1: Ollama API Connectivity
**Impact:** Medium
**Mitigation:**
- Fallback to cached model list in localStorage
- Clear error message for users
- Retry logic with exponential backoff

### Risk 2: Large Number of Relationship Types
**Impact:** Low
**Mitigation:**
- Pagination/virtualization for >100 types
- Search/filter input for quick discovery
- Group by category (e.g., "Entity-Entity", "Entity-Chunk")

### Risk 3: Phase Events Missing for Old Conversations
**Impact:** Low
**Mitigation:**
- Graceful handling with "No phase events available" message
- Only show "Reasoning anzeigen" for conversations after Sprint 48
- Document breaking change in release notes

---

## Success Metrics

### Feature 49.1: Dynamic LLM Selection
- ✅ Admin can see all available Ollama models without code changes
- ✅ New models pulled to Ollama appear within 5 seconds
- ✅ No embedding models in the dropdown

### Feature 49.2: Relationship Types
- ✅ All Neo4j relationship types displayed
- ✅ Graph updates <1s after filter change
- ✅ Relationship counts accurate

### Feature 49.3: Phase Events
- ✅ Phase events viewable for all post-Sprint 48 conversations
- ✅ Phase event loading <500ms
- ✅ No performance degradation on conversation history page

---

## Documentation Updates

### User-Facing Documentation
1. **Admin Guide**: How to configure LLM models dynamically
2. **Admin Guide**: How to filter graph by relationship types
3. **User Guide**: How to view reasoning history for past conversations

### Developer Documentation
1. **API Docs**: Document new admin endpoints
2. **Architecture**: Update with phase events history flow
3. **Testing Guide**: E2E test examples for all three features

---

## Future Enhancements

### Feature 49.1 Extensions
- Model performance comparison dashboard
- A/B testing configuration UI
- Budget limits per model
- Model download/pull from UI

### Feature 49.2 Extensions
- Relationship type editing (rename, merge)
- Relationship type statistics (weight distribution)
- Export relationship type taxonomy

### Feature 49.3 Extensions
- Phase event timeline visualization
- Comparative reasoning analysis (compare two queries)
- Export phase events as JSON
- Search across all phase events

---

## Sprint Completion Criteria

- ✅ All 3 features implemented and tested
- ✅ No regression in existing functionality
- ✅ E2E tests passing for all features
- ✅ Documentation updated
- ✅ Code review completed
- ✅ Deployed to staging environment
- ✅ User acceptance testing completed

---

## Related Documents

- [Sprint 48 Findings](./SPRINT_48_FINDINGS.md) - Phase Events implementation
- [Sprint 36](./SPRINT_36.md) - Original LLM Config implementation
- [Sprint 29](./SPRINT_29.md) - Original Graph Analytics implementation
- [TD-053](../technical-debt/TD-053_ADMIN_DASHBOARD_FULL.md) - Admin Dashboard TD
- [TD-046](../technical-debt/TD-046_RELATES_TO_RELATIONSHIP_EXTRACTION.md) - RELATES_TO TD
- [TD-048](../technical-debt/TD-048_GRAPH_EXTRACTION_UNIFIED_CHUNKS.md) - Graph Extraction TD
- [TD-063](../technical-debt/TD-063_RELATION_DEDUPLICATION.md) - Relation Deduplication TD
