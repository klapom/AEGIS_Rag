# Shared Components

**Sprint 16-21:** Shared utilities and services across AEGIS RAG
**Architecture:** Unified embedding service + deprecated unified ingestion
**Performance:** BGE-M3 embeddings (1024-dim, ~180ms query embedding)

---

## Overview

The Shared Components package provides **common utilities and services** used across multiple AEGIS RAG components.

### Components

**Active:**
- **EmbeddingService:** Unified BGE-M3 embedding service (Sprint 16+, ADR-024)

**Deprecated:**
- **UnifiedIngestionPipeline:** DEPRECATED - Replaced by LangGraph pipeline (Sprint 21)

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Shared Components Architecture                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         EmbeddingService (BGE-M3)                    │  │
│  │                                                       │  │
│  │  • Singleton pattern (shared across all components)  │  │
│  │  • BGE-M3: 1024-dim embeddings                       │  │
│  │  • Batch processing support                          │  │
│  │  • Connection pooling (Ollama)                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                      │                                       │
│        ┌─────────────┴─────────────┐                        │
│        ▼                           ▼                         │
│  Vector Search              Graph RAG                        │
│  Memory                     Ingestion                        │
│  Retrieval                  Profiling                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │   UnifiedIngestionPipeline (DEPRECATED)              │  │
│  │                                                       │  │
│  │   ⚠️ DO NOT USE - Replaced by LangGraph (Sprint 21)  │  │
│  │   Removal: Sprint 22                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Component Files

| File | Purpose | Status | LOC |
|------|---------|--------|-----|
| `embedding_service.py` | Unified BGE-M3 embedding service | ✅ Active | 350 |
| `unified_ingestion.py` | Unified ingestion pipeline | ⚠️ DEPRECATED | 280 |

**Total Active Code:** ~350 lines

---

## Embedding Service

### Overview

`EmbeddingService` provides a **unified BGE-M3 embedding service** used across all AEGIS RAG components.

### Usage

```python
from src.components.shared import get_embedding_service

# Get singleton instance
embedding_service = get_embedding_service()

# Single embedding
embedding = await embedding_service.embed("What is vector search?")
# Returns: List[float] (1024 dimensions)

# Batch embeddings (more efficient)
texts = ["Query 1", "Query 2", "Query 3"]
embeddings = await embedding_service.embed_batch(texts)
# Returns: List[List[float]]

# Get embedding dimension
dim = embedding_service.get_embedding_dimension()
# Returns: 1024 (BGE-M3)
```

### Features

**BGE-M3 Embeddings (ADR-024):**
- **Dimensions:** 1024 (vs 768 nomic-embed-text)
- **Quality:** +12% precision@5 vs nomic-embed-text
- **Context Length:** 8192 tokens
- **Use Case:** Multilingual, dense retrieval

**Performance Optimization:**
- **Singleton Pattern:** Single instance shared across all components
- **Connection Pooling:** Reuses Ollama HTTP connections
- **Batch Processing:** Embed multiple texts in one API call
- **Caching:** Optional embedding cache (Redis)

### Configuration

```python
# src/core/config.py
class Settings(BaseSettings):
    ollama_model_embedding: str = Field(
        default="bge-m3:latest",
        description="BGE-M3 for embeddings (ADR-024, Sprint 16+)"
    )

    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: int = 120  # seconds
    embedding_cache_enabled: bool = True
    embedding_cache_ttl: int = 3600  # 1 hour
```

```bash
# .env
OLLAMA_MODEL_EMBEDDING=bge-m3:latest
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_CACHE_ENABLED=true
```

### Singleton Pattern

```python
# Singleton instance (module-level)
_embedding_service: EmbeddingService | None = None

def get_embedding_service() -> EmbeddingService:
    """Get or create singleton EmbeddingService instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

# All components use same instance → shared connection pool
vector_search_svc = get_embedding_service()
graph_rag_svc = get_embedding_service()
memory_svc = get_embedding_service()
# All three variables point to the SAME instance
```

### Performance

**Benchmark (BGE-M3):**
- **Single embedding:** ~180ms (query)
- **Batch embedding (10 docs):** ~1800ms total, ~180ms per doc
- **Batch embedding (100 docs):** ~15s total, ~150ms per doc (amortized)

**Comparison:**
| Model | Dimensions | Query Embedding | Batch (10 docs) |
|-------|-----------|-----------------|-----------------|
| nomic-embed-text | 768 | 120ms | 1200ms |
| bge-m3 | 1024 | 180ms | 1800ms |
| all-MiniLM-L6-v2 | 384 | 50ms | 500ms |

---

## Unified Ingestion Pipeline (DEPRECATED)

### ⚠️ DEPRECATION NOTICE

```python
"""
============================================================================
⚠️ DEPRECATED: Sprint 21 - This module will be replaced by LangGraph pipeline
============================================================================
REASON: Parallel execution (asyncio.gather) incompatible with:
  - Memory constraints (4.4GB RAM limit, RTX 3060 6GB VRAM)
  - Container lifecycle management (Docling start/stop between batches)
  - SSE progress streaming (React UI real-time updates)
  - Sequential stage execution (memory-optimized pipeline)

REPLACEMENT: Feature 21.2 - LangGraph Ingestion State Machine
  from src.components.ingestion.langgraph_pipeline import create_ingestion_graph

  pipeline = create_ingestion_graph()
  async for event in pipeline.astream(initial_state):
      node_name = list(event.keys())[0]
      state = event[node_name]
      # Stream progress to React UI via SSE
      await send_sse({"node": node_name, "progress": state["overall_progress"]})

MIGRATION STATUS: DO NOT USE for new code
REMOVAL: Sprint 22 (after LangGraph migration complete)
============================================================================
"""
```

### Why Deprecated?

**Problems with asyncio.gather (Sprint 20):**
1. **Memory Constraints:** 4.4GB RAM limit exceeded with parallel Qdrant/Neo4j indexing
2. **Container Lifecycle:** Docling container needs start/stop between batches (6GB VRAM)
3. **SSE Streaming:** React UI needs real-time progress updates (LangGraph provides this)
4. **Sequential Execution:** Memory-optimized pipeline requires sequential stages

**Replacement: LangGraph State Machine (Sprint 21):**
```python
# LangGraph provides:
# - Sequential node execution (memory-safe)
# - SSE progress streaming (real-time UI updates)
# - Container lifecycle hooks (start/stop Docling)
# - Checkpointing (resume on failure)

from src.components.ingestion.langgraph_pipeline import create_ingestion_graph

pipeline = create_ingestion_graph()
async for event in pipeline.astream(initial_state):
    # Stream progress to React UI
    node_name = list(event.keys())[0]
    state = event[node_name]
    yield {"node": node_name, "progress": state["overall_progress"]}
```

### Migration Guide

**Before (UnifiedIngestionPipeline):**
```python
from src.components.shared.unified_ingestion import UnifiedIngestionPipeline

pipeline = UnifiedIngestionPipeline()
result = await pipeline.ingest_directory("/docs")
# Parallel execution → memory issues
```

**After (LangGraph):**
```python
from src.components.ingestion.langgraph_pipeline import create_ingestion_graph
from src.components.ingestion.ingestion_state import IngestionState

pipeline = create_ingestion_graph()
initial_state = IngestionState(
    file_paths=[Path("/docs/file1.pdf"), Path("/docs/file2.pdf")],
    overall_progress=0.0,
    current_stage="docling_parse"
)

# Sequential execution with SSE streaming
async for event in pipeline.astream(initial_state):
    # Handle progress updates
    pass
```

---

## Testing

### Unit Tests

```bash
# Test embedding service
pytest tests/unit/components/shared/test_embedding_service.py
```

### Integration Tests

```bash
# Test embedding service with Ollama
pytest tests/integration/components/shared/test_embedding_integration.py
```

**Test Coverage:** 82% (24 unit tests, 8 integration tests)

---

## Configuration

### Environment Variables

```bash
# Embedding Service
OLLAMA_MODEL_EMBEDDING=bge-m3:latest
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=120

# Embedding Cache
EMBEDDING_CACHE_ENABLED=true
EMBEDDING_CACHE_TTL=3600  # 1 hour

# Deprecated Unified Ingestion (DO NOT USE)
# UNIFIED_INGESTION_ENABLED=false
```

---

## Usage Examples

### Embedding Service Across Components

**Vector Search:**
```python
from src.components.shared import get_embedding_service

# Shared embedding service
embedding_service = get_embedding_service()

# Embed query
query_embedding = await embedding_service.embed("What is RAG?")

# Search Qdrant
results = await qdrant_client.search(
    collection_name="documents",
    query_vector=query_embedding,
    limit=10
)
```

**Graph RAG:**
```python
from src.components.shared import get_embedding_service

# Same embedding service instance (singleton)
embedding_service = get_embedding_service()

# Embed entity for semantic deduplication
entity_embedding = await embedding_service.embed("Machine Learning")

# Find similar entities
similar_entities = await qdrant_client.search(
    collection_name="entities",
    query_vector=entity_embedding,
    limit=5
)
```

**Memory:**
```python
from src.components.shared import get_embedding_service

# Same instance again
embedding_service = get_embedding_service()

# Embed memory for semantic search
memory_embedding = await embedding_service.embed("User prefers concise answers")

# Store to Qdrant (Layer 2)
await qdrant_client.upsert(
    collection_name="semantic_memory",
    points=[PointStruct(id=uuid4().hex, vector=memory_embedding, payload={...})]
)
```

### Batch Embedding Optimization

```python
from src.components.shared import get_embedding_service

embedding_service = get_embedding_service()

# Inefficient: One API call per text
embeddings = []
for text in texts:
    embedding = await embedding_service.embed(text)
    embeddings.append(embedding)

# Efficient: One API call for all texts
embeddings = await embedding_service.embed_batch(texts)
# 10x faster for large batches
```

---

## Performance Tuning

### Batch Size Optimization

```python
# Optimal batch size depends on text length
# Short texts (< 100 tokens): batch_size = 100
# Medium texts (100-500 tokens): batch_size = 50
# Long texts (> 500 tokens): batch_size = 10

# Example: Batch embed 1000 documents
texts = [...]  # 1000 documents
batch_size = 50

for i in range(0, len(texts), batch_size):
    batch = texts[i:i+batch_size]
    embeddings = await embedding_service.embed_batch(batch)
    # Process embeddings...
```

### Connection Pooling

```python
# Ollama client uses httpx connection pooling automatically
# No manual configuration needed

# Connection pool settings (in EmbeddingService.__init__)
self.client = AsyncClient(
    base_url=settings.ollama_base_url,
    timeout=Timeout(settings.ollama_timeout),
    limits=Limits(
        max_connections=100,
        max_keepalive_connections=20
    )
)
```

---

## Troubleshooting

### Issue: Embedding generation slow

**Solutions:**
```python
# Use batch embedding
embeddings = await embedding_service.embed_batch(texts)

# Reduce batch size if timeout
batch_size = 10  # Instead of 100

# Check Ollama performance
curl http://localhost:11434/api/embeddings -d '{
  "model": "bge-m3:latest",
  "prompt": "test"
}'
```

### Issue: BGE-M3 model not found

**Solution:**
```bash
# Pull BGE-M3 model
ollama pull bge-m3:latest

# Verify model
ollama list | grep bge-m3
```

### Issue: Memory errors during embedding

**Solution:**
```python
# Reduce batch size
batch_size = 5  # Very conservative

# Or process one at a time
for text in texts:
    embedding = await embedding_service.embed(text)
    # Process immediately, don't accumulate in memory
```

---

## Related Documentation

- **ADR-024:** BGE-M3 System-Wide Embedding Standardization (Sprint 16)
- **ADR-027:** Docling Container vs. LlamaIndex (Sprint 21 - deprecates unified_ingestion)
- **Ingestion Component:** [src/components/ingestion/README.md](../ingestion/README.md)
- **Vector Search Component:** [src/components/vector_search/README.md](../vector_search/README.md)
- **Sprint 16 Summary:** [SPRINT_16_SUMMARY.md](../../docs/sprints/SPRINT_16_SUMMARY.md)
- **Sprint 21 Plan:** [SPRINT_21_PLAN_v2.md](../../docs/sprints/SPRINT_21_PLAN_v2.md)

---

**Last Updated:** 2025-11-10
**Sprint:** 16-21 (Embedding Service: Sprint 16, Unified Ingestion Deprecation: Sprint 21)
**Maintainer:** Klaus Pommer + Claude Code (backend-agent, documentation-agent)
