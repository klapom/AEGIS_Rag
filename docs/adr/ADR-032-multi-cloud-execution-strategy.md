# ADR-032: Multi-Cloud Execution Strategy (Local + Ollama Cloud + OpenAI)

**Status:** 🔬 PROPOSED (2025-11-11)
**Supersedes:** ADR-031 (extends hybrid strategy to multi-cloud)
**Deciders:** Project Lead (Klaus Pommer), Backend Team
**Date:** 2025-11-11
**Sprint:** Sprint 23 (Feature 23.4)

---

## Context and Problem Statement

### Evolution from ADR-031

ADR-031 proposed a **hybrid local/cloud strategy** with two execution locations:
1. **Local Ollama:** Cost-free, low latency, limited model size (max 8B)
2. **Ollama Cloud:** Pay-per-use, larger models (70B+), improved quality

### New Requirement: OpenAI API Integration

After evaluating ADR-031, we identified an additional opportunity:
> **OpenAI API** (GPT-4o, GPT-4, o1) offers **highest quality** for critical tasks, despite higher costs.

**Use Cases for OpenAI:**
1. **Mission-Critical Extraction:** Legal documents, medical records (accuracy paramount)
2. **Complex Multi-Hop Reasoning:** Research queries requiring deep analysis
3. **Code Generation:** Technical documentation, API specs (GPT-4 excels)
4. **Quality Benchmarking:** Use OpenAI as "gold standard" to validate other models

### Problem Statement

> How can we integrate **three execution tiers** (Local, Ollama Cloud, OpenAI) into a unified ExecutionProxy with intelligent routing based on quality requirements, cost constraints, and task complexity?

---

## Decision Drivers

### Quality Hierarchy
```
Local (gemma-3-4b)  →  Ollama Cloud (llama3-70b)  →  OpenAI (GPT-4o)
   [Good]                    [Better]                    [Best]
```

### Cost Hierarchy (per 1,000 tokens)
```
Local: $0.00  →  Ollama Cloud: ~$0.001  →  OpenAI GPT-4o: ~$0.015
  [Free]              [Affordable]              [Premium]
```

### Latency (similar for both clouds)
- **Local:** 50-200ms (no network overhead)
- **Ollama Cloud:** 200-500ms (network + inference)
- **OpenAI API:** 300-600ms (network + inference)

### Business Drivers
1. **Flexibility:** Choose optimal provider per task
2. **Cost Control:** Use OpenAI only when quality justifies cost
3. **Redundancy:** Fallback chain (OpenAI → Ollama Cloud → Local)
4. **Competitive Benchmarking:** Compare quality across providers

---

## Considered Options

### Option 1: Two-Tier Hybrid (Status Quo from ADR-031)
**Tiers:** Local + Ollama Cloud

**Pros:**
- ✅ Simpler architecture (two providers)
- ✅ Lower complexity in decision logic
- ✅ Good cost/quality balance

**Cons:**
- ❌ Cannot access highest-quality models (GPT-4o, o1)
- ❌ Limited flexibility for premium use cases
- ❌ No competitive benchmarking against OpenAI

---

### Option 2: Three-Tier Multi-Cloud (Proposed) ⭐
**Tiers:** Local + Ollama Cloud + OpenAI API

**Architecture:**
```
                    ┌────────────────────┐
                    │  ExecutionProxy    │
                    │  (Decision Logic)  │
                    └─────────┬──────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
      [Tier 1: Local]   [Tier 2: Cloud]  [Tier 3: Premium]
            │                 │                 │
            ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │Local Ollama  │  │Ollama Cloud  │  │  OpenAI API  │
    │- gemma-3-4b  │  │- llama3-70b  │  │  - GPT-4o    │
    │- llama3.2:8b │  │- llama3-8b   │  │  - GPT-4     │
    │- BGE-M3      │  │- llava-13b   │  │  - o1        │
    └──────────────┘  └──────────────┘  └──────────────┘
         FREE            ~$0.001/1k          ~$0.015/1k
```

**Decision Matrix:**

| Task Type | Complexity | Quality Req | Cost Budget | → Route To |
|-----------|------------|-------------|-------------|------------|
| Embeddings | Any | Any | Any | **Local** (always) |
| Simple Query | Low | Medium | Any | **Local** |
| Extraction (Standard) | Medium | Medium | Normal | **Ollama Cloud** |
| Extraction (Legal/Medical) | High | **Critical** | High | **OpenAI** |
| Complex Reasoning | High | High | Normal | **Ollama Cloud** |
| Multi-Hop Research | Very High | **Critical** | High | **OpenAI** |
| Code Generation | High | High | High | **OpenAI** |
| Batch Processing | Any | Medium | Low | **Ollama Cloud** |

**Fallback Chain:**
```
OpenAI (fails) → Ollama Cloud (fails) → Local (always succeeds)
```

**Pros:**
- ✅ **Maximum Flexibility:** Choose optimal provider per task
- ✅ **Highest Quality Available:** Access to GPT-4o, o1 for critical tasks
- ✅ **Cost Optimization:** Use expensive OpenAI only when justified
- ✅ **Competitive Benchmarking:** Compare Local vs Ollama vs OpenAI
- ✅ **Redundancy:** Triple fallback chain ensures reliability
- ✅ **Future-Proof:** Easy to add more providers (Anthropic, Google Gemini)

**Cons:**
- ⚠️ **Increased Complexity:** Three providers to manage
- ⚠️ **Cost Monitoring:** Must track budgets for two cloud providers
- ⚠️ **API Key Management:** Multiple secrets to secure
- ⚠️ **Testing Overhead:** Test all three execution paths

**Cost Analysis (Estimated):**

**Scenario:** 1,000 documents/month, 10,000 queries/month

**Hybrid Strategy (30% Cloud):**
- Ollama Cloud: 30% × 55M tokens = 16.5M tokens/month
- **Cost:** 16.5M × $0.001/1k = **$16.5/month**

**Multi-Cloud Strategy (20% Ollama, 10% OpenAI):**
- Ollama Cloud: 20% × 55M tokens = 11M tokens/month → **$11/month**
- OpenAI: 10% × 55M tokens = 5.5M tokens/month → **$82.50/month**
- **Total Cloud:** **$93.50/month** ($1,122/year)

**Cost Breakdown by Task:**
- Extraction (20% Ollama, 10% OpenAI): $11 + $75 = $86/month
- Generation (5% OpenAI): $7.50/month
- **Total:** $93.50/month

**Quality Improvement:**
- Ollama Cloud: +15% accuracy (vs local)
- OpenAI: **+25% accuracy** (vs local), **+10% vs Ollama Cloud**

**Break-Even:**
If quality improvement (25% vs 15%) reduces manual correction by 10 hours/month @ $50/hour:
- **Savings:** 10 hours × $50 = **$500/month**
- **Additional Cost:** $93.50 - $16.50 = **$77/month**
- **Net Benefit:** $500 - $77 = **+$423/month ROI**

---

### Option 3: Selective OpenAI (Only for Critical Tasks)
**Tiers:** Local + Ollama Cloud (default) + OpenAI (critical only)

Similar to Option 2, but OpenAI used **<5% of time** (only mission-critical).

**Cost Analysis:**
- Ollama Cloud: 25% of tasks → $13.75/month
- OpenAI: 5% of tasks → $41.25/month
- **Total:** **$55/month** ($660/year)

**Pros:**
- ✅ Lower cost than Option 2
- ✅ Still access to highest quality when needed

**Cons:**
- ⚠️ Less frequent OpenAI usage → harder to benchmark
- ⚠️ May underutilize OpenAI's capabilities

---

## Decision Outcome

**Chosen option:** **Option 2 (Three-Tier Multi-Cloud)** ⭐

### Rationale

1. **Quality Justifies Cost:**
   - OpenAI's +25% accuracy improvement reduces manual corrections
   - ROI: **+$423/month** (quality savings exceed cloud costs)

2. **Flexibility for Critical Use Cases:**
   - Legal document extraction: OpenAI accuracy critical
   - Medical record extraction: Errors costly (compliance, patient safety)
   - Research queries: GPT-4o's reasoning superior

3. **Competitive Benchmarking:**
   - Validate Ollama models against OpenAI "gold standard"
   - Data-driven decision: When is Ollama Cloud "good enough"?

4. **Gradual Rollout:**
   - Week 1: 5% OpenAI (critical only)
   - Week 2: 10% OpenAI (expand to complex reasoning)
   - Week 4: Stabilize at 10% based on cost/quality metrics

5. **Future-Proof:**
   - Easy to add Anthropic Claude, Google Gemini, Cohere
   - Architecture supports N providers (not limited to 3)

---

## Implementation Details

### 1. Enhanced ExecutionProxy

**File:** `src/components/execution/execution_proxy.py`

```python
from enum import Enum

class ExecutionLocation(str, Enum):
    """Execution location for LLM tasks."""
    LOCAL = "local"
    OLLAMA_CLOUD = "ollama_cloud"
    OPENAI = "openai"


class ExecutionProxy:
    """Routes LLM tasks across three execution tiers."""

    def __init__(
        self,
        local_client: OllamaClient,
        ollama_cloud_client: OllamaCloudClient,
        openai_client: OpenAIClient,
        cost_tracker: CostTracker,
        strategy: DecisionStrategy
    ):
        self.local_client = local_client
        self.ollama_cloud_client = ollama_cloud_client
        self.openai_client = openai_client
        self.cost_tracker = cost_tracker
        self.strategy = strategy

    async def execute(self, task: LLMTask) -> LLMResult:
        """Execute LLM task with three-tier routing."""
        # 1. Make routing decision
        decision = self.strategy.decide(task, self.cost_tracker)

        logger.info(
            "execution_routing",
            task_id=task.task_id,
            location=decision.location,
            model=decision.model,
            reason=decision.reason
        )

        # 2. Execute with fallback chain
        try:
            if decision.location == ExecutionLocation.OPENAI:
                result = await self._execute_with_fallback(
                    task,
                    [
                        (self.openai_client, task.model_openai),
                        (self.ollama_cloud_client, task.model_cloud),
                        (self.local_client, task.model_local)
                    ]
                )
            elif decision.location == ExecutionLocation.OLLAMA_CLOUD:
                result = await self._execute_with_fallback(
                    task,
                    [
                        (self.ollama_cloud_client, task.model_cloud),
                        (self.local_client, task.model_local)
                    ]
                )
            else:  # LOCAL
                result = await self.local_client.execute(task, task.model_local)

            # 3. Track cost
            if result.cost_usd > 0:
                self.cost_tracker.record(
                    result.cost_usd,
                    task.task_id,
                    provider=result.location
                )

            return result

        except Exception as e:
            logger.error("execution_failed", task_id=task.task_id, error=str(e))
            # Final fallback: always try local
            return await self.local_client.execute(task, task.model_local)

    async def _execute_with_fallback(
        self,
        task: LLMTask,
        clients: List[Tuple[LLMClient, str]]
    ) -> LLMResult:
        """Execute with fallback chain."""
        last_error = None

        for client, model in clients:
            try:
                return await client.execute(task, model)
            except Exception as e:
                logger.warning(
                    "execution_attempt_failed",
                    task_id=task.task_id,
                    client=client.__class__.__name__,
                    error=str(e)
                )
                last_error = e
                continue

        # All attempts failed
        raise last_error
```

---

### 2. OpenAI Client

**File:** `src/components/execution/openai_client.py`

```python
import openai
from typing import Dict, Any
from src.core.logging import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    """Client for OpenAI API (GPT-4o, GPT-4, o1)."""

    def __init__(self, api_key: str, organization: str = None):
        self.api_key = api_key
        self.organization = organization
        openai.api_key = api_key
        if organization:
            openai.organization = organization

    async def execute(self, task: LLMTask, model: str) -> LLMResult:
        """Execute task using OpenAI API."""
        try:
            response = await openai.ChatCompletion.acreate(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": task.prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            output = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            cost_usd = self._calculate_cost(tokens_used, model)

            return LLMResult(
                task_id=task.task_id,
                location=ExecutionLocation.OPENAI,
                model=model,
                output=output,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                latency_ms=0  # TODO: track latency
            )

        except openai.error.RateLimitError as e:
            logger.error("openai_rate_limit", task_id=task.task_id, error=str(e))
            raise
        except openai.error.InvalidRequestError as e:
            logger.error("openai_invalid_request", task_id=task.task_id, error=str(e))
            raise
        except Exception as e:
            logger.error("openai_unexpected_error", task_id=task.task_id, error=str(e))
            raise

    def _calculate_cost(self, tokens: int, model: str) -> float:
        """Calculate OpenAI API cost."""
        # Pricing as of 2025-11-11
        PRICING = {
            "gpt-4o": 0.015,  # $0.015 per 1k tokens (input+output avg)
            "gpt-4-turbo": 0.01,  # $0.01 per 1k tokens
            "gpt-4": 0.03,  # $0.03 per 1k tokens
            "gpt-3.5-turbo": 0.002,  # $0.002 per 1k tokens
            "o1-preview": 0.015,  # Estimated
            "o1-mini": 0.003  # Estimated
        }

        price_per_1k = PRICING.get(model, 0.015)  # Default to GPT-4o pricing
        cost = (tokens / 1000.0) * price_per_1k
        return cost
```

---

### 3. Enhanced Decision Strategy (Three-Tier)

**File:** `src/components/execution/decision_strategy.py`

```python
class MultiCloudStrategy(DecisionStrategy):
    """Three-tier decision strategy: Local → Ollama Cloud → OpenAI."""

    def __init__(
        self,
        openai_budget_pct: float = 10.0,  # Max % of budget for OpenAI
        quality_threshold_openai: str = "critical",  # When to use OpenAI
        enable_openai: bool = True
    ):
        self.openai_budget_pct = openai_budget_pct
        self.quality_threshold_openai = quality_threshold_openai
        self.enable_openai = enable_openai

    def decide(self, task: LLMTask, cost_tracker: CostTracker) -> DecisionResult:
        """Three-tier decision logic."""

        # 1. Data Privacy: Sensitive data always local
        if task.data_classification in ["confidential", "pii"]:
            return DecisionResult(
                location=ExecutionLocation.LOCAL,
                model=task.model_local,
                reason="sensitive_data",
                confidence=1.0
            )

        # 2. Embeddings: Always local (fast, free, no cloud benefit)
        if task.task_type == "embedding":
            return DecisionResult(
                location=ExecutionLocation.LOCAL,
                model=task.model_local,
                reason="embeddings_local_only",
                confidence=1.0
            )

        # 3. Budget Check: If budgets exceeded, fallback to local
        if cost_tracker.is_budget_exceeded():
            return DecisionResult(
                location=ExecutionLocation.LOCAL,
                model=task.model_local,
                reason="budget_exceeded",
                confidence=1.0
            )

        # 4. TIER 3 (OpenAI): Critical quality requirements
        if self.enable_openai and self._should_use_openai(task, cost_tracker):
            return DecisionResult(
                location=ExecutionLocation.OPENAI,
                model=task.model_openai,
                reason=self._openai_reason(task),
                confidence=0.95
            )

        # 5. TIER 2 (Ollama Cloud): Medium-high quality, cost-effective
        if self._should_use_ollama_cloud(task):
            return DecisionResult(
                location=ExecutionLocation.OLLAMA_CLOUD,
                model=task.model_cloud,
                reason=self._ollama_cloud_reason(task),
                confidence=0.85
            )

        # 6. TIER 1 (Local): Default, cost-free
        return DecisionResult(
            location=ExecutionLocation.LOCAL,
            model=task.model_local,
            reason="default_local",
            confidence=0.7
        )

    def _should_use_openai(self, task: LLMTask, cost_tracker: CostTracker) -> bool:
        """Determine if OpenAI should be used."""
        # Check 1: Quality requirement
        if task.quality_requirement != "critical":
            return False

        # Check 2: OpenAI budget not exceeded
        if cost_tracker.get_provider_cost_pct("openai") > self.openai_budget_pct:
            logger.warning("openai_budget_exceeded", fallback="ollama_cloud")
            return False

        # Check 3: Task type suitable for OpenAI
        openai_suitable_types = [
            "extraction",  # Legal, medical documents
            "generation",  # Complex reasoning
            "code_generation",  # Technical docs
            "research"  # Multi-hop reasoning
        ]
        if task.task_type not in openai_suitable_types:
            return False

        # Check 4: Complexity high enough
        if task.complexity not in ["high", "very_high"]:
            return False

        return True

    def _should_use_ollama_cloud(self, task: LLMTask) -> bool:
        """Determine if Ollama Cloud should be used."""
        # Medium-high quality tasks
        if task.quality_requirement in ["high", "medium"] and task.complexity == "high":
            return True

        # Batch processing
        if hasattr(task, "batch_size") and task.batch_size > 10:
            return True

        # GPU relief (local GPU busy)
        from src.utils.gpu_monitor import get_gpu_utilization
        if get_gpu_utilization() > 80:
            return True

        return False

    def _openai_reason(self, task: LLMTask) -> str:
        """Generate reason for OpenAI routing."""
        reasons = []
        if task.quality_requirement == "critical":
            reasons.append("critical_quality")
        if task.complexity == "very_high":
            reasons.append("very_high_complexity")
        if task.task_type == "extraction" and task.data_classification == "legal":
            reasons.append("legal_document")
        return "_".join(reasons) if reasons else "openai_best_quality"

    def _ollama_cloud_reason(self, task: LLMTask) -> str:
        """Generate reason for Ollama Cloud routing."""
        if task.quality_requirement == "high":
            return "high_quality_cost_effective"
        if task.complexity == "high":
            return "high_complexity"
        if hasattr(task, "batch_size") and task.batch_size > 10:
            return "batch_processing"
        return "cloud_cost_optimized"
```

---

### 4. Enhanced Cost Tracker (Multi-Provider)

**File:** `src/components/execution/cost_tracker.py`

```python
class CostTracker:
    """Track costs across multiple cloud providers."""

    def __init__(
        self,
        daily_budget_usd: float,
        monthly_budget_usd: float,
        openai_budget_pct: float = 10.0,  # Max 10% of budget for OpenAI
        alert_threshold_pct: float = 80.0
    ):
        self.daily_budget_usd = daily_budget_usd
        self.monthly_budget_usd = monthly_budget_usd
        self.openai_budget_pct = openai_budget_pct
        self.alert_threshold_pct = alert_threshold_pct

        # Per-provider cost tracking
        self.provider_costs = defaultdict(lambda: defaultdict(float))
        # provider_costs[provider][date] = cost

    def record(self, cost_usd: float, task_id: str, provider: str):
        """Record cost for a specific provider."""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        self.provider_costs[provider][today] += cost_usd

        # Check per-provider budget limits
        if provider == "openai":
            openai_pct = self.get_provider_cost_pct("openai")
            if openai_pct > self.openai_budget_pct:
                logger.warning(
                    "openai_budget_exceeded",
                    openai_cost_pct=openai_pct,
                    limit_pct=self.openai_budget_pct,
                    task_id=task_id
                )

        logger.info(
            "cost_recorded",
            task_id=task_id,
            provider=provider,
            cost_usd=cost_usd,
            daily_total=self.get_daily_cost(),
            monthly_total=self.get_monthly_cost()
        )

    def get_provider_cost(self, provider: str, period: str = "month") -> float:
        """Get cost for a specific provider."""
        if period == "day":
            date = datetime.now().strftime("%Y-%m-%d")
            return self.provider_costs[provider].get(date, 0.0)
        else:  # month
            month = datetime.now().strftime("%Y-%m")
            # Sum all days in current month
            return sum(
                cost for date, cost in self.provider_costs[provider].items()
                if date.startswith(month)
            )

    def get_provider_cost_pct(self, provider: str) -> float:
        """Get provider cost as % of total budget."""
        total_cost = self.get_monthly_cost()
        if total_cost == 0:
            return 0.0
        provider_cost = self.get_provider_cost(provider, period="month")
        return (provider_cost / total_cost) * 100.0

    def get_cost_breakdown(self) -> Dict[str, float]:
        """Get cost breakdown by provider."""
        return {
            "local": 0.0,  # Always free
            "ollama_cloud": self.get_provider_cost("ollama_cloud"),
            "openai": self.get_provider_cost("openai"),
            "total": self.get_monthly_cost()
        }
```

---

### 5. Enhanced LLMTask Model

**File:** `src/components/execution/models.py`

```python
@dataclass
class LLMTask:
    """LLM task with three-tier model specification."""
    task_id: str
    task_type: str  # "extraction", "generation", "embedding", "vlm", "code_generation"
    prompt: str

    # Model specifications for each tier
    model_local: str  # e.g., "gemma-3-4b-it-Q8_0"
    model_cloud: str  # e.g., "llama3-70b-instruct"
    model_openai: str  # e.g., "gpt-4o", "gpt-4-turbo", "o1-preview"

    # Task characteristics
    complexity: str  # "low", "medium", "high", "very_high"
    quality_requirement: str  # "medium", "high", "critical"
    data_classification: str  # "public", "internal", "confidential", "pii", "legal", "medical"

    # Optional parameters
    latency_requirement_ms: int = 1000
    batch_size: int = 1
```

---

## Configuration Example

**File:** `config/multi_cloud.yaml`

```yaml
multi_cloud:
  # Enable/disable providers
  enabled:
    local: true
    ollama_cloud: true
    openai: true

  # Local Ollama (always available)
  local:
    base_url: "http://localhost:11434"
    models:
      extraction: "gemma-3-4b-it-Q8_0"
      generation: "llama3.2:8b"
      embedding: "nomic-embed-text"

  # Ollama Cloud
  ollama_cloud:
    api_key: ${OLLAMA_CLOUD_API_KEY}
    base_url: "https://cloud.ollama.ai"
    models:
      extraction: "llama3-70b-instruct"
      generation: "llama3-8b-instruct"
      vision: "llava-13b"

  # OpenAI API
  openai:
    api_key: ${OPENAI_API_KEY}
    organization: ${OPENAI_ORGANIZATION}  # Optional
    models:
      extraction: "gpt-4o"  # Highest quality for critical docs
      generation: "gpt-4o"
      code_generation: "o1-preview"  # Best for code
      research: "o1-preview"  # Best for multi-hop reasoning

  # Cost limits
  cost_limits:
    daily_budget_usd: 10.0  # Increased for OpenAI
    monthly_budget_usd: 200.0  # Increased for OpenAI
    openai_budget_pct: 10.0  # Max 10% of total budget for OpenAI
    alert_threshold_pct: 80

  # Decision strategy
  decision_strategy: "multi_cloud"  # "cost_optimized", "quality_optimized", "multi_cloud"

  # Quality thresholds
  quality_thresholds:
    openai_threshold: "critical"  # Use OpenAI only for "critical" tasks
    ollama_cloud_threshold: "high"  # Use Ollama Cloud for "high" tasks
    local_threshold: "medium"  # Use Local for "medium" and below

  # Fallback chain
  fallback:
    openai_unavailable: "ollama_cloud"
    ollama_cloud_unavailable: "local"
    budget_exceeded: "local"
```

---

## Cost Management Strategy

### Budget Allocation (Monthly: $200)

| Provider | Budget | % of Total | Use Cases |
|----------|--------|------------|-----------|
| **Local** | $0 | 0% | Embeddings, simple queries (70% of tasks) |
| **Ollama Cloud** | $120 | 60% | Standard extraction, batch processing (20% of tasks) |
| **OpenAI** | $80 | 40% | Critical extraction, complex reasoning (10% of tasks) |

### Cost Control Mechanisms

**1. Per-Provider Budget Limits:**
```python
if cost_tracker.get_provider_cost_pct("openai") > 10%:
    # Fallback to Ollama Cloud
    logger.warning("openai_budget_exceeded", fallback="ollama_cloud")
    return DecisionResult(location=ExecutionLocation.OLLAMA_CLOUD, ...)
```

**2. Quality-Based Routing:**
```python
# Only use OpenAI for "critical" quality requirement
if task.quality_requirement == "critical":
    return ExecutionLocation.OPENAI
elif task.quality_requirement == "high":
    return ExecutionLocation.OLLAMA_CLOUD
else:
    return ExecutionLocation.LOCAL
```

**3. Task-Type Prioritization:**
```python
# Legal/Medical documents → OpenAI (highest accuracy)
if task.data_classification in ["legal", "medical"]:
    return ExecutionLocation.OPENAI

# Standard documents → Ollama Cloud (cost-effective)
elif task.data_classification == "public":
    return ExecutionLocation.OLLAMA_CLOUD
```

---

## Monitoring & Dashboards

### Grafana Dashboard: "Multi-Cloud Execution"

**Panel 1: Cost Distribution (Pie Chart)**
- Local: 0% ($0)
- Ollama Cloud: 60% ($120)
- OpenAI: 40% ($80)

**Panel 2: Execution Distribution (Bar Chart)**
- Local: 70% of tasks
- Ollama Cloud: 20% of tasks
- OpenAI: 10% of tasks

**Panel 3: Quality Comparison (Line Chart)**
- Local accuracy: 75%
- Ollama Cloud accuracy: 90% (+15% vs local)
- OpenAI accuracy: 100% (+25% vs local, +10% vs Ollama)

**Panel 4: Latency Comparison (Histogram)**
- Local: p50=100ms, p95=200ms
- Ollama Cloud: p50=400ms, p95=600ms
- OpenAI: p50=500ms, p95=800ms

**Panel 5: Cost per Task (Gauge)**
- Local: $0
- Ollama Cloud: $0.001/task
- OpenAI: $0.015/task

---

## Validation Plan

### Phase 1: OpenAI Integration (Sprint 23, Week 4)

**Test 1: API Access**
- Verify OpenAI API key works
- Test GPT-4o, GPT-4, o1-preview models
- **Success:** All models respond correctly

**Test 2: Cost Calculation**
- Execute 100 tasks with OpenAI
- Verify cost calculation matches actual billing
- **Success:** Cost accuracy within 5%

**Test 3: Fallback Chain**
- Simulate OpenAI failure
- Verify fallback to Ollama Cloud → Local
- **Success:** No failed requests due to provider outage

### Phase 2: Quality Benchmarking (Sprint 24, Week 1)

**Test 4: Extraction Quality Comparison**
- 50 test documents with ground truth
- Compare: Local (gemma-3-4b) vs Ollama (llama3-70b) vs OpenAI (GPT-4o)
- Metrics: Precision, Recall, F1-Score
- **Success:** OpenAI shows ≥+10% F1 improvement over Ollama Cloud

**Test 5: Cost-Quality Tradeoff**
- Calculate cost per F1 point improvement
- **Acceptance:** OpenAI cost justified if quality improvement ≥+10% and manual correction time saved ≥$50/month

---

## Security & Compliance

### API Key Management

**Three Secrets Required:**
1. `OLLAMA_CLOUD_API_KEY` (Ollama Cloud)
2. `OPENAI_API_KEY` (OpenAI)
3. `OPENAI_ORGANIZATION` (Optional)

**Kubernetes Secrets:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: llm-provider-keys
type: Opaque
data:
  ollama-cloud-key: <base64-encoded>
  openai-key: <base64-encoded>
  openai-org: <base64-encoded>
```

### Data Classification Rules

| Classification | Allowed Providers |
|----------------|-------------------|
| **PII** | Local only |
| **Confidential** | Local only |
| **Legal** | Local or OpenAI (highest accuracy) |
| **Medical** | Local or OpenAI (HIPAA-compliant) |
| **Internal** | Local or Ollama Cloud |
| **Public** | All providers |

---

## Acceptance Criteria

**Sprint 23 (POC):**
- ✅ OpenAI client implemented and tested
- ✅ Three-tier decision strategy implemented
- ✅ Cost tracker supports multiple providers
- ✅ Fallback chain (OpenAI → Ollama → Local) works
- ✅ Per-provider budget limits enforced

**Sprint 24 (Production):**
- ✅ Monthly cloud cost <$200 ($120 Ollama + $80 OpenAI)
- ✅ OpenAI usage <10% of total budget
- ✅ Quality improvement: OpenAI ≥+10% F1 vs Ollama Cloud
- ✅ Zero failed requests (100% fallback success)
- ✅ Manual correction time reduced by ≥10 hours/month

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **OpenAI costs exceed budget** | High | Medium | Strict 10% budget limit, automatic fallback |
| **OpenAI API unavailable** | Medium | Low | Fallback chain to Ollama Cloud |
| **Quality improvement <10%** | Medium | Low | Benchmark before production rollout |
| **Complexity overhead** | Medium | Medium | Comprehensive tests, monitoring |

---

## References

1. **ADR-031:** Ollama Cloud Hybrid Execution (superseded by this ADR)
2. **OpenAI Pricing:** https://openai.com/pricing
3. **OpenAI API Docs:** https://platform.openai.com/docs
4. **Sprint 23 Planning:** `docs/sprint-23/SPRINT_23_PLANNING.md`

---

**ADR Status:** 🔬 PROPOSED
**Next Review:** Sprint 23 Kickoff (2025-11-12)
**Owner:** Backend Team (Klaus Pommer)
**Approval Required From:** Project Lead, CFO (budget approval for $200/month)
