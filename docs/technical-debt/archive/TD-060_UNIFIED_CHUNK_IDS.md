# TD-060: Unified Chunk/Document IDs zwischen Qdrant und LightRAG

**Status:** RESOLVED
**Priority:** Medium
**Created:** 2025-12-10
**Resolved:** 2025-12-10
**Sprint:** 42

## Problem

Die Chunk- und Document-IDs zwischen Qdrant (Vector Search) und LightRAG (Graph RAG) sind nicht kompatibel. Ein Cross-System Join ist aktuell nicht möglich.

### Aktueller Zustand

| System | Chunk-ID Format | Document-ID Format |
|--------|-----------------|-------------------|
| **Qdrant** | `hotpot_000245_ctx_2` (leserlich) | Fehlt / `source` field |
| **LightRAG vdb** | `chunk-{md5_hash}` | `{uuid}` |
| **Neo4j** | `source_id` = chunk hash | `file_path` = UUID |

### Beispiele

**Qdrant:**
```json
{
  "id": "00017a15-4db8-4fb7-8f4a-8bc987e9dc14",
  "payload": {
    "chunk_id": "hotpot_000245_ctx_2",
    "source": "hotpotqa",
    "namespace_id": "eval_hotpotqa"
  }
}
```

**LightRAG:**
```json
{
  "__id__": "ent-6bcbee33a730f7e475d05f96cc7d6d16",
  "source_id": "chunk-abe18b24d375c0c2fbaf21db63265708",
  "file_path": "a6b356f0-7763-5bf5-a57e-93bdb368bace"
}
```

## Auswirkung

1. **Keine Provenance-Verknüpfung**: Wenn Graph-Suche Entity X findet, können wir nicht direkt den zugehörigen Qdrant-Chunk abrufen
2. **Doppelte Embeddings**: Beide Systeme embedden Chunks separat (gleiche Daten, 2x Speicher)
3. **Kein Cross-System Ranking**: Vector-Score und Graph-Relevanz können nicht kombiniert werden
4. **Keine Deduplizierung**: Gleicher Content kann in beiden Systemen mit unterschiedlichen IDs existieren

## Potenzielle Verbesserungen

### Option A: Unified ID Schema bei Ingestion

Bei der Dokument-Ingestion einheitliche IDs generieren:

```python
# Einheitliches Schema
chunk_id = f"doc-{document_hash}_chunk-{chunk_index}"
document_id = f"doc-{document_hash}"

# Speichern in beiden Systemen mit gleicher ID
qdrant.upsert(id=chunk_id, payload={"document_id": document_id, ...})
lightrag.insert(source_id=chunk_id, file_path=document_id, ...)
```

### Option B: ID Mapping Table

Separate Mapping-Tabelle (Redis/SQLite):

```python
{
  "qdrant_chunk_id": "hotpot_000245_ctx_2",
  "lightrag_source_id": "chunk-abe18b24d375c0c2fbaf21db63265708",
  "document_id": "a6b356f0-7763-5bf5-a57e-93bdb368bace"
}
```

### Option C: Cross-Reference bei Retrieval

Bei Hybrid-Suche: Text-basiertes Matching zwischen Qdrant und LightRAG Ergebnissen.

## Erwartete Verbesserungen

1. **Provenance Tracking**: Von Entity → Chunk → Document navigieren
2. **Score Fusion**: Vector-Score + Graph-Confidence kombinieren
3. **Deduplizierung**: Identische Chunks erkennen und fusionieren
4. **Single Embedding Store**: Optional Qdrant als einzigen Vector Store nutzen

## Betroffene Komponenten

- `src/components/ingestion/` - Chunk-ID Generierung
- `src/components/vector_search/` - Qdrant Payload Schema
- `src/components/graph_rag/lightrag_wrapper.py` - LightRAG source_id
- `src/agents/graph.py` - Hybrid Search Result Merging

## Lösung (Sprint 42)

**Option A** wurde implementiert. Die chunk_ids sind jetzt zwischen Qdrant und Neo4j vereinheitlicht.

### Änderungen

1. **Neue Methode `insert_prechunked_documents()`** in `src/components/graph_rag/lightrag_wrapper.py`:
   - Akzeptiert vorbereitete Chunks mit existierenden chunk_ids von embedding_node
   - Überspringt internes Re-Chunking (_chunk_text_with_metadata)
   - Verwendet die übergebenen chunk_ids direkt als source_id in Neo4j

2. **Anpassung `graph_extraction_node()`** in `src/components/ingestion/langgraph_nodes.py`:
   - Verwendet jetzt `insert_prechunked_documents()` statt `insert_documents_optimized()`
   - Übergibt `embedded_chunk_ids` aus dem Pipeline-State
   - Chunk-IDs werden nicht mehr regeneriert

### Verifizierung

Test-Skript: `scripts/test_ragas_langgraph_ingestion.py`

```
Pipeline chunks: 1
Qdrant chunks:   1
Neo4j source_ids: 1

Pipeline ∩ Qdrant: 1
Qdrant ∩ Neo4j:    1

✅ SUCCESS: Chunk IDs are aligned between Qdrant and Neo4j!
  ✓ 5d8ed057-c09c-5cee-a6a2-ef626e12cd04
```

### Ergebnis

| Location | ID | Value |
|----------|-----|-------|
| Qdrant chunk_id | ✓ | `5d8ed057-c09c-5cee-a6a2-ef626e12cd04` |
| Neo4j entity.source_id | ✓ | `5d8ed057-c09c-5cee-a6a2-ef626e12cd04` |
| Neo4j chunk.chunk_id | ✓ | `5d8ed057-c09c-5cee-a6a2-ef626e12cd04` |

## Referenzen

- ADR-024: BGE-M3 Embeddings
- ADR-040: LightRAG Neo4j Schema
- Sprint 42: True Hybrid Mode
