# Section Nodes - Hierarchical Query Examples

**Feature:** Sprint 32 Feature 32.4
**ADR:** ADR-039 (Adaptive Section-Aware Chunking)
**Implementation:** `src/components/graph_rag/neo4j_client.py::create_section_nodes()`

## Overview

Section nodes provide a hierarchical structure for document organization in Neo4j, enabling powerful queries based on document structure rather than just content similarity.

### Graph Schema

```cypher
(:Document {id: "doc123"})
  -[:HAS_SECTION {order: 0}]->
    (:Section {
      heading: "Multi-Server Architecture",
      level: 1,
      page_no: 1,
      order: 0,
      bbox_left: 50.0,
      bbox_top: 30.0,
      bbox_right: 670.0,
      bbox_bottom: 80.0,
      token_count: 245,
      text_preview: "A multi-server architecture...",
      created_at: datetime()
    })
      -[:CONTAINS_CHUNK]-> (:chunk {chunk_id: "abc123...", text: "..."})
        -[:MENTIONED_IN]- (:base {entity_name: "Load Balancer"})
      -[:DEFINES]-> (:base {entity_name: "Multi-Server", entity_type: "TECHNOLOGY"})
```

### Relationship Types

1. **Document -[:HAS_SECTION]-> Section** - Ordered document structure
2. **Section -[:CONTAINS_CHUNK]-> chunk** - Chunks belonging to section
3. **Section -[:DEFINES]-> base** - Entities defined in section
4. **base -[:MENTIONED_IN]-> chunk** - Entity mentions (existing)

## Hierarchical Query Examples

### 1. Find All Sections in Document

```cypher
MATCH (d:Document {id: "doc123"})-[:HAS_SECTION]->(s:Section)
RETURN s.heading AS section, s.level AS level, s.page_no AS page
ORDER BY s.order
```

**Use Case:** Display document table of contents

### 2. Find All Entities in Specific Section

```cypher
MATCH (s:Section {heading: "Load Balancing"})-[:DEFINES]->(e:base)
RETURN e.entity_name AS entity, e.entity_type AS type
```

**Use Case:** Get entities discussed in a specific topic (e.g., "Load Balancing")

### 3. Find Sections Mentioning Specific Entity

```cypher
MATCH (s:Section)-[:DEFINES]->(e:base {entity_name: "Cache"})
RETURN s.heading AS section, s.page_no AS page
ORDER BY s.order
```

**Use Case:** Find where "Cache" is discussed across document

### 4. Multi-Level Section Hierarchy

```cypher
MATCH (d:Document {id: "doc123"})-[:HAS_SECTION]->(s1:Section)
WHERE s1.level = 1
OPTIONAL MATCH (d)-[:HAS_SECTION]->(s2:Section)
WHERE s2.level = 2 AND s2.order > s1.order
WITH s1, s2
WHERE NOT EXISTS {
  MATCH (d)-[:HAS_SECTION]->(s3:Section)
  WHERE s3.level = 1 AND s3.order > s1.order AND s3.order < s2.order
}
RETURN s1.heading AS parent_section, collect(s2.heading) AS subsections
ORDER BY s1.order
```

**Use Case:** Display hierarchical document outline (main sections + subsections)

### 5. Find Chunks with Context

```cypher
MATCH (s:Section {heading: "Multi-Server Architecture"})-[:CONTAINS_CHUNK]->(c:chunk)
RETURN c.chunk_id AS chunk_id,
       c.text AS text,
       s.heading AS section,
       s.page_no AS page
```

**Use Case:** Retrieve chunks with section context for citation enhancement

### 6. Section-Based Similarity Search

```cypher
// Find semantically similar sections (based on entity overlap)
MATCH (s1:Section {heading: "Load Balancing"})-[:DEFINES]->(e:base)<-[:DEFINES]-(s2:Section)
WHERE s1 <> s2
WITH s2, count(e) AS shared_entities
ORDER BY shared_entities DESC
LIMIT 5
RETURN s2.heading AS similar_section,
       shared_entities,
       s2.page_no AS page
```

**Use Case:** Recommend related sections based on entity overlap

### 7. Cross-Section Entity Relationships

```cypher
// Find entities that span multiple sections
MATCH (e:base)<-[:DEFINES]-(s:Section)
WITH e, collect(s.heading) AS sections
WHERE size(sections) > 1
RETURN e.entity_name AS entity,
       e.entity_type AS type,
       sections
ORDER BY size(sections) DESC
```

**Use Case:** Identify key entities discussed across multiple topics

### 8. Section-Level PageRank

```cypher
// Calculate importance of sections based on entity connections
CALL gds.pageRank.stream('section-graph', {
  nodeLabels: ['Section'],
  relationshipTypes: ['DEFINES']
})
YIELD nodeId, score
MATCH (s:Section)
WHERE id(s) = nodeId
RETURN s.heading AS section, score
ORDER BY score DESC
LIMIT 10
```

**Use Case:** Identify most important sections for document summarization

### 9. Section-Based Citation Enhancement

```cypher
// Enhance Qdrant retrieval with section metadata
MATCH (s:Section)-[:CONTAINS_CHUNK]->(c:chunk {chunk_id: $qdrant_point_id})
RETURN s.heading AS section,
       s.page_no AS page,
       s.level AS level,
       '[' + toString(s.page_no) + '] ' + $document_name + ' - Section: ' + s.heading AS citation
```

**Use Case:** Generate rich citations like "[1] doc.pdf - Section: 'Load Balancing' (Page 2)"

### 10. Filtered Entity Search by Section Type

```cypher
// Find technical entities only in Level 1 sections (main topics)
MATCH (s:Section)-[:DEFINES]->(e:base)
WHERE s.level = 1 AND e.entity_type IN ['TECHNOLOGY', 'PRODUCT']
RETURN DISTINCT e.entity_name AS entity, collect(s.heading) AS sections
```

**Use Case:** Extract high-level technical concepts (main topics only)

## Performance Considerations

### Indexes

Recommended indexes for optimal query performance:

```cypher
CREATE INDEX section_heading IF NOT EXISTS FOR (s:Section) ON (s.heading);
CREATE INDEX section_order IF NOT EXISTS FOR (s:Section) ON (s.order);
CREATE INDEX section_page IF NOT EXISTS FOR (s:Section) ON (s.page_no);
CREATE INDEX section_level IF NOT EXISTS FOR (s:Section) ON (s.level);
```

### Query Optimization Tips

1. **Use Specific Labels:** Always specify `:Section` label in MATCH clauses
2. **Limit Results:** Use `LIMIT` for large documents (e.g., `LIMIT 10`)
3. **Index Lookups:** Filter by `heading`, `order`, or `page_no` for faster lookups
4. **Avoid Full Scans:** Use `WHERE` clauses to reduce candidate nodes
5. **Profile Queries:** Use `PROFILE` or `EXPLAIN` to analyze query plans

## Integration with Qdrant Retrieval

Section nodes complement Qdrant's vector search:

1. **Step 1:** Qdrant retrieves semantically relevant chunks (vector similarity)
2. **Step 2:** Neo4j enriches results with section context
3. **Step 3:** Re-rank by section relevance (boost chunks from high-priority sections)
4. **Step 4:** Generate enhanced citations with section names

**Example Pipeline:**

```python
# 1. Qdrant: Get relevant chunks
chunks = await qdrant.search(query, limit=20)

# 2. Neo4j: Get section context for each chunk
for chunk in chunks:
    section_info = await neo4j.execute_query(
        """
        MATCH (s:Section)-[:CONTAINS_CHUNK]->(c:chunk {chunk_id: $chunk_id})
        RETURN s.heading AS section, s.page_no AS page
        """,
        {"chunk_id": chunk.id}
    )
    chunk.metadata["section"] = section_info["section"]
    chunk.metadata["page"] = section_info["page"]

# 3. Re-rank by section priority (e.g., boost "Introduction" sections)
chunks = rerank_by_section_priority(chunks, priority_sections=["Introduction", "Architecture"])

# 4. Generate citations
for idx, chunk in enumerate(chunks):
    citation = f"[{idx+1}] {chunk.metadata['document']} - Section: '{chunk.metadata['section']}' (Page {chunk.metadata['page']})"
```

## Testing Hierarchical Queries

Use Neo4j Browser or Cypher Shell to test queries:

```bash
# Connect to Neo4j
cypher-shell -u neo4j -p your_password

# Test query
MATCH (d:Document)-[:HAS_SECTION]->(s:Section)
RETURN count(s) AS total_sections;

# Verify relationships
MATCH (s:Section)-[r]->(n)
RETURN type(r) AS relationship, count(*) AS count
ORDER BY count DESC;
```

## Backward Compatibility

Section nodes are **optional enhancements** and do not break existing functionality:

- Existing entity/relation queries work unchanged
- MENTIONED_IN relationships remain primary provenance mechanism
- Section nodes add hierarchical layer on top of existing graph

**Graceful Degradation:**
- If section nodes missing: Fall back to chunk-level provenance
- If section creation fails: Log warning, continue ingestion
- If hierarchical queries fail: Use flat entity queries

## Future Enhancements

Potential future improvements to section-based queries:

1. **Section Embeddings:** Generate embeddings for entire sections (summary vectors)
2. **Cross-Document Section Matching:** Find similar sections across different documents
3. **Section-Level Community Detection:** Group related sections across corpus
4. **Temporal Section Evolution:** Track how sections change across document versions
5. **Section-Based RAG:** Use section embeddings for retrieval (alternative to chunk embeddings)

---

**Last Updated:** 2025-11-24
**Sprint:** Sprint 32 Feature 32.4
**Status:** Implemented & Tested
