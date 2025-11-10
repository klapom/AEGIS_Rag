# Memory Component

**Sprint 7-9:** 3-Layer Memory Architecture
**Architecture:** Redis (Short-Term) + Qdrant (Semantic) + Graphiti (Episodic)
**Performance:** <100ms p95 for memory retrieval across all layers

---

## Overview

The Memory Component provides **3-layer memory architecture** for conversational AI:
- **Layer 1 (Redis):** Short-term working memory (<10ms)
- **Layer 2 (Qdrant):** Long-term semantic memory (<50ms)
- **Layer 3 (Graphiti):** Episodic temporal memory (<100ms)

**Future (Planned):** Layer 0 (Mem0) for user preference learning (ADR-025, Sprint 22+)

### Key Features

- **Unified Memory API:** Single interface for all memory layers
- **Intelligent Router:** Automatic layer selection based on query type
- **Memory Consolidation:** Background job to move STM → LTM
- **Temporal Awareness:** Time-based memory retrieval
- **Relevance Scoring:** Context-aware memory ranking

---

## Architecture

### 3-Layer Memory System

```
┌─────────────────────────────────────────────────────────────┐
│                  Memory Architecture                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │   Layer 1: Short-Term Memory (Redis)                 │  │
│  │                                                       │  │
│  │   - Session state (TTL: 1 hour)                      │  │
│  │   - Recent context (<10 messages)                    │  │
│  │   - Latency: <10ms                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                      │                                       │
│                      ▼ (Consolidation every 10 min)          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │   Layer 2: Long-Term Semantic Memory (Qdrant)        │  │
│  │                                                       │  │
│  │   - Persistent conversation history                  │  │
│  │   - Semantic search over past conversations          │  │
│  │   - Latency: <50ms                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                      │                                       │
│                      ▼ (Entity extraction)                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │   Layer 3: Episodic Temporal Memory (Graphiti)       │  │
│  │                                                       │  │
│  │   - Temporal relationships between concepts          │  │
│  │   - Episode-based retrieval                          │  │
│  │   - Latency: <100ms                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Memory Router (Intelligent Dispatch)         │  │
│  │                                                       │  │
│  │   - Query type classification                        │  │
│  │   - Multi-layer fusion                               │  │
│  │   - Relevance scoring                                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Component Files

| File | Purpose | LOC |
|------|---------|-----|
| `unified_api.py` | Unified memory interface | 530 |
| `memory_router.py` | Intelligent layer routing | 440 |
| `redis_memory.py` | Redis short-term memory | 390 |
| `graphiti_wrapper.py` | Graphiti episodic memory | 525 |
| `consolidation.py` | STM → LTM consolidation | 740 |
| `relevance_scorer.py` | Context-aware scoring | 255 |
| `routing_strategy.py` | Router decision logic | 315 |
| `monitoring.py` | Memory health monitoring | 430 |

**Total:** ~3,625 lines of code

---

## Unified Memory API

### Overview

`UnifiedMemoryAPI` provides single interface to all memory layers.

### Key Methods

```python
from src.components.memory.unified_api import get_unified_memory_api

# Get singleton
memory = get_unified_memory_api()

# Store memory (auto-routes to appropriate layer)
await memory.store(
    session_id="user-123",
    key="user_preference",
    value={"theme": "dark", "language": "en"},
    namespace="preferences"
)

# Retrieve memory (searches all layers)
result = await memory.retrieve(
    session_id="user-123",
    query="What is the user's preferred theme?",
    namespace="preferences"
)

# Result:
# {
#   "key": "user_preference",
#   "value": {"theme": "dark", "language": "en"},
#   "layer": "redis",  # Layer 1 (recent)
#   "relevance_score": 0.95
# }
```

### Features

**Unified Interface:**
- `store()`: Store memory (auto-layer selection)
- `retrieve()`: Retrieve memory (multi-layer search)
- `search()`: Semantic search across layers
- `delete()`: Remove memory from all layers

**Auto-Routing:**
- Recent queries (< 1 hour) → Redis (Layer 1)
- Semantic queries → Qdrant (Layer 2)
- Temporal queries → Graphiti (Layer 3)

---

## Layer 1: Redis Short-Term Memory

### Overview

`RedisMemory` provides ultra-fast working memory with TTL.

### Usage

```python
from src.components.memory.redis_memory import get_redis_memory

# Get singleton
redis_memory = get_redis_memory()

# Store with TTL
await redis_memory.store(
    session_id="user-123",
    key="conversation_state",
    value={
        "last_query": "What is ML?",
        "intent": "definition",
        "timestamp": "2025-11-10T10:30:00Z"
    },
    ttl_seconds=3600  # 1 hour
)

# Retrieve
state = await redis_memory.retrieve(
    session_id="user-123",
    key="conversation_state"
)
```

### Features

**Short-Term Storage:**
- **TTL:** Auto-expiration after 1 hour (configurable)
- **Session Isolation:** Per-user namespace
- **Fast Access:** <10ms latency

**Use Cases:**
- Conversation context (last 10 messages)
- Session state (current query, intent)
- Temporary cache (API responses)

### Performance

**Benchmark:**
- **Store Latency:** <5ms p95
- **Retrieve Latency:** <10ms p95
- **Throughput:** 10,000 ops/sec
- **Memory Usage:** ~50 MB for 10K sessions

---

## Layer 2: Qdrant Semantic Memory

### Overview

Layer 2 uses **Qdrant** for persistent semantic memory.

### Usage

```python
from src.components.memory.unified_api import get_unified_memory_api

memory = get_unified_memory_api()

# Store conversation (persists to Qdrant)
await memory.store_conversation(
    session_id="user-123",
    conversation=[
        {"role": "user", "content": "What is machine learning?"},
        {"role": "assistant", "content": "Machine learning is..."}
    ]
)

# Semantic search over past conversations
results = await memory.search_conversations(
    query="machine learning discussions",
    limit=5
)
```

### Features

**Persistent Storage:**
- **No TTL:** Conversations stored indefinitely
- **Semantic Search:** Find similar past conversations
- **Embedding:** BGE-M3 (1024-dim)

**Use Cases:**
- Long-term conversation history
- Semantic search over past interactions
- User preference learning (future: Mem0)

### Performance

**Benchmark:**
- **Search Latency:** <50ms p95
- **Throughput:** 200 QPS
- **Storage:** ~1 MB per 100 conversations

---

## Layer 3: Graphiti Episodic Memory

### Overview

`GraphitiWrapper` provides **temporal episodic memory** using Graphiti framework.

### Usage

```python
from src.components.memory.graphiti_wrapper import get_graphiti_wrapper

# Get singleton
graphiti = get_graphiti_wrapper()

# Store episode (auto-extracts entities + temporal relations)
await graphiti.add_episode(
    content="User asked about machine learning on 2025-11-10",
    metadata={
        "session_id": "user-123",
        "timestamp": "2025-11-10T10:30:00Z"
    }
)

# Retrieve related episodes
episodes = await graphiti.search_episodes(
    query="machine learning questions",
    temporal_context="last_week"
)
```

### Features

**Temporal Awareness:**
- **Bi-Temporal Structure:** Valid time + transaction time
- **Time-Based Retrieval:** "What did user ask last week?"
- **Episode Linking:** Connect related memories over time

**Use Cases:**
- Long-term user behavior tracking
- Temporal reasoning ("How did user's interests evolve?")
- Episode-based context retrieval

### Performance

**Benchmark:**
- **Add Episode:** ~100ms (entity extraction)
- **Search Latency:** <100ms p95
- **Storage:** ~100 KB per episode

---

## Memory Router

### Overview

`MemoryRouter` intelligently routes queries to appropriate layer(s).

### Routing Logic

```python
# src/components/memory/memory_router.py

async def route_query(query: str, context: dict) -> List[str]:
    """Route query to appropriate memory layers.

    Returns: List of layer names to query
    """

    # Recency check
    if is_recent_query(context):
        return ["redis"]  # Layer 1 only

    # Semantic query
    if is_semantic_query(query):
        return ["qdrant"]  # Layer 2 only

    # Temporal query
    if has_temporal_keywords(query):  # "last week", "yesterday", etc.
        return ["graphiti"]  # Layer 3 only

    # Complex query → Multi-layer
    return ["redis", "qdrant", "graphiti"]
```

### Routing Strategies

**1. Single-Layer:**
- Fast queries (<20ms)
- Clear layer preference (e.g., "what did I just ask?")

**2. Multi-Layer:**
- Comprehensive retrieval
- Fuse results from all layers

**3. Cascading:**
- Try Layer 1 → if no results, try Layer 2 → Layer 3
- Minimize latency for common queries

---

## Memory Consolidation

### Overview

`ConsolidationService` moves memories from Redis → Qdrant → Graphiti.

### Consolidation Pipeline

```python
# src/components/memory/consolidation.py

async def consolidate_memories():
    """Background job: Consolidate short-term to long-term memory.

    Runs every 10 minutes.
    """

    # 1. Fetch recent memories from Redis
    redis_memories = await redis_memory.get_all_sessions()

    # 2. Filter: Select memories for consolidation
    #    - Age > 10 minutes
    #    - Access count > 2 (frequently accessed)
    candidates = filter_consolidation_candidates(redis_memories)

    # 3. Embed and store to Qdrant
    for memory in candidates:
        embedding = await embed(memory["content"])
        await qdrant.upsert(embedding, memory)

    # 4. Extract episodes for Graphiti
    episodes = extract_episodes(candidates)
    for episode in episodes:
        await graphiti.add_episode(episode)

    # 5. Delete from Redis (consolidated)
    await redis_memory.delete_batch([m["key"] for m in candidates])
```

### Consolidation Rules

**When to Consolidate:**
- Age > 10 minutes
- Access count > 2 (frequently referenced)
- Session ended (user logged out)

**What to Consolidate:**
- Conversation history
- User preferences
- Important context (flagged by relevance scorer)

### Performance

**Benchmark:**
- **Consolidation Frequency:** Every 10 minutes
- **Batch Size:** 100 memories per run
- **Processing Time:** ~5s per batch

---

## Relevance Scoring

### Overview

`RelevanceScorer` ranks memories by context relevance.

### Scoring Algorithm

```python
# src/components/memory/relevance_scorer.py

def calculate_relevance(
    query: str,
    memory: dict,
    context: dict
) -> float:
    """Calculate relevance score (0-1).

    Factors:
    1. Semantic similarity (40%)
    2. Recency (30%)
    3. Access frequency (20%)
    4. Source layer (10%)
    """

    # 1. Semantic similarity
    query_embedding = embed(query)
    memory_embedding = embed(memory["content"])
    similarity = cosine_similarity(query_embedding, memory_embedding)

    # 2. Recency decay
    age_hours = (now() - memory["timestamp"]).total_seconds() / 3600
    recency = math.exp(-age_hours / 24)  # Half-life: 24 hours

    # 3. Access frequency
    frequency = min(memory["access_count"] / 10, 1.0)

    # 4. Layer preference
    layer_weight = {"redis": 1.0, "qdrant": 0.9, "graphiti": 0.8}[memory["layer"]]

    # Weighted sum
    relevance = (
        0.4 * similarity +
        0.3 * recency +
        0.2 * frequency +
        0.1 * layer_weight
    )

    return relevance
```

### Features

**Multi-Factor Scoring:**
- Semantic similarity (BGE-M3 embeddings)
- Recency decay (exponential)
- Access frequency (usage-based)
- Layer preference (Redis > Qdrant > Graphiti)

---

## Monitoring

### Overview

`MemoryMonitoring` tracks memory health metrics.

### Metrics

```python
from src.components.memory.monitoring import get_memory_monitor

monitor = get_memory_monitor()

# Get memory stats
stats = await monitor.get_stats()

# {
#   "redis": {
#     "keys": 1234,
#     "memory_mb": 50,
#     "hit_rate": 0.85
#   },
#   "qdrant": {
#     "documents": 5000,
#     "size_mb": 250,
#     "avg_search_latency_ms": 45
#   },
#   "graphiti": {
#     "episodes": 500,
#     "entities": 2000,
#     "avg_search_latency_ms": 95
#   }
# }
```

### Alerts

**Warning Triggers:**
- Redis hit rate < 70%
- Qdrant search latency > 100ms
- Graphiti episode count > 10K (performance degradation)

---

## Usage Examples

### Store and Retrieve

```python
from src.components.memory.unified_api import get_unified_memory_api

memory = get_unified_memory_api()

# Store user preference
await memory.store(
    session_id="user-123",
    key="ui_theme",
    value="dark",
    namespace="preferences"
)

# Retrieve
theme = await memory.retrieve(
    session_id="user-123",
    key="ui_theme",
    namespace="preferences"
)
# Returns: "dark"
```

### Conversation History

```python
# Store conversation
await memory.store_conversation(
    session_id="user-123",
    conversation=[
        {"role": "user", "content": "What is ML?"},
        {"role": "assistant", "content": "ML is...", "sources": [...]}
    ]
)

# Retrieve conversation
history = await memory.get_conversation(session_id="user-123")
```

### Semantic Search

```python
# Search past conversations
results = await memory.search_conversations(
    query="machine learning discussions",
    limit=5,
    min_relevance=0.7
)

for result in results:
    print(f"Session: {result['session_id']}")
    print(f"Relevance: {result['relevance_score']}")
    print(f"Snippet: {result['snippet']}")
```

---

## Testing

### Unit Tests

```bash
# Test unified API
pytest tests/unit/components/memory/test_unified_api.py

# Test router
pytest tests/unit/components/memory/test_memory_router.py

# Test Redis memory
pytest tests/unit/components/memory/test_redis_memory.py
```

### Integration Tests

```bash
# Test memory consolidation
pytest tests/integration/components/memory/test_consolidation.py

# Test multi-layer retrieval
pytest tests/integration/components/memory/test_multi_layer_search.py
```

**Test Coverage:** 84% (68 unit tests, 22 integration tests)

---

## Configuration

### Environment Variables

```bash
# Redis (Layer 1)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=optional
REDIS_DEFAULT_TTL=3600  # 1 hour

# Qdrant (Layer 2)
QDRANT_URL=http://localhost:6333
QDRANT_MEMORY_COLLECTION=aegis-memory

# Graphiti (Layer 3)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Consolidation
CONSOLIDATION_ENABLED=true
CONSOLIDATION_INTERVAL_SECONDS=600  # 10 minutes
CONSOLIDATION_MIN_AGE_SECONDS=600

# Routing
ROUTING_STRATEGY=auto  # auto | manual
MULTI_LAYER_FUSION_ENABLED=true
```

---

## Performance Tuning

### Redis Optimization

**Eviction Policy:**
```bash
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru  # Evict least recently used
```

**Persistence:**
```bash
# Snapshot every 60s if 1000+ writes
save 60 1000

# Append-only file (AOF)
appendonly yes
```

---

## Troubleshooting

### Issue: Low Redis hit rate

**Symptoms:**
- Hit rate < 70%
- Frequent consolidation

**Solutions:**
```bash
# Increase Redis memory
maxmemory 4gb

# Adjust TTL
REDIS_DEFAULT_TTL=7200  # 2 hours
```

### Issue: Slow memory retrieval

**Solutions:**
```python
# Enable single-layer routing (avoid multi-layer)
ROUTING_STRATEGY=manual

# Increase consolidation frequency
CONSOLIDATION_INTERVAL_SECONDS=300  # 5 minutes
```

---

## Future: Mem0 Integration (ADR-025)

**Status:** Planned for Sprint 22+

**Mem0 as Layer 0:**
- **Purpose:** User preference learning and personalization
- **Features:**
  - Automatic preference extraction from conversations
  - Long-term user modeling
  - Personalized response adaptation

**Architecture:**
```
Layer 0 (Mem0): User Preferences (persistent)
   ↓
Layer 1 (Redis): Session State (1 hour TTL)
   ↓
Layer 2 (Qdrant): Conversation History (permanent)
   ↓
Layer 3 (Graphiti): Episodic Memory (temporal)
```

---

## Related Documentation

- **ADR-006:** 3-Layer Memory Architecture
- **ADR-025:** Mem0 as Layer 0 for User Preference Learning (planned)
- **Sprint 7-9 Summary:** [SPRINT_07-09_MEMORY_SUMMARY.md](../../docs/sprints/SPRINT_07-09_MEMORY_SUMMARY.md)

---

**Last Updated:** 2025-11-10
**Sprint:** 7-9 (Core implementation)
**Maintainer:** Klaus Pommer + Claude Code (backend-agent, documentation-agent)
