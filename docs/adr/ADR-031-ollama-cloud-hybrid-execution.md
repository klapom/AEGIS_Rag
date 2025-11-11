# ADR-031: Ollama Cloud Hybrid Execution Strategy

**Status:** 🔬 PROPOSED (2025-11-11)
**Deciders:** Project Lead (Klaus Pommer), Backend Team
**Date:** 2025-11-11
**Sprint:** Sprint 23 (Feature 23.4)

---

## Context and Problem Statement

### Current Architecture

AegisRAG currently runs **all LLM operations locally** using Ollama:

**Models in Use:**
- **Generation:** llama3.2:3b (query routing), llama3.2:8b (answer generation)
- **Extraction:** gemma-3-4b-it-Q8_0 (entity/relation extraction)
- **Vision:** llava:7b-v1.6-mistral-q2_K (VLM for document understanding)
- **Embeddings:** BGE-M3 (1024-dim, multilingual) - Local & cost-free

**Resource Constraints:**
- Docling CUDA container requires **6GB VRAM** (limits parallelism)
- GPU-intensive operations (extraction, VLM) slow on consumer-grade hardware
- Larger models (70B+) not feasible locally for quality-sensitive tasks
- Local GPU contention between Docling (OCR) and LLM inference

### Problem

1. **Quality vs Performance Tradeoff:**
   - Smaller models (3B-8B) run fast locally but have limited reasoning capacity
   - Larger models (70B+) provide better extraction quality but don't fit in local VRAM

2. **Resource Contention:**
   - Docling container monopolizes GPU during document ingestion
   - Cannot parallelize ingestion + extraction/generation

3. **Scalability Limitations:**
   - Single-machine architecture limits throughput
   - Cannot handle batch processing of 100+ documents efficiently

4. **Cost of Local GPU:**
   - Amortized cost of NVIDIA GPU (RTX 4090): ~$1,600
   - Power consumption: ~450W under load (~$30/month electricity)

### Opportunity: Ollama Cloud

Ollama recently launched [cloud-hosted models](https://docs.ollama.com/cloud) with:
- **Large models available:** llama3-70b, mixtral-8x7b, etc.
- **Pay-per-use pricing:** No upfront GPU cost
- **Scalability:** Parallelize requests across cloud infrastructure
- **API-based access:** Standard REST API (similar to local Ollama)

**Key Question:**
> How can we leverage Ollama Cloud for GPU-intensive operations while keeping embeddings, retrieval, and storage local?

---

## Decision Drivers

### Technical Drivers
1. **Extraction Quality:** Larger cloud models (70B+) improve entity/relation extraction accuracy
2. **Local GPU Relief:** Offload extraction/generation to cloud, free local GPU for Docling OCR
3. **Scalability:** Handle batch processing (100+ documents) via cloud parallelization
4. **Latency:** Balance cloud network latency (~200-500ms) vs local inference time

### Business Drivers
1. **Cost Optimization:** Pay-per-use vs amortized local GPU cost
2. **Operational Simplicity:** No GPU maintenance, driver updates, CUDA version conflicts
3. **Quality Improvement:** Better extraction → better knowledge graph → better answers

### Risk Drivers
1. **Cloud Dependency:** Reliance on Ollama Cloud availability
2. **Data Privacy:** Sensitive documents sent to cloud (GDPR, compliance concerns)
3. **Cost Control:** Risk of runaway costs without budget limits
4. **Network Latency:** Cloud adds network round-trip time

---

## Considered Options

### Option 1: 100% Local Execution (Status Quo)
**Description:** Keep all LLM operations local using current Ollama setup.

**Pros:**
- ✅ No cloud dependency
- ✅ No data leaves local infrastructure (privacy)
- ✅ No recurring cloud costs
- ✅ Low latency (no network overhead)

**Cons:**
- ❌ Limited model size (max 8B locally)
- ❌ GPU resource contention (Docling vs LLM)
- ❌ Poor scalability (single-machine bottleneck)
- ❌ Lower extraction quality with smaller models

**Cost Analysis:**
- One-time: $1,600 (GPU)
- Monthly: $30 (electricity)
- **Total Year 1:** $1,960

---

### Option 2: 100% Cloud Execution
**Description:** Move all LLM operations to Ollama Cloud.

**Pros:**
- ✅ Access to largest models (70B+)
- ✅ Unlimited scalability
- ✅ No local GPU needed
- ✅ Highest extraction quality

**Cons:**
- ❌ High cloud costs for all operations
- ❌ All data sent to cloud (privacy risk)
- ❌ Network latency for every request
- ❌ Full dependency on cloud availability

**Cost Analysis (Estimated):**
Assumptions:
- 1,000 documents/month × 50 pages = 50,000 pages
- Extraction: 50,000 pages × 1,000 tokens/page = 50M tokens
- Generation: 10,000 queries × 500 tokens = 5M tokens
- **Total:** 55M tokens/month

Estimated pricing (if $0.001/1k tokens):
- Extraction: 50M × $0.001/1k = **$50/month**
- Generation: 5M × $0.001/1k = **$5/month**
- **Total:** **$55/month** ($660/year)

**Verdict:** Lower cost than local GPU in Year 1, but ongoing expense.

---

### Option 3: Hybrid Execution with ExecutionProxy (Proposed) ⭐
**Description:** Implement intelligent routing between local and cloud execution.

**Architecture:**
```
┌─────────────────────────────────────────────┐
│           User Query / Document             │
└───────────────┬─────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────┐
│         ExecutionProxy                        │
│  (Decision Logic: Local or Cloud?)            │
└─────────┬───────────────────────┬─────────────┘
          │                       │
    [Local]                   [Cloud]
          │                       │
          ▼                       ▼
┌──────────────────┐    ┌──────────────────────┐
│  Local Ollama    │    │   Ollama Cloud API   │
│  - Embeddings    │    │   - Extraction (70B) │
│  - Simple Gen    │    │   - Complex Gen      │
│  - Fallback      │    │   - VLM (13B)        │
└──────────────────┘    └──────────────────────┘
          │                       │
          └───────────┬───────────┘
                      ▼
            ┌──────────────────────┐
            │  Result Integration  │
            │  (Store in KG/DB)    │
            └──────────────────────┘
```

**Decision Logic:**
```python
def should_use_cloud(task: LLMTask) -> bool:
    """Decide whether to execute task on cloud or locally."""

    # 1. Data Privacy: Never send sensitive data to cloud
    if task.contains_pii or task.classification == "confidential":
        return False

    # 2. Model Size: Large models only available in cloud
    if task.required_model_size_gb > 10:
        return True

    # 3. Quality Requirement: Use cloud for high-quality extraction
    if task.type == "extraction" and task.complexity == "high":
        return True

    # 4. Local GPU Availability: Offload if local GPU busy
    if get_local_gpu_utilization() > 80%:
        return True

    # 5. Cost Budget: Fallback to local if budget exceeded
    if cost_tracker.monthly_cost_usd > cost_budget:
        return False

    # 6. Latency Requirement: Prefer local for real-time queries
    if task.latency_requirement_ms < 500:
        return False

    # 7. Batch Processing: Use cloud for large batches
    if task.batch_size > 10:
        return True

    # Default: Local (cost-optimized)
    return False
```

**Routing Strategy Examples:**

| Task | Model | Local/Cloud | Reason |
|------|-------|-------------|--------|
| **Embeddings (BGE-M3)** | 1024-dim | Local | Fast, cost-free, no cloud benefit |
| **Simple Query (Chat)** | llama3.2:3b | Local | Low latency, small model |
| **Complex Reasoning** | llama3-70b | Cloud | Quality > latency |
| **Entity Extraction (Simple)** | gemma-3-4b | Local | Good enough for simple docs |
| **Entity Extraction (Complex)** | llama3-70b | Cloud | Large model improves accuracy |
| **VLM (Document Understanding)** | llava-13b | Cloud | Larger model, GPU relief |
| **Batch Extraction (100 docs)** | llama3-70b | Cloud | Parallel processing |

**Pros:**
- ✅ **Optimal Cost:** Use cloud only when needed
- ✅ **Quality:** Access to large models for complex tasks
- ✅ **Flexibility:** Adapt to workload (batch vs real-time)
- ✅ **Resilience:** Fallback to local if cloud unavailable
- ✅ **Privacy:** Keep sensitive data local

**Cons:**
- ⚠️ **Complexity:** Requires ExecutionProxy implementation
- ⚠️ **Monitoring:** Need to track cloud usage and costs
- ⚠️ **Network Latency:** Cloud adds 200-500ms overhead
- ⚠️ **Dual Maintenance:** Must maintain both local and cloud configs

**Cost Analysis (Estimated):**
Assumptions (Hybrid Strategy):
- **Local:** Embeddings (100%), simple queries (70%), fallback (10%)
- **Cloud:** Complex extraction (30%), batch processing (20%), VLM (10%)

Estimated cloud usage:
- Extraction (30% of 50M tokens): 15M tokens
- Generation (20% of 5M tokens): 1M tokens
- **Total:** 16M tokens/month

Estimated pricing:
- 16M × $0.001/1k = **$16/month** ($192/year)
- Plus local GPU: $30/month (electricity)
- **Total Year 1:** $1,600 (GPU) + $192 (cloud) + $360 (electricity) = **$2,152**

**Break-Even Analysis:**
- **Year 1:** Hybrid ($2,152) > 100% Local ($1,960) → Hybrid slightly more expensive
- **Year 2+:** Hybrid ($552/year) < 100% Local ($360/year electricity only) if GPU amortized
- **Quality Improvement:** Hard to quantify, but estimated **+15-20% extraction accuracy** with 70B model

---

### Option 4: Hybrid with Caching Layer
**Description:** Same as Option 3, but add caching for repeated queries/extractions.

**Additional Component:**
- Redis cache for LLM responses (TTL: 24 hours)
- Cache key: hash(prompt + model + params)
- Reduces cloud costs by ~30-40% for repeated queries

**Cost Analysis:**
- Same as Option 3, but cloud usage reduced to ~11M tokens/month
- **Estimated:** $11/month cloud ($132/year)
- **Total Year 1:** $1,600 + $132 + $360 = **$2,092**

**Pros:**
- ✅ All benefits of Option 3
- ✅ Lower cloud costs due to caching

**Cons:**
- ⚠️ All drawbacks of Option 3
- ⚠️ Redis memory overhead (estimated 2GB for cache)

---

## Decision Outcome

**Chosen option:** **Option 3 (Hybrid Execution with ExecutionProxy)** ⭐

### Rationale

1. **Quality Improvement:** Access to 70B models for complex extraction tasks improves knowledge graph quality by estimated **+15-20%**.

2. **Cost Optimization:** Hybrid approach uses cloud only when needed (~30% of operations), keeping costs manageable (~$16/month cloud).

3. **Flexibility:** Can adjust decision logic based on workload, budget, and quality requirements.

4. **Resilience:** Fallback to local execution if cloud unavailable ensures system reliability.

5. **Privacy Control:** Sensitive data stays local; only anonymized or non-sensitive data sent to cloud.

### Implementation Plan (Sprint 23)

**Phase 1: Design & ADR (Week 2)**
- ✅ Create ADR-031 (this document)
- Document architecture and decision logic
- Cost analysis and break-even calculation

**Phase 2: ExecutionProxy POC (Week 3-4)**
- Implement `ExecutionProxy` class with decision logic
- Integrate with existing extraction pipeline
- Add cost tracking and budget enforcement
- Implement fallback logic

**Phase 3: Testing & Benchmarking (Week 4)**
- Unit tests for decision logic (20 tests)
- Integration tests for cloud execution (10 tests)
- Benchmark latency (local vs cloud)
- Measure extraction quality improvement
- Cost analysis with real usage data

**Phase 4: Production Rollout (Sprint 24)**
- Gradual rollout (10% → 50% → 100% of extraction tasks)
- Monitor costs, latency, quality metrics
- Adjust decision thresholds based on data

---

## Consequences

### Positive Consequences

1. **Quality Improvement:**
   - Larger models (70B) improve entity/relation extraction accuracy
   - Better extraction → better knowledge graph → better answers
   - Estimated **+15-20% extraction accuracy** (to be validated)

2. **Local GPU Relief:**
   - Docling container can run without LLM contention
   - Faster document ingestion (no GPU sharing)

3. **Scalability:**
   - Cloud handles batch processing (100+ documents in parallel)
   - No local hardware bottleneck

4. **Cost Predictability:**
   - Cloud costs scale with usage (pay-per-use)
   - Budget limits prevent runaway costs

5. **Operational Flexibility:**
   - Can adjust cloud/local ratio based on budget and quality needs
   - No need to upgrade local GPU immediately

### Negative Consequences

1. **Increased Complexity:**
   - ExecutionProxy adds new component to maintain
   - Decision logic requires tuning and monitoring

2. **Cloud Dependency:**
   - Partial reliance on Ollama Cloud availability
   - Mitigation: Fallback to local execution

3. **Network Latency:**
   - Cloud adds ~200-500ms per request
   - Acceptable for batch processing, not for real-time queries

4. **Cost Monitoring Required:**
   - Must track cloud usage daily/monthly
   - Risk of unexpected costs if decision logic buggy

5. **Data Privacy Concerns:**
   - Some data sent to cloud (must be anonymized/non-sensitive)
   - Mitigation: Classification-based routing (sensitive data stays local)

---

## Implementation Details

### Component Structure

```
src/components/execution/
├── __init__.py
├── execution_proxy.py          # Main orchestration logic
├── decision_strategy.py         # Decision strategies (cost, quality, latency)
├── ollama_cloud_client.py      # Client for Ollama Cloud API
├── cost_tracker.py              # Budget tracking and alerts
└── models.py                    # LLMTask, LLMResult, DecisionResult

config/
├── ollama_cloud.yaml            # Cloud configuration
└── decision_thresholds.yaml     # Decision logic thresholds
```

### Configuration Example

```yaml
# config/ollama_cloud.yaml
ollama_cloud:
  enabled: true
  api_key: ${OLLAMA_CLOUD_API_KEY}  # From environment
  base_url: "https://cloud.ollama.ai"

  # Cloud models (larger than local)
  models:
    extraction_cloud: "llama3-70b-instruct"
    generation_cloud: "llama3-8b-instruct"
    vision_cloud: "llava-13b"

  # Cost limits (enforced by CostTracker)
  cost_limits:
    daily_budget_usd: 5.0
    monthly_budget_usd: 100.0
    alert_threshold_pct: 80  # Alert at 80% of budget

  # Decision strategy: cost_optimized, quality_optimized, hybrid
  decision_strategy: "hybrid"

  # Fallback behavior
  fallback:
    on_budget_exceeded: "local"
    on_cloud_unavailable: "local"
    on_rate_limit: "queue"  # queue or local

  # Cache settings (optional, for Option 4)
  cache:
    enabled: false
    ttl_seconds: 86400  # 24 hours
    max_size_mb: 2048
```

### Decision Thresholds

```yaml
# config/decision_thresholds.yaml
decision_thresholds:
  # Model size threshold (GB)
  model_size_gb: 10

  # Quality requirement
  quality_threshold:
    high_complexity: "cloud"  # Use cloud for high-complexity tasks
    medium_complexity: "local"
    low_complexity: "local"

  # GPU utilization threshold (%)
  gpu_utilization_pct: 80

  # Latency requirement (ms)
  latency_threshold_ms: 500

  # Batch size threshold
  batch_size_threshold: 10

  # Data classification
  sensitive_data: "local"  # PII, confidential always local
  public_data: "cloud_allowed"
```

### Monitoring Metrics

**Cost Tracking:**
- `ollama_cloud_cost_usd_total` (counter): Total cost since deployment
- `ollama_cloud_cost_usd_daily` (gauge): Daily cost
- `ollama_cloud_cost_usd_monthly` (gauge): Monthly cost
- `ollama_cloud_budget_remaining_pct` (gauge): % of budget remaining

**Usage Tracking:**
- `ollama_cloud_requests_total` (counter): Total cloud requests
- `ollama_cloud_tokens_total` (counter): Total tokens processed
- `ollama_execution_local_vs_cloud_ratio` (gauge): % local vs cloud

**Quality Tracking:**
- `extraction_accuracy_local` (gauge): Accuracy with local model
- `extraction_accuracy_cloud` (gauge): Accuracy with cloud model
- `extraction_quality_improvement_pct` (gauge): Cloud vs local

**Latency Tracking:**
- `llm_execution_latency_seconds{location="local"}` (histogram)
- `llm_execution_latency_seconds{location="cloud"}` (histogram)

---

## Validation Plan

### Phase 1: POC Validation (Sprint 23, Week 4)

**Test 1: Latency Benchmark**
- Execute 100 extraction tasks (local vs cloud)
- Measure p50, p95, p99 latency
- **Success:** Cloud latency <2s p95

**Test 2: Quality Benchmark**
- Extract entities/relations from 50 test documents
- Compare local (gemma-3-4b) vs cloud (llama3-70b)
- Manual evaluation: precision, recall, F1 score
- **Success:** Cloud model shows ≥+10% F1 improvement

**Test 3: Cost Analysis**
- Run 1,000 extraction tasks through ExecutionProxy
- Track cloud usage in tokens
- Calculate actual cost per task
- **Success:** Actual cost <$0.02/task ($20/1,000 tasks)

**Test 4: Fallback Behavior**
- Simulate cloud unavailability (mock API failure)
- Verify fallback to local execution
- **Success:** No request fails due to cloud unavailability

### Phase 2: Production Validation (Sprint 24)

**Gradual Rollout:**
- Week 1: 10% of extraction tasks use cloud
- Week 2: 50% of extraction tasks use cloud
- Week 3: 100% of extraction tasks use cloud (if metrics acceptable)

**Acceptance Criteria:**
- ✅ Monthly cloud cost <$100
- ✅ Extraction quality improvement ≥+10%
- ✅ No increase in user-facing latency (p95 <1s)
- ✅ Zero failed requests due to cloud issues (100% fallback success)

---

## Alternatives Not Chosen

### Why Not 100% Cloud? (Option 2)
- **Cost:** $55/month ($660/year) ongoing, higher than hybrid
- **Privacy:** All data sent to cloud (GDPR concerns)
- **Latency:** Every request has network overhead (200-500ms)
- **Dependency:** Complete reliance on cloud availability

### Why Not Stay 100% Local? (Option 1)
- **Quality:** Limited to 8B models, lower extraction accuracy
- **Scalability:** Single-machine bottleneck for batch processing
- **GPU Contention:** Docling vs LLM competition for GPU

### Why Not Add Caching? (Option 4)
- **Complexity:** Additional Redis component
- **Memory Overhead:** 2GB+ for cache
- **Benefit:** Only ~30% cost reduction (marginal)
- **Decision:** Can add caching later if costs exceed budget

---

## References

1. **Ollama Cloud Documentation:** https://docs.ollama.com/cloud
2. **ADR-027:** Docling CUDA Container Integration (Sprint 21)
3. **ADR-028:** Docling-First Hybrid Ingestion Strategy (Sprint 22)
4. **Sprint 23 Planning:** `docs/sprint-23/SPRINT_23_PLANNING.md`
5. **User-Provided Architecture Document:** Ollama Cloud Integration Proposal (2025-11-11)

---

## Appendix A: Cost Calculation Details

### Assumptions
- **Documents:** 1,000/month × 50 pages = 50,000 pages
- **Queries:** 10,000/month
- **Tokens per page:** ~1,000 (average PDF page)
- **Tokens per query:** ~500 (context + answer)

### Cloud Usage (Hybrid Strategy)
- **Extraction (30% in cloud):** 50,000 pages × 30% × 1,000 tokens = 15M tokens
- **Generation (20% in cloud):** 10,000 queries × 20% × 500 tokens = 1M tokens
- **Total:** 16M tokens/month

### Pricing Estimate
**Note:** Ollama Cloud pricing not yet publicly available (as of 2025-11-11).
Estimated pricing: **$0.001 per 1,000 tokens** (industry standard for 70B models).

- 16M tokens × $0.001/1k = **$16/month** ($192/year)

### Break-Even Analysis
- **Local GPU (amortized over 3 years):** $1,600 / 36 months = **$44/month**
- **Local electricity:** **$30/month**
- **Total Local:** **$74/month** (Year 1-3)

- **Hybrid (Cloud + Local electricity):** $16 + $30 = **$46/month** (Year 1+)

**Conclusion:** Hybrid is **$28/month cheaper** than pure local (when GPU amortized).

---

## Appendix B: Security Considerations

### Data Classification
```python
class DataClassification(Enum):
    PUBLIC = "public"              # Can be sent to cloud
    INTERNAL = "internal"          # Prefer local, cloud if anonymized
    CONFIDENTIAL = "confidential"  # Never send to cloud
    PII = "pii"                    # Never send to cloud (GDPR)
```

### Anonymization Strategy
Before sending data to cloud:
1. **PII Detection:** Scan for names, emails, phone numbers, addresses
2. **Redaction:** Replace PII with placeholders (`[NAME]`, `[EMAIL]`)
3. **Verification:** Log anonymized text for audit
4. **Transmission:** Send only anonymized text to cloud

### API Key Security
- **Storage:** Use Kubernetes Secrets (not environment variables in code)
- **Rotation:** Rotate API key every 90 days
- **Access Control:** Limit API key access to ExecutionProxy component only

### Audit Logging
Every cloud request must log:
- Request ID (for correlation)
- User ID (if applicable)
- Data classification (public, internal, confidential)
- Cloud model used
- Tokens consumed
- Cost incurred
- Timestamp

---

**ADR Status:** 🔬 PROPOSED
**Next Review:** Sprint 23 Kickoff (2025-11-12)
**Owner:** Backend Team (Klaus Pommer)
**Approval Required From:** Project Lead, Security Team
