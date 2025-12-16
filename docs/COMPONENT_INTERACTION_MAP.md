# COMPONENT INTERACTION MAP
**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Purpose:** Complete data flow documentation - how components communicate
**Last Updated:** 2025-12-08 (Sprint 37 - Streaming Pipeline Architecture)

---

## 📋 TABLE OF CONTENTS

1. [System Overview](#system-overview)
2. [Request Flow Scenarios](#request-flow-scenarios)
3. [Component Details](#component-details)
4. [API Contracts](#api-contracts)
5. [Data Flow Diagrams](#data-flow-diagrams)

---

## 🎯 SYSTEM OVERVIEW

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────────────┐
│                         AEGIS RAG System                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────┐          │
│  │   React Frontend (Port 5173)                        │          │
│  │   (Sprint 15 SSE, Sprint 28 Perplexity UX)          │          │
│  │   Components:                                        │          │
│  │   - SearchResultsPage (SSE streaming)               │          │
│  │   - StreamingAnswer (custom ReactMarkdown)          │          │
│  │   - Citation (inline [1][2][3] with tooltips)       │          │
│  │   - FollowUpQuestions (grid layout, responsive)     │          │
│  │   - Settings (tabbed UI, localStorage)              │          │
│  │   - SettingsContext (React Context API)             │          │
│  └──────────────┬───────────────────────────────────────┘          │
│                 │ HTTP POST /api/v1/chat (SSE)                     │
│                 ▼                                                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              FastAPI Backend (Port 8000)                      │  │
│  │  ┌────────────┐  ┌──────────────┐  ┌──────────────┐         │  │
│  │  │ Health API │  │ Retrieval API│  │ Graph Viz API│         │  │
│  │  │ (Sprint 2) │  │  (Sprint 2)  │  │ (Sprint 12)  │         │  │
│  │  │            │  │              │  │ Frontend:    │         │  │
│  │  │            │  │              │  │ Sprint 29 🚧 │         │  │
│  │  └────────────┘  └──────┬───────┘  └──────────────┘         │  │
│  └─────────────────────────┼──────────────────────────────────────┘  │
│                            │                                         │
│                            ▼                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │          LangGraph Multi-Agent Orchestration                  │  │
│  │                     (Sprint 4-9)                              │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │  │
│  │  │ Router  │→ │ Vector  │  │  Graph  │  │ Memory  │         │  │
│  │  │  Agent  │  │  Agent  │  │  Agent  │  │  Agent  │         │  │
│  │  └─────────┘  └────┬────┘  └────┬────┘  └────┬────┘         │  │
│  │                    │            │            │               │  │
│  │               ┌────┴────────────┴────────────┴────┐          │  │
│  │               │     Aggregator Node              │          │  │
│  │               └──────────────┬───────────────────┘          │  │
│  └──────────────────────────────┼──────────────────────────────┘  │
│                                 │                                  │
│                                 ▼                                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   Storage Layer                               │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐     │  │
│  │  │  Redis  │  │ Qdrant  │  │ Neo4j   │  │AegisLLMProxy│     │  │
│  │  │(Memory) │  │(Vector) │  │ (Graph) │  │ Multi-Cloud │     │  │
│  │  │Port 6379│  │Port 6333│  │Port 7687│  │ LLM Routing │     │  │
│  │  │         │  │ BGE-M3  │  │         │  │ (ADR-033)   │     │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────────┘     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Communication Patterns

| Source | Target | Protocol | Data Format | Purpose |
|--------|--------|----------|-------------|---------|
| Gradio UI | FastAPI | HTTP/REST | JSON | User queries, document upload |
| FastAPI | LangGraph | Python Call | Pydantic | Agent orchestration |
| LangGraph | Redis | Redis Protocol | Pickled State | State persistence |
| Vector Agent | Qdrant | gRPC/HTTP | Protobuf/JSON | Vector search |
| Vector Agent | BM25 | Python Call | Python objects | Keyword search |
| Graph Agent | LightRAG | Python Call | Python objects | Entity extraction |
| Graph Agent | Neo4j | Bolt Protocol | Cypher queries | Graph traversal, RELATES_TO queries |
| Memory Agent | Redis | Redis Protocol | JSON | Short-term memory |
| Memory Agent | Qdrant | gRPC/HTTP | Protobuf/JSON | Semantic memory |
| Memory Agent | Graphiti | Python Call | Python objects | Episodic memory |
| RelationExtractor | AegisLLMProxy | Python Call | Pydantic | RELATES_TO extraction via Qwen3-32B (Sprint 34) |
| RelationExtractor | Neo4j | Bolt Protocol | Cypher queries | Store RELATES_TO relationships |
| GraphViewer | Neo4j API | HTTP/REST | JSON | Edge filtering, relationship queries |
| All Agents | AegisLLMProxy | Python Call | Pydantic | Multi-cloud LLM routing (Sprint 25) |
| AegisLLMProxy | Ollama/Cloud | HTTP | JSON | LLM inference (local → Alibaba → OpenAI) |
| StreamingPipelineOrchestrator | TypedQueue[ChunkQueueItem] | AsyncIO Queue | Pydantic | Inter-stage chunk communication (Sprint 37) |
| StreamingPipelineOrchestrator | TypedQueue[EmbeddedChunkItem] | AsyncIO Queue | Pydantic | Embedding stage output queue (Sprint 37) |
| Admin UI | FastAPI SSE Endpoint | SSE | JSON | Real-time pipeline progress updates (Sprint 37) |
| Worker Pool | StreamingPipelineOrchestrator | Python Call | Pydantic | Dynamic worker configuration (Sprint 37) |
| EntityDeduplicator | UnifiedEmbeddingService | Python Call | Pydantic | BGE-M3 entity embeddings (Sprint 49.9) |
| EntityDeduplicator | Neo4j | Bolt Protocol | Cypher queries | Merge duplicate entities (Sprint 49) |
| SemanticRelationDeduplicator | UnifiedEmbeddingService | Python Call | Pydantic | BGE-M3 relation type embeddings (Sprint 49.7) |
| SemanticRelationDeduplicator | Redis | Redis Protocol | JSON | Relation type synonym overrides (Sprint 49.8) |
| RelationNormalizer | Neo4j | Bolt Protocol | Cypher queries | Normalize relations, handle symmetry (Sprint 49.3) |
| IndexConsistencyValidator | Qdrant | gRPC/HTTP | Protobuf/JSON | Cross-reference validation (Sprint 49.6) |
| IndexConsistencyValidator | Neo4j | Bolt Protocol | Cypher queries | Entity/relation integrity check (Sprint 49.6) |
| Admin API | Ollama | HTTP | JSON | List available LLM models (Sprint 49.1) |
| Admin API | Neo4j | Bolt Protocol | Cypher queries | List relationship types dynamically (Sprint 49.2) |

---

## 🔄 REQUEST FLOW SCENARIOS

### Scenario 1: Simple Vector Search Query

**User Query:** "What is RAG?"

```
┌─────────────────────────────────────────────────────────────────────┐
│ Flow: Simple Vector Search (Hybrid Mode)                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. User Input                                                      │
│     └─> Gradio UI: Chatbot.submit("What is RAG?")                 │
│                                                                     │
│  2. HTTP Request                                                    │
│     └─> POST http://localhost:8000/api/v1/chat                    │
│         Body: {                                                     │
│           "query": "What is RAG?",                                 │
│           "session_id": "abc123",                                  │
│           "rag_mode": "hybrid"                                     │
│         }                                                          │
│                                                                     │
│  3. FastAPI Handler                                                 │
│     └─> def chat_endpoint(request: ChatRequest)                   │
│         - Validate request (Pydantic)                              │
│         - Extract query, session_id, rag_mode                      │
│                                                                     │
│  4. LangGraph Invocation                                           │
│     └─> graph = create_agent_graph()                              │
│         initial_state = {                                          │
│           "query": "What is RAG?",                                 │
│           "session_id": "abc123",                                  │
│           "rag_mode": "hybrid"                                     │
│         }                                                          │
│         result = await graph.ainvoke(initial_state)                │
│                                                                     │
│  5. Router Agent (Node: route_query)                               │
│     └─> Classify query type                                       │
│         - Input: "What is RAG?"                                    │
│         - LLM Call: AegisLLMProxy (Sprint 25 Feature 25.10)       │
│           proxy = get_aegis_llm_proxy()                            │
│           response = await proxy.complete(                         │
│             prompt="Classify: What is RAG?",                       │
│             quality=QualityRequirement.LOW,  # Router task         │
│             task_type=TaskType.QUERY_UNDERSTANDING                 │
│           )                                                        │
│           # Multi-cloud routing: Local Ollama → Alibaba → OpenAI  │
│         - Response: {"type": "SIMPLE", "intent": "definition"}     │
│         - Decision: Route to Vector Agent (rag_mode=hybrid)        │
│                                                                     │
│  6. Vector Agent (Node: vector_search)                             │
│     └─> Parallel Execution: Vector + BM25                         │
│                                                                     │
│         A. Embedding Generation                                    │
│            └─> UnifiedEmbeddingService.embed("What is RAG?")      │
│                - LRU Cache Check: MISS                             │
│                - Ollama Call: bge-m3 (Sprint 16)                   │
│                  POST http://localhost:11434/api/embeddings        │
│                  Body: {                                           │
│                    "model": "bge-m3",                              │
│                    "prompt": "What is RAG?"                        │
│                  }                                                 │
│                - Response: [0.123, -0.456, ..., 0.789] (1024d)     │
│                - Cache Store: LRU[hash("What is RAG?")] = vector   │
│                                                                     │
│         B. Vector Search (Qdrant)                                  │
│            └─> QdrantClient.search(                               │
│                  collection="aegis-rag-documents",                 │
│                  query_vector=[0.123, -0.456, ..., 0.789],        │
│                  limit=10                                          │
│                )                                                   │
│                gRPC Call: localhost:6334 (or HTTP :6333)           │
│                Response: [                                         │
│                  {                                                 │
│                    "id": "doc1",                                   │
│                    "score": 0.92,                                  │
│                    "payload": {                                    │
│                      "text": "RAG is Retrieval-Augmented...",      │
│                      "source": "rag_overview.md"                   │
│                    }                                               │
│                  },                                                │
│                  ...                                               │
│                ]                                                   │
│                                                                     │
│         C. BM25 Search (Local)                                     │
│            └─> BM25Search.search("What is RAG?", top_k=10)        │
│                - Load index: pickle.load("bm25_index.pkl")         │
│                - Tokenize query: ["what", "rag"]                   │
│                - Compute BM25 scores                               │
│                - Response: [                                       │
│                    {                                               │
│                      "doc_id": "doc2",                             │
│                      "score": 8.5,                                 │
│                      "text": "Retrieval Augmented Generation..."   │
│                    },                                              │
│                    ...                                             │
│                  ]                                                 │
│                                                                     │
│         D. Reciprocal Rank Fusion                                  │
│            └─> RRF.fuse(                                          │
│                  vector_results=[...],                             │
│                  bm25_results=[...],                               │
│                  k=60                                              │
│                )                                                   │
│                Algorithm:                                          │
│                  for each result r in all_results:                 │
│                    score(r) = sum(1 / (k + rank(r, source)))       │
│                Response: [                                         │
│                  {                                                 │
│                    "doc_id": "doc1",                               │
│                    "rrf_score": 0.035,                             │
│                    "text": "RAG is Retrieval-Augmented...",        │
│                    "sources": ["vector", "bm25"]                   │
│                  },                                                │
│                  ...                                               │
│                ]                                                   │
│                                                                     │
│         E. Reranking (Cross-Encoder)                               │
│            └─> Reranker.rerank(                                   │
│                  query="What is RAG?",                             │
│                  candidates=[...]                                  │
│                )                                                   │
│                Model: sentence-transformers/ms-marco-MiniLM        │
│                For each candidate:                                 │
│                  score = cross_encoder(query, candidate.text)      │
│                Response: [                                         │
│                  {                                                 │
│                    "doc_id": "doc1",                               │
│                    "rerank_score": 0.95,                           │
│                    "text": "RAG is Retrieval-Augmented..."         │
│                  },                                                │
│                  ...                                               │
│                ]                                                   │
│                                                                     │
│  7. Aggregator Node (Node: aggregate_results)                      │
│     └─> Synthesize final answer                                   │
│         - Input: Top 5 reranked documents                          │
│         - Context: "RAG is Retrieval-Augmented Generation..."      │
│         - LLM Call: AegisLLMProxy (Sprint 25)                      │
│           proxy = get_aegis_llm_proxy()                            │
│           response = await proxy.complete(                         │
│             prompt="Answer based on context:\n[context]\n\n        │
│                     Question: What is RAG?",                       │
│             quality=QualityRequirement.MEDIUM,  # Generation task  │
│             task_type=TaskType.GENERATION                          │
│           )                                                        │
│           # Routes to local Ollama (llama3.2:8b) if available      │
│         - Response: {                                              │
│             "answer": "RAG (Retrieval-Augmented Generation)...",   │
│             "sources": ["doc1", "doc2"],                           │
│             "metadata": {...}                                      │
│           }                                                        │
│                                                                     │
│  8. State Update (Redis Checkpointer)                              │
│     └─> Save conversation state                                   │
│         Redis SET session:abc123:state <pickled_state>             │
│         TTL: 86400 seconds (24 hours)                              │
│                                                                     │
│  9. HTTP Response                                                   │
│     └─> FastAPI returns:                                          │
│         {                                                          │
│           "answer": "RAG (Retrieval-Augmented Generation)...",     │
│           "sources": [                                             │
│             {"file": "rag_overview.md", "score": 0.95},            │
│             {"file": "llama_index.md", "score": 0.88}              │
│           ],                                                       │
│           "session_id": "abc123",                                  │
│           "metadata": {                                            │
│             "tokens": 150,                                         │
│             "latency_ms": 450,                                     │
│             "rag_mode": "hybrid"                                   │
│           }                                                        │
│         }                                                          │
│                                                                     │
│  10. UI Update                                                      │
│      └─> Gradio displays answer + sources                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Total Latency: ~450ms (with GPU)
- Embedding: 50ms
- Vector Search: 30ms
- BM25 Search: 20ms (parallel)
- RRF Fusion: 10ms
- Reranking: 50ms
- LLM Generation: 250ms (25 tokens @ 105 tokens/s)
- Overhead: 40ms
```

---

### Scenario 2: Graph RAG Query (Relationship Query)

**User Query:** "How are transformers related to attention mechanisms?"

```
┌─────────────────────────────────────────────────────────────────────┐
│ Flow: Graph RAG Query (Entity Relationships)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1-4. [Same as Scenario 1: User Input → FastAPI → LangGraph]       │
│                                                                     │
│  5. Router Agent (Node: route_query)                               │
│     └─> Classify query type                                       │
│         - Input: "How are transformers related to attention?"      │
│         - LLM Classification: "RELATIONSHIP_QUERY"                 │
│         - Decision: Route to Graph Agent                           │
│                                                                     │
│  6. Graph Agent (Node: graph_search)                               │
│     └─> LightRAG Dual-Level Retrieval                             │
│                                                                     │
│         A. Entity Extraction from Query                            │
│            └─> LLM Call: AegisLLMProxy (Sprint 25)                │
│                proxy = get_aegis_llm_proxy()                       │
│                response = await proxy.complete(                    │
│                  prompt="Extract entities:\n                       │
│                          'How are transformers related to          │
│                           attention mechanisms?'",                 │
│                  quality=QualityRequirement.MEDIUM,                │
│                  task_type=TaskType.ENTITY_EXTRACTION              │
│                )                                                   │
│                # Uses extraction-optimized model (gemma-3-4b-it)   │
│                Response: {                                         │
│                  "entities": [                                     │
│                    {"text": "transformers", "type": "MODEL"},      │
│                    {"text": "attention mechanisms", "type":        │
│                     "TECHNIQUE"}                                   │
│                  ]                                                 │
│                }                                                   │
│                                                                     │
│         B. Low-Level Retrieval (Entity Matching)                   │
│            └─> Neo4j Cypher Query                                 │
│                Bolt Connection: localhost:7687                     │
│                Query:                                              │
│                  MATCH (e1:Entity {name: "transformers"})          │
│                  MATCH (e2:Entity {name: "attention mechanisms"})  │
│                  MATCH path = (e1)-[*1..3]-(e2)                    │
│                  RETURN path, relationships(path)                  │
│                  LIMIT 10                                          │
│                                                                     │
│                Response: [                                         │
│                  {                                                 │
│                    "path": [                                       │
│                      {entity: "transformers"},                     │
│                      {rel: "USES", weight: 0.9},                   │
│                      {entity: "attention mechanisms"}              │
│                    ]                                               │
│                  },                                                │
│                  {                                                 │
│                    "path": [                                       │
│                      {entity: "transformers"},                     │
│                      {rel: "COMPONENT_OF", weight: 0.8},           │
│                      {entity: "multi-head attention"},             │
│                      {rel: "IMPLEMENTS", weight: 0.95},            │
│                      {entity: "attention mechanisms"}              │
│                    ]                                               │
│                  }                                                 │
│                ]                                                   │
│                                                                     │
│         C. High-Level Retrieval (Topic/Community Matching)         │
│            └─> Community Detection                                │
│                Neo4j Cypher Query:                                 │
│                  MATCH (e:Entity)-[:BELONGS_TO]->(c:Community)     │
│                  WHERE e.name IN ["transformers",                  │
│                                   "attention mechanisms"]          │
│                  RETURN c.topic, c.summary                         │
│                                                                     │
│                Response: [                                         │
│                  {                                                 │
│                    "topic": "Neural Network Architectures",        │
│                    "summary": "Transformers use attention          │
│                                mechanisms for sequence             │
│                                processing..."                      │
│                  }                                                 │
│                ]                                                   │
│                                                                     │
│         D. Combine Low-Level + High-Level Context                  │
│            └─> Construct graph context:                           │
│                {                                                   │
│                  "entities": ["transformers", "attention"],        │
│                  "relationships": [                                │
│                    "transformers USES attention mechanisms",       │
│                    "transformers COMPONENT_OF multi-head           │
│                     attention"                                     │
│                  ],                                                │
│                  "community_summary": "Neural Network              │
│                    Architectures..."                               │
│                }                                                   │
│                                                                     │
│  7. Aggregator Node (Node: aggregate_results)                      │
│     └─> Synthesize answer with graph context                      │
│         - LLM Call: AegisLLMProxy (Sprint 25)                      │
│         - Context: Graph relationships + community summary         │
│         - Response: "Transformers are fundamentally built on       │
│                      attention mechanisms..."                      │
│                                                                     │
│  8-10. [Same as Scenario 1: State Update → Response → UI]          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Total Latency: ~800ms (with GPU)
- Entity Extraction: 150ms
- Neo4j Low-Level Query: 200ms
- Neo4j High-Level Query: 150ms
- Context Construction: 50ms
- LLM Generation: 250ms
```

---

### Scenario 3: Memory-Augmented Query

**User Query:** "What did we discuss about RAG earlier?" (continuation of Scenario 1)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Flow: Memory-Augmented Query (3-Layer Memory)                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1-5. [Same as previous: User Input → Router]                      │
│       Router classifies as "MEMORY_QUERY"                          │
│                                                                     │
│  6. Memory Agent (Node: memory_search)                             │
│     └─> 3-Layer Memory Lookup (Parallel)                          │
│                                                                     │
│         A. Layer 1: Redis (Short-Term Memory)                      │
│            └─> Redis GET session:abc123:messages                  │
│                Redis Connection: localhost:6379                     │
│                Response: [                                         │
│                  {                                                 │
│                    "role": "user",                                 │
│                    "content": "What is RAG?",                      │
│                    "timestamp": "2025-10-22T10:15:00Z"             │
│                  },                                                │
│                  {                                                 │
│                    "role": "assistant",                            │
│                    "content": "RAG is Retrieval-Augmented...",     │
│                    "timestamp": "2025-10-22T10:15:02Z"             │
│                  }                                                 │
│                ]                                                   │
│                Latency: 5ms                                        │
│                                                                     │
│         B. Layer 2: Qdrant (Semantic Long-Term Memory)             │
│            └─> Embed query: "What did we discuss about RAG?"      │
│                UnifiedEmbeddingService → Ollama bge-m3 (Sprint 16) │
│                Vector: [0.234, -0.567, ...] (1024d)                │
│                                                                     │
│                QdrantClient.search(                                │
│                  collection="conversation-history",                │
│                  query_vector=[0.234, -0.567, ...],                │
│                  limit=5,                                          │
│                  filter={                                          │
│                    "session_id": "abc123",                         │
│                    "timestamp": {"$gte": "2025-10-21T00:00:00Z"}   │
│                  }                                                 │
│                )                                                   │
│                                                                     │
│                Response: [                                         │
│                  {                                                 │
│                    "conversation_id": "conv1",                     │
│                    "score": 0.88,                                  │
│                    "summary": "Discussed RAG definition and        │
│                                use cases"                          │
│                  }                                                 │
│                ]                                                   │
│                Latency: 30ms                                       │
│                                                                     │
│         C. Layer 3: Graphiti (Episodic Temporal Memory)            │
│            └─> Graphiti.search(                                   │
│                  query="RAG discussion",                           │
│                  session_id="abc123",                              │
│                  temporal_filter={                                 │
│                    "valid_time": "2025-10-22T10:00:00Z"            │
│                  }                                                 │
│                )                                                   │
│                                                                     │
│                Neo4j Query (via Graphiti):                         │
│                  MATCH (e:Episode {session_id: "abc123"})          │
│                  WHERE e.valid_from <= timestamp() AND             │
│                        e.valid_to >= timestamp()                   │
│                  MATCH (e)-[:CONTAINS]->(f:Fact)                   │
│                  WHERE f.text CONTAINS "RAG"                       │
│                  RETURN e, f                                       │
│                                                                     │
│                Response: [                                         │
│                  {                                                 │
│                    "episode_id": "ep1",                            │
│                    "facts": [                                      │
│                      "User asked about RAG definition",            │
│                      "Assistant explained RAG components"          │
│                    ],                                              │
│                    "timestamp": "2025-10-22T10:15:00Z"             │
│                  }                                                 │
│                ]                                                   │
│                Latency: 150ms                                      │
│                                                                     │
│         D. Memory Fusion                                           │
│            └─> Combine all 3 layers:                              │
│                {                                                   │
│                  "recent_context": [Redis messages],               │
│                  "similar_conversations": [Qdrant results],        │
│                  "episodic_facts": [Graphiti facts]                │
│                }                                                   │
│                                                                     │
│  7. Aggregator Node                                                │
│     └─> Synthesize answer using memory context                    │
│         - LLM sees recent conversation from Redis                  │
│         - LLM sees similar past conversations from Qdrant          │
│         - LLM sees extracted facts from Graphiti                   │
│         - Response: "Earlier we discussed that RAG is              │
│                      Retrieval-Augmented Generation, which..."     │
│                                                                     │
│  8-10. [State Update → Response → UI]                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Total Latency: ~350ms
- Redis Lookup: 5ms
- Qdrant Lookup: 30ms (parallel)
- Graphiti Lookup: 150ms (parallel)
- Fusion: 15ms
- LLM Generation: 150ms
```

---

### Scenario 4: Document Ingestion Flow

**User Action:** Upload PDF document "transformer_paper.pdf"

```
┌─────────────────────────────────────────────────────────────────────┐
│ Flow: Document Ingestion (Parallel Indexing)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. User Upload                                                     │
│     └─> Gradio UI: File.upload("transformer_paper.pdf")           │
│                                                                     │
│  2. HTTP Request                                                    │
│     └─> POST http://localhost:8000/api/v1/documents/upload        │
│         Content-Type: multipart/form-data                          │
│         File: transformer_paper.pdf (5MB)                          │
│                                                                     │
│  3. FastAPI Handler                                                 │
│     └─> async def upload_document(file: UploadFile)               │
│         - Save to temp: /tmp/transformer_paper.pdf                 │
│         - Validate: PDF, <10MB                                     │
│         - Security: Path traversal check                           │
│                                                                     │
│  4. LangGraph Ingestion Pipeline (Sprint 21-22)                    │
│     └─> create_ingestion_graph().ainvoke(initial_state)          │
│                                                                     │
│         ┌─────────────────────────────────────────────────────┐   │
│         │   Sequential Execution (LangGraph StateGraph)       │   │
│         │   (Memory-optimized: 4.4GB RAM, 6GB VRAM)           │   │
│         ├─────────────────────────────────────────────────────┤   │
│         │                                                     │   │
│         │  Node 1: memory_check_node (5% progress)           │   │
│         │     └─> Check document already indexed             │   │
│         │         Neo4j query: MATCH (d:Document {hash: ...}) │   │
│         │         Decision: Skip if duplicate                 │   │
│         │                                                     │   │
│         │  Node 2: format_routing_node (10% progress)        │   │
│         │     └─> FormatRouter.route(document_path)          │   │
│         │         Decision: Docling vs LlamaIndex            │   │
│         │         30+ formats supported (Sprint 22.3)         │   │
│         │         - Docling: 14 formats (PDF, DOCX, PPTX...) │   │
│         │         - LlamaIndex: 9 formats (CSV, Markdown...) │   │
│         │         - Shared: 7 formats (fallback logic)       │   │
│         │                                                     │   │
│         │  Node 3a: docling_parse_node (30% progress)        │   │
│         │     └─> DoclingContainerClient.parse(pdf)          │   │
│         │         GPU-accelerated OCR (EasyOCR)              │   │
│         │         Table structure preservation (92% accuracy) │   │
│         │         Performance: 420s → 120s (3.5x speedup)    │   │
│         │         Raw text: "Attention Is All You Need..."    │   │
│         │                                                     │   │
│         │  Node 3b: llamaindex_parse_node (fallback)         │   │
│         │     └─> LlamaIndexParser.parse(csv)                │   │
│         │         SimpleDirectoryReader.load_data()           │   │
│         │         Connector library (300+ sources)            │   │
│         │                                                     │   │
│         │  Node 4: chunking_node (45% progress)              │   │
│         │     └─> ChunkingService.chunk(                    │   │
│         │           text=parsed_text,                        │   │
│         │           strategy="adaptive"  # Document-aware    │   │
│         │         )                                          │   │
│         │         Unified chunks with SHA-256 IDs (Sprint 16) │   │
│         │         Chunks: [Chunk(id="a3f2e1d9", text=...)]   │   │
│         │         # 45 chunks created                        │   │
│         │                                                     │   │
│         │  Node 5: embedding_node (75% progress)             │   │
│         │     └─> UnifiedEmbeddingService.embed_batch([     │   │
│         │           "Abstract: The dominant...",             │   │
│         │           "Introduction: Recurrent...",            │   │
│         │           ...  # batch of 32 (Sprint 16)           │   │
│         │         ])                                         │   │
│         │                                                     │   │
│         │         Ollama API Call:                           │   │
│         │         POST http://localhost:11434/api/embeddings │   │
│         │         Body: {                                    │   │
│         │           "model": "bge-m3",  # 1024-dim (Sprint 16) │   │
│         │           "inputs": [...]  # batch of 32           │   │
│         │         }                                          │   │
│         │                                                     │   │
│         │         Response: [                                │   │
│         │           [0.123, -0.456, ...],  # 1024d           │   │
│         │           [0.234, -0.567, ...],                    │   │
│         │           ...                                      │   │
│         │         ]                                          │   │
│         │         Cache: Store in LRU cache                  │   │
│         │                                                     │   │
│         │         Upload to Qdrant + BM25:                   │   │
│         │         QdrantClient.upsert(                       │   │
│         │           collection="aegis-rag-documents",        │   │
│         │           points=[{id, vector, payload}, ...]      │   │
│         │         )                                          │   │
│         │         BM25Search.add_documents([...])            │   │
│         │         Latency: ~2s for 45 chunks                 │   │
│         │                                                     │   │
│         │  Node 6: graph_extraction_node (100% progress)     │   │
│         │     └─> LightRAG Entity Extraction                │   │
│         │         For each chunk:                            │   │
│         │         AegisLLMProxy.complete(                    │   │
│         │           prompt="Extract entities from chunk...", │   │
│         │           quality=QualityRequirement.MEDIUM,       │   │
│         │           task_type=TaskType.ENTITY_EXTRACTION     │   │
│         │         )                                          │   │
│         │         # Uses gemma-3-4b-it (extraction-optimized) │   │
│         │                                                     │   │
│         │         Entities extracted: [                      │   │
│         │           {"text": "Transformer", "type": "MODEL"} │   │
│         │           {"text": "Attention Mechanism", ...}     │   │
│         │         ]                                          │   │
│         │                                                     │   │
│         │         Store in Neo4j:                            │   │
│         │         MERGE (e:Entity {name: "Transformer"})     │   │
│         │         MERGE (s)-[r:USES]->(t)                    │   │
│         │         SET r.weight = 0.9                         │   │
│         │                                                     │   │
│         │         Community Detection:                       │   │
│         │         CALL gds.leiden.stream(...)                │   │
│         │         Latency: ~8s for 45 chunks                 │   │
│         │                                                     │   │
│         └─────────────────────────────────────────────────────┘   │
│                                                                     │
│  5. Progress Tracking                                               │
│     └─> WebSocket updates to UI:                                  │
│         {                                                          │
│           "status": "indexing",                                    │
│           "overall_progress": 0.75,  # 75% complete               │
│           "current_node": "embedding_node",                        │
│           "chunks_processed": 45,                                  │
│           "entities_extracted": 0  # Not yet reached graph node    │
│         }                                                          │
│                                                                     │
│  6. Completion Response                                             │
│     └─> HTTP 200 OK                                               │
│         {                                                          │
│           "status": "success",                                     │
│           "filename": "transformer_paper.pdf",                     │
│           "chunks_created": 45,                                    │
│           "entities_extracted": 87,                                │
│           "relationships_created": 124,                            │
│           "indexing_time_ms": 10000,                               │
│           "doc_hash": "sha256..."                                  │
│         }                                                          │
│                                                                     │
│  7. UI Update                                                       │
│     └─> Gradio shows success message                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Total Latency: ~12s (Sequential LangGraph Pipeline, Sprint 21-22)
- Memory Check: ~100ms (Neo4j query)
- Format Routing: ~50ms (rule-based decision)
- Docling Parse: ~3s (GPU-accelerated OCR)
- Chunking: ~500ms (adaptive strategy)
- Embedding: ~2s (BGE-M3, batch of 32)
- Qdrant + BM25: ~1s (parallel upload)
- Graph Extraction: ~5s (LLM entity extraction + Neo4j)
- Community Detection: ~500ms (Leiden algorithm)

Sprint 21 Improvements:
- 3.5x faster parsing (Docling vs LlamaIndex: 120s vs 420s)
- 95% OCR accuracy (EasyOCR GPU vs 70% LlamaIndex)
- 92% table structure preservation
- 30+ format support (FormatRouter Sprint 22.3)
```

---

### Scenario 5: Unified Re-Indexing with BGE-M3 (Sprint 16)

**Admin Action:** Trigger full re-indexing after BGE-M3 migration

```
┌─────────────────────────────────────────────────────────────────────┐
│ Flow: Unified Re-Indexing (Admin Endpoint)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Admin Request                                                   │
│     └─> POST /api/v1/admin/reindex?confirm=true                   │
│         Headers: Accept: text/event-stream                          │
│                                                                     │
│  2. Phase 1: Initialization (SSE Event)                             │
│     └─> Validate parameters, load document list                    │
│         SSE: {                                                      │
│           "status": "in_progress",                                  │
│           "phase": "initialization",                                │
│           "documents_total": 933                                    │
│         }                                                          │
│                                                                     │
│  3. Phase 2: Atomic Deletion (SSE Event)                            │
│     └─> Delete all indexes (all-or-nothing):                      │
│         A. Qdrant: DELETE collection "aegis-rag-documents"         │
│         B. BM25: DELETE cache "bm25_index.pkl"                     │
│         C. (Neo4j graph deletion pending Feature 16.6)             │
│         SSE: {                                                      │
│           "status": "in_progress",                                  │
│           "phase": "deletion",                                      │
│           "message": "Deleted Qdrant + BM25 indexes"               │
│         }                                                          │
│                                                                     │
│  4. Phase 3: Unified Chunking (SSE Events)                          │
│     └─> For each document (parallel batches of 10):               │
│                                                                     │
│         ChunkingService.chunk(                                      │
│           text=document.text,                                       │
│           strategy="adaptive",  # Document-aware                   │
│           max_tokens=512,                                          │
│           overlap=128                                              │
│         )                                                          │
│           ↓                                                        │
│         Chunks with SHA-256 IDs:                                   │
│         [                                                          │
│           Chunk(                                                   │
│             chunk_id="a3f2e1d9c8b7",  # Deterministic SHA-256     │
│             text="Abstract: The dominant...",                      │
│             source="transformer_paper.pdf",                        │
│             position=0,                                            │
│             tokens=487                                             │
│           ),                                                       │
│           ...                                                      │
│         ]                                                          │
│                                                                     │
│         SSE: {                                                      │
│           "status": "in_progress",                                  │
│           "phase": "chunking",                                      │
│           "documents_processed": 450,                               │
│           "documents_total": 933,                                   │
│           "progress_percent": 48.2,                                 │
│           "eta_seconds": 1200,                                      │
│           "current_document": "transformer_paper.pdf"               │
│         }                                                          │
│                                                                     │
│  5. Phase 4: BGE-M3 Embedding Generation (SSE Events)               │
│     └─> For each chunk (batch of 32):                             │
│                                                                     │
│         UnifiedEmbeddingService.embed_batch([                       │
│           "Abstract: The dominant...",                              │
│           "Introduction: Recurrent...",                             │
│           ...  # 32 chunks                                         │
│         ])                                                         │
│           ↓                                                        │
│         Ollama API Call:                                           │
│         POST http://localhost:11434/api/embed                      │
│         Body: {                                                    │
│           "model": "bge-m3",  # 1024-dim                           │
│           "inputs": [...]                                          │
│         }                                                          │
│           ↓                                                        │
│         Response: [                                                │
│           [0.123, -0.456, ..., 0.789],  # 1024-dim                 │
│           [0.234, -0.567, ..., 0.890],                             │
│           ...                                                      │
│         ]                                                          │
│                                                                     │
│         SSE: {                                                      │
│           "status": "in_progress",                                  │
│           "phase": "embedding",                                     │
│           "chunks_processed": 2800,                                 │
│           "chunks_total": 10000,                                    │
│           "progress_percent": 28.0,                                 │
│           "eta_seconds": 2400                                       │
│         }                                                          │
│                                                                     │
│  6. Phase 5: Multi-Index Insertion (SSE Events)                     │
│     └─> Insert into all indexes (parallel):                       │
│                                                                     │
│         A. Qdrant Insertion                                         │
│            └─> QdrantClient.upsert(                               │
│                  collection="aegis-rag-documents",                  │
│                  points=[                                          │
│                    {                                               │
│                      "id": "a3f2e1d9c8b7",  # SHA-256             │
│                      "vector": [0.123, ..., 0.789],  # 1024-dim    │
│                      "payload": {                                  │
│                        "text": "Abstract: The...",                 │
│                        "source": "transformer_paper.pdf",          │
│                        "chunk_id": "a3f2e1d9c8b7"                  │
│                      }                                             │
│                    },                                              │
│                    ...                                             │
│                  ]                                                 │
│                )                                                   │
│                                                                     │
│         B. BM25 Indexing (Automatic via Qdrant sync)                │
│            └─> BM25 automatically synchronized                    │
│                No separate indexing needed                         │
│                                                                     │
│         C. LightRAG (Feature 16.6 - uses unified chunks)            │
│            └─> Entity extraction per chunk                        │
│                Neo4j stores chunk_id in :MENTIONED_IN              │
│                                                                     │
│         SSE: {                                                      │
│           "status": "in_progress",                                  │
│           "phase": "indexing",                                      │
│           "indexes": {                                             │
│             "qdrant": "complete",                                  │
│             "bm25": "complete",                                    │
│             "neo4j": "pending"                                     │
│           }                                                        │
│         }                                                          │
│                                                                     │
│  7. Phase 6: Validation (SSE Event)                                 │
│     └─> Verify index consistency:                                 │
│         - Qdrant point count == chunk count                        │
│         - BM25 document count == document count                    │
│         - Neo4j entity count > 0                                   │
│                                                                     │
│         SSE: {                                                      │
│           "status": "complete",                                     │
│           "phase": "validation",                                    │
│           "summary": {                                             │
│             "documents_processed": 933,                             │
│             "chunks_created": 10234,                                │
│             "qdrant_points": 10234,                                 │
│             "bm25_docs": 933,                                       │
│             "neo4j_entities": 1587,                                 │
│             "total_time_seconds": 8940,                             │
│             "embedding_model": "bge-m3",                            │
│             "embedding_dim": 1024                                   │
│           }                                                        │
│         }                                                          │
│                                                                     │
│  8. Admin Dashboard Update                                          │
│     └─> Display completion summary                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Total Latency: ~2.5 hours (9,000 seconds)
- Deletion: ~30s (atomic)
- Chunking: ~1,500s (933 docs → 10K chunks)
- Embedding: ~6,000s (10K chunks × 25ms/chunk BGE-M3)
- Indexing: ~1,400s (parallel: Qdrant + BM25)
- Validation: ~10s

Key Improvements (Sprint 16):
- Unified chunks (ChunkingService) → consistent provenance
- BGE-M3 embeddings (1024-dim) → cross-layer similarity
- SSE progress → real-time visibility
- Atomic deletion → no inconsistent state
- Safety checks → confirm=true required
```

---

### Scenario 6: Knowledge Graph Deduplication Pipeline (Sprint 49)

**Admin Action:** Run deduplication after document ingestion to resolve duplicate entities and relations

```
┌─────────────────────────────────────────────────────────────────────┐
│ Flow: Knowledge Graph Deduplication (Entity + Relation Dedup)       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Admin Request                                                   │
│     └─> POST /api/v1/admin/deduplicate-graph?confirm=true         │
│         Headers: Accept: text/event-stream                          │
│                                                                     │
│  2. Phase 1: Data Collection (SSE Event)                            │
│     └─> Load all entities and relations from Neo4j                 │
│         Neo4j Query:                                                │
│         MATCH (e:Entity) RETURN e                                   │
│         MATCH (e1)-[r:RELATES_TO]->(e2) RETURN r                   │
│                                                                     │
│         Response: 1,587 entities, 2,445 relations                   │
│         SSE: {                                                      │
│           "status": "in_progress",                                  │
│           "phase": "data_collection",                               │
│           "entities_loaded": 1587,                                  │
│           "relations_loaded": 2445                                  │
│         }                                                          │
│                                                                     │
│  3. Phase 2: Entity Deduplication (Sprint 49.9) (SSE Events)       │
│     └─> Identify and merge duplicate entities                      │
│                                                                     │
│         A. Batch Embedding Generation                              │
│            └─> UnifiedEmbeddingService.embed_batch([               │
│                  "Transformer",                                     │
│                  "Transformers",  # Similar entity                  │
│                  "TransformerModel",  # Another variant             │
│                  ...  # All 1,587 entity names                      │
│                ])                                                   │
│                                                                     │
│                Ollama API Call (bge-m3):                            │
│                POST http://localhost:11434/api/embeddings          │
│                Response: [                                          │
│                  [0.123, -0.456, ...],  # "Transformer"            │
│                  [0.125, -0.450, ...],  # "Transformers" (similar) │
│                  [0.128, -0.452, ...],  # "TransformerModel"       │
│                  ...                                               │
│                ]                                                   │
│                Latency: 3s for 1,587 entities                       │
│                                                                     │
│         B. Cosine Similarity Computation                            │
│            └─> Compute pairwise similarities                       │
│                For all pairs (e1, e2):                              │
│                  similarity = cosine_distance(embed[e1], embed[e2]) │
│                Results: 2M+ comparisons                             │
│                Latency: 2s (vectorized)                             │
│                                                                     │
│         C. Duplicate Detection (0.85 threshold)                     │
│            └─> Group similar entities                              │
│                Clusters: [                                         │
│                  {                                                 │
│                    "canonical": "Transformer",  # Most frequent     │
│                    "variants": ["Transformers", "TransformerModel"] │
│                    "similarities": [0.88, 0.86]  # >= 0.85          │
│                  },                                                │
│                  ...                                               │
│                ]                                                   │
│                Duplicates Found: 234 entities                       │
│                                                                     │
│         D. Canonical Entity Mapping                                 │
│            └─> Create dedup_map: variant → canonical                │
│                {                                                   │
│                  "Transformers": "Transformer",                     │
│                  "TransformerModel": "Transformer",                 │
│                  "attention head": "Attention Mechanism",           │
│                  ...                                               │
│                }                                                   │
│                                                                     │
│         SSE: {                                                      │
│           "status": "in_progress",                                  │
│           "phase": "entity_deduplication",                          │
│           "duplicates_found": 234,                                  │
│           "similarity_threshold": 0.85,                             │
│           "dedup_map_size": 234                                     │
│         }                                                          │
│                                                                     │
│  4. Phase 3: Relation Extraction & Deduplication (Sprint 49.7)      │
│     └─> Identify and merge duplicate relations                     │
│                                                                     │
│         A. Relation Type Extraction                                 │
│            └─> Extract relation types: [                           │
│                  "USES",                                            │
│                  "uses",  # Variant                                 │
│                  "RELATED_TO",                                      │
│                  "related-to",  # Another variant                   │
│                  ...                                               │
│                ]                                                   │
│                Unique types: 47                                     │
│                                                                     │
│         B. Relation Type Embedding                                  │
│            └─> Embed relation types (BGE-M3)                       │
│                UnifiedEmbeddingService.embed_batch([                │
│                  "USES",                                            │
│                  "uses",                                            │
│                  "RELATED_TO",                                      │
│                  ...                                               │
│                ])                                                   │
│                Response: [0.234, -0.567, ...] per type              │
│                Latency: 200ms                                       │
│                                                                     │
│         C. Hierarchical Clustering (0.88 threshold)                 │
│            └─> Group similar relation types                        │
│                Algorithm: Hierarchical clustering with linkage      │
│                Clusters: [                                         │
│                  {                                                 │
│                    "canonical": "USES",                             │
│                    "variants": ["uses", "USES"],                    │
│                    "similarities": [0.95, 0.99]  # >= 0.88          │
│                  },                                                │
│                  {                                                 │
│                    "canonical": "RELATED_TO",                       │
│                    "variants": ["related-to", "RELATES_TO"],        │
│                    "similarities": [0.91, 0.92]  # >= 0.88          │
│                  },                                                │
│                  ...                                               │
│                ]                                                   │
│                Type synonyms Found: 12                              │
│                                                                     │
│         D. Relation Type Synonym Mapping                            │
│            └─> Create type_synonym_map                              │
│                {                                                   │
│                  "uses": "USES",                                     │
│                  "USES": "USES",                                     │
│                  "related-to": "RELATED_TO",                        │
│                  "RELATES_TO": "RELATED_TO",                        │
│                  ...                                               │
│                }                                                   │
│                Store in Redis (Sprint 49.8):                        │
│                HSET graph:relation-synonyms "uses" "USES"           │
│                                                                     │
│         SSE: {                                                      │
│           "status": "in_progress",                                  │
│           "phase": "relation_deduplication",                        │
│           "type_synonyms_found": 12,                                │
│           "clustering_threshold": 0.88                              │
│         }                                                          │
│                                                                     │
│  5. Phase 4: Relation Normalization (Sprint 49.3)                   │
│     └─> Apply dedup maps to normalize graph                        │
│                                                                     │
│         A. Entity Name Remapping                                    │
│            └─> For each relation:                                  │
│                OLD: (Transformers)-[USES]->(attention head)         │
│                MAP: Transformers → Transformer                      │
│                     attention head → Attention Mechanism            │
│                NEW: (Transformer)-[USES]->(Attention Mechanism)     │
│                                                                     │
│         B. Relation Type Normalization                              │
│            └─> For each relation:                                  │
│                OLD: (source)-[uses]->(target)                       │
│                MAP: uses → USES                                     │
│                NEW: (source)-[USES]->(target)                       │
│                                                                     │
│         C. Symmetric Relation Handling                              │
│            └─> Detect bidirectional relations:                     │
│                MATCH (e1)-[r1:RELATES_TO]->(e2),                   │
│                       (e2)-[r2:RELATES_TO]->(e1)                   │
│                Decision: Keep only one direction (e1→e2)            │
│                Merge weights: weight = (r1.weight + r2.weight)/2   │
│                                                                     │
│         D. Final Deduplication                                      │
│            └─> GROUP BY (source_entity, target_entity, type)        │
│                For duplicates:                                      │
│                  OLD: 2x (Transformer)-[USES]→(Attention)           │
│                       with weights [0.9, 0.85]                      │
│                  NEW: 1x (Transformer)-[USES]→(Attention)           │
│                       with weight = max(0.9, 0.85) = 0.9            │
│                Relations Merged: 156                                 │
│                                                                     │
│         SSE: {                                                      │
│           "status": "in_progress",                                  │
│           "phase": "relation_normalization",                        │
│           "entities_remapped": 234,                                 │
│           "relation_types_normalized": 47,                          │
│           "symmetric_relations_resolved": 45,                       │
│           "relations_merged": 156                                   │
│         }                                                          │
│                                                                     │
│  6. Phase 5: Neo4j Updates (SSE Event)                              │
│     └─> Apply normalized data to Neo4j                             │
│                                                                     │
│         A. Merge Duplicate Entities                                 │
│            └─> For each duplicate cluster:                         │
│                Neo4j Cypher:                                        │
│                MATCH (canonical:Entity {name: "Transformer"})       │
│                MATCH (dup:Entity {name: "Transformers"})            │
│                SET canonical.aliases = ['Transformers']             │
│                MATCH (dup)-[r]->(target)                            │
│                CREATE (canonical)-[COPY OF r]-(target)              │
│                SET canonical.confidence = max(...)                  │
│                DELETE dup                                           │
│                Entities Deleted: 234                                │
│                Entities Updated: 1,353                              │
│                                                                     │
│         B. Normalize Relations                                      │
│            └─> Delete old relations, create normalized ones         │
│                Relations Deleted: 2,445                             │
│                Relations Created: 2,289 (merged + normalized)       │
│                Net Reduction: 156 relations                         │
│                                                                     │
│         SSE: {                                                      │
│           "status": "in_progress",                                  │
│           "phase": "neo4j_update",                                  │
│           "entities_deleted": 234,                                  │
│           "entities_updated": 1353,                                 │
│           "relations_deleted": 2445,                                │
│           "relations_created": 2289                                 │
│         }                                                          │
│                                                                     │
│  7. Phase 6: Index Consistency Validation (Sprint 49.6)             │
│     └─> Verify graph consistency after dedup                       │
│                                                                     │
│         A. Cross-Reference Check                                    │
│            └─> Verify all Neo4j entities are in Qdrant             │
│                For each entity:                                     │
│                  1. Get entity name                                 │
│                  2. Embed name (BGE-M3)                             │
│                  3. Search Qdrant for documents mentioning entity    │
│                  4. Verify MENTIONED_IN relation exists             │
│                                                                     │
│         B. Orphan Detection                                         │
│            └─> Find entities without source chunks                 │
│                Neo4j Query:                                         │
│                MATCH (e:Entity)                                     │
│                WHERE NOT (e)-[:MENTIONED_IN]->()                    │
│                RETURN e                                             │
│                Orphaned Entities: 0                                  │
│                                                                     │
│         C. Validation Report                                        │
│            └─> Generate consistency report:                         │
│                {                                                   │
│                  "consistency_score": 0.98,  # 98% consistent       │
│                  "total_entities": 1353,                            │
│                  "total_relations": 2289,                           │
│                  "orphaned_entities": 0,                            │
│                  "orphaned_chunks": 0,                              │
│                  "status": "healthy"                                │
│                }                                                   │
│                                                                     │
│         SSE: {                                                      │
│           "status": "complete",                                     │
│           "phase": "validation",                                    │
│           "consistency_score": 0.98,                                │
│           "summary": {                                              │
│             "entities_before": 1587,                                │
│             "entities_after": 1353,                                 │
│             "entities_deduplicated": 234,                           │
│             "relations_before": 2445,                               │
│             "relations_after": 2289,                                │
│             "relations_merged": 156,                                │
│             "total_time_seconds": 45,                               │
│             "dedup_status": "success"                               │
│           }                                                        │
│         }                                                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Total Latency: ~45s
- Data Collection: 2s (Neo4j query)
- Entity Embedding: 3s (1,587 entities)
- Similarity Computation: 2s (vectorized)
- Duplicate Detection: 1s (clustering)
- Relation Embedding: 200ms (47 types)
- Clustering: 1s (hierarchical)
- Neo4j Updates: 20s (transaction)
- Validation: 15s (consistency check)

Key Improvements (Sprint 49):
- Entity deduplication via semantic embeddings (0.85 threshold)
- Relation type normalization (0.88 clustering threshold)
- Orphan detection and validation reporting
- Redis synonym overrides for manual curation (Sprint 49.8)
- Atomic transaction rollback on validation failure
```

---

### Scenario 7: Index Consistency Validation (Sprint 49.6)

**Admin Action:** Validate cross-index consistency between Qdrant, Neo4j, and source chunks

```
┌─────────────────────────────────────────────────────────────────────┐
│ Flow: Index Consistency Validation                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Admin Request                                                   │
│     └─> GET /api/v1/admin/validate-consistency                     │
│         Query Params: ?full=true (detailed check) | false (summary) │
│                                                                     │
│  2. Data Collection Phase                                           │
│     └─> Load all indexes in parallel                               │
│                                                                     │
│         A. Qdrant Collection Query                                  │
│            └─> QdrantClient.scroll(                                │
│                  collection="aegis-rag-documents",                  │
│                  limit=10000                                        │
│                )                                                   │
│                Response: [                                         │
│                  {                                                 │
│                    "id": "chunk_abc123",                            │
│                    "vector": [...],                                 │
│                    "payload": {                                    │
│                      "text": "...",                                 │
│                      "source": "doc.pdf",                           │
│                      "chunk_id": "chunk_abc123"                     │
│                    }                                               │
│                  },                                                │
│                  ...                                               │
│                ]                                                   │
│                Total Chunks: 10,234                                 │
│                                                                     │
│         B. Neo4j Entity Query                                       │
│            └─> MATCH (e:Entity) RETURN e                           │
│                Response: 1,353 entities                             │
│                MATCH (e)-[:MENTIONED_IN]->(c:Chunk)                │
│                Response: 2,156 (entity→chunk) links                │
│                                                                     │
│         C. Neo4j Relation Query                                     │
│            └─> MATCH (e1)-[r:RELATES_TO]->(e2)                    │
│                RETURN r                                             │
│                Response: 2,289 relations                            │
│                                                                     │
│  3. Validation Phase 1: Chunk Presence                              │
│     └─> Verify all Neo4j chunks exist in Qdrant                    │
│                                                                     │
│         For each chunk in Neo4j:                                    │
│           1. Check chunk exists in Qdrant (by ID)                   │
│           2. Verify payload consistency (text, source)              │
│           3. Count mismatches                                       │
│                                                                     │
│         Results: {                                                 │
│           "missing_in_qdrant": 0,  # OK                             │
│           "payload_mismatches": 0   # OK                            │
│         }                                                          │
│                                                                     │
│  4. Validation Phase 2: Entity → Chunk Mapping                      │
│     └─> Verify source_chunk_id references (Sprint 49.5)            │
│                                                                     │
│         For each entity:                                            │
│           1. Check MENTIONED_IN relation exists                     │
│           2. Verify target chunk exists in Qdrant                   │
│           3. Verify entity text is in chunk text                    │
│                                                                     │
│         Results: {                                                 │
│           "orphaned_entities": 0,  # Entities with no chunks        │
│           "invalid_mentions": 0    # Chunk references missing       │
│         }                                                          │
│                                                                     │
│  5. Validation Phase 3: Relation Integrity                          │
│     └─> Verify RELATES_TO relations are valid                      │
│                                                                     │
│         For each relation (e1→e2):                                  │
│           1. Verify both entities exist in Neo4j                    │
│           2. Verify both entities have MENTIONED_IN chunks          │
│           3. Verify relation type is valid                          │
│           4. Verify weight in [0, 1]                                │
│                                                                     │
│         Results: {                                                 │
│           "dangling_relations": 0,  # Relations with missing nodes  │
│           "invalid_weights": 0,     # Out of range weights          │
│           "invalid_types": 0        # Unknown relation types        │
│         }                                                          │
│                                                                     │
│  6. Validation Report                                               │
│     └─> Generate detailed report                                   │
│                                                                     │
│         Response: {                                                │
│           "timestamp": "2025-12-16T10:30:00Z",                     │
│           "validation_status": "healthy",                           │
│           "consistency_score": 0.98,                                │
│           "summary": {                                              │
│             "total_chunks": 10234,                                  │
│             "total_entities": 1353,                                 │
│             "total_relations": 2289                                 │
│           },                                                       │
│           "cross_reference_check": {                                │
│             "missing_in_qdrant": 0,                                 │
│             "payload_mismatches": 0,                                │
│             "status": "OK"                                          │
│           },                                                       │
│           "orphaned_check": {                                       │
│             "orphaned_entities": 0,                                 │
│             "orphaned_chunks": 0,                                   │
│             "status": "OK"                                          │
│           },                                                       │
│           "relation_integrity": {                                   │
│             "dangling_relations": 0,                                │
│             "invalid_weights": 0,                                   │
│             "invalid_types": 0,                                     │
│             "status": "OK"                                          │
│           },                                                       │
│           "recommendations": []                                     │
│         }                                                          │
│                                                                     │
│  7. Admin Dashboard Display                                         │
│     └─> Show validation results in Admin UI                        │
│         - Consistency score: 0.98 (green indicator)                 │
│         - All checks: PASS                                          │
│         - Last validated: 2025-12-16 10:30 UTC                     │
│         - Action buttons:                                           │
│           * "Run Full Deduplication" (if score < 0.95)              │
│           * "Export Report" (JSON/CSV)                              │
│           * "Run Again" (manual trigger)                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Total Latency: ~15s
- Data Collection: 3s (parallel queries)
- Chunk Presence: 4s (10K+ checks)
- Entity Mapping: 5s (1.3K+ checks)
- Relation Integrity: 2s (2.3K+ checks)
- Report Generation: 1s (aggregation)

Key Features (Sprint 49.6):
- Cross-reference consistency verification
- Orphaned entity/chunk detection
- Automatic consistency scoring (0-1)
- Detailed diagnostic report
- Actionable recommendations
```

---

### Scenario 8: Dynamic LLM & Relationship Type Discovery (Sprint 49.1-49.2)

**Admin Action:** Configure LLM models and graph relationship types dynamically without code changes

```
┌─────────────────────────────────────────────────────────────────────┐
│ Flow: Dynamic Discovery (LLM Models + Relationship Types)           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Dynamic LLM Model Discovery (Sprint 49.1)                       │
│     └─> GET /api/v1/admin/ollama/models                            │
│                                                                     │
│         A. Query Ollama Available Models                            │
│            └─> OllamaClient.list_models()                          │
│                HTTP GET http://localhost:11434/api/tags            │
│                Response: {                                         │
│                  "models": [                                       │
│                    {                                               │
│                      "name": "llama3.2:8b",                         │
│                      "modified_at": "2025-12-15T...",              │
│                      "size": 4800000000,                            │
│                      "digest": "sha256:abc123..."                   │
│                    },                                              │
│                    {                                               │
│                      "name": "bge-m3",  # Embedding model           │
│                      "modified_at": "2025-12-01T...",              │
│                      "size": 1600000000                             │
│                    },                                              │
│                    {                                               │
│                      "name": "nemotron-mini",  # NEW               │
│                      "modified_at": "2025-12-14T...",              │
│                      "size": 900000000                              │
│                    },                                              │
│                    ...                                             │
│                  ]                                                 │
│                }                                                   │
│                                                                     │
│         B. Filter Generation Models (exclude embeddings)            │
│            └─> Filter by:                                          │
│                - Exclude: bge-m3 (embedding only)                   │
│                - Exclude: ms-marco-minilm (reranker only)           │
│                - Include: Anything else (generation models)         │
│                                                                     │
│                Filtered Models: [                                   │
│                  "llama3.2:8b",       # Current default             │
│                  "nemotron-mini",     # NEW (Sprint 49)             │
│                  "phi3",                                            │
│                  "mistral:7b",                                      │
│                  ...                                               │
│                ]                                                   │
│                                                                     │
│         C. Response to Frontend                                     │
│            └─> {                                                   │
│                  "generation_models": [                             │
│                    {                                               │
│                      "name": "llama3.2:8b",                         │
│                      "size_gb": 4.8,                                │
│                      "type": "generation",                          │
│                      "is_current": true  # Currently selected       │
│                    },                                              │
│                    {                                               │
│                      "name": "nemotron-mini",                       │
│                      "size_gb": 0.9,                                │
│                      "type": "generation",                          │
│                      "is_current": false                            │
│                    },                                              │
│                    ...                                             │
│                  ],                                                │
│                  "embedding_models": [                              │
│                    {                                               │
│                      "name": "bge-m3",                              │
│                      "size_gb": 1.6,                                │
│                      "type": "embedding",                           │
│                      "is_current": true                             │
│                    }                                               │
│                  ]                                                 │
│                }                                                   │
│                                                                     │
│  2. Dynamic Relationship Type Discovery (Sprint 49.2)               │
│     └─> GET /api/v1/admin/graph/relationship-types                 │
│                                                                     │
│         A. Query Neo4j for All Relationship Types                   │
│            └─> CALL db.relationshipTypes()                         │
│                Response: [                                         │
│                  "RELATES_TO",   # Semantic relationships            │
│                  "MENTIONED_IN", # Chunk references                 │
│                  "HAS_SECTION",  # Document structure               │
│                  "USES",         # Entity relationships              │
│                  "COMPONENT_OF",                                     │
│                  "IMPLEMENTS",                                       │
│                  ...                                               │
│                ]                                                   │
│                Total Types: 47                                      │
│                                                                     │
│         B. Compute Relationship Statistics                          │
│            └─> For each relationship type:                         │
│                Neo4j Query:                                         │
│                MATCH ()-[r:RELATES_TO]->()                         │
│                RETURN count(r) as count,                            │
│                       min(r.weight) as min_weight,                  │
│                       max(r.weight) as max_weight,                  │
│                       avg(r.weight) as avg_weight                   │
│                                                                     │
│                Results: {                                          │
│                  "RELATES_TO": {                                    │
│                    "count": 2289,                                   │
│                    "min_weight": 0.65,                              │
│                    "max_weight": 0.99,                              │
│                    "avg_weight": 0.84                               │
│                  },                                                │
│                  "MENTIONED_IN": {                                  │
│                    "count": 3421,                                   │
│                    "min_weight": 1,                                 │
│                    "max_weight": 1,                                 │
│                    "avg_weight": 1.0                                │
│                  },                                                │
│                  ...                                               │
│                }                                                   │
│                                                                     │
│         C. Response to Frontend                                     │
│            └─> {                                                   │
│                  "relationship_types": [                            │
│                    {                                               │
│                      "name": "RELATES_TO",                          │
│                      "count": 2289,                                 │
│                      "weight_range": [0.65, 0.99],                  │
│                      "avg_weight": 0.84,                            │
│                      "color": "#3B82F6",  # Blue (hardcoded)         │
│                      "category": "semantic"                         │
│                    },                                              │
│                    {                                               │
│                      "name": "MENTIONED_IN",                        │
│                      "count": 3421,                                 │
│                      "weight_range": [1.0, 1.0],                    │
│                      "avg_weight": 1.0,                             │
│                      "color": "#9CA3AF",  # Gray                     │
│                      "category": "mention"                          │
│                    },                                              │
│                    {                                               │
│                      "name": "HAS_SECTION",                         │
│                      "count": 934,                                  │
│                      "weight_range": [0.9, 1.0],                    │
│                      "avg_weight": 0.98,                            │
│                      "color": "#10B981",  # Green                    │
│                      "category": "structure"                        │
│                    },                                              │
│                    ...                                             │
│                  ]                                                 │
│                }                                                   │
│                                                                     │
│  3. Admin UI Update                                                 │
│     └─> Populate dropdowns/selects dynamically                     │
│                                                                     │
│         A. LLM Model Selector (Settings Page)                       │
│            └─> <select>                                            │
│                  <option value="llama3.2:8b">                       │
│                    llama3.2:8b (4.8 GB) - Current                   │
│                  </option>                                         │
│                  <option value="nemotron-mini">                     │
│                    nemotron-mini (0.9 GB)                           │
│                  </option>                                         │
│                  ...                                               │
│                </select>                                           │
│                                                                     │
│         B. Relationship Type Multi-Select (Graph Filter)            │
│            └─> <MultiSelect>                                       │
│                  checked: ["RELATES_TO", "MENTIONED_IN", ...]       │
│                  options: [                                        │
│                    "RELATES_TO" (2289 relations),                   │
│                    "MENTIONED_IN" (3421 relations),                 │
│                    "HAS_SECTION" (934 relations),                   │
│                    ...                                             │
│                  ]                                                 │
│                </MultiSelect>                                      │
│                                                                     │
│  4. User Interaction                                                │
│     └─> Admin changes LLM model in dropdown                        │
│         POST /api/v1/admin/settings/llm-model                      │
│         Body: {"model": "nemotron-mini"}                            │
│                                                                     │
│         Response: {"status": "success", "model": "nemotron-mini"}   │
│         Config saved to environment/database                        │
│         Next API call uses nemotron-mini                            │
│                                                                     │
│  5. Benefits of Dynamic Discovery                                   │
│     ✓ No code changes needed to add/remove LLM models               │
│     ✓ Relationship types discovered automatically from graph        │
│     ✓ Users see accurate statistics (count, weights)                │
│     ✓ UI stays current with Neo4j schema evolution                  │
│     ✓ New models available immediately after Ollama pull            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Total Latency: ~500ms
- Ollama Query: 150ms
- Neo4j Relationship Query: 300ms
- Filtering & Aggregation: 50ms

Key Features (Sprint 49.1-49.2):
- Zero hardcoded LLM model list
- Zero hardcoded relationship types
- Real-time discovery from running services
- Automatic filtering of embedding models
- Statistical metadata for each type
```

---

## 🔧 COMPONENT DETAILS

### FastAPI Endpoints

| Endpoint | Method | Purpose | Request | Response |
|----------|--------|---------|---------|----------|
| `/health` | GET | Health check | - | `{"status": "healthy"}` |
| `/ready` | GET | Readiness check | - | `{"ready": true}` |
| `/live` | GET | Liveness check | - | `{"alive": true}` |
| `/api/v1/chat` | POST | Chat query | `ChatRequest` | `ChatResponse` |
| `/api/v1/documents/upload` | POST | Document upload | `multipart/form-data` | `IngestionResponse` |
| `/api/v1/search` | POST | Raw search (no LLM) | `SearchRequest` | `SearchResponse` |
| `/api/v1/graph/export/json` | GET | Export graph as JSON | - | `GraphJSON` |
| `/api/v1/graph/export/graphml` | GET | Export as GraphML | - | `GraphML` |
| `/stats` | GET | System statistics | - | `SystemStats` |
| `/api/v1/admin/deduplicate-graph` | POST | Deduplicate entities + relations (Sprint 49) | `{"confirm": true}` | SSE stream with progress |
| `/api/v1/admin/validate-consistency` | GET | Validate cross-index consistency (Sprint 49.6) | `?full=true` | `ConsistencyReport` |
| `/api/v1/admin/ollama/models` | GET | List available LLM models (Sprint 49.1) | - | `{"generation_models": [...], "embedding_models": [...]}` |
| `/api/v1/admin/graph/relationship-types` | GET | List all relationship types with stats (Sprint 49.2) | - | `{"relationship_types": [...]}` |

### LangGraph State Schema

```python
from pydantic import BaseModel
from typing import List, Dict, Optional

class AgentState(BaseModel):
    """Centralized state for LangGraph agents."""

    # Input
    query: str
    session_id: str
    rag_mode: str  # "vector" | "graph" | "hybrid"

    # Router outputs
    query_type: Optional[str] = None  # "SIMPLE" | "COMPOUND" | "MULTI_HOP" | "MEMORY_QUERY"
    selected_agents: List[str] = []  # ["vector", "graph", "memory"]

    # Agent outputs
    vector_results: List[Dict] = []
    graph_results: List[Dict] = []
    memory_results: List[Dict] = []

    # Aggregation
    final_context: str = ""
    final_answer: str = ""
    sources: List[Dict] = []

    # Metadata
    metadata: Dict = {}
    error: Optional[str] = None
```

### Redis Data Structures

```python
# Session State (LangGraph Checkpointer)
KEY: "session:{session_id}:state"
VALUE: <pickled AgentState>
TTL: 86400 seconds (24 hours)

# Recent Messages (Short-Term Memory)
KEY: "session:{session_id}:messages"
VALUE: [
    {
        "role": "user",
        "content": "What is RAG?",
        "timestamp": "2025-10-22T10:15:00Z"
    },
    {
        "role": "assistant",
        "content": "RAG is...",
        "timestamp": "2025-10-22T10:15:02Z"
    }
]
TTL: 3600 seconds (1 hour)

# Embedding Cache (LRU)
KEY: "embedding:{sha256(text)}"
VALUE: [0.123, -0.456, ..., 0.789]  # 1024d vector (BGE-M3, Sprint 16)
TTL: 604800 seconds (7 days)
```

### Qdrant Collections

```python
# Vector Collection
collection_name = "aegis-rag-documents"
vector_size = 1024  # bge-m3 (Sprint 16)
distance = "Cosine"

# Point Structure
{
    "id": "doc1_chunk1",
    "vector": [0.123, -0.456, ...],  # 1024 dimensions (BGE-M3)
    "payload": {
        "text": "RAG is Retrieval-Augmented Generation...",
        "source": "rag_overview.md",
        "chunk_id": 1,
        "doc_hash": "sha256...",
        "metadata": {
            "document_type": "markdown",
            "date_added": "2025-10-22",
            "tags": ["rag", "llm", "retrieval"]
        }
    }
}

# Conversation History Collection
collection_name = "conversation-history"
vector_size = 1024  # bge-m3 (Sprint 16)

# Point Structure
{
    "id": "conv1",
    "vector": [0.234, -0.567, ...],  # 1024 dimensions (BGE-M3)
    "payload": {
        "session_id": "abc123",
        "summary": "Discussed RAG definition and use cases",
        "timestamp": "2025-10-22T10:15:00Z",
        "turns": 2
    }
}
```

### Sprint 49 Component Details

#### EntityDeduplicator (Sprint 49.9)

**Purpose:** Identify and merge duplicate entities based on semantic similarity

**Interface:**
```python
class EntityDeduplicator:
    async def deduplicate(
        self,
        entities: List[Entity],
        similarity_threshold: float = 0.85
    ) -> DeduplicationResult:
        """
        Deduplicate entities using BGE-M3 embeddings.

        Returns: {
            "canonical_map": Dict[str, str],  # variant → canonical
            "duplicates_found": int,
            "merged_entities": int
        }
        """
```

**Data Flow:**
1. Load all entities from Neo4j
2. Batch embed entity names using BGE-M3 (1024-dim)
3. Compute pairwise cosine similarities (vectorized)
4. Cluster entities with similarity >= 0.85
5. Select canonical entity (most frequent/recent)
6. Return canonical mapping for Phase 4

---

#### SemanticRelationDeduplicator (Sprint 49.7)

**Purpose:** Identify and normalize duplicate relationship types

**Interface:**
```python
class SemanticRelationDeduplicator:
    async def deduplicate_types(
        self,
        relation_types: List[str],
        clustering_threshold: float = 0.88
    ) -> TypeDeduplicationResult:
        """
        Deduplicate relation types using hierarchical clustering.

        Returns: {
            "type_synonym_map": Dict[str, str],  # variant → canonical
            "synonyms_found": int,
            "clusters": List[List[str]]
        }
        """
```

**Data Flow:**
1. Extract all unique relation types from Neo4j
2. Batch embed relation type names using BGE-M3
3. Perform hierarchical clustering (Ward linkage)
4. Group types with similarity >= 0.88
5. Store mapping in Redis for (Sprint 49.8) overrides
6. Return canonical mapping for Phase 4

---

#### RelationNormalizer (Sprint 49.3)

**Purpose:** Apply deduplication maps to normalize graph

**Interface:**
```python
class RelationNormalizer:
    async def normalize_relations(
        self,
        entity_map: Dict[str, str],  # variant → canonical
        type_map: Dict[str, str],    # variant_type → canonical_type
        handle_symmetry: bool = True
    ) -> NormalizationResult:
        """
        Normalize relations using canonical entity and type mappings.

        Returns: {
            "entities_remapped": int,
            "types_normalized": int,
            "symmetric_resolved": int,
            "relations_merged": int
        }
        """
```

**Data Flow:**
1. For each relation in Neo4j:
   - Remap source entity name using entity_map
   - Remap target entity name using entity_map
   - Normalize relation type using type_map
2. Detect bidirectional relations (e1→e2 and e2→e1)
3. Keep only one direction, merge weights
4. Group by (source, target, type), deduplicate
5. Execute atomic transaction to update Neo4j

---

#### IndexConsistencyValidator (Sprint 49.6)

**Purpose:** Validate cross-index consistency between Qdrant, Neo4j, and chunks

**Interface:**
```python
class IndexConsistencyValidator:
    async def validate_consistency(
        self,
        full_check: bool = False
    ) -> ConsistencyReport:
        """
        Validate index consistency across all stores.

        Returns: {
            "consistency_score": float,  # 0-1
            "total_chunks": int,
            "total_entities": int,
            "total_relations": int,
            "issues": {
                "orphaned_entities": List[str],
                "orphaned_chunks": List[str],
                "dangling_relations": List[Tuple[str, str, str]],
                "missing_in_qdrant": List[str]
            },
            "status": "healthy" | "warning" | "error"
        }
        """
```

**Data Flow:**
1. Load all chunks from Qdrant (chunk_id, text, source)
2. Load all entities from Neo4j (entity_id, name)
3. Load all MENTIONED_IN links (entity→chunk)
4. Verify chunk presence: for each entity link, check chunk exists in Qdrant
5. Detect orphaned entities: entities with no MENTIONED_IN links
6. Verify relation integrity: all referenced entities exist, weights valid
7. Generate consistency score: (total_checks - failures) / total_checks
8. Return detailed report with recommendations

---

### Neo4j Graph Schema

```cypher
// Entity Node
(:Entity {
    name: "Transformer",
    type: "MODEL",
    source: "transformer_paper.pdf",
    first_seen: "2025-10-22T10:15:00Z",
    confidence: 0.95
})

// Relationship Types (Sprint 34)
// 1. RELATES_TO: Semantic relationships (blue #3B82F6)
(:Entity {name: "Transformer"})-[:RELATES_TO {weight: 0.92, extraction_method: "llm"}]->(:Entity {name: "Attention Mechanism"})

// 2. MENTIONED_IN: Chunk references (gray #9CA3AF)
(:Entity {name: "Transformer"})-[:MENTIONED_IN {frequency: 15}]->(:Chunk {id: "chunk_abc123"})

// 3. HAS_SECTION: Document structure (green #10B981)
(:Document {id: "doc_123"})-[:HAS_SECTION]->(:Section {title: "Introduction", page: 1})

// Community Node
(:Community {
    id: "community1",
    topic: "Transformer Architecture",
    summary: "Models and techniques for transformer-based architectures",
    size: 15,
    created: "2025-10-22T10:15:00Z"
})

// Membership
(:Entity {name: "Transformer"})-[:BELONGS_TO]->(:Community {id: "community1"})

// Section Node (Sprint 34)
(:Section {
    id: "section_123",
    title: "Load Balancing",
    document_id: "doc_456",
    page: 2,
    level: 1  # Heading level
})
(:Section {id: "section_123"})-[:PARENT]->(:Document {id: "doc_456"})

// Graphiti Episodic Memory (via Graphiti SDK)
(:Episode {
    session_id: "abc123",
    valid_from: "2025-10-22T10:15:00Z",
    valid_to: "9999-12-31T23:59:59Z",  # Still valid
    transaction_time: "2025-10-22T10:15:00Z"
})-[:CONTAINS]->(:Fact {
    text: "User asked about RAG definition",
    confidence: 0.9
})
```

---

## 📊 API CONTRACTS

### ChatRequest (POST /api/v1/chat)

```json
{
  "query": "What is RAG?",
  "session_id": "abc123",  // Optional, generated if missing
  "rag_mode": "hybrid",    // "vector" | "graph" | "hybrid"
  "options": {
    "top_k": 5,
    "temperature": 0.7,
    "model": "llama3.2:8b"
  }
}
```

### ChatResponse

```json
{
  "answer": "RAG (Retrieval-Augmented Generation) is a technique...",
  "sources": [
    {
      "file": "rag_overview.md",
      "chunk_id": 1,
      "score": 0.95,
      "text": "RAG is Retrieval-Augmented Generation..."
    },
    {
      "file": "llama_index.md",
      "chunk_id": 3,
      "score": 0.88,
      "text": "LlamaIndex implements RAG patterns..."
    }
  ],
  "session_id": "abc123",
  "metadata": {
    "tokens": 150,
    "latency_ms": 450,
    "rag_mode": "hybrid",
    "agents_used": ["router", "vector", "aggregator"],
    "model": "llama3.2:8b"
  }
}
```

### IngestionResponse (POST /api/v1/documents/upload)

```json
{
  "status": "success",
  "filename": "transformer_paper.pdf",
  "chunks_created": 45,
  "entities_extracted": 87,
  "relationships_created": 124,
  "indexing_time_ms": 10000,
  "doc_hash": "sha256:abc123...",
  "collections_updated": ["aegis-rag-documents", "conversation-history"]
}
```

---

## 🎯 EMBEDDING MODEL CONSOLIDATION (Sprint 49)

### Overview

Sprint 49 consolidates all embedding tasks to use BGE-M3 (1024-dim), removing dependency on sentence-transformers for entity deduplication and relation type clustering.

**Before Sprint 49:**
- Query embeddings: BGE-M3 (Ollama)
- Document chunk embeddings: BGE-M3 (Ollama)
- Entity deduplication: sentence-transformers/all-MiniLM-L6-v2
- Reranking: sentence-transformers/ms-marco-MiniLM (removed in Sprint 48)

**After Sprint 49:**
- Query embeddings: BGE-M3 (Ollama)
- Document chunk embeddings: BGE-M3 (Ollama)
- Entity deduplication: BGE-M3 (Ollama) - NEW
- Relation type clustering: BGE-M3 (Ollama) - NEW

### Unified Embedding Flow

```
┌─────────────────────────────────────────┐
│  UnifiedEmbeddingService                │
│  (All embedding tasks route here)       │
├─────────────────────────────────────────┤
│                                         │
│  embed(text: str) → [1024d vector]     │
│  embed_batch(texts: List[str])          │
│                 → List[[1024d vector]]  │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ LRU Cache (SHA-256 hash key)    │   │
│  │ - Query embedding hits          │   │
│  │ - Entity name embedding hits    │   │
│  │ - Relation type embedding hits  │   │
│  └────────┬────────────────────────┘   │
│           │ cache miss                  │
│           ▼                             │
│  ┌─────────────────────────────────┐   │
│  │ Ollama API (localhost:11434)    │   │
│  │ POST /api/embeddings            │   │
│  │ - model: "bge-m3"               │   │
│  │ - inputs: batch of texts        │   │
│  │ Response: List[1024d vector]    │   │
│  └─────────────────────────────────┘   │
│           │                             │
│           ▼                             │
│  ┌─────────────────────────────────┐   │
│  │ Cache Store                     │   │
│  │ Redis key: embedding:{hash}     │   │
│  │ TTL: 7 days                     │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

### Usage by Component

#### 1. Query Embedding (existing)
```
User Query → UnifiedEmbeddingService.embed()
  → Cache: embedding:{hash("What is RAG?")}
  → Hit? Return cached vector
  → Miss? Call Ollama → Cache → Return
  → Use vector for Qdrant search
  → Latency: 50ms (miss), 5ms (hit)
```

#### 2. Document Chunk Embedding (existing)
```
Document Chunk → UnifiedEmbeddingService.embed_batch()
  → Batch of 32 chunks
  → Call Ollama once (not 32 times)
  → Cache each result
  → Use vectors for Qdrant insert
  → Latency: ~2s for 45 chunks
```

#### 3. Entity Name Embedding (NEW - Sprint 49.9)
```
Entity Deduplicator:
  Load all entities: [
    "Transformer",
    "Transformers",
    "TransformerModel",
    ...
  ]
  │
  ├─ Check cache for each entity name
  ├─ Batch embed cache misses
  ├─ Store cache hits + new embeddings
  │
  ▼ Embeddings: [[0.123, ...], [0.125, ...], ...]
  │
  ├─ Compute pairwise cosine similarities
  ├─ Cluster at similarity >= 0.85
  ├─ Create canonical mapping
  │
  ▼ Dedup results
```

#### 4. Relation Type Embedding (NEW - Sprint 49.7)
```
SemanticRelationDeduplicator:
  Load all relation types: [
    "USES",
    "uses",
    "RELATED_TO",
    "related-to",
    ...
  ]
  │
  ├─ Check cache for each type
  ├─ Batch embed cache misses
  ├─ Store cache hits + new embeddings
  │
  ▼ Embeddings: [[0.234, ...], [0.235, ...], ...]
  │
  ├─ Perform hierarchical clustering (Ward)
  ├─ Group at similarity >= 0.88
  ├─ Create type synonym mapping
  │
  ▼ Type synonym results
```

### Performance Characteristics

| Task | Items | Batch Size | Latency | Bottleneck |
|------|-------|-----------|---------|-----------|
| Query Embedding | 1 | 1 | 50ms | Ollama |
| Chunk Embedding | 10K | 32 | 2s | Ollama (10K * 25ms) |
| Entity Embedding | 1.5K | 32 | 3s | Ollama (1.5K * 2ms) |
| Entity Similarity | 1.5K | N/A | 2s | Vectorized cosine |
| Type Embedding | 47 | 32 | 200ms | Ollama |
| Type Clustering | 47 | N/A | 1s | Hierarchical clustering |

### Cache Hit/Miss Rates

**Query Embeddings:**
- Cache hit rate: ~60% (same questions asked multiple times)
- Miss rate: ~40% (new queries)
- Impact: 60% of queries save 45ms

**Entity Name Embeddings:**
- Cache hit rate: ~20% (incremental ingestion)
- Miss rate: ~80% (new entities from documents)
- Impact: Mostly miss, but amortized cost via batch embedding

**Relation Type Embeddings:**
- Cache hit rate: ~95% (stable set of types)
- Miss rate: ~5% (occasional new relation types from LLM)
- Impact: After first dedup, subsequent runs cache-hit for all types

### Removed Dependencies

**sentence-transformers/all-MiniLM-L6-v2**
- Used for: Entity deduplication (Sprint 48)
- Size: 80MB
- Latency: 30ms per entity
- Reason for removal: BGE-M3 is superior (multilingual, 1024-dim)
- Migration: Replace with BGE-M3 batch embedding in EntityDeduplicator

**sentence-transformers/ms-marco-MiniLM**
- Used for: Reranking (Sprint 48)
- Size: 90MB
- Status: Already removed in Sprint 48
- Reason: LLM-based generation provides better quality

### Benefits of Consolidation

1. **Single embedding model:** BGE-M3 (multilingual, 1024-dim, cross-encoder)
2. **Reduced memory footprint:** No need to load multiple transformer models
3. **Consistent embeddings:** All text embedded the same way (semantic consistency)
4. **Better performance:** BGE-M3 > sentence-transformers for multilingual + dense retrieval
5. **Simpler operations:** Manage one model instead of multiple
6. **Cost reduction:** Single Ollama model loaded, not multiple models

---

## 🎯 KEY TAKEAWAYS

### Critical Data Paths
1. **User Query → LLM Response:** ~400ms (simple), ~800ms (graph), ~350ms (memory)
2. **Document Upload → Indexed:** ~10s (parallel), ~22s (sequential)
3. **Embedding Generation:** ~50ms (cache miss), ~5ms (cache hit)
4. **Redis State Persistence:** <10ms
5. **Neo4j Graph Query:** ~200ms (low-level), ~500ms (high-level)

### Performance Bottlenecks
1. **Entity Extraction:** Slowest part of ingestion (~8s for 45 chunks)
2. **Community Detection:** ~2s per run
3. **LLM Generation:** ~250ms (GPU), ~3.5s (CPU)

### Optimization Strategies
1. **Parallel Indexing:** 2.25x speedup (Sprint 11)
2. **LRU Embedding Cache:** 60% hit rate, ~90% latency reduction
3. **GPU Acceleration:** 15-20x LLM speedup (Sprint 11)
4. **Batch Embedding:** Process 10 chunks at once

---

## 🚀 PLANNED: Graph Visualization Frontend (Sprint 29)

**Status:** 📋 PLANNED (36 SP, 7-9 days estimated)
**Sprint:** Sprint 29
**Plan Document:** [SPRINT_29_PLAN.md](sprints/SPRINT_29_PLAN.md)

### Overview

Sprint 29 will deliver comprehensive graph visualization frontend for AegisRAG's knowledge graph, enabling end users to explore query results visually and admins to analyze the entire knowledge graph with community detection.

**Technology Stack:**
- **Library:** `react-force-graph` (2D mode with WebGL)
- **API:** Existing Graph Viz API from Sprint 12 (`/api/v1/graph/viz/*`)
- **Styling:** Tailwind CSS + Lucide Icons

### Planned Features (7 Use Cases)

#### 1. Query Result Graph (End User)
**Feature 29.2 (3 SP):** View entities and relationships from query results
- "View Graph" button in StreamingAnswer component
- Modal with interactive graph of entities from retrieved context
- Highlights entities mentioned in answer
- Example: Query "How are transformers related to attention?" → Shows Transformer → USES → Attention Mechanism

#### 2. Admin Graph Analytics
**Feature 29.3 (5 SP):** Admin-only page at `/admin/graph`
- Full knowledge graph visualization (up to 500 nodes)
- Advanced filters: Entity types, minimum degree, max nodes
- Community highlighting
- Graph statistics: Node count, edge count, avg degree

#### 3. Knowledge Graph Dashboard
**Feature 29.4 (5 SP):** Graph metrics and insights
- Quick stats: Total nodes, edges, communities, avg degree
- Entity type distribution (pie chart)
- Graph growth timeline (line chart, last 30 days)
- Top 10 communities by size
- Health metrics: Orphaned nodes, disconnected components

#### 4. Graph Explorer with Search
**Feature 29.5 (5 SP):** Interactive navigation tools
- Node search: Type entity name → graph centers on node with zoom
- Filter by entity type: Show only PERSON, ORGANIZATION, etc.
- Community highlighting: Select community → highlight all members
- Degree filter: Show only highly connected nodes

#### 5. Pan, Zoom, Node Interactions
**Feature 29.1 (5 SP):** Base graph viewer component
- Pan: Click + drag background
- Zoom: Mouse wheel (zoom in/out)
- Node hover: Tooltip with entity name, type, degree
- Node click: Highlight node + connected edges + open details panel
- Performance: 60 FPS with 100+ nodes (WebGL rendering)

#### 6. Embedding-based Document Search
**Feature 29.6 (8 SP):** Find documents from graph nodes
- Click node → Side panel shows "Related Documents"
- Backend: Embed entity name (BGE-M3) → Qdrant vector search
- Display: Top 10 documents with similarity scores
- Click document → Opens document preview
- API: `POST /api/v1/graph/viz/node-documents`

#### 7. Community Document Browser
**Feature 29.7 (5 SP):** Browse documents by community
- Select community → "View Community Documents" button
- Modal shows all documents mentioning entities from community
- Documents grouped by relevance
- Highlights mentioned entities in excerpts
- API: `GET /api/v1/graph/viz/communities/{id}/documents`

### Component Architecture

```
frontend/src/
├── pages/
│   ├── GraphVisualizationPage.tsx        # Main graph page
│   └── admin/
│       └── GraphAnalyticsPage.tsx        # Admin-only page
├── components/
│   ├── graph/
│   │   ├── GraphViewer.tsx               # Core 2D graph (react-force-graph)
│   │   ├── GraphControls.tsx             # Pan/Zoom/Reset controls
│   │   ├── GraphSearch.tsx               # Node search
│   │   ├── CommunityHighlight.tsx        # Community highlighting
│   │   ├── NodeDetailsPanel.tsx          # Selected node info + docs
│   │   ├── CommunityDocuments.tsx        # Community → Documents
│   │   ├── GraphFilters.tsx              # Entity type, degree filters
│   │   └── GraphExportButton.tsx         # Export JSON/GraphML/Cytoscape
│   └── dashboard/
│       ├── KnowledgeGraphDashboard.tsx   # Statistics dashboard
│       ├── GraphStatistics.tsx           # Node/Edge/Community counts
│       └── TopCommunities.tsx            # Top 10 communities
├── api/
│   └── graphViz.ts                       # API client for graph viz
└── hooks/
    ├── useGraphData.ts                   # Fetch graph data
    ├── useGraphSearch.ts                 # Node search logic
    └── useDocumentsByNode.ts             # Embedding-based doc search
```

### API Endpoints

**Existing (Sprint 12):**
- ✅ `POST /api/v1/graph/viz/export` - Export graph (JSON/GraphML/Cytoscape)
- ✅ `GET /api/v1/graph/viz/export/formats` - Supported formats
- ✅ `POST /api/v1/graph/viz/filter` - Filter by entity types/degree
- ✅ `POST /api/v1/graph/viz/communities/highlight` - Highlight communities

**New (Sprint 29):**
- ❌ `POST /api/v1/graph/viz/query-subgraph` - Get entities from query results (Feature 29.2)
- ❌ `GET /api/v1/graph/viz/statistics` - Graph statistics (Feature 29.4)
- ❌ `POST /api/v1/graph/viz/node-documents` - Documents by entity (Feature 29.6)
- ❌ `GET /api/v1/graph/viz/communities/{id}/documents` - Community documents (Feature 29.7)

### Performance Targets

- **Graph Rendering:** <1s for 100 nodes, <3s for 500 nodes
- **Search Latency:** <200ms for node search
- **Document Lookup:** <500ms for embedding-based search
- **Frame Rate:** 60 FPS with pan/zoom (WebGL rendering)

### Success Criteria

- [ ] All 7 features implemented and tested
- [ ] GraphViewer renders 100+ nodes at 60 FPS
- [ ] End users can view query result graphs
- [ ] Admins can explore entire knowledge graph
- [ ] Document search from graph nodes works
- [ ] Community document browser functional
- [ ] Unit test coverage >80%
- [ ] E2E tests pass for all user flows
- [ ] Documentation updated (API docs, user guide)

---

**Last Updated:** 2025-12-16 (Sprint 49 - Knowledge Graph Deduplication)
**Status:** Active Development

**Architecture Changes Since Sprint 16:**
- **Sprint 21-22:** LangGraph ingestion pipeline with Docling CUDA + Format Router
- **Sprint 23:** AegisLLMProxy multi-cloud LLM routing (ADR-033)
- **Sprint 25:** Complete migration to AegisLLMProxy (Feature 25.10)
- **Sprint 28:** Frontend UX enhancements (Perplexity-style interface)
- **Sprint 34:** Knowledge graph enhancement with RELATES_TO relationships and edge visualization
- **Sprint 49:** Knowledge graph deduplication (entity + relation dedup), embedding consolidation, index validation

**Current Architecture (Sprint 49):**
- **Embeddings:** BGE-M3 (1024-dim, Sprint 16) - Unified for all embedding tasks (query, chunks, dedup, relations)
- **LLM Routing:** AegisLLMProxy (Local Ollama → Alibaba Cloud → OpenAI)
- **Search Strategy:** Hybrid (Vector BGE-M3 + BM25 Keyword + RRF Fusion)
- **Graph Relationships:** RELATES_TO (semantic), MENTIONED_IN (chunk refs + source_chunk_id), HAS_SECTION (document structure)
- **Entity Deduplication:** BGE-M3 embeddings + cosine similarity (0.85 threshold) - Sprint 49.9
- **Relation Deduplication:** Hierarchical clustering (0.88 threshold) + type synonym mapping - Sprint 49.7
- **Relation Normalization:** Entity remapping + symmetric handling + dedup by (source, target, type)
- **Index Validation:** Cross-reference consistency check + orphaned entity/chunk detection - Sprint 49.6
- **Edge Visualization:** Color-coded by type (Blue: RELATES_TO, Gray: MENTIONED_IN, Green: HAS_SECTION)
- **Ingestion:** LangGraph pipeline (Docling primary, LlamaIndex fallback)
- **Document Formats:** 30+ formats (FormatRouter Sprint 22.3)
- **Relation Extraction:** Pure LLM via AegisLLMProxy (Alibaba Cloud Qwen3-32B)
- **Dynamic Discovery:** LLM model list + relationship types from Neo4j (Sprint 49.1-49.2)

**Next:** Sprint 50 (Continued graph optimization and scalability improvements)
