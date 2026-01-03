# Neo4j LLM Graph Builder vs AegisRAG - Detailed Comparison

**Date:** 2025-12-10
**Purpose:** Deep analysis of Neo4j Labs' LLM Graph Builder to identify improvements for AegisRAG
**Source:** https://github.com/neo4j-labs/llm-graph-builder

---

## 1. Overview

| Aspect | AegisRAG | Neo4j LLM Graph Builder |
|--------|----------|-------------------------|
| **Primary Focus** | Enterprise RAG with Graph + Vector | Knowledge Graph construction from documents |
| **LLM Support** | Ollama (local), Alibaba Cloud, OpenAI | OpenAI, Gemini, Claude, Groq, Diffbot, Ollama, Azure, Bedrock |
| **Graph DB** | Neo4j Community | Neo4j (all editions) |
| **Vector DB** | Qdrant | Neo4j Vector Index |
| **Orchestration** | LangGraph | LangChain |

---

## 2. Extraction Architecture

### 2.1 AegisRAG Approach
```
Document → Docling → Chunks (800-1800 tokens) → LLM Extraction → Neo4j
                                                      ↓
                                              Custom Prompts
                                              (extraction_prompts.py)
```

**Key Files:**
- `src/components/graph_rag/extraction_prompts.py` - Custom extraction prompts
- `src/components/graph_rag/lightrag_wrapper.py` - Neo4j integration
- Strategy: UNIFIED (1 LLM call) or SEQUENTIAL (3 LLM calls)

### 2.2 Neo4j LLM Graph Builder Approach
```
Document → Chunking (10,000 tokens) → LLMGraphTransformer → Neo4j
                                              ↓
                                      LangChain Built-in
                                      + ADDITIONAL_INSTRUCTIONS
```

**Key Files (from analysis):**
- `backend/src/llm.py` - Uses `LLMGraphTransformer.aconvert_to_graph_documents()`
- `backend/src/constants.py` - Configuration and ADDITIONAL_INSTRUCTIONS
- `backend/src/graphDB_dataAccess.py` - Neo4j operations and deduplication

**ADDITIONAL_INSTRUCTIONS (from constants.py):**
```
"Identify and categorize entities while ensuring that specific data types
such as dates, numbers, revenues, and other non-entity information are
not extracted as separate nodes."
```

---

## 3. Entity Types

### AegisRAG
- **Default Types:** PERSON, ORGANIZATION, LOCATION, TECHNOLOGY, CONCEPT, EVENT, PRODUCT
- **Custom Types:** Supported via prompt modification
- **Dynamic Labels:** `labels_str = f"base:{entity_type}"` in Neo4j

### Neo4j LLM Graph Builder
- **100% User-Defined:** Via `allowedNodes` parameter (comma-separated)
- **No Defaults:** User must specify all entity types
- **Validation:** Relationships must reference only allowed node types

---

## 4. Chunk Size Comparison

| Parameter | AegisRAG (ADR-039) | Neo4j LLM Graph Builder |
|-----------|-------------------|-------------------------|
| **Default Chunk Size** | 800-1800 tokens (~1500-3500 chars) | **10,000 tokens** |
| **Chat Chunk Size** | Same as above | 3,000 chars |
| **YouTube Chunk** | N/A | 60 seconds |
| **Graph Chunk Limit** | N/A | 50 |

**Our Benchmark Finding:** 3000 chars is fastest (683s), but 500 chars extracts most entities (116 vs 58).

---

## 5. Deduplication (KEY DIFFERENCE)

### 5.1 AegisRAG Current Approach
```python
# Single-criteria: Semantic similarity only
class SemanticDeduplicator:
    def deduplicate(self, entities: List[Entity]) -> List[Entity]:
        # Embedding-based similarity check
        # Threshold-based merging
```

### 5.2 Neo4j LLM Graph Builder Approach (Multi-Criteria)

**From `graphDB_dataAccess.py`:**

```cypher
-- Step 1: Find unconnected nodes
WHERE NOT exists { (e)--(...) }

-- Step 2: Multi-criteria duplicate detection
MATCH (e:__Entity__)
WITH e.id as id, collect(e) as nodes
WHERE size(nodes) > 1
  OR apoc.text.distance(e1.id, e2.id) < 3  -- Edit distance
  OR gds.similarity.cosine(e1.embedding, e2.embedding) > DUPLICATE_SCORE_VALUE
  OR e1.id CONTAINS e2.id  -- Substring containment

-- Step 3: Merge duplicates
CALL apoc.refactor.mergeNodes(nodes, {properties: 'combine'})
```

**Three Criteria:**
1. **Edit Distance:** `apoc.text.distance() < 3` (e.g., "Nicolas Cage" vs "Nicolas cage")
2. **Vector Similarity:** Cosine > configurable threshold
3. **Substring Containment:** "Cage" contained in "Nicolas Cage"

**Merge Strategy:**
- Uses `apoc.refactor.mergeNodes()` with relationship consolidation
- Properties are combined, not overwritten

### 5.3 Comparison Table

| Feature | AegisRAG | Neo4j LLM Graph Builder |
|---------|----------|-------------------------|
| **Criteria** | Single (vector similarity) | Multi (edit dist + vector + substring) |
| **Edit Distance** | No | Yes (`apoc.text.distance() < 3`) |
| **Vector Similarity** | Yes | Yes |
| **Substring Match** | No | Yes (`CONTAINS`) |
| **Merge Tool** | Custom Python | `apoc.refactor.mergeNodes()` |
| **Unconnected Cleanup** | No | Yes (`NOT exists { (e)--(...) }`) |
| **Relationship Handling** | Custom | Built-in consolidation |

---

## 6. Post-Processing (from `post_processing.py`)

### Schema Consolidation
Neo4j LLM Graph Builder includes LLM-guided schema cleanup:
```python
# Prompt asks LLM to categorize labels semantically
# Uses existing input types only
# Consolidates similar labels (e.g., "Person" vs "PERSON" vs "Human")
```

### Entity Embeddings
```python
# Batch processing: 1000 entities at a time
# Stores embeddings on entity nodes
# Enables vector-based KNN within Neo4j
```

### AegisRAG Gap
- No schema consolidation post-processing
- Entity embeddings not stored in Neo4j (only chunk embeddings in Qdrant)

---

## 7. Query Modes

### AegisRAG
- Vector search (Qdrant)
- Graph local search (Neo4j)
- Graph global search (Neo4j)
- Hybrid (RRF fusion)

### Neo4j LLM Graph Builder (7 modes)
1. `vector` - Pure vector search
2. `graph` - Pure graph traversal
3. `graph_vector` - Graph + vector combined
4. `fulltext` - Neo4j fulltext index
5. `hybrid` - Multiple strategies
6. `graph_vector_fulltext` - All three
7. `entity_vector` - Entity-specific vector search

**Key Addition:** Fulltext index on entities (not just chunks)

---

## 8. KNN Graph (SIMILAR Edges)

### Neo4j LLM Graph Builder
```cypher
-- Creates explicit SIMILAR relationships between chunks
CALL vector.queryNodes('vector', 6, c.embedding)
YIELD node, score
CREATE (c)-[:SIMILAR {score: score}]->(node)
```

### AegisRAG
- No explicit SIMILAR edges in Neo4j
- Similarity computed on-demand via Qdrant

---

## 9. Recommendations for AegisRAG

### High Priority

1. **Multi-Criteria Deduplication**
   - Add edit distance check (`apoc.text.distance()`)
   - Add substring containment check
   - Keep existing vector similarity
   - **Benefit:** Catches "Nicolas Cage" vs "nicolas cage" vs "Cage"

2. **Unconnected Node Cleanup**
   - Add `WHERE NOT exists { (e)--(...) }` cleanup
   - Remove isolated entities without relationships
   - **Benefit:** Cleaner graph, fewer false positives

3. **Increase Chunk Size Option**
   - Add "speed mode" with 2500-3500 chars
   - Keep current 800-1800 tokens for "coverage mode"
   - **Benefit:** 35% faster ingestion when coverage is less critical

### Medium Priority

4. **Entity Embeddings**
   - Store embeddings on entity nodes in Neo4j
   - Enable entity-level vector search
   - **Benefit:** Better entity disambiguation

5. **Schema Consolidation**
   - Add optional LLM pass for label normalization
   - Consolidate "Person" / "PERSON" / "Human"
   - **Benefit:** Cleaner schema

6. **Fulltext Index on Entities**
   - Create Neo4j fulltext index on entity names
   - Enable keyword search on entities
   - **Benefit:** Faster entity lookup

### Lower Priority

7. **SIMILAR Edges**
   - Create explicit KNN graph in Neo4j
   - `CALL gds.knn.write()` for similarity edges
   - **Benefit:** Pre-computed similarity for graph algorithms

8. **Data Filtering in Prompt**
   - Add ADDITIONAL_INSTRUCTIONS to exclude dates/numbers
   - **Benefit:** Fewer garbage entities

---

## 10. Implementation Notes

### APOC Functions Required
```cypher
-- For multi-criteria dedup
apoc.text.distance(str1, str2)  -- Levenshtein distance
apoc.refactor.mergeNodes(nodes, config)  -- Node merging

-- Check APOC is installed
CALL apoc.help('text')
```

### Neo4j GDS Required (for KNN)
```cypher
-- For SIMILAR edge creation
CALL gds.knn.write(...)
```

---

## 11. Files Analyzed

| File | Key Functionality |
|------|------------------|
| `llm.py` | LLMGraphTransformer, entity extraction |
| `graphDB_dataAccess.py` | Neo4j operations, multi-criteria dedup |
| `constants.py` | ADDITIONAL_INSTRUCTIONS, thresholds |
| `chunkid_entities.py` | Entity processing, `seen_nodes` dedup |
| `post_processing.py` | Schema consolidation, entity embeddings |

---

## 12. Summary

**Neo4j LLM Graph Builder Advantages:**
- Multi-criteria deduplication (more robust)
- Larger default chunks (faster)
- Schema consolidation (cleaner)
- Entity embeddings (better search)
- 7 query modes (more flexible)

**AegisRAG Advantages:**
- LangGraph orchestration (more agentic)
- Qdrant vector DB (faster vector search)
- Docling CUDA (better OCR)
- Temporal memory (Graphiti)
- Multi-cloud LLM routing (cost optimization)

**Key Takeaway:** Adopt multi-criteria deduplication and unconnected node cleanup from Neo4j LLM Graph Builder while keeping AegisRAG's agentic architecture.

---

**Author:** Claude Code
**Last Updated:** 2025-12-10
