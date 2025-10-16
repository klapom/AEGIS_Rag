# Sprint 6 Examples - Advanced Graph Operations

**Sprint:** Sprint 6 - Advanced Graph Operations & Analytics
**Version:** 1.0
**Last Updated:** 2025-10-16

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Query Builder Examples](#query-builder-examples)
3. [Query Cache Examples](#query-cache-examples)
4. [Batch Query Examples](#batch-query-examples)
5. [Query Templates Examples](#query-templates-examples)
6. [Community Detection Examples](#community-detection-examples)
7. [Temporal Query Examples](#temporal-query-examples)
8. [Visualization API Examples](#visualization-api-examples)
9. [Graph Analytics Examples](#graph-analytics-examples)
10. [Production Pipeline Examples](#production-pipeline-examples)

---

## Quick Start

### Minimal Example: Query Optimization in Action

```python
import asyncio
from src.components.graph_rag.optimization.query_builder import CypherQueryBuilder
from src.components.graph_rag.optimization.query_cache import get_query_cache
from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

async def quick_start():
    """Demonstrate query optimization features."""

    # Initialize
    client = Neo4jClientWrapper()
    cache = get_query_cache()

    # 1. Build query programmatically
    builder = CypherQueryBuilder()
    query, params = (
        builder
        .match("(p:Person)")
        .where("p.age > 30")
        .return_("p.name AS name", "p.age AS age")
        .order_by("age DESC")
        .limit(10)
        .build()
    )

    print(f"Query: {query}")
    print(f"Params: {params}")

    # 2. Check cache first
    cached_result = cache.get(query, params)
    if cached_result:
        print("Cache hit!")
        return cached_result

    # 3. Execute query
    result = await client.execute_read(query, params)

    # 4. Store in cache
    cache.set(query, params, result)

    # 5. Get cache stats
    stats = cache.get_stats()
    print(f"Cache stats: {stats}")

    return result

asyncio.run(quick_start())
```

**Expected Output:**
```
Query: MATCH (p:Person)
WHERE p.age > 30
RETURN p.name AS name, p.age AS age
ORDER BY age DESC
LIMIT 10
Params: {}
Cache stats: {'hits': 0, 'misses': 1, 'hit_rate': 0.0, 'size': 1}
```

---

## Query Builder Examples

### Example 1: Simple Entity Query

```python
from src.components.graph_rag.optimization.query_builder import CypherQueryBuilder

def simple_entity_query():
    """Build simple entity query."""
    builder = CypherQueryBuilder()

    query, params = (
        builder
        .match("(e:Entity)")
        .return_("e")
        .limit(10)
        .build()
    )

    print(query)
    # Output:
    # MATCH (e:Entity)
    # RETURN e
    # LIMIT 10

simple_entity_query()
```

### Example 2: Query with WHERE Clause

```python
def query_with_where():
    """Build query with WHERE condition."""
    builder = CypherQueryBuilder()

    query, params = (
        builder
        .match("(p:Person)")
        .where("p.age > 30")
        .where("p.name CONTAINS 'Smith'")
        .return_("p.name", "p.age")
        .build()
    )

    print(query)
    # Output:
    # MATCH (p:Person)
    # WHERE p.age > 30 AND p.name CONTAINS 'Smith'
    # RETURN p.name, p.age

query_with_where()
```

### Example 3: Relationship Pattern

```python
def relationship_pattern():
    """Build query with relationship pattern."""
    builder = CypherQueryBuilder()

    query, params = (
        builder
        .match("(p:Person)")
        .relationship("WORKS_AT", direction="->")
        .match("(o:Organization)")
        .return_("p.name AS person", "o.name AS company")
        .build()
    )

    print(query)
    # Output:
    # MATCH (p:Person)
    # MATCH (p:Person)-[:WORKS_AT]->(o:Organization)
    # RETURN p.name AS person, o.name AS company

relationship_pattern()
```

### Example 4: Variable-Length Path

```python
def variable_length_path():
    """Build query with variable-length relationship."""
    builder = CypherQueryBuilder()

    query, params = (
        builder
        .match("(a:Entity {name: 'John Smith'})")
        .relationship("RELATED_TO", min_hops=1, max_hops=3)
        .match("(b:Entity)")
        .return_("b.name AS connected_entity")
        .limit(20)
        .build()
    )

    print(query)
    # Output:
    # MATCH (a:Entity {name: 'John Smith'})
    # MATCH (a:Entity {name: 'John Smith'})-[:RELATED_TO*1..3]-(b:Entity)
    # RETURN b.name AS connected_entity
    # LIMIT 20

variable_length_path()
```

### Example 5: Parameterized Query (Safety)

```python
def parameterized_query():
    """Build query with parameterization for safety."""
    builder = CypherQueryBuilder()

    # User input (potentially unsafe)
    user_input = "Smith'; DROP TABLE users; --"  # SQL injection attempt

    builder.match("(p:Person)")
    builder.where_in("p.name", [user_input])  # Automatically parameterized
    query, params = builder.return_("p").build()

    print(query)
    print(params)
    # Output:
    # MATCH (p:Person)
    # WHERE p.name IN $param_0
    # RETURN p
    # {'param_0': ["Smith'; DROP TABLE users; --"]}
    # ✅ Safe: injection attempt is parameterized

parameterized_query()
```

### Example 6: Multi-Hop with Filters

```python
async def multi_hop_query():
    """Complex multi-hop query with filters."""
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    builder = CypherQueryBuilder()

    query, params = (
        builder
        .match("(start:Person {name: $start_name})")
        .relationship("KNOWS", min_hops=1, max_hops=2)
        .match("(friend:Person)")
        .where("friend.age > 25")
        .where("friend.name <> $start_name")
        .return_("DISTINCT friend.name AS name", "friend.age AS age")
        .order_by("age DESC")
        .limit(10)
        .build()
    )

    params["start_name"] = "John Smith"

    results = await client.execute_read(query, params)
    print(f"Found {len(results)} friends of friends over 25")

asyncio.run(multi_hop_query())
```

### Example 7: Aggregation Query

```python
def aggregation_query():
    """Build aggregation query."""
    builder = CypherQueryBuilder()

    query, params = (
        builder
        .match("(p:Person)-[:WORKS_AT]->(o:Organization)")
        .with_("o.name AS company", "count(p) AS employee_count")
        .return_("company", "employee_count")
        .order_by("employee_count DESC")
        .limit(5)
        .build()
    )

    print(query)
    # Output:
    # MATCH (p:Person)-[:WORKS_AT]->(o:Organization)
    # WITH o.name AS company, count(p) AS employee_count
    # RETURN company, employee_count
    # ORDER BY employee_count DESC
    # LIMIT 5

aggregation_query()
```

### Example 8: EXPLAIN and PROFILE

```python
async def explain_query():
    """Use EXPLAIN to analyze query performance."""
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    builder = CypherQueryBuilder()

    builder.match("(p:Person)-[:WORKS_AT]->(o:Organization)")
    builder.where("o.name = 'Google'")
    builder.return_("p.name")

    # Get EXPLAIN plan
    explain_query, params = builder.explain()
    explain_result = await client.execute_read(explain_query, params)

    print("Query plan:")
    print(explain_result)

    # Get PROFILE (with execution)
    profile_query, params = builder.profile()
    profile_result = await client.execute_read(profile_query, params)

    print("Execution profile:")
    print(profile_result)

asyncio.run(explain_query())
```

### Example 9: Pagination

```python
def paginated_query(page: int = 0, page_size: int = 10):
    """Build paginated query."""
    builder = CypherQueryBuilder()

    skip_value = page * page_size

    query, params = (
        builder
        .match("(e:Entity)")
        .return_("e.name AS name", "e.type AS type")
        .order_by("name")
        .skip(skip_value)
        .limit(page_size)
        .build()
    )

    print(f"Page {page}: {query}")

# Get page 0 (first 10 entities)
paginated_query(page=0)

# Get page 2 (entities 20-29)
paginated_query(page=2)
```

### Example 10: Complex Pattern Matching

```python
def complex_pattern():
    """Build complex pattern matching query."""
    builder = CypherQueryBuilder()

    query, params = (
        builder
        .match("(p:Person)-[:WORKS_AT]->(o:Organization)")
        .match("(o)-[:LOCATED_IN]->(c:City)")
        .match("(c)-[:PART_OF]->(country:Country)")
        .where("country.name = 'USA'")
        .return_(
            "p.name AS person",
            "o.name AS company",
            "c.name AS city"
        )
        .order_by("city", "company")
        .build()
    )

    print(query)

complex_pattern()
```

---

## Query Cache Examples

### Example 11: Basic Cache Usage

```python
from src.components.graph_rag.optimization.query_cache import GraphQueryCache

def basic_cache_usage():
    """Demonstrate basic cache operations."""
    cache = GraphQueryCache(max_size=100, ttl_seconds=300)

    query = "MATCH (p:Person) RETURN p"
    params = {}

    # First call: cache miss
    result = cache.get(query, params)
    print(f"First call: {result}")  # None

    # Simulate query execution
    fake_result = [{"name": "John"}, {"name": "Jane"}]

    # Store in cache
    cache.set(query, params, fake_result)

    # Second call: cache hit
    result = cache.get(query, params)
    print(f"Second call: {result}")  # [{"name": "John"}, {"name": "Jane"}]

basic_cache_usage()
```

### Example 12: Cache with Different Parameters

```python
def cache_with_parameters():
    """Cache differentiates by parameters."""
    cache = GraphQueryCache()

    query = "MATCH (p:Person {age: $age}) RETURN p"

    # Store for age=30
    cache.set(query, {"age": 30}, [{"name": "John"}])

    # Store for age=40
    cache.set(query, {"age": 40}, [{"name": "Jane"}])

    # Retrieve for age=30
    result30 = cache.get(query, {"age": 30})
    print(f"Age 30: {result30}")  # [{"name": "John"}]

    # Retrieve for age=40
    result40 = cache.get(query, {"age": 40})
    print(f"Age 40: {result40}")  # [{"name": "Jane"}]

cache_with_parameters()
```

### Example 13: Cache Stats Monitoring

```python
def cache_stats_monitoring():
    """Monitor cache performance."""
    cache = GraphQueryCache(max_size=3)

    # Execute some queries
    for i in range(5):
        query = f"MATCH (p:Person) WHERE p.id = {i} RETURN p"

        # Check cache
        result = cache.get(query, {})

        # Simulate query
        if result is None:
            result = [{"id": i}]
            cache.set(query, {}, result)

    # Get stats
    stats = cache.get_stats()
    print(f"Total requests: {stats['hits'] + stats['misses']}")
    print(f"Cache hits: {stats['hits']}")
    print(f"Cache misses: {stats['misses']}")
    print(f"Hit rate: {stats['hit_rate']:.1%}")
    print(f"Evictions: {stats['evictions']}")
    print(f"Current size: {stats['size']}/{stats['max_size']}")

cache_stats_monitoring()
```

### Example 14: Cache Invalidation

```python
def cache_invalidation():
    """Invalidate cache entries."""
    cache = GraphQueryCache()

    # Add some queries
    cache.set("MATCH (p:Person) RETURN p", {}, [{"name": "John"}])
    cache.set("MATCH (o:Organization) RETURN o", {}, [{"name": "Google"}])
    cache.set("MATCH (e:Entity) RETURN e", {}, [{"id": 1}])

    print(f"Cache size before: {cache.get_stats()['size']}")

    # Invalidate by pattern
    invalidated = cache.invalidate(pattern="Person")
    print(f"Invalidated {invalidated} entries")

    print(f"Cache size after: {cache.get_stats()['size']}")

    # Invalidate all
    cache.invalidate()
    print(f"Cache size after clear: {cache.get_stats()['size']}")

cache_invalidation()
```

### Example 15: Cache TTL Expiration

```python
import time

def cache_ttl_expiration():
    """Demonstrate TTL-based expiration."""
    cache = GraphQueryCache(max_size=100, ttl_seconds=2)

    query = "MATCH (p:Person) RETURN p"
    cache.set(query, {}, [{"name": "John"}])

    # Immediate retrieval: success
    result = cache.get(query, {})
    print(f"Immediate: {result}")  # [{"name": "John"}]

    # Wait for expiration
    print("Waiting 3 seconds for TTL expiration...")
    time.sleep(3)

    # After expiration: miss
    result = cache.get(query, {})
    print(f"After expiration: {result}")  # None

cache_ttl_expiration()
```

---

## Batch Query Examples

### Example 16: Basic Batch Execution

```python
async def basic_batch_execution():
    """Execute multiple queries in parallel."""
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper
    from src.components.graph_rag.optimization.batch_executor import BatchQueryExecutor

    client = Neo4jClientWrapper()
    executor = BatchQueryExecutor(client, max_concurrent=5)

    queries = [
        {"query": "MATCH (p:Person) RETURN count(p) AS count", "params": {}, "read_only": True},
        {"query": "MATCH (o:Organization) RETURN count(o) AS count", "params": {}, "read_only": True},
        {"query": "MATCH ()-[r]->() RETURN count(r) AS count", "params": {}, "read_only": True},
    ]

    results = await executor.execute_batch(queries)

    for i, result in enumerate(results):
        if result["status"] == "success":
            print(f"Query {i}: {result['result']}")
        else:
            print(f"Query {i} failed: {result['error']}")

asyncio.run(basic_batch_execution())
```

### Example 17: Batch with Error Handling

```python
async def batch_with_errors():
    """Batch execution handles errors gracefully."""
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper
    from src.components.graph_rag.optimization.batch_executor import BatchQueryExecutor

    client = Neo4jClientWrapper()
    executor = BatchQueryExecutor(client)

    queries = [
        {"query": "MATCH (p:Person) RETURN count(p)", "params": {}, "read_only": True},
        {"query": "INVALID CYPHER QUERY", "params": {}, "read_only": True},  # Will fail
        {"query": "MATCH (o:Organization) RETURN count(o)", "params": {}, "read_only": True},
    ]

    results = await executor.execute_batch(queries)

    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")

    print(f"Success: {success_count}, Errors: {error_count}")
    # Output: Success: 2, Errors: 1

asyncio.run(batch_with_errors())
```

### Example 18: Parallel Entity Lookups

```python
async def parallel_entity_lookups():
    """Look up multiple entities in parallel."""
    from src.components.graph_rag.optimization.batch_executor import BatchQueryExecutor
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    executor = BatchQueryExecutor(client, max_concurrent=10)

    entity_names = ["John Smith", "Jane Doe", "Bob Johnson", "Alice Williams"]

    queries = [
        {
            "query": "MATCH (e:Entity {name: $name}) RETURN e",
            "params": {"name": name},
            "read_only": True,
        }
        for name in entity_names
    ]

    results = await executor.execute_batch(queries)

    found_entities = [
        r["result"][0]["e"]
        for r in results
        if r["status"] == "success" and r["result"]
    ]

    print(f"Found {len(found_entities)} entities out of {len(entity_names)}")

asyncio.run(parallel_entity_lookups())
```

### Example 19: Batch Statistics Collection

```python
async def batch_statistics_collection():
    """Collect multiple statistics in parallel."""
    from src.components.graph_rag.optimization.batch_executor import BatchQueryExecutor
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    executor = BatchQueryExecutor(client)

    queries = [
        {"query": "MATCH (e:Entity) RETURN count(e) AS count", "params": {}, "read_only": True},
        {"query": "MATCH ()-[r]->() RETURN count(r) AS count", "params": {}, "read_only": True},
        {"query": "MATCH (e:Entity) RETURN e.type AS type, count(e) AS count", "params": {}, "read_only": True},
        {"query": "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count", "params": {}, "read_only": True},
    ]

    results = await executor.execute_batch(queries)

    stats = {
        "entity_count": results[0]["result"][0]["count"] if results[0]["status"] == "success" else 0,
        "relationship_count": results[1]["result"][0]["count"] if results[1]["status"] == "success" else 0,
        "entity_types": results[2]["result"] if results[2]["status"] == "success" else [],
        "relationship_types": results[3]["result"] if results[3]["status"] == "success" else [],
    }

    print(f"Graph Statistics: {stats}")

asyncio.run(batch_statistics_collection())
```

### Example 20: Batch Write Operations

```python
async def batch_write_operations():
    """Execute multiple write operations in batch."""
    from src.components.graph_rag.optimization.batch_executor import BatchQueryExecutor
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    executor = BatchQueryExecutor(client, max_concurrent=3)  # Lower concurrency for writes

    entities = [
        {"name": "Alice", "age": 30, "type": "Person"},
        {"name": "Bob", "age": 35, "type": "Person"},
        {"name": "Charlie", "age": 28, "type": "Person"},
    ]

    queries = [
        {
            "query": "CREATE (p:TestPerson {name: $name, age: $age, type: $type})",
            "params": entity,
            "read_only": False,  # Write operation
        }
        for entity in entities
    ]

    results = await executor.execute_batch(queries)

    success_count = sum(1 for r in results if r["status"] == "success")
    print(f"Created {success_count} entities")

    # Cleanup
    await client.execute_write("MATCH (p:TestPerson) DELETE p")

asyncio.run(batch_write_operations())
```

---

## Query Templates Examples

### Example 21: Find Entity by Name

```python
async def find_entity_by_name_example():
    """Use template to find entity by name."""
    from src.components.graph_rag.optimization.query_templates import GraphQueryTemplates
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    templates = GraphQueryTemplates(client)

    # Find person by name
    entity = await templates.find_entity_by_name("John Smith", entity_type="Person")

    if entity:
        print(f"Found: {entity['e']['name']} ({entity['e']['type']})")
    else:
        print("Entity not found")

asyncio.run(find_entity_by_name_example())
```

### Example 22: Get Entity Relationships

```python
async def get_entity_relationships_example():
    """Get all relationships for an entity."""
    from src.components.graph_rag.optimization.query_templates import GraphQueryTemplates
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    templates = GraphQueryTemplates(client)

    # Get all relationships
    relationships = await templates.get_entity_relationships(
        entity_id="entity_123",
        direction="both"
    )

    print(f"Found {len(relationships)} relationships")
    for rel in relationships:
        print(f"  - {rel['r']['type']}")

asyncio.run(get_entity_relationships_example())
```

### Example 23: Find Shortest Path

```python
async def find_shortest_path_example():
    """Find shortest path between two entities."""
    from src.components.graph_rag.optimization.query_templates import GraphQueryTemplates
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    templates = GraphQueryTemplates(client)

    path = await templates.find_shortest_path(
        start_entity="entity_123",
        end_entity="entity_456",
        max_hops=5
    )

    if path:
        print(f"Path length: {len(path)}")
        print(f"Path: {' -> '.join(path)}")
    else:
        print("No path found")

asyncio.run(find_shortest_path_example())
```

### Example 24: Extract Subgraph

```python
async def extract_subgraph_example():
    """Extract subgraph around an entity."""
    from src.components.graph_rag.optimization.query_templates import GraphQueryTemplates
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    templates = GraphQueryTemplates(client)

    subgraph = await templates.extract_subgraph(
        center_entity="entity_123",
        radius=2,
        max_nodes=50
    )

    print(f"Subgraph:")
    print(f"  Nodes: {len(subgraph['nodes'])}")
    print(f"  Edges: {len(subgraph['edges'])}")

    # Entities by type
    types = {}
    for node in subgraph['nodes']:
        node_type = node.get('type', 'Unknown')
        types[node_type] = types.get(node_type, 0) + 1

    print(f"  Entity types: {types}")

asyncio.run(extract_subgraph_example())
```

### Example 25: Count Entities by Type

```python
async def count_entities_by_type_example():
    """Get entity count breakdown by type."""
    from src.components.graph_rag.optimization.query_templates import GraphQueryTemplates
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    templates = GraphQueryTemplates(client)

    counts = await templates.count_entities_by_type()

    print("Entity counts by type:")
    for entity_type, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {entity_type}: {count}")

asyncio.run(count_entities_by_type_example())
```

---

## Community Detection Examples

### Example 26: Detect Communities

```python
async def detect_communities_example():
    """Detect communities in graph."""
    from src.components.graph_rag.community.detector import CommunityDetector
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    detector = CommunityDetector(client, algorithm="leiden")

    communities = await detector.detect_communities(
        resolution=1.0,
        max_iterations=10,
        min_community_size=5
    )

    print(f"Detected {len(communities)} communities")
    for community in communities:
        print(f"  Community {community['id']}: {community['size']} entities")

asyncio.run(detect_communities_example())
```

### Example 27: Label Communities with LLM

```python
async def label_communities_example():
    """Generate human-readable labels for communities."""
    from src.components.graph_rag.community.detector import CommunityDetector
    from src.components.graph_rag.community.labeler import CommunityLabeler
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    detector = CommunityDetector(client)
    labeler = CommunityLabeler()

    # Detect
    communities = await detector.detect_communities()

    # Label
    labeled_communities = await labeler.label_communities(communities)

    print("Labeled communities:")
    for community in labeled_communities:
        print(f"\n{community['label']}")
        print(f"  Description: {community['description']}")
        print(f"  Topics: {', '.join(community['topics'])}")
        print(f"  Size: {community['size']} entities")

asyncio.run(label_communities_example())
```

### Example 28: Store Communities in Neo4j

```python
async def store_communities_example():
    """Store community information in Neo4j."""
    from src.components.graph_rag.community.detector import CommunityDetector
    from src.components.graph_rag.community.labeler import CommunityLabeler
    from src.components.graph_rag.community.storage import CommunityStorage
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    detector = CommunityDetector(client)
    labeler = CommunityLabeler()
    storage = CommunityStorage(client)

    # Detect and label
    communities = await detector.detect_communities()
    labeled_communities = await labeler.label_communities(communities)

    # Store in Neo4j
    updated_count = await storage.store_communities(labeled_communities)

    print(f"Updated {updated_count} entities with community information")

asyncio.run(store_communities_example())
```

### Example 29: Community-Aware Search

```python
async def community_aware_search():
    """Search entities within a specific community."""
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()

    # Search entities in "Machine Learning" community
    query = """
    MATCH (e:Entity)
    WHERE e.community_label CONTAINS 'Machine Learning'
    RETURN e.name AS name, e.type AS type, e.community_label AS community
    LIMIT 20
    """

    results = await client.execute_read(query, {})

    print(f"Found {len(results)} entities in Machine Learning community")
    for result in results:
        print(f"  {result['name']} ({result['type']})")

asyncio.run(community_aware_search())
```

### Example 30: Community Statistics

```python
async def community_statistics():
    """Get statistics for a community."""
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()

    query = """
    MATCH (e:Entity {community_id: $community_id})
    WITH e.community_label AS label,
         count(e) AS size,
         collect(DISTINCT e.type) AS types
    OPTIONAL MATCH (e1:Entity {community_id: $community_id})-[r]-(e2:Entity {community_id: $community_id})
    WITH label, size, types, count(r) AS internal_edges
    RETURN label, size, types, internal_edges
    """

    result = await client.execute_read(query, {"community_id": "community_0"})

    if result:
        stats = result[0]
        print(f"Community: {stats['label']}")
        print(f"  Size: {stats['size']} entities")
        print(f"  Types: {', '.join(stats['types'])}")
        print(f"  Internal edges: {stats['internal_edges']}")

asyncio.run(community_statistics())
```

---

## Temporal Query Examples

### Example 31: Point-in-Time Query

```python
async def point_in_time_query():
    """Query graph state at specific point in time."""
    from datetime import datetime
    from src.components.graph_rag.temporal.query_builder import TemporalQueryBuilder
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    temporal = TemporalQueryBuilder(client)

    # Query entities valid on June 15, 2022
    timestamp = datetime(2022, 6, 15)
    entities = await temporal.at_time(timestamp, entity_type="Person")

    print(f"Entities valid on {timestamp.date()}:")
    for entity in entities:
        e = entity['e']
        print(f"  {e['name']} ({e['type']})")

asyncio.run(point_in_time_query())
```

### Example 32: Time-Range Query

```python
async def time_range_query():
    """Query entities valid during a time range."""
    from datetime import datetime
    from src.components.graph_rag.temporal.query_builder import TemporalQueryBuilder
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    temporal = TemporalQueryBuilder(client)

    # Query entities valid during 2022
    start = datetime(2022, 1, 1)
    end = datetime(2022, 12, 31)

    entities = await temporal.during_range(start, end, entity_type="Organization")

    print(f"Organizations active during 2022: {len(entities)}")

asyncio.run(time_range_query())
```

### Example 33: Entity Evolution Timeline

```python
async def entity_evolution_timeline():
    """Track entity changes over time."""
    from datetime import datetime
    from src.components.graph_rag.temporal.query_builder import TemporalQueryBuilder
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    temporal = TemporalQueryBuilder(client)

    # Get evolution of entity from 2020 to 2024
    evolution = await temporal.evolution(
        entity_id="entity_123",
        start=datetime(2020, 1, 1),
        end=datetime(2024, 1, 1)
    )

    print(f"Entity evolution ({len(evolution)} versions):")
    for version in evolution:
        e = version['e']
        print(f"  v{e.get('version', 1)}: {e.get('created_at', 'N/A')}")
        print(f"    Name: {e.get('name', 'N/A')}")
        print(f"    Description: {e.get('description', 'N/A')[:50]}...")

asyncio.run(entity_evolution_timeline())
```

### Example 34: Create Version on Update

```python
async def create_version_on_update():
    """Create new version when updating entity."""
    from src.components.graph_rag.temporal.version_manager import VersionManager
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    vm = VersionManager(client)

    # Update entity (automatically creates version)
    changes = {
        "description": "Updated description",
        "age": 31,
    }

    version_id = await vm.create_version("entity_123", changes)
    print(f"Created version: {version_id}")

asyncio.run(create_version_on_update())
```

### Example 35: Compare Versions

```python
async def compare_versions_example():
    """Compare two versions of an entity."""
    from src.components.graph_rag.temporal.version_manager import VersionManager
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    vm = VersionManager(client)

    diff = await vm.compare_versions(
        entity_id="entity_123",
        version1=1,
        version2=3
    )

    print("Version comparison (v1 → v3):")

    if diff["added"]:
        print(f"  Added properties: {diff['added']}")

    if diff["removed"]:
        print(f"  Removed properties: {diff['removed']}")

    if diff["changed"]:
        print("  Changed properties:")
        for key, change in diff["changed"].items():
            print(f"    {key}: {change['from']} → {change['to']}")

asyncio.run(compare_versions_example())
```

---

## Visualization API Examples

### Example 36: D3.js Format Export

```python
async def d3_format_export():
    """Export subgraph in D3.js format."""
    from src.components.graph_rag.visualization.formatter import GraphVisualizer
    from src.components.graph_rag.optimization.query_templates import GraphQueryTemplates
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    templates = GraphQueryTemplates(client)
    visualizer = GraphVisualizer()

    # Extract subgraph
    subgraph = await templates.extract_subgraph("entity_123", radius=2, max_nodes=50)

    # Format for D3.js
    d3_data = await visualizer.format_for_d3(subgraph['nodes'], subgraph['edges'])

    print(f"D3.js data:")
    print(f"  Nodes: {len(d3_data['nodes'])}")
    print(f"  Links: {len(d3_data['links'])}")

    # Save to file
    import json
    with open("graph_d3.json", "w") as f:
        json.dump(d3_data, f, indent=2)

    print("Saved to graph_d3.json")

asyncio.run(d3_format_export())
```

### Example 37: Visualization API Endpoint

```python
# Example FastAPI endpoint (add to src/api/v1/graph.py)

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()

@router.post("/visualize")
async def visualize_subgraph(
    center_entity: Optional[str] = None,
    radius: int = Query(default=2, ge=1, le=5),
    format: str = Query(default="d3", regex="^(d3|cytoscape|visjs|json)$"),
    max_nodes: int = Query(default=100, le=500),
):
    """Extract and format subgraph for visualization.

    Args:
        center_entity: Entity ID to center around
        radius: Hops from center (1-5)
        format: Output format (d3, cytoscape, visjs, json)
        max_nodes: Max nodes to return

    Returns:
        Formatted graph data
    """
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper
    from src.components.graph_rag.optimization.query_templates import GraphQueryTemplates
    from src.components.graph_rag.visualization.formatter import GraphVisualizer

    client = Neo4jClientWrapper()
    templates = GraphQueryTemplates(client)
    visualizer = GraphVisualizer()

    # Extract subgraph
    if center_entity:
        subgraph = await templates.extract_subgraph(center_entity, radius, max_nodes)
    else:
        # Get random sample
        nodes = await client.execute_read(
            "MATCH (e:Entity) RETURN e LIMIT $max_nodes",
            {"max_nodes": max_nodes}
        )
        edges = await client.execute_read(
            "MATCH (a:Entity)-[r]->(b:Entity) RETURN a.id AS source, b.id AS target, type(r) AS type LIMIT 200",
            {}
        )
        subgraph = {"nodes": [n['e'] for n in nodes], "edges": edges}

    # Format
    if format == "d3":
        data = await visualizer.format_for_d3(subgraph['nodes'], subgraph['edges'])
    elif format == "cytoscape":
        data = await visualizer.format_for_cytoscape(subgraph['nodes'], subgraph['edges'])
    elif format == "visjs":
        data = await visualizer.format_for_visjs(subgraph['nodes'], subgraph['edges'])
    else:  # json
        data = subgraph

    return {
        "format": format,
        "metadata": {
            "node_count": len(subgraph['nodes']),
            "edge_count": len(subgraph['edges']),
            "center_entity": center_entity,
            "radius": radius,
        },
        "data": data,
    }
```

### Example 38: HTML + D3.js Interactive Visualization

```html
<!-- Example: static/graph_viz.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Graph Visualization</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body { margin: 0; }
        svg { width: 100vw; height: 100vh; }
        .node { stroke: #fff; stroke-width: 2px; cursor: pointer; }
        .link { stroke: #999; stroke-opacity: 0.6; }
        .label { font-size: 10px; pointer-events: none; }
    </style>
</head>
<body>
    <svg id="graph"></svg>
    <script>
        // Fetch graph data from API
        fetch('/api/v1/graph/visualize?center_entity=entity_123&format=d3')
            .then(response => response.json())
            .then(data => {
                const graph = data.data;

                // Set up SVG
                const width = window.innerWidth;
                const height = window.innerHeight;
                const svg = d3.select("#graph");

                // Create force simulation
                const simulation = d3.forceSimulation(graph.nodes)
                    .force("link", d3.forceLink(graph.links).id(d => d.id).distance(100))
                    .force("charge", d3.forceManyBody().strength(-300))
                    .force("center", d3.forceCenter(width / 2, height / 2));

                // Draw links
                const link = svg.append("g")
                    .selectAll("line")
                    .data(graph.links)
                    .enter().append("line")
                    .attr("class", "link")
                    .attr("stroke-width", d => d.width || 1);

                // Draw nodes
                const node = svg.append("g")
                    .selectAll("circle")
                    .data(graph.nodes)
                    .enter().append("circle")
                    .attr("class", "node")
                    .attr("r", d => d.size || 5)
                    .attr("fill", d => d.color || "#69b3a2")
                    .call(d3.drag()
                        .on("start", dragstarted)
                        .on("drag", dragged)
                        .on("end", dragended));

                // Node labels
                const label = svg.append("g")
                    .selectAll("text")
                    .data(graph.nodes)
                    .enter().append("text")
                    .attr("class", "label")
                    .text(d => d.label);

                // Tooltip
                node.append("title")
                    .text(d => `${d.label}\nType: ${d.type}`);

                // Update positions on tick
                simulation.on("tick", () => {
                    link
                        .attr("x1", d => d.source.x)
                        .attr("y1", d => d.source.y)
                        .attr("x2", d => d.target.x)
                        .attr("y2", d => d.target.y);

                    node
                        .attr("cx", d => d.x)
                        .attr("cy", d => d.y);

                    label
                        .attr("x", d => d.x + 10)
                        .attr("y", d => d.y + 3);
                });

                // Drag functions
                function dragstarted(event, d) {
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                }

                function dragged(event, d) {
                    d.fx = event.x;
                    d.fy = event.y;
                }

                function dragended(event, d) {
                    if (!event.active) simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                }
            });
    </script>
</body>
</html>
```

---

## Graph Analytics Examples

### Example 39: Calculate Degree Centrality

```python
async def degree_centrality_example():
    """Calculate degree centrality for entities."""
    from src.components.graph_rag.analytics.centrality import GraphAnalytics
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    analytics = GraphAnalytics(client)

    # Calculate degree centrality
    centrality_scores = await analytics.degree_centrality(entity_type="Person")

    print("Top 10 entities by degree centrality:")
    for entity_id, score in centrality_scores[:10]:
        print(f"  {entity_id}: {score:.3f}")

asyncio.run(degree_centrality_example())
```

### Example 40: PageRank for Influence Scoring

```python
async def pagerank_example():
    """Calculate PageRank scores."""
    from src.components.graph_rag.analytics.centrality import GraphAnalytics
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    analytics = GraphAnalytics(client)

    # Calculate PageRank
    pagerank_scores = await analytics.pagerank(damping=0.85, max_iterations=20)

    print("Top 10 most influential entities:")
    for entity_id, score in pagerank_scores[:10]:
        print(f"  {entity_id}: {score:.6f}")

asyncio.run(pagerank_example())
```

### Example 41: Knowledge Gap Detection

```python
async def knowledge_gap_detection():
    """Detect knowledge gaps (orphan entities, sparse regions)."""
    from src.components.graph_rag.analytics.gaps import KnowledgeGapDetector
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    detector = KnowledgeGapDetector(client)

    # Find orphan entities (no connections)
    orphans = await detector.find_orphan_entities(max_degree=1)
    print(f"Found {len(orphans)} orphan entities")

    # Find sparse regions (low density)
    sparse_regions = await detector.find_sparse_regions(density_threshold=0.1)
    print(f"Found {len(sparse_regions)} sparse regions")

asyncio.run(knowledge_gap_detection())
```

### Example 42: Entity Recommendations

```python
async def entity_recommendations():
    """Get entity recommendations based on graph structure."""
    from src.components.graph_rag.analytics.recommendations import RecommendationEngine
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    client = Neo4jClientWrapper()
    engine = RecommendationEngine(client)

    # Recommend related entities
    recommendations = await engine.recommend_related_entities(
        entity_id="entity_123",
        top_k=5,
        strategy="collaborative"
    )

    print("Recommended related entities:")
    for rec in recommendations:
        print(f"  {rec['name']} (relevance: {rec['relevance_score']:.2f})")
        print(f"    Reason: {rec['reason']}")

asyncio.run(entity_recommendations())
```

---

## Production Pipeline Examples

### Example 43: Complete Graph Optimization Pipeline

```python
"""
Production-ready graph optimization pipeline.

Demonstrates:
- Query building and optimization
- Caching strategy
- Batch operations
- Community detection
- Temporal queries
- Visualization export
- Analytics
"""

import asyncio
from typing import Any, Dict, List

from src.components.graph_rag.neo4j_client import Neo4jClientWrapper
from src.components.graph_rag.optimization.query_builder import CypherQueryBuilder
from src.components.graph_rag.optimization.query_cache import get_query_cache
from src.components.graph_rag.optimization.batch_executor import BatchQueryExecutor
from src.components.graph_rag.optimization.query_templates import GraphQueryTemplates
from src.components.graph_rag.community.detector import CommunityDetector
from src.components.graph_rag.community.labeler import CommunityLabeler
from src.components.graph_rag.community.storage import CommunityStorage


class GraphOptimizationPipeline:
    """Production pipeline for graph operations."""

    def __init__(self):
        """Initialize pipeline."""
        self.client = Neo4jClientWrapper()
        self.cache = get_query_cache()
        self.executor = BatchQueryExecutor(self.client, max_concurrent=10)
        self.templates = GraphQueryTemplates(self.client)
        self.community_detector = CommunityDetector(self.client)
        self.community_labeler = CommunityLabeler()
        self.community_storage = CommunityStorage(self.client)

    async def optimize_query(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute query with caching."""
        # Check cache
        cached = self.cache.get(query, params)
        if cached:
            return cached

        # Execute query
        result = await self.client.execute_read(query, params)

        # Cache result
        self.cache.set(query, params, result)

        return result

    async def batch_entity_lookup(self, entity_names: List[str]) -> List[Dict[str, Any]]:
        """Look up multiple entities in parallel."""
        queries = [
            {
                "query": "MATCH (e:Entity {name: $name}) RETURN e",
                "params": {"name": name},
                "read_only": True,
            }
            for name in entity_names
        ]

        results = await self.executor.execute_batch(queries)

        return [
            r["result"][0]["e"]
            for r in results
            if r["status"] == "success" and r["result"]
        ]

    async def detect_and_label_communities(self) -> List[Dict[str, Any]]:
        """Detect communities and generate labels."""
        # Detect
        communities = await self.community_detector.detect_communities(
            resolution=1.0,
            min_community_size=5
        )

        # Label
        labeled = await self.community_labeler.label_communities(communities)

        # Store
        await self.community_storage.store_communities(labeled)

        return labeled

    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Collect graph statistics in parallel."""
        queries = [
            {"query": "MATCH (e:Entity) RETURN count(e) AS count", "params": {}, "read_only": True},
            {"query": "MATCH ()-[r]->() RETURN count(r) AS count", "params": {}, "read_only": True},
        ]

        results = await self.executor.execute_batch(queries)

        return {
            "entity_count": results[0]["result"][0]["count"],
            "relationship_count": results[1]["result"][0]["count"],
        }

    async def extract_and_visualize(
        self,
        center_entity: str,
        radius: int = 2
    ) -> Dict[str, Any]:
        """Extract subgraph and format for visualization."""
        subgraph = await self.templates.extract_subgraph(
            center_entity,
            radius,
            max_nodes=100
        )

        return {
            "nodes": len(subgraph["nodes"]),
            "edges": len(subgraph["edges"]),
            "data": subgraph,
        }


async def main():
    """Run production pipeline."""
    pipeline = GraphOptimizationPipeline()

    # 1. Get statistics
    print("Collecting statistics...")
    stats = await pipeline.get_graph_statistics()
    print(f"  Entities: {stats['entity_count']}")
    print(f"  Relationships: {stats['relationship_count']}")

    # 2. Detect communities
    print("\nDetecting communities...")
    communities = await pipeline.detect_and_label_communities()
    print(f"  Found {len(communities)} communities")
    for comm in communities[:5]:
        print(f"    - {comm['label']} ({comm['size']} entities)")

    # 3. Batch entity lookup
    print("\nLooking up entities...")
    entities = await pipeline.batch_entity_lookup(["John Smith", "Jane Doe"])
    print(f"  Found {len(entities)} entities")

    # 4. Extract and visualize
    if entities:
        print("\nExtracting subgraph...")
        viz_data = await pipeline.extract_and_visualize(entities[0]["id"], radius=2)
        print(f"  Subgraph: {viz_data['nodes']} nodes, {viz_data['edges']} edges")

    # 5. Cache stats
    cache_stats = pipeline.cache.get_stats()
    print(f"\nCache statistics:")
    print(f"  Hit rate: {cache_stats['hit_rate']:.1%}")
    print(f"  Size: {cache_stats['size']}/{cache_stats['max_size']}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Summary

This document provided 43 comprehensive examples for Sprint 6 features:

1. **Query Optimization (Examples 1-10):** Query builder, parameterization, complex patterns
2. **Query Cache (Examples 11-15):** Caching, TTL, invalidation, stats
3. **Batch Queries (Examples 16-20):** Parallel execution, error handling, writes
4. **Query Templates (Examples 21-25):** Pre-built patterns, subgraph extraction
5. **Community Detection (Examples 26-30):** Detection, labeling, storage, search
6. **Temporal Queries (Examples 31-35):** Point-in-time, ranges, versioning
7. **Visualization (Examples 36-38):** D3.js export, API endpoints, interactive HTML
8. **Analytics (Examples 39-42):** Centrality, PageRank, gaps, recommendations
9. **Production Pipeline (Example 43):** Complete production-ready implementation

All examples are production-ready and demonstrate best practices for Sprint 6 features.

For more information:
- SPRINT_6_PLAN.md (high-level plan)
- SPRINT_6_IMPLEMENTATION_GUIDE.md (step-by-step guide)
