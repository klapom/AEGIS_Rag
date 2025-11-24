# Neo4j Section Nodes Tests - Sprint 32 Feature 32.4

## Overview

This test suite provides comprehensive unit and integration testing for the Neo4j Section Nodes feature (Sprint 32, Feature 32.4).

The tests verify:
- Section node creation with correct properties
- Section-chunk relationships (CONTAINS_CHUNK)
- Section-entity relationships (DEFINES)
- Hierarchical section queries
- Empty section handling
- Batch operations
- Statistics and analytics

## Test Files

### Unit Tests
**File:** `tests/unit/components/graph_rag/test_section_nodes.py`

Provides 20 unit tests covering:
- **Section Node Creation** (3 tests)
  - `test_section_node_creation` - Verify Section nodes created with correct properties
  - `test_section_node_properties` - Verify section properties stored correctly
  - `test_hierarchical_section_levels` - Verify section hierarchy levels identified

- **Section-Chunk Relationships** (2 tests)
  - `test_section_chunk_relationships` - Verify CONTAINS_CHUNK relationships
  - `test_multi_chunk_sections` - Verify sections can contain multiple chunks

- **Section-Entity Relationships** (2 tests)
  - `test_section_entity_relationships` - Verify DEFINES relationships
  - `test_section_multiple_entities` - Verify sections can define multiple entities

- **Edge Cases** (3 tests)
  - `test_empty_section_handling` - Handle empty sections gracefully
  - `test_section_without_bbox` - Handle sections without bounding boxes
  - `test_section_metadata_preservation` - Preserve metadata through creation

- **Section Queries** (3 tests)
  - `test_query_sections_by_heading` - Query sections by heading name
  - `test_query_sections_by_page` - Query sections by page number
  - `test_query_hierarchical_sections` - Query section hierarchy

- **Batch Operations** (2 tests)
  - `test_batch_create_sections` - Batch creation of section nodes
  - `test_batch_create_section_relationships` - Batch creation of relationships

- **Updates** (2 tests)
  - `test_update_section_metadata` - Update section metadata
  - `test_add_section_parent_child_link` - Add parent-child links

- **Statistics** (3 tests)
  - `test_count_sections` - Count total sections
  - `test_count_section_chunks` - Count chunks per section
  - `test_count_section_entities` - Count entities per section

### Integration Tests
**File:** `tests/integration/test_section_node_ingestion.py`

Provides 7 integration tests covering:
- **End-to-End Ingestion** (1 test)
  - `test_end_to_end_section_ingestion` - Complete flow: extract → chunk → ingest

- **Hierarchical Queries** (1 test)
  - `test_hierarchical_section_queries` - Query entities by section hierarchy

- **Entity Re-ranking** (1 test)
  - `test_section_based_entity_reranking` - Re-rank entities by section

- **Citation Enhancement** (1 test)
  - `test_citation_enhancement_with_sections` - Generate enhanced citations with sections

- **Analytics** (3 tests)
  - `test_section_fragmentation_metrics` - Measure section fragmentation
  - `test_false_relation_reduction_with_sections` - Reduce false relations with sections
  - `test_section_cleanup_and_deletion` - Clean up section nodes

## Running the Tests

### Run All Tests
```bash
# Unit tests only
pytest tests/unit/components/graph_rag/test_section_nodes.py -v

# Integration tests only
pytest tests/integration/test_section_node_ingestion.py -v

# All section node tests
pytest tests/unit/components/graph_rag/test_section_nodes.py \
        tests/integration/test_section_node_ingestion.py -v
```

### Run Specific Test
```bash
pytest tests/unit/components/graph_rag/test_section_nodes.py::test_section_node_creation -v
```

### Run with Coverage
```bash
pytest tests/unit/components/graph_rag/test_section_nodes.py \
        tests/integration/test_section_node_ingestion.py \
        --cov=src/components/ingestion/langgraph_nodes \
        --cov=src/components/graph_rag \
        --cov-report=html
```

### Run by Marker
```bash
# Unit tests only
pytest -m "not integration" tests/unit/components/graph_rag/test_section_nodes.py -v

# Integration tests only
pytest -m integration tests/integration/test_section_node_ingestion.py -v
```

## Test Structure

### Unit Tests Pattern
```python
@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for isolated testing."""
    driver = AsyncMock()
    # ... setup mocks
    return driver

@pytest.mark.asyncio
async def test_feature():
    """Test description."""
    # Arrange: Setup test data
    # Act: Execute test
    # Assert: Verify results
```

### Integration Tests Pattern
```python
@pytest.fixture
async def neo4j_test_session():
    """Mock Neo4j session for integration testing."""
    session = AsyncMock()
    # ... setup mocks
    return session

@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_flow():
    """Test complete flow."""
    # Arrange: Setup complete data
    # Act: Execute full pipeline
    # Assert: Verify all components
```

## Test Fixtures

### Common Fixtures

**`mock_neo4j_driver`** - Mocked Neo4j async driver
- Used for unit tests
- Provides mocked session.run() method
- Returns query results

**`sample_sections`** - Sample SectionMetadata objects
- 3 sections with levels 1, 2, 3
- PowerPoint-style hierarchy
- Full metadata (heading, page, bbox, tokens)

**`sample_chunks`** - Sample AdaptiveChunk objects
- 2 adaptive chunks with merged sections
- Multi-section metadata tracking
- Realistic token counts

**`sample_entities`** - Sample extracted entities
- 2 entities with types and descriptions
- Linked to specific chunks
- Realistic metadata

**`sample_powerpoint_sections`** - Real PowerPoint example
- 6 sections from 3 slides
- Three-level hierarchy
- PowerPoint chunking scenario

**`sample_adaptive_chunks`** - Real adaptive chunks
- 3 chunks from merged sections
- 6 sections → 3 chunks (50% fragmentation reduction)
- Realistic PowerPoint example

**`sample_extracted_entities`** - Real extracted entities
- 4 entities from architecture domain
- Types: CONCEPT, COMPONENT, PATTERN, MECHANISM
- Linked to chunks

## Expected Results

### Unit Tests
- **20 tests** - All passing
- **Duration** - ~5 seconds
- **Coverage** - >80% for langgraph_nodes.py section-related functions

### Integration Tests
- **7 tests** - All passing
- **Duration** - ~6 seconds
- **Scope** - End-to-end pipeline testing

### Total
- **27 tests** - All passing
- **Duration** - ~10 seconds total

## Coverage Goals

- **SectionMetadata dataclass** - 100%
- **AdaptiveChunk dataclass** - 100%
- **Section node operations** - >85%
- **Section relationship operations** - >85%
- **Section query operations** - >80%

## Architecture & Design

### Section Node Schema
```
:section {
  section_id: str
  heading: str
  level: int (1, 2, 3)
  page_no: int
  bbox: {l, t, r, b}
  created_at: datetime
}
```

### Relationships
- **CONTAINS_CHUNK** - Section → Chunk (section contains this chunk)
- **DEFINES** - Section → Entity (entity defined in this section)
- **HAS_SUBSECTION** - Section → Section (parent-child hierarchy)

### Metadata Preservation
- Multi-section tracking per chunk (section_headings list)
- Page numbers per section
- Bounding boxes for spatial queries
- Primary section identification

## Common Issues & Solutions

### Test Failures

**Issue:** `AdaptiveChunk has no attribute 'pages'`
**Solution:** Use `section_pages` instead of `pages` (correct field name)

**Issue:** `mock_neo4j_driver.run.call_count` not available
**Solution:** Use AsyncMock for proper method tracking

**Issue:** Empty section handling
**Solution:** Test both empty and non-empty sections, verify graceful handling

## Related Files

- `src/components/ingestion/langgraph_nodes.py` - SectionMetadata & AdaptiveChunk definitions
- `src/components/ingestion/section_extraction.py` - Section extraction logic
- `src/components/graph_rag/lightrag_wrapper.py` - Neo4j integration
- `tests/conftest.py` - Global pytest fixtures
- `tests/unit/components/graph_rag/conftest.py` - Graph RAG-specific fixtures

## Sprint 32 Context

**Feature:** 32.4 - Neo4j Section Nodes (13 SP)
**Status:** Tests created and passing (Deferred backend implementation)
**Objective:** Comprehensive test coverage for section node functionality

**Related Features:**
- 32.1 - Section Extraction (8 SP) - COMPLETE
- 32.2 - Adaptive Section Merging (13 SP) - COMPLETE
- 32.3 - Multi-Section Metadata in Qdrant (8 SP) - COMPLETE

## Future Enhancements

1. **Real Neo4j Container Testing**
   - Use testcontainers library for real Neo4j instance
   - Test transaction handling and rollback
   - Performance benchmarks

2. **Extended Analytics**
   - Section similarity queries
   - Cross-document section linking
   - Section-based recommendation system

3. **Hierarchical Operations**
   - Section tree traversal
   - Ancestor/descendant queries
   - Path-based analytics

4. **Temporal Queries**
   - Section versioning
   - Change tracking
   - Time-based retrieval

## Contact & Support

For issues or questions about these tests:
1. Check the test docstrings for expected behavior
2. Review fixture setup for test data structure
3. Consult Sprint 32 documentation for feature context
4. Check CLAUDE.md for testing patterns and conventions
