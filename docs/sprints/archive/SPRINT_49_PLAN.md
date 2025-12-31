# Sprint 49: Dynamic UX & Knowledge Graph Deduplication

**Sprint Duration:** 2 Weeks
**Total Story Points:** 79 SP
**Focus:** Dynamic model selection, semantic deduplication via embeddings, provenance tracking

---

## Feature Summary

| Feature | SP | Description |
|---------|-----|-------------|
| 49.1 | 8 | Dynamic LLM Selection from Ollama |
| 49.2 | 8 | Graph Relationship Type Multiselect |
| 49.3 | 13 | Historical Phase Events Display |
| 49.4 | 3 | Indexing Progress Fix |
| 49.5 | 13 | Add source_chunk_id to Relationships |
| 49.6 | 8 | Index Consistency Validation |
| 49.7 | 13 | Semantic Relation Deduplication (Embedding-Based) |
| 49.8 | 5 | Redis-based Manual Synonym Overrides |
| 49.9 | 8 | Migrate Entity Deduplication to BGE-M3 |
| **Total** | **79** | |

---

## Sprint Goal

Enable intelligent knowledge graph deduplication using BGE-M3 embeddings, eliminate redundant dependencies, and provide users with dynamic model selection and transparent reasoning history. Replace all hardcoded synonym mappings with embedding-based semantic clustering, allowing automatic detection of similar relationship types.

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
- New Ollama models appear automatically in dropdown
- Embedding models are excluded
- Vision models are correctly identified
- Error handling for Ollama connectivity issues
- Loading state while fetching models

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
- All relationship types from Neo4j displayed in multiselect
- Show count for each relationship type
- Graph updates when relationship type filter changes
- "Select All" / "Deselect All" buttons
- Relationship types sorted by count (descending)

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
- "Reasoning anzeigen" button on assistant messages
- Phase events loaded on-demand (lazy loading)
- Phase events displayed with icons, duration, metadata
- Graceful handling for pre-Sprint 48 conversations (no phase events)
- Collapsible panel (default: closed)
- Visual distinction between phase types (colors, icons)

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
- No negative document counts ever shown
- "Failed" status when all documents fail (not "Successfully")
- "Partially completed" when some succeed, some fail
- Clear visual distinction (colors, icons) for success/warning/error
- Consistent messaging across all SSE events

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
- All new `MENTIONED_IN` relationships have `source_chunk_id`
- Migration script updates existing relationships
- Validation endpoint confirms 100% provenance coverage
- Entity extraction includes chunk_id parameter
- Admin UI shows provenance validation status

**Files to Create:**
- `scripts/migrate_add_chunk_provenance.py` (migration script)

**Files to Modify:**
- `src/components/graph_rag/lightrag_wrapper.py` (entity insertion)
- `src/components/graph_rag/parallel_extractor.py` (pass chunk_id)
- `src/api/v1/admin.py` (validation endpoint)
- `frontend/src/pages/admin/GraphAnalyticsPage.tsx` (display validation)

**Related TD:** TD-048 (Graph Extraction with Unified Chunks) - RESOLVED

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
              {validation.overall_consistent ? 'Indexes Consistent' : 'Consistency Issues Found'}
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
              <h3 className="font-semibold">Missing Provenance</h3>
              <p>{validation.missing_provenance} entities without source_chunk_id</p>
            </div>
          )}

          {validation.orphaned_chunks > 0 && (
            <div className="p-4 bg-blue-50 rounded-lg">
              <h3 className="font-semibold">Orphaned Chunks</h3>
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
- Admin endpoint validates consistency across all 3 indexes
- Visual dashboard shows consistency status
- Identifies specific inconsistencies (missing provenance, orphaned chunks)
- Namespace-specific validation
- Tolerance thresholds for timing differences

**Files to Create:**
- `frontend/src/pages/admin/IndexValidationPage.tsx` (validation UI)

**Files to Modify:**
- `src/api/v1/admin.py` (validation endpoint)
- `src/models/admin.py` (response models)
- `frontend/src/api/admin.ts` (API function)

**Related TD:** TD-048 (Graph Extraction with Unified Chunks) - RESOLVED

---

### Feature 49.7: Semantic Relation Deduplication (13 SP)

**Problem (TD-063):**
- Duplicate relationships in knowledge graph
- Synonym relationship types not merged (STARRED_IN vs ACTED_IN)
- Entity name variants not remapped after deduplication
- Bidirectional symmetric relationships duplicated
- Hardcoded synonym lists not extensible

**Solution:**
Replace hardcoded synonym mappings with embedding-based semantic clustering using BGE-M3. Automatically detect similar relationship types via cosine similarity.

**Implementation:**

#### Step 1: Semantic Relation Deduplicator Class
```python
# src/components/graph_rag/semantic_relation_deduplicator.py

from scipy.spatial.distance import cosine
from src.components.vector_search.embeddings import get_bgem3_embedder

class SemanticRelationDeduplicator:
    """Relation deduplication via BGE-M3 embeddings and hierarchical clustering.

    Instead of hardcoded synonym maps, uses semantic similarity to detect
    and merge related relationship types automatically.
    """

    def __init__(self, similarity_threshold: float = 0.88):
        """Initialize semantic deduplicator.

        Args:
            similarity_threshold: Cosine similarity threshold for clustering (0-1)
                Default 0.88 = very high similarity required
        """
        self.embedder = get_bgem3_embedder()
        self.similarity_threshold = similarity_threshold
        self.symmetric_types = {"KNOWS", "RELATED_TO", "CO_OCCURS", "SIMILAR_TO"}
        self.redis_client = get_redis_client()
        self.cache_key = "semantic_relation_clusters"

    async def deduplicate(
        self,
        relations: list[dict],
        entity_id_map: dict[str, str] | None = None,
        use_cache: bool = True,
    ) -> list[dict]:
        """Deduplicate relations using semantic similarity clustering.

        Args:
            relations: List of relation dicts with source, target, type, weight
            entity_id_map: Entity dedup mapping (old_id -> canonical_id)
            use_cache: Use cached clusters to improve performance

        Returns:
            Deduplicated relation list with canonical relation types
        """
        # Step 1: Extract unique relation types
        unique_types = list(set(r["relationship_type"].upper() for r in relations))

        # Step 2: Get or compute semantic clusters
        clusters = await self._get_type_clusters(unique_types, use_cache)

        # Step 3: Normalize relation types using clusters
        normalized_relations = []
        for rel in relations:
            rel_type = rel["relationship_type"].upper()
            canonical_type = clusters.get(rel_type, rel_type)

            normalized_relations.append({
                **rel,
                "relationship_type": canonical_type,
                "original_type": rel["relationship_type"]
            })

        # Step 4: Remap entity IDs after entity deduplication
        if entity_id_map:
            for rel in normalized_relations:
                rel["source"] = entity_id_map.get(rel["source"], rel["source"])
                rel["target"] = entity_id_map.get(rel["target"], rel["target"])

        # Step 5: Deduplicate by (source, target, type) key
        deduplicated = {}
        for rel in normalized_relations:
            # For symmetric relations, use sorted tuple
            if rel["relationship_type"] in self.symmetric_types:
                key = tuple(sorted([rel["source"], rel["target"]])) + (rel["relationship_type"],)
            else:
                key = (rel["source"], rel["target"], rel["relationship_type"])

            # Keep relation with highest weight/confidence
            if key not in deduplicated or rel.get("weight", 0) > deduplicated[key].get("weight", 0):
                deduplicated[key] = rel

        return list(deduplicated.values())

    async def _get_type_clusters(
        self,
        unique_types: list[str],
        use_cache: bool = True,
    ) -> dict[str, str]:
        """Get or compute semantic clusters for relation types.

        Returns:
            Mapping of relation_type -> canonical_type
        """
        # Try Redis cache first
        if use_cache:
            cached = await self.redis_client.get(self.cache_key)
            if cached:
                return json.loads(cached)

        # Compute clusters
        logger.info(f"Computing semantic clusters for {len(unique_types)} relation types")

        # Get embeddings for all types
        embeddings = {}
        for rel_type in unique_types:
            try:
                # Format: "WORKS_AT" -> "works at" for better embeddings
                text = rel_type.replace("_", " ").lower()
                emb = await self.embedder.embed_text(text)
                embeddings[rel_type] = emb
            except Exception as e:
                logger.warning(f"Failed to embed {rel_type}: {e}")
                embeddings[rel_type] = None

        # Hierarchical clustering
        clusters = self._hierarchical_cluster(embeddings)

        # Cache for 7 days
        await self.redis_client.set(
            self.cache_key,
            json.dumps(clusters),
            ex=7 * 24 * 3600
        )

        return clusters

    def _hierarchical_cluster(
        self,
        embeddings: dict[str, list[float] | None]
    ) -> dict[str, str]:
        """Perform hierarchical clustering on embeddings.

        Returns:
            Mapping of all types to their canonical representative
        """
        # Filter out None embeddings
        valid_embeddings = {
            t: e for t, e in embeddings.items() if e is not None
        }

        if not valid_embeddings:
            return {t: t for t in embeddings.keys()}

        # Single-linkage clustering
        clusters: dict[str, str] = {}  # type -> canonical
        canonical_types = list(valid_embeddings.keys())

        for rel_type in embeddings.keys():
            if rel_type in clusters:
                continue  # Already assigned

            if rel_type not in valid_embeddings:
                clusters[rel_type] = rel_type
                continue

            # Find similar types
            rel_embedding = valid_embeddings[rel_type]
            similar = [rel_type]  # Start with itself

            for other_type, other_embedding in valid_embeddings.items():
                if other_type == rel_type or other_type in clusters:
                    continue

                # Compute cosine similarity
                similarity = 1 - cosine(rel_embedding, other_embedding)

                if similarity >= self.similarity_threshold:
                    similar.append(other_type)

            # Use first type (alphabetically) as canonical
            canonical = min(similar)
            for t in similar:
                clusters[t] = canonical

        return clusters
```

#### Step 2: Integration in Extraction Pipeline
```python
# src/components/graph_rag/parallel_extractor.py

from src.components.graph_rag.semantic_relation_deduplicator import SemanticRelationDeduplicator

class ParallelExtractor:
    def __init__(self):
        self.entity_deduplicator = MultiCriteriaDeduplicator()
        self.relation_deduplicator = SemanticRelationDeduplicator()  # NEW

    async def extract_parallel(self, chunk_text: str, chunk_id: str):
        # ... existing entity extraction ...

        # Deduplicate entities
        deduplicated_entities, entity_id_map = self.entity_deduplicator.deduplicate(all_entities)

        # Deduplicate relations with semantic clustering
        deduplicated_relations = await self.relation_deduplicator.deduplicate(
            all_relationships,
            entity_id_map=entity_id_map
        )

        return deduplicated_entities, deduplicated_relations
```

#### Step 3: Configuration in Redis
```python
# src/core/semantic_clustering_config.py

class SemanticClusteringConfig:
    """Configuration for semantic relation clustering."""

    def __init__(self):
        self.redis_client = get_redis_client()
        self.config_key = "config:semantic_clustering"

    async def get_threshold(self) -> float:
        """Get current similarity threshold from Redis."""
        data = await self.redis_client.get(self.config_key)
        if not data:
            return 0.88  # Default
        config = json.loads(data)
        return config.get("threshold", 0.88)

    async def update_threshold(self, threshold: float) -> None:
        """Update similarity threshold."""
        config = {"threshold": threshold}
        await self.redis_client.set(self.config_key, json.dumps(config))
        logger.info(f"semantic_clustering_threshold_updated: {threshold}")

    async def clear_cluster_cache(self) -> None:
        """Clear cached clusters to force recomputation."""
        await self.redis_client.delete("semantic_relation_clusters")
        logger.info("semantic_relation_clusters_cache_cleared")
```

**Acceptance Criteria:**
- Synonym relation types merged via embeddings (ACTED_IN -> STARRED_IN)
- Entity name variants remapped in relations
- Bidirectional symmetric relations deduplicated
- Highest confidence relation kept when duplicates found
- Redis caching for cluster results (7-day TTL)
- Similarity threshold adjustable via configuration
- Unit tests for clustering algorithm

**Files to Create:**
- `src/components/graph_rag/semantic_relation_deduplicator.py` (deduplicator class)
- `src/core/semantic_clustering_config.py` (configuration management)
- `tests/unit/test_semantic_relation_deduplicator.py` (unit tests)

**Files to Modify:**
- `src/components/graph_rag/parallel_extractor.py` (integration)
- `src/components/graph_rag/lightrag_wrapper.py` (integration)

**Related TD:** TD-063 (Relation Deduplication) - RESOLVED

---

### Feature 49.8: Redis-based Manual Synonym Overrides (5 SP)

**Problem (TD-063):**
- Embedding-based clustering is automatic but may miss some synonyms
- No way for admins to manually override semantic clusters
- Need hybrid approach: embeddings + manual overrides

**Solution:**
Store manual synonym overrides in Redis. Manual overrides take precedence over semantic clustering.

**Implementation:**

#### Step 1: Hybrid Deduplicator with Overrides
```python
# src/components/graph_rag/hybrid_relation_deduplicator.py

class HybridRelationDeduplicator:
    """Hybrid relation deduplication combining semantic clustering + manual overrides.

    Priority:
    1. Manual overrides (highest priority)
    2. Semantic clustering (BGE-M3 embeddings)
    3. Original type (lowest priority)
    """

    def __init__(self, similarity_threshold: float = 0.88):
        self.semantic_deduplicator = SemanticRelationDeduplicator(similarity_threshold)
        self.redis_client = get_redis_client()
        self.overrides_key = "relation_synonyms:overrides"

    async def deduplicate(
        self,
        relations: list[dict],
        entity_id_map: dict[str, str] | None = None,
    ) -> list[dict]:
        """Deduplicate with manual overrides taking precedence.

        Args:
            relations: List of relation dicts
            entity_id_map: Entity dedup mapping

        Returns:
            Deduplicated relation list
        """
        # Get manual overrides from Redis
        manual_overrides = await self._get_manual_overrides()

        # Apply manual overrides first
        overridden_relations = []
        for rel in relations:
            rel_type = rel["relationship_type"].upper()
            canonical_type = manual_overrides.get(rel_type, rel_type)
            overridden_relations.append({
                **rel,
                "relationship_type": canonical_type,
                "original_type": rel["relationship_type"]
            })

        # Then apply semantic clustering for non-overridden types
        return await self.semantic_deduplicator.deduplicate(
            overridden_relations,
            entity_id_map=entity_id_map,
            use_cache=True
        )

    async def _get_manual_overrides(self) -> dict[str, str]:
        """Get manual synonym overrides from Redis.

        Returns:
            Mapping of relation_type -> canonical_type
        """
        data = await self.redis_client.get(self.overrides_key)
        if not data:
            return {}
        return json.loads(data)

    async def add_override(self, synonym_type: str, canonical_type: str) -> None:
        """Add manual synonym override.

        Args:
            synonym_type: Type to map (e.g., 'ACTED_IN')
            canonical_type: Target canonical type (e.g., 'STARRED_IN')
        """
        overrides = await self._get_manual_overrides()
        overrides[synonym_type.upper()] = canonical_type.upper()

        await self.redis_client.set(
            self.overrides_key,
            json.dumps(overrides),
            ex=None  # No expiration
        )

        # Clear semantic cache so new overrides apply
        await self.redis_client.delete("semantic_relation_clusters")
        logger.info(f"relation_synonym_override_added: {synonym_type} -> {canonical_type}")

    async def remove_override(self, synonym_type: str) -> None:
        """Remove manual synonym override."""
        overrides = await self._get_manual_overrides()
        overrides.pop(synonym_type.upper(), None)

        await self.redis_client.set(
            self.overrides_key,
            json.dumps(overrides)
        )
        logger.info(f"relation_synonym_override_removed: {synonym_type}")
```

#### Step 2: Admin API Endpoints
```python
# src/api/v1/admin.py

@router.get("/graph/relation-overrides", response_model=RelationOverridesResponse)
async def get_relation_overrides():
    """Get current manual relation synonym overrides."""
    deduplicator = HybridRelationDeduplicator()
    overrides = await deduplicator._get_manual_overrides()

    return RelationOverridesResponse(
        overrides=overrides,
        total_overrides=len(overrides)
    )

@router.post("/graph/relation-overrides", response_model=RelationOverrideResponse)
async def add_relation_override(request: AddRelationOverrideRequest):
    """Add a manual relation synonym override.

    Args:
        request: Contains synonym_type and canonical_type

    Example:
        POST /api/v1/admin/graph/relation-overrides
        {
            "synonym_type": "ACTED_IN",
            "canonical_type": "STARRED_IN"
        }
    """
    deduplicator = HybridRelationDeduplicator()
    await deduplicator.add_override(
        request.synonym_type,
        request.canonical_type
    )

    return RelationOverrideResponse(
        synonym_type=request.synonym_type,
        canonical_type=request.canonical_type,
        status="created"
    )

@router.delete("/graph/relation-overrides/{synonym_type}")
async def delete_relation_override(synonym_type: str):
    """Remove a manual relation synonym override."""
    deduplicator = HybridRelationDeduplicator()
    await deduplicator.remove_override(synonym_type)

    return {"status": "deleted", "synonym_type": synonym_type}
```

#### Step 3: Admin UI for Overrides
```tsx
// frontend/src/pages/admin/RelationOverridesPage.tsx

export function RelationOverridesPage() {
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [adding, setAdding] = useState(false);
  const [newSynonym, setNewSynonym] = useState("");
  const [newCanonical, setNewCanonical] = useState("");

  useEffect(() => {
    fetchOverrides();
  }, []);

  const fetchOverrides = async () => {
    const response = await fetch(`${API_BASE_URL}/api/v1/admin/graph/relation-overrides`);
    const data = await response.json();
    setOverrides(data.overrides);
  };

  const handleAdd = async () => {
    if (!newSynonym || !newCanonical) return;

    await fetch(`${API_BASE_URL}/api/v1/admin/graph/relation-overrides`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        synonym_type: newSynonym,
        canonical_type: newCanonical
      })
    });

    setNewSynonym("");
    setNewCanonical("");
    fetchOverrides();
  };

  const handleDelete = async (synonymType: string) => {
    await fetch(
      `${API_BASE_URL}/api/v1/admin/graph/relation-overrides/${synonymType}`,
      { method: 'DELETE' }
    );
    fetchOverrides();
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Manual Relation Synonym Overrides</h1>

      {/* Add Override */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <h2 className="text-lg font-semibold mb-4">Add Override</h2>
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            placeholder="Synonym type (e.g., ACTED_IN)"
            value={newSynonym}
            onChange={(e) => setNewSynonym(e.target.value.toUpperCase())}
            className="flex-1 border rounded px-3 py-2"
          />
          <input
            type="text"
            placeholder="Canonical type (e.g., STARRED_IN)"
            value={newCanonical}
            onChange={(e) => setNewCanonical(e.target.value.toUpperCase())}
            className="flex-1 border rounded px-3 py-2"
          />
          <button
            onClick={handleAdd}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Add
          </button>
        </div>
      </div>

      {/* Overrides Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold">Synonym Type</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Canonical Type</th>
              <th className="px-4 py-3 text-right text-sm font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(overrides).map(([synonym, canonical]) => (
              <tr key={synonym} className="border-t">
                <td className="px-4 py-3">
                  <code className="bg-gray-100 px-2 py-1 rounded">{synonym}</code>
                </td>
                <td className="px-4 py-3">
                  <code className="bg-blue-100 px-2 py-1 rounded font-semibold">{canonical}</code>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => handleDelete(synonym)}
                    className="text-red-600 hover:text-red-800"
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Info */}
      <div className="mt-6 bg-blue-50 p-4 rounded-lg">
        <h3 className="font-semibold mb-2">How It Works</h3>
        <p className="text-sm text-gray-700">
          Manual overrides take precedence over semantic clustering. When the LLM extracts
          relationships, matching synonym types will be automatically remapped to their
          canonical types. Changes apply immediately to new extractions.
        </p>
      </div>
    </div>
  );
}
```

**Acceptance Criteria:**
- Admin API endpoints for CRUD operations on overrides
- Admin UI to view/edit/delete overrides
- Overrides stored in Redis (no code changes needed)
- Manual overrides take precedence over semantic clustering
- Changes apply immediately to new extractions
- Clear visual distinction in UI (synonym type vs canonical type)

**Files to Create:**
- `src/components/graph_rag/hybrid_relation_deduplicator.py` (hybrid class)
- `frontend/src/pages/admin/RelationOverridesPage.tsx` (admin UI)

**Files to Modify:**
- `src/api/v1/admin.py` (override endpoints)
- `frontend/src/App.tsx` (add route)

**Related TD:** TD-063 (Relation Deduplication) - RESOLVED

---

### Feature 49.9: Migrate Entity Deduplication to BGE-M3 (8 SP)

**Problem:**
- `sentence-transformers` dependency (~2GB) only used for entity deduplication
- Project already includes BGE-M3 model for embeddings (ADR-024)
- Redundant embedding model consuming disk space and memory
- No reason to maintain two separate embedding systems

**Solution:**
Replace `sentence-transformers` with BGE-M3 for entity semantic deduplication. Reuse existing 1024-dim embeddings.

**Implementation:**

#### Step 1: Update Entity Deduplicator
```python
# src/components/graph_rag/semantic_entity_deduplicator.py

from src.components.vector_search.embeddings import get_bgem3_embedder
from scipy.spatial.distance import cosine

class SemanticEntityDeduplicator:
    """Entity deduplication using BGE-M3 embeddings.

    Replaces sentence-transformers with project's existing BGE-M3 model.
    Uses same 0.85 cosine similarity threshold as before.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """Initialize with BGE-M3 embedder.

        Args:
            similarity_threshold: Cosine similarity threshold (0-1)
        """
        self.embedder = get_bgem3_embedder()
        self.similarity_threshold = similarity_threshold
        self.redis_client = get_redis_client()

    async def deduplicate(
        self,
        entities: list[dict],
    ) -> tuple[list[dict], dict[str, str]]:
        """Deduplicate entities based on semantic similarity.

        Args:
            entities: List of entity dicts with entity_id, entity_name, entity_type

        Returns:
            Tuple of (deduplicated_entities, entity_id_mapping)
            entity_id_mapping maps old_id -> canonical_id for relationship remapping
        """
        if not entities:
            return [], {}

        # Group entities by type (compare within type only)
        entities_by_type = {}
        for entity in entities:
            entity_type = entity.get("entity_type", "UNKNOWN")
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)

        # Deduplicate within each type
        deduplicated = []
        entity_id_map = {}

        for entity_type, type_entities in entities_by_type.items():
            type_dedup, type_map = await self._deduplicate_type(type_entities)
            deduplicated.extend(type_dedup)
            entity_id_map.update(type_map)

        return deduplicated, entity_id_map

    async def _deduplicate_type(
        self,
        entities: list[dict],
    ) -> tuple[list[dict], dict[str, str]]:
        """Deduplicate entities of same type."""
        if len(entities) <= 1:
            return entities, {}

        # Get embeddings for all entity names
        embeddings = {}
        for entity in entities:
            try:
                entity_name = entity["entity_name"]
                emb = await self.embedder.embed_text(entity_name)
                embeddings[entity["entity_id"]] = emb
            except Exception as e:
                logger.warning(f"Failed to embed {entity['entity_name']}: {e}")
                embeddings[entity["entity_id"]] = None

        # Clustering: group similar entities
        clusters = self._cluster_entities(entities, embeddings)

        # For each cluster, keep the first entity as canonical
        deduplicated = []
        entity_id_map = {}

        for cluster_ids in clusters.values():
            canonical_id = min(cluster_ids)  # Use alphabetically first
            canonical_entity = next(e for e in entities if e["entity_id"] == canonical_id)

            deduplicated.append(canonical_entity)

            # Map all cluster members to canonical
            for entity_id in cluster_ids:
                entity_id_map[entity_id] = canonical_id

        return deduplicated, entity_id_map

    def _cluster_entities(
        self,
        entities: list[dict],
        embeddings: dict[str, list[float] | None],
    ) -> dict[str, list[str]]:
        """Cluster similar entities using cosine similarity.

        Returns:
            Dict mapping cluster_id -> list of entity_ids
        """
        clusters = {}
        cluster_id = 0

        for i, entity1 in enumerate(entities):
            id1 = entity1["entity_id"]

            # Already in a cluster?
            if any(id1 in c for c in clusters.values()):
                continue

            emb1 = embeddings.get(id1)
            if emb1 is None:
                # No embedding, put in own cluster
                clusters[cluster_id] = [id1]
                cluster_id += 1
                continue

            # Find similar entities
            cluster = [id1]
            for j, entity2 in enumerate(entities[i + 1:], start=i + 1):
                id2 = entity2["entity_id"]

                # Already in a cluster?
                if any(id2 in c for c in clusters.values()):
                    continue

                emb2 = embeddings.get(id2)
                if emb2 is None:
                    continue

                # Compute cosine similarity
                similarity = 1 - cosine(emb1, emb2)

                if similarity >= self.similarity_threshold:
                    cluster.append(id2)

            clusters[cluster_id] = cluster
            cluster_id += 1

        return clusters
```

#### Step 2: Update parallel_extractor.py
```python
# src/components/graph_rag/parallel_extractor.py

from src.components.graph_rag.semantic_entity_deduplicator import SemanticEntityDeduplicator
from src.components.graph_rag.semantic_relation_deduplicator import SemanticRelationDeduplicator

class ParallelExtractor:
    def __init__(self):
        self.entity_deduplicator = SemanticEntityDeduplicator()  # BGE-M3
        self.relation_deduplicator = SemanticRelationDeduplicator()

    async def extract_parallel(self, chunk_text: str, chunk_id: str):
        # ... existing extraction logic ...

        # Deduplicate entities using BGE-M3
        deduplicated_entities, entity_id_map = await self.entity_deduplicator.deduplicate(
            all_entities
        )

        # Deduplicate relations with entity remapping
        deduplicated_relations = await self.relation_deduplicator.deduplicate(
            all_relationships,
            entity_id_map=entity_id_map
        )

        return deduplicated_entities, deduplicated_relations
```

#### Step 3: Remove sentence-transformers Dependency
```bash
# pyproject.toml - Remove this line:
# sentence-transformers = "^2.2.2"

# Update Poetry lock
poetry remove sentence-transformers
poetry lock
```

#### Step 4: Migration Script
```python
# scripts/migrate_entity_dedup_to_bge.py

async def migrate_entity_deduplication():
    """Re-deduplicate existing entities using BGE-M3 instead of sentence-transformers."""
    neo4j_client = get_neo4j_client()
    deduplicator = SemanticEntityDeduplicator()

    # Fetch all entities grouped by type
    query = """
    MATCH (e:base)
    RETURN e.entity_id as entity_id, e.entity_name as entity_name,
           e.entity_type as entity_type, e.description as description
    ORDER BY e.entity_type, e.entity_name
    """

    entities = neo4j_client.query(query)
    entities_by_type = {}

    for entity in entities:
        entity_type = entity["entity_type"]
        if entity_type not in entities_by_type:
            entities_by_type[entity_type] = []
        entities_by_type[entity_type].append(entity)

    # Deduplicate each type
    total_before = len(entities)
    merged_count = 0

    for entity_type, type_entities in entities_by_type.items():
        deduplicated, entity_id_map = await deduplicator._deduplicate_type(type_entities)

        # Find merged entities
        merged_ids = [
            eid for eid, canonical_id in entity_id_map.items()
            if eid != canonical_id
        ]

        if merged_ids:
            logger.info(f"Merging {len(merged_ids)} {entity_type} entities...")
            merged_count += len(merged_ids)

            # Merge relationships to canonical entities
            merge_query = """
            UNWIND $merges as merge_pair
            MATCH (old:base {entity_id: merge_pair.old_id})
            MATCH (canonical:base {entity_id: merge_pair.canonical_id})

            // Merge relationships
            MATCH (old)-[r:RELATES_TO]->(target)
            CREATE (canonical)-[:RELATES_TO]->(target)

            MATCH (source)-[r:RELATES_TO]->(old)
            CREATE (source)-[:RELATES_TO]->(canonical)

            // Delete old entity
            DETACH DELETE old
            """

            merges = [
                {"old_id": old_id, "canonical_id": canonical_id}
                for old_id, canonical_id in entity_id_map.items()
                if old_id != canonical_id
            ]

            if merges:
                await neo4j_client.execute(merge_query, {"merges": merges})

    logger.info(f"Entity dedup migration complete: {total_before} -> {total_before - merged_count}, merged {merged_count}")
```

**Acceptance Criteria:**
- Entity deduplication uses BGE-M3 embeddings (1024-dim)
- Performance same or better than sentence-transformers
- Similarity threshold remains 0.85
- sentence-transformers dependency completely removed
- Migration script re-deduplicates existing entities
- No regression in entity deduplication quality
- Disk space reduced by ~2GB

**Files to Create:**
- `src/components/graph_rag/semantic_entity_deduplicator.py` (new deduplicator)
- `scripts/migrate_entity_dedup_to_bge.py` (migration script)
- `tests/unit/test_semantic_entity_deduplicator.py` (unit tests)

**Files to Modify:**
- `src/components/graph_rag/parallel_extractor.py` (use BGE-M3)
- `pyproject.toml` (remove sentence-transformers)

**Related TD:** TD-059 (Reranking Container) - Indirectly resolved

---

## Technical Debt Resolution

### TD-053: Admin Dashboard Full Implementation
**Addressed in Feature 49.1:**
- Dynamic LLM model configuration UI
- No more hardcoded model lists
- Foundation for A/B testing and performance comparison

**Remaining:**
- User & Permission Management (Future Sprint)
- Budget limits per provider (Future Sprint)
- System configuration UI (Future Sprint)

### TD-048: Graph Extraction with Unified Chunks
**Fully Resolved in Features 49.5 & 49.6:**
- `source_chunk_id` property on all MENTIONED_IN relationships
- Index consistency validation across Qdrant, Neo4j, BM25
- Provenance tracking for all entities

### TD-063: Relation Deduplication
**Fully Resolved in Features 49.7 & 49.8:**
- Embedding-based semantic relation deduplication
- Redis-based manual synonym overrides
- Hybrid approach for maximum flexibility
- Automatic synonym detection via BGE-M3

### TD-059: Reranking Container
**Indirectly Resolved in Feature 49.9:**
- Removing sentence-transformers dependency reduces Docker image size
- Reranking model (bge-reranker-v2-m3) handled via Ollama
- Single embedding model (BGE-M3) for entire system

---

## Story Point Breakdown

| Feature | SP | Complexity |
|---------|----|----|
| 49.1: Dynamic LLM Selection | 8 | Backend API (3) + Frontend Integration (3) + Testing (2) |
| 49.2: Relationship Type Multiselect | 8 | Backend Query (3) + Frontend Multiselect (3) + Graph Integration (2) |
| 49.3: Historical Phase Events Display | 13 | Backend Extension (4) + Frontend Components (5) + Testing (4) |
| 49.4: Indexing Progress Fix | 3 | Frontend Fix (1) + Backend Fix (1) + Testing (1) |
| 49.5: Add source_chunk_id to Relationships | 13 | Entity Extraction (3) + Migration Script (3) + Validation (3) + Testing (4) |
| 49.6: Index Consistency Validation | 8 | Backend Validation (3) + Frontend Dashboard (3) + Testing (2) |
| 49.7: Semantic Relation Deduplication | 13 | BGE-M3 Clustering (4) + Redis Caching (2) + Integration (3) + Testing (4) |
| 49.8: Redis-based Manual Overrides | 5 | Admin API (2) + Admin UI (2) + Testing (1) |
| 49.9: Migrate Entity Dedup to BGE-M3 | 8 | Entity Deduplicator (3) + Dependency Removal (2) + Migration Script (2) + Testing (1) |
| **Total** | **79** | |

---

## Implementation Order

### Phase 1: Dynamic UX Features (Days 1-3)
1. Feature 49.1: Dynamic LLM Selection (backend + frontend)
2. Feature 49.2: Relationship Type Multiselect (backend + frontend)
3. Feature 49.3: Historical Phase Events (backend + frontend)
4. Feature 49.4: Indexing Progress Fix (quick fix)

### Phase 2: Graph Deduplication via Embeddings (Days 4-8)
5. Feature 49.9: Migrate Entity Dedup to BGE-M3 (foundation)
6. Feature 49.7: Semantic Relation Deduplication (clustering)
7. Feature 49.8: Redis-based Manual Overrides (admin UI)

### Phase 3: Provenance & Consistency (Days 9-10)
8. Feature 49.5: Add source_chunk_id to Relationships (extraction)
9. Feature 49.6: Index Consistency Validation (validation)

### Phase 4: Testing & Integration (Days 11-14)
10. Unit tests for all deduplicators
11. Integration tests for all features
12. E2E tests for user-facing features
13. Documentation updates

---

## Success Metrics

### Feature 49.1: Dynamic LLM Selection
- Admin can see all available Ollama models without code changes
- New models pulled to Ollama appear within 5 seconds
- No embedding models in the dropdown

### Feature 49.2: Relationship Types
- All Neo4j relationship types displayed
- Graph updates <1s after filter change
- Relationship counts accurate

### Feature 49.3: Phase Events
- Phase events viewable for all post-Sprint 48 conversations
- Phase event loading <500ms
- No performance degradation on conversation history page

### Feature 49.4: Progress Fix
- No negative document counts ever shown
- Correct status indicator (success/warning/error)
- User feedback is clear and accurate

### Feature 49.5: Provenance Tracking
- 100% of MENTIONED_IN relationships have source_chunk_id
- Validation endpoint confirms consistency
- Migration script completes without errors

### Feature 49.6: Consistency Validation
- Cross-layer consistency validated
- Tolerance thresholds respected (Qdrant-BM25: 1, Qdrant-Neo4j: 5)
- Admin can identify inconsistencies quickly

### Feature 49.7: Semantic Relation Dedup
- Synonym types merged automatically via embeddings
- Redis caching improves performance (7-day TTL)
- No hardcoded synonyms in code

### Feature 49.8: Manual Overrides
- Admin can add/remove overrides in real-time
- Overrides take precedence over semantic clustering
- Changes apply immediately to new extractions

### Feature 49.9: Entity Dedup to BGE-M3
- Entity deduplication works with BGE-M3 embeddings
- Same 0.85 similarity threshold maintained
- Disk space reduced by ~2GB (sentence-transformers removed)

---

## Dependencies

### External Dependencies
- **Ollama API**: `/api/tags` endpoint for model listing
- **Neo4j**: Cypher query for relationship types and consistency checks
- **Qdrant**: Vector store for consistency validation
- **Redis**: For caching semantic clusters and storing overrides
- **BGE-M3**: Already in project for embeddings (ADR-024)

### Internal Dependencies
- Sprint 48 Phase Events infrastructure (for Feature 49.3)
- Sprint 36 AdminLLMConfigPage foundation (for Feature 49.1)
- Sprint 29 GraphAnalyticsPage foundation (for Feature 49.2)
- ADR-024 BGE-M3 embeddings (for Features 49.7, 49.8, 49.9)

---

## Risks & Mitigation

### Risk 1: Embedding Performance for Large Entity Sets
**Impact:** Medium
**Probability:** Low
**Mitigation:**
- Cache embeddings in Redis (24-hour TTL)
- Batch embed requests for better efficiency
- Profile performance with 100k+ entities

### Risk 2: BGE-M3 Semantic Similarity False Positives
**Impact:** Medium
**Probability:** Low
**Mitigation:**
- Conservative threshold (0.88 for relations, 0.85 for entities)
- Manual override UI for false positives
- Admin review dashboard for deduplication results

### Risk 3: Migration Script Compatibility
**Impact:** Medium
**Probability:** Medium
**Mitigation:**
- Test on staging environment first
- Create backup before running
- Validation script confirms 100% success

### Risk 4: Sentence-transformers Removal Breaking Dependencies
**Impact:** Low
**Probability:** Low
**Mitigation:**
- Grep codebase for any remaining dependencies
- Test entire pipeline end-to-end
- Check container image size reduction

---

## Definition of Done

- All 9 features implemented and tested
- Unit tests for deduplication algorithms (>80% coverage)
- Integration tests for provenance tracking
- E2E tests for user-facing features (admin UI, graph filtering)
- Migration scripts tested on staging data
- Code review completed
- Documentation updated (API docs, admin guides)
- Performance validated (BGE-M3 embeddings, Redis caching)
- Disk space reduced by 2GB+ (sentence-transformers removed)
- Deployed to staging environment
- User acceptance testing completed

---

## Related Documents

- [Sprint 48 Plan](./SPRINT_48_PLAN.md) - Phase Events implementation
- [ADR-024](../adr/ADR-024-bge-m3-embeddings.md) - BGE-M3 Embeddings
- [ADR-039](../adr/ADR-039-adaptive-section-aware-chunking.md) - Chunking strategy
- [TD-048](../technical-debt/TD-048_GRAPH_EXTRACTION_UNIFIED_CHUNKS.md) - Graph Extraction
- [TD-063](../technical-debt/TD-063_RELATION_DEDUPLICATION.md) - Relation Deduplication
- [CLAUDE.md](../../CLAUDE.md) - Project context

---

**Created:** 2025-12-16
**Last Updated:** 2025-12-16
**Status:** Ready for Implementation
