# Architecture Decision Records (ADR)
## AegisRAG Project

ADRs dokumentieren wichtige Architektur-Entscheidungen mit Kontext, Alternativen und Begründung.

**Format:** [MADR](https://adr.github.io/madr/) (Markdown Any Decision Records)

---

## ADR Index

| # | Title | Status | Date |
|---|-------|--------|------|
| 001 | LangGraph als Orchestrierungs-Framework | Accepted | 2025-01-15 |
| 002 | Ollama-Only LLM Strategy | Accepted | 2025-01-15 |
| 003 | Hybrid Vector-Graph Retrieval Architecture | Accepted | 2025-01-15 |
| 004 | Qdrant als primäre Vector Database | Accepted | 2025-01-15 |
| 005 | LightRAG statt Microsoft GraphRAG | Accepted | 2025-01-15 |
| 006 | 3-Layer Memory Architecture | Accepted | 2025-01-15 |
| 007 | Model Context Protocol Integration | Accepted | 2025-01-15 |
| 008 | Python + FastAPI für Backend | Accepted | 2025-01-15 |
| 009 | Reciprocal Rank Fusion für Hybrid Search | Accepted | 2025-01-15 |
| 010 | Adaptive Chunking Strategy | Accepted | 2025-10-15 |
| 011 | Pydantic Settings for Configuration Management | Accepted | 2025-10-14 |
| 012 | Embedding Model Selection (nomic-embed-text) | Superseded | 2025-10-14 |
| 013 | Document Parsing Strategy (LlamaIndex) | Superseded | 2025-10-14 |
| 014 | E2E Integration Testing Strategy | Accepted | 2025-10-17 |
| 015 | Critical Path Testing Strategy | Accepted | 2025-10-17 |
| 016 | BGE-M3 Embedding Model für Graphiti | Accepted | 2025-10-22 |
| 017 | Semantic Entity Deduplication | Accepted | 2025-10-24 |
| 018 | Model Selection for Entity/Relation Extraction | Accepted | 2025-10-24 |
| 019 | Integration Tests as E2E Tests | Accepted | 2025-10-27 |
| 020 | Server-Sent Events (SSE) Streaming for Chat | Accepted | 2025-10-27 |
| 021 | Perplexity-Inspired UI Design for Frontend | Accepted | 2025-10-27 |
| 022 | Unified Chunking Service | Accepted | 2025-10-28 |
| 023 | Unified Re-Indexing Pipeline | Accepted | 2025-10-28 |
| 024 | BGE-M3 System-Wide Embedding Standardization | Accepted | 2025-10-28 |
| 025 | Mem0 as Layer 0 for User Preference Learning | Accepted | 2025-10-31 |
| 026 | Pure LLM Extraction as Default Pipeline | Accepted | 2025-11-07 |
| 027 | Docling Container vs. LlamaIndex for Document Ingestion | Accepted | 2025-11-07 |
| 028 | Docling-First Hybrid Ingestion Strategy | Accepted | 2025-11-07 |
| 029 | React Frontend Migration Deferral | Accepted | 2025-11-07 |
| 030 | Sprint Extension from 12 to 21+ Sprints | Accepted | 2025-11-07 |
| 031 | Ollama Cloud Hybrid Execution | Superseded | 2025-11-11 |
| 032 | Multi-Cloud Execution Strategy | Superseded | 2025-11-11 |
| 033 | Mozilla ANY-LLM Framework Integration | Accepted | 2025-11-13 |
| 034 | Perplexity-Inspired UX Features | Accepted | 2025-11-16 |
| 035 | Parallel Development Strategy | Accepted | 2025-11-16 |
| 036 | Settings Management via localStorage | Accepted | 2025-11-16 |
| 037 | Alibaba Cloud Extraction (Complexity.HIGH Routing) | Accepted | 2025-11-19 |
| 038 | DashScope Custom Parameters via OpenAI SDK extra_body | Accepted | 2025-11-19 |
| 039 | Adaptive Section-Aware Chunking | Accepted | 2025-11-24 |
| 040 | LightRAG Neo4j Schema Alignment | Accepted | 2025-12-01 |
| 041 | Entity→Chunk Expansion & 3-Stage Semantic Search | Accepted | 2026-01-08 |
| 042 | Bi-Temporal Queries - Opt-In Strategy | Accepted | 2025-12-08 |
| 043 | Secure Shell Sandbox for Tool Execution | Accepted | 2025-12-08 |
| 044 | Hybrid Multi-Criteria Entity Deduplication | Accepted | 2025-12-10 |
| 045 | Namespace Isolation Architecture | Accepted | 2025-12-17 |
| 046 | Comprehensive Refactoring Strategy | Accepted | 2025-12-19 |
| 047 | Hybrid Agent Memory Architecture | Accepted | 2025-12-19 |
| 048 | 1000-Sample RAGAS Benchmark Strategy | Proposed | 2026-01-09 |

---

## ADR-001: LangGraph als Orchestrierungs-Framework

### Status
**Accepted** (2025-01-15)

### Context
Für die Multi-Agent Orchestration benötigen wir ein Framework mit:
- Expliziter Kontrolle über Agent-Workflows
- State Management über Multi-Turn Conversations
- Production-ready Features (Monitoring, Retry Logic)
- Aktive Community und Maintenance

### Decision
Wir verwenden **LangGraph** als primäres Orchestrierungs-Framework.

### Alternatives Considered

#### 1. CrewAI
**Pro:**
- Einfachste Lernkurve
- 5,76x schnellere Ausführung als LangGraph (Benchmarks)
- Rollenbasierter Ansatz sehr intuitiv

**Contra:**
- Weniger Kontrolle über Workflow-Details
- Graph-Visualisierung limitiert
- Jüngeres Ecosystem

#### 2. AutoGen
**Pro:**
- Microsoft-Backing, langfristige Unterstützung
- Event-driven Architecture
- Cross-Language Support (Python + .NET)

**Contra:**
- Mehr Infrastruktur-Setup erforderlich
- Konversations-Paradigma weniger geeignet für deterministische Workflows

#### 3. LlamaIndex Workflows
**Pro:**
- Native RAG-Integration
- Event-driven wie AutoGen
- Weniger Boilerplate als LangGraph

**Contra:**
- Neuere API, weniger mature
- Weniger Ecosystem-Integration

### Rationale
LangGraph bietet die beste Balance aus:
1. **Kontrolle:** Explizite Graph-Definition ermöglicht präzise Workflow-Kontrolle
2. **Production Features:** LangSmith Tracing, Durable Execution, State Persistence
3. **Flexibilität:** Conditional Routing, Cycles, Parallel Execution (Send API)
4. **Ecosystem:** Breite Integration mit LangChain, Vector DBs, Tools

Die höhere Lernkurve wird durch bessere Debuggability und Production-Reife kompensiert.

### Consequences
**Positive:**
- Präzise Kontrolle über komplexe Multi-Agent Workflows
- Exzellentes Debugging via LangGraph Studio + LangSmith
- State Management "out of the box"
- Enterprise-proven (Klarna, Uber, Replit)

**Negative:**
- Steile Lernkurve für Team
- Mehr Boilerplate-Code als CrewAI
- Höhere initiale Development-Zeit

**Mitigations:**
- Team-Training zu LangGraph Concepts
- Reusable Templates für häufige Patterns
- Evaluation nach Sprint 4: Bei gravierenden Problemen → Pivot zu CrewAI

---

## ADR-002: Ollama-Only LLM Strategy

### Status
**Accepted** (2025-01-15, Updated: 2025-10-19)

### Context
Für die Entwicklung und den Betrieb des AEGIS RAG Systems benötigen wir eine LLM-Strategie, die folgende Anforderungen erfüllt:
- **Kosteneffizienz:** Entwicklung und Production ohne laufende API-Kosten
- **Offline-Fähigkeit:** Voller Betrieb ohne Internetverbindung
- **Compliance:** Vollständig lokaler Betrieb ohne externe Abhängigkeiten
- **Performance:** Akzeptable Latenz für alle Szenarien
- **Simplicity:** Keine komplexen Multi-LLM Abstraktionen

### Decision
Wir verwenden **Ollama als einziges LLM-Backend** für Entwicklung, Testing und Production.

**Ollama-Only Approach:**
1. **Development/Testing (Sprint 1-8):** 100% Ollama (lokal, kostenfrei)
2. **Production (Sprint 9-12):** 100% Ollama (lokal, kostenfrei)

### Alternatives Considered

#### 1. Azure OpenAI
**Pro:**
- Höchste Qualität (GPT-4o, GPT-4o-mini)
- Beste Strukturierte Outputs
- Enterprise Support von Microsoft
- DSGVO-konform durch EU-Hosting

**Contra:**
- Laufende Kosten ($200-500/Monat bei Entwicklung, mehr bei Production)
- Internetverbindung erforderlich
- Vendor Lock-in
- API-Limits und Quotas
- Nicht für vollständig air-gapped Deployment geeignet
- Zusätzliche Komplexität durch Multi-LLM Abstraktionen

#### 2. Anthropic Claude (via API)
**Pro:**
- Längerer Context (200K Token)
- Sehr gute Reasoning-Fähigkeiten
- Weniger Hallucinations als GPT-4

**Contra:**
- Ähnliche Kosten wie OpenAI
- Keine EU-Hosting Option
- Kleineres Ecosystem als OpenAI
- Vendor Lock-in
- Zusätzliche Komplexität

#### 3. OpenAI API (direkt)
**Pro:**
- Direkter Zugang zu neuesten Modellen
- Günstiger als Azure OpenAI
- Mehr Features (DALL-E, Whisper)

**Contra:**
- Nicht DSGVO-konform
- Keine SLA/Enterprise Support
- Daten gehen nach USA
- Zusätzliche Komplexität

### Rationale

**Warum Ollama-Only?**

1. **Kosteneffizienz:** $0 für gesamten Lebenszyklus (Development + Production)
   - Azure OpenAI: ~$300-500/Monat für Development, $1000+/Monat für Production
   - Ollama: Vollständig kostenfrei
   - ROI: ~$18,000-24,000 Ersparnis pro Jahr

2. **Offline-Fähigkeit:**
   - Entwicklung und Betrieb ohne Internetverbindung
   - Keine API-Limits oder Throttling
   - Keine Abhängigkeit von Cloud-Verfügbarkeit

3. **Compliance & Privacy:**
   - Vollständig air-gapped Deployment möglich
   - 100% Datenkontrolle - keine Daten verlassen lokales Netzwerk
   - DSGVO-konform durch Design

4. **Modern Model Performance:**
   - Llama 3.2 (3B/8B) sind hochperformant
   - Qwen 2.5 (7B/14B) für komplexere Tasks
   - SmolLM2 (1.7B) für ressourcenlimitierte Umgebungen
   - Ausreichende Qualität für 90%+ der Use Cases
   - Schnelle lokale Inferenz

5. **Architektur-Simplicity:**
   - Kein Multi-LLM Abstraction Layer nötig
   - Reduzierte Komplexität im Code
   - Einfacheres Testing (nur ein Backend)
   - Kein Configuration-Overhead für LLM-Switching

### Implementation Strategy

**Ollama Models:**
```bash
# Primäre Models für Development und Production
ollama pull llama3.2:3b        # Fast, 2GB RAM, Query Understanding
ollama pull llama3.2:8b        # Quality, 4.7GB RAM, Generation
ollama pull nomic-embed-text   # Embeddings, 768-dim, 274MB
ollama pull qwen2.5:7b         # Alternative für komplexe Tasks
ollama pull qwen3:0.6b         # Ultra-lightweight, Entity Extraction
ollama pull smollm2:1.7b       # Ressourcen-limitierte Umgebungen
```

**LLM Selection:**
```python
# config/llm_config.py
def get_llm(task_type: str = "generation") -> BaseLLM:
    """Select LLM based on task type."""

    if task_type == "query_understanding":
        return ChatOllama(model="llama3.2:3b")
    elif task_type == "entity_extraction":
        return ChatOllama(model="qwen3:0.6b")  # Lightweight für LightRAG
    elif task_type == "complex_reasoning":
        return ChatOllama(model="qwen2.5:7b")
    else:
        return ChatOllama(model="llama3.2:8b")
```

**Development Path:**
- **Sprint 1-8:** Core features mit Ollama
- **Sprint 9-12:** Production-Readiness, Performance Optimierung

### Consequences

**Positive:**
- ✅ **$0 Kosten** für LLM (Development + Production)
- ✅ **Offline-fähig** ohne Cloud-Abhängigkeit
- ✅ **Kein Vendor Lock-in**
- ✅ **Keine API-Limits** - unbegrenzte Nutzung
- ✅ **Privacy by Design** - Daten bleiben lokal
- ✅ **Simplere Architektur** - keine Multi-LLM Abstraktion
- ✅ **DSGVO-konform** durch lokalen Betrieb

**Negative:**
- ⚠️ **Qualität:** Lokale Modelle unter Cloud-LLMs für sehr komplexe Tasks
- ⚠️ **Hardware:** Mindestens 8GB RAM für llama3.2:8b
- ⚠️ **Maintenance:** Eigene Modell-Updates erforderlich

**Mitigations:**
- **Qualität:** Größere Ollama-Modelle (qwen2.5:14b) für kritische Tasks
- **Hardware:** Kleinere Modelle (llama3.2:3b, smollm2:1.7b) für schwächere Hardware
- **Maintenance:** Automatische Modell-Updates via Ollama API

### Performance Expectations

| Metric | qwen3:0.6b | llama3.2:3b | llama3.2:8b | qwen2.5:7b |
|--------|-----------|-------------|-------------|------------|
| **Latency** | 50-150ms | 100-300ms | 200-500ms | 250-600ms |
| **Quality** | Good (6.5/10) | Good (7/10) | Very Good (8/10) | Very Good (8.5/10) |
| **Cost** | $0 | $0 | $0 | $0 |
| **Context** | 32K | 128K | 128K | 128K |
| **Offline** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **RAM** | 0.5GB | 2GB | 4.7GB | 4.5GB |
| **Use Case** | Entity Extraction | Query Understanding | Generation | Complex Reasoning |

### Compliance & Security

**Security Requirements:**
- ✅ Ollama läuft vollständig offline
- ✅ Lokale Deployment ohne externe Verbindungen
- ✅ **Data Residency:** 100% lokal
- ✅ **DSGVO-konform** durch Design
- ✅ **Air-gapped** deployment möglich

**Security Considerations:**
- Alle Daten bleiben im lokalen Netzwerk
- Keine externe API-Calls
- Volle Kontrolle über Datenverarbeitung
- Ideal für sensible/klassifizierte Daten

### References
- [Ollama Documentation](https://ollama.ai/docs)
- [LangChain Ollama Integration](https://python.langchain.com/docs/integrations/llms/ollama)
- [Llama 3.2 Release](https://ai.meta.com/blog/llama-3-2-connect-2024-vision-edge-mobile-devices/)
- [Qwen 2.5 Release](https://qwenlm.github.io/blog/qwen2.5/)

---

## ADR-003: Hybrid Vector-Graph Retrieval Architecture

### Status
**Accepted** (2025-01-15)

### Context
RAG-Systeme können primär Vector-basiert, Graph-basiert oder hybrid sein. Research zeigt 40-60% bessere Relevanz für Hybrid-Ansätze, aber höhere Komplexität.

### Decision
Wir implementieren eine **Hybrid Architecture** mit:
- **Qdrant** für semantische Vector Search
- **Neo4j + LightRAG** für Graph-basiertes Reasoning
- **Reciprocal Rank Fusion** für Context Combination

### Alternatives Considered

#### 1. Pure Vector Search (Qdrant only)
**Pro:**
- Simplere Architektur
- Niedrigere Latency (<100ms)
- Einfachere Wartung

**Contra:**
- Keine Multi-Hop Reasoning Fähigkeit
- Schlechter bei relationalen Queries
- Kein temporales Reasoning

#### 2. Pure Graph Search (Neo4j only)
**Pro:**
- Exzellent für Relationship Queries
- Native Community Detection
- Temporal Awareness

**Contra:**
- Schlechter bei semantischer Ähnlichkeit
- Höhere Latency für große Graphen
- Schwieriger Indexing-Prozess

#### 3. Single DB mit Dual Capabilities (Weaviate)
**Pro:**
- Reduzierte Operational Complexity
- Einheitliches Query Interface
- Niedrigere Infrastructure Costs

**Contra:**
- Jack-of-all-trades, master of none
- Weniger optimiert für spezifische Use Cases

### Rationale
Hybrid-Ansatz maximiert Recall und Precision:
1. **Vector Search:** Schnell, skaliert gut, exzellent für semantische Ähnlichkeit
2. **Graph Search:** Multi-Hop Reasoning, Relationship Discovery, Temporal Context
3. **Fusion:** Reciprocal Rank Fusion kombiniert Stärken beider Ansätze

Research-Validierung: 40-60% Improvement in Production-Benchmarks.

### Consequences
**Positive:**
- Beste Retrieval-Qualität für diverse Query-Typen
- Flexibilität: Router kann optimal Strategy wählen
- Future-Proof: Beide Technologies mature und aktiv entwickelt

**Negative:**
- Höhere Operational Complexity (2 Datenbanken)
- Höhere Infrastruktur-Kosten
- Komplexeres Debugging

**Mitigations:**
- Docker Compose für einfache lokale Entwicklung
- Unified Retrieval API abstrahiert Komplexität
- Monitoring Dashboard für beide Systeme
- Start mit Vector-only MVP, füge Graph iterativ hinzu

---

## ADR-004: Qdrant als primäre Vector Database

### Status
**Accepted** (2025-01-15)

### Context
Vector Database benötigt für Production: High Performance, Scalability, Advanced Filtering, Cost-Efficiency, Self-Hosting Option.

### Decision
Wir verwenden **Qdrant** als primäre Vector Database.

### Alternatives Considered

#### 1. Pinecone
**Pro:**
- Einfachste Operations (Managed, Serverless)
- Sub-10ms Latency bei Milliarden Embeddings
- Exzellenter Support

**Contra:**
- Vendor Lock-in (kein Self-Hosting)
- Höhere Kosten bei Scale
- Weniger Kontrolle über Infrastruktur

#### 2. Weaviate
**Pro:**
- Native Hybrid Search (Vector + BM25)
- GraphQL Interface
- Open Source + Managed Option

**Contra:**
- Langsamere Performance als Qdrant
- Höherer Memory-Footprint
- Weniger mature Quantisierung

#### 3. ChromaDB
**Pro:**
- Schnellstes Setup (pip install)
- MCP Server verfügbar
- Gut für Prototyping

**Contra:**
- Nicht für Milliarden-Scale geeignet
- Keine distributed Replication
- Limitierte Production Features

### Rationale
Qdrant bietet optimale Balance:
1. **Performance:** 3ms Latency bei 1M Embeddings (Best in Class)
2. **Cost:** 24x Compression via asymmetrische Quantisierung
3. **Flexibility:** Self-Hosted + Managed Cloud Option
4. **Features:** Advanced Filtering, RBAC, Multi-Tenancy
5. **Integration:** Native Support in LangGraph, CrewAI, LlamaIndex

### Consequences
**Positive:**
- Beste Performance für Production Scale
- Kosteneffizient durch aggressive Quantisierung
- Volle Kontrolle via Self-Hosting
- Aktive Community (21K+ Stars)

**Negative:**
- Kein Managed Service bei Self-Hosting
- Erfordert Operations-Expertise für Tuning

**Mitigations:**
- Start mit Qdrant Cloud für MVP
- Migration zu Self-Hosted nach Product-Market Fit
- Dokumentation für Tuning (Quantisierung, Indexing)

---

## ADR-005: LightRAG statt Microsoft GraphRAG

### Status
**Accepted** (2025-01-15)

### Context
GraphRAG-Technologie benötigt für: Knowledge Graph Construction, Community Detection, Multi-Hop Reasoning. Microsoft GraphRAG ist etabliert aber teuer und statisch.

### Decision
Wir verwenden **LightRAG** als primäres GraphRAG-System.

### Alternatives Considered

#### 1. Microsoft GraphRAG
**Pro:**
- Most mature, 23.8K+ Stars
- Exzellente Documentation
- Azure Integration

**Contra:**
- Extrem hohe Indexing Costs (intensive LLM Usage)
- Statische Graph-Struktur (Full Re-Index bei Updates)
- Keine native Temporal Awareness

#### 2. LlamaIndex PropertyGraph
**Pro:**
- Native Integration mit LlamaIndex Ecosystem
- Flexibles Schema
- Good Documentation

**Contra:**
- Weniger optimiert als dedizierte GraphRAG-Systeme
- Jüngere Entwicklung

#### 3. Keine GraphRAG (nur Vector + Graphiti Memory)
**Pro:**
- Simplere Architektur
- Niedrigere Kosten

**Contra:**
- Kein Community Detection
- Keine Global Search Capability

### Rationale
LightRAG überzeugt durch:
1. **Cost:** Niedrigere Token-Kosten als Microsoft GraphRAG
2. **Speed:** Schnelleres Indexing
3. **Flexibility:** Incremental Updates ohne Full Re-Index
4. **Features:** Dual-Level Retrieval (Entities + Topics)
5. **Developer Experience:** Web UI, API Server, Docker-Ready

Benchmarks zeigen vergleichbare oder bessere Accuracy bei deutlich niedrigeren Kosten.

### Consequences
**Positive:**
- Schnellere Iteration (kein Re-Index bei Updates)
- Niedrigere Betriebskosten
- Bessere Developer Experience (Web UI)
- Multiple Graph Backend Options

**Negative:**
- Jüngeres Projekt (weniger mature als Microsoft)
- Kleinere Community
- Weniger Enterprise-Features

**Mitigations:**
- Active Monitoring der Projekt-Health
- Abstraction Layer erlaubt Swap zu Microsoft GraphRAG
- Community Engagement für Feature Requests

---

## ADR-006: 3-Layer Memory Architecture

### Status
**Accepted** (2025-01-15)

### Context
Agent Memory benötigt unterschiedliche Charakteristiken:
- Short-Term: Ultra-fast Read/Write, Ephemeral
- Long-Term: Semantic Search, Persistent
- Episodic: Temporal Context, Relationship Tracking

### Decision
Wir implementieren **3-Layer Memory Architecture**:
1. **Redis:** Short-Term Working Memory (<10ms)
2. **Qdrant:** Long-Term Semantic Memory (<50ms)
3. **Graphiti + Neo4j:** Episodic Temporal Memory (<100ms)

### Alternatives Considered

#### 1. Single Database (Qdrant only)
**Pro:**
- Simplere Architektur
- Niedrigere Operational Complexity
- Unified API

**Contra:**
- Suboptimal für alle Use Cases
- Keine Temporal Awareness
- Keine ultra-fast Working Memory

#### 2. Two-Layer (Redis + Qdrant)
**Pro:**
- Reduzierte Komplexität vs. 3-Layer
- Ausreichend für viele Use Cases

**Contra:**
- Kein temporales Reasoning
- Kein Relationship Tracking
- Limitierte Long-Term Context

#### 3. SQL-based Unified Memory
**Pro:**
- Bewährte Technologie
- ACID Guarantees
- Einfache Queries

**Contra:**
- Schlechter für Semantic Search
- Kein Graph Traversal
- Höhere Latency

### Rationale
3-Layer Architecture optimiert für unterschiedliche Anforderungen:
1. **Redis:** Session State, Recent Context, Cache → Ultra-Fast
2. **Qdrant:** Semantic Long-Term Memory → Similarity Search
3. **Graphiti:** Relationships, Temporal Evolution → Graph Reasoning

**Memory Router** entscheidet basierend auf Query-Typ und Recency.

### Consequences
**Positive:**
- Optimale Performance für jeden Use Case
- Temporal Awareness (Graphiti Unique Feature)
- Skalierbarkeit (jede Layer unabhängig)
- Future-Proof Design

**Negative:**
- Höchste Komplexität aller Alternativen
- Mehr Operational Overhead
- Data Consistency Challenges

**Mitigations:**
- Start mit 2-Layer (Redis + Qdrant) für MVP
- Füge Graphiti in Sprint 7 hinzu
- Memory Consolidation Pipeline automatisiert Sync
- Monitoring für Consistency Checks

---

## ADR-007: Model Context Protocol Client Integration

### Status
**Accepted** (2025-01-15, Updated: 2025-10-19)

### Context
Tool-Integration benötigt standardisierten Ansatz. Custom Integrations skalieren nicht (N×M Problem). MCP etabliert sich als Universal-Standard mit Industry-wide Adoption.

**Wichtige Unterscheidung:**
- **MCP Server:** Bietet Tools für andere Systeme an (wir SIND der Tool-Provider)
- **MCP Client:** Nutzt Tools von anderen Systemen (wir NUTZEN externe Tools)

### Decision
Wir implementieren einen **MCP Client** um externe MCP-Tools zu nutzen (Filesystem, GitHub, Slack, etc.).

**Kein MCP Server:** Wir bieten vorerst KEINE Tools für andere Systeme an.

### Alternatives Considered

#### 1. Custom Tool Integration (LangChain Tools)
**Pro:**
- Maximale Flexibilität
- Keine zusätzliche Abstraction
- Direkter Code

**Contra:**
- N×M Problem (jede Kombination custom)
- Nicht wiederverwendbar
- Kein Standard

#### 2. Function Calling (Native LLM)
**Pro:**
- Native LLM Support
- Einfache Implementation
- Low Latency

**Contra:**
- LLM-spezifisch (nicht portable)
- Keine complex Tool Composition
- Limitierte Metadata

#### 3. REST APIs ohne Standard
**Pro:**
- Bewährte Technologie
- Einfach zu implementieren

**Contra:**
- Kein Discovery Mechanism
- Keine Tool Composition
- Authentication manuell

### Rationale

**Warum MCP Client?**

1. **Standardisierte Tool-Nutzung:**
   - Zugriff auf 500+ Community MCP Servers (Filesystem, GitHub, Slack, Databases)
   - Keine custom Integration für jedes Tool nötig

2. **Industry Adoption:**
   - OpenAI, Google, Microsoft, Anthropic unterstützen MCP
   - Framework Support: LangChain, LlamaIndex, CrewAI

3. **Zukunftssicherheit:**
   - MCP wird Standard für AI Tool Integration
   - Kompatibilität mit allen MCP-fähigen Systemen

4. **Entwickler-Effizienz:**
   - Nutze bestehende MCP Servers statt eigene zu bauen
   - Standardisierte API, keine custom Protokolle

**Warum KEIN MCP Server (vorerst)?**

- **Bedarf unklar:** Aktuell keine Anforderung, RAG-Tools für andere Systeme bereitzustellen
- **Komplexität:** Server-Implementierung + Maintenance würde Sprint 9 überladen
- **Spätere Option:** Kann bei Bedarf in Post-Sprint 12 hinzugefügt werden

### Consequences

**Positive:**
- ✅ Zugriff auf 500+ Community MCP Servers (ohne eigene Implementation)
- ✅ Standardisierte Tool-Integration (kein N×M Problem)
- ✅ Future-Proof (MCP wird Industry-Standard)
- ✅ Action Agent kann externe Tools nutzen (Filesystem, GitHub, etc.)

**Negative:**
- ⚠️ Abhängigkeit von externen MCP Servers
- ⚠️ Lernkurve für MCP Client SDK
- ⚠️ Zusätzliche Abstraction Layer

**Mitigations:**
- **Abhängigkeit:** Fallback zu direkten API-Calls wenn MCP Server unavailable
- **Lernkurve:** Start mit Official Python SDK (gut dokumentiert)
- **Abstraction:** Thin Wrapper, minimal Overhead

### Implementation Scope

**Sprint 9 (MCP Client Only):**
- ✅ MCP Client Implementation
- ✅ Connection zu 1-2 externen Servern (Filesystem, GitHub)
- ✅ Tool Discovery + Execution
- ✅ Action Agent Integration

**Post-Sprint 12 (Optional: MCP Server):**
- ⏸️ MCP Server Implementation (falls Bedarf)
- ⏸️ RAG-Tools als MCP Services anbieten
- ⏸️ Integration mit Cursor, Claude Desktop, etc.

---

## ADR-008: Python + FastAPI für Backend

### Status
**Accepted** (2025-01-15)

### Context
Backend-Technologie muss AI/ML Ecosystem, Performance, Developer Productivity und Async I/O balancieren.

### Decision
Wir verwenden **Python 3.11+** mit **FastAPI** als Backend-Framework.

### Alternatives Considered

#### 1. TypeScript + Node.js
**Pro:**
- Single Language (Frontend + Backend)
- Exzellente Async Performance
- Type Safety

**Contra:**
- Weniger AI/ML Libraries
- Schwächeres Ecosystem für LLMs
- Schlechtere NumPy/Pandas Integration

#### 2. Go
**Pro:**
- Beste Raw Performance
- Native Concurrency
- Small Binary Size

**Contra:**
- Sehr limitiertes AI/ML Ecosystem
- Keine native LangChain/LlamaIndex
- Höherer Development Overhead

#### 3. Python + Django
**Pro:**
- Batteries-included Framework
- ORM, Admin Panel out-of-box

**Contra:**
- Overkill für API-only Backend
- Langsamer als FastAPI
- Schwergewichtiger

### Rationale
Python + FastAPI ist optimal für AI/ML Applications:
1. **Ecosystem:** LangChain, LlamaIndex, LangGraph alle Python-first
2. **Performance:** FastAPI ist schnellstes Python-Framework (Starlette/Uvicorn)
3. **Developer Experience:** Auto OpenAPI Docs, Type Hints, Pydantic v2
4. **Async:** Native async/await für I/O-bound Operations
5. **Community:** Größte AI/ML Community

### Consequences
**Positive:**
- Nahtlose Integration mit AI/ML Libraries
- Schnelle Development Velocity
- Type Safety via Pydantic
- Auto-generated API Documentation

**Negative:**
- Langsamere Raw Performance vs. Go/Rust
- GIL Limitations (nicht relevant bei I/O-bound)

**Mitigations:**
- Async I/O für alle External Calls
- Caching (Redis) für häufige Queries
- Horizontal Scaling statt Vertical

---

## ADR-009: Reciprocal Rank Fusion für Hybrid Search

### Status
**Accepted** (2025-01-15)

### Context
Hybrid Search benötigt Methode um Vector-Rankings und BM25-Rankings zu kombinieren. Verschiedene Fusion-Strategien verfügbar.

### Decision
Wir verwenden **Reciprocal Rank Fusion (RRF)** als primäre Fusion-Methode.

### Alternatives Considered

#### 1. Weighted Average (Linear Combination)
**Pro:**
- Einfachste Implementation
- Intuitive Interpretation
- Tunable Weights

**Contra:**
- Erfordert Score Normalization
- Weights müssen per Query-Type kalibriert werden
- Empfindlich für Score-Scale Differences

#### 2. CombSUM / CombMNZ
**Pro:**
- Established in IR Research
- Berücksichtigt Anzahl der Votes

**Contra:**
- Komplexer als RRF
- Weniger robust bei unterschiedlichen Score-Ranges

#### 3. Reranking-only (Cross-Encoder after Union)
**Pro:**
- State-of-the-art Quality
- Keine manuelle Fusion

**Contra:**
- Hohe Latency (evaluates all candidates)
- Hohe Compute Costs

### Rationale
RRF überzeugt durch:
1. **Simplicity:** Score-agnostic, keine Normalization
2. **Robustness:** Funktioniert gut ohne Hyperparameter-Tuning
3. **Research-Validated:** Cormack et al. 2009, etablierter Standard
4. **Performance:** k=60 empirisch optimal (original paper)
5. **Implementation:** Single Formula: `score = sum(1/(k+rank))`

RRF ist de-facto Standard in Hybrid Search Systems.

### Consequences
**Positive:**
- Keine Score Normalization nötig
- Robust über verschiedene Query-Types
- Einfach zu implementieren und debuggen
- Research-validated Performance

**Negative:**
- Nicht optimal für alle Edge Cases
- Fixed k=60 (wenig Tuning-Potential)

**Mitigations:**
- Reranking als Post-Processing für Top-K Results
- A/B Testing von k-Werten (optional)
- Logging von Fusion-Metrics für Analysis

---

## ADR Template

Für zukünftige ADRs verwende dieses Template:

```markdown
## ADR-XXX: [Title]

### Status
[Proposed | Accepted | Deprecated | Superseded]

### Context
Was ist die Situation? Welches Problem lösen wir? Welche Constraints existieren?

### Decision
Was haben wir entschieden? Kurz und klar.

### Alternatives Considered
Welche Alternativen haben wir evaluiert?

#### Alternative 1: [Name]
**Pro:**
- Vorteil 1
- Vorteil 2

**Contra:**
- Nachteil 1
- Nachteil 2

### Rationale
Warum diese Decision? Welche Faktoren haben ausschlaggebend?

### Consequences
**Positive:**
- Benefit 1
- Benefit 2

**Negative:**
- Trade-off 1
- Trade-off 2

**Mitigations:**
- Wie adressieren wir Negative Consequences?
```

---

## Decision Review Process

ADRs sollten reviewed werden:
- **Initial:** Vor Implementation (Team Consensus)
- **Quarterly:** Relevanz prüfen (sind Assumptions noch valid?)
- **Post-Incident:** Nach Major Issues (war Decision korrekt?)

Status-Transitions:
- **Proposed → Accepted:** Nach Team-Review und Consensus
- **Accepted → Deprecated:** Wenn bessere Alternative gefunden
- **Accepted → Superseded:** Wenn durch neue ADR ersetzt
