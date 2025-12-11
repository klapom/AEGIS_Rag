# TD-059: Cross-Encoder Reranking im Docker-Container deaktiviert

**Status:** OPEN
**Priority:** Medium
**Created:** 2025-12-09
**Sprint:** 42

## Problem

Das Cross-Encoder Reranking (`ms-marco-MiniLM-L-6-v2`) ist im Docker-Container deaktiviert, da `sentence-transformers` nicht installiert ist.

**Fehlermeldung:**
```
sentence-transformers is required for reranking. Install with: poetry install --with reranking
```

## Hintergrund

| Komponente | Modell | Library | Status |
|------------|--------|---------|--------|
| **Embeddings** | BGE-M3 | Ollama | ✅ Funktioniert |
| **Reranking** | ms-marco-MiniLM-L-6-v2 | sentence-transformers | ❌ Deaktiviert |

- **Embeddings** werden via Ollama erzeugt (BGE-M3, 1024-dim)
- **Reranking** verwendet einen separaten Cross-Encoder, der Query+Document zusammen bewertet
- Cross-Encoder benötigt `sentence-transformers` Library

## Aktuelle Lösung

Reranking wurde deaktiviert via:
- `VECTOR_AGENT_USE_RERANKING=false` in `docker-compose.dgx-spark.yml`
- Default in `hybrid_search()` auf `False` gesetzt

Die Suche funktioniert ohne Reranking - nur etwas weniger präzise bei der Ergebnis-Sortierung.

## Auswirkung

- **Ohne Reranking:** Vector + BM25 + RRF Fusion (immer noch gute Qualität)
- **Mit Reranking:** Zusätzliche Cross-Encoder Bewertung für bessere Relevanz-Sortierung

## Lösungsoptionen

### Option A: sentence-transformers im Container installieren
```dockerfile
# Im Dockerfile
RUN pip install sentence-transformers
```
**Nachteil:** Erhöht Container-Größe erheblich (~2GB für PyTorch + Transformers)

### Option B: Reranking via Ollama/vLLM
Ein reranking-fähiges Modell auf DGX Spark deployen:
- `BAAI/bge-reranker-v2-m3`
- `jinaai/jina-reranker-v2-base-multilingual`

**Vorteil:** Nutzt bestehende Ollama-Infrastruktur

### Option C: Separater Reranking-Service
Eigener Container für Reranking mit sentence-transformers.

**Vorteil:** Isolation, keine Änderung am API-Container

## Empfehlung

**Option B** - Reranking via Ollama mit BGE-Reranker-v2-m3 implementieren.
Das Modell ist multilingual und kompatibel mit BGE-M3 Embeddings.

## Betroffene Dateien

- `src/components/vector_search/hybrid_search.py`
- `src/agents/vector_search_agent.py`
- `src/components/retrieval/reranker.py`
- `docker-compose.dgx-spark.yml`

## Referenzen

- ADR-024: BGE-M3 Embeddings
- [BGE-Reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3)
