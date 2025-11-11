# Sprint 23 Planning: Production Deployment & Ollama Cloud Integration

**Sprint:** Sprint 23 (2025-11-12+)
**Status:** 📋 PLANNED
**Previous Sprint:** Sprint 22 ✅ COMPLETE (Hybrid Approach - Critical Refactoring + Hybrid Ingestion)

---

## Sprint 23 Objectives

### Primary Goal: Production Deployment Readiness
Enable external user onboarding and production-grade infrastructure.

### Secondary Goal: Ollama Cloud Integration (Evaluation)
Evaluate and design hybrid local/cloud execution for GPU-intensive operations.

---

## Sprint 22 Completion Summary

### ✅ Completed Features
- **Phase 1: Critical Refactoring**
  - Removed deprecated unified_ingestion.py (275 lines)
  - API Security Hardening (Request ID, Error Responses, Rate Limiting, JWT Auth)
  - 80+ tests (100% pass rate)

- **Phase 2: Hybrid Ingestion**
  - FormatRouter for 30 document formats (39 tests, 100% pass)
  - LlamaIndex fallback parser (18 tests, 100% pass)
  - Updated /upload endpoint with intelligent routing
  - Comprehensive documentation (1,500+ lines)

### 📊 Test Results
- **149 total tests** executed
- **96% pass rate** (145/149)
- **100% pass rate** on core functionality (routing, security, parsing)
- 4 expected failures due to RAM constraints (not code bugs)

### 🚀 Production Ready
- 30-format support validated
- Complete API security stack
- Comprehensive documentation
- Standardized error handling

---

## Sprint 23 Features

### Phase 1: Production Infrastructure (Priority 1)

#### Feature 23.1: Kubernetes Deployment ⭐
**Owner:** infrastructure-agent
**Estimated Effort:** 3-4 days
**Dependencies:** Docker Compose working

**Deliverables:**
1. **Helm Chart** (`k8s/aegis-rag-helm/`)
   - `Chart.yaml` (metadata, version, dependencies)
   - `values.yaml` (production configuration)
   - `values-dev.yaml` (development configuration)
   - `templates/deployment.yaml` (API, Docling container)
   - `templates/service.yaml` (ClusterIP, LoadBalancer)
   - `templates/ingress.yaml` (Nginx Ingress)
   - `templates/configmap.yaml` (environment config)
   - `templates/secret.yaml` (API keys, credentials)
   - `templates/pvc.yaml` (persistent storage for documents)
   - `templates/hpa.yaml` (horizontal pod autoscaler)

2. **StatefulSet for Databases**
   - Qdrant (vector storage)
   - Neo4j (graph storage)
   - Redis (memory cache)

3. **Resource Limits**
   - CPU: 4 cores per pod (API), 2 cores (Docling)
   - Memory: 8GB per pod (API), 4GB (Docling)
   - GPU: 1x NVIDIA GPU for Docling (CUDA 12.4+)

4. **Health Checks**
   - Liveness probe: `/health` endpoint (every 30s)
   - Readiness probe: `/health/ready` (checks DB connections)
   - Startup probe: 60s timeout for Docling container

5. **Secrets Management**
   - Kubernetes Secrets for API keys
   - External Secrets Operator for Vault integration
   - Sealed Secrets for GitOps workflow

**Testing:**
- Deploy to local Minikube cluster
- Deploy to staging environment (DigitalOcean Kubernetes)
- Load testing with 100 concurrent users
- Verify auto-scaling (HPA triggers at 70% CPU)

**Success Criteria:**
- ✅ Helm chart deploys without errors
- ✅ All pods reach "Running" state within 2 minutes
- ✅ API responds to /health with 200 OK
- ✅ Upload endpoint accepts 30 formats
- ✅ Auto-scaling works under load

---

#### Feature 23.2: Monitoring & Observability ⭐
**Owner:** infrastructure-agent
**Estimated Effort:** 2-3 days
**Dependencies:** Feature 23.1 (Kubernetes deployment)

**Deliverables:**
1. **Prometheus Setup**
   - `k8s/monitoring/prometheus.yaml`
   - Custom metrics: request_duration_seconds, error_rate, ingestion_time_seconds
   - ServiceMonitor for auto-discovery

2. **Grafana Dashboards**
   - `k8s/monitoring/grafana-dashboards/`
   - Dashboard 1: API Performance (latency, throughput, error rate)
   - Dashboard 2: Ingestion Pipeline (format distribution, parsing time, success rate)
   - Dashboard 3: Database Health (Qdrant, Neo4j, Redis connection pools)
   - Dashboard 4: Request ID Correlation (error tracking by request ID)

3. **Alerting Rules**
   - `k8s/monitoring/alerts.yaml`
   - Critical: API error rate >5% for 3 minutes
   - Warning: p95 latency >1000ms for 5 minutes
   - Info: Docling container restart

4. **Structured Logging**
   - Fluentd/Fluent Bit for log aggregation
   - Elasticsearch for log storage
   - Kibana for log visualization
   - Request ID correlation in all logs

**Testing:**
- Trigger alerts by simulating high error rate
- Verify request ID appears in logs and Grafana
- Load test and observe metrics in real-time

**Success Criteria:**
- ✅ Prometheus scrapes metrics every 15s
- ✅ Grafana dashboards show real-time data
- ✅ Alerts fire correctly (tested with simulated errors)
- ✅ Request IDs correlate logs across services

---

#### Feature 23.3: CI/CD Pipeline Enhancements ⭐
**Owner:** infrastructure-agent
**Estimated Effort:** 2 days
**Dependencies:** Feature 23.1 (Kubernetes)

**Deliverables:**
1. **GitHub Actions Workflows**
   - `.github/workflows/deploy-production.yml`
   - `.github/workflows/deploy-staging.yml`
   - `.github/workflows/rollback.yml`

2. **Deployment Strategy**
   - Blue-Green deployment (zero downtime)
   - Canary releases (10% → 50% → 100%)
   - Automatic rollback on health check failure

3. **Quality Gates**
   - All tests must pass (unit, integration, E2E)
   - Code coverage >80%
   - Security scan (Bandit, Safety) must pass
   - Docker image scan (Trivy) must pass

4. **Smoke Tests**
   - Post-deployment smoke tests
   - `/health`, `/formats`, `/auth/login` endpoints
   - Fail deployment if smoke tests fail

**Testing:**
- Simulate failed deployment (trigger rollback)
- Deploy to staging, verify canary release
- Test blue-green switch

**Success Criteria:**
- ✅ Deployment completes in <5 minutes
- ✅ Zero downtime during deployment
- ✅ Rollback works automatically on failure
- ✅ Smoke tests catch broken deployments

---

### Phase 2: Ollama Cloud Integration (Evaluation) 🔬

#### Feature 23.4: Ollama Cloud Architecture Design (ADR-031)
**Owner:** backend-agent + documentation-agent
**Estimated Effort:** 2-3 days
**Dependencies:** None (design phase)

**Objective:**
Evaluate and design hybrid local/cloud execution strategy for GPU-intensive LLM operations.

**Background:**
Current architecture runs all LLM operations locally (Ollama):
- **Generation Models:** llama3.2:3b (query), llama3.2:8b (generation)
- **Extraction Model:** gemma-3-4b-it-Q8_0 (entity/relation extraction)
- **Vision Model:** llava:7b-v1.6-mistral-q2_K (VLM)
- **Embeddings:** BGE-M3 (local, cost-free)

**Problem:**
- GPU-intensive operations (extraction, VLM) slow on local hardware
- Docling container requires 6GB VRAM (limits parallelism)
- Extraction quality improves with larger models (not feasible locally)

**Proposed Solution (from user document):**
Hybrid architecture with **Execution Proxy** that routes tasks:
- **Local:** Ingestion, embeddings, retrieval, post-processing
- **Cloud:** GPU-intensive extraction, generation, VLM (via Ollama Cloud API)

**Deliverables:**

1. **ADR-031: Ollama Cloud Hybrid Execution**
   - `docs/adr/ADR-031-ollama-cloud-hybrid-execution.md`
   - **Status:** Proposed
   - **Context:** GPU resource constraints, quality vs cost tradeoff
   - **Decision:** Implement ExecutionProxy with decision logic
   - **Consequences:** Reduced local GPU load, cloud costs, network latency

2. **Architecture Design Document**
   - `docs/architecture/OLLAMA_CLOUD_INTEGRATION.md`
   - Component diagram (as provided in user document)
   - Data flow diagram (8 steps)
   - Decision criteria (model size, latency, cost, quality)
   - Security considerations (API key, data privacy)

3. **Cost Analysis**
   - Ollama Cloud pricing model (if available)
   - Estimated monthly costs for:
     - 1,000 documents/month
     - 10,000 queries/month
     - Extraction: 50,000 entities/month
   - Comparison: Local GPU (amortized) vs Cloud

4. **Proof of Concept (POC) Plan**
   - Task 1: Test Ollama Cloud API access (authentication)
   - Task 2: Implement simple ExecutionProxy
   - Task 3: Benchmark latency (local vs cloud)
   - Task 4: Validate extraction quality (local vs cloud model)
   - Task 5: Measure cost per 1,000 requests

**Decision Criteria for Cloud Execution:**
```python
# Pseudocode from user document
def should_use_cloud(task: Task) -> bool:
    # Model size threshold
    if task.model_size_gb > 10:
        return True

    # Quality requirement
    if task.quality_requirement == "high" and task.complexity == "complex":
        return True

    # Local GPU availability
    if local_gpu_utilization > 80%:
        return True

    # Cost budget
    if current_month_cost < cost_budget:
        return True

    # Latency requirement (prefer local for low latency)
    if task.latency_requirement_ms < 500:
        return False

    return False  # Default: local execution
```

**Testing:**
- Evaluate decision logic with sample tasks
- Cost simulation (1,000 documents, 10,000 queries)
- Latency benchmarking (local vs cloud)

**Success Criteria:**
- ✅ ADR-031 approved and documented
- ✅ Architecture design reviewed by team
- ✅ Cost analysis shows acceptable ROI
- ✅ POC plan defined with clear milestones

---

#### Feature 23.5: ExecutionProxy Implementation (POC)
**Owner:** backend-agent
**Estimated Effort:** 3-4 days
**Dependencies:** Feature 23.4 (ADR-031 approved)

**Objective:**
Implement proof-of-concept for hybrid local/cloud LLM execution.

**Deliverables:**

1. **ExecutionProxy Component**
   - `src/components/execution/execution_proxy.py`
   ```python
   class ExecutionProxy:
       """Routes LLM tasks between local Ollama and Ollama Cloud."""

       def __init__(
           self,
           local_ollama_url: str,
           cloud_api_key: str,
           cost_budget_usd: float,
           decision_strategy: DecisionStrategy
       ):
           self.local_client = OllamaClient(local_ollama_url)
           self.cloud_client = OllamaCloudClient(api_key=cloud_api_key)
           self.cost_tracker = CostTracker(budget=cost_budget_usd)
           self.strategy = decision_strategy

       async def execute(self, task: LLMTask) -> LLMResult:
           """Execute LLM task (local or cloud based on strategy)."""
           decision = self.strategy.decide(task, self.cost_tracker)

           if decision.use_cloud:
               logger.info("Executing on Ollama Cloud", task=task.id, model=decision.model)
               result = await self.cloud_client.execute(task)
               self.cost_tracker.record(result.cost_usd)
           else:
               logger.info("Executing locally", task=task.id, model=decision.model)
               result = await self.local_client.execute(task)

           return result
   ```

2. **Decision Strategies**
   - `src/components/execution/strategies.py`
   - `CostOptimizedStrategy`: Minimize cost (prefer local)
   - `QualityOptimizedStrategy`: Maximize quality (prefer cloud for complex tasks)
   - `LatencyOptimizedStrategy`: Minimize latency (prefer local)
   - `HybridStrategy`: Balance cost, quality, latency

3. **Ollama Cloud Client**
   - `src/components/execution/ollama_cloud_client.py`
   ```python
   class OllamaCloudClient:
       """Client for Ollama Cloud API."""

       def __init__(self, api_key: str, base_url: str = "https://cloud.ollama.ai"):
           self.api_key = api_key
           self.base_url = base_url
           self.session = httpx.AsyncClient()

       async def execute(self, task: LLMTask) -> LLMResult:
           """Execute LLM task on Ollama Cloud."""
           response = await self.session.post(
               f"{self.base_url}/api/generate",
               headers={"Authorization": f"Bearer {self.api_key}"},
               json={
                   "model": task.cloud_model,
                   "prompt": task.prompt,
                   "stream": False
               }
           )
           # Parse response, track cost
           return LLMResult(...)
   ```

4. **Cost Tracking**
   - `src/components/execution/cost_tracker.py`
   - Track usage per day/month
   - Alert when budget threshold reached (80%, 90%, 100%)
   - Fallback to local when budget exceeded

5. **Integration with Existing Components**
   - **Extraction:** `src/components/graph_rag/three_phase_extraction.py`
     - Use ExecutionProxy for entity/relation extraction
     - Prefer cloud for large documents (>10 pages)
   - **Generation:** `src/agents/generation.py`
     - Use ExecutionProxy for answer generation
     - Prefer local for simple queries, cloud for complex reasoning

**Configuration:**
```yaml
# config/ollama_cloud.yaml
ollama_cloud:
  enabled: true
  api_key: ${OLLAMA_CLOUD_API_KEY}
  base_url: "https://cloud.ollama.ai"

  models:
    extraction_cloud: "llama3-70b-instruct"  # Large model for quality
    generation_cloud: "llama3-8b-instruct"   # Medium model
    vision_cloud: "llava-13b"                # Vision model

  cost_limits:
    daily_budget_usd: 5.0
    monthly_budget_usd: 100.0
    alert_threshold_pct: 80

  decision_strategy: "hybrid"  # cost_optimized, quality_optimized, latency_optimized, hybrid

  fallback:
    on_budget_exceeded: "local"
    on_cloud_unavailable: "local"
    on_rate_limit: "queue"  # queue or local
```

**Testing:**
1. **Unit Tests** (20 tests)
   - Test decision strategies with sample tasks
   - Test cost tracking (budget enforcement)
   - Test fallback logic (cloud unavailable)
   - Mock Ollama Cloud API responses

2. **Integration Tests** (10 tests)
   - End-to-end extraction with cloud model
   - End-to-end generation with cloud model
   - Cost tracking across multiple requests
   - Fallback to local when cloud fails

3. **Benchmarking**
   - Latency: Local vs Cloud (100 requests)
   - Quality: Extraction accuracy (local vs cloud model)
   - Cost: Actual cost per 1,000 requests

**Success Criteria:**
- ✅ ExecutionProxy routes tasks correctly (100% test pass)
- ✅ Cost tracking enforces budget limits
- ✅ Fallback to local works when cloud unavailable
- ✅ Latency acceptable (<2s for cloud requests)
- ✅ Quality improvement measurable (cloud vs local)

---

### Phase 3: User Onboarding & Documentation

#### Feature 23.6: User Onboarding Documentation
**Owner:** documentation-agent
**Estimated Effort:** 2 days
**Dependencies:** Features 23.1, 23.2, 23.3 (infrastructure deployed)

**Deliverables:**
1. **Quick Start Guide** (`docs/guides/QUICK_START.md`)
   - Install requirements (Docker, Kubernetes, GPU drivers)
   - Deploy with Helm (5-minute setup)
   - Upload first document
   - Query the knowledge graph

2. **API Client Examples** (`docs/examples/`)
   - Python client (`python_client_example.py`)
   - JavaScript client (`javascript_client_example.js`)
   - cURL examples (`curl_examples.sh`)

3. **Troubleshooting Guide** (`docs/guides/TROUBLESHOOTING.md`)
   - Common errors and solutions
   - Debug logging
   - Performance tuning

4. **Video Tutorials** (optional)
   - 5-minute deployment walkthrough
   - 10-minute API usage demo

**Success Criteria:**
- ✅ External user can deploy in <10 minutes
- ✅ All examples work without modification
- ✅ Troubleshooting guide covers 90% of issues

---

#### Feature 23.7: API Rate Limiting Enhancements
**Owner:** api-agent
**Estimated Effort:** 1 day
**Dependencies:** Feature 22.2.3 (rate limiting implemented)

**Deliverables:**
1. **Tiered Rate Limits**
   - Free tier: 10 requests/minute, 100 requests/day
   - Pro tier: 100 requests/minute, 10,000 requests/day
   - Enterprise tier: Unlimited (custom contract)

2. **Rate Limit Headers**
   - `X-RateLimit-Limit`: Total allowed
   - `X-RateLimit-Remaining`: Remaining requests
   - `X-RateLimit-Reset`: Reset timestamp

3. **API Key Management**
   - Generate API keys per user
   - Revoke API keys
   - Track usage per API key

**Testing:**
- Test rate limit enforcement per tier
- Verify headers in responses
- Test API key revocation

**Success Criteria:**
- ✅ Tiered rate limits enforced correctly
- ✅ Rate limit headers present in all responses
- ✅ API key management UI (basic)

---

## Sprint 23 Timeline (Estimated)

| Week | Features | Owner | Status |
|------|----------|-------|--------|
| **Week 1** | Feature 23.1 (Kubernetes Deployment) | infrastructure-agent | Planned |
| **Week 1-2** | Feature 23.2 (Monitoring) | infrastructure-agent | Planned |
| **Week 2** | Feature 23.3 (CI/CD Enhancements) | infrastructure-agent | Planned |
| **Week 2-3** | Feature 23.4 (Ollama Cloud Design) | backend-agent + docs | Planned |
| **Week 3-4** | Feature 23.5 (ExecutionProxy POC) | backend-agent | Planned |
| **Week 4** | Feature 23.6 (User Onboarding Docs) | documentation-agent | Planned |
| **Week 4** | Feature 23.7 (Rate Limiting Enhancements) | api-agent | Planned |

**Total Sprint Duration:** 4 weeks (2025-11-12 to 2025-12-10)

---

## Success Criteria for Sprint 23

### Production Readiness ✅
- [ ] Kubernetes deployment with Helm chart
- [ ] Monitoring (Prometheus + Grafana) operational
- [ ] CI/CD pipeline with blue-green deployment
- [ ] External users can deploy in <10 minutes
- [ ] API rate limiting with tiered plans

### Ollama Cloud Integration (POC) ✅
- [ ] ADR-031 approved and documented
- [ ] Architecture design reviewed
- [ ] ExecutionProxy implemented (POC)
- [ ] Cost analysis shows acceptable ROI (<$100/month for 10k queries)
- [ ] Quality improvement measurable (cloud vs local)

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Ollama Cloud API not available** | High | Medium | Use POC to validate API access early |
| **Cloud costs too high** | High | Low | Set strict budget limits, fallback to local |
| **Kubernetes complexity** | Medium | Medium | Start with Minikube, use managed K8s (DigitalOcean) |
| **Network latency to cloud** | Medium | Low | Measure latency in POC, optimize batching |
| **GPU unavailable for Docling** | High | Low | Document GPU requirements, test on cloud GPU |

---

## Dependencies

### External Dependencies
- Ollama Cloud API access (requires account, API key)
- Kubernetes cluster (local Minikube or cloud provider)
- GPU for Docling container (NVIDIA GPU with CUDA 12.4+)

### Internal Dependencies
- Sprint 22 features must be complete ✅
- All tests passing (96%+ pass rate) ✅
- Documentation up-to-date ✅

---

## Post-Sprint 23 Goals (Sprint 24+)

### Sprint 24: React Frontend Migration (ADR-029)
- Migrate from legacy frontend to React
- Implement drag-and-drop file upload (30 formats)
- Real-time query interface with streaming responses
- Knowledge graph visualization (D3.js, Cytoscape.js)

### Sprint 25: Advanced RAG Features
- Multi-hop reasoning with graph traversal
- Temporal memory with Graphiti (bi-temporal structure)
- MCP server for tool integration (anthropic/mcp)
- RAGAS evaluation framework

### Sprint 26: Enterprise Features
- Multi-tenancy with RBAC
- Audit logging with compliance reports
- Advanced analytics (query patterns, extraction quality)
- Export/import for knowledge graphs

---

## Next Actions (Immediate)

1. **Review this plan with team** (30 minutes)
   - Validate feature scope
   - Adjust timeline if needed
   - Assign owners

2. **Start Feature 23.4 (Ollama Cloud Design)** (Week 2)
   - Create ADR-031 draft
   - Analyze cost model
   - Design ExecutionProxy architecture

3. **Start Feature 23.1 (Kubernetes Deployment)** (Week 1)
   - Create Helm chart skeleton
   - Test deployment on Minikube
   - Document resource requirements

4. **Sprint 23 Kickoff Meeting** (2025-11-12)
   - Review Sprint 22 achievements
   - Assign Feature 23.1 to infrastructure-agent
   - Set up weekly standup (30 minutes)

---

**Document Status:** 📋 DRAFT (2025-11-11)
**Next Review:** Sprint 23 Kickoff (2025-11-12)
**Owner:** Project Lead (Klaus Pommer)
