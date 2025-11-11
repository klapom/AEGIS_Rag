# Ollama Cloud Implementation Guide

**Document Type:** Technical Implementation Guide
**Status:** 📋 PLANNED (Sprint 23, Feature 23.4-23.5)
**Owner:** Backend Team
**Date:** 2025-11-11

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Component Design](#component-design)
4. [Integration Points](#integration-points)
5. [Implementation Roadmap](#implementation-roadmap)
6. [Code Examples](#code-examples)
7. [Testing Strategy](#testing-strategy)
8. [Monitoring & Observability](#monitoring--observability)
9. [Security & Compliance](#security--compliance)
10. [Cost Management](#cost-management)

---

## Executive Summary

This document provides a **technical implementation guide** for integrating **Ollama Cloud** into the AegisRAG system as a hybrid local/cloud execution strategy.

### Key Objectives
1. **Offload GPU-intensive operations** (extraction, VLM) to Ollama Cloud
2. **Improve extraction quality** with larger models (70B+)
3. **Maintain local execution** for embeddings, retrieval, and sensitive data
4. **Control costs** with budget limits and intelligent routing

### Implementation Timeline
- **Sprint 23 (Week 2-4):** Design, POC, testing
- **Sprint 24 (Week 1-2):** Production rollout (10% → 50% → 100%)

---

## Architecture Overview

### Current Architecture (Sprint 22)

```
┌─────────────────────────────────────────────────────────────┐
│                        User Input                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   FastAPI Endpoints  │
              │   /upload, /query    │
              └──────────┬───────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  FormatRouter│  │  Retrieval  │  │   Memory    │
│  (30 formats)│  │  (Qdrant)   │  │   (Redis)   │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       ▼                │                │
┌──────────────────┐    │                │
│  LangGraph Pipeline│  │                │
│  (6-node state)   │  │                │
│  ┌──────────────┐ │  │                │
│  │ Docling/     │ │  │                │
│  │ LlamaIndex   │ │  │                │
│  └──────┬───────┘ │  │                │
│         │         │  │                │
│         ▼         │  │                │
│  ┌──────────────┐ │  │                │
│  │  Local Ollama│◄┼──┘                │
│  │  (Extraction,│ │                   │
│  │   Generation)│ │                   │
│  └──────────────┘ │                   │
└──────────────────┘                    │
         │                              │
         └──────────────┬───────────────┘
                        ▼
              ┌──────────────────┐
              │   Knowledge Graph│
              │   (Neo4j)        │
              └──────────────────┘
```

### Proposed Architecture (Sprint 23+)

```
┌─────────────────────────────────────────────────────────────┐
│                        User Input                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   FastAPI Endpoints  │
              │   /upload, /query    │
              └──────────┬───────────┘
                         │
         ┌───────────────┼───────────────────────────┐
         │               │                           │
         ▼               ▼                           ▼
┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐
│FormatRouter │  │  Retrieval  │  │  ExecutionProxy ⭐   │
│(30 formats) │  │  (Qdrant)   │  │  (NEW COMPONENT)     │
└──────┬──────┘  └──────┬──────┘  └──────────┬───────────┘
       │                │                     │
       │                │         ┌───────────┴───────────┐
       │                │         │   Decision Logic      │
       │                │         │   (Local or Cloud?)   │
       │                │         └───────────┬───────────┘
       │                │                     │
       ▼                │         ┌───────────┴───────────┐
┌──────────────────┐   │         │                       │
│LangGraph Pipeline│   │    [Local]                  [Cloud]
│(6-node state)    │   │         │                       │
│┌────────────────┐│   │         ▼                       ▼
││ Docling/       ││   │ ┌──────────────┐    ┌──────────────────┐
││ LlamaIndex     ││   │ │Local Ollama  │    │Ollama Cloud API  │
│└────────┬───────┘│   │ │- Embeddings  │    │- Extraction (70B)│
│         │        │   │ │- Simple Gen  │    │- Complex Gen     │
│         ▼        │   │ │- Fallback    │    │- VLM (13B)       │
│┌────────────────┐│   │ └──────┬───────┘    └──────┬───────────┘
││ExecutionProxy ◄├┼───┘        │                   │
││Integration     ││             └───────────┬───────┘
│└────────┬───────┘│                        │
│         │        │             ┌──────────▼────────────┐
│         ▼        │             │  CostTracker          │
│ ┌──────────────┐ │             │  (Budget Enforcement) │
│ │  Post-Process│ │             └───────────────────────┘
│ └──────┬───────┘ │
└────────┼─────────┘
         │
         ▼
┌──────────────────┐
│Knowledge Graph   │
│(Neo4j)           │
└──────────────────┘
```

---

## Component Design

### 1. ExecutionProxy (Core Component) ⭐

**File:** `src/components/execution/execution_proxy.py`

**Responsibilities:**
- Route LLM tasks between local and cloud execution
- Apply decision logic based on task characteristics
- Track costs and enforce budget limits
- Handle fallback to local on cloud failure
- Log all routing decisions for monitoring

**Key Classes:**

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
import httpx
from src.core.logging import get_logger

logger = get_logger(__name__)


class ExecutionLocation(str, Enum):
    """Where to execute LLM task."""
    LOCAL = "local"
    CLOUD = "cloud"


@dataclass
class LLMTask:
    """LLM task to be executed."""
    task_id: str
    task_type: str  # "extraction", "generation", "embedding", "vlm"
    prompt: str
    model_local: str  # e.g., "gemma-3-4b-it-Q8_0"
    model_cloud: str  # e.g., "llama3-70b-instruct"
    complexity: str  # "low", "medium", "high"
    data_classification: str  # "public", "internal", "confidential", "pii"
    latency_requirement_ms: int = 1000
    quality_requirement: str = "medium"  # "low", "medium", "high"


@dataclass
class DecisionResult:
    """Result of routing decision."""
    location: ExecutionLocation
    model: str
    reason: str
    confidence: float  # 0.0 to 1.0


@dataclass
class LLMResult:
    """Result of LLM execution."""
    task_id: str
    location: ExecutionLocation
    model: str
    output: str
    tokens_used: int
    cost_usd: float
    latency_ms: int
    error: Optional[str] = None


class ExecutionProxy:
    """Routes LLM tasks between local Ollama and Ollama Cloud."""

    def __init__(
        self,
        local_ollama_url: str,
        cloud_api_key: str,
        cloud_base_url: str,
        cost_tracker: "CostTracker",
        decision_strategy: "DecisionStrategy"
    ):
        self.local_client = OllamaClient(local_ollama_url)
        self.cloud_client = OllamaCloudClient(api_key=cloud_api_key, base_url=cloud_base_url)
        self.cost_tracker = cost_tracker
        self.strategy = decision_strategy

    async def execute(self, task: LLMTask) -> LLMResult:
        """Execute LLM task (local or cloud based on strategy)."""
        # 1. Make routing decision
        decision = self.strategy.decide(task, self.cost_tracker)

        logger.info(
            "execution_routing",
            task_id=task.task_id,
            task_type=task.task_type,
            location=decision.location,
            model=decision.model,
            reason=decision.reason,
            confidence=decision.confidence
        )

        # 2. Execute based on decision
        try:
            if decision.location == ExecutionLocation.CLOUD:
                result = await self._execute_cloud(task, decision.model)
            else:
                result = await self._execute_local(task, decision.model)

            # 3. Track cost
            if result.cost_usd > 0:
                self.cost_tracker.record(result.cost_usd, task.task_id)

            return result

        except Exception as e:
            logger.error(
                "execution_failed",
                task_id=task.task_id,
                location=decision.location,
                error=str(e)
            )

            # 4. Fallback to local if cloud fails
            if decision.location == ExecutionLocation.CLOUD:
                logger.warning("cloud_execution_failed_fallback_to_local", task_id=task.task_id)
                return await self._execute_local(task, task.model_local)
            else:
                raise

    async def _execute_cloud(self, task: LLMTask, model: str) -> LLMResult:
        """Execute task on Ollama Cloud."""
        import time
        start_time = time.time()

        response = await self.cloud_client.generate(
            model=model,
            prompt=task.prompt
        )

        latency_ms = int((time.time() - start_time) * 1000)

        return LLMResult(
            task_id=task.task_id,
            location=ExecutionLocation.CLOUD,
            model=model,
            output=response["output"],
            tokens_used=response["tokens_used"],
            cost_usd=response["cost_usd"],
            latency_ms=latency_ms
        )

    async def _execute_local(self, task: LLMTask, model: str) -> LLMResult:
        """Execute task on local Ollama."""
        import time
        start_time = time.time()

        response = await self.local_client.generate(
            model=model,
            prompt=task.prompt
        )

        latency_ms = int((time.time() - start_time) * 1000)

        return LLMResult(
            task_id=task.task_id,
            location=ExecutionLocation.LOCAL,
            model=model,
            output=response["response"],
            tokens_used=response.get("tokens_used", 0),
            cost_usd=0.0,  # Local execution is free
            latency_ms=latency_ms
        )
```

---

### 2. Decision Strategies

**File:** `src/components/execution/decision_strategy.py`

```python
from abc import ABC, abstractmethod
from src.components.execution.execution_proxy import (
    LLMTask, DecisionResult, ExecutionLocation
)


class DecisionStrategy(ABC):
    """Abstract base class for decision strategies."""

    @abstractmethod
    def decide(self, task: LLMTask, cost_tracker: "CostTracker") -> DecisionResult:
        """Decide whether to execute task locally or in cloud."""
        pass


class CostOptimizedStrategy(DecisionStrategy):
    """Minimize cost by preferring local execution."""

    def decide(self, task: LLMTask, cost_tracker: "CostTracker") -> DecisionResult:
        # Always prefer local unless budget allows cloud
        if cost_tracker.is_budget_exceeded():
            return DecisionResult(
                location=ExecutionLocation.LOCAL,
                model=task.model_local,
                reason="budget_exceeded",
                confidence=1.0
            )

        # Use local by default (cost-optimized)
        return DecisionResult(
            location=ExecutionLocation.LOCAL,
            model=task.model_local,
            reason="cost_optimized",
            confidence=0.9
        )


class QualityOptimizedStrategy(DecisionStrategy):
    """Maximize quality by preferring cloud for complex tasks."""

    def decide(self, task: LLMTask, cost_tracker: "CostTracker") -> DecisionResult:
        # 1. Never send sensitive data to cloud
        if task.data_classification in ["confidential", "pii"]:
            return DecisionResult(
                location=ExecutionLocation.LOCAL,
                model=task.model_local,
                reason="sensitive_data",
                confidence=1.0
            )

        # 2. Use cloud for high-quality requirements
        if task.quality_requirement == "high":
            return DecisionResult(
                location=ExecutionLocation.CLOUD,
                model=task.model_cloud,
                reason="high_quality_required",
                confidence=0.95
            )

        # 3. Use cloud for complex tasks
        if task.complexity == "high":
            return DecisionResult(
                location=ExecutionLocation.CLOUD,
                model=task.model_cloud,
                reason="high_complexity",
                confidence=0.85
            )

        # 4. Default to local
        return DecisionResult(
            location=ExecutionLocation.LOCAL,
            model=task.model_local,
            reason="default_local",
            confidence=0.7
        )


class HybridStrategy(DecisionStrategy):
    """Balance cost, quality, and latency."""

    def __init__(
        self,
        model_size_threshold_gb: float = 10.0,
        gpu_utilization_threshold_pct: float = 80.0,
        latency_threshold_ms: int = 500,
        batch_size_threshold: int = 10
    ):
        self.model_size_threshold_gb = model_size_threshold_gb
        self.gpu_utilization_threshold_pct = gpu_utilization_threshold_pct
        self.latency_threshold_ms = latency_threshold_ms
        self.batch_size_threshold = batch_size_threshold

    def decide(self, task: LLMTask, cost_tracker: "CostTracker") -> DecisionResult:
        """Apply hybrid decision logic (from ADR-031)."""

        # 1. Data Privacy: Never send sensitive data to cloud
        if task.data_classification in ["confidential", "pii"]:
            return DecisionResult(
                location=ExecutionLocation.LOCAL,
                model=task.model_local,
                reason="sensitive_data",
                confidence=1.0
            )

        # 2. Budget: Fallback to local if budget exceeded
        if cost_tracker.is_budget_exceeded():
            return DecisionResult(
                location=ExecutionLocation.LOCAL,
                model=task.model_local,
                reason="budget_exceeded",
                confidence=1.0
            )

        # 3. Quality Requirement: Use cloud for high-quality extraction
        if task.task_type == "extraction" and task.quality_requirement == "high":
            return DecisionResult(
                location=ExecutionLocation.CLOUD,
                model=task.model_cloud,
                reason="high_quality_extraction",
                confidence=0.95
            )

        # 4. Latency Requirement: Prefer local for low latency
        if task.latency_requirement_ms < self.latency_threshold_ms:
            return DecisionResult(
                location=ExecutionLocation.LOCAL,
                model=task.model_local,
                reason="low_latency_required",
                confidence=0.9
            )

        # 5. GPU Availability: Offload if local GPU busy
        from src.utils.gpu_monitor import get_gpu_utilization
        gpu_util = get_gpu_utilization()
        if gpu_util > self.gpu_utilization_threshold_pct:
            return DecisionResult(
                location=ExecutionLocation.CLOUD,
                model=task.model_cloud,
                reason="local_gpu_busy",
                confidence=0.85
            )

        # 6. Default: Local (cost-optimized)
        return DecisionResult(
            location=ExecutionLocation.LOCAL,
            model=task.model_local,
            reason="default_local",
            confidence=0.7
        )
```

---

### 3. Ollama Cloud Client

**File:** `src/components/execution/ollama_cloud_client.py`

```python
import httpx
from typing import Dict, Any
from src.core.logging import get_logger

logger = get_logger(__name__)


class OllamaCloudClient:
    """Client for Ollama Cloud API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://cloud.ollama.ai",
        timeout_seconds: int = 60
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.session = httpx.AsyncClient(timeout=timeout_seconds)

    async def generate(
        self,
        model: str,
        prompt: str,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Generate text using Ollama Cloud model."""
        try:
            response = await self.session.post(
                f"{self.base_url}/api/generate",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": stream
                }
            )

            response.raise_for_status()
            data = response.json()

            # Parse response
            return {
                "output": data.get("response", ""),
                "tokens_used": data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
                "cost_usd": self._calculate_cost(data.get("eval_count", 0), model)
            }

        except httpx.HTTPStatusError as e:
            logger.error("ollama_cloud_api_error", status_code=e.response.status_code, detail=str(e))
            raise
        except Exception as e:
            logger.error("ollama_cloud_unexpected_error", error=str(e))
            raise

    def _calculate_cost(self, tokens: int, model: str) -> float:
        """Calculate cost based on tokens and model pricing."""
        # Pricing: Estimated $0.001 per 1,000 tokens for 70B models
        # TODO: Update with actual Ollama Cloud pricing
        PRICING = {
            "llama3-70b-instruct": 0.001,  # $0.001 per 1k tokens
            "llama3-8b-instruct": 0.0002,  # $0.0002 per 1k tokens
            "llava-13b": 0.0005  # $0.0005 per 1k tokens
        }

        price_per_1k = PRICING.get(model, 0.001)  # Default pricing
        cost = (tokens / 1000.0) * price_per_1k
        return cost

    async def close(self):
        """Close HTTP session."""
        await self.session.aclose()
```

---

### 4. Cost Tracker

**File:** `src/components/execution/cost_tracker.py`

```python
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict
from src.core.logging import get_logger

logger = get_logger(__name__)


class CostTracker:
    """Track cloud usage costs and enforce budget limits."""

    def __init__(
        self,
        daily_budget_usd: float,
        monthly_budget_usd: float,
        alert_threshold_pct: float = 80.0
    ):
        self.daily_budget_usd = daily_budget_usd
        self.monthly_budget_usd = monthly_budget_usd
        self.alert_threshold_pct = alert_threshold_pct

        self.daily_costs: Dict[str, float] = defaultdict(float)  # date -> cost
        self.monthly_costs: Dict[str, float] = defaultdict(float)  # month -> cost

    def record(self, cost_usd: float, task_id: str):
        """Record cost for a task."""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        self.daily_costs[today] += cost_usd
        self.monthly_costs[month] += cost_usd

        # Check budget thresholds
        if self.is_budget_exceeded():
            logger.warning(
                "budget_exceeded",
                daily_cost=self.daily_costs[today],
                monthly_cost=self.monthly_costs[month],
                daily_budget=self.daily_budget_usd,
                monthly_budget=self.monthly_budget_usd,
                task_id=task_id
            )
        elif self.is_budget_alert_threshold():
            logger.warning(
                "budget_alert_threshold",
                daily_cost=self.daily_costs[today],
                monthly_cost=self.monthly_costs[month],
                daily_budget=self.daily_budget_usd,
                monthly_budget=self.monthly_budget_usd,
                threshold_pct=self.alert_threshold_pct
            )

        logger.info(
            "cost_recorded",
            task_id=task_id,
            cost_usd=cost_usd,
            daily_total=self.daily_costs[today],
            monthly_total=self.monthly_costs[month]
        )

    def is_budget_exceeded(self) -> bool:
        """Check if budget is exceeded."""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        return (
            self.daily_costs[today] >= self.daily_budget_usd
            or self.monthly_costs[month] >= self.monthly_budget_usd
        )

    def is_budget_alert_threshold(self) -> bool:
        """Check if budget alert threshold reached."""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        daily_threshold = self.daily_budget_usd * (self.alert_threshold_pct / 100.0)
        monthly_threshold = self.monthly_budget_usd * (self.alert_threshold_pct / 100.0)

        return (
            self.daily_costs[today] >= daily_threshold
            or self.monthly_costs[month] >= monthly_threshold
        )

    def get_daily_cost(self, date: str = None) -> float:
        """Get cost for a specific date (default: today)."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self.daily_costs[date]

    def get_monthly_cost(self, month: str = None) -> float:
        """Get cost for a specific month (default: current month)."""
        if month is None:
            month = datetime.now().strftime("%Y-%m")
        return self.monthly_costs[month]

    def get_budget_remaining_pct(self) -> Dict[str, float]:
        """Get remaining budget percentage."""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        daily_remaining_pct = max(0, (1 - self.daily_costs[today] / self.daily_budget_usd) * 100)
        monthly_remaining_pct = max(0, (1 - self.monthly_costs[month] / self.monthly_budget_usd) * 100)

        return {
            "daily_remaining_pct": daily_remaining_pct,
            "monthly_remaining_pct": monthly_remaining_pct
        }
```

---

## Integration Points

### Integration 1: Three-Phase Extraction (Graph RAG)

**File:** `src/components/graph_rag/three_phase_extraction.py`

**Current Implementation:**
```python
# Phase 1: Entity Extraction (local gemma-3-4b)
entities = await extract_entities_local(text)
```

**After Integration:**
```python
from src.components.execution.execution_proxy import ExecutionProxy, LLMTask

# Phase 1: Entity Extraction (hybrid: local or cloud)
task = LLMTask(
    task_id=f"extract_{document_id}",
    task_type="extraction",
    prompt=extraction_prompt,
    model_local="gemma-3-4b-it-Q8_0",
    model_cloud="llama3-70b-instruct",
    complexity="high" if page_count > 10 else "medium",
    data_classification=classify_document(text),
    quality_requirement="high"
)

result = await execution_proxy.execute(task)
entities = parse_entities(result.output)
```

---

### Integration 2: LangGraph Ingestion Pipeline

**File:** `src/components/ingestion/langgraph_nodes.py`

**New Node:** `vlm_extraction_node`

```python
async def vlm_extraction_node(state: IngestionState) -> Dict[str, Any]:
    """Extract visual elements using VLM (local or cloud)."""
    from src.components.execution.execution_proxy import ExecutionProxy, LLMTask

    # Create VLM task
    task = LLMTask(
        task_id=f"vlm_{state['document_id']}",
        task_type="vlm",
        prompt=f"Describe the visual elements in this image: {state['parsed_document'].images[0]}",
        model_local="llava:7b-v1.6-mistral-q2_K",
        model_cloud="llava-13b",
        complexity="medium",
        data_classification=state.get("data_classification", "public"),
        quality_requirement="high"
    )

    # Execute via proxy
    result = await execution_proxy.execute(task)

    # Store result
    state["vlm_descriptions"] = [result.output]
    state["vlm_cost_usd"] = result.cost_usd

    return state
```

---

### Integration 3: Generation Agent

**File:** `src/agents/generation.py`

**Current Implementation:**
```python
# Generate answer using local llama3.2:8b
answer = await ollama_client.generate(prompt=final_prompt)
```

**After Integration:**
```python
from src.components.execution.execution_proxy import ExecutionProxy, LLMTask

# Create generation task
task = LLMTask(
    task_id=f"gen_{query_id}",
    task_type="generation",
    prompt=final_prompt,
    model_local="llama3.2:8b",
    model_cloud="llama3-70b-instruct",
    complexity=analyze_query_complexity(query),
    data_classification="public",  # User queries are public
    latency_requirement_ms=1000,  # Prefer local for real-time
    quality_requirement="medium"
)

result = await execution_proxy.execute(task)
answer = result.output
```

---

## Implementation Roadmap

### Sprint 23 (Week 2-4): POC Implementation

#### Week 2: Design & Setup
- [x] Create ADR-031
- [x] Create Sprint 23 Planning
- [ ] Create this implementation guide
- [ ] Set up Ollama Cloud account + API key
- [ ] Test Ollama Cloud API access (authentication)

#### Week 3: Core Implementation
- [ ] Implement `ExecutionProxy` class
- [ ] Implement Decision Strategies (Cost, Quality, Hybrid)
- [ ] Implement `OllamaCloudClient`
- [ ] Implement `CostTracker`
- [ ] Add configuration (`config/ollama_cloud.yaml`)

#### Week 4: Integration & Testing
- [ ] Integrate with Three-Phase Extraction
- [ ] Integrate with LangGraph Pipeline (VLM node)
- [ ] Integrate with Generation Agent
- [ ] Unit tests (20 tests)
- [ ] Integration tests (10 tests)
- [ ] Benchmarking (latency, quality, cost)

### Sprint 24 (Week 1-2): Production Rollout

#### Week 1: Gradual Rollout
- [ ] Deploy to staging (10% of extraction tasks use cloud)
- [ ] Monitor cost, latency, quality metrics
- [ ] Adjust decision thresholds based on data

#### Week 2: Full Rollout
- [ ] Increase to 50% cloud usage
- [ ] Validate cost <$100/month
- [ ] Validate quality improvement ≥+10%
- [ ] Increase to 100% (if metrics acceptable)

---

## Testing Strategy

### Unit Tests (20 tests)

**File:** `tests/unit/components/execution/test_execution_proxy.py`

```python
import pytest
from src.components.execution.execution_proxy import ExecutionProxy, LLMTask
from src.components.execution.decision_strategy import HybridStrategy
from src.components.execution.cost_tracker import CostTracker


class TestExecutionProxy:
    """Test ExecutionProxy routing logic."""

    @pytest.fixture
    def execution_proxy(self):
        cost_tracker = CostTracker(daily_budget_usd=5.0, monthly_budget_usd=100.0)
        strategy = HybridStrategy()
        return ExecutionProxy(
            local_ollama_url="http://localhost:11434",
            cloud_api_key="test-key",
            cloud_base_url="https://cloud.ollama.ai",
            cost_tracker=cost_tracker,
            strategy=strategy
        )

    def test_route__sensitive_data__uses_local(self, execution_proxy):
        """Verify sensitive data always routed to local."""
        task = LLMTask(
            task_id="test_1",
            task_type="extraction",
            prompt="Extract entities from confidential document",
            model_local="gemma-3-4b",
            model_cloud="llama3-70b",
            complexity="high",
            data_classification="confidential"  # Sensitive!
        )

        decision = execution_proxy.strategy.decide(task, execution_proxy.cost_tracker)
        assert decision.location == "local"
        assert decision.reason == "sensitive_data"

    def test_route__high_quality__uses_cloud(self, execution_proxy):
        """Verify high-quality tasks routed to cloud."""
        task = LLMTask(
            task_id="test_2",
            task_type="extraction",
            prompt="Extract entities",
            model_local="gemma-3-4b",
            model_cloud="llama3-70b",
            complexity="high",
            data_classification="public",
            quality_requirement="high"
        )

        decision = execution_proxy.strategy.decide(task, execution_proxy.cost_tracker)
        assert decision.location == "cloud"
        assert decision.reason == "high_quality_extraction"

    # ... 18 more tests
```

### Integration Tests (10 tests)

**File:** `tests/integration/components/execution/test_ollama_cloud_integration.py`

```python
import pytest
from src.components.execution.execution_proxy import ExecutionProxy, LLMTask


@pytest.mark.asyncio
async def test_cloud_execution__real_api__returns_result():
    """Test real Ollama Cloud API call (requires API key)."""
    # This test requires OLLAMA_CLOUD_API_KEY environment variable
    import os
    api_key = os.getenv("OLLAMA_CLOUD_API_KEY")
    if not api_key:
        pytest.skip("OLLAMA_CLOUD_API_KEY not set")

    # Create ExecutionProxy with real API key
    from src.components.execution.cost_tracker import CostTracker
    from src.components.execution.decision_strategy import QualityOptimizedStrategy

    cost_tracker = CostTracker(daily_budget_usd=5.0, monthly_budget_usd=100.0)
    strategy = QualityOptimizedStrategy()
    proxy = ExecutionProxy(
        local_ollama_url="http://localhost:11434",
        cloud_api_key=api_key,
        cloud_base_url="https://cloud.ollama.ai",
        cost_tracker=cost_tracker,
        strategy=strategy
    )

    # Create task
    task = LLMTask(
        task_id="integration_test_1",
        task_type="extraction",
        prompt="Extract the main entity from: 'Apple released iPhone 16 in September 2025.'",
        model_local="gemma-3-4b",
        model_cloud="llama3-70b-instruct",
        complexity="medium",
        data_classification="public",
        quality_requirement="high"
    )

    # Execute
    result = await proxy.execute(task)

    # Assertions
    assert result.location == "cloud"
    assert result.model == "llama3-70b-instruct"
    assert result.output is not None
    assert result.tokens_used > 0
    assert result.cost_usd > 0
    assert result.latency_ms > 0
```

---

## Monitoring & Observability

### Prometheus Metrics

**File:** `src/components/execution/metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge

# Cost tracking
ollama_cloud_cost_total = Counter(
    "ollama_cloud_cost_usd_total",
    "Total cost incurred from Ollama Cloud (USD)"
)

ollama_cloud_cost_daily = Gauge(
    "ollama_cloud_cost_usd_daily",
    "Daily cost from Ollama Cloud (USD)"
)

ollama_cloud_budget_remaining_pct = Gauge(
    "ollama_cloud_budget_remaining_pct",
    "Remaining budget percentage",
    ["period"]  # "daily" or "monthly"
)

# Usage tracking
ollama_execution_total = Counter(
    "ollama_execution_total",
    "Total LLM executions",
    ["location", "model", "task_type"]  # "local" or "cloud"
)

ollama_tokens_total = Counter(
    "ollama_tokens_total",
    "Total tokens processed",
    ["location", "model"]
)

# Latency tracking
ollama_execution_latency_seconds = Histogram(
    "ollama_execution_latency_seconds",
    "LLM execution latency (seconds)",
    ["location", "model", "task_type"]
)

# Quality tracking (manual metrics)
extraction_accuracy = Gauge(
    "extraction_accuracy",
    "Extraction accuracy (F1 score)",
    ["location", "model"]
)
```

### Grafana Dashboard

**Dashboard:** Ollama Cloud Hybrid Execution

**Panels:**
1. **Cost Overview**
   - Daily cost (line chart)
   - Monthly cost (line chart)
   - Budget remaining (gauge: 0-100%)

2. **Usage Distribution**
   - Local vs Cloud execution ratio (pie chart)
   - Requests by task type (bar chart: extraction, generation, VLM)

3. **Latency Comparison**
   - p50/p95/p99 latency (local vs cloud, line chart)

4. **Quality Metrics**
   - Extraction accuracy: Local vs Cloud (bar chart)
   - Quality improvement % (gauge)

5. **Decision Reasons**
   - Top decision reasons (bar chart: high_quality, budget_exceeded, sensitive_data, etc.)

---

## Security & Compliance

### API Key Management

**Best Practices:**
1. **Storage:** Kubernetes Secret (not in code or .env files)
2. **Rotation:** Rotate every 90 days
3. **Access Control:** Limit to ExecutionProxy pod only
4. **Auditing:** Log all API key usage

**Kubernetes Secret:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ollama-cloud-api-key
type: Opaque
data:
  api-key: <base64-encoded-key>
```

### Data Classification

**Classification Logic:**
```python
def classify_document(text: str) -> str:
    """Classify document based on content."""
    # Check for PII
    if contains_pii(text):
        return "pii"

    # Check for confidential keywords
    confidential_keywords = ["confidential", "internal", "proprietary", "secret"]
    if any(keyword in text.lower() for keyword in confidential_keywords):
        return "confidential"

    # Check for internal data
    if is_internal_document(text):
        return "internal"

    # Default: public
    return "public"
```

### Audit Logging

**Every cloud request must log:**
```json
{
  "timestamp": "2025-11-11T14:30:00.123456Z",
  "request_id": "a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6",
  "event": "ollama_cloud_execution",
  "task_id": "extract_doc_12345",
  "task_type": "extraction",
  "data_classification": "public",
  "cloud_model": "llama3-70b-instruct",
  "tokens_used": 5000,
  "cost_usd": 0.005,
  "latency_ms": 1500,
  "decision_reason": "high_quality_required",
  "user_id": "user_001" // if applicable
}
```

---

## Cost Management

### Budget Enforcement

**Daily Budget Exceeded:**
```python
if cost_tracker.is_budget_exceeded():
    logger.warning("daily_budget_exceeded", fallback="local")
    # Force all subsequent tasks to local execution
    return DecisionResult(
        location=ExecutionLocation.LOCAL,
        model=task.model_local,
        reason="budget_exceeded",
        confidence=1.0
    )
```

**Alert at 80% Budget:**
```python
if cost_tracker.is_budget_alert_threshold():
    # Send alert to monitoring system
    send_alert(
        severity="warning",
        message=f"80% of daily budget reached: ${cost_tracker.get_daily_cost():.2f} / ${cost_tracker.daily_budget_usd:.2f}"
    )
```

### Cost Optimization Tips

1. **Batch Processing:** Send multiple extractions in one request (reduces overhead)
2. **Caching:** Cache LLM responses for repeated queries (30-40% cost reduction)
3. **Model Selection:** Use smallest cloud model that meets quality requirements
4. **Local Fallback:** Always fallback to local when possible
5. **Budget Alerts:** Set alerts at 50%, 80%, 90%, 100% of budget

---

## Appendix: Configuration Example

**File:** `config/ollama_cloud.yaml`

```yaml
ollama_cloud:
  # Enable/disable cloud execution
  enabled: true

  # API credentials
  api_key: ${OLLAMA_CLOUD_API_KEY}  # From environment variable
  base_url: "https://cloud.ollama.ai"

  # Cloud models (larger than local models)
  models:
    extraction_cloud: "llama3-70b-instruct"
    generation_cloud: "llama3-8b-instruct"
    vision_cloud: "llava-13b"

  # Cost limits
  cost_limits:
    daily_budget_usd: 5.0
    monthly_budget_usd: 100.0
    alert_threshold_pct: 80

  # Decision strategy: "cost_optimized", "quality_optimized", "hybrid"
  decision_strategy: "hybrid"

  # Decision thresholds (for HybridStrategy)
  decision_thresholds:
    model_size_threshold_gb: 10.0
    gpu_utilization_threshold_pct: 80.0
    latency_threshold_ms: 500
    batch_size_threshold: 10

  # Fallback behavior
  fallback:
    on_budget_exceeded: "local"
    on_cloud_unavailable: "local"
    on_rate_limit: "queue"  # "queue" or "local"

  # Cache settings (optional)
  cache:
    enabled: false
    ttl_seconds: 86400  # 24 hours
    max_size_mb: 2048
```

---

**Document Status:** 📋 DRAFT (2025-11-11)
**Next Update:** After POC completion (Sprint 23, Week 4)
**Owner:** Backend Team (Klaus Pommer)
