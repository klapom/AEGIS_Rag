# Sprint 36: DGX Spark Local Infrastructure + Admin LLM Configuration

**Status:** PLANNED
**Branch:** `sprint-36-dgx-spark-local`
**Start Date:** TBD (nach Sprint 35)
**Estimated Duration:** 6-8 Tage
**Total Story Points:** 46 SP

---

## Sprint Theme: Vollständig lokale LLM/VLM-Infrastruktur

Sprint 36 kombiniert zwei strategische Ziele:

1. **DGX Spark Local Infrastructure** - VLM-Calls lokal statt Cloud (Feature 36.1-36.2)
2. **Admin LLM Configuration** - UI zur Modell-Konfiguration (Feature 36.3-36.5)
3. **Infrastructure Improvements** - Unified Chunking, Performance (Feature 36.6-36.7)

---

## Sprint Overview

Sprint 36 fokussiert auf **Admin-Konfiguration für LLM-Modelle**. Nach der DGX Spark Migration (lokale Qwen3-Modelle) benötigen wir eine UI zur flexiblen Modell-Konfiguration ohne Code-Änderungen.

### Motivation

Mit der DGX Spark Deployment haben wir jetzt:
- Lokale Qwen3-32B und Qwen3-VL-32B Modelle
- Cloud-Fallback (Alibaba DashScope, OpenAI)
- 6 verschiedene LLM Use Cases im System

**Problem:** Aktuell ist die Modell-Zuordnung hardcoded in `AegisLLMProxy`. Admins können nicht:
- Modelle pro Use Case wechseln
- Parameter (Temperature, Top-K) anpassen
- Provider-Credentials verwalten

---

## LLM Use Cases im System

| # | Use Case | Aktuelles Modul | Default Model | Beschreibung |
|---|----------|-----------------|---------------|--------------|
| 1 | **Intent-Klassifizierung** | `src/agents/router.py` | qwen3:32b | Query → VECTOR/GRAPH/HYBRID/MEMORY |
| 2 | **Entity/Relation Extraktion** | `src/components/graph_rag/extraction_service.py` | qwen3:32b | Dokumente → Entities + Relations |
| 3 | **Antwortgenerierung** | `src/agents/answer_generator.py` | qwen3:32b | Context → Final Answer |
| 4 | **Follow-Up & Titel** | `src/agents/followup_generator.py`, `title_generator.py` | qwen3:32b | Answer → Folgefragen, Titel |
| 5 | **Query Decomposition** | `src/components/retrieval/query_decomposition.py` | qwen3:32b | Complex Query → Sub-Queries |
| 6 | **VLM (Bilder)** | `src/components/ingestion/image_processor.py` | qwen3-vl:32b | Image → Text Description |

### Weitere Module (nutzen dieselben Kategorien)

- `community_labeler.py` → Kategorie 3 (Antwortgenerierung)
- `dual_level_search.py` → Kategorie 3 (Antwortgenerierung)
- `lightrag_wrapper.py` → Kategorie 3 (Antwortgenerierung)
- `graphiti_wrapper.py` → Kategorie 3 (Antwortgenerierung)
- `relation_extractor.py` → Kategorie 2 (Entity/Relation Extraktion)

---

## Features

| # | Feature | SP | Priority | Kategorie | Dependencies |
|---|---------|-----|----------|-----------|--------------|
| **36.1** | VLM Factory Pattern | 5 | P0 | DGX Spark | - |
| **36.2** | OllamaVLMClient Implementation | 8 | P0 | DGX Spark | 36.1 |
| **36.3** | Model Selection per Use Case | 8 | P0 | Admin UI | - |
| **36.4** | Model Parameters Configuration | 5 | P1 | Admin UI | 36.3 |
| **36.5** | Provider Configuration (URLs, Auth) | 5 | P1 | Admin UI | 36.3 |
| **36.6** | TD-054: Unified ChunkingService | 6 | P2 | Infrastructure | - |
| **36.7** | Performance Benchmarks (Local vs Cloud) | 3 | P2 | DGX Spark | 36.2 |
| **36.8** | LLM Config prefer_cloud Toggle | 3 | P0 | DGX Spark | - |
| **36.9** | Integration Tests (Local VLM) | 3 | P1 | Testing | 36.2 |

**Total: 46 SP**

---

## Architektur-Kontext: ANY-LLM und VLM

### Warum VLM separat von ANY-LLM?

Laut ADR-033 (Implementation Outcomes):

> **"ANY-LLM `acompletion()` doesn't support image inputs"**

Das bedeutet:
- **Text-LLM:** Läuft über `AegisLLMProxy` → `ANY-LLM acompletion()` ✅
- **VLM:** Muss über separate VLM-Clients laufen (DashScopeVLMClient / OllamaVLMClient)

### Aktuelle Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                         LangGraph Nodes                         │
└───────────────┬────────────────────────────┬────────────────────┘
                │                            │
                ▼                            ▼
    ┌───────────────────────┐    ┌───────────────────────┐
    │   AegisLLMProxy       │    │   DashScopeVLMClient  │ ← Cloud only!
    │   (Text-LLM via       │    │   (VLM via httpx)     │
    │   ANY-LLM acompletion)│    └───────────────────────┘
    └───────────────────────┘
```

### Ziel-Architektur (nach Sprint 36)

```
┌─────────────────────────────────────────────────────────────────┐
│                         LangGraph Nodes                         │
└───────────────┬────────────────────────────┬────────────────────┘
                │                            │
                ▼                            ▼
    ┌───────────────────────┐    ┌───────────────────────┐
    │   AegisLLMProxy       │    │   VLM Factory         │ ← NEU!
    │   (Text-LLM via       │    │   get_vlm_client()    │
    │   ANY-LLM acompletion)│    └───────────┬───────────┘
    └───────────────────────┘                │
                                   ┌─────────┴─────────┐
                                   ▼                   ▼
                        ┌──────────────────┐  ┌──────────────────┐
                        │ OllamaVLMClient  │  │DashScopeVLMClient│
                        │ (Local, NEU!)    │  │ (Cloud, existiert)│
                        │ qwen3-vl:32b     │  │ qwen3-vl-30b     │
                        └──────────────────┘  └──────────────────┘
```

---

## Feature 36.1: VLM Factory Pattern (5 SP)

**Priority:** P0
**Kategorie:** DGX Spark Infrastructure

### Ziel

Factory Pattern für VLM-Clients, ähnlich wie das Embedding Factory Pattern (Feature 35.8).

### Implementation

```python
# src/components/llm_proxy/vlm_factory.py

from enum import Enum
from typing import Protocol

class VLMBackend(str, Enum):
    """Available VLM backends."""
    OLLAMA = "ollama"           # Local qwen3-vl:32b via Ollama API
    DASHSCOPE = "dashscope"     # Alibaba Cloud qwen3-vl-30b

class VLMClient(Protocol):
    """Protocol for VLM clients."""
    async def generate_image_description(
        self,
        image_path: Path,
        prompt: str,
        model: str | None = None,
    ) -> tuple[str, dict]:
        """Generate description for image."""
        ...

def get_vlm_client(backend: VLMBackend | None = None) -> VLMClient:
    """
    Factory function for VLM clients.

    Backend selection priority:
    1. Explicit backend parameter
    2. VLM_BACKEND environment variable
    3. Default: OLLAMA (local-first for DGX Spark)

    Example:
        client = get_vlm_client()  # Uses config/env
        client = get_vlm_client(VLMBackend.DASHSCOPE)  # Force cloud
    """
    if backend is None:
        backend_str = os.getenv("VLM_BACKEND", "ollama")
        backend = VLMBackend(backend_str)

    if backend == VLMBackend.OLLAMA:
        from src.components.llm_proxy.ollama_vlm import OllamaVLMClient
        return OllamaVLMClient()
    else:
        from src.components.llm_proxy.dashscope_vlm import DashScopeVLMClient
        return DashScopeVLMClient()
```

### Deliverables

- [ ] `src/components/llm_proxy/vlm_factory.py` - Factory function
- [ ] `src/components/llm_proxy/vlm_protocol.py` - VLMClient Protocol
- [ ] `.env.dgx-spark.template` - Add `VLM_BACKEND=ollama`
- [ ] Unit Tests (5+ tests)

### Test IDs

```python
"vlm-factory-ollama-backend"
"vlm-factory-dashscope-backend"
"vlm-factory-env-config"
"vlm-factory-default-local"
```

---

## Feature 36.2: OllamaVLMClient Implementation (8 SP)

**Priority:** P0
**Kategorie:** DGX Spark Infrastructure
**Dependencies:** 36.1

### Ziel

Lokale VLM-Calls über Ollama API mit `qwen3-vl:32b` Modell.

### Implementation

```python
# src/components/llm_proxy/ollama_vlm.py

import base64
from pathlib import Path
import httpx
import structlog

logger = structlog.get_logger(__name__)

class OllamaVLMClient:
    """Local VLM client using Ollama API.

    Uses qwen3-vl:32b for image understanding on DGX Spark.

    Ollama VLM API:
        POST /api/generate
        {
            "model": "qwen3-vl:32b",
            "prompt": "Describe this image",
            "images": ["base64_encoded_image"],
            "stream": false
        }
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 120.0,
    ):
        self.base_url = base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.client = httpx.AsyncClient(timeout=timeout)
        self.default_model = os.getenv("OLLAMA_MODEL_VLM", "qwen3-vl:32b")

    async def generate_image_description(
        self,
        image_path: Path,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> tuple[str, dict]:
        """Generate image description using local Ollama VLM.

        Args:
            image_path: Path to image file
            prompt: Text prompt for VLM
            model: Model to use (default: qwen3-vl:32b)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Tuple of (description_text, metadata_dict)
        """
        model = model or self.default_model

        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode("utf-8")

        # Ollama API request
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            }
        }

        logger.info(
            "Sending VLM request to Ollama",
            model=model,
            image_size_kb=len(image_data) / 1024,
        )

        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        description = data.get("response", "")
        metadata = {
            "model": model,
            "provider": "ollama",
            "tokens_total": data.get("eval_count", 0),
            "duration_ms": data.get("total_duration", 0) / 1_000_000,
            "local": True,
            "cost_usd": 0.0,  # Local is free!
        }

        logger.info(
            "VLM description generated (local)",
            model=model,
            tokens=metadata["tokens_total"],
            duration_ms=metadata["duration_ms"],
        )

        return description, metadata

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
```

### Comparison: Local vs Cloud VLM

| Aspect | OllamaVLMClient (Local) | DashScopeVLMClient (Cloud) |
|--------|-------------------------|----------------------------|
| **Model** | qwen3-vl:32b | qwen3-vl-30b-a3b-instruct |
| **Latency** | ~2-5s (local GPU) | ~3-8s (network + inference) |
| **Cost** | $0 | ~$0.003/image |
| **Privacy** | Data stays local | Data sent to cloud |
| **Availability** | Requires DGX Spark | Always available |

### Deliverables

- [ ] `src/components/llm_proxy/ollama_vlm.py` - OllamaVLMClient (150+ LOC)
- [ ] Update `src/components/ingestion/image_processor.py` to use VLM Factory
- [ ] Integration with existing DashScopeVLMClient fallback
- [ ] Unit Tests (10+ tests)
- [ ] Integration Tests (5+ tests)

### Test IDs

```python
"ollama-vlm-basic-description"
"ollama-vlm-image-encoding"
"ollama-vlm-model-selection"
"ollama-vlm-timeout-handling"
"ollama-vlm-error-fallback"
```

---

## Feature 36.8: LLM Config prefer_cloud Toggle (3 SP)

**Priority:** P0
**Kategorie:** DGX Spark Infrastructure

### Ziel

Einfacher Toggle in `llm_config.yml` um zwischen Cloud-First und Local-First zu wechseln.

### Implementation

```yaml
# config/llm_config.yml
routing:
  # DGX Spark: Local-First (default)
  prefer_cloud: false  # Set to true for cloud-first routing

  # VLM Backend Selection (NEW)
  vlm_backend: ollama  # "ollama" (local) or "dashscope" (cloud)
```

### Deliverables

- [ ] Update `config/llm_config.yml` with `prefer_cloud: false`
- [ ] Add `vlm_backend` configuration
- [ ] Update `AegisLLMProxy` to respect config
- [ ] Update VLM Factory to use config

---

## Feature 36.9: Integration Tests (Local VLM) (3 SP)

**Priority:** P1
**Kategorie:** Testing
**Dependencies:** 36.2

### Ziel

E2E Tests für lokale VLM-Pipeline auf DGX Spark.

### Test Scenarios

```python
# tests/integration/test_local_vlm.py

async def test_vlm_factory_returns_ollama_client():
    """VLM Factory should return OllamaVLMClient when VLM_BACKEND=ollama."""

async def test_ollama_vlm_generates_description():
    """OllamaVLMClient should generate description for test image."""

async def test_image_processor_uses_local_vlm():
    """ImageProcessor should use local VLM on DGX Spark."""

async def test_vlm_fallback_cloud_on_ollama_error():
    """Should fallback to DashScope if Ollama unavailable."""

async def test_local_vlm_cost_is_zero():
    """Local VLM calls should have cost_usd=0."""
```

### Deliverables

- [ ] `tests/integration/test_local_vlm.py` (5+ tests)
- [ ] Test fixtures for VLM mocking
- [ ] CI integration (skip on non-DGX environments)

---

## Feature 36.3: Model Selection per Use Case (8 SP)

**Priority:** P0
**Kategorie:** Admin UI

### Ziel

Admin UI zur Auswahl des LLM-Modells für jede der 6 Use Case Kategorien.

### UI Design

```
┌─────────────────────────────────────────────────────────────────┐
│  Admin > Settings > LLM Configuration                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ Use Case Model Assignment ─────────────────────────────┐   │
│  │                                                          │   │
│  │  1. Intent Classification                                │   │
│  │     Model: [▼ qwen3:32b                              ]   │   │
│  │                                                          │   │
│  │  2. Entity/Relation Extraction                           │   │
│  │     Model: [▼ qwen3:32b                              ]   │   │
│  │                                                          │   │
│  │  3. Answer Generation                                    │   │
│  │     Model: [▼ qwen3:32b                              ]   │   │
│  │                                                          │   │
│  │  4. Follow-Up & Titles                                   │   │
│  │     Model: [▼ qwen3:32b                              ]   │   │
│  │                                                          │   │
│  │  5. Query Decomposition                                  │   │
│  │     Model: [▼ qwen3:32b                              ]   │   │
│  │                                                          │   │
│  │  6. Vision (VLM)                                         │   │
│  │     Model: [▼ qwen3-vl:32b                           ]   │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Refresh Models]  [Test Connection]  [Save Configuration]      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Model Dropdown Options

```typescript
interface ModelOption {
  id: string;           // "ollama/qwen3:32b" oder "alibaba/qwen-turbo"
  provider: Provider;   // "ollama" | "alibaba_cloud" | "openai"
  name: string;         // Display name
  description: string;  // "32B parameters, local"
  capabilities: string[]; // ["text", "vision", "embedding"]
  isAvailable: boolean; // Connection check result
}

// Beispiel-Optionen
const modelOptions: ModelOption[] = [
  // Ollama (Local)
  { id: "ollama/qwen3:32b", provider: "ollama", name: "Qwen3 32B (Local)", ... },
  { id: "ollama/qwen3-vl:32b", provider: "ollama", name: "Qwen3-VL 32B (Local)", ... },
  { id: "ollama/llama3.2:8b", provider: "ollama", name: "Llama 3.2 8B (Local)", ... },

  // Alibaba Cloud
  { id: "alibaba/qwen-turbo", provider: "alibaba_cloud", name: "Qwen Turbo (Cloud)", ... },
  { id: "alibaba/qwen-plus", provider: "alibaba_cloud", name: "Qwen Plus (Cloud)", ... },
  { id: "alibaba/qwen-max", provider: "alibaba_cloud", name: "Qwen Max (Cloud)", ... },

  // OpenAI
  { id: "openai/gpt-4o", provider: "openai", name: "GPT-4o (Cloud)", ... },
  { id: "openai/gpt-4o-mini", provider: "openai", name: "GPT-4o Mini (Cloud)", ... },
];
```

### Data Model

```typescript
// Frontend: src/types/llm-config.ts
interface UseCaseModelConfig {
  useCase: UseCaseType;
  modelId: string;        // "ollama/qwen3:32b"
  enabled: boolean;
  lastUpdated: string;    // ISO timestamp
}

type UseCaseType =
  | "intent_classification"
  | "entity_extraction"
  | "answer_generation"
  | "followup_titles"
  | "query_decomposition"
  | "vision_vlm";

interface LLMConfiguration {
  useCases: UseCaseModelConfig[];
  version: string;        // Schema version for migrations
}
```

### Backend API

```python
# src/api/v1/admin.py

@router.get("/llm/models")
async def list_available_models() -> list[ModelInfo]:
    """List all available models from all configured providers."""
    pass

@router.get("/llm/config")
async def get_llm_configuration() -> LLMConfiguration:
    """Get current LLM configuration for all use cases."""
    pass

@router.put("/llm/config")
async def update_llm_configuration(config: LLMConfiguration) -> LLMConfiguration:
    """Update LLM configuration."""
    pass

@router.post("/llm/test-connection")
async def test_model_connection(model_id: str) -> ConnectionTestResult:
    """Test connection to a specific model."""
    pass
```

### Storage

**Phase 1:** localStorage (wie Settings)
**Phase 2:** Backend SQLite/Redis persistence

```typescript
// localStorage key
const LLM_CONFIG_KEY = "aegis-rag-llm-config";

// Save
localStorage.setItem(LLM_CONFIG_KEY, JSON.stringify(config));

// Load with defaults
const stored = localStorage.getItem(LLM_CONFIG_KEY);
const config = stored ? JSON.parse(stored) : defaultLLMConfig;
```

### Deliverables

- [ ] `frontend/src/pages/AdminLLMConfigPage.tsx` (neue Seite)
- [ ] `frontend/src/components/admin/UseCaseModelSelector.tsx`
- [ ] `frontend/src/components/admin/ModelDropdown.tsx`
- [ ] `frontend/src/types/llm-config.ts`
- [ ] `frontend/src/hooks/useLLMConfig.ts`
- [ ] `src/api/v1/admin.py` - Neue Endpoints
- [ ] Route Registration in `AdminLayout.tsx`
- [ ] 10+ Unit Tests

### Test IDs

```typescript
// data-testid Attribute
"llm-config-page"
"usecase-selector-{usecase}"
"model-dropdown-{usecase}"
"model-option-{modelId}"
"refresh-models-button"
"test-connection-button"
"save-config-button"
"connection-status-{provider}"
```

---

## Feature 36.4: Model Parameters Configuration (5 SP)

**Priority:** P1
**Kategorie:** Admin UI
**Dependencies:** 36.3

### Ziel

Konfigurierbare LLM-Parameter pro Use Case Kategorie.

### UI Design

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Intent Classification                                       │
│     Model: [▼ qwen3:32b                              ]          │
│                                                                 │
│     ┌─ Parameters ──────────────────────────────────────────┐   │
│     │                                                        │   │
│     │  Temperature     [=====○─────────────] 0.7            │   │
│     │                  Creative ←──────→ Deterministic       │   │
│     │                                                        │   │
│     │  Top-K           [────────○────────] 40               │   │
│     │                  1 ←─────────────→ 100                 │   │
│     │                                                        │   │
│     │  Top-P           [════════○────────] 0.9              │   │
│     │                  0.0 ←───────────→ 1.0                 │   │
│     │                                                        │   │
│     │  Max Tokens      [──────────────○──] 2048             │   │
│     │                  256 ←──────────→ 8192                 │   │
│     │                                                        │   │
│     │  Repeat Penalty  [═══════○─────────] 1.1              │   │
│     │                  1.0 ←───────────→ 2.0                 │   │
│     │                                                        │   │
│     │  [Reset to Defaults]                                   │   │
│     └────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Parameter Definitions

```typescript
interface ModelParameters {
  temperature: number;      // 0.0 - 2.0, default: 0.7
  topK: number;             // 1 - 100, default: 40
  topP: number;             // 0.0 - 1.0, default: 0.9
  maxTokens: number;        // 256 - 8192, default: 2048
  repeatPenalty: number;    // 1.0 - 2.0, default: 1.1
  presencePenalty?: number; // OpenAI specific
  frequencyPenalty?: number; // OpenAI specific
  stop?: string[];          // Stop sequences
}

// Recommended defaults per use case
const useCaseDefaults: Record<UseCaseType, ModelParameters> = {
  intent_classification: {
    temperature: 0.3,    // Deterministic for classification
    topK: 10,
    topP: 0.5,
    maxTokens: 256,      // Short responses
    repeatPenalty: 1.0,
  },
  entity_extraction: {
    temperature: 0.2,    // Very deterministic
    topK: 20,
    topP: 0.7,
    maxTokens: 4096,     // Long extractions
    repeatPenalty: 1.0,
  },
  answer_generation: {
    temperature: 0.7,    // Balanced creativity
    topK: 40,
    topP: 0.9,
    maxTokens: 2048,
    repeatPenalty: 1.1,
  },
  followup_titles: {
    temperature: 0.8,    // Creative
    topK: 50,
    topP: 0.95,
    maxTokens: 512,
    repeatPenalty: 1.2,
  },
  query_decomposition: {
    temperature: 0.4,    // Structured output
    topK: 30,
    topP: 0.8,
    maxTokens: 1024,
    repeatPenalty: 1.0,
  },
  vision_vlm: {
    temperature: 0.5,
    topK: 40,
    topP: 0.9,
    maxTokens: 1024,
    repeatPenalty: 1.0,
  },
};
```

### Data Model Extension

```typescript
interface UseCaseModelConfig {
  useCase: UseCaseType;
  modelId: string;
  enabled: boolean;
  parameters: ModelParameters;  // NEU
  useCustomParameters: boolean; // NEU - false = use defaults
  lastUpdated: string;
}
```

### Deliverables

- [ ] `frontend/src/components/admin/ModelParametersPanel.tsx`
- [ ] `frontend/src/components/admin/ParameterSlider.tsx`
- [ ] Parameter validation logic
- [ ] Default presets per use case
- [ ] "Reset to Defaults" functionality
- [ ] 8+ Unit Tests

### Test IDs

```typescript
"parameters-panel-{usecase}"
"param-slider-temperature-{usecase}"
"param-slider-topk-{usecase}"
"param-slider-topp-{usecase}"
"param-slider-maxtokens-{usecase}"
"param-slider-repeatpenalty-{usecase}"
"reset-defaults-button-{usecase}"
"use-custom-params-toggle-{usecase}"
```

---

## Feature 36.5: Provider Configuration (5 SP)

**Priority:** P1
**Kategorie:** Admin UI
**Dependencies:** 36.3

### Ziel

Admin UI zur Konfiguration von LLM-Providern (URLs, API Keys, Authentication).

### UI Design

```
┌─────────────────────────────────────────────────────────────────┐
│  Admin > Settings > LLM Providers                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ Ollama (Local) ─────────────────────────────────────────┐   │
│  │  [✓] Enabled                                              │   │
│  │                                                           │   │
│  │  Base URL:  [http://localhost:11434              ]        │   │
│  │                                                           │   │
│  │  Status: ● Connected (3 models available)                 │   │
│  │          qwen3:32b, qwen3-vl:32b, bge-m3                  │   │
│  │                                                           │   │
│  │  [Test Connection]  [Refresh Models]                      │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ Alibaba Cloud DashScope ────────────────────────────────┐   │
│  │  [✓] Enabled                                              │   │
│  │                                                           │   │
│  │  Base URL:  [https://dashscope-intl.aliyuncs.com/...  ]   │   │
│  │  API Key:   [sk-••••••••••••••••••••••••      ] [Show]    │   │
│  │                                                           │   │
│  │  Monthly Budget: [$10.00        ] (Current: $3.45)        │   │
│  │                                                           │   │
│  │  Status: ● Connected                                      │   │
│  │                                                           │   │
│  │  [Test Connection]  [View Usage]                          │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ OpenAI ─────────────────────────────────────────────────┐   │
│  │  [ ] Enabled (disabled)                                   │   │
│  │                                                           │   │
│  │  Base URL:  [https://api.openai.com/v1           ]        │   │
│  │  API Key:   [                                    ]        │   │
│  │                                                           │   │
│  │  Monthly Budget: [$20.00        ]                         │   │
│  │                                                           │   │
│  │  Status: ○ Not configured                                 │   │
│  │                                                           │   │
│  │  [Test Connection]                                        │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ Azure OpenAI ───────────────────────────────────────────┐   │
│  │  [ ] Enabled (disabled)                                   │   │
│  │                                                           │   │
│  │  Endpoint:  [https://your-resource.openai.azure.com  ]    │   │
│  │  API Key:   [                                    ]        │   │
│  │  Deployment: [                                   ]        │   │
│  │  API Version: [2024-02-15-preview                ]        │   │
│  │                                                           │   │
│  │  Status: ○ Not configured                                 │   │
│  │                                                           │   │
│  │  [Test Connection]                                        │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Save All]  [Export Configuration]  [Import Configuration]     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Model

```typescript
interface ProviderConfig {
  provider: Provider;
  enabled: boolean;
  baseUrl: string;
  apiKey?: string;          // Encrypted/masked in UI
  monthlyBudget?: number;   // USD
  currentSpend?: number;    // From cost tracker

  // Azure-specific
  azureEndpoint?: string;
  azureDeployment?: string;
  azureApiVersion?: string;

  // Status
  connectionStatus: "connected" | "disconnected" | "error" | "unknown";
  lastChecked?: string;
  availableModels?: string[];
  errorMessage?: string;
}

type Provider = "ollama" | "alibaba_cloud" | "openai" | "azure_openai";

interface ProvidersConfiguration {
  providers: ProviderConfig[];
  routingPriority: Provider[];  // Fallback order
  version: string;
}
```

### Security Considerations

```typescript
// API Keys werden NICHT im localStorage gespeichert!
// Nur im Backend (encrypted) oder als env vars

// Frontend zeigt nur masked version:
const maskApiKey = (key: string) => {
  if (!key) return "";
  return `sk-${"•".repeat(20)}${key.slice(-4)}`;
};

// Backend handles actual keys via:
// 1. Environment variables (ALIBABA_CLOUD_API_KEY, etc.)
// 2. Encrypted storage in SQLite
// 3. Secrets manager (production)
```

### Backend API

```python
# src/api/v1/admin.py

@router.get("/llm/providers")
async def list_providers() -> list[ProviderConfig]:
    """List all configured providers with status."""
    pass

@router.put("/llm/providers/{provider}")
async def update_provider(provider: str, config: ProviderConfigUpdate) -> ProviderConfig:
    """Update provider configuration."""
    pass

@router.post("/llm/providers/{provider}/test")
async def test_provider(provider: str) -> ConnectionTestResult:
    """Test connection to provider."""
    pass

@router.get("/llm/providers/{provider}/models")
async def list_provider_models(provider: str) -> list[ModelInfo]:
    """List available models for a provider."""
    pass

@router.get("/llm/providers/{provider}/usage")
async def get_provider_usage(provider: str) -> UsageStats:
    """Get usage statistics for a provider."""
    pass
```

### Deliverables

- [ ] `frontend/src/pages/AdminProvidersPage.tsx` (neue Seite)
- [ ] `frontend/src/components/admin/ProviderCard.tsx`
- [ ] `frontend/src/components/admin/ApiKeyInput.tsx` (masked input)
- [ ] `frontend/src/components/admin/ConnectionStatus.tsx`
- [ ] `frontend/src/components/admin/BudgetTracker.tsx`
- [ ] `src/api/v1/admin.py` - Provider Endpoints
- [ ] Integration with existing `CostTracker`
- [ ] 10+ Unit Tests

### Test IDs

```typescript
"providers-page"
"provider-card-{provider}"
"provider-enabled-toggle-{provider}"
"provider-baseurl-input-{provider}"
"provider-apikey-input-{provider}"
"provider-apikey-show-button-{provider}"
"provider-budget-input-{provider}"
"provider-test-button-{provider}"
"provider-status-{provider}"
"provider-models-list-{provider}"
"save-all-button"
"export-config-button"
"import-config-button"
```

---

## Technical Implementation

### AegisLLMProxy Integration

```python
# src/components/llm_proxy/aegis_llm_proxy.py

class AegisLLMProxy:
    def __init__(self, config: LLMProxyConfig | None = None):
        # Load use case configs from storage
        self.use_case_configs = self._load_use_case_configs()
        self.provider_configs = self._load_provider_configs()

    async def generate(self, task: LLMTask) -> str:
        # Get config for this use case
        use_case = task.use_case or "answer_generation"
        config = self.use_case_configs.get(use_case)

        # Apply model and parameters from config
        model = config.model_id if config else self._default_model
        params = config.parameters if config and config.use_custom_parameters else self._default_params

        # Route to provider
        return await self._route_to_provider(model, task, params)
```

### LLMTask Extension

```python
# src/components/llm_proxy/models.py

class LLMTask(BaseModel):
    prompt: str
    system_prompt: str | None = None

    # NEW: Use case for config lookup
    use_case: UseCaseType | None = None

    # Override defaults (optional)
    model_override: str | None = None
    parameters_override: ModelParameters | None = None
```

---

## Feature 36.6: TD-054 Unified ChunkingService (6 SP)

**Priority:** P2
**Kategorie:** Infrastructure
**Reference:** [TD-054_UNIFIED_CHUNKING_SERVICE.md](../technical-debt/TD-054_UNIFIED_CHUNKING_SERVICE.md)

### Ziel

Zentraler ChunkingService als Single Source of Truth für alle Chunking-Operationen.

### Deliverables

- [ ] `src/core/chunking_service.py` - Central ChunkingService
- [ ] Unified Chunk model
- [ ] Update Qdrant/BM25/Neo4j consumers
- [ ] Index consistency validation
- [ ] 10+ Unit Tests

---

## Feature 36.7: Performance Benchmarks (3 SP)

**Priority:** P2
**Kategorie:** DGX Spark
**Dependencies:** 36.2

### Ziel

Systematischer Vergleich: Local Ollama vs. Cloud DashScope

### Benchmark Metrics

| Metric | Local Target | Cloud Baseline |
|--------|--------------|----------------|
| **VLM Latency (p50)** | <3s | ~5s |
| **VLM Latency (p95)** | <8s | ~12s |
| **LLM Latency (p50)** | <500ms | ~800ms |
| **Cost per 1k Requests** | $0 | ~$3 |
| **Privacy** | 100% local | Data sent to cloud |

### Deliverables

- [ ] `scripts/benchmark_local_vs_cloud.py`
- [ ] Benchmark results in `docs/benchmarks/`
- [ ] Grafana dashboard for performance comparison

---

## Definition of Done

### Feature 36.1 (VLM Factory)
- [ ] VLM Factory function implemented
- [ ] VLMClient Protocol defined
- [ ] Environment variable support (VLM_BACKEND)
- [ ] 5+ Unit Tests passing

### Feature 36.2 (OllamaVLMClient)
- [ ] OllamaVLMClient generates image descriptions
- [ ] ImageProcessor uses VLM Factory
- [ ] Fallback to DashScope on error
- [ ] 10+ Unit Tests passing
- [ ] Integration tests on DGX Spark

### Feature 36.3 (Model Selection)
- [ ] Admin kann Modell pro Use Case auswählen
- [ ] Modell-Liste wird dynamisch von Providern geladen
- [ ] Konfiguration wird persistent gespeichert
- [ ] AegisLLMProxy nutzt konfiguriertes Modell
- [ ] 10+ Unit Tests passing

### Feature 36.4 (Parameters)
- [ ] Parameter-Slider für alle 5 Parameter
- [ ] Defaults pro Use Case vordefiniert
- [ ] "Reset to Defaults" funktioniert
- [ ] Parameter werden an LLM übergeben
- [ ] 8+ Unit Tests passing

### Feature 36.5 (Providers)
- [ ] Provider Enable/Disable funktioniert
- [ ] API Key wird sicher gehandhabt (masked)
- [ ] Connection Test funktioniert
- [ ] Budget-Anzeige aus CostTracker
- [ ] 10+ Unit Tests passing

### Feature 36.6 (ChunkingService)
- [ ] Central ChunkingService implemented
- [ ] All consumers use ChunkingService
- [ ] Index consistency validator
- [ ] 10+ Unit Tests passing

### Feature 36.7 (Benchmarks)
- [ ] Benchmark script runs successfully
- [ ] Results documented
- [ ] Performance comparison report

---

## Dependencies

### Backend
- `AegisLLMProxy` (existiert)
- `CostTracker` (existiert)
- `LLMProxyConfig` (existiert)

### Frontend
- Settings-Infrastruktur (existiert aus Sprint 28)
- Admin Layout (existiert aus Sprint 31)
- Tailwind CSS (existiert)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| API Key exposure | High | Keys nur im Backend, masked in UI |
| Config breaks LLM routing | High | Validation + fallback to defaults |
| Provider unavailable | Medium | Connection test + status indicator |
| Parameter causes bad output | Medium | Reset to defaults, validation ranges |

---

## Future Enhancements (nicht in Sprint 36)

- **36.x:** Custom Model Profiles (Presets speichern)
- **36.x:** A/B Testing zwischen Modellen
- **36.x:** Per-User Model Preferences
- **36.x:** Cost Estimation vor Request
- **36.x:** Model Performance Metrics Dashboard

---

## Related Documentation

- [DGX_SPARK_DEPLOYMENT.md](../operations/DGX_SPARK_DEPLOYMENT.md) - Local model setup
- [ADR-033](../adr/ADR-033-any-llm-integration.md) - ANY-LLM Integration
- [TECH_STACK.md](../TECH_STACK.md) - Technology overview
- `src/components/llm_proxy/README.md` - LLM Proxy architecture

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-05 | Initial Sprint 36 plan created |
| 2025-12-05 | Extended: DGX Spark VLM features (36.1, 36.2, 36.8, 36.9) |
| 2025-12-05 | Added TD-054 Unified ChunkingService (36.6) |
| 2025-12-05 | Added Performance Benchmarks (36.7) |
| 2025-12-05 | Documented ANY-LLM architecture context |
| 2025-12-05 | Total SP: 18 → 46 SP |
