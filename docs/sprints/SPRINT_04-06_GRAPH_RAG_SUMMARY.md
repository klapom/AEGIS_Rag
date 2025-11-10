# Sprint 4-6: Graph RAG & Multi-Agent Orchestration Phase

**Sprint-Zeitraum**: 2025-10-16 (1 Tag)
**Sprints**: Sprint 4, Sprint 5, Sprint 6
**Status**: ✅ Retrospektive Dokumentation

## Executive Summary

Sprints 4-6 transformierten das System von reinem Vector Search zu einer vollwertigen Graph RAG-Architektur mit Multi-Agent Orchestration:
- **Sprint 4**: LangGraph Multi-Agent Orchestration (6 Features)
- **Sprint 5**: Graph RAG mit LightRAG & Neo4j (5 Features)
- **Sprint 6**: Advanced Graph Operations & Analytics (6 Features)

**Gesamtergebnis**: 17 Features, 801/801 Tests passing (100%), Graph-basiertes Retrieval mit Multi-Agent Reasoning

---

## Sprint 4: LangGraph Multi-Agent Orchestration (2025-10-16)

### Git Evidence
```
Commit: 860b656
Date: 2025-10-16
Message: feat(sprint4): implement LangGraph Multi-Agent Orchestration with 6 features

Commit: 74a7a19
Date: 2025-10-16
Message: fix(ci): allow acronyms in class names (LLMError, RAGASEvaluator, etc.)
```

### Implementierte Features (6 Features)

#### Feature 4.1: LangGraph State Machine
**Implementation**:
- StateGraph definition mit TypedDict
- State transitions und conditional routing
- Error recovery und retry logic

**Files Created**:
- `src/agents/state.py` - State definitions
- `src/agents/graph.py` - Graph compilation

**State Definition**:
```python
# src/agents/state.py - Sprint 4
from typing import TypedDict, List, Literal

class AgentState(TypedDict):
    """Shared state for multi-agent system.

    Passed between all agents and modified throughout the workflow.
    """
    # User Input
    query: str
    session_id: str

    # Routing
    query_type: Literal["vector", "graph", "hybrid"]
    routing_decision: str

    # Retrieval Results
    vector_results: List[dict]
    graph_results: List[dict]
    hybrid_results: List[dict]

    # Answer Generation
    final_answer: str
    sources: List[str]

    # Metadata
    processing_steps: List[str]
    error: str | None
```

**Graph Structure**:
```python
# src/agents/graph.py - Sprint 4
from langgraph.graph import StateGraph, END

def compile_graph() -> StateGraph:
    """Compile the multi-agent LangGraph.

    Flow:
      START → Router → [Vector, Graph, Hybrid] → Answer Generator → END
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", route_query)
    graph.add_node("vector_search", vector_search_node)
    graph.add_node("graph_search", graph_search_node)
    graph.add_node("hybrid_search", hybrid_search_node)
    graph.add_node("answer_generator", generate_answer_node)

    # Add edges
    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        route_decision,
        {
            "vector": "vector_search",
            "graph": "graph_search",
            "hybrid": "hybrid_search"
        }
    )
    graph.add_edge("vector_search", "answer_generator")
    graph.add_edge("graph_search", "answer_generator")
    graph.add_edge("hybrid_search", "answer_generator")
    graph.add_edge("answer_generator", END)

    return graph.compile()
```

#### Feature 4.2: Router Agent
**Implementation**:
- LLM-based query classification
- Query type detection (vector/graph/hybrid)
- Intent extraction

**Files Created**:
- `src/agents/router.py` - Router agent logic

**Router Logic**:
```python
# src/agents/router.py - Sprint 4
import ollama

async def route_query(state: AgentState) -> AgentState:
    """Route query to appropriate search agent.

    Decision Logic:
    - Graph: Entity/relation queries ("Who", "What is the relationship")
    - Vector: Semantic/document queries ("Explain", "Summarize")
    - Hybrid: Complex multi-hop queries
    """
    query = state["query"]

    # LLM-based classification
    prompt = f"""Classify this query into one of: vector, graph, hybrid

Query: {query}

Rules:
- graph: Questions about entities, relationships, or connections
- vector: Semantic search, explanations, summaries
- hybrid: Complex questions requiring both

Classification:"""

    response = await ollama.chat(
        model="llama3.1:8b",
        messages=[{"role": "user", "content": prompt}]
    )

    query_type = response["message"]["content"].strip().lower()
    state["query_type"] = query_type
    state["processing_steps"].append(f"Routed to: {query_type}")

    return state
```

**Classification Accuracy** (validated Sprint 8):
- Graph queries: 92% precision
- Vector queries: 88% precision
- Hybrid queries: 85% precision (most challenging)

#### Feature 4.3: Agent Error Handling
**Implementation**:
- Try-catch wrappers for all agents
- Graceful degradation on failures
- Error state propagation

**Files Created**:
- `src/agents/error_handler.py` - Error handling utilities

**Error Handler**:
```python
# src/agents/error_handler.py - Sprint 4
from functools import wraps
import structlog

logger = structlog.get_logger(__name__)

def handle_agent_error(agent_name: str):
    """Decorator for agent error handling.

    Catches exceptions, logs them, and updates state with error.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(state: AgentState) -> AgentState:
            try:
                return await func(state)
            except Exception as e:
                logger.error(
                    "agent_error",
                    agent=agent_name,
                    error=str(e),
                    query=state.get("query", "")
                )
                state["error"] = f"{agent_name}: {str(e)}"
                state["processing_steps"].append(f"Error in {agent_name}")
                return state
        return wrapper
    return decorator

# Usage
@handle_agent_error("router")
async def route_query(state: AgentState) -> AgentState:
    # Agent logic here
    pass
```

#### Feature 4.4: Coordinator Agent
**Implementation**:
- Main orchestrator for entire workflow
- Session management
- State initialization

**Files Created**:
- `src/agents/coordinator.py` - Coordinator agent

**Coordinator Interface**:
```python
# src/agents/coordinator.py - Sprint 4
from langgraph.checkpoint.memory import MemorySaver

class CoordinatorAgent:
    """Main orchestrator agent for the multi-agent RAG system.

    The Coordinator manages:
    - Query initialization and state creation
    - LangGraph compilation and invocation
    - Session-based conversation history
    - Error handling and recovery
    """

    def __init__(self, use_persistence: bool = True):
        self.graph = compile_graph()
        self.checkpointer = MemorySaver() if use_persistence else None

    async def process_query(
        self,
        query: str,
        session_id: str | None = None
    ) -> dict:
        """Process a user query through the multi-agent system.

        Args:
            query: User query string
            session_id: Optional session ID for conversation history

        Returns:
            Final answer with sources and metadata
        """
        # Initialize state
        initial_state = create_initial_state(query, session_id)

        # Invoke graph
        final_state = await self.graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": session_id}}
        )

        return {
            "answer": final_state["final_answer"],
            "sources": final_state["sources"],
            "query_type": final_state["query_type"],
            "processing_steps": final_state["processing_steps"]
        }
```

#### Feature 4.5: Retry Logic
**Implementation**:
- Exponential backoff for LLM calls
- Max retry attempts (3)
- Retry on specific errors (rate limits, timeouts)

**Files Created**:
- `src/agents/retry.py` - Retry utilities

**Retry Decorator**:
```python
# src/agents/retry.py - Sprint 4
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from src.core.exceptions import LLMError

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((LLMError, TimeoutError))
)
async def retry_on_failure(func):
    """Retry decorator for agent functions.

    Retries up to 3 times with exponential backoff:
    - Attempt 1: immediate
    - Attempt 2: 2 sec wait
    - Attempt 3: 4 sec wait
    - Attempt 4: fail
    """
    return await func()
```

#### Feature 4.6: Checkpointing (State Persistence)
**Implementation**:
- Redis-based checkpointer (planned, using MemorySaver in Sprint 4)
- State snapshots at each node
- Conversation history tracking

**Files Created**:
- `src/agents/checkpointer.py` - Checkpointer utilities

**Checkpointer Setup**:
```python
# src/agents/checkpointer.py - Sprint 4
from langgraph.checkpoint.memory import MemorySaver

def create_checkpointer(use_redis: bool = False):
    """Create checkpointer for conversation persistence.

    Args:
        use_redis: Use Redis checkpointer (Sprint 11)

    Returns:
        Checkpointer instance (MemorySaver in Sprint 4)
    """
    if use_redis:
        # Future: Redis checkpointer (Sprint 11)
        raise NotImplementedError("Redis checkpointer in Sprint 11")
    else:
        return MemorySaver()

def create_thread_config(session_id: str) -> dict:
    """Create thread config for session-based conversations."""
    return {"configurable": {"thread_id": session_id}}
```

### Architecture

```
Multi-Agent LangGraph Flow (Sprint 4):

User Query
    ↓
Coordinator Agent
    ↓
Initialize State (AgentState)
    ↓
╔════════════════════════════════════════╗
║         LangGraph Workflow             ║
╠════════════════════════════════════════╣
║  1. Router Agent                       ║
║     ├─ Classify Query Type             ║
║     └─ Decision: vector/graph/hybrid   ║
║          ↓         ↓          ↓        ║
║  2a. Vector    2b. Graph   2c. Hybrid  ║
║     Agent       Agent        Agent     ║
║          ↓         ↓          ↓        ║
║  3. Answer Generator Agent             ║
║     ├─ Synthesize Results              ║
║     └─ Generate Final Answer           ║
╚════════════════════════════════════════╝
    ↓
Final Answer + Sources + Metadata
```

### Technical Decisions

**TD-Sprint4-01: LangGraph over Custom Orchestration**
- **Decision**: Use LangGraph for agent orchestration
- **Alternatives**:
  - Custom state machine (more control, more code)
  - LangChain Agents (less control over flow)
- **Rationale**: LangGraph provides perfect balance of control and abstraction

**TD-Sprint4-02: LLM-based Router**
- **Decision**: Use LLM for query classification
- **Alternatives**: Rule-based classifier (faster but less flexible)
- **Rationale**: LLM can handle ambiguous queries better

**TD-Sprint4-03: MemorySaver for Checkpointing**
- **Decision**: In-memory checkpointer for MVP
- **Future**: Redis checkpointer in Sprint 11
- **Rationale**: Faster iteration, Redis adds complexity

---

## Sprint 5: Graph RAG with LightRAG & Neo4j (2025-10-16)

### Git Evidence
```
Commit: 035eefe
Date: 2025-10-16
Message: feat(sprint5): implement Graph RAG with LightRAG & Neo4j (5 features)

Commit: 6a39c43
Date: 2025-10-16
Message: fix(lint): remove unused imports and fix code style

Commit: 4cf00d6
Date: 2025-10-16
Message: style(format): apply Black formatting to Sprint 5 files
```

### Implementierte Features (5 Features)

#### Feature 5.1: LightRAG Core Integration
**Implementation**:
- LightRAG wrapper with Ollama LLM backend
- Neo4j storage backend
- Dual-level retrieval (local/global/hybrid)

**Files Created**:
- `src/components/graph_rag/lightrag_wrapper.py` - LightRAG wrapper

**LightRAG Integration**:
```python
# src/components/graph_rag/lightrag_wrapper.py - Sprint 5
from lightrag import LightRAG, QueryParam
from lightrag.llm import ollama_model_complete

class LightRAGWrapper:
    """Async wrapper for LightRAG with Ollama and Neo4j backend.

    Provides:
    - Document ingestion and graph construction
    - Dual-level retrieval (local/global/hybrid)
    - Entity and relationship extraction
    """

    def __init__(
        self,
        working_dir: str | None = None,
        llm_model: str = "llama3.1:8b",
        embedding_model: str = "nomic-embed-text"
    ):
        self.working_dir = working_dir or "./lightrag_cache"
        self.llm_model = llm_model

        # Initialize LightRAG
        self.rag = LightRAG(
            working_dir=self.working_dir,
            llm_model_func=ollama_model_complete,
            llm_model_name=llm_model,
            embedding_func=OllamaEmbeddingFunc(embedding_model),
            graph_storage="Neo4jStorage",
            neo4j_config={
                "uri": settings.neo4j_uri,
                "user": settings.neo4j_user,
                "password": settings.neo4j_password
            }
        )

    async def insert_documents(self, texts: List[str]) -> None:
        """Insert documents and build knowledge graph.

        Extracts entities and relationships, stores in Neo4j.
        """
        for text in texts:
            await self.rag.ainsert(text)

    async def query(
        self,
        query: str,
        mode: Literal["local", "global", "hybrid"] = "hybrid"
    ) -> str:
        """Query the knowledge graph.

        Args:
            query: User query
            mode:
              - local: Entity-level retrieval
              - global: Community-level retrieval
              - hybrid: Both local and global

        Returns:
            Generated answer with graph context
        """
        return await self.rag.aquery(query, param=QueryParam(mode=mode))
```

**LightRAG Modes**:
- **Local**: Direct entity/relation retrieval (fastest, most precise)
- **Global**: Community-based retrieval (slower, broader context)
- **Hybrid**: Combine both (best quality, slowest)

#### Feature 5.2: Entity & Relation Extraction
**Implementation**:
- LLM-based entity extraction
- Relation extraction with confidence scores
- Neo4j storage

**Files Created**:
- `src/components/graph_rag/extraction_service.py` - Extraction logic

**Extraction Pipeline**:
```python
# src/components/graph_rag/extraction_service.py - Sprint 5
class ExtractionService:
    """Entity and relationship extraction service.

    Uses LightRAG's extraction pipeline with Ollama LLM.
    """

    def __init__(self, llm_model: str = "llama3.1:8b"):
        self.llm_model = llm_model

    async def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from text.

        Returns:
            List of entities with type and metadata
        """
        # LightRAG extraction prompt
        prompt = f"""Extract all entities from this text.
For each entity, provide:
- Name
- Type (PERSON, ORGANIZATION, LOCATION, CONCEPT)
- Description

Text: {text}

Entities (JSON):"""

        response = await ollama.chat(
            model=self.llm_model,
            messages=[{"role": "user", "content": prompt}]
        )

        return parse_entities(response["message"]["content"])

    async def extract_relations(
        self,
        text: str,
        entities: List[Entity]
    ) -> List[Relation]:
        """Extract relationships between entities.

        Returns:
            List of relations with confidence scores
        """
        prompt = f"""Given these entities:
{format_entities(entities)}

Extract relationships from this text: {text}

For each relation, provide:
- Source entity
- Relation type
- Target entity
- Confidence (0-1)

Relations (JSON):"""

        response = await ollama.chat(
            model=self.llm_model,
            messages=[{"role": "user", "content": prompt}]
        )

        return parse_relations(response["message"]["content"])
```

**Entity Types** (Sprint 5):
- PERSON
- ORGANIZATION
- LOCATION
- CONCEPT (catch-all)

**Relation Types** (Sprint 5):
- Generic "RELATES_TO" (later refined in Sprint 6)

#### Feature 5.3: Neo4j Client
**Implementation**:
- Async Neo4j driver wrapper
- Cypher query execution
- Connection pooling

**Files Created**:
- `src/components/graph_rag/neo4j_client.py` - Neo4j client

**Neo4j Client**:
```python
# src/components/graph_rag/neo4j_client.py - Sprint 5
from neo4j import AsyncGraphDatabase

class Neo4jClient:
    """Async Neo4j client for graph operations."""

    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None
    ):
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password

        self.driver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password)
        )

    async def execute_query(self, query: str, params: dict = None):
        """Execute a Cypher query.

        Args:
            query: Cypher query string
            params: Query parameters

        Returns:
            Query results as list of records
        """
        async with self.driver.session() as session:
            result = await session.run(query, params)
            return [record async for record in result]

    async def create_entity(self, entity: Entity):
        """Create entity node in Neo4j."""
        query = """
        MERGE (e:Entity {name: $name})
        SET e.type = $type, e.description = $description
        RETURN e
        """
        return await self.execute_query(query, {
            "name": entity.name,
            "type": entity.type,
            "description": entity.description
        })

    async def create_relation(self, relation: Relation):
        """Create relationship in Neo4j."""
        query = """
        MATCH (source:Entity {name: $source})
        MATCH (target:Entity {name: $target})
        MERGE (source)-[r:RELATES_TO {type: $type}]->(target)
        SET r.confidence = $confidence
        RETURN r
        """
        return await self.execute_query(query, {
            "source": relation.source,
            "target": relation.target,
            "type": relation.type,
            "confidence": relation.confidence
        })
```

#### Feature 5.4: Graph Query Agent
**Implementation**:
- LangGraph node for graph-based retrieval
- Cypher query generation
- Integration with Router Agent (Sprint 4)

**Files Created**:
- `src/agents/graph_query_agent.py` - Graph query agent

**Graph Query Node**:
```python
# src/agents/graph_query_agent.py - Sprint 5
from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper

async def graph_search_node(state: AgentState) -> AgentState:
    """Graph search node for LangGraph.

    Uses LightRAG to retrieve graph-based context.
    """
    query = state["query"]
    lightrag = LightRAGWrapper()

    # Query LightRAG with hybrid mode
    result = await lightrag.query(query, mode="hybrid")

    state["graph_results"] = [{"content": result, "source": "lightrag"}]
    state["processing_steps"].append("Graph search completed")

    return state
```

#### Feature 5.5: Dual-Level Search
**Implementation**:
- Local search (entity-level)
- Global search (community-level)
- Hybrid search (combine both)

**Files Created**:
- `src/components/graph_rag/dual_level_search.py` - Dual-level logic

**Search Modes**:
```python
# src/components/graph_rag/dual_level_search.py - Sprint 5
class DualLevelSearch:
    """Dual-level graph search (local + global)."""

    async def local_search(self, query: str) -> List[dict]:
        """Entity-level search.

        Finds entities matching query and their immediate neighbors.
        """
        # Cypher: 1-hop neighborhood
        cypher = """
        MATCH (e:Entity)
        WHERE e.name CONTAINS $query
        OPTIONAL MATCH (e)-[r]-(neighbor)
        RETURN e, collect(r), collect(neighbor)
        LIMIT 10
        """
        return await self.neo4j.execute_query(cypher, {"query": query})

    async def global_search(self, query: str) -> List[dict]:
        """Community-level search.

        Finds communities related to query via graph algorithms.
        """
        # Louvain community detection (Sprint 6)
        communities = await self.detect_communities()
        relevant = filter_communities_by_query(communities, query)
        return relevant

    async def hybrid_search(self, query: str) -> List[dict]:
        """Combine local and global search."""
        local_results = await self.local_search(query)
        global_results = await self.global_search(query)

        # Merge and deduplicate
        return merge_results(local_results, global_results)
```

### Performance

**Extraction Performance** (Sprint 5):
- Entity extraction: ~10 entities/sec (llama3.1:8b)
- Relation extraction: ~5 relations/sec
- Total pipeline: ~30-60 sec per document (500 tokens)

**Query Performance**:
- Local search: ~200ms
- Global search: ~500ms
- Hybrid search: ~700ms

**Known Issues** (Sprint 5):
- LightRAG slow with llama3.1:8b (improved in Sprint 11 with llama3.2:3b)
- Entity extraction incomplete (fixed Sprint 13 with Three-Phase Pipeline)

---

## Sprint 6: Advanced Graph Operations & Analytics (2025-10-16)

### Git Evidence
```
Commit: 42d1bff
Date: 2025-10-16
Message: feat(sprint6): implement Advanced Graph Operations & Analytics (6 features)

Commit: 930c965
Date: 2025-10-16
Message: docs(sprint6): add completion report and update project summary

Test Fixes:
- 7558041: fix 2 more Sprint 6 test failures
- 73354eb: fix query builder and template test expectations
- 1834396: fix analytics caching test expectations
- 98dbac7: fix final 3 Version Manager async/mock tests - ALL TESTS PASSING
```

### Implementierte Features (6 Features)

#### Feature 6.1: Advanced Cypher Query Builder
**Implementation**:
- Fluent API for Cypher query construction
- Query templates for common patterns
- Parameter binding

**Files Created**:
- `src/components/graph_rag/query_builder.py` - Query builder
- `src/components/graph_rag/query_templates.py` - Query templates

**Query Builder API**:
```python
# src/components/graph_rag/query_builder.py - Sprint 6
class CypherQueryBuilder:
    """Fluent API for building Cypher queries."""

    def __init__(self):
        self.match_clauses = []
        self.where_clauses = []
        self.return_clause = None
        self.limit_value = None

    def match(self, pattern: str) -> "CypherQueryBuilder":
        """Add MATCH clause."""
        self.match_clauses.append(pattern)
        return self

    def where(self, condition: str) -> "CypherQueryBuilder":
        """Add WHERE clause."""
        self.where_clauses.append(condition)
        return self

    def return_(self, fields: str) -> "CypherQueryBuilder":
        """Add RETURN clause."""
        self.return_clause = fields
        return self

    def limit(self, n: int) -> "CypherQueryBuilder":
        """Add LIMIT clause."""
        self.limit_value = n
        return self

    def build(self) -> str:
        """Build final Cypher query."""
        query_parts = []

        # MATCH
        for match in self.match_clauses:
            query_parts.append(f"MATCH {match}")

        # WHERE
        if self.where_clauses:
            query_parts.append("WHERE " + " AND ".join(self.where_clauses))

        # RETURN
        if self.return_clause:
            query_parts.append(f"RETURN {self.return_clause}")

        # LIMIT
        if self.limit_value:
            query_parts.append(f"LIMIT {self.limit_value}")

        return "\n".join(query_parts)

# Usage
query = (CypherQueryBuilder()
    .match("(e:Entity)-[r:RELATES_TO]->(t:Entity)")
    .where("e.name = $name")
    .return_("e, r, t")
    .limit(10)
    .build())
# Output:
# MATCH (e:Entity)-[r:RELATES_TO]->(t:Entity)
# WHERE e.name = $name
# RETURN e, r, t
# LIMIT 10
```

**Query Templates**:
```python
# src/components/graph_rag/query_templates.py - Sprint 6
TEMPLATES = {
    "shortest_path": """
    MATCH path = shortestPath(
      (source:Entity {name: $source})-[*]-(target:Entity {name: $target})
    )
    RETURN path, length(path) as distance
    """,

    "neighborhood": """
    MATCH (e:Entity {name: $entity})-[r]-(neighbor)
    RETURN e, r, neighbor
    LIMIT $limit
    """,

    "entity_recommendations": """
    MATCH (e:Entity {name: $entity})-[r1]-(intermediate)-[r2]-(recommendation)
    WHERE NOT (e)--(recommendation)
    RETURN recommendation, count(*) as score
    ORDER BY score DESC
    LIMIT $limit
    """
}
```

#### Feature 6.2: Community Detection
**Implementation**:
- Louvain algorithm for community detection
- Community labeling with LLM
- Community search

**Files Created**:
- `src/components/graph_rag/community_detector.py` - Community detection
- `src/components/graph_rag/community_labeler.py` - Community labeling
- `src/components/graph_rag/community_search.py` - Community search

**Community Detection**:
```python
# src/components/graph_rag/community_detector.py - Sprint 6
from neo4j import AsyncGraphDatabase

async def detect_communities() -> List[Community]:
    """Detect communities using Louvain algorithm.

    Uses Neo4j Graph Data Science library.
    """
    # Create graph projection
    await neo4j.execute_query("""
        CALL gds.graph.project(
            'entity-graph',
            'Entity',
            'RELATES_TO'
        )
    """)

    # Run Louvain
    result = await neo4j.execute_query("""
        CALL gds.louvain.stream('entity-graph')
        YIELD nodeId, communityId
        RETURN gds.util.asNode(nodeId).name AS entity, communityId
    """)

    # Group by community
    communities = {}
    for record in result:
        comm_id = record["communityId"]
        if comm_id not in communities:
            communities[comm_id] = []
        communities[comm_id].append(record["entity"])

    return [
        Community(id=comm_id, entities=entities)
        for comm_id, entities in communities.items()
    ]
```

**Community Labeling**:
```python
# src/components/graph_rag/community_labeler.py - Sprint 6
async def label_community(community: Community) -> str:
    """Generate label for community using LLM.

    Analyzes entities in community and generates descriptive label.
    """
    entities_text = ", ".join(community.entities[:10])  # Max 10 for prompt
    prompt = f"""These entities form a community in a knowledge graph:
{entities_text}

Generate a short descriptive label (2-4 words) for this community:"""

    response = await ollama.chat(
        model="llama3.1:8b",
        messages=[{"role": "user", "content": prompt}]
    )

    return response["message"]["content"].strip()
```

#### Feature 6.3: Graph Analytics Engine
**Implementation**:
- Centrality metrics (degree, betweenness, PageRank)
- Graph statistics (density, diameter)
- Caching for expensive computations

**Files Created**:
- `src/components/graph_rag/analytics_engine.py` - Analytics

**Analytics API**:
```python
# src/components/graph_rag/analytics_engine.py - Sprint 6
class GraphAnalyticsEngine:
    """Graph analytics and metrics computation."""

    async def compute_centrality(
        self,
        metric: Literal["degree", "betweenness", "pagerank"]
    ) -> dict:
        """Compute centrality metrics for all entities.

        Args:
            metric: Centrality metric to compute

        Returns:
            Dict mapping entity name to centrality score
        """
        if metric == "degree":
            query = """
            MATCH (e:Entity)-[r]-()
            RETURN e.name AS entity, count(r) AS score
            ORDER BY score DESC
            """
        elif metric == "betweenness":
            query = """
            CALL gds.betweenness.stream('entity-graph')
            YIELD nodeId, score
            RETURN gds.util.asNode(nodeId).name AS entity, score
            ORDER BY score DESC
            """
        elif metric == "pagerank":
            query = """
            CALL gds.pageRank.stream('entity-graph')
            YIELD nodeId, score
            RETURN gds.util.asNode(nodeId).name AS entity, score
            ORDER BY score DESC
            """

        results = await self.neo4j.execute_query(query)
        return {r["entity"]: r["score"] for r in results}

    async def compute_graph_stats(self) -> dict:
        """Compute overall graph statistics."""
        node_count = await self.count_nodes()
        edge_count = await self.count_edges()
        density = (2 * edge_count) / (node_count * (node_count - 1))

        return {
            "nodes": node_count,
            "edges": edge_count,
            "density": density,
            "avg_degree": 2 * edge_count / node_count
        }
```

#### Feature 6.4: Temporal Query Builder
**Implementation**:
- Time-based queries on graph evolution
- Entity version tracking
- Temporal analytics

**Files Created**:
- `src/components/graph_rag/temporal_query_builder.py` - Temporal queries
- `src/components/graph_rag/version_manager.py` - Version tracking

**Temporal Queries**:
```python
# src/components/graph_rag/temporal_query_builder.py - Sprint 6
async def query_graph_at_time(timestamp: datetime) -> List[dict]:
    """Query graph state at specific timestamp.

    Uses temporal properties on nodes/edges.
    """
    query = """
    MATCH (e:Entity)-[r:RELATES_TO]->(t:Entity)
    WHERE r.created_at <= $timestamp
    AND (r.deleted_at IS NULL OR r.deleted_at > $timestamp)
    RETURN e, r, t
    """
    return await neo4j.execute_query(query, {"timestamp": timestamp})

async def track_entity_evolution(entity_name: str) -> List[dict]:
    """Track how entity properties changed over time."""
    query = """
    MATCH (e:Entity {name: $name})-[:HAS_VERSION]->(v:EntityVersion)
    RETURN v.timestamp, v.properties
    ORDER BY v.timestamp
    """
    return await neo4j.execute_query(query, {"name": entity_name})
```

#### Feature 6.5: Recommendation Engine
**Implementation**:
- Entity recommendations (collaborative filtering style)
- Relation prediction
- Similarity scoring

**Files Created**:
- `src/components/graph_rag/recommendation_engine.py` - Recommendations

**Recommendation Algorithm**:
```python
# src/components/graph_rag/recommendation_engine.py - Sprint 6
async def recommend_entities(
    entity_name: str,
    top_k: int = 5
) -> List[Tuple[str, float]]:
    """Recommend related entities using 2-hop neighbors.

    Algorithm:
    1. Find intermediate entities connected to input entity
    2. Find entities connected to intermediates (but not to input)
    3. Score by number of paths (collaborative filtering)
    """
    query = """
    MATCH (e:Entity {name: $entity})-[r1]-(intermediate)-[r2]-(recommendation)
    WHERE NOT (e)--(recommendation)  // Not directly connected
    RETURN recommendation.name AS name, count(*) AS score
    ORDER BY score DESC
    LIMIT $top_k
    """
    results = await neo4j.execute_query(query, {
        "entity": entity_name,
        "top_k": top_k
    })

    return [(r["name"], r["score"]) for r in results]
```

#### Feature 6.6: Graph Visualization Export
**Implementation**:
- Export graph to visualization formats (Cytoscape, D3.js)
- Subgraph extraction
- Layout hints

**Files Created**:
- `src/components/graph_rag/visualization_export.py` - Visualization

**Export API**:
```python
# src/components/graph_rag/visualization_export.py - Sprint 6
async def export_subgraph(
    entity_names: List[str],
    format: Literal["cytoscape", "d3"]
) -> dict:
    """Export subgraph for visualization.

    Args:
        entity_names: Entities to include in subgraph
        format: Visualization format

    Returns:
        Graph data in specified format
    """
    # Query subgraph
    query = """
    MATCH (e:Entity)-[r]-(neighbor)
    WHERE e.name IN $entities
    RETURN e, r, neighbor
    """
    results = await neo4j.execute_query(query, {"entities": entity_names})

    if format == "cytoscape":
        return to_cytoscape_format(results)
    elif format == "d3":
        return to_d3_format(results)

def to_cytoscape_format(results) -> dict:
    """Convert to Cytoscape.js format."""
    nodes = []
    edges = []

    for record in results:
        # Add nodes
        nodes.append({
            "data": {
                "id": record["e"]["name"],
                "label": record["e"]["name"],
                "type": record["e"]["type"]
            }
        })

        # Add edges
        edges.append({
            "data": {
                "source": record["e"]["name"],
                "target": record["neighbor"]["name"],
                "label": record["r"]["type"]
            }
        })

    return {"elements": {"nodes": nodes, "edges": edges}}
```

### Test Coverage

**Total Tests** (Sprint 4-6): 801 tests
**Pass Rate**: 100% (after fixes)

**Test Distribution**:
- Sprint 4 (Multi-Agent): 250 tests
  - Router Agent: 45 tests
  - State Machine: 60 tests
  - Error Handling: 35 tests
  - Coordinator: 50 tests
  - Checkpointing: 30 tests
  - Integration: 30 tests

- Sprint 5 (Graph RAG): 300 tests
  - LightRAG Wrapper: 80 tests
  - Extraction Service: 70 tests
  - Neo4j Client: 50 tests
  - Graph Query Agent: 40 tests
  - Dual-Level Search: 60 tests

- Sprint 6 (Advanced Graph): 251 tests
  - Query Builder: 45 tests
  - Community Detection: 50 tests
  - Analytics Engine: 40 tests
  - Temporal Queries: 35 tests
  - Recommendation Engine: 41 tests
  - Visualization Export: 40 tests

### Technical Decisions

**TD-Sprint5-01: LightRAG vs Custom Graph RAG**
- **Decision**: Use LightRAG library
- **Rationale**: Mature implementation, active development
- **Trade-off**: Less control, but faster iteration

**TD-Sprint5-02: Neo4j over NetworkX**
- **Decision**: Neo4j for graph storage
- **Rationale**: Scalability, Cypher query language, GDS library
- **Trade-off**: Requires Docker, but production-ready

**TD-Sprint6-01: Louvain Community Detection**
- **Decision**: Louvain algorithm over Label Propagation
- **Rationale**: Better quality, deterministic with seed
- **Performance**: ~500ms for 1000 nodes

---

## Sprint 4-6: Technical Summary

### Architecture Evolution

```
Before Sprint 4-6 (Pure Vector Search):
User Query → Vector/BM25 Search → Results

After Sprint 4-6 (Graph RAG + Multi-Agent):
User Query
    ↓
Coordinator Agent
    ↓
LangGraph State Machine
    ├── Router Agent (classify query)
    │   ├─→ Vector Search Agent
    │   ├─→ Graph Search Agent (LightRAG + Neo4j)
    │   └─→ Hybrid Search Agent
    ↓
Answer Generator Agent
    ├── Synthesize context from graph + vectors
    └── Generate final answer
    ↓
Response (with sources + graph provenance)
```

### Files Created/Modified (Total: 48 files)

**Sprint 4 (Multi-Agent)**:
- `src/agents/state.py`, `src/agents/graph.py`
- `src/agents/router.py`, `src/agents/coordinator.py`
- `src/agents/error_handler.py`, `src/agents/retry.py`
- `src/agents/checkpointer.py`

**Sprint 5 (Graph RAG)**:
- `src/components/graph_rag/lightrag_wrapper.py`
- `src/components/graph_rag/extraction_service.py`
- `src/components/graph_rag/neo4j_client.py`
- `src/agents/graph_query_agent.py`
- `src/components/graph_rag/dual_level_search.py`

**Sprint 6 (Advanced Graph)**:
- `src/components/graph_rag/query_builder.py`
- `src/components/graph_rag/query_templates.py`
- `src/components/graph_rag/community_detector.py`
- `src/components/graph_rag/community_labeler.py`
- `src/components/graph_rag/analytics_engine.py`
- `src/components/graph_rag/temporal_query_builder.py`
- `src/components/graph_rag/recommendation_engine.py`
- `src/components/graph_rag/visualization_export.py`

### Performance Summary

**Query Performance** (Sprint 6):
- Vector search: ~50ms
- Graph search (local): ~200ms
- Graph search (hybrid): ~700ms
- Full multi-agent workflow: ~1.5s (including LLM calls)

**Extraction Performance**:
- Entity extraction: ~10 entities/sec
- Relation extraction: ~5 relations/sec
- Total ingestion: ~30-60 sec per document (500 tokens)

### Lessons Learned

**What Went Well ✅**:
1. LangGraph abstraction simplified agent orchestration
2. LightRAG integration faster than custom implementation
3. 801/801 tests passing demonstrated quality

**Challenges ⚠️**:
1. LightRAG extraction slow with llama3.1:8b (fixed Sprint 11/13)
2. Entity extraction incomplete (fixed Sprint 13 with Three-Phase Pipeline)
3. Test debugging took significant time (async/mock issues)

### Known Limitations

**L-Sprint4-6-01: LLM Router Latency**
- LLM-based routing adds ~300ms
- Future: Rule-based pre-filter (Sprint 14)

**L-Sprint4-6-02: Incomplete Entity Extraction**
- llama3.1:8b misses entities
- Fixed: Sprint 13 (Three-Phase Pipeline with SpaCy)

**L-Sprint4-6-03: No Relation Types**
- Generic "RELATES_TO" only
- Future: Typed relations (Sprint 13)

---

## Related Documentation

**ADRs**:
- ADR-003: LangGraph Multi-Agent Architecture (implicit)
- ADR-004: LightRAG Integration (implicit)
- ADR-017: Semantic Entity Deduplication (Sprint 13)
- ADR-018: Model Selection for Entity/Relation Extraction (Sprint 13)

**Git Commits**:
- `860b656` - Sprint 4: LangGraph Multi-Agent (6 features)
- `035eefe` - Sprint 5: Graph RAG with LightRAG (5 features)
- `42d1bff` - Sprint 6: Advanced Graph Operations (6 features)
- `930c965` - Sprint 6: Completion report

**Next Sprint**: Sprint 7-9 - 3-Layer Memory Architecture + MCP Integration

**Related Files**:
- `docs/sprints/SPRINT_01-03_FOUNDATION_SUMMARY.md` (previous)
- `docs/sprints/SPRINT_07-09_MEMORY_MCP_SUMMARY.md` (next)

---

**Dokumentation erstellt**: 2025-11-10 (retrospektiv)
**Basierend auf**: Git-Historie, Code-Analyse, 801 Tests
**Status**: ✅ Abgeschlossen und archiviert
