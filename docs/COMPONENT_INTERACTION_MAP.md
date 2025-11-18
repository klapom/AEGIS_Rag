# COMPONENT INTERACTION MAP
**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Purpose:** Complete data flow documentation - how components communicate
**Last Updated:** 2025-11-18 (Sprint 28 - Frontend UX Enhancements)

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
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │  │
│  │  │  Redis  │  │ Qdrant  │  │ Neo4j   │  │ Ollama  │         │  │
│  │  │(Memory) │  │(Vector) │  │ (Graph) │  │  (LLM)  │         │  │
│  │  │Port 6379│  │Port 6333│  │Port 7687│  │Port     │         │  │
│  │  │         │  │         │  │         │  │ 11434   │         │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘         │  │
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
| Graph Agent | Neo4j | Bolt Protocol | Cypher queries | Graph traversal |
| Memory Agent | Redis | Redis Protocol | JSON | Short-term memory |
| Memory Agent | Qdrant | gRPC/HTTP | Protobuf/JSON | Semantic memory |
| Memory Agent | Graphiti | Python Call | Python objects | Episodic memory |
| All Agents | Ollama | HTTP | JSON | LLM inference |

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
│         - LLM Call: Ollama llama3.2:3b                             │
│           POST http://localhost:11434/api/generate                 │
│           Body: {                                                  │
│             "model": "llama3.2:3b",                                │
│             "prompt": "Classify: What is RAG?",                    │
│             "stream": false                                        │
│           }                                                        │
│         - Response: {"type": "SIMPLE", "intent": "definition"}     │
│         - Decision: Route to Vector Agent (rag_mode=hybrid)        │
│                                                                     │
│  6. Vector Agent (Node: vector_search)                             │
│     └─> Parallel Execution: Vector + BM25                         │
│                                                                     │
│         A. Embedding Generation                                    │
│            └─> EmbeddingService.get_embedding("What is RAG?")     │
│                - LRU Cache Check: MISS                             │
│                - Ollama Call: nomic-embed-text                     │
│                  POST http://localhost:11434/api/embeddings        │
│                  Body: {                                           │
│                    "model": "nomic-embed-text",                    │
│                    "prompt": "What is RAG?"                        │
│                  }                                                 │
│                - Response: [0.123, -0.456, ..., 0.789] (768d)      │
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
│         - LLM Call: Ollama llama3.2:8b                             │
│           POST http://localhost:11434/api/generate                 │
│           Body: {                                                  │
│             "model": "llama3.2:8b",                                │
│             "prompt": "Answer based on context:\n[context]\n\n     │
│                        Question: What is RAG?",                    │
│             "stream": false                                        │
│           }                                                        │
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
│            └─> LLM Call: Ollama qwen3:0.6b                        │
│                POST http://localhost:11434/api/generate            │
│                Body: {                                             │
│                  "model": "qwen3:0.6b",                            │
│                  "prompt": "Extract entities:\n                    │
│                             'How are transformers related to       │
│                              attention mechanisms?'",              │
│                  "stream": false                                   │
│                }                                                   │
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
│         - LLM Call: Ollama llama3.2:8b                             │
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
│                EmbeddingService → Ollama nomic-embed-text          │
│                Vector: [0.234, -0.567, ...]                        │
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
│  4. Unified Ingestion Pipeline (Parallel)                          │
│     └─> UnifiedIngestionPipeline.ingest(file_path, mode="all")   │
│                                                                     │
│         ┌─────────────────────────────────────────────────────┐   │
│         │   Parallel Execution (asyncio.gather)               │   │
│         ├─────────────────────────────────────────────────────┤   │
│         │                                                     │   │
│         │  ┌──────────────────────────────────────────────┐  │   │
│         │  │  Task 1: Qdrant Indexing                     │  │   │
│         │  └──────────────────────────────────────────────┘  │   │
│         │       │                                            │   │
│         │       ▼                                            │   │
│         │  A. Load Document (LlamaIndex)                     │   │
│         │     └─> SimpleDirectoryReader.load_data()         │   │
│         │         PDF Parser: pypdf                          │   │
│         │         Pages: 12                                  │   │
│         │         Text: "Attention Is All You Need..."       │   │
│         │                                                     │   │
│         │  B. Chunk Text (Adaptive Chunking)                 │   │
│         │     └─> AdaptiveChunker.chunk(                    │   │
│         │           text=doc_text,                           │   │
│         │           strategy="paragraph"  # PDF detected     │   │
│         │         )                                          │   │
│         │         Chunks: [                                  │   │
│         │           "Abstract: The dominant...",             │   │
│         │           "Introduction: Recurrent...",            │   │
│         │           ...                                      │   │
│         │         ]  # 45 chunks                             │   │
│         │                                                     │   │
│         │  C. Generate Embeddings (Batch)                    │   │
│         │     └─> For each chunk (parallel batches):        │   │
│         │         EmbeddingService.get_embeddings_batch([    │   │
│         │           "Abstract: The dominant...",             │   │
│         │           "Introduction: Recurrent...",            │   │
│         │           ...                                      │   │
│         │         ])                                         │   │
│         │                                                     │   │
│         │         Ollama API Call:                           │   │
│         │         POST http://localhost:11434/api/embeddings │   │
│         │         Body: {                                    │   │
│         │           "model": "nomic-embed-text",             │   │
│         │           "texts": [...]  # batch of 10            │   │
│         │         }                                          │   │
│         │                                                     │   │
│         │         Response: [                                │   │
│         │           [0.123, -0.456, ...],  # 768d            │   │
│         │           [0.234, -0.567, ...],                    │   │
│         │           ...                                      │   │
│         │         ]                                          │   │
│         │         Cache: Store in LRU cache                  │   │
│         │                                                     │   │
│         │  D. Upload to Qdrant                               │   │
│         │     └─> QdrantClient.upsert(                      │   │
│         │           collection="aegis-rag-documents",        │   │
│         │           points=[                                 │   │
│         │             {                                      │   │
│         │               "id": "doc1_chunk1",                 │   │
│         │               "vector": [0.123, -0.456, ...],      │   │
│         │               "payload": {                         │   │
│         │                 "text": "Abstract: The...",        │   │
│         │                 "source": "transformer_paper.pdf", │   │
│         │                 "chunk_id": 1,                     │   │
│         │                 "doc_hash": "sha256..."            │   │
│         │               }                                    │   │
│         │             },                                     │   │
│         │             ...  # 45 points                       │   │
│         │           ]                                        │   │
│         │         )                                          │   │
│         │         gRPC Call: localhost:6334                  │   │
│         │         Latency: ~2s for 45 chunks                 │   │
│         │                                                     │   │
│         │  ┌──────────────────────────────────────────────┐  │   │
│         │  │  Task 2: BM25 Indexing                       │  │   │
│         │  └──────────────────────────────────────────────┘  │   │
│         │       │                                            │   │
│         │       ▼                                            │   │
│         │  A. Tokenize Chunks                                │   │
│         │     └─> For each chunk:                           │   │
│         │         tokens = tokenize(chunk.text)              │   │
│         │         ["attention", "all", "need", ...]          │   │
│         │                                                     │   │
│         │  B. Update BM25 Index                              │   │
│         │     └─> BM25Search.add_documents([                │   │
│         │           {                                        │   │
│         │             "id": "doc1_chunk1",                   │   │
│         │             "tokens": ["attention", "all", ...],   │   │
│         │             "text": "Abstract: The..."             │   │
│         │           },                                       │   │
│         │           ...  # 45 chunks                         │   │
│         │         ])                                         │   │
│         │                                                     │   │
│         │  C. Save Index to Disk                             │   │
│         │     └─> pickle.dump(bm25_index,                   │   │
│         │                      "data/bm25/bm25_index.pkl")   │   │
│         │         Latency: ~500ms for 45 chunks              │   │
│         │                                                     │   │
│         │  ┌──────────────────────────────────────────────┐  │   │
│         │  │  Task 3: LightRAG Indexing                   │  │   │
│         │  └──────────────────────────────────────────────┘  │   │
│         │       │                                            │   │
│         │       ▼                                            │   │
│         │  A. Entity Extraction (per chunk)                  │   │
│         │     └─> For each chunk:                           │   │
│         │         LLM Call: Ollama llama3.2:3b               │   │
│         │         POST http://localhost:11434/api/generate   │   │
│         │         Body: {                                    │   │
│         │           "model": "llama3.2:3b",                  │   │
│         │           "prompt": "Extract entities from:\n      │   │
│         │                      'Abstract: The dominant...'", │   │
│         │           "stream": false                          │   │
│         │         }                                          │   │
│         │                                                     │   │
│         │         Response: {                                │   │
│         │           "entities": [                            │   │
│         │             {                                      │   │
│         │               "text": "Transformer",               │   │
│         │               "type": "MODEL"                      │   │
│         │             },                                     │   │
│         │             {                                      │   │
│         │               "text": "Attention Mechanism",       │   │
│         │               "type": "TECHNIQUE"                  │   │
│         │             }                                      │   │
│         │           ],                                       │   │
│         │           "relationships": [                       │   │
│         │             {                                      │   │
│         │               "source": "Transformer",             │   │
│         │               "rel": "USES",                       │   │
│         │               "target": "Attention Mechanism"      │   │
│         │             }                                      │   │
│         │           ]                                        │   │
│         │         }                                          │   │
│         │         Latency: ~500ms per chunk × 45 chunks      │   │
│         │                  = 22.5s (parallel batches → 8s)   │   │
│         │                                                     │   │
│         │  B. Store in Neo4j                                 │   │
│         │     └─> For each entity:                          │   │
│         │         Neo4j Cypher:                              │   │
│         │           MERGE (e:Entity {name: "Transformer"})   │   │
│         │           SET e.type = "MODEL",                    │   │
│         │               e.source = "transformer_paper.pdf"   │   │
│         │                                                     │   │
│         │         For each relationship:                     │   │
│         │           MATCH (s:Entity {name: "Transformer"})   │   │
│         │           MATCH (t:Entity {name: "Attention..."})  │   │
│         │           MERGE (s)-[r:USES]->(t)                  │   │
│         │           SET r.weight = 0.9                       │   │
│         │                                                     │   │
│         │         Bolt Connection: localhost:7687            │   │
│         │         Latency: ~3s for 45 chunks                 │   │
│         │                                                     │   │
│         │  C. Community Detection (Post-Indexing)            │   │
│         │     └─> Run Leiden Algorithm (graspologic)        │   │
│         │         Neo4j Cypher:                              │   │
│         │           CALL gds.graph.project(...)              │   │
│         │           CALL gds.leiden.stream(...)              │   │
│         │                                                     │   │
│         │         Communities: [                             │   │
│         │           {                                        │   │
│         │             "id": "community1",                    │   │
│         │             "topic": "Transformer Architecture",   │   │
│         │             "members": [                           │   │
│         │               "Transformer",                       │   │
│         │               "Attention Mechanism",               │   │
│         │               "Multi-Head Attention"               │   │
│         │             ]                                      │   │
│         │           }                                        │   │
│         │         ]                                          │   │
│         │         Latency: ~2s                               │   │
│         │                                                     │   │
│         └─────────────────────────────────────────────────────┘   │
│                                                                     │
│  5. Progress Tracking                                               │
│     └─> WebSocket updates to UI:                                  │
│         {                                                          │
│           "status": "indexing",                                    │
│           "progress": {                                            │
│             "qdrant": "45/45 chunks",                              │
│             "bm25": "45/45 chunks",                                │
│             "lightrag": "30/45 chunks"                             │
│           }                                                        │
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

Total Latency: ~10s (parallel indexing)
- Qdrant: ~2s
- BM25: ~500ms (parallel)
- LightRAG: ~8s (parallel entity extraction)
- Community Detection: ~2s (runs after indexing)

Sequential would be: ~22.5s
Speedup: 2.25x
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
VALUE: [0.123, -0.456, ..., 0.789]  # 768d vector
TTL: 604800 seconds (7 days)
```

### Qdrant Collections

```python
# Vector Collection
collection_name = "aegis-rag-documents"
vector_size = 768  # nomic-embed-text
distance = "Cosine"

# Point Structure
{
    "id": "doc1_chunk1",
    "vector": [0.123, -0.456, ...],  # 768 dimensions
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
vector_size = 768

# Point Structure
{
    "id": "conv1",
    "vector": [0.234, -0.567, ...],
    "payload": {
        "session_id": "abc123",
        "summary": "Discussed RAG definition and use cases",
        "timestamp": "2025-10-22T10:15:00Z",
        "turns": 2
    }
}
```

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

// Relationship
(:Entity {name: "Transformer"})-[:USES {weight: 0.9}]->(:Entity {name: "Attention Mechanism"})

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

**Last Updated:** 2025-10-28 (Sprint 16)
**Status:** Active Development
**Sprint 16 Changes:** Unified chunking, BGE-M3 standardization, admin re-indexing
**Next:** Sprint 17 (TBD)
