# TD-051: Memory Consolidation Pipeline (Sprint 9)

**Status:** OPEN
**Priority:** MEDIUM
**Severity:** Feature Gap
**Original Sprint:** Sprint 9
**Story Points:** 21 SP
**Created:** 2025-12-04

---

## Problem Statement

The 3-Layer Memory Architecture is not fully implemented. Memory consolidation from short-term (Redis) to long-term storage (Qdrant/Graphiti) is missing. There are no memory decay policies, no automatic eviction, and no unified memory API.

**Current State:**
- Redis stores short-term memory (conversations)
- Qdrant stores vector embeddings
- Graphiti stores episodic memory
- **Missing:** Automatic consolidation between layers
- **Missing:** Memory decay and eviction policies
- **Missing:** Memory routing logic

---

## Target Architecture

### 3-Layer Memory System

```
Layer 1: Redis (Short-Term)
├── TTL: 24 hours (configurable)
├── Latency: <10ms
├── Content: Recent conversations, working context
└── Eviction: LRU + TTL-based

     ↓ Consolidation (automatic)

Layer 2: Qdrant + BM25 (Semantic)
├── TTL: Permanent (with decay)
├── Latency: <50ms
├── Content: Facts, entities, document chunks
└── Decay: Relevance score decreases over time

     ↓ Consolidation (event-based)

Layer 3: Graphiti (Episodic)
├── TTL: Permanent (bi-temporal)
├── Latency: <100ms
├── Content: Episodes, relationships, temporal context
└── Versioning: Point-in-time queries
```

### Memory Consolidation Flow

```
User Query → Redis Check → Cache Hit? → Return
                    ↓ (miss)
              Qdrant/BM25 Search → Found? → Return + Cache to Redis
                    ↓ (miss)
              Graphiti Query → Return + Update Relevance
                    ↓
              Background: Consolidate important memories
```

---

## Solution Components

### 1. Memory Router

```python
# src/components/memory/router.py

class MemoryRouter:
    """Route memory queries to appropriate layer."""

    async def retrieve(
        self,
        query: str,
        user_id: str,
        context_window: int = 10
    ) -> MemoryResult:
        """Retrieve memories from optimal layer."""
        # 1. Check Redis for recent context
        redis_result = await self.redis_memory.get_recent(
            user_id, context_window
        )
        if redis_result.sufficient:
            return redis_result

        # 2. Search semantic memory (Qdrant + BM25)
        semantic_result = await self.semantic_search(query)

        # 3. Query episodic memory (Graphiti)
        episodic_result = await self.graphiti.query(
            query, user_id
        )

        # 4. Fuse results
        return self.fuse_memories(
            redis_result, semantic_result, episodic_result
        )
```

### 2. Memory Consolidation Pipeline

```python
# src/components/memory/consolidation.py

class MemoryConsolidationPipeline:
    """Consolidate memories from short-term to long-term."""

    async def consolidate_session(
        self,
        session_id: str
    ) -> ConsolidationResult:
        """Consolidate a conversation session."""
        # 1. Get session from Redis
        session = await self.redis_memory.get_session(session_id)

        # 2. Extract facts and entities
        facts = await self.extract_facts(session.messages)
        entities = await self.extract_entities(session.messages)

        # 3. Store in semantic memory
        await self.qdrant_client.upsert_facts(facts)

        # 4. Create episodic memory in Graphiti
        episode = Episode(
            user_id=session.user_id,
            content=session.summary,
            facts=facts,
            entities=entities,
            timestamp=session.created_at
        )
        await self.graphiti.add_episode(episode)

        return ConsolidationResult(
            facts_stored=len(facts),
            entities_linked=len(entities),
            episode_created=True
        )

    async def run_scheduled_consolidation(self) -> None:
        """Background job for memory consolidation."""
        # Run every 6 hours
        expired_sessions = await self.redis_memory.get_expiring(
            hours=6
        )
        for session in expired_sessions:
            await self.consolidate_session(session.id)
```

### 3. Memory Decay & Eviction

```python
# src/components/memory/decay.py

class MemoryDecayManager:
    """Manage memory decay and eviction."""

    async def apply_decay(self) -> DecayResult:
        """Apply time-based decay to memories."""
        # Decay formula: score = original_score * e^(-lambda * days)
        decay_rate = 0.01  # 1% per day

        query = """
        MATCH (m:Memory)
        WHERE m.last_accessed < datetime() - duration('P30D')
        SET m.relevance_score = m.relevance_score * exp(-$decay_rate * 30)
        RETURN count(m) as decayed
        """
        return await self.neo4j.execute(query, {"decay_rate": decay_rate})

    async def evict_stale_memories(
        self,
        threshold: float = 0.1
    ) -> EvictionResult:
        """Evict memories below relevance threshold."""
        # Archive before deletion
        stale = await self.get_stale_memories(threshold)
        await self.archive_memories(stale)
        await self.delete_memories(stale)
        return EvictionResult(evicted=len(stale))
```

### 4. Unified Memory API

```python
# src/api/v1/memory.py

@router.get("/api/v1/memory/query")
async def query_memory(
    query: str,
    user_id: str,
    layers: List[str] = ["redis", "qdrant", "graphiti"]
) -> MemoryResponse:
    """Query memories across all layers."""

@router.post("/api/v1/memory/consolidate")
async def trigger_consolidation(
    session_id: str
) -> ConsolidationResult:
    """Manually trigger memory consolidation."""

@router.get("/api/v1/memory/stats")
async def get_memory_stats(
    user_id: str
) -> MemoryStats:
    """Get memory statistics per layer."""
```

---

## Implementation Tasks

### Phase 1: Memory Router (5 SP)
- [ ] Create MemoryRouter class
- [ ] Implement layer selection logic
- [ ] Add caching logic (Redis as L1 cache)
- [ ] Unit tests for routing logic

### Phase 2: Consolidation Pipeline (8 SP)
- [ ] Implement fact extraction from conversations
- [ ] Implement entity extraction
- [ ] Create Episode builder for Graphiti
- [ ] Background job scheduler (APScheduler or Celery)
- [ ] Integration tests

### Phase 3: Decay & Eviction (5 SP)
- [ ] Implement decay algorithm
- [ ] Create eviction policy
- [ ] Add archival before deletion
- [ ] Monitoring metrics

### Phase 4: Unified API (3 SP)
- [ ] Create memory API endpoints
- [ ] Add memory health monitoring
- [ ] Prometheus metrics for memory stats

---

## Acceptance Criteria

- [ ] Memory Router selects optimal layer (90%+ accuracy)
- [ ] Consolidation runs automatically without data loss
- [ ] Memory decay applies correctly over time
- [ ] Eviction archives before deletion
- [ ] Memory latencies: Redis <10ms, Qdrant <50ms, Graphiti <100ms
- [ ] Memory capacity monitoring in Prometheus
- [ ] 80%+ test coverage

---

## Affected Files

```
src/components/memory/                   # NEW/EXPANDED
├── router.py                           # Memory routing
├── consolidation.py                    # Consolidation pipeline
├── decay.py                            # Decay & eviction
├── unified_api.py                      # Unified memory API
└── scheduler.py                        # Background jobs

src/api/v1/memory.py                    # NEW: Memory API endpoints
src/core/config.py                      # Memory configuration
```

---

## Dependencies

- Redis (existing)
- Qdrant (existing)
- Graphiti (existing, may need updates)
- APScheduler or Celery (for background jobs)

---

## Estimated Effort

**Story Points:** 21 SP

**Breakdown:**
- Phase 1 (Router): 5 SP
- Phase 2 (Consolidation): 8 SP
- Phase 3 (Decay): 5 SP
- Phase 4 (API): 3 SP

---

## References

- [SPRINT_PLAN.md - Sprint 9](../sprints/SPRINT_PLAN.md#sprint-9)
- [CLAUDE.md - 3-Layer Memory Architecture](../../CLAUDE.md)

---

## Target Sprint

**Recommended:** Sprint 38 (foundational feature)

---

**Last Updated:** 2025-12-04
