# TD-068: Cloud LLM Support (AnyLLM / Dashscope)

**Status:** OPEN
**Priority:** MEDIUM
**Story Points:** 13
**Created:** Sprint 60 Planning
**Target:** Sprint 61+

---

## Problem Statement

AegisRAG benötigt vollständige Unterstützung für Cloud LLM Provider, insbesondere:
- **Alibaba Cloud DashScope** (Qwen/Qwen-Plus/Qwen-Max)
- **AnyLLM Integration** für generische Provider

Aktuell ist die Integration teilweise implementiert, aber nicht vollständig getestet und dokumentiert.

---

## Analysis References

Die folgenden Analysedokumente enthalten relevante Informationen:

| Dokument | Inhalt |
|----------|--------|
| `docs/analysis/CLOUD_LLM_DECISION_MATRIX.md` | Provider-Vergleich, Kosten |
| `docs/analysis/CLOUD_LLM_INGESTION_ANALYSIS.md` | Ingestion mit Cloud LLMs |

---

## Current State

### Implementiert
- `AegisLLMProxy` mit Multi-Cloud Routing (ADR-033)
- DashScope API Key Configuration (`ALIBABA_CLOUD_API_KEY`)
- Monthly Budget Tracking (`MONTHLY_BUDGET_ALIBABA_CLOUD`)
- Basic Qwen Model Support

### Fehlend
- [ ] Vollständige DashScope Model-Liste (qwen-turbo, qwen-plus, qwen-max)
- [ ] Streaming Support für DashScope
- [ ] AnyLLM Adapter für generische OpenAI-kompatible APIs
- [ ] Fallback-Logik bei Rate Limits
- [ ] Cost Tracking per Model/Provider
- [ ] Admin UI für Provider-Konfiguration

---

## Requirements

### 1. DashScope Full Support
```python
# Unterstützte Models
DASHSCOPE_MODELS = {
    "qwen-turbo": {"context": 8192, "cost_per_1k": 0.002},
    "qwen-plus": {"context": 32768, "cost_per_1k": 0.004},
    "qwen-max": {"context": 32768, "cost_per_1k": 0.024},
    "qwen-vl-plus": {"context": 8192, "cost_per_1k": 0.008},  # Vision
}
```

### 2. AnyLLM Integration
```python
# Generic OpenAI-compatible endpoint
class AnyLLMProvider:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
    ):
        ...
```

### 3. Admin Configuration
- Provider Selection (Ollama, DashScope, OpenAI, AnyLLM)
- Model Selection per Task Type
- Budget Limits per Provider

---

## Implementation Plan

### Phase 1: DashScope Completion (5 SP)
- Vollständige Model-Liste
- Streaming Implementation
- Rate Limit Handling

### Phase 2: AnyLLM Adapter (5 SP)
- Generic Provider Interface
- Configuration via Admin UI
- Connection Testing

### Phase 3: Admin Integration (3 SP)
- Provider Management UI
- Cost Dashboard per Provider
- Budget Alerts

---

## Acceptance Criteria

- [ ] DashScope qwen-turbo/plus/max funktional
- [ ] Streaming für alle DashScope Models
- [ ] AnyLLM Adapter für OpenAI-kompatible APIs
- [ ] Admin UI für Provider-Konfiguration
- [ ] Cost Tracking per Provider
- [ ] Integration Tests

---

## Dependencies

- ADR-033: AegisLLMProxy Multi-Cloud Routing
- TD-053: Admin Dashboard (für UI)

---

## References

- [docs/analysis/CLOUD_LLM_DECISION_MATRIX.md](../analysis/CLOUD_LLM_DECISION_MATRIX.md)
- [docs/analysis/CLOUD_LLM_INGESTION_ANALYSIS.md](../analysis/CLOUD_LLM_INGESTION_ANALYSIS.md)
- [ADR-033: AegisLLMProxy](../adr/ADR-033_AEGIS_LLM_PROXY.md)
