# Changelog: LLM-Strategie Migration zu Ollama-First

**Datum**: 2025-10-14
**Änderung**: Migration von Azure OpenAI als primäres LLM zu Ollama-First Strategie

## Zusammenfassung

Das AEGIS RAG Projekt wurde von einer Azure OpenAI-primären Strategie zu einer **Ollama-First Strategie** migriert. Ollama wird nun als primäres LLM für Entwicklung und Testing verwendet, während Azure OpenAI als optionale Production-Alternative erhalten bleibt.

## Hauptgründe für die Migration

1. **Kosteneffizienz**: $0 Entwicklungskosten statt $300-500/Monat
2. **Offline-Fähigkeit**: Entwicklung ohne Internetverbindung möglich
3. **Bundeswehr-Compliance**: Vollständig air-gapped Deployment möglich
4. **Kein Vendor Lock-in**: Flexible Wahl zwischen Ollama und Azure
5. **Privacy by Design**: Daten bleiben lokal während der Entwicklung

## Geänderte Dokumente

### 1. TECH_STACK.md
**Änderungen:**
- LLM Primary: `Ollama (Local)` statt `Azure OpenAI GPT-4o`
- Neue LLM Selection Matrix mit Ollama-Modellen:
  - `llama3.2:3b` für Query Understanding
  - `llama3.2:8b` für Generation
  - `nomic-embed-text` für Embeddings
- Dual-Stack LLM Strategy Code-Beispiele hinzugefügt
- Dependencies aktualisiert: `langchain-ollama`, `llama-index-llms-ollama` als primär
- Cost Estimation: $0 für Development, $0-500 für Production (optional)
- Vector size: 768 (nomic-embed-text) als default, 3072 optional für Azure

### 2. ADR_INDEX.md
**Änderungen:**
- **Neuer ADR-002**: "Ollama-First LLM Strategy mit optionalem Azure OpenAI"
- ADR-Nummerierung aktualisiert (alte ADR-002 bis ADR-008 sind jetzt ADR-003 bis ADR-009)
- ADR-002 enthält:
  - Vollständige Rationale für Ollama-First
  - Alternativen-Vergleich (Azure, Anthropic, OpenAI, Vollständig lokal)
  - Implementation Strategy mit Code-Beispielen
  - Performance Comparison Tabelle
  - Compliance & Security Considerations
  - Review Criteria für Sprint 6

**ADR-002 Key Points:**
- Status: Accepted (2025-01-15, Updated: 2025-10-14)
- Decision: Ollama primär, Azure OpenAI optional
- Migration Path: Sprint 1-6 Ollama only, Sprint 7 Azure Integration, Sprint 8 A/B Testing
- Compliance: VS-NfD und Geheim-kompatibel mit Ollama

### 3. SPRINT_PLAN.md
**Änderungen:**
- **Sprint 2**: Embedding Model Integration: `Ollama nomic-embed-text` statt `OpenAI`
- **Sprint 5**: LightRAG Config mit `Ollama LLM`
- **Sprint 7**: Neuer Titel: "Graphiti Memory + Azure OpenAI Integration (Optional)"
  - 3 neue Deliverables: Azure OpenAI Integration Layer, LLM Abstraction, Environment-based Selection
  - 4 neue Technical Tasks: Azure Client Wrapper, LLM Factory Pattern, Environment Variables, Fallback Logic
  - 2 neue Success Criteria: Dual LLM Support, LLM-Switch ohne Code-Änderung
- **Sprint 8**: Neuer Titel: "3-Layer Memory + LLM A/B Testing"
  - 3 neue Deliverables: A/B Testing Framework, Performance Benchmarks, Quality Metrics
  - 4 neue Technical Tasks: A/B Test Harness, Latency Comparison, Quality Comparison, Cost Tracking
  - 2 neue Success Criteria: Benchmark Report, Decision Matrix dokumentiert
- **Risk Management**:
  - "LLM API Rate Limits": Wahrscheinlichkeit von Hoch → Niedrig (Ollama has no limits)
  - "Budget Überschreitung": Impact von Hoch → Niedrig ($0 development costs)

### 4. PROJECT_SUMMARY.md
**Änderungen:**
- Sprint 7 Titel aktualisiert: "Graphiti Memory + Azure OpenAI (Optional)"
- Sprint 8 Titel aktualisiert: "3-Layer Memory + LLM A/B Testing"

### 5. QUICK_START.md
**Änderungen:**
- **Neue Voraussetzung**: Ollama Installation mit 3 Models
  ```bash
  ollama pull llama3.2:3b
  ollama pull llama3.2:8b
  ollama pull nomic-embed-text
  ```
- **API Keys**: Umbenannt von "API Keys (für später)" zu "API Keys (Optional für Production)"
- **Minimale .env**: Komplett überarbeitet:
  - Ollama-Konfiguration als primär (4 Variablen)
  - Azure OpenAI als optional (auskommentiert, 4 Variablen)
- **Nächste Schritte**: "OpenAI Embedding API Key verifizieren" → "Ollama Models pullen"

### 6. README.md
**Änderungen:**
- Technologie-Stack Section komplett überarbeitet:
  - RAG: `LangGraph, LlamaIndex, LightRAG` (detaillierter)
  - Vector DB: `Qdrant` (spezifisch)
  - Graph DB: `Neo4j` hinzugefügt
  - Memory: `Graphiti` hinzugefügt
  - LLM: `Ollama (lokal, primär) + Azure OpenAI (optional)`
  - Embeddings: Details hinzugefügt
- **Neue Section**: "LLM-Strategie (ADR-002)" mit 3 Key Points
- ADR Count: 8 → 9
- Sprint Plan Details aktualisiert (präzisere Sprint-Beschreibungen)

## Technische Implementierungs-Details

### Ollama Models
```bash
# Primäre Models für Development
ollama pull llama3.2:3b        # 2GB RAM, schnelle Queries
ollama pull llama3.2:8b        # 4.7GB RAM, Qualitäts-Generierung
ollama pull nomic-embed-text   # 274MB, 768-dim Embeddings
ollama pull mistral:7b         # Alternative
```

### Environment-Based LLM Selection Pattern
```python
def get_llm(task_type: str = "generation") -> BaseLLM:
    """Select LLM based on environment and task."""
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

### Dependencies Update
```toml
# Primär (required)
langchain-ollama = "^0.2.0"
llama-index-llms-ollama = "^0.4.0"
llama-index-embeddings-ollama = "^0.4.0"
ollama = "^0.3.0"

# Optional (für Azure OpenAI)
openai = "^1.40.0"
langchain-openai = "^0.2.0"
llama-index-llms-openai = "^0.2.0"
llama-index-embeddings-openai = "^0.2.0"
```

## Migration Timeline

| Sprint | Milestone | Status |
|--------|-----------|--------|
| Sprint 1-6 | Entwicklung mit Ollama (100%) | ✅ Planned |
| Sprint 7 | Azure OpenAI Integration (optional) | ⏳ Planned |
| Sprint 8 | A/B Testing (Ollama vs. Azure) | ⏳ Planned |
| Sprint 9-10 | Production Decision & Deployment | ⏳ Planned |

## Performance Expectations

| Metric | Ollama (llama3.2:8b) | Azure GPT-4o-mini | Azure GPT-4o |
|--------|---------------------|-------------------|--------------|
| Latency | 200-500ms | 150-300ms | 300-600ms |
| Quality | Good (7/10) | Very Good (8.5/10) | Excellent (9.5/10) |
| Cost | $0 | $0.15/1M tokens | $2.50/1M tokens |
| Context | 128K | 128K | 128K |
| Offline | ✅ Yes | ❌ No | ❌ No |

## Cost Impact

### Before (Azure OpenAI Primary)
- Development: $300-500/month
- 6 Sprints (3 Monate): $900-1500
- Production: $300-1000/month

### After (Ollama-First)
- Development: $0/month
- 6 Sprints: $0
- Production: $0-500/month (optional Azure)

**Savings**: ~$900-1500 während Entwicklungsphase

## Compliance Benefits

### Bundeswehr-Anforderungen
- ✅ **VS-NfD**: Ollama läuft vollständig offline
- ✅ **Geheim**: Keine Daten verlassen lokales Netzwerk
- ✅ **Data Residency**: 100% lokal/Deutschland
- ✅ **Air-gapped Deployment**: Möglich mit Ollama
- ⚠️ **Azure OpenAI**: Nur für nicht-klassifizierte Daten (DSGVO-konform)

## Review & Decision Point

**Sprint 6 Review**: Evaluierung der Ollama-Qualität
- Target: >80% user satisfaction
- Target: <500ms p95 latency
- Decision: Ollama ausreichend oder Azure OpenAI aktivieren

**Sprint 8 Benchmark**: A/B Testing Results
- Latency Comparison dokumentiert
- Quality Metrics (RAGAS) verglichen
- Cost-Benefit Analyse
- Final Production Decision

## Rollback Plan

Falls Ollama nicht ausreichend:
1. Azure OpenAI Credentials konfigurieren
2. Environment Variable `USE_AZURE_LLM=true` setzen
3. Kein Code-Change erforderlich (nur Config)
4. Fallback zu Ollama jederzeit möglich

## Weitere Dokumentation

- Vollständiger ADR: [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md#adr-002-ollama-first-llm-strategy-mit-optionalem-azure-openai)
- Tech Stack Details: [docs/core/TECH_STACK.md](docs/core/TECH_STACK.md#8-llm-selection-matrix)
- Setup Instructions: [docs/core/QUICK_START.md](docs/core/QUICK_START.md)
- Sprint Plan: [docs/core/SPRINT_PLAN.md](docs/core/SPRINT_PLAN.md)

---

**Maintainer**: AEGIS RAG Team
**Version**: 1.1.0
**Status**: ✅ Alle Dokumente aktualisiert
