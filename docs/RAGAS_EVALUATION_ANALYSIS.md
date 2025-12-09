# RAGAS Evaluation Analysis

## Status: Sprint 41 - Initial Analysis

**Date:** 2025-12-09
**Author:** Claude Code

---

## 1. Current Pipeline Gap

### Problem
Die `BenchmarkCorpusIngestionPipeline` umgeht die vollständige Ingestion-Pipeline:

| Component | Frontend Pipeline | Evaluation Pipeline | Gap |
|-----------|------------------|---------------------|-----|
| Qdrant (Vector) | embedding_node | _batch_ingest_contexts | OK |
| BM25 Index | Nach Ingestion refreshed | Nicht aktualisiert | BM25=0 results |
| Neo4j (Entities) | graph_extraction_node | Nicht aufgerufen | Graph Local=0 |
| Community Detection | graph_extraction_node | Nicht aufgerufen | Graph Global=0 |

### Debug-Ergebnis (HotpotQA Frage 1)
```
Channel Contributions:
  - Vector: 15 results     ✓
  - BM25: 0 results        ✗ (not fitted)
  - Graph Local: 0 results ✗ (no entities)
  - Graph Global: 0 results (weight=0 for factual)
```

---

## 2. Solution: Full Pipeline Integration

### Ansatz: LangGraph-Nodes wiederverwenden

Die RAGAS-Kontexte als "bereits gechunkte" Dokumente behandeln und durch:
1. `embedding_node` → Qdrant
2. `graph_extraction_node` → Neo4j + BM25

### Zu implementieren in `corpus_ingestion.py`

```python
# Nach Qdrant upsert zusätzlich:

# 1. BM25-Index aktualisieren
from src.components.vector_search.bm25_search import get_bm25_search
bm25 = get_bm25_search()
bm25.fit(texts)  # oder add_documents()

# 2. Graph Extraction → Neo4j Entities
from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
lightrag = await get_lightrag_wrapper_async()
await lightrag.ainsert(full_text, metadata)
```

---

## 3. RAGAS Metrics (Baseline - Vector Only)

| Metric | Score | Note |
|--------|-------|------|
| Context Precision | 0.65 | Nur Vector Search |
| Context Recall | 0.90 | Gute Abdeckung |
| Faithfulness | 0.60 | LLM-basiert |
| Answer Relevancy | 0.72 | LLM-basiert |

**Erwartung nach Full Pipeline:** +10-15% bei Context Precision durch BM25+Graph

---

## 4. Next Steps

- [ ] Sprint 43: Full Pipeline Integration für Evaluation
- [ ] BM25-Index nach Ingestion aktualisieren
- [ ] Graph Extraction für Evaluation-Kontexte aktivieren
- [ ] Vergleichsmessung: Vector-only vs. 4-Way Hybrid

---

## 5. Debug-Script

Verfügbar unter: `scripts/debug_single_query.py`

```bash
# Einzelne Frage debuggen
poetry run python scripts/debug_single_query.py --question 0

# Eigene Frage testen
poetry run python scripts/debug_single_query.py --custom "What is Python?"
```

Zeigt: Embedding → Intent → 4-Way Search → LLM Answer
