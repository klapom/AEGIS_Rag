# Sprint 62: Section-Aware Features

**Sprint Duration:** 2-3 weeks
**Total Story Points:** 38 SP
**Priority:** HIGH (Activate Dormant Infrastructure)
**Dependencies:** Sprint 61 Complete (Performance migrations)

---

## Executive Summary

Sprint 62 activates **section-aware infrastructure** implemented but largely unused since Sprint 32:
- **Current utilization:** ~20% (adaptive chunking works, metadata stored but not used)
- **Target utilization:** ~95% (full activation of all section features)

**Key insight:** Section metadata exists in Qdrant/Neo4j but is **not used for queries, filtering, citations, or reranking**.

**Expected Impact:**
- Citation precision: **+40%** (section-level vs document-level)
- Graph query precision: **+25%** (section-aware entity filtering)
- VLM integration: **Images mapped to sections**
- Document type coverage: **+3 formats** (Markdown, DOCX, TXT)
- Community detection: **Section-based communities**
- Analytics: **Section-level insights for docs**

---

## Background: Section-Aware Infrastructure (Sprint 32)

### What Exists (Currently Unused)

**1. Adaptive Section Chunking** (`src/components/ingestion/nodes/adaptive_chunking.py`)
- ✅ **WORKS**: Merges small sections intelligently
- ✅ **OUTPUT**: Multi-section chunks with metadata

**2. Qdrant Section Metadata** (`src/components/vector_search/qdrant_client.py`)
- ✅ **STORED**: `section_headings`, `section_pages`, `section_bboxes`, `primary_section`
- ❌ **NOT USED**: No filtering, no reranking, no citations use this data

**3. Neo4j Section Nodes** (`src/components/graph_rag/neo4j_client.py`)
- ✅ **CREATED**: Section nodes with `HAS_SECTION`, `CONTAINS_CHUNK`, `DEFINES` relationships
- ❌ **NOT USED**: Graph queries ignore section nodes entirely

**4. Section-Aware Reranking Code** (`src/components/vector_search/hybrid_search.py`)
- ✅ **EXISTS**: Section boost logic in reranking
- ❌ **NOT CALLED**: Never invoked in production queries

---

## Feature 62.1: Section-Aware Graph Queries (5 SP)

**Priority:** P1
**Rationale:** Enable Neo4j Cypher queries to filter/navigate by sections

### Tasks

#### 1. Section-Aware Entity Retrieval (2 SP)

**File:** `src/agents/graph_query.py`

Add section filtering to graph queries:
```python
async def query_entities_by_section(
    query: str,
    section_filter: str | None = None,
    document_id: str | None = None,
) -> list[dict]:
    """Query entities filtered by section.

    Args:
        query: Entity query
        section_filter: Section heading pattern (e.g., "Introduction%")
        document_id: Limit to specific document

    Returns:
        List of entities with section context
    """
    cypher = """
    MATCH (d:Document)-[:HAS_SECTION]->(s:Section)-[:DEFINES]->(e:Entity)
    WHERE s.heading LIKE $section_filter
    AND d.document_id = $document_id
    RETURN e, s.heading as section, s.page_number as page
    """
    # Execute and return results
```

#### 2. Section-Aware Path Queries (2 SP)

**File:** `src/components/graph_rag/path_queries.py` (new)

```python
def find_entities_in_section(
    section_heading: str,
    document_id: str,
) -> list[dict]:
    """Find all entities mentioned in a specific section.

    Cypher:
        MATCH (d:Document {document_id: $doc_id})
              -[:HAS_SECTION]->(s:Section {heading: $heading})
              -[:DEFINES]->(e:Entity)
        RETURN e, s
    """
```

#### 3. Integration with Hybrid Search (1 SP)

Update `src/agents/coordinator.py` to pass section context to graph queries.

---

## Feature 62.2: Multi-Section Metadata in Vector Search (3 SP)

**Priority:** P1
**Rationale:** Use stored section metadata for filtering and boosting

### Tasks

#### 1. Section-Based Filtering (1 SP)

**File:** `src/components/vector_search/qdrant_client.py`

```python
def search_with_section_filter(
    query_vector: list[float],
    section_filter: str | None = None,
    top_k: int = 10,
) -> list[dict]:
    """Search with optional section heading filter.

    Args:
        query_vector: Embedding vector
        section_filter: Section heading pattern (e.g., "Chapter%")
        top_k: Number of results

    Returns:
        Filtered search results
    """
    filter_conditions = {}
    if section_filter:
        filter_conditions["primary_section"] = {
            "$like": section_filter
        }

    return self.client.search(
        collection_name=self.collection_name,
        query_vector=query_vector,
        query_filter=Filter(**filter_conditions) if filter_conditions else None,
        limit=top_k,
    )
```

#### 2. Section Boost in Scoring (1 SP)

**File:** `src/components/vector_search/hybrid_search.py`

```python
def boost_section_matches(
    results: list[dict],
    query: str,
    boost_factor: float = 1.2,
) -> list[dict]:
    """Boost results where section heading matches query keywords.

    If query="Introduction to ML" and section="Introduction",
    boost score by 1.2x.
    """
    query_keywords = set(query.lower().split())

    for result in results:
        section = result.get("primary_section", "").lower()
        section_keywords = set(section.split())

        if query_keywords & section_keywords:  # Overlap
            result["score"] *= boost_factor
            result["boost_reason"] = "section_match"

    return sorted(results, key=lambda x: x["score"], reverse=True)
```

#### 3. Section Metadata in API Response (1 SP)

Update `src/api/v1/chat.py` to include section metadata in `SourceDocument` model.

---

## Feature 62.3: VLM Image Integration with Sections (5 SP)

**Priority:** P2
**Rationale:** Map VLM-described images to their containing sections

### Tasks

#### 1. Image-to-Section Mapping (2 SP)

**File:** `src/components/ingestion/nodes/image_enrichment.py`

```python
def map_images_to_sections(
    images: list[dict],  # VLM processed images
    sections: list[SectionMetadata],  # From adaptive chunking
) -> list[dict]:
    """Map images to sections based on bounding box overlap.

    Args:
        images: [{"page": 2, "bbox": [x1,y1,x2,y2], "description": "..."}]
        sections: [SectionMetadata(page=2, bbox=[...], heading="...")]

    Returns:
        Images with added "section_heading" field
    """
    for image in images:
        img_page = image["page"]
        img_bbox = image["bbox"]

        # Find section with highest bbox overlap on same page
        best_section = None
        best_overlap = 0

        for section in sections:
            if section.page_number != img_page:
                continue

            overlap = calculate_bbox_overlap(img_bbox, section.bbox)
            if overlap > best_overlap:
                best_overlap = overlap
                best_section = section

        if best_section:
            image["section_heading"] = best_section.heading
            image["section_id"] = best_section.section_id

    return images
```

#### 2. Insert VLM Descriptions into Section Text (2 SP)

**File:** `src/components/ingestion/ingestion_pipeline.py`

Update ingestion pipeline to insert image descriptions into section content:
```python
# After VLM processing and section mapping
for image in enriched_images:
    section_id = image.get("section_id")
    description = image["description"]

    # Find section and append image description
    for section in sections:
        if section.section_id == section_id:
            section.text += f"\n\n[IMAGE: {description}]"
```

#### 3. Test VLM-Section Integration (1 SP)

**File:** `tests/integration/test_vlm_section_integration.py`

Verify images are correctly mapped and descriptions inserted.

---

## Feature 62.4: Section-Aware Citations (3 SP)

**Priority:** P1
**Rationale:** Precise citations with section + page number

### Current vs Target

**Current (Sprint 32):**
```python
# Citation format: "document.pdf (Page 5)"
title = ctx.get("title", "Unknown")
```

**Target (Sprint 62):**
```python
# Citation format: "document.pdf - Section: 'Introduction' (Page 2)"
primary_section = ctx.get("primary_section", "")
page = ctx.get("section_pages", [None])[0]
title = f"{ctx.get('title')} - Section: '{primary_section}' (Page {page})"
```

### Tasks

#### 1. Enhanced Citation Formatter (1 SP)

**File:** `src/api/v1/chat.py` (update `_extract_sources`)

Already partially implemented in line 1326-1346, ensure it's always used.

#### 2. Citation Validation in UI (1 SP)

**File:** `frontend/src/components/SourceCard.tsx`

Update to display section-aware citations prominently.

#### 3. Test Section Citations E2E (1 SP)

**File:** `tests/e2e/test_section_citations.py`

---

## Feature 62.5: Section-Aware Reranking Integration (2 SP)

**Priority:** P2
**Rationale:** Activate dormant section boost in reranking

### Tasks

#### 1. Enable Section Boost in Reranking (1 SP)

**File:** `src/components/vector_search/hybrid_search.py`

Ensure section-aware reranking is called:
```python
# Currently exists but not called - activate it
reranked = boost_section_matches(
    results=retrieved_docs,
    query=query,
    boost_factor=1.2,
)
```

#### 2. Test Reranking with Section Boost (1 SP)

Verify section matches get higher scores.

---

## Feature 62.6: HAS_SUBSECTION Hierarchical Links (3 SP)

**Priority:** P2
**Rationale:** Model section hierarchy in Neo4j

### Tasks

#### 1. Create HAS_SUBSECTION Relationships (2 SP)

**File:** `src/components/graph_rag/neo4j_client.py`

```python
def create_section_hierarchy(
    document_id: str,
    sections: list[SectionMetadata],
):
    """Create parent-child relationships between sections.

    Example:
        (Section: "1. Introduction") -[:HAS_SUBSECTION]-> (Section: "1.1 Motivation")
        (Section: "1. Introduction") -[:HAS_SUBSECTION]-> (Section: "1.2 Goals")
    """
    for i, section in enumerate(sections):
        heading = section.heading

        # Find parent section (e.g., "1.1" -> parent "1")
        parent_heading = extract_parent_heading(heading)

        if parent_heading:
            cypher = """
            MATCH (parent:Section {document_id: $doc_id, heading: $parent})
            MATCH (child:Section {document_id: $doc_id, heading: $child})
            MERGE (parent)-[:HAS_SUBSECTION]->(child)
            """
            # Execute
```

#### 2. Query Section Hierarchies (1 SP)

**File:** `src/components/graph_rag/path_queries.py`

```python
def get_section_tree(document_id: str) -> dict:
    """Get hierarchical section tree for document.

    Returns:
        {"section": "1. Intro", "subsections": [...]}
    """
```

---

## Feature 62.7: Document Type Support for Sections (5 SP)

**Priority:** P1
**Rationale:** Extend section extraction to Markdown, DOCX, TXT

### Current Support

| Format | Section Support | Implementation |
|--------|-----------------|----------------|
| PDF | ✅ Full | Docling extracts headings |
| PPTX | ✅ Full | Slides = sections |
| Markdown | ❌ None | No heading extraction |
| DOCX | ❌ None | No style detection |
| TXT | ❌ None | No structure assumed |

### Tasks

#### 1. Markdown Section Extraction (2 SP)

**File:** `src/components/ingestion/parsers/markdown_parser.py` (new)

```python
import re
from src.models.section import SectionMetadata

def extract_markdown_sections(markdown_text: str) -> list[SectionMetadata]:
    """Extract sections from Markdown # headers.

    # Level 1 -> Section
    ## Level 2 -> Subsection
    ### Level 3 -> Subsection
    """
    sections = []
    lines = markdown_text.split("\n")
    current_section = {"heading": "", "text": "", "level": 0}

    for line in lines:
        if line.startswith("#"):
            # Save previous section
            if current_section["heading"]:
                sections.append(SectionMetadata(**current_section))

            # Parse new heading
            match = re.match(r"^(#+)\s+(.+)$", line)
            if match:
                level = len(match.group(1))
                heading = match.group(2)
                current_section = {
                    "heading": heading,
                    "text": "",
                    "level": level,
                    "page_number": 1,  # No pages in Markdown
                }
        else:
            current_section["text"] += line + "\n"

    # Save final section
    if current_section["heading"]:
        sections.append(SectionMetadata(**current_section))

    return sections
```

#### 2. DOCX Section Extraction (2 SP)

**File:** `src/components/ingestion/parsers/docx_parser.py` (new)

```python
from docx import Document
from src.models.section import SectionMetadata

def extract_docx_sections(docx_path: str) -> list[SectionMetadata]:
    """Extract sections from DOCX heading styles.

    Detect:
        - Heading 1 -> Section
        - Heading 2 -> Subsection
        - Heading 3 -> Subsection
    """
    doc = Document(docx_path)
    sections = []
    current_section = None

    for para in doc.paragraphs:
        style = para.style.name

        if style.startswith("Heading"):
            # Save previous section
            if current_section:
                sections.append(SectionMetadata(**current_section))

            # New section
            level = int(style.split()[-1])  # "Heading 1" -> 1
            current_section = {
                "heading": para.text,
                "text": "",
                "level": level,
                "page_number": 1,  # Approximate
            }
        elif current_section:
            current_section["text"] += para.text + "\n"

    if current_section:
        sections.append(SectionMetadata(**current_section))

    return sections
```

#### 3. TXT Heuristic Section Detection (1 SP)

**File:** `src/components/ingestion/parsers/txt_parser.py` (new)

```python
import re

def extract_txt_sections(txt_content: str) -> list[SectionMetadata]:
    """Heuristically detect sections in plain text.

    Patterns:
        - ALL CAPS LINES (e.g., "INTRODUCTION")
        - Numbered headings (e.g., "1. Introduction")
        - Lines ending with colon (e.g., "Background:")
    """
    sections = []
    lines = txt_content.split("\n")
    current_section = None

    for line in lines:
        # Pattern 1: ALL CAPS (min 3 words)
        if line.isupper() and len(line.split()) >= 2:
            if current_section:
                sections.append(SectionMetadata(**current_section))
            current_section = {"heading": line, "text": "", "level": 1}

        # Pattern 2: Numbered heading (e.g., "1. Introduction")
        elif re.match(r"^\d+\.\s+[A-Z]", line):
            if current_section:
                sections.append(SectionMetadata(**current_section))
            current_section = {"heading": line, "text": "", "level": 1}

        # Pattern 3: Ending with colon
        elif line.endswith(":") and len(line) < 50:
            if current_section:
                sections.append(SectionMetadata(**current_section))
            current_section = {"heading": line[:-1], "text": "", "level": 1}

        elif current_section:
            current_section["text"] += line + "\n"

    if current_section:
        sections.append(SectionMetadata(**current_section))

    return sections or [SectionMetadata(heading="Document", text=txt_content, level=1)]
```

---

## Feature 62.8: Section-Based Community Detection (3 SP)

**Priority:** P2
**Rationale:** Run Leiden algorithm per section for finer-grained communities

### Tasks

#### 1. Section-Level Community Detection (2 SP)

**File:** `src/components/graph_rag/community_detection.py`

```python
def detect_communities_per_section(
    document_id: str,
) -> dict[str, list[dict]]:
    """Run Leiden algorithm per section instead of per document.

    Returns:
        {
            "Section: Introduction": [community_0, community_1, ...],
            "Section: Methods": [community_0, community_1, ...],
        }
    """
    sections = get_sections_for_document(document_id)

    communities_by_section = {}

    for section in sections:
        # Get entities in this section
        entities = get_entities_in_section(section.heading, document_id)

        # Build subgraph for this section
        subgraph = build_section_subgraph(entities)

        # Run Leiden
        communities = leiden_algorithm(subgraph)

        communities_by_section[f"Section: {section.heading}"] = communities

    return communities_by_section
```

#### 2. Integration with Community Summaries (1 SP)

Update community summary generation to include section context.

---

## Feature 62.9: Section Analytics Endpoint (2 SP)

**Priority:** P3
**Rationale:** Provide section-level insights for documents

### Tasks

#### 1. Section Analytics API (1 SP)

**File:** `src/api/v1/analytics.py` (new)

```python
@router.get("/analytics/sections/{document_id}")
async def get_section_analytics(document_id: str) -> dict:
    """Get analytics for document sections.

    Returns:
        {
            "document_id": "doc123",
            "total_sections": 15,
            "sections": [
                {
                    "heading": "Introduction",
                    "page": 1,
                    "chunk_count": 3,
                    "entity_count": 12,
                    "avg_chunk_size": 1200,
                    "images": 2,
                },
                ...
            ]
        }
    """
```

#### 2. Frontend Section Analytics View (1 SP)

Add section analytics to document details page.

---

## Success Criteria

| Feature | Success Metric | Target | Verification |
|---------|---------------|--------|--------------|
| 62.1 | Section-aware graph queries | Works | Integration test |
| 62.2 | Section filtering in vector search | Works | Unit test |
| 62.3 | VLM images mapped to sections | >90% | Integration test |
| 62.4 | Section-aware citations | 100% | E2E test |
| 62.5 | Section boost in reranking | +10% precision | Benchmark |
| 62.6 | HAS_SUBSECTION relationships | Created | Cypher query |
| 62.7 | Markdown/DOCX/TXT sections | Extracted | Parser tests |
| 62.8 | Section-based communities | Detected | Community test |
| 62.9 | Section analytics API | Returns data | API test |
| 62.10 | Research endpoint implemented | 200 response | Integration test |
| 62.10 | Research workflow completes | Synthesis returned | E2E test |

---

## Testing Strategy

- **Unit Tests:** Parser tests (Markdown, DOCX, TXT), section filtering
- **Integration Tests:** VLM-section mapping, graph queries with sections
- **E2E Tests:** Section-aware citations in UI, section analytics dashboard
- **Benchmarks:** Section boost effectiveness in retrieval quality

---

## Timeline

| Day | Tasks | Deliverables |
|-----|-------|--------------|
| 1-3 | Features 62.1-62.2 | Section graph queries + vector filtering |
| 4-6 | Features 62.3-62.4 | VLM integration + citations |
| 7-9 | Features 62.5-62.7 | Reranking + hierarchy + document types |
| 10-12 | Features 62.8-62.9 | Community detection + analytics |
| 13-14 | Testing & integration | All tests passing |

**Total Duration:** 14 days (2 weeks)

---

## Feature 62.10: Implement Research Endpoint (8 SP)

**Priority:** P1 (High - Missing Critical Feature)
**Status:** READY (Discovered during Sprint 59 testing)
**Dependencies:** None

### Rationale

During Sprint 59 Tool Framework testing, the `/api/v1/chat/research` endpoint was **documented but not implemented**:
- **Impact:** Users cannot perform dedicated agentic research workflows
- **Current workaround:** Use `/api/v1/chat/` with `use_tools=true` (not optimized for research)
- **Expected benefit:** Dedicated research workflow with better planning, iteration, and synthesis

**Documentation Reference:**
- `docs/e2e/TOOL_FRAMEWORK_USER_JOURNEY.md` Journey 3 describes the research workflow
- LangGraph state machine planned but never implemented

### Tasks

#### 1. Implement ResearchAgent LangGraph Workflow (3 SP)

**File:** `src/agents/research_agent.py` (new)

```python
"""Research agent for multi-step agentic search.

Sprint 62 Feature 62.10: Implement /chat/research endpoint.
Based on Journey 3 from TOOL_FRAMEWORK_USER_JOURNEY.md.
"""

from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import structlog

logger = structlog.get_logger(__name__)


class ResearchState(TypedDict):
    """State for research agent workflow."""
    query: str
    max_iterations: int
    current_iteration: int
    search_queries: list[str]
    results: list[dict]
    synthesis: str | None
    is_sufficient: bool


async def plan_node(state: ResearchState) -> ResearchState:
    """Generate research plan with 3-5 search queries.

    Uses LLM to analyze query and generate targeted search queries.
    """
    logger.info("research_planning", query=state["query"])

    # Use LLM to generate search plan
    from src.components.llm_proxy import AegisLLMProxy
    proxy = AegisLLMProxy()

    prompt = f"""Analyze this research question and generate 3-5 targeted search queries:

Question: {state['query']}

Generate diverse queries that cover different aspects. Return JSON:
{{"queries": ["query1", "query2", "query3"]}}"""

    response = await proxy.generate(prompt=prompt, temperature=0.7)
    # Parse response and extract queries
    state["search_queries"] = parse_queries(response)

    return state


async def search_node(state: ResearchState) -> ResearchState:
    """Execute multi-source search (vector + graph).

    Performs hybrid search and accumulates results.
    """
    logger.info(
        "research_search",
        iteration=state["current_iteration"],
        queries_count=len(state["search_queries"])
    )

    from src.agents.coordinator import coordinator_agent

    # Execute searches
    for query in state["search_queries"]:
        result = await coordinator_agent.run(query=query, intent="hybrid")
        state["results"].extend(result.get("sources", []))

    # Deduplicate results by document_id
    state["results"] = deduplicate_results(state["results"])

    return state


async def evaluate_node(state: ResearchState) -> ResearchState:
    """Evaluate if results are sufficient.

    Quality metrics:
    - Coverage: min(num_results / 10.0, 1.0)
    - Diversity: num_sources / 2.0
    - Quality: avg_score > 0.5
    - Sufficient: num_results >= 5 AND avg_score > 0.5
    """
    logger.info("research_evaluation", results_count=len(state["results"]))

    num_results = len(state["results"])
    avg_score = sum(r.get("score", 0) for r in state["results"]) / max(num_results, 1)

    state["is_sufficient"] = (num_results >= 5 and avg_score > 0.5)
    state["current_iteration"] += 1

    logger.info(
        "research_evaluation_result",
        sufficient=state["is_sufficient"],
        num_results=num_results,
        avg_score=avg_score,
    )

    return state


async def synthesize_node(state: ResearchState) -> ResearchState:
    """Synthesize final research summary.

    Generates comprehensive answer from accumulated results.
    """
    logger.info("research_synthesis", results_count=len(state["results"]))

    from src.components.llm_proxy import AegisLLMProxy
    proxy = AegisLLMProxy()

    # Format results for context
    context = "\n\n".join([
        f"[{i+1}] {r.get('text', '')[:500]}..."
        for i, r in enumerate(state["results"][:10])
    ])

    prompt = f"""Based on the research results below, provide a comprehensive answer to the question.

Question: {state['query']}

Research Results:
{context}

Provide a well-structured, comprehensive answer with key insights."""

    synthesis = await proxy.generate(prompt=prompt, temperature=0.3)
    state["synthesis"] = synthesis

    return state


def should_continue(state: ResearchState) -> str:
    """Decide whether to continue research or synthesize."""
    if state["is_sufficient"] or state["current_iteration"] >= state["max_iterations"]:
        return "synthesize"
    else:
        return "search"


# Build graph
def create_research_agent() -> StateGraph:
    """Create research agent workflow graph."""
    workflow = StateGraph(ResearchState)

    # Add nodes
    workflow.add_node("plan", plan_node)
    workflow.add_node("search", search_node)
    workflow.add_node("evaluate", evaluate_node)
    workflow.add_node("synthesize", synthesize_node)

    # Add edges
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "search")
    workflow.add_edge("search", "evaluate")
    workflow.add_conditional_edges(
        "evaluate",
        should_continue,
        {
            "search": "search",
            "synthesize": "synthesize"
        }
    )
    workflow.add_edge("synthesize", END)

    return workflow.compile()


# Helper functions
def parse_queries(response: str) -> list[str]:
    """Parse queries from LLM response."""
    import json
    try:
        data = json.loads(response)
        return data.get("queries", [])
    except:
        # Fallback: split by newlines
        return [q.strip("- ") for q in response.split("\n") if q.strip()]


def deduplicate_results(results: list[dict]) -> list[dict]:
    """Deduplicate results by document_id."""
    seen = set()
    deduplicated = []
    for r in results:
        doc_id = r.get("metadata", {}).get("document_id")
        if doc_id not in seen:
            seen.add(doc_id)
            deduplicated.append(r)
    return deduplicated
```

#### 2. Implement Research API Endpoint (2 SP)

**File:** `src/api/v1/chat.py` (update)

Add research endpoint:
```python
@router.post("/research")
async def research_endpoint(
    query: str = Body(...),
    max_iterations: int = Body(default=3, ge=1, le=5),
    session_id: str = Body(default_factory=lambda: str(uuid.uuid4())),
) -> StreamingResponse:
    """Agentic research endpoint with multi-step search.

    Sprint 62 Feature 62.10: Dedicated research workflow.

    Args:
        query: Research question
        max_iterations: Max search iterations (1-5)
        session_id: Session ID for tracking

    Returns:
        Streaming response with research progress and synthesis
    """
    from src.agents.research_agent import create_research_agent

    logger.info("research_endpoint_called", query=query, session_id=session_id)

    async def generate():
        # Initialize research state
        state = ResearchState(
            query=query,
            max_iterations=max_iterations,
            current_iteration=0,
            search_queries=[],
            results=[],
            synthesis=None,
            is_sufficient=False,
        )

        # Create and run research agent
        research_agent = create_research_agent()

        # Stream events
        async for event in research_agent.astream(state):
            if "plan" in event:
                yield f"data: {json.dumps({'event': 'plan_created', 'queries': event['plan']['search_queries']})}\n\n"
            elif "search" in event:
                yield f"data: {json.dumps({'event': 'search_completed', 'results': len(event['search']['results'])})}\n\n"
            elif "evaluate" in event:
                yield f"data: {json.dumps({'event': 'evaluation', 'sufficient': event['evaluate']['is_sufficient']})}\n\n"
            elif "synthesize" in event:
                yield f"data: {json.dumps({'event': 'synthesis', 'text': event['synthesize']['synthesis']})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

#### 3. Add Pydantic Models (1 SP)

**File:** `src/core/models/research.py` (new)

```python
"""Research endpoint models.

Sprint 62 Feature 62.10.
"""

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    """Request model for research endpoint."""
    query: str = Field(..., min_length=10, max_length=500)
    max_iterations: int = Field(default=3, ge=1, le=5)
    session_id: str | None = None


class ResearchEvent(BaseModel):
    """Streaming event from research agent."""
    event: str  # plan_created, search_started, search_completed, evaluation, synthesis
    data: dict
```

#### 4. Integration Tests (1 SP)

**File:** `tests/integration/api/test_research_endpoint.py`

```python
"""Test research endpoint implementation.

Sprint 62 Feature 62.10.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.mark.integration
def test_research_endpoint_exists():
    """Test that research endpoint is implemented."""
    client = TestClient(app)

    response = client.post(
        "/api/v1/chat/research",
        json={
            "query": "What are the latest advances in RAG systems?",
            "max_iterations": 2
        }
    )

    # Should return 200 (not 404)
    assert response.status_code == 200


@pytest.mark.integration
async def test_research_workflow_completes():
    """Test complete research workflow."""
    client = TestClient(app)

    response = client.post(
        "/api/v1/chat/research",
        json={
            "query": "What is machine learning?",
            "max_iterations": 1  # Quick test
        },
        stream=True
    )

    events = []
    for line in response.iter_lines():
        if line.startswith(b"data:"):
            events.append(line.decode())

    # Should have plan, search, evaluate, synthesize events
    assert len(events) >= 4
    assert any("plan_created" in e for e in events)
    assert any("synthesis" in e for e in events)
```

#### 5. Documentation Update (1 SP)

**File:** `docs/e2e/TOOL_FRAMEWORK_USER_JOURNEY.md`

Update Journey 3 to mark as **IMPLEMENTED**:
```markdown
## Journey 3: Deep Research with Agentic Search

> **✅ STATUS**: Implemented in Sprint 62 (Feature 62.10)

### Scenario
User asks complex question requiring multi-step research.

### User Steps

1. **Send Research Request**
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat/research \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What are the latest advances in transformer architectures?",
       "max_iterations": 3
     }'
   ```
```

---

## Dependencies

- ✅ Sprint 61 Complete (Performance baseline)
- ✅ Section infrastructure exists (Sprint 32)
- ✅ VLM pipeline exists (Sprint 35+)
- ✅ Neo4j section nodes created (Sprint 32)

---

## Next Steps (Sprint 63)

Sprint 63 will focus on **Conversational Intelligence & Temporal** (29 SP):
- Multi-Turn RAG Template (13 SP)
- Basic Temporal Audit Trail (8 SP)
- Redis Prompt Caching (5 SP)
- Section-based community features (3 SP)

See `SPRINT_63_PLAN.md` for details.
