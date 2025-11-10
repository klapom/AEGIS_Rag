# Graph RAG Component

**Sprint 4-13:** LightRAG + Neo4j for Knowledge Graph Reasoning
**Architecture:** Three-Phase Extraction + Dual-Level Retrieval
**Performance:** <150ms p95 for graph queries on 15K entities

---

## Overview

The Graph RAG Component provides **graph-based reasoning** over document knowledge using:
- **LightRAG:** Lightweight Graph RAG framework for entity/relation extraction
- **Neo4j:** Property graph database for knowledge storage
- **Three-Phase Extraction:** Entity → Relation → Community (ADR-018, Sprint 13)
- **Dual-Level Retrieval:** Entity-level + Community-level search

### Key Features

- **Three-Phase Extraction:** Optimized extraction pipeline (ADR-018)
- **Semantic Deduplication:** GPT-4o-based entity deduplication (ADR-017, Sprint 13)
- **Community Detection:** Louvain algorithm for topic clustering
- **Temporal Query Builder:** Time-aware graph traversal
- **LightRAG Integration:** Incremental updates without full re-index

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Graph RAG Pipeline                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        Extraction Pipeline (3-Phase)                 │  │
│  │                                                       │  │
│  │  Phase 1: Entity Extraction (Gemma-3-4b)            │  │
│  │           ↓                                          │  │
│  │  Phase 2: Relation Extraction (Gemma-3-4b)          │  │
│  │           ↓                                          │  │
│  │  Phase 3: Community Detection (Louvain)             │  │
│  └──────────────────────────────────────────────────────┘  │
│                      │                                       │
│                      ▼                                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Neo4j Knowledge Graph                      │  │
│  │                                                       │  │
│  │   Entities: 15,000 nodes                             │  │
│  │   Relationships: 45,000 edges                        │  │
│  │   Communities: 120 topic clusters                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                      │                                       │
│                      ▼                                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        Dual-Level Retrieval (LightRAG)               │  │
│  │                                                       │  │
│  │  Entity-Level: Direct entity matches                 │  │
│  │  Community-Level: Topic-based retrieval              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Component Files

| File | Purpose | LOC |
|------|---------|-----|
| `lightrag_wrapper.py` | LightRAG framework integration | 1,400 |
| `three_phase_extractor.py` | 3-phase extraction pipeline | 350 |
| `extraction_service.py` | Unified extraction interface | 600 |
| `semantic_deduplicator.py` | Entity deduplication logic | 350 |
| `neo4j_client.py` | Neo4j database client | 330 |
| `community_detector.py` | Louvain community detection | 650 |
| `dual_level_search.py` | Entity + community retrieval | 480 |
| `query_builder.py` | Cypher query generation | 410 |
| `temporal_query_builder.py` | Time-aware queries | 315 |

**Total:** ~4,885 lines of code

---

## LightRAG Wrapper

### Overview

`LightRAGWrapper` integrates LightRAG framework for incremental graph updates.

### Key Methods

```python
from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async

# Get singleton
lightrag = await get_lightrag_wrapper_async()

# Insert documents (incremental)
await lightrag.insert_documents([
    "Machine learning is a subset of AI...",
    "Neural networks are computational models..."
])

# Query graph (dual-level)
results = await lightrag.query(
    query="What is machine learning?",
    mode="hybrid"  # Entity + community level
)
```

### Features

**Incremental Updates:**
- No full re-index needed (vs. Microsoft GraphRAG)
- Append new entities/relations to existing graph
- Update existing entities with new information

**Dual-Level Retrieval:**
- **Entity-Level:** Direct entity name matching
- **Community-Level:** Topic cluster matching via Louvain

**Storage Backend:**
- Neo4j for graph storage
- Qdrant for entity embeddings
- Redis for query cache

### Performance

**Benchmark (10K documents):**
- **Indexing Time:** 45 minutes (vs. 3 hours Microsoft GraphRAG)
- **Query Latency:** <150ms p95
- **Memory Usage:** ~500 MB (Neo4j in-memory cache)

---

## Three-Phase Extraction Pipeline

### Overview

**ADR-018 (Sprint 13):** Optimized extraction with separate entity and relation phases.

### Pipeline Stages

```python
# src/components/graph_rag/three_phase_extractor.py

async def extract_three_phase(text: str):
    """Three-phase extraction pipeline.

    Phase 1: Extract entities
    Phase 2: Extract relations (given entities)
    Phase 3: Detect communities (graph clustering)
    """

    # Phase 1: Entity Extraction
    entities = await extract_entities(text)
    # Model: gemma-3-4b-it-Q8_0
    # Prompt: "Extract all entities (people, places, concepts) from the text"

    # Phase 2: Relation Extraction
    relations = await extract_relations(text, entities)
    # Prompt: "Given entities {entities}, extract relationships between them"

    # Phase 3: Community Detection (after graph insert)
    communities = await detect_communities(entities, relations)
    # Algorithm: Louvain (modularity optimization)

    return {
        "entities": entities,
        "relations": relations,
        "communities": communities
    }
```

### Why Three Phases? (ADR-018)

**Problem with Single-Phase:**
- Gemma-3-4b struggled with simultaneous entity + relation extraction
- Low F1 score: 0.45 (entity detection)
- Hallucinated relations between non-existent entities

**Solution: Sequential Extraction:**
- **Phase 1:** Focus only on entity detection → F1: 0.72 (+60%)
- **Phase 2:** Given entities, extract relations → Precision: 0.85
- **Phase 3:** Graph-level community detection

**Results:**
- **Entity F1:** 0.72 (vs 0.45 single-phase, +60%)
- **Relation Precision:** 0.85 (vs 0.60, +42%)
- **Processing Time:** +15% overhead (acceptable for quality gain)

---

## Semantic Deduplication

### Overview

**ADR-017 (Sprint 13):** GPT-4o-based semantic deduplication for entities.

### Problem

Different text representations of the same entity:
- "ML" vs "Machine Learning" vs "machine learning"
- "GPT-4" vs "GPT 4" vs "GPT-4.0"
- "New York" vs "NYC" vs "New York City"

### Solution

```python
# src/components/graph_rag/semantic_deduplicator.py

async def deduplicate_entities(entities: List[Entity]) -> List[Entity]:
    """Semantically deduplicate entities using GPT-4o.

    Approach:
    1. Cluster candidates by string similarity (edit distance < 3)
    2. For each cluster, use GPT-4o to identify duplicates
    3. Merge duplicates, keeping most complete entity
    """

    # Group by similarity
    clusters = group_by_similarity(entities, threshold=0.8)

    deduped = []
    for cluster in clusters:
        # GPT-4o deduplication prompt
        prompt = f"""
        Are these entities referring to the same real-world concept?
        Entities: {[e.name for e in cluster]}

        Respond with JSON:
        {{"is_duplicate": true/false, "canonical_name": "..."}}
        """

        response = await llm.generate(prompt, model="gpt-4o")

        if response["is_duplicate"]:
            # Merge entities
            canonical = merge_entities(cluster, response["canonical_name"])
            deduped.append(canonical)
        else:
            deduped.extend(cluster)

    return deduped
```

### Performance

**Benchmark (1000 entities):**
- **Deduplication Time:** ~30s (GPT-4o API calls)
- **Accuracy:** 92% correct merges (manual validation)
- **Cost:** ~$0.50 per 1000 entities (GPT-4o API)

**Alternative:** Local LLM (llama3.2:8b) → 75% accuracy, but free

---

## Neo4j Client

### Overview

`Neo4jClient` provides async interface to Neo4j graph database.

### Key Methods

```python
from src.components.graph_rag.neo4j_client import get_neo4j_client

# Get singleton
neo4j = get_neo4j_client()

# Insert entities
await neo4j.create_nodes(
    label="Entity",
    nodes=[
        {"name": "Machine Learning", "type": "concept"},
        {"name": "Neural Network", "type": "concept"}
    ]
)

# Insert relationships
await neo4j.create_relationships(
    start_label="Entity",
    end_label="Entity",
    relationship_type="RELATED_TO",
    relationships=[
        {"start": "Machine Learning", "end": "Neural Network", "weight": 0.8}
    ]
)

# Query graph
results = await neo4j.query(
    "MATCH (e:Entity {name: $name})-[r]->(related) RETURN related",
    parameters={"name": "Machine Learning"}
)
```

### Features

**Graph Operations:**
- `create_nodes()`: Batch node insertion
- `create_relationships()`: Batch edge insertion
- `query()`: Cypher query execution
- `get_neighbors()`: Find connected nodes
- `shortest_path()`: Shortest path between entities

**Advanced Features:**
- **Connection Pooling:** Automatic connection reuse
- **Transaction Support:** ACID guarantees
- **Retry Logic:** 3 attempts with exponential backoff
- **Query Caching:** Redis-cached query results

### Configuration

```python
# src/core/config.py
class Settings(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"
```

---

## Community Detection

### Overview

`CommunityDetector` implements **Louvain algorithm** for topic clustering.

### Usage

```python
from src.components.graph_rag.community_detector import CommunityDetector

# Initialize
detector = CommunityDetector()

# Detect communities
communities = await detector.detect(
    min_community_size=5,
    resolution=1.0  # Higher = more granular communities
)

# Results:
# [
#   {
#     "id": 1,
#     "members": ["ML", "Neural Network", "Deep Learning"],
#     "cohesion": 0.85,
#     "label": "Machine Learning"
#   },
#   ...
# ]
```

### Louvain Algorithm

**How it works:**
1. **Initialization:** Each node in its own community
2. **Phase 1 (Local):** Move nodes to maximize modularity
3. **Phase 2 (Global):** Aggregate communities into super-nodes
4. **Repeat** until modularity converges

**Modularity Score:**
```
Q = (1/2m) * Σ [A_ij - (k_i * k_j) / 2m] * δ(c_i, c_j)

Where:
- m = total edge weight
- A_ij = edge weight between i and j
- k_i = sum of weights of edges incident to i
- δ(c_i, c_j) = 1 if i,j in same community, else 0
```

### Performance

**Benchmark (15K nodes, 45K edges):**
- **Detection Time:** ~5s
- **Communities Found:** 120
- **Modularity Score:** 0.72 (good separation)
- **Largest Community:** 250 nodes

---

## Dual-Level Retrieval

### Overview

**Dual-Level Search** combines entity-level and community-level retrieval.

### Search Modes

```python
from src.components.graph_rag.dual_level_search import DualLevelSearch

search = DualLevelSearch()

# Entity-level: Direct entity matching
entity_results = await search.search_entities(
    query="machine learning algorithms",
    top_k=5
)

# Community-level: Topic cluster matching
community_results = await search.search_communities(
    query="machine learning algorithms",
    top_k=3
)

# Hybrid: Combine both levels
hybrid_results = await search.search_hybrid(
    query="machine learning algorithms",
    top_k=10
)
```

### Why Dual-Level?

**Entity-Level:**
- **Precision:** Exact entity matches
- **Use Case:** "Who is John Doe?" → Direct entity lookup
- **Latency:** <50ms

**Community-Level:**
- **Recall:** Broad topic coverage
- **Use Case:** "Tell me about machine learning" → Entire ML cluster
- **Latency:** <100ms

**Hybrid:**
- **Best of Both:** High precision + high recall
- **Use Case:** Complex multi-hop queries

---

## Query Builder

### Overview

`QueryBuilder` generates **Cypher queries** from natural language.

### Usage

```python
from src.components.graph_rag.query_builder import QueryBuilder

builder = QueryBuilder()

# Natural language → Cypher
cypher = await builder.build_query(
    query="Find all concepts related to machine learning",
    max_depth=2
)

# Generated Cypher:
# MATCH (e:Entity {name: "Machine Learning"})-[r*1..2]-(related)
# RETURN related.name, type(r), related.type
```

### Features

**Query Templates:**
- **Find Related:** Entities connected to query entity
- **Shortest Path:** Path between two entities
- **Community Members:** All entities in a community
- **Temporal:** Entities within time range

**Optimization:**
- **Query Hints:** USING INDEX for faster lookups
- **Result Limiting:** LIMIT 100 by default
- **Caching:** Redis-cached frequent queries

---

## Temporal Query Builder

### Overview

`TemporalQueryBuilder` adds **time-aware** graph traversal.

### Usage

```python
from src.components.graph_rag.temporal_query_builder import TemporalQueryBuilder

builder = TemporalQueryBuilder()

# Time-aware query
results = await builder.query_temporal(
    entity="Machine Learning",
    start_date="2020-01-01",
    end_date="2023-12-31",
    relationship_type="RELATED_TO"
)
```

### Features

**Temporal Relationships:**
- Edges have `timestamp` property
- Filter by date range
- Find evolving relationships

**Use Cases:**
- "How did the concept of AI evolve from 2010 to 2020?"
- "What papers were published about transformers in 2023?"

---

## Usage Examples

### Basic Entity Extraction

```python
from src.components.graph_rag.extraction_service import get_extraction_service

# Get extraction service (three-phase by default, ADR-018)
extractor = get_extraction_service()

# Extract from text
result = await extractor.extract(
    text="Machine learning is a subset of artificial intelligence..."
)

# Results:
# {
#   "entities": [
#     {"name": "Machine Learning", "type": "concept"},
#     {"name": "Artificial Intelligence", "type": "concept"}
#   ],
#   "relations": [
#     {
#       "source": "Machine Learning",
#       "target": "Artificial Intelligence",
#       "type": "IS_SUBSET_OF"
#     }
#   ]
# }
```

### Graph Query

```python
from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async

# Query graph
lightrag = await get_lightrag_wrapper_async()

# Dual-level search
results = await lightrag.query(
    query="What are the applications of machine learning?",
    mode="hybrid"  # Entity + community level
)

# Results include:
# - Direct entity matches
# - Community context
# - Related concepts
```

### Community Analysis

```python
from src.components.graph_rag.community_detector import CommunityDetector

detector = CommunityDetector()

# Detect communities
communities = await detector.detect()

# Analyze largest community
largest = max(communities, key=lambda c: c["size"])
print(f"Largest community: {largest['label']}")
print(f"Members: {len(largest['members'])}")
print(f"Cohesion: {largest['cohesion']}")
```

---

## Testing

### Unit Tests

```bash
# Test LightRAG wrapper
pytest tests/unit/components/graph_rag/test_lightrag_wrapper.py

# Test three-phase extractor
pytest tests/unit/components/graph_rag/test_three_phase_extractor.py

# Test community detector
pytest tests/unit/components/graph_rag/test_community_detector.py
```

### Integration Tests

```bash
# Test full extraction pipeline
pytest tests/integration/components/graph_rag/test_extraction_pipeline.py

# Test Neo4j integration
pytest tests/integration/components/graph_rag/test_neo4j_integration.py
```

**Test Coverage:** 82% (95 unit tests, 28 integration tests)

---

## Configuration

### Environment Variables

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Extraction
EXTRACTION_MODEL=gemma-3-4b-it-Q8_0
EXTRACTION_PIPELINE=three_phase  # ADR-018

# Community Detection
COMMUNITY_MIN_SIZE=5
COMMUNITY_RESOLUTION=1.0

# Deduplication
DEDUP_ENABLED=true
DEDUP_MODEL=gpt-4o  # or llama3.2:8b for local
```

---

## Performance Tuning

### Neo4j Optimization

**Indexes:**
```cypher
-- Entity name index (mandatory)
CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);

-- Relationship type index
CREATE INDEX rel_type IF NOT EXISTS FOR ()-[r]-() ON (type(r));
```

**Memory Configuration:**
```bash
# neo4j.conf
dbms.memory.heap.initial_size=1g
dbms.memory.heap.max_size=2g
dbms.memory.pagecache.size=1g
```

---

## Troubleshooting

### Issue: Slow extraction

**Solutions:**
```bash
# Use three-phase pipeline (ADR-018)
EXTRACTION_PIPELINE=three_phase

# Batch processing
# Process 10 documents in parallel
```

### Issue: Low entity detection accuracy

**Solutions:**
```python
# Enable semantic deduplication
DEDUP_ENABLED=true

# Use GPT-4o for higher accuracy (vs llama3.2:8b)
DEDUP_MODEL=gpt-4o
```

---

## Related Documentation

- **ADR-005:** LightRAG statt Microsoft GraphRAG
- **ADR-017:** Semantic Entity Deduplication (Sprint 13)
- **ADR-018:** Model Selection for Entity/Relation Extraction (Sprint 13)
- **Sprint 04-06 Summary:** [SPRINT_04-06_GRAPH_RAG_SUMMARY.md](../../docs/sprints/SPRINT_04-06_GRAPH_RAG_SUMMARY.md)
- **Sprint 13 Summary:** [SPRINT_13_SUMMARY.md](../../docs/sprints/SPRINT_13_SUMMARY.md)

---

**Last Updated:** 2025-11-10
**Sprint:** 4-13 (Core: Sprint 4-6, Enhanced: Sprint 13)
**Maintainer:** Klaus Pommer + Claude Code (backend-agent, documentation-agent)
