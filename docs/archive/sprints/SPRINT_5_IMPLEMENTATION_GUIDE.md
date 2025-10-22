# Sprint 5 Implementation Guide - LightRAG Integration

**Version:** 1.0
**Last Updated:** 2025-10-16
**Sprint:** Sprint 5 - Graph Retrieval with LightRAG + Neo4j

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Feature 5.1: LightRAG Core Integration](#feature-51-lightrag-core-integration)
4. [Feature 5.2: Neo4j Backend Configuration](#feature-52-neo4j-backend-configuration)
5. [Feature 5.3: Entity & Relationship Extraction](#feature-53-entity--relationship-extraction)
6. [Feature 5.4: Dual-Level Retrieval](#feature-54-dual-level-retrieval)
7. [Feature 5.5: Graph Query Agent](#feature-55-graph-query-agent)
8. [Feature 5.6: Incremental Graph Updates](#feature-56-incremental-graph-updates)
9. [Testing Strategy](#testing-strategy)
10. [Common Pitfalls & Solutions](#common-pitfalls--solutions)
11. [Performance Optimization](#performance-optimization)
12. [Monitoring & Debugging](#monitoring--debugging)

---

## Overview

This guide provides step-by-step instructions for implementing Sprint 5: LightRAG Integration for graph-based knowledge retrieval. By the end of this sprint, AEGIS RAG will support:

- Knowledge graph construction from documents
- Entity and relationship extraction using LLM
- Dual-level retrieval (entity-level + topic-level)
- GRAPH intent routing via LangGraph
- Incremental graph updates

### Sprint 5 Architecture

```
User Query → Router → GRAPH Intent → Graph Query Agent → LightRAG → Neo4j
                                                            ↓
                                                       Entities +
                                                      Relationships
                                                            ↓
                                                    LLM-Generated
                                                        Answer
```

### Implementation Order

Follow this order to minimize dependency issues:

1. **Feature 5.2:** Neo4j Backend (infrastructure first)
2. **Feature 5.1:** LightRAG Core (requires Neo4j)
3. **Feature 5.3:** Entity Extraction (requires LightRAG)
4. **Feature 5.4:** Dual-Level Search (requires extraction)
5. **Feature 5.5:** Graph Query Agent (requires search + Sprint 4)
6. **Feature 5.6:** Incremental Updates (optional, requires all above)

---

## Prerequisites

### System Requirements

**Software:**
- Python 3.11+
- Docker & Docker Compose
- Git
- Ollama server (running)

**Disk Space:**
- Neo4j data: ~5GB (for 1000 documents)
- Ollama models: ~5GB (llama3.2:8b + nomic-embed-text)
- Total: ~15GB free disk space

**Memory:**
- Development: 8GB RAM minimum
- Production: 16GB RAM recommended

### Sprint 4 Completion Check

Verify Sprint 4 is complete:

```bash
# Check if router supports GRAPH intent
cd "c:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag"
python -c "from src.agents.router import QueryIntent; print(QueryIntent.GRAPH)"
# Should print: QueryIntent.GRAPH

# Check if base agent exists
python -c "from src.agents.base_agent import BaseAgent; print('BaseAgent available')"
# Should print: BaseAgent available
```

### Ollama Models

Ensure required models are available:

```bash
# Check models
ollama list

# Pull models if missing
ollama pull llama3.2:8b
ollama pull nomic-embed-text

# Verify
ollama run llama3.2:8b "Test" --verbose
```

### Python Environment

Install base dependencies:

```bash
# Activate Poetry environment
poetry shell

# Verify existing dependencies
poetry show | grep -E "neo4j|ollama|langgraph"

# Should see:
# - neo4j 5.14.0
# - ollama 0.3.x
# - langgraph 0.6.10+
```

---

## Feature 5.1: LightRAG Core Integration

**Goal:** Integrate LightRAG library with Ollama LLM and Neo4j backend.

**Estimated Time:** 1.5 days

### Step 1.1: Install LightRAG Package

```bash
# Install LightRAG and dependencies
poetry add lightrag-hku
poetry add networkx
poetry add graspologic

# Verify installation
python -c "import lightrag; print(lightrag.__version__)"
# Should print version (e.g., 0.2.0)
```

**Dependency Notes:**
- `lightrag-hku`: Official LightRAG package from HKU research
- `networkx`: Graph algorithms (LightRAG uses for in-memory graphs)
- `graspologic`: Community detection (Leiden algorithm)

### Step 1.2: Create Directory Structure

```bash
# Create directories
mkdir -p src/components/graph_rag
mkdir -p tests/components/graph_rag
mkdir -p data/lightrag

# Create __init__ files
touch src/components/graph_rag/__init__.py
touch tests/components/graph_rag/__init__.py
```

### Step 1.3: Add Configuration Settings

Update `src/core/config.py`:

```python
# src/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # ... existing settings ...

    # ========================================================================
    # LightRAG Settings (Sprint 5: Graph RAG)
    # ========================================================================
    lightrag_enabled: bool = Field(
        default=True,
        description="Enable LightRAG graph retrieval"
    )
    lightrag_working_dir: str = Field(
        default="./data/lightrag",
        description="LightRAG working directory for graph storage"
    )

    # LightRAG LLM Configuration
    lightrag_llm_model: str = Field(
        default="llama3.2:8b",
        description="Ollama model for entity/relationship extraction"
    )
    lightrag_llm_temperature: float = Field(
        default=0.1,
        description="LLM temperature for extraction (low for consistency)"
    )
    lightrag_llm_max_tokens: int = Field(
        default=4096,
        description="Max tokens for LLM response"
    )

    # LightRAG Embedding Configuration
    lightrag_embedding_model: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model"
    )
    lightrag_embedding_dim: int = Field(
        default=768,
        description="Embedding dimension (nomic-embed-text=768)"
    )

    # Graph Construction Settings
    lightrag_entity_extraction_batch_size: int = Field(
        default=5,
        description="Batch size for entity extraction"
    )
    lightrag_max_tokens_per_chunk: int = Field(
        default=1200,
        description="Max tokens per chunk for extraction"
    )

    # Neo4j Backend (Sprint 5: Graph Storage)
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j Bolt URI"
    )
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4j username"
    )
    neo4j_password: str = Field(
        default="your-password-here",
        description="Neo4j password"
    )
    neo4j_database: str = Field(
        default="neo4j",
        description="Neo4j database name"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Singleton instance
settings = Settings()
```

### Step 1.4: Create Pydantic Models

Create `src/components/graph_rag/models.py`:

```python
"""Pydantic models for graph retrieval components.

Sprint 5: LightRAG Integration
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GraphQueryMode(str, Enum):
    """LightRAG query modes for dual-level retrieval."""

    LOCAL = "local"      # Entity-level: specific entities and relationships
    GLOBAL = "global"    # Topic-level: high-level summaries, communities
    HYBRID = "hybrid"    # Combined: local + global results fused


class GraphNode(BaseModel):
    """Graph node (entity) representation."""

    id: str = Field(..., description="Unique node ID")
    label: str = Field(..., description="Node label/type (Person, Organization, etc.)")
    name: str = Field(..., description="Entity name")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Node properties (description, aliases, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "entity_1",
                "label": "Person",
                "name": "John Smith",
                "properties": {
                    "description": "Software engineer at Google",
                    "aliases": ["J. Smith", "Johnny"],
                }
            }
        }


class GraphRelationship(BaseModel):
    """Graph relationship (edge) representation."""

    id: str = Field(..., description="Unique relationship ID")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Relationship type (WORKS_AT, KNOWS, etc.)")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Relationship properties (description, confidence, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "rel_1",
                "source": "entity_1",
                "target": "entity_2",
                "type": "WORKS_AT",
                "properties": {
                    "description": "John Smith works at Google",
                    "since": "2020-01-01",
                }
            }
        }


class GraphQueryResult(BaseModel):
    """Graph query result with LLM-generated answer."""

    query: str = Field(..., description="Original query")
    mode: GraphQueryMode = Field(..., description="Query mode used (local/global/hybrid)")
    answer: str = Field(..., description="LLM-generated answer from graph context")
    entities: list[GraphNode] = Field(
        default_factory=list,
        description="Retrieved entities (nodes)"
    )
    relationships: list[GraphRelationship] = Field(
        default_factory=list,
        description="Retrieved relationships (edges)"
    )
    context: str = Field(
        default="",
        description="Graph context used for answer generation"
    )
    topics: list[str] = Field(
        default_factory=list,
        description="Topics/communities (global search only)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Query metadata (execution_time, entity_count, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What companies has John Smith worked for?",
                "mode": "local",
                "answer": "John Smith has worked for Google (2020-present) and Microsoft (2015-2020).",
                "entities": [
                    {"id": "e1", "label": "Person", "name": "John Smith", "properties": {}},
                    {"id": "e2", "label": "Organization", "name": "Google", "properties": {}},
                ],
                "relationships": [
                    {
                        "id": "r1",
                        "source": "e1",
                        "target": "e2",
                        "type": "WORKS_AT",
                        "properties": {},
                    }
                ],
                "context": "John Smith-WORKS_AT->Google...",
                "topics": [],
                "metadata": {"execution_time_ms": 250, "entities_found": 2},
            }
        }
```

### Step 1.5: Implement LightRAG Wrapper

Create `src/components/graph_rag/lightrag_wrapper.py`:

```python
"""LightRAG wrapper for graph-based knowledge retrieval.

This module wraps the LightRAG library to provide:
- Ollama LLM integration
- Neo4j backend storage
- Async support
- Error handling and retry logic

Sprint 5: Feature 5.1 - LightRAG Core Integration
"""

import asyncio
from pathlib import Path
from typing import Any

import structlog
from lightrag import LightRAG
from lightrag.llm import openai_complete_if_cache, openai_embedding
from lightrag.storage import Neo4jStorage
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import settings
from src.components.graph_rag.models import (
    GraphNode,
    GraphQueryMode,
    GraphQueryResult,
    GraphRelationship,
)

logger = structlog.get_logger(__name__)


class LightRAGWrapper:
    """Async wrapper for LightRAG with Ollama and Neo4j backend.

    Provides:
    - Document ingestion and graph construction
    - Dual-level retrieval (local/global/hybrid)
    - Entity and relationship extraction
    - Integration with existing AEGIS RAG components
    """

    def __init__(
        self,
        working_dir: str | None = None,
        llm_model: str | None = None,
        embedding_model: str | None = None,
        neo4j_uri: str | None = None,
        neo4j_user: str | None = None,
        neo4j_password: str | None = None,
    ):
        """Initialize LightRAG wrapper.

        Args:
            working_dir: Working directory for LightRAG
            llm_model: Ollama LLM model name
            embedding_model: Ollama embedding model name
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        # Configuration
        self.working_dir = Path(working_dir or settings.lightrag_working_dir)
        self.llm_model = llm_model or settings.lightrag_llm_model
        self.embedding_model = embedding_model or settings.lightrag_embedding_model
        self.neo4j_uri = neo4j_uri or settings.neo4j_uri
        self.neo4j_user = neo4j_user or settings.neo4j_user
        self.neo4j_password = neo4j_password or settings.neo4j_password

        # Create working directory
        self.working_dir.mkdir(parents=True, exist_ok=True)

        # Initialize LightRAG with Ollama LLM functions
        self.rag = self._initialize_lightrag()

        logger.info(
            "lightrag_wrapper_initialized",
            working_dir=str(self.working_dir),
            llm_model=self.llm_model,
            embedding_model=self.embedding_model,
            neo4j_uri=self.neo4j_uri,
        )

    def _initialize_lightrag(self) -> LightRAG:
        """Initialize LightRAG with Ollama and Neo4j backend."""
        # Configure Ollama LLM function
        async def ollama_llm_complete(
            prompt: str,
            model: str = self.llm_model,
            **kwargs,
        ) -> str:
            """Ollama LLM completion function for LightRAG."""
            from ollama import AsyncClient

            client = AsyncClient(host=settings.ollama_base_url)

            response = await client.generate(
                model=model,
                prompt=prompt,
                options={
                    "temperature": settings.lightrag_llm_temperature,
                    "num_predict": settings.lightrag_llm_max_tokens,
                },
            )

            return response.get("response", "")

        # Configure Ollama embedding function
        async def ollama_embedding_func(
            texts: list[str],
            model: str = self.embedding_model,
            **kwargs,
        ) -> list[list[float]]:
            """Ollama embedding function for LightRAG."""
            from ollama import AsyncClient

            client = AsyncClient(host=settings.ollama_base_url)

            embeddings = []
            for text in texts:
                response = await client.embeddings(
                    model=model,
                    prompt=text,
                )
                embeddings.append(response.get("embedding", []))

            return embeddings

        # Initialize Neo4j storage
        neo4j_storage = Neo4jStorage(
            uri=self.neo4j_uri,
            user=self.neo4j_user,
            password=self.neo4j_password,
        )

        # Initialize LightRAG
        rag = LightRAG(
            working_dir=str(self.working_dir),
            llm_model_func=ollama_llm_complete,
            embedding_func=ollama_embedding_func,
            graph_storage=neo4j_storage,
        )

        return rag

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def insert_text(self, text: str) -> dict[str, Any]:
        """Insert text document into knowledge graph.

        Args:
            text: Document text to process

        Returns:
            Insertion result metadata

        Raises:
            Exception: If insertion fails after retries
        """
        logger.info("lightrag_insert_text", text_length=len(text))

        try:
            # Insert text into LightRAG
            # LightRAG automatically:
            # 1. Extracts entities and relationships using LLM
            # 2. Builds knowledge graph in Neo4j
            # 3. Creates embeddings for entities
            result = await self.rag.ainsert(text)

            logger.info("lightrag_insert_complete", result=result)

            return {"status": "success", "result": result}

        except Exception as e:
            logger.error("lightrag_insert_failed", error=str(e), text_length=len(text))
            raise

    async def insert_documents(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        """Insert multiple documents into knowledge graph.

        Args:
            documents: List of documents with 'text' and optional 'metadata' fields

        Returns:
            Batch insertion result
        """
        logger.info("lightrag_insert_documents", count=len(documents))

        results = []
        for i, doc in enumerate(documents):
            try:
                result = await self.insert_text(doc["text"])
                results.append({"index": i, "status": "success", "result": result})
            except Exception as e:
                logger.error(
                    "lightrag_insert_document_failed",
                    index=i,
                    error=str(e),
                )
                results.append({"index": i, "status": "error", "error": str(e)})

        success_count = sum(1 for r in results if r["status"] == "success")
        logger.info(
            "lightrag_insert_documents_complete",
            total=len(documents),
            success=success_count,
            failed=len(documents) - success_count,
        )

        return {
            "total": len(documents),
            "success": success_count,
            "failed": len(documents) - success_count,
            "results": results,
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def query(
        self,
        query: str,
        mode: str | GraphQueryMode = GraphQueryMode.HYBRID,
        top_k: int = 10,
    ) -> GraphQueryResult:
        """Query knowledge graph with dual-level retrieval.

        Args:
            query: User query string
            mode: Search mode (local/global/hybrid)
            top_k: Number of results to retrieve

        Returns:
            GraphQueryResult with answer and retrieved entities/relationships
        """
        # Convert enum to string if needed
        if isinstance(mode, GraphQueryMode):
            mode = mode.value

        logger.info("lightrag_query", query=query[:100], mode=mode, top_k=top_k)

        try:
            # Query LightRAG
            # - local: Entity-level retrieval (specific entities and relationships)
            # - global: Topic-level retrieval (high-level summaries, communities)
            # - hybrid: Combined local + global
            answer = await self.rag.aquery(
                query=query,
                param={"mode": mode, "top_k": top_k},
            )

            # LightRAG returns a string answer
            # We need to parse/structure it for our response
            result = GraphQueryResult(
                query=query,
                mode=GraphQueryMode(mode),
                answer=answer,
                entities=[],  # TODO: Extract from LightRAG internal state
                relationships=[],  # TODO: Extract from LightRAG internal state
                context="",  # TODO: Get context used for generation
                topics=[],
                metadata={
                    "mode": mode,
                    "top_k": top_k,
                },
            )

            logger.info(
                "lightrag_query_complete",
                query=query[:100],
                mode=mode,
                answer_length=len(answer),
            )

            return result

        except Exception as e:
            logger.error("lightrag_query_failed", query=query[:100], mode=mode, error=str(e))
            raise

    async def get_entity_count(self) -> int:
        """Get total number of entities in graph.

        Returns:
            Entity count
        """
        # Query Neo4j directly for entity count
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password),
        )

        async with driver.session() as session:
            result = await session.run("MATCH (e:Entity) RETURN count(e) AS count")
            record = await result.single()
            count = record["count"] if record else 0

        await driver.close()

        logger.info("lightrag_entity_count", count=count)
        return count

    async def health_check(self) -> bool:
        """Check health of LightRAG and Neo4j connection.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Test Neo4j connection
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
            )

            async with driver.session() as session:
                result = await session.run("RETURN 1 AS health")
                record = await result.single()
                healthy = record["health"] == 1

            await driver.close()

            logger.info("lightrag_health_check", healthy=healthy)
            return healthy

        except Exception as e:
            logger.error("lightrag_health_check_failed", error=str(e))
            return False


# Global instance (singleton pattern)
_lightrag_wrapper: LightRAGWrapper | None = None


def get_lightrag_wrapper() -> LightRAGWrapper:
    """Get global LightRAG wrapper instance (singleton).

    Returns:
        LightRAGWrapper instance
    """
    global _lightrag_wrapper
    if _lightrag_wrapper is None:
        _lightrag_wrapper = LightRAGWrapper()
    return _lightrag_wrapper
```

### Step 1.6: Write Unit Tests

Create `tests/components/graph_rag/test_lightrag_wrapper.py`:

```python
"""Unit tests for LightRAG wrapper.

Sprint 5: Feature 5.1
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper, get_lightrag_wrapper
from src.components.graph_rag.models import GraphQueryMode


class TestLightRAGWrapper:
    """Test LightRAG wrapper initialization and core methods."""

    @pytest.fixture
    def mock_lightrag(self):
        """Mock LightRAG instance."""
        with patch("src.components.graph_rag.lightrag_wrapper.LightRAG") as mock:
            mock_instance = MagicMock()
            mock_instance.ainsert = AsyncMock(return_value={"status": "success"})
            mock_instance.aquery = AsyncMock(return_value="Mock answer")
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def wrapper(self, mock_lightrag):
        """LightRAG wrapper instance with mocked dependencies."""
        with patch(
            "src.components.graph_rag.lightrag_wrapper.Neo4jStorage"
        ) as mock_storage:
            mock_storage.return_value = MagicMock()
            wrapper = LightRAGWrapper(
                working_dir="./data/test_lightrag",
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="test",
            )
            wrapper.rag = mock_lightrag
            yield wrapper

    def test_initialization(self, wrapper):
        """Test LightRAG wrapper initializes correctly."""
        assert wrapper is not None
        assert wrapper.llm_model == "llama3.2:8b"
        assert wrapper.embedding_model == "nomic-embed-text"
        assert wrapper.working_dir.name == "test_lightrag"

    @pytest.mark.asyncio
    async def test_insert_text(self, wrapper, mock_lightrag):
        """Test text insertion."""
        text = "Test document about machine learning."

        result = await wrapper.insert_text(text)

        assert result["status"] == "success"
        mock_lightrag.ainsert.assert_called_once_with(text)

    @pytest.mark.asyncio
    async def test_insert_documents(self, wrapper):
        """Test batch document insertion."""
        documents = [
            {"text": "Document 1"},
            {"text": "Document 2"},
        ]

        result = await wrapper.insert_documents(documents)

        assert result["total"] == 2
        assert result["success"] == 2
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_query_local_mode(self, wrapper, mock_lightrag):
        """Test local (entity-level) query."""
        query = "What companies does John work for?"

        result = await wrapper.query(query, mode=GraphQueryMode.LOCAL)

        assert result.query == query
        assert result.mode == GraphQueryMode.LOCAL
        assert result.answer == "Mock answer"
        mock_lightrag.aquery.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_global_mode(self, wrapper, mock_lightrag):
        """Test global (topic-level) query."""
        query = "What are the main themes?"

        result = await wrapper.query(query, mode=GraphQueryMode.GLOBAL)

        assert result.mode == GraphQueryMode.GLOBAL
        assert result.answer == "Mock answer"

    @pytest.mark.asyncio
    async def test_query_hybrid_mode(self, wrapper, mock_lightrag):
        """Test hybrid query."""
        query = "Complex query needing both local and global."

        result = await wrapper.query(query, mode=GraphQueryMode.HYBRID)

        assert result.mode == GraphQueryMode.HYBRID

    @pytest.mark.asyncio
    async def test_health_check(self, wrapper):
        """Test health check."""
        with patch("src.components.graph_rag.lightrag_wrapper.AsyncGraphDatabase") as mock_db:
            mock_driver = MagicMock()
            mock_session = MagicMock()
            mock_result = AsyncMock()
            mock_record = {"health": 1}

            mock_result.single = AsyncMock(return_value=mock_record)
            mock_session.run = AsyncMock(return_value=mock_result)
            mock_driver.session = MagicMock(return_value=mock_session)
            mock_driver.close = AsyncMock()
            mock_db.driver = MagicMock(return_value=mock_driver)

            # Need to handle async context manager
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            healthy = await wrapper.health_check()

            assert healthy is True

    def test_singleton_pattern(self):
        """Test singleton pattern for global instance."""
        instance1 = get_lightrag_wrapper()
        instance2 = get_lightrag_wrapper()

        assert instance1 is instance2
```

### Step 1.7: Manual Testing

Test LightRAG wrapper manually:

```python
# scripts/test_lightrag_wrapper.py
"""Manual test script for LightRAG wrapper."""

import asyncio
from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper

async def main():
    # Initialize wrapper
    wrapper = LightRAGWrapper()

    # Test health check
    print("Testing health check...")
    healthy = await wrapper.health_check()
    print(f"Health check: {healthy}")

    # Test document insertion
    print("\nInserting test document...")
    text = """
    John Smith is a software engineer at Google. He previously worked at Microsoft.
    John lives in San Francisco and specializes in machine learning.
    """

    result = await wrapper.insert_text(text)
    print(f"Insert result: {result}")

    # Test query (local mode)
    print("\nQuerying graph (local mode)...")
    query_result = await wrapper.query(
        "What companies has John Smith worked for?",
        mode="local"
    )
    print(f"Answer: {query_result.answer}")

    # Check entity count
    print("\nChecking entity count...")
    count = await wrapper.get_entity_count()
    print(f"Entity count: {count}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run the test:

```bash
python scripts/test_lightrag_wrapper.py
```

---

## Feature 5.2: Neo4j Backend Configuration

**Goal:** Set up Neo4j as graph storage backend with Docker Compose.

**Estimated Time:** 1 day

### Step 2.1: Update Docker Compose

Edit `docker-compose.yml`:

```yaml
# docker-compose.yml (add Neo4j service)
version: "3.8"

services:
  # ... existing services (qdrant, redis, etc.) ...

  neo4j:
    image: neo4j:5.14-community
    container_name: aegis-neo4j
    ports:
      - "7474:7474"  # HTTP browser UI
      - "7687:7687"  # Bolt protocol
    environment:
      # Authentication (change password in production!)
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-your-password-here}

      # Plugins (optional but recommended)
      - NEO4J_PLUGINS=["apoc"]  # APOC procedures for graph algorithms

      # Memory configuration
      - NEO4J_server_memory_heap_initial__size=512m
      - NEO4J_server_memory_heap_max__size=2g
      - NEO4J_server_memory_pagecache_size=1g

      # Performance tuning
      - NEO4J_dbms_memory_transaction_total_max=512m

    volumes:
      # Persistent storage
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_import:/var/lib/neo4j/import
      - neo4j_plugins:/plugins

    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "${NEO4J_PASSWORD:-your-password-here}", "RETURN 1"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

    networks:
      - aegis-network

    restart: unless-stopped

volumes:
  # ... existing volumes ...
  neo4j_data:
    driver: local
  neo4j_logs:
    driver: local
  neo4j_import:
    driver: local
  neo4j_plugins:
    driver: local

networks:
  aegis-network:
    driver: bridge
```

### Step 2.2: Create Environment Variables

Update `.env`:

```bash
# .env (add Neo4j configuration)

# Neo4j Configuration (Sprint 5: Graph Storage)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password-here  # CHANGE THIS!
NEO4J_DATABASE=neo4j
```

### Step 2.3: Start Neo4j

```bash
# Pull Neo4j image
docker pull neo4j:5.14-community

# Start Neo4j
docker compose up -d neo4j

# Check logs
docker compose logs -f neo4j

# Wait for health check to pass (30s)
# You should see: "Remote interface available at http://localhost:7474/"
```

### Step 2.4: Access Neo4j Browser

Open Neo4j Browser:

```bash
# Browser URL
http://localhost:7474

# Login credentials:
# - Username: neo4j
# - Password: (your password from .env)
```

Test connection in browser:

```cypher
// Test query
RETURN "Hello Neo4j!" AS message
```

### Step 2.5: Create Neo4j Client Wrapper

Create `src/components/graph_rag/neo4j_client.py`:

```python
"""Neo4j client wrapper with connection pooling and health checks.

Sprint 5: Feature 5.2 - Neo4j Backend Configuration
"""

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import settings

logger = structlog.get_logger(__name__)


class Neo4jClientWrapper:
    """Async Neo4j client with connection pooling and retry logic."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        max_connection_pool_size: int = 50,
        connection_timeout: int = 30,
    ):
        """Initialize Neo4j client.

        Args:
            uri: Neo4j Bolt URI
            user: Username
            password: Password
            database: Database name
            max_connection_pool_size: Max connections in pool
            connection_timeout: Connection timeout in seconds
        """
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self.database = database or settings.neo4j_database

        # Initialize async driver
        self.driver: AsyncDriver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
            max_connection_pool_size=max_connection_pool_size,
            connection_timeout=connection_timeout,
        )

        logger.info(
            "neo4j_client_initialized",
            uri=self.uri,
            database=self.database,
            pool_size=max_connection_pool_size,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def health_check(self) -> bool:
        """Check Neo4j connection health.

        Returns:
            True if healthy, False otherwise
        """
        try:
            async with self.driver.session(database=self.database) as session:
                result = await session.run("RETURN 1 AS health")
                record = await result.single()
                healthy = record and record["health"] == 1

                logger.info("neo4j_health_check", healthy=healthy)
                return healthy

        except Exception as e:
            logger.error("neo4j_health_check_failed", error=str(e))
            return False

    async def execute_read(
        self,
        query: str,
        parameters: dict | None = None,
    ) -> list[dict]:
        """Execute read query.

        Args:
            query: Cypher query
            parameters: Query parameters

        Returns:
            List of result records as dicts
        """
        async with self.driver.session(database=self.database) as session:
            result = await session.run(query, parameters or {})
            records = [record.data() async for record in result]

            logger.debug(
                "neo4j_read_query",
                query=query[:100],
                record_count=len(records),
            )

            return records

    async def execute_write(
        self,
        query: str,
        parameters: dict | None = None,
    ) -> list[dict]:
        """Execute write query.

        Args:
            query: Cypher query
            parameters: Query parameters

        Returns:
            List of result records as dicts
        """
        async with self.driver.session(database=self.database) as session:
            result = await session.run(query, parameters or {})
            records = [record.data() async for record in result]

            logger.debug(
                "neo4j_write_query",
                query=query[:100],
                record_count=len(records),
            )

            return records

    async def get_node_count(self, label: str | None = None) -> int:
        """Get count of nodes, optionally filtered by label.

        Args:
            label: Node label to filter (e.g., "Entity")

        Returns:
            Node count
        """
        if label:
            query = f"MATCH (n:{label}) RETURN count(n) AS count"
        else:
            query = "MATCH (n) RETURN count(n) AS count"

        results = await self.execute_read(query)
        return results[0]["count"] if results else 0

    async def get_relationship_count(self, rel_type: str | None = None) -> int:
        """Get count of relationships, optionally filtered by type.

        Args:
            rel_type: Relationship type to filter (e.g., "WORKS_AT")

        Returns:
            Relationship count
        """
        if rel_type:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS count"
        else:
            query = "MATCH ()-[r]->() RETURN count(r) AS count"

        results = await self.execute_read(query)
        return results[0]["count"] if results else 0

    async def close(self):
        """Close driver connection pool."""
        await self.driver.close()
        logger.info("neo4j_client_closed")


# Global instance (singleton pattern)
_neo4j_client: Neo4jClientWrapper | None = None


def get_neo4j_client() -> Neo4jClientWrapper:
    """Get global Neo4j client instance (singleton).

    Returns:
        Neo4jClientWrapper instance
    """
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClientWrapper()
    return _neo4j_client
```

### Step 2.6: Create Database Initialization Script

Create `scripts/init_neo4j.py`:

```python
"""Initialize Neo4j database schema for LightRAG.

Creates indexes and constraints for optimal graph query performance.

Sprint 5: Feature 5.2
"""

import asyncio
import structlog
from neo4j import AsyncGraphDatabase

from src.core.config import settings

logger = structlog.get_logger(__name__)


async def init_schema():
    """Initialize Neo4j indexes and constraints."""
    logger.info("neo4j_schema_init_started")

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    try:
        async with driver.session(database=settings.neo4j_database) as session:
            # Create index on Entity.name for fast lookups
            logger.info("creating_index", index="entity_name_idx")
            await session.run(
                "CREATE INDEX entity_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.name)"
            )

            # Create index on Entity.type for filtering
            logger.info("creating_index", index="entity_type_idx")
            await session.run(
                "CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.type)"
            )

            # Create uniqueness constraint on Entity.id
            logger.info("creating_constraint", constraint="entity_id_unique")
            await session.run(
                "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS "
                "FOR (e:Entity) REQUIRE e.id IS UNIQUE"
            )

            # Create index on Relationship.type
            logger.info("creating_index", index="relationship_type_idx")
            await session.run(
                "CREATE INDEX relationship_type_idx IF NOT EXISTS "
                "FOR ()-[r:RELATED_TO]->() ON (r.type)"
            )

            # Create index on Document.id for incremental updates
            logger.info("creating_index", index="document_id_idx")
            await session.run(
                "CREATE INDEX document_id_idx IF NOT EXISTS FOR (d:Document) ON (d.id)"
            )

            # Create constraint on Document.id
            logger.info("creating_constraint", constraint="document_id_unique")
            await session.run(
                "CREATE CONSTRAINT document_id_unique IF NOT EXISTS "
                "FOR (d:Document) REQUIRE d.id IS UNIQUE"
            )

            logger.info("neo4j_schema_init_complete")
            print("✅ Neo4j schema initialized successfully")
            print("   - Indexes: entity_name, entity_type, relationship_type, document_id")
            print("   - Constraints: entity_id_unique, document_id_unique")

    except Exception as e:
        logger.error("neo4j_schema_init_failed", error=str(e))
        print(f"❌ Neo4j schema initialization failed: {e}")
        raise

    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(init_schema())
```

Run the initialization:

```bash
python scripts/init_neo4j.py
```

Expected output:

```
✅ Neo4j schema initialized successfully
   - Indexes: entity_name, entity_type, relationship_type, document_id
   - Constraints: entity_id_unique, document_id_unique
```

### Step 2.7: Verify Schema in Neo4j Browser

```cypher
// Show all indexes
SHOW INDEXES

// Show all constraints
SHOW CONSTRAINTS

// Expected:
// - entity_name_idx (INDEX)
// - entity_type_idx (INDEX)
// - entity_id_unique (UNIQUENESS CONSTRAINT)
// - relationship_type_idx (INDEX)
// - document_id_idx (INDEX)
// - document_id_unique (UNIQUENESS CONSTRAINT)
```

### Step 2.8: Write Integration Tests

Create `tests/integration/test_neo4j_integration.py`:

```python
"""Integration tests for Neo4j client.

Sprint 5: Feature 5.2
"""

import pytest
from src.components.graph_rag.neo4j_client import Neo4jClientWrapper


@pytest.fixture
async def neo4j_client():
    """Neo4j client fixture."""
    client = Neo4jClientWrapper()
    yield client
    await client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_neo4j_health_check(neo4j_client):
    """Test Neo4j health check."""
    healthy = await neo4j_client.health_check()
    assert healthy is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_neo4j_create_and_query_node(neo4j_client):
    """Test creating and querying a node."""
    # Create test node
    await neo4j_client.execute_write(
        """
        CREATE (p:Person {name: $name, age: $age})
        """,
        {"name": "Test Person", "age": 30},
    )

    # Query node
    results = await neo4j_client.execute_read(
        """
        MATCH (p:Person {name: $name})
        RETURN p.name AS name, p.age AS age
        """,
        {"name": "Test Person"},
    )

    assert len(results) == 1
    assert results[0]["name"] == "Test Person"
    assert results[0]["age"] == 30

    # Cleanup
    await neo4j_client.execute_write(
        "MATCH (p:Person {name: $name}) DELETE p",
        {"name": "Test Person"},
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_neo4j_node_count(neo4j_client):
    """Test getting node count."""
    # Create test nodes
    await neo4j_client.execute_write(
        """
        CREATE (p1:TestEntity {name: 'Entity1'})
        CREATE (p2:TestEntity {name: 'Entity2'})
        """
    )

    # Get count
    count = await neo4j_client.get_node_count(label="TestEntity")
    assert count >= 2

    # Cleanup
    await neo4j_client.execute_write("MATCH (n:TestEntity) DELETE n")
```

Run integration tests:

```bash
pytest tests/integration/test_neo4j_integration.py -v
```

---

## Feature 5.3: Entity & Relationship Extraction

**Goal:** Extract entities and relationships from text using LLM.

**Estimated Time:** 2 days

### Step 3.1: Create Extraction Prompts

Create `src/components/graph_rag/prompts.py`:

```python
"""Prompts for entity and relationship extraction.

Sprint 5: Feature 5.3
"""

ENTITY_EXTRACTION_PROMPT = """
Extract entities from the following text. For each entity, identify:
1. Entity name (exact string from text)
2. Entity type (Person, Organization, Location, Event, Concept, Technology, Product, etc.)
3. Short description (1 sentence, based on context in text)

Text:
{text}

Return entities as a JSON array. Use this exact format:
[
  {{"name": "Entity Name", "type": "EntityType", "description": "One sentence description"}},
  ...
]

Guidelines:
- Extract ALL significant entities mentioned in the text
- Use standard entity types (Person, Organization, Location, Technology, etc.)
- Be comprehensive but avoid duplicates
- Keep descriptions concise (1 sentence)
- Return only valid JSON (no additional text)

Entities:
"""

RELATIONSHIP_EXTRACTION_PROMPT = """
Extract relationships between entities from the following text.

Entities found in this text:
{entities}

Text:
{text}

For each relationship, identify:
1. Source entity (must be from the list above)
2. Target entity (must be from the list above)
3. Relationship type (WORKS_AT, KNOWS, LOCATED_IN, USES, CREATES, PART_OF, etc.)
4. Description (1 sentence explaining the relationship based on text)

Return relationships as a JSON array. Use this exact format:
[
  {{"source": "Entity1", "target": "Entity2", "type": "RELATIONSHIP_TYPE", "description": "One sentence description"}},
  ...
]

Guidelines:
- Only extract relationships explicitly stated or strongly implied in the text
- Use standard relationship types (uppercase with underscores, e.g., WORKS_AT)
- Common types: WORKS_AT, KNOWS, LOCATED_IN, CREATED, USES, PART_OF, MANAGES
- Ensure source and target entities exist in the list above
- Return only valid JSON (no additional text)

Relationships:
"""
```

### Step 3.2: Create Extraction Models

Add to `src/components/graph_rag/models.py`:

```python
# Add to existing models.py

class Entity(BaseModel):
    """Extracted entity from text."""

    name: str = Field(..., description="Entity name (exact from text)")
    type: str = Field(..., description="Entity type (Person, Organization, etc.)")
    description: str = Field(..., description="Entity description (1 sentence)")
    source_document: str | None = Field(
        default=None,
        description="Source document ID"
    )


class Relationship(BaseModel):
    """Extracted relationship between entities."""

    source: str = Field(..., description="Source entity name")
    target: str = Field(..., description="Target entity name")
    type: str = Field(..., description="Relationship type (WORKS_AT, KNOWS, etc.)")
    description: str = Field(..., description="Relationship description (1 sentence)")
    source_document: str | None = Field(
        default=None,
        description="Source document ID"
    )
```

### Step 3.3: Implement Extraction Pipeline

Create `src/components/graph_rag/extraction.py`:

```python
"""Entity and relationship extraction pipeline using LLM.

Sprint 5: Feature 5.3 - Entity & Relationship Extraction
"""

import json
import re
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
from src.components.graph_rag.models import Entity, Relationship
from src.components.graph_rag.prompts import (
    ENTITY_EXTRACTION_PROMPT,
    RELATIONSHIP_EXTRACTION_PROMPT,
)

logger = structlog.get_logger(__name__)


class ExtractionPipeline:
    """Entity and relationship extraction using Ollama LLM."""

    def __init__(
        self,
        llm_model: str | None = None,
        ollama_base_url: str | None = None,
        temperature: float | None = None,
    ):
        """Initialize extraction pipeline.

        Args:
            llm_model: Ollama LLM model name
            ollama_base_url: Ollama server URL
            temperature: LLM temperature for extraction
        """
        self.llm_model = llm_model or settings.lightrag_llm_model
        self.ollama_base_url = ollama_base_url or settings.ollama_base_url
        self.temperature = temperature if temperature is not None else settings.lightrag_llm_temperature

        # Initialize Ollama client
        self.client = AsyncClient(host=self.ollama_base_url)

        logger.info(
            "extraction_pipeline_initialized",
            llm_model=self.llm_model,
            ollama_url=self.ollama_base_url,
            temperature=self.temperature,
        )

    def _parse_json_response(self, response: str) -> list[dict[str, Any]]:
        """Parse JSON from LLM response.

        Handles various response formats and cleans up common issues.

        Args:
            response: Raw LLM response text

        Returns:
            Parsed JSON as list of dicts

        Raises:
            ValueError: If JSON parsing fails
        """
        # Try to extract JSON from response
        # Sometimes LLM adds extra text before/after JSON

        # Look for JSON array pattern
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response

        # Clean up common JSON issues
        json_str = json_str.strip()
        json_str = json_str.replace("'", '"')  # Single quotes to double quotes

        try:
            data = json.loads(json_str)
            if isinstance(data, list):
                return data
            else:
                logger.warning("json_not_array", data_type=type(data))
                return [data] if data else []

        except json.JSONDecodeError as e:
            logger.error(
                "json_parse_failed",
                response=response[:500],
                error=str(e),
            )
            # Return empty list instead of raising
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def extract_entities(
        self,
        text: str,
        document_id: str | None = None,
    ) -> list[Entity]:
        """Extract entities from text using LLM.

        Args:
            text: Document text
            document_id: Source document ID

        Returns:
            List of extracted entities
        """
        logger.info(
            "extracting_entities",
            text_length=len(text),
            document_id=document_id,
        )

        # Format prompt
        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)

        try:
            # Call Ollama LLM
            response = await self.client.generate(
                model=self.llm_model,
                prompt=prompt,
                options={
                    "temperature": self.temperature,
                    "num_predict": 2048,
                },
            )

            llm_response = response.get("response", "")

            # Parse JSON response
            entities_data = self._parse_json_response(llm_response)

            # Create Entity objects
            entities = []
            for entity_dict in entities_data:
                try:
                    entity = Entity(
                        name=entity_dict.get("name", ""),
                        type=entity_dict.get("type", "Unknown"),
                        description=entity_dict.get("description", ""),
                        source_document=document_id,
                    )
                    entities.append(entity)
                except Exception as e:
                    logger.warning(
                        "entity_creation_failed",
                        entity_dict=entity_dict,
                        error=str(e),
                    )

            logger.info(
                "entities_extracted",
                count=len(entities),
                document_id=document_id,
            )

            return entities

        except Exception as e:
            logger.error(
                "entity_extraction_failed",
                document_id=document_id,
                error=str(e),
            )
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def extract_relationships(
        self,
        text: str,
        entities: list[Entity],
        document_id: str | None = None,
    ) -> list[Relationship]:
        """Extract relationships from text given entities.

        Args:
            text: Document text
            entities: Extracted entities from text
            document_id: Source document ID

        Returns:
            List of extracted relationships
        """
        logger.info(
            "extracting_relationships",
            text_length=len(text),
            entity_count=len(entities),
            document_id=document_id,
        )

        if not entities:
            logger.warning("no_entities_for_relationship_extraction")
            return []

        # Format entity list for prompt
        entity_list = "\n".join([f"- {e.name} ({e.type})" for e in entities])

        # Format prompt
        prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(
            entities=entity_list,
            text=text,
        )

        try:
            # Call Ollama LLM
            response = await self.client.generate(
                model=self.llm_model,
                prompt=prompt,
                options={
                    "temperature": self.temperature,
                    "num_predict": 2048,
                },
            )

            llm_response = response.get("response", "")

            # Parse JSON response
            relationships_data = self._parse_json_response(llm_response)

            # Create Relationship objects
            relationships = []
            for rel_dict in relationships_data:
                try:
                    relationship = Relationship(
                        source=rel_dict.get("source", ""),
                        target=rel_dict.get("target", ""),
                        type=rel_dict.get("type", "RELATED_TO"),
                        description=rel_dict.get("description", ""),
                        source_document=document_id,
                    )
                    relationships.append(relationship)
                except Exception as e:
                    logger.warning(
                        "relationship_creation_failed",
                        rel_dict=rel_dict,
                        error=str(e),
                    )

            logger.info(
                "relationships_extracted",
                count=len(relationships),
                document_id=document_id,
            )

            return relationships

        except Exception as e:
            logger.error(
                "relationship_extraction_failed",
                document_id=document_id,
                error=str(e),
            )
            raise

    async def extract_from_document(
        self,
        document: str,
        document_id: str,
    ) -> tuple[list[Entity], list[Relationship]]:
        """Extract entities and relationships from a single document.

        Args:
            document: Document text
            document_id: Document ID

        Returns:
            Tuple of (entities, relationships)
        """
        logger.info("extracting_from_document", document_id=document_id)

        # Extract entities first
        entities = await self.extract_entities(document, document_id)

        # Extract relationships based on entities
        relationships = await self.extract_relationships(
            document,
            entities,
            document_id,
        )

        logger.info(
            "extraction_complete",
            document_id=document_id,
            entities=len(entities),
            relationships=len(relationships),
        )

        return entities, relationships

    async def extract_from_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> tuple[list[Entity], list[Relationship]]:
        """Batch extraction from multiple documents.

        Args:
            documents: List of {'id': str, 'text': str} dicts

        Returns:
            Tuple of (all_entities, all_relationships)
        """
        logger.info("batch_extraction_started", document_count=len(documents))

        all_entities = []
        all_relationships = []

        for i, doc in enumerate(documents):
            try:
                entities, relationships = await self.extract_from_document(
                    doc["text"],
                    doc["id"],
                )
                all_entities.extend(entities)
                all_relationships.extend(relationships)

                logger.info(
                    "batch_extraction_progress",
                    progress=f"{i+1}/{len(documents)}",
                )

            except Exception as e:
                logger.error(
                    "batch_extraction_document_failed",
                    document_id=doc["id"],
                    error=str(e),
                )

        logger.info(
            "batch_extraction_complete",
            documents=len(documents),
            entities=len(all_entities),
            relationships=len(all_relationships),
        )

        return all_entities, all_relationships


# Global instance (singleton pattern)
_extraction_pipeline: ExtractionPipeline | None = None


def get_extraction_pipeline() -> ExtractionPipeline:
    """Get global extraction pipeline instance (singleton).

    Returns:
        ExtractionPipeline instance
    """
    global _extraction_pipeline
    if _extraction_pipeline is None:
        _extraction_pipeline = ExtractionPipeline()
    return _extraction_pipeline
```

### Step 3.4: Write Unit Tests

Create `tests/components/graph_rag/test_extraction.py`:

```python
"""Unit tests for entity/relationship extraction.

Sprint 5: Feature 5.3
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.components.graph_rag.extraction import ExtractionPipeline
from src.components.graph_rag.models import Entity, Relationship


@pytest.fixture
def extraction_pipeline():
    """Extraction pipeline fixture."""
    return ExtractionPipeline(
        llm_model="llama3.2:3b",
        ollama_base_url="http://localhost:11434",
    )


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    def _response(json_data):
        return {"response": json.dumps(json_data)}
    return _response


class TestExtractionPipeline:
    """Test extraction pipeline."""

    def test_initialization(self, extraction_pipeline):
        """Test pipeline initializes correctly."""
        assert extraction_pipeline is not None
        assert extraction_pipeline.llm_model == "llama3.2:3b"

    def test_parse_json_response(self, extraction_pipeline):
        """Test JSON parsing from LLM response."""
        # Valid JSON array
        response = '[{"name": "John", "type": "Person"}]'
        parsed = extraction_pipeline._parse_json_response(response)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "John"

    def test_parse_json_response_with_extra_text(self, extraction_pipeline):
        """Test JSON parsing with extra text."""
        response = 'Here are the entities:\n[{"name": "John", "type": "Person"}]\nDone!'
        parsed = extraction_pipeline._parse_json_response(response)
        assert len(parsed) == 1

    @pytest.mark.asyncio
    async def test_extract_entities(self, extraction_pipeline, mock_ollama_response):
        """Test entity extraction."""
        mock_entities = [
            {"name": "John Smith", "type": "Person", "description": "Software engineer"},
            {"name": "Google", "type": "Organization", "description": "Technology company"},
        ]

        with patch.object(
            extraction_pipeline.client,
            'generate',
            new=AsyncMock(return_value=mock_ollama_response(mock_entities))
        ):
            text = "John Smith works at Google as a software engineer."
            entities = await extraction_pipeline.extract_entities(text, "doc1")

            assert len(entities) == 2
            assert isinstance(entities[0], Entity)
            assert entities[0].name == "John Smith"
            assert entities[0].type == "Person"
            assert entities[0].source_document == "doc1"

    @pytest.mark.asyncio
    async def test_extract_relationships(self, extraction_pipeline, mock_ollama_response):
        """Test relationship extraction."""
        entities = [
            Entity(name="John Smith", type="Person", description="Engineer"),
            Entity(name="Google", type="Organization", description="Company"),
        ]

        mock_relationships = [
            {
                "source": "John Smith",
                "target": "Google",
                "type": "WORKS_AT",
                "description": "John Smith works at Google"
            }
        ]

        with patch.object(
            extraction_pipeline.client,
            'generate',
            new=AsyncMock(return_value=mock_ollama_response(mock_relationships))
        ):
            text = "John Smith works at Google."
            relationships = await extraction_pipeline.extract_relationships(
                text,
                entities,
                "doc1"
            )

            assert len(relationships) == 1
            assert isinstance(relationships[0], Relationship)
            assert relationships[0].source == "John Smith"
            assert relationships[0].target == "Google"
            assert relationships[0].type == "WORKS_AT"

    @pytest.mark.asyncio
    async def test_extract_from_document(self, extraction_pipeline):
        """Test full document extraction (integration with real Ollama)."""
        # Skip if Ollama not available
        pytest.skip("Integration test - requires Ollama running")

        text = """
        John Smith is a software engineer at Google. He previously worked at Microsoft.
        Google is a technology company based in Mountain View, California.
        """

        entities, relationships = await extraction_pipeline.extract_from_document(
            text,
            "test_doc_1"
        )

        # Should extract at least: John Smith, Google, Microsoft, Mountain View
        assert len(entities) >= 3
        # Should extract at least: John-WORKS_AT->Google, Google-LOCATED_IN->Mountain View
        assert len(relationships) >= 1
```

### Step 3.5: Manual Testing

Create `scripts/test_extraction.py`:

```python
"""Manual test script for extraction pipeline."""

import asyncio
from src.components.graph_rag.extraction import ExtractionPipeline


async def main():
    pipeline = ExtractionPipeline()

    text = """
    John Smith is a senior software engineer at Google, where he has worked since 2020.
    Before joining Google, John spent five years at Microsoft working on Azure.
    John lives in San Francisco and specializes in machine learning and distributed systems.
    Google is a multinational technology company headquartered in Mountain View, California.
    """

    print("Extracting entities...")
    entities = await pipeline.extract_entities(text, "test_doc")
    print(f"\nExtracted {len(entities)} entities:")
    for entity in entities:
        print(f"  - {entity.name} ({entity.type}): {entity.description}")

    print("\nExtracting relationships...")
    relationships = await pipeline.extract_relationships(text, entities, "test_doc")
    print(f"\nExtracted {len(relationships)} relationships:")
    for rel in relationships:
        print(f"  - {rel.source} --[{rel.type}]--> {rel.target}")
        print(f"    Description: {rel.description}")


if __name__ == "__main__":
    asyncio.run(main())
```

Run the test:

```bash
python scripts/test_extraction.py
```

---

## Testing Strategy

### Unit Tests (80%+ Coverage)

**Test Categories:**
1. **Initialization Tests:** Verify component initialization
2. **Core Functionality Tests:** Test main methods with mocked dependencies
3. **Error Handling Tests:** Test exception handling and retry logic
4. **Edge Case Tests:** Test empty inputs, malformed data, etc.

**Mocking Strategy:**
- Mock Ollama API calls (for speed and reliability)
- Mock Neo4j connections (for unit tests)
- Use real dependencies only in integration tests

**Run Unit Tests:**
```bash
pytest tests/components/graph_rag/ -v --cov=src/components/graph_rag
```

### Integration Tests

**Test Real Dependencies:**
- LightRAG + Neo4j integration
- Ollama LLM calls
- End-to-end document → graph → query flow

**Fixtures:**
```python
@pytest.fixture(scope="session")
async def neo4j_client():
    """Real Neo4j client for integration tests."""
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper
    client = Neo4jClientWrapper()
    yield client
    # Cleanup test data
    await client.execute_write("MATCH (n:TestEntity) DELETE n")
    await client.close()
```

**Run Integration Tests:**
```bash
pytest tests/integration/ -v -m integration
```

### End-to-End Tests

**E2E Test Scenarios:**
1. Document ingestion → Graph construction → Entity count verification
2. Graph query (local mode) → Answer generation → Result validation
3. Incremental update → No duplicates → Entity count delta check

**Example E2E Test:**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_graph_construction():
    """Test full pipeline: document → entities → graph → query."""
    from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper

    # 1. Initialize LightRAG
    lightrag = LightRAGWrapper()

    # 2. Insert test document
    text = "John Smith works at Google in San Francisco."
    await lightrag.insert_text(text)

    # 3. Query graph
    result = await lightrag.query("Where does John Smith work?", mode="local")

    # 4. Verify answer
    assert "Google" in result.answer
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Neo4j Docker Volume Permissions (Windows)

**Problem:** Neo4j container fails to start due to volume permission errors on Windows.

**Solution:**
```yaml
# docker-compose.yml
# Use named volumes instead of bind mounts
volumes:
  neo4j_data:
    driver: local
  # NOT: - ./data/neo4j:/data  (causes permission issues on Windows)
```

### Pitfall 2: LLM JSON Parsing Errors

**Problem:** LLM returns malformed JSON or includes extra text.

**Solution:**
- Implement robust JSON parsing with regex extraction
- Add retry logic with exponential backoff
- Log failures and return empty lists instead of crashing

```python
def _parse_json_response(self, response: str) -> list[dict]:
    """Robust JSON parsing with fallback."""
    json_match = re.search(r'\[.*\]', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            logger.error("json_parse_failed", response=response[:500])
            return []  # Graceful degradation
    return []
```

### Pitfall 3: Entity Deduplication

**Problem:** Same entity extracted multiple times with slight variations (e.g., "John Smith" vs. "J. Smith").

**Solution:**
- Implement fuzzy matching in Feature 5.6
- Use Neo4j MERGE instead of CREATE
- Add confidence scoring for entity merges

### Pitfall 4: Slow Graph Queries

**Problem:** Graph queries exceed 500ms target latency.

**Solution:**
- Ensure Neo4j indexes are created (run `scripts/init_neo4j.py`)
- Limit graph traversal depth (max 2-3 hops)
- Use Cypher query profiling: `PROFILE MATCH ... RETURN ...`
- Consider caching frequent queries

### Pitfall 5: LightRAG API Changes

**Problem:** LightRAG library updates break wrapper implementation.

**Solution:**
- Pin LightRAG version in `pyproject.toml`: `lightrag-hku = "^0.2.0"`
- Add version check in wrapper initialization
- Maintain abstraction layer (LightRAGWrapper) to isolate changes

---

## Performance Optimization

### Optimization 1: Batch Extraction

**Problem:** Extracting entities from 100+ documents takes too long (sequential processing).

**Solution:** Implement batch processing with async concurrency.

```python
async def extract_batch_concurrent(
    self,
    documents: list[dict],
    max_concurrent: int = 5,
) -> tuple[list[Entity], list[Relationship]]:
    """Extract from multiple documents concurrently."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def extract_with_semaphore(doc):
        async with semaphore:
            return await self.extract_from_document(doc["text"], doc["id"])

    tasks = [extract_with_semaphore(doc) for doc in documents]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Flatten results
    all_entities = []
    all_relationships = []
    for result in results:
        if isinstance(result, tuple):
            entities, relationships = result
            all_entities.extend(entities)
            all_relationships.extend(relationships)

    return all_entities, all_relationships
```

### Optimization 2: Neo4j Indexing

**Problem:** Graph queries slow as graph grows.

**Solution:** Create composite indexes for common query patterns.

```cypher
// Composite index for entity lookup by name and type
CREATE INDEX entity_name_type_idx IF NOT EXISTS
FOR (e:Entity) ON (e.name, e.type)

// Full-text search index for entity names
CREATE FULLTEXT INDEX entity_name_fulltext IF NOT EXISTS
FOR (e:Entity) ON EACH [e.name, e.description]
```

### Optimization 3: Query Caching

**Problem:** Same queries executed repeatedly (e.g., "What is RAG?").

**Solution:** Implement LRU cache for query results.

```python
from functools import lru_cache

class GraphSearch:
    @lru_cache(maxsize=128)
    async def search_cached(self, query: str, mode: str) -> GraphQueryResult:
        """Cached graph search."""
        return await self.search(query, mode)
```

---

## Monitoring & Debugging

### Logging Configuration

**Structured Logging with Structlog:**
```python
import structlog

logger = structlog.get_logger(__name__)

logger.info(
    "graph_query_executed",
    query=query[:100],
    mode=mode,
    entities_found=len(entities),
    execution_time_ms=execution_time,
)
```

### Neo4j Query Profiling

**Profile Slow Queries:**
```cypher
// Profile query execution plan
PROFILE
MATCH (p:Person {name: "John Smith"})-[r:WORKS_AT]->(o:Organization)
RETURN p, r, o

// Explain query plan (no execution)
EXPLAIN
MATCH (p:Person {name: "John Smith"})-[r:WORKS_AT]->(o:Organization)
RETURN p, r, o
```

### Metrics to Track

**Key Metrics:**
- Entity extraction latency (p50, p95, p99)
- Graph query latency (p50, p95, p99)
- Entity count (over time)
- Relationship count (over time)
- LLM call count and cost (if using paid API)
- Neo4j query count and avg duration

**Prometheus Metrics Example:**
```python
from prometheus_client import Counter, Histogram

entity_extraction_duration = Histogram(
    'graph_entity_extraction_duration_seconds',
    'Entity extraction duration',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0]
)

graph_query_duration = Histogram(
    'graph_query_duration_seconds',
    'Graph query duration',
    buckets=[0.1, 0.3, 0.5, 1.0, 2.0]
)
```

### Debugging Tools

**Neo4j Browser:**
- Access: http://localhost:7474
- Visualize graph structure
- Execute Cypher queries
- Monitor query performance

**LangSmith (Optional):**
- Trace LLM calls
- Debug extraction prompts
- Monitor token usage

---

## Next Steps

After completing Sprint 5:

1. **Verify All Features:**
   - [ ] Run full test suite: `pytest tests/ -v`
   - [ ] Check test coverage: `pytest --cov=src --cov-report=html`
   - [ ] Manual testing via scripts
   - [ ] Verify all 6 features complete

2. **Documentation:**
   - [ ] Create SPRINT_5_SUMMARY.md
   - [ ] Create SPRINT_5_COMPLETION_REPORT.md
   - [ ] Update README.md
   - [ ] Create ADRs for key decisions

3. **Prepare for Sprint 6:**
   - [ ] Review Sprint 6 plan (Hybrid Vector-Graph Fusion)
   - [ ] Identify integration points
   - [ ] Plan parallel execution strategy

4. **Sprint 5 Retrospective:**
   - What went well?
   - What could be improved?
   - Action items for Sprint 6

---

**End of Sprint 5 Implementation Guide**

For questions or issues, refer to:
- SPRINT_5_PLAN.md (high-level plan)
- docs/examples/sprint5_examples.md (usage examples)
- LightRAG documentation: https://github.com/HKUDS/LightRAG
- Neo4j Cypher manual: https://neo4j.com/docs/cypher-manual/
