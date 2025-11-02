# ADR-025: mem0 as Layer 0 for User Preference Learning

**Status:** ✅ Accepted (Sprint 21)
**Date:** 2025-10-31
**Authors:** Claude Code, Klaus Pommer
**Related:** Sprint 21 Feature 21.5, Sprint 22 Feature 22.5 (optional)

---

## Context

### Problem Statement

AEGIS RAG currently uses **static user preferences** stored as JSONB in PostgreSQL:

```sql
CREATE TABLE users (
    ...
    preferences JSONB DEFAULT '{
        "default_search_mode": "hybrid",
        "theme": "light",
        "language": "de"
    }'::jsonb,
    ...
);
```

**Limitations:**
1. ❌ **Static Configuration:** Preferences must be manually set, no learning
2. ❌ **No Behavioral Insights:** Cannot extract implicit preferences from conversations
3. ❌ **Limited Personalization:** Cannot adapt to user communication styles
4. ❌ **No Cross-Session Learning:** Each session starts from scratch

**Missing Capabilities:**
- "Klaus prefers concise, technical answers" (communication style)
- "User works primarily with Python and VBScript" (technical context)
- "User frequently asks about server-side scripting" (topic affinity)
- "User prefers German but understands English" (language flexibility)

### Current Memory Architecture (3 Layers)

```
Layer 1: Redis (Short-term Conversation Context)
         ↓
Layer 2: Qdrant + BM25 + LightRAG (Document Retrieval)
         ↓
Layer 3: Graphiti (Episodic Memory + Temporal Knowledge Graph)
```

**Gap:** No dedicated layer for **user preference learning**!

---

## Decision

We integrate **mem0** ([github.com/mem0ai/mem0](https://github.com/mem0ai/mem0)) as **Layer 0** of AEGIS RAG's memory architecture to enable **LLM-driven user preference extraction and personalization**.

### Why mem0?

1. **Apache 2.0 License** → Fully compatible with AEGIS RAG (commercial use allowed)
2. **Proven Performance** → 42k+ GitHub stars, 4.5k+ dependent projects
3. **Tech Stack Alignment** → Uses Qdrant (Vector Store), Neo4j (Graph Store), Ollama (LLM) - all already in AEGIS RAG
4. **Established Benchmarks** → +26% accuracy vs. OpenAI Memory, 90% token reduction, 91% faster responses (LOCOMO benchmark)
5. **Production-Ready** → Y Combinator S24 batch, 269 releases, enterprise deployments

### Architecture: 4-Layer Memory System

```
┌───────────────────────────────────────────────────────────┐
│                   Layer 0: mem0                           │
│              USER PREFERENCE LAYER (NEW!)                 │
│                                                           │
│  Purpose: Long-term user preferences, behaviors, context  │
│  Storage: Qdrant (mem0_user_preferences collection)      │
│  LLM: Ollama (llama3.2:3b - shared with chat)            │
│  Embeddings: BGE-M3 (1024-dim - AEGIS RAG standard)      │
│  Latency: <50ms (fast fact retrieval)                    │
│  Scope: Cross-session, persistent per user               │
└───────────────────┬───────────────────────────────────────┘
                    │
                    ↓ (Inject preferences into prompts)
                    │
┌───────────────────┴───────────────────────────────────────┐
│                  Layer 1: Redis                           │
│           SHORT-TERM CONVERSATION CONTEXT                 │
└───────────────────┬───────────────────────────────────────┘
                    │
                    ↓
┌───────────────────┴───────────────────────────────────────┐
│         Layer 2: Qdrant + BM25 + LightRAG                 │
│              DOCUMENT RETRIEVAL LAYER                     │
└───────────────────┬───────────────────────────────────────┘
                    │
                    ↓
┌───────────────────┴───────────────────────────────────────┐
│                  Layer 3: Graphiti                        │
│               EPISODIC MEMORY LAYER                       │
└───────────────────────────────────────────────────────────┘
```

---

## Technical Implementation

### mem0 Configuration

```python
# src/components/memory/mem0_wrapper.py
from mem0 import Memory
from mem0.configs.base import MemoryConfig

class Mem0Wrapper:
    def __init__(self):
        config = MemoryConfig(
            # Reuse AEGIS RAG's Qdrant instance (separate collection)
            vector_store=VectorStoreConfig(
                provider="qdrant",
                config=QdrantConfig(
                    host=settings.qdrant_host,  # localhost:6333
                    port=settings.qdrant_port,
                    collection_name="mem0_user_preferences",  # NEW
                    embedding_dim=1024,  # BGE-M3
                )
            ),
            # Reuse AEGIS RAG's Ollama LLM
            llm=LlmConfig(
                provider="ollama",
                config=OllamaConfig(
                    model=settings.ollama_model_generation,  # llama3.2:3b
                    base_url=settings.ollama_base_url,  # http://localhost:11434
                )
            ),
            # Reuse AEGIS RAG's BGE-M3 embeddings
            embedder=EmbedderConfig(
                provider="ollama",
                config=OllamaEmbedderConfig(
                    model="bge-m3",
                    base_url=settings.ollama_base_url,
                    embedding_dims=1024,
                )
            ),
        )
        self.memory = Memory.from_config(config)
```

### Integration with Chat API

```python
# src/api/v1/chat.py
@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, user: User = Depends(get_current_user)):
    # STEP 1: Get user preferences from mem0 (Layer 0)
    mem0 = get_mem0_wrapper()
    preferences = await mem0.get_user_preferences(
        user_id=str(user.id),
        query=request.query,
        limit=3
    )

    # STEP 2: Build personalized system prompt
    system_prompt = f"""You are AegisRAG, a helpful AI assistant.

User: {user.name}
Preferences (learned from conversations):
{chr(10).join(f"- {p['memory']}" for p in preferences)}

Please tailor your responses accordingly."""

    # STEP 3: Execute RAG + LLM with personalized prompt
    async for chunk in coordinator.stream(query, mode, system_prompt):
        yield chunk

    # STEP 4: Update mem0 in background (async, non-blocking)
    background_tasks.add_task(
        mem0.add_user_memory,
        user_id=str(user.id),
        messages=[
            {"role": "user", "content": request.query},
            {"role": "assistant", "content": full_response}
        ]
    )
```

### Database Schema Extension

```sql
-- Migration 002: Add mem0 support to users table
ALTER TABLE users
ADD COLUMN mem0_enabled BOOLEAN NOT NULL DEFAULT true,
ADD COLUMN mem0_memory_count INT NOT NULL DEFAULT 0,
ADD COLUMN last_preference_update TIMESTAMP WITH TIME ZONE;

CREATE INDEX idx_users_mem0_enabled
ON users(mem0_enabled)
WHERE mem0_enabled = true;
```

---

## Alternatives Considered

### Alternative 1: Extend Graphiti for User Preferences

**Pros:**
- ✅ No new dependency
- ✅ Leverage existing Neo4j infrastructure

**Cons:**
- ❌ Graphiti optimized for **episodic memory** (events), not user facts
- ❌ Would need significant custom development
- ❌ Slower fact retrieval (graph traversal vs vector search)
- ❌ No established benchmarks for this use case

**Verdict:** ❌ Rejected - Architectural mismatch

---

### Alternative 2: Build Custom User Preference Layer

**Pros:**
- ✅ Full control over implementation
- ✅ Optimized for AEGIS RAG specifics

**Cons:**
- ❌ High development effort (~21-34 SP)
- ❌ No established performance benchmarks
- ❌ Requires custom LLM prompts for fact extraction
- ❌ Need to implement deduplication logic
- ❌ Maintenance burden (updates, bug fixes)

**Verdict:** ❌ Rejected - Reinventing the wheel

---

### Alternative 3: Use OpenAI Memory API

**Pros:**
- ✅ Managed service, no infrastructure
- ✅ Established performance

**Cons:**
- ❌ Violates **air-gapped deployment** requirement (ADR-002)
- ❌ Requires API key and internet connectivity
- ❌ Monthly cost per user ($X/month)
- ❌ Data privacy concerns (user data on OpenAI servers)
- ❌ Vendor lock-in (proprietary API)

**Verdict:** ❌ Rejected - Conflicts with AEGIS RAG principles

---

### Alternative 4: mem0 (SELECTED)

**Pros:**
- ✅ Apache 2.0 licensed (commercial-friendly)
- ✅ Proven performance (+26% accuracy, 90% token reduction)
- ✅ Tech stack alignment (Qdrant, Ollama, Neo4j)
- ✅ 100% local deployment (no cloud dependencies)
- ✅ Established in production (42k stars, 4.5k+ dependents)
- ✅ Active development (269 releases, Y Combinator S24)
- ✅ Minimal integration effort (8 SP vs 21-34 SP custom)

**Cons:**
- ⚠️ Additional dependency (~10 transitive dependencies)
- ⚠️ Overlap with Graphiti (but complementary, not redundant)
- ⚠️ Vendor dependency (though open-source)

**Verdict:** ✅ **ACCEPTED** - Best risk/reward ratio

---

## Consequences

### Positive ✅

1. **LLM-Driven Personalization**
   - Facts automatically extracted from conversations
   - No manual preference configuration needed
   - Cross-session learning and memory consolidation

2. **Tech Stack Synergy**
   - Reuses Qdrant (shared instance, separate collection)
   - Reuses Ollama LLM (llama3.2:3b)
   - Reuses BGE-M3 embeddings (1024-dim standard)
   - Optional: Reuses Neo4j for entity relationships

3. **Performance Benefits (from mem0 benchmarks)**
   - 90% token reduction vs full context
   - 91% faster responses
   - +26% accuracy vs OpenAI Memory (LOCOMO benchmark)

4. **User Privacy**
   - 100% local, no cloud dependencies
   - User-controlled preferences (view/delete)
   - GDPR-compliant (data residency)

5. **Developer Experience**
   - Simple API: `add()`, `search()`, `update()`, `delete()`
   - Automatic deduplication (LLM-driven ADD/UPDATE/DELETE logic)
   - Graceful degradation (mem0 failures don't break chat)

### Negative ⚠️

1. **Additional Dependency**
   - mem0ai package + ~10 transitive dependencies
   - Increases maintenance surface
   - **Mitigation:** Apache 2.0 allows forking if needed

2. **Architectural Complexity**
   - 3-layer → 4-layer memory system
   - More moving parts to debug
   - **Mitigation:** Clear separation of concerns, comprehensive logging

3. **Overlap with Graphiti**
   - Both store user/agent information
   - **Mitigation:**
     - mem0 (Layer 0): User **preferences** (static facts)
     - Graphiti (Layer 3): User **interactions** (episodic events)
     - Clear responsibility boundaries

4. **Performance Overhead**
   - Fact extraction: ~200-500ms per conversation (LLM call)
   - **Mitigation:** Runs as async background task, doesn't block chat

5. **Qdrant Collection Growth**
   - New collection: `mem0_user_preferences`
   - Estimated: ~100-500 facts per active user
   - **Mitigation:** Monitor collection size, implement retention policies

### Neutral ℹ️

1. **Learning Curve**
   - Team needs to understand mem0's fact extraction logic
   - **Mitigation:** Comprehensive documentation, code examples

2. **Testing Requirements**
   - New test suite for mem0 integration
   - **Mitigation:** Included in Sprint 21.5 scope (8 SP)

---

## Implementation Plan

### Sprint 21 (Feature 21.5 - 8 SP, 2 days)

**Tasks:**
1. Setup mem0 dependencies (`poetry add mem0ai`)
2. Implement `Mem0Wrapper` class
3. Extend PostgreSQL schema (mem0-related columns)
4. Integrate into chat API (preference injection)
5. Create user preferences API (`GET /users/me/preferences`)
6. Frontend: User profile page with learned preferences
7. Tests: Unit + Integration (100% coverage)
8. Documentation: ADR-025 + integration guide

**Success Criteria:**
- ✅ Users can view learned preferences
- ✅ Preferences injected into chat prompts
- ✅ mem0 failures gracefully degrade

### Sprint 22 (Feature 22.5 - OPTIONAL, 5 SP, 1 day)

**Extend to project-level memory:**
- Project-specific terminology
- Team communication styles
- Project conventions

**Decision:** Implement if Sprint 22 stays on schedule, otherwise defer to Sprint 23.

---

## Monitoring & Observability

### Key Metrics

```python
# Prometheus metrics to track
mem0_fact_extraction_duration_seconds  # p50, p95, p99
mem0_preference_retrieval_duration_seconds  # p50, p95, p99
mem0_memory_count_by_user  # Histogram
mem0_error_rate  # Counter
mem0_cache_hit_rate  # Gauge (if caching implemented)
```

### Alerts

```yaml
- name: mem0_high_latency
  condition: mem0_preference_retrieval_duration_seconds_p95 > 0.1  # 100ms
  severity: warning

- name: mem0_extraction_failures
  condition: rate(mem0_error_rate[5m]) > 0.05  # 5% error rate
  severity: critical

- name: mem0_memory_explosion
  condition: mem0_memory_count_by_user_p99 > 1000  # Too many facts per user
  severity: warning
```

---

## Rollback Plan

If mem0 causes production issues:

1. **Immediate:** Set `MEM0_ENABLED=false` in `.env`
2. **Graceful Degradation:** Chat API falls back to static preferences
3. **Data Retention:** mem0 data persists in Qdrant (not deleted)
4. **Re-enable:** Set `MEM0_ENABLED=true` when issue resolved

**No data loss, clean rollback path.**

---

## References

- [mem0 GitHub Repository](https://github.com/mem0ai/mem0)
- [mem0 Documentation](https://docs.mem0.ai)
- [mem0 LOCOMO Benchmark](https://github.com/mem0ai/locomo)
- [mem0 License (Apache 2.0)](https://github.com/mem0ai/mem0/blob/main/LICENSE)
- [AEGIS RAG Sprint 21 Plan](../sprints/SPRINT_21_PLAN.md)
- [AEGIS RAG Sprint 22 Plan](../sprints/SPRINT_22_PLAN.md)

---

## Approval

- **Architect:** Claude Code ✅
- **Product Owner:** Klaus Pommer ✅
- **Implementation:** Sprint 21 Feature 21.5
- **Review Date:** Post-Sprint 21 retrospective
