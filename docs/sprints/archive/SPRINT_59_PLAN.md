# Sprint 59: Agentic Capabilities, Lifecycle & Hybrid Memory

**Status:** PLANNED  
**Branch:** `sprint-59-agentic-capabilities`  
**Start Date:** TBD (nach Sprint 58)  
**Estimated Duration:** 7–9 Tage  
**Total Story Points:** 76 SP  

---

## Sprint Overview

Sprint 59 entwickelt AEGIS RAG von **Tool-augmented Agents** zu einer **langlebigen, auditierbaren Agentic Platform** mit **Hybrid Memory Architecture**:

- Deterministischer Agent Lifecycle (AgentRun, Resume, Replay)
- Tool Use Framework mit Bash/Python + Sandboxing
- Task / Todo Tracking als First-Class-Entity
- Knowledge Graph Community Fix
- **Hybrid Memory Ansatz**
  - Eigener Agent Memory Core (deterministisch)
  - mem0 als **optionales, containerisiertes Long-Term Memory Backend**

**Voraussetzung:**  
Sprint 58 abgeschlossen (Refactoring complete, ≥80 % Coverage)

**Architektur-Leitplanken:**
- Agent-Core bleibt deterministisch
- mem0 ist **Service**, kein Steuerungsmechanismus
- Kein Vendor-Lock-in
- Auditierbarkeit vor Token-Effizienz

---

## Feature Overview

| # | Feature | SP | Priority | Parallelisierbar |
|---|--------|----|----------|------------------|
| 59.1 | Community Detection Fix | 8 | P0 | Nein (Blocker) |
| 59.2 | Tool Use Framework | 13 | P0 | Nach 59.1 |
| 59.3 | Bash Execution Tool | 8 | P1 | Ja |
| 59.4 | Python Execution Tool | 8 | P1 | Ja |
| 59.5 | Sandboxing Layer | 10 | P0 | Ja |
| 59.6 | Agent Identity & Lifecycle | 10 | P0 | Nach 59.2 |
| 59.7 | Agent Memory Core (Interface + Policies) | 7 | P0 | Nach 59.6 |
| 59.8 | mem0 Backend Adapter (Container, optional) | 5 | P1 | Ja |
| 59.9 | Task / Todo Tracking | 4 | P1 | Ja |
| 59.10 | Agentic Search / Deep Research (Durable) | 13 | P1 | Nach 59.6 |

**Total: 76 SP**

---

## Feature Details

### Feature 59.7: Agent Memory Core (Hybrid – Core Layer) (7 SP)

**Priority:** P0  
**Ziel:** Einführung eines **deterministischen Agent Memory Core**, unabhängig von mem0.

**Scope:**
- Definition eines Memory-Interfaces
- Policy-gesteuerte Writes
- Trennung von KG, State und Memory

**Neue Dateien:**
```
src/domains/agents/memory/
├── interfaces.py
├── models.py
├── policies.py
├── internal_store.py
```

**Memory Interface:**
```python
class AgentMemoryService(Protocol):
    async def retrieve(self, agent_id: str, query: str) -> list[MemoryItem]
    async def store(self, agent_id: str, item: MemoryItem) -> None
    async def summarize(self, agent_id: str) -> None
```

**Acceptance Criteria:**
- [ ] Agent Memory unabhängig vom Backend
- [ ] Memory-Writes explizit & nachvollziehbar
- [ ] Kein Einfluss auf Control Flow

---

### Feature 59.8: mem0 Backend Adapter (5 SP)

**Priority:** P1  
**Ziel:** Optionale Integration von mem0 als **Long-Term Memory Backend**.

**Design-Prinzipien:**
- mem0 läuft **containerisiert**
- Zugriff ausschließlich über Adapter
- Abschaltbar via Config (`MEM0_ENABLED=false`)

**Neue Dateien:**
```
src/domains/agents/memory/backends/
├── mem0_adapter.py
```

**Acceptance Criteria:**
- [ ] mem0 nur über Adapter erreichbar
- [ ] Fallback auf Internal Store möglich
- [ ] Kein mem0 SDK im Agent-Core

---

### Feature 59.10: Agentic Search / Deep Research (Durable)

**Erweiterungen:**
- LangGraph Checkpointing
- Resume per `run_id`
- Tasks + Evidence im State
- Optionaler Memory-Retrieval-Step (Hybrid)

**Acceptance Criteria (zusätzlich):**
- [ ] Research Runs resume-fähig
- [ ] Memory kontextualisiert, nicht steuernd
- [ ] Deterministisches Replay möglich

---

## Parallel Execution Strategy

### Wave 1 (Tag 1)
- 59.1 Community Detection Fix

### Wave 2 (Tag 2)
- 59.2 Tool Use Framework

### Wave 3 (Tag 3–5, parallel)
- 59.3 Bash Tool  
- 59.4 Python Tool  
- 59.5 Sandboxing Layer  

### Wave 4 (Tag 6–7)
- 59.6 Agent Identity & Lifecycle
- 59.7 Agent Memory Core

### Wave 5 (Tag 8–9)
- 59.8 mem0 Adapter (optional)
- 59.9 Task / Todo Tracking
- 59.10 Durable Deep Research
- Integration Tests & Security Review

---

## Security & Governance Notes

- mem0 darf **keine** personenbezogenen Daten ohne Policy speichern
- Keine Memory-Writes aus Sandbox ohne Freigabe
- KG bleibt Source of Truth
- Agent Memory ist erklärbar & auditierbar

---

## Definition of Done (Sprint 59)

- [ ] AgentRuns persistent & resume-fähig
- [ ] Hybrid Memory Interface implementiert
- [ ] mem0 optional integrierbar & abschaltbar
- [ ] Tool Execution sicher & sandboxed
- [ ] Deep Research deterministisch & reproduzierbar
- [ ] Security Review bestanden

---

**END OF UPDATED SPRINT 59 PLAN**
