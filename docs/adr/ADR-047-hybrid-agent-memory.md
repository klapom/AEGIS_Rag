# ADR-0XX: Hybrid Agent Memory Architecture (Deterministic Core + mem0 Backend)

**Status:** 🟡 Partially Accepted / Incremental Adoption  
**Date:** 2025-12-19  
**Authors:** Klaus Pommer, ChatGPT  
**Related:**  
- Sprint 59: Agentic Capabilities & Lifecycle  
- ADR-025: mem0 as Layer 0 for User Preference Learning  

---

## Context

### Problem Statement

AEGIS RAG entwickelt sich von einem **klassischen RAG-System** hin zu einer **Agentic Platform** mit:

- langlebigen Agenten
- resume-fähigen Ausführungen
- Tool-Execution mit Sandbox
- Knowledge Graph als objektiver Wissensanker

Im Zuge dessen entsteht ein **neuer Bedarf an Agent Memory**, der sich klar von Dokumentenwissen und episodischem Graph-Wissen unterscheidet.

**Zentrale Anforderungen:**

1. Persistentes Agent-Gedächtnis über Sessions hinweg
2. Deterministischer, auditierbarer AgentRun-Lifecycle
3. Trennung von:
   - objektivem Wissen (KG)
   - subjektiver Agent-Erfahrung (Memory)
4. Optionale Nutzung von mem0 zur Token-Effizienz und Kompression
5. Kein Vendor-Lock-in, kein „Magic Memory“

---

### Aktueller Stand (nach Sprint 59)

Bereits umgesetzt oder in Umsetzung:

✅ AgentRun & LangGraph-basierter Control Flow  
✅ Tool Use Framework mit Sandbox  
✅ Task-/Todo-Tracking im Agent State  
✅ Knowledge Graph (Communities, Relations)  

Noch **nicht vollständig umgesetzt**:

❌ Persistentes Agent Memory  
❌ Standardisiertes Memory-Interface  
❌ Langzeit-Kompression / Token-Optimierung  
❌ Klare Abgrenzung zwischen Agent-Memory und externem Memory-Service  

---

## Decision

Wir entscheiden uns **gegen ein mem0-only-Modell** und **für einen Hybrid-Ansatz**:

> **Deterministischer Agent Core + optionales mem0 als austauschbares Long-Term-Memory-Backend**

mem0 wird **nicht** zur Steuerzentrale des Agenten, sondern zu einer **optionalen Speicher- und Retrieval-Komponente**.

---

## Hybrid Memory Architektur

```
Agent / AgentRun
 ├─ run_id
 ├─ lifecycle (resume, replay, audit)
 ├─ tasks / decisions
 ├─ LangGraph state
 └─ Agent Memory Interface (CORE)
      ├─ episodic
      ├─ procedural
      └─ retention & policies
           ↓
      Optional Memory Backend
      ├─ mem0
      └─ internal store
```

---

## Deployment Architecture

mem0 wird als **separater Docker-Container** deployt, analog zu den anderen Backend-Services:

```yaml
Services Stack:
├── api           # FastAPI (AEGIS RAG Backend)
├── frontend      # React/Vite
├── qdrant        # Vector DB
├── neo4j         # Knowledge Graph
├── redis         # Session/Cache
├── ollama        # LLM Inference
├── docling       # PDF/Document Processing
└── mem0          # Optional: Agent Long-Term Memory (NEU)
```

**Container-Konfiguration (docker-compose.dgx-spark.yml):**

```yaml
mem0:
  image: mem0ai/mem0:latest
  container_name: aegis-mem0
  ports:
    - "8081:8080"  # mem0 API Port
  environment:
    - QDRANT_HOST=qdrant
    - QDRANT_PORT=6333
    - QDRANT_API_KEY=${QDRANT_API_KEY:-}
  networks:
    - aegis-network
  depends_on:
    - qdrant
  restart: unless-stopped
```

**Vorteile dieser Architektur:**

1. **Service-Isolation**: mem0 läuft unabhängig vom Hauptsystem
2. **Optionale Nutzung**: Container kann deaktiviert werden, wenn mem0 nicht benötigt wird
3. **Skalierbarkeit**: mem0 kann separat skaliert werden
4. **Qdrant-Reuse**: Nutzt existierende Qdrant-Instanz für Vektorsuche
5. **Standard-Deployment**: Konsistent mit anderen Services (Ollama, Docling, etc.)

**Zugriff vom Backend:**

```python
# src/components/memory/mem0_client.py
from mem0 import Memory

# Optional: Nur wenn mem0 Container verfügbar ist
if settings.MEM0_ENABLED:
    mem0_client = Memory.from_config({
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "host": "qdrant",
                "port": 6333,
            }
        },
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "nemotron3nano:30b",
                "base_url": "http://ollama:11434",
            }
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": "bge-m3",
                "base_url": "http://ollama:11434",
            }
        }
    })
```

**LLM & Embeddings Stack-Reuse:**

mem0 nutzt die **existierenden AEGIS Services**:

| Komponente | Service | Modell | Zweck |
|------------|---------|--------|-------|
| **LLM** | Ollama | `nemotron3nano:30b` | Memory-Reasoning & Compression |
| **Embeddings** | Ollama | `bge-m3` | Memory-Vektorisierung |
| **Vector Store** | Qdrant | - | Memory-Retrieval |

**Wichtig:** Keine zusätzlichen LLM-Provider oder Embedding-Services nötig - mem0 integriert sich vollständig in den bestehenden Stack!

---

## Consequences

### Positive

- Architekturelle Sauberkeit
- Determinismus & Auditierbarkeit
- Kein Vendor-Lock-in
- Optionale Token-Optimierung

### Negative

- Höhere Komplexität
- Zusätzliche Adapter-Schicht
- Mehr Governance-Aufwand

---

## Rollout Strategy

1. Sprint 59: Lifecycle & Tasks  
2. Sprint 60: Memory Interface  
3. Sprint 61: mem0 PoC & Benchmark  

---

## Approval

- **Architect:** Klaus Pommer  
- **Decision Date:** 2025-12-19  
- **Status:** Incremental Adoption
