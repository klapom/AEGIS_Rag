# Sprint 23 Planning: Mozilla ANY-LLM Multi-Cloud Integration (REVISED)

**Sprint:** Sprint 23 (2025-11-12+)
**Status:** 📋 PLANNED (Revised with ANY-LLM approach)
**Previous Sprint:** Sprint 22 ✅ COMPLETE
**Supersedes:** SPRINT_23_PLANNING.md (original plan)
**Related ADR:** ADR-033 (Mozilla ANY-LLM Integration)

---

## 🔄 Plan Revision: Why ANY-LLM?

### Original Plan (SPRINT_23_PLANNING.md)
Build custom **ExecutionProxy** for multi-cloud (Local + Ollama Cloud + OpenAI)
- **Estimated Effort:** 3-4 weeks
- **Lines of Code:** ~2,600 LOC custom implementation
- **Cost:** $15,000-20,000 development
- **Risk:** High (new code, unproven)

### Revised Plan (THIS DOCUMENT)
Use **Mozilla ANY-LLM** framework as foundation
- **Estimated Effort:** 1-2 weeks (50% faster)
- **Lines of Code:** ~400 LOC wrapper (85% reduction)
- **Cost:** $5,000-10,000 development (50% savings)
- **Risk:** Low (battle-tested, 1.3k stars, Apache 2.0)

**Decision:** Leverage ANY-LLM (see ADR-033 for full rationale)

---

## Sprint 23 Objectives

### Primary Goal: Mozilla ANY-LLM Multi-Cloud Integration
Enable three-tier LLM execution (Local → Ollama Cloud → OpenAI) using Mozilla's ANY-LLM framework.

### Secondary Goal: Production Infrastructure
Kubernetes deployment, monitoring, CI/CD (deferred from original Sprint 23).

---

## Sprint 22 Completion Summary

### ✅ Completed Features
- **Phase 1: Critical Refactoring**
  - API Security Hardening (Request ID, Error Responses, Rate Limiting, JWT Auth)
  - 80+ tests (100% pass rate)

- **Phase 2: Hybrid Ingestion**
  - FormatRouter for 30 document formats
  - LlamaIndex fallback parser
  - Comprehensive documentation (1,500+ lines)

### 📊 Test Results
- **149 total tests** executed
- **96% pass rate** (145/149)
- **100% core functionality** (routing, security, parsing)

---

## Sprint 23 Features (REVISED)

### Phase 1: Mozilla ANY-LLM Integration (Priority 1)

#### Feature 23.4: AegisLLMProxy Implementation (REVISED) ⭐
**Owner:** backend-agent
**Estimated Effort:** 5 days (Week 1 of Sprint 23)
**Dependencies:** Poetry, Python 3.12+, ANY-LLM SDK

**Original Scope (ADR-032):**
- Custom ExecutionProxy (~500 LOC)
- OllamaCloudClient (~400 LOC)
- OpenAIClient (~400 LOC)
- CostTracker (~400 LOC)
- MultiCloudStrategy (~600 LOC)
- Fallback logic (~300 LOC)
- **Total:** ~2,600 LOC custom

**Revised Scope (ADR-033 with ANY-LLM):**
- AegisLLMProxy wrapper (~300 LOC) - routing logic only
- Configuration management (~50 LOC)
- Pydantic models (~50 LOC)
- **Total:** ~400 LOC (ANY-LLM handles the rest)

**Deliverables:**

1. **ANY-LLM SDK Installation**
   ```bash
   poetry add 'any-llm-sdk[openai,ollama]'
   ```

2. **AegisLLMProxy Implementation**
   ```
   src/components/llm_proxy/
   ├── __init__.py
   ├── aegis_llm_proxy.py      # Main proxy (300 LOC)
   ├── models.py                # Pydantic models (50 LOC)
   ├── config.py                # Config loader (50 LOC)
   └── README.md
   ```

3. **Configuration Files**
   ```yaml
   # config/llm_config.yml
   providers:
     local_ollama: {base_url: "http://localhost:11434"}
     ollama_cloud: {base_url: "https://ollama.cloud", api_key: "..."}
     openai: {api_key: "sk-...", organization: "org-..."}

   budgets:
     monthly_limits:
       ollama_cloud: 120.0  # $120/month
       openai: 80.0         # $80/month
   ```

4. **Routing Logic (AEGIS-specific)**
   - Data privacy enforcement: PII/HIPAA → always local
   - Quality-based routing: critical + high complexity → OpenAI
   - Batch processing: >10 docs → Ollama Cloud
   - Default: Local (70% of tasks)

5. **Integration with Existing Components**
   - Update `src/components/graph_rag/extraction/llm_extraction.py`
   - Update `src/components/ingestion/langgraph_nodes.py`
   - Update `src/agents/*.py` (coordinator, vector_search, etc.)

**Testing:**
- Unit tests: 30 tests (routing logic, budget enforcement)
- Integration tests: 15 tests (actual provider calls)
- E2E tests: 5 tests (full pipelines)
- **Total:** 50 tests (target: 100% pass rate)

**Success Criteria:**
- [ ] ANY-LLM SDK installed and working
- [ ] AegisLLMProxy routes correctly (10 test cases)
- [ ] 3 providers configured (Local, Ollama Cloud, OpenAI)
- [ ] Budget limits enforced (ANY-LLM built-in)
- [ ] Fallback chain works (OpenAI → Ollama → Local)
- [ ] PII data stays local (GDPR/HIPAA compliance)
- [ ] 50 tests passing (100%)

**Documentation:**
- [x] ADR-033: ANY-LLM Integration Decision
- [x] ANY_LLM_IMPLEMENTATION_GUIDE.md (comprehensive guide)
- [ ] CLAUDE.md updated (technology stack section)
- [ ] TECH_STACK.md updated (any-llm-sdk entry)

**Duration:** 5 days (Sprint 23, Week 1)

---

#### Feature 23.5: Provider Configuration & POC (NEW)
**Owner:** backend-agent
**Estimated Effort:** 3 days (Week 1 of Sprint 23)
**Dependencies:** Feature 23.4 complete

**Deliverables:**

1. **Ollama Cloud Account Setup**
   - Sign up at https://ollama.cloud
   - Get API key
   - Test llama3-70b model
   - Verify pricing: ~$0.001/1k tokens

2. **OpenAI Account Setup**
   - Sign up at https://platform.openai.com
   - Get API key
   - Test gpt-4o-mini (cheaper for POC)
   - Set budget alerts ($10/day)

3. **POC with 10% Traffic**
   - Route 10% of extraction tasks to Ollama Cloud
   - Route 5% of critical tasks to OpenAI
   - Track costs for 1 week
   - Validate quality improvement (+10-15% expected)

4. **Metrics Collection**
   - Prometheus metrics: `llm_requests_total{provider="openai"}`
   - Cost tracking: `llm_cost_usd_total{provider="ollama_cloud"}`
   - Latency tracking: `llm_latency_seconds{provider="local_ollama"}`

**Testing:**
- Manual testing with 100 sample documents
- Cost validation: <$50 for POC week
- Quality validation: RAGAS benchmarking

**Success Criteria:**
- [ ] Ollama Cloud account active and tested
- [ ] OpenAI account active and tested
- [ ] 10% traffic routed successfully
- [ ] Cost <$50 for POC week
- [ ] Quality improvement validated (+10-15%)
- [ ] Zero data privacy violations

**Duration:** 3 days (Sprint 23, Week 1)

---

### Phase 2: Production Integration (Priority 2)

#### Feature 23.6: LangGraph Pipeline Migration
**Owner:** backend-agent
**Estimated Effort:** 5 days (Week 2 of Sprint 23)
**Dependencies:** Feature 23.4, 23.5 complete

**Deliverables:**

1. **Replace Hardcoded Ollama Calls**
   - `src/components/graph_rag/extraction/llm_extraction.py`
     - Before: `ChatOllama(model="gemma-3-4b-it-Q8_0")`
     - After: `await proxy.generate(task)`
   - `src/components/ingestion/langgraph_nodes.py`
     - VLM annotation node
     - Entity extraction node
   - `src/agents/coordinator.py`
     - Query classification
     - Response generation

2. **Add Provider Selection Logic**
   ```python
   # Example: Legal document extraction
   if document.classification == "legal":
       task = LLMTask(
           task_type=TaskType.EXTRACTION,
           quality_requirement=QualityRequirement.CRITICAL,
           complexity=Complexity.HIGH,
       )
       # Routes to OpenAI (critical quality)
   ```

3. **Metrics Integration**
   - Add Prometheus metrics to all LangGraph nodes
   - LangSmith tracing with provider tags
   - Grafana dashboard: "LLM Provider Distribution"

4. **Error Handling**
   - Catch `BudgetExceededError` → fallback to local
   - Catch `ProviderError` → automatic ANY-LLM fallback
   - Log all fallback events

**Testing:**
- Integration tests: 20 tests (LangGraph nodes with AegisLLMProxy)
- E2E tests: 10 tests (full ingestion → extraction → graph)
- Performance tests: Latency validation (<600ms p95 for OpenAI)

**Success Criteria:**
- [ ] All Ollama calls replaced with AegisLLMProxy
- [ ] Provider selection logic working (10 scenarios tested)
- [ ] Metrics visible in Grafana
- [ ] Error handling validated (budget exceeded, provider error)
- [ ] 30 tests passing (100%)

**Duration:** 5 days (Sprint 23, Week 2)

---

### Phase 3: Gradual Rollout (Priority 3)

#### Feature 23.7: Production Rollout with Monitoring
**Owner:** backend-agent + infrastructure-agent
**Estimated Effort:** 10 days (Weeks 3-4 of Sprint 23)
**Dependencies:** Feature 23.6 complete

**Rollout Plan:**

**Week 3: 10% → 50%**
- Day 1-2: **10% traffic** (internal testing)
  - Monitor: Cost, latency, error rate
  - Alert threshold: Cost >$5/day
- Day 3-4: **30% traffic** (customer testing)
  - Monitor: Quality improvements (RAGAS)
  - Alert threshold: Cost >$10/day
- Day 5: **50% traffic** (expanded rollout)
  - Monitor: Budget utilization (Ollama 50%, OpenAI 40%)
  - Alert threshold: Cost >$15/day

**Week 4: 50% → 100%**
- Day 1-2: **75% traffic**
  - Monitor: Fallback rate (<5% expected)
  - Alert threshold: Error rate >1%
- Day 3-5: **100% traffic** (full rollout)
  - Monitor: All metrics (cost, quality, latency, errors)
  - Alert threshold: Cost >$200/month

**Monitoring Dashboard (Grafana):**
1. **Provider Distribution** (Pie chart)
   - Local: 70% (target)
   - Ollama Cloud: 20% (target)
   - OpenAI: 10% (target)

2. **Cost per Provider** (Time series)
   - Daily cost trend
   - Budget utilization gauge (80% alert)
   - Projected monthly cost

3. **Quality Metrics** (RAGAS)
   - Accuracy by provider
   - Quality improvement over baseline
   - Error rate by provider

4. **Latency p95** (Time series)
   - Local: 50-200ms (baseline)
   - Ollama Cloud: 200-500ms (acceptable)
   - OpenAI: 300-600ms (acceptable)

5. **Fallback Events** (Counter)
   - Budget exceeded: Count per day
   - Provider error: Count per day
   - Total fallback rate: <5% (target)

**Rollback Criteria:**
- Cost >$300/month (50% over budget) → rollback to 50%
- Error rate >5% → rollback to previous percentage
- Quality regression >5% → investigate and fix
- Latency p95 >1000ms → rollback or optimize

**Success Criteria:**
- [ ] 100% traffic migrated successfully
- [ ] Cost <$200/month (within budget)
- [ ] Quality +10-15% (validated with RAGAS)
- [ ] Latency p95 <600ms (OpenAI)
- [ ] Error rate <1%
- [ ] Fallback rate <5%
- [ ] Zero data privacy violations

**Duration:** 10 days (Sprint 23, Weeks 3-4)

---

## DEFERRED Features (Original Sprint 23)

The following features from the original Sprint 23 plan are **deferred to Sprint 24**:

### Deferred to Sprint 24:
- **Feature 23.1:** Kubernetes Deployment (Helm charts)
- **Feature 23.2:** Monitoring & Observability (Prometheus, Grafana, Jaeger)
- **Feature 23.3:** CI/CD Pipeline (GitHub Actions)

**Rationale:**
- ANY-LLM integration is higher priority (enables cloud execution)
- Kubernetes can run on existing Docker Compose for now
- Monitoring partially covered by ANY-LLM integration (Prometheus metrics)
- CI/CD already functional (pre-commit hooks, pytest)

**Timeline:**
- Sprint 23 (4 weeks): ANY-LLM integration (Features 23.4-23.7)
- Sprint 24 (4 weeks): Production infrastructure (Features 23.1-23.3 + user onboarding)

---

## Sprint 23 Timeline

### Week 1: POC (Nov 12-18)
- **Day 1-2:** Feature 23.4 - AegisLLMProxy implementation (300 LOC)
- **Day 3:** Feature 23.5 - Provider setup (Ollama Cloud, OpenAI)
- **Day 4-5:** Testing (50 unit + integration tests)

**Milestone:** AegisLLMProxy working with 3 providers, 10% traffic POC

---

### Week 2: Integration (Nov 19-25)
- **Day 1-3:** Feature 23.6 - LangGraph pipeline migration
- **Day 4-5:** Testing (30 integration + E2E tests)

**Milestone:** All LangGraph nodes using AegisLLMProxy, 30 tests passing

---

### Week 3: Rollout Phase 1 (Nov 26 - Dec 2)
- **Day 1-2:** 10% traffic (internal testing)
- **Day 3-4:** 30% traffic (customer testing)
- **Day 5:** 50% traffic (expanded rollout)

**Milestone:** 50% traffic migrated, costs <$100 for week 3

---

### Week 4: Rollout Phase 2 (Dec 3-9)
- **Day 1-2:** 75% traffic
- **Day 3-5:** 100% traffic (full rollout)

**Milestone:** 100% traffic migrated, Sprint 23 complete

---

## Success Criteria (Sprint 23)

### Technical Success:
- [ ] ANY-LLM SDK integrated successfully
- [ ] AegisLLMProxy routes to 3 providers correctly
- [ ] 80 tests passing (50 new + 30 updated)
- [ ] All LangGraph nodes migrated to AegisLLMProxy
- [ ] 100% traffic using multi-cloud execution

### Business Success:
- [ ] Cost <$200/month (within budget)
- [ ] Quality +10-15% on critical tasks (RAGAS validated)
- [ ] Zero data privacy violations (PII stays local)
- [ ] Fallback rate <5%
- [ ] Error rate <1%

### Documentation Success:
- [x] ADR-033 created (Mozilla ANY-LLM Integration)
- [x] ANY_LLM_IMPLEMENTATION_GUIDE.md created (comprehensive)
- [ ] CLAUDE.md updated (technology stack)
- [ ] TECH_STACK.md updated (any-llm-sdk entry)
- [ ] Sprint 23 completion report

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **ANY-LLM breaking changes** | Low | Medium | Pin version (`any-llm-sdk~=1.2.0`) |
| **Ollama Cloud API changes** | Medium | Medium | Fallback to local (ANY-LLM automatic) |
| **OpenAI cost overrun** | Medium | Medium | Hard budget cap ($80/month) |
| **Integration issues** | Low | High | 50 tests, gradual rollout (10% → 100%) |
| **Data privacy breach** | Low | Critical | Code-enforced PII → local routing |

### Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Budget approval delayed** | Medium | Medium | Start POC with $50 test budget |
| **Quality doesn't improve** | Low | High | RAGAS benchmarking, A/B testing |
| **Vendor lock-in (ANY-LLM)** | Low | Medium | Thin abstraction layer (400 LOC) |

---

## Comparison: Original vs Revised Plan

| Aspect | Original Plan | Revised Plan (ANY-LLM) | Improvement |
|--------|---------------|------------------------|-------------|
| **Development Time** | 3-4 weeks | 1-2 weeks | **50% faster** ✅ |
| **Lines of Code** | ~2,600 LOC custom | ~400 LOC wrapper | **85% less** ✅ |
| **Cost** | $15,000-20,000 | $5,000-10,000 | **$10,000 saved** ✅ |
| **Risk** | High (new code) | Low (battle-tested) | **Lower risk** ✅ |
| **Provider Support** | 3 providers | 10+ providers | **3x more** ✅ |
| **Budget Management** | Custom (untested) | Built-in (proven) | **Better** ✅ |
| **Maintenance** | Full ownership | Mozilla maintains | **Reduced** ✅ |
| **Community Support** | None | Mozilla + Discord | **Better** ✅ |

**Summary:** ANY-LLM approach is superior in every dimension.

---

## Sprint 24 Preview (Next Steps)

After Sprint 23 (ANY-LLM integration), Sprint 24 will focus on:

1. **Kubernetes Deployment** (deferred Feature 23.1)
   - Helm charts for production deployment
   - StatefulSets for databases
   - Horizontal Pod Autoscaler

2. **Advanced Monitoring** (deferred Feature 23.2)
   - Prometheus + Grafana dashboards
   - Jaeger distributed tracing
   - AlertManager for incidents

3. **CI/CD Pipeline** (deferred Feature 23.3)
   - GitHub Actions workflows
   - Automated testing (unit, integration, E2E)
   - Deployment automation

4. **User Onboarding**
   - External user registration
   - Project management UI (React frontend)
   - User documentation

**Estimated Duration:** 4 weeks (Sprint 24)

---

## References

### Related Documents
- [ADR-033: Mozilla ANY-LLM Integration](../adr/ADR-033-any-llm-integration.md) ⭐
- [ANY-LLM Implementation Guide](../architecture/ANY_LLM_IMPLEMENTATION_GUIDE.md)
- [ADR-032: Multi-Cloud Execution Strategy](../adr/ADR-032-multi-cloud-execution-strategy.md) (superseded by ADR-033)
- [Multi-Cloud Evaluation](../architecture/MULTI_CLOUD_EVALUATION.md)
- [Sprint 22 Test Execution Report](../sprint-22/SPRINT_22_TEST_EXECUTION_REPORT.md)

### External Resources
- Mozilla ANY-LLM Docs: https://mozilla-ai.github.io/any-llm/
- Mozilla ANY-LLM GitHub: https://github.com/mozilla-ai/any-llm (1.3k stars)
- ANY-LLM License: Apache 2.0

---

**Document Version:** 2.0 (Revised with ANY-LLM approach)
**Last Updated:** 2025-11-11
**Status:** 📋 AWAITING APPROVAL
**Approvers:** Klaus Pommer (Project Lead), CFO (Budget $200/month), CTO (Architecture)
