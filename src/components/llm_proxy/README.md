# LLM Proxy Component - Mozilla ANY-LLM Integration

**Status:** 🚧 IN DEVELOPMENT (Sprint 23, Feature 23.4)
**Related ADR:** [ADR-033](../../../docs/adr/ADR-033-any-llm-integration.md)

---

## Overview

The LLM Proxy component provides AegisRAG-specific routing logic on top of Mozilla's ANY-LLM framework, enabling intelligent three-tier execution:

```
TIER 1: Local Ollama (FREE, 70% tasks)
   ↓ (if quality/scale needed)
TIER 2: Ollama Cloud ($0.001/1k tokens, 20% tasks)
   ↓ (if critical quality)
TIER 3: OpenAI API ($0.015/1k tokens, 10% tasks)
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│  LangGraph Nodes / Agents              │
│  (call AegisLLMProxy.generate())       │
└───────────────┬─────────────────────────┘
                │
                ▼
    ┌───────────────────────────┐
    │  AegisLLMProxy (400 LOC)  │  ← AEGIS Custom Routing
    │  - Data privacy check     │
    │  - Quality-based routing  │
    │  - Metrics tracking       │
    └───────────┬───────────────┘
                │
                ▼
    ┌───────────────────────────┐
    │  Mozilla ANY-LLM SDK      │  ← Heavy Lifting
    │  - Multi-provider         │
    │  - Budget management      │
    │  - Fallback logic         │
    └───────────┬───────────────┘
                │
      ┌─────────┼─────────┐
      ▼         ▼         ▼
  [Local]  [Ollama]  [OpenAI]
```

---

## Components

### 1. `models.py` ✅ (Complete)
**Purpose:** Pydantic models for LLM tasks and responses

**Key Classes:**
- `TaskType`: Task categorization (extraction, generation, etc.)
- `DataClassification`: GDPR/HIPAA compliance (PII → local only)
- `QualityRequirement`: Quality level (low, medium, high, critical)
- `Complexity`: Task complexity (influences routing)
- `ExecutionLocation`: Provider selection (local, ollama_cloud, openai)
- `LLMTask`: Request model with routing criteria
- `LLMResponse`: Response model with execution metadata

**Example:**
```python
from src.components.llm_proxy.models import LLMTask, TaskType, QualityRequirement

task = LLMTask(
    task_type=TaskType.EXTRACTION,
    prompt="Extract entities from legal contract...",
    data_classification=DataClassification.CONFIDENTIAL,  # → forces local
    quality_requirement=QualityRequirement.CRITICAL,
    complexity=Complexity.HIGH,
)
```

---

### 2. `config.py` ✅ (Complete)
**Purpose:** Configuration management with environment variable interpolation

**Key Classes:**
- `LLMProxyConfig`: Main configuration model
- `get_llm_proxy_config()`: Singleton configuration accessor

**Features:**
- Loads `config/llm_config.yml`
- Interpolates environment variables: `${VAR}` or `${VAR:-default}`
- Validates required providers
- Provides convenience methods for budget limits, model defaults

**Example:**
```python
from src.components.llm_proxy.config import get_llm_proxy_config

config = get_llm_proxy_config()
local_config = config.get_provider_config("local_ollama")
budget_limit = config.get_budget_limit("openai")  # → 80.0 (USD)
```

---

### 3. `aegis_llm_proxy.py` 🚧 (Pending)
**Purpose:** Main proxy class with routing logic

**Status:** Waiting for `any-llm-sdk` installation

**Key Features:**
- Initialize ANY-LLM with multiple providers
- Intelligent routing based on task characteristics
- Budget enforcement (ANY-LLM built-in)
- Automatic fallback (OpenAI → Ollama → Local)
- Metrics tracking (Prometheus, LangSmith)

**Planned API:**
```python
from src.components.llm_proxy import get_aegis_llm_proxy

proxy = get_aegis_llm_proxy()
response = await proxy.generate(task)

print(response.provider)  # → "local_ollama"
print(response.cost_usd)  # → 0.0
print(response.content)   # → Generated text
```

---

## Configuration

### File: `config/llm_config.yml`

**Providers:**
```yaml
providers:
  local_ollama:
    base_url: "http://localhost:11434"
    models: [gemma-3-4b-it-Q8_0, llama3.2:8b, bge-m3]

  ollama_cloud:
    base_url: "https://ollama.cloud"
    api_key: "${OLLAMA_CLOUD_API_KEY}"
    models: [llama3-70b, llava-13b]

  openai:
    api_key: "${OPENAI_API_KEY}"
    models: [gpt-4o, gpt-4o-mini]
```

**Budgets:**
```yaml
budgets:
  monthly_limits:
    ollama_cloud: 120.0  # $120/month
    openai: 80.0         # $80/month
  alert_threshold: 0.8   # Alert at 80%
```

**Routing:**
```yaml
routing:
  default_provider: local_ollama
  quality_critical_provider: openai
  data_classification_overrides:
    pii: local_ollama      # GDPR compliance
    hipaa: local_ollama    # HIPAA compliance
    confidential: local_ollama
```

---

## Environment Variables

**Required:**
```bash
# Local Ollama (always required)
OLLAMA_BASE_URL=http://localhost:11434

# Ollama Cloud (optional, for Tier 2)
OLLAMA_CLOUD_BASE_URL=https://ollama.cloud
OLLAMA_CLOUD_API_KEY=your-key-here

# OpenAI (optional, for Tier 3)
OPENAI_API_KEY=sk-...
OPENAI_ORGANIZATION=org-...  # Optional
```

---

## Routing Logic

### Priority Order:

1. **Data Privacy** (FIRST PRIORITY)
   - PII, HIPAA, Confidential → **ALWAYS local**
   - Non-negotiable (GDPR/HIPAA compliance)

2. **Task Type**
   - Embeddings → **ALWAYS local** (BGE-M3 excellent, no cloud benefit)

3. **Budget Check**
   - If budget exceeded → **Fallback to local**

4. **Quality + Complexity**
   - Critical quality + High complexity → **OpenAI**
   - High quality + Medium complexity → **Ollama Cloud**
   - Default → **Local**

### Example Routing Decisions:

| Task | Classification | Quality | Complexity | → Provider | Reason |
|------|---------------|---------|------------|-----------|--------|
| Simple query | Public | Medium | Low | **Local** | Default |
| Legal contract | Confidential | Critical | High | **Local** | Data privacy |
| Standard extraction | Public | High | High | **Ollama Cloud** | Quality + cost |
| Medical record | HIPAA | Critical | High | **Local** | HIPAA compliance |
| Batch 100 docs | Public | High | Medium | **Ollama Cloud** | Scale |

---

## Installation

### 1. Install ANY-LLM SDK

```bash
# Add to pyproject.toml (already done in Sprint 23)
poetry add 'any-llm-sdk[openai,ollama]'

# Install
poetry install
```

### 2. Verify Installation

```python
# Test import
from any_llm import AnyLLM, Provider

# Test local Ollama
llm = AnyLLM(providers=[
    Provider.OLLAMA(base_url="http://localhost:11434")
])

response = llm.completions.create(
    provider="ollama",
    model="gemma-3-4b-it-Q8_0",
    messages=[{"role": "user", "content": "Hello"}],
)
print(response.choices[0].message.content)
```

---

## Testing

### Unit Tests (30 tests planned)
**File:** `tests/unit/llm_proxy/test_routing.py`

**Test Categories:**
- Data privacy routing (PII → local)
- Quality-based routing (critical → OpenAI)
- Batch processing routing (>10 docs → Ollama Cloud)
- Budget enforcement
- Fallback chain

### Integration Tests (15 tests planned)
**File:** `tests/integration/llm_proxy/test_any_llm_integration.py`

**Test Categories:**
- Actual provider calls (Local, Ollama Cloud, OpenAI)
- Budget exceeded fallback
- Provider error fallback
- Cost tracking accuracy

### E2E Tests (5 tests planned)
**File:** `tests/e2e/test_llm_proxy_e2e.py`

**Test Categories:**
- Full ingestion pipeline (Docling → Extraction → Graph)
- LangGraph nodes using AegisLLMProxy
- Multi-turn conversation with routing

---

## Development Status (Sprint 23, Week 1)

### ✅ Completed (Nov 13, 2025)
- [x] `models.py`: Pydantic models for tasks/responses (200 LOC)
- [x] `config.py`: Configuration management (150 LOC)
- [x] `config/llm_config.yml`: YAML configuration (120 lines)
- [x] `README.md`: Component documentation (this file)
- [x] `pyproject.toml`: ANY-LLM SDK dependency added

### 🚧 In Progress
- [ ] Install `any-llm-sdk` (poetry install)
- [ ] Implement `aegis_llm_proxy.py` (400 LOC)

### 📋 Pending (Week 1-2)
- [ ] Unit tests (30 tests)
- [ ] Integration tests (15 tests)
- [ ] E2E tests (5 tests)
- [ ] LangGraph pipeline migration
- [ ] Provider setup (Ollama Cloud, OpenAI accounts)

---

## Next Steps

### Immediate (Today)
1. Run `poetry install` to install ANY-LLM SDK
2. Implement `AegisLLMProxy` base class (400 LOC)
3. Write routing logic (data privacy, quality-based, batch)

### This Week (Week 1)
1. Complete `aegis_llm_proxy.py`
2. Write 30 unit tests for routing
3. Test with local Ollama
4. Create Ollama Cloud account (if ready)
5. Create OpenAI account (test with gpt-4o-mini)

### Next Week (Week 2)
1. Migrate LangGraph pipelines to use AegisLLMProxy
2. Write 15 integration tests
3. Write 5 E2E tests
4. Validate metrics tracking (Prometheus)

---

## References

### Documentation
- [ADR-033: Mozilla ANY-LLM Integration](../../../docs/adr/ADR-033-any-llm-integration.md)
- [ANY-LLM Implementation Guide](../../../docs/architecture/ANY_LLM_IMPLEMENTATION_GUIDE.md)
- [Sprint 23 Planning (Revised)](../../../docs/sprint-23/SPRINT_23_PLANNING_v2_ANY_LLM.md)
- [Multi-Cloud Evaluation](../../../docs/architecture/MULTI_CLOUD_EVALUATION.md)

### External Resources
- [Mozilla ANY-LLM Docs](https://mozilla-ai.github.io/any-llm/)
- [Mozilla ANY-LLM GitHub](https://github.com/mozilla-ai/any-llm)

---

**Component Status:** 🚧 **IN DEVELOPMENT**
**Sprint:** Sprint 23 (Feature 23.4)
**Last Updated:** 2025-11-13
**Owner:** Backend Team
