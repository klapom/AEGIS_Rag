# TD-054: Unified Chunking Service (Sprint 16)

**Status:** PARTIALLY COMPLETE
**Priority:** HIGH
**Severity:** Architectural Duplication
**Original Sprint:** Sprint 16 (Feature 16.1)
**Story Points:** 6 SP (remaining)
**Created:** 2025-12-04

---

## Problem Statement

Chunking logic is scattered across multiple components (Qdrant ingestion, BM25 indexing, LightRAG extraction), leading to potential inconsistencies between indexes. While some chunking infrastructure exists, full unification and 3-index alignment is incomplete.

**Current State:**
- Section-aware chunking implemented (ADR-039)
- `src/components/ingestion/section_extraction.py` exists
- Adaptive merging in `langgraph_nodes.py`
- **Unclear:** Full alignment between Qdrant, BM25, and LightRAG
- **Missing:** Central ChunkingService as single source of truth
- **Missing:** Validation of index consistency

---

## Existing Implementation (Sprint 32)

### Section Extraction
```python
# src/components/ingestion/section_extraction.py
def extract_section_hierarchy(docling_document, section_metadata_class):
    """Extract sections from Docling JSON."""
```

### Adaptive Merging
```python
# src/components/ingestion/langgraph_nodes.py (Lines 123-271)
def adaptive_section_chunking():
    """Merge small sections, keep large sections standalone."""
    # Target: 800-1800 tokens per chunk
```

---

## Gap Analysis

### What's Done
- Section extraction from Docling JSON
- Adaptive section merging (800-1800 tokens)
- Section nodes in Neo4j
- Multi-section metadata in Qdrant

### What's Missing
- **Central ChunkingService class** - Single entry point for all chunking
- **3-Index consistency validation** - Verify Qdrant/BM25/Neo4j alignment
- **Configuration-driven strategy** - Switch between adaptive/sentence/fixed-size
- **Chunk format standardization** - Unified Chunk model across consumers

---

## Solution

### 1. Central ChunkingService

```python
# src/core/chunking_service.py

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

class ChunkStrategy(str, Enum):
    ADAPTIVE = "adaptive"      # Section-aware, 800-1800 tokens
    SENTENCE = "sentence"      # Sentence-based splitting
    FIXED_SIZE = "fixed_size"  # Fixed token count

class ChunkingConfig(BaseModel):
    strategy: ChunkStrategy = ChunkStrategy.ADAPTIVE
    min_tokens: int = 800
    max_tokens: int = 1800
    overlap_tokens: int = 100
    preserve_sections: bool = True

class Chunk(BaseModel):
    chunk_id: str
    text: str
    token_count: int
    metadata: dict
    section_headings: List[str]
    pages: List[int]
    document_id: str
    chunk_index: int

class ChunkingService:
    """Unified chunking for all consumers (Qdrant, BM25, LightRAG)."""

    def __init__(self, config: ChunkingConfig):
        self.config = config

    async def chunk_document(
        self,
        parsed_document: DoclingParsedDocument,
        document_id: str
    ) -> List[Chunk]:
        """
        Chunk document using configured strategy.

        This is the SINGLE SOURCE OF TRUTH for chunking.
        All consumers (Qdrant, BM25, LightRAG) MUST use this method.
        """
        if self.config.strategy == ChunkStrategy.ADAPTIVE:
            return await self._chunk_adaptive(parsed_document, document_id)
        elif self.config.strategy == ChunkStrategy.SENTENCE:
            return await self._chunk_sentence(parsed_document, document_id)
        else:
            return await self._chunk_fixed_size(parsed_document, document_id)

    async def _chunk_adaptive(
        self,
        parsed_document: DoclingParsedDocument,
        document_id: str
    ) -> List[Chunk]:
        """Section-aware adaptive chunking (ADR-039)."""
        # 1. Extract sections from Docling JSON
        sections = extract_section_hierarchy(
            parsed_document.document,
            SectionMetadata
        )

        # 2. Apply adaptive merging
        merged = adaptive_section_merging(
            sections,
            min_tokens=self.config.min_tokens,
            max_tokens=self.config.max_tokens
        )

        # 3. Convert to Chunk objects
        chunks = []
        for i, section in enumerate(merged):
            chunk = Chunk(
                chunk_id=f"{document_id}_chunk_{i}",
                text=section.text,
                token_count=section.token_count,
                metadata=section.metadata,
                section_headings=section.headings,
                pages=section.pages,
                document_id=document_id,
                chunk_index=i
            )
            chunks.append(chunk)

        return chunks
```

### 2. Unified Consumer Interface

```python
# Update all consumers to use ChunkingService

# Qdrant Ingestion
async def index_to_qdrant(chunks: List[Chunk]) -> None:
    """Index chunks to Qdrant."""
    points = [
        PointStruct(
            id=chunk.chunk_id,
            vector=await embed(chunk.text),
            payload={
                "text": chunk.text,
                "section_headings": chunk.section_headings,
                "pages": chunk.pages,
                "document_id": chunk.document_id
            }
        )
        for chunk in chunks
    ]
    await qdrant_client.upsert(points)

# BM25 Indexing
async def index_to_bm25(chunks: List[Chunk]) -> None:
    """Index chunks to BM25."""
    for chunk in chunks:
        bm25_engine.add_document(
            doc_id=chunk.chunk_id,
            text=chunk.text
        )

# LightRAG/Neo4j
async def index_to_neo4j(chunks: List[Chunk]) -> None:
    """Index chunks to Neo4j."""
    for chunk in chunks:
        await neo4j_client.create_chunk_node(
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            metadata=chunk.metadata
        )
```

### 3. Index Consistency Validation

```python
# src/core/index_validator.py

class IndexConsistencyValidator:
    """Validate consistency across all indexes."""

    async def validate(self) -> ConsistencyReport:
        """Check that all indexes have same chunks."""
        qdrant_ids = set(await self.qdrant_client.get_all_ids())
        bm25_ids = set(self.bm25_engine.get_all_doc_ids())
        neo4j_ids = set(await self.neo4j_client.get_all_chunk_ids())

        return ConsistencyReport(
            qdrant_count=len(qdrant_ids),
            bm25_count=len(bm25_ids),
            neo4j_count=len(neo4j_ids),
            is_consistent=qdrant_ids == bm25_ids == neo4j_ids,
            missing_in_qdrant=bm25_ids - qdrant_ids,
            missing_in_bm25=qdrant_ids - bm25_ids,
            missing_in_neo4j=qdrant_ids - neo4j_ids
        )
```

---

## Implementation Tasks

### Phase 1: ChunkingService Class (3 SP)
- [ ] Create `src/core/chunking_service.py`
- [ ] Define Chunk model and ChunkingConfig
- [ ] Implement adaptive strategy (wrap existing code)
- [ ] Implement sentence and fixed-size strategies
- [ ] Unit tests (10+ test cases)

### Phase 2: Consumer Migration (2 SP)
- [ ] Update Qdrant ingestion to use ChunkingService
- [ ] Update BM25 indexing to use ChunkingService
- [ ] Update LightRAG/Neo4j to use ChunkingService
- [ ] Integration tests

### Phase 3: Consistency Validation (1 SP)
- [ ] Create IndexConsistencyValidator
- [ ] Add validation endpoint
- [ ] Add monitoring metric
- [ ] Documentation

---

## Acceptance Criteria

- [ ] ChunkingService is single entry point for all chunking
- [ ] All 3 consumers use ChunkingService
- [ ] Configuration supports adaptive/sentence/fixed strategies
- [ ] Index consistency validator confirms alignment
- [ ] Qdrant points == BM25 corpus == Neo4j chunks
- [ ] 80%+ test coverage
- [ ] Documentation updated

---

## Affected Files

```
src/core/chunking_service.py            # NEW: Central service
src/core/index_validator.py             # NEW: Consistency validation
src/components/ingestion/langgraph_nodes.py  # UPDATE: Use ChunkingService
src/components/vector_search/qdrant_client.py  # UPDATE: Accept Chunk objects
src/components/graph_rag/lightrag_wrapper.py   # UPDATE: Accept Chunk objects
tests/unit/test_chunking_service.py     # NEW: Unit tests
tests/integration/test_index_consistency.py  # NEW: Consistency tests
```

---

## Dependencies

- **TD-044:** DoclingParsedDocument Interface (section extraction)
- **ADR-039:** Adaptive Section-Aware Chunking (strategy definition)

---

## Estimated Effort

**Story Points:** 6 SP (remaining work)

**Breakdown:**
- Phase 1 (Service): 3 SP
- Phase 2 (Migration): 2 SP
- Phase 3 (Validation): 1 SP

---

## References

- [SPRINT_PLAN.md - Sprint 16 Feature 16.1](../sprints/SPRINT_PLAN.md#sprint-16)
- [ADR-022: Unified Chunking Service](../adr/ADR-022-unified-chunking-service.md)
- [ADR-039: Adaptive Section-Aware Chunking](../adr/ADR-039-adaptive-section-aware-chunking.md)
- [TD-048: Graph Extraction with Unified Chunks](TD-048_GRAPH_EXTRACTION_UNIFIED_CHUNKS.md)

---

## Target Sprint

**Recommended:** Sprint 36 (architectural foundation)

---

**Last Updated:** 2025-12-04
