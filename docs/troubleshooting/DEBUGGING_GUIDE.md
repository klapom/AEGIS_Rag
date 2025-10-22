# LightRAG Empty Query Results - Comprehensive Debugging Guide

## Your Issue Summary

- **Symptom**: query_graph() returns empty answer with answer='', entities=[], relationships=[]
- **Model**: llama3.2:3b via Ollama
- **Status**: insert_documents() completes successfully
- **Duration**: 168 seconds then fails
- **Root Cause**: Empty context from knowledge graph triggers failure

## Root Causes Identified

### 1. Context Not Built (Most Common)
From commit 29bac49f (Oct 2025):
```python
if context_result is None:
    logger.info("[kg_query] No query context could be built; returning no-result.")
    return None
```

### 2. Entity Extraction Failed
- Small models struggle with complex extraction prompts
- Delimiter corruption or format parsing failures

### 3. Vector Search Returns Nothing
- Embedding dimension mismatch
- Cosine threshold too high (default 0.2)
- Poor semantic matching

### 4. Context Window Too Small
- llama3.2:3b: ~8k tokens
- LightRAG default MAX_TOTAL_TOKENS: 30000 (EXCEEDS LIMIT!)

## Step 1: Enable Debug Logging

```bash
export VERBOSE_DEBUG=true
export LOG_LEVEL=DEBUG
```

Critical messages to watch:
```
[kg_query] No query context could be built
[naive_query] No relevant document chunks found
[entity_extraction] Failed to extract entities
```

## Step 2: Configuration Fixes for llama3.2:3b

Create .env file:

```bash
# Reduced for 8k context window
TOP_K=15
CHUNK_TOP_K=10
MAX_ENTITY_TOKENS=2500
MAX_RELATION_TOKENS=2500
MAX_TOTAL_TOKENS=7000

# Document processing
SUMMARY_MAX_TOKENS=600
SUMMARY_LENGTH_RECOMMENDED=400
SUMMARY_CONTEXT_SIZE=4000
CHUNK_SIZE=600

# Lower similarity threshold
COSINE_THRESHOLD=0.05
RERANK_BINDING=null

# Enable caching
ENABLE_LLM_CACHE=true
```

## Step 3: Verify Knowledge Graph Building

Check if entities were extracted:

```python
import json

# Check entities
with open("./rag_storage/vdb_entities.json", "r") as f:
    entities = json.load(f)
    print(f"Entities extracted: {len(entities)}")

# Check relationships
with open("./rag_storage/vdb_relationships.json", "r") as f:
    relationships = json.load(f)
    print(f"Relationships extracted: {len(relationships)}")
```

If empty → Entity extraction failed during insert

## Step 4: Test Models Individually

Test LLM:
```python
import asyncio
from lightrag.llm.ollama import ollama_model_complete

async def test():
    response = await ollama_model_complete(
        prompt="What is 2+2?",
        host="http://localhost:11434",
        hashing_kv=None,
    )
    print(response)

asyncio.run(test())
```

Test Embedding:
```python
import asyncio
from lightrag.llm.ollama import ollama_embed

async def test():
    embeddings = await ollama_embed(
        ["test"],
        embed_model="bge-m3:latest",
        host="http://localhost:11434",
    )
    print(f"Dimension: {embeddings.shape[1]}")  # Should be 1024

asyncio.run(test())
```

## Step 5: Llama3.2:3b Python Initialization

```python
from lightrag import LightRAG
from lightrag.llm.ollama import ollama_model_complete, ollama_embed
from lightrag.utils import EmbeddingFunc

rag = LightRAG(
    working_dir="./rag_storage",
    llm_model_func=ollama_model_complete,
    llm_model_name="llama3.2:3b",
    summary_max_tokens=600,
    llm_model_kwargs={
        "host": "http://localhost:11434",
        "options": {
            "num_ctx": 8192,
            "num_predict": 256,
            "temperature": 0.7,
        },
        "timeout": 300,
    },
    embedding_func=EmbeddingFunc(
        embedding_dim=1024,
        max_token_size=512,
        func=lambda texts: ollama_embed(
            texts,
            embed_model="bge-m3:latest",
            host="http://localhost:11434",
        ),
    ),
)
```

## Key Findings from Source Code

### Recent Fixes
- **Commit 29bac49f** (Oct 2025): Handle empty results gracefully
- **Commit 4ce823b4** (Sep 2025): Handle empty context in mix mode
- **Commit 6cc9411c** (Jul 2025): Handle empty merge tasks

### Critical Settings for llama3.2:3b
- DEFAULT_MAX_TOTAL_TOKENS: 30000 (TOO HIGH!)
- DEFAULT_SUMMARY_CONTEXT_SIZE: 12000 (TOO HIGH!)
- DEFAULT_COSINE_THRESHOLD: 0.2 (Too strict for small models)

### Embedding Info
- BGE-M3 outputs 1024 dimensions
- Must match EMBEDDING_DIM setting (default 1024) ✓

## Files Found in Repository

### Ollama Example
- `/examples/lightrag_ollama_demo.py` - Working example
- Uses qwen2.5-coder:7b by default
- Shows proper configuration patterns

### Core Query Logic
- `/lightrag/llm/ollama.py` - Ollama integration (supports streaming/JSON output)
- `/lightrag/prompt.py` - Contains all prompt templates including fail_response
- `/lightrag/constants.py` - All default constants
- `/lightrag/base.py` - QueryParam dataclass with all settings

### Environment Configuration
- `/env.example` - Full environment variable reference
- `/env.ollama-binding-options.example` - Ollama-specific options

### Key Commits Mentioning Empty Results
```
29bac49f Handle empty query results by returning None
4ce823b4 Handle empty context in mix mode
6cc9411c Handle empty tasks list in merge
6b37d3ca Add entity/relation chunk tracking
b6aedba7 Fix assistant message display content fallback
```

## Common Errors & Solutions

**Error: No relevant document chunks found**
→ Vector search returned nothing
→ Solution: Lower COSINE_THRESHOLD to 0.05

**Error: No entities extracted**
→ LLM extraction failed
→ Solution: Reduce CHUNK_SIZE, increase TIMEOUT

**Error: Timeout after 168 seconds**
→ Model too slow for insertion
→ Solution: Smaller chunks, increase timeout, or use larger model

**Error: Empty context in mix mode**
→ Both KG and vector search failed
→ Solution: Verify entities exist, lower thresholds

## When to Upgrade Model

llama3.2:3b limitations:
- Poor instruction following
- Weak entity extraction
- Limited context (8k tokens)

Better alternatives:
- llama3.2:7b (2x larger)
- qwen2.5-coder:7b (better extraction)
- mistral:7b

## Debugging Checklist

- [ ] Check entities extracted in vdb_entities.json
- [ ] Test models individually
- [ ] Reduce MAX_TOTAL_TOKENS < 8000
- [ ] Set COSINE_THRESHOLD to 0.05-0.1
- [ ] Try "naive" mode query first
- [ ] Monitor DEBUG logs
- [ ] Check Ollama process: ollama ps
- [ ] Verify bge-m3:latest is pulled

## Resources

- GitHub: https://github.com/HKUDS/LightRAG
- Ollama: https://github.com/ollama/ollama
- BGE-M3: https://huggingface.co/BAAI/bge-m3

