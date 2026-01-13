# FlagEmbedding Quick Start Guide

**Sprint 87 Feature 87.1** - Multi-Vector Embedding Service

---

## Installation

```bash
# Install FlagEmbedding library
pip install FlagEmbedding

# Verify installation
python -c "from FlagEmbedding import BGEM3FlagModel; print('OK')"
```

---

## Configuration

Add to `.env` file:

```bash
# Enable FlagEmbedding backend
EMBEDDING_BACKEND=flag-embedding

# Model settings
ST_MODEL_NAME=BAAI/bge-m3
ST_DEVICE=auto  # 'auto', 'cuda', 'cpu'
ST_BATCH_SIZE=32
ST_USE_FP16=true

# Sparse vector filtering
ST_SPARSE_MIN_WEIGHT=0.0  # Filter tokens below this weight
ST_SPARSE_TOP_K=100        # Keep only top-100 tokens (None = all)
```

---

## Basic Usage

### Option 1: Factory (Recommended)

```python
from src.components.shared.embedding_factory import get_embedding_service

# Get service based on EMBEDDING_BACKEND env var
service = get_embedding_service()

# Multi-vector embedding (flag-embedding backend)
result = service.embed_single("Hello world")
print(result.keys())  # dict_keys(['dense', 'sparse', 'sparse_vector'])
print(len(result["dense"]))  # 1024
print(len(result["sparse"]))  # ~50-100 tokens
```

### Option 2: Direct Instantiation

```python
from src.components.shared.flag_embedding_service import FlagEmbeddingService

service = FlagEmbeddingService(
    model_name="BAAI/bge-m3",
    device="auto",
    use_fp16=True,
    batch_size=32,
    sparse_min_weight=0.0,
    sparse_top_k=100,
)

result = service.embed_single("Hello world")
```

---

## API Reference

### Multi-Vector Methods (NEW)

```python
# Embed single text (returns dict with dense + sparse)
result = service.embed_single("Hello world")
# {
#   "dense": [0.1, 0.2, ...],  # 1024D vector
#   "sparse": {12345: 0.8, 67890: 0.6, ...},  # {token_id: weight}
#   "sparse_vector": SparseVector(indices=[...], values=[...])  # Qdrant format
# }

# Embed batch of texts
results = service.embed_batch(["text1", "text2", "text3"])
# list[dict] (same structure as embed_single)
```

### Backward Compatibility Methods

```python
# Embed single text (returns only dense vector)
dense = service.embed_single_dense("Hello world")
# [0.1, 0.2, ...]  # 1024D list[float]

# Embed batch (returns only dense vectors)
dense_batch = service.embed_batch_dense(["text1", "text2"])
# [[0.1, 0.2, ...], [0.3, 0.4, ...]]
```

### Statistics

```python
stats = service.get_stats()
print(stats)
# {
#   "model": "BAAI/bge-m3",
#   "device": "cuda:0",
#   "use_fp16": True,
#   "batch_size": 32,
#   "embedding_dim": 1024,
#   "sparse_min_weight": 0.0,
#   "sparse_top_k": 100,
#   "cache": {
#     "size": 42,
#     "max_size": 10000,
#     "hits": 100,
#     "misses": 42,
#     "hit_rate": 0.704
#   }
# }
```

---

## Sparse Vector Utilities

```python
from src.components.shared.sparse_vector_utils import (
    lexical_to_sparse_vector,
    dict_to_sparse_vector,
    merge_sparse_vectors,
)

# Convert FlagEmbedding lexical weights to Qdrant SparseVector
lexical_weights = {"hello": 0.8, "world": 0.6, "test": 0.2}
sparse_vector = lexical_to_sparse_vector(
    lexical_weights,
    min_weight=0.3,  # Filter "test"
    top_k=100        # Keep top-100 tokens
)
# SparseVector(indices=[hash("hello"), hash("world")], values=[0.8, 0.6])

# Convert {int: float} dict to SparseVector
sparse_dict = {12345: 0.8, 67890: 0.6}
sparse_vector = dict_to_sparse_vector(sparse_dict, top_k=100)

# Merge multiple sparse vectors
vec1 = SparseVector(indices=[1, 2, 3], values=[0.8, 0.6, 0.4])
vec2 = SparseVector(indices=[2, 3, 4], values=[0.5, 0.3, 0.7])
merged = merge_sparse_vectors([vec1, vec2], merge_strategy="sum")
# SparseVector(indices=[1, 2, 3, 4], values=[0.8, 1.1, 0.7, 0.7])
```

---

## Integration Examples

### Example 1: Ingestion Pipeline

```python
from src.components.shared.flag_embedding_service import get_flag_embedding_service
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

# Initialize services
embedding_service = get_flag_embedding_service()
qdrant_client = QdrantClient(url="http://localhost:6333")

# Embed documents
texts = ["Document 1 content", "Document 2 content"]
results = embedding_service.embed_batch(texts)

# Create Qdrant points with named vectors
points = []
for i, result in enumerate(results):
    point = PointStruct(
        id=i,
        vector={
            "dense": result["dense"],  # Named vector: dense
        },
        payload={
            "text": texts[i],
            "sparse": result["sparse"],  # Store sparse dict in payload
        },
    )
    points.append(point)

# Upload to Qdrant (dense vectors)
qdrant_client.upsert(collection_name="my_collection", points=points)

# TODO (Sprint 87.3): Upload sparse vectors separately
# await upsert_with_sparse(collection, points, [r["sparse_vector"] for r in results])
```

### Example 2: Hybrid Search Query

```python
from src.components.shared.flag_embedding_service import get_flag_embedding_service

# Initialize service
embedding_service = get_flag_embedding_service()

# Embed query
query = "What is hybrid search?"
query_embedding = embedding_service.embed_single(query)

# Extract dense and sparse vectors
dense_query = query_embedding["dense"]
sparse_query = query_embedding["sparse_vector"]

# TODO (Sprint 87.5): Use Qdrant Query API for hybrid search
# results = await qdrant_client.query_points(
#     collection_name="my_collection",
#     prefetch=[
#         Prefetch(query=dense_query, using="dense", limit=50),
#         Prefetch(query=sparse_query, using="sparse", limit=50),
#     ],
#     query=FusionQuery(fusion=Fusion.RRF),
#     limit=10,
# )
```

---

## Performance Tips

### 1. Use Batch Processing

```python
# SLOW (100 texts, ~10s)
for text in texts:
    result = service.embed_single(text)

# FAST (100 texts, ~1s)
results = service.embed_batch(texts)
```

### 2. Leverage Cache

```python
# First call: Cache miss (~10ms)
result1 = service.embed_single("Hello world")

# Second call: Cache hit (~0.01ms, 1000x faster!)
result2 = service.embed_single("Hello world")

# Results are identical
assert result1 == result2
```

### 3. Tune Sparse Filtering

```python
# No filtering: ~200 tokens per document, slower storage/retrieval
service = FlagEmbeddingService(sparse_min_weight=0.0, sparse_top_k=None)

# Aggressive filtering: ~20 tokens per document, faster but less precise
service = FlagEmbeddingService(sparse_min_weight=0.5, sparse_top_k=20)

# Recommended: Balance precision and performance
service = FlagEmbeddingService(sparse_min_weight=0.0, sparse_top_k=100)
```

### 4. Use FP16 on GPU

```python
# FP16 (half-precision): 2x faster, 50% less VRAM, ~0.1% accuracy loss
service = FlagEmbeddingService(use_fp16=True, device="cuda")

# FP32 (full-precision): Slower but highest accuracy
service = FlagEmbeddingService(use_fp16=False, device="cuda")
```

---

## Testing

```bash
# Run all 5 test cases
python scripts/test_flag_embedding.py

# Expected output:
# ✓ Test 1: Single Text Embedding
# ✓ Test 2: Batch Embedding
# ✓ Test 3: Cache Performance
# ✓ Test 4: Backward Compatibility
# ✓ Test 5: Sparse Filtering
# All tests passed! ✓

# Benchmark mode (1000 texts)
python scripts/test_flag_embedding.py --benchmark --num-texts 1000
```

---

## Troubleshooting

### Import Error: FlagEmbedding not found

```bash
# Install FlagEmbedding
pip install FlagEmbedding

# Verify installation
python -c "from FlagEmbedding import BGEM3FlagModel; print('OK')"
```

### CUDA Out of Memory

```python
# Reduce batch size
service = FlagEmbeddingService(batch_size=16)  # Default: 32

# Use CPU instead of GPU
service = FlagEmbeddingService(device="cpu")

# Use FP16 to reduce VRAM usage
service = FlagEmbeddingService(use_fp16=True)
```

### Slow Performance

```python
# Check device (should be "cuda:0" on GPU)
print(service._model.device)

# Enable FP16 for 2x speedup
service = FlagEmbeddingService(use_fp16=True)

# Increase batch size (if VRAM allows)
service = FlagEmbeddingService(batch_size=64)
```

### Sparse Vectors Too Large

```python
# Apply top-k filtering
service = FlagEmbeddingService(sparse_top_k=100)  # Keep only top-100 tokens

# Apply min-weight filtering
service = FlagEmbeddingService(sparse_min_weight=0.3)  # Filter low-weight tokens

# Combine both
service = FlagEmbeddingService(sparse_min_weight=0.1, sparse_top_k=50)
```

---

## Migration Guide

### From SentenceTransformers to FlagEmbedding

**Before:**
```python
from src.components.shared.sentence_transformers_embedding import (
    SentenceTransformersEmbeddingService
)

service = SentenceTransformersEmbeddingService()
embedding = service.embed_single("Hello world")  # list[float]
```

**After:**
```python
from src.components.shared.flag_embedding_service import FlagEmbeddingService

service = FlagEmbeddingService()

# Option 1: Multi-vector (recommended)
result = service.embed_single("Hello world")
dense = result["dense"]  # list[float]
sparse = result["sparse"]  # dict[int, float]

# Option 2: Backward compat (dense-only)
embedding = service.embed_single_dense("Hello world")  # list[float]
```

### From Ollama to FlagEmbedding

**Before:**
```python
from src.components.shared.embedding_service import get_embedding_service

service = get_embedding_service()
embedding = service.embed_single("Hello world")  # list[float]
```

**After:**
```bash
# Update .env
EMBEDDING_BACKEND=flag-embedding
```

```python
from src.components.shared.embedding_factory import get_embedding_service

service = get_embedding_service()  # Returns FlagEmbeddingService

# Multi-vector
result = service.embed_single("Hello world")

# Dense-only (backward compat)
embedding = service.embed_single_dense("Hello world")
```

---

## FAQ

**Q: Is FlagEmbedding slower than SentenceTransformers?**
A: Yes, ~10-20% slower due to sparse vector generation, but the sync guarantee is worth it.

**Q: Can I use FlagEmbedding without GPU?**
A: Yes, but 10-50x slower. Use `device="cpu"` and `use_fp16=False`.

**Q: Do I need to re-embed all documents?**
A: Yes, to get sparse vectors. Use migration script (Sprint 87.6).

**Q: Can I disable sparse vectors?**
A: Use backward compat methods (`embed_single_dense`) or switch backend to `sentence-transformers`.

**Q: How much storage do sparse vectors need?**
A: ~5-10KB per document with `sparse_top_k=100` (vs ~4KB for dense).

**Q: Is the cache thread-safe?**
A: No, use separate service instances for multi-threading or add locks.

---

## Next Steps

- **Sprint 87.3**: Multi-vector Qdrant collections (named vectors + sparse vectors)
- **Sprint 87.4**: Embedding node integration (auto-generate sparse vectors)
- **Sprint 87.5**: Hybrid retrieval with Query API (server-side RRF)
- **Sprint 87.6**: Zero-downtime migration script
- **Sprint 87.7**: RAGAS validation (before/after comparison)

---

**Last Updated:** 2026-01-13
**Sprint:** 87 (BGE-M3 Native Hybrid Search)
**Feature:** 87.1 (FlagEmbedding Service)
