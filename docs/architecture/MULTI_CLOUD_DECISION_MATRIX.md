# Multi-Cloud Execution Decision Matrix

**Document Type:** Decision Reference Guide
**Related ADR:** ADR-032 (Multi-Cloud Execution Strategy)
**Status:** 📋 REFERENCE (Sprint 23+)
**Date:** 2025-11-11

---

## Quick Reference: When to Use Which Provider?

### Three-Tier Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                  TIER 1: LOCAL OLLAMA                       │
│  Cost: FREE  •  Latency: 50-200ms  •  Quality: GOOD ★★★☆☆  │
│  Use: 70% of tasks  •  Always available (fallback)          │
└─────────────────────────────────────────────────────────────┘
                            ↑
                   (If budget exceeded)
                            │
┌─────────────────────────────────────────────────────────────┐
│              TIER 2: OLLAMA CLOUD                           │
│  Cost: $0.001/1k tokens  •  Latency: 200-500ms              │
│  Quality: BETTER ★★★★☆  •  Use: 20% of tasks                │
│  Best for: Standard extraction, batch processing            │
└─────────────────────────────────────────────────────────────┘
                            ↑
                   (If quality critical)
                            │
┌─────────────────────────────────────────────────────────────┐
│                  TIER 3: OPENAI API                         │
│  Cost: $0.015/1k tokens  •  Latency: 300-600ms              │
│  Quality: BEST ★★★★★  •  Use: 10% of tasks                  │
│  Best for: Legal docs, medical records, complex reasoning   │
└─────────────────────────────────────────────────────────────┘
```

---

## Decision Flowchart

```
                        ┌──────────────┐
                        │   New Task   │
                        └──────┬───────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Sensitive Data?     │
                    │ (PII, Confidential) │
                    └─────────┬───────────┘
                              │
                    ┌─────────┴─────────┐
                  YES│                 │NO
                    ▼                   ▼
          ┌──────────────┐    ┌─────────────────┐
          │ USE LOCAL    │    │ Budget Check    │
          │ (Security)   │    └────────┬────────┘
          └──────────────┘             │
                              ┌────────┴────────┐
                            YES│              │NO
                              ▼                 ▼
                    ┌──────────────┐  ┌─────────────────┐
                    │ USE LOCAL    │  │ Quality = Critical? │
                    │ (Budget)     │  └────────┬────────┘
                    └──────────────┘           │
                                    ┌──────────┴────────┐
                                  YES│                │NO
                                    ▼                  ▼
                          ┌──────────────┐  ┌─────────────────┐
                          │ USE OPENAI   │  │ Complexity High? │
                          │ (Quality)    │  └────────┬────────┘
                          └──────────────┘           │
                                          ┌──────────┴────────┐
                                        YES│                │NO
                                          ▼                  ▼
                                ┌──────────────┐  ┌─────────────┐
                                │ OLLAMA CLOUD │  │ USE LOCAL   │
                                │ (Performance)│  │ (Default)   │
                                └──────────────┘  └─────────────┘
```

---

## Task-Based Routing Examples

### Example 1: Simple User Query
**Input:** "What is the capital of France?"

**Task Characteristics:**
- Type: `generation`
- Complexity: `low`
- Quality Req: `medium`
- Data Classification: `public`
- Latency Req: `<500ms`

**Decision Logic:**
```python
task = LLMTask(
    task_type="generation",
    complexity="low",
    quality_requirement="medium",
    data_classification="public",
    latency_requirement_ms=500,
    model_local="llama3.2:3b",
    model_cloud="llama3-8b",
    model_openai="gpt-3.5-turbo"
)

decision = strategy.decide(task, cost_tracker)
# → Result: ExecutionLocation.LOCAL
# → Reason: "default_local" (simple query, low latency requirement)
```

**✅ Route to: LOCAL** (llama3.2:3b)
- **Cost:** $0
- **Latency:** ~100ms
- **Quality:** Sufficient for factual question

---

### Example 2: Standard Document Extraction
**Input:** Extract entities from a 20-page business report (PDF)

**Task Characteristics:**
- Type: `extraction`
- Complexity: `high`
- Quality Req: `high`
- Data Classification: `internal`
- Document Pages: 20

**Decision Logic:**
```python
task = LLMTask(
    task_type="extraction",
    complexity="high",
    quality_requirement="high",
    data_classification="internal",
    model_local="gemma-3-4b-it-Q8_0",
    model_cloud="llama3-70b-instruct",
    model_openai="gpt-4o"
)

decision = strategy.decide(task, cost_tracker)
# → Result: ExecutionLocation.OLLAMA_CLOUD
# → Reason: "high_quality_cost_effective"
```

**✅ Route to: OLLAMA CLOUD** (llama3-70b-instruct)
- **Cost:** ~$20 (20k tokens × $0.001/1k)
- **Latency:** ~400ms
- **Quality:** +15% accuracy vs local (70B model)

---

### Example 3: Legal Contract Extraction (CRITICAL)
**Input:** Extract clauses, obligations, and dates from 50-page legal contract

**Task Characteristics:**
- Type: `extraction`
- Complexity: `very_high`
- Quality Req: **`critical`** ⭐
- Data Classification: **`legal`** ⭐
- Document Pages: 50
- Stakes: High (legal liability)

**Decision Logic:**
```python
task = LLMTask(
    task_type="extraction",
    complexity="very_high",
    quality_requirement="critical",  # ← CRITICAL!
    data_classification="legal",  # ← LEGAL!
    model_local="gemma-3-4b-it-Q8_0",
    model_cloud="llama3-70b-instruct",
    model_openai="gpt-4o"
)

decision = strategy.decide(task, cost_tracker)
# → Result: ExecutionLocation.OPENAI
# → Reason: "critical_quality_legal_document"
```

**✅ Route to: OPENAI** (GPT-4o)
- **Cost:** ~$750 (50k tokens × $0.015/1k)
- **Latency:** ~600ms
- **Quality:** +25% accuracy vs local, +10% vs Ollama Cloud
- **ROI:** Prevents legal errors (worth $10k+ if mistake avoided)

---

### Example 4: Medical Record Extraction (HIPAA-Compliant)
**Input:** Extract patient data from 100 medical records (sensitive PHI)

**Task Characteristics:**
- Type: `extraction`
- Complexity: `high`
- Quality Req: `critical`
- Data Classification: **`pii`** + **`medical`** ⭐
- HIPAA Compliance Required

**Decision Logic:**
```python
task = LLMTask(
    task_type="extraction",
    complexity="high",
    quality_requirement="critical",
    data_classification="pii",  # ← PII! Must stay local
    model_local="gemma-3-4b-it-Q8_0",
    model_cloud="llama3-70b-instruct",
    model_openai="gpt-4o"
)

decision = strategy.decide(task, cost_tracker)
# → Result: ExecutionLocation.LOCAL
# → Reason: "sensitive_data" (PII classification overrides quality)
```

**✅ Route to: LOCAL** (gemma-3-4b-it-Q8_0)
- **Cost:** $0
- **Latency:** ~150ms
- **Quality:** Lower, but **HIPAA compliance mandatory**
- **Alternative:** If quality critical, anonymize data first, then use OpenAI

---

### Example 5: Batch Processing (100 Documents)
**Input:** Extract entities from 100 standard documents overnight

**Task Characteristics:**
- Type: `extraction`
- Complexity: `medium`
- Quality Req: `medium`
- Data Classification: `public`
- **Batch Size:** 100 ⭐
- Latency Req: Not critical (overnight batch)

**Decision Logic:**
```python
task = LLMTask(
    task_type="extraction",
    complexity="medium",
    quality_requirement="medium",
    data_classification="public",
    batch_size=100,  # ← BATCH!
    model_local="gemma-3-4b-it-Q8_0",
    model_cloud="llama3-70b-instruct",
    model_openai="gpt-4o"
)

decision = strategy.decide(task, cost_tracker)
# → Result: ExecutionLocation.OLLAMA_CLOUD
# → Reason: "batch_processing" (cloud scales better)
```

**✅ Route to: OLLAMA CLOUD** (llama3-70b-instruct)
- **Cost:** ~$100 (100 docs × 1k tokens × $0.001/1k)
- **Latency:** Parallel execution (10 docs/min = 10 minutes total)
- **Quality:** Better than local, cost-effective at scale

---

### Example 6: Code Generation for Technical Docs
**Input:** Generate Python code from natural language API specification

**Task Characteristics:**
- Type: **`code_generation`** ⭐
- Complexity: `high`
- Quality Req: `high`
- Data Classification: `public`

**Decision Logic:**
```python
task = LLMTask(
    task_type="code_generation",  # ← CODE!
    complexity="high",
    quality_requirement="high",
    data_classification="public",
    model_local="llama3.2:8b",
    model_cloud="llama3-70b-instruct",
    model_openai="o1-preview"  # ← Best for code
)

decision = strategy.decide(task, cost_tracker)
# → Result: ExecutionLocation.OPENAI
# → Reason: "code_generation_best_quality"
```

**✅ Route to: OPENAI** (o1-preview)
- **Cost:** ~$15 (1k tokens × $0.015/1k)
- **Latency:** ~800ms
- **Quality:** o1-preview excels at code generation (better than llama3-70b)

---

### Example 7: Multi-Hop Research Query
**Input:** "Compare the economic policies of three countries and predict their impact on global trade"

**Task Characteristics:**
- Type: **`research`** (multi-hop reasoning)
- Complexity: **`very_high`**
- Quality Req: `high`
- Data Classification: `public`

**Decision Logic:**
```python
task = LLMTask(
    task_type="research",  # ← MULTI-HOP!
    complexity="very_high",
    quality_requirement="high",
    data_classification="public",
    model_local="llama3.2:8b",
    model_cloud="llama3-70b-instruct",
    model_openai="o1-preview"  # ← Best for reasoning
)

decision = strategy.decide(task, cost_tracker)
# → Result: ExecutionLocation.OPENAI
# → Reason: "very_high_complexity_multi_hop_reasoning"
```

**✅ Route to: OPENAI** (o1-preview)
- **Cost:** ~$75 (5k tokens × $0.015/1k)
- **Latency:** ~1200ms (complex reasoning takes longer)
- **Quality:** o1-preview's chain-of-thought reasoning superior

---

## Cost-Quality Matrix

| Task Type | Local | Ollama Cloud | OpenAI | Recommended |
|-----------|-------|--------------|--------|-------------|
| **Embeddings** | ✅ FREE | ❌ No benefit | ❌ No benefit | **LOCAL** |
| **Simple Query** | ✅ FREE, Fast | ⚠️ $0.001, Slower | ❌ $0.015, Overkill | **LOCAL** |
| **Standard Extraction** | ⚠️ 75% accuracy | ✅ 90% accuracy | ⚠️ 100%, Expensive | **OLLAMA CLOUD** |
| **Legal Extraction** | ❌ 75%, Risky | ⚠️ 90%, Better | ✅ 100%, Worth it | **OPENAI** |
| **Medical Extraction** | ✅ 75%, HIPAA OK | ❌ Cloud = HIPAA risk | ❌ Cloud = HIPAA risk | **LOCAL** |
| **Batch (100 docs)** | ⚠️ Slow (local GPU) | ✅ Parallel, $100 | ❌ $1,500, Overkill | **OLLAMA CLOUD** |
| **Code Generation** | ⚠️ 70% correct | ⚠️ 85% correct | ✅ 95% correct | **OPENAI** |
| **Multi-Hop Reasoning** | ❌ 60% correct | ⚠️ 80% correct | ✅ 95% correct | **OPENAI** |

---

## Budget Allocation Example (Monthly: $200)

### Scenario: 1,000 documents/month + 10,000 queries/month

**Task Distribution:**
- 70% Local (7,000 queries + 700 docs): **$0**
- 20% Ollama Cloud (2,000 queries + 200 docs): **$120**
- 10% OpenAI (1,000 queries + 100 docs): **$80**

**Breakdown by Task Type:**

| Task Type | Volume | Provider | Cost |
|-----------|--------|----------|------|
| Embeddings (all docs) | 1,000 docs | Local | $0 |
| Simple Queries | 7,000 | Local | $0 |
| Standard Extraction | 200 docs | Ollama Cloud | $100 |
| Complex Queries | 2,000 | Ollama Cloud | $20 |
| Legal Extraction | 50 docs | OpenAI | $60 |
| Research Queries | 500 | OpenAI | $15 |
| Code Generation | 50 | OpenAI | $5 |
| **TOTAL** | | | **$200** |

**ROI Analysis:**
- OpenAI cost: $80/month
- Quality improvement: +25% accuracy → -10 hours manual correction @ $50/hour
- **Savings:** $500/month - $80/month = **+$420/month ROI**

---

## Fallback Chain Behavior

### Scenario 1: OpenAI Rate Limit Reached
```
User submits legal document extraction → Routes to OpenAI
↓
OpenAI returns 429 (Rate Limit Exceeded)
↓
Fallback to Ollama Cloud (llama3-70b)
↓
Ollama Cloud succeeds (90% accuracy instead of 100%)
↓
Log: "openai_rate_limit_fallback_ollama_cloud"
```

### Scenario 2: Ollama Cloud Unavailable
```
User submits standard extraction → Routes to Ollama Cloud
↓
Ollama Cloud connection timeout
↓
Fallback to Local (gemma-3-4b)
↓
Local succeeds (75% accuracy instead of 90%)
↓
Log: "ollama_cloud_unavailable_fallback_local"
```

### Scenario 3: Budget Exceeded
```
User submits task → Decision logic checks budget
↓
OpenAI budget exceeded (10% of $200 = $20 spent)
↓
Force route to Ollama Cloud instead
↓
Ollama Cloud succeeds (cost-effective fallback)
↓
Log: "openai_budget_exceeded_fallback_ollama_cloud"
```

---

## Configuration Examples

### Cost-Optimized Configuration
**Goal:** Minimize costs, use OpenAI rarely

```yaml
multi_cloud:
  cost_limits:
    daily_budget_usd: 5.0
    monthly_budget_usd: 100.0
    openai_budget_pct: 5.0  # Only 5% for OpenAI

  quality_thresholds:
    openai_threshold: "critical"  # Very restrictive
    ollama_cloud_threshold: "high"
    local_threshold: "medium"
```

**Expected Distribution:**
- Local: 75%
- Ollama Cloud: 20%
- OpenAI: 5%

**Monthly Cost:** ~$70 ($60 Ollama + $10 OpenAI)

---

### Quality-Optimized Configuration
**Goal:** Maximize quality, use OpenAI frequently

```yaml
multi_cloud:
  cost_limits:
    daily_budget_usd: 15.0
    monthly_budget_usd: 300.0
    openai_budget_pct: 20.0  # 20% for OpenAI

  quality_thresholds:
    openai_threshold: "high"  # More permissive
    ollama_cloud_threshold: "medium"
    local_threshold: "low"
```

**Expected Distribution:**
- Local: 60%
- Ollama Cloud: 20%
- OpenAI: 20%

**Monthly Cost:** ~$260 ($100 Ollama + $160 OpenAI)

---

### Balanced Configuration (Recommended)
**Goal:** Balance cost and quality

```yaml
multi_cloud:
  cost_limits:
    daily_budget_usd: 10.0
    monthly_budget_usd: 200.0
    openai_budget_pct: 10.0  # 10% for OpenAI

  quality_thresholds:
    openai_threshold: "critical"  # Critical tasks only
    ollama_cloud_threshold: "high"
    local_threshold: "medium"
```

**Expected Distribution:**
- Local: 70%
- Ollama Cloud: 20%
- OpenAI: 10%

**Monthly Cost:** ~$200 ($120 Ollama + $80 OpenAI)

---

## Monitoring Alerts

### Alert 1: OpenAI Budget Warning (80%)
```
Severity: WARNING
Message: "OpenAI budget at 80% ($16 of $20 spent)"
Action: Log warning, continue using OpenAI
Threshold: openai_budget_pct > 8%
```

### Alert 2: OpenAI Budget Exceeded (100%)
```
Severity: CRITICAL
Message: "OpenAI budget exceeded ($20 of $20 spent), forcing fallback to Ollama Cloud"
Action: Force all OpenAI tasks to Ollama Cloud until end of month
Threshold: openai_budget_pct >= 10%
```

### Alert 3: Total Budget Warning (90%)
```
Severity: CRITICAL
Message: "Total budget at 90% ($180 of $200 spent)"
Action: Force all tasks to Local until end of month
Threshold: monthly_cost_usd > 180
```

---

## Testing Checklist

**Unit Tests (30 tests):**
- [ ] Decision logic for each tier (Local, Ollama Cloud, OpenAI)
- [ ] Budget enforcement (per-provider limits)
- [ ] Fallback chain (OpenAI → Ollama → Local)
- [ ] Data classification routing (PII → Local)
- [ ] Cost calculation (verify OpenAI pricing)

**Integration Tests (15 tests):**
- [ ] End-to-end extraction with OpenAI
- [ ] Fallback on OpenAI rate limit
- [ ] Fallback on Ollama Cloud unavailable
- [ ] Per-provider cost tracking
- [ ] Quality comparison (Local vs Ollama vs OpenAI)

**Acceptance Tests (5 scenarios):**
- [ ] Legal document extraction (must use OpenAI)
- [ ] Standard document extraction (must use Ollama Cloud)
- [ ] Batch processing (must use Ollama Cloud for parallelism)
- [ ] Medical records (must use Local for HIPAA)
- [ ] Budget exceeded (must fallback to Local)

---

## Best Practices

### DO's ✅
- **DO** use OpenAI for legal, medical, and critical documents (accuracy paramount)
- **DO** use Ollama Cloud for standard extraction and batch processing (cost-effective)
- **DO** use Local for embeddings, simple queries, and sensitive data (free and fast)
- **DO** set strict budget limits (10% max for OpenAI)
- **DO** monitor cost/quality metrics weekly
- **DO** validate quality improvement before increasing OpenAI usage

### DON'Ts ❌
- **DON'T** send PII/confidential data to cloud (GDPR violation)
- **DON'T** use OpenAI for simple queries (overkill, wastes budget)
- **DON'T** use Local for complex reasoning (quality suffers)
- **DON'T** ignore cost alerts (budget can spiral quickly)
- **DON'T** skip quality benchmarking (validate ROI)

---

**Document Status:** 📋 REFERENCE GUIDE
**Related ADR:** ADR-032 (Multi-Cloud Execution Strategy)
**Last Updated:** 2025-11-11
**Owner:** Backend Team (Klaus Pommer)
