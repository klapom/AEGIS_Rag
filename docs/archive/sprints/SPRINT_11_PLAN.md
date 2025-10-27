# Sprint 11 Plan: Technical Debt Resolution & Unified Ingestion Pipeline

**Sprint Goal:** Resolve critical technical debt and implement unified document ingestion
**Duration:** 2 Wochen
**Story Points:** 34 SP
**Start Date:** 2025-10-21
**Branch:** `sprint-11-dev`

---

## Executive Summary

Sprint 11 fokussiert auf **technische Schuldenbeseitigung** und **Pipeline-Vereinheitlichung**. Nach der Analyse der ursprünglichen Architektur implementieren wir eine **Unified Ingestion Pipeline**, die Dokumente parallel zu Qdrant, BM25 UND Neo4j (Graph) indexiert.

### Key Insights from Architecture Review

**Original Design (Sprint 2-7):**
- ❌ Separate Pipelines: Vector (Sprint 2) → Graph (Sprint 5) → Memory (Sprint 7)
- ❌ Keine gemeinsame Ingestion
- ❌ Integration nur auf Retrieval-Ebene geplant

**Current Problem:**
- ✅ Qdrant + BM25: Funktioniert (DocumentIngestionPipeline)
- ❌ Neo4j/LightRAG: NICHT im Upload-Flow
- ❌ Knowledge Graph bleibt leer bei Document Upload

**Sprint 11 Solution:**
- ✅ **Unified Embedding Service:** Shared Ollama client + cache
- ✅ **Unified Ingestion Pipeline:** Parallel indexing zu allen Systemen
- ✅ **Single Upload API:** User hochladen → alle Systeme gefüllt

### Sprint 11 Priorities

1. **🔴 CRITICAL:** LLM-basierte Antwortgenerierung (TD-01)
2. **🔴 CRITICAL:** Unified Embedding Service (NEW - Architecture Enhancement)
3. **🔴 CRITICAL:** Unified Ingestion Pipeline (NEW - Architecture Enhancement)
4. **🟠 HIGH:** Fix LightRAG Entity Extraction (TD-14: qwen3 → llama3.2)
5. **🟠 HIGH:** Redis LangGraph Checkpointer (TD-02)
6. **🟠 HIGH:** E2E Test Fixes (TD-07)
7. **🟡 MEDIUM:** Performance Improvements (TD-09, TD-15, TD-16)
8. **🟡 MEDIUM:** Enhanced Visualization (TD-17, TD-22)
9. **✅ NEW:** Integration Tests für Sprint 10 Features

---

## Features Overview

| ID | Feature | SP | Priority | Dependencies | Status |
|----|---------|----|---------| -------------|--------|
| 11.1 | LLM-Based Answer Generation | 5 | 🔴 CRITICAL | None | 📋 TODO |
| 11.2 | Shared Embedding Service | 2 | 🔴 CRITICAL | None | 📋 TODO |
| 11.3 | Unified Ingestion Pipeline | 3 | 🔴 CRITICAL | 11.2 | 📋 TODO |
| 11.4 | Fix LightRAG Entity Extraction | 2 | 🟠 HIGH | 11.2, 11.3 | 📋 TODO |
| 11.5 | Redis LangGraph Checkpointer | 3 | 🟠 HIGH | None | 📋 TODO |
| 11.6 | E2E Test Fixes | 3 | 🟠 HIGH | 11.3, 11.4 | 📋 TODO |
| 11.7 | Community Detection Performance | 3 | 🟡 MEDIUM | 11.4 | 📋 TODO |
| 11.8 | Temporal Retention Policy | 2 | 🟡 MEDIUM | None | 📋 TODO |
| 11.9 | Enhanced Graph Visualization | 3 | 🟡 MEDIUM | 11.3 | 📋 TODO |
| 11.10 | Sprint 10 Integration Tests | 8 | 🟠 HIGH | 11.1 | 📋 TODO |
| **TOTAL** | | **34** | | | |

---

## Week 1: Critical Fixes + Unified Pipeline

### Feature 11.1: LLM-Based Answer Generation (5 SP)

**Technical Debt:** TD-01
**Priority:** 🔴 CRITICAL
**Files:** `src/agents/graph.py`, `src/agents/answer_generator.py` (new), `src/prompts/answer_prompts.py` (new)

#### Current Problem

```python
# src/agents/graph.py:57-94
async def simple_answer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Sprint 10 Quick Fix: This is a placeholder answer generator.
    TODO: Replace with proper LLM-based generation in future sprint.
    """
    # Just concatenates context - NO actual answering!
    context_text = "\n\n".join([ctx.get("text", "") for ctx in contexts[:3]])
    answer = f"Based on the retrieved documents:\n\n{context_text}"
```

**Impact:**
- ❌ No synthesis or reasoning
- ❌ Just returns raw context
- ❌ Poor user experience

#### Solution Architecture

**NEW FILE:** `src/prompts/answer_prompts.py`

```python
"""Answer generation prompts for RAG system."""

ANSWER_GENERATION_PROMPT = """You are a helpful AI assistant answering questions based on retrieved context.

**Context Information:**
{context}

**User Question:**
{query}

**Instructions:**
1. Analyze the provided context carefully
2. Answer the question directly and concisely
3. Use ONLY information from the context
4. If context doesn't contain the answer, say "I don't have enough information"
5. Cite sources when possible using [Source: filename]

**Answer:**"""

MULTI_HOP_REASONING_PROMPT = """You are an AI assistant that combines information from multiple sources.

**Retrieved Documents:**
{contexts}

**Question:**
{query}

**Task:**
Connect information across documents to answer the multi-hop question.
Show your reasoning step-by-step.

**Answer:**"""
```

**NEW FILE:** `src/agents/answer_generator.py`

```python
"""LLM-based answer generation for RAG."""

import structlog
from typing import Any

from langchain_ollama import ChatOllama
from src.core.config import settings
from src.prompts.answer_prompts import (
    ANSWER_GENERATION_PROMPT,
    MULTI_HOP_REASONING_PROMPT,
)

logger = structlog.get_logger(__name__)


class AnswerGenerator:
    """Generate answers using LLM with retrieved context."""

    def __init__(self, model_name: str | None = None, temperature: float = 0.0):
        """Initialize answer generator.

        Args:
            model_name: Ollama model name (default: llama3.2:3b)
            temperature: LLM temperature for answer generation
        """
        self.model_name = model_name or settings.router_model
        self.temperature = temperature
        self.llm = ChatOllama(
            model=self.model_name,
            temperature=self.temperature,
            base_url=settings.ollama_base_url,
        )

        logger.info(
            "answer_generator_initialized",
            model=self.model_name,
            temperature=self.temperature,
        )

    async def generate_answer(
        self,
        query: str,
        contexts: list[dict[str, Any]],
        mode: str = "simple",
    ) -> str:
        """Generate answer from query and retrieved contexts.

        Args:
            query: User question
            contexts: Retrieved document contexts
            mode: "simple" or "multi_hop"

        Returns:
            Generated answer string
        """
        if not contexts:
            return self._no_context_answer(query)

        # Format contexts
        context_text = self._format_contexts(contexts)

        # Select prompt based on mode
        if mode == "multi_hop":
            prompt = MULTI_HOP_REASONING_PROMPT.format(
                contexts=context_text, query=query
            )
        else:
            prompt = ANSWER_GENERATION_PROMPT.format(context=context_text, query=query)

        # Generate answer
        logger.debug("generating_answer", query=query[:100], contexts_count=len(contexts))

        try:
            response = await self.llm.ainvoke(prompt)
            answer = response.content.strip()

            logger.info(
                "answer_generated",
                query=query[:100],
                answer_length=len(answer),
                contexts_used=len(contexts),
            )

            return answer

        except Exception as e:
            logger.error("answer_generation_failed", query=query[:100], error=str(e))
            return self._fallback_answer(query, contexts)

    def _format_contexts(self, contexts: list[dict[str, Any]]) -> str:
        """Format contexts for prompt."""
        formatted = []
        for i, ctx in enumerate(contexts[:5], 1):  # Top 5 contexts
            text = ctx.get("text", "")
            source = ctx.get("source", "Unknown")
            formatted.append(f"[Context {i} - Source: {source}]\n{text}")
        return "\n\n".join(formatted)

    def _no_context_answer(self, query: str) -> str:
        """Answer when no context retrieved."""
        return (
            "I don't have enough information in the knowledge base to answer this question. "
            "Please try rephrasing your question or providing more context."
        )

    def _fallback_answer(self, query: str, contexts: list[dict[str, Any]]) -> str:
        """Fallback answer if LLM generation fails."""
        context_text = self._format_contexts(contexts)
        return f"Based on the retrieved documents:\n\n{context_text}"


# Global instance (singleton)
_answer_generator: AnswerGenerator | None = None


def get_answer_generator() -> AnswerGenerator:
    """Get global AnswerGenerator instance."""
    global _answer_generator
    if _answer_generator is None:
        _answer_generator = AnswerGenerator()
    return _answer_generator
```

**REPLACE in:** `src/agents/graph.py`

```python
# OLD: simple_answer_node (lines 57-94)
# NEW: llm_answer_node

from src.agents.answer_generator import get_answer_generator

async def llm_answer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate LLM-based answer from retrieved contexts.

    Replaces simple_answer_node placeholder with proper LLM generation.
    """
    query = state.get("query", "")
    contexts = state.get("contexts", [])

    logger.info("llm_answer_node_start", query=query[:100], contexts_count=len(contexts))

    # Generate answer using LLM
    generator = get_answer_generator()
    answer = await generator.generate_answer(query, contexts, mode="simple")

    state["answer"] = answer

    logger.info("llm_answer_node_complete", answer_length=len(answer))

    return state


# Update graph builder
graph_builder.add_node("answer", llm_answer_node)  # Was: simple_answer_node
```

#### Testing

**NEW FILE:** `tests/agents/test_answer_generator.py`

```python
"""Tests for LLM-based answer generation."""

import pytest
from src.agents.answer_generator import AnswerGenerator


@pytest.mark.asyncio
async def test_answer_generation_with_context():
    """Test answer generation with valid context."""
    generator = AnswerGenerator()

    contexts = [
        {
            "text": "AEGIS RAG uses LangGraph for multi-agent orchestration.",
            "source": "README.md",
        },
        {
            "text": "LangGraph provides state management and conditional routing.",
            "source": "docs/architecture.md",
        },
    ]

    answer = await generator.generate_answer(
        query="What does AEGIS RAG use for orchestration?",
        contexts=contexts,
    )

    assert answer
    assert len(answer) > 50
    assert "LangGraph" in answer or "langgraph" in answer.lower()


@pytest.mark.asyncio
async def test_answer_generation_no_context():
    """Test answer generation with no context."""
    generator = AnswerGenerator()

    answer = await generator.generate_answer(
        query="What is the meaning of life?",
        contexts=[],
    )

    assert "don't have enough information" in answer.lower()


@pytest.mark.asyncio
async def test_multi_hop_reasoning():
    """Test multi-hop reasoning mode."""
    generator = AnswerGenerator()

    contexts = [
        {"text": "AEGIS RAG uses LangGraph.", "source": "doc1.md"},
        {"text": "LangGraph was created by LangChain.", "source": "doc2.md"},
    ]

    answer = await generator.generate_answer(
        query="Who created the orchestration framework used by AEGIS RAG?",
        contexts=contexts,
        mode="multi_hop",
    )

    assert answer
    assert "LangChain" in answer or "langchain" in answer.lower()
```

#### Success Criteria

- ✅ AnswerGenerator generates proper answers using LLM
- ✅ Answers are contextual and coherent (not just concatenation)
- ✅ Source citations included where possible
- ✅ Graceful fallback when no context available
- ✅ Integration tests pass with real LLM
- ✅ Chat API returns synthesized answers

---

### Feature 11.2: Shared Embedding Service (2 SP) 🆕

**Priority:** 🔴 CRITICAL
**Rationale:** LightRAG and Qdrant beide generieren Embeddings mit `nomic-embed-text` → Shared Service spart 30-50% Ollama-Requests

#### Current Problem

**Duplicate Embedding Infrastructure:**

```python
# src/components/vector_search/embeddings.py
class EmbeddingService:
    """Qdrant pipeline uses OllamaEmbedding from LlamaIndex."""
    def __init__(self):
        self.ollama_embedding = OllamaEmbedding(
            model_name="nomic-embed-text",
            base_url=settings.ollama_base_url,
        )
        self.cache = LRUCache(max_size=10000)

# src/components/graph_rag/lightrag_wrapper.py
class OllamaEmbeddingFunc:
    """LightRAG uses custom Ollama client."""
    async def __call__(self, texts: list[str]) -> list[list[float]]:
        from ollama import AsyncClient
        client = AsyncClient(host=settings.ollama_base_url)
        # Duplicate Ollama connection!
```

**Issues:**
- ❌ Two separate Ollama clients
- ❌ Two separate caches (keine cache sharing!)
- ❌ Duplicate retry logic
- ❌ No unified metrics

#### Solution Architecture

**NEW FILE:** `src/components/shared/embedding_service.py`

```python
"""Unified embedding service for all AEGIS RAG components.

Shared by:
- DocumentIngestionPipeline (Qdrant chunks)
- LightRAG (Entity embeddings)
- Graphiti (Memory embeddings)
"""

import hashlib
from collections import OrderedDict
from typing import Any

import structlog
from ollama import AsyncClient
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import settings
from src.core.exceptions import LLMError

logger = structlog.get_logger(__name__)


class LRUCache:
    """Least Recently Used (LRU) cache with size limit."""

    def __init__(self, max_size: int = 10000):
        self.cache: OrderedDict[str, list[float]] = OrderedDict()
        self.max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> list[float] | None:
        """Get item from cache."""
        if key in self.cache:
            self._hits += 1
            self.cache.move_to_end(key)
            return self.cache[key]
        self._misses += 1
        return None

    def set(self, key: str, value: list[float]) -> None:
        """Add item to cache."""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value

        if len(self.cache) > self.max_size:
            evicted_key, _ = self.cache.popitem(last=False)
            logger.debug("cache_eviction", evicted_key=evicted_key[:16])

    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate(),
        }


class UnifiedEmbeddingService:
    """Shared embedding service for all AEGIS RAG components.

    Features:
    - Single Ollama client for all embeddings
    - Shared LRU cache (improves hit rate across components)
    - Unified retry logic and error handling
    - Centralized metrics and monitoring
    """

    def __init__(
        self,
        model_name: str | None = None,
        embedding_dim: int = 768,
        cache_max_size: int = 10000,
    ):
        """Initialize unified embedding service.

        Args:
            model_name: Ollama embedding model (default: nomic-embed-text)
            embedding_dim: Embedding dimension (nomic-embed-text: 768)
            cache_max_size: Maximum cache size (default: 10000)
        """
        self.model_name = model_name or "nomic-embed-text"
        self.embedding_dim = embedding_dim
        self.ollama_client = AsyncClient(host=settings.ollama_base_url)
        self.cache = LRUCache(max_size=cache_max_size)

        logger.info(
            "unified_embedding_service_initialized",
            model=self.model_name,
            embedding_dim=self.embedding_dim,
            cache_size=cache_max_size,
        )

    def _cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.sha256(text.encode()).hexdigest()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def embed_single(self, text: str) -> list[float]:
        """Embed single text with caching.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (768 dimensions for nomic-embed-text)
        """
        # Check cache
        cache_key = self._cache_key(text)
        cached = self.cache.get(cache_key)
        if cached:
            logger.debug("embedding_cache_hit", text_preview=text[:50])
            return cached

        # Generate embedding
        try:
            response = await self.ollama_client.embeddings(
                model=self.model_name,
                prompt=text,
            )
            embedding = response.get("embedding", [])

            if not embedding:
                raise LLMError(f"Empty embedding returned for text: {text[:100]}")

            # Cache result
            self.cache.set(cache_key, embedding)

            logger.debug(
                "embedding_generated",
                text_preview=text[:50],
                embedding_dim=len(embedding),
            )

            return embedding

        except Exception as e:
            logger.error("embedding_generation_failed", text_preview=text[:50], error=str(e))
            raise LLMError(f"Failed to generate embedding: {e}") from e

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed batch of texts with caching.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []

        for text in texts:
            embedding = await self.embed_single(text)
            embeddings.append(embedding)

        logger.info(
            "batch_embedding_complete",
            batch_size=len(texts),
            cache_hit_rate=self.cache.hit_rate(),
        )

        return embeddings

    def get_stats(self) -> dict[str, Any]:
        """Get embedding service statistics."""
        return {
            "model": self.model_name,
            "embedding_dim": self.embedding_dim,
            "cache": self.cache.stats(),
        }


# Global instance (singleton)
_embedding_service: UnifiedEmbeddingService | None = None


def get_embedding_service() -> UnifiedEmbeddingService:
    """Get global UnifiedEmbeddingService instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = UnifiedEmbeddingService()
    return _embedding_service
```

#### Migration Steps

**1. Update Qdrant Pipeline** (src/components/vector_search/embeddings.py)

```python
# REPLACE entire file with thin wrapper
from src.components.shared.embedding_service import get_embedding_service

class EmbeddingService:
    """Wrapper around UnifiedEmbeddingService for backward compatibility."""

    def __init__(self):
        self.unified_service = get_embedding_service()

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for texts (backward compatible)."""
        return await self.unified_service.embed_batch(texts)

    async def get_text_embedding(self, text: str) -> list[float]:
        """Get embedding for single text (backward compatible)."""
        return await self.unified_service.embed_single(text)
```

**2. Update LightRAG Wrapper** (src/components/graph_rag/lightrag_wrapper.py)

```python
# REPLACE OllamaEmbeddingFunc (lines 157-190)
from src.components.shared.embedding_service import get_embedding_service

class UnifiedEmbeddingFunc:
    """Wrapper for UnifiedEmbeddingService compatible with LightRAG."""

    def __init__(self, embedding_dim: int = 768):
        self.embedding_dim = embedding_dim
        self.unified_service = get_embedding_service()

    async def __call__(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        """Generate embeddings using shared service."""
        return await self.unified_service.embed_batch(texts)

    @property
    def async_func(self):
        """Return self to indicate this is an async function."""
        return self

# In _ensure_initialized():
embedding_func = UnifiedEmbeddingFunc(embedding_dim=768)
```

**3. Update Graphiti (if needed)**

```python
# src/components/temporal_memory/graphiti_wrapper.py
from src.components.shared.embedding_service import get_embedding_service

# Replace Graphiti's embedding function with unified service
```

#### Testing

**NEW FILE:** `tests/components/shared/test_embedding_service.py`

```python
"""Tests for unified embedding service."""

import pytest
from src.components.shared.embedding_service import UnifiedEmbeddingService


@pytest.mark.asyncio
async def test_embed_single():
    """Test single text embedding."""
    service = UnifiedEmbeddingService()
    embedding = await service.embed_single("AEGIS RAG")

    assert len(embedding) == 768  # nomic-embed-text dimension
    assert all(isinstance(x, float) for x in embedding)


@pytest.mark.asyncio
async def test_embed_batch():
    """Test batch embedding."""
    service = UnifiedEmbeddingService()
    texts = ["AEGIS RAG", "LangGraph", "Neo4j"]

    embeddings = await service.embed_batch(texts)

    assert len(embeddings) == 3
    assert all(len(emb) == 768 for emb in embeddings)


@pytest.mark.asyncio
async def test_caching():
    """Test embedding cache."""
    service = UnifiedEmbeddingService()

    # First call - cache miss
    emb1 = await service.embed_single("test")
    assert service.cache.stats()["misses"] == 1

    # Second call - cache hit
    emb2 = await service.embed_single("test")
    assert service.cache.stats()["hits"] == 1
    assert emb1 == emb2


@pytest.mark.asyncio
async def test_cache_sharing():
    """Test cache sharing across components."""
    service = UnifiedEmbeddingService()

    # Simulate Qdrant embedding
    qdrant_emb = await service.embed_single("LangGraph")

    # Simulate LightRAG embedding (same text as entity)
    lightrag_emb = await service.embed_single("LangGraph")

    # Should hit cache
    assert service.cache.stats()["hits"] >= 1
    assert qdrant_emb == lightrag_emb
```

#### Success Criteria

- ✅ UnifiedEmbeddingService implemented with shared cache
- ✅ Qdrant pipeline migrated to use shared service
- ✅ LightRAG migrated to use shared service
- ✅ Cache hit rate > 20% (cross-component sharing)
- ✅ All existing tests pass (backward compatibility)
- ✅ Ollama requests reduced by 30-50%

---

### Feature 11.3: Unified Ingestion Pipeline (3 SP) 🆕

**Priority:** 🔴 CRITICAL
**Dependencies:** Feature 11.2 (Shared Embedding Service)
**Rationale:** Original architecture hatte separate Pipelines → Unified Pipeline indexiert zu allen Systemen parallel

#### Current Problem

**Fragmented Ingestion:**

```python
# Current: DocumentIngestionPipeline (src/components/vector_search/ingestion.py)
class DocumentIngestionPipeline:
    """Only indexes to Qdrant + BM25."""
    async def index_documents(self, input_dir: str) -> dict:
        # 1. Load documents
        # 2. Chunk documents
        # 3. Generate embeddings
        # 4. Store in Qdrant
        # 5. Update BM25 index
        # ❌ NO Neo4j/Graph integration!
```

**Result:**
- ✅ Vector Search: Works (Qdrant + BM25)
- ❌ Graph Search: Empty (LightRAG not called)
- ❌ Hybrid Search: Falls back to vector-only

#### Solution Architecture

**NEW FILE:** `src/components/shared/unified_ingestion.py`

```python
"""Unified document ingestion pipeline for all AEGIS RAG components.

Indexes documents to:
- Qdrant (vector search)
- BM25 (keyword search)
- Neo4j (knowledge graph via LightRAG)
"""

import asyncio
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from src.components.vector_search.ingestion import DocumentIngestionPipeline
from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
from src.components.shared.embedding_service import get_embedding_service

logger = structlog.get_logger(__name__)


class IngestionResult(BaseModel):
    """Result of unified ingestion."""

    total_documents: int = Field(description="Total documents processed")
    qdrant_indexed: int = Field(description="Documents indexed to Qdrant")
    bm25_indexed: int = Field(description="Documents indexed to BM25")
    neo4j_entities: int = Field(description="Entities extracted to Neo4j")
    neo4j_relationships: int = Field(description="Relationships extracted to Neo4j")
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
    duration_seconds: float = Field(description="Total ingestion duration")


class UnifiedIngestionPipeline:
    """Single pipeline that indexes documents to all AEGIS RAG systems.

    Features:
    - Parallel indexing to Qdrant, BM25, and Neo4j
    - Shared embedding service (no duplicate embeddings)
    - Progress tracking for all systems
    - Error handling and partial success
    """

    def __init__(
        self,
        allowed_base_path: str | None = None,
        enable_qdrant: bool = True,
        enable_neo4j: bool = True,
    ):
        """Initialize unified ingestion pipeline.

        Args:
            allowed_base_path: Base path for file security validation
            enable_qdrant: Enable Qdrant/BM25 indexing (default: True)
            enable_neo4j: Enable Neo4j graph construction (default: True)
        """
        self.allowed_base_path = Path(allowed_base_path) if allowed_base_path else None
        self.enable_qdrant = enable_qdrant
        self.enable_neo4j = enable_neo4j

        # Component pipelines
        self.qdrant_pipeline = DocumentIngestionPipeline(
            allowed_base_path=str(self.allowed_base_path) if self.allowed_base_path else None
        )

        logger.info(
            "unified_ingestion_pipeline_initialized",
            qdrant_enabled=self.enable_qdrant,
            neo4j_enabled=self.enable_neo4j,
        )

    async def ingest_directory(
        self,
        input_dir: str,
        progress_callback: Any = None,
    ) -> IngestionResult:
        """Ingest all documents from directory to all systems.

        Args:
            input_dir: Directory path with documents
            progress_callback: Optional callback for progress updates

        Returns:
            IngestionResult with statistics
        """
        import time
        start_time = time.time()

        logger.info("unified_ingestion_start", input_dir=input_dir)

        errors = []

        # Phase 1: Parallel indexing
        tasks = []

        if self.enable_qdrant:
            tasks.append(self._index_to_qdrant(input_dir))

        if self.enable_neo4j:
            tasks.append(self._index_to_neo4j(input_dir))

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Parse results
        qdrant_result = {}
        neo4j_result = {}

        if self.enable_qdrant:
            qdrant_result = results[0] if not isinstance(results[0], Exception) else {}
            if isinstance(results[0], Exception):
                errors.append(f"Qdrant indexing failed: {results[0]}")

        if self.enable_neo4j:
            neo4j_idx = 1 if self.enable_qdrant else 0
            neo4j_result = results[neo4j_idx] if not isinstance(results[neo4j_idx], Exception) else {}
            if isinstance(results[neo4j_idx], Exception):
                errors.append(f"Neo4j indexing failed: {results[neo4j_idx]}")

        duration = time.time() - start_time

        result = IngestionResult(
            total_documents=qdrant_result.get("indexed_count", 0),
            qdrant_indexed=qdrant_result.get("indexed_count", 0),
            bm25_indexed=qdrant_result.get("indexed_count", 0),  # Same as Qdrant
            neo4j_entities=neo4j_result.get("entity_count", 0),
            neo4j_relationships=neo4j_result.get("relationship_count", 0),
            errors=errors,
            duration_seconds=duration,
        )

        logger.info(
            "unified_ingestion_complete",
            total_documents=result.total_documents,
            qdrant_indexed=result.qdrant_indexed,
            neo4j_entities=result.neo4j_entities,
            neo4j_relationships=result.neo4j_relationships,
            duration=duration,
            errors_count=len(errors),
        )

        return result

    async def _index_to_qdrant(self, input_dir: str) -> dict[str, Any]:
        """Index documents to Qdrant and BM25.

        Args:
            input_dir: Directory path

        Returns:
            Indexing statistics
        """
        logger.info("qdrant_indexing_start", input_dir=input_dir)

        try:
            # Use existing DocumentIngestionPipeline
            stats = await self.qdrant_pipeline.index_documents(input_dir=input_dir)

            logger.info(
                "qdrant_indexing_complete",
                indexed_count=stats.get("indexed_count", 0),
                chunks_created=stats.get("chunks_created", 0),
            )

            return stats

        except Exception as e:
            logger.error("qdrant_indexing_failed", error=str(e))
            raise

    async def _index_to_neo4j(self, input_dir: str) -> dict[str, Any]:
        """Index documents to Neo4j via LightRAG.

        Args:
            input_dir: Directory path

        Returns:
            Graph statistics (entity_count, relationship_count)
        """
        logger.info("neo4j_indexing_start", input_dir=input_dir)

        try:
            # Get LightRAG wrapper
            lightrag = await get_lightrag_wrapper_async()

            # Load documents
            from llama_index.core import SimpleDirectoryReader

            reader = SimpleDirectoryReader(
                input_dir=input_dir,
                recursive=True,
                required_exts=[".txt", ".md", ".pdf", ".docx"],
            )
            documents = reader.load_data()

            # Convert to LightRAG format
            lightrag_docs = [
                {
                    "text": doc.text,
                    "metadata": doc.metadata,
                }
                for doc in documents
            ]

            # Insert into LightRAG (builds graph)
            insert_result = await lightrag.insert_documents(lightrag_docs)

            # Get graph statistics
            stats = await lightrag.get_stats()

            logger.info(
                "neo4j_indexing_complete",
                documents=len(documents),
                entities=stats.get("entity_count", 0),
                relationships=stats.get("relationship_count", 0),
            )

            return stats

        except Exception as e:
            logger.error("neo4j_indexing_failed", error=str(e))
            raise


# Global instance (singleton)
_unified_pipeline: UnifiedIngestionPipeline | None = None


def get_unified_pipeline() -> UnifiedIngestionPipeline:
    """Get global UnifiedIngestionPipeline instance."""
    global _unified_pipeline
    if _unified_pipeline is None:
        _unified_pipeline = UnifiedIngestionPipeline()
    return _unified_pipeline
```

#### API Integration

**UPDATE:** `src/api/v1/retrieval.py` (Upload Endpoint)

```python
# REPLACE upload endpoint to use UnifiedIngestionPipeline

from src.components.shared.unified_ingestion import get_unified_pipeline, IngestionResult

@router.post(
    "/upload",
    response_model=IngestionResponse,
    summary="Upload documents for ingestion (Qdrant + BM25 + Neo4j)",
)
async def upload_documents(
    files: list[UploadFile] = File(...),
) -> IngestionResponse:
    """Upload documents and index to ALL systems (Qdrant, BM25, Neo4j).

    Changes in Sprint 11:
    - Now uses UnifiedIngestionPipeline
    - Indexes to Qdrant + BM25 + Neo4j in parallel
    - Returns statistics for all systems
    """
    # ... save files to temp directory ...

    # Use unified pipeline
    pipeline = get_unified_pipeline()
    result = await pipeline.ingest_directory(input_dir=temp_dir)

    return IngestionResponse(
        message="Documents uploaded and indexed to all systems",
        files_processed=len(files),
        indexed_count=result.qdrant_indexed,
        neo4j_entities=result.neo4j_entities,
        neo4j_relationships=result.neo4j_relationships,
        bm25_updated=True,
        errors=result.errors,
        duration_seconds=result.duration_seconds,
    )
```

#### Testing

**NEW FILE:** `tests/components/shared/test_unified_ingestion.py`

```python
"""Tests for unified ingestion pipeline."""

import pytest
from pathlib import Path
from src.components.shared.unified_ingestion import UnifiedIngestionPipeline


@pytest.mark.asyncio
async def test_unified_ingestion_e2e(tmp_path):
    """Test end-to-end unified ingestion."""
    # Create test documents
    doc_dir = tmp_path / "docs"
    doc_dir.mkdir()

    (doc_dir / "test1.txt").write_text("AEGIS RAG uses LangGraph for orchestration.")
    (doc_dir / "test2.txt").write_text("LangGraph provides state management.")

    # Ingest
    pipeline = UnifiedIngestionPipeline(allowed_base_path=str(tmp_path))
    result = await pipeline.ingest_directory(str(doc_dir))

    # Verify
    assert result.total_documents >= 2
    assert result.qdrant_indexed >= 2
    assert result.bm25_indexed >= 2
    # Neo4j entities depend on LightRAG extraction
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_parallel_indexing_performance(tmp_path):
    """Test that parallel indexing is faster than sequential."""
    import time

    doc_dir = tmp_path / "docs"
    doc_dir.mkdir()

    # Create 10 test documents
    for i in range(10):
        (doc_dir / f"test{i}.txt").write_text(f"Document {i} content.")

    # Measure unified pipeline (parallel)
    pipeline = UnifiedIngestionPipeline(allowed_base_path=str(tmp_path))
    start = time.time()
    result = await pipeline.ingest_directory(str(doc_dir))
    parallel_duration = time.time() - start

    # Parallel should complete (no assertion, just measurement)
    assert result.total_documents == 10
    assert parallel_duration < 60  # Should complete in < 1 minute
```

#### Success Criteria

- ✅ UnifiedIngestionPipeline indexes to Qdrant + BM25 + Neo4j
- ✅ Parallel execution (both systems indexed simultaneously)
- ✅ Upload API returns statistics for all systems
- ✅ Graph query works after upload (entities exist in Neo4j)
- ✅ Hybrid search (vector + graph) returns results
- ✅ Integration tests pass end-to-end

---

### Feature 11.4: Fix LightRAG Entity Extraction (2 SP)

**Technical Debt:** TD-14
**Priority:** 🟠 HIGH
**Dependencies:** Feature 11.2, 11.3
**Files:** `src/core/config.py`, `src/components/graph_rag/lightrag_wrapper.py`

#### Current Problem

LightRAG uses `qwen3:0.6b` which produces **malformed entity extraction output**.

**Root Cause Analysis (LIGHTRAG_ROOT_CAUSE_ANALYSIS.md):**
- ✅ Explicitly tested with debug script `debug_lightrag_vdb.py`
- ✅ VDB files inspected: `vdb_entities.json` was **empty**
- ✅ LLM outputs analyzed: qwen3:0.6b produces wrong format
- ✅ Parser warnings documented

**Example qwen3:0.6b Output:**
```
Entity: AEGIS, Type: System
Relationship: AEGIS uses LangGraph
# ❌ Wrong format! Should be JSON with specific fields
```

#### Solution

**REPLACE Model:** `qwen3:0.6b` → `llama3.2:3b`

**UPDATE:** `src/core/config.py`

```python
# OLD:
lightrag_llm_model: str = Field(
    default="qwen3:0.6b", description="Ollama LLM model for LightRAG"
)

# NEW:
lightrag_llm_model: str = Field(
    default="llama3.2:3b",
    description="Ollama LLM model for LightRAG entity extraction (requires good instruction following)"
)
```

**Rationale:**
- ✅ `llama3.2:3b` has better instruction following
- ✅ Produces correctly formatted JSON outputs
- ✅ Still fast enough (3B parameter model)
- ✅ Used successfully in other agents (RouterAgent, AnswerGenerator)

#### Testing

**1. Manual Verification:**

```bash
# Pull model
poetry run ollama pull llama3.2:3b

# Test entity extraction
poetry run python -c "
from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
import asyncio

async def test():
    lightrag = await get_lightrag_wrapper_async()
    result = await lightrag.insert_documents([
        {'text': 'AEGIS RAG uses LangGraph for multi-agent orchestration.'}
    ])
    print(result)

    stats = await lightrag.get_stats()
    print(f'Entities: {stats[\"entity_count\"]}')
    print(f'Relationships: {stats[\"relationship_count\"]}')

asyncio.run(test())
"
```

**Expected:**
- ✅ `entity_count > 0` (at least "AEGIS RAG", "LangGraph")
- ✅ `relationship_count > 0` (at least "AEGIS RAG uses LangGraph")

**2. Integration Test:**

```python
# tests/integration/test_lightrag_extraction.py

@pytest.mark.asyncio
async def test_lightrag_entity_extraction_with_llama32():
    """Test that llama3.2:3b correctly extracts entities."""
    lightrag = await get_lightrag_wrapper_async()

    # Insert test document
    result = await lightrag.insert_documents([
        {
            "text": "AEGIS RAG is a multi-agent system. "
                    "It uses LangGraph for orchestration and Neo4j for knowledge graphs."
        }
    ])

    assert result["success"] > 0

    # Check graph statistics
    stats = await lightrag.get_stats()

    # Should extract at least 3 entities
    assert stats["entity_count"] >= 3
    # Should extract at least 2 relationships
    assert stats["relationship_count"] >= 2
```

#### Success Criteria

- ✅ Config updated to use `llama3.2:3b`
- ✅ Entity extraction produces non-empty results
- ✅ Manual test shows entities in Neo4j
- ✅ Integration test passes with real extraction
- ✅ Graph query returns entities (not empty)

---

### Feature 11.5: Redis LangGraph Checkpointer (3 SP)

**Technical Debt:** TD-02
**Priority:** 🟠 HIGH
**Files:** `src/agents/checkpointer.py`

#### Current Problem

```python
# src/agents/checkpointer.py:146-165
def get_checkpointer():
    """Get LangGraph checkpointer based on configuration."""

    # Commented out since Sprint 7
    # if settings.use_redis_checkpointer and settings.redis_host:
    #     return get_redis_checkpointer()

    # Always uses MemorySaver (no persistence!)
    return MemorySaver()
```

**Impact:**
- ❌ No conversation persistence across restarts
- ❌ Redis infrastructure unused
- ❌ Session state lost on API restart

#### Solution

**UNCOMMENT and FIX:** `src/agents/checkpointer.py`

```python
from langgraph.checkpoint.redis import RedisSaver

def get_redis_checkpointer() -> RedisSaver:
    """Get Redis-based LangGraph checkpointer.

    Returns:
        RedisSaver instance configured for Redis backend
    """
    import redis.asyncio as redis

    # Create Redis connection pool
    redis_url = f"redis://{settings.redis_host}:{settings.redis_port}"
    if settings.redis_password:
        redis_url = f"redis://:{settings.redis_password.get_secret_value()}@{settings.redis_host}:{settings.redis_port}"

    client = redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=False,  # RedisSaver expects bytes
    )

    checkpointer = RedisSaver(client)

    logger.info(
        "redis_checkpointer_initialized",
        redis_host=settings.redis_host,
        redis_port=settings.redis_port,
    )

    return checkpointer


def get_checkpointer():
    """Get LangGraph checkpointer based on configuration."""

    if settings.use_redis_checkpointer and settings.redis_host:
        logger.info("using_redis_checkpointer")
        return get_redis_checkpointer()

    logger.warning("using_memory_checkpointer", reason="Redis not configured")
    return MemorySaver()
```

**UPDATE:** `src/core/config.py`

```python
# Enable Redis checkpointer by default
use_redis_checkpointer: bool = Field(
    default=True,  # Changed from False
    description="Use Redis for LangGraph checkpointing"
)
```

#### Testing

```python
# tests/agents/test_redis_checkpointer.py

@pytest.mark.asyncio
async def test_redis_checkpointer_persistence():
    """Test that conversation state persists in Redis."""
    from src.agents.checkpointer import get_checkpointer
    from src.agents.graph import create_graph

    checkpointer = get_checkpointer()
    graph = create_graph(checkpointer=checkpointer)

    # First conversation
    config = {"configurable": {"thread_id": "test-123"}}
    state1 = await graph.ainvoke(
        {"query": "What is AEGIS RAG?"},
        config=config,
    )

    # Second conversation (same thread)
    state2 = await graph.ainvoke(
        {"query": "Tell me more"},
        config=config,
    )

    # Should have conversation history
    assert len(state2["messages"]) > len(state1["messages"])
```

#### Success Criteria

- ✅ Redis checkpointer uncommented and working
- ✅ Conversation state persists across requests
- ✅ Session history retrievable by thread_id
- ✅ Redis keys visible in Redis CLI (`KEYS langgraph:*`)
- ✅ Integration test passes with real Redis

---

## Week 2: Performance + Testing

### Feature 11.6: E2E Test Fixes (3 SP)

**Technical Debt:** TD-07
**Priority:** 🟠 HIGH
**Dependencies:** Feature 11.3, 11.4
**Files:** `tests/integration/test_sprint5_critical_e2e.py`

#### Current Problem

```python
# tests/integration/test_sprint5_critical_e2e.py:199
@pytest.mark.asyncio
async def test_graph_query_e2e():
    """Test graph query returns structured results."""
    # ... setup ...

    result = await lightrag.query_graph(
        query="What is knowledge graph?",
        mode="local",
    )

    # ❌ FAILS: Empty answer (TD-14: qwen3:0.6b produces malformed output)
    assert result.answer
    assert len(result.answer) > 0
```

**Root Cause:**
- TD-14: LightRAG entity extraction broken → empty graph → empty answer
- Now fixed by Feature 11.4 (llama3.2:3b)

#### Solution

**After Feature 11.4 is complete:**
1. Re-run Sprint 5 E2E tests
2. Verify graph queries return non-empty results
3. Update test expectations if needed

**UPDATE:** `tests/integration/test_sprint5_critical_e2e.py`

```python
@pytest.mark.asyncio
async def test_graph_query_e2e():
    """Test graph query returns structured results.

    Sprint 11 Fix: Now uses llama3.2:3b for entity extraction.
    """
    # Setup LightRAG with test corpus
    lightrag = await get_lightrag_wrapper_async()

    # Insert test documents
    await lightrag.insert_documents([
        {"text": "A knowledge graph is a structured representation of entities and relationships."}
    ])

    # Query graph
    result = await lightrag.query_graph(
        query="What is a knowledge graph?",
        mode="local",
    )

    # Should have non-empty answer
    assert result.answer, "Graph query returned empty answer"
    assert len(result.answer) > 50, "Answer too short"
    assert "knowledge graph" in result.answer.lower()

    # Verify graph statistics
    stats = await lightrag.get_stats()
    assert stats["entity_count"] > 0, "No entities extracted"
    assert stats["relationship_count"] > 0, "No relationships extracted"
```

#### Success Criteria

- ✅ All Sprint 5 E2E tests pass
- ✅ Graph query tests return non-empty answers
- ✅ Entity extraction tests show entities in Neo4j
- ✅ CI pipeline green

---

### Feature 11.7: Community Detection Performance (3 SP)

**Technical Debt:** TD-09
**Priority:** 🟡 MEDIUM
**Files:** `src/components/graph_rag/community_detection.py`

#### Current Problem

```python
# src/components/graph_rag/community_detection.py:89
def detect_communities(self, graph: nx.Graph) -> list[set[str]]:
    """Detect communities using Leiden algorithm."""
    # Uses NetworkX → igraph → Leiden (slow for large graphs)
    ig_graph = self._nx_to_igraph(graph)
    communities = ig_graph.community_leiden()  # O(n log n) but high constant
```

**Performance Issue:**
- Graphs with 1000+ nodes: 5-10 seconds
- Blocks query execution (synchronous)

#### Solution

**1. Add Caching:**

```python
# Add to CommunityDetector
from functools import lru_cache

@lru_cache(maxsize=10)
def detect_communities_cached(self, graph_hash: str) -> list[set[str]]:
    """Detect communities with caching."""
    # ... existing implementation ...
```

**2. Make Async:**

```python
async def detect_communities_async(self, graph: nx.Graph) -> list[set[str]]:
    """Detect communities asynchronously."""
    import asyncio

    # Run in thread pool (CPU-bound operation)
    loop = asyncio.get_event_loop()
    communities = await loop.run_in_executor(
        None,  # Use default executor
        self._detect_communities_sync,
        graph,
    )
    return communities
```

#### Success Criteria

- ✅ Community detection < 2 seconds for 1000 nodes
- ✅ Cached results returned instantly
- ✅ Async execution doesn't block other operations

---

### Feature 11.8: Temporal Retention Policy (2 SP)

**Technical Debt:** TD-16
**Priority:** 🟡 MEDIUM
**Files:** `src/core/config.py`, `src/components/temporal_memory/graphiti_wrapper.py`

#### Solution

**ADD TO:** `src/core/config.py`

```python
# Temporal Memory Retention Policy
temporal_retention_days: int = Field(
    default=365,
    ge=0,
    description="Days to retain temporal versions (0 = infinite retention)"
)

temporal_auto_purge: bool = Field(
    default=True,
    description="Automatically purge old temporal versions on schedule"
)

temporal_purge_schedule: str = Field(
    default="0 2 * * *",  # 2 AM daily
    description="Cron schedule for temporal purge job"
)
```

**NEW FILE:** `src/components/temporal_memory/retention.py`

```python
"""Temporal memory retention policy management."""

import asyncio
from datetime import datetime, timedelta

import structlog
from src.core.config import settings
from src.components.temporal_memory.graphiti_wrapper import get_graphiti_wrapper

logger = structlog.get_logger(__name__)


async def purge_old_temporal_versions():
    """Purge temporal versions older than retention policy."""
    if settings.temporal_retention_days == 0:
        logger.info("temporal_purge_skipped", reason="infinite_retention")
        return

    cutoff_date = datetime.now() - timedelta(days=settings.temporal_retention_days)

    logger.info(
        "temporal_purge_start",
        cutoff_date=cutoff_date.isoformat(),
        retention_days=settings.temporal_retention_days,
    )

    graphiti = await get_graphiti_wrapper()

    # Query for old versions (Cypher query)
    purge_query = """
    MATCH (n)
    WHERE n.valid_until < $cutoff_timestamp
    DELETE n
    RETURN count(n) as deleted_count
    """

    # Execute purge
    # ... implementation ...

    logger.info("temporal_purge_complete", deleted_count=0)


# Background task scheduler
async def start_retention_scheduler():
    """Start background scheduler for temporal retention."""
    if not settings.temporal_auto_purge:
        logger.info("temporal_scheduler_disabled")
        return

    logger.info("temporal_scheduler_started", schedule=settings.temporal_purge_schedule)

    # Run daily at configured time
    while True:
        await purge_old_temporal_versions()
        await asyncio.sleep(86400)  # 24 hours
```

#### Success Criteria

- ✅ Retention policy configurable in config.py
- ✅ Auto-purge runs on schedule
- ✅ Old versions deleted from Neo4j
- ✅ Recent versions retained

---

### Feature 11.9: Enhanced Graph Visualization (3 SP)

**Technical Debt:** TD-17, TD-22
**Priority:** 🟡 MEDIUM
**Files:** Gradio UI

#### Solution

**ADD TO Gradio UI:**

1. **Real-time Graph Stats Panel:**
   - Entity count
   - Relationship count
   - Community count
   - Last updated timestamp

2. **Ingestion Progress Bar:**
   - Qdrant progress: X/Y documents
   - Neo4j progress: X entities, Y relationships
   - Overall: Z%

3. **Interactive Graph Viewer:**
   - Vis.js or D3.js visualization
   - Node: Entities
   - Edge: Relationships
   - Community coloring

#### Success Criteria

- ✅ Graph stats visible in UI
- ✅ Ingestion progress tracked
- ✅ Graph visualization interactive

---

### Feature 11.10: Sprint 10 Integration Tests (8 SP)

**Priority:** 🟠 HIGH
**Dependencies:** Feature 11.1 (LLM Answer Generation)

#### Test Coverage

**NEW FILE:** `tests/integration/test_sprint10_integration.py`

```python
"""Integration tests for Sprint 10 features."""

import pytest


class TestChatAPI:
    """Chat API integration tests."""

    @pytest.mark.asyncio
    async def test_chat_session_persistence(self, test_client):
        """Test that chat sessions persist in Redis."""
        # First message
        response1 = await test_client.post(
            "/api/v1/chat",
            json={"query": "What is AEGIS RAG?", "session_id": "test-123"},
        )
        assert response1.status_code == 200

        # Second message (same session)
        response2 = await test_client.post(
            "/api/v1/chat",
            json={"query": "Tell me more", "session_id": "test-123"},
        )
        assert response2.status_code == 200

        # Should reference previous context
        # (Actual test depends on LLM response)

    @pytest.mark.asyncio
    async def test_chat_source_citations(self, test_client):
        """Test that chat responses include source citations."""
        response = await test_client.post(
            "/api/v1/chat",
            json={"query": "What is LangGraph?", "include_sources": True},
        )

        data = response.json()
        assert "sources" in data
        assert len(data["sources"]) > 0

    @pytest.mark.asyncio
    async def test_chat_tool_calls_visibility(self, test_client):
        """Test that tool calls are returned when requested."""
        response = await test_client.post(
            "/api/v1/chat",
            json={"query": "What is AEGIS?", "include_tool_calls": True},
        )

        data = response.json()
        assert "tool_calls" in data
        # Should have at least one retrieval tool call
        assert len(data["tool_calls"]) > 0


class TestDocumentUpload:
    """Document upload integration tests."""

    @pytest.mark.asyncio
    async def test_single_file_upload(self, test_client, tmp_path):
        """Test single file upload."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test document content.")

        # Upload
        with open(test_file, "rb") as f:
            response = await test_client.post(
                "/api/v1/upload",
                files={"files": ("test.txt", f, "text/plain")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["indexed_count"] >= 1
        assert data["neo4j_entities"] >= 0  # May be 0 if no entities extracted

    @pytest.mark.asyncio
    async def test_multi_file_upload(self, test_client, tmp_path):
        """Test multi-file upload."""
        # Create test files
        files = []
        for i in range(5):
            f = tmp_path / f"test{i}.txt"
            f.write_text(f"Document {i} content.")
            files.append(f)

        # Upload
        file_objs = [
            ("files", (f.name, open(f, "rb"), "text/plain"))
            for f in files
        ]

        response = await test_client.post(
            "/api/v1/upload",
            files=file_objs,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["files_processed"] == 5
        assert data["indexed_count"] >= 5

    @pytest.mark.asyncio
    async def test_upload_then_query_flow(self, test_client, tmp_path):
        """Test that uploaded documents are immediately queryable."""
        # Upload
        test_file = tmp_path / "test.txt"
        test_file.write_text("AEGIS RAG is an advanced retrieval system.")

        with open(test_file, "rb") as f:
            upload_response = await test_client.post(
                "/api/v1/upload",
                files={"files": ("test.txt", f, "text/plain")},
            )

        assert upload_response.status_code == 200

        # Query
        query_response = await test_client.post(
            "/api/v1/chat",
            json={"query": "What is AEGIS RAG?"},
        )

        assert query_response.status_code == 200
        data = query_response.json()
        assert "AEGIS RAG" in data["answer"]


class TestBM25Persistence:
    """BM25 persistence integration tests."""

    @pytest.mark.asyncio
    async def test_bm25_saves_to_disk(self, test_client):
        """Test that BM25 index is saved to disk."""
        import os

        # Prepare BM25
        response = await test_client.post("/api/v1/bm25/prepare")
        assert response.status_code == 200

        # Check file exists
        cache_path = "data/cache/bm25_index.pkl"
        assert os.path.exists(cache_path)

    @pytest.mark.asyncio
    async def test_bm25_loads_from_disk(self, test_client, monkeypatch):
        """Test that BM25 index loads from disk on startup."""
        # Simulate restart by clearing in-memory index
        # ... implementation ...
        pass


class TestMCPIntegration:
    """MCP integration tests."""

    @pytest.mark.asyncio
    async def test_mcp_server_connection(self, test_client):
        """Test MCP server connection."""
        response = await test_client.get("/api/v1/mcp/servers")
        assert response.status_code == 200
        data = response.json()
        assert "servers" in data

    @pytest.mark.asyncio
    async def test_mcp_tool_discovery(self, test_client):
        """Test MCP tool discovery."""
        response = await test_client.get("/api/v1/mcp/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data


class TestMarkdownRendering:
    """Markdown rendering tests."""

    @pytest.mark.asyncio
    async def test_markdown_formatting_in_response(self, test_client):
        """Test that markdown is properly formatted in responses."""
        response = await test_client.post(
            "/api/v1/chat",
            json={"query": "Explain LangGraph in bullet points"},
        )

        data = response.json()
        answer = data["answer"]

        # Check for markdown formatting
        # (Actual check depends on LLM response)
        # Should have proper line breaks, not literal \n\n
        assert "\\n\\n" not in answer  # Should be actual line breaks
```

#### Success Criteria

- ✅ 25+ integration tests for Sprint 10 features
- ✅ All tests passing
- ✅ Coverage > 80% for Sprint 10 code
- ✅ CI pipeline green

---

## Sprint 11 Execution Plan

### Week 1 (Day 1-5)

**Day 1: LLM Answer Generation**
- Feature 11.1: Implement AnswerGenerator (5 SP)
- Git: `feat(agents): add LLM-based answer generation`

**Day 2: Shared Embedding Service**
- Feature 11.2: Implement UnifiedEmbeddingService (2 SP)
- Migrate Qdrant + LightRAG to use shared service
- Git: `feat(shared): add unified embedding service with shared cache`

**Day 3: Unified Ingestion Pipeline**
- Feature 11.3: Implement UnifiedIngestionPipeline (3 SP)
- Update upload API endpoint
- Git: `feat(ingestion): add unified pipeline for Qdrant + Neo4j`

**Day 4: Fix LightRAG**
- Feature 11.4: Switch to llama3.2:3b (2 SP)
- Verify entity extraction works
- Git: `fix(lightrag): switch to llama3.2:3b for entity extraction`

**Day 5: Redis Checkpointer**
- Feature 11.5: Uncomment and fix Redis checkpointer (3 SP)
- Git: `feat(agents): enable Redis LangGraph checkpointer`

### Week 2 (Day 6-10)

**Day 6: E2E Test Fixes**
- Feature 11.6: Fix Sprint 5 E2E tests (3 SP)
- Git: `test(integration): fix Sprint 5 E2E tests after LightRAG fix`

**Day 7: Performance Improvements**
- Feature 11.7: Community detection optimization (3 SP)
- Git: `perf(graph): optimize community detection with caching`

**Day 8: Retention Policy**
- Feature 11.8: Temporal retention policy (2 SP)
- Git: `feat(temporal): add retention policy for temporal memory`

**Day 9: Graph Visualization**
- Feature 11.9: Enhanced graph viz (3 SP)
- Git: `feat(ui): add graph stats and visualization`

**Day 10: Integration Tests**
- Feature 11.10: Sprint 10 integration tests (8 SP)
- Git: `test(integration): add comprehensive Sprint 10 tests`

---

## Success Metrics

### Technical Metrics

- ✅ **Test Coverage:** >85% (up from 80%)
- ✅ **E2E Tests Passing:** 100% (currently 7/9 = 78%)
- ✅ **Ollama Requests:** -30% (shared embedding service)
- ✅ **Upload Performance:** Parallel indexing saves 40% time
- ✅ **Graph Queries:** Non-empty answers (TD-14 fixed)

### User Experience Metrics

- ✅ **Answer Quality:** LLM-generated (not just context dump)
- ✅ **Conversation Persistence:** Sessions survive restarts
- ✅ **Graph Search:** Works after upload (entities in Neo4j)
- ✅ **Hybrid Search:** Vector + Graph fusion working

### Architecture Quality

- ✅ **Code Duplication:** -2 embedding services (unified)
- ✅ **Pipeline Integration:** Single upload → all systems
- ✅ **Technical Debt:** 10 items resolved (TD-01, 02, 03, 04, 07, 09, 14, 15, 16, 17)

---

## Dependencies

### External Dependencies

- **Ollama Models:**
  - `llama3.2:3b` (LightRAG entity extraction)
  - `llama3.2:8b` (answer generation)
  - `nomic-embed-text` (unified embeddings)

### Infrastructure

- **Redis:** Required for LangGraph checkpointer
- **Neo4j:** Required for LightRAG graph storage
- **Qdrant:** Vector search

### Python Packages

No new dependencies required (all existing).

---

## Risk Mitigation

### High Risk Items

1. **LightRAG Entity Extraction Fix (TD-14)**
   - **Risk:** llama3.2:3b might still produce malformed output
   - **Mitigation:** Test with debug script before integration
   - **Fallback:** Try qwen2.5:3b if llama3.2 fails

2. **Unified Pipeline Performance**
   - **Risk:** Parallel indexing might timeout on large uploads
   - **Mitigation:** Add progress tracking + timeout config
   - **Fallback:** Add option to disable Neo4j indexing

### Medium Risk Items

1. **Redis Checkpointer Compatibility**
   - **Risk:** LangGraph version mismatch
   - **Mitigation:** Test with existing Redis infrastructure
   - **Fallback:** Keep MemorySaver option

---

## Documentation Updates

### Files to Update

1. **README.md:**
   - Document unified ingestion pipeline
   - Update architecture diagram

2. **docs/core/ARCHITECTURE.md:** (create if not exists)
   - Document UnifiedEmbeddingService design
   - Document UnifiedIngestionPipeline flow

3. **docs/examples/sprint11_examples.md:**
   - LLM answer generation example
   - Unified upload example with all systems

4. **CHANGELOG.md:**
   - Sprint 11 changes

---

## Definition of Done

### Feature-Level DoD

- ✅ Implementation complete
- ✅ Unit tests passing (>80% coverage)
- ✅ Integration tests passing
- ✅ Documentation updated
- ✅ Git commit with conventional commit message
- ✅ Code review passed (self-review)

### Sprint-Level DoD

- ✅ All 10 features complete
- ✅ 34 SP delivered
- ✅ All tests passing (unit + integration + E2E)
- ✅ Sprint completion report created
- ✅ Merged to main via PR
- ✅ No regressions in existing features

---

## Next Steps After Sprint 11

### Sprint 12 Candidates

1. **Frontend Improvements:**
   - React/Vue UI (replace Gradio)
   - Advanced graph visualization

2. **Production Readiness:**
   - Kubernetes deployment
   - Monitoring + Alerting
   - Load testing

3. **Advanced Features:**
   - Multi-modal RAG (images, tables)
   - Agentic Tool Integration
   - Custom LLM fine-tuning

---

**Sprint 11 Plan Complete** ✅

Total: **34 Story Points**, **10 Features**, **2 Weeks**
