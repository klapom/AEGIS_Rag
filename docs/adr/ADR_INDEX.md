# Architecture Decision Records (ADR)
## AegisRAG Project

ADRs dokumentieren wichtige Architektur-Entscheidungen mit Kontext, Alternativen und Begründung.

**Format:** [MADR](https://adr.github.io/madr/) (Markdown Any Decision Records)

---

## ADR Index

| # | Title | Status | Date |
|---|-------|--------|------|
| 001 | LangGraph als Orchestrierungs-Framework | Accepted | 2025-01-15 |
| 002 | Ollama-First LLM Strategy mit optionalem Azure OpenAI | Accepted | 2025-01-15 |
| 003 | Hybrid Vector-Graph Retrieval Architecture | Accepted | 2025-01-15 |
| 004 | Qdrant als primäre Vector Database | Accepted | 2025-01-15 |
| 005 | LightRAG statt Microsoft GraphRAG | Accepted | 2025-01-15 |
| 006 | 3-Layer Memory Architecture | Accepted | 2025-01-15 |
| 007 | Model Context Protocol Integration | Accepted | 2025-01-15 |
| 008 | Python + FastAPI für Backend | Accepted | 2025-01-15 |
| 009 | Reciprocal Rank Fusion für Hybrid Search | Accepted | 2025-01-15 |

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

## ADR-002: Ollama-First LLM Strategy mit optionalem Azure OpenAI

### Status
**Accepted** (2025-01-15, Updated: 2025-10-14)

### Context
Für die Entwicklung und den Betrieb des AEGIS RAG Systems benötigen wir eine LLM-Strategie, die folgende Anforderungen erfüllt:
- **Kosteneffizienz:** Entwicklung sollte ohne laufende API-Kosten möglich sein
- **Offline-Fähigkeit:** Entwicklung auch ohne Internetverbindung
- **Flexibilität:** Option für Production-Grade LLMs bei Bedarf
- **Bundeswehr-Compliance:** Möglichkeit für vollständig lokalen Betrieb
- **Performance:** Akzeptable Latenz für Entwicklung und Testing

### Decision
Wir verwenden **Ollama als primäres LLM für Entwicklung und Testing**, mit **optionaler Azure OpenAI Integration für Production**.

**Dual-Stack Approach:**
1. **Development/Testing (Sprint 1-6):** 100% Ollama (lokal, kostenfrei)
2. **Integration (Sprint 7):** Azure OpenAI Support hinzufügen (optional)
3. **Production (Sprint 8-10):** Konfigurierbar zwischen Ollama und Azure OpenAI

### Alternatives Considered

#### 1. Azure OpenAI Primär
**Pro:**
- Höchste Qualität (GPT-4o, GPT-4o-mini)
- Beste Strukturierte Outputs
- Enterprise Support von Microsoft
- DSGVO-konform durch EU-Hosting

**Contra:**
- Laufende Kosten ab Tag 1 ($200-500/Monat bei Entwicklung)
- Internetverbindung erforderlich
- Vendor Lock-in
- API-Limits und Quotas
- Nicht für vollständig air-gapped Deployment geeignet

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

#### 3. OpenAI API (direkt)
**Pro:**
- Direkter Zugang zu neuesten Modellen
- Günstiger als Azure OpenAI
- Mehr Features (DALL-E, Whisper)

**Contra:**
- Nicht DSGVO-konform
- Keine SLA/Enterprise Support
- Daten gehen nach USA
- Nicht für Bundeswehr geeignet

#### 4. Vollständig lokale Lösung (nur Ollama)
**Pro:**
- 100% kostenfrei
- Volle Datenkontrolle
- Kein Vendor Lock-in
- Air-gapped deployment möglich

**Contra:**
- Qualität unter Cloud-LLMs (besonders für komplexe Reasoning)
- Höhere Hardware-Anforderungen
- Langsamere Inferenz
- Weniger Structured Output Support

### Rationale

**Warum Ollama-First?**

1. **Kosteneffizienz:** $0 während gesamter Entwicklung (Sprint 1-6)
   - Azure OpenAI: ~$300-500/Monat für Development
   - Ollama: Vollständig kostenfrei
   - ROI: ~$2000-3000 Ersparnis in Entwicklungsphase

2. **Offline Development:**
   - Entwicklung im Zug, zu Hause, ohne VPN
   - Keine API-Limits oder Throttling
   - Keine Abhängigkeit von Azure-Verfügbarkeit

3. **Bundeswehr-Compliance:**
   - Möglichkeit für vollständig air-gapped Deployment
   - Keine Daten verlassen lokales Netzwerk
   - VS-NfD kompatibel (falls erforderlich)

4. **Modern Model Performance:**
   - Llama 3.2 (3B/8B) sind hochperformant
   - Ausreichend für 80-90% der Use Cases
   - Schnelle lokale Inferenz

5. **Flexibilität für Production:**
   - Azure OpenAI bleibt Option für Production
   - Konfigurierbar per Environment Variable
   - Keine Code-Änderungen nötig für Switch

**Warum Azure OpenAI Optional?**

- **Quality:** Falls Ollama-Qualität nicht ausreicht
- **Speed:** Cloud-Inferenz kann schneller sein für große Modelle
- **Features:** Structured Outputs, Function Calling besser unterstützt
- **Enterprise:** Falls Support und SLA benötigt werden

### Implementation Strategy

**Ollama Models:**
```bash
# Primäre Models für Development
ollama pull llama3.2:3b        # Fast, 2GB RAM, Query Understanding
ollama pull llama3.2:8b        # Quality, 4.7GB RAM, Generation
ollama pull nomic-embed-text   # Embeddings, 768-dim, 274MB
ollama pull mistral:7b         # Alternative/Fallback
```

**Environment-Based LLM Selection:**
```python
# config/llm_config.py
def get_llm(task_type: str = "generation") -> BaseLLM:
    """Select LLM based on environment and task."""

    # Check if Azure OpenAI is configured
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    use_azure = os.getenv("USE_AZURE_LLM", "false").lower() == "true"

    if azure_endpoint and use_azure:
        # Production: Azure OpenAI
        if task_type == "query_understanding":
            return AzureChatOpenAI(model="gpt-4o-mini")
        else:
            return AzureChatOpenAI(model="gpt-4o")
    else:
        # Development: Ollama
        if task_type == "query_understanding":
            return ChatOllama(model="llama3.2:3b")
        else:
            return ChatOllama(model="llama3.2:8b")
```

**Migration Path:**
- **Sprint 1-6:** Develop with Ollama only
- **Sprint 7:** Add Azure OpenAI integration layer
- **Sprint 8:** A/B testing between Ollama and Azure
- **Sprint 9-10:** Performance benchmarking, final decision

### Consequences

**Positive:**
- ✅ **$0 Entwicklungskosten** für LLM API
- ✅ **Offline-fähige Entwicklung** ohne Cloud-Abhängigkeit
- ✅ **Bundeswehr-kompatibel** (air-gapped möglich)
- ✅ **Kein Vendor Lock-in** - easy migration
- ✅ **Fast Iteration** - keine API-Limits
- ✅ **Privacy by Design** - Daten bleiben lokal

**Negative:**
- ⚠️ **Qualität:** Lokale Modelle unter Cloud-LLMs für komplexe Tasks
- ⚠️ **Hardware:** Mindestens 8GB RAM für llama3.2:8b
- ⚠️ **Entwicklungsaufwand:** LLM-Abstraction Layer nötig
- ⚠️ **Testing:** Beide LLM-Backends müssen getestet werden

**Mitigations:**
- **Qualität:** Azure OpenAI als Fallback für kritische Use Cases
- **Hardware:** Kleinere Modelle (3B) für schwächere Hardware
- **Abstraction:** Clean LLM interface von Anfang an
- **Testing:** Automated tests mit beiden Backends (CI/CD)

### Performance Comparison

| Metric | Ollama (llama3.2:8b) | Azure GPT-4o-mini | Azure GPT-4o |
|--------|---------------------|-------------------|--------------|
| **Latency** | 200-500ms | 150-300ms | 300-600ms |
| **Quality** | Good (7/10) | Very Good (8.5/10) | Excellent (9.5/10) |
| **Cost** | $0 | $0.15/1M tokens | $2.50/1M tokens |
| **Context** | 128K | 128K | 128K |
| **Offline** | ✅ Yes | ❌ No | ❌ No |

### Compliance & Security

**Bundeswehr Requirements:**
- ✅ **VS-NfD:** Ollama kann vollständig offline laufen
- ✅ **Geheim:** Lokale Deployment ohne externe Verbindungen
- ✅ **Data Residency:** 100% Deutschland/lokal
- ⚠️ **Azure OpenAI:** Nur für nicht-klassifizierte Daten (DSGVO-konform)

**Security Considerations:**
- Ollama: Keine Daten verlassen Netzwerk
- Azure OpenAI: EU-Hosting, DSGVO-konform, aber Cloud-Service
- Empfehlung: Ollama für sensible Daten, Azure optional für öffentliche Daten

### Review Criteria

Nach Sprint 6 evaluieren wir:
1. **Quality:** Ist Ollama-Qualität ausreichend? (Target: >80% user satisfaction)
2. **Performance:** Sind Latenzen akzeptabel? (Target: <500ms p95)
3. **Cost:** Rechtfertigen Einsparungen die Qualitäts-Unterschiede?
4. **Compliance:** Ist air-gapped deployment tatsächlich erforderlich?

**Decision Matrix:**
- Ollama ausreichend → Bleibe bei Ollama (auch Production)
- Ollama nicht ausreichend → Aktiviere Azure OpenAI für Production
- Hybrid → Ollama für unkritische Queries, Azure für kritische

### References
- [Ollama Documentation](https://ollama.ai/docs)
- [LangChain Ollama Integration](https://python.langchain.com/docs/integrations/llms/ollama)
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Llama 3.2 Model Card](https://huggingface.co/meta-llama/Llama-3.2-8B)

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

## ADR-007: Model Context Protocol Integration

### Status
**Accepted** (2025-01-15)

### Context
Tool-Integration benötigt standardisierten Ansatz. Custom Integrations skalieren nicht (N×M Problem). MCP etabliert sich als Universal-Standard mit Industry-wide Adoption.

### Decision
Wir implementieren **Model Context Protocol (MCP)** für alle Tool-Integrationen.

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
MCP ist der emerging Standard:
1. **Industry Adoption:** OpenAI, Google, Microsoft, Anthropic
2. **Framework Support:** LangChain, LlamaIndex, CrewAI, OpenAI SDK
3. **Standardisierung:** OAuth 2.1, JSON-RPC, Type-Safe Schemas
4. **Ecosystem:** 500+ Community Servers, 9 Official SDKs
5. **Future-Proof:** Spec Maturity (2025-06-18 Spec)

**Strategisch:** Investing in MCP now = Compatibility mit zukünftigen AI Systems.

### Consequences
**Positive:**
- Kompatibel mit allen Major AI Frameworks
- Wiederverwendbare Tool Definitions
- Community-built Servers (Slack, Jira, Drive)
- Standardisierte Authentication (OAuth 2.1)

**Negative:**
- Zusätzliche Abstraction Layer
- Lernkurve für neues Protokoll
- MCP Server Maintenance

**Mitigations:**
- Start mit Official Python SDK (gut dokumentiert)
- Nutze Community Servers wo möglich
- stdio Transport für MVP (einfacher als HTTP)
- Plain-HTTP Fallback für kritische Services

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
