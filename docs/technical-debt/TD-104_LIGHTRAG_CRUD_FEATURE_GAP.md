# TD-104: LightRAG CRUD Feature Gap

**Status:** OPEN
**Priority:** MEDIUM
**Story Points:** 11 SP
**Target Sprint:** Sprint 89
**Created:** 2026-01-13
**Discovered During:** Sprint 87 (BGE-M3 Native Hybrid)

---

## Summary

LightRAG v1.4.9.8 provides comprehensive CRUD APIs for entities, relations, and data export that are **not exposed** through our AegisRAG wrapper (`src/components/graph_rag/lightrag/client.py`). These APIs enable manual KG curation, data portability, and operational management that users cannot currently access.

---

## Problem Statement

Our `LightRAGClient` wrapper only exposes:
- `insert_documents()`
- `insert_prechunked_documents()`
- `query_graph()`
- `get_stats()`
- `health_check()`

LightRAG natively provides **18+ additional methods** we don't expose, including:
- Entity CRUD (create, edit, delete, merge)
- Relation CRUD (create, edit, delete)
- Data export (CSV, Excel, Markdown)
- Document management (delete by doc_id, get by status)
- Cache management (clear LLM cache)

---

## LightRAG vs AegisRAG Comparison

### Feature Gap Analysis

| Category | LightRAG Method | AegisRAG Status | Priority |
|----------|-----------------|-----------------|----------|
| **Entity CRUD** | | | |
| Create Entity | `acreate_entity()` | NOT EXPOSED | P1 |
| Edit Entity | `aedit_entity()` | NOT EXPOSED | P1 |
| Delete Entity | `adelete_by_entity()` | NOT EXPOSED | P1 |
| Merge Entities | `amerge_entities()` | NOT EXPOSED | P1 |
| Get Entity Info | `get_entity_info()` | Via Neo4j (partial) | P2 |
| **Relation CRUD** | | | |
| Create Relation | `acreate_relation()` | Partial (`_store_relations_to_neo4j`) | P1 |
| Edit Relation | `aedit_relation()` | NOT EXPOSED | P1 |
| Delete Relation | `adelete_by_relation()` | NOT EXPOSED | P1 |
| Get Relation Info | `get_relation_info()` | Via Neo4j (partial) | P2 |
| **Data Export** | | | |
| Export to CSV | `aexport_data(format="csv")` | NOT EXPOSED | P1 |
| Export to Excel | `aexport_data(format="excel")` | NOT EXPOSED | P1 |
| Export to Markdown | `aexport_data(format="md")` | NOT EXPOSED | P2 |
| **Document Management** | | | |
| Delete by Doc ID | `adelete_by_doc_id()` | NOT EXPOSED | P1 |
| Get Docs by Status | `get_docs_by_status()` | NOT EXPOSED | P2 |
| Get Docs by Track ID | `aget_docs_by_track_id()` | NOT EXPOSED | P2 |
| **Cache/Ops** | | | |
| Clear LLM Cache | `aclear_cache()` | NOT EXPOSED | P2 |
| Get Graph Labels | `get_graph_labels()` | NOT EXPOSED | P2 |
| Insert Custom KG | `ainsert_custom_kg()` | NOT EXPOSED | P3 |

### AegisRAG Unique Strengths (Why We're Better)

| Feature | Description | Sprint |
|---------|-------------|--------|
| 3-Stage Entity Expansion | LLM + Graph N-hop + Synonym fallback | Sprint 78 |
| Community Detection | Louvain/Label Propagation clustering | Sprint 68 |
| Community Summarization | LLM-based community labeling | Sprint 77 |
| Semantic Deduplication | Multiple strategies | Sprint 70+ |
| 3-Rank LLM Cascade | Nemotron3 → GPT-OSS → SpaCy | Sprint 83 |
| Gleaning | Microsoft GraphRAG multi-pass | Sprint 83 |
| Multi-Language SpaCy | DE/EN/FR/ES NER | Sprint 83 |
| BGE-M3 Hybrid Search | Dense + Sparse via FlagEmbedding | Sprint 87 |
| Version Manager | Entity versioning with retention | Sprint 60+ |
| Evolution Tracker | Entity drift detection | Sprint 60+ |
| KG Hygiene Service | Duplicate detection, self-loops | Sprint 60+ |
| Temporal Query Builder | Bi-temporal queries | Sprint 60+ |
| Namespace Isolation | Multi-tenant data separation | Sprint 75 |
| RAGAS Integration | Automated quality metrics | Sprint 74+ |
| C-LARA Intent Classifier | 95% accuracy multi-teacher | Sprint 81 |

---

## Proposed Solution (Sprint 89)

### Feature 89.5: Entity CRUD API (4 SP)

Wrap LightRAG's entity management methods and expose via FastAPI:

```python
# src/api/v1/graph.py (new endpoints)

@router.post("/entities")
async def create_entity(
    name: str,
    entity_type: str,
    description: str,
    source_id: str = "",
):
    """Create a new entity in the knowledge graph."""
    client = await get_lightrag_client_async()
    return await client.rag.acreate_entity(name, {
        "entity_type": entity_type,
        "description": description,
        "source_id": source_id,
    })

@router.put("/entities/{entity_name}")
async def edit_entity(
    entity_name: str,
    updated_data: dict,
    allow_rename: bool = True,
    allow_merge: bool = False,
):
    """Edit an existing entity."""
    client = await get_lightrag_client_async()
    return await client.rag.aedit_entity(
        entity_name, updated_data, allow_rename, allow_merge
    )

@router.delete("/entities/{entity_name}")
async def delete_entity(entity_name: str):
    """Delete an entity and its relationships."""
    client = await get_lightrag_client_async()
    return await client.rag.adelete_by_entity(entity_name)

@router.post("/entities/merge")
async def merge_entities(
    source_entities: list[str],
    target_entity: str,
    merge_strategy: dict | None = None,
):
    """Merge multiple entities into one."""
    client = await get_lightrag_client_async()
    return await client.rag.amerge_entities(
        source_entities, target_entity, merge_strategy
    )
```

### Feature 89.6: Relation CRUD API (3 SP)

```python
@router.post("/relations")
async def create_relation(
    source_entity: str,
    target_entity: str,
    description: str,
    keywords: str,
    weight: float = 1.0,
):
    """Create a new relation between entities."""
    client = await get_lightrag_client_async()
    return await client.rag.acreate_relation(source_entity, target_entity, {
        "description": description,
        "keywords": keywords,
        "weight": weight,
    })

@router.put("/relations/{source_entity}/{target_entity}")
async def edit_relation(
    source_entity: str,
    target_entity: str,
    updated_data: dict,
):
    """Edit an existing relation."""
    client = await get_lightrag_client_async()
    return await client.rag.aedit_relation(source_entity, target_entity, updated_data)

@router.delete("/relations/{source_entity}/{target_entity}")
async def delete_relation(source_entity: str, target_entity: str):
    """Delete a relation."""
    client = await get_lightrag_client_async()
    return await client.rag.adelete_by_relation(source_entity, target_entity)
```

### Feature 89.7: Data Export API (2 SP)

```python
@router.get("/export")
async def export_graph_data(
    format: str = "csv",  # csv, excel, md
    include_vector_data: bool = False,
):
    """Export all entities and relations."""
    client = await get_lightrag_client_async()
    output_path = f"/tmp/graph_export_{uuid.uuid4()}.{format}"
    await client.rag.aexport_data(output_path, format, include_vector_data)
    return FileResponse(output_path)
```

### Feature 89.8: Document Deletion API (2 SP)

```python
@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and its associated chunks/entities."""
    client = await get_lightrag_client_async()

    # LightRAG deletion
    result = await client.rag.adelete_by_doc_id(doc_id)

    # Also clean Qdrant (guaranteed sync)
    qdrant = get_qdrant_client()
    await qdrant.delete_by_doc_id(doc_id)

    return {"deleted": True, "doc_id": doc_id, "details": result}
```

---

## Acceptance Criteria

- [ ] Entity CRUD endpoints implemented and tested
- [ ] Relation CRUD endpoints implemented and tested
- [ ] Export endpoint supports CSV, Excel, Markdown
- [ ] Document deletion with Qdrant sync
- [ ] OpenAPI documentation updated
- [ ] Integration tests (>80% coverage)
- [ ] Admin UI integration (optional, Sprint 90)

---

## Story Point Breakdown

| Feature | SP | Description |
|---------|-----|-------------|
| 89.5: Entity CRUD API | 4 | create, edit, delete, merge |
| 89.6: Relation CRUD API | 3 | create, edit, delete |
| 89.7: Data Export API | 2 | CSV, Excel, Markdown |
| 89.8: Document Deletion | 2 | with Qdrant sync |
| **Total** | **11** | |

---

## Related Documents

- [Sprint 87 Feature 87.4](../sprints/SPRINT_87_FEATURE_87.4_IMPLEMENTATION.md) - Embedding Node Integration
- [LightRAG Source](venv/lib/python3.12/site-packages/lightrag/lightrag.py) - v1.4.9.8
- [LightRAGClient Wrapper](../../src/components/graph_rag/lightrag/client.py)

---

## Archive Criteria

This TD can be archived when:
1. All 4 features (89.5-89.8) are implemented
2. Unit and integration tests pass
3. OpenAPI docs updated
4. Sprint 89 complete

---

**Resolution Target:** Sprint 89 (alongside RAGAS Phase 3)
