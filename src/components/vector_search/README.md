# Vector Search Component

**Sprint 2-16:** Hybrid Vector + Keyword Search with BGE-M3
**Architecture:** Qdrant + BM25 + Reciprocal Rank Fusion (RRF)
**Performance:** <100ms p95 for hybrid search on 10K documents

---

## Overview

The Vector Search Component provides **hybrid retrieval** combining:
- **Vector Search:** Semantic similarity via BGE-M3 embeddings (1024-dim)
- **Keyword Search:** BM25 algorithm for exact keyword matching
- **Fusion:** Reciprocal Rank Fusion (RRF) for optimal result combination

### Key Features

- **Hybrid Search:** Best of vector + keyword (ADR-009)
- **BGE-M3 Embeddings:** 1024-dim multilingual embeddings (ADR-024, Sprint 16)
- **BM25 Persistence:** Redis-cached index for fast restarts (Sprint 10)
- **Qdrant Client:** Async client with connection pooling
- **Adaptive Chunking:** Content-type-specific chunk sizes (ADR-010, Sprint 3)

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Hybrid Search Pipeline                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│        ┌────────────────────────────────────┐               │
│        │      Query Embedding (BGE-M3)      │               │
│        └────────────────────────────────────┘               │
│                      │                                       │
│           ┌──────────┴───────────┐                          │
│           ▼                      ▼                           │
│   ┌──────────────┐      ┌──────────────┐                   │
│   │ Vector Search│      │ BM25 Search  │                   │
│   │  (Qdrant)    │      │  (Redis)     │                   │
│   │ <50ms        │      │ <10ms        │                   │
│   └──────────────┘      └──────────────┘                   │
│           │                      │                           │
│           └──────────┬───────────┘                          │
│                      ▼                                       │
│        ┌────────────────────────────────────┐               │
│        │ Reciprocal Rank Fusion (RRF k=60) │               │
│        │          <10ms                     │               │
│        └────────────────────────────────────┘               │
│                      │                                       │
│                      ▼                                       │
│              Top-K Results                                   │
│          (Precision@5: 0.85)                                │
└─────────────────────────────────────────────────────────────┘
```

### Component Files

| File | Purpose | LOC |
|------|---------|-----|
| `qdrant_client.py` | Qdrant vector database client | 350 |
| `bm25_search.py` | BM25 keyword search engine | 250 |
| `hybrid_search.py` | RRF fusion orchestrator | 600 |
| `embeddings.py` | BGE-M3 embedding wrapper | 150 |
| `ingestion.py` | Document ingestion pipeline | 600 |

**Total:** ~1,950 lines of code

---

## Qdrant Client

### Overview

`QdrantClient` provides async interface to Qdrant vector database with connection pooling.

### Key Methods

```python
from src.components.vector_search.qdrant_client import get_qdrant_client

# Get singleton client
client = get_qdrant_client()

# Create collection
await client.create_collection(
    collection_name="aegis-rag-chunks",
    vector_size=1024,  # BGE-M3 dimensions
    distance="Cosine"
)

# Upsert vectors
await client.upsert(
    collection_name="aegis-rag-chunks",
    vectors=[...],  # 1024-dim embeddings
    payloads=[{
        "text": "Document content...",
        "metadata": {"file_name": "doc.pdf", "page": 1}
    }]
)

# Search
results = await client.search(
    collection_name="aegis-rag-chunks",
    query_vector=[...],  # 1024-dim query embedding
    limit=5,
    score_threshold=0.7
)
```

### Features

**Collection Management:**
- `create_collection()`: Create with custom schema
- `delete_collection()`: Delete collection
- `get_collection_info()`: Stats (document count, size)
- `list_collections()`: All collections

**Vector Operations:**
- `upsert()`: Insert/update vectors
- `search()`: Similarity search
- `scroll()`: Paginated retrieval
- `delete()`: Delete by ID or filter

**Advanced Features:**
- **Connection Pooling:** Automatic connection reuse
- **Retry Logic:** 3 attempts with exponential backoff
- **Scalar Quantization:** 8-bit compression for memory efficiency
- **HNSW Indexing:** Fast approximate nearest neighbor search

### Configuration

```python
# src/core/config.py
class Settings(BaseSettings):
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "aegis-rag-chunks"
    qdrant_vector_size: int = 1024  # BGE-M3
    qdrant_distance: str = "Cosine"
```

### Performance

**Benchmark (10K documents, 1024-dim):**
- **Search Latency:** <50ms p95
- **Throughput:** 200 QPS
- **Memory Usage:** ~250 MB (with scalar quantization)
- **Index Build Time:** ~5s for 10K vectors

---

## BM25 Search Engine

### Overview

`BM25Search` implements keyword search using **Okapi BM25 algorithm** with Redis persistence.

### Key Methods

```python
from src.components.vector_search.bm25_search import BM25Search

# Initialize
bm25 = BM25Search()

# Fit on corpus (one-time)
await bm25.fit(documents=[
    {"id": "doc1", "text": "machine learning algorithms"},
    {"id": "doc2", "text": "neural network architecture"}
])

# Search
results = await bm25.search(
    query="machine learning",
    top_k=5
)

# Results:
# [
#   {"id": "doc1", "score": 2.45, "text": "machine learning algorithms"},
#   ...
# ]
```

### Features

**BM25 Algorithm:**
- **Parameters:** k1=1.5 (term frequency saturation), b=0.75 (length normalization)
- **Tokenization:** Lowercase + stopword removal
- **Scoring:** `BM25(q, d) = Σ IDF(qi) * (f(qi, d) * (k1 + 1)) / (f(qi, d) + k1 * (1 - b + b * |d| / avgdl))`

**Persistence (Sprint 10):**
- **Redis Cache:** Serialized BM25 model stored in Redis
- **Auto-Load:** Load from cache on startup (no re-fit needed)
- **Cache Key:** `bm25:model:v1`
- **TTL:** No expiration (persistent)

**Performance Optimizations:**
- **Sparse Matrix:** Efficient storage for term frequencies
- **Pre-computed IDF:** Cached inverse document frequencies
- **Batch Processing:** Process 100 queries in parallel

### Configuration

```python
# BM25 hyperparameters
bm25_k1: float = 1.5  # Term frequency saturation
bm25_b: float = 0.75  # Length normalization

# Redis cache
bm25_cache_enabled: bool = True
bm25_cache_key: str = "bm25:model:v1"
```

### Performance

**Benchmark (10K documents):**
- **Search Latency:** <10ms p95
- **Corpus Fit Time:** ~2s (one-time)
- **Memory Usage:** ~50 MB (sparse matrix)
- **Cache Load Time:** ~100ms from Redis

---

## Hybrid Search

### Overview

`HybridSearch` orchestrates vector + keyword search with **Reciprocal Rank Fusion (RRF)**.

### Key Methods

```python
from src.components.vector_search.hybrid_search import HybridSearch

# Initialize
hybrid_search = HybridSearch()

# Hybrid search
results = await hybrid_search.search(
    query="machine learning algorithms",
    mode="hybrid",  # or "vector", "keyword"
    top_k=5,
    alpha=0.5  # Weight: 0.5 = equal vector/keyword, 1.0 = vector only
)
```

### Reciprocal Rank Fusion (RRF)

**Algorithm (ADR-009):**
```python
def rrf_fusion(
    vector_results: List[Tuple[str, float]],
    bm25_results: List[Tuple[str, float]],
    k: int = 60
) -> List[Tuple[str, float]]:
    """Fuse results using Reciprocal Rank Fusion.

    RRF Formula: score(d) = Σ 1 / (k + rank(d))

    Args:
        k: RRF constant (default: 60, from Cormack et al. 2009)
    """
    scores = {}

    # Add vector scores
    for rank, (doc_id, _) in enumerate(vector_results):
        scores[doc_id] = scores.get(doc_id, 0) + 1/(k + rank + 1)

    # Add BM25 scores
    for rank, (doc_id, _) in enumerate(bm25_results):
        scores[doc_id] = scores.get(doc_id, 0) + 1/(k + rank + 1)

    # Sort by fused score
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**Why RRF?**
- **Score-agnostic:** No normalization needed (vector: 0-1, BM25: 0-∞)
- **Parameter-free:** k=60 works well across domains (empirically validated)
- **Robust:** Handles different score distributions

### Search Modes

**1. Hybrid (default):**
```python
results = await hybrid_search.search(query="ML", mode="hybrid")
# Uses RRF to combine vector + BM25
```

**2. Vector-only:**
```python
results = await hybrid_search.search(query="ML", mode="vector")
# Pure semantic search via Qdrant
```

**3. Keyword-only:**
```python
results = await hybrid_search.search(query="ML", mode="keyword")
# Pure BM25 keyword search
```

### Performance

**Benchmark (10K documents):**
| Mode | Latency (p95) | Precision@5 | Recall@5 |
|------|---------------|-------------|----------|
| Vector | 50ms | 0.78 | 0.65 |
| Keyword | 10ms | 0.65 | 0.58 |
| **Hybrid (RRF)** | **60ms** | **0.85** | **0.75** |

**Hybrid Advantage:** +9% precision vs. best single method

---

## Embeddings

### Overview

`EmbeddingService` wraps **BGE-M3** (1024-dim multilingual embeddings) via Ollama.

### Key Methods

```python
from src.components.vector_search.embeddings import get_embedding_service

# Get singleton
embedding_service = get_embedding_service()

# Embed query
query_embedding = await embedding_service.embed_query(
    "What is machine learning?"
)
# Returns: List[float] (1024 dimensions)

# Embed documents (batch)
doc_embeddings = await embedding_service.embed_documents([
    "Machine learning is...",
    "Neural networks are...",
    "Deep learning uses..."
])
# Returns: List[List[float]] (N x 1024)
```

### BGE-M3 Specifications

**Model:** BAAI/bge-m3 (ADR-024, Sprint 16)
- **Dimensions:** 1024
- **Languages:** 100+ languages (multilingual)
- **Context Length:** 8192 tokens
- **Performance:** 0.85 precision@5 on OMNITRACKER docs (+12% vs. nomic-embed-text)

**Why BGE-M3?**
- **Higher Quality:** +12% precision vs. nomic-embed-text (768D)
- **Multilingual:** Supports German + English technical docs
- **Longer Context:** 8192 tokens vs. 2048 (nomic-embed-text)
- **Cost:** $0 (local inference via Ollama)

### Configuration

```python
# src/core/config.py
class Settings(BaseSettings):
    embedding_model: str = "bge-m3"
    embedding_dimension: int = 1024
    embedding_batch_size: int = 10
```

### Performance

**Benchmark:**
- **Query Embedding:** ~180ms (single query)
- **Batch Embedding:** ~30ms per document (batch=10)
- **Model Size:** 274 MB
- **VRAM Usage:** ~500 MB during inference

---

## Ingestion Pipeline

### Overview

`ingest_documents()` orchestrates end-to-end document ingestion.

### Usage

```python
from src.components.vector_search.ingestion import ingest_documents
from pathlib import Path

# Ingest documents
stats = await ingest_documents(
    input_dir=Path("/documents"),
    collection_name="aegis-rag-chunks",
    chunk_size=1800,  # Sprint 21: Pure LLM extraction
    chunk_overlap=200
)

# Stats:
# {
#   "documents_processed": 100,
#   "chunks_created": 5000,
#   "vectors_indexed": 5000,
#   "processing_time_seconds": 450
# }
```

### Pipeline Stages

```python
# Simplified ingestion flow
async def ingest_documents(input_dir: Path):
    # 1. Discover documents
    files = list(input_dir.glob("*.pdf"))

    # 2. Parse documents (via Docling, Sprint 21)
    documents = await parse_documents(files)

    # 3. Chunk documents (adaptive)
    chunks = await chunk_documents(documents)

    # 4. Generate embeddings (BGE-M3)
    embeddings = await embed_chunks(chunks)

    # 5. Index to Qdrant
    await index_to_qdrant(chunks, embeddings)

    # 6. Build BM25 index
    await build_bm25_index(chunks)

    return stats
```

### Performance

**Benchmark (100 documents):**
- **Total Time:** 450s
- **Per Document:** ~4.5s
- **Bottleneck:** Docling parsing (~3s/doc) + embedding (~1s/doc)

---

## Usage Examples

### Basic Hybrid Search

```python
from src.components.vector_search.hybrid_search import HybridSearch

# Initialize
hybrid_search = HybridSearch()

# Search
results = await hybrid_search.search(
    query="How does vector search work?",
    mode="hybrid",
    top_k=5
)

# Process results
for result in results:
    print(f"Score: {result['score']:.2f}")
    print(f"Text: {result['text'][:100]}...")
    print(f"Metadata: {result['metadata']}")
```

### Filtered Search

```python
# Search with metadata filters
results = await hybrid_search.search(
    query="machine learning",
    filters={
        "file_name": {"$in": ["ml_book.pdf", "dl_paper.pdf"]},
        "page": {"$gte": 10, "$lte": 50}
    },
    top_k=10
)
```

### Batch Ingestion

```python
from src.components.vector_search.ingestion import ingest_documents
from pathlib import Path

# Ingest all PDFs in directory
stats = await ingest_documents(
    input_dir=Path("/documents/corpus"),
    collection_name="aegis-rag-chunks",
    batch_size=10  # Process 10 docs in parallel
)

print(f"Indexed {stats['chunks_created']} chunks in {stats['processing_time_seconds']}s")
```

---

## Testing

### Unit Tests

```bash
# Test Qdrant client
pytest tests/unit/components/vector_search/test_qdrant_client.py

# Test BM25 search
pytest tests/unit/components/vector_search/test_bm25_search.py

# Test hybrid search
pytest tests/unit/components/vector_search/test_hybrid_search.py
```

### Integration Tests

```bash
# Test ingestion pipeline
pytest tests/integration/components/vector_search/test_ingestion.py

# Test embeddings
pytest tests/integration/components/vector_search/test_embeddings.py
```

**Test Coverage:** 85% (180 unit tests, 32 integration tests)

---

## Configuration

### Environment Variables

```bash
# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=aegis-rag-chunks
QDRANT_VECTOR_SIZE=1024  # BGE-M3

# Embeddings
EMBEDDING_MODEL=bge-m3
EMBEDDING_BATCH_SIZE=10

# BM25
BM25_K1=1.5
BM25_B=0.75
BM25_CACHE_ENABLED=true

# Chunking
CHUNK_SIZE=1800  # Sprint 21
CHUNK_OVERLAP=200
```

### Qdrant Collection Schema

```python
from qdrant_client.models import Distance, VectorParams

collection_config = {
    "vectors": VectorParams(
        size=1024,  # BGE-M3
        distance=Distance.COSINE
    ),
    "optimizers_config": {
        "indexing_threshold": 10000
    },
    "hnsw_config": {
        "m": 16,  # Number of edges per node
        "ef_construct": 100  # Construction parameter
    }
}
```

---

## Performance Tuning

### Qdrant Optimization

**Scalar Quantization (8-bit):**
```python
# Reduces memory by 75% with minimal quality loss
await client.update_collection(
    collection_name="aegis-rag-chunks",
    quantization_config={
        "scalar": {
            "type": "int8",
            "always_ram": True
        }
    }
)
```

**HNSW Parameters:**
- `m=16`: Good balance between speed and accuracy
- `ef_construct=100`: Higher = better accuracy, slower indexing
- `ef=64` (search): Higher = better recall, slower search

### BM25 Optimization

**Redis Persistence:**
```python
# Enable BM25 model caching
BM25_CACHE_ENABLED=true

# Cache TTL (0 = no expiration)
BM25_CACHE_TTL=0
```

**Batch Processing:**
```python
# Process documents in batches
batch_size = 100  # Adjust based on memory
```

---

## Troubleshooting

### Issue: Slow search performance

**Symptoms:**
- Search latency >200ms p95
- High CPU/memory usage

**Solutions:**
```bash
# 1. Enable scalar quantization
# Reduces memory and speeds up search

# 2. Check Qdrant collection stats
curl http://localhost:6333/collections/aegis-rag-chunks

# 3. Reduce HNSW ef parameter
# Lower ef = faster search, slightly lower recall
```

### Issue: BM25 index not loading

**Symptoms:**
- `BM25NotFittedError: BM25 index not loaded`
- Long startup time (rebuilding index)

**Solutions:**
```bash
# Check Redis cache
docker exec aegis-redis redis-cli GET bm25:model:v1

# Rebuild BM25 index
curl -X POST http://localhost:8000/api/v1/retrieval/prepare-bm25

# Enable cache persistence
BM25_CACHE_ENABLED=true
```

### Issue: Low search quality

**Symptoms:**
- Poor retrieval results
- Low Precision@5 (<0.7)

**Solutions:**
```python
# 1. Switch to hybrid mode (if using vector/keyword only)
results = await hybrid_search.search(query="...", mode="hybrid")

# 2. Adjust RRF k parameter (default: 60)
# Higher k = more weight to top results
results = await rrf_fusion(..., k=80)

# 3. Increase chunk overlap for better context
CHUNK_OVERLAP=300  # From 200
```

---

## Related Documentation

- **ADR-009:** Reciprocal Rank Fusion for Hybrid Search
- **ADR-010:** Adaptive Chunking Strategy (Sprint 3)
- **ADR-024:** BGE-M3 System-Wide Embedding Standardization (Sprint 16)
- **Sprint 2 Summary:** [SPRINT_01-03_FOUNDATION_SUMMARY.md](../../docs/sprints/SPRINT_01-03_FOUNDATION_SUMMARY.md)
- **Sprint 16 Summary:** [SPRINT_16_PLAN.md](../../docs/sprints/SPRINT_16_PLAN.md)

---

**Last Updated:** 2025-11-10
**Sprint:** 2-16 (Evolved from Sprint 2 to Sprint 16)
**Maintainer:** Klaus Pommer + Claude Code (backend-agent, documentation-agent)
