# Section-Based Community Detection - Cypher Queries

**Sprint 62 Feature 62.8: Section-Based Community Detection**

This document provides Cypher queries for section-based community detection and analysis.

## Table of Contents
1. [Community Detection Queries](#community-detection-queries)
2. [Community Retrieval Queries](#community-retrieval-queries)
3. [Cross-Section Analysis Queries](#cross-section-analysis-queries)
4. [Community Metadata Queries](#community-metadata-queries)
5. [Performance Queries](#performance-queries)

---

## Community Detection Queries

### 1. Get Entities in a Section

```cypher
// Get all entities defined in a specific section
MATCH (s:Section)-[:DEFINES]->(e:base)
WHERE s.heading = $section_heading
RETURN e.entity_id AS entity_id,
       e.name AS entity_name,
       e.type AS entity_type
```

**Parameters:**
- `section_heading`: String (e.g., "Introduction")

**Performance:** < 50ms for sections with < 1000 entities

---

### 2. Get Section Subgraph

```cypher
// Get all relationships between entities in a section
MATCH (s:Section {heading: $section_heading})
MATCH (s)-[:DEFINES]->(e1:base)
MATCH (s)-[:DEFINES]->(e2:base)
MATCH (e1)-[r:RELATES_TO]-(e2)
WHERE e1.entity_id < e2.entity_id  // Avoid duplicates
RETURN e1.entity_id AS source,
       e2.entity_id AS target,
       type(r) AS relationship_type
```

**Parameters:**
- `section_heading`: String

**Use Case:** Building NetworkX graph for community detection

---

## Community Retrieval Queries

### 3. Store Community Relationships

```cypher
// Create BELONGS_TO_COMMUNITY relationships
UNWIND $entity_ids AS entity_id
MATCH (e:base {entity_id: entity_id})
MATCH (s:Section {heading: $section_heading})
MERGE (e)-[r:BELONGS_TO_COMMUNITY]->(c:Community {
    community_id: $community_id,
    section_heading: $section_heading
})
ON CREATE SET
    c.created_at = datetime(),
    c.size = $size,
    c.density = $density,
    c.algorithm = $algorithm,
    c.resolution = $resolution
ON MATCH SET
    c.updated_at = datetime(),
    c.size = $size,
    c.density = $density
SET r.assigned_at = datetime()
RETURN count(r) AS relationships_created
```

**Parameters:**
- `entity_ids`: List of strings
- `section_heading`: String
- `community_id`: String (e.g., "section_community_0")
- `size`: Integer
- `density`: Float (0.0 to 1.0)
- `algorithm`: String ("louvain" or "leiden")
- `resolution`: Float

**Graph Schema:**
```
(Entity)-[:BELONGS_TO_COMMUNITY]->(Community)
```

---

### 4. Get Communities in a Section

```cypher
// Retrieve all communities for a section
MATCH (s:Section {heading: $section_heading})
MATCH (e:base)-[:BELONGS_TO_COMMUNITY]->(c:Community)
MATCH (s)-[:DEFINES]->(e)
RETURN c.community_id AS community_id,
       c.size AS size,
       c.density AS density,
       c.algorithm AS algorithm,
       collect(e.entity_id) AS entity_ids
```

**Parameters:**
- `section_heading`: String

**Returns:** List of communities with metadata

---

### 5. Get Community Members

```cypher
// Get all entities in a specific community
MATCH (e:base)-[:BELONGS_TO_COMMUNITY]->(c:Community {community_id: $community_id})
RETURN e.entity_id AS entity_id,
       e.name AS entity_name,
       e.type AS entity_type,
       e.description AS description
```

**Parameters:**
- `community_id`: String

---

## Cross-Section Analysis Queries

### 6. Identify Shared Entities

```cypher
// Find entities that appear in multiple sections
MATCH (s1:Section {heading: $section1})-[:DEFINES]->(e:base)
MATCH (s2:Section {heading: $section2})-[:DEFINES]->(e)
WHERE s1 <> s2
RETURN e.entity_id AS entity_id,
       e.name AS entity_name,
       collect(DISTINCT s1.heading) + collect(DISTINCT s2.heading) AS sections
```

**Parameters:**
- `section1`: String
- `section2`: String

**Use Case:** Building overlap matrix for cross-section comparison

---

### 7. Community Overlap Analysis

```cypher
// Count shared entities between two sections
MATCH (s1:Section {heading: $section1})-[:DEFINES]->(e1:base)
MATCH (s2:Section {heading: $section2})-[:DEFINES]->(e2:base)
WHERE e1 = e2
RETURN count(DISTINCT e1) AS shared_entity_count
```

**Parameters:**
- `section1`: String
- `section2`: String

---

### 8. Identify Section-Specific Communities

```cypher
// Find communities that are specific to one section
MATCH (c:Community {section_heading: $section_heading})
MATCH (e:base)-[:BELONGS_TO_COMMUNITY]->(c)
MATCH (s:Section {heading: $section_heading})-[:DEFINES]->(e)
WITH c, collect(e.entity_id) AS entity_ids

// Check if all entities are only in this section
UNWIND entity_ids AS entity_id
MATCH (other_s:Section)-[:DEFINES]->(:base {entity_id: entity_id})
WHERE other_s.heading <> $section_heading

// If no other sections found, community is section-specific
WITH c, count(other_s) AS other_section_count
WHERE other_section_count = 0

RETURN c.community_id AS community_id,
       c.size AS size,
       c.density AS density
```

**Parameters:**
- `section_heading`: String

---

## Community Metadata Queries

### 9. Update Section Community Metadata

```cypher
// Update section node with community statistics
MATCH (s:Section {heading: $section_heading})
SET s.community_count = $community_count,
    s.last_community_detection = datetime()
RETURN s.heading AS heading
```

**Parameters:**
- `section_heading`: String
- `community_count`: Integer

---

### 10. Get Section Hierarchy with Communities

```cypher
// Get section hierarchy with community counts
MATCH (d:Document {id: $document_id})-[:HAS_SECTION]->(s:Section)
OPTIONAL MATCH (s)-[:DEFINES]->(e:base)-[:BELONGS_TO_COMMUNITY]->(c:Community)
RETURN s.heading AS section_heading,
       s.level AS section_level,
       s.order AS section_order,
       count(DISTINCT c) AS community_count,
       count(DISTINCT e) AS entity_count
ORDER BY s.order ASC
```

**Parameters:**
- `document_id`: String

---

## Performance Queries

### 11. Community Detection Statistics

```cypher
// Get overall community detection statistics
MATCH (c:Community)
RETURN c.algorithm AS algorithm,
       count(c) AS community_count,
       avg(c.size) AS avg_community_size,
       avg(c.density) AS avg_density,
       min(c.created_at) AS first_detection,
       max(c.created_at) AS last_detection
```

**Use Case:** Monitoring and analytics

---

### 12. Section Community Coverage

```cypher
// Check what percentage of entities are in communities
MATCH (s:Section {heading: $section_heading})-[:DEFINES]->(e:base)
WITH count(e) AS total_entities

MATCH (s:Section {heading: $section_heading})-[:DEFINES]->(e:base)
      -[:BELONGS_TO_COMMUNITY]->(:Community)
WITH total_entities, count(DISTINCT e) AS entities_in_communities

RETURN total_entities,
       entities_in_communities,
       (entities_in_communities * 100.0 / total_entities) AS coverage_percentage
```

**Parameters:**
- `section_heading`: String

---

## Advanced Queries

### 13. Find Bridging Entities

```cypher
// Find entities that bridge multiple communities
MATCH (e:base)-[:BELONGS_TO_COMMUNITY]->(c:Community)
WITH e, collect(DISTINCT c.community_id) AS communities
WHERE size(communities) > 1
RETURN e.entity_id AS entity_id,
       e.name AS entity_name,
       communities AS community_ids,
       size(communities) AS community_count
ORDER BY community_count DESC
```

**Use Case:** Identify cross-cutting concepts

---

### 14. Community Density Distribution

```cypher
// Analyze distribution of community densities
MATCH (c:Community {section_heading: $section_heading})
WITH c.density AS density
RETURN
    CASE
        WHEN density < 0.2 THEN 'Very Sparse (< 0.2)'
        WHEN density < 0.4 THEN 'Sparse (0.2-0.4)'
        WHEN density < 0.6 THEN 'Medium (0.4-0.6)'
        WHEN density < 0.8 THEN 'Dense (0.6-0.8)'
        ELSE 'Very Dense (>= 0.8)'
    END AS density_category,
    count(*) AS community_count
```

**Parameters:**
- `section_heading`: String

---

### 15. Temporal Community Evolution

```cypher
// Track how communities change over time (for incremental updates)
MATCH (c:Community {section_heading: $section_heading})
WHERE c.created_at >= datetime($start_date)
  AND c.created_at <= datetime($end_date)
RETURN c.created_at AS detection_time,
       count(c) AS communities_detected,
       avg(c.size) AS avg_size,
       avg(c.density) AS avg_density
ORDER BY c.created_at ASC
```

**Parameters:**
- `section_heading`: String
- `start_date`: ISO 8601 datetime string
- `end_date`: ISO 8601 datetime string

---

## Performance Notes

### Indexing Recommendations

```cypher
// Create indexes for optimal query performance
CREATE INDEX section_heading_idx IF NOT EXISTS FOR (s:Section) ON (s.heading);
CREATE INDEX community_id_idx IF NOT EXISTS FOR (c:Community) ON (c.community_id);
CREATE INDEX entity_id_idx IF NOT EXISTS FOR (e:base) ON (e.entity_id);
```

### Query Optimization Tips

1. **Use Parameters:** Always use parameterized queries for better query plan caching
2. **Limit Results:** Add `LIMIT` clauses for large result sets
3. **Filter Early:** Put most selective filters in the first `MATCH` clause
4. **Avoid Cartesian Products:** Ensure all nodes are connected via relationships
5. **Profile Queries:** Use `EXPLAIN` and `PROFILE` to analyze query performance

### Expected Performance

| Query Type | Target Performance | Notes |
|------------|-------------------|-------|
| Get Section Entities | < 50ms | For sections with < 1000 entities |
| Build Subgraph | < 100ms | For sections with < 500 relationships |
| Store Communities | < 200ms | For communities with < 100 entities |
| Cross-Section Comparison | < 500ms | For 2-5 sections |
| Community Retrieval | < 100ms | With proper indexing |

---

## Graph Schema

```
Document
   |
   +--[:HAS_SECTION]-->Section
                         |
                         +--[:DEFINES]-->Entity (base)
                                           |
                                           +--[:BELONGS_TO_COMMUNITY]-->Community
                                           |
                                           +--[:RELATES_TO]-->Entity
```

**Node Properties:**

- **Section:** `heading`, `level`, `order`, `community_count`, `last_community_detection`
- **Entity (base):** `entity_id`, `name`, `type`, `description`
- **Community:** `community_id`, `section_heading`, `size`, `density`, `algorithm`, `resolution`, `created_at`, `updated_at`

**Relationship Properties:**

- **BELONGS_TO_COMMUNITY:** `assigned_at`

---

## Example Usage

```python
from src.domains.knowledge_graph.communities import get_section_community_detector

detector = get_section_community_detector()

# Detect communities in a section
result = await detector.detect_communities_in_section(
    section_heading="Introduction",
    document_id="doc_123",
    algorithm="louvain",
    resolution=1.0
)

# The above Python code executes these Cypher queries:
# 1. Get section entities (Query #1)
# 2. Get section subgraph (Query #2)
# 3. Store communities (Query #3)
# 4. Update section metadata (Query #9)
```

---

## References

- **Sprint 62 Plan:** `docs/sprints/SPRINT_62_PLAN.md`
- **Feature Documentation:** `docs/sprints/FEATURE_62.8_SECTION_COMMUNITY_DETECTION.md`
- **Neo4j Cypher Manual:** https://neo4j.com/docs/cypher-manual/current/
- **Louvain Algorithm:** https://en.wikipedia.org/wiki/Louvain_method
