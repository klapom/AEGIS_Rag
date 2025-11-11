# Mozilla ANY-LLM Integration: Implementation Guide

**Document Type:** Technical Implementation Guide
**Status:** 📋 PLANNED (Sprint 23, Feature 23.4 - Revised)
**Owner:** Backend Team
**Date:** 2025-11-11
**Related ADR:** ADR-033

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Installation & Setup](#installation--setup)
4. [AegisLLMProxy Implementation](#aegisllmproxy-implementation)
5. [Configuration Management](#configuration-management)
6. [Provider Setup](#provider-setup)
7. [Budget Management](#budget-management)
8. [Routing Strategies](#routing-strategies)
9. [Integration with LangGraph](#integration-with-langgraph)
10. [Testing Strategy](#testing-strategy)
11. [Monitoring & Observability](#monitoring--observability)
12. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 5-Minute Setup (Local Testing)

```bash
# 1. Install ANY-LLM SDK
poetry add 'any-llm-sdk[openai,ollama]'

# 2. Set environment variables
export OPENAI_API_KEY="sk-..."
export OLLAMA_BASE_URL="http://localhost:11434"

# 3. Test basic usage
python
```

```python
from any_llm import AnyLLM, Provider

# Initialize with multiple providers
llm = AnyLLM(
    providers=[
        Provider.OLLAMA(base_url="http://localhost:11434"),
        Provider.OPENAI(api_key="sk-..."),
    ]
)

# Test local Ollama
response = llm.completions.create(
    provider="ollama",
    model="gemma-3-4b-it-Q8_0",
    messages=[{"role": "user", "content": "What is RAG?"}],
)
print(response.choices[0].message.content)

# Test OpenAI
response = llm.completions.create(
    provider="openai",
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What is RAG?"}],
)
print(response.choices[0].message.content)
```

**Expected Output:**
```
Local Ollama: RAG stands for Retrieval-Augmented Generation...
OpenAI: RAG (Retrieval-Augmented Generation) is a framework...
```

---

## Architecture Overview

### Current Architecture (Pre-ANY-LLM)

```
┌─────────────────────────────────────────────────────────┐
│              AegisRAG Application                       │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Hardcoded Ollama Calls (via langchain-ollama)  │   │
│  │  - src/components/graph_rag/extraction/         │   │
│  │  - src/components/ingestion/langgraph_nodes.py  │   │
│  │  - src/agents/coordinator.py                    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Local Ollama         │
            │  http://localhost:11434│
            └───────────────────────┘
```

**Limitations:**
- ❌ Single provider (local Ollama only)
- ❌ No budget management
- ❌ No fallback mechanism
- ❌ Hard to add new providers

---

### New Architecture (With ANY-LLM)

```
┌─────────────────────────────────────────────────────────────────┐
│                    AegisRAG Application                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  LangGraph Nodes, Agents, Extraction                     │   │
│  │  (call AegisLLMProxy instead of hardcoded Ollama)       │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│       ┌───────────────────────────────────────┐                │
│       │   AegisLLMProxy (400 LOC)             │                │
│       │   - Data privacy routing (PII→local)  │                │
│       │   - Quality-based routing             │                │
│       │   - Metrics tracking                  │                │
│       └────────────────┬──────────────────────┘                │
│                        │                                        │
└────────────────────────┼────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────┐
         │   Mozilla ANY-LLM SDK             │
         │   - Multi-provider abstraction    │
         │   - Budget management (built-in)  │
         │   - Connection pooling            │
         │   - Automatic fallback            │
         └────────────────┬──────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│Local Ollama  │  │Ollama Cloud  │  │  OpenAI API  │
│localhost:11434│  │ollama.cloud  │  │api.openai.com│
└──────────────┘  └──────────────┘  └──────────────┘
```

**Benefits:**
- ✅ Three providers (local, Ollama Cloud, OpenAI)
- ✅ Built-in budget management (ANY-LLM)
- ✅ Automatic fallback (ANY-LLM)
- ✅ Easy to add more providers (Anthropic, Mistral, etc.)

---

## Installation & Setup

### Step 1: Install Dependencies

```bash
# Add ANY-LLM SDK to pyproject.toml
poetry add 'any-llm-sdk[openai,ollama]'

# Install
poetry install
```

**Version Requirements:**
- Python: 3.11+ (we have 3.12.7 ✅)
- any-llm-sdk: ~1.2.0 (latest stable)

---

### Step 2: Environment Variables

Create `.env` file:

```bash
# Local Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Ollama Cloud (when available)
OLLAMA_CLOUD_BASE_URL=https://ollama.cloud
OLLAMA_CLOUD_API_KEY=your-ollama-cloud-key

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_ORGANIZATION=org-...  # Optional

# Budget Limits (monthly, USD)
BUDGET_OLLAMA_CLOUD=120.0
BUDGET_OPENAI=80.0
```

---

### Step 3: Update pyproject.toml

```toml
[tool.poetry.dependencies]
python = "^3.12"
# ... existing dependencies ...

# NEW: ANY-LLM SDK
any-llm-sdk = {extras = ["openai", "ollama"], version = "~1.2.0"}

# OPTIONAL: ANY-LLM Gateway (for advanced observability)
# any-llm-gateway = "~1.2.0"
```

---

## AegisLLMProxy Implementation

### File Structure

```
src/components/llm_proxy/
├── __init__.py                 # Exports AegisLLMProxy
├── aegis_llm_proxy.py          # Main proxy class (300 LOC)
├── models.py                   # Pydantic models (50 LOC)
├── config.py                   # Configuration loader (50 LOC)
└── README.md                   # Documentation
```

---

### Core Implementation

**File:** `src/components/llm_proxy/aegis_llm_proxy.py`

```python
"""
AegisRAG LLM Proxy using Mozilla ANY-LLM.

This module provides a thin wrapper around Mozilla's ANY-LLM framework,
adding AegisRAG-specific routing logic while leveraging ANY-LLM's
multi-provider abstraction, budget management, and fallback mechanisms.

Sprint Context: Sprint 23 (2025-11-11) - Feature 23.4 (revised with ANY-LLM)
Related ADR: ADR-033 (Mozilla ANY-LLM Integration)
"""

import structlog
from typing import Optional, List, Dict, Any
from any_llm import AnyLLM, Provider, BudgetManager, BudgetExceededError
from pydantic import BaseModel

from src.components.llm_proxy.models import LLMTask, ExecutionLocation, LLMResponse
from src.components.llm_proxy.config import LLMProxyConfig
from src.core.exceptions import LLMExecutionError

logger = structlog.get_logger(__name__)


class AegisLLMProxy:
    """
    AegisRAG-specific LLM proxy with intelligent routing.

    Architecture:
        User → AegisLLMProxy (routing) → ANY-LLM (execution) → Providers

    Responsibilities:
        - Data privacy enforcement (PII/HIPAA → local only)
        - Quality-based routing (critical → OpenAI)
        - Complexity-based routing (high → Ollama Cloud)
        - Default routing (simple → local)
        - Metrics tracking (Prometheus, LangSmith)

    ANY-LLM handles:
        - Multi-provider abstraction
        - Budget management and enforcement
        - Connection pooling
        - Automatic fallback (provider → provider → local)
    """

    def __init__(self, config: Optional[LLMProxyConfig] = None):
        """
        Initialize AegisLLMProxy with configuration.

        Args:
            config: Configuration for providers, budgets, routing
                    If None, loads from environment variables + config files
        """
        self.config = config or LLMProxyConfig.from_env()

        # Initialize ANY-LLM with all configured providers
        self.any_llm = self._initialize_any_llm()

        # Budget manager (ANY-LLM built-in)
        self.budget_manager = self._initialize_budget_manager()

        logger.info(
            "aegis_llm_proxy_initialized",
            providers=len(self.config.providers),
            budgets=self.config.budgets,
        )

    def _initialize_any_llm(self) -> AnyLLM:
        """Initialize ANY-LLM with configured providers."""
        providers = []

        # Local Ollama
        if "local_ollama" in self.config.providers:
            local_config = self.config.providers["local_ollama"]
            providers.append(
                Provider.OLLAMA(
                    base_url=local_config["base_url"],
                    timeout=local_config.get("timeout", 60),
                )
            )

        # Ollama Cloud
        if "ollama_cloud" in self.config.providers:
            cloud_config = self.config.providers["ollama_cloud"]
            providers.append(
                Provider.OLLAMA(
                    base_url=cloud_config["base_url"],
                    api_key=cloud_config["api_key"],
                    timeout=cloud_config.get("timeout", 120),
                )
            )

        # OpenAI
        if "openai" in self.config.providers:
            openai_config = self.config.providers["openai"]
            providers.append(
                Provider.OPENAI(
                    api_key=openai_config["api_key"],
                    organization=openai_config.get("organization"),
                    timeout=openai_config.get("timeout", 60),
                )
            )

        return AnyLLM(providers=providers)

    def _initialize_budget_manager(self) -> BudgetManager:
        """Initialize ANY-LLM budget manager."""
        return BudgetManager(
            monthly_limits=self.config.budgets.get("monthly_limits", {}),
            alert_threshold=self.config.budgets.get("alert_threshold", 0.8),  # 80%
        )

    async def generate(
        self,
        task: LLMTask,
        stream: bool = False,
    ) -> LLMResponse:
        """
        Generate LLM response with intelligent routing.

        Args:
            task: LLM task with prompt, quality requirements, data classification
            stream: Enable streaming response (token-by-token)

        Returns:
            LLMResponse with content, provider used, metrics

        Raises:
            LLMExecutionError: If all providers fail
        """
        # Step 1: AEGIS ROUTING LOGIC (custom)
        provider, reason = self._route_task(task)

        # Step 2: ANY-LLM EXECUTION (built-in)
        try:
            result = await self._execute_with_any_llm(
                provider=provider,
                task=task,
                stream=stream,
            )

            # Step 3: AEGIS METRICS (custom)
            self._track_metrics(provider, task, result)

            return result

        except BudgetExceededError as e:
            # ANY-LLM detected budget exceeded → fallback to local
            logger.warning(
                "budget_exceeded_fallback",
                provider=provider,
                fallback="local_ollama",
                budget_limit=e.limit,
            )
            return await self._execute_with_any_llm(
                provider="local_ollama",
                task=task,
                stream=stream,
            )

        except Exception as e:
            # ANY-LLM automatic fallback failed → raise error
            logger.error(
                "llm_execution_failed_all_providers",
                task_id=task.id,
                last_provider=provider,
                error=str(e),
            )
            raise LLMExecutionError(
                f"All LLM providers failed for task {task.id}"
            ) from e

    def _route_task(self, task: LLMTask) -> tuple[str, str]:
        """
        Route task to optimal provider (AEGIS CUSTOM LOGIC).

        Returns:
            (provider_name, routing_reason)
        """
        # PRIORITY 1: Data Privacy (PII/HIPAA always local)
        if task.data_classification in ["pii", "hipaa", "confidential"]:
            logger.info(
                "routing_data_privacy",
                classification=task.data_classification,
                provider="local_ollama",
            )
            return ("local_ollama", "sensitive_data_local_only")

        # PRIORITY 2: Task Type (embeddings always local)
        if task.task_type == "embedding":
            return ("local_ollama", "embeddings_local_only")

        # PRIORITY 3: Quality Critical + High Complexity → OpenAI
        if (
            task.quality_requirement == "critical"
            and task.complexity in ["high", "very_high"]
            and "openai" in self.config.providers
        ):
            return ("openai", "critical_quality_high_complexity")

        # PRIORITY 4: High Quality or Batch Processing → Ollama Cloud
        if "ollama_cloud" in self.config.providers:
            if task.quality_requirement == "high" and task.complexity == "high":
                return ("ollama_cloud", "high_quality_cost_effective")

            if hasattr(task, "batch_size") and task.batch_size > 10:
                return ("ollama_cloud", "batch_processing")

        # DEFAULT: Local Ollama (70% of tasks)
        return ("local_ollama", "default_local")

    async def _execute_with_any_llm(
        self,
        provider: str,
        task: LLMTask,
        stream: bool,
    ) -> LLMResponse:
        """
        Execute task with ANY-LLM (handles provider abstraction).

        ANY-LLM responsibilities:
            - Convert to provider-specific API format
            - Handle connection pooling
            - Track costs (if BudgetManager enabled)
            - Automatic retry on transient errors
            - Fallback to next provider on failure
        """
        model = self._get_model_for_provider(provider, task)

        messages = [{"role": "user", "content": task.prompt}]

        # ANY-LLM unified API (works with all providers)
        response = await self.any_llm.completions.create(
            provider=provider,
            model=model,
            messages=messages,
            max_tokens=task.max_tokens,
            temperature=task.temperature,
            stream=stream,
        )

        # Convert ANY-LLM response to AegisRAG format
        return LLMResponse(
            content=response.choices[0].message.content,
            provider=provider,
            model=model,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            cost_usd=self._calculate_cost(provider, response),
            latency_ms=response.latency_ms if hasattr(response, "latency_ms") else None,
        )

    def _get_model_for_provider(self, provider: str, task: LLMTask) -> str:
        """Get optimal model for provider and task."""
        model_map = {
            "local_ollama": task.model_local or "gemma-3-4b-it-Q8_0",
            "ollama_cloud": task.model_cloud or "llama3-70b",
            "openai": task.model_openai or "gpt-4o",
        }
        return model_map.get(provider, task.model_local)

    def _calculate_cost(self, provider: str, response) -> float:
        """Calculate cost for this request (USD)."""
        if not response.usage:
            return 0.0

        tokens = response.usage.total_tokens
        pricing = {
            "local_ollama": 0.0,  # Free
            "ollama_cloud": 0.000001,  # $0.001 per 1k tokens
            "openai": 0.000015,  # $0.015 per 1k tokens (avg GPT-4o)
        }
        return tokens * pricing.get(provider, 0.0)

    def _track_metrics(self, provider: str, task: LLMTask, result: LLMResponse):
        """Track metrics for observability (Prometheus, LangSmith)."""
        # Prometheus metrics
        from src.core.metrics import llm_requests_total, llm_latency_seconds, llm_cost_usd

        llm_requests_total.labels(provider=provider, task_type=task.task_type).inc()

        if result.latency_ms:
            llm_latency_seconds.labels(provider=provider).observe(
                result.latency_ms / 1000
            )

        llm_cost_usd.labels(provider=provider).observe(result.cost_usd)

        # LangSmith tracing (if enabled)
        # ... (add LangSmith tags for provider, model, cost)


# Factory function for easy instantiation
def get_aegis_llm_proxy() -> AegisLLMProxy:
    """
    Get singleton instance of AegisLLMProxy.

    Usage:
        from src.components.llm_proxy import get_aegis_llm_proxy

        proxy = get_aegis_llm_proxy()
        response = await proxy.generate(task)
    """
    # Singleton pattern (lazy initialization)
    if not hasattr(get_aegis_llm_proxy, "_instance"):
        get_aegis_llm_proxy._instance = AegisLLMProxy()
    return get_aegis_llm_proxy._instance
```

---

### Pydantic Models

**File:** `src/components/llm_proxy/models.py`

```python
"""Pydantic models for LLM proxy."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from uuid import uuid4, UUID


class TaskType(str, Enum):
    """LLM task types."""

    EMBEDDING = "embedding"
    EXTRACTION = "extraction"
    GENERATION = "generation"
    CODE_GENERATION = "code_generation"
    RESEARCH = "research"


class DataClassification(str, Enum):
    """Data sensitivity classification (for GDPR/HIPAA compliance)."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PII = "pii"  # Personal Identifiable Information (GDPR)
    HIPAA = "hipaa"  # Protected Health Information (HIPAA)


class QualityRequirement(str, Enum):
    """Quality requirement for task."""

    LOW = "low"  # Local OK (75% accuracy)
    MEDIUM = "medium"  # Local or Ollama Cloud (75-85%)
    HIGH = "high"  # Ollama Cloud preferred (85%)
    CRITICAL = "critical"  # OpenAI required (95%)


class Complexity(str, Enum):
    """Task complexity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class LLMTask(BaseModel):
    """LLM task definition."""

    id: UUID = Field(default_factory=uuid4)
    task_type: TaskType
    prompt: str
    data_classification: DataClassification = DataClassification.PUBLIC
    quality_requirement: QualityRequirement = QualityRequirement.MEDIUM
    complexity: Complexity = Complexity.MEDIUM

    # Model preferences (optional, provider-specific)
    model_local: Optional[str] = None
    model_cloud: Optional[str] = None
    model_openai: Optional[str] = None

    # Generation parameters
    max_tokens: int = 1024
    temperature: float = 0.1
    batch_size: Optional[int] = None  # For batch processing


class LLMResponse(BaseModel):
    """LLM response with metadata."""

    content: str
    provider: str
    model: str
    tokens_used: int
    cost_usd: float
    latency_ms: Optional[float] = None
```

---

## Configuration Management

**File:** `config/llm_config.yml`

```yaml
# LLM Proxy Configuration
# Sprint 23 (Feature 23.4 - ANY-LLM Integration)

providers:
  local_ollama:
    base_url: "${OLLAMA_BASE_URL:-http://localhost:11434}"
    timeout: 60
    models:
      - gemma-3-4b-it-Q8_0
      - llama3.2:8b
      - BGE-M3  # Embeddings

  ollama_cloud:
    base_url: "${OLLAMA_CLOUD_BASE_URL:-https://ollama.cloud}"
    api_key: "${OLLAMA_CLOUD_API_KEY}"
    timeout: 120
    models:
      - llama3-70b
      - llava-13b
      - mistral-7b

  openai:
    api_key: "${OPENAI_API_KEY}"
    organization: "${OPENAI_ORGANIZATION:-}"
    timeout: 60
    models:
      - gpt-4o
      - gpt-4o-mini
      - gpt-4

budgets:
  monthly_limits:
    ollama_cloud: 120.0  # $120/month
    openai: 80.0         # $80/month
  alert_threshold: 0.8   # Alert at 80% of budget

routing:
  default_provider: local_ollama
  quality_critical_provider: openai
  batch_processing_provider: ollama_cloud

  # Data classification overrides (security-critical)
  data_classification_overrides:
    pii: local_ollama       # GDPR compliance
    hipaa: local_ollama     # HIPAA compliance
    confidential: local_ollama

  # Task type overrides
  task_type_overrides:
    embedding: local_ollama  # Always local (no cloud benefit)
```

---

**File:** `src/components/llm_proxy/config.py`

```python
"""Configuration loader for LLM proxy."""

import os
import yaml
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Any


class LLMProxyConfig(BaseModel):
    """Configuration for AegisLLMProxy."""

    providers: Dict[str, Dict[str, Any]]
    budgets: Dict[str, Any]
    routing: Dict[str, Any]

    @classmethod
    def from_env(cls) -> "LLMProxyConfig":
        """Load configuration from environment + YAML file."""
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "llm_config.yml"

        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Interpolate environment variables
        config_str = yaml.dump(config_data)
        for key, value in os.environ.items():
            config_str = config_str.replace(f"${{{key}}}", value)
            config_str = config_str.replace(f"${{{key}:-", f"{value or '")

        config_data = yaml.safe_load(config_str)

        return cls(**config_data)
```

---

## Provider Setup

### Local Ollama (Tier 1)

```bash
# Already running on localhost:11434
# No additional setup required
```

### Ollama Cloud (Tier 2)

```bash
# 1. Sign up at https://ollama.cloud
# 2. Get API key
# 3. Set environment variable
export OLLAMA_CLOUD_API_KEY="your-key-here"
```

### OpenAI (Tier 3)

```bash
# 1. Sign up at https://platform.openai.com
# 2. Get API key from https://platform.openai.com/api-keys
# 3. Set environment variables
export OPENAI_API_KEY="sk-..."
export OPENAI_ORGANIZATION="org-..."  # Optional
```

---

## Budget Management

ANY-LLM has **built-in budget management**. We just configure limits:

```python
# Automatically enforced by ANY-LLM
budget_manager = BudgetManager(
    monthly_limits={
        "ollama_cloud": 120.0,  # $120/month
        "openai": 80.0,         # $80/month
    },
    alert_threshold=0.8  # Alert at 80%
)
```

**When budget exceeded:**
1. ANY-LLM raises `BudgetExceededError`
2. AegisLLMProxy catches exception
3. Automatically falls back to local (free)

**Budget tracking:**
- ANY-LLM tracks costs per provider
- Resets monthly
- Prometheus metrics exposed
- Grafana dashboard shows utilization

---

## Routing Strategies

### Example 1: Simple Query (Default → Local)

```python
task = LLMTask(
    task_type=TaskType.GENERATION,
    prompt="What is RAG?",
    quality_requirement=QualityRequirement.MEDIUM,
    complexity=Complexity.LOW,
)

# Routes to: local_ollama (reason: default_local)
# Cost: $0
# Latency: ~100ms
```

### Example 2: Legal Document (Critical → OpenAI)

```python
task = LLMTask(
    task_type=TaskType.EXTRACTION,
    prompt="Extract clauses from this contract...",
    data_classification=DataClassification.CONFIDENTIAL,  # Would force local!
    quality_requirement=QualityRequirement.CRITICAL,
    complexity=Complexity.HIGH,
)

# Routes to: local_ollama (reason: sensitive_data_local_only)
# Cost: $0 (GDPR compliance overrides quality)
```

### Example 3: Medical Record (PII → Local)

```python
task = LLMTask(
    task_type=TaskType.EXTRACTION,
    prompt="Extract diagnosis from patient record...",
    data_classification=DataClassification.HIPAA,  # HIPAA-protected
    quality_requirement=QualityRequirement.CRITICAL,
    complexity=Complexity.HIGH,
)

# Routes to: local_ollama (reason: sensitive_data_local_only)
# Cost: $0 (HIPAA compliance mandatory)
```

### Example 4: Batch Processing (Scale → Ollama Cloud)

```python
task = LLMTask(
    task_type=TaskType.EXTRACTION,
    prompt="Extract entities from 100 documents...",
    quality_requirement=QualityRequirement.HIGH,
    complexity=Complexity.HIGH,
    batch_size=100,
)

# Routes to: ollama_cloud (reason: batch_processing)
# Cost: ~$20 (200k tokens @ $0.001/1k)
# Latency: Parallel processing (~5 minutes for 100 docs)
```

---

## Integration with LangGraph

### Before (Hardcoded Ollama)

```python
# src/components/graph_rag/extraction/llm_extraction.py
from langchain_ollama import ChatOllama

llm = ChatOllama(model="gemma-3-4b-it-Q8_0", base_url="http://localhost:11434")

def extract_entities(text: str) -> List[Entity]:
    prompt = f"Extract entities from: {text}"
    response = llm.invoke(prompt)
    return parse_entities(response.content)
```

---

### After (ANY-LLM via AegisLLMProxy)

```python
# src/components/graph_rag/extraction/llm_extraction.py
from src.components.llm_proxy import get_aegis_llm_proxy
from src.components.llm_proxy.models import LLMTask, TaskType, QualityRequirement

proxy = get_aegis_llm_proxy()

async def extract_entities(text: str, quality: str = "medium") -> List[Entity]:
    """Extract entities with intelligent routing."""

    task = LLMTask(
        task_type=TaskType.EXTRACTION,
        prompt=f"Extract entities from: {text}",
        quality_requirement=QualityRequirement(quality),
        complexity=Complexity.HIGH,
    )

    response = await proxy.generate(task)

    logger.info(
        "entity_extraction_complete",
        provider=response.provider,
        model=response.model,
        tokens=response.tokens_used,
        cost_usd=response.cost_usd,
    )

    return parse_entities(response.content)
```

**Benefits:**
- ✅ Automatic provider selection (local/Ollama/OpenAI)
- ✅ Budget enforcement (ANY-LLM)
- ✅ Fallback on failure (ANY-LLM)
- ✅ Cost tracking (AegisLLMProxy)

---

## Testing Strategy

### Unit Tests (30 tests)

**File:** `tests/unit/llm_proxy/test_aegis_llm_proxy.py`

```python
import pytest
from src.components.llm_proxy import AegisLLMProxy
from src.components.llm_proxy.models import LLMTask, DataClassification, QualityRequirement

@pytest.fixture
def proxy():
    return AegisLLMProxy()

def test_routing_pii_data_always_local(proxy):
    """PII data must always route to local (GDPR)."""
    task = LLMTask(
        task_type=TaskType.EXTRACTION,
        prompt="Extract PII...",
        data_classification=DataClassification.PII,
        quality_requirement=QualityRequirement.CRITICAL,  # Even critical → local
    )

    provider, reason = proxy._route_task(task)

    assert provider == "local_ollama"
    assert reason == "sensitive_data_local_only"

def test_routing_critical_quality_routes_to_openai(proxy):
    """Critical quality + high complexity → OpenAI."""
    task = LLMTask(
        task_type=TaskType.EXTRACTION,
        prompt="Extract legal clauses...",
        data_classification=DataClassification.PUBLIC,
        quality_requirement=QualityRequirement.CRITICAL,
        complexity=Complexity.HIGH,
    )

    provider, reason = proxy._route_task(task)

    assert provider == "openai"
    assert reason == "critical_quality_high_complexity"

def test_routing_batch_processing_routes_to_ollama_cloud(proxy):
    """Batch processing (>10 docs) → Ollama Cloud."""
    task = LLMTask(
        task_type=TaskType.EXTRACTION,
        prompt="Batch extract...",
        quality_requirement=QualityRequirement.HIGH,
        batch_size=50,
    )

    provider, reason = proxy._route_task(task)

    assert provider == "ollama_cloud"
    assert reason == "batch_processing"

# ... 27 more tests
```

---

### Integration Tests (15 tests)

**File:** `tests/integration/llm_proxy/test_any_llm_integration.py`

```python
@pytest.mark.asyncio
async def test_generate_with_local_ollama():
    """Test actual generation with local Ollama."""
    proxy = get_aegis_llm_proxy()

    task = LLMTask(
        task_type=TaskType.GENERATION,
        prompt="What is 2+2?",
        quality_requirement=QualityRequirement.LOW,
    )

    response = await proxy.generate(task)

    assert response.provider == "local_ollama"
    assert "4" in response.content
    assert response.cost_usd == 0.0  # Free

@pytest.mark.asyncio
async def test_budget_exceeded_fallback():
    """Test fallback to local when budget exceeded."""
    # ... set budget to $0.01 ...
    # ... make expensive OpenAI call ...
    # ... verify fallback to local ...
```

---

### E2E Tests (5 tests)

**File:** `tests/e2e/test_llm_proxy_e2e.py`

```python
@pytest.mark.asyncio
async def test_full_extraction_pipeline_with_routing():
    """Test full extraction pipeline (ingestion → extraction → graph)."""
    # Upload PDF → Docling → Extraction (ANY-LLM) → Neo4j
    # Verify correct provider used based on document classification
```

---

## Monitoring & Observability

### Prometheus Metrics

```python
# src/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request counters per provider
llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["provider", "task_type", "status"],
)

# Latency per provider
llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "LLM request latency",
    ["provider"],
)

# Cost tracking
llm_cost_usd = Gauge(
    "llm_cost_usd_total",
    "Total LLM cost (USD)",
    ["provider"],
)

# Budget utilization
llm_budget_utilization = Gauge(
    "llm_budget_utilization",
    "Budget utilization (0-1)",
    ["provider"],
)
```

---

### Grafana Dashboard

**Dashboard:** `LLM Proxy Observability`

**Panels:**
1. **Provider Distribution** (Pie chart)
   - Local: 70% (green)
   - Ollama Cloud: 20% (yellow)
   - OpenAI: 10% (red)

2. **Cost per Provider** (Time series)
   - Ollama Cloud: $120/month
   - OpenAI: $80/month
   - Local: $0

3. **Budget Utilization** (Gauge)
   - Ollama: 85% (warning at 80%)
   - OpenAI: 65%

4. **Latency p95** (Time series)
   - Local: 100ms
   - Ollama Cloud: 400ms
   - OpenAI: 500ms

5. **Error Rate** (Time series)
   - Total errors: <1%
   - Fallback rate: <5%

---

## Troubleshooting

### Issue 1: `BudgetExceededError` raised unexpectedly

**Symptom:**
```
any_llm.exceptions.BudgetExceededError: Budget limit of $120.00 exceeded for provider 'ollama_cloud'
```

**Solution:**
1. Check budget utilization: `llm_budget_utilization{provider="ollama_cloud"}`
2. Increase budget in `config/llm_config.yml`:
   ```yaml
   budgets:
     monthly_limits:
       ollama_cloud: 200.0  # Increase to $200
   ```
3. Or wait until next month (budget resets monthly)

---

### Issue 2: PII data accidentally sent to cloud

**Prevention (code-enforced):**
```python
# FIRST check in routing logic
if task.data_classification in ["pii", "hipaa", "confidential"]:
    return ("local_ollama", "sensitive_data_local_only")
```

**Validation:**
- Unit test: `test_routing_pii_data_always_local`
- Pre-commit hook: Check for hardcoded API calls bypassing proxy

---

### Issue 3: OpenAI API key invalid

**Symptom:**
```
any_llm.exceptions.AuthenticationError: Incorrect API key provided
```

**Solution:**
1. Verify API key: `echo $OPENAI_API_KEY`
2. Check OpenAI dashboard: https://platform.openai.com/api-keys
3. Regenerate key if compromised
4. Update `.env` file

---

## Next Steps

1. **Week 1 (POC):** Implement AegisLLMProxy, test with 3 providers
2. **Week 2 (Integration):** Replace hardcoded Ollama calls in LangGraph
3. **Weeks 3-4 (Rollout):** Gradual rollout 10% → 100% with monitoring

---

**Document Version:** 1.0
**Last Updated:** 2025-11-11
**Owner:** Backend Team
**Related ADR:** ADR-033
