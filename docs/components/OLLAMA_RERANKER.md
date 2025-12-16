# Ollama Reranker - TD-059 Implementation

**Sprint 48 Feature 48.8: Ollama-Based Reranking**

## Overview

The Ollama Reranker provides document reranking using the `bge-reranker-v2-m3` model via Ollama's API, eliminating the need for `sentence-transformers` dependency in Docker containers.

## Why Ollama Reranker?

| Feature | OllamaReranker | CrossEncoderReranker (Legacy) |
|---------|----------------|-------------------------------|
| Model | bge-reranker-v2-m3 | ms-marco-MiniLM-L-6-v2 |
| Backend | Ollama HTTP API | sentence-transformers (local) |
| Dependencies | None (uses existing Ollama) | sentence-transformers (~2GB) |
| Docker Size | No increase | +2GB PyTorch/Transformers |
| Multilingual | Yes (91 languages) | No (English only) |
| Deployment | Shared Ollama service | Embedded in API container |

## Installation

### 1. Pull the Reranker Model

The `bge-reranker-v2-m3` model must be available in Ollama:

```bash
# Pull the model (one-time setup)
ollama pull bge-reranker-v2-m3
```

### 2. Verify Model Availability

```bash
# Check if model is available
curl http://localhost:11434/api/tags | grep bge-reranker

# Or via Ollama CLI
ollama list | grep bge-reranker
```

Expected output:
```
bge-reranker-v2-m3:latest    <timestamp>    <size>
```

### 3. Configure AegisRAG

Set environment variables in `.env` or `docker-compose.yml`:

```bash
# Enable reranking
RERANKER_ENABLED=true

# Use Ollama backend (default)
RERANKER_BACKEND=ollama

# Ollama model (default: bge-reranker-v2-m3)
RERANKER_OLLAMA_MODEL=bge-reranker-v2-m3

# Number of documents to return after reranking
RERANKER_TOP_K=10
```

## Usage

### Python API

```python
from src.components.retrieval.ollama_reranker import OllamaReranker

# Initialize reranker
reranker = OllamaReranker(
    model="bge-reranker-v2-m3",
    top_k=10
)

# Rerank documents
query = "What is vector search?"
documents = [
    "Vector search uses embeddings for semantic similarity",
    "BM25 is a probabilistic keyword search algorithm",
    "Hybrid search combines vector and keyword approaches"
]

# Returns list of (doc_index, score) tuples sorted by relevance
ranked = await reranker.rerank(query, documents, top_k=5)

# Results: [(0, 0.95), (2, 0.78), (1, 0.23)]
# Doc 0 is most relevant (score: 0.95)
# Doc 2 is second (score: 0.78)
# Doc 1 is least relevant (score: 0.23)
```

### Automatic Integration

The Ollama Reranker is automatically used in `FourWayHybridSearch` when:
- `RERANKER_ENABLED=true`
- `RERANKER_BACKEND=ollama` (default)
- `use_reranking=True` is passed to the search function

```python
from src.components.retrieval.four_way_hybrid_search import four_way_search

results = await four_way_search(
    query="How does authentication work?",
    top_k=10,
    use_reranking=True  # Enables Ollama reranking
)
```

## Configuration

All settings in `src/core/config.py`:

```python
# Enable/disable reranking globally
reranker_enabled: bool = True

# Backend selection: "ollama" or "sentence-transformers"
reranker_backend: str = "ollama"

# Ollama model for reranking
reranker_ollama_model: str = "bge-reranker-v2-m3"

# Number of documents to return after reranking
reranker_top_k: int = 10
```

## Performance

**Measured on DGX Spark (NVIDIA GB10, Blackwell):**

| Metric | Value | Notes |
|--------|-------|-------|
| Latency per document | 50-100ms | Depends on Ollama server load |
| 5 documents | ~250-500ms | Sequential scoring |
| 10 documents | ~500-1000ms | Sequential scoring |
| 20 documents | <2000ms | Tested in integration tests |

**Tips for Performance:**
- Reranking is done sequentially per document
- Limit initial candidate set with RRF before reranking
- Use `top_k` to control how many results to rerank
- Consider caching for repeated queries

## Model Information

**BAAI/bge-reranker-v2-m3:**
- **Type:** Cross-encoder reranker
- **Languages:** 91+ languages (multilingual)
- **Input:** Query + Document pairs
- **Output:** Relevance score (0-10, normalized to 0-1)
- **Context Window:** Up to 8192 tokens
- **Compatibility:** Works with BGE-M3 embeddings (ADR-024)

**Model Card:** https://huggingface.co/BAAI/bge-reranker-v2-m3

## Testing

### Unit Tests

```bash
# Run unit tests (mocked Ollama API)
poetry run pytest tests/unit/components/retrieval/test_ollama_reranker.py -v
```

### Integration Tests

```bash
# Run integration tests (requires Ollama + model)
poetry run pytest tests/integration/components/test_ollama_reranker_integration.py -v

# Skip if Ollama not available
poetry run pytest tests/integration/components/test_ollama_reranker_integration.py -v -m "not requires_ollama"
```

## Troubleshooting

### Model Not Found

**Error:**
```
Error: model 'bge-reranker-v2-m3' not found
```

**Solution:**
```bash
ollama pull bge-reranker-v2-m3
```

### Ollama Not Running

**Error:**
```
Connection refused to localhost:11434
```

**Solution:**
```bash
# Start Ollama service
systemctl start ollama  # Linux
# or
docker compose up -d ollama  # Docker
```

### Slow Reranking

If reranking is too slow (>100ms per document):
1. Check Ollama server load: `ollama ps`
2. Reduce number of documents to rerank
3. Use GPU acceleration for Ollama (if available)
4. Consider using a smaller reranker model

### Fallback to Legacy Reranker

To use the legacy sentence-transformers reranker:

```bash
# In .env or docker-compose.yml
RERANKER_BACKEND=sentence-transformers
```

**Note:** This requires `sentence-transformers` to be installed:
```bash
poetry install --with reranking
```

## Migration from CrossEncoderReranker

The Ollama Reranker is a **drop-in replacement** for CrossEncoderReranker:

**Before (Legacy):**
```python
from src.components.retrieval.reranker import CrossEncoderReranker

reranker = CrossEncoderReranker()
results = await reranker.rerank(query, documents, top_k=5)
# Returns: List[RerankResult]
```

**After (Ollama):**
```python
from src.components.retrieval.ollama_reranker import OllamaReranker

reranker = OllamaReranker()
results = await reranker.rerank(query, documents, top_k=5)
# Returns: List[Tuple[int, float]] - (doc_index, score)
```

**Key Differences:**
- OllamaReranker returns `(index, score)` tuples instead of `RerankResult` objects
- Scores are normalized to `[0.0, 1.0]` range
- No model download required (uses Ollama)
- Supports multilingual content

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  FourWayHybridSearch                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Vector    │  │    BM25     │  │    Graph    │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│         │                │                │             │
│         └────────────────┴────────────────┘             │
│                          │                              │
│                    ┌─────▼─────┐                        │
│                    │    RRF    │                        │
│                    │  Fusion   │                        │
│                    └─────┬─────┘                        │
│                          │                              │
│                          │ if use_reranking=True        │
│                    ┌─────▼─────────┐                    │
│                    │ OllamaReranker│                    │
│                    └─────┬─────────┘                    │
│                          │                              │
│                          ▼                              │
│               ┌──────────────────────┐                  │
│               │  Ollama API          │                  │
│               │  bge-reranker-v2-m3  │                  │
│               └──────────────────────┘                  │
│                          │                              │
│                          ▼                              │
│               ┌──────────────────────┐                  │
│               │  Reranked Results    │                  │
│               │  [(idx, score), ...] │                  │
│               └──────────────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

## References

- **TD-059:** Technical Debt tracking reranking in Docker containers
- **ADR-024:** BGE-M3 embeddings decision
- **Sprint 48 Feature 48.8:** Ollama Reranker implementation
- **Model Card:** https://huggingface.co/BAAI/bge-reranker-v2-m3
- **Academic Paper:** BGE-M3: https://arxiv.org/abs/2402.03216
