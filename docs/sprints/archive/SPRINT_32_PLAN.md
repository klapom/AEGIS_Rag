# Sprint 32 Plan: Adaptive Section-Aware Chunking & Admin E2E Testing
**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Sprint:** 32
**Duration:** 2025-11-21 → 2025-11-28 (7 days)
**Status:** 📋 PLANNED
**Branch:** `sprint-32-adaptive-chunking`

---

## 📋 TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [Sprint Context](#sprint-context)
3. [Sprint Goals](#sprint-goals)
4. [Feature Breakdown](#feature-breakdown)
5. [Technical Architecture](#technical-architecture)
6. [Testing Strategy](#testing-strategy)
7. [Success Criteria](#success-criteria)
8. [Risk Management](#risk-management)
9. [Timeline & Milestones](#timeline--milestones)

---

## 🎯 Executive Summary

**Mission:** Implement adaptive section-aware chunking (ADR-039) to improve extraction quality and complete comprehensive Admin UI E2E testing with Playwright.

**Key Deliverables:**
1. ✅ **Adaptive Section-Aware Chunking** (ADR-039 implementation)
2. ✅ **Multi-Section Metadata Tracking** (section headings, pages, bounding boxes)
3. ✅ **Neo4j Section Nodes** (hierarchical knowledge graph)
4. ✅ **Admin E2E Tests** (Playwright, comprehensive coverage)
5. ✅ **PowerPoint Chunking Optimization** (6-8 chunks vs 124 tiny chunks)

**Expected Impact:**
- **Extraction Quality:** -15% false positive relations (cleaner knowledge graph)
- **Retrieval Precision:** +10% section-based re-ranking
- **Citation Accuracy:** 100% (precise section references)
- **Admin UI Confidence:** 95% (comprehensive E2E coverage)

---

## 📖 Sprint Context

### Background

**Sprint 31 Achievements:**
- ✅ E2E Test Infrastructure (Playwright with 111 tests: 100 User + 11 Admin)
- ✅ HomePage → ChatPage Transformation (chat interface on `/`)
- ✅ AdminIndexingPage Implementation (document indexing UI)
- ✅ Frontend Dependency Optimization (react-force-graph migration)

**Sprint 31 Learnings:**
- Feature 31.12 analysis revealed chunking issues (PowerPoint slides merge 8-10 into one chunk)
- Fixed 1800-token chunking doesn't respect document section boundaries
- Result: +23% false relations in LightRAG, +15% hallucination rate

**ADR-039 Decision:**
- **ACCEPTED:** Adaptive Section-Aware Chunking with Multi-Section Metadata (2025-11-21)
- **Problem:** Fixed-size chunks (1800 tokens) span multiple sections → Mixed topics → Noisy graph
- **Solution:** Adaptive merging (large sections >1200 tokens standalone, small sections <1200 tokens merged)
- **Metadata:** Track ALL sections in chunk (section_headings, section_pages, section_bboxes)

### Related ADRs
- **ADR-022:** Unified Chunking Service (Fixed 1800-token chunks, Sprint 16)
- **ADR-026:** Pure LLM Extraction (Default pipeline, Sprint 20)
- **ADR-027:** Docling Container Architecture (JSON structure for sections, Sprint 21)
- **ADR-037:** Alibaba Cloud Extraction (Qwen3-32B for high-quality extraction, Sprint 28)
- **ADR-039:** Adaptive Section-Aware Chunking (THIS SPRINT)

---

## 🎯 Sprint Goals

### Primary Goals

**Goal 1: Implement Adaptive Section-Aware Chunking (ADR-039)**
- Extract section hierarchy from Docling JSON
- Implement adaptive merging logic (800-1200 token thresholds)
- Add multi-section metadata to chunks
- Backward compatible with existing chunks

**Goal 2: Enhance Neo4j Knowledge Graph with Section Nodes**
- Add Section nodes to Neo4j schema
- Create `(:Section)-[:CONTAINS_CHUNK]->(:Chunk)` relationships
- Enable hierarchical queries ("Find all entities in section X")
- Preserve provenance chain (Document → Section → Chunk → Entity)

**Goal 3: Improve Retrieval with Section-Based Re-Ranking**
- Add section heading boost to hybrid search
- Use multi-section metadata for citation generation
- Format: "[1] document.pdf - Section: 'Load Balancing' (Page 2)"

**Goal 4: Complete Admin UI E2E Testing (Playwright)**
- Directory Indexing UI tests (progress, cancellation, error handling)
- Graph Analytics tests (community detection, PageRank)
- Cost Dashboard tests (budget tracking, provider breakdown)
- Settings tests (configuration management)

### Secondary Goals

**Goal 5: PowerPoint Chunking Validation**
- Benchmark chunking on OMNITRACKER PowerPoint files
- Validate 6-8 chunks (vs 124 tiny chunks baseline)
- Measure extraction quality improvement

**Goal 6: Documentation & ADR Updates**
- Update CLAUDE.md with Sprint 32 status
- Create comprehensive Sprint 32 Summary
- Document section-aware patterns for future sprints

---

## 🚀 Feature Breakdown

### Feature 32.1: Section Extraction from Docling JSON (8 SP)
**Owner:** backend-agent
**Priority:** P0 (Blocking for all other features)

**Deliverables:**
- `extract_section_hierarchy()` function in `langgraph_nodes.py`
- Parse Docling JSON for section headings (title, subtitle-level-1, subtitle-level-2)
- Extract bounding boxes and page numbers for each section
- Return structured SectionMetadata objects

**Technical Tasks:**
```python
# src/components/ingestion/langgraph_nodes.py

@dataclass
class SectionMetadata:
    """Section metadata extracted from Docling JSON."""
    heading: str
    level: int  # 1 = title, 2 = subtitle-level-1, 3 = subtitle-level-2
    page_no: int
    bbox: Dict[str, float]  # {"l": 50, "t": 30, "r": 670, "b": 80}
    text: str
    token_count: int

def extract_section_hierarchy(docling_json: Dict[str, Any]) -> List[SectionMetadata]:
    """
    Extract section hierarchy from Docling JSON.

    Docling JSON structure:
    {
      "pages": [
        {
          "cells": [
            {"type": "title", "text": "Multi-Server Architecture", "bbox": {...}},
            {"type": "subtitle-level-1", "text": "Load Balancing", "bbox": {...}},
            {"type": "text", "text": "Round-robin algorithm...", "bbox": {...}}
          ]
        }
      ]
    }

    Returns:
        List of SectionMetadata objects with heading, text, page, bbox
    """
    sections = []
    current_section = None

    for page in docling_json["pages"]:
        for cell in page["cells"]:
            if cell["type"] in ["title", "subtitle-level-1", "subtitle-level-2"]:
                # New section detected
                if current_section:
                    sections.append(current_section)
                current_section = SectionMetadata(
                    heading=cell["text"],
                    level=_get_heading_level(cell["type"]),
                    page_no=page["page_no"],
                    bbox=cell["bbox"],
                    text="",
                    token_count=0
                )
            elif current_section:
                # Accumulate body text
                current_section.text += cell["text"] + "\n"
                current_section.token_count = count_tokens(current_section.text)

    if current_section:
        sections.append(current_section)

    return sections
```

**Tests:**
- `test_extract_sections_from_docling_json()` - Parse PowerPoint JSON
- `test_section_hierarchy_levels()` - Validate heading levels
- `test_bbox_extraction()` - Verify bounding box coordinates
- `test_empty_sections()` - Handle sections with no body text

**Success Criteria:**
- ✅ Extract all sections from OMNITRACKER PowerPoint (15 slides → 15 sections)
- ✅ Correctly identify heading levels (H1, H2, H3)
- ✅ Preserve bounding box coordinates
- ✅ 100% test coverage

---

### Feature 32.2: Adaptive Section Merging Logic (13 SP)
**Owner:** backend-agent
**Priority:** P0 (Core algorithm)

**Deliverables:**
- `adaptive_section_chunking()` function with merging logic
- Support for large sections (>1200 tokens → standalone chunk)
- Support for small sections (<1200 tokens → merge until 800-1800 tokens)
- Multi-section metadata tracking

**Technical Tasks:**
```python
# src/components/ingestion/langgraph_nodes.py

@dataclass
class AdaptiveChunk:
    """Chunk with multi-section metadata."""
    text: str
    token_count: int
    section_headings: List[str]
    section_pages: List[int]
    section_bboxes: List[Dict[str, float]]
    primary_section: str  # First section (main topic)
    metadata: Dict[str, Any]  # Additional metadata

def adaptive_section_chunking(
    sections: List[SectionMetadata],
    min_chunk: int = 800,
    max_chunk: int = 1800,
    large_section_threshold: int = 1200
) -> List[AdaptiveChunk]:
    """
    Chunk with section-awareness, merging small sections intelligently.

    Rules:
    1. Large section (>1200 tokens): Keep as standalone chunk
    2. Small sections (<1200 tokens): Merge until 800-1800 tokens
    3. Track ALL sections in chunk metadata (multi-section support)
    4. Preserve thematic coherence when merging

    Args:
        sections: List of SectionMetadata from extract_section_hierarchy()
        min_chunk: Minimum tokens per chunk (default 800)
        max_chunk: Maximum tokens per chunk (default 1800)
        large_section_threshold: Threshold for standalone sections (default 1200)

    Returns:
        List of AdaptiveChunk with multi-section metadata
    """
    chunks = []
    current_sections = []
    current_tokens = 0

    for section in sections:
        section_tokens = section.token_count

        # Large section → standalone chunk (preserve clean extraction)
        if section_tokens > large_section_threshold:
            if current_sections:
                chunks.append(_merge_sections(current_sections))
                current_sections = []
                current_tokens = 0

            chunks.append(_create_chunk(section))

        # Small section → merge with others (reduce fragmentation)
        elif current_tokens + section_tokens <= max_chunk:
            current_sections.append(section)
            current_tokens += section_tokens

        # Current batch full → flush and start new
        else:
            chunks.append(_merge_sections(current_sections))
            current_sections = [section]
            current_tokens = section_tokens

    # Flush remaining sections
    if current_sections:
        chunks.append(_merge_sections(current_sections))

    return chunks

def _merge_sections(sections: List[SectionMetadata]) -> AdaptiveChunk:
    """Merge multiple sections into one chunk with multi-section metadata."""
    return AdaptiveChunk(
        text="\n\n".join(s.text for s in sections),
        token_count=sum(s.token_count for s in sections),
        section_headings=[s.heading for s in sections],
        section_pages=[s.page_no for s in sections],
        section_bboxes=[s.bbox for s in sections],
        primary_section=sections[0].heading,
        metadata={
            "source": sections[0].metadata.get("source"),
            "file_type": sections[0].metadata.get("file_type"),
            "num_sections": len(sections)
        }
    )
```

**Tests:**
- `test_large_section_standalone()` - 1500-token section → standalone chunk
- `test_small_sections_merged()` - 3x 400-token sections → 1 chunk (1200 tokens)
- `test_multi_section_metadata()` - Verify section_headings, section_pages tracking
- `test_powerpoint_chunking()` - 15 slides → 6-8 chunks (not 124)
- `test_thematic_coherence()` - Related sections grouped together

**Success Criteria:**
- ✅ PowerPoint (15 slides, 150-250 tokens each) → 6-8 chunks
- ✅ Large sections (>1200 tokens) → standalone chunks
- ✅ Small sections merged until 800-1800 tokens
- ✅ All section metadata preserved (headings, pages, bboxes)

---

### Feature 32.3: Multi-Section Metadata in Qdrant (8 SP)
**Owner:** backend-agent
**Priority:** P1 (Retrieval improvement)

**Deliverables:**
- Update Qdrant ingestion to use adaptive chunks
- Store multi-section metadata in Qdrant payloads
- Add section heading boost to hybrid search
- Update citation generation to use section metadata

**Technical Tasks:**
```python
# src/components/vector_search/qdrant_client.py

async def ingest_with_section_metadata(
    chunks: List[AdaptiveChunk],
    collection_name: str
) -> None:
    """
    Ingest chunks with multi-section metadata into Qdrant.

    Payload structure:
    {
        "text": "Multi-Server Architecture\n\nLoad Balancing...",
        "section_headings": ["Multi-Server Architecture", "Load Balancing", "Caching"],
        "section_pages": [1, 2, 3],
        "section_bboxes": [{"l": 50, "t": 30, "r": 670, "b": 80}, ...],
        "primary_section": "Multi-Server Architecture",
        "source": "PerformanceTuning.pptx",
        "num_sections": 3
    }
    """
    points = []
    for idx, chunk in enumerate(chunks):
        embedding = await embed_text(chunk.text)
        points.append(
            PointStruct(
                id=idx,
                vector=embedding,
                payload={
                    "text": chunk.text,
                    "section_headings": chunk.section_headings,
                    "section_pages": chunk.section_pages,
                    "section_bboxes": chunk.section_bboxes,
                    "primary_section": chunk.primary_section,
                    "source": chunk.metadata["source"],
                    "num_sections": chunk.metadata["num_sections"]
                }
            )
        )

    await qdrant_client.upsert(collection_name=collection_name, points=points)
```

**Hybrid Search Enhancement:**
```python
# src/components/vector_search/hybrid_search.py

def section_based_reranking(results: List[Document], query: str) -> List[Document]:
    """
    Boost results when query matches section headings.

    Example:
    Query: "What is load balancing?"
    Result: section_headings = ["Multi-Server", "Load Balancing", "Caching"]
    Boost: 0.15 (1/3 sections match)
    """
    for result in results:
        headings = result.metadata.get("section_headings", [])
        matches = sum(1 for h in headings if query.lower() in h.lower())
        boost = (matches / len(headings)) * 0.3 if headings else 0
        result.score += boost

    return sorted(results, key=lambda x: x.score, reverse=True)
```

**Tests:**
- `test_section_metadata_storage()` - Verify Qdrant payload structure
- `test_section_heading_boost()` - Query "load balancing" boosts matching chunks
- `test_citation_with_sections()` - Format: "[1] doc.pdf - Section: 'Load Balancing' (Page 2)"
- `test_multi_section_retrieval()` - Retrieve chunks with multiple sections

**Success Criteria:**
- ✅ Section metadata stored in Qdrant payloads
- ✅ +10% retrieval precision with section-based re-ranking
- ✅ Citations include section names
- ✅ 100% backward compatibility (existing chunks work)

---

### Feature 32.4: Neo4j Section Nodes (13 SP)
**Owner:** backend-agent
**Priority:** P2 (Graph enhancement, optional for Sprint 32)

**Deliverables:**
- Add Section nodes to Neo4j schema
- Create `(:Document)-[:HAS_SECTION]->(:Section)` relationships
- Create `(:Section)-[:CONTAINS_CHUNK]->(:Chunk)` relationships
- Create `(:Section)-[:DEFINES]->(:Entity)` relationships (hierarchical queries)

**Technical Tasks:**
```python
# src/components/graph_rag/lightrag_client.py

async def create_section_nodes(
    document_id: str,
    sections: List[SectionMetadata],
    chunks: List[AdaptiveChunk]
) -> None:
    """
    Create Section nodes in Neo4j with hierarchical relationships.

    Graph Schema:
    (:Document {id: "doc123"})
      -[:HAS_SECTION]-> (:Section {
          title: "Multi-Server Architecture",
          page_no: 1,
          order: 1,
          bbox: {...}
      })
        -[:CONTAINS_CHUNK]-> (:Chunk {id: "chunk_0", tokens: 1050})
          -[:MENTIONS]-> (:Entity {name: "Load Balancer"})

    Direct section-to-entity link (for hierarchical queries):
    (:Section {title: "Multi-Server Architecture"})
      -[:DEFINES]-> (:Entity {name: "Multi-Server"})
    """
    async with neo4j_session() as session:
        # Create Section nodes
        for idx, section in enumerate(sections):
            await session.run("""
                MATCH (doc:Document {id: $doc_id})
                CREATE (s:Section {
                    title: $title,
                    page_no: $page_no,
                    order: $order,
                    bbox: $bbox
                })
                CREATE (doc)-[:HAS_SECTION]->(s)
            """, {
                "doc_id": document_id,
                "title": section.heading,
                "page_no": section.page_no,
                "order": idx,
                "bbox": section.bbox
            })

        # Link chunks to sections
        for chunk in chunks:
            for section_heading in chunk.section_headings:
                await session.run("""
                    MATCH (s:Section {title: $section_heading})
                    MATCH (c:Chunk {id: $chunk_id})
                    CREATE (s)-[:CONTAINS_CHUNK]->(c)
                """, {
                    "section_heading": section_heading,
                    "chunk_id": chunk.id
                })

        # Create Section-Entity links (extracted from chunk entities)
        await session.run("""
            MATCH (s:Section)-[:CONTAINS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity)
            CREATE (s)-[:DEFINES]->(e)
        """)
```

**Hierarchical Queries:**
```cypher
// Query: Find all entities in section "Load Balancing"
MATCH (s:Section {title: "Load Balancing"})-[:DEFINES]->(e:Entity)
RETURN e.name, e.type

// Query: Find all sections that mention entity "Cache"
MATCH (s:Section)-[:DEFINES]->(e:Entity {name: "Cache"})
RETURN s.title, s.page_no
```

**Tests:**
- `test_section_node_creation()` - Create Section nodes for PowerPoint
- `test_section_chunk_relationships()` - Verify CONTAINS_CHUNK links
- `test_section_entity_relationships()` - Verify DEFINES links
- `test_hierarchical_queries()` - Query entities by section

**Success Criteria:**
- ✅ Section nodes created for all documents
- ✅ Hierarchical relationships preserved
- ✅ Hierarchical queries work ("Find entities in section X")
- ✅ Backward compatible (optional migration)

---

### Feature 32.5: Admin UI E2E Tests - Directory Indexing (8 SP)
**Owner:** frontend-agent + testing-agent
**Priority:** P1 (Admin UI confidence)

**Deliverables:**
- Playwright tests for AdminIndexingPage
- Progress tracking tests (SSE streaming)
- Cancellation tests (abort indexing)
- Error handling tests (invalid paths, permissions)

**Test Structure:**
```typescript
// frontend/tests/e2e/admin/indexing.spec.ts

describe('Admin Indexing Page', () => {
  test('should display indexing form with directory input', async ({ page }) => {
    await page.goto('http://localhost:3000/admin/indexing');

    // Verify form elements
    await expect(page.getByTestId('directory-input')).toBeVisible();
    await expect(page.getByTestId('start-indexing-button')).toBeVisible();
    await expect(page.getByTestId('cancel-indexing-button')).toBeDisabled();
  });

  test('should show progress during indexing with SSE updates', async ({ page }) => {
    await page.goto('http://localhost:3000/admin/indexing');

    // Start indexing
    await page.getByTestId('directory-input').fill('/test/documents');
    await page.getByTestId('start-indexing-button').click();

    // Wait for SSE progress updates
    await expect(page.getByTestId('progress-bar')).toBeVisible();
    await expect(page.getByTestId('progress-percentage')).toContainText(/\d+%/);
    await expect(page.getByTestId('current-file')).toBeVisible();

    // Wait for completion
    await expect(page.getByTestId('indexing-complete-message')).toBeVisible({ timeout: 60000 });
    await expect(page.getByTestId('indexed-count')).toContainText(/\d+ documents/);
  });

  test('should allow cancellation during indexing', async ({ page }) => {
    await page.goto('http://localhost:3000/admin/indexing');

    // Start indexing
    await page.getByTestId('directory-input').fill('/test/large-corpus');
    await page.getByTestId('start-indexing-button').click();

    // Wait for progress, then cancel
    await expect(page.getByTestId('progress-bar')).toBeVisible();
    await page.getByTestId('cancel-indexing-button').click();

    // Verify cancellation
    await expect(page.getByTestId('indexing-cancelled-message')).toBeVisible();
    await expect(page.getByTestId('start-indexing-button')).toBeEnabled();
  });

  test('should handle invalid directory path gracefully', async ({ page }) => {
    await page.goto('http://localhost:3000/admin/indexing');

    // Submit invalid path
    await page.getByTestId('directory-input').fill('/invalid/path/does/not/exist');
    await page.getByTestId('start-indexing-button').click();

    // Verify error message
    await expect(page.getByTestId('error-message')).toBeVisible();
    await expect(page.getByTestId('error-message')).toContainText(/invalid.*path/i);
  });

  test('should display indexing history table', async ({ page }) => {
    await page.goto('http://localhost:3000/admin/indexing');

    // Verify history table
    await expect(page.getByTestId('indexing-history-table')).toBeVisible();
    await expect(page.getByTestId('history-row')).toHaveCount.greaterThan(0);

    // Verify columns
    await expect(page.getByText('Timestamp')).toBeVisible();
    await expect(page.getByText('Directory')).toBeVisible();
    await expect(page.getByText('Status')).toBeVisible();
    await expect(page.getByText('Documents')).toBeVisible();
  });
});
```

**Success Criteria:**
- ✅ 5+ tests for AdminIndexingPage
- ✅ SSE progress tracking validated
- ✅ Cancellation works correctly
- ✅ Error handling tested
- ✅ All tests pass in CI

---

### Feature 32.6: Admin UI E2E Tests - Graph Analytics (8 SP)
**Owner:** frontend-agent + testing-agent
**Priority:** P2 (Nice-to-have)

**Deliverables:**
- Playwright tests for Graph Analytics page
- Community detection visualization tests
- PageRank tests
- Graph export tests (D3, Cytoscape, vis.js)

**Test Structure:**
```typescript
// frontend/tests/e2e/admin/graph-analytics.spec.ts

describe('Admin Graph Analytics Page', () => {
  test('should display graph visualization with communities', async ({ page }) => {
    await page.goto('http://localhost:3000/admin/graph-analytics');

    // Verify graph canvas
    await expect(page.getByTestId('graph-canvas')).toBeVisible();
    await expect(page.getByTestId('community-legend')).toBeVisible();

    // Verify community detection ran
    await expect(page.getByTestId('community-count')).toContainText(/\d+ communities/);
  });

  test('should allow graph export in multiple formats', async ({ page }) => {
    await page.goto('http://localhost:3000/admin/graph-analytics');

    // Test D3 export
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByTestId('export-d3-button').click()
    ]);
    expect(download.suggestedFilename()).toContain('.json');

    // Test Cytoscape export
    const [download2] = await Promise.all([
      page.waitForEvent('download'),
      page.getByTestId('export-cytoscape-button').click()
    ]);
    expect(download2.suggestedFilename()).toContain('.json');
  });

  test('should display PageRank scores for entities', async ({ page }) => {
    await page.goto('http://localhost:3000/admin/graph-analytics');

    // Verify PageRank table
    await expect(page.getByTestId('pagerank-table')).toBeVisible();
    await expect(page.getByTestId('entity-name')).toHaveCount.greaterThan(0);
    await expect(page.getByTestId('pagerank-score')).toContainText(/0\.\d+/);
  });
});
```

**Success Criteria:**
- ✅ 3+ tests for Graph Analytics
- ✅ Community detection validated
- ✅ Export formats work
- ✅ PageRank visualization tested

---

### Feature 32.7: Admin UI E2E Tests - Cost Dashboard (5 SP)
**Owner:** frontend-agent + testing-agent
**Priority:** P2 (Nice-to-have)

**Deliverables:**
- Playwright tests for Cost Dashboard
- Budget tracking tests
- Provider breakdown tests (Alibaba Cloud, OpenAI, Local)

**Test Structure:**
```typescript
// frontend/tests/e2e/admin/cost-dashboard.spec.ts

describe('Admin Cost Dashboard', () => {
  test('should display cost summary with provider breakdown', async ({ page }) => {
    await page.goto('http://localhost:3000/admin/cost-dashboard');

    // Verify cost summary
    await expect(page.getByTestId('total-cost')).toBeVisible();
    await expect(page.getByTestId('total-cost')).toContainText(/\$\d+\.\d+/);

    // Verify provider breakdown
    await expect(page.getByTestId('alibaba-cloud-cost')).toBeVisible();
    await expect(page.getByTestId('openai-cost')).toBeVisible();
    await expect(page.getByTestId('local-cost')).toContainText('$0.00');
  });

  test('should show budget warnings when approaching limit', async ({ page }) => {
    // Set budget limit via settings
    await page.goto('http://localhost:3000/admin/settings');
    await page.getByTestId('monthly-budget').fill('10.00');
    await page.getByTestId('save-settings').click();

    // Navigate to cost dashboard
    await page.goto('http://localhost:3000/admin/cost-dashboard');

    // Verify budget warning (if costs > 80% of budget)
    const totalCost = await page.getByTestId('total-cost').textContent();
    if (parseFloat(totalCost?.replace('$', '') || '0') > 8.00) {
      await expect(page.getByTestId('budget-warning')).toBeVisible();
    }
  });
});
```

**Success Criteria:**
- ✅ 2+ tests for Cost Dashboard
- ✅ Provider breakdown validated
- ✅ Budget warnings tested

---

## 🏗️ Technical Architecture

### Adaptive Chunking Pipeline

```
Document (Docling JSON)
    ↓
extract_section_hierarchy()  # Feature 32.1
    ↓
List[SectionMetadata]  # (heading, page, bbox, text, tokens)
    ↓
adaptive_section_chunking()  # Feature 32.2
    ↓
List[AdaptiveChunk]  # (multi-section metadata)
    ↓
┌────────────────┬──────────────────┬────────────────────┐
│   Qdrant       │   Neo4j          │   LightRAG         │
│  (Feature 32.3)│  (Feature 32.4)  │  (Extraction)      │
└────────────────┴──────────────────┴────────────────────┘
    ↓                  ↓                    ↓
Vector Search    Section Nodes      Entity/Relation
+ Section Boost  + Hierarchical     + Clean Graph
                   Queries
```

### Neo4j Graph Schema (with Section Nodes)

```cypher
// Hierarchical provenance chain
(:Document {id: "doc123", source: "PerformanceTuning.pptx"})
  -[:HAS_SECTION]-> (:Section {title: "Multi-Server Architecture", page: 1, order: 1})
    -[:CONTAINS_CHUNK]-> (:Chunk {id: "chunk_0", tokens: 1050})
      -[:MENTIONS]-> (:Entity {name: "Load Balancer", type: "TECHNOLOGY"})
      -[:MENTIONS]-> (:Entity {name: "Multi-Server", type: "ARCHITECTURE"})
  -[:HAS_SECTION]-> (:Section {title: "Load Balancing Strategies", page: 2, order: 2})
    -[:CONTAINS_CHUNK]-> (:Chunk {id: "chunk_1", tokens: 980})
      -[:MENTIONS]-> (:Entity {name: "Round-Robin", type: "ALGORITHM"})

// Direct section-to-entity link (hierarchical queries)
(:Section {title: "Multi-Server Architecture"})
  -[:DEFINES]-> (:Entity {name: "Multi-Server"})
  -[:DEFINES]-> (:Entity {name: "Load Balancer"})
```

### Qdrant Payload Structure (Multi-Section Metadata)

```json
{
  "text": "Multi-Server Architecture\n\nLoad Balancing Strategies\n\nCaching Optimization",
  "section_headings": [
    "Multi-Server Architecture",
    "Load Balancing Strategies",
    "Caching Optimization"
  ],
  "section_pages": [1, 2, 3],
  "section_bboxes": [
    {"l": 50, "t": 30, "r": 670, "b": 80},
    {"l": 50, "t": 30, "r": 670, "b": 80},
    {"l": 50, "t": 30, "r": 670, "b": 80}
  ],
  "primary_section": "Multi-Server Architecture",
  "source": "PerformanceTuning_textonly.pptx",
  "file_type": "pptx",
  "num_sections": 3,
  "token_count": 1050
}
```

---

## 🧪 Testing Strategy

### Backend Testing

**Unit Tests (30+ tests):**
- `test_extract_sections_from_docling_json()` - Section extraction
- `test_adaptive_section_merging()` - Merging logic
- `test_large_section_standalone()` - Large sections standalone
- `test_small_sections_merged()` - Small sections merged
- `test_multi_section_metadata()` - Metadata tracking
- `test_section_based_reranking()` - Retrieval boost
- `test_citation_with_sections()` - Citation format

**Integration Tests (15+ tests):**
- `test_end_to_end_powerpoint_chunking()` - PowerPoint → Chunks → Qdrant
- `test_section_nodes_in_neo4j()` - Section node creation
- `test_hierarchical_queries()` - Query entities by section
- `test_backward_compatibility()` - Existing chunks work

**Acceptance Tests (5+ tests):**
- `test_powerpoint_6_to_8_chunks()` - PowerPoint chunking benchmark
- `test_extraction_quality_improvement()` - -15% false positives
- `test_retrieval_precision_improvement()` - +10% precision
- `test_citation_accuracy()` - 100% section names match

### Frontend E2E Testing (Playwright)

**Admin Indexing (5 tests):**
- Directory indexing form
- SSE progress tracking
- Cancellation
- Error handling
- Indexing history

**Admin Graph Analytics (3 tests):**
- Graph visualization
- Community detection
- PageRank scores

**Admin Cost Dashboard (2 tests):**
- Cost summary
- Budget warnings

**Total Frontend E2E Tests:** 10+ new tests (on top of 111 from Sprint 31)

---

## ✅ Success Criteria

### Quantitative Metrics

**Chunking Quality:**
- ✅ PowerPoint (15 slides) → 6-8 chunks (not 124 tiny chunks)
- ✅ Average chunk size: 800-1200 tokens
- ✅ Section coverage: 100% (all headings tracked)

**Extraction Quality:**
- ✅ False positive relations: <10% (vs 23% baseline)
- ✅ Entity accuracy: >90%
- ✅ Community detection precision: >85%

**Retrieval Accuracy:**
- ✅ Section-based re-ranking lift: +10%
- ✅ Citation precision: 100% (section names match document)
- ✅ User satisfaction: >4/5 (manual review)

**Frontend E2E Coverage:**
- ✅ Admin Indexing: 5+ tests passing
- ✅ Admin Graph Analytics: 3+ tests passing
- ✅ Admin Cost Dashboard: 2+ tests passing
- ✅ Total E2E tests: 121+ (111 Sprint 31 + 10 Sprint 32)

### Qualitative Goals

- ✅ Backward compatible (no breaking changes)
- ✅ Production ready (comprehensive testing)
- ✅ Well documented (ADR-039, Sprint 32 Summary)
- ✅ Clean code (80%+ test coverage)

---

## ⚠️ Risk Management

### Risk 1: Section Detection Accuracy (Medium)

**Problem:** Docling JSON may not always correctly identify headings
**Impact:** Incorrect section boundaries → suboptimal chunking
**Mitigation:**
- Validate Docling JSON structure on test corpus
- Implement fallback to fixed chunking if section detection fails
- Manual review of PowerPoint chunking results

**Contingency:** Revert to ADR-022 fixed chunking if quality degrades

---

### Risk 2: Neo4j Schema Migration (Low)

**Problem:** Adding Section nodes requires schema migration
**Impact:** Existing graphs may need re-indexing
**Mitigation:**
- Make Section nodes optional (backward compatible)
- Implement gradual migration (new documents only)
- Provide migration script for existing graphs

**Contingency:** Defer Feature 32.4 (Neo4j Section Nodes) to Sprint 33

---

### Risk 3: E2E Test Flakiness (Medium)

**Problem:** Playwright tests may be flaky (SSE timing, async updates)
**Impact:** CI failures, reduced confidence
**Mitigation:**
- Use explicit waits (not fixed timeouts)
- Retry failed tests (Playwright retry: 2)
- Test against real backend (not mocks)

**Contingency:** Increase test timeouts, add retry logic

---

### Risk 4: PowerPoint Chunking Edge Cases (Low)

**Problem:** Some PowerPoint files may have unusual structures
**Impact:** Chunking may not work as expected
**Mitigation:**
- Test on diverse PowerPoint files (OMNITRACKER corpus)
- Add logging for chunking decisions
- Manual review of edge cases

**Contingency:** Add heuristics for edge cases (e.g., slides with no headings)

---

## 📅 Timeline & Milestones

### Day 1-2: Section Extraction & Merging Logic (21 SP)
**Features:** 32.1, 32.2
- Extract section hierarchy from Docling JSON
- Implement adaptive merging logic
- Unit tests (15+ tests)
- Benchmark PowerPoint chunking

**Milestone:** Adaptive chunking works for PowerPoint (6-8 chunks)

---

### Day 3-4: Qdrant Integration & Retrieval Enhancement (8 SP)
**Feature:** 32.3
- Multi-section metadata in Qdrant
- Section-based re-ranking
- Citation generation
- Integration tests (10+ tests)

**Milestone:** Retrieval precision +10%, citations include section names

---

### Day 5: Admin UI E2E Tests - Indexing (8 SP)
**Feature:** 32.5
- Playwright tests for AdminIndexingPage
- SSE progress tracking, cancellation, error handling
- 5+ tests

**Milestone:** Admin Indexing E2E coverage 100%

---

### Day 6: Admin UI E2E Tests - Graph & Cost (13 SP)
**Features:** 32.6, 32.7
- Playwright tests for Graph Analytics
- Playwright tests for Cost Dashboard
- 5+ tests

**Milestone:** Admin UI E2E coverage 100%

---

### Day 7: Neo4j Section Nodes (Optional) + Documentation (13 SP)
**Feature:** 32.4 (optional)
- Add Section nodes to Neo4j
- Hierarchical queries
- Sprint 32 Summary
- Update CLAUDE.md

**Milestone:** Sprint 32 COMPLETE, Production ready

---

## 📊 Story Point Breakdown

```
Feature 32.1: Section Extraction             8 SP
Feature 32.2: Adaptive Merging Logic        13 SP
Feature 32.3: Qdrant Multi-Section Metadata  8 SP
Feature 32.4: Neo4j Section Nodes (Opt)     13 SP
Feature 32.5: Admin E2E - Indexing           8 SP
Feature 32.6: Admin E2E - Graph Analytics    8 SP
Feature 32.7: Admin E2E - Cost Dashboard     5 SP
---------------------------------------------------
Total:                                      63 SP
```

**Timeline:**
- Sequential: 7 days (1 developer, ~9 SP/day)
- Parallel: 3-4 days (3 subagents: backend, frontend, testing)

**Velocity:**
- Sprint 31: 45 SP in 1 day (8x acceleration with 4 agents)
- Sprint 32 Target: 63 SP in 7 days (~9 SP/day sequential)

---

## 🎯 Definition of Done

- [ ] **Code Complete:**
  - [ ] All 7 features implemented
  - [ ] Black, Ruff, MyPy passing
  - [ ] 80%+ test coverage

- [ ] **Testing Complete:**
  - [ ] 30+ backend unit tests passing
  - [ ] 15+ integration tests passing
  - [ ] 10+ Playwright E2E tests passing
  - [ ] Acceptance tests validate success criteria

- [ ] **Documentation Complete:**
  - [ ] ADR-039 marked as IMPLEMENTED
  - [ ] Sprint 32 Summary created
  - [ ] CLAUDE.md updated with Sprint 32 status
  - [ ] Code examples in docstrings

- [ ] **Production Ready:**
  - [ ] CI/CD pipeline green
  - [ ] No regressions in existing tests
  - [ ] Performance benchmarks validate improvements
  - [ ] Manual QA on PowerPoint corpus

---

## 📚 References

- **ADR-039:** Adaptive Section-Aware Chunking (2025-11-21)
- **ADR-022:** Unified Chunking Service (Sprint 16)
- **ADR-026:** Pure LLM Extraction (Sprint 20)
- **ADR-027:** Docling Container Architecture (Sprint 21)
- **ADR-037:** Alibaba Cloud Extraction (Sprint 28)
- **Sprint 31 Status:** E2E Test Infrastructure (CLAUDE.md)
- **LangChain Docling Standard:** Multi-section metadata tracking

---

## 🔄 Next Sprint Preview (Sprint 33)

**Potential Focus Areas:**
1. **BGE-M3 Similarity-Based Section Merging** (TD-042 from ADR-039)
   - Use BGE-M3 embeddings + cosine similarity for thematic merging
   - Alternative to token-based thresholds
   - Opt-in feature for unstructured docs

2. **Frontend Production Optimization**
   - Code splitting, lazy loading
   - Performance optimization
   - Accessibility improvements (TD-36, TD-37 from Sprint 17)

3. **Advanced Graph Analytics**
   - Temporal graph queries
   - Cross-document entity linking
   - Graph schema evolution

---

**Document Version:** 1.0
**Created:** 2025-11-21
**Last Updated:** 2025-11-21
**Status:** 📋 PLANNED

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
