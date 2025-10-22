# Sprint 6 Plan - Advanced Graph Operations & Analytics

**Sprint Goal:** Enhance Graph RAG capabilities with advanced query operations, performance optimization, community detection, temporal features, visualization API, and analytics
**Duration:** 5 working days
**Story Points:** 38 (within team capacity: 30-40)
**Status:** 🔜 **READY TO START**

---

## 📋 Executive Summary

Sprint 6 builds upon Sprint 5's Graph RAG foundation (LightRAG + Neo4j) to deliver enterprise-grade graph capabilities that enable sophisticated knowledge discovery, temporal analysis, and interactive visualization.

### Context from Previous Sprints

**Sprint 5 Achievements:**
- ✅ LightRAG Core Integration with Ollama LLM
- ✅ Neo4j Backend Configuration (Docker + indexing)
- ✅ Entity & Relationship Extraction Pipeline
- ✅ Dual-Level Retrieval (local/global/hybrid modes)
- ✅ Graph Query Agent with LangGraph integration
- ✅ Incremental Graph Updates with deduplication

**Sprint 6 Focus:**
This sprint transforms the graph from a retrieval tool into a comprehensive knowledge platform with:
- **Query Optimization:** Cypher query builder, caching, batch operations
- **Community Detection:** Leiden/Louvain algorithms for topic clustering
- **Temporal Features:** Time-aware graph queries, versioning, evolution tracking
- **Visualization API:** Interactive graph rendering for frontend integration
- **Analytics:** Centrality metrics, influence scoring, knowledge gap detection

### Success Metrics

1. **Performance:** Graph query latency p95 <300ms (vs. current ~500ms)
2. **Scale:** Support 10,000+ entities without degradation
3. **Discovery:** Community detection identifies 15+ distinct topic clusters
4. **Insights:** Analytics API returns 10+ metrics per entity
5. **UX:** Visualization API renders 100-node subgraphs <500ms
6. **Quality:** 90%+ test coverage across all new features

---

## 🎯 Sprint Goals & Strategic Value

### Primary Goals

1. **Optimize Query Performance** (Features 6.1, 6.2)
   - Reduce graph query latency by 40%
   - Enable complex multi-hop queries without timeout
   - Support batch operations for efficiency

2. **Enable Knowledge Discovery** (Features 6.3, 6.4)
   - Identify hidden communities and relationships
   - Track knowledge evolution over time
   - Detect gaps and emerging topics

3. **Improve User Experience** (Feature 6.5)
   - Provide interactive graph visualization
   - Enable exploration of entity neighborhoods
   - Support filtering and drill-down operations

4. **Deliver Actionable Insights** (Feature 6.6)
   - Calculate influence and centrality scores
   - Identify key entities and relationships
   - Generate automated recommendations

### Strategic Value

**For AEGIS RAG System:**
- **Enhanced Retrieval:** Better context through community-aware search
- **Temporal Intelligence:** Answer "when" and "how changed" questions
- **Visual Understanding:** Enable non-technical users to explore knowledge
- **Data-Driven Decisions:** Use analytics to prioritize content curation

**For End Users:**
- **Discover:** Find related entities and hidden connections
- **Understand:** See how knowledge clusters and evolves
- **Explore:** Interact with visual graph representations
- **Decide:** Get recommendations based on graph analysis

**For Development Team:**
- **Observability:** Monitor graph health and performance
- **Optimization:** Identify slow queries and bottlenecks
- **Maintenance:** Track temporal changes and versioning
- **Integration:** Provide APIs for frontend/dashboard integration

---

## 📊 Feature Breakdown (1 Feature = 1-2 Commits)

### Feature 6.1: Advanced Query Operations ⚡

**Priority:** P0 (Performance Critical)
**Story Points:** 8
**Effort:** 1.5 days

**Problem Statement:**
Current graph queries are limited to simple patterns and suffer from:
- Slow multi-hop traversals (>500ms for 3+ hops)
- No query optimization or caching
- Limited query complexity (basic patterns only)
- No support for batch operations

**Solution:**
Implement a comprehensive query optimization layer with:
- Cypher query builder for complex patterns
- Multi-level caching (query results + subgraph)
- Query optimization (parameterization, index hints)
- Batch query executor for parallel operations

#### Deliverables

- [ ] `CypherQueryBuilder` class for programmatic query construction
- [ ] `GraphQueryCache` with LRU eviction and TTL
- [ ] `QueryOptimizer` with pattern analysis and rewriting
- [ ] `BatchQueryExecutor` for parallel query execution
- [ ] Performance benchmarks showing 40%+ latency reduction
- [ ] 25+ unit tests for query builder and cache
- [ ] Integration tests for batch operations

#### Technical Tasks

1. **Cypher Query Builder (Day 1 Morning)**
   - Implement fluent API for query construction
   - Support MATCH, WHERE, RETURN, WITH, ORDER BY, LIMIT
   - Add relationship pattern builder (multi-hop, variable length)
   - Implement query parameterization for safety
   - Add query explanation and profiling

2. **Query Cache Implementation (Day 1 Afternoon)**
   - LRU cache with configurable max size (default: 1000 queries)
   - TTL-based expiration (default: 5 minutes)
   - Cache invalidation on graph updates
   - Cache hit/miss metrics tracking
   - Subgraph caching for entity neighborhoods

3. **Query Optimization (Day 2 Morning)**
   - Query pattern analysis (identify slow patterns)
   - Automatic index hint insertion
   - Query rewriting (push-down filters, join optimization)
   - Cost-based optimization using Neo4j EXPLAIN
   - Optimization metrics and recommendations

4. **Batch Operations (Day 2 Afternoon)**
   - Parallel query executor (asyncio.gather)
   - Result aggregation and deduplication
   - Error handling per query (fail gracefully)
   - Batch size tuning (optimal: 5-10 concurrent)
   - Monitoring and logging per batch

#### API Design

```python
# Cypher Query Builder
from src.components.graph_rag.query_builder import CypherQueryBuilder

builder = CypherQueryBuilder()
query = (
    builder
    .match("(person:Entity {type: 'Person'})")
    .relationship("WORKS_AT", direction="->")
    .match("(org:Entity {type: 'Organization'})")
    .where("org.name CONTAINS $company_name")
    .return_("person.name AS name", "org.name AS company")
    .order_by("name")
    .limit(10)
    .build()
)

# Returns: Cypher query string + parameters dict
# {
#   "query": "MATCH (person:Entity {type: 'Person'})-[:WORKS_AT]->(org:Entity {type: 'Organization'}) WHERE org.name CONTAINS $company_name RETURN person.name AS name, org.name AS company ORDER BY name LIMIT 10",
#   "parameters": {"company_name": "Google"}
# }

# Query Cache
from src.components.graph_rag.query_cache import GraphQueryCache

cache = GraphQueryCache(max_size=1000, ttl_seconds=300)

# Try cache first
cached_result = await cache.get(query, parameters)
if cached_result:
    return cached_result

# Execute query and cache result
result = await neo4j_client.execute_read(query, parameters)
await cache.set(query, parameters, result)

# Batch Executor
from src.components.graph_rag.batch_executor import BatchQueryExecutor

executor = BatchQueryExecutor(neo4j_client, max_concurrent=10)

queries = [
    {"query": "MATCH (p:Person) RETURN p", "params": {}},
    {"query": "MATCH (o:Organization) RETURN o", "params": {}},
    {"query": "MATCH (t:Technology) RETURN t", "params": {}},
]

results = await executor.execute_batch(queries)
# Returns: List of results, preserving order
```

#### Configuration

```python
# src/core/config.py additions
class Settings(BaseSettings):
    # Query Optimization Settings (Sprint 6.1)
    graph_query_cache_enabled: bool = Field(
        default=True,
        description="Enable query result caching"
    )
    graph_query_cache_max_size: int = Field(
        default=1000,
        description="Max number of cached queries (LRU)"
    )
    graph_query_cache_ttl_seconds: int = Field(
        default=300,
        description="Cache TTL in seconds (5 minutes default)"
    )
    graph_query_optimization_enabled: bool = Field(
        default=True,
        description="Enable automatic query optimization"
    )
    graph_batch_query_max_concurrent: int = Field(
        default=10,
        description="Max concurrent queries in batch operations"
    )
    graph_query_timeout_seconds: int = Field(
        default=30,
        description="Query timeout (prevents runaway queries)"
    )
```

#### Performance Targets

| Metric | Before (Sprint 5) | After (Sprint 6.1) | Improvement |
|--------|-------------------|-------------------|-------------|
| Simple query (1-hop) | 150ms p95 | 50ms p95 | 67% faster |
| Complex query (3-hop) | 800ms p95 | 300ms p95 | 63% faster |
| Batch queries (10 queries) | 5000ms | 1500ms | 70% faster |
| Cache hit rate | N/A | 60%+ | New capability |

#### Acceptance Criteria

- [ ] CypherQueryBuilder generates valid Cypher for 20+ test cases
- [ ] Query cache achieves 60%+ hit rate on repeated queries
- [ ] Query optimization reduces latency by 40%+ for complex queries
- [ ] Batch executor handles 100 queries concurrently without failure
- [ ] All queries have configurable timeout (default: 30s)
- [ ] 25+ unit tests passing (mocked Neo4j)
- [ ] Integration tests verify cache invalidation on updates
- [ ] Performance benchmark shows 40%+ improvement

#### Git Commit Messages

```
feat(graph): add Cypher query builder with fluent API

Implements CypherQueryBuilder for programmatic query construction
with safety (parameterization) and flexibility (fluent interface).

Features:
- Fluent API for MATCH, WHERE, RETURN, WITH, ORDER BY, LIMIT
- Relationship pattern builder (multi-hop, variable length)
- Query parameterization for SQL injection prevention
- Query explanation and profiling support

Examples:
- Simple entity query: builder.match("(e:Entity)").return_("e").build()
- Multi-hop: builder.match("(a)-[:REL*1..3]->(b)").where("a.name = $name")

Performance:
- Query construction: <1ms
- Parameterization prevents injection attacks

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

```
feat(graph): add query cache and batch executor

Implements GraphQueryCache with LRU eviction and BatchQueryExecutor
for parallel query execution. Reduces latency by 40%+.

Features:
- LRU cache (1000 queries, 5min TTL)
- Cache invalidation on graph updates
- Batch executor (max 10 concurrent queries)
- Per-query error handling (fail gracefully)
- Cache hit/miss metrics tracking

Performance:
- Cache hit rate: 60%+ on repeated queries
- Batch executor: 70% faster than sequential
- Simple queries: 150ms → 50ms (67% improvement)
- Complex queries: 800ms → 300ms (63% improvement)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Dependencies

- Sprint 5 (LightRAG + Neo4j) ✅
- `neo4j` Python driver 5.14+ ✅
- No new external dependencies

#### Risks & Mitigation

**Risk 1:** Cache invalidation complexity
- **Mitigation:** Conservative TTL (5min), invalidate on all writes

**Risk 2:** Query optimization may not always improve performance
- **Mitigation:** A/B testing, fallback to original query if slower

**Risk 3:** Batch executor may exhaust Neo4j connections
- **Mitigation:** Connection pool sizing, max_concurrent limit

---

### Feature 6.2: Query Pattern Templates & Shortcuts 🎯

**Priority:** P1 (Developer Experience)
**Story Points:** 5
**Effort:** 1 day

**Problem Statement:**
Writing Cypher queries manually is error-prone and time-consuming for common patterns like:
- Find entity by name/type
- Get entity neighborhood (1-2 hops)
- Find shortest path between entities
- Get all relationships of a specific type

**Solution:**
Provide pre-built query templates and helper functions for common operations.

#### Deliverables

- [ ] `GraphQueryTemplates` class with 15+ common patterns
- [ ] Type-safe helper functions (find_entity, get_neighbors, etc.)
- [ ] Query composition (combine templates)
- [ ] Template validation and testing
- [ ] 20+ unit tests for templates
- [ ] Documentation with examples for each template

#### Technical Tasks

1. **Common Query Templates (Morning)**
   ```python
   # Entity Queries
   - find_entity_by_name(name: str, entity_type: str | None = None)
   - find_entities_by_type(entity_type: str, limit: int = 100)
   - get_entity_properties(entity_id: str)

   # Relationship Queries
   - get_entity_relationships(entity_id: str, rel_type: str | None = None)
   - find_shortest_path(start_entity: str, end_entity: str, max_hops: int = 5)
   - get_entity_neighbors(entity_id: str, hops: int = 1, direction: str = "both")

   # Pattern Queries
   - find_entities_with_relationship(rel_type: str, limit: int = 100)
   - get_relationship_types(entity_type: str | None = None)
   - find_similar_entities(entity_id: str, similarity_threshold: float = 0.8)
   ```

2. **Advanced Patterns (Afternoon)**
   ```python
   # Subgraph Extraction
   - extract_subgraph(center_entity: str, radius: int = 2)
   - extract_community_subgraph(community_id: str)

   # Aggregation Queries
   - count_entities_by_type()
   - count_relationships_by_type()
   - get_entity_degree_distribution()

   # Traversal Patterns
   - breadth_first_search(start_entity: str, max_depth: int = 3)
   - depth_first_search(start_entity: str, max_depth: int = 3)
   ```

3. **Template Composition**
   - Combine multiple templates into complex queries
   - Support filtering, sorting, pagination
   - Add UNION, INTERSECTION operations

4. **Testing & Documentation**
   - Unit tests for each template (20+ tests)
   - Integration tests with real Neo4j
   - API documentation with examples
   - Performance benchmarks per template

#### API Design

```python
from src.components.graph_rag.query_templates import GraphQueryTemplates

templates = GraphQueryTemplates(neo4j_client)

# Find entity by name
entity = await templates.find_entity_by_name("John Smith", entity_type="Person")

# Get entity neighbors (1-hop)
neighbors = await templates.get_entity_neighbors(
    entity_id="entity_123",
    hops=1,
    direction="outgoing"
)

# Find shortest path
path = await templates.find_shortest_path(
    start_entity="entity_123",
    end_entity="entity_456",
    max_hops=5
)

# Extract subgraph (2-hop radius)
subgraph = await templates.extract_subgraph(
    center_entity="entity_123",
    radius=2
)
# Returns: {nodes: [...], edges: [...]}
```

#### Acceptance Criteria

- [ ] 15+ query templates implemented and tested
- [ ] All templates return consistent data structures
- [ ] Templates support optional parameters (filtering, pagination)
- [ ] Subgraph extraction returns nodes + edges in standard format
- [ ] 20+ unit tests passing
- [ ] Documentation includes examples for each template
- [ ] Templates are 10x faster than manual query writing

#### Git Commit Message

```
feat(graph): add query pattern templates for common operations

Implements 15+ pre-built query templates for common graph operations.
Reduces development time by 10x for standard queries.

Templates:
- Entity lookup: find_entity_by_name, find_entities_by_type
- Relationships: get_entity_relationships, find_shortest_path
- Neighbors: get_entity_neighbors (1-N hops, directional)
- Subgraphs: extract_subgraph, extract_community_subgraph
- Aggregations: count_entities_by_type, count_relationships_by_type
- Traversal: BFS, DFS with max_depth

API:
- Type-safe helper functions with validation
- Consistent return formats (nodes + edges)
- Support for filtering, sorting, pagination

Performance:
- Template execution: 50-200ms (cached)
- 10x faster than manual query writing

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Dependencies

- Feature 6.1 (Query Builder) ✅
- No new external dependencies

#### Risks & Mitigation

**Risk:** Templates may not cover all use cases
- **Mitigation:** Provide query builder for custom queries, document extension patterns

---

### Feature 6.3: Community Detection & Clustering 🎯

**Priority:** P0 (Knowledge Discovery)
**Story Points:** 8
**Effort:** 1.5 days

**Problem Statement:**
Current graph lacks understanding of topic clusters and communities:
- No automatic grouping of related entities
- Cannot identify distinct knowledge domains
- Missing insights into information silos
- No community-aware search capabilities

**Solution:**
Implement graph community detection using Leiden and Louvain algorithms to automatically identify and label topic clusters.

#### Deliverables

- [ ] `CommunityDetector` class with Leiden/Louvain algorithms
- [ ] Neo4j GDS (Graph Data Science) integration
- [ ] Community labeling with LLM-generated descriptions
- [ ] Community-aware search (filter by community)
- [ ] Community visualization data export
- [ ] 20+ unit tests for community detection
- [ ] Integration tests with test graph (500+ nodes)

#### Technical Tasks

1. **Neo4j GDS Setup (Day 1 Morning)**
   - Install Neo4j GDS plugin (via Docker)
   - Configure graph projections (Entity → RELATED_TO)
   - Test Leiden/Louvain algorithms on sample graph
   - Set up algorithm parameters (resolution, iterations)

2. **Community Detection Implementation (Day 1 Afternoon)**
   ```python
   class CommunityDetector:
       async def detect_communities(
           self,
           algorithm: str = "leiden",  # or "louvain"
           resolution: float = 1.0,
           max_iterations: int = 10
       ) -> List[Community]:
           """Detect communities in graph using specified algorithm."""

       async def label_communities(
           self,
           communities: List[Community]
       ) -> List[LabeledCommunity]:
           """Generate human-readable labels for communities using LLM."""

       async def get_community_stats(
           self,
           community_id: str
       ) -> CommunityStats:
           """Get statistics for a specific community."""
   ```

3. **Community Labeling with LLM (Day 2 Morning)**
   - Extract representative entities from each community
   - Generate label prompt with entity names/descriptions
   - Call Ollama LLM to generate community label
   - Store labels in Neo4j (community_label property)
   - Cache labels to avoid re-computation

4. **Community-Aware Search (Day 2 Afternoon)**
   - Add community filter to graph search
   - Support queries like "entities in AI community"
   - Implement cross-community search
   - Add community-based ranking boost

5. **Visualization Export**
   - Export communities as colored node groups
   - Generate community hierarchy (if hierarchical)
   - Provide community-to-entity mapping

#### Algorithm Configuration

```python
# src/core/config.py additions
class Settings(BaseSettings):
    # Community Detection Settings (Sprint 6.3)
    graph_community_algorithm: str = Field(
        default="leiden",
        description="Community detection algorithm (leiden or louvain)"
    )
    graph_community_resolution: float = Field(
        default=1.0,
        description="Community resolution (higher = more communities)"
    )
    graph_community_max_iterations: int = Field(
        default=10,
        description="Max iterations for community detection"
    )
    graph_community_min_size: int = Field(
        default=5,
        description="Minimum community size (filter small communities)"
    )
    graph_community_labeling_enabled: bool = Field(
        default=True,
        description="Enable LLM-based community labeling"
    )
```

#### Data Models

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class Community(BaseModel):
    """Detected community (topic cluster)."""
    id: str = Field(..., description="Community ID")
    size: int = Field(..., description="Number of entities in community")
    entity_ids: List[str] = Field(..., description="List of entity IDs")
    density: float = Field(..., description="Community density (0-1)")
    modularity: float = Field(..., description="Modularity score")

class LabeledCommunity(Community):
    """Community with human-readable label."""
    label: str = Field(..., description="LLM-generated community label")
    description: str = Field(..., description="Community description")
    representative_entities: List[str] = Field(..., description="Top entities")
    topics: List[str] = Field(default_factory=list, description="Detected topics")

class CommunityStats(BaseModel):
    """Statistics for a community."""
    community_id: str
    size: int
    density: float
    avg_degree: float
    top_entities: List[Dict[str, Any]]  # Top 10 by degree centrality
    relationship_types: Dict[str, int]  # Count per relationship type
```

#### API Design

```python
from src.components.graph_rag.community_detector import CommunityDetector

detector = CommunityDetector(neo4j_client)

# Detect communities
communities = await detector.detect_communities(
    algorithm="leiden",
    resolution=1.0,
    max_iterations=10
)

# Label communities with LLM
labeled_communities = await detector.label_communities(communities)

# Get community stats
stats = await detector.get_community_stats(community_id="community_0")

# Community-aware search
from src.components.graph_rag.dual_level_search import DualLevelSearch

search = DualLevelSearch(lightrag_wrapper, neo4j_client)
results = await search.hybrid_search(
    query="machine learning frameworks",
    community_filter="AI & Machine Learning"  # Filter by community label
)
```

#### Labeling Prompt Template

```python
COMMUNITY_LABELING_PROMPT = """
Analyze this group of related entities and generate a concise, descriptive label.

Entities in this community:
{entity_list}

Entity types: {entity_types}
Common relationships: {relationship_types}

Generate:
1. Label: A 2-4 word label describing this community (e.g., "Machine Learning Tools")
2. Description: A 1-sentence description of what this community represents
3. Topics: 3-5 keywords representing main topics

Respond in JSON format:
{{
  "label": "...",
  "description": "...",
  "topics": [...]
}}
"""
```

#### Acceptance Criteria

- [ ] Community detection identifies 15+ distinct clusters on test graph
- [ ] Leiden algorithm completes in <5s for 1000-node graph
- [ ] Community labels are descriptive and accurate (manual review)
- [ ] Communities have modularity score >0.3 (good clustering)
- [ ] Community-aware search filters results correctly
- [ ] 20+ unit tests passing (mocked GDS)
- [ ] Integration tests with real Neo4j GDS
- [ ] Communities stored in Neo4j with labels

#### Git Commit Messages

```
feat(graph): add Leiden community detection for topic clustering

Implements community detection using Neo4j GDS Leiden algorithm.
Identifies 15+ distinct knowledge clusters automatically.

Features:
- Leiden and Louvain algorithm support
- Neo4j GDS integration
- Configurable resolution and iterations
- Community statistics (size, density, modularity)
- Minimum size filtering (default: 5 entities)

Algorithm:
- Leiden: Fast, high-quality community detection
- Resolution: Adjustable granularity (default: 1.0)
- Modularity: >0.3 indicates good clustering

Performance:
- 1000-node graph: <5s detection time
- Scalable to 10,000+ nodes

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

```
feat(graph): add LLM-based community labeling and search integration

Implements automatic community labeling using Ollama LLM and
integrates with dual-level search for community-aware retrieval.

Features:
- LLM-generated community labels (2-4 words)
- Community descriptions and topics
- Representative entity extraction
- Community filter in search API
- Cross-community relationship analysis

Labeling:
- Uses top entities and relationship patterns
- Generates descriptive, human-readable labels
- Example: "AI & Machine Learning", "Cloud Computing Platforms"
- Cached in Neo4j (community_label property)

Integration:
- Community filter in dual-level search
- Boost ranking for entities in target community
- Support for multi-community queries

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Dependencies

- Sprint 5 (Neo4j backend) ✅
- Feature 6.1 (Query optimization) ✅
- Neo4j GDS plugin (new) ⚠️

#### Risks & Mitigation

**Risk 1:** Neo4j GDS plugin may not be available in community edition
- **Mitigation:** Test with community edition first, provide fallback using NetworkX

**Risk 2:** LLM-generated labels may be inconsistent
- **Mitigation:** Provide override mechanism, validate with regex patterns

**Risk 3:** Large graphs may take too long for detection
- **Mitigation:** Implement incremental detection, sample-based labeling

---

### Feature 6.4: Temporal Graph Features 🕒

**Priority:** P1 (Advanced Capability)
**Story Points:** 7
**Effort:** 1.5 days

**Problem Statement:**
Current graph lacks temporal awareness:
- Cannot answer "when" questions (e.g., "When did X join Y?")
- No tracking of entity/relationship changes over time
- Missing versioning and audit trail
- Cannot query historical states

**Solution:**
Implement bi-temporal graph model with valid time and transaction time, enabling time-aware queries and evolution tracking.

#### Deliverables

- [ ] Temporal property model (valid_from, valid_to, created_at, updated_at)
- [ ] Time-aware query support (point-in-time, time-range)
- [ ] Entity version history tracking
- [ ] Relationship evolution tracking
- [ ] Temporal visualization export (timeline view)
- [ ] 18+ unit tests for temporal features
- [ ] Integration tests with versioned entities

#### Technical Tasks

1. **Temporal Data Model (Day 1 Morning)**
   ```python
   # Entity temporal properties
   {
     "id": "entity_123",
     "name": "John Smith",
     "type": "Person",
     "description": "Software Engineer",

     # Temporal properties
     "valid_from": "2020-01-01T00:00:00Z",  # When fact became true
     "valid_to": "2023-12-31T23:59:59Z",    # When fact ceased to be true
     "created_at": "2024-01-15T10:30:00Z",  # When record was created
     "updated_at": "2024-01-20T14:20:00Z",  # When record was last updated

     # Version tracking
     "version": 3,
     "previous_versions": ["entity_123_v1", "entity_123_v2"]
   }

   # Relationship temporal properties
   {
     "type": "WORKS_AT",
     "source": "entity_123",
     "target": "entity_456",
     "properties": {
       "role": "Senior Engineer",
       "valid_from": "2020-01-01",
       "valid_to": "2022-12-31",  # Left company
       "created_at": "2024-01-15",
       "updated_at": "2024-01-15"
     }
   }
   ```

2. **Time-Aware Queries (Day 1 Afternoon)**
   ```python
   class TemporalQueryBuilder:
       def at_time(self, timestamp: datetime) -> CypherQueryBuilder:
           """Query graph state at specific point in time."""

       def during_range(
           self,
           start: datetime,
           end: datetime
       ) -> CypherQueryBuilder:
           """Query entities/relationships valid during time range."""

       def evolution(
           self,
           entity_id: str,
           start: datetime | None = None,
           end: datetime | None = None
       ) -> List[EntityVersion]:
           """Get entity evolution over time."""
   ```

3. **Version Management (Day 2 Morning)**
   - Automatic version creation on updates
   - Version comparison (diff between versions)
   - Rollback to previous version
   - Version pruning (keep last N versions)

4. **Temporal Analytics (Day 2 Afternoon)**
   - Entity lifespan analysis
   - Relationship duration statistics
   - Change frequency tracking
   - Temporal event extraction (entity created, updated, deleted)

#### API Design

```python
from src.components.graph_rag.temporal_query import TemporalQueryBuilder
from datetime import datetime

temporal = TemporalQueryBuilder(neo4j_client)

# Point-in-time query
entities_2022 = await temporal.at_time(
    datetime(2022, 6, 15)
).find_entities_by_type("Person")

# Time-range query
active_relationships = await temporal.during_range(
    start=datetime(2020, 1, 1),
    end=datetime(2023, 12, 31)
).get_entity_relationships(entity_id="entity_123")

# Entity evolution
evolution = await temporal.evolution(
    entity_id="entity_123",
    start=datetime(2020, 1, 1),
    end=datetime(2024, 1, 1)
)
# Returns: List of versions with changes

# Version comparison
from src.components.graph_rag.version_manager import VersionManager

vm = VersionManager(neo4j_client)
diff = await vm.compare_versions(
    entity_id="entity_123",
    version1=1,
    version2=3
)
# Returns: {"added": {...}, "removed": {...}, "changed": {...}}
```

#### Configuration

```python
# src/core/config.py additions
class Settings(BaseSettings):
    # Temporal Graph Settings (Sprint 6.4)
    graph_temporal_enabled: bool = Field(
        default=True,
        description="Enable temporal features"
    )
    graph_version_retention: int = Field(
        default=10,
        description="Number of versions to keep per entity"
    )
    graph_version_pruning_enabled: bool = Field(
        default=True,
        description="Automatically prune old versions"
    )
    graph_temporal_precision: str = Field(
        default="second",
        description="Timestamp precision (second, minute, day)"
    )
```

#### Data Models

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any

class TemporalEntity(BaseModel):
    """Entity with temporal properties."""
    id: str
    name: str
    type: str
    properties: Dict[str, Any]
    valid_from: datetime = Field(..., description="Fact valid from")
    valid_to: datetime | None = Field(None, description="Fact valid until")
    created_at: datetime
    updated_at: datetime
    version: int = Field(default=1)

class EntityVersion(BaseModel):
    """Versioned snapshot of an entity."""
    entity_id: str
    version: int
    timestamp: datetime
    properties: Dict[str, Any]
    changes: Dict[str, Any] = Field(default_factory=dict)

class TemporalQueryResult(BaseModel):
    """Result of temporal query."""
    query_time: datetime | None = Field(None)
    time_range: tuple[datetime, datetime] | None = Field(None)
    entities: List[TemporalEntity]
    relationships: List[Dict[str, Any]]
```

#### Acceptance Criteria

- [ ] All entities have temporal properties (valid_from, valid_to, created_at, updated_at)
- [ ] Point-in-time queries return correct historical state
- [ ] Version history tracks all changes (max 10 versions retained)
- [ ] Entity evolution shows chronological changes
- [ ] Version comparison returns accurate diffs
- [ ] 18+ unit tests passing
- [ ] Integration tests with versioned test data
- [ ] Temporal queries add <50ms overhead

#### Git Commit Messages

```
feat(graph): add temporal graph model with bi-temporal support

Implements bi-temporal graph model with valid time and transaction time.
Enables time-aware queries and historical state reconstruction.

Features:
- Temporal properties (valid_from, valid_to, created_at, updated_at)
- Point-in-time queries (graph state at specific timestamp)
- Time-range queries (entities/relationships during period)
- Automatic versioning on updates (max 10 versions)
- Version pruning (configurable retention)

Model:
- Valid time: When fact is/was true in real world
- Transaction time: When fact was recorded in database
- Bi-temporal: Track both dimensions independently

Use Cases:
- "Who worked at Google in 2022?"
- "When did John Smith join Microsoft?"
- "Show entity history from 2020-2023"

Performance:
- Temporal queries: <50ms overhead vs. non-temporal
- Version storage: ~20% increase in disk space

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

```
feat(graph): add entity versioning and evolution tracking

Implements automatic entity versioning with change tracking,
comparison, and rollback capabilities.

Features:
- Automatic version creation on updates
- Version comparison (diff between versions)
- Entity evolution timeline
- Change frequency analytics
- Rollback to previous version
- Configurable version retention (default: 10)

Versioning:
- Versions linked via previous_versions property
- Each version is immutable snapshot
- Comparison shows added/removed/changed properties
- Timeline view for evolution visualization

Analytics:
- Entity lifespan analysis
- Relationship duration statistics
- Change frequency tracking
- Temporal event extraction

API:
- vm.compare_versions(entity_id, v1, v2) → diff
- temporal.evolution(entity_id, start, end) → timeline
- vm.rollback(entity_id, version) → restore

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Dependencies

- Sprint 5 (Neo4j backend) ✅
- Feature 6.1 (Query builder) ✅
- No new external dependencies

#### Risks & Mitigation

**Risk 1:** Version storage may increase database size significantly
- **Mitigation:** Configurable retention (default: 10), compression, archival strategy

**Risk 2:** Temporal queries may be slower than non-temporal
- **Mitigation:** Index temporal properties, cache frequent queries, <50ms overhead target

**Risk 3:** Version conflicts in concurrent updates
- **Mitigation:** Optimistic locking, version conflict detection

---

### Feature 6.5: Graph Visualization API 📊

**Priority:** P1 (User Experience)
**Story Points:** 6
**Effort:** 1 day

**Problem Statement:**
No way for frontend/UI to visualize graph structure:
- Cannot render interactive graph views
- Missing data format for visualization libraries
- No support for subgraph extraction for display
- Difficult to explore entity neighborhoods visually

**Solution:**
Provide REST API endpoints that return graph data in formats compatible with popular visualization libraries (D3.js, Cytoscape.js, vis.js).

#### Deliverables

- [ ] `/api/v1/graph/visualize` endpoint (subgraph extraction)
- [ ] `/api/v1/graph/entity/{id}/neighborhood` endpoint
- [ ] `/api/v1/graph/community/{id}/visualize` endpoint
- [ ] Multiple output formats (D3, Cytoscape, vis.js, JSON)
- [ ] Layout hints (force-directed, hierarchical, circular)
- [ ] Filtering and pagination for large subgraphs
- [ ] 15+ unit tests for visualization API
- [ ] Example frontend integration (HTML + D3.js)

#### Technical Tasks

1. **Visualization Data Formatter (Morning)**
   ```python
   class GraphVisualizer:
       async def format_for_d3(
           self,
           nodes: List[GraphNode],
           edges: List[GraphRelationship]
       ) -> Dict[str, Any]:
           """Format graph for D3.js force-directed layout."""

       async def format_for_cytoscape(
           self,
           nodes: List[GraphNode],
           edges: List[GraphRelationship]
       ) -> Dict[str, Any]:
           """Format graph for Cytoscape.js."""

       async def format_for_visjs(
           self,
           nodes: List[GraphNode],
           edges: List[GraphRelationship]
       ) -> Dict[str, Any]:
           """Format graph for vis.js."""
   ```

2. **API Endpoints (Afternoon)**
   - Subgraph extraction endpoint
   - Entity neighborhood endpoint
   - Community visualization endpoint
   - Full graph export (with pagination)

3. **Layout & Styling**
   - Node coloring by entity type
   - Edge styling by relationship type
   - Community-based coloring
   - Size by centrality/importance

4. **Example Integration**
   - HTML page with D3.js visualization
   - Interactive features (zoom, pan, click)
   - Tooltip on hover (entity details)
   - Filter by entity type/community

#### API Design

```python
# POST /api/v1/graph/visualize
{
  "center_entity": "entity_123",  # Optional: center around entity
  "radius": 2,                     # Hops from center
  "format": "d3",                  # d3, cytoscape, visjs, json
  "layout": "force",               # force, hierarchical, circular
  "max_nodes": 100,                # Limit for performance
  "filters": {
    "entity_types": ["Person", "Organization"],
    "relationship_types": ["WORKS_AT", "KNOWS"]
  }
}

# Response (D3 format)
{
  "nodes": [
    {
      "id": "entity_123",
      "label": "John Smith",
      "type": "Person",
      "color": "#1f77b4",
      "size": 10,
      "x": 100,  # Optional: pre-computed layout
      "y": 150,
      "properties": {...}
    }
  ],
  "links": [
    {
      "source": "entity_123",
      "target": "entity_456",
      "type": "WORKS_AT",
      "color": "#aec7e8",
      "width": 2,
      "label": "Senior Engineer"
    }
  ],
  "metadata": {
    "node_count": 25,
    "edge_count": 32,
    "communities": 3,
    "layout": "force"
  }
}

# GET /api/v1/graph/entity/{entity_id}/neighborhood
# Returns: Entity + N-hop neighbors in specified format

# GET /api/v1/graph/community/{community_id}/visualize
# Returns: All entities in community + inter-community edges
```

#### Output Formats

**D3.js Format:**
```json
{
  "nodes": [{"id": "...", "label": "...", "type": "..."}],
  "links": [{"source": "...", "target": "...", "type": "..."}]
}
```

**Cytoscape.js Format:**
```json
{
  "elements": {
    "nodes": [{"data": {"id": "...", "label": "..."}}],
    "edges": [{"data": {"source": "...", "target": "..."}}]
  }
}
```

**vis.js Format:**
```json
{
  "nodes": [{"id": "...", "label": "...", "group": "..."}],
  "edges": [{"from": "...", "to": "...", "label": "..."}]
}
```

#### Styling Configuration

```python
# src/core/config.py additions
class Settings(BaseSettings):
    # Graph Visualization Settings (Sprint 6.5)
    graph_viz_max_nodes: int = Field(
        default=100,
        description="Max nodes to return in visualization"
    )
    graph_viz_default_format: str = Field(
        default="d3",
        description="Default output format (d3, cytoscape, visjs)"
    )
    graph_viz_node_size_by: str = Field(
        default="degree",
        description="Node size metric (degree, centrality, fixed)"
    )
    graph_viz_color_by: str = Field(
        default="type",
        description="Node color scheme (type, community, fixed)"
    )
```

#### Acceptance Criteria

- [ ] Visualization API returns valid D3.js, Cytoscape.js, vis.js formats
- [ ] Subgraph extraction limits nodes to max_nodes (default: 100)
- [ ] Node coloring by entity type works correctly
- [ ] Community-based coloring highlights communities
- [ ] Example HTML page renders interactive graph with D3.js
- [ ] API response time <500ms for 100-node subgraph
- [ ] 15+ unit tests passing
- [ ] Integration tests verify format compatibility

#### Git Commit Message

```
feat(graph): add visualization API with D3/Cytoscape/vis.js support

Implements REST API for graph visualization with support for
popular JavaScript libraries (D3.js, Cytoscape.js, vis.js).

Features:
- Subgraph extraction (center entity + radius)
- Entity neighborhood visualization
- Community visualization
- Multiple output formats (D3, Cytoscape, vis.js, JSON)
- Layout hints (force-directed, hierarchical, circular)
- Node coloring by type/community
- Edge styling by relationship type

API Endpoints:
- POST /api/v1/graph/visualize (custom subgraph)
- GET /api/v1/graph/entity/{id}/neighborhood (entity-centric)
- GET /api/v1/graph/community/{id}/visualize (community view)

Formats:
- D3.js: {nodes: [...], links: [...]}
- Cytoscape.js: {elements: {nodes: [...], edges: [...]}}
- vis.js: {nodes: [...], edges: [...]}

Example:
- Included HTML + D3.js demo page
- Interactive zoom, pan, click
- Tooltips on hover

Performance:
- 100-node subgraph: <500ms
- Max nodes configurable (default: 100)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Dependencies

- Sprint 5 (Graph RAG) ✅
- Feature 6.1 (Query builder) ✅
- Feature 6.2 (Query templates - subgraph extraction) ✅
- No new Python dependencies (frontend uses JS libraries)

#### Risks & Mitigation

**Risk 1:** Large subgraphs may timeout or crash frontend
- **Mitigation:** Enforce max_nodes limit, pagination, server-side layout computation

**Risk 2:** Different libraries have incompatible formats
- **Mitigation:** Provide converter functions, extensive testing per format

---

### Feature 6.6: Graph Analytics & Insights 📈

**Priority:** P1 (Business Value)
**Story Points:** 4
**Effort:** 1 day

**Problem Statement:**
No metrics or insights extracted from graph structure:
- Cannot identify influential entities
- Missing bottleneck detection (information flow)
- No recommendations based on graph analysis
- Lack of knowledge gap identification

**Solution:**
Implement graph analytics algorithms (centrality, PageRank, etc.) and provide actionable insights via API.

#### Deliverables

- [ ] `GraphAnalytics` class with 10+ metrics
- [ ] Centrality measures (degree, betweenness, closeness, eigenvector)
- [ ] PageRank for entity importance
- [ ] Knowledge gap detection (orphan entities, sparse areas)
- [ ] Recommendation engine (related entities, missing links)
- [ ] Analytics API endpoint
- [ ] 20+ unit tests for analytics
- [ ] Integration with Neo4j GDS algorithms

#### Technical Tasks

1. **Centrality Metrics (Morning)**
   ```python
   class GraphAnalytics:
       async def degree_centrality(
           self,
           entity_type: str | None = None
       ) -> List[Tuple[str, float]]:
           """Calculate degree centrality (# of connections)."""

       async def betweenness_centrality(
           self,
           entity_type: str | None = None
       ) -> List[Tuple[str, float]]:
           """Calculate betweenness centrality (bridge entities)."""

       async def closeness_centrality(
           self,
           entity_type: str | None = None
       ) -> List[Tuple[str, float]]:
           """Calculate closeness centrality (avg distance to all)."""

       async def eigenvector_centrality(
           self,
           entity_type: str | None = None
       ) -> List[Tuple[str, float]]:
           """Calculate eigenvector centrality (influential connections)."""
   ```

2. **Influence & Importance (Afternoon - Part 1)**
   ```python
   async def pagerank(
       self,
       damping: float = 0.85,
       max_iterations: int = 20
   ) -> List[Tuple[str, float]]:
       """Calculate PageRank scores (Google's algorithm)."""

   async def get_influential_entities(
       self,
       top_k: int = 10,
       metric: str = "pagerank"  # pagerank, degree, betweenness
   ) -> List[Dict[str, Any]]:
       """Get most influential entities by specified metric."""
   ```

3. **Knowledge Gap Detection (Afternoon - Part 2)**
   ```python
   async def find_orphan_entities(
       self,
       max_degree: int = 1
   ) -> List[str]:
       """Find entities with few/no connections."""

   async def find_sparse_regions(
       self,
       density_threshold: float = 0.1
   ) -> List[Dict[str, Any]]:
       """Find under-connected regions (knowledge gaps)."""

   async def find_bridge_entities(
       self
   ) -> List[str]:
       """Find entities connecting disparate communities."""
   ```

4. **Recommendation Engine (Afternoon - Part 3)**
   ```python
   async def recommend_related_entities(
       self,
       entity_id: str,
       top_k: int = 5,
       strategy: str = "collaborative"  # collaborative, content, hybrid
   ) -> List[Dict[str, Any]]:
       """Recommend related entities based on graph structure."""

   async def suggest_missing_links(
       self,
       entity_id: str,
       top_k: int = 5
   ) -> List[Dict[str, Any]]:
       """Suggest likely missing relationships (link prediction)."""
   ```

#### API Design

```python
# GET /api/v1/graph/analytics/centrality
{
  "metric": "degree",  # degree, betweenness, closeness, eigenvector
  "entity_type": "Person",  # Optional filter
  "top_k": 10
}

# Response
{
  "metric": "degree_centrality",
  "results": [
    {
      "entity_id": "entity_123",
      "name": "John Smith",
      "type": "Person",
      "score": 0.85,
      "rank": 1
    }
  ]
}

# GET /api/v1/graph/analytics/pagerank
{
  "damping": 0.85,
  "top_k": 10
}

# GET /api/v1/graph/analytics/gaps
{
  "gap_type": "orphans",  # orphans, sparse_regions, bridges
  "threshold": 0.1
}

# GET /api/v1/graph/recommendations/{entity_id}
{
  "type": "related_entities",  # related_entities, missing_links
  "strategy": "collaborative",
  "top_k": 5
}
```

#### Data Models

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class CentralityScore(BaseModel):
    """Centrality score for an entity."""
    entity_id: str
    name: str
    type: str
    score: float = Field(..., ge=0.0, le=1.0)
    rank: int

class InfluentialEntity(BaseModel):
    """Influential entity with metrics."""
    entity_id: str
    name: str
    type: str
    pagerank: float
    degree: int
    betweenness: float
    communities: List[str]

class KnowledgeGap(BaseModel):
    """Identified knowledge gap."""
    gap_type: str  # orphan, sparse_region, missing_bridge
    entity_ids: List[str]
    severity: float  # 0-1, higher = more severe
    recommendation: str

class EntityRecommendation(BaseModel):
    """Recommended related entity."""
    entity_id: str
    name: str
    type: str
    relevance_score: float
    reason: str  # Why recommended
    common_neighbors: List[str] = Field(default_factory=list)
```

#### Acceptance Criteria

- [ ] All 4 centrality metrics (degree, betweenness, closeness, eigenvector) implemented
- [ ] PageRank calculation matches Neo4j GDS results (validation test)
- [ ] Knowledge gap detection finds orphans and sparse regions
- [ ] Recommendation engine provides 5+ relevant suggestions per entity
- [ ] Analytics API returns results in <2s for 1000-node graph
- [ ] 20+ unit tests passing
- [ ] Integration tests with Neo4j GDS verify correctness

#### Git Commit Message

```
feat(graph): add graph analytics with centrality and PageRank

Implements comprehensive graph analytics including centrality metrics,
influence scoring, and knowledge gap detection.

Features:
- Centrality: degree, betweenness, closeness, eigenvector
- Influence: PageRank with configurable damping
- Knowledge Gaps: orphan entities, sparse regions, bridges
- Recommendations: related entities, missing link prediction
- Top-K ranking for all metrics

Algorithms:
- Neo4j GDS integration for performance
- PageRank: Google's algorithm (damping=0.85, 20 iterations)
- Centrality: normalized scores (0-1 range)

Analytics:
- Degree: # of connections (popularity)
- Betweenness: bridge entities (information flow)
- Closeness: avg distance to all (accessibility)
- Eigenvector: influential connections (network effect)

API:
- GET /api/v1/graph/analytics/centrality
- GET /api/v1/graph/analytics/pagerank
- GET /api/v1/graph/analytics/gaps
- GET /api/v1/graph/recommendations/{entity_id}

Performance:
- 1000-node graph: <2s for all metrics
- Caching for repeated queries

Use Cases:
- Identify key entities (influencers)
- Find bottlenecks (betweenness)
- Detect knowledge gaps (orphans, sparse areas)
- Recommend content (collaborative filtering)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Dependencies

- Sprint 5 (Neo4j backend) ✅
- Feature 6.3 (Community detection - for bridge entities) ✅
- Neo4j GDS plugin ⚠️

#### Risks & Mitigation

**Risk 1:** Analytics may be slow on large graphs
- **Mitigation:** Use Neo4j GDS for performance, cache results, sample-based approximation

**Risk 2:** Recommendations may not be relevant
- **Mitigation:** A/B testing, user feedback loop, multiple strategies

---

## 🔧 Technical Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       Sprint 6 Architecture                  │
└─────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   FastAPI REST   │
                    │      API         │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼─────┐ ┌─────▼────┐ ┌──────▼──────┐
       │  Query     │ │Community │ │  Temporal   │
       │Optimization│ │Detection │ │   Queries   │
       └──────┬─────┘ └─────┬────┘ └──────┬──────┘
              │              │              │
       ┌──────▼──────────────▼──────────────▼──────┐
       │         Neo4j Client (Sprint 5)            │
       └──────────────────┬────────────────────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
       ┌──────▼─────┐ ┌──▼───────┐ ┌─▼──────────┐
       │   Neo4j    │ │ Neo4j    │ │  LightRAG  │
       │ (Graph DB) │ │   GDS    │ │  (Sprint 5)│
       └────────────┘ └──────────┘ └────────────┘
```

### Component Interactions

```python
# Sprint 6 Component Flow

1. Query Optimization (Feature 6.1)
   User Query → CypherQueryBuilder → QueryCache (check)
             → QueryOptimizer → Neo4j → Cache (store) → Result

2. Community Detection (Feature 6.3)
   Graph → Neo4j GDS (Leiden) → Communities
        → LLM (Ollama) → Community Labels → Neo4j (store)

3. Temporal Queries (Feature 6.4)
   Query + Timestamp → TemporalQueryBuilder → Neo4j
                    → Filter by valid_from/valid_to → Result

4. Visualization (Feature 6.5)
   Subgraph Request → Extract Nodes/Edges → Format Converter
                   → D3/Cytoscape/vis.js Format → Frontend

5. Analytics (Feature 6.6)
   Graph → Neo4j GDS (Centrality/PageRank) → Rankings
        → Knowledge Gap Detector → Gaps
        → Recommendation Engine → Suggestions
```

### Data Flow

```
Query Request (API)
    ↓
Query Optimizer (6.1)
    ↓
Temporal Filter (6.4) [if temporal query]
    ↓
Community Filter (6.3) [if community-aware]
    ↓
Neo4j Query Execution
    ↓
Result Caching (6.1)
    ↓
Format Conversion (6.5) [if visualization]
    ↓
Analytics Enrichment (6.6) [if requested]
    ↓
API Response
```

### Database Schema Extensions

```cypher
// Temporal Properties (Sprint 6.4)
CREATE INDEX entity_valid_from_idx IF NOT EXISTS
FOR (e:Entity) ON (e.valid_from);

CREATE INDEX entity_valid_to_idx IF NOT EXISTS
FOR (e:Entity) ON (e.valid_to);

CREATE INDEX entity_version_idx IF NOT EXISTS
FOR (e:Entity) ON (e.version);

// Community Detection (Sprint 6.3)
CREATE INDEX entity_community_idx IF NOT EXISTS
FOR (e:Entity) ON (e.community_id);

CREATE INDEX entity_community_label_idx IF NOT EXISTS
FOR (e:Entity) ON (e.community_label);

// Analytics (Sprint 6.6)
CREATE INDEX entity_pagerank_idx IF NOT EXISTS
FOR (e:Entity) ON (e.pagerank);

CREATE INDEX entity_degree_idx IF NOT EXISTS
FOR (e:Entity) ON (e.degree);

// Full-text search for community labels
CREATE FULLTEXT INDEX community_label_fulltext IF NOT EXISTS
FOR (e:Entity) ON EACH [e.community_label];
```

---

## 📦 Dependencies & Prerequisites

### Sprint Dependencies

- ✅ **Sprint 5 Complete:** LightRAG + Neo4j + Dual-Level Search
- ✅ **Sprint 4 Complete:** LangGraph Router + State Management
- ✅ **Sprint 2-3 Complete:** Vector Search + Advanced Retrieval

### Technical Dependencies

**Python Packages (existing):**
- `neo4j==5.14.0` (driver) ✅
- `lightrag-hku` (from Sprint 5) ✅
- `ollama` (for LLM labeling) ✅
- `structlog` (logging) ✅
- `pydantic>=2.0` (models) ✅

**New Dependencies:**
- `networkx>=3.2` (for fallback algorithms if GDS unavailable)
- No other new packages required

**Neo4j GDS Plugin:**
- Installation: Docker image `neo4j:5.14-enterprise` or manual plugin
- Algorithms needed: Leiden, Louvain, PageRank, Centrality metrics
- **Fallback:** NetworkX implementations if GDS not available

**Infrastructure:**
- Neo4j Community/Enterprise Edition 5.14+
- Minimum 16GB RAM (for 10k+ entities)
- Minimum 4 CPU cores
- 50GB disk space (for indexes + temporal versions)

### Environment Variables

```bash
# Sprint 6 Configuration (.env additions)

# Query Optimization (6.1)
GRAPH_QUERY_CACHE_ENABLED=true
GRAPH_QUERY_CACHE_MAX_SIZE=1000
GRAPH_QUERY_CACHE_TTL_SECONDS=300
GRAPH_BATCH_QUERY_MAX_CONCURRENT=10
GRAPH_QUERY_TIMEOUT_SECONDS=30

# Community Detection (6.3)
GRAPH_COMMUNITY_ALGORITHM=leiden
GRAPH_COMMUNITY_RESOLUTION=1.0
GRAPH_COMMUNITY_MIN_SIZE=5
GRAPH_COMMUNITY_LABELING_ENABLED=true

# Temporal Features (6.4)
GRAPH_TEMPORAL_ENABLED=true
GRAPH_VERSION_RETENTION=10
GRAPH_VERSION_PRUNING_ENABLED=true

# Visualization (6.5)
GRAPH_VIZ_MAX_NODES=100
GRAPH_VIZ_DEFAULT_FORMAT=d3

# Analytics (6.6)
GRAPH_ANALYTICS_ENABLED=true
GRAPH_PAGERANK_DAMPING=0.85
GRAPH_PAGERANK_ITERATIONS=20
```

---

## 🧪 Test Strategy

### Test Coverage Goals

- **Overall:** 90%+ test coverage across Sprint 6 features
- **Unit Tests:** 120+ tests (20+ per feature)
- **Integration Tests:** 25+ tests (Neo4j + GDS)
- **E2E Tests:** 10+ tests (full pipeline)
- **Performance Tests:** 15+ benchmarks

### Test Breakdown by Feature

**Feature 6.1 (Query Optimization):**
- Unit tests: 25 tests
  - Query builder: 10 tests (fluent API, parameterization)
  - Query cache: 8 tests (LRU, TTL, invalidation)
  - Query optimizer: 4 tests (pattern analysis, rewriting)
  - Batch executor: 3 tests (parallel execution, error handling)
- Integration tests: 5 tests (with Neo4j)
- Performance tests: 5 benchmarks (latency reduction)

**Feature 6.2 (Query Templates):**
- Unit tests: 20 tests (1-2 per template)
- Integration tests: 5 tests (template execution)
- Example tests: 5 tests (verify examples work)

**Feature 6.3 (Community Detection):**
- Unit tests: 20 tests
  - Detection: 8 tests (Leiden/Louvain, parameters)
  - Labeling: 6 tests (LLM prompts, caching)
  - Community search: 6 tests (filtering, ranking)
- Integration tests: 5 tests (with Neo4j GDS)
- Validation tests: 5 tests (modularity score, label quality)

**Feature 6.4 (Temporal Features):**
- Unit tests: 18 tests
  - Temporal model: 5 tests (properties, validation)
  - Time-aware queries: 6 tests (point-in-time, range)
  - Versioning: 7 tests (creation, comparison, rollback)
- Integration tests: 5 tests (versioned entities)
- Temporal tests: 5 tests (historical state reconstruction)

**Feature 6.5 (Visualization API):**
- Unit tests: 15 tests
  - Formatters: 9 tests (D3, Cytoscape, vis.js)
  - Subgraph extraction: 6 tests (radius, filtering)
- Integration tests: 5 tests (API endpoints)
- Format validation: 3 tests (schema compliance)

**Feature 6.6 (Analytics):**
- Unit tests: 20 tests
  - Centrality: 8 tests (4 metrics)
  - PageRank: 4 tests (algorithm, ranking)
  - Knowledge gaps: 4 tests (orphans, sparse regions)
  - Recommendations: 4 tests (related, missing links)
- Integration tests: 5 tests (with Neo4j GDS)
- Validation tests: 5 tests (compare with known results)

### Test Data

**Test Graph (500+ entities):**
- Entity types: Person (200), Organization (100), Technology (150), Concept (50)
- Relationships: ~800 edges
- Communities: 5-8 distinct clusters
- Temporal span: 2020-2024 (5 years)

**Test Scenarios:**
1. Simple query optimization (cache hit/miss)
2. Complex multi-hop query (3+ hops)
3. Community detection (5+ communities)
4. Temporal query (point-in-time, range)
5. Visualization export (100-node subgraph)
6. Analytics calculation (all metrics)

### Performance Benchmarks

| Operation | Target Latency | Test Data |
|-----------|---------------|-----------|
| Simple query (cached) | <50ms p95 | 1-hop, 10 entities |
| Complex query (optimized) | <300ms p95 | 3-hop, 50 entities |
| Batch queries (10 queries) | <1500ms | 10 parallel queries |
| Community detection | <5s | 1000-node graph |
| Temporal query | <200ms | 100 entities, 5-year span |
| Visualization export | <500ms | 100-node subgraph |
| PageRank calculation | <3s | 1000-node graph |

---

## ⚠️ Risk Assessment

### High-Priority Risks

**Risk 1: Neo4j GDS Plugin Availability**
- **Severity:** HIGH
- **Probability:** MEDIUM
- **Impact:** Community detection and analytics features compromised
- **Mitigation:**
  - Test with Neo4j Community Edition first (GDS may not be included)
  - Implement fallback using NetworkX for core algorithms
  - Provide degraded mode (slower but functional)
  - Document GDS installation for Enterprise Edition users

**Risk 2: Performance Degradation on Large Graphs**
- **Severity:** HIGH
- **Probability:** MEDIUM
- **Impact:** Query timeouts, slow response times, poor UX
- **Mitigation:**
  - Implement query timeout (30s default)
  - Add pagination for large result sets
  - Use sampling for analytics on graphs >10k entities
  - Monitor query performance and optimize slow patterns
  - Cache frequently accessed subgraphs

**Risk 3: Temporal Version Storage Explosion**
- **Severity:** MEDIUM
- **Probability:** HIGH
- **Impact:** Database size growth, increased costs
- **Mitigation:**
  - Configurable version retention (default: 10)
  - Automatic pruning of old versions
  - Compression for archived versions
  - Monitor disk usage, alert on threshold

**Risk 4: LLM Labeling Inconsistency (Community Labels)**
- **Severity:** MEDIUM
- **Probability:** MEDIUM
- **Impact:** Poor community labels, user confusion
- **Mitigation:**
  - Validate labels with regex patterns
  - Allow manual override/editing
  - Use temperature=0.1 for consistency
  - Cache labels to avoid re-generation
  - Provide feedback mechanism

### Medium-Priority Risks

**Risk 5: Visualization API Overload (Large Subgraphs)**
- **Severity:** MEDIUM
- **Probability:** MEDIUM
- **Impact:** Frontend crashes, slow rendering
- **Mitigation:**
  - Enforce max_nodes limit (default: 100)
  - Server-side layout computation (optional)
  - Progressive loading (render nodes first, edges later)
  - Client-side throttling

**Risk 6: Query Cache Invalidation Complexity**
- **Severity:** MEDIUM
- **Probability:** MEDIUM
- **Impact:** Stale data, incorrect results
- **Mitigation:**
  - Conservative TTL (5 minutes)
  - Invalidate all caches on write operations
  - Add cache version tracking
  - Monitor cache hit/miss rate

**Risk 7: Integration with Sprint 5 (Breaking Changes)**
- **Severity:** MEDIUM
- **Probability:** LOW
- **Impact:** Existing graph queries break
- **Mitigation:**
  - Thorough integration testing
  - Backward compatibility for Sprint 5 APIs
  - Feature flags for Sprint 6 features
  - Gradual rollout

### Low-Priority Risks

**Risk 8: Temporal Query Complexity**
- **Severity:** LOW
- **Probability:** MEDIUM
- **Impact:** Developers struggle with temporal queries
- **Mitigation:**
  - Comprehensive documentation with examples
  - Helper functions for common patterns
  - Error messages with suggestions

**Risk 9: Analytics Metric Interpretation**
- **Severity:** LOW
- **Probability:** MEDIUM
- **Impact:** Users misunderstand metrics
- **Mitigation:**
  - Clear metric descriptions in API docs
  - Visualization of metrics (charts)
  - Examples with explanations

---

## 📅 Implementation Phases

### Phase 1: Query Optimization (Day 1-2)

**Goals:**
- Implement query builder, cache, optimizer, batch executor
- Achieve 40%+ latency reduction
- Test with Sprint 5 graph

**Deliverables:**
- Feature 6.1 complete (query optimization)
- Feature 6.2 complete (query templates)
- 45 unit tests passing
- Performance benchmarks showing improvement

**Success Criteria:**
- [ ] Query cache hit rate >60% on repeated queries
- [ ] Complex queries <300ms p95
- [ ] Batch executor handles 100 queries without failure
- [ ] All tests passing

### Phase 2: Community Detection (Day 2-3)

**Goals:**
- Implement Leiden community detection
- Generate LLM-based community labels
- Integrate with search API

**Deliverables:**
- Feature 6.3 complete (community detection)
- 20 unit tests passing
- 5+ communities detected on test graph
- Community labels generated

**Success Criteria:**
- [ ] Community detection completes in <5s for 1000-node graph
- [ ] Modularity score >0.3
- [ ] Community labels are descriptive and accurate
- [ ] Community filter works in search API

### Phase 3: Temporal & Visualization (Day 3-4)

**Goals:**
- Implement temporal graph model
- Build visualization API
- Test time-aware queries

**Deliverables:**
- Feature 6.4 complete (temporal features)
- Feature 6.5 complete (visualization API)
- 33 unit tests passing
- Example D3.js visualization page

**Success Criteria:**
- [ ] Temporal queries return correct historical state
- [ ] Version tracking works (10 versions retained)
- [ ] Visualization API returns valid D3/Cytoscape formats
- [ ] Example page renders interactive graph

### Phase 4: Analytics & Integration (Day 4-5)

**Goals:**
- Implement graph analytics (centrality, PageRank)
- Integration testing across all Sprint 6 features
- Documentation and examples

**Deliverables:**
- Feature 6.6 complete (analytics)
- 20 unit tests passing
- All integration tests passing
- Sprint 6 documentation complete

**Success Criteria:**
- [ ] All 4 centrality metrics implemented
- [ ] PageRank calculation completes in <3s
- [ ] Knowledge gap detection finds orphans and sparse regions
- [ ] Recommendation engine provides relevant suggestions
- [ ] 90%+ test coverage achieved

### Phase 5: Testing & Polish (Day 5)

**Goals:**
- Comprehensive testing (unit, integration, E2E)
- Performance optimization
- Documentation finalization
- Sprint 6 completion report

**Deliverables:**
- All 120+ tests passing
- Performance benchmarks documented
- SPRINT_6_COMPLETION_REPORT.md
- Examples and API documentation

**Success Criteria:**
- [ ] 90%+ test coverage
- [ ] All performance targets met
- [ ] Zero P0/P1 bugs
- [ ] Documentation review complete

---

## 📊 Timeline Estimates

### Day-by-Day Breakdown

**Day 1: Query Optimization Foundation**
- Morning: Feature 6.1 (Query Builder + Cache) - 4 hours
- Afternoon: Feature 6.1 (Optimizer + Batch) - 4 hours
- Total: 8 hours (1 full day)

**Day 2: Query Templates + Community Detection Start**
- Morning: Feature 6.2 (Query Templates) - 4 hours
- Afternoon: Feature 6.3 (Community Detection - Part 1) - 4 hours
- Total: 8 hours (1 full day)

**Day 3: Community Detection + Temporal Features Start**
- Morning: Feature 6.3 (Community Labeling) - 3 hours
- Afternoon: Feature 6.4 (Temporal Model + Queries) - 5 hours
- Total: 8 hours (1 full day)

**Day 4: Temporal + Visualization + Analytics Start**
- Morning: Feature 6.4 (Versioning) + Feature 6.5 (Visualization) - 4 hours
- Afternoon: Feature 6.6 (Analytics) - 4 hours
- Total: 8 hours (1 full day)

**Day 5: Analytics + Testing + Documentation**
- Morning: Feature 6.6 (Analytics complete) - 2 hours
- Afternoon: Integration testing, documentation, polish - 6 hours
- Total: 8 hours (1 full day)

### Buffer Time

- **Built-in Buffer:** 20% per feature (included in estimates)
- **Sprint Buffer:** 0.5 days at end for unexpected issues
- **Total Sprint Duration:** 5 working days

### Critical Path

```
Day 1: 6.1 Query Optimization (CRITICAL - foundation for all features)
    ↓
Day 2: 6.2 Query Templates (uses 6.1) + 6.3 Community Detection (independent)
    ↓
Day 3: 6.3 Community Labeling (uses 6.1) + 6.4 Temporal (uses 6.1)
    ↓
Day 4: 6.4 Versioning + 6.5 Visualization (uses 6.1, 6.2, 6.3) + 6.6 Analytics (uses 6.1, 6.3)
    ↓
Day 5: 6.6 Analytics complete + Integration Testing + Documentation
```

---

## 📝 Success Criteria Summary

### Feature-Level Success Criteria

**Feature 6.1 (Query Optimization):**
- ✅ Query builder generates valid Cypher for 20+ test cases
- ✅ Cache achieves 60%+ hit rate
- ✅ 40%+ latency reduction for complex queries
- ✅ Batch executor handles 100 concurrent queries
- ✅ 25+ unit tests passing

**Feature 6.2 (Query Templates):**
- ✅ 15+ templates implemented
- ✅ Templates reduce dev time by 10x
- ✅ 20+ unit tests passing
- ✅ Documentation with examples

**Feature 6.3 (Community Detection):**
- ✅ Detects 15+ communities on test graph
- ✅ Modularity score >0.3
- ✅ Community labels are descriptive
- ✅ Community filter in search works
- ✅ 20+ unit tests passing

**Feature 6.4 (Temporal Features):**
- ✅ Point-in-time queries return correct state
- ✅ Version history tracks changes (10 versions)
- ✅ Temporal queries add <50ms overhead
- ✅ 18+ unit tests passing

**Feature 6.5 (Visualization API):**
- ✅ Returns valid D3/Cytoscape/vis.js formats
- ✅ 100-node subgraph renders in <500ms
- ✅ Example D3 page works interactively
- ✅ 15+ unit tests passing

**Feature 6.6 (Analytics):**
- ✅ All 4 centrality metrics implemented
- ✅ PageRank completes in <3s for 1000 nodes
- ✅ Knowledge gap detection finds orphans
- ✅ Recommendations are relevant
- ✅ 20+ unit tests passing

### Sprint-Level Success Criteria

**Performance:**
- ✅ Graph query latency p95 <300ms (vs. 500ms baseline)
- ✅ Support 10,000+ entities without degradation
- ✅ All operations meet target latencies

**Quality:**
- ✅ 90%+ test coverage across Sprint 6
- ✅ 120+ unit tests passing
- ✅ 25+ integration tests passing
- ✅ 10+ E2E tests passing
- ✅ Zero P0/P1 bugs at sprint end

**Functionality:**
- ✅ All 6 features (6.1-6.6) complete and tested
- ✅ Community detection identifies 15+ clusters
- ✅ Analytics API returns 10+ metrics
- ✅ Visualization API renders 100-node graphs
- ✅ Temporal queries work for 5-year span

**Documentation:**
- ✅ SPRINT_6_IMPLEMENTATION_GUIDE.md complete
- ✅ docs/examples/sprint6_examples.md with 40+ examples
- ✅ API documentation updated (OpenAPI)
- ✅ All configuration documented

**Integration:**
- ✅ Backward compatible with Sprint 5
- ✅ No breaking changes to existing APIs
- ✅ Smooth integration with LangGraph router
- ✅ CI/CD pipeline passes all checks

---

## 🔄 Integration with Existing System

### Sprint 5 Integration Points

**LightRAG Wrapper:**
- No changes required (Feature 6.1 uses Neo4j client directly)
- Community detection adds metadata to entities (compatible)
- Temporal properties are additive (non-breaking)

**Dual-Level Search:**
- Feature 6.3 adds community filter (optional parameter)
- Feature 6.1 optimizes underlying queries (transparent)
- No API changes required

**Graph Query Agent:**
- Automatically benefits from query optimization (Feature 6.1)
- Can use community-aware search (Feature 6.3)
- No code changes required

### Sprint 4 Integration (LangGraph Router)

**Router Intent Classification:**
- No changes required
- Graph queries continue to route to graph_query agent
- New analytics queries can route to analytics agent (optional)

**State Management:**
- Community metadata added to state (optional)
- Temporal context added to state (optional)
- Backward compatible with existing state structure

### API Compatibility

**Existing Endpoints (Sprint 5):**
- `/api/v1/graph/query` - unchanged, benefits from optimization
- `/api/v1/graph/insert` - unchanged, adds temporal properties automatically

**New Endpoints (Sprint 6):**
- `/api/v1/graph/visualize` (new)
- `/api/v1/graph/analytics/*` (new)
- `/api/v1/graph/communities` (new)
- All new endpoints, no breaking changes

---

## 📚 Documentation Deliverables

### Required Documentation

1. **SPRINT_6_PLAN.md** (this document)
   - Comprehensive feature breakdown
   - Technical architecture
   - Test strategy
   - Risk assessment

2. **docs/SPRINT_6_IMPLEMENTATION_GUIDE.md**
   - Step-by-step implementation guide
   - Code examples and patterns
   - Testing approach
   - Troubleshooting tips

3. **docs/examples/sprint6_examples.md**
   - 40+ code examples
   - Community detection examples
   - Temporal query examples
   - Visualization API examples
   - Analytics examples

4. **API Documentation Updates**
   - OpenAPI schema updates
   - Endpoint descriptions
   - Request/response examples
   - Error codes

5. **Configuration Documentation**
   - Environment variables
   - Neo4j GDS setup
   - Performance tuning
   - Monitoring setup

### Post-Sprint Documentation

1. **SPRINT_6_COMPLETION_REPORT.md**
   - Summary of achievements
   - Test coverage report
   - Performance benchmarks
   - Known issues and future work

2. **SPRINT_6_SUMMARY.md**
   - High-level overview
   - Key features delivered
   - Metrics and statistics
   - Next steps

---

## 🎯 Sprint Retrospective Questions

### For End of Sprint 6

**What went well?**
- Which features exceeded expectations?
- What optimizations had the biggest impact?
- Which tests caught the most bugs?

**What could be improved?**
- Were time estimates accurate?
- Which features took longer than expected?
- What technical debt was created?

**What did we learn?**
- Neo4j GDS insights
- Community detection best practices
- Temporal modeling lessons
- Performance optimization techniques

**Action items for Sprint 7:**
- What should we continue doing?
- What should we stop doing?
- What should we start doing?

---

## 📞 Support & Resources

### Documentation References

- **Neo4j Cypher Manual:** https://neo4j.com/docs/cypher-manual/
- **Neo4j GDS Documentation:** https://neo4j.com/docs/graph-data-science/
- **LightRAG GitHub:** https://github.com/HKUDS/LightRAG
- **NetworkX Documentation:** https://networkx.org/documentation/stable/
- **D3.js Documentation:** https://d3js.org/
- **Cytoscape.js Documentation:** https://js.cytoscape.org/
- **vis.js Documentation:** https://visjs.org/

### Internal References

- **CLAUDE.md:** Project context and conventions
- **SPRINT_5_PLAN.md:** Previous sprint details
- **SPRINT_5_COMPLETION_REPORT.md:** Sprint 5 outcomes
- **ADR_INDEX.md:** Architecture decision records
- **NAMING_CONVENTIONS.md:** Code style guide

---

## ✅ Ready to Implement Checklist

Before starting Sprint 6, verify:

- [ ] Sprint 5 complete (all features tested)
- [ ] Neo4j running and accessible
- [ ] Neo4j GDS plugin installed (or fallback plan ready)
- [ ] Test data prepared (500+ entity graph)
- [ ] Dependencies installed (`neo4j`, `networkx`)
- [ ] Environment variables configured
- [ ] Git branch created (`sprint-6`)
- [ ] Team capacity confirmed (5 days)
- [ ] SPRINT_6_PLAN.md reviewed and approved

---

**End of Sprint 6 Plan**

For implementation details, see:
- `docs/SPRINT_6_IMPLEMENTATION_GUIDE.md`
- `docs/examples/sprint6_examples.md`

Ready to build advanced graph capabilities! 🚀
