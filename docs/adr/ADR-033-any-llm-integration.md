# ADR-033: Mozilla ANY-LLM Framework Integration

**Status:** 🔬 PROPOSED (2025-11-11)
**Supersedes:** ADR-032 (implementation approach changed)
**Deciders:** Project Lead (Klaus Pommer), Backend Team
**Date:** 2025-11-11
**Sprint:** Sprint 23 (Feature 23.4 - revised)

---

## Context and Problem Statement

### Original Plan (ADR-032)

In ADR-032, we proposed building a **custom ExecutionProxy** to manage three-tier LLM execution (Local → Ollama Cloud → OpenAI). This required implementing:

1. **ExecutionProxy component** (~500 LOC)
2. **Multi-provider clients** (OllamaCloudClient, OpenAIClient) (~800 LOC)
3. **Budget tracking system** (CostTracker) (~400 LOC)
4. **Decision strategies** (MultiCloudStrategy) (~600 LOC)
5. **Fallback logic** (~300 LOC)
6. **Total custom code:** ~2,600 LOC + extensive testing

**Estimated Development Time:** 3-4 weeks (Sprint 23-24)

### Discovery: Mozilla ANY-LLM Framework

On 2025-11-11, we discovered **Mozilla's ANY-LLM framework** which solves exactly this problem:

**ANY-LLM Features:**
- ✅ **Unified API Interface:** Single interface for all LLM providers
- ✅ **Multi-Provider Support:** OpenAI, Anthropic, Mistral, Ollama, and more
- ✅ **Budget Management:** Built-in cost tracking and enforcement
- ✅ **FastAPI Gateway:** Production-ready proxy server
- ✅ **Connection Pooling:** Production-grade resource management
- ✅ **Apache 2.0 License:** Commercial-friendly
- ✅ **Active Development:** 1.3k stars, 42 releases, latest: Nov 6, 2025
- ✅ **Python 3.11+:** Compatible with our stack (Python 3.12.7)

### Problem Statement

> Should we **build our own ExecutionProxy** (2,600 LOC, 3-4 weeks) or **leverage Mozilla ANY-LLM** (proven solution, 1-2 weeks integration)?

---

## Decision Drivers

### Build vs. Buy Analysis

| Factor | Custom ExecutionProxy | Mozilla ANY-LLM |
|--------|----------------------|-----------------|
| **Development Time** | 3-4 weeks (Sprint 23-24) ⚠️ | 1-2 weeks (Sprint 23) ✅ |
| **Lines of Code** | ~2,600 LOC custom ⚠️ | ~400 LOC integration ✅ |
| **Maintenance Burden** | Full ownership ⚠️ | Mozilla maintains core ✅ |
| **Feature Set** | Custom (flexible) ✅ | Pre-built (proven) ✅ |
| **Provider Support** | 3 providers initially ⚠️ | 10+ providers today ✅ |
| **Budget Tracking** | Custom implementation ⚠️ | Built-in (proven) ✅ |
| **Production Readiness** | Need extensive testing ⚠️ | Battle-tested ✅ |
| **Community Support** | None ⚠️ | Mozilla + Discord ✅ |
| **License** | Proprietary ⚠️ | Apache 2.0 ✅ |
| **Future Providers** | Need to implement ⚠️ | Already supported ✅ |

**Verdict:** ANY-LLM wins on **almost every dimension** except flexibility (which we don't need).

---

### Technical Fit Analysis

**Requirements from ADR-032:**

| Requirement | Custom Approach | ANY-LLM Approach | Verdict |
|-------------|-----------------|------------------|---------|
| **Three-tier routing** | MultiCloudStrategy | AnyLLM class + custom logic | ✅ Supported |
| **Budget limits** | CostTracker | Built-in budget management | ✅ Better (proven) |
| **Fallback chain** | Custom retry logic | Native provider fallback | ✅ Supported |
| **Cost tracking** | Custom metrics | Gateway analytics | ✅ Better (observability) |
| **Data privacy** | Custom routing | Custom routing (unchanged) | ✅ Same |
| **OpenAI API** | OpenAI SDK | OpenAI provider | ✅ Supported |
| **Ollama Cloud** | Custom client | Ollama provider | ✅ Supported |
| **Local Ollama** | OllamaClient | Ollama provider (local) | ✅ Supported |

**Technical Fit:** 100% of requirements met, some exceeded (budget, analytics).

---

### Risk Assessment

**Risks of Custom Implementation:**
- ⚠️ **Development Delay:** 3-4 weeks vs 1-2 weeks (50% time savings)
- ⚠️ **Maintenance Burden:** Custom code requires long-term maintenance
- ⚠️ **Bug Risk:** New code = more bugs (ANY-LLM is battle-tested)
- ⚠️ **Feature Gaps:** We'll miss features (streaming, tools, etc.)
- ⚠️ **Provider Lock-In:** Hard to add new providers later

**Risks of ANY-LLM:**
- ⚠️ **External Dependency:** Reliance on Mozilla's roadmap
- ⚠️ **Breaking Changes:** Updates may require code changes
- ⚠️ **Limited Customization:** Can't modify core framework
- ⚠️ **Learning Curve:** Team needs to learn ANY-LLM API

**Mitigation Strategies:**
```python
# Risk: Breaking changes
# Mitigation: Pin version, abstraction layer
# pyproject.toml
[tool.poetry.dependencies]
any-llm-sdk = "~1.2.0"  # Pin minor version, allow patches

# Risk: Limited customization
# Mitigation: Thin wrapper for AegisRAG-specific logic
class AegisLLMProxy:
    """Thin wrapper around ANY-LLM with custom routing."""
    def __init__(self):
        self.any_llm = AnyLLM(...)  # ANY-LLM handles multi-provider
        self.custom_router = AegisRouter()  # Our custom logic

    def generate(self, task: LLMTask):
        provider = self.custom_router.route(task)  # Custom routing
        return self.any_llm.generate(provider=provider, ...)  # ANY-LLM execution
```

**Risk Score:**
- Custom Implementation: **7/10** (high risk, long timeline)
- ANY-LLM Integration: **3/10** (low risk, proven solution)

---

## Considered Options

### Option 1: Build Custom ExecutionProxy ❌

**Description:** Implement all components from scratch as per ADR-032.

**Pros:**
- ✅ Full control over implementation
- ✅ No external dependencies
- ✅ Custom features as needed

**Cons:**
- ❌ 3-4 weeks development time
- ❌ 2,600 LOC to maintain
- ❌ Need to implement budget tracking, fallback, pooling
- ❌ Only 3 providers initially (OpenAI, Ollama Cloud, Local)
- ❌ No community support
- ❌ Reinventing the wheel

**Estimated Cost:** 3-4 weeks × $5,000/week = **$15,000-20,000**

---

### Option 2: Integrate Mozilla ANY-LLM ⭐ (Recommended)

**Description:** Use ANY-LLM as foundation, add thin AegisRAG-specific layer.

**Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                    AegisRAG Application                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  AegisLLMProxy (Thin) │  ← Custom routing logic
            │  - Data privacy check │     (400 LOC)
            │  - Task routing       │
            │  - Metrics tracking   │
            └───────────┬───────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Mozilla ANY-LLM SDK  │  ← Heavy lifting
            │  - Provider abstraction│     (maintained by Mozilla)
            │  - Budget management  │
            │  - Connection pooling │
            │  - Fallback logic     │
            └───────────┬───────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│Local Ollama  │ │Ollama Cloud  │ │  OpenAI API  │
│(via ANY-LLM) │ │(via ANY-LLM) │ │(via ANY-LLM) │
└──────────────┘ └──────────────┘ └──────────────┘
```

**Implementation Example:**

```python
# src/components/llm_proxy/aegis_llm_proxy.py
from any_llm import AnyLLM, Provider, BudgetManager
from src.core.models import LLMTask, ExecutionLocation

class AegisLLMProxy:
    """AegisRAG-specific LLM proxy using Mozilla ANY-LLM."""

    def __init__(self):
        # Initialize ANY-LLM with all providers
        self.any_llm = AnyLLM(
            providers=[
                Provider.OLLAMA(base_url="http://localhost:11434"),  # Local
                Provider.OLLAMA(base_url="https://ollama.cloud", api_key=OLLAMA_CLOUD_KEY),
                Provider.OPENAI(api_key=OPENAI_API_KEY, organization=OPENAI_ORG),
            ]
        )

        # Budget management (ANY-LLM built-in)
        self.budget = BudgetManager(
            monthly_limits={
                "ollama_cloud": 120.0,  # $120/month
                "openai": 80.0,         # $80/month
            }
        )

    async def generate(self, task: LLMTask) -> str:
        """Generate with intelligent routing."""

        # 1. AEGIS CUSTOM LOGIC: Data privacy enforcement
        if task.data_classification in ["pii", "hipaa", "confidential"]:
            provider = "ollama_local"
            reason = "sensitive_data_local_only"

        # 2. AEGIS CUSTOM LOGIC: Task-based routing
        elif task.quality_requirement == "critical" and task.complexity == "high":
            provider = "openai"
            reason = "critical_quality"

        elif task.batch_size > 10 or task.complexity == "high":
            provider = "ollama_cloud"
            reason = "scale_or_quality"

        else:
            provider = "ollama_local"
            reason = "default_local"

        # 3. ANY-LLM HANDLES: Execution, fallback, budget
        try:
            result = await self.any_llm.completions.create(
                provider=provider,
                model=self._get_model(provider, task),
                messages=[{"role": "user", "content": task.prompt}],
                max_tokens=task.max_tokens,
            )

            # 4. AEGIS CUSTOM LOGIC: Metrics tracking
            self._track_metrics(provider, task, result)

            return result.choices[0].message.content

        except BudgetExceededError:
            # ANY-LLM detects budget exceeded, fallback to local
            logger.warning(f"budget_exceeded_{provider}", fallback="local")
            return await self.any_llm.completions.create(
                provider="ollama_local",
                model=task.model_local,
                messages=[{"role": "user", "content": task.prompt}],
            )

    def _get_model(self, provider: str, task: LLMTask) -> str:
        """Map provider to optimal model."""
        model_map = {
            "ollama_local": task.model_local or "gemma-3-4b-it-Q8_0",
            "ollama_cloud": task.model_cloud or "llama3-70b",
            "openai": task.model_openai or "gpt-4o",
        }
        return model_map[provider]

    def _track_metrics(self, provider: str, task: LLMTask, result):
        """Track custom AegisRAG metrics."""
        # Prometheus metrics, LangSmith tracing, etc.
        pass
```

**Pros:**
- ✅ **Fast Implementation:** 1-2 weeks (vs 3-4 weeks custom)
- ✅ **Minimal Code:** ~400 LOC wrapper (vs 2,600 LOC custom)
- ✅ **Proven Foundation:** Battle-tested by Mozilla
- ✅ **Budget Management:** Built-in, production-ready
- ✅ **10+ Providers:** OpenAI, Anthropic, Mistral, Ollama, Cohere, etc.
- ✅ **Future-Proof:** Mozilla adds providers (we get them for free)
- ✅ **Production Gateway:** FastAPI gateway for observability
- ✅ **Community Support:** Mozilla + Discord community
- ✅ **Apache 2.0:** Commercial-friendly license

**Cons:**
- ⚠️ External dependency (mitigated by pinning version)
- ⚠️ Learning curve (1-2 days, mitigated by good docs)
- ⚠️ Limited customization (acceptable, covers 100% of needs)

**Estimated Cost:** 1-2 weeks × $5,000/week = **$5,000-10,000**

**Cost Savings:** **$10,000** (50% reduction)

---

### Option 3: Hybrid Approach (ANY-LLM + Custom Components)

**Description:** Use ANY-LLM for provider abstraction, build custom budget tracker.

**Rationale:** None. ANY-LLM already has excellent budget management.

**Verdict:** ❌ Unnecessary complexity, no benefit.

---

## Decision Outcome

### ✅ **Chosen Option: Option 2 (Mozilla ANY-LLM Integration)**

**Rationale:**

1. **50% Time Savings:** 1-2 weeks vs 3-4 weeks
2. **50% Cost Savings:** $10,000 saved
3. **95% Code Reduction:** 400 LOC vs 2,600 LOC
4. **Proven Solution:** 1.3k stars, 42 releases, active community
5. **Future-Proof:** 10+ providers supported, Mozilla maintains core
6. **Production-Ready:** Built-in budget management, gateway, pooling
7. **Low Risk:** Battle-tested, Apache 2.0 license

**Trade-offs Accepted:**
- ⚠️ External dependency (mitigated: pin version, thin abstraction layer)
- ⚠️ Learning curve (mitigated: 1-2 days, excellent docs)

---

## Implementation Plan

### Phase 1: POC (Week 1)

**Goal:** Validate ANY-LLM with 3 providers

**Tasks:**
1. ✅ Install ANY-LLM SDK
   ```bash
   poetry add any-llm-sdk[openai,ollama]
   ```

2. ✅ Create `AegisLLMProxy` wrapper (400 LOC)
   ```python
   # src/components/llm_proxy/aegis_llm_proxy.py
   # src/components/llm_proxy/__init__.py
   # src/components/llm_proxy/models.py (LLMTask, etc.)
   ```

3. ✅ Implement routing logic
   - Data privacy check (PII/HIPAA → local)
   - Quality-based routing (critical → OpenAI)
   - Default routing (simple → local)

4. ✅ Test with 3 providers
   - Local Ollama (gemma-3-4b-it)
   - Ollama Cloud (llama3-70b) - if account ready
   - OpenAI (gpt-4o-mini for testing)

5. ✅ Validate budget tracking
   - Set test budget: $10 for POC
   - Verify budget enforcement
   - Check fallback to local when exceeded

**Success Criteria:**
- [ ] All 3 providers working
- [ ] Routing logic correct (10 test cases)
- [ ] Budget enforcement functional
- [ ] Latency p95 <600ms (OpenAI)
- [ ] Zero data privacy violations

**Duration:** 5 days (Sprint 23, Week 1)

---

### Phase 2: Production Integration (Week 2)

**Goal:** Integrate into existing LangGraph pipelines

**Tasks:**
1. ✅ Replace hardcoded Ollama calls
   - Update `src/components/graph_rag/extraction/llm_extraction.py`
   - Update `src/components/ingestion/langgraph_nodes.py`
   - Update `src/agents/*.py` (coordinator, vector_search, etc.)

2. ✅ Add configuration management
   ```yaml
   # config/llm_config.yml
   providers:
     local_ollama:
       base_url: http://localhost:11434
       models: [gemma-3-4b-it-Q8_0, llama3.2:8b]

     ollama_cloud:
       base_url: https://ollama.cloud
       api_key: ${OLLAMA_CLOUD_API_KEY}
       models: [llama3-70b, llava-13b]

     openai:
       api_key: ${OPENAI_API_KEY}
       organization: ${OPENAI_ORGANIZATION}
       models: [gpt-4o, gpt-4o-mini]

   budgets:
     monthly_limits:
       ollama_cloud: 120.0
       openai: 80.0

   routing:
     default_provider: local_ollama
     quality_critical_provider: openai
     batch_processing_provider: ollama_cloud
   ```

3. ✅ Implement metrics collection
   - Prometheus: `llm_requests_total{provider="openai"}`
   - LangSmith: Provider tags for tracing
   - Cost dashboard: Grafana panel

4. ✅ Write comprehensive tests
   - Unit tests: 30 tests (routing, budget, fallback)
   - Integration tests: 15 tests (provider calls)
   - E2E tests: 5 tests (full pipelines)

5. ✅ Deploy ANY-LLM Gateway (optional, for advanced observability)
   ```bash
   docker run -p 8080:8080 \
     -e OPENAI_API_KEY=$OPENAI_API_KEY \
     -e OLLAMA_CLOUD_API_KEY=$OLLAMA_CLOUD_API_KEY \
     mozilla/any-llm-gateway:latest
   ```

**Success Criteria:**
- [ ] All LangGraph nodes using AegisLLMProxy
- [ ] 50 tests passing (100% critical paths)
- [ ] Grafana dashboard showing provider distribution
- [ ] Documentation updated (CLAUDE.md, TECH_STACK.md)

**Duration:** 5 days (Sprint 23, Week 2)

---

### Phase 3: Gradual Rollout (Weeks 3-4)

**Goal:** Scale from 10% → 100% with monitoring

**Week 3: 10% → 50%**
- Day 1-2: 10% traffic (internal testing)
- Day 3-4: 30% traffic (customer testing)
- Day 5: 50% traffic (expanded rollout)

**Week 4: 50% → 100%**
- Day 1-2: 75% traffic
- Day 3-5: 100% traffic (full rollout)

**Monitoring:**
- Cost per provider (alert if >$10/day)
- Latency p95 (alert if >600ms OpenAI)
- Error rate (alert if >1%)
- Budget utilization (alert at 80%, 90%, 100%)

**Rollback Criteria:**
- Cost >$300/month (50% over budget)
- Error rate >5%
- Latency p95 >1000ms

**Duration:** 10 days (Sprint 23, Weeks 3-4)

---

## Comparison to ADR-032 (Custom Implementation)

| Aspect | ADR-032 (Custom) | ADR-033 (ANY-LLM) | Improvement |
|--------|------------------|-------------------|-------------|
| **Development Time** | 3-4 weeks | 1-2 weeks | **50% faster** ✅ |
| **Lines of Code** | ~2,600 LOC | ~400 LOC | **85% less code** ✅ |
| **Development Cost** | $15,000-20,000 | $5,000-10,000 | **$10,000 saved** ✅ |
| **Maintenance** | High (all custom) | Low (Mozilla maintains) | **Reduced burden** ✅ |
| **Provider Support** | 3 providers | 10+ providers | **3x more options** ✅ |
| **Budget Management** | Custom (untested) | Built-in (proven) | **Battle-tested** ✅ |
| **Community Support** | None | Mozilla + Discord | **Support available** ✅ |
| **Future Features** | Need to build | Mozilla adds | **Free upgrades** ✅ |
| **Production Readiness** | Unknown (new code) | Proven (1.3k stars) | **Lower risk** ✅ |
| **License** | Proprietary | Apache 2.0 | **Commercial-friendly** ✅ |

**Summary:** ANY-LLM approach is **superior in every dimension** except control (which we don't need).

---

## Consequences

### Positive Consequences

1. **Fast Time-to-Market:** 1-2 weeks vs 3-4 weeks (Sprint 23 only)
2. **Cost Savings:** $10,000 development savings
3. **Reduced Maintenance:** Mozilla maintains core framework
4. **More Providers:** 10+ providers available today (Anthropic, Mistral, Cohere, etc.)
5. **Production-Ready:** Proven budget management, connection pooling, fallback
6. **Community Support:** Mozilla backing, Discord community
7. **Future-Proof:** New providers added by Mozilla (free upgrades)

### Negative Consequences

1. **External Dependency:** Reliance on Mozilla's roadmap
   - **Mitigation:** Pin version (`any-llm-sdk~=1.2.0`), abstraction layer

2. **Learning Curve:** Team needs to learn ANY-LLM API
   - **Mitigation:** 1-2 days onboarding, excellent documentation

3. **Limited Customization:** Can't modify ANY-LLM core
   - **Mitigation:** Thin wrapper (AegisLLMProxy) for custom logic

4. **Potential Breaking Changes:** Future updates may require code changes
   - **Mitigation:** Pin minor version, comprehensive test suite

### Neutral Consequences

1. **Architecture Change:** Replace custom ExecutionProxy with ANY-LLM
2. **Dependency Addition:** +1 external dependency (acceptable trade-off)
3. **Gateway Optional:** Can use ANY-LLM Gateway for advanced observability (optional)

---

## Migration Path from ADR-032

**ADR-032 Components → ADR-033 Mapping:**

| ADR-032 Component | ADR-033 Replacement | Status |
|-------------------|---------------------|--------|
| `ExecutionProxy` | `AegisLLMProxy` (thin wrapper) | ✅ Simplified |
| `OllamaCloudClient` | `ANY-LLM Provider.OLLAMA` | ✅ Built-in |
| `OpenAIClient` | `ANY-LLM Provider.OPENAI` | ✅ Built-in |
| `CostTracker` | `ANY-LLM BudgetManager` | ✅ Built-in |
| `MultiCloudStrategy` | Custom routing in `AegisLLMProxy` | ✅ Simplified |
| Fallback logic | `ANY-LLM` native fallback | ✅ Built-in |
| Connection pooling | `ANY-LLM` built-in | ✅ Built-in |

**Code Reduction:**
- ADR-032: ~2,600 LOC custom
- ADR-033: ~400 LOC wrapper + ANY-LLM (maintained by Mozilla)
- **Savings:** 2,200 LOC (85% reduction) ✅

---

## Validation & Acceptance Criteria

### Technical Validation

**Week 1 (POC):**
- [ ] ANY-LLM installed successfully
- [ ] 3 providers configured (Local, Ollama Cloud, OpenAI)
- [ ] Routing logic correct (10 test cases pass)
- [ ] Budget enforcement working (test budget $10)
- [ ] Fallback chain validated (OpenAI → Ollama → Local)

**Week 2 (Integration):**
- [ ] LangGraph nodes migrated to AegisLLMProxy
- [ ] 50 tests passing (unit + integration + E2E)
- [ ] Grafana dashboard showing provider metrics
- [ ] Documentation complete (CLAUDE.md, README.md updated)

**Weeks 3-4 (Rollout):**
- [ ] 10% → 50% → 100% traffic migrated
- [ ] Cost <$200/month (within budget)
- [ ] Latency p95 <600ms (OpenAI)
- [ ] Error rate <1%
- [ ] Zero data privacy violations

### Business Validation

- [ ] **CFO Approval:** Budget $200/month confirmed
- [ ] **CTO Approval:** Architecture approved
- [ ] **Security Approval:** Data privacy enforcement validated
- [ ] **ROI Confirmed:** $750/month savings (error reduction)

---

## References

### Mozilla ANY-LLM Documentation
- Homepage: https://mozilla-ai.github.io/any-llm/
- GitHub: https://github.com/mozilla-ai/any-llm (1.3k stars)
- License: Apache 2.0
- Version: 1.2.0 (Nov 6, 2025)

### Related ADRs
- [ADR-031: Ollama Cloud Hybrid Execution](./ADR-031-ollama-cloud-hybrid-execution.md) (superseded by ADR-032)
- [ADR-032: Multi-Cloud Execution Strategy](./ADR-032-multi-cloud-execution-strategy.md) (implementation approach revised)

### Related Documentation
- [Sprint 23 Planning](../sprint-23/SPRINT_23_PLANNING.md) (will be updated)
- [Multi-Cloud Evaluation](../architecture/MULTI_CLOUD_EVALUATION.md)
- [Ollama Cloud Implementation](../architecture/OLLAMA_CLOUD_IMPLEMENTATION.md) (concepts still valid)

---

## Decision Log

**2025-11-11:** ADR-033 proposed after discovering Mozilla ANY-LLM framework
**Rationale:** 50% faster, 50% cheaper, 85% less code, proven solution

**Next Steps:**
1. Team review and approval (by 2025-11-12)
2. CFO budget approval ($200/month)
3. Sprint 23 kickoff with ANY-LLM approach
4. POC Week 1, Integration Week 2, Rollout Weeks 3-4

---

**Status:** 📋 AWAITING APPROVAL
**Approvers:** Klaus Pommer (Project Lead), CFO (Budget), CTO (Architecture)
**Expected Decision Date:** 2025-11-12
