# Vector Search Agent Architecture

**Sprint 4 Feature 4.3**
**Date:** 2025-10-15

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LangGraph Orchestration                          │
│                                                                          │
│  ┌──────────┐    ┌─────────────────┐    ┌─────────────────┐           │
│  │  START   │───▶│  Router Node    │───▶│ Vector Search   │──▶ END    │
│  └──────────┘    │  (Feature 4.2)  │    │    Node (4.3)   │           │
│                  └─────────────────┘    └─────────────────┘           │
│                          │                       │                      │
│                          │ intent="hybrid"       │                      │
│                          ▼                       ▼                      │
│                  ┌─────────────────┐    ┌─────────────────┐           │
│                  │  AgentState     │───▶│ VectorSearchAgent│           │
│                  │  - query        │    │  - process()     │           │
│                  │  - intent       │    │  - retry logic   │           │
│                  │  - metadata     │    │  - state update  │           │
│                  └─────────────────┘    └─────────────────┘           │
│                                                  │                      │
└──────────────────────────────────────────────────┼──────────────────────┘
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Existing Components (Sprint 2-3)                      │
│                                                                          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐   │
│  │  HybridSearch   │───▶│ QdrantClient    │    │ EmbeddingService│   │
│  │  - vector_search│    │ - search()      │    │ - embed_text()  │   │
│  │  - keyword_srch │    │ - scroll()      │    └─────────────────┘   │
│  │  - RRF fusion   │    └─────────────────┘                           │
│  │  - reranking    │            │                                      │
│  └─────────────────┘            │                                      │
│          │                      ▼                                      │
│          │              ┌─────────────────┐                           │
│          └─────────────▶│  Qdrant VectorDB│                           │
│                         │  (Docker)       │                           │
│                         └─────────────────┘                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Interaction

### 1. Graph Execution Flow

```
User Query
    │
    ▼
create_initial_state(query, intent)
    │
    ▼
graph.ainvoke(state)
    │
    ├─▶ router_node(state)
    │      │
    │      ├─ Detect intent
    │      └─ Set route_decision
    │
    ├─▶ route_query(state)  [conditional edge]
    │      │
    │      └─ Returns "vector_search"
    │
    ├─▶ vector_search_node(state)
    │      │
    │      ├─ Instantiate VectorSearchAgent
    │      ├─ Call agent.process(state)
    │      │    │
    │      │    ├─ Validate query
    │      │    ├─ Call hybrid_search.hybrid_search()
    │      │    │    │
    │      │    │    ├─ vector_search (Qdrant)
    │      │    │    ├─ keyword_search (BM25)
    │      │    │    ├─ RRF fusion
    │      │    │    └─ rerank (optional)
    │      │    │
    │      │    ├─ Convert to RetrievedContext[]
    │      │    ├─ Calculate latency
    │      │    └─ Update state
    │      │
    │      └─ Return updated state
    │
    └─▶ END
        │
        ▼
    Final State (with results)
```

---

## State Transformation

### Input State

```python
{
    "query": "What is RAG?",
    "intent": "hybrid",
    "messages": [],
    "retrieved_contexts": [],
    "metadata": {
        "timestamp": "2025-10-15T...",
        "agent_path": []
    }
}
```

### After Router Node

```python
{
    "query": "What is RAG?",
    "intent": "hybrid",
    "route_decision": "hybrid",  # ← Added
    "metadata": {
        "agent_path": ["router"]  # ← Updated
    }
}
```

### After Vector Search Node

```python
{
    "query": "What is RAG?",
    "intent": "hybrid",
    "route_decision": "hybrid",
    "retrieved_contexts": [  # ← Populated
        {
            "id": "doc_123",
            "text": "RAG combines retrieval...",
            "score": 0.95,
            "source": "paper.pdf",
            "rank": 1,
            "metadata": {
                "rrf_score": 0.95,
                "rerank_score": 0.97
            }
        },
        # ... more results
    ],
    "metadata": {
        "agent_path": [  # ← Extended
            "router",
            "VectorSearchAgent: started",
            "VectorSearchAgent: completed (5 results, 234ms)"
        ],
        "search": {  # ← Added
            "latency_ms": 234.5,
            "result_count": 5,
            "search_mode": "hybrid",
            "vector_results_count": 10,
            "bm25_results_count": 8,
            "reranking_applied": true
        }
    }
}
```

---

## Class Hierarchy

```
BaseAgent (ABC)
    │
    ├── process(state) -> state  [abstract]
    ├── _add_trace(state, action)
    ├── _measure_latency() -> timing
    ├── _calculate_latency_ms(timing) -> float
    ├── _log_success(operation, **kwargs)
    ├── _log_error(operation, error, **kwargs)
    └── _set_error(state, error, context)
         │
         └── VectorSearchAgent
                 │
                 ├── __init__(hybrid_search, top_k, use_reranking, max_retries)
                 ├── process(state) -> state  [implemented]
                 ├── _search_with_retry(query) -> results  [@retry decorator]
                 └── _convert_results(results) -> RetrievedContext[]
```

---

## Data Models

### RetrievedContext

```python
class RetrievedContext(BaseModel):
    id: str                                    # Document ID
    text: str                                  # Content
    score: float                               # Relevance (0.0-1.0)
    source: str                                # File name
    document_id: str                           # Parent doc
    rank: int                                  # Position
    search_type: Literal["vector", "bm25", "hybrid", "graph"]
    metadata: dict[str, Any]                   # Additional info
        - rrf_score: float                     # RRF score
        - rrf_rank: int                        # RRF rank
        - rerank_score: float (optional)       # Reranking score
        - original_rrf_rank: int (optional)    # Rank before rerank
```

### SearchMetadata

```python
class SearchMetadata(BaseModel):
    latency_ms: float                          # Search duration
    result_count: int                          # Results returned
    search_mode: Literal["vector", "bm25", "hybrid", "graph"]
    vector_results_count: int                  # Vector results
    bm25_results_count: int                    # BM25 results
    reranking_applied: bool                    # Reranking used
    error: Optional[str]                       # Error if failed
```

---

## Error Handling Flow

```
VectorSearchAgent.process(state)
    │
    ├─ Try:
    │    │
    │    └─ _search_with_retry(query)
    │         │
    │         ├─ Attempt 1: hybrid_search.hybrid_search()
    │         │   └─ [Fails: VectorSearchError]
    │         │
    │         ├─ Wait 1s (exponential backoff)
    │         │
    │         ├─ Attempt 2: hybrid_search.hybrid_search()
    │         │   └─ [Fails: VectorSearchError]
    │         │
    │         ├─ Wait 2s (exponential backoff)
    │         │
    │         ├─ Attempt 3: hybrid_search.hybrid_search()
    │         │   └─ [Success or Final Failure]
    │         │
    │         └─ Return result or raise
    │
    ├─ Except VectorSearchError:
    │    │
    │    ├─ Log error
    │    ├─ Set state["metadata"]["error"]
    │    ├─ Set state["metadata"]["search"]["error"]
    │    └─ Return state (graceful degradation)
    │
    └─ Return state (with or without error)
```

---

## Performance Optimization

### 1. Async Execution

```python
# All operations are async for non-blocking I/O
async def process(state):
    result = await self._search_with_retry(query)
    # ↑ Doesn't block event loop
```

### 2. Retry Strategy

```python
@retry(
    stop=stop_after_attempt(3),           # Max 3 attempts
    wait=wait_exponential(                # Exponential backoff
        multiplier=1,                      # Base: 1s
        min=1,                             # Min: 1s
        max=10                             # Max: 10s
    ),
    retry=retry_if_exception_type(        # Only retry on specific error
        VectorSearchError
    )
)
```

**Backoff Schedule:**
- Attempt 1: Immediate
- Attempt 2: Wait 1s
- Attempt 3: Wait 2s
- Total max delay: 3s

### 3. Reranking (Optional)

```
Without Reranking:          With Reranking:
Vector: 10 results          Vector: 20 results
BM25: 10 results            BM25: 20 results
   ↓                           ↓
RRF Fusion                  RRF Fusion (40 candidates)
   ↓                           ↓
Top 5 results               Rerank top 10
                               ↓
                            Top 5 results
```

**Latency:**
- Without reranking: ~200ms
- With reranking: ~400ms (2x slower, better quality)

---

## Integration Points

### 1. With Existing Components

| Component | Usage | Location |
|-----------|-------|----------|
| HybridSearch | Main search engine | `src/components/vector_search/` |
| QdrantClient | Vector database | `src/components/vector_search/` |
| EmbeddingService | Query embeddings | `src/components/vector_search/` |
| CrossEncoderReranker | Result reranking | `src/components/retrieval/` |

### 2. With LangGraph

| Aspect | Implementation |
|--------|----------------|
| State Schema | `AgentState` (extends `MessagesState`) |
| Node Function | `vector_search_node(state) -> state` |
| Graph Registration | `graph.add_node("vector_search", vector_search_node)` |
| Routing | Conditional edge from router |

### 3. With Configuration

```python
# src/core/config.py
retrieval_top_k: int = 5                    # Results to return
vector_agent_timeout: int = 30              # Timeout (seconds)
vector_agent_max_retries: int = 3           # Retry attempts
vector_agent_use_reranking: bool = True     # Enable reranking
```

---

## Testing Strategy

### Unit Tests (15 tests)

```
Initialization (2 tests)
├─ test_vector_search_agent_init_default
└─ test_vector_search_agent_init_custom

Processing (4 tests)
├─ test_process_success
├─ test_process_with_reranking
├─ test_process_empty_query
└─ test_process_search_error

Retry Logic (2 tests)
├─ test_retry_on_failure
└─ test_retry_exhausted

Result Conversion (2 tests)
├─ test_convert_results_basic
└─ test_convert_results_with_rrf_metadata

State Management (2 tests)
├─ test_state_metadata_tracking
└─ test_latency_measurement

Node Function (1 test)
└─ test_vector_search_node

Edge Cases (2 tests)
├─ test_empty_results
└─ test_malformed_results
```

### Integration Tests (9 tests)

```
Real Search (2 tests)
├─ test_agent_process_real_search
└─ test_agent_with_different_queries

Graph Integration (2 tests)
├─ test_vector_search_node_integration
└─ test_full_graph_execution

Performance (2 tests)
├─ test_search_performance_benchmark (P50/P95/P99)
└─ test_concurrent_searches

Error Handling (2 tests)
├─ test_agent_with_empty_query
└─ test_agent_with_very_long_query

Reranking (1 test)
└─ test_search_with_reranking
```

---

## Metrics & Observability

### Logged Metrics

```python
# In VectorSearchAgent
logger.info(
    "vector_search",
    query_length=len(query),
    result_count=len(contexts),
    latency_ms=latency_ms,
    reranking_applied=reranking_applied,
    agent=self.name
)
```

### State Metadata

```python
# Available in state after execution
state["metadata"]["search"] = {
    "latency_ms": 234.5,
    "result_count": 5,
    "search_mode": "hybrid",
    "vector_results_count": 10,
    "bm25_results_count": 8,
    "reranking_applied": true,
    "error": null
}
```

### Agent Path Tracing

```python
# Execution trace
state["metadata"]["agent_path"] = [
    "router",
    "VectorSearchAgent: started",
    "VectorSearchAgent: completed (5 results, 234ms)"
]
```

---

## Future Enhancements

### Short-term (Sprint 4)

- [ ] Add generation agent (Feature 4.4)
- [ ] Connect vector_search → generation
- [ ] Add conversation history checkpointing

### Mid-term (Sprint 5)

- [ ] Add Graph RAG agent
- [ ] Parallel retrieval (vector + graph)
- [ ] Result fusion across multiple sources

### Long-term

- [ ] Query expansion
- [ ] Multi-modal search (images, code)
- [ ] Adaptive top_k based on query complexity
- [ ] Smart caching for repeated queries

---

## References

- **Implementation:** `src/agents/vector_search_agent.py`
- **Tests:** `tests/unit/agents/test_vector_search_agent.py`
- **Integration:** `tests/integration/test_vector_agent_integration.py`
- **Documentation:** `SPRINT_4_FEATURE_4.3_SUMMARY.md`
- **Graph:** `src/agents/graph.py`
- **State:** `src/agents/state.py`
