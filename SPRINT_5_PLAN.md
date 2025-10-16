# Sprint 5 Plan - LightRAG Integration & Graph Retrieval

**Sprint Goal:** Implement Graph-based Reasoning with LightRAG + Neo4j
**Duration:** 5-6 working days
**Story Points:** 42 (within capacity: 40-50 with buffer)
**Status:** Planning → Ready to Start

---

## Executive Summary

Sprint 5 introduces **graph-based retrieval** capabilities to AEGIS RAG by integrating LightRAG with Neo4j. This enables the system to perform entity-relationship reasoning, dual-level retrieval (entities + topics), and multi-hop graph traversal alongside existing vector search capabilities.

### Sprint 5 Position in System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AEGIS RAG Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│ Sprint 4: LangGraph Orchestration Layer                         │
│   ├─ Coordinator Agent                                          │
│   ├─ Query Router (VECTOR | GRAPH | HYBRID | MEMORY) ← EXISTS  │
│   └─ State Management                                           │
├─────────────────────────────────────────────────────────────────┤
│ Sprint 2-3: Vector Search (COMPLETE)                            │
│   ├─ Hybrid Search (Vector + BM25 + RRF)                        │
│   ├─ Cross-Encoder Reranking                                    │
│   ├─ Query Decomposition                                        │
│   ├─ Metadata Filtering                                         │
│   └─ Adaptive Chunking                                          │
├─────────────────────────────────────────────────────────────────┤
│ Sprint 5: Graph Retrieval (NEW) ← THIS SPRINT                   │
│   ├─ LightRAG Integration                                       │
│   ├─ Neo4j Knowledge Graph                                      │
│   ├─ Entity/Relationship Extraction                             │
│   ├─ Dual-Level Retrieval (Entities + Topics)                   │
│   ├─ Graph Query Agent                                          │
│   └─ Incremental Graph Updates                                  │
├─────────────────────────────────────────────────────────────────┤
│ Future: Sprint 6 - Hybrid Vector-Graph Fusion                   │
│ Future: Sprint 7-8 - Temporal Memory (Graphiti)                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Deliverables

1. **LightRAG Core Integration** - Graph construction and dual-level retrieval
2. **Neo4j Backend Setup** - Graph database with persistence and health checks
3. **Entity/Relationship Extraction** - LLM-powered knowledge graph construction
4. **Graph Query Agent** - LangGraph integration for GRAPH intent routing
5. **Dual-Level Search** - Entities (specific) + Topics (general) retrieval
6. **Incremental Updates** - Add documents without full graph rebuild

### Success Metrics

- Knowledge graph with 500+ entities constructed from test corpus
- Graph queries complete in <500ms (p95)
- Dual-level retrieval functional (entities + topics)
- Incremental updates work without full reindex
- 80%+ test coverage (unit + integration)
- GRAPH intent routing accuracy >85%

---

## Sprint 5 Objectives

### Primary Goals

1. **Enable Graph-based Reasoning**
   - Build knowledge graph from document corpus
   - Extract entities and relationships using LLM
   - Support graph traversal and reasoning

2. **Integrate with Sprint 4 Router**
   - Implement Graph Query Agent
   - Handle GRAPH intent routing
   - Return structured graph-based results

3. **Dual-Level Retrieval**
   - Entity-level search (specific entities, relationships)
   - Topic-level search (high-level concepts, communities)
   - Combine both for comprehensive coverage

4. **Production-Ready Implementation**
   - Neo4j persistence and backup
   - Incremental graph updates
   - Error handling and retry logic
   - Monitoring and observability

### Non-Goals (Deferred to Sprint 6)

- Hybrid vector+graph fusion (RRF across retrieval types)
- Multi-hop query expansion and reasoning
- Community detection and topic clustering
- Performance optimization (query caching, indexing)

---

## Feature Breakdown (1 Feature = 1 Commit)

### Feature 5.1: LightRAG Core Integration

**Priority:** P0 (Blocker for all other features)
**Story Points:** 8
**Effort:** 1.5 days

**Deliverables:**
- LightRAG Python package installation and configuration
- LightRAGWrapper class with async support
- Configuration for Ollama LLM + embeddings
- Graph storage backend (Neo4j connector)
- Basic graph construction from text documents
- Unit tests for LightRAG wrapper (20+ tests)

**Technical Tasks:**
1. Install `lightrag-hku` via pip (official LightRAG package)
2. Create `src/components/graph_rag/lightrag_wrapper.py`
3. Configure LightRAG:
   - LLM: Ollama llama3.2:8b (generation)
   - Embeddings: Ollama nomic-embed-text
   - Storage: Neo4j backend (via `lightrag.storage.Neo4jStorage`)
4. Implement graph construction methods:
   - `insert_text(text: str)` - Add document to graph
   - `insert_documents(docs: List[Document])` - Batch insertion
   - `query(query: str, mode: str)` - Query graph (local/global/hybrid)
5. Add retry logic with tenacity
6. Write unit tests with mocked Neo4j

**Configuration:**
```python
# src/core/config.py
class Settings(BaseSettings):
    # LightRAG Settings (Sprint 5: Graph RAG)
    lightrag_enabled: bool = Field(default=True, description="Enable LightRAG graph retrieval")
    lightrag_working_dir: str = Field(default="./data/lightrag", description="LightRAG working directory")

    # LightRAG LLM Configuration
    lightrag_llm_model: str = Field(default="llama3.2:8b", description="LLM for entity extraction")
    lightrag_llm_temperature: float = Field(default=0.1, description="LLM temperature for extraction")
    lightrag_llm_max_tokens: int = Field(default=4096, description="Max tokens for LLM response")

    # LightRAG Embedding Configuration
    lightrag_embedding_model: str = Field(default="nomic-embed-text", description="Embedding model")
    lightrag_embedding_dim: int = Field(default=768, description="Embedding dimension (nomic=768)")

    # Graph Construction Settings
    lightrag_entity_extraction_batch_size: int = Field(default=5, description="Batch size for extraction")
    lightrag_max_tokens_per_chunk: int = Field(default=1200, description="Max tokens per chunk for extraction")

    # Neo4j Backend (Sprint 5: Graph Storage)
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="your-password-here", description="Neo4j password")
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")
```

**API Models:**
```python
# src/components/graph_rag/models.py
from pydantic import BaseModel, Field
from enum import Enum

class GraphQueryMode(str, Enum):
    """LightRAG query modes."""
    LOCAL = "local"      # Entity-level (specific entities and relationships)
    GLOBAL = "global"    # Topic-level (high-level summaries, communities)
    HYBRID = "hybrid"    # Combined local + global

class GraphNode(BaseModel):
    """Graph node (entity) representation."""
    id: str = Field(..., description="Unique node ID")
    label: str = Field(..., description="Node label/type (Person, Organization, etc.)")
    properties: dict[str, Any] = Field(default_factory=dict, description="Node properties")

class GraphRelationship(BaseModel):
    """Graph relationship (edge) representation."""
    id: str = Field(..., description="Unique relationship ID")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Relationship type (WORKS_AT, KNOWS, etc.)")
    properties: dict[str, Any] = Field(default_factory=dict, description="Relationship properties")

class GraphQueryResult(BaseModel):
    """Graph query result."""
    query: str = Field(..., description="Original query")
    mode: GraphQueryMode = Field(..., description="Query mode used")
    answer: str = Field(..., description="LLM-generated answer from graph context")
    entities: list[GraphNode] = Field(default_factory=list, description="Retrieved entities")
    relationships: list[GraphRelationship] = Field(default_factory=list, description="Retrieved relationships")
    context: str = Field(default="", description="Graph context used for answer generation")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Query metadata")
```

**Acceptance Criteria:**
- LightRAG wrapper initializes with Ollama LLM + embeddings
- Graph construction works for text documents
- Neo4j connection established and verified
- Query modes (local/global/hybrid) functional
- 20+ unit tests passing
- Configuration documented

**Git Commit Message:**
```
feat(graph-rag): implement LightRAG core integration with Neo4j backend

Integrates LightRAG for graph-based knowledge retrieval using Neo4j as storage backend.
Supports entity/relationship extraction and dual-level retrieval (local/global).

Features:
- LightRAGWrapper with async support
- Ollama LLM integration (llama3.2:8b for extraction)
- Ollama embeddings (nomic-embed-text, dim=768)
- Neo4j storage backend
- Graph construction from documents
- Query modes: local (entities), global (topics), hybrid
- Configurable extraction parameters

Components:
- src/components/graph_rag/lightrag_wrapper.py (400+ lines)
- src/components/graph_rag/models.py (Pydantic models)
- Configuration: lightrag_* settings in config.py

Performance:
- Entity extraction: ~2-3s per document (depends on size)
- Graph query: <500ms target (Neo4j indexed)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Dependencies:** Neo4j running on localhost:7687, Ollama with llama3.2:8b + nomic-embed-text
**Risks:** LightRAG API changes (new package), Neo4j connection issues

---

### Feature 5.2: Neo4j Backend Configuration

**Priority:** P0 (Blocker for Feature 5.1)
**Story Points:** 5
**Effort:** 1 day

**Deliverables:**
- Neo4j Docker Compose service with persistence
- Neo4j connection pool and health checks
- Database schema initialization (indexes, constraints)
- Backup and restore scripts
- Neo4jClientWrapper with retry logic
- Integration tests for Neo4j operations (15+ tests)

**Technical Tasks:**
1. Add Neo4j service to `docker-compose.yml`:
   - Image: `neo4j:5.14-community` (aligned with neo4j==5.14.0 driver)
   - Persistent volumes for data + logs
   - Environment variables (auth, memory config)
   - Health check endpoint
2. Create `src/components/graph_rag/neo4j_client.py`:
   - AsyncDriver connection pool
   - Health check method
   - Transaction management (read/write)
   - Retry logic with exponential backoff
3. Create `scripts/init_neo4j.py`:
   - Create indexes on entity/relationship properties
   - Create uniqueness constraints
   - Initialize database schema
4. Create `scripts/backup_neo4j.sh` and `scripts/restore_neo4j.sh`
5. Write integration tests with real Neo4j instance

**Docker Compose Configuration:**
```yaml
# docker-compose.yml (add to existing services)
services:
  # ... existing services (qdrant, redis)

  neo4j:
    image: neo4j:5.14-community
    container_name: aegis-neo4j
    ports:
      - "7474:7474"  # HTTP browser UI
      - "7687:7687"  # Bolt protocol
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-your-password-here}
      - NEO4J_PLUGINS=["apoc"]  # APOC procedures (optional but recommended)
      - NEO4J_server_memory_heap_initial__size=512m
      - NEO4J_server_memory_heap_max__size=2g
      - NEO4J_server_memory_pagecache_size=1g
    volumes:
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
  # ... existing volumes
  neo4j_data:
    driver: local
  neo4j_logs:
    driver: local
  neo4j_import:
    driver: local
  neo4j_plugins:
    driver: local
```

**Neo4j Client Wrapper:**
```python
# src/components/graph_rag/neo4j_client.py
from neo4j import AsyncGraphDatabase, AsyncDriver
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)

class Neo4jClientWrapper:
    """Async Neo4j client with connection pooling and health checks."""

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
        max_connection_pool_size: int = 50,
        connection_timeout: int = 30,
    ):
        self.uri = uri
        self.user = user
        self.database = database

        # Initialize async driver
        self.driver: AsyncDriver = AsyncGraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_pool_size=max_connection_pool_size,
            connection_timeout=connection_timeout,
        )

        logger.info(
            "neo4j_client_initialized",
            uri=uri,
            database=database,
            pool_size=max_connection_pool_size,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def health_check(self) -> bool:
        """Check Neo4j connection health."""
        try:
            async with self.driver.session(database=self.database) as session:
                result = await session.run("RETURN 1 AS health")
                record = await result.single()
                return record["health"] == 1
        except Exception as e:
            logger.error("neo4j_health_check_failed", error=str(e))
            return False

    async def execute_read(self, query: str, parameters: dict | None = None) -> list[dict]:
        """Execute read query."""
        async with self.driver.session(database=self.database) as session:
            result = await session.run(query, parameters or {})
            return [record.data() async for record in result]

    async def execute_write(self, query: str, parameters: dict | None = None) -> list[dict]:
        """Execute write query."""
        async with self.driver.session(database=self.database) as session:
            result = await session.run(query, parameters or {})
            return [record.data() async for record in result]

    async def close(self):
        """Close driver connection pool."""
        await self.driver.close()
        logger.info("neo4j_client_closed")
```

**Database Initialization Script:**
```python
# scripts/init_neo4j.py
"""Initialize Neo4j database schema for LightRAG."""

import asyncio
from neo4j import AsyncGraphDatabase
from src.core.config import settings

async def init_schema():
    """Initialize Neo4j indexes and constraints."""
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    async with driver.session(database=settings.neo4j_database) as session:
        # Create index on Entity.name for fast lookups
        await session.run("CREATE INDEX entity_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.name)")

        # Create index on Entity.type
        await session.run("CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.type)")

        # Create uniqueness constraint on Entity.id
        await session.run("CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE")

        # Create index on Relationship.type
        await session.run("CREATE INDEX relationship_type_idx IF NOT EXISTS FOR ()-[r:RELATED_TO]->() ON (r.type)")

        print("✅ Neo4j schema initialized successfully")

    await driver.close()

if __name__ == "__main__":
    asyncio.run(init_schema())
```

**Acceptance Criteria:**
- Neo4j container starts via `docker compose up`
- Health check passes within 30s
- Connection pool works with concurrent queries
- Indexes and constraints created successfully
- Backup/restore scripts functional
- 15+ integration tests passing

**Git Commit Message:**
```
feat(graph-rag): add Neo4j backend configuration with Docker Compose

Configures Neo4j 5.14 Community Edition as graph storage backend for LightRAG.
Includes connection pooling, health checks, and schema initialization.

Features:
- Docker Compose service with persistent volumes
- Neo4jClientWrapper with async driver
- Health check and retry logic
- Database schema initialization (indexes, constraints)
- Backup and restore scripts
- Integration tests with real Neo4j

Configuration:
- Image: neo4j:5.14-community
- Heap: 512MB-2GB, PageCache: 1GB
- Ports: 7474 (UI), 7687 (Bolt)
- Volumes: data, logs, import, plugins

Performance:
- Connection pool: 50 connections
- Health check: <5s
- Query timeout: 30s

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Dependencies:** Docker, docker-compose, neo4j==5.14.0 Python driver
**Risks:** Docker volume permissions on Windows, Neo4j memory configuration

---

### Feature 5.3: Entity & Relationship Extraction Pipeline

**Priority:** P1 (Core Feature)
**Story Points:** 10
**Effort:** 2 days

**Deliverables:**
- Entity extraction using LLM (Ollama llama3.2)
- Relationship extraction from entity co-occurrences
- Structured entity/relationship models (Pydantic)
- Graph construction from extracted entities
- Batch extraction pipeline for document corpus
- Unit tests for extraction logic (25+ tests)
- Integration test for end-to-end extraction

**Technical Tasks:**
1. Implement entity extraction in `src/components/graph_rag/extraction.py`:
   - LLM prompt for entity identification
   - Entity type classification (Person, Organization, Location, etc.)
   - Entity property extraction (description, aliases, etc.)
2. Implement relationship extraction:
   - Co-occurrence analysis within sentences/paragraphs
   - Relationship type classification (WORKS_AT, LOCATED_IN, etc.)
   - Relationship strength/confidence scoring
3. Create extraction pipeline:
   - Batch processing for document corpus
   - Progress tracking and error handling
   - Incremental extraction (only new documents)
4. Integrate with LightRAG graph construction
5. Write unit tests with mocked LLM responses
6. Write integration test with real Ollama + Neo4j

**Entity Extraction Prompt:**
```python
# src/components/graph_rag/prompts.py
ENTITY_EXTRACTION_PROMPT = """
Extract entities from the following text. For each entity, identify:
1. Entity name (exact string from text)
2. Entity type (Person, Organization, Location, Event, Concept, Technology, etc.)
3. Short description (1 sentence)

Text:
{text}

Return entities as JSON array:
[
  {{"name": "Entity Name", "type": "Type", "description": "Description"}},
  ...
]

Extract all significant entities. Be comprehensive but avoid duplicates.
"""

RELATIONSHIP_EXTRACTION_PROMPT = """
Extract relationships between entities from the following text.

Entities:
{entities}

Text:
{text}

For each relationship, identify:
1. Source entity (from list above)
2. Target entity (from list above)
3. Relationship type (WORKS_AT, KNOWS, LOCATED_IN, USES, CREATES, etc.)
4. Description (1 sentence explaining the relationship)

Return relationships as JSON array:
[
  {{"source": "Entity1", "target": "Entity2", "type": "RELATIONSHIP_TYPE", "description": "Description"}},
  ...
]

Only extract relationships explicitly stated or strongly implied in the text.
"""
```

**Extraction Pipeline:**
```python
# src/components/graph_rag/extraction.py
from pydantic import BaseModel, Field
from ollama import AsyncClient
import structlog

logger = structlog.get_logger(__name__)

class Entity(BaseModel):
    """Extracted entity."""
    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type (Person, Organization, etc.)")
    description: str = Field(..., description="Entity description")
    source_document: str | None = Field(default=None, description="Source document ID")

class Relationship(BaseModel):
    """Extracted relationship between entities."""
    source: str = Field(..., description="Source entity name")
    target: str = Field(..., description="Target entity name")
    type: str = Field(..., description="Relationship type (WORKS_AT, KNOWS, etc.)")
    description: str = Field(..., description="Relationship description")
    source_document: str | None = Field(default=None, description="Source document ID")

class ExtractionPipeline:
    """Entity and relationship extraction pipeline."""

    def __init__(self, llm_model: str, ollama_base_url: str):
        self.llm_model = llm_model
        self.client = AsyncClient(host=ollama_base_url)

    async def extract_entities(self, text: str, document_id: str | None = None) -> list[Entity]:
        """Extract entities from text using LLM."""
        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)

        response = await self.client.generate(
            model=self.llm_model,
            prompt=prompt,
            options={"temperature": 0.1, "num_predict": 2048},
        )

        # Parse JSON response
        entities_data = self._parse_json_response(response["response"])

        # Create Entity objects
        entities = [
            Entity(**entity_dict, source_document=document_id)
            for entity_dict in entities_data
        ]

        logger.info(
            "entities_extracted",
            count=len(entities),
            document_id=document_id,
        )

        return entities

    async def extract_relationships(
        self,
        text: str,
        entities: list[Entity],
        document_id: str | None = None,
    ) -> list[Relationship]:
        """Extract relationships from text given entities."""
        entity_list = "\n".join([f"- {e.name} ({e.type})" for e in entities])
        prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(
            entities=entity_list,
            text=text,
        )

        response = await self.client.generate(
            model=self.llm_model,
            prompt=prompt,
            options={"temperature": 0.1, "num_predict": 2048},
        )

        # Parse JSON response
        relationships_data = self._parse_json_response(response["response"])

        # Create Relationship objects
        relationships = [
            Relationship(**rel_dict, source_document=document_id)
            for rel_dict in relationships_data
        ]

        logger.info(
            "relationships_extracted",
            count=len(relationships),
            document_id=document_id,
        )

        return relationships

    async def extract_from_document(self, document: str, document_id: str) -> tuple[list[Entity], list[Relationship]]:
        """Extract entities and relationships from document."""
        # Extract entities first
        entities = await self.extract_entities(document, document_id)

        # Extract relationships based on entities
        relationships = await self.extract_relationships(document, entities, document_id)

        return entities, relationships
```

**Acceptance Criteria:**
- Entity extraction identifies 10+ entity types
- Relationship extraction captures common relationship patterns
- JSON parsing handles LLM response variations
- Batch pipeline processes document corpus
- Incremental extraction works (only new docs)
- 25+ unit tests passing
- End-to-end integration test successful

**Git Commit Message:**
```
feat(graph-rag): implement entity and relationship extraction pipeline

Adds LLM-powered entity and relationship extraction for knowledge graph construction.
Supports batch processing and incremental updates.

Features:
- Entity extraction (10+ types: Person, Organization, Location, etc.)
- Relationship extraction (WORKS_AT, KNOWS, LOCATED_IN, etc.)
- Structured models (Pydantic Entity, Relationship)
- Batch extraction pipeline
- Incremental extraction (new documents only)
- Progress tracking and error handling

Components:
- src/components/graph_rag/extraction.py (500+ lines)
- src/components/graph_rag/prompts.py (extraction prompts)
- Ollama llama3.2:8b for entity/relationship identification

Performance:
- Entity extraction: ~2-3s per document
- Relationship extraction: ~2-3s per document
- Batch processing: ~5-6s per document total

Quality:
- Entity recall: ~85% (depends on text clarity)
- Relationship precision: ~80% (conservative extraction)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Dependencies:** Feature 5.1 (LightRAG wrapper), Ollama llama3.2:8b
**Risks:** LLM prompt engineering, JSON parsing errors, extraction quality

---

### Feature 5.4: Dual-Level Retrieval (Entities + Topics)

**Priority:** P1 (Core Feature)
**Story Points:** 8
**Effort:** 1.5 days

**Deliverables:**
- Local search (entity-level) implementation
- Global search (topic-level) implementation
- Hybrid search combining local + global
- Search result ranking and fusion
- API integration with search modes
- Unit tests for search modes (20+ tests)

**Technical Tasks:**
1. Implement local search in `src/components/graph_rag/search.py`:
   - Query entity detection (NER or LLM)
   - Graph traversal from query entities
   - Multi-hop relationship following (1-2 hops)
   - Result ranking by relevance
2. Implement global search:
   - Topic/community detection (Leiden algorithm via Neo4j)
   - High-level summary generation
   - Semantic similarity to query
3. Implement hybrid search:
   - Parallel local + global execution
   - Result fusion (RRF or weighted combination)
   - Deduplication and ranking
4. Add search API endpoints:
   - `POST /api/v1/graph/search` (local/global/hybrid modes)
5. Write unit tests for each search mode
6. Write integration test with real graph

**Search Modes:**

**Local Search (Entity-Level):**
- Finds specific entities and their relationships
- Good for: "What companies does John work for?" (entity-centric)
- Approach:
  1. Detect entities in query ("John")
  2. Find matching nodes in graph
  3. Traverse relationships (1-2 hops)
  4. Generate answer from subgraph context

**Global Search (Topic-Level):**
- Finds high-level topics and summaries
- Good for: "What are the main themes in the corpus?" (topic-centric)
- Approach:
  1. Detect query topic/intent
  2. Match to community summaries
  3. Retrieve relevant topic clusters
  4. Generate answer from summaries

**Hybrid Search:**
- Combines local + global for comprehensive results
- Good for: Complex queries needing both detail and context
- Approach:
  1. Run local and global in parallel
  2. Fuse results with RRF
  3. Generate answer from combined context

**Implementation:**
```python
# src/components/graph_rag/search.py
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)

class SearchMode(str, Enum):
    """Graph search modes."""
    LOCAL = "local"    # Entity-level search
    GLOBAL = "global"  # Topic-level search
    HYBRID = "hybrid"  # Combined local + global

class GraphSearch:
    """Dual-level graph search (entities + topics)."""

    def __init__(self, lightrag_wrapper, neo4j_client):
        self.lightrag = lightrag_wrapper
        self.neo4j = neo4j_client

    async def search_local(self, query: str, max_hops: int = 2, top_k: int = 10) -> dict:
        """Local search: entity-level retrieval."""
        logger.info("graph_search_local", query=query[:100], max_hops=max_hops)

        # Use LightRAG local mode
        result = await self.lightrag.query(query, mode="local")

        return {
            "mode": "local",
            "query": query,
            "answer": result["answer"],
            "entities": result.get("entities", []),
            "relationships": result.get("relationships", []),
            "context": result.get("context", ""),
        }

    async def search_global(self, query: str, top_k: int = 5) -> dict:
        """Global search: topic-level retrieval."""
        logger.info("graph_search_global", query=query[:100])

        # Use LightRAG global mode
        result = await self.lightrag.query(query, mode="global")

        return {
            "mode": "global",
            "query": query,
            "answer": result["answer"],
            "topics": result.get("topics", []),
            "summaries": result.get("summaries", []),
            "context": result.get("context", ""),
        }

    async def search_hybrid(self, query: str, top_k: int = 10) -> dict:
        """Hybrid search: combined local + global."""
        logger.info("graph_search_hybrid", query=query[:100])

        # Use LightRAG hybrid mode
        result = await self.lightrag.query(query, mode="hybrid")

        return {
            "mode": "hybrid",
            "query": query,
            "answer": result["answer"],
            "entities": result.get("entities", []),
            "relationships": result.get("relationships", []),
            "topics": result.get("topics", []),
            "context": result.get("context", ""),
        }

    async def search(self, query: str, mode: SearchMode = SearchMode.HYBRID, top_k: int = 10) -> dict:
        """Unified search interface."""
        if mode == SearchMode.LOCAL:
            return await self.search_local(query, top_k=top_k)
        elif mode == SearchMode.GLOBAL:
            return await self.search_global(query, top_k=top_k)
        else:  # HYBRID
            return await self.search_hybrid(query, top_k=top_k)
```

**API Endpoint:**
```python
# src/api/v1/graph.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/graph", tags=["Graph Retrieval"])

class GraphSearchRequest(BaseModel):
    """Graph search request."""
    query: str = Field(..., description="Search query", min_length=1)
    mode: str = Field(default="hybrid", description="Search mode (local/global/hybrid)")
    top_k: int = Field(default=10, description="Number of results", ge=1, le=50)
    max_hops: int = Field(default=2, description="Max graph traversal hops (local mode)", ge=1, le=3)

class GraphSearchResponse(BaseModel):
    """Graph search response."""
    query: str
    mode: str
    answer: str
    entities: list[dict] = []
    relationships: list[dict] = []
    topics: list[dict] = []
    context: str
    metadata: dict

@router.post("/search", response_model=GraphSearchResponse)
async def search_graph(request: GraphSearchRequest):
    """Search knowledge graph with dual-level retrieval."""
    # Implementation in Sprint 5
    pass
```

**Acceptance Criteria:**
- Local search retrieves entity-specific results
- Global search retrieves topic-level summaries
- Hybrid search combines both effectively
- Search completes in <500ms (p95)
- API endpoint functional with all modes
- 20+ unit tests passing

**Git Commit Message:**
```
feat(graph-rag): implement dual-level retrieval (entities + topics)

Adds local (entity-level) and global (topic-level) graph search modes
with hybrid combination for comprehensive retrieval.

Features:
- Local search: Entity-level retrieval with graph traversal
- Global search: Topic-level retrieval with community summaries
- Hybrid search: Combined local + global with result fusion
- Configurable search parameters (mode, top_k, max_hops)
- API endpoint: POST /api/v1/graph/search

Components:
- src/components/graph_rag/search.py (GraphSearch class)
- src/api/v1/graph.py (API endpoints)
- Pydantic models for requests/responses

Performance:
- Local search: <300ms (entity lookup + 1-2 hop traversal)
- Global search: <400ms (topic matching + summary retrieval)
- Hybrid search: <500ms (parallel execution)

Quality:
- Entity retrieval precision: ~85%
- Topic coverage: ~90% of query intent

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Dependencies:** Feature 5.1 (LightRAG), Feature 5.3 (Extraction)
**Risks:** Query entity detection accuracy, community detection quality

---

### Feature 5.5: Graph Query Agent (LangGraph Integration)

**Priority:** P0 (Required for Sprint 4 integration)
**Story Points:** 6
**Effort:** 1 day

**Deliverables:**
- GraphQueryAgent class extending BaseAgent
- Integration with LangGraph coordinator
- GRAPH intent routing handler
- State management for graph results
- Error handling and fallback logic
- Unit tests for agent (15+ tests)
- Integration test with coordinator

**Technical Tasks:**
1. Create `src/agents/graph_query_agent.py`:
   - Extend BaseAgent from Sprint 4
   - Implement `process()` method for GRAPH intent
   - Call GraphSearch with appropriate mode
   - Format results for coordinator
2. Integrate with LangGraph coordinator:
   - Add graph_query node to graph
   - Add conditional edge from router to graph_query
   - Update state schema to include graph results
3. Add error handling:
   - Retry logic for transient failures
   - Fallback to vector search if graph unavailable
   - Graceful degradation
4. Write unit tests with mocked dependencies
5. Write integration test with real coordinator

**Graph Query Agent:**
```python
# src/agents/graph_query_agent.py
from src.agents.base_agent import BaseAgent
from src.components.graph_rag.search import GraphSearch, SearchMode
from src.agents.state import AgentState
import structlog

logger = structlog.get_logger(__name__)

class GraphQueryAgent(BaseAgent):
    """Agent for graph-based knowledge retrieval.

    Handles GRAPH intent from router, performs dual-level graph search,
    and returns structured results.
    """

    def __init__(self, graph_search: GraphSearch):
        super().__init__(name="graph_query_agent")
        self.graph_search = graph_search

    async def process(self, state: AgentState) -> AgentState:
        """Process GRAPH intent query.

        Args:
            state: Current agent state with query and intent

        Returns:
            Updated state with graph results
        """
        query = state.query

        logger.info(
            "graph_query_agent_processing",
            query=query[:100],
            intent=state.intent,
        )

        try:
            # Determine search mode from query complexity
            # Simple queries → local, complex queries → hybrid
            mode = self._select_search_mode(query)

            # Execute graph search
            result = await self.graph_search.search(
                query=query,
                mode=mode,
                top_k=state.config.get("top_k", 10),
            )

            # Update state with results
            state.graph_results = result
            state.retrieved_contexts.extend([
                {
                    "text": result["answer"],
                    "source": "graph_search",
                    "mode": result["mode"],
                    "entities": result.get("entities", []),
                    "relationships": result.get("relationships", []),
                }
            ])

            # Update metadata
            state.metadata["graph_search_mode"] = mode.value
            state.metadata["entities_found"] = len(result.get("entities", []))
            state.metadata["agent_path"].append("graph_query")

            logger.info(
                "graph_query_agent_complete",
                query=query[:100],
                mode=mode.value,
                entities=len(result.get("entities", [])),
            )

            return state

        except Exception as e:
            logger.error(
                "graph_query_agent_error",
                query=query[:100],
                error=str(e),
            )

            state.error = f"Graph query failed: {str(e)}"
            state.metadata["graph_query_error"] = str(e)

            # Fallback flag (coordinator can route to vector search)
            state.fallback_to_vector = True

            return state

    def _select_search_mode(self, query: str) -> SearchMode:
        """Select appropriate search mode based on query.

        Heuristic:
        - Short queries with entity names → LOCAL
        - Broad, conceptual queries → GLOBAL
        - Complex multi-part queries → HYBRID
        """
        # Simple heuristic (can be replaced with LLM classification)
        word_count = len(query.split())
        has_entity_indicators = any(
            indicator in query.lower()
            for indicator in ["who", "which company", "person", "organization"]
        )

        if word_count < 10 and has_entity_indicators:
            return SearchMode.LOCAL
        elif word_count > 15 or "and" in query.lower():
            return SearchMode.HYBRID
        else:
            return SearchMode.GLOBAL
```

**Coordinator Integration:**
```python
# src/agents/coordinator.py (update)
from src.agents.graph_query_agent import GraphQueryAgent

# In build_graph():
def build_graph(self):
    """Build LangGraph agent graph."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", self.router_node)
    graph.add_node("vector_search", self.vector_search_agent.process)
    graph.add_node("graph_query", self.graph_query_agent.process)  # NEW
    graph.add_node("generate", self.generation_node)

    # Add edges
    graph.add_edge(START, "router")

    # Conditional routing from router
    graph.add_conditional_edges(
        "router",
        self.route_to_agent,
        {
            "vector": "vector_search",
            "graph": "graph_query",  # NEW
            "hybrid": "vector_search",  # Sprint 6 will handle hybrid
            "memory": "vector_search",  # Fallback until Sprint 7
        },
    )

    # Connect to generation
    graph.add_edge("vector_search", "generate")
    graph.add_edge("graph_query", "generate")  # NEW

    graph.add_edge("generate", END)

    return graph.compile()
```

**Acceptance Criteria:**
- GraphQueryAgent handles GRAPH intent correctly
- Agent integrates with LangGraph coordinator
- State updates include graph results
- Error handling works with fallback
- 15+ unit tests passing
- Integration test with coordinator successful

**Git Commit Message:**
```
feat(agents): add Graph Query Agent for LangGraph integration

Implements GraphQueryAgent to handle GRAPH intent routing from Sprint 4.
Integrates dual-level graph search with LangGraph orchestration.

Features:
- GraphQueryAgent extending BaseAgent
- GRAPH intent handler (local/global/hybrid search)
- LangGraph coordinator integration
- State management for graph results
- Error handling with fallback to vector search
- Automatic search mode selection (heuristic)

Components:
- src/agents/graph_query_agent.py (250+ lines)
- Updated coordinator with graph_query node
- State schema updates for graph results

Integration:
- Router → GRAPH intent → graph_query node
- graph_query → generate node
- Fallback: graph error → vector_search

Performance:
- Graph query: <500ms (p95)
- Fallback overhead: <50ms

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Dependencies:** Feature 5.4 (GraphSearch), Sprint 4 (Coordinator)
**Risks:** State schema conflicts, fallback logic complexity

---

### Feature 5.6: Incremental Graph Updates

**Priority:** P2 (Nice to Have)
**Story Points:** 5
**Effort:** 1 day

**Deliverables:**
- Incremental document insertion (no full rebuild)
- Graph diff detection (new vs. existing entities)
- Entity merging and conflict resolution
- Update API endpoint
- Unit tests for incremental updates (15+ tests)

**Technical Tasks:**
1. Implement incremental insertion in `src/components/graph_rag/incremental.py`:
   - Track indexed documents (metadata in Neo4j)
   - Detect new documents vs. updates
   - Extract entities/relationships only from new docs
   - Merge entities (handle duplicates, aliases)
2. Implement entity resolution:
   - Fuzzy matching for entity deduplication
   - Confidence scoring for merges
   - Manual override capability
3. Add update API endpoint:
   - `POST /api/v1/graph/update` (add new documents)
   - `POST /api/v1/graph/rebuild` (full rebuild)
4. Write unit tests for update logic
5. Write integration test with document corpus

**Incremental Update Pipeline:**
```python
# src/components/graph_rag/incremental.py
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)

class IncrementalGraphUpdater:
    """Incremental knowledge graph updates."""

    def __init__(self, lightrag_wrapper, extraction_pipeline):
        self.lightrag = lightrag_wrapper
        self.extractor = extraction_pipeline

    async def get_indexed_documents(self) -> set[str]:
        """Get list of already indexed document IDs from graph metadata."""
        # Query Neo4j for document IDs
        query = """
        MATCH (d:Document)
        RETURN d.id AS doc_id
        """
        results = await self.lightrag.neo4j_client.execute_read(query)
        return {r["doc_id"] for r in results}

    async def insert_new_documents(self, documents: list[dict]) -> dict:
        """Insert only new documents into graph.

        Args:
            documents: List of {id: str, text: str, metadata: dict}

        Returns:
            Update statistics
        """
        # Get already indexed documents
        indexed_docs = await self.get_indexed_documents()

        # Filter out already indexed documents
        new_docs = [
            doc for doc in documents
            if doc["id"] not in indexed_docs
        ]

        logger.info(
            "incremental_update_started",
            total_docs=len(documents),
            indexed_docs=len(indexed_docs),
            new_docs=len(new_docs),
        )

        if not new_docs:
            return {
                "status": "no_updates",
                "total_docs": len(documents),
                "new_docs": 0,
                "updated_entities": 0,
            }

        # Extract entities and relationships from new documents
        entities_added = 0
        relationships_added = 0

        for doc in new_docs:
            # Extract
            entities, relationships = await self.extractor.extract_from_document(
                doc["text"],
                doc["id"],
            )

            # Insert into LightRAG graph
            await self.lightrag.insert_entities(entities)
            await self.lightrag.insert_relationships(relationships)

            # Mark document as indexed
            await self._mark_document_indexed(doc["id"], doc.get("metadata", {}))

            entities_added += len(entities)
            relationships_added += len(relationships)

        logger.info(
            "incremental_update_complete",
            new_docs=len(new_docs),
            entities_added=entities_added,
            relationships_added=relationships_added,
        )

        return {
            "status": "success",
            "total_docs": len(documents),
            "new_docs": len(new_docs),
            "entities_added": entities_added,
            "relationships_added": relationships_added,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _mark_document_indexed(self, doc_id: str, metadata: dict):
        """Mark document as indexed in Neo4j."""
        query = """
        MERGE (d:Document {id: $doc_id})
        SET d.indexed_at = $timestamp,
            d.metadata = $metadata
        """
        await self.lightrag.neo4j_client.execute_write(
            query,
            {
                "doc_id": doc_id,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata,
            },
        )
```

**API Endpoint:**
```python
# src/api/v1/graph.py (add endpoint)
@router.post("/update")
async def update_graph(documents: list[dict]):
    """Incrementally update graph with new documents."""
    updater = IncrementalGraphUpdater(lightrag_wrapper, extraction_pipeline)
    result = await updater.insert_new_documents(documents)
    return result
```

**Acceptance Criteria:**
- Incremental updates work without full rebuild
- Already indexed documents are skipped
- Entity deduplication prevents duplicates
- Update API endpoint functional
- Performance: 10x faster than full rebuild for small updates
- 15+ unit tests passing

**Git Commit Message:**
```
feat(graph-rag): implement incremental graph updates

Adds incremental document insertion to knowledge graph without full rebuild.
Includes entity deduplication and conflict resolution.

Features:
- Incremental document insertion (skip already indexed)
- Graph diff detection (new vs. existing entities)
- Entity merging with fuzzy matching
- Update API endpoint: POST /api/v1/graph/update
- Performance optimization (10x faster for small updates)

Components:
- src/components/graph_rag/incremental.py (IncrementalGraphUpdater)
- Updated API with update endpoint
- Document tracking in Neo4j metadata

Performance:
- Incremental update: ~5-6s per new document
- Full rebuild: ~60s for 100 documents
- Incremental (10 new docs): ~60s vs. ~600s full rebuild

Quality:
- Entity deduplication: 95%+ accuracy
- No duplicates introduced

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Dependencies:** Feature 5.3 (Extraction), Feature 5.1 (LightRAG)
**Risks:** Entity resolution accuracy, merge conflicts

---

## Sprint 5 Summary

### Feature Overview

| Feature | Priority | Story Points | Effort | Dependencies |
|---------|----------|--------------|--------|--------------|
| 5.1: LightRAG Core | P0 | 8 | 1.5 days | Neo4j, Ollama |
| 5.2: Neo4j Backend | P0 | 5 | 1 day | Docker |
| 5.3: Entity Extraction | P1 | 10 | 2 days | 5.1, Ollama |
| 5.4: Dual-Level Search | P1 | 8 | 1.5 days | 5.1, 5.3 |
| 5.5: Graph Query Agent | P0 | 6 | 1 day | 5.4, Sprint 4 |
| 5.6: Incremental Updates | P2 | 5 | 1 day | 5.1, 5.3 |
| **TOTAL** | | **42** | **8 days** | |

### Sprint Burn-Down Plan

```
Day 1: Feature 5.2 (Neo4j Backend) + Start 5.1 (LightRAG Core)
Day 2: Complete 5.1 + Start 5.3 (Entity Extraction)
Day 3: Complete 5.3
Day 4: Feature 5.4 (Dual-Level Search)
Day 5: Feature 5.5 (Graph Query Agent)
Day 6: (Optional) Feature 5.6 (Incremental Updates) or testing/docs
```

### Dependencies Graph

```
Sprint 4 ✅ (Router with GRAPH intent)
  └─> 5.2: Neo4j Backend
        └─> 5.1: LightRAG Core
              ├─> 5.3: Entity Extraction
              │     ├─> 5.4: Dual-Level Search
              │     │     └─> 5.5: Graph Query Agent
              │     └─> 5.6: Incremental Updates
              └─> 5.4: Dual-Level Search (alternative path)
```

---

## Technical Architecture

### System Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────────┐
│                         AEGIS RAG - Sprint 5                           │
├───────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    LangGraph Coordinator                         │  │
│  │  ┌──────────┐   ┌──────────────┐   ┌──────────────────────┐    │  │
│  │  │  Router  │──>│ QueryIntent  │──>│ Conditional Routing │    │  │
│  │  └──────────┘   │  Classifier  │   └──────────────────────┘    │  │
│  │                 └──────────────┘             │                  │  │
│  │                       (Sprint 4)             │                  │  │
│  │                                              │                  │  │
│  │           ┌──────────────┬───────────────────┼────────────────┐ │  │
│  │           │              │                   │                │ │  │
│  │           ▼              ▼                   ▼                ▼ │  │
│  │   ┌──────────────┐ ┌──────────┐      ┌──────────┐  ┌────────┐ │  │
│  │   │Vector Search │ │  Graph   │      │  Memory  │  │Fallback│ │  │
│  │   │    Agent     │ │  Query   │◄─NEW─┤  Agent   │  │        │ │  │
│  │   │  (Sprint 2)  │ │  Agent   │      │(Sprint 7)│  │        │ │  │
│  │   └──────────────┘ └──────────┘      └──────────┘  └────────┘ │  │
│  │           │              │                   │                │ │  │
│  │           └──────────────┴───────────────────┴────────────────┘ │  │
│  │                                 │                                │  │
│  │                                 ▼                                │  │
│  │                        ┌─────────────────┐                       │  │
│  │                        │   Generation    │                       │  │
│  │                        │      Node       │                       │  │
│  │                        └─────────────────┘                       │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
├───────────────────────────────────────────────────────────────────────┤
│                     Graph Retrieval Components (NEW)                   │
├───────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                      LightRAG Wrapper                            │  │
│  │  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐   │  │
│  │  │ Graph Query  │  │    Dual-Level   │  │   Incremental    │   │  │
│  │  │   Engine     │  │    Retrieval    │  │     Updates      │   │  │
│  │  └──────────────┘  └─────────────────┘  └──────────────────┘   │  │
│  │         │                   │                     │              │  │
│  │         │                   │                     │              │  │
│  │         ▼                   ▼                     ▼              │  │
│  │  ┌──────────────────────────────────────────────────────────┐   │  │
│  │  │              LightRAG Core Library                       │   │  │
│  │  │   ┌────────────┐  ┌────────────┐  ┌────────────────┐    │   │  │
│  │  │   │   Local    │  │   Global   │  │     Hybrid     │    │   │  │
│  │  │   │  Search    │  │   Search   │  │     Search     │    │   │  │
│  │  │   │ (Entities) │  │  (Topics)  │  │ (Combined)     │    │   │  │
│  │  │   └────────────┘  └────────────┘  └────────────────┘    │   │  │
│  │  └──────────────────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │              Entity/Relationship Extraction Pipeline             │  │
│  │  ┌──────────────────┐        ┌─────────────────────────────┐    │  │
│  │  │  Ollama LLM      │───────>│  Entity Extraction          │    │  │
│  │  │  llama3.2:8b     │        │  - Person, Org, Location... │    │  │
│  │  └──────────────────┘        └─────────────────────────────┘    │  │
│  │           │                              │                       │  │
│  │           │                              ▼                       │  │
│  │           │                   ┌─────────────────────────────┐   │  │
│  │           └──────────────────>│  Relationship Extraction    │   │  │
│  │                                │  - WORKS_AT, KNOWS, etc.    │   │  │
│  │                                └─────────────────────────────┘   │  │
│  │                                           │                      │  │
│  │                                           ▼                      │  │
│  │                                ┌──────────────────────┐          │  │
│  │                                │  Graph Construction  │          │  │
│  │                                │  - Nodes (Entities)  │          │  │
│  │                                │  - Edges (Relations) │          │  │
│  │                                └──────────────────────┘          │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
├───────────────────────────────────────────────────────────────────────┤
│                        Neo4j Knowledge Graph                           │
├───────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                     Neo4j Graph Database                         │  │
│  │                                                                   │  │
│  │  Nodes:                        Relationships:                    │  │
│  │  ┌─────────────┐               ┌────────────────┐               │  │
│  │  │   Entity    │──WORKS_AT────>│ Organization   │               │  │
│  │  │   (Person)  │               └────────────────┘               │  │
│  │  │  - name     │                                                │  │
│  │  │  - type     │──LOCATED_IN──>┌────────────────┐               │  │
│  │  │  - desc     │               │   Location     │               │  │
│  │  └─────────────┘               └────────────────┘               │  │
│  │        │                                                         │  │
│  │        │                                                         │  │
│  │        └──KNOWS──────>┌─────────────┐                           │  │
│  │                       │   Entity    │                           │  │
│  │                       │   (Person)  │                           │  │
│  │                       └─────────────┘                           │  │
│  │                                                                  │  │
│  │  Indexes:                                                        │  │
│  │  - Entity.name (fast lookups)                                   │  │
│  │  - Entity.type (filtering)                                      │  │
│  │  - Entity.id (uniqueness)                                       │  │
│  │                                                                  │  │
│  │  Storage:                                                        │  │
│  │  - Persistent volumes (Docker)                                  │  │
│  │  - Heap: 512MB-2GB                                              │  │
│  │  - PageCache: 1GB                                               │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
├───────────────────────────────────────────────────────────────────────┤
│                         LLM & Embeddings (Ollama)                      │
├───────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                      Ollama Server                               │  │
│  │                                                                   │  │
│  │  Models:                                                         │  │
│  │  ┌──────────────────────┐        ┌─────────────────────────┐    │  │
│  │  │  llama3.2:8b         │        │  nomic-embed-text       │    │  │
│  │  │  (Entity Extraction) │        │  (Graph Embeddings)     │    │  │
│  │  │  - Temperature: 0.1  │        │  - Dimension: 768       │    │  │
│  │  │  - Max tokens: 4096  │        │  - Context: 8192 tokens │    │  │
│  │  └──────────────────────┘        └─────────────────────────┘    │  │
│  │                                                                  │  │
│  │  Uses:                                                           │  │
│  │  - Entity/relationship extraction from text                     │  │
│  │  - Graph query answer generation                                │  │
│  │  - Topic/community summarization                                │  │
│  │  - Entity embeddings for similarity search                      │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└───────────────────────────────────────────────────────────────────────┘
```

### Data Flow: Document → Knowledge Graph

```
1. Document Ingestion
   └─> Documents (PDF, TXT, MD, etc.)
        └─> LlamaIndex SimpleDirectoryReader
             └─> Parsed text chunks

2. Entity Extraction (Feature 5.3)
   └─> Text chunks
        └─> Ollama LLM (llama3.2:8b) + Extraction Prompts
             └─> Entities:
                  - Person, Organization, Location, Technology, Concept, etc.
                  - Properties: name, type, description

3. Relationship Extraction (Feature 5.3)
   └─> Text chunks + Extracted entities
        └─> Ollama LLM (llama3.2:8b) + Relationship Prompts
             └─> Relationships:
                  - WORKS_AT, KNOWS, LOCATED_IN, USES, CREATES, etc.
                  - Properties: type, description, confidence

4. Graph Construction (Feature 5.1)
   └─> Entities + Relationships
        └─> LightRAG Core
             └─> Neo4j Graph Database
                  ├─> Nodes (Entities) with embeddings
                  ├─> Edges (Relationships) with properties
                  └─> Community detection (Leiden algorithm)

5. Indexing (Feature 5.2)
   └─> Neo4j Graph
        └─> Indexes:
             ├─> Entity.name (B-tree index)
             ├─> Entity.type (B-tree index)
             └─> Entity.id (Unique constraint)

6. Ready for Query (Feature 5.4)
   └─> Knowledge Graph
        ├─> Local Search (entity-level)
        ├─> Global Search (topic-level)
        └─> Hybrid Search (combined)
```

### Query Flow: User Query → Graph Answer

```
1. User Query
   └─> "What companies has John Smith worked for?"

2. Router (Sprint 4)
   └─> Intent Classification
        └─> QueryIntent.GRAPH (detected entity-centric query)

3. Graph Query Agent (Feature 5.5)
   └─> Receive GRAPH intent
        └─> Select search mode: LOCAL (entity-focused)

4. Dual-Level Search (Feature 5.4)
   └─> Local Search:
        ├─> Detect entities in query: ["John Smith"]
        ├─> Find matching nodes in graph:
        │    └─> MATCH (p:Person {name: "John Smith"})-[r:WORKS_AT]->(o:Organization)
        ├─> Traverse relationships (1-2 hops)
        └─> Retrieve subgraph context

5. LLM Answer Generation
   └─> Graph context (entities + relationships)
        └─> Ollama LLM (llama3.2:8b)
             └─> Generated answer:
                  "John Smith has worked for Microsoft (2015-2020) and Google (2020-present)."

6. State Update
   └─> AgentState.graph_results = {answer, entities, relationships}
        └─> Return to Coordinator
             └─> Generation Node (final formatting)

7. Response to User
   └─> Structured response with:
        ├─> answer: "John Smith has worked for..."
        ├─> entities: [Person(John Smith), Org(Microsoft), Org(Google)]
        ├─> relationships: [WORKS_AT(John→Microsoft), WORKS_AT(John→Google)]
        └─> metadata: {mode: "local", entities_found: 3}
```

---

## Dependencies & Prerequisites

### External Dependencies

**Python Packages (New for Sprint 5):**
```toml
[tool.poetry.dependencies]
# Sprint 5: LightRAG & Graph RAG
lightrag-hku = "^0.2.0"  # Official LightRAG package (PyPI)
# neo4j = "^5.14.0"  # Already installed in Sprint 2 (health checks)
networkx = "^3.3"  # Graph algorithms (LightRAG dependency)
graspologic = "^3.4.1"  # Community detection (LightRAG dependency)
```

**System Requirements:**
- Docker & Docker Compose (for Neo4j)
- Neo4j 5.14 Community Edition
- Ollama server with models:
  - llama3.2:8b (entity extraction)
  - nomic-embed-text (embeddings)
- Minimum 8GB RAM (Neo4j + Ollama)
- 10GB disk space (Neo4j data + models)

### Infrastructure Setup

**Neo4j Setup:**
```bash
# Pull Neo4j image
docker pull neo4j:5.14-community

# Start services
docker compose up -d neo4j

# Initialize schema
python scripts/init_neo4j.py

# Verify health
curl http://localhost:7474
```

**Ollama Models:**
```bash
# Ensure models are available
ollama pull llama3.2:8b
ollama pull nomic-embed-text

# Verify
ollama list
```

### Sprint 4 Integration Points

**Required from Sprint 4:**
- Router with QueryIntent.GRAPH support
- BaseAgent class for agent implementation
- AgentState schema for state management
- LangGraph coordinator with conditional routing
- State persistence (checkpointer)

**Integration Checklist:**
- [ ] QueryIntent.GRAPH enum value exists
- [ ] Router can classify GRAPH intent
- [ ] Coordinator can route to graph_query node
- [ ] AgentState has fields for graph results
- [ ] Error handling supports fallback routing

---

## Success Criteria & Acceptance Tests

### Functional Requirements

**Feature 5.1: LightRAG Core**
- [ ] LightRAG initializes with Ollama LLM + embeddings
- [ ] Graph construction works for test corpus (10+ documents)
- [ ] Neo4j connection established and verified
- [ ] Query modes (local/global/hybrid) return results
- [ ] 20+ unit tests passing

**Feature 5.2: Neo4j Backend**
- [ ] Neo4j container starts via `docker compose up`
- [ ] Health check passes within 30s
- [ ] Connection pool handles 10+ concurrent queries
- [ ] Indexes and constraints created successfully
- [ ] 15+ integration tests passing

**Feature 5.3: Entity Extraction**
- [ ] Entity extraction identifies 10+ entity types
- [ ] Relationship extraction captures common patterns
- [ ] JSON parsing handles LLM response variations
- [ ] Batch pipeline processes test corpus (100+ documents)
- [ ] 25+ unit tests passing

**Feature 5.4: Dual-Level Search**
- [ ] Local search retrieves entity-specific results
- [ ] Global search retrieves topic-level summaries
- [ ] Hybrid search combines both effectively
- [ ] Search completes in <500ms (p95)
- [ ] 20+ unit tests passing

**Feature 5.5: Graph Query Agent**
- [ ] Agent handles GRAPH intent correctly
- [ ] Integration with LangGraph coordinator successful
- [ ] State updates include graph results
- [ ] Error handling with fallback works
- [ ] 15+ unit tests passing

**Feature 5.6: Incremental Updates (Optional)**
- [ ] Incremental updates work without full rebuild
- [ ] Already indexed documents are skipped
- [ ] Entity deduplication prevents duplicates
- [ ] 10x faster than full rebuild for small updates
- [ ] 15+ unit tests passing

### Quality Requirements

**Test Coverage:**
- [ ] >80% code coverage (unit + integration)
- [ ] All P0 features have integration tests
- [ ] Error paths covered by tests
- [ ] Performance benchmarks in place

**Performance Benchmarks:**
| Operation | Target | Acceptance |
|-----------|--------|------------|
| Entity extraction | <3s per document | <5s per document |
| Graph construction | <60s for 100 docs | <90s for 100 docs |
| Local search | <300ms p95 | <500ms p95 |
| Global search | <400ms p95 | <600ms p95 |
| Hybrid search | <500ms p95 | <800ms p95 |
| Incremental update | <6s per new doc | <10s per new doc |

**Quality Metrics:**
| Metric | Target | Minimum |
|--------|--------|---------|
| Entity recall | >85% | >75% |
| Relationship precision | >80% | >70% |
| Entity deduplication | >95% | >90% |
| GRAPH routing accuracy | >85% | >75% |
| Graph query relevance | >80% | >70% |

### End-to-End Acceptance Tests

**Test 1: Document to Graph Construction**
```python
async def test_e2e_graph_construction():
    """Test full pipeline: document → entities → graph → query."""
    # 1. Ingest documents
    docs = load_test_documents("data/test_corpus/small")  # 10 documents

    # 2. Extract entities and relationships
    extractor = ExtractionPipeline()
    entities, relationships = await extractor.extract_from_documents(docs)

    assert len(entities) >= 50, "Should extract 50+ entities"
    assert len(relationships) >= 30, "Should extract 30+ relationships"

    # 3. Build graph
    lightrag = LightRAGWrapper()
    await lightrag.insert_entities(entities)
    await lightrag.insert_relationships(relationships)

    # 4. Verify graph in Neo4j
    neo4j = Neo4jClientWrapper()
    entity_count = await neo4j.execute_read("MATCH (e:Entity) RETURN count(e) AS count")

    assert entity_count[0]["count"] >= 50, "Graph should have 50+ entities"

    # 5. Query graph
    result = await lightrag.query("What entities are related to machine learning?", mode="local")

    assert result["answer"], "Should generate answer"
    assert len(result.get("entities", [])) > 0, "Should retrieve entities"
```

**Test 2: GRAPH Intent Routing**
```python
async def test_e2e_graph_intent_routing():
    """Test Sprint 4 router → Graph Query Agent flow."""
    # 1. Create query with GRAPH intent
    query = "What companies has the person in document 5 worked for?"

    # 2. Route via coordinator
    coordinator = AgentCoordinator()
    state = AgentState(query=query)

    result_state = await coordinator.process(state)

    # 3. Verify routing
    assert state.intent == "graph", "Router should classify as GRAPH"
    assert "graph_query" in state.metadata["agent_path"], "Should route to graph_query agent"

    # 4. Verify results
    assert result_state.graph_results, "Should have graph results"
    assert result_state.graph_results["mode"] in ["local", "global", "hybrid"]
    assert result_state.graph_results["answer"], "Should generate answer"
```

**Test 3: Incremental Updates**
```python
async def test_e2e_incremental_update():
    """Test incremental graph updates without rebuild."""
    # 1. Build initial graph
    initial_docs = load_test_documents("data/test_corpus/batch1")  # 50 docs
    lightrag = LightRAGWrapper()
    await lightrag.insert_documents(initial_docs)

    initial_entities = await get_entity_count()

    # 2. Add new documents incrementally
    new_docs = load_test_documents("data/test_corpus/batch2")  # 10 new docs
    updater = IncrementalGraphUpdater()
    result = await updater.insert_new_documents(new_docs)

    assert result["new_docs"] == 10, "Should identify 10 new docs"
    assert result["entities_added"] > 0, "Should add entities"

    # 3. Verify no duplicates
    final_entities = await get_entity_count()
    assert final_entities > initial_entities, "Entity count should increase"

    # 4. Verify re-insertion is idempotent
    result2 = await updater.insert_new_documents(new_docs)
    assert result2["new_docs"] == 0, "Should skip already indexed docs"
```

---

## Risk Assessment

### High Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LightRAG API instability | Medium | High | Pin to specific version (^0.2.0), add wrapper abstraction layer |
| Neo4j memory issues at scale | Medium | High | Configure heap (2GB max), implement pagination for large queries |
| Entity extraction quality | High | Medium | Fine-tune prompts, add human-in-the-loop validation for critical entities |
| JSON parsing errors from LLM | High | Medium | Robust parsing with fallback, retry logic, validation schemas |
| Sprint 4 integration conflicts | Low | High | Close coordination with Sprint 4 agent state schema, early integration testing |

### Medium Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Slow entity extraction | Medium | Medium | Batch processing, async execution, consider GPU for LLM |
| Neo4j Docker volume permissions (Windows) | Medium | Low | Document setup steps, provide troubleshooting guide |
| Community detection performance | Low | Medium | Use Neo4j GDS library, limit community size |
| Entity deduplication errors | Medium | Medium | Implement confidence scoring, manual review workflow |

### Low Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Ollama model availability | Low | Low | Pre-pull models in Docker init, fallback to smaller models |
| Graph query timeout | Low | Medium | Set query timeout (30s), implement query caching |
| Incremental update conflicts | Low | Low | Transaction-based updates, conflict resolution strategy |

---

## Timeline & Milestones

### Sprint Timeline

**Total Duration:** 6 working days (5 core + 1 buffer/optional)
**Target Dates:** TBD (after Sprint 4 completion)

### Daily Milestones

**Day 1: Infrastructure Setup**
- Morning: Feature 5.2 (Neo4j Backend) - Docker Compose, health checks
- Afternoon: Start Feature 5.1 (LightRAG Core) - Installation, basic config
- **Milestone:** Neo4j running, LightRAG installed

**Day 2: LightRAG Integration**
- Morning: Complete Feature 5.1 - Graph construction, query modes
- Afternoon: Start Feature 5.3 (Entity Extraction) - LLM prompts, extraction logic
- **Milestone:** LightRAG wrapper functional, 20+ tests passing

**Day 3: Entity Extraction**
- Morning: Complete Feature 5.3 - Relationship extraction, batch pipeline
- Afternoon: Integration test with real Ollama + Neo4j
- **Milestone:** Extraction pipeline complete, 25+ tests passing

**Day 4: Dual-Level Search**
- Morning: Feature 5.4 (Dual-Level Search) - Local + Global search
- Afternoon: Hybrid search, result fusion, API endpoint
- **Milestone:** All search modes functional, <500ms latency

**Day 5: Agent Integration**
- Morning: Feature 5.5 (Graph Query Agent) - Agent class, LangGraph integration
- Afternoon: Error handling, fallback logic, integration tests
- **Milestone:** GRAPH intent routing works end-to-end

**Day 6: Optional/Buffer**
- Option A: Feature 5.6 (Incremental Updates) - If time permits
- Option B: Testing, documentation, performance optimization
- Option C: Bug fixes, polish, extra test coverage
- **Milestone:** Sprint 5 complete, all P0/P1 features delivered

### Sprint Review & Retrospective

**Sprint Review (End of Day 6):**
- Demo: Live graph construction from document corpus
- Demo: GRAPH intent routing and dual-level search
- Demo: Entity extraction and graph visualization (Neo4j Browser)
- Metrics review: Performance, quality, test coverage

**Sprint Retrospective:**
- What went well? (e.g., LightRAG integration, Neo4j setup)
- What could be improved? (e.g., entity extraction quality, LLM prompting)
- Action items for Sprint 6

---

## Post-Sprint 5: Next Steps

### Sprint 6 Preview: Hybrid Vector-Graph Retrieval

**Goal:** Combine vector search (Sprint 2-3) with graph retrieval (Sprint 5) for optimal results.

**Planned Features:**
- Parallel vector + graph execution (LangGraph Send API)
- Reciprocal Rank Fusion (RRF) across retrieval types
- Multi-hop query expansion for graph reasoning
- Community detection for topic clustering (Leiden algorithm)
- Global vs. Local search mode selection logic
- Hybrid retrieval evaluation (RAGAS extended for graph)

**Dependencies:**
- Sprint 5 ✅ (Graph retrieval functional)
- Sprint 2-3 ✅ (Vector search functional)

### Sprint 7-8 Preview: Temporal Memory (Graphiti)

**Goal:** Add episodic and semantic memory layers with bi-temporal structure.

**Planned Features:**
- Graphiti integration with Neo4j backend
- Episodic subgraph (raw conversations)
- Semantic subgraph (extracted facts)
- Memory Agent for MEMORY intent
- Point-in-time query API
- 3-layer memory architecture (Redis + Qdrant + Graphiti)

---

## Documentation & Knowledge Transfer

### Documentation Deliverables

**Required Documentation:**
1. **SPRINT_5_IMPLEMENTATION_GUIDE.md** - Step-by-step implementation guide
2. **docs/examples/sprint5_examples.md** - Usage examples and code snippets
3. **SPRINT_5_SUMMARY.md** - Sprint completion summary (after sprint)
4. **SPRINT_5_COMPLETION_REPORT.md** - Detailed completion report (after sprint)

**API Documentation:**
- OpenAPI/Swagger spec updates for graph endpoints
- GraphQL schema (if applicable)
- Code examples for each feature

**Architecture Decision Records (ADRs):**
- ADR-010: LightRAG vs. Microsoft GraphRAG comparison
- ADR-011: Neo4j storage backend selection
- ADR-012: Entity extraction prompt engineering approach
- ADR-013: Dual-level search architecture

### Knowledge Transfer Plan

**For Developers:**
- LightRAG architecture overview
- Neo4j query patterns and best practices
- Entity extraction prompt design
- Graph query optimization techniques

**For Operations:**
- Neo4j deployment and configuration
- Backup and restore procedures
- Monitoring and alerting setup
- Troubleshooting common issues

---

## Sprint 5 Definition of Done

For each feature, the following criteria must be met:

- [ ] **Code Complete:** Implementation matches acceptance criteria
- [ ] **Unit Tests:** >80% coverage, all tests passing
- [ ] **Integration Tests:** End-to-end test with real dependencies (Neo4j, Ollama)
- [ ] **Code Review:** Self-review completed, no critical issues
- [ ] **Documentation:** Docstrings, API docs, usage examples
- [ ] **Performance:** Meets latency and quality benchmarks
- [ ] **Security:** Input validation, no new vulnerabilities (Bandit scan)
- [ ] **CI/CD:** All relevant CI jobs passing (9/11+)
- [ ] **Git Commit:** Follows commit message template
- [ ] **Manual Testing:** Tested via API/scripts with real data

---

## Appendix

### LightRAG Overview

**What is LightRAG?**
- Research paper: "LightRAG: Simple and Fast Retrieval-Augmented Generation" (HKU)
- Purpose: Graph-based RAG with dual-level retrieval
- Key features:
  - Entity and relationship extraction via LLM
  - Dual-level retrieval (local + global)
  - Neo4j/NetworkX backend support
  - Incremental graph updates

**LightRAG vs. Microsoft GraphRAG:**
| Feature | LightRAG | Microsoft GraphRAG |
|---------|----------|-------------------|
| Complexity | Simple, lightweight | Complex, heavyweight |
| Setup | Easy (pip install) | Complex (many dependencies) |
| Backend | Neo4j, NetworkX | Azure Cognitive Search |
| Community | Active (HKU research) | Microsoft-backed |
| Cost | Free (local) | Azure costs |
| **Decision** | ✅ **Selected for Sprint 5** | Deferred |

**Reason:** LightRAG aligns with AEGIS RAG's local-first, cost-free philosophy.

### Neo4j Cypher Query Examples

**Entity Lookup:**
```cypher
MATCH (e:Entity {name: "John Smith"})
RETURN e
```

**Relationship Traversal (1-hop):**
```cypher
MATCH (p:Person {name: "John Smith"})-[r:WORKS_AT]->(o:Organization)
RETURN p, r, o
```

**Multi-hop Query:**
```cypher
MATCH path = (p:Person {name: "John Smith"})-[*1..2]-(related)
RETURN path
```

**Community Detection (Leiden):**
```cypher
CALL gds.leiden.stream('myGraph')
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).name AS name, communityId
ORDER BY communityId
```

### Environment Variables

**New for Sprint 5:**
```bash
# LightRAG Configuration
LIGHTRAG_ENABLED=true
LIGHTRAG_WORKING_DIR=./data/lightrag
LIGHTRAG_LLM_MODEL=llama3.2:8b
LIGHTRAG_EMBEDDING_MODEL=nomic-embed-text

# Neo4j Configuration (Sprint 5: Graph Storage)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password-here
NEO4J_DATABASE=neo4j
```

---

**Ready to Start Sprint 5?** ✅

**Prerequisites Checklist:**
- [ ] Sprint 4 complete (Router with GRAPH intent)
- [ ] Neo4j 5.14 Docker image pulled
- [ ] Ollama llama3.2:8b + nomic-embed-text available
- [ ] Test corpus prepared (100+ documents)
- [ ] Team capacity confirmed (30-40 story points)

**Sprint 5 Status:** Planning → Ready to Start

*Generated: 2025-10-16*
*Based on: SPRINT_PLAN.md (Sprint 5 section), Sprint 3 Plan/Summary, Sprint 4 Router*
*Story Points: 42 (P0: 19, P1: 18, P2: 5)*
*Features: 6 (5 core + 1 optional)*
*Duration: 6 days (5 core + 1 buffer)*
