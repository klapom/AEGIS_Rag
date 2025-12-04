# Sentence-Transformers Embedding Usage Guide

**Sprint:** Sprint 35 Feature 35.8
**Date:** 2025-12-04

## Overview

High-performance embedding service using sentence-transformers for DGX Spark deployment.
Provides 5-10x performance improvement over Ollama HTTP API.

## Performance Comparison

| Backend | Throughput | GPU Utilization | Latency (100 texts) |
|---------|------------|-----------------|---------------------|
| Ollama HTTP | 50-100 emb/s | 30-50% | ~1000ms |
| SentenceTransformers | 500-1000 emb/s | 90%+ | ~100ms |

## Configuration

### Environment Variables

```bash
# .env or .env.dgx-spark
EMBEDDING_BACKEND=sentence-transformers  # or 'ollama' for default

# Sentence-Transformers settings (only used if backend=sentence-transformers)
ST_MODEL_NAME=BAAI/bge-m3        # HuggingFace model
ST_DEVICE=auto                   # 'auto', 'cuda', 'cpu'
ST_BATCH_SIZE=64                 # Batch size for GPU processing
```

### Python Configuration

```python
# src/core/config.py
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    embedding_backend: Literal["ollama", "sentence-transformers"] = Field(
        default="ollama",
        description="Embedding backend selection"
    )
    st_model_name: str = Field(
        default="BAAI/bge-m3",
        description="HuggingFace model name"
    )
    st_device: str = Field(
        default="auto",
        description="Device: 'auto', 'cuda', 'cpu'"
    )
    st_batch_size: int = Field(
        default=64,
        description="Batch size for GPU processing"
    )
```

## Usage Examples

### Basic Usage (Factory Pattern)

```python
from src.components.shared.embedding_factory import get_embedding_service

# Get service instance (backend selected automatically from config)
service = get_embedding_service()

# Single text embedding
embedding = service.embed_single("Hello world")
print(f"Embedding dimension: {len(embedding)}")  # 1024

# Batch embedding (GPU accelerated)
texts = ["text1", "text2", "text3", ...]
embeddings = service.embed_batch(texts)
print(f"Generated {len(embeddings)} embeddings")
```

### Direct SentenceTransformers Service

```python
from src.components.shared.sentence_transformers_embedding import (
    SentenceTransformersEmbeddingService
)

# Create service with custom config
service = SentenceTransformersEmbeddingService(
    model_name="BAAI/bge-m3",
    device="cuda",
    batch_size=128,
    cache_max_size=10000
)

# Use service
embedding = service.embed_single("Hello world")
embeddings = service.embed_batch(["text1", "text2", ...])
```

### Ollama Backend (Default)

```python
# .env
EMBEDDING_BACKEND=ollama

# Python code (no changes needed)
from src.components.shared.embedding_factory import get_embedding_service

service = get_embedding_service()  # Returns UnifiedEmbeddingService
embedding = service.embed_single("Hello world")
```

## Performance Optimization

### Batch Size Tuning

```python
# Smaller GPUs (6GB VRAM)
ST_BATCH_SIZE=32

# Medium GPUs (12GB VRAM)
ST_BATCH_SIZE=64

# Large GPUs (24GB+ VRAM)
ST_BATCH_SIZE=128
```

### Device Selection

```python
# Automatic (CUDA if available, else CPU)
ST_DEVICE=auto

# Force CUDA
ST_DEVICE=cuda

# Force CPU (testing only)
ST_DEVICE=cpu
```

### Cache Configuration

```python
service = SentenceTransformersEmbeddingService(
    cache_max_size=10000  # Default: 10,000 embeddings
)

# Check cache statistics
stats = service.get_stats()
print(f"Cache hit rate: {stats['cache']['hit_rate']:.2%}")
```

## Migration Guide

### Step 1: Update Configuration

```bash
# .env.dgx-spark
EMBEDDING_BACKEND=sentence-transformers
ST_MODEL_NAME=BAAI/bge-m3
ST_DEVICE=auto
ST_BATCH_SIZE=64
```

### Step 2: No Code Changes Required

The factory pattern ensures backward compatibility. Existing code using
`get_embedding_service()` will automatically use the new backend.

```python
# Existing code (no changes needed)
from src.components.shared.embedding_factory import get_embedding_service

service = get_embedding_service()  # Backend selected from config
embedding = service.embed_single("Hello world")
```

### Step 3: Verify Performance

```python
import time

service = get_embedding_service()

# Benchmark batch processing
texts = [f"test text {i}" for i in range(1000)]

start = time.perf_counter()
embeddings = service.embed_batch(texts)
duration = time.perf_counter() - start

print(f"Generated {len(embeddings)} embeddings in {duration:.2f}s")
print(f"Throughput: {len(embeddings)/duration:.2f} embeddings/sec")
```

## Troubleshooting

### Issue: Model Download Fails

```bash
# Solution: Check HuggingFace cache directory
ls ~/.cache/huggingface/hub/

# Solution: Manually download model
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"
```

### Issue: CUDA Out of Memory

```bash
# Solution: Reduce batch size
ST_BATCH_SIZE=32  # or 16

# Solution: Use CPU (slower but works)
ST_DEVICE=cpu
```

### Issue: Slow Performance on First Run

**Expected behavior**: First run downloads model from HuggingFace (~400MB for BGE-M3).
Subsequent runs use cached model and are fast.

```python
# First run: ~30s (model download)
service = get_embedding_service()
embedding = service.embed_single("test")

# Subsequent runs: <100ms
embedding = service.embed_single("test2")
```

## API Compatibility

Both backends implement the same API:

| Method | Returns | Description |
|--------|---------|-------------|
| `embed_single(text: str)` | `list[float]` | Embed single text |
| `embed_batch(texts: list[str])` | `list[list[float]]` | Embed batch of texts |
| `get_stats()` | `dict[str, Any]` | Get service statistics |

## Best Practices

1. **Use Factory Pattern**: Always use `get_embedding_service()` for backend flexibility
2. **Batch Processing**: Use `embed_batch()` for multiple texts (5-10x faster)
3. **Cache Awareness**: Identical texts are cached automatically
4. **Device Selection**: Use `auto` for development, explicit for production
5. **Batch Size**: Tune based on GPU VRAM (64 is good default)

## See Also

- `/home/admin/projects/aegisrag/AEGIS_Rag/src/components/shared/sentence_transformers_embedding.py` - Implementation
- `/home/admin/projects/aegisrag/AEGIS_Rag/src/components/shared/embedding_factory.py` - Factory
- `/home/admin/projects/aegisrag/AEGIS_Rag/src/core/config.py` - Configuration
- `/home/admin/projects/aegisrag/AEGIS_Rag/.env.dgx-spark.template` - Example config
