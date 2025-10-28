# LightRAG vs Graphiti - Architectural Comparison

**Created:** 2025-10-28 (Sprint 16 Planning)
**Purpose:** Document differences between LightRAG (Layer 2) and Graphiti (Layer 3) to avoid confusion
**Status:** Reference Document

---

## TL;DR

| Aspect | LightRAG (Layer 2) | Graphiti (Layer 3) |
|--------|-------------------|-------------------|
| **Data Model** | Chunk-based | Episode-based |
| **Input** | Chunks (512 tokens) | Full documents |
| **Purpose** | Retrieval (entity-based search) | Episodic Memory (temporal queries) |
| **Entity Extraction** | SpaCy + Gemma 2 4B (optimized) | LLM-based (internal, blackbox) |
| **Performance** | 10x optimized (Sprint 13) | Unknown (needs evaluation) |
| **Neo4j Labels** | `:LightRAGEntity`, `:LightRAGRelation` | `:EntityNode`, `:EpisodeNode`, `:CommunityNode` |
| **Chunk Alignment** | Yes (source_chunk_id) | No (episode-level) |
| **Unified Chunking** | ✅ Consumer of ChunkingService | ❌ Not applicable (episode-based) |

---

## 1. Architecture Overview

### Layer 2: LightRAG (Graph Retrieval)

```
┌──────────────────────────────────────────────────────┐
│ LightRAG - Chunk-Based Graph Retrieval              │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Document                                            │
│      │                                               │
│      ▼                                               │
│  ┌───────────────────────┐                          │
│  │ ChunkingService       │ (Unified, Sprint 16)     │
│  │ • chunk_document()    │                          │
│  └──────┬────────────────┘                          │
│         │                                            │
│         ▼                                            │
│  List[Chunk] (512 tokens, 128 overlap)              │
│         │                                            │
│         ▼                                            │
│  ┌───────────────────────┐                          │
│  │ Entity Extraction     │ (Sprint 13 Optimized)    │
│  │ • Phase 1: SpaCy NER  │ (~50ms/doc)              │
│  │ • Phase 2: Dedup      │ (95% accuracy)           │
│  │ • Phase 3: Gemma 2 4B │ (~2s/doc, quantized)     │
│  └──────┬────────────────┘                          │
│         │                                            │
│         ▼                                            │
│  ┌───────────────────────┐                          │
│  │ Neo4j Storage         │                          │
│  │ (:LightRAGEntity)     │                          │
│  │ • source_chunk_id     │ ✅ Chunk Alignment       │
│  │ • document_id         │                          │
│  │ • chunk_index         │                          │
│  └───────────────────────┘                          │
│                                                      │
│  Use Case: Entity-based retrieval                   │
│  Query: "Find all entities related to 'Klaus'"      │
└──────────────────────────────────────────────────────┘
```

**Code Example:**
```python
# LightRAG Ingestion (Layer 2)
from src.core.chunking_service import get_chunking_service

chunks = get_chunking_service().chunk_document(
    document_id="doc_123",
    content=document.text,
    metadata=document.metadata
)

# Extract entities from chunks (optimized pipeline)
for chunk in chunks:
    entities = await lightrag.extract_entities(chunk.content)
    relations = await lightrag.extract_relations(chunk.content)

    # Store in Neo4j with chunk alignment
    await lightrag.store_entities(
        entities,
        relations,
        source_chunk_id=chunk.chunk_id,  # ✅ Links to Qdrant
        document_id=chunk.document_id,
        chunk_index=chunk.chunk_index
    )
```

**Neo4j Cypher Query:**
```cypher
// LightRAG Query Example
MATCH (e:LightRAGEntity {name: 'Klaus Pommer'})-[r]-(other:LightRAGEntity)
WHERE e.source_chunk_id = 'a3f8e2b1...'  // Chunk-level granularity
RETURN e, r, other
```

---

### Layer 3: Graphiti (Episodic Memory)

```
┌──────────────────────────────────────────────────────┐
│ Graphiti - Episode-Based Temporal Memory            │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Document                                            │
│      │                                               │
│      ▼                                               │
│  ┌───────────────────────┐                          │
│  │ NO CHUNKING!          │                          │
│  │ Full document as      │                          │
│  │ single Episode        │                          │
│  └──────┬────────────────┘                          │
│         │                                            │
│         ▼                                            │
│  episode_body = full_document_text                   │
│         │                                            │
│         ▼                                            │
│  ┌───────────────────────┐                          │
│  │ Entity Extraction     │ (Graphiti Internal)      │
│  │ • LLM-based (BGE-M3)  │ ⚠️ Blackbox, unknown     │
│  │ • Full LLM calls      │    performance           │
│  │ • No SpaCy            │                          │
│  └──────┬────────────────┘                          │
│         │                                            │
│         ▼                                            │
│  ┌───────────────────────┐                          │
│  │ Neo4j Storage         │                          │
│  │ (:EpisodeNode)        │                          │
│  │ • reference_time      │ ✅ Temporal queries      │
│  │ • group_id            │ ✅ Namespacing           │
│  │ • source_description  │                          │
│  │                       │                          │
│  │ (:EntityNode)         │                          │
│  │ • NO chunk_id         │ ❌ Episode-level only    │
│  │ • MENTIONS episode    │                          │
│  └───────────────────────┘                          │
│                                                      │
│  Use Case: Temporal memory                          │
│  Query: "What did Klaus say on 2023-11-15?"         │
└──────────────────────────────────────────────────────┘
```

**Code Example:**
```python
# Graphiti Ingestion (Layer 3)
from src.components.memory.graphiti_wrapper import GraphitiWrapper

graphiti = GraphitiWrapper()

# NO CHUNKING - Full document as episode
await graphiti.add_episode(
    name=f"Document: {document.metadata.get('title')}",
    episode_body=document.text,  # ✅ FULL TEXT, no chunks
    source=EpisodeType.text,
    source_description="OMNITRACKER documentation",
    reference_time=datetime.now(),  # ✅ Temporal context
    group_id="tenant_acme"  # ✅ Multi-tenancy
)

# Graphiti internally:
# 1. Calls LLM to extract entities (unknown performance)
# 2. Creates EntityNodes + EpisodeNode
# 3. Links via MENTIONS edges
# 4. No chunk_id stored
```

**Neo4j Cypher Query:**
```cypher
// Graphiti Query Example
MATCH (episode:EpisodeNode)-[:MENTIONS]->(entity:EntityNode {name: 'Klaus Pommer'})
WHERE episode.reference_time > datetime('2023-11-01')  // Temporal filter
AND episode.group_id = 'tenant_acme'  // Namespace filter
RETURN episode, entity
```

---

## 2. Key Differences

### 2.1 Data Granularity

**LightRAG:**
- **Input:** 512-token chunks (from ChunkingService)
- **Entities stored at chunk-level** (source_chunk_id)
- **Enables precise retrieval:** "This entity was mentioned in chunk 142 of document X"
- **Use case:** Retrieval augmentation (find relevant chunks for RAG)

**Graphiti:**
- **Input:** Full document (no chunking)
- **Entities stored at episode-level** (no chunk_id)
- **Enables temporal queries:** "What entities appeared in documents from November 2023?"
- **Use case:** Episodic memory (conversation history, temporal reasoning)

---

### 2.2 Entity Extraction Performance

**LightRAG (Sprint 13 Optimization):**
```python
# 3-Phase Pipeline (10x faster than baseline)
# Phase 1: SpaCy NER (50ms/doc)
entities = spacy_nlp(text).ents  # Fast, rule-based

# Phase 2: Semantic Deduplication (100ms/batch)
dedup_entities = deduplicate_with_faiss(entities)  # 95% accuracy

# Phase 3: Relation Extraction (2s/doc)
relations = gemma2_4b(text, entities)  # Quantized, local

# Total: ~2.5s per document (300s → 30s improvement)
```

**Graphiti (Unknown Performance):**
```python
# Graphiti Internal (Blackbox)
await graphiti.add_episode(episode_body=text)

# Internally (from documentation):
# 1. Full LLM call for entity extraction (unknown duration)
# 2. Full LLM call for relation extraction (unknown duration)
# 3. Deduplication (unknown strategy)
# 4. Community detection (Leiden algorithm)

# Performance: ⚠️ Unknown, needs benchmarking
# Model: BGE-M3 embeddings (1024-dim)
# Concerns:
#   - No SpaCy pre-filtering (slower?)
#   - Full LLM calls (expensive?)
#   - No quantization mentioned
```

---

### 2.3 Neo4j Schema

**LightRAG Schema:**
```cypher
// Nodes
(:LightRAGEntity {
  name: "Klaus Pommer",
  type: "PERSON",
  source_chunk_id: "a3f8e2b1...",  // ✅ Links to Qdrant
  document_id: "doc_123",
  chunk_index: 42
})

// Edges
(:LightRAGEntity)-[:WORKS_AT]->(:LightRAGEntity {name: "Pommer IT"})
```

**Graphiti Schema:**
```cypher
// Episode Node
(:EpisodeNode {
  uuid: "ep_456",
  name: "Document: OMNITRACKER Manual",
  reference_time: datetime("2023-11-15T10:30:00"),
  group_id: "tenant_acme",
  source_description: "PDF ingestion"
})

// Entity Nodes
(:EntityNode {
  uuid: "ent_789",
  name: "Klaus Pommer",
  summary: "Person mentioned in context of IT consulting",
  created_at: datetime("2023-11-15T10:30:00")
})

// Episode → Entity Link
(:EpisodeNode)-[:MENTIONS]->(:EntityNode)

// Entity → Entity Relations
(:EntityNode)-[:WORKS_AT {
  fact: "Klaus Pommer works at Pommer IT",
  created_at: datetime("2023-11-15T10:30:00")
}]->(:EntityNode {name: "Pommer IT"})

// Communities (Leiden algorithm)
(:CommunityNode {
  uuid: "com_012",
  summary: "IT Consulting cluster"
})-[:CONTAINS]->(:EntityNode)
```

---

### 2.4 Unified Chunking Impact

**LightRAG: ✅ Consumer of ChunkingService**
```python
# Sprint 16 Feature 16.1 - LightRAG uses ChunkingService
chunks = get_chunking_service().chunk_document(
    document_id="doc_123",
    content=document.text
)

# LightRAG extracts entities from unified chunks
for chunk in chunks:
    entities = await lightrag.extract_entities(chunk.content)
    # Store with source_chunk_id for Qdrant alignment
```

**Graphiti: ❌ Not Applicable (Episode-Based)**
```python
# Graphiti does NOT use ChunkingService
# Works at document-level, not chunk-level
await graphiti.add_episode(
    episode_body=document.text,  # Full document, no chunking
    reference_time=datetime.now()
)
```

---

## 3. Concerns & Action Items

### 3.1 Graphiti Performance Blackbox ⚠️

**Problem:**
- Graphiti internally calls LLM for entity extraction (unknown performance)
- No visibility into:
  - LLM model used (BGE-M3 for embeddings, but what about extraction?)
  - Number of LLM calls per episode
  - Token usage (cost implications)
  - Extraction duration (latency)
- LightRAG optimizations (SpaCy, quantized Gemma 2 4B, deduplication) NOT applied

**Risk:**
- Graphiti might be 10-100x slower than LightRAG
- Graphiti might make expensive LLM calls (GPT-4o equivalent)
- No control over extraction quality

---

### 3.2 Proposed Solution: Sprint 16 Feature 16.7

**New Feature: Graphiti Performance Evaluation & Optimization**

**Story Points:** 8 SP (2 days)

**Goal:** Benchmark Graphiti performance and evaluate optimization opportunities

**Tasks:**

**Day 1: Benchmarking (4 SP)**
1. **Benchmark Graphiti Ingestion:**
   - Measure `add_episode()` duration for 100 documents
   - Profile LLM call count and token usage
   - Compare with LightRAG performance (baseline)

2. **Entity Extraction Quality:**
   - Compare Graphiti entities vs LightRAG entities (precision/recall)
   - Evaluate deduplication accuracy
   - Test on OMNITRACKER documents

3. **Memory Profiling:**
   - Peak memory usage during `add_episode()`
   - Compare with LightRAG memory footprint

**Day 2: Optimization Evaluation (4 SP)**
4. **Custom Entity Extractors (Graphiti 0.3.21+):**
   - Research Graphiti's custom entity type API
   - Can we inject SpaCy pre-filtering?
   - Can we use our Gemma 2 4B pipeline?

5. **LLM Configuration:**
   - What LLM does Graphiti use internally? (Check source code)
   - Can we replace with quantized Gemma 2 4B?
   - Can we disable expensive LLM calls?

6. **Document Decision:**
   - If Graphiti is 10x+ slower: Consider alternatives
   - If Graphiti is optimizable: Create ADR-024 for custom extractors
   - If Graphiti is acceptable: Keep as-is

**Acceptance Criteria:**
- [ ] Benchmark report comparing Graphiti vs LightRAG (duration, memory, quality)
- [ ] Document Graphiti internal LLM usage (model, calls, tokens)
- [ ] Evaluate custom entity extractor feasibility
- [ ] Decision: Keep Graphiti / Optimize Graphiti / Replace Graphiti
- [ ] If keep/optimize: Create optimization plan (ADR-024)

**Deliverables:**
- `docs/benchmarks/GRAPHITI_PERFORMANCE_BENCHMARK.md`
- `docs/adr/ADR-024-graphiti-optimization-strategy.md` (if needed)

---

## 4. Recommendations

### 4.1 Short-Term (Sprint 16)

**✅ Proceed with Feature 16.1 (Unified Chunking):**
- Implement ChunkingService for Layer 2 (Qdrant, BM25, LightRAG)
- Leave Graphiti unchanged (episode-based)

**✅ Add Feature 16.7 (Graphiti Evaluation):**
- Schedule at end of Sprint 16 (after 16.1-16.6 complete)
- Benchmark Graphiti performance
- Decide on optimization strategy

**✅ Document LightRAG/Graphiti Differences:**
- This document (LIGHTRAG_VS_GRAPHITI.md)
- Add to architecture documentation index

---

### 4.2 Long-Term (Sprint 17+)

**Option A: Optimize Graphiti (Preferred)**
- Use custom entity extractors to inject SpaCy + Gemma 2 4B
- Reduce LLM calls
- Achieve similar performance to LightRAG

**Option B: Replace Graphiti**
- If optimization not feasible, consider alternatives:
  - Extend LightRAG with temporal features (reference_time, episode nodes)
  - Build custom episodic memory layer
  - Use Neo4j temporal queries directly

**Option C: Keep Graphiti As-Is**
- If performance acceptable (<5s per episode for 10KB documents)
- Accept trade-off: Richer features (communities, namespacing) vs performance

---

## 5. Neo4j Coexistence

### 5.1 Shared Neo4j Database (Current)

**Approach:** LightRAG and Graphiti share same Neo4j instance, different labels

**Advantages:**
- ✅ Single Neo4j deployment
- ✅ Simpler infrastructure
- ✅ Can query across layers (advanced use cases)

**Disadvantages:**
- ⚠️ Label collision risk (must maintain separate namespaces)
- ⚠️ Performance: Mixed workloads in one database
- ⚠️ Backup/restore: All-or-nothing

**Cypher Namespace Strategy:**
```cypher
-- LightRAG queries always filter by label
MATCH (e:LightRAGEntity)-[r:LightRAGRelation]-(other)
WHERE e.source_chunk_id = $chunk_id
RETURN e, r, other

-- Graphiti queries always filter by label
MATCH (ep:EpisodeNode)-[:MENTIONS]->(ent:EntityNode)
WHERE ep.reference_time > $timestamp
RETURN ep, ent
```

---

### 5.2 Separate Neo4j Databases (Recommended)

**Approach:** LightRAG in `neo4j.lightrag`, Graphiti in `neo4j.graphiti`

**Advantages:**
- ✅ Complete isolation (no label conflicts)
- ✅ Independent scaling (e.g., Graphiti needs more memory)
- ✅ Independent backups (can restore LightRAG without Graphiti)
- ✅ Cleaner architecture

**Disadvantages:**
- ⚠️ Two Neo4j connections to manage
- ⚠️ Cannot query across layers (rare use case)

**Configuration:**
```python
# src/core/config.py
class Neo4jConfig:
    # LightRAG (Layer 2)
    LIGHTRAG_URI = "bolt://localhost:7687"
    LIGHTRAG_DATABASE = "lightrag"  # Neo4j database name

    # Graphiti (Layer 3)
    GRAPHITI_URI = "bolt://localhost:7687"
    GRAPHITI_DATABASE = "graphiti"  # Neo4j database name

    # Shared auth
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "password"
```

**Neo4j Multi-Database Setup:**
```cypher
// Create separate databases in Neo4j
CREATE DATABASE lightrag IF NOT EXISTS;
CREATE DATABASE graphiti IF NOT EXISTS;

// Grant access
GRANT ACCESS ON DATABASE lightrag TO neo4j;
GRANT ACCESS ON DATABASE graphiti TO neo4j;
```

---

## 6. References

- **Sprint 16 Plan:** [SPRINT_PLAN.md](../core/SPRINT_PLAN.md)
- **Graphiti Reference:** [graphiti_reference.md](../graphiti_reference.md)
- **ADR-017:** Semantic Entity Deduplication (LightRAG)
- **ADR-018:** Model Selection for Relation Extraction (LightRAG)
- **ADR-022:** Unified Chunking Service (Feature 16.1)
- **ADR-024:** Graphiti Optimization Strategy (To Be Created, Feature 16.7)

---

## 7. Summary

| Layer | System | Data Model | Performance | Unified Chunking |
|-------|--------|------------|-------------|-----------------|
| **Layer 2** | LightRAG | Chunk-based (512 tokens) | ✅ Optimized (10x, Sprint 13) | ✅ Consumer of ChunkingService |
| **Layer 3** | Graphiti | Episode-based (full docs) | ⚠️ Unknown (blackbox) | ❌ Not applicable |

**Key Takeaway:**
- **LightRAG and Graphiti are complementary, not competing**
- **LightRAG:** Chunk-level retrieval (entity-based search)
- **Graphiti:** Document-level memory (temporal queries, communities)
- **Unified Chunking:** Only affects LightRAG (Layer 2)
- **Graphiti Performance:** Needs evaluation (Sprint 16 Feature 16.7)

---

**Document Status:** Reference Material
**Last Updated:** 2025-10-28 (Sprint 16 Planning)
**Next Review:** Post-Sprint 16 (after Feature 16.7 benchmarking)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
