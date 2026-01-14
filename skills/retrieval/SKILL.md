---
name: retrieval
version: 1.0.0
description: Vector and graph retrieval using BGE-M3 hybrid search and LightRAG entity reasoning
author: AegisRAG Team
triggers:
  - search
  - find
  - lookup
  - retrieve
  - query
  - get documents
dependencies:
  - qdrant
  - neo4j
  - bge-m3
permissions:
  - read_documents
  - invoke_llm
resources:
  prompts: prompts/
---

# Retrieval Skill

## Overview

The Retrieval Skill provides comprehensive document retrieval capabilities combining:
- **BGE-M3 Hybrid Search**: Dense (1024-dim) + Sparse (learned lexical weights) with server-side RRF fusion
- **LightRAG Graph Reasoning**: Entity and relationship-based queries via Neo4j
- **Semantic Expansion**: 3-stage search (LLM → Graph N-hop → Synonym → BGE-M3)
- **Reranking**: Cross-encoder reranking of top-k candidates

This skill is activated for search, research, and question-answering intents.

## Capabilities

- **Hybrid Vector Search**: Combines dense semantic embeddings with sparse lexical matching
- **Graph Entity Search**: Queries Neo4j knowledge graph for entity-based retrieval
- **Multi-Hop Reasoning**: Expands queries through graph relationships (1-3 hops)
- **Namespace Isolation**: Per-project document isolation (Sprint 75+)
- **Section-Aware Retrieval**: Preserves document structure (ADR-039)
- **Parent Chunk Retrieval**: Returns full context for matched chunks
- **Metadata Filtering**: Filter by domain, document type, date range

## Usage

### When to Activate

This skill is activated when:
- User query contains search intent keywords: "search", "find", "lookup"
- Intent classifier returns SEARCH or RESEARCH
- Agent needs to retrieve documents for context
- Graph reasoning is required for entity-based queries

### Input Requirements

**Required:**
- `query`: str - User query or search terms
- `namespace`: str - Document namespace (e.g., "ragas_phase2")

**Optional:**
- `top_k`: int - Number of results to return (default: 10)
- `mode`: str - Search mode: "vector", "graph", "hybrid" (default: "hybrid")
- `filters`: dict - Metadata filters (domain, doc_type, date_range)
- `rerank`: bool - Apply cross-encoder reranking (default: true)
- `expand_graph`: bool - Use semantic expansion via graph (default: false)
- `graph_hops`: int - N-hop expansion depth 1-3 (default: 2)

### Output Format

```python
{
    "documents": [
        {
            "id": "doc_abc123",
            "text": "Full chunk text...",
            "score": 0.92,
            "metadata": {
                "source": "paper.pdf",
                "page": 5,
                "section": "Introduction",
                "domain": "research_papers"
            }
        }
    ],
    "mode": "hybrid",
    "latency_ms": 145.3,
    "retrieval_stats": {
        "vector_results": 10,
        "graph_results": 5,
        "reranked": true
    }
}
```

## Configuration

```yaml
# Hybrid Search Settings
vector:
  top_k: 10
  score_threshold: 0.6
  use_sparse: true
  rrf_k: 60  # Reciprocal Rank Fusion parameter

# Graph Search Settings
graph:
  enabled: true
  entity_types:
    - PERSON
    - ORGANIZATION
    - CONCEPT
    - TECHNOLOGY
  relationship_types:
    - RELATES_TO
    - PART_OF
    - USES
  max_hops: 2

# Semantic Expansion
expansion:
  enabled: false
  llm_synonyms: true
  graph_neighbors: true
  similarity_threshold: 0.75

# Reranking
reranking:
  enabled: true
  model: cross-encoder
  top_k_candidates: 30
  final_k: 10

# Performance
cache:
  enabled: true
  ttl_seconds: 300
  key_prefix: "retrieval"
```

## Examples

### Example 1: Basic Hybrid Search

**Input:**
```python
query = "What is hybrid search?"
namespace = "ragas_phase2"
top_k = 5
mode = "hybrid"
```

**Output:**
```json
{
    "documents": [
        {
            "id": "doc_123",
            "text": "Hybrid search combines vector similarity with keyword matching using Reciprocal Rank Fusion...",
            "score": 0.92,
            "metadata": {
                "source": "architecture.md",
                "section": "Search Algorithms"
            }
        }
    ],
    "mode": "hybrid",
    "latency_ms": 145.3
}
```

### Example 2: Graph Entity Search

**Input:**
```python
query = "Find documents about BGE-M3 embeddings"
namespace = "ragas_phase2"
mode = "graph"
expand_graph = true
graph_hops = 2
```

**Output:**
```json
{
    "documents": [
        {
            "id": "doc_456",
            "text": "BGE-M3 is a multi-vector embedding model that produces 1024-dimensional dense vectors...",
            "score": 0.87,
            "metadata": {
                "source": "embeddings.md",
                "entities": ["BGE-M3", "FlagEmbedding", "Dense Vectors"]
            }
        }
    ],
    "mode": "graph",
    "latency_ms": 320.5,
    "retrieval_stats": {
        "entities_found": 3,
        "relationships_traversed": 8,
        "graph_hops": 2
    }
}
```

### Example 3: Filtered Search with Reranking

**Input:**
```python
query = "Neural network architectures in computer vision"
namespace = "research_papers"
top_k = 10
filters = {
    "domain": "machine_learning",
    "doc_type": "research_paper",
    "date_range": {"start": "2024-01-01", "end": "2025-12-31"}
}
rerank = true
```

**Output:**
```json
{
    "documents": [
        {
            "id": "doc_789",
            "text": "Convolutional Neural Networks (CNNs) are the dominant architecture...",
            "score": 0.95,
            "rerank_score": 0.98,
            "metadata": {
                "source": "cnn_survey_2024.pdf",
                "domain": "machine_learning",
                "doc_type": "research_paper",
                "date": "2024-03-15"
            }
        }
    ],
    "mode": "hybrid",
    "latency_ms": 287.6,
    "retrieval_stats": {
        "initial_candidates": 30,
        "after_reranking": 10,
        "reranked": true
    }
}
```

## Limitations

- **Embedding Latency**: BGE-M3 embeddings take ~99ms per query (GPU-accelerated)
- **Graph Complexity**: N-hop expansion can be slow for dense graphs (>1000 nodes)
- **Namespace Required**: Must specify namespace for multi-tenant isolation
- **Cold Start**: First query per namespace may be slower due to cache warming
- **Token Limits**: Very long documents (>2000 tokens) are chunked, losing some context

## Version History

- 1.0.0 (2026-01-14): Initial release (Sprint 90)
  - BGE-M3 hybrid search integration
  - LightRAG graph reasoning
  - Namespace isolation
  - Section-aware retrieval
  - Cross-encoder reranking
  - Based on Sprint 87 (BGE-M3 native), Sprint 78 (graph expansion), Sprint 75 (namespace isolation)
