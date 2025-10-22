# Sprint 7 Plan - Graphiti Memory System & 3-Layer Memory Architecture

**Sprint Goal:** Complete 3-Layer Memory Architecture with Graphiti Episodic Temporal Memory
**Duration:** 1-2 weeks (flexible based on Ollama integration complexity)
**Story Points:** 40-45 (within capacity: 40-50 with buffer)
**Status:** Planning → Ready to Start

---

## Executive Summary

Sprint 7 implements **Component 3: Graphiti Memory System** to complete the 3-Layer Memory Architecture defined in ADR-006. This sprint introduces episodic temporal memory capabilities, enabling the system to remember conversations, track entity evolution over time, and provide point-in-time queries.

### Critical Design Constraint (ADR-002: Ollama-First Strategy)

**Challenge:** Graphiti defaults to OpenAI API, but AEGIS RAG mandates Ollama-First strategy

**Solution:** Configure Graphiti with Ollama as LLM provider:
- LLM: Ollama llama3.2:8b (fact extraction, memory consolidation)
- Embeddings: Ollama nomic-embed-text (memory retrieval)
- Zero API costs, fully offline-capable
- Optional Azure OpenAI fallback for production

### Sprint 7 Position in System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AEGIS RAG Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│ Sprint 4-6: LangGraph + Graph RAG (COMPLETE)                    │
│   ├─ Coordinator Agent                                          │
│   ├─ Vector Search Agent                                        │
│   ├─ Graph Query Agent                                          │
│   └─ Community Detection + Temporal Features                    │
├─────────────────────────────────────────────────────────────────┤
│ Sprint 7: 3-Layer Memory Architecture (NEW) ← THIS SPRINT       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Memory Architecture                      │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Layer 1: Redis (Short-Term Working Memory) <10ms         │  │
│  │  - Session context, recent queries                       │  │
│  │  - TTL: 1 hour                                           │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Layer 2: Qdrant (Long-Term Semantic Memory) <50ms        │  │
│  │  - Document embeddings, consolidated knowledge           │  │
│  │  - Persistent, searchable                                │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Layer 3: Graphiti + Neo4j (Episodic Temporal) <100ms ←NEW│  │
│  │  - Conversation graphs, entity evolution                 │  │
│  │  - Bi-temporal: valid_time + transaction_time            │  │
│  │  - Point-in-time queries                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Graphiti Memory System (NEW)                 │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Episodic Subgraph: Raw conversations, events             │  │
│  │ Semantic Subgraph: Extracted facts, relationships        │  │
│  │ Memory Router: Intelligent layer selection               │  │
│  │ Memory Agent: LangGraph integration                      │  │
│  └──────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│ Future: Sprint 8-10 - Memory Consolidation, MCP, Production    │
└─────────────────────────────────────────────────────────────────┘
```

### Key Deliverables

1. **Graphiti Core Integration** - Temporal memory graph with Ollama LLM
2. **Bi-Temporal Data Model** - Valid time + transaction time tracking
3. **Memory Router** - Intelligent 3-layer memory selection
4. **Memory Agent** - LangGraph integration for MEMORY intent
5. **Memory Consolidation Pipeline** - Short-term → Long-term transfer
6. **Point-in-Time Query API** - Historical context reconstruction

### Success Metrics

- Conversations automatically persist to episodic memory
- Facts extracted and stored in semantic memory
- Point-in-time queries reconstruct historical context
- Memory retrieval: Redis <10ms, Qdrant <50ms, Graphiti <100ms
- 100% Ollama compatibility (no OpenAI dependency)
- Memory Router accuracy >85% (correct layer selection)
- 80%+ test coverage (unit + integration)

---

## Sprint 7 Objectives

### Primary Goals

1. **Integrate Graphiti with Ollama**
   - Configure Graphiti to use Ollama llama3.2:8b (not OpenAI)
   - Configure embeddings: Ollama nomic-embed-text
   - Verify zero API cost, offline-capable operation

2. **Implement Bi-Temporal Memory Model**
   - Valid time: When facts are true in real world
   - Transaction time: When facts are recorded in system
   - Support point-in-time queries

3. **Build Memory Router**
   - Route queries to appropriate memory layer
   - Layer 1 (Redis): Recent context, session data
   - Layer 2 (Qdrant): Semantic search, document retrieval
   - Layer 3 (Graphiti): Episodic memory, temporal queries

4. **Create Memory Agent**
   - LangGraph integration for MEMORY intent
   - Handle episodic retrieval requests
   - Format temporal context for generation

5. **Implement Memory Consolidation**
   - Automatic: Redis → Qdrant (frequent patterns)
   - Background: Conversation → Graphiti (episodic storage)
   - Policy: Time-based + relevance-based

### Non-Goals (Deferred to Sprint 8)

- Memory decay strategies (time-based + relevance)
- Memory eviction policies (LRU, LFU)
- Advanced memory consolidation algorithms
- Memory health monitoring dashboard
- A/B testing Ollama vs Azure OpenAI

---

## Feature Breakdown (1 Feature = 1 Commit)

### Feature 7.1: Graphiti Core Integration with Ollama

**Priority:** P0 (Blocker for all other features)
**Story Points:** 10
**Effort:** 2 days

**Deliverables:**
- Graphiti Python package installation and configuration
- GraphitiWrapper class with Ollama LLM integration
- Configuration for Ollama llama3.2:8b + nomic-embed-text
- Neo4j backend integration (reuse Sprint 5 Neo4j setup)
- Episodic memory storage (conversation graphs)
- Semantic memory storage (extracted facts)
- Unit tests for Graphiti wrapper (25+ tests)

**Technical Tasks:**

1. **Install Graphiti Package:**
   ```bash
   poetry add graphiti-core
   ```

2. **Create GraphitiWrapper Class:**
   ```python
   # src/components/memory/graphiti_wrapper.py
   from graphiti_core import Graphiti
   from graphiti_core.llm_client import LLMClient
   import structlog

   logger = structlog.get_logger(__name__)

   class OllamaLLMClient(LLMClient):
       """Custom LLM client for Ollama integration."""

       def __init__(self, model: str, base_url: str):
           self.model = model
           self.base_url = base_url
           self.client = AsyncClient(host=base_url)

       async def generate(self, prompt: str, **kwargs):
           """Generate text using Ollama."""
           response = await self.client.generate(
               model=self.model,
               prompt=prompt,
               options={"temperature": 0.1, "num_predict": 2048},
           )
           return response["response"]

   class GraphitiWrapper:
       """Wrapper for Graphiti with Ollama LLM integration."""

       def __init__(
           self,
           neo4j_uri: str,
           neo4j_user: str,
           neo4j_password: str,
           ollama_llm_model: str = "llama3.2:8b",
           ollama_embedding_model: str = "nomic-embed-text",
           ollama_base_url: str = "http://localhost:11434",
       ):
           # Initialize Ollama LLM client
           llm_client = OllamaLLMClient(
               model=ollama_llm_model,
               base_url=ollama_base_url,
           )

           # Initialize Graphiti with Ollama
           self.graphiti = Graphiti(
               llm_client=llm_client,
               neo4j_uri=neo4j_uri,
               neo4j_user=neo4j_user,
               neo4j_password=neo4j_password,
               embedding_model=ollama_embedding_model,
           )

           logger.info(
               "graphiti_initialized",
               llm_model=ollama_llm_model,
               embedding_model=ollama_embedding_model,
           )

       async def add_episode(
           self,
           text: str,
           timestamp: str,
           metadata: dict | None = None,
       ):
           """Add conversation episode to memory."""
           await self.graphiti.add_episode(
               name=f"episode_{timestamp}",
               episode_body=text,
               source_description=metadata.get("source", "conversation"),
               reference_time=timestamp,
           )

       async def search(
           self,
           query: str,
           timestamp: str | None = None,
           top_k: int = 5,
       ):
           """Search episodic memory."""
           return await self.graphiti.search(
               query=query,
               center_node_uuid=None,
               num_results=top_k,
           )
   ```

3. **Configuration:**
   ```python
   # src/core/config.py (add settings)
   class Settings(BaseSettings):
       # Graphiti Memory Configuration (Sprint 7)
       graphiti_enabled: bool = Field(default=True, description="Enable Graphiti memory")
       graphiti_llm_model: str = Field(default="llama3.2:8b", description="Ollama LLM for memory")
       graphiti_embedding_model: str = Field(default="nomic-embed-text", description="Ollama embeddings")
       graphiti_ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")

       # Memory Consolidation
       memory_consolidation_enabled: bool = Field(default=True, description="Auto consolidation")
       memory_consolidation_interval_minutes: int = Field(default=30, description="Consolidation frequency")
   ```

4. **Write Unit Tests:**
   - Test Ollama LLM client integration
   - Test episode addition
   - Test memory search
   - Test temporal queries

**Acceptance Criteria:**
- Graphiti initializes with Ollama LLM (not OpenAI)
- Episodes can be added with timestamps
- Memory search returns relevant results
- Zero OpenAI API calls (verify with logging)
- 25+ unit tests passing
- Configuration documented

**Git Commit Message:**
```
feat(memory): integrate Graphiti with Ollama for episodic memory

Implements Graphiti temporal memory system using Ollama llama3.2:8b
instead of OpenAI, maintaining AEGIS RAG's local-first strategy.

Features:
- GraphitiWrapper with custom OllamaLLMClient
- Ollama llama3.2:8b for fact extraction (temperature=0.1)
- Ollama nomic-embed-text for memory retrieval
- Neo4j backend integration (reuses Sprint 5 setup)
- Episodic memory storage (conversations)
- Semantic memory storage (extracted facts)
- Zero API costs, fully offline-capable

Components:
- src/components/memory/graphiti_wrapper.py (450+ lines)
- Custom LLMClient for Ollama integration
- Configuration: graphiti_* settings

Performance:
- Memory retrieval: <100ms target
- Episode addition: ~2-3s (LLM extraction)

Cost:
- Development: $0 (Ollama local)
- Production: $0 (Ollama) or optional Azure

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Dependencies:** Neo4j (Sprint 5), Ollama llama3.2:8b, nomic-embed-text
**Risks:** Graphiti API compatibility with custom LLM client, Neo4j schema conflicts

---

### Feature 7.2: Bi-Temporal Data Model Implementation

**Priority:** P0 (Core Feature)
**Story Points:** 7
**Effort:** 1.5 days

**Deliverables:**
- Bi-temporal schema (valid_time + transaction_time)
- Point-in-time query support
- Temporal indexes for performance
- Time-travel query API
- Unit tests for temporal queries (20+ tests)

**Technical Tasks:**

1. **Extend Neo4j Schema with Temporal Properties:**
   ```cypher
   -- All Graphiti nodes/edges get temporal properties
   CREATE CONSTRAINT temporal_episode_id IF NOT EXISTS
   FOR (e:Episode) REQUIRE e.id IS UNIQUE;

   CREATE INDEX temporal_valid_from IF NOT EXISTS
   FOR (n) ON (n.valid_from);

   CREATE INDEX temporal_valid_to IF NOT EXISTS
   FOR (n) ON (n.valid_to);

   CREATE INDEX temporal_transaction_time IF NOT EXISTS
   FOR (n) ON (n.transaction_time);
   ```

2. **Implement Temporal Query Interface:**
   ```python
   # src/components/memory/temporal_queries.py
   from datetime import datetime
   import structlog

   logger = structlog.get_logger(__name__)

   class TemporalMemoryQuery:
       """Bi-temporal queries for Graphiti memory."""

       def __init__(self, graphiti_wrapper):
           self.graphiti = graphiti_wrapper

       async def query_point_in_time(
           self,
           query: str,
           timestamp: datetime,
           top_k: int = 5,
       ):
           """Query memory as it was at specific point in time.

           Uses valid_time to filter facts that were true at timestamp.
           """
           iso_timestamp = timestamp.isoformat()

           results = await self.graphiti.search(
               query=query,
               timestamp=iso_timestamp,
               top_k=top_k,
           )

           logger.info(
               "point_in_time_query",
               query=query[:100],
               timestamp=iso_timestamp,
               results=len(results),
           )

           return {
               "query": query,
               "timestamp": iso_timestamp,
               "results": results,
               "metadata": {"query_type": "point_in_time"},
           }

       async def query_time_range(
           self,
           query: str,
           start_time: datetime,
           end_time: datetime,
           top_k: int = 10,
       ):
           """Query memory for facts valid in time range."""
           # Implementation using Graphiti time-range queries
           pass

       async def get_entity_history(
           self,
           entity_id: str,
           start_time: datetime | None = None,
           end_time: datetime | None = None,
       ):
           """Get complete evolution history of entity."""
           # Implementation using Graphiti entity tracking
           pass
   ```

3. **API Endpoint for Temporal Queries:**
   ```python
   # src/api/v1/memory.py
   from fastapi import APIRouter
   from pydantic import BaseModel, Field
   from datetime import datetime

   router = APIRouter(prefix="/memory", tags=["Memory"])

   class PointInTimeQueryRequest(BaseModel):
       query: str = Field(..., min_length=1)
       timestamp: datetime = Field(..., description="Query time (ISO format)")
       top_k: int = Field(default=5, ge=1, le=20)

   @router.post("/temporal/point-in-time")
   async def query_point_in_time(request: PointInTimeQueryRequest):
       """Query memory as it was at specific point in time."""
       temporal_query = TemporalMemoryQuery(graphiti_wrapper)
       result = await temporal_query.query_point_in_time(
           query=request.query,
           timestamp=request.timestamp,
           top_k=request.top_k,
       )
       return result
   ```

**Acceptance Criteria:**
- Temporal schema created in Neo4j
- Point-in-time queries functional
- Time-range queries functional
- Entity history retrieval works
- Temporal overhead <50ms
- 20+ unit tests passing

**Git Commit Message:**
```
feat(memory): implement bi-temporal data model for Graphiti

Adds valid_time + transaction_time tracking to enable point-in-time
queries and entity evolution tracking.

Features:
- Bi-temporal schema (valid_time, transaction_time)
- Point-in-time query support
- Time-range queries
- Entity history retrieval
- Temporal indexes for performance
- API endpoint: POST /api/v1/memory/temporal/point-in-time

Components:
- src/components/memory/temporal_queries.py (300+ lines)
- src/api/v1/memory.py (temporal endpoints)
- Neo4j temporal indexes

Performance:
- Temporal query overhead: <50ms
- Index speedup: 10x vs full scan

Semantics:
- valid_time: When fact is true in real world
- transaction_time: When fact recorded in system

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Dependencies:** Feature 7.1 (Graphiti wrapper)
**Risks:** Neo4j query performance with temporal filters

---

### Feature 7.3: Memory Router (3-Layer Intelligence)

**Priority:** P0 (Core Integration)
**Story Points:** 8
**Effort:** 1.5 days

**Deliverables:**
- MemoryRouter class with layer selection logic
- Redis integration (Layer 1: working memory)
- Qdrant integration (Layer 2: semantic memory)
- Graphiti integration (Layer 3: episodic memory)
- Routing decision logic (rule-based + optional LLM)
- Unit tests for routing (25+ tests)

**Technical Tasks:**

1. **Implement Memory Router:**
   ```python
   # src/components/memory/memory_router.py
   from enum import Enum
   import structlog

   logger = structlog.get_logger(__name__)

   class MemoryLayer(str, Enum):
       SHORT_TERM = "redis"        # <10ms
       LONG_TERM = "qdrant"        # <50ms
       EPISODIC = "graphiti"       # <100ms

   class MemoryRouter:
       """Intelligent router for 3-layer memory architecture."""

       def __init__(
           self,
           redis_client,
           qdrant_client,
           graphiti_wrapper,
       ):
           self.redis = redis_client
           self.qdrant = qdrant_client
           self.graphiti = graphiti_wrapper

       async def route_query(
           self,
           query: str,
           context: dict | None = None,
       ) -> MemoryLayer:
           """Determine which memory layer(s) to query.

           Routing Logic:
           - Recent context (last 10 min) → Redis (Layer 1)
           - Semantic similarity → Qdrant (Layer 2)
           - Temporal/historical → Graphiti (Layer 3)
           - Complex queries → Multiple layers
           """
           # Check if recent context query
           if self._is_recent_context_query(query, context):
               return MemoryLayer.SHORT_TERM

           # Check if temporal/historical query
           if self._is_temporal_query(query):
               return MemoryLayer.EPISODIC

           # Default: semantic similarity
           return MemoryLayer.LONG_TERM

       async def search_memory(
           self,
           query: str,
           layers: list[MemoryLayer] | None = None,
           top_k: int = 5,
       ):
           """Search across memory layers."""
           if layers is None:
               # Auto-route
               primary_layer = await self.route_query(query)
               layers = [primary_layer]

           results = {}

           for layer in layers:
               if layer == MemoryLayer.SHORT_TERM:
                   results["redis"] = await self._search_redis(query, top_k)
               elif layer == MemoryLayer.LONG_TERM:
                   results["qdrant"] = await self._search_qdrant(query, top_k)
               elif layer == MemoryLayer.EPISODIC:
                   results["graphiti"] = await self._search_graphiti(query, top_k)

           return results

       def _is_recent_context_query(self, query: str, context: dict | None) -> bool:
           """Detect if query is about recent conversation context."""
           recent_indicators = [
               "just said", "you mentioned", "we discussed",
               "earlier today", "in this conversation"
           ]
           return any(ind in query.lower() for ind in recent_indicators)

       def _is_temporal_query(self, query: str) -> bool:
           """Detect if query has temporal component."""
           temporal_indicators = [
               "when", "last week", "yesterday", "ago",
               "history", "evolution", "changed", "before"
           ]
           return any(ind in query.lower() for ind in temporal_indicators)
   ```

2. **Redis Integration (Layer 1):**
   ```python
   # src/components/memory/redis_memory.py
   import redis.asyncio as redis
   import json
   from datetime import timedelta

   class RedisMemoryManager:
       """Short-term working memory with Redis."""

       def __init__(self, redis_url: str):
           self.client = redis.from_url(redis_url, decode_responses=True)

       async def set_context(
           self,
           session_id: str,
           context: dict,
           ttl: int = 3600,  # 1 hour
       ):
           """Store conversation context."""
           key = f"aegis:memory:session:{session_id}"
           await self.client.setex(
               key,
               timedelta(seconds=ttl),
               json.dumps(context),
           )

       async def get_context(self, session_id: str):
           """Retrieve conversation context."""
           key = f"aegis:memory:session:{session_id}"
           data = await self.client.get(key)
           return json.loads(data) if data else None
   ```

**Acceptance Criteria:**
- Router correctly selects layer for different query types
- All 3 layers integrated
- Search across multiple layers works
- Routing accuracy >85%
- 25+ unit tests passing

**Git Commit Message:**
```
feat(memory): implement 3-layer memory router

Intelligent routing between Redis (short-term), Qdrant (semantic),
and Graphiti (episodic) memory layers based on query type.

Features:
- MemoryRouter with automatic layer selection
- Redis integration (Layer 1: working memory <10ms)
- Qdrant integration (Layer 2: semantic <50ms)
- Graphiti integration (Layer 3: episodic <100ms)
- Rule-based routing logic
- Multi-layer search support

Components:
- src/components/memory/memory_router.py (400+ lines)
- src/components/memory/redis_memory.py (200+ lines)
- Unified memory search API

Routing Logic:
- Recent context → Redis
- Semantic similarity → Qdrant
- Temporal/historical → Graphiti

Performance:
- Layer selection: <5ms
- Multi-layer search: parallelized

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Dependencies:** Feature 7.1 (Graphiti), Redis client, Qdrant client
**Risks:** Routing accuracy, latency of multi-layer search

---

### Feature 7.4: Memory Agent (LangGraph Integration)

**Priority:** P0 (Required for orchestration)
**Story Points:** 6
**Effort:** 1 day

**Deliverables:**
- MemoryAgent class extending BaseAgent
- MEMORY intent routing handler
- Integration with Memory Router
- State management for memory results
- Error handling and fallback
- Unit tests for agent (15+ tests)

**Technical Tasks:**

1. **Create Memory Agent:**
   ```python
   # src/agents/memory_agent.py
   from src.agents.base_agent import BaseAgent
   from src.components.memory.memory_router import MemoryRouter, MemoryLayer
   from src.agents.state import AgentState
   import structlog

   logger = structlog.get_logger(__name__)

   class MemoryAgent(BaseAgent):
       """Agent for episodic and semantic memory retrieval."""

       def __init__(self, memory_router: MemoryRouter):
           super().__init__(name="memory_agent")
           self.memory_router = memory_router

       async def process(self, state: AgentState) -> AgentState:
           """Process MEMORY intent query."""
           query = state.query

           logger.info(
               "memory_agent_processing",
               query=query[:100],
               intent=state.intent,
           )

           try:
               # Route to appropriate memory layer(s)
               results = await self.memory_router.search_memory(
                   query=query,
                   layers=None,  # Auto-route
                   top_k=state.config.get("top_k", 5),
               )

               # Update state with memory results
               state.memory_results = results
               state.retrieved_contexts.extend([
                   {
                       "text": str(result),
                       "source": layer,
                       "timestamp": result.get("timestamp"),
                   }
                   for layer, layer_results in results.items()
                   for result in layer_results
               ])

               # Update metadata
               state.metadata["memory_layers_used"] = list(results.keys())
               state.metadata["agent_path"].append("memory")

               logger.info(
                   "memory_agent_complete",
                   query=query[:100],
                   layers=list(results.keys()),
                   total_results=sum(len(r) for r in results.values()),
               )

               return state

           except Exception as e:
               logger.error("memory_agent_error", query=query[:100], error=str(e))
               state.error = f"Memory retrieval failed: {str(e)}"
               return state
   ```

2. **Coordinator Integration:**
   ```python
   # src/agents/coordinator.py (update)
   from src.agents.memory_agent import MemoryAgent

   # In build_graph():
   graph.add_node("memory", self.memory_agent.process)

   # Routing from router
   graph.add_conditional_edges(
       "router",
       self.route_to_agent,
       {
           "vector": "vector_search",
           "graph": "graph_query",
           "memory": "memory",  # NEW
           "hybrid": "vector_search",
       },
   )

   graph.add_edge("memory", "generate")
   ```

**Acceptance Criteria:**
- MemoryAgent handles MEMORY intent
- Integrates with LangGraph coordinator
- Memory results included in state
- Error handling functional
- 15+ unit tests passing

**Git Commit Message:**
```
feat(agents): add Memory Agent for episodic retrieval

Implements MemoryAgent to handle MEMORY intent routing from coordinator.
Integrates 3-layer memory router with LangGraph orchestration.

Features:
- MemoryAgent extending BaseAgent
- MEMORY intent handler
- Automatic memory layer selection
- Multi-layer result aggregation
- LangGraph coordinator integration
- Error handling with logging

Components:
- src/agents/memory_agent.py (200+ lines)
- Updated coordinator with memory node
- State schema updates for memory results

Integration:
- Router → MEMORY intent → memory node
- memory → generate node
- Supports all 3 memory layers

Performance:
- Memory retrieval: <100ms (layer-dependent)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Dependencies:** Feature 7.3 (Memory Router), Sprint 4 Coordinator
**Risks:** State schema conflicts

---

### Feature 7.5: Memory Consolidation Pipeline

**Priority:** P1 (Important but not blocker)
**Story Points:** 7
**Effort:** 1.5 days

**Deliverables:**
- Automatic Redis → Qdrant consolidation
- Background conversation → Graphiti pipeline
- Time-based + relevance-based policies
- Consolidation scheduler
- Unit tests for consolidation (20+ tests)

**Technical Tasks:**

1. **Implement Consolidation Pipeline:**
   ```python
   # src/components/memory/consolidation.py
   import structlog
   from datetime import datetime, timedelta

   logger = structlog.get_logger(__name__)

   class MemoryConsolidationPipeline:
       """Automatic memory consolidation across layers."""

       def __init__(
           self,
           redis_manager,
           qdrant_client,
           graphiti_wrapper,
       ):
           self.redis = redis_manager
           self.qdrant = qdrant_client
           self.graphiti = graphiti_wrapper

       async def consolidate_redis_to_qdrant(
           self,
           min_access_count: int = 3,
           max_age_hours: int = 24,
       ):
           """Consolidate frequently accessed Redis data to Qdrant."""
           # Get all Redis keys with access count
           keys = await self.redis.scan_match("aegis:memory:*")

           consolidated = 0
           for key in keys:
               access_count = await self.redis.get(f"{key}:access_count")

               if int(access_count or 0) >= min_access_count:
                   # Consolidate to Qdrant
                   data = await self.redis.get(key)
                   await self.qdrant.upsert(...)
                   consolidated += 1

           logger.info(
               "redis_to_qdrant_consolidation",
               keys_processed=len(keys),
               consolidated=consolidated,
           )

           return consolidated

       async def consolidate_conversation_to_graphiti(
           self,
           conversation_id: str,
           messages: list[dict],
       ):
           """Store conversation in episodic memory."""
           # Convert conversation to episode
           episode_text = self._format_conversation(messages)
           timestamp = datetime.utcnow().isoformat()

           await self.graphiti.add_episode(
               text=episode_text,
               timestamp=timestamp,
               metadata={"conversation_id": conversation_id},
           )

           logger.info(
               "conversation_to_graphiti",
               conversation_id=conversation_id,
               message_count=len(messages),
           )
   ```

2. **Background Scheduler:**
   ```python
   # src/utils/scheduler.py
   import asyncio

   async def run_consolidation_scheduler(
       consolidation_pipeline,
       interval_minutes: int = 30,
   ):
       """Run consolidation pipeline periodically."""
       while True:
           await asyncio.sleep(interval_minutes * 60)

           try:
               await consolidation_pipeline.consolidate_redis_to_qdrant()
           except Exception as e:
               logger.error("consolidation_failed", error=str(e))
   ```

**Acceptance Criteria:**
- Automatic consolidation works
- Scheduler runs in background
- Policies configurable
- 20+ unit tests passing

**Git Commit Message:**
```
feat(memory): implement memory consolidation pipeline

Automatic consolidation from Redis to Qdrant (frequent patterns)
and conversations to Graphiti (episodic storage).

Features:
- Automatic Redis → Qdrant consolidation
- Conversation → Graphiti episodic storage
- Time-based + relevance-based policies
- Background scheduler (30-min intervals)
- Configurable consolidation rules

Components:
- src/components/memory/consolidation.py (350+ lines)
- src/utils/scheduler.py (background task)
- Consolidation policies

Policies:
- Redis → Qdrant: 3+ accesses in 24h
- Conversation → Graphiti: End of conversation

Performance:
- Consolidation time: ~5s per batch
- No user-facing latency

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Dependencies:** Feature 7.3 (Memory Router)
**Risks:** Background task reliability

---

### Feature 7.6: Memory API Endpoints

**Priority:** P2 (Nice to have)
**Story Points:** 4
**Effort:** 1 day

**Deliverables:**
- 6 new memory API endpoints
- OpenAPI documentation
- API integration tests

**API Endpoints:**
1. `POST /api/v1/memory/search` - Unified memory search
2. `POST /api/v1/memory/temporal/point-in-time` - Point-in-time queries
3. `GET /api/v1/memory/session/{session_id}` - Session context
4. `POST /api/v1/memory/consolidate` - Manual consolidation trigger
5. `GET /api/v1/memory/stats` - Memory statistics
6. `DELETE /api/v1/memory/session/{session_id}` - Clear session

**Acceptance Criteria:**
- All 6 endpoints functional
- OpenAPI docs updated
- 15+ API tests passing

---

## Sprint 7 Summary

### Feature Overview

| Feature | Priority | Story Points | Effort | Dependencies |
|---------|----------|--------------|--------|--------------|
| 7.1: Graphiti + Ollama | P0 | 10 | 2 days | Neo4j, Ollama |
| 7.2: Bi-Temporal Model | P0 | 7 | 1.5 days | 7.1 |
| 7.3: Memory Router | P0 | 8 | 1.5 days | 7.1, Redis, Qdrant |
| 7.4: Memory Agent | P0 | 6 | 1 day | 7.3, Sprint 4 |
| 7.5: Consolidation | P1 | 7 | 1.5 days | 7.3 |
| 7.6: API Endpoints | P2 | 4 | 1 day | All above |
| **TOTAL** | | **42** | **8.5 days** | |

### Sprint Burn-Down Plan

```
Week 1:
Day 1-2: Feature 7.1 (Graphiti + Ollama Core)
Day 3: Feature 7.2 (Bi-Temporal Model)
Day 4-5: Feature 7.3 (Memory Router)

Week 2:
Day 1: Feature 7.4 (Memory Agent)
Day 2: Feature 7.5 (Consolidation)
Day 3: (Optional) Feature 7.6 (API Endpoints) or testing/docs
```

### Dependencies Graph

```
Sprint 5 ✅ (Neo4j Backend)
Sprint 6 ✅ (Temporal Features)
  └─> 7.1: Graphiti + Ollama
        ├─> 7.2: Bi-Temporal Model
        └─> 7.3: Memory Router
              ├─> 7.4: Memory Agent
              ├─> 7.5: Consolidation
              └─> 7.6: API Endpoints
```

---

## Success Criteria

### Functional Requirements

- [ ] Graphiti initializes with Ollama (zero OpenAI calls)
- [ ] Episodes can be added with bi-temporal tracking
- [ ] Point-in-time queries return historical context
- [ ] Memory Router selects correct layer >85% accuracy
- [ ] Memory Agent integrates with LangGraph coordinator
- [ ] Consolidation pipeline runs in background
- [ ] 80%+ test coverage

### Performance Benchmarks

| Operation | Target | Acceptance |
|-----------|--------|------------|
| Redis retrieval | <10ms | <20ms |
| Qdrant retrieval | <50ms | <100ms |
| Graphiti retrieval | <100ms | <200ms |
| Memory consolidation | <5s per batch | <10s |
| Point-in-time query | <200ms | <400ms |

### Quality Metrics

| Metric | Target | Minimum |
|--------|--------|---------|
| Routing accuracy | >90% | >85% |
| Memory recall | >80% | >70% |
| Test coverage | >85% | >80% |

---

## Risk Assessment

### High Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Graphiti Ollama integration issues | High | High | Custom LLMClient abstraction, fallback to Azure |
| Neo4j schema conflicts with Sprint 6 | Medium | High | Careful schema planning, separate Graphiti namespace |
| Memory Router accuracy | Medium | Medium | Rule-based + optional LLM, iterative improvement |

### Medium Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Consolidation background task failures | Medium | Medium | Error handling, retry logic, monitoring |
| Redis memory overflow | Low | Medium | TTL policies, max memory config, eviction |
| Graphiti performance at scale | Medium | Medium | Batch operations, async execution |

---

## Definition of Done

For each feature:

- [ ] Code complete and matches acceptance criteria
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests with real dependencies
- [ ] Code review completed
- [ ] Documentation (docstrings, API docs)
- [ ] Performance benchmarks met
- [ ] Security validation (Bandit scan)
- [ ] CI/CD passing (all jobs green)
- [ ] Git commit follows template
- [ ] Manual testing completed

---

## Post-Sprint 7: Next Steps

### Sprint 8 Preview

**Goal:** Memory optimization and A/B testing

**Planned Features:**
- Memory decay strategies
- Memory eviction policies
- Ollama vs Azure OpenAI A/B testing
- Memory health monitoring
- Performance optimization

---

**Sprint 7 Status:** Planning → Ready to Start

**Prerequisites Checklist:**
- [ ] Sprint 6 complete ✅
- [ ] Neo4j running with Sprint 6 schema
- [ ] Ollama llama3.2:8b + nomic-embed-text available
- [ ] Redis running
- [ ] Qdrant running
- [ ] CI pipeline issues resolved (Docker Build + Integration Tests)

**Estimated Start:** After CI pipeline resolution
**Estimated Duration:** 1-2 weeks
**Story Points:** 42

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
